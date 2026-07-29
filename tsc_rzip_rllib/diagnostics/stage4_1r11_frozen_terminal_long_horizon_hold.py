"""Stage4.1R11 frozen-policy long-horizon hold validation.

R10 closed a finite 750 ms clean digital-twin envelope after causally replacing
only the main-MPC commands that were still unapplied at the 350 ms transition.
That is an important queue-boundary result, but it is not yet a long-horizon
invariant hold: several R10 cases ended close to the 30 mm box boundary and the
terminal controller still issued non-zero current-increment commands.

R11 therefore freezes the single R10-selected policy and all upstream
MPC/observer/library/Jacobian/calibration semantics.  No policy search, endpoint
search, target reuse for tuning, gate relaxation, or online handover is allowed.
Every one of the two targets and nine static delay/slew pairs is extended from
the exact R10 750 ms prefix to a 2000 ms causal hold.  The hold is evaluated from
a fixed 650 ms start, inherited from the latest R10 admissible arrival, so the
long run cannot select a more favorable endpoint after seeing the result.

This remains a finite, static, clean-measurement digital-twin test.  It is not
true restart validation, hidden vessel/eddy-history validation, plant-model
robustness, continuous actuator change, noisy terminal sensing, or deployment
qualification.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import resource
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage4_1r3_control_aware_robustness as r3
from . import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8
from . import stage4_1r9_terminal_template_mpc_feedback_hold as r9
from . import stage4_1r10_queue_preview_terminal_transition_hold as r10
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r10.atomic_write_json
atomic_write_json_gz = r10.atomic_write_json_gz
read_json = r10.read_json
read_json_gz = r10.read_json_gz
utc_timestamp = r10.utc_timestamp
write_csv = r10.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R11"
CONTROLLER_REVISION = "frozen_queue_preview_terminal_long_horizon_hold_v11"
EXPECTED_SOURCE_REVISION = r10.CONTROLLER_REVISION
PACKAGE_REVISION = "r11_frozen_long_hold_v1"
MAIN_CONTROL_STEPS = 35
SOURCE_HORIZON_STEPS = 75
N_MODES = 3


def _json_safe(value: Any) -> Any:
    return r10._json_safe(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    return r10._as_bool(value, default)


def _as_int(value: Any, default: int = 0) -> int:
    return r10._as_int(value, default)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r10._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r10._sha256_file(path)


def _result_complete(path: Path) -> bool:
    return r10._result_complete(path)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "s41r11_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape:
        return math.inf
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def _array_digest(array: np.ndarray, prefix: str) -> str:
    return r10._array_digest(np.asarray(array), prefix)


@dataclass(frozen=True)
class Stage41R11Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    oracle_long_hold: Path
    calibrated_long_hold: Path
    restart_audit: Path
    analysis: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R11Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r11_source_reference",
            source_audit=run_dir / "stage4_1r11_source_audit",
            oracle_long_hold=run_dir / "stage4_1r11_oracle_long_hold",
            calibrated_long_hold=run_dir / "stage4_1r11_calibrated_long_hold",
            restart_audit=run_dir / "stage4_1r11_restart_audit",
            analysis=run_dir / "stage4_1r11_analysis",
            state=run_dir / "stage4_1r11_state.json",
            manifest=run_dir / "stage4_1r11_manifest.json",
        )


@dataclass
class Stage41R11Context:
    cfg: dict[str, Any]
    paths: Stage41R11Paths
    project_dir: Path
    source_stage41r10_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    source_stage41r9_run: Path
    source_stage41r8_run: Path
    r10_ctx: r10.Stage41R10Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r10_manifest.json",
        source / "stage4_1r10_state.json",
        source / "stage4_1r10_config.resolved.json",
        source / "stage4_1r10_analysis" / "stage4_1r10_verdict.json",
        source / "stage4_1r10_analysis" / "stage4_1r10_summary.json",
        source / "stage4_1r10_oracle_development" / "summary.json",
        source / "stage4_1r10_oracle_development" / "results.json",
        source / "stage4_1r10_oracle_holdout" / "summary.json",
        source / "stage4_1r10_oracle_holdout" / "results.json",
        source / "stage4_1r10_calibrated_confirmation" / "summary.json",
        source / "stage4_1r10_calibrated_confirmation" / "results.json",
    ]
    for phase in (
        "stage4_1r10_oracle_development",
        "stage4_1r10_oracle_holdout",
        "stage4_1r10_calibrated_confirmation",
    ):
        required.extend(sorted((source / phase / "raw").glob("*.json.gz")))
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R10 source file missing: {path}")
        size = path.stat().st_size
        total += size
        rows.append(
            {
                "relative_path": str(path.relative_to(source)),
                "size_bytes": size,
                "sha256": _sha256_file(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "schema_version": 1,
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
    }


def _resolve_recorded_run(
    project_dir: Path, recorded: str, run_root_name: str
) -> Path:
    return r10._resolve_recorded_run(project_dir, recorded, run_root_name)


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R11 controller_revision mismatch")
    source = cfg["source_requirement"]
    if source.get("required_stage") != "Stage4.1R10":
        raise ValueError("R11 source stage must remain Stage4.1R10")
    if source.get("required_controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("R11 source controller revision mismatch")
    gate = cfg["gate"]
    if not math.isclose(float(gate["position_box_max_m"]), 0.03, abs_tol=1e-15):
        raise ValueError("R11 may not weaken the 30 mm position gate")
    if not math.isclose(float(gate["velocity_max_m_per_s"]), 0.1, abs_tol=1e-15):
        raise ValueError("R11 may not weaken the 0.1 m/s velocity gate")
    hold = cfg["long_hold"]
    if int(hold["main_control_steps"]) != MAIN_CONTROL_STEPS:
        raise ValueError("R11 main-control boundary must remain 35 steps")
    if int(hold["source_horizon_steps"]) != SOURCE_HORIZON_STEPS:
        raise ValueError("R11 source prefix must remain 75 steps")
    horizon = int(hold["horizon_steps"])
    tail = int(hold["tail_feedback_steps"])
    if horizon != MAIN_CONTROL_STEPS + tail or horizon != 200:
        raise ValueError("R11 horizon must be 35 + 165 = 200 steps")
    if int(hold["uniform_hold_start_step"]) != 65:
        raise ValueError("R11 fixed hold start must remain 650 ms")
    if int(hold["require_exact_source_prefix_through_step"]) != SOURCE_HORIZON_STEPS:
        raise ValueError("R11 must preserve the complete R10 750 ms prefix")
    if [int(x) for x in hold["actual_delay_steps"]] != [0, 1, 2]:
        raise ValueError("R11 delay bank must remain [0,1,2]")
    if [float(x) for x in hold["actual_slew_scales"]] != [0.9, 1.0, 1.1]:
        raise ValueError("R11 slew bank must remain [0.9,1.0,1.1]")
    targets = list(hold["targets"])
    if [str(x["target_id"]) for x in targets] != ["nominal", "RZ_p10_m10"]:
        raise ValueError("R11 targets must remain the frozen R10 development/holdout pair")
    policy = hold["selected_policy"]
    if str(policy["policy_id"]) != str(source["require_selected_policy"]):
        raise ValueError("R11 may not change the R10-selected policy")
    expected_policy = {
        "template_step": 28,
        "controller_scale": 0.5,
        "velocity_measurement_gain": 1.5,
        "position_measurement_gain": 1.25,
    }
    for key, expected in expected_policy.items():
        if not math.isclose(float(policy[key]), float(expected), abs_tol=1e-15):
            raise ValueError(f"R11 frozen policy field changed: {key}")
    if not bool(hold.get("no_policy_retuning_allowed")):
        raise ValueError("R11 must prohibit policy retuning")
    if not bool(hold.get("no_new_arrival_search_allowed")):
        raise ValueError("R11 must prohibit new endpoint search")
    if cfg["calibrated_confirmation"].get("online_handover_enabled"):
        raise ValueError("R11 calibrated path must not use online handover")
    if not bool(cfg.get("finite_test_envelope_only", False)):
        raise ValueError("R11 must remain explicitly finite-envelope only")


def _validate_source_stage41r10(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R10 source file missing: {path}")
    manifest = read_json(source / "stage4_1r10_manifest.json")
    state = read_json(source / "stage4_1r10_state.json")
    source_cfg = read_json(source / "stage4_1r10_config.resolved.json")
    verdict = read_json(source / "stage4_1r10_analysis" / "stage4_1r10_verdict.json")
    requirement = cfg["source_requirement"]
    if manifest.get("stage") != requirement["required_stage"]:
        raise ValueError("source Stage4.1R10 manifest stage mismatch")
    if manifest.get("controller_revision") != requirement["required_controller_revision"]:
        raise ValueError("source Stage4.1R10 controller revision mismatch")
    if source_cfg.get("controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R10 resolved config revision mismatch")
    if bool(requirement.get("require_finished", True)) and not bool(state.get("finished")):
        raise ValueError("source Stage4.1R10 is not finished")
    if str(state.get("stop_reason", "")) != str(requirement.get("require_stop_reason", "")):
        raise ValueError("source Stage4.1R10 stop_reason mismatch")
    if bool(requirement.get("require_primary_pass", True)) and not bool(verdict.get("primary_pass")):
        raise ValueError("source Stage4.1R10 primary verdict did not pass")
    selected = str(verdict.get("selected_terminal_policy") or "")
    if selected != str(requirement["require_selected_policy"]):
        raise ValueError(f"source R10 selected policy mismatch: {selected}")
    counts = {
        "stage4_1r10_oracle_development": int(requirement["require_oracle_development_raw_count"]),
        "stage4_1r10_oracle_holdout": int(requirement["require_oracle_holdout_raw_count"]),
        "stage4_1r10_calibrated_confirmation": int(requirement["require_calibrated_confirmation_raw_count"]),
    }
    for phase, expected in counts.items():
        actual = len(list((source / phase / "raw").glob("*.json.gz")))
        if actual != expected:
            raise ValueError(f"source R10 {phase} raw count mismatch: {actual} != {expected}")
    confirmation = read_json(source / "stage4_1r10_calibrated_confirmation" / "summary.json")
    if _as_float(confirmation.get("exact_trace_equivalence_fraction"), 0.0) < float(
        requirement["require_calibrated_exact_trace_fraction"]
    ):
        raise ValueError("source R10 calibrated exact trace fraction is insufficient")
    return manifest, state, source_cfg, verdict


def load_stage41r11_config(
    config_path: Path,
    *,
    source_stage41r10_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R11Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r10_run = source_stage41r10_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r10(
        source_stage41r10_run, cfg
    )
    source_stage41r9_run = _resolve_recorded_run(
        project_dir,
        str(manifest["source_stage4_1r9_run"]),
        "stage4_1r9_runs",
    )
    source_stage41r8_run = _resolve_recorded_run(
        project_dir,
        str(manifest["source_stage4_1r8_run"]),
        "stage4_1r8_runs",
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r11_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r11')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    paths = Stage41R11Paths.from_run_dir(run_dir)

    r10_config_path = (
        project_dir
        / "configs"
        / "stage4_1r10_queue_preview_terminal_transition_hold_750ms.json"
    )
    if not r10_config_path.is_file():
        raise FileNotFoundError(f"packaged R10 dependency config missing: {r10_config_path}")
    r10_ctx = r10.load_stage41r10_config(
        r10_config_path,
        source_stage41r9_run=source_stage41r9_run,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    base34 = r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R11_TSC_WORKSPACE_ROOT",
                storage["tsc_workspace_root"],
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get("STAGE4_1R11_TSC_RUN_ROOT", storage["tsc_run_root"])
        )
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    base34.env_cfg = env_cfg
    fingerprint = _source_inventory(source_stage41r10_run)
    return Stage41R11Context(
        cfg=cfg,
        paths=paths,
        project_dir=project_dir,
        source_stage41r10_run=source_stage41r10_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        source_stage41r9_run=source_stage41r9_run,
        source_stage41r8_run=source_stage41r8_run,
        r10_ctx=r10_ctx,
        source_fingerprint=fingerprint,
    )


def _initial_state(ctx: Stage41R11Context) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "oracle_long_hold_complete": False,
        "calibrated_long_hold_complete": False,
        "restart_audit_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R11Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R11Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.oracle_long_hold,
        ctx.paths.calibrated_long_hold,
        ctx.paths.restart_audit,
        ctx.paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.is_file():
        existing = read_json(ctx.paths.manifest)
        if existing.get("source_fingerprint", {}).get("digest") != ctx.source_fingerprint["digest"]:
            raise ValueError("R11 resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R11 resume controller revision mismatch")
    elif resume:
        raise FileNotFoundError("R11 resume requested but manifest is missing")

    atomic_write_json(ctx.paths.run_dir / "stage4_1r11_config.resolved.json", ctx.cfg)
    for name, payload in (
        ("stage4_1r10_manifest.json", ctx.source_manifest),
        ("stage4_1r10_state.json", ctx.source_state),
        ("stage4_1r10_config.resolved.json", ctx.source_cfg),
        ("stage4_1r10_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r10_run": str(ctx.source_stage41r10_run),
        "source_stage4_1r9_run": str(ctx.source_stage41r9_run),
        "source_stage4_1r8_run": str(ctx.source_stage41r8_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": int(
            os.environ.get("STAGE4_1R11_WORKERS", ctx.cfg["parallel"]["n_workers"])
        ),
        "selected_policy_frozen": ctx.cfg["long_hold"]["selected_policy"],
        "source_prefix_through_750ms_must_be_exact": True,
        "fixed_hold_start_step": int(ctx.cfg["long_hold"]["uniform_hold_start_step"]),
        "new_arrival_search_allowed": False,
        "policy_retuning_allowed": False,
        "finite_test_envelope_only": True,
        "true_restart_validation_performed": False,
        "plant_parameter_robustness_validated": False,
        "terminal_measurement_noise_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _phase_raw(source: Path, phase: str) -> list[dict[str, Any]]:
    return [read_json_gz(path) for path in sorted((source / phase / "raw").glob("*.json.gz"))]


def _source_selected_oracle_raw(ctx: Stage41R11Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    selected = str(ctx.cfg["long_hold"]["selected_policy"]["policy_id"])
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for phase in ("stage4_1r10_oracle_development", "stage4_1r10_oracle_holdout"):
        for result in _phase_raw(ctx.source_stage41r10_run, phase):
            spec = result.get("spec") or {}
            if str(spec.get("terminal_policy_id")) != selected:
                continue
            key = (
                str(spec["target_id"]),
                int(spec["action_delay_steps"]),
                float(spec["slew_scale"]),
            )
            if key in output:
                raise ValueError(f"duplicate source R10 selected Oracle case: {key}")
            output[key] = result
    return output


def _source_result_rows(ctx: Stage41R11Context) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    return (
        read_json(ctx.source_stage41r10_run / "stage4_1r10_oracle_development" / "results.json"),
        read_json(ctx.source_stage41r10_run / "stage4_1r10_oracle_holdout" / "results.json"),
        read_json(ctx.source_stage41r10_run / "stage4_1r10_calibrated_confirmation" / "results.json"),
    )


def _all_finite_result(result: Mapping[str, Any]) -> bool:
    for row in result.get("trajectory") or []:
        values = [row.get("R"), row.get("Z"), row.get("Ip")]
        values.extend(row.get("currents_a_tsc") or [])
        for value in values:
            try:
                if not math.isfinite(float(value)):
                    return False
            except (TypeError, ValueError):
                return False
    return True


def _speed(y: np.ndarray, dt_s: float) -> np.ndarray:
    positions = np.asarray(y, dtype=float)[:, :2]
    velocity = np.zeros_like(positions)
    if len(positions) > 1:
        velocity[1:] = np.diff(positions, axis=0) / max(float(dt_s), 1e-12)
    return np.linalg.norm(velocity, axis=1)


def _linear_slope(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return np.zeros(values.shape[1:] or (), dtype=float)
    x = np.arange(len(values), dtype=float)
    if values.ndim == 1:
        return np.asarray(np.polyfit(x, values, 1)[0])
    return np.asarray([np.polyfit(x, values[:, i], 1)[0] for i in range(values.shape[1])])


def run_source_audit(ctx: Stage41R11Context) -> dict[str, Any]:
    dev_raw = _phase_raw(ctx.source_stage41r10_run, "stage4_1r10_oracle_development")
    hold_raw = _phase_raw(ctx.source_stage41r10_run, "stage4_1r10_oracle_holdout")
    conf_raw = _phase_raw(ctx.source_stage41r10_run, "stage4_1r10_calibrated_confirmation")
    dev_rows, hold_rows, conf_rows = _source_result_rows(ctx)
    all_raw = dev_raw + hold_raw + conf_raw
    expected_total = (
        int(ctx.cfg["source_requirement"]["require_oracle_development_raw_count"])
        + int(ctx.cfg["source_requirement"]["require_oracle_holdout_raw_count"])
        + int(ctx.cfg["source_requirement"]["require_calibrated_confirmation_raw_count"])
    )
    ids = [str(row.get("experiment_id")) for row in all_raw]
    environment_success = sum(bool(row.get("success")) for row in all_raw)
    failure_reason_count = sum(bool(str(row.get("failure_reason", "")).strip()) for row in all_raw)
    abnormal_count = sum(
        bool(state.get("abnormal", False))
        for result in all_raw
        for state in (result.get("trajectory") or [])
    )
    nonfinite_count = sum(not _all_finite_result(result) for result in all_raw)

    policy_rows: list[dict[str, Any]] = []
    for policy_id in sorted({str(row["policy_id"]) for row in dev_rows}):
        subset = [row for row in dev_rows if str(row["policy_id"]) == policy_id]
        pure = sum(bool(row.get("stage3_4_target_tracking_pass")) for row in subset) / max(len(subset), 1)
        composite = sum(bool(row.get("r10_target_tracking_pass")) for row in subset) / max(len(subset), 1)
        policy_rows.append(
            {
                "policy_id": policy_id,
                "n_rollouts": len(subset),
                "pure_stage3_tracking_fraction": pure,
                "r10_composite_pass_fraction": composite,
                "summary_tracking_fraction_is_composite": True,
                "minimum_stage3_tracking_margin": min(
                    (_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in subset),
                    default=-1e12,
                ),
                "minimum_r10_combined_margin": min(
                    (_as_float(row.get("r10_combined_minimum_signed_margin"), -1e12) for row in subset),
                    default=-1e12,
                ),
            }
        )

    selected = str(ctx.cfg["long_hold"]["selected_policy"]["policy_id"])
    selected_dev = [row for row in dev_rows if str(row.get("policy_id")) == selected]
    selected_hold = [row for row in hold_rows if str(row.get("policy_id")) == selected]
    selected_rows = selected_dev + selected_hold
    baseline_id = "qp28_c0p50_v1p50_p1p00_baseline"
    baseline_rows = [row for row in dev_rows if str(row.get("policy_id")) == baseline_id]
    selected_min = min(
        (_as_float(row.get("r10_combined_minimum_signed_margin"), -1e12) for row in selected_dev),
        default=-1e12,
    )
    baseline_min = min(
        (_as_float(row.get("r10_combined_minimum_signed_margin"), -1e12) for row in baseline_rows),
        default=-1e12,
    )

    selected_raw = _source_selected_oracle_raw(ctx)
    tail_rows: list[dict[str, Any]] = []
    for key, result in sorted(selected_raw.items()):
        trajectory = list(result.get("trajectory") or [])
        terminal = list(result.get("terminal_feedback_trace") or [])
        target_id, delay, slew = key
        target_cfg = next(
            row for row in ctx.cfg["long_hold"]["targets"] if str(row["target_id"]) == target_id
        )
        base_target = ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg["target"]
        target = np.asarray(
            [
                float(base_target["R"]) + float(target_cfg.get("R_offset_m", 0.0)),
                float(base_target["Z"]) + float(target_cfg.get("Z_offset_m", 0.0)),
                float(base_target["Ip"]) + float(target_cfg.get("Ip_offset_A", 0.0)),
            ]
        )
        y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
        speed = _speed(y, float(ctx.cfg["long_hold"]["dt_s"]))
        issued = np.asarray(
            [row.get("issued_desired_physical_mode_coefficients", [0.0] * N_MODES) for row in terminal[-10:]],
            dtype=float,
        )
        currents = np.asarray([row["currents_after_A"] for row in terminal], dtype=float)
        tail_rows.append(
            {
                "target_id": target_id,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "source_terminal_box_error_m": float(np.max(np.abs(y[-1, :2] - target[:2]))),
                "source_terminal_speed_m_per_s": float(speed[-1]),
                "source_last10_speed_rms_m_per_s": float(np.sqrt(np.mean(speed[-10:] ** 2))),
                "source_last10_speed_linear_slope_per_step": float(_linear_slope(speed[-10:])),
                "source_last10_issued_desired_rms": float(np.sqrt(np.mean(issued**2))) if issued.size else 0.0,
                "source_last10_issued_mean_norm": float(np.linalg.norm(np.mean(issued, axis=0))) if issued.size else 0.0,
                "source_last10_any_mode_at_0p1_fraction": float(
                    np.mean(np.any(np.isclose(np.abs(issued), 0.1, atol=1e-8), axis=1))
                ) if issued.size else 0.0,
                "source_last10_current_net_change_norm_A": float(np.linalg.norm(currents[-1] - currents[-11])) if len(currents) >= 11 else 0.0,
                "source_max_final_pending_desired_norm": _as_float(
                    (result.get("terminal_feedback_summary") or {}).get(
                        "maximum_final_pending_desired_physical_norm"
                    ),
                    0.0,
                ),
                "source_vessel_current_abs_sum_final_A": _as_float(
                    trajectory[-1].get("vessel_current_abs_sum_a"), 0.0
                ),
            }
        )

    confirmation_summary = read_json(
        ctx.source_stage41r10_run
        / "stage4_1r10_calibrated_confirmation"
        / "summary.json"
    )
    passed = bool(
        len(all_raw) == expected_total
        and len(set(ids)) == expected_total
        and environment_success == expected_total
        and failure_reason_count == 0
        and abnormal_count == 0
        and nonfinite_count == 0
        and len(selected_dev) == 9
        and len(selected_hold) == 9
        and all(bool(row.get("r10_target_tracking_pass")) for row in selected_rows)
        and len(conf_rows) == 18
        and all(bool(row.get("r10_target_tracking_pass")) for row in conf_rows)
        and math.isclose(
            _as_float(confirmation_summary.get("exact_trace_equivalence_fraction"), 0.0),
            1.0,
            abs_tol=1e-15,
        )
        and len(selected_raw) == 18
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r10_run": str(ctx.source_stage41r10_run),
        "raw_rollouts": len(all_raw),
        "expected_raw_rollouts": expected_total,
        "unique_experiment_ids": len(set(ids)),
        "environment_success_count": environment_success,
        "failure_reason_count": failure_reason_count,
        "abnormal_state_count": abnormal_count,
        "nonfinite_rollout_count": nonfinite_count,
        "selected_policy_id": selected,
        "selected_policy_development_rollouts": len(selected_dev),
        "selected_policy_holdout_rollouts": len(selected_hold),
        "selected_policy_all_18_composite_pass": all(
            bool(row.get("r10_target_tracking_pass")) for row in selected_rows
        ),
        "selected_policy_minimum_development_combined_margin": selected_min,
        "baseline_minimum_development_combined_margin": baseline_min,
        "selected_minus_baseline_minimum_margin": selected_min - baseline_min,
        "selected_policy_minimum_holdout_combined_margin": min(
            (_as_float(row.get("r10_combined_minimum_signed_margin"), -1e12) for row in selected_hold),
            default=-1e12,
        ),
        "all_six_policies_pure_stage3_tracking_fraction": min(
            (row["pure_stage3_tracking_fraction"] for row in policy_rows), default=0.0
        ),
        "r10_summary_tracking_fraction_is_composite_not_pure_tracking": any(
            not math.isclose(
                row["pure_stage3_tracking_fraction"],
                row["r10_composite_pass_fraction"],
                abs_tol=1e-15,
            )
            for row in policy_rows
        ),
        "calibrated_exact_trace_equivalence_fraction": _as_float(
            confirmation_summary.get("exact_trace_equivalence_fraction"), 0.0
        ),
        "source_terminal_nonzero_control_diagnostic": {
            "maximum_final_pending_desired_norm": max(
                (row["source_max_final_pending_desired_norm"] for row in tail_rows),
                default=0.0,
            ),
            "maximum_last10_issued_mean_norm": max(
                (row["source_last10_issued_mean_norm"] for row in tail_rows),
                default=0.0,
            ),
            "maximum_last10_current_net_change_norm_A": max(
                (row["source_last10_current_net_change_norm_A"] for row in tail_rows),
                default=0.0,
            ),
            "positive_last10_speed_slope_case_count": sum(
                row["source_last10_speed_linear_slope_per_step"] > 0.0 for row in tail_rows
            ),
            "interpretation": (
                "R10 is a valid finite 750 ms closure, but the terminal command "
                "and current increments are not uniformly near zero. R11 must test "
                "the frozen controller over a much longer horizon before restart "
                "or plant-mismatch claims."
            ),
        },
        "passed": passed,
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    write_csv(ctx.paths.source_audit / "policy_semantics.csv", policy_rows)
    write_csv(ctx.paths.source_audit / "selected_terminal_diagnostics.csv", tail_rows)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


class LocalStage41R11Worker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.inner = r10.LocalStage41R10Worker(
            payload, library, bundle, worker_id, selector_cfg
        )

    def close(self) -> None:
        self.inner.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        inner_spec = copy.deepcopy(spec)
        inner_spec["controller_revision"] = r10.CONTROLLER_REVISION
        result = self.inner.evaluate(inner_spec)
        result["spec"] = copy.deepcopy(spec)
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r11_controller_revision"] = CONTROLLER_REVISION
        result["frozen_source_controller_revision"] = r10.CONTROLLER_REVISION
        return _json_safe(result)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage41R11Actor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalStage41R11Worker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R11Actor
    return _RAY_ACTOR


def materialize_variant(
    ctx: Stage41R11Context, *, slew_scale: float
) -> tuple[str, dict[str, Any]]:
    return r10.materialize_variant(
        ctx.r10_ctx,
        slew_scale=float(slew_scale),
        horizon_steps=int(ctx.cfg["long_hold"]["horizon_steps"]),
    )


def evaluate_specs(
    ctx: Stage41R11Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = (
        ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.variants
    )
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        variant = str(spec["environment_variant"])
        if variant not in variants:
            raise KeyError(f"unmaterialized R11 environment variant {variant}")
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, rows in by_variant.items():
        pending = [
            row
            for row in rows
            if not (
                resume
                and _result_complete(output_dir / f"{row['experiment_id']}.json.gz")
            )
        ]
        if pending:
            pending_by_variant[variant] = pending
    library = (
        ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_library
    )
    bundle = (
        ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle
    )
    selector_cfg = ctx.r10_ctx.r9_ctx.r8_ctx.cfg["batch_selector"]
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalStage41R11Worker(
                variants[variant],
                library,
                bundle,
                f"stage41r11_{variant}_serial",
                selector_cfg,
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz",
                        worker.evaluate(spec),
                    )
                    print(
                        f"[Stage4.1R11 {variant}] {index}/{len(pending)}",
                        flush=True,
                    )
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(
            os.environ.get("STAGE4_1R11_WORKERS", ctx.cfg["parallel"]["n_workers"])
        )
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get(
                "RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")
            )
            or None,
            log_prefix="[Stage4.1R11 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()},
            plan.actor_count,
        )
        print(
            "[Stage4.1R11 mixed-variant] actor_allocation="
            + json.dumps(allocation, sort_keys=True, separators=(",", ":")),
            flush=True,
        )
        Actor = _ray_actor_class()
        actors_by_variant: dict[str, list[Any]] = {}
        all_actors: list[Any] = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(
                    variants[variant],
                    library,
                    bundle,
                    f"stage41r11_{variant}_{index:03d}",
                    selector_cfg,
                )
                for index in range(count)
            ]
            actors_by_variant[variant] = actors
            all_actors.extend(actors)
        refs: dict[Any, dict[str, Any]] = {}
        for variant, pending in pending_by_variant.items():
            actors = actors_by_variant[variant]
            for index, spec in enumerate(pending):
                refs[actors[index % len(actors)].evaluate.remote(spec)] = spec
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(
                        f"[Stage4.1R11 mixed-variant] waiting {done}/{total_pending}",
                        flush=True,
                    )
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": SCHEMA_VERSION,
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                        }
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(
                            f"[Stage4.1R11 mixed-variant] {done}/{total_pending}",
                            flush=True,
                        )
        finally:
            s2._close_ray_actors(
                all_actors,
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


def _make_spec(
    *,
    phase: str,
    scenario: str,
    category: str,
    target: Mapping[str, Any],
    controller_scale: float,
    environment_variant: str,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    identity = {
        "revision": CONTROLLER_REVISION,
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target": dict(target),
        "controller_scale": controller_scale,
        "environment_variant": environment_variant,
        "extra": dict(extra),
    }
    return {
        "kind": "stage4_1r11_frozen_terminal_long_horizon_hold",
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": _scenario_digest(identity),
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target_id": str(target["target_id"]),
        "target_R_offset_m": float(target.get("R_offset_m", 0.0)),
        "target_Z_offset_m": float(target.get("Z_offset_m", 0.0)),
        "target_Ip_offset_A": float(target.get("Ip_offset_A", 0.0)),
        "controller_scale": float(controller_scale),
        "environment_variant": environment_variant,
        **copy.deepcopy(dict(extra)),
    }


def _long_hold_extra(
    ctx: Stage41R11Context,
    *,
    actual_delay: int,
    actual_slew: float,
    modeled_delay: int,
    modeled_slew: float,
    calibration_token: str | None,
    trusted: bool,
    controller_variant: str,
) -> dict[str, Any]:
    hold = ctx.cfg["long_hold"]
    policy = hold["selected_policy"]
    generic_policy = {
        "horizon_steps": int(hold["horizon_steps"]),
        "tail_steps": int(hold["tail_feedback_steps"]),
        "tail_policy": "queue_preview_then_streaming_terminal_feedback",
        "policy_id": str(policy["policy_id"]),
    }
    extra = r8._main_extra(
        ctx.r10_ctx.r9_ctx.r8_ctx,
        actual_delay=int(actual_delay),
        actual_slew=float(actual_slew),
        modeled_delay=int(modeled_delay),
        modeled_slew=float(modeled_slew),
        policy=generic_policy,
        variant=controller_variant,
        monitor_enabled=False,
        calibration_token=calibration_token,
        trusted=trusted,
    )
    extra.update(
        {
            "horizon_steps": int(hold["horizon_steps"]),
            "tail_feedback_steps": int(hold["tail_feedback_steps"]),
            "tail_steps": int(hold["tail_feedback_steps"]),
            "tail_policy": "queue_preview_then_streaming_terminal_feedback",
            "terminal_policy_id": str(policy["policy_id"]),
            "terminal_template_step": int(policy["template_step"]),
            "terminal_controller_scale": float(policy["controller_scale"]),
            "terminal_velocity_measurement_gain": float(
                policy["velocity_measurement_gain"]
            ),
            "terminal_position_measurement_gain": float(
                policy["position_measurement_gain"]
            ),
            "terminal_ip_measurement_gain": float(policy["ip_measurement_gain"]),
            "terminal_controller_model_scale": float(
                policy["controller_model_scale"]
            ),
            "terminal_integral_mode": str(policy["integral_mode"]),
            "terminal_nominal_physical_mode": str(
                policy["terminal_nominal_physical_mode"]
            ),
            "terminal_initial_previous_correction": str(
                policy["initial_previous_correction"]
            ),
            "transition_preview_replaces_only_unapplied_issue_slots": True,
            "transition_preview_uses_only_original_issue_time_information": True,
            "r11_frozen_policy_no_retuning": True,
            "r11_fixed_hold_start_step": int(hold["uniform_hold_start_step"]),
            "r11_source_prefix_steps": int(hold["source_horizon_steps"]),
        }
    )
    return extra


def _source_scale(ctx: Stage41R11Context) -> float:
    return float(
        ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )


def build_oracle_specs(ctx: Stage41R11Context) -> list[dict[str, Any]]:
    hold = ctx.cfg["long_hold"]
    specs: list[dict[str, Any]] = []
    for slew in hold["actual_slew_scales"]:
        variant, _ = materialize_variant(ctx, slew_scale=float(slew))
        for delay in hold["actual_delay_steps"]:
            for target in hold["targets"]:
                extra = _long_hold_extra(
                    ctx,
                    actual_delay=int(delay),
                    actual_slew=float(slew),
                    modeled_delay=int(delay),
                    modeled_slew=float(slew),
                    calibration_token=None,
                    trusted=True,
                    controller_variant="r11_oracle_long_hold",
                )
                specs.append(
                    _make_spec(
                        phase="oracle_long_hold",
                        scenario=f"{hold['selected_policy']['policy_id']}__{target['target_id']}__d{delay}__s{float(slew):.1f}",
                        category="oracle_long_hold",
                        target=target,
                        controller_scale=_source_scale(ctx),
                        environment_variant=variant,
                        extra=extra,
                    )
                )
    return specs


def _trusted_tokens(ctx: Stage41R11Context) -> dict[tuple[int, float], dict[str, Any]]:
    tokens = r9.source_calibration_tokens(ctx.r10_ctx.r9_ctx)
    expected = {(d, s) for d in (0, 1, 2) for s in (0.9, 1.0, 1.1)}
    if set(tokens) != expected:
        raise ValueError("R11 source calibration token coverage mismatch")
    for key, row in tokens.items():
        if not bool(row.get("success")):
            raise ValueError(f"R11 calibration token environment failure: {key}")
        if not bool(row.get("batch_trusted")):
            raise ValueError(f"R11 calibration token is not trusted: {key}")
        if not bool(row.get("batch_trusted_correct")):
            raise ValueError(f"R11 calibration token is not trusted-correct: {key}")
        if bool(row.get("batch_wrong_accept")):
            raise ValueError(f"R11 calibration token is a wrong accept: {key}")
        if int(row.get("batch_selected_delay_steps", -999)) != key[0]:
            raise ValueError(f"R11 token delay mismatch: {key}")
        if not math.isclose(
            _as_float(row.get("batch_selected_slew_scale"), math.nan),
            key[1],
            abs_tol=1e-12,
        ):
            raise ValueError(f"R11 token slew mismatch: {key}")
    return tokens


def build_calibrated_specs(ctx: Stage41R11Context) -> list[dict[str, Any]]:
    if not bool(
        (read_json(ctx.paths.state).get("oracle_long_hold_summary") or {}).get("passed")
    ):
        return []
    hold = ctx.cfg["long_hold"]
    tokens = _trusted_tokens(ctx)
    specs: list[dict[str, Any]] = []
    for slew in hold["actual_slew_scales"]:
        variant, _ = materialize_variant(ctx, slew_scale=float(slew))
        for delay in hold["actual_delay_steps"]:
            token = tokens[(int(delay), float(slew))]
            for target in hold["targets"]:
                extra = _long_hold_extra(
                    ctx,
                    actual_delay=int(delay),
                    actual_slew=float(slew),
                    modeled_delay=int(token["batch_selected_delay_steps"]),
                    modeled_slew=float(token["batch_selected_slew_scale"]),
                    calibration_token=str(token["experiment_id"]),
                    trusted=True,
                    controller_variant="r11_calibrated_long_hold",
                )
                specs.append(
                    _make_spec(
                        phase="calibrated_long_hold",
                        scenario=f"{hold['selected_policy']['policy_id']}__{target['target_id']}__d{delay}__s{float(slew):.1f}",
                        category="calibrated_long_hold",
                        target=target,
                        controller_scale=_source_scale(ctx),
                        environment_variant=variant,
                        extra=extra,
                    )
                )
    return specs


def _physics_array(result: Mapping[str, Any], *, count: int | None = None) -> np.ndarray:
    rows = list(result.get("trajectory") or [])
    if count is not None:
        rows = rows[:count]
    return np.asarray(
        [
            [
                row["R"],
                row["Z"],
                row["Ip"],
                row.get("vessel_current_total_a", 0.0),
                row.get("vessel_current_abs_sum_a", 0.0),
                row.get("vessel_current_rms_a", 0.0),
                row.get("vessel_current_max_abs_a", 0.0),
                *(row.get("currents_a_tsc") or []),
            ]
            for row in rows
        ],
        dtype=float,
    )


def _trace_array(
    result: Mapping[str, Any],
    trace_name: str,
    fields: Sequence[str],
    *,
    count: int | None = None,
) -> np.ndarray:
    rows = list(result.get(trace_name) or [])
    if count is not None:
        rows = rows[:count]
    flattened: list[list[float]] = []
    for row in rows:
        values: list[float] = []
        for field in fields:
            raw = row.get(field, [])
            if isinstance(raw, (list, tuple)):
                values.extend(float(x) for x in raw)
            else:
                values.append(float(raw))
        flattened.append(values)
    return np.asarray(flattened, dtype=float)


def _source_prefix_comparison(
    ctx: Stage41R11Context,
    result: Mapping[str, Any],
    *,
    atol: float,
) -> dict[str, Any]:
    spec = result.get("spec") or {}
    key = (
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )
    source = _source_selected_oracle_raw(ctx).get(key)
    if source is None:
        return {"source_available": False, "maximum_abs_difference": math.inf}
    state_count = SOURCE_HORIZON_STEPS + 1
    comparisons = {
        "physics": (
            _physics_array(result, count=state_count),
            _physics_array(source, count=state_count),
        ),
        "main_issued": (
            _trace_array(result, "control_trace", ["issued_mode_coefficients"], count=MAIN_CONTROL_STEPS),
            _trace_array(source, "control_trace", ["issued_mode_coefficients"], count=MAIN_CONTROL_STEPS),
        ),
        "main_applied": (
            _trace_array(result, "control_trace", ["applied_command_mode_coefficients"], count=MAIN_CONTROL_STEPS),
            _trace_array(source, "control_trace", ["applied_command_mode_coefficients"], count=MAIN_CONTROL_STEPS),
        ),
        "original_main_issued": (
            _trace_array(result, "original_main_control_trace", ["issued_mode_coefficients"], count=MAIN_CONTROL_STEPS),
            _trace_array(source, "original_main_control_trace", ["issued_mode_coefficients"], count=MAIN_CONTROL_STEPS),
        ),
        "preview_issued_applied": (
            _trace_array(
                result,
                "transition_preview_trace",
                ["issued_mode_coefficients", "applied_mode_coefficients"],
            ),
            _trace_array(
                source,
                "transition_preview_trace",
                ["issued_mode_coefficients", "applied_mode_coefficients"],
            ),
        ),
        "terminal_first40": (
            _trace_array(
                result,
                "terminal_feedback_trace",
                ["issued_mode_coefficients", "applied_mode_coefficients"],
                count=SOURCE_HORIZON_STEPS - MAIN_CONTROL_STEPS,
            ),
            _trace_array(
                source,
                "terminal_feedback_trace",
                ["issued_mode_coefficients", "applied_mode_coefficients"],
                count=SOURCE_HORIZON_STEPS - MAIN_CONTROL_STEPS,
            ),
        ),
    }
    components = {
        name: _finite_max_abs(left, right)
        for name, (left, right) in comparisons.items()
    }
    exact = {
        name: bool(left.shape == right.shape and np.array_equal(left, right))
        for name, (left, right) in comparisons.items()
    }
    numeric = {
        name: bool(
            left.shape == right.shape
            and np.allclose(left, right, rtol=0.0, atol=float(atol))
        )
        for name, (left, right) in comparisons.items()
    }
    return {
        "source_available": True,
        "source_experiment_id": source.get("experiment_id"),
        "component_max_abs_difference": components,
        "component_exact": exact,
        "component_numeric": numeric,
        "exact": all(exact.values()),
        "numeric": all(numeric.values()),
        "maximum_abs_difference": max(components.values(), default=0.0),
    }


def _target_vector(ctx: Stage41R11Context, spec: Mapping[str, Any]) -> np.ndarray:
    base = ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg["target"]
    return np.asarray(
        [
            float(base["R"]) + float(spec.get("target_R_offset_m", 0.0)),
            float(base["Z"]) + float(spec.get("target_Z_offset_m", 0.0)),
            float(base["Ip"]) + float(spec.get("target_Ip_offset_A", 0.0)),
        ],
        dtype=float,
    )


def _current_utilization(ctx: Stage41R11Context, trajectory: Sequence[Mapping[str, Any]]) -> float:
    currents = np.asarray([row["currents_a_display"] for row in trajectory], dtype=float)
    env_cfg = ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg
    minimum = np.asarray(env_cfg["min_current_a_display_order"], dtype=float)
    maximum = np.asarray(env_cfg["max_current_a_display_order"], dtype=float)
    center = 0.5 * (minimum + maximum)
    half = np.maximum(0.5 * (maximum - minimum), 1e-9)
    return float(np.max(np.abs((currents - center[None, :]) / half[None, :])))


def long_hold_result_row(
    ctx: Stage41R11Context,
    result: Mapping[str, Any],
    *,
    phase: str,
) -> dict[str, Any]:
    spec = result.get("spec") or {}
    trajectory = list(result.get("trajectory") or [])
    terminal_trace = list(result.get("terminal_feedback_trace") or [])
    hold = ctx.cfg["long_hold"]
    gate = ctx.cfg["gate"]
    horizon = int(hold["horizon_steps"])
    hold_start = int(hold["uniform_hold_start_step"])
    final_window_steps = int(hold["final_window_steps"])
    half_window = int(hold["stationarity_half_window_steps"])
    dt_s = float(hold["dt_s"])
    target = _target_vector(ctx, spec)
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    error = y - target[None, :] if len(y) else np.zeros((0, 3), dtype=float)
    speed = _speed(y, dt_s) if len(y) else np.zeros(0, dtype=float)
    prefix = _source_prefix_comparison(
        ctx, result, atol=float(hold["prefix_numeric_atol"])
    )
    sufficient = bool(
        len(trajectory) == horizon + 1
        and len(terminal_trace) == int(hold["tail_feedback_steps"])
        and len(y) > hold_start
    )

    hold_error = error[hold_start:] if sufficient else np.zeros((0, 3))
    hold_speed = speed[hold_start:] if sufficient else np.zeros(0)
    final_error = error[-final_window_steps:] if sufficient else np.zeros((0, 3))
    final_speed = speed[-final_window_steps:] if sufficient else np.zeros(0)
    currents = np.asarray(
        [row["currents_a_display"] for row in trajectory[-final_window_steps:]],
        dtype=float,
    ) if sufficient else np.zeros((0, 14))
    issued = np.asarray(
        [
            row.get("issued_desired_physical_mode_coefficients", [0.0] * N_MODES)
            for row in terminal_trace[-final_window_steps:]
        ],
        dtype=float,
    ) if sufficient else np.zeros((0, N_MODES))
    vessel = np.asarray(
        [row.get("vessel_current_abs_sum_a", 0.0) for row in trajectory[-final_window_steps:]],
        dtype=float,
    ) if sufficient else np.zeros(0)

    hold_box = float(np.max(np.abs(hold_error[:, :2]))) if hold_error.size else math.inf
    hold_speed_max = float(np.max(hold_speed)) if hold_speed.size else math.inf
    hold_ip_max = float(np.max(np.abs(hold_error[:, 2]))) if hold_error.size else math.inf
    final_box = float(np.max(np.abs(final_error[:, :2]))) if final_error.size else math.inf
    final_speed_rms = float(np.sqrt(np.mean(final_speed**2))) if final_speed.size else math.inf
    final_speed_max = float(np.max(final_speed)) if final_speed.size else math.inf
    final_ip_rms = float(np.sqrt(np.mean(final_error[:, 2] ** 2))) if final_error.size else math.inf
    final_ip_max = float(np.max(np.abs(final_error[:, 2]))) if final_error.size else math.inf
    terminal_ip_abs = float(abs(error[-1, 2])) if error.size else math.inf
    tail_box = (
        float(np.max(np.abs(error[MAIN_CONTROL_STEPS:, :2])))
        if len(error) > MAIN_CONTROL_STEPS
        else math.inf
    )
    current_util = _current_utilization(ctx, trajectory) if sufficient else math.inf

    if len(currents) >= 2 * half_window:
        previous_mean = np.mean(currents[-2 * half_window : -half_window], axis=0)
        final_mean = np.mean(currents[-half_window:], axis=0)
        current_mean_shift = float(np.max(np.abs(final_mean - previous_mean)))
    else:
        current_mean_shift = math.inf
    current_net_change = (
        float(np.max(np.abs(currents[-1] - currents[0])))
        if len(currents)
        else math.inf
    )
    current_slope = (
        float(np.max(np.abs(_linear_slope(currents))))
        if len(currents)
        else math.inf
    )
    issued_rms = (
        float(np.sqrt(np.mean(issued**2))) if issued.size else math.inf
    )
    issued_mean_norm = (
        float(np.linalg.norm(np.mean(issued, axis=0)))
        if issued.size
        else math.inf
    )
    vessel_max = float(np.max(vessel)) if vessel.size else math.inf
    if len(vessel) >= 2 * half_window:
        vessel_growth = float(
            np.mean(vessel[-half_window:])
            - np.mean(vessel[-2 * half_window : -half_window])
        )
    else:
        vessel_growth = math.inf
    terminal_summary = result.get("terminal_feedback_summary") or {}
    final_pending = _as_float(
        terminal_summary.get("maximum_final_pending_desired_physical_norm"),
        math.inf,
    )
    queue_ok = bool(
        terminal_summary.get("continuous_streaming_queue")
        and terminal_summary.get("streaming_queue_consistent")
        and not terminal_summary.get("pending_queue_bypassed", True)
    )

    limits = {
        "hold_box": float(gate["position_box_max_m"]),
        "hold_speed_max": float(gate["velocity_max_m_per_s"]),
        "hold_ip_max": float(gate["ip_sustained_max_tolerance_A"]),
        "final_box": float(gate["position_box_max_m"]),
        "final_speed_rms": float(gate["final_window_velocity_rms_max_m_per_s"]),
        "final_speed_max": float(gate["velocity_max_m_per_s"]),
        "final_ip_rms": float(gate["ip_hold_rms_tolerance_A"]),
        "final_ip_max": float(gate["ip_sustained_max_tolerance_A"]),
        "terminal_ip_abs": float(gate["ip_terminal_abs_tolerance_A"]),
        "tail_box": float(hold["maximum_tail_box_error_m"]),
        "current_utilization": float(gate["maximum_current_utilization"]),
        "current_mean_shift": float(hold["maximum_final_window_current_mean_shift_A"]),
        "current_net_change": float(hold["maximum_final_window_current_net_change_A"]),
        "current_linear_drift": float(hold["maximum_final_window_current_linear_drift_A_per_step"]),
        "issued_rms": float(hold["maximum_final_window_issued_desired_rms"]),
        "issued_mean_norm": float(hold["maximum_final_window_issued_mean_norm"]),
        "final_pending": float(hold["maximum_final_pending_desired_physical_norm"]),
        "vessel_abs_sum": float(hold["maximum_final_window_vessel_abs_sum_A"]),
        "vessel_mean_growth": float(hold["maximum_final_window_vessel_mean_growth_A"]),
    }
    values = {
        "hold_box": hold_box,
        "hold_speed_max": hold_speed_max,
        "hold_ip_max": hold_ip_max,
        "final_box": final_box,
        "final_speed_rms": final_speed_rms,
        "final_speed_max": final_speed_max,
        "final_ip_rms": final_ip_rms,
        "final_ip_max": final_ip_max,
        "terminal_ip_abs": terminal_ip_abs,
        "tail_box": tail_box,
        "current_utilization": current_util,
        "current_mean_shift": current_mean_shift,
        "current_net_change": current_net_change,
        "current_linear_drift": current_slope,
        "issued_rms": issued_rms,
        "issued_mean_norm": issued_mean_norm,
        "final_pending": final_pending,
        "vessel_abs_sum": vessel_max,
        "vessel_mean_growth": max(vessel_growth, 0.0),
    }
    margins = {
        key: 1.0 - values[key] / max(limits[key], 1e-12)
        for key in values
    }
    combined = min(margins.values(), default=-math.inf)
    guards = {
        "complete_horizon": sufficient,
        "source_prefix_exact": bool(prefix.get("exact")),
        "source_prefix_numeric": bool(prefix.get("numeric")),
        "streaming_queue": queue_ok,
        "all_thresholds": bool(all(value >= -1e-12 for value in margins.values())),
        "minimum_margin": bool(
            combined >= float(hold["minimum_combined_signed_margin"]) - 1e-12
        ),
    }
    case_pass = bool(
        result.get("success")
        and all(guards.values())
        and not any(bool(row.get("abnormal", False)) for row in trajectory)
        and all(
            bool(row.get("solver_success", False))
            for row in terminal_trace
        )
    )
    actions = np.asarray(
        [row.get("action_norm_tsc", [0.0] * 14) for row in trajectory[1:]],
        dtype=float,
    )
    return {
        "experiment_id": result.get("experiment_id"),
        "phase": phase,
        "scenario": spec.get("scenario"),
        "target_id": spec.get("target_id"),
        "policy_id": spec.get("terminal_policy_id"),
        "actual_action_delay_steps": spec.get("action_delay_steps"),
        "controller_action_delay_steps": spec.get("controller_action_delay_steps"),
        "actual_slew_scale": spec.get("slew_scale"),
        "controller_slew_scale_estimate": spec.get("controller_slew_scale_estimate"),
        "calibration_token": spec.get("calibration_token"),
        "trusted_calibration_model": bool(spec.get("trusted_calibration_model", False)),
        "success": bool(result.get("success")),
        "failure_reason": result.get("failure_reason", ""),
        "n_trajectory_steps": len(trajectory),
        "n_terminal_feedback_steps": len(terminal_trace),
        "uniform_hold_start_step": hold_start,
        "source_prefix_exact": bool(prefix.get("exact")),
        "source_prefix_numeric": bool(prefix.get("numeric")),
        "source_prefix_max_abs_difference": prefix.get("maximum_abs_difference"),
        "source_prefix_component_max_abs_difference": prefix.get(
            "component_max_abs_difference"
        ),
        "streaming_queue_consistent": bool(
            terminal_summary.get("streaming_queue_consistent", False)
        ),
        "pending_queue_bypassed": bool(
            terminal_summary.get("pending_queue_bypassed", True)
        ),
        "hold_box_max_error_m": hold_box,
        "hold_speed_max_m_per_s": hold_speed_max,
        "hold_ip_max_abs_error_A": hold_ip_max,
        "final_window_box_max_error_m": final_box,
        "final_window_speed_rms_m_per_s": final_speed_rms,
        "final_window_speed_max_m_per_s": final_speed_max,
        "final_window_ip_rms_error_A": final_ip_rms,
        "final_window_ip_max_abs_error_A": final_ip_max,
        "terminal_ip_abs_error_A": terminal_ip_abs,
        "tail_box_max_error_m": tail_box,
        "max_current_utilization": current_util,
        "final_window_current_mean_shift_max_A": current_mean_shift,
        "final_window_current_net_change_max_A": current_net_change,
        "final_window_current_linear_drift_max_A_per_step": current_slope,
        "final_window_issued_desired_rms": issued_rms,
        "final_window_issued_desired_mean_norm": issued_mean_norm,
        "maximum_final_pending_desired_physical_norm": final_pending,
        "final_window_vessel_abs_sum_max_A": vessel_max,
        "final_window_vessel_mean_growth_A": vessel_growth,
        "long_hold_margins": margins,
        "long_hold_combined_minimum_signed_margin": combined,
        "long_hold_guards": guards,
        "long_hold_pass": case_pass,
        "full_action_rms": float(np.sqrt(np.mean(actions**2))) if actions.size else 0.0,
        "wall_time_s": _as_float(result.get("wall_time_s"), 0.0),
        "physics_signature": _array_digest(_physics_array(result), "physics"),
        "terminal_issued_signature": _array_digest(
            _trace_array(result, "terminal_feedback_trace", ["issued_mode_coefficients"]),
            "terminalissued",
        ),
        "terminal_applied_signature": _array_digest(
            _trace_array(result, "terminal_feedback_trace", ["applied_mode_coefficients"]),
            "terminalapplied",
        ),
    }


def _expected_case_keys(ctx: Stage41R11Context) -> set[tuple[str, int, float]]:
    return {
        (str(target["target_id"]), int(delay), float(slew))
        for target in ctx.cfg["long_hold"]["targets"]
        for delay in ctx.cfg["long_hold"]["actual_delay_steps"]
        for slew in ctx.cfg["long_hold"]["actual_slew_scales"]
    }


def summarize_long_hold(
    ctx: Stage41R11Context,
    rows: Sequence[Mapping[str, Any]],
    *,
    phase: str,
) -> dict[str, Any]:
    expected = _expected_case_keys(ctx)
    observed = {
        (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in rows
    }
    coverage = len(rows) == len(expected) and observed == expected
    pass_fraction = sum(bool(row.get("long_hold_pass")) for row in rows) / max(
        len(rows), 1
    )
    minimum_margin = min(
        (
            _as_float(
                row.get("long_hold_combined_minimum_signed_margin"), -math.inf
            )
            for row in rows
        ),
        default=-math.inf,
    )
    passed = bool(
        coverage
        and all(bool(row.get("success")) for row in rows)
        and pass_fraction >= float(ctx.cfg["long_hold"]["minimum_case_pass_fraction"])
        and minimum_margin
        >= float(ctx.cfg["long_hold"]["minimum_combined_signed_margin"])
        - 1e-12
        and all(bool(row.get("source_prefix_exact")) for row in rows)
        and all(bool(row.get("streaming_queue_consistent")) for row in rows)
        and not any(bool(row.get("pending_queue_bypassed")) for row in rows)
    )
    by_target: list[dict[str, Any]] = []
    for target in [str(row["target_id"]) for row in ctx.cfg["long_hold"]["targets"]]:
        subset = [row for row in rows if str(row.get("target_id")) == target]
        by_target.append(
            {
                "target_id": target,
                "n_rollouts": len(subset),
                "pass_fraction": sum(bool(row.get("long_hold_pass")) for row in subset)
                / max(len(subset), 1),
                "minimum_combined_margin": min(
                    (
                        _as_float(
                            row.get("long_hold_combined_minimum_signed_margin"),
                            -math.inf,
                        )
                        for row in subset
                    ),
                    default=-math.inf,
                ),
                "maximum_hold_box_error_m": max(
                    (_as_float(row.get("hold_box_max_error_m"), math.inf) for row in subset),
                    default=math.inf,
                ),
                "maximum_hold_speed_m_per_s": max(
                    (_as_float(row.get("hold_speed_max_m_per_s"), math.inf) for row in subset),
                    default=math.inf,
                ),
                "maximum_current_utilization": max(
                    (_as_float(row.get("max_current_utilization"), math.inf) for row in subset),
                    default=math.inf,
                ),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": phase,
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected),
        "coverage_complete": coverage,
        "environment_success_count": sum(bool(row.get("success")) for row in rows),
        "long_hold_pass_fraction": pass_fraction,
        "minimum_combined_signed_margin": minimum_margin,
        "source_prefix_exact_fraction": sum(bool(row.get("source_prefix_exact")) for row in rows)
        / max(len(rows), 1),
        "maximum_source_prefix_abs_difference": max(
            (_as_float(row.get("source_prefix_max_abs_difference"), math.inf) for row in rows),
            default=math.inf,
        ),
        "maximum_hold_box_error_m": max(
            (_as_float(row.get("hold_box_max_error_m"), math.inf) for row in rows),
            default=math.inf,
        ),
        "maximum_hold_speed_m_per_s": max(
            (_as_float(row.get("hold_speed_max_m_per_s"), math.inf) for row in rows),
            default=math.inf,
        ),
        "maximum_final_window_speed_rms_m_per_s": max(
            (_as_float(row.get("final_window_speed_rms_m_per_s"), math.inf) for row in rows),
            default=math.inf,
        ),
        "maximum_current_utilization": max(
            (_as_float(row.get("max_current_utilization"), math.inf) for row in rows),
            default=math.inf,
        ),
        "maximum_final_window_current_net_change_A": max(
            (_as_float(row.get("final_window_current_net_change_max_A"), math.inf) for row in rows),
            default=math.inf,
        ),
        "maximum_final_window_issued_desired_mean_norm": max(
            (_as_float(row.get("final_window_issued_desired_mean_norm"), math.inf) for row in rows),
            default=math.inf,
        ),
        "maximum_final_pending_desired_norm": max(
            (_as_float(row.get("maximum_final_pending_desired_physical_norm"), math.inf) for row in rows),
            default=math.inf,
        ),
        "by_target": by_target,
        "passed": passed,
    }


def run_oracle_long_hold(
    ctx: Stage41R11Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_oracle_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.oracle_long_hold / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [long_hold_result_row(ctx, result, phase="oracle_long_hold") for result in results]
    summary = summarize_long_hold(ctx, rows, phase="oracle_long_hold")
    atomic_write_json(ctx.paths.oracle_long_hold / "results.json", rows)
    atomic_write_json(ctx.paths.oracle_long_hold / "summary.json", summary)
    write_csv(ctx.paths.oracle_long_hold / "results.csv", rows)
    _update_state(
        ctx,
        oracle_long_hold_complete=True,
        oracle_long_hold_summary=summary,
    )
    return summary


def _result_trace_arrays(result: Mapping[str, Any]) -> dict[str, np.ndarray]:
    return {
        "physics": _physics_array(result),
        "main_issued": _trace_array(result, "control_trace", ["issued_mode_coefficients"]),
        "main_applied": _trace_array(result, "control_trace", ["applied_command_mode_coefficients"]),
        "original_main_issued": _trace_array(
            result, "original_main_control_trace", ["issued_mode_coefficients"]
        ),
        "preview_issued": _trace_array(
            result, "transition_preview_trace", ["issued_mode_coefficients"]
        ),
        "preview_applied": _trace_array(
            result, "transition_preview_trace", ["applied_mode_coefficients"]
        ),
        "terminal_issued": _trace_array(
            result, "terminal_feedback_trace", ["issued_mode_coefficients"]
        ),
        "terminal_applied": _trace_array(
            result, "terminal_feedback_trace", ["applied_mode_coefficients"]
        ),
    }


def summarize_calibrated_long_hold(
    ctx: Stage41R11Context,
    rows: Sequence[Mapping[str, Any]],
    raw_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    base = summarize_long_hold(ctx, rows, phase="calibrated_long_hold")
    oracle_raw = {
        (
            str(result["spec"]["target_id"]),
            int(result["spec"]["action_delay_steps"]),
            float(result["spec"]["slew_scale"]),
        ): result
        for result in (
            read_json_gz(path)
            for path in sorted((ctx.paths.oracle_long_hold / "raw").glob("*.json.gz"))
        )
    }
    atol = float(ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"])
    comparisons: list[dict[str, Any]] = []
    token_ids: set[str] = set()
    untrusted = 0
    for result in raw_results:
        spec = result.get("spec") or {}
        key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        oracle = oracle_raw.get(key)
        arrays = _result_trace_arrays(result)
        oracle_arrays = _result_trace_arrays(oracle) if oracle is not None else {}
        components: dict[str, float] = {}
        exact = True
        numeric = True
        for name, array in arrays.items():
            other = oracle_arrays.get(name)
            if other is None:
                diff = math.inf
                exact = numeric = False
            else:
                diff = _finite_max_abs(array, other)
                exact = bool(exact and array.shape == other.shape and np.array_equal(array, other))
                numeric = bool(
                    numeric
                    and array.shape == other.shape
                    and np.allclose(array, other, rtol=0.0, atol=atol)
                )
            components[name] = diff
        token = str(spec.get("calibration_token") or "")
        if token:
            token_ids.add(token)
        if not bool(spec.get("trusted_calibration_model", False)):
            untrusted += 1
        comparisons.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "calibration_token": token,
                "exact_trace_equal_to_oracle": exact,
                "numeric_trace_equal_to_oracle": numeric,
                "maximum_trace_abs_difference": max(components.values(), default=math.inf),
                "component_max_abs_difference": components,
            }
        )
    exact_fraction = sum(row["exact_trace_equal_to_oracle"] for row in comparisons) / max(len(comparisons), 1)
    numeric_fraction = sum(row["numeric_trace_equal_to_oracle"] for row in comparisons) / max(len(comparisons), 1)
    base.update(
        {
            "distinct_calibration_tokens": len(token_ids),
            "untrusted_main_start_count": untrusted,
            "exact_trace_equivalence_fraction": exact_fraction,
            "numeric_trace_equivalence_fraction": numeric_fraction,
            "numeric_trace_equivalence_atol": atol,
            "maximum_trace_abs_difference": max(
                (row["maximum_trace_abs_difference"] for row in comparisons),
                default=math.inf,
            ),
            "comparisons": comparisons,
        }
    )
    base["passed"] = bool(
        base["passed"]
        and len(rows) == 18
        and len(token_ids) == 9
        and untrusted == 0
        and exact_fraction
        >= float(
            ctx.cfg["calibrated_confirmation"][
                "minimum_trace_equivalence_fraction"
            ]
        )
        and numeric_fraction >= 1.0 - 1e-12
    )
    return base


def run_calibrated_long_hold(
    ctx: Stage41R11Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_calibrated_specs(ctx)
    if not specs:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "calibrated_long_hold",
            "status": "not_run_oracle_long_hold_not_closed",
            "passed": False,
        }
        atomic_write_json(ctx.paths.calibrated_long_hold / "summary.json", summary)
        _update_state(
            ctx,
            calibrated_long_hold_complete=False,
            calibrated_long_hold_summary=summary,
        )
        return summary
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.calibrated_long_hold / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [
        long_hold_result_row(ctx, result, phase="calibrated_long_hold")
        for result in results
    ]
    summary = summarize_calibrated_long_hold(ctx, rows, results)
    atomic_write_json(ctx.paths.calibrated_long_hold / "results.json", rows)
    atomic_write_json(ctx.paths.calibrated_long_hold / "summary.json", summary)
    write_csv(ctx.paths.calibrated_long_hold / "results.csv", rows)
    _update_state(
        ctx,
        calibrated_long_hold_complete=True,
        calibrated_long_hold_summary=summary,
    )
    return summary


def run_restart_audit(ctx: Stage41R11Context) -> dict[str, Any]:
    folders = [str(x) for x in ctx.cfg["restart_audit"]["candidate_folders"]]
    available: list[str] = []
    simulation_root = Path(
        ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "simulation_root"
        ]
    ).expanduser()
    for name in folders:
        if (simulation_root / name).is_dir():
            available.append(name)
    required = int(ctx.cfg["restart_audit"]["minimum_distinct_folders"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_audit",
        "simulation_root": str(simulation_root),
        "candidate_folders": folders,
        "available_folders": available,
        "true_restart_validation_available": len(available) >= required,
        "true_restart_validation_performed": False,
        "availability_requirement_for_stage4_1r11": bool(
            ctx.cfg["restart_audit"].get(
                "availability_requirement_for_stage4_1r11", False
            )
        ),
        "audit_completed": True,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart_audit / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


def _phase_status(
    state: Mapping[str, Any], complete_key: str, summary_key: str
) -> str:
    if not bool(state.get(complete_key)):
        return "not_run"
    return "passed" if bool((state.get(summary_key) or {}).get("passed")) else "failed"


def analyze(ctx: Stage41R11Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    oracle = state.get("oracle_long_hold_summary") or {}
    calibrated = state.get("calibrated_long_hold_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    primary_pass = bool(source.get("passed") and oracle.get("passed") and calibrated.get("passed"))
    verdict = (
        "STAGE4_1R11_FINITE_FROZEN_TERMINAL_2000MS_LONG_HOLD_CLOSURE"
        if primary_pass
        else "STAGE4_1R11_FROZEN_TERMINAL_LONG_HOLD_INCOMPLETE"
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r10_run": str(ctx.source_stage41r10_run),
        "source_audit_status": _phase_status(
            state, "source_audit_complete", "source_audit_summary"
        ),
        "oracle_long_hold_status": _phase_status(
            state, "oracle_long_hold_complete", "oracle_long_hold_summary"
        ),
        "calibrated_long_hold_status": _phase_status(
            state,
            "calibrated_long_hold_complete",
            "calibrated_long_hold_summary",
        ),
        "selected_terminal_policy": ctx.cfg["long_hold"]["selected_policy"]["policy_id"],
        "policy_retuned": False,
        "new_arrival_endpoint_selected": False,
        "fixed_hold_start_ms": int(ctx.cfg["long_hold"]["uniform_hold_start_step"]) * 10,
        "hold_horizon_ms": int(ctx.cfg["long_hold"]["horizon_steps"]) * 10,
        "source_750ms_prefix_exact_required": True,
        "finite_frozen_terminal_long_hold_envelope_validated": primary_pass,
        "true_restart_validation_available": bool(
            restart.get("true_restart_validation_available", False)
        ),
        "true_restart_validation_performed": False,
        "plant_parameter_robustness_validated": False,
        "continuous_parameter_change_validated": False,
        "terminal_measurement_noise_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "finite_test_envelope_only": True,
        "warning": (
            "R11 can only validate a frozen 2000 ms clean hold for two targets and "
            "the discrete 3x3 static delay/slew grid in the same digital twin. It "
            "does not validate true restart state, hidden vessel/eddy history, "
            "plant-model error, continuous actuator changes, noisy sensing, or deployment."
        ),
        "next_if_pass": (
            "Proceed to Stage4.2 true restart, hidden-history and plant/actuator-"
            "parameter robustness. Do not start BC/DAgger/RL yet."
        ),
        "next_if_fail": (
            "Do not reinterpret R10 finite closure as a stable expert baseline. "
            "Identify a bounded terminal local model and redesign an offset-free "
            "terminal regulator without weakening the 30 mm/0.1 m/s gates and "
            "without handing 14-coil control to RL."
        ),
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "oracle_long_hold": oracle,
            "calibrated_long_hold": calibrated,
            "restart_audit": restart,
        },
    }
    verdict_payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": verdict,
        "primary_pass": primary_pass,
        "selected_terminal_policy": ctx.cfg["long_hold"]["selected_policy"]["policy_id"],
        "next_if_pass": summary["next_if_pass"],
        "next_if_fail": summary["next_if_fail"],
        "final_task": ctx.cfg["final_task"],
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r11_summary.json", summary)
    atomic_write_json(ctx.paths.analysis / "stage4_1r11_verdict.json", verdict_payload)
    if primary_pass:
        stop_reason = ""
    elif bool(state.get("source_audit_complete")) and not bool(source.get("passed")):
        stop_reason = "source_audit_failed"
    elif bool(state.get("oracle_long_hold_complete")) and not bool(oracle.get("passed")):
        stop_reason = "oracle_long_hold_failed"
    elif bool(state.get("calibrated_long_hold_complete")) and not bool(calibrated.get("passed")):
        stop_reason = "calibrated_long_hold_failed"
    else:
        stop_reason = "long_hold_incomplete"
    _update_state(ctx, finished=True, stop_reason=stop_reason)
    return summary


def execute(
    ctx: Stage41R11Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    if command == "prepare":
        return {"stage": STAGE, "run_dir": str(ctx.paths.run_dir), "prepared": True}
    if command in {"all", "audit"}:
        source = run_source_audit(ctx)
        if command == "audit":
            return source
        if not source.get("passed"):
            _update_state(ctx, finished=True, stop_reason="source_audit_failed")
            return analyze(ctx)
    if command in {"all", "oracle"}:
        oracle = run_oracle_long_hold(ctx, backend=backend, resume=resume)
        if command == "oracle":
            return oracle
        if not oracle.get("passed"):
            run_restart_audit(ctx)
            _update_state(ctx, finished=True, stop_reason="oracle_long_hold_failed")
            return analyze(ctx)
    if command in {"all", "calibrated"}:
        calibrated = run_calibrated_long_hold(ctx, backend=backend, resume=resume)
        if command == "calibrated":
            return calibrated
        if not calibrated.get("passed"):
            run_restart_audit(ctx)
            _update_state(ctx, finished=True, stop_reason="calibrated_long_hold_failed")
            return analyze(ctx)
    if command in {"all", "restart"}:
        restart = run_restart_audit(ctx)
        if command == "restart":
            return restart
    return analyze(ctx)


def self_test() -> dict[str, Any]:
    config_path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json"
    )
    cfg = read_json(config_path)
    validate_config(cfg)

    # Exact queue-preview semantics remain inherited from R10.
    fake_control = []
    for index in range(MAIN_CONTROL_STEPS):
        fake_control.append(
            {
                "issued_mode_coefficients": [float(index), 0.0, 0.0],
                "issued_desired_physical_mode_coefficients": [float(index), 0.0, 0.0],
            }
        )
    queue, preview = r10._initial_preview_queue(fake_control, 2)
    queue_ok = bool(
        preview == [33, 34]
        and [int(item["origin_index"]) for item in queue] == [31, 32]
    )

    # Synthetic long-hold arithmetic regression.
    horizon = int(cfg["long_hold"]["horizon_steps"])
    target = np.asarray([0.75, 0.0, 29779.724])
    t = np.arange(horizon + 1)
    y = np.column_stack(
        [
            target[0] + 0.01 * np.exp(-t / 30.0),
            target[1] + 0.01 * np.exp(-t / 30.0),
            target[2] + 100.0 * np.exp(-t / 30.0),
        ]
    )
    speed = _speed(y, float(cfg["long_hold"]["dt_s"]))
    arithmetic_ok = bool(
        len(speed) == horizon + 1
        and float(np.max(np.abs(y[65:, :2] - target[:2]))) < 0.03
        and float(np.max(speed[65:])) < 0.1
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_validation_passed": True,
        "r10_preview_queue_semantics_retained": queue_ok,
        "long_hold_metric_arithmetic_passed": arithmetic_ok,
        "frozen_policy_id": cfg["long_hold"]["selected_policy"]["policy_id"],
        "passed": bool(queue_ok and arithmetic_ok),
    }
    return payload


def _set_resource_limits() -> None:
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        target = min(max(soft, 65536), hard if hard > 0 else 65536)
        resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    except (ValueError, OSError):
        pass


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R11 frozen terminal long-horizon hold"
    )
    parser.add_argument(
        "--config",
        default="configs/stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json",
    )
    parser.add_argument("--source-stage4-1r10-run")
    parser.add_argument("--run-dir")
    parser.add_argument(
        "--command",
        choices=("all", "prepare", "audit", "oracle", "calibrated", "restart", "analyze"),
        default="all",
    )
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        payload = self_test()
        print(json.dumps(payload, indent=2, sort_keys=True))
        if not payload.get("passed"):
            raise SystemExit(1)
        return
    if not args.source_stage4_1r10_run:
        parser.error("--source-stage4-1r10-run is required")
    _set_resource_limits()
    ctx = load_stage41r11_config(
        Path(args.config),
        source_stage41r10_run=Path(args.source_stage4_1r10_run),
        run_dir_override=Path(args.run_dir) if args.run_dir else None,
    )
    try:
        payload = execute(
            ctx,
            command=args.command,
            backend=args.backend,
            resume=bool(args.resume),
        )
        print(json.dumps(_json_safe(payload), indent=2, sort_keys=False))
    except Exception:
        if ctx.paths.state.is_file():
            _update_state(ctx, finished=True, stop_reason="runtime_exception")
        raise


if __name__ == "__main__":
    main()
