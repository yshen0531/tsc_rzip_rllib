"""Stage4.1R14 original-deadline integrated target-conditioned deadline MPC.

R13 completed normally and provided a useful causal onset bank, but its handoff
was not the original target-conditioned expert: after the handoff it set the
Stage3.4 nominal control and nominal feature to zero and reset the accumulated
integral state.  The remaining bounded residual regulator improved braking but
could not close either RZ_p10_m10 weak-slew delay=1/2 case.

R14 keeps the immutable formal contracts (250/350 ms for normal slew and
270/370 ms for 0.9x slew), fixes the first physical effect at R13's preregistered
minimax state 23, restores the target-conditioned Stage3.4 nominal trajectory,
feedforward and checkpoint integral, and adds an explicit velocity penalty for
states 24--27 inside the same delay-aware 175x105 MPC.  Only a small,
interpretable deadline-weight/correction-scale bank is compared.  No onset,
arrival deadline or horizon is re-searched.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage3_4_late_arrival_continuation_mpc as s34
from . import stage4_1r3_control_aware_robustness as r3
from . import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8
from . import stage4_1r9_terminal_template_mpc_feedback_hold as r9
from . import stage4_1r10_queue_preview_terminal_transition_hold as r10
from . import stage4_1r12_original_deadline_weak_slew_anticipatory_damping as r12
from . import stage4_1r13_original_deadline_delay_pipeline_early_braking as r13
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r13.atomic_write_json
atomic_write_json_gz = r13.atomic_write_json_gz
read_json = r13.read_json
read_json_gz = r13.read_json_gz
utc_timestamp = r13.utc_timestamp
write_csv = r13.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R14"
CONTROLLER_REVISION = "original_deadline_integrated_target_conditioned_deadline_mpc_v14"
PACKAGE_REVISION = "r14_integrated_target_conditioned_deadline_mpc_v1"
EXPECTED_SOURCE_REVISION = r13.CONTROLLER_REVISION
EXPECTED_SOURCE_PACKAGE_REVISION = r13.PACKAGE_REVISION
WEAK_SLEW = 0.9
WEAK_HORIZON = 37
MAIN_HORIZON = 35
N_MODES = 3


def _json_safe(value: Any) -> Any:
    return r13._json_safe(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r13._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r13._sha256_file(path)


def _result_complete(path: Path) -> bool:
    return r13._result_complete(path)


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    return r13._finite_max_abs(left, right)


def _array_digest(array: np.ndarray, prefix: str) -> str:
    return r13._array_digest(np.asarray(array), prefix)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return "s41r14_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class Stage41R14Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    oracle_development: Path
    calibrated_confirmation: Path
    formal_grid_confirmation: Path
    restart_audit: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R14Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r14_source_reference",
            source_audit=run_dir / "stage4_1r14_source_audit",
            oracle_development=run_dir / "stage4_1r14_oracle_development",
            calibrated_confirmation=run_dir / "stage4_1r14_calibrated_confirmation",
            formal_grid_confirmation=run_dir / "stage4_1r14_formal_grid_confirmation",
            restart_audit=run_dir / "stage4_1r14_restart_audit",
            analysis=run_dir / "stage4_1r14_analysis",
            variants=run_dir / "stage4_1r14_environment_variants",
            state=run_dir / "stage4_1r14_state.json",
            manifest=run_dir / "stage4_1r14_manifest.json",
        )


@dataclass
class Stage41R14Context:
    cfg: dict[str, Any]
    paths: Stage41R14Paths
    project_dir: Path
    source_stage41r13_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    source_stage41r12_run: Path
    r13_ctx: r13.Stage41R13Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r13_manifest.json",
        source / "stage4_1r13_state.json",
        source / "stage4_1r13_config.resolved.json",
        source / "stage4_1r13_analysis" / "stage4_1r13_verdict.json",
        source / "stage4_1r13_analysis" / "stage4_1r13_summary.json",
        source / "stage4_1r13_source_audit" / "summary.json",
        source / "stage4_1r13_oracle_development" / "summary.json",
        source / "stage4_1r13_oracle_development" / "results.json",
        source / "stage4_1r13_oracle_development" / "results.csv",
    ]
    required.extend(sorted((source / "stage4_1r13_oracle_development" / "raw").glob("*.json.gz")))
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R13 source file missing: {path}")
        size = path.stat().st_size
        total += size
        rows.append(
            {
                "relative_path": str(path.relative_to(source)),
                "size_bytes": size,
                "sha256": _sha256_file(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": 1,
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
    }


def _resolve_recorded_run(project_dir: Path, recorded: str, root_name: str) -> Path:
    return r13._resolve_recorded_run(project_dir, recorded, root_name)


def _transition_issue_step(first_affected_state_step: int, delay_steps: int) -> int:
    return r13._transition_issue_step(first_affected_state_step, delay_steps)


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R14 controller_revision mismatch")
    req = cfg["source_requirement"]
    if req.get("required_stage") != "Stage4.1R13":
        raise ValueError("R14 source stage must remain Stage4.1R13")
    if req.get("required_controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("R14 source controller revision mismatch")
    if req.get("required_package_revision") != EXPECTED_SOURCE_PACKAGE_REVISION:
        raise ValueError("R14 source package revision mismatch")
    gate = cfg["gate"]
    if not math.isclose(float(gate["precise_tolerance_m"]), 0.03, abs_tol=1e-15):
        raise ValueError("R14 may not weaken the 30 mm position gate")
    if not math.isclose(float(gate["terminal_velocity_max_m_per_s"]), 0.1, abs_tol=1e-15):
        raise ValueError("R14 may not weaken the 0.1 m/s speed gate")
    timing = cfg["formal_timing_contract"]
    normal, weak = timing["normal_slew"], timing["weak_slew"]
    if not bool(timing.get("immutable")):
        raise ValueError("R14 timing contract must remain immutable")
    if (int(normal["arrival_deadline_step"]), int(normal["horizon_steps"])) != (25, 35):
        raise ValueError("normal-slew contract must remain 250/350 ms")
    if (int(weak["arrival_deadline_step"]), int(weak["horizon_steps"])) != (27, 37):
        raise ValueError("weak-slew contract must remain 270/370 ms")
    if max(map(int, normal["allowed_arrival_steps"])) != 25 or max(map(int, weak["allowed_arrival_steps"])) != 27:
        raise ValueError("formal arrival list exceeds immutable deadline")
    design = cfg["integrated_deadline_mpc"]
    if not math.isclose(float(design["actual_slew_scale"]), WEAK_SLEW, abs_tol=1e-15):
        raise ValueError("R14 may modify only the 0.9x-slew branch")
    if int(design["horizon_steps"]) != WEAK_HORIZON:
        raise ValueError("R14 weak-slew horizon must remain 37 steps")
    if [int(x) for x in design["actual_delay_steps"]] != [1, 2]:
        raise ValueError("R14 may modify only delay=1/2")
    if int(design["fixed_first_affected_state_step"]) != 23:
        raise ValueError("R14 must fix, not rescan, the R13 minimax onset state 23")
    if [int(x) for x in design["deadline_velocity_states"]] != [24, 25, 26, 27]:
        raise ValueError("R14 deadline velocity states changed")
    if not bool(design.get("target_conditioned_nominal_physical_required")):
        raise ValueError("R14 must retain target-conditioned nominal feedforward")
    if not bool(design.get("target_conditioned_nominal_feature_required")):
        raise ValueError("R14 must retain target-conditioned nominal feature")
    if not bool(design.get("checkpoint_integral_preservation_required")):
        raise ValueError("R14 must preserve the main-MPC checkpoint integral")
    candidates = list(design["candidate_bank"])
    expected = [
        ("itc_vw1_c0p50", 1.0, 0.50),
        ("itc_vw3_c0p50", 3.0, 0.50),
        ("itc_vw6_c0p50", 6.0, 0.50),
        ("itc_vw10_c0p50", 10.0, 0.50),
        ("itc_vw6_c0p60", 6.0, 0.60),
        ("itc_vw10_c0p60", 10.0, 0.60),
    ]
    actual = [
        (str(row["policy_id"]), float(row["deadline_velocity_weight_multiplier"]), float(row["controller_scale"]))
        for row in candidates
    ]
    if actual != expected:
        raise ValueError("R14 candidate bank changed")
    if not bool(design.get("require_no_onset_rescan")):
        raise ValueError("R14 must prohibit another onset scan")
    if not bool(design.get("selection_is_conditioned_only_on_trusted_delay")):
        raise ValueError("R14 selection may only branch on trusted delay")
    if not bool(design.get("selection_uses_both_required_targets")):
        raise ValueError("R14 must close both required targets per delay")
    if bool(design.get("unseen_target_holdout_claimed")):
        raise ValueError("R14 may not claim unseen-target generalization")
    if bool(cfg["calibrated_confirmation"].get("online_handover_enabled")):
        raise ValueError("R14 calibrated path must not use online handover")
    if not bool(cfg.get("finite_test_envelope_only")):
        raise ValueError("R14 must remain finite-envelope only")


def _validate_source_stage41r13(source: Path, cfg: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R13 source file missing: {path}")
    manifest = read_json(source / "stage4_1r13_manifest.json")
    state = read_json(source / "stage4_1r13_state.json")
    source_cfg = read_json(source / "stage4_1r13_config.resolved.json")
    verdict = read_json(source / "stage4_1r13_analysis" / "stage4_1r13_verdict.json")
    req = cfg["source_requirement"]
    if manifest.get("stage") != req["required_stage"]:
        raise ValueError("source Stage4.1R13 manifest stage mismatch")
    if manifest.get("controller_revision") != req["required_controller_revision"]:
        raise ValueError("source Stage4.1R13 controller revision mismatch")
    if manifest.get("package_revision") != req["required_package_revision"]:
        raise ValueError("source Stage4.1R13 package revision mismatch")
    if source_cfg.get("controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R13 resolved config revision mismatch")
    if bool(req.get("require_finished")) and not bool(state.get("finished")):
        raise ValueError("source Stage4.1R13 is not finished")
    if str(state.get("stop_reason", "")) != str(req.get("require_stop_reason", "")):
        raise ValueError("source Stage4.1R13 stop_reason mismatch")
    if bool(req.get("require_source_audit_passed")) and not bool((state.get("source_audit_summary") or {}).get("passed")):
        raise ValueError("source Stage4.1R13 source audit did not pass")
    if bool(req.get("require_oracle_development_complete")) and not bool(state.get("oracle_development_complete")):
        raise ValueError("source Stage4.1R13 development is incomplete")
    source_dev = state.get("oracle_development_summary") or {}
    if bool(source_dev.get("passed")) != bool(req.get("require_oracle_development_passed")):
        raise ValueError("source Stage4.1R13 development pass status mismatch")
    raw_count = len(list((source / "stage4_1r13_oracle_development" / "raw").glob("*.json.gz")))
    if raw_count != int(req["require_oracle_raw_count"]):
        raise ValueError(f"source Stage4.1R13 raw count mismatch: {raw_count}")
    if bool(verdict.get("primary_pass")):
        raise ValueError("source Stage4.1R13 unexpectedly claims primary closure")
    return manifest, state, source_cfg, verdict


def load_stage41r14_config(
    config_path: Path,
    *,
    source_stage41r13_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R14Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r13_run = source_stage41r13_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r13(source_stage41r13_run, cfg)
    source_stage41r12_run = _resolve_recorded_run(
        project_dir, str(manifest["source_stage4_1r12_run"]), "stage4_1r12_runs"
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r14_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r14')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    packaged_r13_cfg = project_dir / "configs" / "stage4_1r13_original_deadline_delay_pipeline_early_braking_370ms.json"
    if not packaged_r13_cfg.is_file():
        raise FileNotFoundError(f"packaged R13 dependency config missing: {packaged_r13_cfg}")
    r13_ctx = r13.load_stage41r13_config(
        packaged_r13_cfg,
        source_stage41r12_run=source_stage41r12_run,
        run_dir_override=run_dir,
    )
    recorded = manifest.get("source_fingerprint") or {}
    current_r12 = r13._source_inventory(source_stage41r12_run)
    if recorded.get("digest") != current_r12.get("digest"):
        raise ValueError("R14 nested Stage4.1R12 source fingerprint mismatch")
    storage = cfg["storage"]
    base34 = r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_1R14_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]))
        .expanduser().resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R14_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser().resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    base34.env_cfg = env_cfg
    return Stage41R14Context(
        cfg=cfg,
        paths=Stage41R14Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r13_run=source_stage41r13_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        source_stage41r12_run=source_stage41r12_run,
        r13_ctx=r13_ctx,
        source_fingerprint=_source_inventory(source_stage41r13_run),
    )


def _initial_state(ctx: Stage41R14Context) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "oracle_development_complete": False,
        "calibrated_confirmation_complete": False,
        "formal_grid_confirmation_complete": False,
        "restart_audit_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R14Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R14Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.oracle_development,
        ctx.paths.calibrated_confirmation,
        ctx.paths.formal_grid_confirmation,
        ctx.paths.restart_audit,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.is_file():
        existing = read_json(ctx.paths.manifest)
        if existing.get("source_fingerprint", {}).get("digest") != ctx.source_fingerprint["digest"]:
            raise ValueError("R14 resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R14 resume controller revision mismatch")
        if existing.get("package_revision") != PACKAGE_REVISION:
            raise ValueError("R14 resume package revision mismatch")
    elif resume:
        raise FileNotFoundError("R14 resume requested but manifest is missing")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r14_config.resolved.json", ctx.cfg)
    for name, payload in (
        ("stage4_1r13_manifest.json", ctx.source_manifest),
        ("stage4_1r13_state.json", ctx.source_state),
        ("stage4_1r13_config.resolved.json", ctx.source_cfg),
        ("stage4_1r13_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "source_stage4_1r12_run": str(ctx.source_stage41r12_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": int(os.environ.get("STAGE4_1R14_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "fixed_first_affected_state_step": 23,
        "target_conditioned_nominal_retained": True,
        "checkpoint_integral_preserved": True,
        "arrival_deadline_expansion_allowed": False,
        "unseen_target_holdout_claimed": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "final_task": ctx.cfg["final_task"],
    }
    if not ctx.paths.manifest.is_file():
        atomic_write_json(ctx.paths.manifest, manifest)
    inventory = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory.is_file():
        atomic_write_json(inventory, ctx.source_fingerprint)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _source_raw(ctx: Stage41R14Context) -> list[dict[str, Any]]:
    return [read_json_gz(path) for path in sorted((ctx.source_stage41r13_run / "stage4_1r13_oracle_development" / "raw").glob("*.json.gz"))]


def _source_saturation(result: Mapping[str, Any]) -> dict[str, float]:
    spec = result["spec"]
    trace = list(result.get("anticipatory_damping_trace") or [])
    correction = np.asarray([row.get("mode_correction_physical", [0.0, 0.0, 0.0]) for row in trace], dtype=float)
    limit = np.asarray([0.2, 0.2, 0.07], dtype=float) * float(spec["terminal_controller_scale"])
    at = np.isclose(np.abs(correction), limit[None, :], atol=1e-6, rtol=0.0) if correction.size else np.zeros((0, 3), dtype=bool)
    return {
        "any_mode_bound_fraction": float(np.mean(np.any(at, axis=1))) if at.size else 0.0,
        "mode0_bound_fraction": float(np.mean(at[:, 0])) if at.size else 0.0,
        "mode1_bound_fraction": float(np.mean(at[:, 1])) if at.size else 0.0,
        "mode2_bound_fraction": float(np.mean(at[:, 2])) if at.size else 0.0,
    }


def run_source_audit(ctx: Stage41R14Context) -> dict[str, Any]:
    results = _source_raw(ctx)
    official = read_json(ctx.source_stage41r13_run / "stage4_1r13_oracle_development" / "results.json")
    row_by_id = {str(row["experiment_id"]): row for row in official}
    audit_rows: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        official_row = row_by_id[str(result["experiment_id"])]
        sat = _source_saturation(result)
        checkpoint = result.get("partial_main_control_checkpoint") or {}
        audit_rows.append(
            {
                "experiment_id": result["experiment_id"],
                "target_id": spec["target_id"],
                "actual_delay_steps": int(spec["action_delay_steps"]),
                "first_affected_state_step": int(spec["anticipatory_first_affected_state_step"]),
                "environment_success": bool(result.get("success")),
                "failure_reason": result.get("failure_reason", ""),
                "formal_contract_pass": bool(official_row.get("r13_composite_pass")),
                "formal_margin": _as_float(official_row.get("formal_contract_minimum_signed_margin"), -math.inf),
                "limiting_component": official_row.get("limiting_component"),
                "endpoint_late_speed_rms_m_per_s": _as_float(official_row.get("endpoint_late_speed_rms_m_per_s"), math.inf),
                "terminal_nominal_physical_mode": spec.get("terminal_nominal_physical_mode"),
                "terminal_integral_mode": spec.get("terminal_integral_mode"),
                "checkpoint_integral_l2": float(np.linalg.norm(np.asarray(checkpoint.get("integral_normalized", [0.0] * 5), dtype=float))),
                "library_task_ids": ",".join((result.get("library_interpolation") or {}).get("task_ids") or []),
                "any_mode_bound_fraction": sat["any_mode_bound_fraction"],
                "mode0_bound_fraction": sat["mode0_bound_fraction"],
                "mode1_bound_fraction": sat["mode1_bound_fraction"],
                "mode2_bound_fraction": sat["mode2_bound_fraction"],
                "max_current_utilization": _as_float(official_row.get("max_current_utilization"), math.inf),
                "solver_failure_steps": sum(not bool(row.get("solver_success")) for row in result.get("anticipatory_damping_trace") or []),
                "future_measurement_used": any(bool(row.get("future_measurement_used")) for row in result.get("anticipatory_damping_trace") or []),
                "streaming_queue_consistent": bool((result.get("anticipatory_damping_summary") or {}).get("streaming_queue_consistent")),
            }
        )
    required = ctx.cfg["source_requirement"]
    group_counts: dict[tuple[str, int], int] = {}
    for row in audit_rows:
        key = (str(row["target_id"]), int(row["actual_delay_steps"]))
        group_counts[key] = group_counts.get(key, 0) + int(bool(row["formal_contract_pass"]))
    onset_rows: list[dict[str, Any]] = []
    for first in range(20, 27):
        subset = [row for row in audit_rows if int(row["first_affected_state_step"]) == first]
        onset_rows.append(
            {
                "first_affected_state_step": first,
                "minimum_formal_margin": min((_as_float(row["formal_margin"], -math.inf) for row in subset), default=-math.inf),
                "mean_formal_margin": float(np.mean([_as_float(row["formal_margin"], -math.inf) for row in subset])) if subset else -math.inf,
                "pass_count": sum(bool(row["formal_contract_pass"]) for row in subset),
            }
        )
    global_best = max(onset_rows, key=lambda row: float(row["minimum_formal_margin"]))
    rz23 = {
        int(row["actual_delay_steps"]): row
        for row in audit_rows
        if row["target_id"] == "RZ_p10_m10" and int(row["first_affected_state_step"]) == 23
    }
    forensic = ctx.cfg["r13_forensic_contract"]
    passed = bool(
        len(results) == int(required["require_oracle_raw_count"])
        and len({result["experiment_id"] for result in results}) == len(results)
        and sum(bool(result.get("success")) for result in results) == int(required["expected_environment_success_count"])
        and all(not bool(result.get("failure_reason")) for result in results)
        and group_counts.get(("nominal", 1), 0) == int(required["expected_nominal_delay1_pass_count"])
        and group_counts.get(("nominal", 2), 0) == int(required["expected_nominal_delay2_pass_count"])
        and group_counts.get(("RZ_p10_m10", 1), 0) == int(required["expected_rz_delay1_pass_count"])
        and group_counts.get(("RZ_p10_m10", 2), 0) == int(required["expected_rz_delay2_pass_count"])
        and int(global_best["first_affected_state_step"]) == int(required["expected_global_minimax_first_effect_step"])
        and {str(row["limiting_component"]) for row in audit_rows} == {str(required["expected_limiting_component"])}
        and all(row["terminal_nominal_physical_mode"] == "zero_current_increment" for row in audit_rows)
        and all(row["terminal_integral_mode"] == "reset_zero" for row in audit_rows)
        and all(float(row["checkpoint_integral_l2"]) > 0.0 for row in audit_rows)
        and rz23[1]["any_mode_bound_fraction"] >= float(forensic["minimum_rz_state23_mode_bound_fraction_delay1"])
        and rz23[2]["any_mode_bound_fraction"] >= float(forensic["minimum_rz_state23_mode_bound_fraction_delay2"])
        and max(float(row["max_current_utilization"]) for row in audit_rows) <= float(forensic["maximum_observed_current_utilization"]) + 1e-12
        and all(int(row["solver_failure_steps"]) == 0 for row in audit_rows)
        and all(not bool(row["future_measurement_used"]) for row in audit_rows)
        and all(bool(row["streaming_queue_consistent"]) for row in audit_rows)
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "raw_rollouts": len(results),
        "unique_experiment_ids": len({result["experiment_id"] for result in results}),
        "environment_success_count": sum(bool(result.get("success")) for result in results),
        "failure_reason_count": sum(bool(result.get("failure_reason")) for result in results),
        "nominal_delay1_pass_count": group_counts.get(("nominal", 1), 0),
        "nominal_delay2_pass_count": group_counts.get(("nominal", 2), 0),
        "rz_delay1_pass_count": group_counts.get(("RZ_p10_m10", 1), 0),
        "rz_delay2_pass_count": group_counts.get(("RZ_p10_m10", 2), 0),
        "global_minimax_first_effect_state": int(global_best["first_affected_state_step"]),
        "global_minimax_margin": float(global_best["minimum_formal_margin"]),
        "all_failures_limited_by_endpoint_late_speed": {str(row["limiting_component"]) for row in audit_rows} == {"endpoint_late_speed"},
        "target_conditioned_nominal_was_discarded": all(row["terminal_nominal_physical_mode"] == "zero_current_increment" for row in audit_rows),
        "checkpoint_integral_was_reset": all(row["terminal_integral_mode"] == "reset_zero" for row in audit_rows),
        "all_checkpoint_integrals_nonzero": all(float(row["checkpoint_integral_l2"]) > 0.0 for row in audit_rows),
        "rz_state23_any_mode_bound_fraction": {"1": rz23[1]["any_mode_bound_fraction"], "2": rz23[2]["any_mode_bound_fraction"]},
        "maximum_current_utilization": max(float(row["max_current_utilization"]) for row in audit_rows),
        "formal_timing_contract_unchanged": True,
        "r11_2000ms_remains_auxiliary_only": True,
        "stage4_2r1_was_not_run_or_reused": True,
        "passed": passed,
        "interpretation": (
            "R13 ran correctly and found state 23 as the best onset. Nominal has passing candidates, but RZ has none. "
            "The handoff discarded the target-conditioned Stage3.4 nominal plan and reset a nonzero integral state; the first two residual modes then spent most steps at software correction bounds while physical current utilization stayed near 41%. R14 must restore the target-conditioned expert and add an explicit deadline-speed objective rather than scan another onset."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    write_csv(ctx.paths.source_audit / "r13_rollout_audit.csv", audit_rows)
    write_csv(ctx.paths.source_audit / "r13_onset_minimax.csv", onset_rows)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def solve_deadline_weighted_physical_correction(
    ctx_stub: Any,
    bundle: dict[str, Any],
    *,
    current_step: int,
    modeled_action_delay_steps: int,
    modeled_pending_physical_coefficients: Sequence[np.ndarray],
    nominal_physical_coefficients: np.ndarray,
    nominal_feature: np.ndarray,
    measurement_normalized: np.ndarray,
    integral_normalized: np.ndarray,
    previous_correction: np.ndarray,
    controller_scale: float,
    controller_model_scale: float,
    deadline_velocity_states: Sequence[int],
    deadline_velocity_weight_multiplier: float,
) -> dict[str, Any]:
    try:
        from scipy.optimize import lsq_linear
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage4.1R14 MPC") from exc
    current_step = int(current_step)
    delay = max(0, int(modeled_action_delay_steps))
    effect_step = min(current_step + delay, MAIN_HORIZON)
    if effect_step >= MAIN_HORIZON:
        return {
            "first_correction": np.zeros(N_MODES),
            "sequence_correction": np.zeros((0, N_MODES)),
            "solver_success": True,
            "solver_status": 0,
            "solver_cost": 0.0,
            "solver_optimality": 0.0,
            "predicted_normalized_residual_rms": 0.0,
            "active_lower": 0,
            "active_upper": 0,
            "effect_step": effect_step,
            "fixed_pending_steps": delay,
            "deadline_velocity_weight_multiplier": float(deadline_velocity_weight_multiplier),
            "deadline_velocity_row_count": 0,
        }
    jacobian = r3._scaled_jacobian(bundle, controller_model_scale)
    scales = np.asarray(bundle["output_scales"], dtype=float)
    rows = s34._future_feature_rows(current_step)
    projection = s34._measurement_bias_projection(ctx_stub, current_step, rows)
    integral_gain = np.asarray(ctx_stub.cfg["mpc"]["integral_measurement_gain"], dtype=float)
    effective_measurement = np.asarray(measurement_normalized, dtype=float) + integral_gain * np.asarray(integral_normalized, dtype=float)
    future_error = nominal_feature[np.asarray(rows)] / scales[np.asarray(rows)] + projection @ effective_measurement
    fixed_steps = list(range(current_step, min(effect_step, MAIN_HORIZON)))
    if fixed_steps:
        fixed_columns = [step * N_MODES + mode for step in fixed_steps for mode in range(N_MODES)]
        fixed_delta: list[float] = []
        for offset, step in enumerate(fixed_steps):
            if offset < len(modeled_pending_physical_coefficients):
                physical = np.asarray(modeled_pending_physical_coefficients[offset], dtype=float)
            else:
                physical = np.asarray(nominal_physical_coefficients[step], dtype=float)
            fixed_delta.extend((physical - nominal_physical_coefficients[step]).tolist())
        future_error = future_error + jacobian[np.ix_(rows, fixed_columns)] @ np.asarray(fixed_delta, dtype=float)
    free_steps = list(range(effect_step, MAIN_HORIZON))
    columns = [step * N_MODES + mode for step in free_steps for mode in range(N_MODES)]
    a = jacobian[np.ix_(rows, columns)]
    weights = s34._state_weight_vector(ctx_stub, rows, current_step)
    deadline_states = {int(value) for value in deadline_velocity_states}
    multiplier = float(deadline_velocity_weight_multiplier)
    deadline_count = 0
    for index, row in enumerate(rows):
        block = int(row) // MAIN_HORIZON
        state = int(row) % MAIN_HORIZON + 1
        if block in {2, 3} and state in deadline_states:
            weights[index] *= multiplier
            deadline_count += 1
    sqrt_w = np.sqrt(np.maximum(weights, 0.0))
    augmented_a: list[np.ndarray] = [sqrt_w[:, None] * a]
    augmented_b: list[np.ndarray] = [-sqrt_w * future_error]
    nominal_future = np.asarray(nominal_physical_coefficients, dtype=float)[free_steps].reshape(-1)
    lower_mode = np.asarray(ctx_stub.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx_stub.cfg["trajectory"]["coefficient_upper"], dtype=float)
    feedback_limit = np.asarray(ctx_stub.cfg["mpc"]["per_step_feedback_limit_by_mode"], dtype=float) * float(controller_scale)
    lower = np.maximum(np.tile(lower_mode, len(free_steps)) - nominal_future, -np.tile(feedback_limit, len(free_steps)))
    upper = np.minimum(np.tile(upper_mode, len(free_steps)) - nominal_future, np.tile(feedback_limit, len(free_steps)))
    ridge = float(ctx_stub.cfg["mpc"].get("ridge_lambda", 0.08))
    if ridge > 0.0:
        radius = np.maximum(np.tile(feedback_limit, len(free_steps)), 1e-8)
        augmented_a.append(math.sqrt(ridge) * np.diag(1.0 / radius))
        augmented_b.append(np.zeros(len(columns)))
    smooth = float(ctx_stub.cfg["mpc"].get("future_correction_smoothness", 0.08))
    if smooth > 0.0 and len(free_steps) > 1:
        from . import stage3_3_target_conditioned_mpc as s33
        difference = s33._difference_matrix(len(free_steps))
        augmented_a.append(math.sqrt(smooth) * difference)
        augmented_b.append(np.zeros(difference.shape[0]))
    rate = float(ctx_stub.cfg["mpc"].get("first_action_rate_weight", 0.20))
    if rate > 0.0:
        first_matrix = np.zeros((N_MODES, len(columns)))
        first_matrix[:, :N_MODES] = np.eye(N_MODES)
        augmented_a.append(math.sqrt(rate) * first_matrix)
        augmented_b.append(math.sqrt(rate) * np.asarray(previous_correction, dtype=float))
    solution = lsq_linear(
        np.vstack(augmented_a),
        np.concatenate(augmented_b),
        bounds=(lower, upper),
        method="trf",
        tol=float(ctx_stub.cfg["mpc"].get("solver_tolerance", 1e-8)),
        max_iter=int(ctx_stub.cfg["mpc"].get("solver_max_iterations", 300)),
        lsmr_tol="auto",
    )
    sequence = np.asarray(solution.x, dtype=float).reshape(len(free_steps), N_MODES)
    first = sequence[0]
    rate_limit = np.asarray(ctx_stub.cfg["mpc"]["per_step_correction_rate_limit_by_mode"], dtype=float)
    first = np.clip(first, np.asarray(previous_correction) - rate_limit, np.asarray(previous_correction) + rate_limit)
    first = np.clip(first, lower[:N_MODES], upper[:N_MODES])
    predicted = a @ np.asarray(solution.x) + future_error
    return {
        "first_correction": first,
        "sequence_correction": sequence,
        "solver_success": bool(solution.success),
        "solver_status": int(solution.status),
        "solver_cost": float(solution.cost),
        "solver_optimality": float(solution.optimality),
        "predicted_normalized_residual_rms": float(np.sqrt(np.mean(predicted**2))),
        "active_lower": int(np.sum(np.isclose(solution.x, lower, atol=1e-7))),
        "active_upper": int(np.sum(np.isclose(solution.x, upper, atol=1e-7))),
        "effect_step": effect_step,
        "fixed_pending_steps": len(fixed_steps),
        "deadline_velocity_weight_multiplier": multiplier,
        "deadline_velocity_row_count": deadline_count,
    }


class LocalStage41R14Worker:
    """Run a causal partial main-MPC prefix then an integrated deadline MPC.

    The first physical effect is fixed at state 23.  The partial checkpoint
    preserves the actual TSC state, delay queue, previous correction and
    accumulated integral.  R14 reconstructs the exact target-conditioned
    Stage3.4 nominal plan and continues the same physical-coordinate MPC with
    extra velocity weight at states 24--27.  A two-step target hold keeps the
    delay queue streaming after the 35-step identified horizon.
    """

    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.r9_worker = r9.LocalStage41R9Worker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base_worker = self.r9_worker.base_worker
        self.bundle = bundle
        self.library = library
        self.horizon_steps = int(payload.get("stage4_1r4_horizon_steps", MAIN_HORIZON))

    def close(self) -> None:
        self.r9_worker.close()

    def _cleanup_episode(self, *, failed: bool, reason: str) -> None:
        runner = getattr(self.base_worker.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=failed, reason=reason)

    @staticmethod
    def _history_values(trajectory: Sequence[Mapping[str, Any]]) -> list[np.ndarray]:
        return [
            np.asarray([row["R"], row["Z"], row["Ip"]], dtype=float)
            for row in trajectory
        ]

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": spec.get("experiment_id", "unknown"),
            "spec": copy.deepcopy(spec),
            "success": False,
            "failure_reason": "",
            "trajectory": [],
            "control_trace": [],
        }
        failed = True
        try:
            actual_slew = float(spec["slew_scale"])
            modeled_slew = float(spec["controller_slew_scale_estimate"])
            actual_delay = int(spec["action_delay_steps"])
            modeled_delay = int(spec["controller_action_delay_steps"])
            if not bool(spec.get("trusted_calibration_model", False)):
                raise ValueError("R14 may not start from an untrusted actuator model")
            if not math.isclose(actual_slew, WEAK_SLEW, abs_tol=1e-12):
                raise ValueError("R14 modifies only 0.9x slew")
            if actual_delay not in {1, 2}:
                raise ValueError("R14 modifies only weak-slew delay=1/2")
            if actual_delay != modeled_delay or not math.isclose(actual_slew, modeled_slew, abs_tol=1e-12):
                raise ValueError("R14 trusted finite model must match the actual pair")
            horizon = int(spec["horizon_steps"])
            if horizon != WEAK_HORIZON or horizon != self.horizon_steps:
                raise ValueError("R14 environment horizon must remain exactly 37 steps")
            first_affected_state = int(spec["anticipatory_first_affected_state_step"])
            if first_affected_state != 23:
                raise ValueError("R14 first physical effect is fixed at state 23")
            issue_start = _transition_issue_step(first_affected_state, actual_delay)
            if int(spec["anticipatory_transition_issue_step"]) != issue_start:
                raise ValueError("R14 transition issue/effect alignment mismatch")

            internal = copy.deepcopy(spec)
            internal["_defer_cleanup"] = True
            internal["_stage4_1r12_main_control_stop_step"] = issue_start
            internal["extended_horizon"] = False
            internal["tail_hold_steps"] = 0
            internal["tail_action_policy"] = "none"
            partial = self.base_worker.evaluate(internal)
            partial["spec"] = copy.deepcopy(spec)
            if not partial.get("success"):
                partial["controller_revision"] = CONTROLLER_REVISION
                partial["stage4_1r14_controller_revision"] = CONTROLLER_REVISION
                result = partial
                return _json_safe(result)

            trajectory = copy.deepcopy(list(partial.get("trajectory") or []))
            main_trace = copy.deepcopy(list(partial.get("control_trace") or []))
            if len(trajectory) != issue_start + 1 or len(main_trace) != issue_start:
                raise ValueError("R14 partial main-control prefix length mismatch")
            checkpoint = partial.get("partial_main_control_checkpoint") or {}
            if int(checkpoint.get("state_index", -1)) != issue_start:
                raise ValueError("R14 partial checkpoint state mismatch")
            if bool(checkpoint.get("future_measurement_used", True)):
                raise ValueError("R14 partial checkpoint used future measurement")
            checkpoint_queue = list(checkpoint.get("queue") or [])
            if len(checkpoint_queue) != actual_delay:
                raise ValueError("R14 partial main-control queue length mismatch")
            queue = [
                {
                    "origin": "main_control",
                    "origin_index": issue_start - actual_delay + index,
                    "command": np.asarray(item["command"], dtype=float).reshape(N_MODES),
                    "desired_physical": np.asarray(item["desired_physical"], dtype=float).reshape(N_MODES),
                }
                for index, item in enumerate(checkpoint_queue)
            ]
            previous_correction = np.asarray(
                checkpoint.get("previous_correction_physical", np.zeros(N_MODES)),
                dtype=float,
            ).reshape(N_MODES)
            integral = np.asarray(
                checkpoint.get("integral_normalized", np.zeros(5)), dtype=float
            ).reshape(5)
            checkpoint_integral = integral.copy()

            offset = np.asarray(
                [
                    float(spec.get("target_R_offset_m", 0.0)),
                    float(spec.get("target_Z_offset_m", 0.0)),
                    float(spec.get("target_Ip_offset_A", 0.0)),
                ],
                dtype=float,
            )
            interpolation = s34.interpolation_for_target(
                self.base_worker.stub, self.library, offset
            )
            nominal_physical = np.asarray(
                interpolation["full_control_vector"], dtype=float
            ).reshape(MAIN_HORIZON, N_MODES)
            nominal_y = np.asarray(
                interpolation["nominal_trajectory_RZI"], dtype=float
            )
            nominal_velocity = np.asarray(
                interpolation["nominal_velocity_RZ"], dtype=float
            )
            requested_target = np.asarray(
                [
                    float(self.base_worker.cfg["target"]["R"]) + offset[0],
                    float(self.base_worker.cfg["target"]["Z"]) + offset[1],
                    float(self.base_worker.cfg["target"]["Ip"]) + offset[2],
                ],
                dtype=float,
            )
            nominal_feature = s34._nominal_feature(
                nominal_y, nominal_velocity, requested_target
            )
            if not np.any(np.abs(nominal_physical[issue_start:]) > 0.0):
                raise ValueError("R14 target-conditioned nominal feedforward is unexpectedly zero")

            scales_cfg = self.base_worker.cfg["identification"]["output_scales"]
            measurement_scales = np.asarray(
                [
                    scales_cfg["R_m"],
                    scales_cfg["Z_m"],
                    scales_cfg["vR_m_per_s"],
                    scales_cfg["vZ_m_per_s"],
                    scales_cfg["Ip_A"],
                ],
                dtype=float,
            )
            dt_s = float(self.base_worker.env_cfg["dt_ms"]) / 1000.0
            controller_scale = float(spec["integrated_controller_scale"])
            model_scale = float(spec.get("integrated_controller_model_scale", 1.0))
            deadline_multiplier = float(spec["deadline_velocity_weight_multiplier"])
            deadline_states = [int(value) for value in spec["deadline_velocity_states"]]
            tail_scale = float(spec["tail_controller_scale"])
            tail_phase_cap = int(spec["tail_model_phase_cap_step"])
            actual_gain = np.asarray(
                spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]), dtype=float
            ).reshape(N_MODES)
            controller_gain = np.asarray(
                spec.get("controller_gain_estimate_by_mode", [1.0, 1.0, 1.0]),
                dtype=float,
            ).reshape(N_MODES)
            actuator_bias = np.asarray(
                spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]), dtype=float
            ).reshape(N_MODES)

            integrated_trace: list[dict[str, Any]] = []
            streaming_consistent = True
            failure_reason = ""
            for env_step in range(issue_start, horizon):
                histories = self._history_values(trajectory)
                if len(histories) != env_step + 1:
                    raise ValueError("R14 measurement history length mismatch")
                modeled_pending = [
                    np.asarray(item["desired_physical"], dtype=float)
                    for item in queue[:modeled_delay]
                ]
                if len(modeled_pending) != modeled_delay:
                    raise ValueError("R14 modeled pending queue length mismatch")

                if env_step < MAIN_HORIZON:
                    measurement_physical = r3.legacy_measurement_error(
                        histories,
                        delayed_local_index=len(histories) - 1,
                        delayed_absolute_index=env_step,
                        current_absolute_index=env_step,
                        nominal_y=nominal_y,
                        nominal_velocity=nominal_velocity,
                        dt_s=dt_s,
                    )
                    measurement_normalized = measurement_physical / measurement_scales
                    integral_previous = integral.copy()
                    integral_candidate = self.base_worker._integral_candidate(
                        integral_previous,
                        measurement_normalized,
                        reference_step=env_step,
                        anti_windup_enabled=False,
                    )
                    solve = solve_deadline_weighted_physical_correction(
                        self.base_worker.stub,
                        self.bundle,
                        current_step=env_step,
                        modeled_action_delay_steps=modeled_delay,
                        modeled_pending_physical_coefficients=modeled_pending,
                        nominal_physical_coefficients=nominal_physical,
                        nominal_feature=nominal_feature,
                        measurement_normalized=measurement_normalized,
                        integral_normalized=integral_candidate,
                        previous_correction=previous_correction,
                        controller_scale=controller_scale,
                        controller_model_scale=model_scale,
                        deadline_velocity_states=deadline_states,
                        deadline_velocity_weight_multiplier=deadline_multiplier,
                    )
                    correction = np.asarray(solve["first_correction"], dtype=float).reshape(N_MODES)
                    integral = integral_candidate
                    effect_step = min(int(solve.get("effect_step", env_step)), MAIN_HORIZON - 1)
                    feedforward = nominal_physical[effect_step]
                    desired_physical = np.clip(
                        feedforward + correction,
                        self.base_worker.lower_mode,
                        self.base_worker.upper_mode,
                    )
                    phase = "integrated_target_conditioned_deadline_mpc"
                    measurement_for_solver = measurement_normalized
                else:
                    measurement_physical = r9._terminal_measurement(
                        trajectory, requested_target, dt_s
                    )
                    measurement_normalized, measurement_for_solver = r12._measurement_for_solver(
                        measurement_physical,
                        measurement_scales,
                        position_gain=float(spec["tail_position_measurement_gain"]),
                        velocity_gain=float(spec["tail_velocity_measurement_gain"]),
                        ip_gain=float(spec["tail_ip_measurement_gain"]),
                    )
                    zero_nominal = np.zeros((MAIN_HORIZON, N_MODES), dtype=float)
                    zero_feature = np.zeros(MAIN_HORIZON * 5, dtype=float)
                    solve = r3.solve_delay_aware_physical_correction(
                        self.base_worker.stub,
                        self.bundle,
                        current_step=tail_phase_cap,
                        modeled_action_delay_steps=modeled_delay,
                        modeled_pending_physical_coefficients=modeled_pending,
                        nominal_physical_coefficients=zero_nominal,
                        nominal_feature=zero_feature,
                        measurement_normalized=measurement_for_solver,
                        integral_normalized=np.zeros(5, dtype=float),
                        previous_correction=previous_correction,
                        controller_scale=tail_scale,
                        controller_model_scale=model_scale,
                    )
                    correction = np.asarray(solve["first_correction"], dtype=float).reshape(N_MODES)
                    feedforward = np.zeros(N_MODES, dtype=float)
                    desired_physical = np.clip(
                        correction,
                        self.base_worker.lower_mode,
                        self.base_worker.upper_mode,
                    )
                    phase = "post_main_horizon_target_hold"

                currents_before = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                scheduled = self.base_worker.scheduler.solve_command(
                    desired_physical,
                    currents_before,
                    controller_gain,
                    modeled_slew,
                    enabled=True,
                )
                issued_command = np.asarray(
                    scheduled["command"], dtype=float
                ).reshape(N_MODES)
                issued_item = {
                    "origin": "integrated_deadline_mpc",
                    "origin_index": int(env_step),
                    "command": issued_command,
                    "desired_physical": desired_physical,
                }
                queue_before = r9._queue_origins(queue)
                applied_item, queue = r9._stream_queue_apply(
                    queue, issued_item, actual_delay
                )
                if len(queue) != actual_delay:
                    streaming_consistent = False
                applied_command = np.asarray(
                    applied_item["command"], dtype=float
                ).reshape(N_MODES)
                effective = actual_gain * applied_command + actuator_bias
                action = self.base_worker._mode_action(effective, currents_before)
                _, _, terminated, truncated, info = self.base_worker.env.step(action)
                state_index = env_step + 1
                trajectory.append(
                    r3.base._state_record(self.base_worker.env, state_index, action)
                )
                currents_after = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                row = {
                    "step": int(env_step),
                    "reference_step": int(min(env_step, MAIN_HORIZON - 1)),
                    "issue_step": int(env_step),
                    "state_index_before": int(env_step),
                    "state_index_after": int(state_index),
                    "phase": phase,
                    "first_affected_state_step": int(first_affected_state),
                    "transition_issue_start_step": int(issue_start),
                    "measurement_max_state_index_used": int(env_step),
                    "future_measurement_used": False,
                    "measurement_source": (
                        "target_conditioned_nominal_residual"
                        if env_step < MAIN_HORIZON
                        else "direct_target_hold"
                    ),
                    "measurement_physical": np.asarray(measurement_physical, dtype=float).tolist(),
                    "measurement_normalized": np.asarray(measurement_normalized, dtype=float).tolist(),
                    "measurement_for_solver": np.asarray(measurement_for_solver, dtype=float).tolist(),
                    "modeled_action_delay_steps": int(modeled_delay),
                    "actual_action_delay_steps": int(actual_delay),
                    "queue_before": queue_before,
                    "queue_after": r9._queue_origins(queue),
                    "issued_origin": {"origin": "integrated_deadline_mpc", "origin_index": int(env_step)},
                    "applied_origin": {
                        "origin": str(applied_item["origin"]),
                        "origin_index": int(applied_item["origin_index"]),
                    },
                    "target_conditioned_nominal_retained": env_step < MAIN_HORIZON,
                    "checkpoint_integral_preserved": True,
                    "checkpoint_integral_l2": float(np.linalg.norm(checkpoint_integral)),
                    "integral_normalized": integral.tolist(),
                    "feedforward_physical_mode_coefficients": feedforward.tolist(),
                    "mode_correction_physical": correction.tolist(),
                    "previous_correction_physical": previous_correction.tolist(),
                    "desired_physical_mode_coefficients": desired_physical.tolist(),
                    "issued_desired_physical_mode_coefficients": desired_physical.tolist(),
                    "issued_mode_coefficients": issued_command.tolist(),
                    "applied_desired_physical_mode_coefficients": np.asarray(applied_item["desired_physical"], dtype=float).tolist(),
                    "applied_command_mode_coefficients": applied_command.tolist(),
                    "effective_mode_coefficients": effective.tolist(),
                    "deadline_velocity_weight_multiplier": deadline_multiplier,
                    "deadline_velocity_states": deadline_states,
                    "integrated_controller_scale": controller_scale,
                    "solver_success": bool(solve.get("solver_success", False)),
                    "solver_status": int(solve.get("solver_status", 0)),
                    "solver_cost": float(solve.get("solver_cost", 0.0)),
                    "solver_effect_step": int(solve.get("effect_step", -1)),
                    "solver_fixed_pending_steps": int(solve.get("fixed_pending_steps", modeled_delay)),
                    "solver_deadline_velocity_row_count": int(solve.get("deadline_velocity_row_count", 0)),
                    "solver_active_lower": int(solve.get("active_lower", 0)),
                    "solver_active_upper": int(solve.get("active_upper", 0)),
                    "predicted_normalized_residual_rms": float(solve.get("predicted_normalized_residual_rms", 0.0)),
                    "scheduler_predicted_mismatch_rms_a": float(scheduled.get("mismatch_rms_a", 0.0)),
                    "scheduler_predicted_mismatch_max_abs_a": float(scheduled.get("mismatch_max_abs_a", 0.0)),
                    "currents_before_A": currents_before.tolist(),
                    "currents_after_A": currents_after.tolist(),
                    "actual_current_delta_A": (currents_after - currents_before).tolist(),
                    "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                }
                integrated_trace.append(row)
                previous_correction = correction.copy()
                if terminated:
                    failure_reason = str(info.get("failure_reason", "R14 controller terminated"))
                    break
                if truncated and state_index < horizon:
                    failure_reason = "environment truncated before R14 370 ms horizon"
                    break

            combined_trace = main_trace + integrated_trace
            first_observed_affected_state: int | None = None
            for row in integrated_trace:
                if str((row.get("applied_origin") or {}).get("origin")) == "integrated_deadline_mpc":
                    first_observed_affected_state = int(row["state_index_after"])
                    break
            success = bool(
                len(trajectory) == horizon + 1
                and len(combined_trace) == horizon
                and not failure_reason
                and not any(bool(row.get("abnormal", False)) for row in trajectory)
                and streaming_consistent
                and all(bool(row.get("solver_success")) for row in integrated_trace)
            )
            result = copy.deepcopy(partial)
            result.update(
                {
                    "schema_version": SCHEMA_VERSION,
                    "controller_revision": CONTROLLER_REVISION,
                    "stage4_1r14_controller_revision": CONTROLLER_REVISION,
                    "experiment_id": spec["experiment_id"],
                    "spec": copy.deepcopy(spec),
                    "success": success,
                    "failure_reason": "" if success else (failure_reason or "incomplete/abnormal R14 trajectory"),
                    "trajectory": trajectory,
                    "control_trace": combined_trace,
                    "main_control_trace": main_trace,
                    "integrated_deadline_mpc_trace": integrated_trace,
                    "anticipatory_damping_trace": integrated_trace,
                    "tail_queue_trace": integrated_trace,
                    "library_interpolation": interpolation,
                    "partial_main_control_checkpoint": checkpoint,
                    "integrated_deadline_mpc_summary": {
                        "policy_id": spec["anticipatory_policy_id"],
                        "first_affected_state_step": first_affected_state,
                        "transition_issue_start_step": issue_start,
                        "expected_first_affected_state_step": issue_start + actual_delay + 1,
                        "observed_first_affected_state_step": first_observed_affected_state,
                        "actual_delay_steps": actual_delay,
                        "modeled_delay_steps": modeled_delay,
                        "horizon_steps": horizon,
                        "control_steps": len(integrated_trace),
                        "main_integrated_steps": sum(row["phase"] == "integrated_target_conditioned_deadline_mpc" for row in integrated_trace),
                        "tail_hold_steps": sum(row["phase"] == "post_main_horizon_target_hold" for row in integrated_trace),
                        "target_conditioned_nominal_retained": True,
                        "checkpoint_integral_preserved": True,
                        "checkpoint_integral_l2": float(np.linalg.norm(checkpoint_integral)),
                        "deadline_velocity_weight_multiplier": deadline_multiplier,
                        "deadline_velocity_states": deadline_states,
                        "controller_scale": controller_scale,
                        "continuous_streaming_queue": True,
                        "streaming_queue_consistent": streaming_consistent,
                        "final_pending_count": len(queue),
                        "final_pending_origins": r9._queue_origins(queue),
                        "future_measurement_used": False,
                    },
                    # Compatibility fields let the validated R12/R13 prefix and metric
                    # auditors inspect the new controller without weakening guards.
                    "anticipatory_damping_summary": {
                        "policy_id": spec["anticipatory_policy_id"],
                        "first_affected_state_step": first_affected_state,
                        "transition_issue_start_step": issue_start,
                        "expected_first_affected_state_step": issue_start + actual_delay + 1,
                        "observed_first_affected_state_step": first_observed_affected_state,
                        "actual_delay_steps": actual_delay,
                        "modeled_delay_steps": modeled_delay,
                        "horizon_steps": horizon,
                        "damping_control_steps": len(integrated_trace),
                        "continuous_streaming_queue": True,
                        "streaming_queue_consistent": streaming_consistent,
                        "final_pending_count": len(queue),
                        "final_pending_origins": r9._queue_origins(queue),
                        "future_measurement_used": False,
                    },
                    "wall_time_s": float(time.time() - started),
                }
            )
            failed = not success
            return _json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "failure_reason": repr(exc),
                    "traceback": traceback.format_exc(),
                    "wall_time_s": float(time.time() - started),
                }
            )
            failed = True
            return _json_safe(result)
        finally:
            self._cleanup_episode(
                failed=failed,
                reason=str(result.get("failure_reason", "stage4_1r14_complete")),
            )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage41R14Actor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalStage41R14Worker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R14Actor
    return _RAY_ACTOR


def materialize_variant(ctx: Stage41R14Context) -> tuple[str, dict[str, Any]]:
    variant, payload = r10.materialize_variant(
        ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx,
        slew_scale=WEAK_SLEW,
        horizon_steps=WEAK_HORIZON,
    )
    atomic_write_json(ctx.paths.variants / f"{variant}.payload.json", payload)
    return variant, payload


def evaluate_specs(
    ctx: Stage41R14Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variant, payload = materialize_variant(ctx)
    chain = ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx
    chain.variants[variant] = payload
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(output_dir / f"{spec['experiment_id']}.json.gz"))
    ]
    library = chain.r3_ctx.source_library
    bundle = chain.r3_ctx.source_bundle
    selector_cfg = ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg["batch_selector"]
    if backend == "serial":
        worker = LocalStage41R14Worker(
            payload, library, bundle, "stage41r14_serial", selector_cfg
        )
        try:
            for index, spec in enumerate(pending, 1):
                atomic_write_json_gz(
                    output_dir / f"{spec['experiment_id']}.json.gz",
                    worker.evaluate(spec),
                )
                print(f"[Stage4.1R14 {variant}] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        requested = int(
            os.environ.get("STAGE4_1R14_WORKERS", ctx.cfg["parallel"]["n_workers"])
        )
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get(
                "RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")
            )
            or None,
            log_prefix="[Stage4.1R14 integrated-deadline-mpc]",
        )
        Actor = _ray_actor_class()
        actors = [
            Actor.remote(
                payload,
                library,
                bundle,
                f"stage41r14_{index:03d}",
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
                        f"[Stage4.1R14 integrated-deadline-mpc] waiting {done}/{len(pending)}",
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
                            f"[Stage4.1R14 integrated-deadline-mpc] {done}/{len(pending)}",
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


def _source_scale(ctx: Stage41R14Context) -> float:
    return float(
        ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )


def _make_spec(
    *,
    phase: str,
    policy: Mapping[str, Any],
    target: Mapping[str, Any],
    actual_delay: int,
    modeled_delay: int,
    calibration_token: str | None,
    trusted: bool,
    controller_variant: str,
    environment_variant: str,
    ctx: Stage41R14Context,
) -> dict[str, Any]:
    design = ctx.cfg["integrated_deadline_mpc"]
    first_affected = int(design["fixed_first_affected_state_step"])
    issue_start = _transition_issue_step(first_affected, modeled_delay)
    generic_policy = {
        "horizon_steps": WEAK_HORIZON,
        "tail_steps": 0,
        "tail_policy": "r14_integrated_target_conditioned_deadline_mpc",
        "policy_id": str(policy["policy_id"]),
    }
    extra = r8._main_extra(
        ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
        actual_delay=int(actual_delay),
        actual_slew=WEAK_SLEW,
        modeled_delay=int(modeled_delay),
        modeled_slew=WEAK_SLEW,
        policy=generic_policy,
        variant=controller_variant,
        monitor_enabled=False,
        calibration_token=calibration_token,
        trusted=trusted,
    )
    extra.update(
        {
            "horizon_steps": WEAK_HORIZON,
            "tail_feedback_steps": 0,
            "tail_steps": 0,
            "tail_policy": "r14_integrated_target_conditioned_deadline_mpc",
            # Compatibility names are retained for the independently validated
            # R12/R13 prefix auditor; the controller itself is new and identified
            # by the integrated_* fields below.
            "anticipatory_policy_id": str(policy["policy_id"]),
            "anticipatory_first_affected_state_step": first_affected,
            "anticipatory_transition_issue_step": issue_start,
            "integrated_deadline_velocity_weight_multiplier": float(
                policy["deadline_velocity_weight_multiplier"]
            ),
            "deadline_velocity_weight_multiplier": float(
                policy["deadline_velocity_weight_multiplier"]
            ),
            "deadline_velocity_states": [
                int(value) for value in design["deadline_velocity_states"]
            ],
            "integrated_controller_scale": float(policy["controller_scale"]),
            "integrated_controller_model_scale": float(
                design["main_phase_model_scale"]
            ),
            "tail_model_phase_cap_step": int(
                design["tail_model_phase_cap_step"]
            ),
            "tail_controller_scale": float(design["tail_controller_scale"]),
            "tail_velocity_measurement_gain": float(
                design["tail_velocity_measurement_gain"]
            ),
            "tail_position_measurement_gain": float(
                design["tail_position_measurement_gain"]
            ),
            "tail_ip_measurement_gain": float(
                design["tail_ip_measurement_gain"]
            ),
            "target_conditioned_nominal_physical_required": True,
            "target_conditioned_nominal_feature_required": True,
            "checkpoint_integral_preservation_required": True,
            "formal_arrival_deadline_step": 27,
            "formal_hold_through_step": 37,
            "arrival_deadline_expansion_allowed": False,
            "normal_slew_controller_changed": False,
            "r14_selection_conditioned_on_trusted_delay": True,
            "r14_fixed_first_effect_no_onset_rescan": True,
        }
    )
    identity = {
        "revision": CONTROLLER_REVISION,
        "phase": phase,
        "policy": dict(policy),
        "target": dict(target),
        "actual_delay": int(actual_delay),
        "modeled_delay": int(modeled_delay),
        "calibration_token": calibration_token,
        "environment_variant": environment_variant,
    }
    return {
        "kind": "stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc",
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": _scenario_digest(identity),
        "phase": phase,
        "scenario": f"{policy['policy_id']}__{target['target_id']}__d{actual_delay}__s0.9",
        "category": phase,
        "target_id": str(target["target_id"]),
        "target_R_offset_m": float(target.get("R_offset_m", 0.0)),
        "target_Z_offset_m": float(target.get("Z_offset_m", 0.0)),
        "target_Ip_offset_A": float(target.get("Ip_offset_A", 0.0)),
        "controller_scale": _source_scale(ctx),
        "environment_variant": environment_variant,
        **copy.deepcopy(extra),
    }


def build_development_specs(ctx: Stage41R14Context) -> list[dict[str, Any]]:
    design = ctx.cfg["integrated_deadline_mpc"]
    variant, _ = materialize_variant(ctx)
    specs: list[dict[str, Any]] = []
    for policy in design["candidate_bank"]:
        for delay in design["actual_delay_steps"]:
            for target in design["required_targets"]:
                specs.append(
                    _make_spec(
                        phase="oracle_development",
                        policy=policy,
                        target=target,
                        actual_delay=int(delay),
                        modeled_delay=int(delay),
                        calibration_token=None,
                        trusted=True,
                        controller_variant="r14_oracle_development",
                        environment_variant=variant,
                        ctx=ctx,
                    )
                )
    return specs


def _selected_policy_by_delay(ctx: Stage41R14Context) -> dict[int, dict[str, Any]]:
    if not ctx.paths.state.is_file():
        return {}
    selected = (
        (read_json(ctx.paths.state).get("oracle_development_summary") or {}).get(
            "selected_policy_by_delay"
        )
        or {}
    )
    bank = {
        str(row["policy_id"]): copy.deepcopy(row)
        for row in ctx.cfg["integrated_deadline_mpc"]["candidate_bank"]
    }
    output: dict[int, dict[str, Any]] = {}
    for delay_text, policy_id in selected.items():
        if str(policy_id) not in bank:
            raise ValueError(f"selected R14 policy is not in candidate bank: {policy_id}")
        output[int(delay_text)] = bank[str(policy_id)]
    return output


def _trusted_tokens(ctx: Stage41R14Context) -> dict[tuple[int, float], dict[str, Any]]:
    return r13._trusted_tokens(ctx.r13_ctx)


def build_calibrated_specs(ctx: Stage41R14Context) -> list[dict[str, Any]]:
    state = read_json(ctx.paths.state)
    if not bool((state.get("oracle_development_summary") or {}).get("passed")):
        return []
    selected = _selected_policy_by_delay(ctx)
    if set(selected) != {1, 2}:
        return []
    tokens = _trusted_tokens(ctx)
    variant, _ = materialize_variant(ctx)
    specs: list[dict[str, Any]] = []
    for delay in (1, 2):
        token = tokens[(delay, WEAK_SLEW)]
        if not bool(token.get("batch_trusted_correct")) or bool(
            token.get("batch_wrong_accept")
        ):
            raise ValueError(f"R14 untrusted calibration token for delay={delay}")
        for target in ctx.cfg["calibrated_confirmation"]["targets"]:
            specs.append(
                _make_spec(
                    phase="calibrated_confirmation",
                    policy=selected[delay],
                    target=target,
                    actual_delay=delay,
                    modeled_delay=int(token["batch_selected_delay_steps"]),
                    calibration_token=str(token["experiment_id"]),
                    trusted=True,
                    controller_variant="r14_calibrated_confirmation",
                    environment_variant=variant,
                    ctx=ctx,
                )
            )
    return specs


def _physics_array(result: Mapping[str, Any], *, count: int | None = None) -> np.ndarray:
    return r13._physics_array(result, count=count)


def _control_array(
    result: Mapping[str, Any], field: str, *, count: int | None = None
) -> np.ndarray:
    return r13._control_array(result, field, count=count)


def _integrated_array(result: Mapping[str, Any], field: str) -> np.ndarray:
    return np.asarray(
        [row.get(field, [0.0] * N_MODES) for row in result.get("integrated_deadline_mpc_trace") or []],
        dtype=float,
    )


def _source_oracle_map(ctx: Stage41R14Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    return r13._source_oracle_map(ctx.r13_ctx)


def _source_calibrated_map(ctx: Stage41R14Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    return r13._source_calibrated_map(ctx.r13_ctx)


def _timing_policy(ctx: Stage41R14Context, slew: float, *, policy_id: str) -> dict[str, Any]:
    return r13._timing_policy(ctx.r13_ctx, slew, policy_id=policy_id)


def _slice_result(result: Mapping[str, Any], horizon: int) -> dict[str, Any]:
    return r13._slice_result(result, horizon)


def result_row(ctx: Stage41R14Context, result: Mapping[str, Any]) -> dict[str, Any]:
    base = r13.result_row(ctx.r13_ctx, result)
    base["r14_composite_pass"] = bool(base.pop("r13_composite_pass"))
    trace = list(result.get("integrated_deadline_mpc_trace") or [])
    summary = result.get("integrated_deadline_mpc_summary") or {}
    main_rows = [row for row in trace if row.get("phase") == "integrated_target_conditioned_deadline_mpc"]
    any_bound = []
    mode_bound = [[], [], []]
    scale = float((result.get("spec") or {}).get("integrated_controller_scale", 0.0))
    limit = np.asarray([0.2, 0.2, 0.07], dtype=float) * scale
    for row in main_rows:
        correction = np.asarray(row.get("mode_correction_physical", [0.0] * 3), dtype=float)
        at = np.isclose(np.abs(correction), limit, atol=1e-6, rtol=0.0)
        any_bound.append(bool(np.any(at)))
        for index in range(3):
            mode_bound[index].append(bool(at[index]))
    base.update(
        {
            "deadline_velocity_weight_multiplier": (result.get("spec") or {}).get(
                "deadline_velocity_weight_multiplier"
            ),
            "integrated_controller_scale": scale,
            "target_conditioned_nominal_retained": bool(
                summary.get("target_conditioned_nominal_retained")
            ),
            "checkpoint_integral_preserved": bool(
                summary.get("checkpoint_integral_preserved")
            ),
            "checkpoint_integral_l2": summary.get("checkpoint_integral_l2"),
            "main_integrated_steps": summary.get("main_integrated_steps"),
            "tail_hold_steps": summary.get("tail_hold_steps"),
            "any_mode_bound_fraction": float(np.mean(any_bound)) if any_bound else 0.0,
            "mode0_bound_fraction": float(np.mean(mode_bound[0])) if mode_bound[0] else 0.0,
            "mode1_bound_fraction": float(np.mean(mode_bound[1])) if mode_bound[1] else 0.0,
            "mode2_bound_fraction": float(np.mean(mode_bound[2])) if mode_bound[2] else 0.0,
            "integrated_issued_signature": _array_digest(
                _integrated_array(result, "issued_mode_coefficients"),
                "integratedissued",
            ),
            "integrated_applied_signature": _array_digest(
                _integrated_array(result, "applied_command_mode_coefficients"),
                "integratedapplied",
            ),
        }
    )
    return base


def _candidate_summary(
    ctx: Stage41R14Context,
    rows: Sequence[Mapping[str, Any]],
    *,
    policy: Mapping[str, Any],
    delay: int,
) -> dict[str, Any]:
    policy_id = str(policy["policy_id"])
    subset = [
        row
        for row in rows
        if str(row.get("policy_id")) == policy_id
        and int(row.get("actual_delay_steps")) == int(delay)
    ]
    required_targets = {
        str(row["target_id"])
        for row in ctx.cfg["integrated_deadline_mpc"]["required_targets"]
    }
    coverage = bool(
        len(subset) == len(required_targets)
        and {str(row["target_id"]) for row in subset} == required_targets
    )
    pass_fraction = (
        sum(bool(row.get("r14_composite_pass")) for row in subset) / len(subset)
        if subset
        else 0.0
    )
    minimum_margin = min(
        (
            _as_float(row.get("formal_contract_minimum_signed_margin"), -1e12)
            for row in subset
        ),
        default=-1e12,
    )
    mean_margin = (
        float(
            np.mean(
                [
                    _as_float(
                        row.get("formal_contract_minimum_signed_margin"), -1e12
                    )
                    for row in subset
                ]
            )
        )
        if subset
        else -1e12
    )
    max_terminal_speed = max(
        (_as_float(row.get("terminal_speed_m_per_s"), math.inf) for row in subset),
        default=math.inf,
    )
    mean_action_rms = (
        float(np.mean([_as_float(row.get("action_rms"), math.inf) for row in subset]))
        if subset
        else math.inf
    )
    design = ctx.cfg["integrated_deadline_mpc"]
    passed = bool(
        coverage
        and pass_fraction
        >= float(design["minimum_target_pass_fraction_per_delay"])
        and minimum_margin
        >= float(design["minimum_tracking_signed_margin"]) - 1e-12
        and all(bool(row.get("target_conditioned_nominal_retained")) for row in subset)
        and all(bool(row.get("checkpoint_integral_preserved")) for row in subset)
    )
    return {
        "policy_id": policy_id,
        "actual_delay_steps": int(delay),
        "fixed_first_affected_state_step": int(
            design["fixed_first_affected_state_step"]
        ),
        "deadline_velocity_weight_multiplier": float(
            policy["deadline_velocity_weight_multiplier"]
        ),
        "controller_scale": float(policy["controller_scale"]),
        "n_rollouts": len(subset),
        "expected_rollouts": len(required_targets),
        "target_coverage_complete": coverage,
        "target_pass_fraction": pass_fraction,
        "minimum_formal_signed_margin": minimum_margin,
        "mean_formal_signed_margin": mean_margin,
        "maximum_terminal_speed_m_per_s": max_terminal_speed,
        "mean_action_rms": mean_action_rms,
        "maximum_any_mode_bound_fraction": max(
            (_as_float(row.get("any_mode_bound_fraction"), 0.0) for row in subset),
            default=0.0,
        ),
        "all_prefix_guards_pass": bool(
            subset
            and all(
                bool(row.get("physics_prefix_exact"))
                and bool(row.get("issued_prefix_exact"))
                and bool(row.get("applied_prefix_exact"))
                for row in subset
            )
        ),
        "all_no_future_measurement": bool(
            subset and all(bool(row.get("no_future_measurement")) for row in subset)
        ),
        "all_streaming_queues_consistent": bool(
            subset
            and all(bool(row.get("streaming_queue_consistent")) for row in subset)
        ),
        "all_target_conditioned_nominal_retained": bool(
            subset
            and all(
                bool(row.get("target_conditioned_nominal_retained"))
                for row in subset
            )
        ),
        "all_checkpoint_integrals_preserved": bool(
            subset
            and all(bool(row.get("checkpoint_integral_preserved")) for row in subset)
        ),
        "passed": passed,
    }


def run_development(
    ctx: Stage41R14Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_development_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.oracle_development / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [result_row(ctx, result) for result in results]
    policies = list(ctx.cfg["integrated_deadline_mpc"]["candidate_bank"])
    summaries = [
        _candidate_summary(ctx, rows, policy=policy, delay=delay)
        for delay in (1, 2)
        for policy in policies
    ]
    selected_by_delay: dict[str, str] = {}
    selected_summaries: list[dict[str, Any]] = []
    for delay in (1, 2):
        passing = [
            row
            for row in summaries
            if int(row["actual_delay_steps"]) == delay and bool(row["passed"])
        ]
        if not passing:
            continue
        selected = max(
            passing,
            key=lambda row: (
                float(row["minimum_formal_signed_margin"]),
                float(row["mean_formal_signed_margin"]),
                -float(row["controller_scale"]),
                -float(row["deadline_velocity_weight_multiplier"]),
                -float(row["maximum_terminal_speed_m_per_s"]),
                -float(row["mean_action_rms"]),
            ),
        )
        selected_by_delay[str(delay)] = str(selected["policy_id"])
        selected_summaries.append(selected)
    expected = len(policies) * 2 * 2
    passed = bool(
        len(rows) == expected
        and len({row["experiment_id"] for row in rows}) == expected
        and set(selected_by_delay) == {"1", "2"}
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "oracle_development",
        "required_targets": [
            row["target_id"]
            for row in ctx.cfg["integrated_deadline_mpc"]["required_targets"]
        ],
        "candidate_selection_uses_both_required_targets": True,
        "unseen_target_holdout_claimed": False,
        "selection_conditioned_only_on_trusted_delay": True,
        "formal_arrival_deadline_step": 27,
        "formal_hold_through_step": 37,
        "arrival_deadline_expanded": False,
        "fixed_first_effect_step": 23,
        "onset_rescanned": False,
        "deadline_velocity_states": [24, 25, 26, 27],
        "n_rollouts": len(rows),
        "expected_rollouts": expected,
        "coverage_complete": len(rows) == expected
        and len({row["experiment_id"] for row in rows}) == expected,
        "candidate_summaries": summaries,
        "selected_policy_by_delay": selected_by_delay,
        "selected_summaries": selected_summaries,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.oracle_development / "results.json", rows)
    write_csv(ctx.paths.oracle_development / "results.csv", rows)
    atomic_write_json(ctx.paths.oracle_development / "summary.json", summary)
    _update_state(
        ctx,
        oracle_development_complete=True,
        oracle_development_summary=summary,
    )
    return summary


def _selected_oracle_raw(
    ctx: Stage41R14Context,
) -> dict[tuple[str, int], dict[str, Any]]:
    selected = _selected_policy_by_delay(ctx)
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((ctx.paths.oracle_development / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result.get("spec") or {}
        delay = int(spec.get("action_delay_steps", -1))
        policy = selected.get(delay)
        if policy is None or str(spec.get("anticipatory_policy_id")) != str(
            policy["policy_id"]
        ):
            continue
        key = (str(spec["target_id"]), delay)
        if key in output:
            raise ValueError(f"duplicate selected R14 Oracle case: {key}")
        output[key] = result
    return output


def _comparison_components(result: Mapping[str, Any]) -> dict[str, np.ndarray]:
    return {
        "physics": _physics_array(result),
        "issued": _control_array(result, "issued_mode_coefficients"),
        "applied": _control_array(result, "applied_command_mode_coefficients"),
        "integrated_issued": _integrated_array(result, "issued_mode_coefficients"),
        "integrated_applied": _integrated_array(
            result, "applied_command_mode_coefficients"
        ),
    }


def run_calibrated_confirmation(
    ctx: Stage41R14Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_calibrated_specs(ctx)
    if not specs:
        summary = {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "calibrated_confirmation",
            "status": "not_run",
            "passed": False,
        }
        atomic_write_json(ctx.paths.calibrated_confirmation / "summary.json", summary)
        return summary
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.calibrated_confirmation / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [result_row(ctx, result) for result in results]
    oracle = _selected_oracle_raw(ctx)
    atol = float(
        ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"]
    )
    comparisons: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key not in oracle:
            raise ValueError(f"missing selected R14 Oracle comparison for {key}")
        left = _comparison_components(result)
        right = _comparison_components(oracle[key])
        component_diff = {
            name: _finite_max_abs(left[name], right[name]) for name in left
        }
        exact = all(np.array_equal(left[name], right[name]) for name in left)
        numeric = all(
            np.allclose(left[name], right[name], rtol=0.0, atol=atol)
            for name in left
        )
        comparisons.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": WEAK_SLEW,
                "calibration_token": spec.get("calibration_token"),
                "exact_trace_equal_to_oracle": exact,
                "numeric_trace_equal_to_oracle": numeric,
                "maximum_trace_abs_difference": max(component_diff.values()),
                "component_max_abs_difference": component_diff,
            }
        )
    pass_fraction = (
        sum(bool(row.get("r14_composite_pass")) for row in rows) / len(rows)
    )
    exact_fraction = (
        sum(bool(row["exact_trace_equal_to_oracle"]) for row in comparisons)
        / len(comparisons)
    )
    numeric_fraction = (
        sum(bool(row["numeric_trace_equal_to_oracle"]) for row in comparisons)
        / len(comparisons)
    )
    tokens = {
        str(row.get("calibration_token"))
        for row in rows
        if row.get("calibration_token")
    }
    untrusted = sum(
        not bool((result.get("spec") or {}).get("trusted_calibration_model"))
        for result in results
    )
    passed = bool(
        len(rows) == 4
        and pass_fraction >= 1.0
        and len(tokens) == 2
        and untrusted == 0
        and exact_fraction
        >= float(
            ctx.cfg["calibrated_confirmation"][
                "minimum_trace_equivalence_fraction"
            ]
        )
        and numeric_fraction >= 1.0
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "calibrated_confirmation",
        "n_rollouts": len(rows),
        "expected_rollouts": 4,
        "formal_contract_pass_fraction": pass_fraction,
        "distinct_calibration_tokens": len(tokens),
        "untrusted_main_start_count": untrusted,
        "exact_trace_equivalence_fraction": exact_fraction,
        "numeric_trace_equivalence_fraction": numeric_fraction,
        "numeric_trace_equivalence_atol": atol,
        "maximum_trace_abs_difference": max(
            (
                float(row["maximum_trace_abs_difference"])
                for row in comparisons
            ),
            default=math.inf,
        ),
        "comparisons": comparisons,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.calibrated_confirmation / "results.json", rows)
    write_csv(ctx.paths.calibrated_confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.calibrated_confirmation / "summary.json", summary)
    _update_state(
        ctx,
        calibrated_confirmation_complete=True,
        calibrated_confirmation_summary=summary,
    )
    return summary


def _r14_calibrated_map(
    ctx: Stage41R14Context,
) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((ctx.paths.calibrated_confirmation / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result.get("spec") or {}
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key in output:
            raise ValueError(f"duplicate R14 calibrated case: {key}")
        output[key] = result
    return output


def _formal_equivalence_components(
    result: Mapping[str, Any], *, horizon: int
) -> dict[str, np.ndarray]:
    return {
        "physics": _physics_array(result, count=horizon + 1),
        "issued": _control_array(
            result, "issued_mode_coefficients", count=horizon
        ),
        "applied": _control_array(
            result, "applied_command_mode_coefficients", count=horizon
        ),
    }


def run_formal_grid_confirmation(ctx: Stage41R14Context) -> dict[str, Any]:
    source_oracle = _source_oracle_map(ctx)
    source_calibrated = _source_calibrated_map(ctx)
    selected_oracle = _selected_oracle_raw(ctx)
    selected_calibrated = _r14_calibrated_map(ctx)
    affected_keys = {
        (target, delay, WEAK_SLEW)
        for target in ("nominal", "RZ_p10_m10")
        for delay in (1, 2)
    }
    rows: list[dict[str, Any]] = []
    atol = float(
        ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"]
    )
    for key in sorted(source_oracle):
        target, delay, slew = key
        affected = key in affected_keys
        if affected:
            pair_key = (target, delay)
            if pair_key not in selected_oracle or pair_key not in selected_calibrated:
                raise ValueError(f"missing R14 affected formal-grid case: {pair_key}")
            oracle_result = selected_oracle[pair_key]
            calibrated_result = selected_calibrated[pair_key]
            path = "r14_integrated_target_conditioned_deadline_mpc"
            path_guard = bool(result_row(ctx, oracle_result)["r14_composite_pass"])
        else:
            oracle_result = source_oracle[key]
            calibrated_result = source_calibrated[key]
            path = "source_unchanged_r11_original_deadline"
            path_guard = True
        policy = _timing_policy(
            ctx, slew, policy_id=f"formal_{target}_d{delay}_s{slew:.1f}"
        )
        horizon = int(policy["horizon_steps"])
        oracle_slice = _slice_result(oracle_result, horizon)
        calibrated_slice = _slice_result(calibrated_result, horizon)
        metrics = r8.tracking_metrics(
            ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
            oracle_slice,
            policy,
        )
        left = _formal_equivalence_components(calibrated_slice, horizon=horizon)
        right = _formal_equivalence_components(oracle_slice, horizon=horizon)
        component_diff = {
            name: _finite_max_abs(left[name], right[name]) for name in left
        }
        exact = all(np.array_equal(left[name], right[name]) for name in left)
        numeric = all(
            np.allclose(left[name], right[name], rtol=0.0, atol=atol)
            for name in left
        )
        passed = bool(
            metrics.get("stage3_4_target_tracking_pass")
            and path_guard
            and exact
            and numeric
        )
        rows.append(
            {
                "target_id": target,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "controller_path": path,
                "formal_horizon_steps": horizon,
                "formal_arrival_deadline_step": max(
                    policy["allowed_arrival_steps"]
                ),
                "oracle_formal_tracking_pass": bool(
                    metrics.get("stage3_4_target_tracking_pass")
                ),
                "oracle_minimum_signed_margin": metrics.get(
                    "stage3_4_tracking_minimum_signed_margin"
                ),
                "calibrated_exact_equal_to_oracle": exact,
                "calibrated_numeric_equal_to_oracle": numeric,
                "maximum_trace_abs_difference": max(component_diff.values()),
                "component_max_abs_difference": component_diff,
                "path_guard_pass": path_guard,
                "formal_grid_case_pass": passed,
            }
        )
    affected_rows = [
        row
        for row in rows
        if row["controller_path"]
        == "r14_integrated_target_conditioned_deadline_mpc"
    ]
    unchanged_rows = [
        row
        for row in rows
        if row["controller_path"]
        != "r14_integrated_target_conditioned_deadline_mpc"
    ]
    passed = bool(
        len(rows) == 18
        and len(affected_rows) == 4
        and len(unchanged_rows) == 14
        and all(bool(row["formal_grid_case_pass"]) for row in rows)
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "formal_grid_confirmation",
        "n_cases": len(rows),
        "expected_cases": 18,
        "affected_r14_cases": len(affected_rows),
        "source_unchanged_cases": len(unchanged_rows),
        "formal_contract_pass_fraction": (
            sum(bool(row["formal_grid_case_pass"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "calibrated_exact_trace_equivalence_fraction": (
            sum(bool(row["calibrated_exact_equal_to_oracle"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "maximum_trace_abs_difference": max(
            (float(row["maximum_trace_abs_difference"]) for row in rows),
            default=math.inf,
        ),
        "normal_slew_and_weak_delay0_reused_without_new_tsc": True,
        "arrival_deadline_expanded": False,
        "unseen_target_generalization_validated": False,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.formal_grid_confirmation / "results.json", rows)
    write_csv(ctx.paths.formal_grid_confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.formal_grid_confirmation / "summary.json", summary)
    _update_state(
        ctx,
        formal_grid_confirmation_complete=True,
        formal_grid_confirmation_summary=summary,
    )
    return summary


def run_restart_audit(ctx: Stage41R14Context) -> dict[str, Any]:
    simulation_root = Path(
        ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
            "simulation_root"
        ]
    ).expanduser()
    candidates = [str(x) for x in ctx.cfg["restart_audit"]["candidate_folders"]]
    available = [name for name in candidates if (simulation_root / name).is_dir()]
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "restart_audit",
        "simulation_root": str(simulation_root),
        "candidate_folders": candidates,
        "available_folders": available,
        "true_restart_validation_available": len(available)
        >= int(ctx.cfg["restart_audit"]["minimum_distinct_folders"]),
        "true_restart_validation_performed": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "availability_requirement_for_stage4_1r14": False,
        "audit_completed": True,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart_audit / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


def finalize(ctx: Stage41R14Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    development = state.get("oracle_development_summary") or {}
    calibrated = state.get("calibrated_confirmation_summary") or {}
    formal_grid = state.get("formal_grid_confirmation_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    primary_pass = bool(
        source.get("passed")
        and development.get("passed")
        and calibrated.get("passed")
        and formal_grid.get("passed")
    )
    verdict_name = (
        "STAGE4_1R14_ORIGINAL_250_270MS_DEADLINE_STATIC_GRID_CLOSURE"
        if primary_pass
        else "STAGE4_1R14_ORIGINAL_DEADLINE_INTEGRATED_MPC_INCOMPLETE"
    )
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "verdict": verdict_name,
        "primary_pass": primary_pass,
        "formal_timing_contract_restored": primary_pass,
        "formal_combined_case_count": 18,
        "unchanged_source_case_count": 14,
        "modified_case_count": 4,
        "normal_slew_arrival_deadline_ms": 250,
        "normal_slew_hold_through_ms": 350,
        "weak_slew_arrival_deadline_ms": 270,
        "weak_slew_hold_through_ms": 370,
        "arrival_deadline_expanded": False,
        "fixed_first_affected_state_step": 23,
        "onset_rescanned": False,
        "target_conditioned_nominal_retained": True,
        "checkpoint_integral_preserved": True,
        "deadline_velocity_states": [24, 25, 26, 27],
        "source_r11_long_hold_retained_as_diagnostic_only": True,
        "stage4_2r1_was_not_run_or_reused": True,
        "selected_policy_by_delay": development.get("selected_policy_by_delay", {}),
        "selection_conditioned_only_on_trusted_delay": True,
        "selection_used_both_required_targets": True,
        "unseen_target_generalization_validated": False,
        "normal_slew_controller_changed": False,
        "weak_slew_delay0_controller_changed": False,
        "trusted_calibration_required": True,
        "true_restart_validation_available": restart.get(
            "true_restart_validation_available", False
        ),
        "true_restart_validation_performed": False,
        "plant_parameter_robustness_validated": False,
        "continuous_parameter_change_validated": False,
        "terminal_measurement_noise_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "finite_test_envelope_only": True,
        "next_if_pass": (
            "Freeze the original-deadline finite static-grid MPC expert and proceed to true restart and hidden vessel/eddy-history validation. "
            "Do not reinterpret R10/R11 late-arrival trajectories as the timing contract and do not start BC/DAgger/RL yet."
        ),
        "next_if_fail": (
            "Do not enlarge the 250/270 ms deadlines and do not scan another scalar handoff time. Use the complete R13/R14 causal raw bank "
            "to identify a bounded early-braking local model and formulate one constrained delay-pipeline-aware main MPC with an explicit deadline-speed constraint. "
            "Do not add another late tail and do not hand 14-coil control to RL."
        ),
        "final_task": ctx.cfg["final_task"],
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "source_stage4_1r12_run": str(ctx.source_stage41r12_run),
        "phases": {
            "source_audit": source,
            "oracle_development": development,
            "calibrated_confirmation": calibrated,
            "formal_grid_confirmation": formal_grid,
            "restart_audit": restart,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r14_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_1r14_summary.json", summary)
    if primary_pass:
        stop_reason = ""
    elif not source.get("passed"):
        stop_reason = "source_audit_failed"
    elif not development.get("passed"):
        stop_reason = "formal_original_deadline_integrated_deadline_mpc_failed"
    elif not calibrated.get("passed"):
        stop_reason = "calibrated_confirmation_failed"
    else:
        stop_reason = "formal_grid_confirmation_failed"
    _update_state(ctx, finished=True, stop_reason=stop_reason)
    return summary


def execute(
    ctx: Stage41R14Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    if command not in {"all", "audit", "development", "confirmation", "grid"}:
        raise ValueError("command must be all/audit/development/confirmation/grid")
    state = read_json(ctx.paths.state)
    if command in {"all", "audit"} and not bool(state.get("source_audit_complete")):
        source = run_source_audit(ctx)
        if not source.get("passed"):
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "development"} and not bool(
        state.get("oracle_development_complete")
    ):
        development = run_development(ctx, backend=backend, resume=resume)
        if not development.get("passed"):
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "confirmation"} and not bool(
        state.get("calibrated_confirmation_complete")
    ):
        calibrated = run_calibrated_confirmation(
            ctx, backend=backend, resume=resume
        )
        if not calibrated.get("passed"):
            _update_state(
                ctx,
                calibrated_confirmation_complete=True,
                calibrated_confirmation_summary=calibrated,
            )
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "grid"} and not bool(
        state.get("formal_grid_confirmation_complete")
    ):
        formal_grid = run_formal_grid_confirmation(ctx)
        if not formal_grid.get("passed"):
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if not bool(state.get("restart_audit_complete")):
        run_restart_audit(ctx)
    return finalize(ctx)


def self_test(project_dir: Path) -> dict[str, Any]:
    cfg_path = (
        project_dir
        / "configs"
        / "stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_370ms.json"
    )
    cfg = read_json(cfg_path)
    validate_config(cfg)
    design = cfg["integrated_deadline_mpc"]
    candidates = list(design["candidate_bank"])
    fixed_onset = int(design["fixed_first_affected_state_step"])
    transitions = {
        delay: _transition_issue_step(fixed_onset, delay) for delay in (1, 2)
    }
    alignment = all(
        issue + delay + 1 == fixed_onset
        for delay, issue in transitions.items()
    )
    no_deadline_expansion = bool(
        max(cfg["formal_timing_contract"]["normal_slew"]["allowed_arrival_steps"])
        == 25
        and max(
            cfg["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"]
        )
        == 27
        and int(design["horizon_steps"]) == 37
    )
    candidate_identity = [row["policy_id"] for row in candidates] == [
        "itc_vw1_c0p50",
        "itc_vw3_c0p50",
        "itc_vw6_c0p50",
        "itc_vw10_c0p50",
        "itc_vw6_c0p60",
        "itc_vw10_c0p60",
    ]
    passed = bool(
        alignment
        and no_deadline_expansion
        and fixed_onset == 23
        and candidate_identity
        and design["target_conditioned_nominal_physical_required"]
        and design["target_conditioned_nominal_feature_required"]
        and design["checkpoint_integral_preservation_required"]
        and design["require_no_onset_rescan"]
        and design["selection_is_conditioned_only_on_trusted_delay"]
        and design["selection_uses_both_required_targets"]
        and not design["unseen_target_holdout_claimed"]
        and cfg.get("stage4_2r1_was_not_run_or_reused")
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_valid": True,
        "fixed_first_affected_state_step": fixed_onset,
        "transition_issue_steps": transitions,
        "transition_alignment_valid": alignment,
        "no_arrival_deadline_expansion": no_deadline_expansion,
        "target_conditioned_nominal_required": True,
        "checkpoint_integral_preservation_required": True,
        "deadline_velocity_states": [int(x) for x in design["deadline_velocity_states"]],
        "candidate_policy_ids": [str(row["policy_id"]) for row in candidates],
        "candidate_count": len(candidates),
        "development_rollout_count": 24,
        "calibrated_rollout_count_if_development_passes": 4,
        "maximum_true_tsc_rollouts": 28,
        "selection_conditioned_on_trusted_delay": bool(
            design["selection_is_conditioned_only_on_trusted_delay"]
        ),
        "selection_uses_both_required_targets": bool(
            design["selection_uses_both_required_targets"]
        ),
        "unseen_target_holdout_claimed": bool(
            design["unseen_target_holdout_claimed"]
        ),
        "stage4_2r1_was_not_run_or_reused": bool(
            cfg.get("stage4_2r1_was_not_run_or_reused")
        ),
        "passed": passed,
    }


def _default_source(project_dir: Path) -> Path:
    env = os.environ.get("STAGE4_1R14_SOURCE_STAGE4_1R13_RUN")
    if env:
        return Path(env).expanduser().resolve()
    latest = project_dir / "stage4_1r13_runs" / "latest_stage4_1r13_run.txt"
    if latest.is_file():
        return Path(latest.read_text(encoding="utf-8").strip()).expanduser().resolve()
    raise FileNotFoundError(
        "set STAGE4_1R14_SOURCE_STAGE4_1R13_RUN or provide --source-stage4-1r13-run"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Stage4.1R14 immutable-deadline integrated target-conditioned deadline MPC"
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "configs"
        / "stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_370ms.json",
    )
    parser.add_argument("--source-stage4-1r13-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command",
        choices=["all", "audit", "development", "confirmation", "grid"],
        default=os.environ.get("STAGE4_1R14_COMMAND", "all"),
    )
    parser.add_argument(
        "--backend",
        choices=["ray", "serial"],
        default=os.environ.get("STAGE4_1R14_BACKEND", "ray"),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    project_dir = args.config.expanduser().resolve().parents[1]
    if args.self_test:
        print(json.dumps(self_test(project_dir), indent=2, sort_keys=True))
        return
    source = args.source_stage4_1r13_run or _default_source(project_dir)
    ctx = load_stage41r14_config(
        args.config,
        source_stage41r13_run=source,
        run_dir_override=args.run_dir,
    )
    payload = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume or os.environ.get("STAGE4_1R14_RESUME") == "1"),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
