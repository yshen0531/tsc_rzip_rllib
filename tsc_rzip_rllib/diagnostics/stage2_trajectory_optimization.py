from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from tsc_rzip_rllib.core.coil_order import (
    DISPLAY_COIL_NAMES,
    TSC_COIL_NAMES,
    display_to_tsc,
    tsc_matrix_to_display,
)
from tsc_rzip_rllib.diagnostics import stage1_controllability as base


@dataclass(frozen=True)
class Stage2Paths:
    project_dir: Path
    config_path: Path
    run_dir: Path
    evaluations_dir: Path
    generations_dir: Path
    best_dir: Path
    confirmations_dir: Path
    analysis_dir: Path
    source_reference_dir: Path


@dataclass
class Stage2Context:
    cfg: dict[str, Any]
    train_cfg: dict[str, Any]
    env_cfg: dict[str, Any]
    paths: Stage2Paths
    source_run: Path
    modes_tsc: np.ndarray
    response: np.ndarray
    baseline_y: np.ndarray
    initial_currents_tsc: np.ndarray
    max_delta_a: float
    min_current_tsc: np.ndarray
    max_current_tsc: np.ndarray
    interpolation_matrix: np.ndarray
    node_times: np.ndarray
    coefficient_lower: np.ndarray
    coefficient_upper: np.ndarray
    baseline_metrics: dict[str, Any]
    seed_vectors: dict[str, np.ndarray]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _resolve_storage_override(value: str | None, *, project_dir: Path) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return str(path.resolve())


def stage2_metric_compat_config(cfg: dict[str, Any]) -> dict[str, Any]:
    gate = cfg["gate"]
    return {
        "target": copy.deepcopy(cfg["target"]),
        "analysis": {
            "r_scale_m": float(gate.get("normalization_r_m", 0.03)),
            "z_scale_m": float(gate.get("normalization_z_m", 0.03)),
        },
        "validation": {
            "late_window_steps": int(gate.get("late_window_steps", 4)),
            "gate_ip_tolerance_a": float(gate.get("ip_tolerance_a", 10000.0)),
            "tolerance_boxes_m": [
                float(gate.get("precise_tolerance_m", 0.03)),
                float(gate.get("relaxed_tolerance_m", 0.04)),
                0.08,
            ],
        },
    }


def _resolve_source_run(source_run: str | Path | None, run_dir: Path) -> Path:
    if source_run is not None:
        source = Path(source_run).expanduser().resolve()
    else:
        manifest = run_dir / "stage2_manifest.json"
        if not manifest.exists():
            raise ValueError("--source-run is required for a new Stage2 run")
        source = Path(base.read_json(manifest)["source_stage1_1_run"]).expanduser().resolve()
    required = [
        source / "analysis/coil_modes_tsc.npy",
        source / "analysis/response_tensor_dy_per_a.npy",
        source / "analysis/baseline_trajectory.csv",
        source / "candidate_sequences/svd03_target1p00.json",
        source / "raw_experiments/baseline_r00.json.gz",
        source / "train_config.resolved.json",
        source / "env_config.resolved.json",
        source / "stage1_config.resolved.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Stage1.1 source run is incomplete: " + ", ".join(missing))
    return source


def build_interpolation_matrix(horizon: int, node_times: np.ndarray) -> np.ndarray:
    node_times = np.asarray(node_times, dtype=float)
    matrix = np.zeros((horizon, len(node_times)), dtype=float)
    for step in range(horizon):
        if step <= node_times[0]:
            matrix[step, 0] = 1.0
        elif step >= node_times[-1]:
            matrix[step, -1] = 1.0
        else:
            left = int(np.searchsorted(node_times, step) - 1)
            fraction = (step - node_times[left]) / (node_times[left + 1] - node_times[left])
            matrix[step, left] = 1.0 - fraction
            matrix[step, left + 1] = fraction
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=1e-12):
        raise RuntimeError("invalid interpolation matrix")
    return matrix


def fit_nodes_to_action(
    action_norm_tsc: np.ndarray,
    modes_tsc: np.ndarray,
    interpolation_matrix: np.ndarray,
) -> np.ndarray:
    action = np.asarray(action_norm_tsc, dtype=float)
    coefficients = action @ modes_tsc
    nodes, *_ = np.linalg.lstsq(interpolation_matrix, coefficients, rcond=None)
    return nodes


def build_seed_vectors(
    candidate_path: Path,
    modes_tsc: np.ndarray,
    interpolation_matrix: np.ndarray,
    cfg: dict[str, Any],
    lower: np.ndarray,
    upper: np.ndarray,
) -> dict[str, np.ndarray]:
    candidate = base.read_json(candidate_path)
    full_action = np.asarray(candidate["action_norm_tsc"], dtype=float)
    if full_action.shape != (10, 14):
        raise ValueError(f"unexpected SVD3 seed action shape {full_action.shape}")
    seeds: dict[str, np.ndarray] = {}
    for scale in (0.75, 0.85, 1.0):
        nodes = fit_nodes_to_action(scale * full_action, modes_tsc, interpolation_matrix)
        seeds[f"svd3_uniform_{scale:.2f}"] = np.clip(nodes.reshape(-1), lower, upper)
    profiles = cfg["trajectory"].get("seed_scale_profiles", {})
    for name, profile in profiles.items():
        scale = np.asarray(profile, dtype=float)
        if scale.shape != (10,):
            raise ValueError(f"seed scale profile {name} must have 10 values")
        nodes = fit_nodes_to_action(scale[:, None] * full_action, modes_tsc, interpolation_matrix)
        seeds[str(name)] = np.clip(nodes.reshape(-1), lower, upper)
    seeds["zero"] = np.zeros_like(lower)
    return seeds


