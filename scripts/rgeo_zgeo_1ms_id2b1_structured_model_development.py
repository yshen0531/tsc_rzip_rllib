#!/usr/bin/env python3
"""Fit and compare leak-free structured ID-2B1 development models."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2a_duration_history_development import rollout_specs  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2b1-structured-model-development-result-v1"
ARTIFACT_SCHEMA = "rgeo-zgeo-1ms-id2b1-structured-model-artifact-v1"
CONFIG_SHA256 = "de37d8f84eab8acf9eda018336d0c31e74d7f1e7e7100800d54091acd7efe112"
ID2A_SOURCE_REVISION = "d25ee2a9e6112f9da25014b5349888298e1bd500"
INPUT_FAIL_ROUTE = "ONE_MS_ID2B1_INPUT_OR_DATA_INTEGRITY_FAIL_NO_MODEL_CLAIM"
NO_MODEL_ROUTE = "ONE_MS_ID2B1_NO_CONTEXT_ROBUST_ACTION_MODEL_TARGETED_DATA_REQUIRED"
PASS_ROUTE = "ONE_MS_ID2B1_STABLE_LIFTED_MODEL_PASS_FRESH_CALIBRATION_REQUIRED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def load_config(repo_root: Path, config_path: Path) -> dict[str, Any]:
    path = inside(repo_root, config_path, "ID2B1 config")
    if sha256_file(path) != CONFIG_SHA256:
        raise ValueError("ID2B1 config hash mismatch")
    config = read_json(path)
    if config.get("schema_version") != "rgeo-zgeo-1ms-id2b1-structured-model-development-v1":
        raise ValueError("ID2B1 schema mismatch")
    if any(config.get(key) != 0 for key in ("plant_advances", "tsc_calls", "holdout_records_read", "calibration_records_read")):
        raise ValueError("ID2B1 execution/data counters must remain zero")
    if config.get("routes") != {
        "input_fail": INPUT_FAIL_ROUTE,
        "no_action_model": NO_MODEL_ROUTE,
        "structured_pass": PASS_ROUTE,
    }:
        raise ValueError("ID2B1 routes mismatch")
    poles = [float(value) for value in config["stable_memory"]["poles"]]
    if not poles or any(not 0.0 <= abs(value) < 1.0 for value in poles):
        raise ValueError("ID2B1 stable-memory poles are invalid")
    prediction = config["prediction_contract"]
    if prediction.get("future_actual_current") != "derived_only_from_issued_target_and_issue_plus_one_contract":
        raise ValueError("future-current propagation contract mismatch")
    if prediction.get("recursive_predicted_state_feedback") is not False:
        raise ValueError("unconstrained predicted-state feedback is forbidden")
    if config["selection"].get("neural_residual_in_this_stage") is not False:
        raise ValueError("neural residual is forbidden in ID2B1")
    return config


def _verify_bound(repo_root: Path, relative: str, expected: str, label: str) -> Path:
    path = inside(repo_root, repo_root / relative, label)
    if sha256_file(path) != expected:
        raise ValueError(f"{label} hash mismatch")
    return path


def load_rows(
    repo_root: Path,
    config: dict[str, Any],
    run_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    run_dir = inside(repo_root, run_dir, "ID2A run directory")
    if run_dir.name != config["source_id2a_run_directory"]:
        raise ValueError("ID2A run-directory identity mismatch")
    stage_path = _verify_bound(
        repo_root,
        config["source_id2a_config"]["path"],
        config["source_id2a_config"]["sha256"],
        "ID2A config",
    )
    b0 = config["source_id2b0"]
    b0_result_path = _verify_bound(repo_root, b0["result_path"], b0["result_sha256"], "ID2B0 result")
    b0_independent_path = _verify_bound(
        repo_root, b0["independent_path"], b0["independent_sha256"], "ID2B0 independent audit"
    )
    b0_result = read_json(b0_result_path)
    b0_independent = read_json(b0_independent_path)
    if b0_result.get("config_sha256") != b0["config_sha256"] or b0_result.get("route") != b0["required_route"]:
        raise ValueError("ID2B0 result identity mismatch")
    if b0_result.get("passed") is not True or b0_independent.get("audit_passed") is not True:
        raise ValueError("ID2B0 readiness did not pass")
    if b0_independent.get("recomputed_route") != b0["required_route"]:
        raise ValueError("ID2B0 independent route mismatch")

    primary_path = run_dir / "result.json"
    independent_path = run_dir / "independent_audit.json"
    if sha256_file(primary_path) != config["source_id2a_primary_sha256"]:
        raise ValueError("ID2A primary result hash mismatch")
    if sha256_file(independent_path) != config["source_id2a_independent_sha256"]:
        raise ValueError("ID2A independent result hash mismatch")
    primary = read_json(primary_path)
    independent = read_json(independent_path)
    if primary.get("model_fit_data_eligible") is not True or independent.get("audit_passed") is not True:
        raise ValueError("ID2A source is not fit eligible")

    stage = read_json(stage_path)
    specs = rollout_specs(stage)
    rows: list[dict[str, Any]] = []
    compact_lines: list[str] = []
    for spec in specs:
        path = run_dir / f"{spec['rollout_id']}.json"
        if not path.is_file():
            raise ValueError(f"missing ID2A compact: {spec['rollout_id']}")
        row = read_json(path)
        if row.get("schema_version") != "rgeo-zgeo-1ms-id2a-duration-history-development-v1":
            raise ValueError(f"ID2A compact schema mismatch: {spec['rollout_id']}")
        if row.get("source_revision") != ID2A_SOURCE_REVISION or row.get("passed") is not True:
            raise ValueError(f"ID2A compact identity mismatch: {spec['rollout_id']}")
        for key in ("rollout_id", "context_id", "direction_id", "sign", "duration_issues", "repeat_index"):
            if row.get(key) != spec.get(key):
                raise ValueError(f"ID2A compact spec mismatch: {spec['rollout_id']}:{key}")
        if len(row.get("states", [])) != 33 or len(row.get("actions", [])) != 32:
            raise ValueError(f"ID2A compact length mismatch: {spec['rollout_id']}")
        compact_lines.append(f"{path.name}\t{path.stat().st_size}\t{sha256_file(path)}")
        rows.append(row)
    unique = [row for row in rows if int(row["repeat_index"]) == 0]
    contract = config["data_contract"]
    if len(rows) != contract["whole_trajectory_records"] or len(unique) != contract["unique_whole_trajectory_cells"]:
        raise ValueError("ID2A trajectory count mismatch")
    if sorted({row["context_id"] for row in unique}) != sorted(contract["contexts"]):
        raise ValueError("ID2A context set mismatch")
    payload = "".join(f"{line}\n" for line in sorted(compact_lines)).encode("utf-8")
    identity = {
        "id2a_source_revision": primary["source_revision"],
        "id2a_route": primary["route"],
        "id2a_required_artifact_inventory_sha256": primary["required_artifact_inventory_sha256"],
        "id2a_compact_inventory_sha256": hashlib.sha256(payload).hexdigest(),
        "id2b0_result_sha256": sha256_file(b0_result_path),
        "id2b0_independent_sha256": sha256_file(b0_independent_path),
    }
    return stage, unique, identity


def _states(row: dict[str, Any]) -> np.ndarray:
    return np.asarray(
        [[float(state["r_geo_m"]), float(state["z_geo_m"]), float(state["ip_a"])] for state in row["states"]],
        dtype=float,
    )


def _q0_target(row: dict[str, Any]) -> np.ndarray:
    target = np.asarray(row["actions"][9]["target_current_a_tsc"], dtype=float)
    if target.shape != (14,):
        raise ValueError("q0 target does not have fourteen coils")
    return target


def _issued_offsets(row: dict[str, Any], scale: float) -> np.ndarray:
    q0 = _q0_target(row)
    values = np.asarray([action["target_current_a_tsc"] for action in row["actions"]], dtype=float)
    if values.shape != (32, 14):
        raise ValueError("issued current history shape mismatch")
    return (values - q0) / scale


def _actual_offset(row: dict[str, Any], origin: int, scale: float) -> np.ndarray:
    actual = np.asarray(row["states"][origin]["actual_current_a_tsc"], dtype=float)
    if actual.shape != (14,):
        raise ValueError("actual current shape mismatch")
    return (actual - _q0_target(row)) / scale


def _filter_history(sequence: np.ndarray, poles: Sequence[float]) -> np.ndarray:
    states = np.zeros((len(poles), sequence.shape[1]), dtype=float)
    for value in sequence:
        states = np.asarray(poles, dtype=float)[:, None] * states + value[None, :]
    return states.reshape(-1)


def feature_vector(
    row: dict[str, Any],
    origin: int,
    horizon: int,
    model_id: str,
    config: dict[str, Any],
) -> np.ndarray:
    """Build one causal direct-horizon feature vector without future truth."""
    if not (10 <= origin <= 31 and 1 <= horizon and origin + horizon <= 32):
        raise ValueError("invalid origin/horizon")
    scales = config["scales"]
    output_scale = np.asarray([scales["r_geo_m"], scales["z_geo_m"], scales["ip_a"]], dtype=float)
    coil_scale = float(scales["coil_command_offset_a"])
    poles = [float(value) for value in config["stable_memory"]["poles"]]
    values = _states(row)
    scaled = (values - values[0]) / output_scale
    innovations = np.diff(values[: origin + 1], axis=0) / output_scale
    issued = _issued_offsets(row, coil_scale)
    virtual = np.asarray([action["probe_virtual_action"] for action in row["actions"]], dtype=float)
    if virtual.shape != (32, 2):
        raise ValueError("virtual action shape mismatch")

    history_dy = _filter_history(innovations, poles)
    history_signed = _filter_history(issued[:origin], poles)
    history_even = _filter_history(np.abs(issued[:origin]), poles)
    current_innovation = innovations[-1]
    base = np.concatenate(
        [
            np.asarray(
                [
                    (origin - 10.0) / 22.0,
                    horizon / 22.0,
                    (horizon / 22.0) ** 2,
                ]
            ),
            scaled[origin],
            current_innovation,
            _actual_offset(row, origin, coil_scale),
            history_dy,
            history_signed,
            history_even,
        ]
    )
    if model_id == "action_blind_history":
        return base

    future = issued[origin : origin + horizon]
    future_virtual = virtual[origin : origin + horizon]
    future_signed = _filter_history(future, poles)
    future_virtual_signed = _filter_history(future_virtual, poles)
    if model_id == "stable_exp_signed":
        return np.concatenate([base, future_signed, future_virtual_signed])

    future_even = _filter_history(np.abs(future), poles)
    future_virtual_even = _filter_history(np.abs(future_virtual), poles)
    signed_even = np.concatenate([base, future_signed, future_even, future_virtual_signed, future_virtual_even])
    if model_id == "stable_exp_signed_even":
        return signed_even
    if model_id == "stable_exp_contextual":
        # A fixed low-dimensional interaction: current innovation and the
        # slowest causal R/Z/Ip innovation state schedule the known future
        # two-coordinate action lift.  No context label or future state enters.
        slow_history_dy = history_dy[-3:]
        context = np.concatenate([[1.0], current_innovation, slow_history_dy])
        future_small = np.concatenate([future_virtual_signed, future_virtual_even])
        interaction = np.outer(context, future_small).reshape(-1)
        return np.concatenate([signed_even, interaction])
    raise ValueError(f"unsupported ridge model: {model_id}")


def target_delta(row: dict[str, Any], origin: int, horizon: int, config: dict[str, Any]) -> np.ndarray:
    scales = config["scales"]
    output_scale = np.asarray([scales["r_geo_m"], scales["z_geo_m"], scales["ip_a"]], dtype=float)
    values = _states(row)
    return (values[origin + horizon] - values[origin]) / output_scale


def sample_pairs(config: dict[str, Any], dense: bool = False) -> list[tuple[int, int]]:
    prediction = config["prediction_contract"]
    if dense:
        origin = int(prediction["paired_response_origin_state_index"])
        low, high = [int(value) for value in prediction["paired_response_dense_horizons"]]
        return [(origin, horizon) for horizon in range(low, high + 1)]
    low, high = [int(value) for value in prediction["fit_origin_indices"]]
    horizons = [int(value) for value in prediction["horizons_steps"]]
    return [
        (origin, horizon)
        for origin in range(low, high + 1)
        for horizon in horizons
        if origin + horizon <= int(prediction["maximum_state_index"])
    ]


def evaluation_pairs(config: dict[str, Any]) -> list[tuple[int, int]]:
    prediction = config["prediction_contract"]
    return [
        (int(origin), int(horizon))
        for origin in prediction["evaluation_origin_indices"]
        for horizon in prediction["horizons_steps"]
        if int(origin) + int(horizon) <= int(prediction["maximum_state_index"])
    ]


def fit_ridge(features: np.ndarray, targets: np.ndarray, ridge: float) -> dict[str, Any]:
    if features.ndim != 2 or targets.ndim != 2 or features.shape[0] != targets.shape[0]:
        raise ValueError("ridge fit shape mismatch")
    mean = np.mean(features, axis=0)
    std = np.std(features, axis=0)
    std = np.where(std > 1e-12, std, 1.0)
    normalized = (features - mean) / std
    design = np.column_stack([np.ones(features.shape[0]), normalized])
    penalty = np.eye(design.shape[1], dtype=float) * float(ridge)
    penalty[0, 0] = 0.0
    gram = design.T @ design + penalty
    rhs = design.T @ targets
    try:
        coefficients = np.linalg.solve(gram, rhs)
    except np.linalg.LinAlgError:
        coefficients = np.linalg.lstsq(gram, rhs, rcond=None)[0]
    if not np.all(np.isfinite(coefficients)):
        raise ValueError("non-finite ridge coefficients")
    return {
        "mean": mean.tolist(),
        "std": std.tolist(),
        "coefficients": coefficients.tolist(),
        "ridge": float(ridge),
        "feature_count": int(features.shape[1]),
        "training_rows": int(features.shape[0]),
    }


def predict_ridge(model: dict[str, Any], features: np.ndarray) -> np.ndarray:
    mean = np.asarray(model["mean"], dtype=float)
    std = np.asarray(model["std"], dtype=float)
    coefficients = np.asarray(model["coefficients"], dtype=float)
    normalized = (features - mean) / std
    design = np.column_stack([np.ones(features.shape[0]), normalized])
    return design @ coefficients


def _baseline_prediction(row: dict[str, Any], origin: int, horizon: int, model_id: str, config: dict[str, Any]) -> np.ndarray:
    if model_id == "persistence":
        return np.zeros(3, dtype=float)
    if model_id == "last_velocity":
        values = _states(row)
        scales = config["scales"]
        output_scale = np.asarray([scales["r_geo_m"], scales["z_geo_m"], scales["ip_a"]], dtype=float)
        velocity = (values[origin] - values[origin - 1]) / output_scale
        decay = next(float(value["velocity_decay"]) for value in config["candidates"] if value["model_id"] == model_id)
        multiplier = sum(decay**step for step in range(horizon))
        return velocity * multiplier
    raise ValueError(f"unsupported baseline: {model_id}")


def _predict_one(
    row: dict[str, Any], origin: int, horizon: int, model_id: str,
    model: dict[str, Any] | None, config: dict[str, Any],
) -> np.ndarray:
    if model_id in ("persistence", "last_velocity"):
        return _baseline_prediction(row, origin, horizon, model_id, config)
    if model is None:
        raise ValueError("ridge model is missing")
    feature = feature_vector(row, origin, horizon, model_id, config)[None, :]
    return predict_ridge(model, feature)[0]


def fit_fold_model(
    rows: Sequence[dict[str, Any]],
    train_contexts: Sequence[str],
    candidate: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    model_id = candidate["model_id"]
    if candidate["kind"] == "baseline":
        return None
    features: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    for row in rows:
        if row["context_id"] not in train_contexts:
            continue
        for origin, horizon in sample_pairs(config):
            features.append(feature_vector(row, origin, horizon, model_id, config))
            targets.append(target_delta(row, origin, horizon, config))
    return fit_ridge(np.stack(features), np.stack(targets), float(candidate["ridge"]))


def evaluate_fold(
    rows: Sequence[dict[str, Any]],
    test_context: str,
    candidate: dict[str, Any],
    model: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    model_id = candidate["model_id"]
    test_rows = [row for row in rows if row["context_id"] == test_context]
    output_scale = np.asarray(
        [config["scales"]["r_geo_m"], config["scales"]["z_geo_m"], config["scales"]["ip_a"]], dtype=float
    )
    absolute_errors_scaled: list[np.ndarray] = []
    for row in test_rows:
        for origin, horizon in evaluation_pairs(config):
            predicted = _predict_one(row, origin, horizon, model_id, model, config)
            absolute_errors_scaled.append(predicted - target_delta(row, origin, horizon, config))
    errors = np.stack(absolute_errors_scaled)
    geometry_mm = np.linalg.norm(errors[:, :2], axis=1)
    ip_a = np.abs(errors[:, 2]) * output_scale[2]

    baseline = next(row for row in test_rows if row["is_context_baseline"])
    action_rows = [row for row in test_rows if not row["is_context_baseline"]]
    arm_metrics: list[dict[str, Any]] = []
    response_floor = float(config["scales"]["response_floor_mm"])
    signal_threshold = float(config["eligibility_gates"]["signal_arm_peak_threshold_mm"])
    all_normalized_squared: list[float] = []
    direction_passes: list[bool] = []
    for row in action_rows:
        actual_curve: list[np.ndarray] = []
        predicted_curve: list[np.ndarray] = []
        for origin, horizon in sample_pairs(config, dense=True):
            actual = target_delta(row, origin, horizon, config) - target_delta(baseline, origin, horizon, config)
            predicted = _predict_one(row, origin, horizon, model_id, model, config) - _predict_one(
                baseline, origin, horizon, model_id, model, config
            )
            actual_curve.append(actual)
            predicted_curve.append(predicted)
        actual_values = np.stack(actual_curve)
        predicted_values = np.stack(predicted_curve)
        actual_rz_mm = actual_values[:, :2]
        predicted_rz_mm = predicted_values[:, :2]
        norms = np.linalg.norm(actual_rz_mm, axis=1)
        peak_index = int(np.argmax(norms))
        peak = float(norms[peak_index])
        eligible = peak >= signal_threshold
        denominator = max(peak, response_floor)
        vector_errors = np.linalg.norm(predicted_rz_mm - actual_rz_mm, axis=1) / denominator
        curve_rmse = float(np.sqrt(np.mean(vector_errors**2)))
        actual_peak = actual_rz_mm[peak_index]
        predicted_peak = predicted_rz_mm[peak_index]
        denom = float(np.linalg.norm(actual_peak) * np.linalg.norm(predicted_peak))
        cosine = float(np.dot(actual_peak, predicted_peak) / denom) if denom > 0.0 else -1.0
        if eligible:
            all_normalized_squared.extend((vector_errors**2).tolist())
            direction_passes.append(cosine >= float(config["eligibility_gates"]["peak_vector_direction_cosine_threshold"]))
        arm_metrics.append(
            {
                "rollout_id": row["rollout_id"],
                "peak_response_mm": peak,
                "signal_eligible": eligible,
                "response_scaled_rmse": curve_rmse,
                "peak_direction_cosine": cosine,
            }
        )
    eligible_rmses = [row["response_scaled_rmse"] for row in arm_metrics if row["signal_eligible"]]
    if not eligible_rmses:
        raise ValueError(f"no signal-eligible arms in fold {test_context}")
    response_rmse = float(math.sqrt(sum(all_normalized_squared) / len(all_normalized_squared)))
    return {
        "test_context": test_context,
        "absolute_geometry_p95_mm": float(np.percentile(geometry_mm, 95)),
        "absolute_geometry_max_mm": float(np.max(geometry_mm)),
        "absolute_ip_p95_a": float(np.percentile(ip_a, 95)),
        "absolute_ip_max_a": float(np.max(ip_a)),
        "absolute_scaled_rmse": float(np.sqrt(np.mean(errors**2))),
        "signal_eligible_arms": len(eligible_rmses),
        "response_scaled_rmse": response_rmse,
        "response_arm_scaled_rmse_p90": float(np.percentile(eligible_rmses, 90)),
        "response_arm_scaled_rmse_max": float(max(eligible_rmses)),
        "peak_vector_direction_pass_fraction": float(sum(direction_passes) / len(direction_passes)),
        "arm_metrics": arm_metrics,
    }


def apply_gates(
    candidate_metrics: dict[str, list[dict[str, Any]]],
    config: dict[str, Any],
) -> dict[str, Any]:
    gates = config["eligibility_gates"]
    action_blind = {row["test_context"]: row for row in candidate_metrics["action_blind_history"]}
    verdicts: dict[str, Any] = {}
    candidate_specs = {row["model_id"]: row for row in config["candidates"]}
    for model_id, folds in candidate_metrics.items():
        spec = candidate_specs[model_id]
        reasons: list[str] = []
        improvements: dict[str, float] = {}
        for fold in folds:
            context = fold["test_context"]
            if fold["absolute_geometry_p95_mm"] > gates["maximum_absolute_geometry_p95_mm_each_fold"]:
                reasons.append(f"GEOMETRY_P95:{context}")
            if fold["absolute_geometry_max_mm"] > gates["maximum_absolute_geometry_max_mm_each_fold"]:
                reasons.append(f"GEOMETRY_MAX:{context}")
            if fold["absolute_ip_p95_a"] > gates["maximum_absolute_ip_p95_a_each_fold"]:
                reasons.append(f"IP_P95:{context}")
            if fold["absolute_ip_max_a"] > gates["maximum_absolute_ip_max_a_each_fold"]:
                reasons.append(f"IP_MAX:{context}")
            if spec["kind"] == "baseline" or model_id == "action_blind_history":
                continue
            if fold["response_arm_scaled_rmse_max"] > gates["maximum_signal_arm_response_scaled_rmse_each_fold"]:
                reasons.append(f"RESPONSE_MAX:{context}")
            if fold["response_arm_scaled_rmse_p90"] > gates["maximum_signal_arm_response_scaled_rmse_p90_each_fold"]:
                reasons.append(f"RESPONSE_P90:{context}")
            blind_value = action_blind[context]["response_scaled_rmse"]
            improvement = 1.0 - fold["response_scaled_rmse"] / blind_value if blind_value > 0.0 else -math.inf
            improvements[context] = float(improvement)
            if improvement < gates["minimum_action_response_improvement_vs_action_blind_each_fold"]:
                reasons.append(f"ACTION_IMPROVEMENT:{context}")
            if fold["peak_vector_direction_pass_fraction"] < gates["minimum_peak_vector_direction_pass_fraction_each_fold"]:
                reasons.append(f"PEAK_DIRECTION:{context}")
        action_conditioned = spec["kind"] != "baseline" and model_id != "action_blind_history"
        eligible = action_conditioned and not reasons
        verdicts[model_id] = {
            "action_conditioned": action_conditioned,
            "eligible": eligible,
            "failure_reasons": reasons,
            "action_response_improvement_vs_action_blind": improvements,
            "worst_fold_response_scaled_rmse": float(max(row["response_scaled_rmse"] for row in folds)),
            "worst_fold_absolute_scaled_rmse": float(max(row["absolute_scaled_rmse"] for row in folds)),
        }
    eligible = [model_id for model_id, value in verdicts.items() if value["eligible"]]
    selected = min(
        eligible,
        key=lambda model_id: (
            verdicts[model_id]["worst_fold_response_scaled_rmse"],
            verdicts[model_id]["worst_fold_absolute_scaled_rmse"],
            model_id,
        ),
        default=None,
    )
    return {"candidate_verdicts": verdicts, "eligible_candidates": eligible, "selected_model_id": selected}


def run_development(
    rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    contexts = list(config["data_contract"]["contexts"])
    candidate_metrics: dict[str, list[dict[str, Any]]] = {}
    fold_models: dict[str, dict[str, Any]] = {}
    fit_count = 0
    for candidate in config["candidates"]:
        model_id = candidate["model_id"]
        candidate_metrics[model_id] = []
        fold_models[model_id] = {}
        for test_context in contexts:
            train_contexts = [context for context in contexts if context != test_context]
            model = fit_fold_model(rows, train_contexts, candidate, config)
            if model is not None:
                fit_count += 1
                fold_models[model_id][test_context] = model
            candidate_metrics[model_id].append(evaluate_fold(rows, test_context, candidate, model, config))
    selection = apply_gates(candidate_metrics, config)
    selected = selection["selected_model_id"]
    final_model = None
    if selected is not None:
        spec = next(row for row in config["candidates"] if row["model_id"] == selected)
        final_model = fit_fold_model(rows, contexts, spec, config)
        fit_count += 1
    artifact = {
        "schema_version": ARTIFACT_SCHEMA,
        "config_sha256": CONFIG_SHA256,
        "fold_models": fold_models,
        "selected_model_id": selected,
        "all_context_model": final_model,
    }
    evaluation = {
        "candidate_metrics": candidate_metrics,
        "selection": selection,
        "models_fit": fit_count,
        "whole_context_folds": len(contexts),
        "unique_trajectory_cells": len(rows),
        "fit_origin_horizon_pairs_per_trajectory": len(sample_pairs(config)),
        "absolute_evaluation_pairs_per_trajectory": len(evaluation_pairs(config)),
        "dense_response_horizons": len(sample_pairs(config, dense=True)),
    }
    return evaluation, artifact


def _numeric_max_difference(left: Any, right: Any) -> float:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return math.inf
        return max((_numeric_max_difference(left[key], right[key]) for key in left), default=0.0)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return math.inf
        return max((_numeric_max_difference(a, b) for a, b in zip(left, right)), default=0.0)
    if isinstance(left, bool) or isinstance(right, bool) or left is None or right is None or isinstance(left, str) or isinstance(right, str):
        return 0.0 if left == right else math.inf
    return abs(float(left) - float(right))


def execute(
    repo_root: Path,
    config_path: Path,
    run_dir: Path,
    output_dir: Path,
    source_revision: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("source revision must be a full lowercase Git hash")
    output_dir = inside(repo_root, output_dir, "ID2B1 output directory")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        config = load_config(repo_root, config_path)
        _, rows, source_identity = load_rows(repo_root, config, run_dir)
        evaluation, artifact = run_development(rows, config)
        artifact.update({"source_revision": source_revision, "source_identity": source_identity})
        artifact_path = output_dir / "model_artifact.json"
        artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        selected = evaluation["selection"]["selected_model_id"]
        passed = selected is not None
        result = {
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "config_sha256": CONFIG_SHA256,
            "passed": passed,
            "route": PASS_ROUTE if passed else NO_MODEL_ROUTE,
            "failure_reasons": [] if passed else ["NO_ACTION_CONDITIONED_CANDIDATE_PASSED_ALL_CONTEXT_FOLDS"],
            "source_identity": source_identity,
            "evaluation": evaluation,
            "model_artifact_sha256": sha256_file(artifact_path),
            "claim_boundary": {
                "development_model_selected": passed,
                "uncertainty_calibrated": False,
                "holdout_opened": False,
                "controller_or_recovery_qualified": False,
                "arbitrary_14_coil_or_crossing_supported": False,
            },
            "counters": {
                "models_fit_or_trained": evaluation["models_fit"],
                "plant_advances": 0,
                "tsc_calls": 0,
                "holdout_records_read": 0,
                "calibration_records_read": 0,
            },
        }
    except Exception as exc:
        result = {
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": INPUT_FAIL_ROUTE,
            "failure_reasons": [f"{type(exc).__name__}:{exc}"],
            "counters": {
                "models_fit_or_trained": 0,
                "plant_advances": 0,
                "tsc_calls": 0,
                "holdout_records_read": 0,
                "calibration_records_read": 0,
            },
        }
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("configs/rgeo_zgeo_1ms_id2b1_structured_model_development.json"))
    parser.add_argument("--id2a-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    run_dir = args.id2a_run_dir if args.id2a_run_dir.is_absolute() else root / args.id2a_run_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    result = execute(root, config_path, run_dir, output_dir, args.source_revision)
    summary = {
        "schema_version": result["schema_version"],
        "route": result["route"],
        "passed": result["passed"],
        "selected_model_id": result.get("evaluation", {}).get("selection", {}).get("selected_model_id"),
        "failure_reasons": result.get("failure_reasons", []),
        "counters": result["counters"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["route"] != INPUT_FAIL_ROUTE else 2


if __name__ == "__main__":
    raise SystemExit(main())
