"""Stage4.1R15 bounded early-braking local-response identification.

R14 completed normally but did not restore the immutable 270/370 ms contract.
The raw traces show a structural mismatch rather than a runtime failure:

* the lifted 175x105 response model ends at state 35 while the formal weak-slew
  hold ends at state 37;
* R14 issued non-zero final nominal feedforward commands whose delayed physical
  effects landed in states 36/37;
* all 24 R14 development cases were limited by final speed, even though their
  speed was already below 0.1 m/s around states 34--36;
* the R14 summary claimed target-conditioned nominal/integral continuity for the
  whole rollout even though the two post-main-horizon rows used a zero-nominal,
  zero-integral tail.

R15 deliberately does not tune another controller.  It constructs a bounded,
interpolation-only local lifted response model from the complete causal R13/R14
bank, cross-validates that model, and then validates it against preregistered
small zero-net probes around the stable R13 state-23 feedback baseline.  The
formal 250/350 and 270/370 ms contracts remain immutable, and no formal closure
is claimed by this identification stage.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage4_1r10_queue_preview_terminal_transition_hold as r10
from . import stage4_1r12_original_deadline_weak_slew_anticipatory_damping as r12
from . import stage4_1r13_original_deadline_delay_pipeline_early_braking as r13
from . import stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc as r14
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r14.atomic_write_json
atomic_write_json_gz = r14.atomic_write_json_gz
read_json = r14.read_json
read_json_gz = r14.read_json_gz
utc_timestamp = r14.utc_timestamp
write_csv = r14.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R15"
CONTROLLER_REVISION = "bounded_early_braking_local_response_identification_v15"
PACKAGE_REVISION = "r15_bounded_local_response_identification_v1"
EXPECTED_SOURCE_REVISION = r14.CONTROLLER_REVISION
EXPECTED_SOURCE_PACKAGE_REVISION = r14.PACKAGE_REVISION
WEAK_SLEW = 0.9
WEAK_HORIZON = 37
MAIN_HORIZON = 35
N_MODES = 3


def _json_safe(value: Any) -> Any:
    return r14._json_safe(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r14._as_float(value, default)


def _result_complete(path: Path) -> bool:
    return r14._result_complete(path)


def _sha256_file(path: Path) -> str:
    return r14._sha256_file(path)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return "s41r15_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class Stage41R15Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    local_model: Path
    probe_validation: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R15Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r15_source_reference",
            source_audit=run_dir / "stage4_1r15_source_audit",
            local_model=run_dir / "stage4_1r15_local_response_model",
            probe_validation=run_dir / "stage4_1r15_bounded_probe_validation",
            analysis=run_dir / "stage4_1r15_analysis",
            variants=run_dir / "stage4_1r15_environment_variants",
            state=run_dir / "stage4_1r15_state.json",
            manifest=run_dir / "stage4_1r15_manifest.json",
        )


@dataclass
class Stage41R15Context:
    cfg: dict[str, Any]
    paths: Stage41R15Paths
    project_dir: Path
    source_stage41r14_run: Path
    source_stage41r13_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    r14_ctx: r14.Stage41R14Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    return [
        source / "stage4_1r14_manifest.json",
        source / "stage4_1r14_state.json",
        source / "stage4_1r14_config.resolved.json",
        source / "stage4_1r14_analysis" / "stage4_1r14_verdict.json",
        source / "stage4_1r14_analysis" / "stage4_1r14_summary.json",
        source / "stage4_1r14_source_audit" / "summary.json",
        source / "stage4_1r14_oracle_development" / "summary.json",
        source / "stage4_1r14_oracle_development" / "results.json",
        source / "stage4_1r14_oracle_development" / "results.csv",
    ]


def _source_inventory(source: Path) -> dict[str, Any]:
    return r14._source_inventory(source)


def _resolve_recorded_run(project_dir: Path, recorded: str, root_name: str) -> Path:
    return r14._resolve_recorded_run(project_dir, recorded, root_name)


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("R15 controller revision mismatch")
    contract = cfg["formal_timing_contract"]
    if not bool(contract.get("immutable")):
        raise ValueError("R15 formal timing must be immutable")
    normal = contract["normal_slew"]
    weak = contract["weak_slew"]
    if int(normal["arrival_deadline_step"]) != 25 or int(normal["hold_through_step"]) != 35:
        raise ValueError("R15 normal timing must remain 250/350 ms")
    if int(weak["arrival_deadline_step"]) != 27 or int(weak["hold_through_step"]) != 37:
        raise ValueError("R15 weak timing must remain 270/370 ms")
    model = cfg["local_response_model"]
    if int(model["input_step_start"]) != 16 or int(model["input_step_end_inclusive"]) != 36:
        raise ValueError("R15 local-model input window must remain steps 16--36")
    if int(model["output_state_start"]) != 23 or int(model["output_state_end_inclusive"]) != 37:
        raise ValueError("R15 local-model output window must remain states 23--37")
    if int(model["pca_rank"]) != 6:
        raise ValueError("R15 PCA rank is preregistered at 6")
    probe = cfg["bounded_probe_validation"]
    if int(probe["baseline_first_affected_state_step"]) != 23:
        raise ValueError("R15 probes must use the R13 state-23 baseline")
    if int(probe["expected_rollouts"]) != 32:
        raise ValueError("R15 expected probe count must be 32")
    amplitudes = np.asarray(probe["probe_amplitude_by_mode"], dtype=float)
    if amplitudes.shape != (3,) or np.any(amplitudes < 0.0):
        raise ValueError("invalid R15 probe amplitudes")
    if not math.isclose(float(amplitudes[2]), 0.0, abs_tol=1e-15):
        raise ValueError("R15 does not probe mode 2; its dominant-bound diagnosis is modes 0/1")
    ids = [str(row["probe_id"]) for row in probe["probe_basis"]]
    if ids != ["early_mode0", "early_mode1", "late_mode0", "late_mode1"]:
        raise ValueError("R15 probe basis identity changed")
    for row in probe["probe_basis"]:
        effects = [int(x) for x in row["effect_offsets"]]
        signs = [int(x) for x in row["sign_pattern"]]
        if len(effects) != len(signs) or sum(signs) != 0:
            raise ValueError("R15 probes must be zero-net")
        if int(row["mode"]) not in {0, 1}:
            raise ValueError("R15 bounded probes are restricted to dominant modes 0/1")
    if not bool(cfg.get("stage4_2r1_was_not_run_or_reused")):
        raise ValueError("R15 must not reuse Stage4.2R1")
    if bool(cfg.get("formal_timing_contract_restored_by_this_stage")):
        raise ValueError("R15 is identification-only and may not claim formal closure")


def _validate_source_stage41r14(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = source.expanduser().resolve()
    missing = [str(path) for path in _required_source_files(source) if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"R15 source R14 files missing: {missing}")
    manifest = read_json(source / "stage4_1r14_manifest.json")
    state = read_json(source / "stage4_1r14_state.json")
    source_cfg = read_json(source / "stage4_1r14_config.resolved.json")
    verdict = read_json(source / "stage4_1r14_analysis" / "stage4_1r14_verdict.json")
    req = cfg["source_requirement"]
    checks = {
        "stage": manifest.get("stage") == req["required_stage"],
        "controller_revision": manifest.get("controller_revision")
        == req["required_controller_revision"],
        "package_revision": manifest.get("package_revision")
        == req["required_package_revision"],
        "finished": bool(state.get("finished")) is bool(req["require_finished"]),
        "stop_reason": str(state.get("stop_reason", "")) == str(req["require_stop_reason"]),
        "source_audit": bool(state.get("source_audit_complete"))
        and bool((state.get("source_audit_summary") or {}).get("passed")),
        "development_complete": bool(state.get("oracle_development_complete")),
        "development_failed_as_expected": not bool(
            (state.get("oracle_development_summary") or {}).get("passed")
        ),
        "selected_policy_empty": not bool(verdict.get("selected_policy_by_delay")),
    }
    if not all(checks.values()):
        raise ValueError(f"R15 source R14 validation failed: {checks}")
    raw = sorted((source / "stage4_1r14_oracle_development" / "raw").glob("*.json.gz"))
    if len(raw) != int(req["require_r14_raw_count"]):
        raise ValueError(f"R15 expected 24 R14 raw files, found {len(raw)}")
    return manifest, state, source_cfg, verdict


def load_stage41r15_config(
    config_path: Path,
    *,
    source_stage41r14_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R15Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r14_run = source_stage41r14_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r14(
        source_stage41r14_run, cfg
    )
    source_stage41r13_run = _resolve_recorded_run(
        project_dir,
        str(manifest["source_stage4_1r13_run"]),
        "stage4_1r13_runs",
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r15_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r15')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    packaged_r14_cfg = (
        project_dir
        / "configs"
        / "stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_370ms.json"
    )
    if not packaged_r14_cfg.is_file():
        raise FileNotFoundError(f"packaged R14 dependency config missing: {packaged_r14_cfg}")
    r14_ctx = r14.load_stage41r14_config(
        packaged_r14_cfg,
        source_stage41r13_run=source_stage41r13_run,
        run_dir_override=run_dir,
    )
    recorded = manifest.get("source_fingerprint") or {}
    current_r13 = r14._source_inventory(source_stage41r13_run)
    if recorded.get("digest") != current_r13.get("digest"):
        raise ValueError("R15 nested Stage4.1R13 source fingerprint mismatch")
    storage = cfg["storage"]
    base34 = (
        r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    )
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R15_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get("STAGE4_1R15_TSC_RUN_ROOT", storage["tsc_run_root"])
        )
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(
        storage.get("keep_failed_episode_dir", False)
    )
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    base34.env_cfg = env_cfg
    return Stage41R15Context(
        cfg=cfg,
        paths=Stage41R15Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r14_run=source_stage41r14_run,
        source_stage41r13_run=source_stage41r13_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        r14_ctx=r14_ctx,
        source_fingerprint=_source_inventory(source_stage41r14_run),
    )


def _initial_state(ctx: Stage41R15Context) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "local_model_complete": False,
        "probe_validation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R15Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R15Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.local_model,
        ctx.paths.probe_validation,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.is_file():
        existing = read_json(ctx.paths.manifest)
        if existing.get("source_fingerprint", {}).get("digest") != ctx.source_fingerprint["digest"]:
            raise ValueError("R15 resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R15 resume controller revision mismatch")
        if existing.get("package_revision") != PACKAGE_REVISION:
            raise ValueError("R15 resume package revision mismatch")
    elif resume:
        raise FileNotFoundError("R15 resume requested but manifest is missing")
    atomic_write_json(
        ctx.paths.run_dir / "stage4_1r15_config.resolved.json", ctx.cfg
    )
    for name, payload in (
        ("stage4_1r14_manifest.json", ctx.source_manifest),
        ("stage4_1r14_state.json", ctx.source_state),
        ("stage4_1r14_config.resolved.json", ctx.source_cfg),
        ("stage4_1r14_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r14_run": str(ctx.source_stage41r14_run),
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": int(os.environ.get("STAGE4_1R15_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "identification_only": True,
        "formal_timing_contract_restored": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "final_task": ctx.cfg["final_task"],
    }
    if not ctx.paths.manifest.is_file():
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _read_raw_dir(path: Path) -> list[dict[str, Any]]:
    return [read_json_gz(item) for item in sorted(path.glob("*.json.gz"))]


def _velocity_arrays(result: Mapping[str, Any], dt_s: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
    trajectory = list(result.get("trajectory") or [])
    r = np.asarray([row["R"] for row in trajectory], dtype=float)
    z = np.asarray([row["Z"] for row in trajectory], dtype=float)
    vr = np.zeros(len(trajectory), dtype=float)
    vz = np.zeros(len(trajectory), dtype=float)
    if len(trajectory) > 1:
        vr[1:] = np.diff(r) / dt_s
        vz[1:] = np.diff(z) / dt_s
    return vr, vz


def _speed_array(result: Mapping[str, Any], dt_s: float = 0.01) -> np.ndarray:
    vr, vz = _velocity_arrays(result, dt_s)
    return np.sqrt(vr**2 + vz**2)


def _control_input_vector(
    result: Mapping[str, Any], *, start_step: int, end_step_inclusive: int
) -> np.ndarray:
    count = end_step_inclusive - start_step + 1
    values = np.zeros((count, N_MODES), dtype=float)
    present = np.zeros(count, dtype=bool)
    for row in result.get("control_trace") or []:
        step = int(row.get("step", -1))
        if start_step <= step <= end_step_inclusive:
            raw = row.get("applied_desired_physical_mode_coefficients")
            if raw is None:
                raw = row.get("effective_mode_coefficients")
            values[step - start_step] = np.asarray(raw, dtype=float).reshape(N_MODES)
            present[step - start_step] = True
    if not bool(np.all(present)):
        missing = [start_step + index for index, ok in enumerate(present) if not ok]
        raise ValueError(f"local-model input trace missing steps {missing}")
    return values.reshape(-1)


def _output_vector(
    result: Mapping[str, Any], *, start_state: int, end_state_inclusive: int
) -> np.ndarray:
    trajectory = list(result.get("trajectory") or [])
    if len(trajectory) <= end_state_inclusive:
        raise ValueError("local-model trajectory shorter than requested output window")
    vr, vz = _velocity_arrays(result)
    idx = np.arange(start_state, end_state_inclusive + 1)
    r = np.asarray([trajectory[index]["R"] for index in idx], dtype=float)
    z = np.asarray([trajectory[index]["Z"] for index in idx], dtype=float)
    ip = np.asarray([trajectory[index]["Ip"] for index in idx], dtype=float)
    return np.concatenate([vr[idx], vz[idx], r, z, ip])


def _output_layout(cfg: Mapping[str, Any]) -> dict[str, Any]:
    model = cfg["local_response_model"]
    start = int(model["output_state_start"])
    end = int(model["output_state_end_inclusive"])
    count = end - start + 1
    return {
        "state_start": start,
        "state_end_inclusive": end,
        "state_count": count,
        "blocks": ["vR_m_per_s", "vZ_m_per_s", "R_m", "Z_m", "Ip_A"],
        "block_length": count,
    }


def _fit_pca_ridge(
    x: np.ndarray, y: np.ndarray, *, rank: int, ridge_lambda: float
) -> dict[str, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
        raise ValueError("PCA-ridge input shapes are inconsistent")
    mean_x = np.mean(x, axis=0)
    _, singular, vt = np.linalg.svd(x - mean_x, full_matrices=False)
    effective_rank = min(int(rank), max(1, len(x) - 2), vt.shape[0])
    basis = vt[:effective_rank].T
    latent = (x - mean_x) @ basis
    design = np.column_stack([np.ones(len(latent)), latent])
    regularizer = np.diag([0.0] + [float(ridge_lambda)] * effective_rank)
    coefficients = np.linalg.solve(
        design.T @ design + regularizer,
        design.T @ y,
    )
    return {
        "mean_x": mean_x,
        "basis": basis,
        "coefficients": coefficients,
        "singular_values": singular,
    }


def _predict_pca_ridge(model: Mapping[str, Any], x: np.ndarray) -> np.ndarray:
    mean_x = np.asarray(model["mean_x"], dtype=float)
    basis = np.asarray(model["basis"], dtype=float)
    coefficients = np.asarray(model["coefficients"], dtype=float)
    x = np.asarray(x, dtype=float)
    latent = (x - mean_x) @ basis
    if latent.ndim == 1:
        design = np.concatenate([[1.0], latent])
    else:
        design = np.column_stack([np.ones(len(latent)), latent])
    return design @ coefficients


def _endpoint_late_speed(vector: np.ndarray, layout: Mapping[str, Any]) -> float:
    count = int(layout["state_count"])
    start = int(layout["state_start"])
    vr = np.asarray(vector[:count], dtype=float)
    vz = np.asarray(vector[count : 2 * count], dtype=float)
    states = np.arange(start, start + count)
    mask = np.isin(states, [24, 25, 26, 27])
    speed = np.sqrt(vr[mask] ** 2 + vz[mask] ** 2)
    return float(np.sqrt(np.mean(speed**2)))


def _final_speed(vector: np.ndarray, layout: Mapping[str, Any]) -> float:
    count = int(layout["state_count"])
    return float(math.hypot(vector[count - 1], vector[2 * count - 1]))


def _prediction_metrics(
    actual: np.ndarray, predicted: np.ndarray, layout: Mapping[str, Any]
) -> dict[str, float]:
    count = int(layout["state_count"])
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    velocity_rmse = float(
        np.sqrt(np.mean((predicted[: 2 * count] - actual[: 2 * count]) ** 2))
    )
    position_rmse = float(
        np.sqrt(
            np.mean(
                (
                    predicted[2 * count : 4 * count]
                    - actual[2 * count : 4 * count]
                )
                ** 2
            )
        )
    )
    ip_rmse = float(
        np.sqrt(np.mean((predicted[4 * count :] - actual[4 * count :]) ** 2))
    )
    return {
        "velocity_component_rmse_m_per_s": velocity_rmse,
        "endpoint_late_speed_error_m_per_s": abs(
            _endpoint_late_speed(predicted, layout)
            - _endpoint_late_speed(actual, layout)
        ),
        "final_speed_error_m_per_s": abs(
            _final_speed(predicted, layout) - _final_speed(actual, layout)
        ),
        "position_rmse_m": position_rmse,
        "ip_rmse_A": ip_rmse,
    }


def _loocv_model(
    x: np.ndarray,
    y: np.ndarray,
    *,
    rank: int,
    ridge_lambda: float,
    layout: Mapping[str, Any],
) -> dict[str, Any]:
    predictions: list[np.ndarray] = []
    for index in range(len(x)):
        keep = np.arange(len(x)) != index
        model = _fit_pca_ridge(
            x[keep], y[keep], rank=rank, ridge_lambda=ridge_lambda
        )
        predictions.append(_predict_pca_ridge(model, x[index]))
    predicted = np.asarray(predictions, dtype=float)
    metrics = [
        _prediction_metrics(y[index], predicted[index], layout)
        for index in range(len(y))
    ]
    aggregate = {
        key: float(np.sqrt(np.mean([row[key] ** 2 for row in metrics])))
        for key in metrics[0]
    }
    return {
        "predicted": predicted,
        "sample_metrics": metrics,
        "aggregate": aggregate,
    }


def _source_group_key(result: Mapping[str, Any]) -> tuple[str, int]:
    spec = result["spec"]
    return str(spec["target_id"]), int(spec["action_delay_steps"])


def _source_samples(ctx: Stage41R15Context) -> dict[tuple[str, int], list[dict[str, Any]]]:
    r13_raw = _read_raw_dir(
        ctx.source_stage41r13_run / "stage4_1r13_oracle_development" / "raw"
    )
    r14_raw = _read_raw_dir(
        ctx.source_stage41r14_run / "stage4_1r14_oracle_development" / "raw"
    )
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for source_stage, results in (("R13", r13_raw), ("R14", r14_raw)):
        for result in results:
            key = _source_group_key(result)
            if key[0] not in {"nominal", "RZ_p10_m10"} or key[1] not in {1, 2}:
                continue
            groups.setdefault(key, []).append(
                {"source_stage": source_stage, "result": result}
            )
    return groups


def run_source_audit(ctx: Stage41R15Context) -> dict[str, Any]:
    cfg = ctx.cfg["r14_forensic_contract"]
    r14_raw = _read_raw_dir(
        ctx.source_stage41r14_run / "stage4_1r14_oracle_development" / "raw"
    )
    r13_raw = _read_raw_dir(
        ctx.source_stage41r13_run / "stage4_1r13_oracle_development" / "raw"
    )
    if len(r14_raw) != int(cfg["required_r14_raw_count"]):
        raise ValueError("R15 R14 raw coverage mismatch")
    if len(r13_raw) != int(cfg["required_r13_raw_count"]):
        raise ValueError("R15 R13 raw coverage mismatch")
    all_results = r13_raw + r14_raw
    environment_success = sum(bool(row.get("success")) for row in all_results)
    failure_reason_count = sum(bool(str(row.get("failure_reason", "")).strip()) for row in all_results)
    abnormal_count = sum(
        any(bool(item.get("abnormal", False)) for item in row.get("trajectory") or [])
        for row in all_results
    )
    nonfinite_count = 0
    for result in all_results:
        for item in result.get("trajectory") or []:
            numeric = [
                item.get("R"), item.get("Z"), item.get("Ip"),
                item.get("vessel_current_total_a"),
                item.get("vessel_current_abs_sum_a"),
            ]
            if not np.all(np.isfinite(np.asarray(numeric, dtype=float))):
                nonfinite_count += 1
                break

    r14_results = read_json(
        ctx.source_stage41r14_run / "stage4_1r14_oracle_development" / "results.json"
    )
    r14_rows = list(r14_results)
    limiting = {str(row.get("limiting_component")) for row in r14_rows}
    all_final_speed_limited = limiting == {"final_speed"}

    state34_speeds: list[float] = []
    state37_speeds: list[float] = []
    beyond_rows: list[dict[str, Any]] = []
    tail_nominal_false_rows = 0
    summary_claim_true_count = 0
    for result in r14_raw:
        speed = _speed_array(result)
        state34_speeds.append(float(speed[34]))
        state37_speeds.append(float(speed[37]))
        summary = result.get("integrated_deadline_mpc_summary") or {}
        summary_claim_true_count += int(bool(summary.get("target_conditioned_nominal_retained")))
        for row in result.get("integrated_deadline_mpc_trace") or []:
            if not bool(row.get("target_conditioned_nominal_retained", True)):
                tail_nominal_false_rows += 1
            issue = int(row.get("issue_step", -1))
            delay = int(row.get("actual_action_delay_steps", -1))
            affected_state = issue + delay + 1
            feedforward = np.asarray(
                row.get("feedforward_physical_mode_coefficients", [0.0] * N_MODES),
                dtype=float,
            )
            if affected_state > MAIN_HORIZON and float(np.linalg.norm(feedforward)) > 1e-12:
                beyond_rows.append(
                    {
                        "experiment_id": result["experiment_id"],
                        "target_id": result["spec"]["target_id"],
                        "actual_delay_steps": delay,
                        "policy_id": result["spec"]["anticipatory_policy_id"],
                        "issue_step": issue,
                        "affected_state": affected_state,
                        "feedforward_norm": float(np.linalg.norm(feedforward)),
                    }
                )
    beyond_counts: dict[str, list[int]] = {}
    for delay in (1, 2):
        counts = []
        for result in r14_raw:
            if int(result["spec"]["action_delay_steps"]) != delay:
                continue
            count = sum(
                int(row["actual_delay_steps"]) == delay
                for row in beyond_rows
                if row["experiment_id"] == result["experiment_id"]
            )
            counts.append(count)
        beyond_counts[str(delay)] = counts

    groups = _source_samples(ctx)
    group_counts = {
        f"{target}__d{delay}": len(rows)
        for (target, delay), rows in sorted(groups.items())
    }
    expected_group_count = int(ctx.cfg["local_response_model"]["minimum_samples_per_group"])
    group_coverage = len(groups) == 4 and all(
        count == expected_group_count for count in group_counts.values()
    )
    expected_beyond = cfg["expected_beyond_horizon_feedforward_rows_per_delay"]
    beyond_ok = all(
        counts
        and all(count == int(expected_beyond[delay]) for count in counts)
        for delay, counts in beyond_counts.items()
    )
    tail_summary_mismatch = bool(
        summary_claim_true_count == len(r14_raw) and tail_nominal_false_rows > 0
    )
    passed = bool(
        environment_success == len(all_results)
        and failure_reason_count == 0
        and abnormal_count == 0
        and nonfinite_count == 0
        and all_final_speed_limited
        and max(state34_speeds) < float(cfg["require_state34_speed_below_m_per_s"])
        and min(state37_speeds) > float(cfg["require_state37_speed_above_m_per_s"])
        and beyond_ok
        and tail_summary_mismatch
        and group_coverage
    )
    write_csv(ctx.paths.source_audit / "r14_beyond_horizon_feedforward.csv", beyond_rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "r13_raw_rollouts": len(r13_raw),
        "r14_raw_rollouts": len(r14_raw),
        "total_source_rollouts": len(all_results),
        "environment_success_count": environment_success,
        "failure_reason_count": failure_reason_count,
        "abnormal_rollout_count": abnormal_count,
        "nonfinite_rollout_count": nonfinite_count,
        "r14_limiting_components": sorted(limiting),
        "r14_all_final_speed_limited": all_final_speed_limited,
        "maximum_state34_speed_m_per_s": max(state34_speeds),
        "minimum_state37_speed_m_per_s": min(state37_speeds),
        "maximum_state37_speed_m_per_s": max(state37_speeds),
        "beyond_horizon_feedforward_row_count": len(beyond_rows),
        "beyond_horizon_feedforward_rows_per_rollout_by_delay": beyond_counts,
        "tail_rows_with_target_conditioned_nominal_false": tail_nominal_false_rows,
        "rollout_summaries_claiming_target_conditioned_nominal_retained": summary_claim_true_count,
        "tail_nominal_summary_mismatch_detected": tail_summary_mismatch,
        "r14_main_identified_state_horizon": MAIN_HORIZON,
        "formal_hold_state_horizon": WEAK_HORIZON,
        "source_group_sample_counts": group_counts,
        "source_group_coverage_complete": group_coverage,
        "stage4_2r1_was_not_run_or_reused": True,
        "passed": passed,
        "interpretation": (
            "R14 ran normally. All 24 cases were final-speed limited. The speed was "
            "already below 0.1 m/s near state 34, but delayed nonzero last nominal "
            "commands were issued beyond the 35-state identified horizon and the "
            "two-step tail changed nominal/integral semantics. R15 therefore "
            "identifies and validates a bounded local model instead of tuning another "
            "controller."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def run_local_model(ctx: Stage41R15Context) -> dict[str, Any]:
    model_cfg = ctx.cfg["local_response_model"]
    layout = _output_layout(ctx.cfg)
    groups = _source_samples(ctx)
    models: dict[str, Any] = {}
    cv_rows: list[dict[str, Any]] = []
    all_pass = True
    for key in sorted(groups):
        target, delay = key
        samples = groups[key]
        x = np.stack(
            [
                _control_input_vector(
                    item["result"],
                    start_step=int(model_cfg["input_step_start"]),
                    end_step_inclusive=int(model_cfg["input_step_end_inclusive"]),
                )
                for item in samples
            ]
        )
        y = np.stack(
            [
                _output_vector(
                    item["result"],
                    start_state=int(model_cfg["output_state_start"]),
                    end_state_inclusive=int(model_cfg["output_state_end_inclusive"]),
                )
                for item in samples
            ]
        )
        cv = _loocv_model(
            x,
            y,
            rank=int(model_cfg["pca_rank"]),
            ridge_lambda=float(model_cfg["ridge_lambda"]),
            layout=layout,
        )
        thresholds = model_cfg["cross_validation"]
        aggregate = cv["aggregate"]
        group_pass = bool(
            aggregate["velocity_component_rmse_m_per_s"]
            <= float(thresholds["maximum_velocity_component_rmse_m_per_s"])
            and aggregate["endpoint_late_speed_error_m_per_s"]
            <= float(thresholds["maximum_endpoint_late_speed_rmse_m_per_s"])
            and aggregate["final_speed_error_m_per_s"]
            <= float(thresholds["maximum_final_speed_rmse_m_per_s"])
            and aggregate["position_rmse_m"]
            <= float(thresholds["maximum_position_rmse_m"])
            and aggregate["ip_rmse_A"] <= float(thresholds["maximum_ip_rmse_A"])
        )
        all_pass = all_pass and group_pass
        fitted = _fit_pca_ridge(
            x,
            y,
            rank=int(model_cfg["pca_rank"]),
            ridge_lambda=float(model_cfg["ridge_lambda"]),
        )
        group_id = f"{target}__d{delay}"
        models[group_id] = {
            "schema_version": 1,
            "target_id": target,
            "actual_delay_steps": delay,
            "sample_count": len(samples),
            "sample_experiment_ids": [
                item["result"]["experiment_id"] for item in samples
            ],
            "sample_source_stages": [item["source_stage"] for item in samples],
            "input_layout": {
                "step_start": int(model_cfg["input_step_start"]),
                "step_end_inclusive": int(model_cfg["input_step_end_inclusive"]),
                "mode_count": N_MODES,
            },
            "output_layout": layout,
            "pca_rank": int(fitted["basis"].shape[1]),
            "ridge_lambda": float(model_cfg["ridge_lambda"]),
            "mean_x": fitted["mean_x"].tolist(),
            "basis": fitted["basis"].tolist(),
            "coefficients": fitted["coefficients"].tolist(),
            "singular_values": fitted["singular_values"].tolist(),
            "cross_validation": aggregate,
            "cross_validation_passed": group_pass,
            "scope": model_cfg["model_scope"],
        }
        cv_rows.append(
            {
                "group_id": group_id,
                "target_id": target,
                "actual_delay_steps": delay,
                "sample_count": len(samples),
                **aggregate,
                "passed": group_pass,
            }
        )
    write_csv(ctx.paths.local_model / "cross_validation.csv", cv_rows)
    atomic_write_json(ctx.paths.local_model / "models.json", models)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "local_response_model",
        "group_count": len(models),
        "expected_group_count": 4,
        "group_sample_count": {
            group_id: int(model["sample_count"]) for group_id, model in models.items()
        },
        "pca_rank": int(model_cfg["pca_rank"]),
        "ridge_lambda": float(model_cfg["ridge_lambda"]),
        "cross_validation_rows": cv_rows,
        "all_groups_cross_validated": all_pass,
        "identification_only": True,
        "deployment_model_claimed": False,
        "passed": bool(len(models) == 4 and all_pass),
    }
    atomic_write_json(ctx.paths.local_model / "summary.json", summary)
    _update_state(ctx, local_model_complete=True, local_model_summary=summary)
    return summary


def _probe_schedule(
    *, first_effect_state: int, actual_delay: int, basis: Mapping[str, Any],
    sign: int, amplitude_by_mode: Sequence[float]
) -> dict[int, np.ndarray]:
    mode = int(basis["mode"])
    amplitude = float(amplitude_by_mode[mode]) * int(sign)
    schedule: dict[int, np.ndarray] = {}
    for offset, pattern in zip(basis["effect_offsets"], basis["sign_pattern"]):
        effect_state = int(first_effect_state) + int(offset)
        issue_step = effect_state - int(actual_delay) - 1
        delta = np.zeros(N_MODES, dtype=float)
        delta[mode] = amplitude * int(pattern)
        schedule[issue_step] = schedule.get(issue_step, np.zeros(N_MODES)) + delta
    return schedule


class LocalStage41R15ProbeWorker:
    """R13 state-23 feedback with a preregistered bounded identification probe.

    The probe is added to the solver's issued physical correction only at
    preregistered causal issue steps.  It is not a candidate controller and is
    therefore not restricted by the R13 residual-software bound; it remains
    clipped by the absolute trajectory coefficient bounds and by the real
    scheduler/slew constraints.  Each pulse is zero-net and at most 0.015 in one
    dominant SVD mode.
    """

    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.inner = r13.LocalStage41R13Worker(
            payload, library, bundle, worker_id, selector_cfg
        )

    def close(self) -> None:
        self.inner.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        schedule = {
            int(step): np.asarray(value, dtype=float).reshape(N_MODES)
            for step, value in (spec.get("r15_probe_delta_by_issue_step") or {}).items()
        }
        probe_log: dict[int, dict[str, Any]] = {}
        original = r12.r3.solve_delay_aware_physical_correction

        def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
            out = original(*args, **kwargs)
            step = int(kwargs.get("current_step", -1))
            requested = schedule.get(step)
            if requested is None:
                return out
            first = np.asarray(out["first_correction"], dtype=float).reshape(N_MODES)
            ctx_stub = args[0] if args else kwargs["ctx_stub"]
            lower = np.asarray(
                ctx_stub.cfg["trajectory"]["coefficient_lower"], dtype=float
            ).reshape(N_MODES)
            upper = np.asarray(
                ctx_stub.cfg["trajectory"]["coefficient_upper"], dtype=float
            ).reshape(N_MODES)
            modified = np.clip(first + requested, lower, upper)
            updated = dict(out)
            updated["first_correction"] = modified
            sequence = np.asarray(
                updated.get("sequence_correction", np.zeros((0, N_MODES))),
                dtype=float,
            )
            if sequence.ndim == 2 and len(sequence):
                sequence = sequence.copy()
                sequence[0] = modified
                updated["sequence_correction"] = sequence
            probe_log[step] = {
                "requested_delta": requested.tolist(),
                "applied_delta": (modified - first).tolist(),
                "baseline_correction": first.tolist(),
                "modified_correction": modified.tolist(),
            }
            return updated

        r12.r3.solve_delay_aware_physical_correction = wrapped
        try:
            result = self.inner.evaluate(spec)
        finally:
            r12.r3.solve_delay_aware_physical_correction = original
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r15_controller_revision"] = CONTROLLER_REVISION
        result["spec"] = copy.deepcopy(spec)
        trace = list(result.get("anticipatory_damping_trace") or [])
        for row in trace:
            step = int(row.get("step", -1))
            info = probe_log.get(step)
            row["r15_probe_requested_delta"] = (
                info["requested_delta"] if info else [0.0] * N_MODES
            )
            row["r15_probe_applied_delta"] = (
                info["applied_delta"] if info else [0.0] * N_MODES
            )
            row["r15_identification_probe"] = bool(info)
        requested_net = np.sum(np.stack(list(schedule.values())), axis=0)
        applied_deltas = [
            np.asarray(probe_log[step]["applied_delta"], dtype=float)
            for step in sorted(schedule)
            if step in probe_log
        ]
        applied_net = (
            np.sum(np.stack(applied_deltas), axis=0)
            if applied_deltas
            else np.full(N_MODES, np.nan)
        )
        result["r15_probe_summary"] = {
            "probe_id": spec["r15_probe_id"],
            "probe_sign": int(spec["r15_probe_sign"]),
            "probe_schedule": {
                str(step): value.tolist() for step, value in sorted(schedule.items())
            },
            "probe_issue_count": len(schedule),
            "probe_applied_issue_count": len(applied_deltas),
            "requested_probe_net": requested_net.tolist(),
            "applied_probe_net": applied_net.tolist(),
            "requested_probe_net_norm": float(np.linalg.norm(requested_net)),
            "applied_probe_net_norm": float(np.linalg.norm(applied_net)),
            "probe_zero_net": bool(
                np.allclose(requested_net, np.zeros(N_MODES), atol=1e-12, rtol=0.0)
            ),
            "applied_probe_zero_net": bool(
                len(applied_deltas) == len(schedule)
                and np.allclose(applied_net, np.zeros(N_MODES), atol=1e-12, rtol=0.0)
            ),
            "maximum_requested_component": float(
                max([np.max(np.abs(value)) for value in schedule.values()] or [0.0])
            ),
            "maximum_applied_component": float(
                max([np.max(np.abs(value)) for value in applied_deltas] or [0.0])
            ),
            "future_measurement_used": False,
        }
        return _json_safe(result)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage41R15ProbeActor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalStage41R15ProbeWorker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R15ProbeActor
    return _RAY_ACTOR


def materialize_variant(ctx: Stage41R15Context) -> tuple[str, dict[str, Any]]:
    chain = (
        ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx
    )
    variant, payload = r10.materialize_variant(
        chain, slew_scale=WEAK_SLEW, horizon_steps=WEAK_HORIZON
    )
    atomic_write_json(ctx.paths.variants / f"{variant}.payload.json", payload)
    return variant, payload


def _probe_specs(ctx: Stage41R15Context) -> list[dict[str, Any]]:
    probe_cfg = ctx.cfg["bounded_probe_validation"]
    variant, _ = materialize_variant(ctx)
    baseline_policy = {
        "policy_id": str(probe_cfg["baseline_policy_id"]),
        "first_affected_state_step": int(
            probe_cfg["baseline_first_affected_state_step"]
        ),
    }
    specs: list[dict[str, Any]] = []
    for delay in probe_cfg["actual_delay_steps"]:
        for target in probe_cfg["required_targets"]:
            for basis in probe_cfg["probe_basis"]:
                for sign in probe_cfg["probe_signs"]:
                    schedule = _probe_schedule(
                        first_effect_state=int(
                            probe_cfg["baseline_first_affected_state_step"]
                        ),
                        actual_delay=int(delay),
                        basis=basis,
                        sign=int(sign),
                        amplitude_by_mode=probe_cfg["probe_amplitude_by_mode"],
                    )
                    base_spec = r13._make_spec(
                        phase="bounded_probe_validation",
                        policy=baseline_policy,
                        target=target,
                        actual_delay=int(delay),
                        modeled_delay=int(delay),
                        calibration_token=None,
                        trusted=True,
                        controller_variant="r15_bounded_identification_probe",
                        environment_variant=variant,
                        ctx=ctx.r14_ctx.r13_ctx,
                    )
                    identity = {
                        "revision": CONTROLLER_REVISION,
                        "target": dict(target),
                        "actual_delay": int(delay),
                        "probe_id": str(basis["probe_id"]),
                        "probe_sign": int(sign),
                        "schedule": {
                            str(step): value.tolist()
                            for step, value in sorted(schedule.items())
                        },
                    }
                    base_spec.update(
                        {
                            "kind": "stage4_1r15_bounded_early_braking_local_response_identification",
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": _scenario_digest(identity),
                            "phase": "bounded_probe_validation",
                            "category": "bounded_probe_validation",
                            "scenario": (
                                f"{basis['probe_id']}__sign{int(sign):+d}__"
                                f"{target['target_id']}__d{int(delay)}__s0.9"
                            ),
                            "r15_probe_id": str(basis["probe_id"]),
                            "r15_probe_sign": int(sign),
                            "r15_probe_mode": int(basis["mode"]),
                            "r15_probe_delta_by_issue_step": {
                                str(step): value.tolist()
                                for step, value in sorted(schedule.items())
                            },
                            "r15_identification_only": True,
                            "formal_tracking_pass_required": False,
                            "arrival_deadline_expansion_allowed": False,
                        }
                    )
                    specs.append(base_spec)
    if len(specs) != int(probe_cfg["expected_rollouts"]):
        raise ValueError("R15 probe specification count mismatch")
    return specs


def evaluate_specs(
    ctx: Stage41R15Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variant, payload = materialize_variant(ctx)
    chain = (
        ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx
    )
    chain.variants[variant] = payload
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(output_dir / f"{spec['experiment_id']}.json.gz"))
    ]
    library = chain.r3_ctx.source_library
    bundle = chain.r3_ctx.source_bundle
    selector_cfg = ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg[
        "batch_selector"
    ]
    if backend == "serial":
        worker = LocalStage41R15ProbeWorker(
            payload, library, bundle, "stage41r15_serial", selector_cfg
        )
        try:
            for index, spec in enumerate(pending, 1):
                atomic_write_json_gz(
                    output_dir / f"{spec['experiment_id']}.json.gz",
                    worker.evaluate(spec),
                )
                print(
                    f"[Stage4.1R15 bounded-probe] {index}/{len(pending)}",
                    flush=True,
                )
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        requested = int(
            os.environ.get("STAGE4_1R15_WORKERS", ctx.cfg["parallel"]["n_workers"])
        )
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get(
                "RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")
            )
            or None,
            log_prefix="[Stage4.1R15 bounded-probe]",
        )
        Actor = _ray_actor_class()
        actors = [
            Actor.remote(
                payload,
                library,
                bundle,
                f"stage41r15_{index:03d}",
                selector_cfg,
            )
            for index in range(plan.actor_count)
        ]
        refs: dict[Any, dict[str, Any]] = {}
        for index, spec in enumerate(pending):
            refs[actors[index % len(actors)].evaluate.remote(spec)] = spec
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(
                        f"[Stage4.1R15 bounded-probe] waiting {done}/{len(pending)}",
                        flush=True,
                    )
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1,
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                            "control_trace": [],
                        }
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(
                            f"[Stage4.1R15 bounded-probe] {done}/{len(pending)}",
                            flush=True,
                        )
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(
                    ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)
                ),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [
        read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz")
        for spec in specs
    ]


def _baseline_map(ctx: Stage41R15Context) -> dict[tuple[str, int], dict[str, Any]]:
    raw = _read_raw_dir(
        ctx.source_stage41r13_run / "stage4_1r13_oracle_development" / "raw"
    )
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for result in raw:
        spec = result["spec"]
        if (
            int(spec.get("anticipatory_first_affected_state_step", -1)) == 23
            and str(spec["target_id"]) in {"nominal", "RZ_p10_m10"}
            and int(spec["action_delay_steps"]) in {1, 2}
        ):
            out[(str(spec["target_id"]), int(spec["action_delay_steps"]))] = result
    if len(out) != 4:
        raise ValueError("R15 could not locate the four R13 state-23 baselines")
    return out


def _load_models(ctx: Stage41R15Context) -> dict[str, Any]:
    path = ctx.paths.local_model / "models.json"
    if not path.is_file():
        raise FileNotFoundError("R15 local response model artifact is missing")
    return read_json(path)


def run_probe_validation(
    ctx: Stage41R15Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = _probe_specs(ctx)
    raw_dir = ctx.paths.probe_validation / "raw"
    results = evaluate_specs(
        ctx, specs, output_dir=raw_dir, backend=backend, resume=resume
    )
    models = _load_models(ctx)
    baselines = _baseline_map(ctx)
    model_cfg = ctx.cfg["local_response_model"]
    probe_cfg = ctx.cfg["bounded_probe_validation"]
    layout = _output_layout(ctx.cfg)
    validation_cfg = probe_cfg["model_validation"]
    rows: list[dict[str, Any]] = []
    actual_outputs: dict[tuple[str, int, str, int], np.ndarray] = {}
    all_runtime_success = True
    for result in results:
        spec = result["spec"]
        target = str(spec["target_id"])
        delay = int(spec["action_delay_steps"])
        group_id = f"{target}__d{delay}"
        model = models[group_id]
        x = _control_input_vector(
            result,
            start_step=int(model_cfg["input_step_start"]),
            end_step_inclusive=int(model_cfg["input_step_end_inclusive"]),
        )
        actual = _output_vector(
            result,
            start_state=int(model_cfg["output_state_start"]),
            end_state_inclusive=int(model_cfg["output_state_end_inclusive"]),
        )
        predicted = _predict_pca_ridge(model, x)
        metrics = _prediction_metrics(actual, predicted, layout)
        summary = result.get("r15_probe_summary") or {}
        trace = list(result.get("anticipatory_damping_trace") or [])
        prefix_end = int(probe_cfg["baseline_first_affected_state_step"]) - 1
        baseline = baselines[(target, delay)]
        physics_prefix = r14._physics_array(result)[: prefix_end + 1]
        baseline_prefix = r14._physics_array(baseline)[: prefix_end + 1]
        prefix_exact = bool(
            physics_prefix.shape == baseline_prefix.shape
            and np.array_equal(physics_prefix, baseline_prefix)
        )
        r8_ctx = (
            ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx
        )
        env_cfg = (
            r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg
        )
        currents = np.asarray(
            [row["currents_a_display"] for row in result.get("trajectory") or []],
            dtype=float,
        )
        min_i = np.asarray(env_cfg["min_current_a_display_order"], dtype=float)
        max_i = np.asarray(env_cfg["max_current_a_display_order"], dtype=float)
        center_i = 0.5 * (min_i + max_i)
        half_i = np.maximum(0.5 * (max_i - min_i), 1e-9)
        current_utilization = (
            float(np.max(np.abs((currents - center_i[None, :]) / half_i[None, :])))
            if currents.size
            else math.inf
        )
        runtime_success = bool(
            result.get("success")
            and not str(result.get("failure_reason", "")).strip()
            and not any(bool(row.get("abnormal", False)) for row in result.get("trajectory") or [])
            and all(bool(row.get("solver_success", False)) for row in trace)
            and bool((result.get("anticipatory_damping_summary") or {}).get("streaming_queue_consistent"))
            and not any(bool(row.get("future_measurement_used", True)) for row in trace)
            and bool(summary.get("probe_zero_net"))
            and bool(summary.get("applied_probe_zero_net"))
            and int(summary.get("probe_applied_issue_count", -1))
            == int(summary.get("probe_issue_count", -2))
            and _as_float(summary.get("maximum_applied_component"), math.inf)
            <= float(probe_cfg["maximum_requested_probe_component"]) + 1e-12
            and prefix_exact
            and current_utilization <= float(probe_cfg["maximum_current_utilization"])
        )
        model_pass = bool(
            metrics["velocity_component_rmse_m_per_s"]
            <= float(validation_cfg["maximum_velocity_component_rmse_m_per_s"])
            and metrics["endpoint_late_speed_error_m_per_s"]
            <= float(validation_cfg["maximum_endpoint_late_speed_error_m_per_s"])
            and metrics["final_speed_error_m_per_s"]
            <= float(validation_cfg["maximum_final_speed_error_m_per_s"])
            and metrics["position_rmse_m"]
            <= float(validation_cfg["maximum_position_rmse_m"])
            and metrics["ip_rmse_A"] <= float(validation_cfg["maximum_ip_rmse_A"])
        )
        row = {
            "experiment_id": result["experiment_id"],
            "target_id": target,
            "actual_delay_steps": delay,
            "probe_id": str(spec["r15_probe_id"]),
            "probe_sign": int(spec["r15_probe_sign"]),
            "environment_success": bool(result.get("success")),
            "failure_reason": str(result.get("failure_reason", "")),
            "prefix_exact_before_first_probe_effect": prefix_exact,
            "streaming_queue_consistent": bool(
                (result.get("anticipatory_damping_summary") or {}).get(
                    "streaming_queue_consistent"
                )
            ),
            "no_future_measurement": not any(
                bool(item.get("future_measurement_used", True)) for item in trace
            ),
            "probe_zero_net": bool(summary.get("probe_zero_net")),
            "applied_probe_zero_net": bool(summary.get("applied_probe_zero_net")),
            "requested_probe_net_norm": _as_float(summary.get("requested_probe_net_norm")),
            "applied_probe_net_norm": _as_float(summary.get("applied_probe_net_norm"), math.inf),
            "probe_issue_count": int(summary.get("probe_issue_count", 0)),
            "probe_applied_issue_count": int(summary.get("probe_applied_issue_count", 0)),
            "maximum_requested_probe_component": _as_float(
                summary.get("maximum_requested_component")
            ),
            "maximum_applied_probe_component": _as_float(
                summary.get("maximum_applied_component")
            ),
            "maximum_current_utilization": current_utilization,
            **metrics,
            "runtime_guard_pass": runtime_success,
            "model_prediction_pass": model_pass,
        }
        rows.append(row)
        actual_outputs[
            (target, delay, str(spec["r15_probe_id"]), int(spec["r15_probe_sign"]))
        ] = actual
        all_runtime_success = all_runtime_success and runtime_success

    symmetry_rows: list[dict[str, Any]] = []
    all_symmetry_pass = True
    count = int(layout["state_count"])
    for target in ("nominal", "RZ_p10_m10"):
        for delay in (1, 2):
            baseline_y = _output_vector(
                baselines[(target, delay)],
                start_state=int(model_cfg["output_state_start"]),
                end_state_inclusive=int(model_cfg["output_state_end_inclusive"]),
            )
            for basis in probe_cfg["probe_basis"]:
                probe_id = str(basis["probe_id"])
                plus = actual_outputs[(target, delay, probe_id, 1)]
                minus = actual_outputs[(target, delay, probe_id, -1)]
                asymmetry = plus + minus - 2.0 * baseline_y
                velocity_rmse = float(
                    np.sqrt(np.mean(asymmetry[: 2 * count] ** 2))
                )
                passed = velocity_rmse <= float(
                    validation_cfg[
                        "maximum_central_symmetry_velocity_rmse_m_per_s"
                    ]
                )
                all_symmetry_pass = all_symmetry_pass and passed
                symmetry_rows.append(
                    {
                        "target_id": target,
                        "actual_delay_steps": delay,
                        "probe_id": probe_id,
                        "central_symmetry_velocity_rmse_m_per_s": velocity_rmse,
                        "passed": passed,
                    }
                )
    pass_fraction = float(
        np.mean(
            [
                bool(row["runtime_guard_pass"] and row["model_prediction_pass"])
                for row in rows
            ]
        )
    )
    passed = bool(
        len(rows) == int(probe_cfg["expected_rollouts"])
        and all_runtime_success
        and pass_fraction >= float(validation_cfg["minimum_pass_fraction"])
        and all_symmetry_pass
    )
    write_csv(ctx.paths.probe_validation / "results.csv", rows)
    atomic_write_json(ctx.paths.probe_validation / "results.json", rows)
    write_csv(ctx.paths.probe_validation / "central_symmetry.csv", symmetry_rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "bounded_probe_validation",
        "n_rollouts": len(rows),
        "expected_rollouts": int(probe_cfg["expected_rollouts"]),
        "coverage_complete": len(rows) == int(probe_cfg["expected_rollouts"]),
        "environment_success_count": sum(bool(row["environment_success"]) for row in rows),
        "runtime_guard_pass_fraction": float(
            np.mean([bool(row["runtime_guard_pass"]) for row in rows])
        ),
        "model_prediction_pass_fraction": float(
            np.mean([bool(row["model_prediction_pass"]) for row in rows])
        ),
        "joint_pass_fraction": pass_fraction,
        "maximum_velocity_component_rmse_m_per_s": max(
            row["velocity_component_rmse_m_per_s"] for row in rows
        ),
        "maximum_endpoint_late_speed_error_m_per_s": max(
            row["endpoint_late_speed_error_m_per_s"] for row in rows
        ),
        "maximum_final_speed_error_m_per_s": max(
            row["final_speed_error_m_per_s"] for row in rows
        ),
        "maximum_position_rmse_m": max(row["position_rmse_m"] for row in rows),
        "maximum_ip_rmse_A": max(row["ip_rmse_A"] for row in rows),
        "maximum_central_symmetry_velocity_rmse_m_per_s": max(
            row["central_symmetry_velocity_rmse_m_per_s"] for row in symmetry_rows
        ),
        "formal_tracking_pass_required": False,
        "formal_timing_contract_restored": False,
        "identification_only": True,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.probe_validation / "summary.json", summary)
    _update_state(
        ctx, probe_validation_complete=True, probe_validation_summary=summary
    )
    return summary


def finalize(ctx: Stage41R15Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    model = state.get("local_model_summary") or {}
    probes = state.get("probe_validation_summary") or {}
    passed = bool(
        source.get("passed") and model.get("passed") and probes.get("passed")
    )
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": (
            "STAGE4_1R15_BOUNDED_EARLY_BRAKING_LOCAL_RESPONSE_MODEL_VALIDATED"
            if passed
            else "STAGE4_1R15_BOUNDED_EARLY_BRAKING_LOCAL_RESPONSE_MODEL_INCOMPLETE"
        ),
        "source_stage4_1r14_run": str(ctx.source_stage41r14_run),
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "source_audit_status": "passed" if source.get("passed") else "failed",
        "local_model_status": "passed" if model.get("passed") else (
            "not_run" if not model else "failed"
        ),
        "bounded_probe_validation_status": "passed" if probes.get("passed") else (
            "not_run" if not probes else "failed"
        ),
        "identification_only": True,
        "formal_timing_contract_restored": False,
        "arrival_deadline_expanded": False,
        "true_restart_validation_performed": False,
        "continuous_parameter_change_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "next_if_pass": ctx.cfg["next_if_pass"],
        "next_if_fail": ctx.cfg["next_if_fail"],
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "local_response_model": model,
            "bounded_probe_validation": probes,
        },
    }
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.analysis / "stage4_1r15_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_1r15_summary.json", verdict)
    stop_reason = "" if passed else (
        "bounded_probe_model_validation_failed"
        if probes
        else "source_or_local_model_validation_failed"
    )
    _update_state(
        ctx,
        finished=True,
        stop_reason=stop_reason,
        final_verdict=verdict["verdict"],
    )
    return verdict


def execute(
    ctx: Stage41R15Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    if command not in {"all", "audit", "model", "probes"}:
        raise ValueError("command must be all/audit/model/probes")
    state = read_json(ctx.paths.state)
    if command in {"all", "audit"} and not bool(state.get("source_audit_complete")):
        source = run_source_audit(ctx)
        if not source.get("passed"):
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "model"} and not bool(state.get("local_model_complete")):
        model = run_local_model(ctx)
        if not model.get("passed"):
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "probes"} and not bool(state.get("probe_validation_complete")):
        probes = run_probe_validation(ctx, backend=backend, resume=resume)
        if not probes.get("passed"):
            return finalize(ctx)
    return finalize(ctx)


def self_test(project_dir: Path) -> dict[str, Any]:
    cfg_path = (
        project_dir
        / "configs"
        / "stage4_1r15_bounded_early_braking_local_response_identification_370ms.json"
    )
    cfg = read_json(cfg_path)
    validate_config(cfg)
    probe = cfg["bounded_probe_validation"]
    schedules: list[dict[str, Any]] = []
    for delay in probe["actual_delay_steps"]:
        for basis in probe["probe_basis"]:
            for sign in probe["probe_signs"]:
                schedule = _probe_schedule(
                    first_effect_state=int(probe["baseline_first_affected_state_step"]),
                    actual_delay=int(delay),
                    basis=basis,
                    sign=int(sign),
                    amplitude_by_mode=probe["probe_amplitude_by_mode"],
                )
                net = np.sum(np.stack(list(schedule.values())), axis=0)
                schedules.append(
                    {
                        "delay": int(delay),
                        "probe_id": str(basis["probe_id"]),
                        "sign": int(sign),
                        "issue_steps": sorted(schedule),
                        "zero_net": bool(
                            np.allclose(net, np.zeros(N_MODES), atol=1e-12, rtol=0.0)
                        ),
                        "maximum_component": float(
                            max(np.max(np.abs(value)) for value in schedule.values())
                        ),
                    }
                )
    synthetic_x = np.arange(13 * 12, dtype=float).reshape(13, 12) / 100.0
    synthetic_y = np.column_stack(
        [
            0.5 * synthetic_x[:, 0] - 0.2 * synthetic_x[:, 1],
            synthetic_x[:, 2] + 0.1,
            -0.3 * synthetic_x[:, 3],
        ]
    )
    fitted = _fit_pca_ridge(synthetic_x, synthetic_y, rank=3, ridge_lambda=1e-6)
    predicted = _predict_pca_ridge(fitted, synthetic_x)
    synthetic_rmse = float(np.sqrt(np.mean((predicted - synthetic_y) ** 2)))
    passed = bool(
        len(schedules) == 16
        and all(row["zero_net"] for row in schedules)
        and all(
            row["maximum_component"]
            <= float(probe["maximum_requested_probe_component"]) + 1e-12
            for row in schedules
        )
        and int(probe["expected_rollouts"]) == 32
        and synthetic_rmse < 1e-6
        and cfg["formal_timing_contract"]["normal_slew"]["arrival_deadline_step"] == 25
        and cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] == 27
        and cfg.get("stage4_2r1_was_not_run_or_reused")
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_valid": True,
        "probe_schedule_variants_per_target": len(schedules),
        "expected_true_tsc_probe_rollouts": int(probe["expected_rollouts"]),
        "all_probes_zero_net": all(row["zero_net"] for row in schedules),
        "maximum_probe_component": max(row["maximum_component"] for row in schedules),
        "source_model_group_count": 4,
        "source_samples_per_group": 13,
        "synthetic_model_rmse": synthetic_rmse,
        "formal_timing_contract_immutable": True,
        "formal_timing_contract_restored_by_this_stage": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "passed": passed,
    }


def _default_source(project_dir: Path) -> Path:
    env = os.environ.get("STAGE4_1R15_SOURCE_STAGE4_1R14_RUN")
    if env:
        return Path(env).expanduser().resolve()
    latest = project_dir / "stage4_1r14_runs" / "latest_stage4_1r14_run.txt"
    if latest.is_file():
        return Path(latest.read_text(encoding="utf-8").strip()).expanduser().resolve()
    raise FileNotFoundError(
        "set STAGE4_1R15_SOURCE_STAGE4_1R14_RUN or provide --source-stage4-1r14-run"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R15 bounded early-braking local-response identification"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "configs"
        / "stage4_1r15_bounded_early_braking_local_response_identification_370ms.json",
    )
    parser.add_argument("--source-stage4-1r14-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command",
        choices=["all", "audit", "model", "probes"],
        default=os.environ.get("STAGE4_1R15_COMMAND", "all"),
    )
    parser.add_argument(
        "--backend",
        choices=["ray", "serial"],
        default=os.environ.get("STAGE4_1R15_BACKEND", "ray"),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    project_dir = args.config.expanduser().resolve().parents[1]
    if args.self_test:
        print(json.dumps(self_test(project_dir), indent=2, sort_keys=True))
        return
    source = args.source_stage4_1r14_run or _default_source(project_dir)
    ctx = load_stage41r15_config(
        args.config,
        source_stage41r14_run=source,
        run_dir_override=args.run_dir,
    )
    payload = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(_json_safe(payload), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