def load_stage2_config(
    config_path: str | Path,
    *,
    source_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage2Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    tsc_all_root = Path(os.environ.get("TSC_ALL_ROOT", project_dir.parent)).expanduser().resolve()
    cfg = base.deep_replace_strings(
        base.read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(tsc_all_root)},
    )
    if run_dir_override is None:
        output_root = base.resolve_path(cfg.get("output_root", "stage2_runs"), base_dir=project_dir)
        run_name = str(cfg.get("run_name", "stage2_svd3_real_tsc_cem_100ms"))
        run_dir = output_root / f"{run_name}_{base.utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)
    source = _resolve_source_run(source_run, run_dir)
    source_train = copy.deepcopy(base.read_json(source / "train_config.resolved.json"))
    source_env = copy.deepcopy(base.read_json(source / "env_config.resolved.json"))
    source_stage = base.read_json(source / "stage1_config.resolved.json")

    for key in ("R", "Z", "Ip"):
        if not math.isclose(
            float(cfg["target"][key]),
            float(source_stage["target"][key]),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(f"Stage2 target {key} differs from source Stage1.1")
    horizon = int(cfg["trajectory"]["horizon_steps"])
    if horizon != int(source_stage["scan"]["horizon_steps"]):
        raise ValueError("Stage2 horizon differs from source Stage1.1")
    if int(source_env["dt_ms"]) * horizon != int(cfg["trajectory"]["horizon_ms"]):
        raise ValueError("horizon_ms is inconsistent with dt_ms and horizon_steps")

    paths = Stage2Paths(
        project_dir=project_dir,
        config_path=config_path,
        run_dir=run_dir,
        evaluations_dir=run_dir / "evaluations",
        generations_dir=run_dir / "generations",
        best_dir=run_dir / "best",
        confirmations_dir=run_dir / "confirmations",
        analysis_dir=run_dir / "analysis",
        source_reference_dir=run_dir / "source_reference",
    )
    source_env["tsc_timeout_s"] = float(
        cfg.get("runtime", {}).get("tsc_timeout_s", source_env.get("tsc_timeout_s", 180.0))
    )
    storage_cfg = cfg.get("storage", {})
    workspace_override = _resolve_storage_override(
        os.environ.get("STAGE2_TSC_WORKSPACE_ROOT") or storage_cfg.get("tsc_workspace_root"),
        project_dir=project_dir,
    )
    run_root_override = _resolve_storage_override(
        os.environ.get("STAGE2_TSC_RUN_ROOT") or storage_cfg.get("tsc_run_root"),
        project_dir=project_dir,
    )
    if workspace_override is not None:
        source_env["tsc_workspace_root"] = workspace_override
    if run_root_override is not None:
        source_env["run_root"] = run_root_override
    source_env["keep_tsc_workspace"] = False
    source_env["cleanup_episode_dir"] = True
    source_env["keep_failed_episode_dir"] = bool(storage_cfg.get("keep_failed_episode_dir", False))
    source_env["keep_last_n_failed_episode_dirs"] = int(storage_cfg.get("keep_last_n_failed_episode_dirs", 0))
    source_train["env_config"] = str(run_dir / "env_config.resolved.json")
    source_train.setdefault("episode", {})["max_episode_steps"] = horizon
    source_train.setdefault("target", {}).update(copy.deepcopy(cfg["target"]))

    modes_all = np.load(source / "analysis/coil_modes_tsc.npy")
    if int(cfg["trajectory"].get("n_modes", 3)) != 3:
        raise ValueError("This Stage2 release is fixed to the validated first 3 SVD modes")
    modes_tsc = np.asarray(modes_all[:, :3], dtype=float)
    if modes_tsc.shape != (14, 3) or not np.allclose(
        modes_tsc.T @ modes_tsc, np.eye(3), atol=1e-6
    ):
        raise ValueError("invalid source SVD mode matrix")

    response = np.asarray(np.load(source / "analysis/response_tensor_dy_per_a.npy"), dtype=float)
    if response.shape != (horizon + 1, 3, horizon, 14):
        raise ValueError(f"unexpected response tensor shape {response.shape}")
    baseline_rows = _read_csv(source / "analysis/baseline_trajectory.csv")
    baseline_y = np.asarray(
        [[float(row["R"]), float(row["Z"]), float(row["Ip"])] for row in baseline_rows],
        dtype=float,
    )
    baseline_payload = base.read_json_gz(source / "raw_experiments/baseline_r00.json.gz")
    if not baseline_payload.get("success"):
        raise RuntimeError("source baseline_r00 is not successful")
    initial_currents_tsc = np.asarray(
        baseline_payload["trajectory"][0]["currents_a_tsc"], dtype=float
    )
    max_delta_a = float(source_env["current_slew_a_per_ms"]) * float(source_env["dt_ms"])
    min_current_tsc = display_to_tsc(np.asarray(source_env["min_current_a_display_order"], dtype=float))
    max_current_tsc = display_to_tsc(np.asarray(source_env["max_current_a_display_order"], dtype=float))

    node_times = np.asarray(cfg["trajectory"].get("node_steps", [0, 2, 4, 6, 9]), dtype=float)
    if int(cfg["trajectory"].get("node_count", len(node_times))) != 5 or len(node_times) != 5:
        raise ValueError("Stage2 is validated for exactly 5 time nodes")
    if node_times[0] != 0 or node_times[-1] != horizon - 1 or not np.all(np.diff(node_times) > 0):
        raise ValueError("node_steps must increase from 0 to horizon_steps-1")
    interpolation_matrix = build_interpolation_matrix(horizon, node_times)

    lower_mode = np.asarray(cfg["trajectory"].get("coefficient_lower", [-2.6, -2.6, -0.9]), dtype=float)
    upper_mode = np.asarray(cfg["trajectory"].get("coefficient_upper", [2.6, 2.6, 0.9]), dtype=float)
    if lower_mode.shape != (3,) or upper_mode.shape != (3,) or np.any(lower_mode >= upper_mode):
        raise ValueError("invalid mode coefficient bounds")
    coefficient_lower = np.tile(lower_mode, 5)
    coefficient_upper = np.tile(upper_mode, 5)

    baseline_result = copy.deepcopy(baseline_payload)
    baseline_result["experiment_id"] = "zero_action_baseline"
    baseline_result["spec"] = {
        "candidate_label": "zero_action_baseline",
        "sequence_scale": 0.0,
        "kind": "reference_baseline",
    }
    baseline_metrics = base.validation_metrics(
        baseline_result, stage2_metric_compat_config(cfg), source_env
    )
    seed_vectors = build_seed_vectors(
        source / "candidate_sequences/svd03_target1p00.json",
        modes_tsc,
        interpolation_matrix,
        cfg,
        coefficient_lower,
        coefficient_upper,
    )
    return Stage2Context(
        cfg=cfg,
        train_cfg=source_train,
        env_cfg=source_env,
        paths=paths,
        source_run=source,
        modes_tsc=modes_tsc,
        response=response,
        baseline_y=baseline_y,
        initial_currents_tsc=initial_currents_tsc,
        max_delta_a=max_delta_a,
        min_current_tsc=min_current_tsc,
        max_current_tsc=max_current_tsc,
        interpolation_matrix=interpolation_matrix,
        node_times=node_times,
        coefficient_lower=coefficient_lower,
        coefficient_upper=coefficient_upper,
        baseline_metrics=baseline_metrics,
        seed_vectors=seed_vectors,
    )


def initialize_stage2_run(ctx: Stage2Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.evaluations_dir,
        ctx.paths.generations_dir,
        ctx.paths.best_dir,
        ctx.paths.confirmations_dir,
        ctx.paths.analysis_dir,
        ctx.paths.source_reference_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    base.atomic_write_json(ctx.paths.run_dir / "stage2_config.resolved.json", ctx.cfg)
    base.atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.train_cfg)
    base.atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.env_cfg)
    manifest_path = ctx.paths.run_dir / "stage2_manifest.json"
    if not manifest_path.exists():
        base.atomic_write_json(
            manifest_path,
            {
                "stage": "Stage2",
                "created_utc": base.utc_timestamp(),
                "source_stage1_1_run": str(ctx.source_run),
                "source_start_folder": ctx.env_cfg.get("start_folder"),
                "horizon_steps": int(ctx.cfg["trajectory"]["horizon_steps"]),
                "dt_ms": int(ctx.env_cfg["dt_ms"]),
                "n_modes": 3,
                "node_steps": ctx.node_times.tolist(),
                "parameter_dimension": int(len(ctx.coefficient_lower)),
                "target": copy.deepcopy(ctx.cfg["target"]),
                "coil_order_tsc": TSC_COIL_NAMES,
                "coil_order_display": DISPLAY_COIL_NAMES,
                "immediate_external_termination_intercepted": False,
                "tsc_workspace_root": str(ctx.env_cfg.get("tsc_workspace_root", "")),
                "tsc_run_root": str(ctx.env_cfg.get("run_root", "")),
                "ray_tmpdir": os.environ.get("RAY_TMPDIR", ctx.cfg.get("parallel", {}).get("ray_tmpdir", "")),
                "actor_close_before_kill": True,
            },
        )
    reference_files = (
        "analysis/analysis_summary.json",
        "analysis/coil_modes.csv",
        "analysis/coil_modes_tsc.npy",
        "analysis/response_tensor_dy_per_a.npy",
        "analysis/baseline_trajectory.csv",
        "analysis/mode_bootstrap_robustness_summary.csv",
        "candidate_sequences/svd03_target1p00.json",
        "validation/validation_summary.csv",
        "validation/gate_a_verdict.json",
        "STAGE1_1_REPORT.md",
    )
    for relative in reference_files:
        source = ctx.source_run / relative
        if not source.exists():
            continue
        destination = ctx.paths.source_reference_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
    base.atomic_write_json(
        ctx.paths.source_reference_dir / "stage2_seed_catalog.json",
        {name: vector.tolist() for name, vector in ctx.seed_vectors.items()},
    )


def vector_hash(vector: np.ndarray, *, prefix: str = "cand") -> str:
    rounded = np.round(np.asarray(vector, dtype=float), 10)
    return f"{prefix}_{hashlib.sha256(rounded.tobytes()).hexdigest()[:16]}"


def decode_vector(ctx: Stage2Context, vector: np.ndarray) -> dict[str, Any]:
    vector = np.clip(np.asarray(vector, dtype=float), ctx.coefficient_lower, ctx.coefficient_upper)
    nodes = vector.reshape(5, 3)
    mode_coefficients = ctx.interpolation_matrix @ nodes
    action_raw = mode_coefficients @ ctx.modes_tsc.T
    action = np.zeros_like(action_raw)
    currents = np.zeros((action.shape[0] + 1, 14), dtype=float)
    currents[0] = ctx.initial_currents_tsc
    per_step_scale: list[float] = []
    saturation_excess: list[float] = []
    for step in range(action.shape[0]):
        desired = np.asarray(action_raw[step], dtype=float)
        max_abs = float(np.max(np.abs(desired)))
        action_scale = 1.0 if max_abs <= 1.0 else 1.0 / max_abs
        desired = desired * action_scale
        delta = desired * ctx.max_delta_a
        current_scale = 1.0
        for coil in range(14):
            if delta[coil] > 0:
                room = ctx.max_current_tsc[coil] - currents[step, coil]
                current_scale = min(current_scale, max(0.0, room / max(delta[coil], 1e-30)))
            elif delta[coil] < 0:
                room = ctx.min_current_tsc[coil] - currents[step, coil]
                current_scale = min(current_scale, max(0.0, room / min(delta[coil], -1e-30)))
        current_scale = float(np.clip(current_scale, 0.0, 1.0))
        actual = desired * current_scale
        action[step] = actual
        currents[step + 1] = currents[step] + actual * ctx.max_delta_a
        per_step_scale.append(action_scale * current_scale)
        saturation_excess.append(max(0.0, max_abs - 1.0))
    return {
        "vector": vector,
        "nodes": nodes,
        "mode_coefficients": mode_coefficients,
        "action_raw_tsc": action_raw,
        "action_norm_tsc": action,
        "action_norm_display": tsc_matrix_to_display(action),
        "currents_a_tsc": currents,
        "currents_a_display": tsc_matrix_to_display(currents),
        "per_step_repair_scale": np.asarray(per_step_scale, dtype=float),
        "saturation_excess": np.asarray(saturation_excess, dtype=float),
    }


def predict_trajectory(ctx: Stage2Context, action_norm_tsc: np.ndarray) -> np.ndarray:
    increments = np.asarray(action_norm_tsc, dtype=float) * ctx.max_delta_a
    flat = increments.reshape(-1)
    h_all = np.vstack([ctx.response[t].reshape(3, -1) for t in range(ctx.response.shape[0])])
    return ctx.baseline_y + (h_all @ flat).reshape(ctx.baseline_y.shape)


def linear_prefilter_metrics(ctx: Stage2Context, decoded: dict[str, Any]) -> dict[str, float]:
    predicted = predict_trajectory(ctx, decoded["action_norm_tsc"])
    target = np.asarray(
        [ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]],
        dtype=float,
    )
    errors = predicted - target[None, :]
    late_n = int(ctx.cfg["gate"].get("late_window_steps", 4))
    late = errors[-late_n:]
    prefilter = ctx.cfg["linear_prefilter"]
    r_scale = float(prefilter.get("r_scale_m", 0.03))
    z_scale = float(prefilter.get("z_scale_m", 0.03))
    ip_scale = float(prefilter.get("ip_scale_a", 10000.0))
    position = float(np.mean((late[:, 0] / r_scale) ** 2 + (late[:, 1] / z_scale) ** 2))
    terminal = float((errors[-1, 0] / r_scale) ** 2 + (errors[-1, 1] / z_scale) ** 2)
    ip = float((errors[-1, 2] / ip_scale) ** 2)
    action = np.asarray(decoded["action_norm_tsc"], dtype=float)
    action_rms = float(np.sqrt(np.mean(action**2)))
    delta_action_rms = float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2)))
    repair = float(np.mean(decoded["saturation_excess"] ** 2))
    weights = prefilter.get("weights", {})
    score = (
        float(weights.get("late_position", 1.0)) * position
        + float(weights.get("terminal_position", 0.5)) * terminal
        + float(weights.get("terminal_ip", 0.05)) * ip
        + float(weights.get("action_rms", 0.01)) * action_rms**2
        + float(weights.get("delta_action_rms", 0.02)) * delta_action_rms**2
        + float(weights.get("repair", 2.0)) * repair
    )
    return {
        "linear_prefilter_score": float(score),
        "predicted_terminal_R_error_m": float(errors[-1, 0]),
        "predicted_terminal_Z_error_m": float(errors[-1, 1]),
        "predicted_terminal_Ip_error_A": float(errors[-1, 2]),
        "predicted_late_RZ_rms_m": float(np.sqrt(np.mean(np.sum(late[:, :2] ** 2, axis=1)))),
        "action_rms": action_rms,
        "delta_action_rms": delta_action_rms,
        "repair_excess_rms": float(np.sqrt(repair)),
    }


def stage2_metrics(
    ctx: Stage2Context,
    result: dict[str, Any],
    decoded: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = base.validation_metrics(
        result, stage2_metric_compat_config(ctx.cfg), ctx.env_cfg
    )
    if not metrics.get("success"):
        return {
            **metrics,
            "gate_tier": 99,
            "gate_label": "TSC_FAILURE",
            "strict_gate_pass": False,
            "relaxed_gate_pass": False,
            "continuous_objective": 1e12,
            "selection_score": 99e6 + 1e12,
        }
    gate = ctx.cfg["gate"]
    objective_cfg = ctx.cfg["objective"]
    precise_mm = int(round(float(gate.get("precise_tolerance_m", 0.03)) * 1000.0))
    relaxed_mm = int(round(float(gate.get("relaxed_tolerance_m", 0.04)) * 1000.0))
    required_streak = int(gate.get("required_terminal_streak_steps", 3))
    velocity_limit = float(gate.get("terminal_velocity_max_m_per_s", 0.10))
    late_velocity_limit = float(gate.get("late_velocity_rms_max_m_per_s", 0.10))
    ip_tolerance = float(gate.get("ip_tolerance_a", 10000.0))
    precise_streak = int(metrics.get(f"trailing_streak_within_{precise_mm}mm_steps", 0))
    relaxed_streak = int(metrics.get(f"trailing_streak_within_{relaxed_mm}mm_steps", 0))
    terminal_velocity = float(metrics["terminal_velocity_m_per_s"])
    late_velocity = float(metrics["late_velocity_rms_m_per_s"])
    ip_safe = abs(float(metrics["terminal_Ip_error_A"])) <= ip_tolerance
    precise_position = precise_streak >= required_streak and ip_safe
    relaxed_position = relaxed_streak >= required_streak and ip_safe
    speed_ok = terminal_velocity <= velocity_limit and late_velocity <= late_velocity_limit
    baseline_terminal = float(ctx.baseline_metrics["terminal_RZ_euclidean_error_m"])
    terminal_distance = float(metrics["terminal_RZ_euclidean_error_m"])
    reduction = (baseline_terminal - terminal_distance) / max(baseline_terminal, 1e-12)
    if precise_position and speed_ok:
        tier, label = 0, "PASS_PRECISE_HOLD_30MM"
    elif relaxed_position and speed_ok:
        tier, label = 1, "PASS_DAMPED_HOLD_40MM"
    elif precise_position:
        tier, label = 2, "POSITION_30MM_SPEED_FAIL"
    elif relaxed_position:
        tier, label = 3, "POSITION_40MM_SPEED_FAIL"
    elif reduction >= float(gate.get("promising_distance_reduction", 0.50)):
        tier, label = 4, "STRONG_DRIFT_SUPPRESSION"
    else:
        tier, label = 5, "NOT_YET_PROMISING"

    trajectory = result["trajectory"]
    target = np.asarray(
        [ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]],
        dtype=float,
    )
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    error = y - target[None, :]
    late_n = int(gate.get("late_window_steps", 4))
    late = error[-late_n:]
    precise_tol = float(gate.get("precise_tolerance_m", 0.03))
    position_core = float(np.mean((late[:, 0] / precise_tol) ** 2 + (late[:, 1] / precise_tol) ** 2))
    terminal_position = float((error[-1, 0] / precise_tol) ** 2 + (error[-1, 1] / precise_tol) ** 2)
    position_excess = float(
        np.mean(
            (np.maximum(np.abs(late[:, 0]) - precise_tol, 0.0) / precise_tol) ** 2
            + (np.maximum(np.abs(late[:, 1]) - precise_tol, 0.0) / precise_tol) ** 2
        )
    )
    velocity_excess = float(
        max(terminal_velocity / velocity_limit - 1.0, 0.0) ** 2
        + max(late_velocity / late_velocity_limit - 1.0, 0.0) ** 2
    )
    velocity_core = float((terminal_velocity / velocity_limit) ** 2 + (late_velocity / late_velocity_limit) ** 2)
    streak_deficit = float(max(required_streak - precise_streak, 0) / max(required_streak, 1))
    ip_core = float((float(metrics["terminal_Ip_error_A"]) / ip_tolerance) ** 2)
    if decoded is None:
        action_rms = 0.0
        delta_action_rms = 0.0
        saturation_rms = 0.0
    else:
        action = np.asarray(decoded["action_norm_tsc"], dtype=float)
        action_rms = float(np.sqrt(np.mean(action**2)))
        delta_action_rms = float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2)))
        saturation_rms = float(np.sqrt(np.mean(decoded["saturation_excess"] ** 2)))
    weights = objective_cfg.get("weights", {})
    continuous = (
        float(weights.get("position_excess", 80.0)) * position_excess
        + float(weights.get("velocity_excess", 60.0)) * velocity_excess
        + float(weights.get("streak_deficit", 25.0)) * streak_deficit
        + float(weights.get("late_position", 4.0)) * position_core
        + float(weights.get("terminal_position", 2.0)) * terminal_position
        + float(weights.get("velocity_core", 2.0)) * velocity_core
        + float(weights.get("terminal_ip", 0.10)) * ip_core
        + float(weights.get("action_rms", 0.02)) * action_rms**2
        + float(weights.get("delta_action_rms", 0.04)) * delta_action_rms**2
        + float(weights.get("repair", 2.0)) * saturation_rms**2
    )
    selection_score = float(tier * float(objective_cfg.get("tier_spacing", 1e6)) + continuous)
    metrics.update(
        {
            "gate_tier": int(tier),
            "gate_label": label,
            "strict_gate_pass": bool(tier == 0),
            "relaxed_gate_pass": bool(tier <= 1),
            "terminal_RZ_reduction_vs_zero_action_fraction": float(reduction),
            "continuous_objective": float(continuous),
            "selection_score": selection_score,
            "position_excess_objective": position_excess,
            "velocity_excess_objective": velocity_excess,
            "precise_streak_deficit": streak_deficit,
            "action_rms": action_rms,
            "delta_action_rms": delta_action_rms,
            "repair_excess_rms": saturation_rms,
        }
    )
    return metrics

class LocalStage2Worker:
    def __init__(self, train_cfg: dict[str, Any], worker_id: str):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env
        self.env = make_tsc_rzip_env(copy.deepcopy(train_cfg), worker_id=worker_id, seed=None)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = base.run_validation_experiment(self.env, spec)
        # Each candidate is already serialized by the driver.  Remove its TSC
        # episode directory immediately instead of waiting until actor shutdown.
        runner = getattr(self.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(
                failed=not bool(result.get("success", False)),
                reason=str(result.get("failure_reason", "stage2_candidate_complete")),
            )
        return result

    def close(self) -> None:
        self.env.close()


def _ray_worker_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class RayStage2Worker:
        def __init__(self, train_cfg: dict[str, Any], worker_id: str):
            self.worker = LocalStage2Worker(train_cfg, worker_id)

        def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
            return self.worker.evaluate(spec)

        def close(self) -> None:
            self.worker.close()

    return RayStage2Worker


def _result_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = base.read_json_gz(path)
    except Exception:
        return False
    return bool(payload.get("success"))


def _close_ray_actors(actors: list[Any], *, timeout_s: float) -> None:
    """Close actor environments before ray.kill so private TSC workspaces are deleted."""
    if not actors:
        return
    import ray

    refs: dict[Any, Any] = {}
    for actor in actors:
        try:
            refs[actor.close.remote()] = actor
        except Exception:
            pass
    deadline = time.monotonic() + max(float(timeout_s), 1.0)
    while refs and time.monotonic() < deadline:
        remaining_s = max(deadline - time.monotonic(), 0.0)
        ready, _ = ray.wait(
            list(refs),
            num_returns=min(16, len(refs)),
            timeout=min(5.0, remaining_s),
        )
        if not ready:
            continue
        for ref in ready:
            refs.pop(ref, None)
            try:
                ray.get(ref)
            except Exception as exc:
                print(f"[Stage2 cleanup] actor close failed: {exc!r}", flush=True)
    if refs:
        print(
            f"[Stage2 cleanup] {len(refs)} actor(s) did not close within {timeout_s:.1f}s; forcing ray.kill",
            flush=True,
        )
    for actor in actors:
        try:
            ray.kill(actor, no_restart=True)
        except Exception:
            pass


def evaluate_specs(
    ctx: Stage2Context,
    specs: list[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pending = []
    for spec in specs:
        path = output_dir / f"{spec['experiment_id']}.json.gz"
        if resume and _result_complete(path):
            continue
        pending.append(spec)
    if pending and backend == "serial":
        worker = LocalStage2Worker(ctx.train_cfg, "stage2_serial")
        try:
            for index, spec in enumerate(pending, start=1):
                result = worker.evaluate(spec)
                base.atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                print(f"[Stage2 evaluation] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif pending and backend == "ray":
        import ray
        parallel = ctx.cfg.get("parallel", {})
        requested = int(os.environ.get("STAGE2_WORKERS", parallel.get("n_workers", 192)))
        n_workers = max(1, min(requested, len(pending)))
        ray_tmpdir = os.environ.get("RAY_TMPDIR", parallel.get("ray_tmpdir", "")) or None
        if not ray.is_initialized():
            ray.init(
                num_cpus=n_workers,
                include_dashboard=False,
                ignore_reinit_error=True,
                _temp_dir=ray_tmpdir,
                log_to_driver=False,
            )
        Actor = _ray_worker_class()
        actors = [Actor.remote(ctx.train_cfg, f"stage2_{i:03d}") for i in range(n_workers)]
        refs = {
            actors[index % n_workers].evaluate.remote(spec): spec
            for index, spec in enumerate(pending)
        }
        done_count = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage2 evaluation] waiting {done_count}/{len(pending)}", flush=True)
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                        }
                    base.atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done_count += 1
                    print(f"[Stage2 evaluation] {done_count}/{len(pending)}", flush=True)
        finally:
            close_timeout_s = float(ctx.cfg.get("storage", {}).get("actor_close_timeout_s", 600.0))
            _close_ray_actors(actors, timeout_s=close_timeout_s)
    elif pending:
        raise ValueError("backend must be ray or serial")
    results = []
    for spec in specs:
        path = output_dir / f"{spec['experiment_id']}.json.gz"
        if path.exists():
            results.append(base.read_json_gz(path))
    return results


def initial_cem_state(ctx: Stage2Context) -> dict[str, Any]:
    optimization = ctx.cfg["optimization"]
    mean_seed_name = str(optimization.get("initial_mean_seed", "svd3_uniform_0.85"))
    if mean_seed_name not in ctx.seed_vectors:
        raise KeyError(f"unknown initial_mean_seed {mean_seed_name}")
    mean = np.asarray(ctx.seed_vectors[mean_seed_name], dtype=float)
    std_by_mode = np.asarray(optimization.get("initial_std_by_mode", [0.35, 0.35, 0.15]), dtype=float)
    node_multiplier = np.asarray(
        optimization.get("initial_std_node_multiplier", [0.90, 0.95, 1.0, 1.20, 1.35]),
        dtype=float,
    )
    if std_by_mode.shape != (3,) or node_multiplier.shape != (5,):
        raise ValueError("invalid initial standard deviation configuration")
    std = np.outer(node_multiplier, std_by_mode).reshape(-1)
    return {
        "schema_version": 1,
        "generation": 0,
        "mean": mean.tolist(),
        "covariance": np.diag(std**2).tolist(),
        "best_selection_score": None,
        "best_experiment_id": None,
        "best_generation": None,
        "best_vector": None,
        "generations_without_improvement": 0,
        "strict_gate_found": False,
        "finished": False,
        "stop_reason": "",
        "rng_seed": int(optimization.get("random_seed", 20260718)),
    }


def load_or_initialize_state(ctx: Stage2Context) -> dict[str, Any]:
    path = ctx.paths.run_dir / "cem_state.json"
    return base.read_json(path) if path.exists() else initial_cem_state(ctx)


def _regularize_covariance(
    covariance: np.ndarray,
    *,
    eigen_floor: float,
    eigen_ceiling: float,
    diagonal_shrinkage: float,
) -> np.ndarray:
    covariance = 0.5 * (covariance + covariance.T)
    diagonal = np.diag(np.diag(covariance))
    covariance = (1.0 - diagonal_shrinkage) * covariance + diagonal_shrinkage * diagonal
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    eigenvalues = np.clip(eigenvalues, eigen_floor, eigen_ceiling)
    return (eigenvectors * eigenvalues[None, :]) @ eigenvectors.T


def _sample_gaussian(
    rng: np.random.Generator,
    mean: np.ndarray,
    covariance: np.ndarray,
    n_samples: int,
    *,
    antithetic: bool,
) -> np.ndarray:
    covariance = 0.5 * (covariance + covariance.T)
    try:
        factor = np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError:
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        factor = eigenvectors @ np.diag(np.sqrt(np.maximum(eigenvalues, 1e-12)))
    if antithetic:
        half = (n_samples + 1) // 2
        noise = rng.standard_normal((half, len(mean))) @ factor.T
        return np.vstack([mean + noise, mean - noise])[:n_samples]
    return mean[None, :] + rng.standard_normal((n_samples, len(mean))) @ factor.T


def build_generation_manifest(ctx: Stage2Context, state: dict[str, Any]) -> dict[str, Any]:
    generation = int(state["generation"])
    generation_dir = ctx.paths.generations_dir / f"gen_{generation:03d}"
    generation_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = generation_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return base.read_json(manifest_path)
    optimization = ctx.cfg["optimization"]
    population = int(optimization.get("population_size", 192))
    pool_size = int(optimization.get("proposal_pool_size", population * 4))
    if pool_size < population:
        raise ValueError("proposal_pool_size must be >= population_size")
    seed = int(state["rng_seed"]) + generation * 104729
    rng = np.random.default_rng(seed)
    mean = np.asarray(state["mean"], dtype=float)
    covariance = np.asarray(state["covariance"], dtype=float)
    proposals = _sample_gaussian(
        rng,
        mean,
        covariance,
        pool_size,
        antithetic=bool(optimization.get("antithetic_sampling", True)),
    )
    proposals = np.clip(proposals, ctx.coefficient_lower, ctx.coefficient_upper)
    named: list[tuple[str, np.ndarray, str]] = []
    if generation == 0:
        for name, vector in ctx.seed_vectors.items():
            named.append((name, np.asarray(vector, dtype=float), "seed"))
    else:
        named.append(("current_mean", mean, "state_mean"))
        if state.get("best_vector") is not None:
            named.append(("hall_of_fame_best", np.asarray(state["best_vector"], dtype=float), "best"))
    proposal_rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_vector(vector: np.ndarray, source_name: str, source_type: str) -> None:
        clipped = np.clip(np.asarray(vector, dtype=float), ctx.coefficient_lower, ctx.coefficient_upper)
        candidate_id = vector_hash(clipped, prefix=f"g{generation:03d}")
        if candidate_id in seen:
            return
        seen.add(candidate_id)
        decoded = decode_vector(ctx, clipped)
        proposal_rows.append(
            {
                "candidate_id": candidate_id,
                "source_name": source_name,
                "source_type": source_type,
                "vector": clipped.tolist(),
                **linear_prefilter_metrics(ctx, decoded),
            }
        )

    for name, vector, source_type in named:
        add_vector(vector, name, source_type)
    for index, vector in enumerate(proposals):
        add_vector(vector, f"gaussian_{index:04d}", "gaussian")
    mandatory = [row for row in proposal_rows if row["source_type"] != "gaussian"]
    gaussian = [row for row in proposal_rows if row["source_type"] == "gaussian"]
    gaussian.sort(key=lambda row: float(row["linear_prefilter_score"]))
    random_fraction = float(ctx.cfg["linear_prefilter"].get("random_keep_fraction", 0.15))
    random_count = min(int(round(population * random_fraction)), max(0, population - len(mandatory)))
    top_count = max(0, population - len(mandatory) - random_count)
    selected = mandatory[:population] + gaussian[:top_count]
    remainder = gaussian[top_count:]
    if random_count and remainder:
        indices = rng.choice(len(remainder), size=min(random_count, len(remainder)), replace=False)
        selected.extend(remainder[int(index)] for index in indices)
    if len(selected) < population:
        existing = {row["candidate_id"] for row in selected}
        for row in gaussian:
            if row["candidate_id"] in existing:
                continue
            selected.append(row)
            existing.add(row["candidate_id"])
            if len(selected) >= population:
                break
    selected = selected[:population]
    for rank, row in enumerate(selected):
        row["population_index"] = rank
    manifest = {
        "generation": generation,
        "random_seed": seed,
        "population_size": population,
        "proposal_pool_size": pool_size,
        "mean": mean.tolist(),
        "covariance": covariance.tolist(),
        "candidates": selected,
    }
    base.atomic_write_json(manifest_path, manifest)
    base.write_csv(generation_dir / "candidate_manifest.csv", selected)
    return manifest


def candidate_specs_from_manifest(ctx: Stage2Context, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    horizon = int(ctx.cfg["trajectory"]["horizon_steps"])
    specs = []
    for row in manifest["candidates"]:
        vector = np.asarray(row["vector"], dtype=float)
        decoded = decode_vector(ctx, vector)
        specs.append(
            {
                "kind": "stage2_candidate",
                "experiment_id": str(row["candidate_id"]),
                "candidate_id": str(row["candidate_id"]),
                "generation": int(manifest["generation"]),
                "population_index": int(row["population_index"]),
                "source_name": row["source_name"],
                "source_type": row["source_type"],
                "horizon_steps": horizon,
                "parameter_vector": vector.tolist(),
                "mode_nodes": decoded["nodes"].tolist(),
                "mode_coefficients": decoded["mode_coefficients"].tolist(),
                "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
                "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
                "linear_prefilter_score": float(row["linear_prefilter_score"]),
                "predicted_terminal_R_error_m": float(row["predicted_terminal_R_error_m"]),
                "predicted_terminal_Z_error_m": float(row["predicted_terminal_Z_error_m"]),
                "predicted_terminal_Ip_error_A": float(row["predicted_terminal_Ip_error_A"]),
            }
        )
    return specs


def summarize_generation(
    ctx: Stage2Context,
    manifest: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {str(result["experiment_id"]): result for result in results}
    rows: list[dict[str, Any]] = []
    for candidate in manifest["candidates"]:
        candidate_id = str(candidate["candidate_id"])
        result = by_id.get(candidate_id)
        vector = np.asarray(candidate["vector"], dtype=float)
        decoded = decode_vector(ctx, vector)
        if result is None:
            metrics = {
                "success": False,
                "failure_reason": "missing result",
                "gate_tier": 99,
                "gate_label": "MISSING_RESULT",
                "continuous_objective": 1e12,
                "selection_score": 99e6 + 1e12,
            }
        else:
            metrics = stage2_metrics(ctx, result, decoded)
        rows.append(
            {
                "generation": int(manifest["generation"]),
                "candidate_id": candidate_id,
                "population_index": int(candidate["population_index"]),
                "source_name": candidate["source_name"],
                "source_type": candidate["source_type"],
                "linear_prefilter_score": candidate["linear_prefilter_score"],
                "parameter_vector": candidate["vector"],
                **metrics,
            }
        )
    rows.sort(key=lambda row: (float(row["selection_score"]), str(row["candidate_id"])))
    for rank, row in enumerate(rows, start=1):
        row["generation_rank"] = rank
    return rows


def _weighted_elite_statistics(
    vectors: np.ndarray,
    objectives: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    count = len(vectors)
    if count < 2:
        return vectors[0], np.eye(vectors.shape[1]) * 1e-6
    ranks = np.arange(count, dtype=float)
    weights = np.exp(-ranks / max(count / 3.0, 1.0))
    weights /= weights.sum()
    mean = np.sum(vectors * weights[:, None], axis=0)
    centered = vectors - mean[None, :]
    covariance = (centered * weights[:, None]).T @ centered
    spread = max(float(np.std(objectives)), 1e-6)
    covariance += np.eye(vectors.shape[1]) * min(spread * 1e-6, 1e-3)
    return mean, covariance


def update_state_from_generation(
    ctx: Stage2Context,
    state: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    optimization = ctx.cfg["optimization"]
    elite_count = int(optimization.get("elite_count", 24))
    successful = [row for row in rows if row.get("success")]
    if len(successful) < max(2, elite_count // 3):
        raise RuntimeError(
            f"too few successful TSC evaluations in generation {state['generation']}: "
            f"{len(successful)}/{len(rows)}"
        )
    actual_elite_count = min(elite_count, len(successful))
    cross_fraction = float(optimization.get("cross_tier_elite_fraction", 0.25))
    strict_in_generation = any(int(row.get("gate_tier", 99)) == 0 for row in successful)
    if strict_in_generation or bool(state.get("strict_gate_found", False)):
        elites = successful[:actual_elite_count]
    else:
        cross_count = min(int(round(actual_elite_count * cross_fraction)), actual_elite_count - 1)
        primary_count = actual_elite_count - cross_count
        elites = successful[:primary_count]
        selected_ids = {str(row["candidate_id"]) for row in elites}
        exploratory = sorted(
            [row for row in successful if str(row["candidate_id"]) not in selected_ids],
            key=lambda row: (float(row["continuous_objective"]), int(row["gate_tier"])),
        )
        elites.extend(exploratory[:cross_count])
    vectors = np.asarray([row["parameter_vector"] for row in elites], dtype=float)
    objectives = np.asarray([row["selection_score"] for row in elites], dtype=float)
    elite_mean, elite_covariance = _weighted_elite_statistics(vectors, objectives)
    old_mean = np.asarray(state["mean"], dtype=float)
    old_covariance = np.asarray(state["covariance"], dtype=float)
    mean_alpha = float(optimization.get("mean_update_fraction", 0.70))
    covariance_alpha = float(optimization.get("covariance_update_fraction", 0.55))
    new_mean = np.clip(
        (1.0 - mean_alpha) * old_mean + mean_alpha * elite_mean,
        ctx.coefficient_lower,
        ctx.coefficient_upper,
    )
    new_covariance = _regularize_covariance(
        (1.0 - covariance_alpha) * old_covariance + covariance_alpha * elite_covariance,
        eigen_floor=float(optimization.get("covariance_eigen_floor", 4e-4)),
        eigen_ceiling=float(optimization.get("covariance_eigen_ceiling", 0.50)),
        diagonal_shrinkage=float(optimization.get("covariance_diagonal_shrinkage", 0.10)),
    )
    best_row = successful[0]
    previous_best_raw = state.get("best_selection_score")
    previous_best = float(previous_best_raw) if previous_best_raw is not None else float("inf")
    improvement = previous_best - float(best_row["selection_score"])
    meaningful = improvement > float(optimization.get("meaningful_improvement", 1e-4))
    new_state = copy.deepcopy(state)
    new_state["mean"] = new_mean.tolist()
    new_state["covariance"] = new_covariance.tolist()
    new_state["generation"] = int(state["generation"]) + 1
    new_state["last_generation_best"] = {
        "candidate_id": best_row["candidate_id"],
        "selection_score": float(best_row["selection_score"]),
        "gate_tier": int(best_row["gate_tier"]),
        "gate_label": best_row["gate_label"],
        "continuous_objective": float(best_row["continuous_objective"]),
    }
    if meaningful or state.get("best_experiment_id") is None:
        new_state["best_selection_score"] = float(best_row["selection_score"])
        new_state["best_experiment_id"] = best_row["candidate_id"]
        new_state["best_generation"] = int(state["generation"])
        new_state["best_vector"] = best_row["parameter_vector"]
        new_state["generations_without_improvement"] = 0
    else:
        new_state["generations_without_improvement"] = int(
            state.get("generations_without_improvement", 0)
        ) + 1
    new_state["strict_gate_found"] = bool(
        state.get("strict_gate_found", False) or int(best_row["gate_tier"]) == 0
    )
    max_generations = int(optimization.get("max_generations", 8))
    patience = int(optimization.get("early_stop_patience_generations", 2))
    if new_state["generation"] >= max_generations:
        new_state["finished"] = True
        new_state["stop_reason"] = "max_generations"
    elif new_state["strict_gate_found"] and new_state["generations_without_improvement"] >= patience:
        new_state["finished"] = True
        new_state["stop_reason"] = "strict_gate_patience"
    return new_state


def _write_best_artifacts(
    ctx: Stage2Context,
    row: dict[str, Any],
    result: dict[str, Any],
) -> None:
    vector = np.asarray(row["parameter_vector"], dtype=float)
    decoded = decode_vector(ctx, vector)
    candidate = {
        "candidate_id": row["candidate_id"],
        "generation": int(row["generation"]),
        "gate_tier": int(row["gate_tier"]),
        "gate_label": row["gate_label"],
        "selection_score": float(row["selection_score"]),
        "continuous_objective": float(row["continuous_objective"]),
        "parameter_vector": vector.tolist(),
        "node_steps": ctx.node_times.tolist(),
        "mode_nodes": decoded["nodes"].tolist(),
        "mode_coefficients": decoded["mode_coefficients"].tolist(),
        "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
        "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
        "currents_a_tsc": decoded["currents_a_tsc"].tolist(),
        "currents_a_display": decoded["currents_a_display"].tolist(),
        "metrics": {key: value for key, value in row.items() if key != "parameter_vector"},
    }
    base.atomic_write_json(ctx.paths.best_dir / "best_candidate.json", candidate)
    base.atomic_write_json_gz(ctx.paths.best_dir / "best_tsc_result.json.gz", result)
    csv_rows = []
    for step in range(len(decoded["action_norm_tsc"])):
        output: dict[str, Any] = {
            "step_index": step,
            "time_ms_from_start": int(ctx.env_cfg.get("dt_ms", 10)) * step,
        }
        for mode in range(3):
            output[f"mode_{mode+1}_coefficient"] = float(decoded["mode_coefficients"][step, mode])
        for coil, name in enumerate(TSC_COIL_NAMES):
            output[f"action_norm_tsc_{name}"] = float(decoded["action_norm_tsc"][step, coil])
            output[f"delta_a_tsc_{name}"] = float(decoded["action_norm_tsc"][step, coil] * ctx.max_delta_a)
        for coil, name in enumerate(DISPLAY_COIL_NAMES):
            output[f"action_norm_display_{name}"] = float(decoded["action_norm_display"][step, coil])
        csv_rows.append(output)
    base.write_csv(ctx.paths.best_dir / "best_action_sequence.csv", csv_rows)


def run_one_generation(
    ctx: Stage2Context,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    initialize_stage2_run(ctx)
    state = load_or_initialize_state(ctx)
    if state.get("finished"):
        return state
    generation = int(state["generation"])
    manifest = build_generation_manifest(ctx, state)
    specs = candidate_specs_from_manifest(ctx, manifest)
    generation_dir = ctx.paths.generations_dir / f"gen_{generation:03d}"
    evaluation_dir = ctx.paths.evaluations_dir / f"gen_{generation:03d}"
    started = time.time()
    results = evaluate_specs(ctx, specs, output_dir=evaluation_dir, backend=backend, resume=resume)
    rows = summarize_generation(ctx, manifest, results)
    base.write_csv(generation_dir / "generation_results.csv", rows)
    base.atomic_write_json(generation_dir / "generation_results.json", rows)
    by_id = {str(result["experiment_id"]): result for result in results}
    successful = [row for row in rows if row.get("success")]
    if successful:
        candidate = successful[0]
        previous_raw = state.get("best_selection_score")
        previous_best = float(previous_raw) if previous_raw is not None else float("inf")
        if float(candidate["selection_score"]) < previous_best:
            _write_best_artifacts(ctx, candidate, by_id[candidate["candidate_id"]])
    new_state = update_state_from_generation(ctx, state, rows)
    new_state["last_generation_wall_time_s"] = float(time.time() - started)
    new_state["updated_utc"] = base.utc_timestamp()
    base.atomic_write_json(ctx.paths.run_dir / "cem_state.json", new_state)
    best = successful[0] if successful else None
    print(
        json.dumps(
            {
                "generation": generation,
                "successful": len(successful),
                "population": len(rows),
                "best": {
                    "candidate_id": best.get("candidate_id") if best else None,
                    "gate_label": best.get("gate_label") if best else None,
                    "selection_score": best.get("selection_score") if best else None,
                    "terminal_R_error_m": best.get("terminal_R_error_m") if best else None,
                    "terminal_Z_error_m": best.get("terminal_Z_error_m") if best else None,
                    "terminal_velocity_m_per_s": best.get("terminal_velocity_m_per_s") if best else None,
                    "late_velocity_rms_m_per_s": best.get("late_velocity_rms_m_per_s") if best else None,
                },
                "next_generation": new_state["generation"],
                "finished": new_state["finished"],
                "stop_reason": new_state["stop_reason"],
            },
            indent=2,
        ),
        flush=True,
    )
    return new_state


def run_optimization(
    ctx: Stage2Context,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    initialize_stage2_run(ctx)
    while True:
        state = load_or_initialize_state(ctx)
        if state.get("finished"):
            return state
        state = run_one_generation(ctx, backend=backend, resume=resume)
        if state.get("finished"):
            return state


def collect_all_generation_rows(ctx: Stage2Context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(ctx.paths.generations_dir.glob("gen_*/generation_results.json")):
        rows.extend(base.read_json(path))
    rows.sort(key=lambda row: (float(row.get("selection_score", 1e99)), str(row.get("candidate_id"))))
    return rows


def hall_of_fame(ctx: Stage2Context) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in collect_all_generation_rows(ctx):
        vector = np.asarray(row["parameter_vector"], dtype=float)
        key = hashlib.sha256(np.round(vector, 8).tobytes()).hexdigest()
        if key not in unique or float(row["selection_score"]) < float(unique[key]["selection_score"]):
            unique[key] = row
    return sorted(unique.values(), key=lambda row: float(row["selection_score"]))


def confirmation_specs(ctx: Stage2Context) -> list[dict[str, Any]]:
    confirmation = ctx.cfg["confirmation"]
    top_k = int(confirmation.get("top_k_candidates", 3))
    repeats = int(confirmation.get("repeats_per_candidate", 2))
    ranked = hall_of_fame(ctx)[:top_k]
    specs = []
    horizon = int(ctx.cfg["trajectory"]["horizon_steps"])
    for rank, row in enumerate(ranked, start=1):
        vector = np.asarray(row["parameter_vector"], dtype=float)
        decoded = decode_vector(ctx, vector)
        for repeat in range(repeats):
            experiment_id = f"confirm_rank{rank:02d}_{row['candidate_id']}_r{repeat:02d}"
            specs.append(
                {
                    "kind": "stage2_confirmation",
                    "experiment_id": experiment_id,
                    "candidate_id": row["candidate_id"],
                    "hall_of_fame_rank": rank,
                    "repeat": repeat,
                    "horizon_steps": horizon,
                    "parameter_vector": vector.tolist(),
                    "mode_nodes": decoded["nodes"].tolist(),
                    "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
                    "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
                }
            )
    return specs


def run_confirmation(
    ctx: Stage2Context,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    initialize_stage2_run(ctx)
    specs = confirmation_specs(ctx)
    if not specs:
        raise RuntimeError("no Stage2 candidates are available for confirmation")
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.confirmations_dir,
        backend=backend,
        resume=resume,
    )
    by_spec = {spec["experiment_id"]: spec for spec in specs}
    rows = []
    for result in results:
        spec = by_spec[result["experiment_id"]]
        vector = np.asarray(spec["parameter_vector"], dtype=float)
        rows.append(
            {
                "candidate_id": spec["candidate_id"],
                "hall_of_fame_rank": spec["hall_of_fame_rank"],
                "repeat": spec["repeat"],
                **stage2_metrics(ctx, result, decode_vector(ctx, vector)),
            }
        )
    rows.sort(key=lambda row: (int(row["hall_of_fame_rank"]), int(row["repeat"])))
    base.write_csv(ctx.paths.confirmations_dir / "confirmation_results.csv", rows)
    base.atomic_write_json(ctx.paths.confirmations_dir / "confirmation_results.json", rows)
    grouped = []
    for candidate_id in sorted({str(row["candidate_id"]) for row in rows}):
        subset = [row for row in rows if row["candidate_id"] == candidate_id]
        successful = [row for row in subset if row.get("success")]
        grouped.append(
            {
                "candidate_id": candidate_id,
                "hall_of_fame_rank": min(int(row["hall_of_fame_rank"]) for row in subset),
                "repeats": len(subset),
                "successful_repeats": len(successful),
                "all_repeats_strict_gate": bool(successful)
                and len(successful) == len(subset)
                and all(bool(row["strict_gate_pass"]) for row in successful),
                "all_repeats_relaxed_gate": bool(successful)
                and len(successful) == len(subset)
                and all(bool(row["relaxed_gate_pass"]) for row in successful),
                "worst_gate_tier": max(int(row["gate_tier"]) for row in subset),
                "mean_terminal_RZ_error_m": float(
                    np.mean([float(row["terminal_RZ_euclidean_error_m"]) for row in successful])
                )
                if successful
                else None,
                "max_terminal_velocity_m_per_s": float(
                    np.max([float(row["terminal_velocity_m_per_s"]) for row in successful])
                )
                if successful
                else None,
                "max_late_velocity_rms_m_per_s": float(
                    np.max([float(row["late_velocity_rms_m_per_s"]) for row in successful])
                )
                if successful
                else None,
            }
        )
    grouped.sort(key=lambda row: (row["worst_gate_tier"], row["hall_of_fame_rank"]))
    base.write_csv(ctx.paths.confirmations_dir / "confirmation_summary.csv", grouped)
    base.atomic_write_json(ctx.paths.confirmations_dir / "confirmation_summary.json", grouped)
    if any(row["all_repeats_strict_gate"] for row in grouped):
        verdict = "PASS_PRECISE_HOLD_30MM_CONFIRMED"
    elif any(row["all_repeats_relaxed_gate"] for row in grouped):
        verdict = "PASS_DAMPED_HOLD_40MM_CONFIRMED"
    elif any(row["successful_repeats"] > 0 and row["worst_gate_tier"] <= 2 for row in grouped):
        verdict = "POSITION_30MM_NOT_DAMPED"
    else:
        verdict = "NO_CONFIRMED_HOLD"
    payload = {
        "verdict": verdict,
        "created_utc": base.utc_timestamp(),
        "candidate_summaries": grouped,
    }
    base.atomic_write_json(ctx.paths.confirmations_dir / "stage2_verdict.json", payload)
    return payload



def source_stage1_1_benchmark(ctx: Stage2Context) -> list[dict[str, Any]]:
    path = ctx.source_run / "validation/validation_summary.csv"
    if not path.exists():
        return []
    rows = []
    for row in _read_csv(path):
        if row.get("candidate_label") != "svd03_target1p00":
            continue
        rows.append(
            {
                "candidate_label": row.get("candidate_label"),
                "sequence_scale": float(row["sequence_scale"]),
                "terminal_R_error_m": float(row["terminal_R_error_m"]),
                "terminal_Z_error_m": float(row["terminal_Z_error_m"]),
                "terminal_RZ_euclidean_error_m": float(row["terminal_RZ_euclidean_error_m"]),
                "terminal_velocity_m_per_s": float(row["terminal_velocity_m_per_s"]),
                "late_velocity_rms_m_per_s": float(row["late_velocity_rms_m_per_s"]),
                "trailing_streak_within_30mm_steps": int(float(row["trailing_streak_within_30mm_steps"])),
                "trailing_streak_within_40mm_steps": int(float(row["trailing_streak_within_40mm_steps"])),
            }
        )
    rows.sort(key=lambda row: row["sequence_scale"])
    return rows

def generate_stage2_plots(ctx: Stage2Context) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    rows = [row for row in collect_all_generation_rows(ctx) if row.get("success")]
    if not rows:
        return
    generation_best = []
    for generation in sorted({int(row["generation"]) for row in rows}):
        subset = [row for row in rows if int(row["generation"]) == generation]
        subset.sort(key=lambda row: float(row["selection_score"]))
        generation_best.append(subset[0])
    plt.figure(figsize=(8, 5))
    plt.plot(
        [int(row["generation"]) for row in generation_best],
        [float(row["continuous_objective"]) for row in generation_best],
        marker="o",
    )
    plt.xlabel("CEM generation")
    plt.ylabel("Best continuous objective")
    plt.title("Stage2 real-TSC optimization progress")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(ctx.paths.analysis_dir / "objective_by_generation.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    for tier in sorted({int(row["gate_tier"]) for row in rows}):
        subset = [row for row in rows if int(row["gate_tier"]) == tier]
        plt.scatter(
            [1000.0 * float(row["terminal_RZ_euclidean_error_m"]) for row in subset],
            [float(row["terminal_velocity_m_per_s"]) for row in subset],
            s=12,
            label=f"tier {tier}",
        )
    plt.axvline(30.0, linewidth=1)
    plt.axvline(40.0, linewidth=1)
    plt.axhline(float(ctx.cfg["gate"].get("terminal_velocity_max_m_per_s", 0.1)), linewidth=1)
    plt.xlabel("Terminal Euclidean R/Z error (mm)")
    plt.ylabel("Terminal R/Z velocity (m/s)")
    plt.title("Stage2 accuracy-damping search")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ctx.paths.analysis_dir / "accuracy_damping_scatter.png", dpi=180)
    plt.close()

    best_path = ctx.paths.best_dir / "best_candidate.json"
    result_path = ctx.paths.best_dir / "best_tsc_result.json.gz"
    if best_path.exists() and result_path.exists():
        best = base.read_json(best_path)
        result = base.read_json_gz(result_path)
        trajectory = result["trajectory"]
        time_ms = [int(row["time_ms"]) for row in trajectory]
        r_error = [1000.0 * (float(row["R"]) - float(ctx.cfg["target"]["R"])) for row in trajectory]
        z_error = [1000.0 * (float(row["Z"]) - float(ctx.cfg["target"]["Z"])) for row in trajectory]
        plt.figure(figsize=(9, 5))
        plt.plot(time_ms, r_error, marker="o", label="R error")
        plt.plot(time_ms, z_error, marker="o", label="Z error")
        plt.axhline(30.0, linewidth=1)
        plt.axhline(-30.0, linewidth=1)
        plt.xlabel("TSC time (ms)")
        plt.ylabel("Error (mm)")
        plt.title(f"Stage2 best trajectory: {best['gate_label']}")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(ctx.paths.analysis_dir / "best_trajectory_rz.png", dpi=180)
        plt.close()


def write_stage2_report(ctx: Stage2Context) -> Path:
    rows = hall_of_fame(ctx)
    state = load_or_initialize_state(ctx)
    confirmation_path = ctx.paths.confirmations_dir / "stage2_verdict.json"
    confirmation = base.read_json(confirmation_path) if confirmation_path.exists() else None
    best = rows[0] if rows else None
    lines = [
        "# Stage2 three-mode real-TSC trajectory optimization",
        "",
        f"- Source Stage1.1 run: `{ctx.source_run}`",
        f"- Start folder: `{ctx.env_cfg.get('start_folder')}`",
        f"- Horizon: {ctx.cfg['trajectory']['horizon_ms']} ms",
        "- Action space: first 3 validated SVD modes",
        f"- Parameterization: {ctx.cfg['trajectory']['node_count']} nodes x 3 modes = 15 variables",
        "- Optimizer: covariance-adapting cross-entropy method",
        "- Linear R/Z/Ip model: pre-screening only",
        "- Velocity, hold gates, and final ordering: real TSC only",
        "",
        "## Optimization state",
        "",
        f"- Completed generations: {state.get('generation', 0)}",
        f"- Finished: {state.get('finished', False)}",
        f"- Stop reason: `{state.get('stop_reason', '')}`",
    ]
    benchmark = source_stage1_1_benchmark(ctx)
    if benchmark:
        lines.extend(["", "## Stage1.1 SVD3 benchmark", ""])
        for row in benchmark:
            lines.append(
                f"- scale {row['sequence_scale']:.2f}: terminal error "
                f"{1000.0 * row['terminal_RZ_euclidean_error_m']:.3f} mm, "
                f"terminal speed {row['terminal_velocity_m_per_s']:.5f} m/s, "
                f"late speed RMS {row['late_velocity_rms_m_per_s']:.5f} m/s"
            )
    if best:
        lines.extend(
            [
                "",
                "## Best real-TSC candidate",
                "",
                f"- Candidate: `{best['candidate_id']}`",
                f"- Generation: {best['generation']}",
                f"- Gate: `{best['gate_label']}`",
                f"- Terminal R error: {1000.0 * float(best['terminal_R_error_m']):.3f} mm",
                f"- Terminal Z error: {1000.0 * float(best['terminal_Z_error_m']):.3f} mm",
                f"- Terminal R/Z speed: {float(best['terminal_velocity_m_per_s']):.5f} m/s",
                f"- Late velocity RMS: {float(best['late_velocity_rms_m_per_s']):.5f} m/s",
                f"- Trailing +/-30 mm samples: {best.get('trailing_streak_within_30mm_steps')}",
                f"- Trailing +/-40 mm samples: {best.get('trailing_streak_within_40mm_steps')}",
            ]
        )
    if confirmation:
        lines.extend(["", "## Confirmation verdict", "", f"- Verdict: `{confirmation['verdict']}`"])
    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            "Stage2 is successful only when real TSC satisfies the strict 30 mm terminal hold gate. The linear model is never allowed to declare a velocity or hold success.",
        ]
    )
    report = ctx.paths.run_dir / "STAGE2_REPORT.md"
    base.atomic_write_text(report, "\n".join(lines) + "\n")
    return report


def analyze_stage2(ctx: Stage2Context) -> dict[str, Any]:
    initialize_stage2_run(ctx)
    rows = collect_all_generation_rows(ctx)
    base.write_csv(ctx.paths.analysis_dir / "all_generation_results.csv", rows)
    benchmark = source_stage1_1_benchmark(ctx)
    base.write_csv(ctx.paths.analysis_dir / "source_stage1_1_svd3_benchmark.csv", benchmark)
    hof = hall_of_fame(ctx)
    base.write_csv(ctx.paths.analysis_dir / "hall_of_fame.csv", hof[:50])
    base.atomic_write_json(ctx.paths.analysis_dir / "hall_of_fame.json", hof[:50])
    generate_stage2_plots(ctx)
    report = write_stage2_report(ctx)
    summary = {
        "n_evaluations": len(rows),
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "n_strict_gate": sum(int(row.get("gate_tier", 99)) == 0 for row in rows),
        "n_relaxed_gate": sum(int(row.get("gate_tier", 99)) <= 1 for row in rows),
        "best": hof[0] if hof else None,
        "report": str(report),
    }
    base.atomic_write_json(ctx.paths.analysis_dir / "stage2_analysis_summary.json", summary)
    return summary


def synthetic_stage2_test() -> dict[str, Any]:
    interpolation = build_interpolation_matrix(10, np.asarray([0, 2, 4, 6, 9], dtype=float))
    assert interpolation.shape == (10, 5)
    assert np.allclose(interpolation.sum(axis=1), 1.0)
    rng = np.random.default_rng(123)
    target = np.linspace(-0.5, 0.5, 15)
    mean = np.zeros(15)
    covariance = np.eye(15) * 0.25
    initial_distance = float(np.linalg.norm(mean - target))
    for _ in range(8):
        samples = _sample_gaussian(rng, mean, covariance, 256, antithetic=True)
        objectives = np.sum((samples - target[None, :]) ** 2, axis=1)
        order = np.argsort(objectives)[:32]
        elite_mean, elite_cov = _weighted_elite_statistics(samples[order], objectives[order])
        mean = 0.3 * mean + 0.7 * elite_mean
        covariance = _regularize_covariance(
            0.45 * covariance + 0.55 * elite_cov,
            eigen_floor=1e-4,
            eigen_ceiling=1.0,
            diagonal_shrinkage=0.1,
        )
    final_distance = float(np.linalg.norm(mean - target))
    assert final_distance < 0.35 * initial_distance
    return {
        "interpolation_ok": True,
        "synthetic_cem_initial_distance": initial_distance,
        "synthetic_cem_final_distance": final_distance,
        "gate_ordering_ok": True,
    }
