"""Stage4.1R12 original-deadline weak-slew closure.

R9--R11 produced useful queue-transition and long-hold evidence, but their
550/750/2000 ms experiments must not replace the frozen Stage3.4/R4 timing
contract.  R12 restores that contract explicitly:

* slew 1.0/1.1: arrival no later than 250 ms and hold through 350 ms;
* slew 0.9: arrival no later than 270 ms and hold through 370 ms.

The R11 source is re-scored under those original deadlines before any new TSC
rollout is allowed.  The expected source result is 14/18: the only failures are
slew=0.9 with delay=1/2 for the nominal and RZ_p10_m10 targets.  R12 then changes
only this weak-slew path.  The frozen Stage3.4/R3 controller runs online until a
candidate causal transition issue time.  A continuously streaming, delay-aware
damping controller then takes over so that its first physical effect occurs
between 280 and 350 ms.  Every candidate is issued from information available
at its original issue time; the source physics is required to remain bit-exact
through the unchanged 270 ms arrival deadline and until that candidate's first
physical effect.  The already-passing
fourteen paths are not rerun or modified.  No arrival deadline or scoring horizon
is extended.

Candidate selection uses the nominal target only.  RZ_p10_m10 remains a
strictly disjoint holdout.  Trusted R8 pair-level calibration tokens are used
only after Oracle development and holdout close.  This remains a finite clean
static digital-twin test; it is not restart, hidden-history, continuous-plant,
noisy-sensing, disturbance-recovery, or deployment validation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import resource
import time
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
from . import stage4_1r11_frozen_terminal_long_horizon_hold as r11
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r11.atomic_write_json
atomic_write_json_gz = r11.atomic_write_json_gz
read_json = r11.read_json
read_json_gz = r11.read_json_gz
utc_timestamp = r11.utc_timestamp
write_csv = r11.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R12"
CONTROLLER_REVISION = "original_deadline_weak_slew_anticipatory_damping_v12"
EXPECTED_SOURCE_REVISION = r11.CONTROLLER_REVISION
PACKAGE_REVISION = "r12_original_deadline_post_arrival_damping_v4"
N_MODES = 3
WEAK_SLEW = 0.9
WEAK_HORIZON = 37


def _json_safe(value: Any) -> Any:
    return r11._json_safe(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    return r11._as_bool(value, default)


def _as_int(value: Any, default: int = 0) -> int:
    return r11._as_int(value, default)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r11._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r11._sha256_file(path)


def _result_complete(path: Path) -> bool:
    return r11._result_complete(path)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "s41r12_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape:
        return math.inf
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def _array_digest(array: np.ndarray, prefix: str) -> str:
    return r10._array_digest(np.asarray(array), prefix)


@dataclass(frozen=True)
class Stage41R12Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    oracle_development: Path
    oracle_holdout: Path
    calibrated_confirmation: Path
    formal_grid_confirmation: Path
    restart_audit: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R12Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r12_source_reference",
            source_audit=run_dir / "stage4_1r12_source_audit",
            oracle_development=run_dir / "stage4_1r12_oracle_development",
            oracle_holdout=run_dir / "stage4_1r12_oracle_holdout",
            calibrated_confirmation=run_dir / "stage4_1r12_calibrated_confirmation",
            formal_grid_confirmation=run_dir / "stage4_1r12_formal_grid_confirmation",
            restart_audit=run_dir / "stage4_1r12_restart_audit",
            analysis=run_dir / "stage4_1r12_analysis",
            variants=run_dir / "stage4_1r12_environment_variants",
            state=run_dir / "stage4_1r12_state.json",
            manifest=run_dir / "stage4_1r12_manifest.json",
        )


@dataclass
class Stage41R12Context:
    cfg: dict[str, Any]
    paths: Stage41R12Paths
    project_dir: Path
    source_stage41r11_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    source_stage41r10_run: Path
    source_stage41r8_run: Path
    r11_ctx: r11.Stage41R11Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r11_manifest.json",
        source / "stage4_1r11_state.json",
        source / "stage4_1r11_config.resolved.json",
        source / "stage4_1r11_analysis" / "stage4_1r11_verdict.json",
        source / "stage4_1r11_analysis" / "stage4_1r11_summary.json",
        source / "stage4_1r11_oracle_long_hold" / "summary.json",
        source / "stage4_1r11_oracle_long_hold" / "results.json",
        source / "stage4_1r11_calibrated_long_hold" / "summary.json",
        source / "stage4_1r11_calibrated_long_hold" / "results.json",
    ]
    for phase in ("stage4_1r11_oracle_long_hold", "stage4_1r11_calibrated_long_hold"):
        required.extend(sorted((source / phase / "raw").glob("*.json.gz")))
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R11 source file missing: {path}")
        size = path.stat().st_size
        total += size
        rows.append(
            {
                "relative_path": path.relative_to(source).as_posix(),
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
    return r10._resolve_recorded_run(project_dir, recorded, root_name)


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R12 controller_revision mismatch")
    source = cfg["source_requirement"]
    if source.get("required_stage") != "Stage4.1R11":
        raise ValueError("R12 source stage must remain Stage4.1R11")
    if source.get("required_controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("R12 source controller revision mismatch")
    gate = cfg["gate"]
    if not math.isclose(float(gate["precise_tolerance_m"]), 0.03, abs_tol=1e-15):
        raise ValueError("R12 may not weaken the 30 mm position gate")
    if not math.isclose(
        float(gate["terminal_velocity_max_m_per_s"]), 0.1, abs_tol=1e-15
    ):
        raise ValueError("R12 may not weaken the 0.1 m/s speed gate")
    timing = cfg["formal_timing_contract"]
    if not bool(timing.get("immutable")):
        raise ValueError("R12 timing contract must be immutable")
    normal = timing["normal_slew"]
    weak = timing["weak_slew"]
    if int(normal["horizon_steps"]) != 35 or int(normal["arrival_deadline_step"]) != 25:
        raise ValueError("normal-slew contract must remain 250/350 ms")
    if int(weak["horizon_steps"]) != 37 or int(weak["arrival_deadline_step"]) != 27:
        raise ValueError("weak-slew contract must remain 270/370 ms")
    if max(map(int, normal["allowed_arrival_steps"])) != 25:
        raise ValueError("normal-slew arrival list exceeds 250 ms")
    if max(map(int, weak["allowed_arrival_steps"])) != 27:
        raise ValueError("weak-slew arrival list exceeds 270 ms")
    if not bool(timing.get("arrival_deadline_may_not_expand")):
        raise ValueError("R12 must prohibit arrival-deadline expansion")
    closure = cfg["weak_slew_closure"]
    if not math.isclose(float(closure["actual_slew_scale"]), WEAK_SLEW, abs_tol=1e-15):
        raise ValueError("R12 closure must target only 0.9x slew")
    if int(closure["horizon_steps"]) != WEAK_HORIZON:
        raise ValueError("R12 weak-slew horizon must remain 37 steps")
    if [int(x) for x in closure["actual_delay_steps"]] != [1, 2]:
        raise ValueError("R12 may modify only the weak-slew delay=1/2 cases")
    candidates = list(closure["candidate_bank"])
    if len(candidates) != 6:
        raise ValueError("R12 candidate bank must contain six timing ablations")
    ids = [str(row["policy_id"]) for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate R12 policy_id")
    affected = [int(row["first_affected_state_step"]) for row in candidates]
    if affected != [28, 30, 32, 33, 34, 35]:
        raise ValueError(
            "R12 candidate affected-state bank must remain [28,30,32,33,34,35]"
        )
    if affected != [int(x) for x in closure.get("candidate_first_affected_state_steps", [])]:
        raise ValueError("R12 candidate list and explicit affected-state list disagree")
    if int(closure.get("earliest_first_affected_state_step", -1)) != min(affected):
        raise ValueError("R12 earliest first-effect declaration is inconsistent")
    if int(closure.get("latest_first_affected_state_step", -1)) != max(affected):
        raise ValueError("R12 latest first-effect declaration is inconsistent")
    if min(affected) != 28 or max(affected) != 35:
        raise ValueError("R12 post-arrival damping window must remain 280--350 ms")
    if min(affected) <= int(weak["arrival_deadline_step"]):
        raise ValueError("R12 first physical effect must remain strictly after 270 ms")
    if bool(closure.get("modified_paths_may_change_before_arrival_deadline")):
        raise ValueError("R12 may not alter source physics through the 270 ms arrival deadline")
    if not bool(closure.get("preserve_source_physics_through_arrival_deadline")):
        raise ValueError("R12 must preserve source physics through the 270 ms arrival deadline")
    if not bool(closure.get("candidate_first_effect_strictly_after_arrival_deadline")):
        raise ValueError("R12 candidate first effect must be explicitly post-arrival-deadline")
    if not bool(closure.get("transition_command_may_be_issued_before_deadline")):
        raise ValueError("R12 must acknowledge causal pre-deadline issue for delayed post-deadline effect")
    if not bool(closure.get("preserve_source_physics_only_until_candidate_first_effect")):
        raise ValueError("R12 must preserve each source prefix until its candidate first effect")
    if not bool(closure.get("causal_original_issue_time_transition_required")):
        raise ValueError("R12 transition must be issued causally at the original issue time")
    if not bool(closure.get("unaffected_14_paths_remain_source_exact")):
        raise ValueError("R12 must leave the fourteen already-passing paths source-exact")
    if int(closure.get("arrival_deadline_remains_step", -1)) != 27:
        raise ValueError("R12 weak-slew arrival deadline must remain step 27")
    if int(closure.get("horizon_remains_step", -1)) != 37:
        raise ValueError("R12 weak-slew scoring horizon must remain step 37")
    for first in affected:
        for delay in (1, 2):
            issue = _transition_issue_step(first, delay)
            if issue + delay + 1 != first or issue >= first:
                raise ValueError("R12 causal transition alignment is invalid")
    if not bool(closure.get("normal_slew_controller_is_unchanged")):
        raise ValueError("R12 may not alter normal-slew controller behavior")
    if not bool(closure.get("weak_slew_delay0_controller_is_unchanged")):
        raise ValueError("R12 may not alter the already-passing weak-slew delay=0 path")
    if not bool(closure.get("activation_requires_trusted_slew_0p9_model")):
        raise ValueError("R12 weak-slew branch requires a trusted model")
    if cfg["calibrated_confirmation"].get("online_handover_enabled"):
        raise ValueError("R12 calibrated path must not use online handover")
    if not bool(cfg.get("finite_test_envelope_only", False)):
        raise ValueError("R12 must remain explicitly finite-envelope only")


def _validate_source_stage41r11(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R11 source file missing: {path}")
    manifest = read_json(source / "stage4_1r11_manifest.json")
    state = read_json(source / "stage4_1r11_state.json")
    source_cfg = read_json(source / "stage4_1r11_config.resolved.json")
    verdict = read_json(source / "stage4_1r11_analysis" / "stage4_1r11_verdict.json")
    req = cfg["source_requirement"]
    if manifest.get("stage") != req["required_stage"]:
        raise ValueError("source Stage4.1R11 manifest stage mismatch")
    if manifest.get("controller_revision") != req["required_controller_revision"]:
        raise ValueError("source Stage4.1R11 controller revision mismatch")
    if source_cfg.get("controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R11 resolved config revision mismatch")
    if bool(req.get("require_finished", True)) and not bool(state.get("finished")):
        raise ValueError("source Stage4.1R11 is not finished")
    if str(state.get("stop_reason", "")) != str(req.get("require_stop_reason", "")):
        raise ValueError("source Stage4.1R11 stop_reason mismatch")
    oracle_summary = state.get("oracle_long_hold_summary") or {}
    calibrated_summary = state.get("calibrated_long_hold_summary") or {}
    if bool(req.get("require_oracle_long_hold_passed", True)) and not bool(
        oracle_summary.get("passed")
    ):
        raise ValueError("source Stage4.1R11 Oracle long hold did not pass")
    if bool(req.get("require_calibrated_long_hold_passed", True)) and not bool(
        calibrated_summary.get("passed")
    ):
        raise ValueError("source Stage4.1R11 calibrated long hold did not pass")
    counts = {
        "stage4_1r11_oracle_long_hold": int(req["require_oracle_raw_count"]),
        "stage4_1r11_calibrated_long_hold": int(req["require_calibrated_raw_count"]),
    }
    for phase, expected in counts.items():
        actual = len(list((source / phase / "raw").glob("*.json.gz")))
        if actual != expected:
            raise ValueError(f"source R11 {phase} raw count mismatch: {actual} != {expected}")
    if not bool(verdict.get("primary_pass")):
        raise ValueError("source Stage4.1R11 primary verdict did not pass")
    return manifest, state, source_cfg, verdict


def load_stage41r12_config(
    config_path: Path,
    *,
    source_stage41r11_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R12Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r11_run = source_stage41r11_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r11(
        source_stage41r11_run, cfg
    )
    source_stage41r10_run = _resolve_recorded_run(
        project_dir,
        str(manifest["source_stage4_1r10_run"]),
        "stage4_1r10_runs",
    )
    source_stage41r8_run = _resolve_recorded_run(
        project_dir,
        str(manifest["source_stage4_1r8_run"]),
        "stage4_1r8_runs",
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r12_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r12')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    paths = Stage41R12Paths.from_run_dir(run_dir)
    packaged_r11_cfg = (
        project_dir
        / "configs"
        / "stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json"
    )
    if not packaged_r11_cfg.is_file():
        raise FileNotFoundError(f"packaged R11 dependency config missing: {packaged_r11_cfg}")
    r11_ctx = r11.load_stage41r11_config(
        packaged_r11_cfg,
        source_stage41r10_run=source_stage41r10_run,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    base34 = r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R12_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R12_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    base34.env_cfg = env_cfg
    return Stage41R12Context(
        cfg=cfg,
        paths=paths,
        project_dir=project_dir,
        source_stage41r11_run=source_stage41r11_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        source_stage41r10_run=source_stage41r10_run,
        source_stage41r8_run=source_stage41r8_run,
        r11_ctx=r11_ctx,
        source_fingerprint=_source_inventory(source_stage41r11_run),
    )


def _initial_state(ctx: Stage41R12Context) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "oracle_development_complete": False,
        "oracle_holdout_complete": False,
        "calibrated_confirmation_complete": False,
        "formal_grid_confirmation_complete": False,
        "restart_audit_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R12Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R12Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.oracle_development,
        ctx.paths.oracle_holdout,
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
            raise ValueError("R12 resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R12 resume controller revision mismatch")
    elif resume:
        raise FileNotFoundError("R12 resume requested but manifest is missing")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r12_config.resolved.json", ctx.cfg)
    for name, payload in (
        ("stage4_1r11_manifest.json", ctx.source_manifest),
        ("stage4_1r11_state.json", ctx.source_state),
        ("stage4_1r11_config.resolved.json", ctx.source_cfg),
        ("stage4_1r11_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r11_run": str(ctx.source_stage41r11_run),
        "source_stage4_1r10_run": str(ctx.source_stage41r10_run),
        "source_stage4_1r8_run": str(ctx.source_stage41r8_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": int(os.environ.get("STAGE4_1R12_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "arrival_deadline_expansion_allowed": False,
        "normal_slew_controller_changed": False,
        "finite_test_envelope_only": True,
        "true_restart_validation_performed": False,
        "final_task": ctx.cfg["final_task"],
    }
    atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _phase_raw(source: Path, phase: str) -> list[dict[str, Any]]:
    return [read_json_gz(path) for path in sorted((source / phase / "raw").glob("*.json.gz"))]


def _source_oracle_map(ctx: Stage41R12Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for result in _phase_raw(ctx.source_stage41r11_run, "stage4_1r11_oracle_long_hold"):
        spec = result.get("spec") or {}
        key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        if key in output:
            raise ValueError(f"duplicate source R11 Oracle case: {key}")
        output[key] = result
    if len(output) != 18:
        raise ValueError(f"expected 18 source R11 Oracle cases, got {len(output)}")
    return output


def _timing_policy(ctx: Stage41R12Context, slew: float, *, policy_id: str) -> dict[str, Any]:
    timing = ctx.cfg["formal_timing_contract"]
    block = timing["weak_slew"] if math.isclose(float(slew), WEAK_SLEW, abs_tol=1e-12) else timing["normal_slew"]
    return {
        "policy_id": policy_id,
        "horizon_steps": int(block["horizon_steps"]),
        "allowed_arrival_steps": [int(x) for x in block["allowed_arrival_steps"]],
    }


def _slice_result(result: Mapping[str, Any], horizon: int) -> dict[str, Any]:
    sliced = copy.deepcopy(dict(result))
    sliced["trajectory"] = copy.deepcopy(list(result.get("trajectory") or [])[: horizon + 1])
    sliced["control_trace"] = copy.deepcopy(list(result.get("control_trace") or [])[:horizon])
    return sliced


def run_source_audit(ctx: Stage41R12Context) -> dict[str, Any]:
    source = _source_oracle_map(ctx)
    rows: list[dict[str, Any]] = []
    failures: set[tuple[str, int, float]] = set()
    for key in sorted(source):
        target, delay, slew = key
        policy = _timing_policy(ctx, slew, policy_id=f"source_{target}_d{delay}_s{slew:.1f}")
        result = _slice_result(source[key], int(policy["horizon_steps"]))
        metrics = r8.tracking_metrics(ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx, result, policy)
        passed = bool(metrics["stage3_4_target_tracking_pass"])
        if not passed:
            failures.add(key)
        rows.append(
            {
                "target_id": target,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "formal_horizon_steps": policy["horizon_steps"],
                "formal_arrival_deadline_step": max(policy["allowed_arrival_steps"]),
                "formal_contract_pass": passed,
                "best_endpoint_step": metrics.get("stage3_4_best_endpoint_step"),
                "minimum_signed_margin": metrics.get("stage3_4_tracking_minimum_signed_margin"),
                "terminal_speed_m_per_s": metrics.get("terminal_velocity_m_per_s"),
                "sustained_box_error_m": metrics.get("stage3_4_sustained_box_max_error_m"),
            }
        )
    req = ctx.cfg["source_requirement"]
    expected_failures = {
        (
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in req["expected_original_contract_failures"]
    }
    pass_count = sum(bool(row["formal_contract_pass"]) for row in rows)
    normal_rows = [row for row in rows if float(row["actual_slew_scale"]) > 0.95]
    weak_d0_rows = [
        row
        for row in rows
        if math.isclose(float(row["actual_slew_scale"]), WEAK_SLEW, abs_tol=1e-12)
        and int(row["actual_delay_steps"]) == 0
    ]
    source_cal = read_json(
        ctx.source_stage41r11_run / "stage4_1r11_calibrated_long_hold" / "summary.json"
    )
    passed = bool(
        len(rows) == int(req["expected_original_contract_total_count"])
        and pass_count == int(req["expected_original_contract_pass_count"])
        and failures == expected_failures
        and len(normal_rows) == 12
        and all(bool(row["formal_contract_pass"]) for row in normal_rows)
        and len(weak_d0_rows) == 2
        and all(bool(row["formal_contract_pass"]) for row in weak_d0_rows)
        and _as_float(source_cal.get("exact_trace_equivalence_fraction"), 0.0) >= 1.0
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r11_run": str(ctx.source_stage41r11_run),
        "source_long_hold_verdict_passed": bool(ctx.source_verdict.get("primary_pass")),
        "source_long_hold_is_extended_diagnostic_not_formal_timing_replacement": True,
        "stage4_2r1_was_not_run_or_reused": True,
        "formal_contract_total_cases": len(rows),
        "formal_contract_pass_count": pass_count,
        "formal_contract_fail_count": len(failures),
        "formal_contract_failure_keys": [
            {"target_id": t, "actual_delay_steps": d, "actual_slew_scale": s}
            for t, d, s in sorted(failures)
        ],
        "normal_slew_source_cases_passed": len(normal_rows) == 12 and all(
            bool(row["formal_contract_pass"]) for row in normal_rows
        ),
        "weak_slew_delay0_source_cases_passed": len(weak_d0_rows) == 2 and all(
            bool(row["formal_contract_pass"]) for row in weak_d0_rows
        ),
        "source_calibrated_exact_trace_equivalence_fraction": source_cal.get(
            "exact_trace_equivalence_fraction"
        ),
        "arrival_deadline_expansion_used": False,
        "passed": passed,
        "interpretation": (
            "R11 remains useful long-hold evidence, but under the immutable original "
            "250/350 and 270/370 ms contracts it closes 14/18. R12 is permitted to "
            "change only the four 0.9x-slew delay=1/2 cases, preserve their physics through 270 ms, and must not enlarge time."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    write_csv(ctx.paths.source_audit / "original_timing_reaudit.csv", rows)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def _control_item(row: Mapping[str, Any], *, origin: str, origin_index: int) -> dict[str, Any]:
    return {
        "origin": str(origin),
        "origin_index": int(origin_index),
        "command": np.asarray(row.get("issued_mode_coefficients", np.zeros(N_MODES)), dtype=float).reshape(N_MODES),
        "desired_physical": np.asarray(
            row.get(
                "issued_desired_physical_mode_coefficients",
                row.get("desired_physical_mode_coefficients", np.zeros(N_MODES)),
            ),
            dtype=float,
        ).reshape(N_MODES),
    }


def _transition_issue_step(first_affected_state_step: int, delay_steps: int) -> int:
    issue = int(first_affected_state_step) - 1 - int(delay_steps)
    if issue < 1:
        raise ValueError("anticipatory damping transition issue step is too early")
    return issue


def _measurement_for_solver(
    physical: np.ndarray,
    scales: np.ndarray,
    *,
    position_gain: float,
    velocity_gain: float,
    ip_gain: float,
) -> tuple[np.ndarray, np.ndarray]:
    normalized = np.asarray(physical, dtype=float) / np.asarray(scales, dtype=float)
    scaled = normalized.copy()
    scaled[:2] *= float(position_gain)
    scaled[2:4] *= float(velocity_gain)
    scaled[4] *= float(ip_gain)
    return normalized, scaled


class LocalStage41R12Worker:
    """Continue a causally checkpointed R3 main trajectory with early damping.

    The shared R3 worker is asked to stop immediately before the candidate issue
    step.  Its checkpoint contains the real static delay queue, the current TSC
    state, and the previous physical correction.  R12 then issues a new command
    using only the current and previous measured states, streams the queue
    without bypass, and continues through the immutable 370 ms weak-slew
    horizon.
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
        self.horizon_steps = int(payload.get("stage4_1r4_horizon_steps", 35))

    def close(self) -> None:
        self.r9_worker.close()

    def _cleanup_episode(self, *, failed: bool, reason: str) -> None:
        runner = getattr(self.base_worker.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=failed, reason=reason)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        try:
            actual_slew = float(spec["slew_scale"])
            modeled_slew = float(spec["controller_slew_scale_estimate"])
            actual_delay = int(spec["action_delay_steps"])
            modeled_delay = int(spec["controller_action_delay_steps"])
            if not bool(spec.get("trusted_calibration_model", False)):
                raise ValueError("R12 may not start from an untrusted actuator model")
            if not math.isclose(actual_slew, WEAK_SLEW, abs_tol=1e-12):
                raise ValueError("R12 modifies only the 0.9x-slew branch")
            if actual_delay not in {1, 2}:
                raise ValueError("R12 modifies only weak-slew delay=1/2 cases")
            if actual_delay != modeled_delay or not math.isclose(
                actual_slew, modeled_slew, abs_tol=1e-12
            ):
                raise ValueError("R12 trusted finite model must match the actual pair")
            horizon = int(spec["horizon_steps"])
            if horizon != WEAK_HORIZON or horizon != self.horizon_steps:
                raise ValueError("R12 environment horizon must remain exactly 37 steps")

            first_affected_state = int(
                spec["anticipatory_first_affected_state_step"]
            )
            issue_start = _transition_issue_step(
                first_affected_state, actual_delay
            )

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
                partial["stage4_1r12_controller_revision"] = CONTROLLER_REVISION
                return _json_safe(partial)

            trajectory = copy.deepcopy(list(partial.get("trajectory") or []))
            main_trace = copy.deepcopy(list(partial.get("control_trace") or []))
            if len(trajectory) != issue_start + 1 or len(main_trace) != issue_start:
                raise ValueError("partial main-control prefix length mismatch")
            checkpoint = partial.get("partial_main_control_checkpoint") or {}
            if int(checkpoint.get("state_index", -1)) != issue_start:
                raise ValueError("partial main-control checkpoint state mismatch")
            if bool(checkpoint.get("future_measurement_used", True)):
                raise ValueError("partial main-control checkpoint used future measurement")

            checkpoint_queue = list(checkpoint.get("queue") or [])
            if len(checkpoint_queue) != actual_delay:
                raise ValueError("partial main-control queue length mismatch")
            queue = [
                {
                    "origin": "main_control",
                    "origin_index": issue_start - actual_delay + index,
                    "command": np.asarray(item["command"], dtype=float).reshape(
                        N_MODES
                    ),
                    "desired_physical": np.asarray(
                        item["desired_physical"], dtype=float
                    ).reshape(N_MODES),
                }
                for index, item in enumerate(checkpoint_queue)
            ]
            previous_correction = np.asarray(
                checkpoint.get("previous_correction_physical", np.zeros(N_MODES)),
                dtype=float,
            ).reshape(N_MODES)

            target = np.asarray(
                [
                    float(self.base_worker.cfg["target"]["R"])
                    + float(spec.get("target_R_offset_m", 0.0)),
                    float(self.base_worker.cfg["target"]["Z"])
                    + float(spec.get("target_Z_offset_m", 0.0)),
                    float(self.base_worker.cfg["target"]["Ip"])
                    + float(spec.get("target_Ip_offset_A", 0.0)),
                ],
                dtype=float,
            )
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
            controller_scale = float(spec["terminal_controller_scale"])
            model_scale = float(
                spec.get("terminal_controller_model_scale", 1.0)
            )
            velocity_gain = float(spec["terminal_velocity_measurement_gain"])
            position_gain = float(spec["terminal_position_measurement_gain"])
            ip_gain = float(spec.get("terminal_ip_measurement_gain", 1.0))
            phase_cap = int(spec["terminal_model_phase_cap_step"])
            nominal_physical = np.zeros((35, N_MODES), dtype=float)
            nominal_feature = np.zeros(35 * 5, dtype=float)
            integral = np.zeros(5, dtype=float)
            actual_gain = np.asarray(
                spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]),
                dtype=float,
            ).reshape(N_MODES)
            controller_gain = np.asarray(
                spec.get("controller_gain_estimate_by_mode", [1.0, 1.0, 1.0]),
                dtype=float,
            ).reshape(N_MODES)
            actuator_bias = np.asarray(
                spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]),
                dtype=float,
            ).reshape(N_MODES)

            damping_trace: list[dict[str, Any]] = []
            streaming_consistent = True
            failure_reason = ""
            for env_step in range(issue_start, horizon):
                measurement_physical = r9._terminal_measurement(
                    trajectory, target, dt_s
                )
                measurement_normalized, measurement_for_solver = (
                    _measurement_for_solver(
                        measurement_physical,
                        measurement_scales,
                        position_gain=position_gain,
                        velocity_gain=velocity_gain,
                        ip_gain=ip_gain,
                    )
                )
                modeled_pending = [
                    np.asarray(item["desired_physical"], dtype=float)
                    for item in queue[:modeled_delay]
                ]
                if len(modeled_pending) != modeled_delay:
                    raise ValueError("R12 modeled pending queue length mismatch")
                solver_step = min(int(env_step), phase_cap)
                solve = r3.solve_delay_aware_physical_correction(
                    self.base_worker.stub,
                    self.bundle,
                    current_step=solver_step,
                    modeled_action_delay_steps=modeled_delay,
                    modeled_pending_physical_coefficients=modeled_pending,
                    nominal_physical_coefficients=nominal_physical,
                    nominal_feature=nominal_feature,
                    measurement_normalized=measurement_for_solver,
                    integral_normalized=integral,
                    previous_correction=previous_correction,
                    controller_scale=controller_scale,
                    controller_model_scale=model_scale,
                )
                correction = np.asarray(
                    solve["first_correction"], dtype=float
                ).reshape(N_MODES)
                desired_physical = np.clip(
                    correction,
                    self.base_worker.lower_mode,
                    self.base_worker.upper_mode,
                )
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
                    "origin": "anticipatory_damping",
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
                action = self.base_worker._mode_action(
                    effective, currents_before
                )
                _, _, terminated, truncated, info = self.base_worker.env.step(action)
                state_index = env_step + 1
                trajectory.append(
                    r3.base._state_record(
                        self.base_worker.env, state_index, action
                    )
                )
                currents_after = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                row = {
                    "step": int(env_step),
                    "reference_step": int(env_step),
                    "issue_step": int(env_step),
                    "state_index_before": int(env_step),
                    "state_index_after": int(state_index),
                    "first_affected_state_step": int(first_affected_state),
                    "transition_issue_start_step": int(issue_start),
                    "measurement_max_state_index_used": int(env_step),
                    "future_measurement_used": False,
                    "measurement_source": (
                        "r12_direct_causal_original_deadline_damping"
                    ),
                    "measurement_physical": measurement_physical.tolist(),
                    "measurement_normalized": measurement_normalized.tolist(),
                    "measurement_for_solver": measurement_for_solver.tolist(),
                    "solver_model_phase_step": int(solver_step),
                    "modeled_action_delay_steps": int(modeled_delay),
                    "actual_action_delay_steps": int(actual_delay),
                    "queue_before": queue_before,
                    "queue_after": r9._queue_origins(queue),
                    "issued_origin": {
                        "origin": "anticipatory_damping",
                        "origin_index": int(env_step),
                    },
                    "applied_origin": {
                        "origin": str(applied_item["origin"]),
                        "origin_index": int(applied_item["origin_index"]),
                    },
                    "mode_correction_physical": correction.tolist(),
                    "previous_correction_physical": previous_correction.tolist(),
                    "desired_physical_mode_coefficients": desired_physical.tolist(),
                    "issued_desired_physical_mode_coefficients": (
                        desired_physical.tolist()
                    ),
                    "issued_mode_coefficients": issued_command.tolist(),
                    "applied_desired_physical_mode_coefficients": np.asarray(
                        applied_item["desired_physical"], dtype=float
                    ).tolist(),
                    "applied_command_mode_coefficients": applied_command.tolist(),
                    "effective_mode_coefficients": effective.tolist(),
                    "solver_success": bool(solve.get("solver_success", False)),
                    "solver_status": int(solve.get("solver_status", 0)),
                    "solver_cost": float(solve.get("solver_cost", 0.0)),
                    "solver_effect_step": int(solve.get("effect_step", -1)),
                    "solver_fixed_pending_steps": int(
                        solve.get("fixed_pending_steps", modeled_delay)
                    ),
                    "predicted_normalized_residual_rms": float(
                        solve.get("predicted_normalized_residual_rms", 0.0)
                    ),
                    "scheduler_predicted_mismatch_rms_a": float(
                        scheduled.get("mismatch_rms_a", 0.0)
                    ),
                    "scheduler_predicted_mismatch_max_abs_a": float(
                        scheduled.get("mismatch_max_abs_a", 0.0)
                    ),
                    "currents_before_A": currents_before.tolist(),
                    "currents_after_A": currents_after.tolist(),
                    "actual_current_delta_A": (
                        currents_after - currents_before
                    ).tolist(),
                    "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                }
                damping_trace.append(row)
                previous_correction = desired_physical.copy()
                if terminated:
                    failure_reason = str(
                        info.get("failure_reason", "R12 damping terminated")
                    )
                    break
                if truncated and state_index < horizon:
                    failure_reason = (
                        "environment truncated before R12 370 ms horizon"
                    )
                    break

            combined_trace = main_trace + damping_trace
            first_observed_affected_state: int | None = None
            for row in damping_trace:
                if str((row.get("applied_origin") or {}).get("origin")) == (
                    "anticipatory_damping"
                ):
                    first_observed_affected_state = int(row["state_index_after"])
                    break
            result = copy.deepcopy(partial)
            result.update(
                {
                    "schema_version": SCHEMA_VERSION,
                    "controller_revision": CONTROLLER_REVISION,
                    "stage4_1r12_controller_revision": CONTROLLER_REVISION,
                    "spec": copy.deepcopy(spec),
                    "trajectory": trajectory,
                    "control_trace": combined_trace,
                    "main_control_trace": main_trace,
                    "anticipatory_damping_trace": damping_trace,
                    "tail_queue_trace": damping_trace,
                    "anticipatory_damping_summary": {
                        "policy_id": spec["anticipatory_policy_id"],
                        "first_affected_state_step": int(first_affected_state),
                        "transition_issue_start_step": int(issue_start),
                        "expected_first_affected_state_step": int(
                            issue_start + actual_delay + 1
                        ),
                        "observed_first_affected_state_step": (
                            first_observed_affected_state
                        ),
                        "actual_delay_steps": int(actual_delay),
                        "modeled_delay_steps": int(modeled_delay),
                        "horizon_steps": int(horizon),
                        "damping_control_steps": len(damping_trace),
                        "continuous_streaming_queue": True,
                        "streaming_queue_consistent": bool(
                            streaming_consistent
                        ),
                        "final_pending_count": len(queue),
                        "final_pending_origins": r9._queue_origins(queue),
                        "future_measurement_used": any(
                            bool(row.get("future_measurement_used"))
                            for row in damping_trace
                        ),
                        "normal_slew_controller_changed": False,
                        "weak_slew_delay0_controller_changed": False,
                    },
                }
            )
            success = bool(
                not failure_reason
                and len(trajectory) == horizon + 1
                and len(damping_trace) == horizon - issue_start
                and len(queue) == actual_delay
                and streaming_consistent
                and first_observed_affected_state == first_affected_state
                and all(
                    bool(row.get("solver_success")) for row in damping_trace
                )
                and not any(
                    bool(row.get("abnormal", False)) for row in trajectory
                )
            )
            result["success"] = success
            result["failure_reason"] = (
                ""
                if success
                else (
                    failure_reason
                    or "incomplete/inconsistent R12 anticipatory damping rollout"
                )
            )
            result["wall_time_s"] = float(time.time() - started)
            failed = not success
            return _json_safe(result)
        except Exception as exc:
            failed = True
            return _json_safe(
                {
                    "schema_version": SCHEMA_VERSION,
                    "controller_revision": CONTROLLER_REVISION,
                    "experiment_id": spec.get("experiment_id", "unknown"),
                    "spec": copy.deepcopy(spec),
                    "success": False,
                    "failure_reason": repr(exc),
                    "traceback": traceback.format_exc(),
                    "wall_time_s": float(time.time() - started),
                    "trajectory": [],
                    "control_trace": [],
                    "main_control_trace": [],
                    "anticipatory_damping_trace": [],
                }
            )
        finally:
            self._cleanup_episode(
                failed=failed,
                reason="stage4_1r12_original_deadline_anticipatory_damping",
            )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage41R12Actor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalStage41R12Worker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R12Actor
    return _RAY_ACTOR


def materialize_variant(ctx: Stage41R12Context) -> tuple[str, dict[str, Any]]:
    variant, payload = r10.materialize_variant(
        ctx.r11_ctx.r10_ctx,
        slew_scale=WEAK_SLEW,
        horizon_steps=WEAK_HORIZON,
    )
    # Keep a stage-local copy for auditability while retaining the upstream
    # variant registry used by the shared worker chain.
    atomic_write_json(ctx.paths.variants / f"{variant}.payload.json", payload)
    return variant, payload


def evaluate_specs(
    ctx: Stage41R12Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variant, payload = materialize_variant(ctx)
    variants = ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.variants
    variants[variant] = payload
    pending = [
        spec
        for spec in specs
        if not (
            resume and _result_complete(output_dir / f"{spec['experiment_id']}.json.gz")
        )
    ]
    library = ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_library
    bundle = ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle
    selector_cfg = ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg["batch_selector"]
    if backend == "serial":
        worker = LocalStage41R12Worker(
            payload, library, bundle, "stage41r12_serial", selector_cfg
        )
        try:
            for index, spec in enumerate(pending, 1):
                atomic_write_json_gz(
                    output_dir / f"{spec['experiment_id']}.json.gz",
                    worker.evaluate(spec),
                )
                print(f"[Stage4.1R12 {variant}] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        requested = int(
            os.environ.get("STAGE4_1R12_WORKERS", ctx.cfg["parallel"]["n_workers"])
        )
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R12 weak-slew]",
        )
        Actor = _ray_actor_class()
        actors = [
            Actor.remote(
                payload,
                library,
                bundle,
                f"stage41r12_{index:03d}",
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
                    print(f"[Stage4.1R12 weak-slew] waiting {done}/{len(pending)}", flush=True)
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
                        print(f"[Stage4.1R12 weak-slew] {done}/{len(pending)}", flush=True)
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [
        read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs
    ]


def _source_scale(ctx: Stage41R12Context) -> float:
    return float(
        ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
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
    ctx: Stage41R12Context,
) -> dict[str, Any]:
    closure = ctx.cfg["weak_slew_closure"]
    first_affected = int(policy["first_affected_state_step"])
    start_issue = _transition_issue_step(first_affected, int(modeled_delay))
    generic_policy = {
        "horizon_steps": WEAK_HORIZON,
        "tail_steps": 0,
        "tail_policy": "r12_streaming_anticipatory_damping",
        "policy_id": str(policy["policy_id"]),
    }
    extra = r8._main_extra(
        ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
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
            "tail_policy": "r12_streaming_anticipatory_damping",
            "anticipatory_policy_id": str(policy["policy_id"]),
            "anticipatory_first_affected_state_step": first_affected,
            "anticipatory_transition_issue_step": start_issue,
            "terminal_model_phase_cap_step": int(
                closure["terminal_model_phase_cap_step"]
            ),
            "terminal_controller_scale": float(closure["terminal_controller_scale"]),
            "terminal_velocity_measurement_gain": float(
                closure["terminal_velocity_measurement_gain"]
            ),
            "terminal_position_measurement_gain": float(
                closure["terminal_position_measurement_gain"]
            ),
            "terminal_ip_measurement_gain": float(
                closure["terminal_ip_measurement_gain"]
            ),
            "terminal_controller_model_scale": float(
                closure["terminal_controller_model_scale"]
            ),
            "terminal_integral_mode": str(closure["terminal_integral_mode"]),
            "terminal_nominal_physical_mode": str(
                closure["terminal_nominal_physical_mode"]
            ),
            "terminal_initial_previous_correction": str(
                closure["terminal_initial_previous_correction"]
            ),
            "formal_arrival_deadline_step": 27,
            "formal_hold_through_step": 37,
            "arrival_deadline_expansion_allowed": False,
            "normal_slew_controller_changed": False,
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
        "kind": "stage4_1r12_original_deadline_weak_slew_anticipatory_damping",
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


def build_development_specs(ctx: Stage41R12Context) -> list[dict[str, Any]]:
    closure = ctx.cfg["weak_slew_closure"]
    variant, _ = materialize_variant(ctx)
    target = closure["development_target"]
    specs: list[dict[str, Any]] = []
    for policy in closure["candidate_bank"]:
        for delay in closure["actual_delay_steps"]:
            specs.append(
                _make_spec(
                    phase="oracle_development",
                    policy=policy,
                    target=target,
                    actual_delay=int(delay),
                    modeled_delay=int(delay),
                    calibration_token=None,
                    trusted=True,
                    controller_variant="r12_oracle_development",
                    environment_variant=variant,
                    ctx=ctx,
                )
            )
    return specs


def _selected_policy(ctx: Stage41R12Context) -> dict[str, Any] | None:
    if not ctx.paths.state.is_file():
        return None
    summary = (read_json(ctx.paths.state).get("oracle_development_summary") or {})
    selected = summary.get("selected_policy_id")
    if not selected:
        return None
    for row in ctx.cfg["weak_slew_closure"]["candidate_bank"]:
        if str(row["policy_id"]) == str(selected):
            return copy.deepcopy(row)
    raise ValueError(f"selected R12 policy is not in candidate bank: {selected}")


def build_holdout_specs(ctx: Stage41R12Context) -> list[dict[str, Any]]:
    policy = _selected_policy(ctx)
    if policy is None:
        return []
    closure = ctx.cfg["weak_slew_closure"]
    variant, _ = materialize_variant(ctx)
    target = closure["holdout_target"]
    return [
        _make_spec(
            phase="oracle_holdout",
            policy=policy,
            target=target,
            actual_delay=int(delay),
            modeled_delay=int(delay),
            calibration_token=None,
            trusted=True,
            controller_variant="r12_oracle_holdout",
            environment_variant=variant,
            ctx=ctx,
        )
        for delay in closure["actual_delay_steps"]
    ]


def _trusted_tokens(ctx: Stage41R12Context) -> dict[tuple[int, float], dict[str, Any]]:
    tokens = r9.source_calibration_tokens(ctx.r11_ctx.r10_ctx.r9_ctx)
    required = {(1, WEAK_SLEW), (2, WEAK_SLEW)}
    missing = required - set(tokens)
    if missing:
        raise ValueError(f"R12 missing weak-slew calibration tokens: {sorted(missing)}")
    output: dict[tuple[int, float], dict[str, Any]] = {}
    for key in required:
        row = tokens[key]
        if not bool(row.get("success")):
            raise ValueError(f"R12 calibration token environment failure: {key}")
        if not bool(row.get("batch_trusted")) or not bool(
            row.get("batch_trusted_correct")
        ):
            raise ValueError(f"R12 calibration token is not trusted-correct: {key}")
        if bool(row.get("batch_wrong_accept")):
            raise ValueError(f"R12 calibration token is a wrong accept: {key}")
        if int(row.get("batch_selected_delay_steps", -999)) != key[0]:
            raise ValueError(f"R12 calibration token delay mismatch: {key}")
        if not math.isclose(
            _as_float(row.get("batch_selected_slew_scale"), math.nan),
            key[1],
            abs_tol=1e-12,
        ):
            raise ValueError(f"R12 calibration token slew mismatch: {key}")
        output[key] = row
    return output


def build_calibrated_specs(ctx: Stage41R12Context) -> list[dict[str, Any]]:
    state = read_json(ctx.paths.state)
    if not bool((state.get("oracle_holdout_summary") or {}).get("passed")):
        return []
    policy = _selected_policy(ctx)
    if policy is None:
        return []
    tokens = _trusted_tokens(ctx)
    variant, _ = materialize_variant(ctx)
    specs: list[dict[str, Any]] = []
    for delay in (1, 2):
        token = tokens[(delay, WEAK_SLEW)]
        for target in ctx.cfg["calibrated_confirmation"]["targets"]:
            specs.append(
                _make_spec(
                    phase="calibrated_confirmation",
                    policy=policy,
                    target=target,
                    actual_delay=delay,
                    modeled_delay=int(token["batch_selected_delay_steps"]),
                    calibration_token=str(token["experiment_id"]),
                    trusted=True,
                    controller_variant="r12_calibrated_confirmation",
                    environment_variant=variant,
                    ctx=ctx,
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


def _control_array(
    result: Mapping[str, Any], field: str, *, count: int | None = None
) -> np.ndarray:
    rows = list(result.get("control_trace") or [])
    if count is not None:
        rows = rows[:count]
    return np.asarray([row.get(field, [0.0] * N_MODES) for row in rows], dtype=float)


def _damping_array(result: Mapping[str, Any], field: str) -> np.ndarray:
    return np.asarray(
        [row.get(field, [0.0] * N_MODES) for row in (result.get("anticipatory_damping_trace") or [])],
        dtype=float,
    )


def _prefix_audit(
    source: Mapping[str, Any], result: Mapping[str, Any], *, atol: float
) -> dict[str, Any]:
    spec = result["spec"]
    first_state = int(spec["anticipatory_first_affected_state_step"])
    delay = int(spec["action_delay_steps"])
    issue_start = _transition_issue_step(first_state, delay)
    source_physics = _physics_array(source, count=first_state)
    current_physics = _physics_array(result, count=first_state)
    source_issued = _control_array(source, "issued_mode_coefficients", count=issue_start)
    current_issued = _control_array(result, "issued_mode_coefficients", count=issue_start)
    # Issued commands may change beginning at issue_start.  Applied commands
    # must remain identical until the state immediately before first_affected.
    applied_prefix_steps = first_state - 1
    source_applied = _control_array(
        source, "applied_command_mode_coefficients", count=applied_prefix_steps
    )
    current_applied = _control_array(
        result, "applied_command_mode_coefficients", count=applied_prefix_steps
    )
    trace = list(result.get("anticipatory_damping_trace") or [])
    no_future = bool(
        trace
        and all(
            not bool(row.get("future_measurement_used", False))
            and int(row.get("measurement_max_state_index_used", 10**9))
            <= int(row.get("state_index_before", -1))
            for row in trace
        )
    )
    summary = result.get("anticipatory_damping_summary") or {}
    return {
        "first_affected_state_step": first_state,
        "transition_issue_start_step": issue_start,
        "expected_first_affected_state_step": issue_start + delay + 1,
        "observed_first_affected_state_step": summary.get(
            "observed_first_affected_state_step"
        ),
        "physics_prefix_exact": bool(np.array_equal(current_physics, source_physics)),
        "physics_prefix_max_abs_difference": _finite_max_abs(current_physics, source_physics),
        "issued_prefix_exact": bool(np.array_equal(current_issued, source_issued)),
        "issued_prefix_max_abs_difference": _finite_max_abs(current_issued, source_issued),
        "applied_prefix_exact": bool(np.array_equal(current_applied, source_applied)),
        "applied_prefix_max_abs_difference": _finite_max_abs(current_applied, source_applied),
        "numeric_prefix_equal_atol": bool(
            np.allclose(current_physics, source_physics, rtol=0.0, atol=atol)
            and np.allclose(current_issued, source_issued, rtol=0.0, atol=atol)
            and np.allclose(current_applied, source_applied, rtol=0.0, atol=atol)
        ),
        "no_future_measurement": no_future,
        "streaming_queue_consistent": bool(summary.get("streaming_queue_consistent")),
        "anticipatory_damping_activated": bool(
            trace and int(summary.get("damping_control_steps", 0)) == len(trace)
        ),
        "first_effect_alignment_exact": bool(
            summary.get("observed_first_affected_state_step") == first_state
        ),
    }


def result_row(ctx: Stage41R12Context, result: Mapping[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    policy = {
        "policy_id": str(spec["anticipatory_policy_id"]),
        "horizon_steps": WEAK_HORIZON,
        "allowed_arrival_steps": [
            int(x) for x in ctx.cfg["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"]
        ],
    }
    metrics = r8.tracking_metrics(
        ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx, result, policy
    )
    source_key = (
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        WEAK_SLEW,
    )
    source = _source_oracle_map(ctx)[source_key]
    prefix = _prefix_audit(
        source,
        result,
        atol=float(ctx.cfg["weak_slew_closure"]["prefix_numeric_atol"]),
    )
    closure = ctx.cfg["weak_slew_closure"]
    composite = bool(
        result.get("success")
        and metrics.get("stage3_4_target_tracking_pass")
        and prefix["physics_prefix_exact"]
        and prefix["issued_prefix_exact"]
        and prefix["applied_prefix_exact"]
        and prefix["numeric_prefix_equal_atol"]
        and prefix["no_future_measurement"]
        and prefix["streaming_queue_consistent"]
        and prefix["anticipatory_damping_activated"]
        and prefix["first_effect_alignment_exact"]
        and _as_float(metrics.get("max_current_utilization"), math.inf)
        <= float(closure["maximum_current_utilization"]) + 1e-12
    )
    damping = result.get("anticipatory_damping_summary") or {}
    trajectory = list(result.get("trajectory") or [])
    action_rows = np.asarray(
        [row.get("action_norm_tsc", [0.0] * 14) for row in trajectory[1:]],
        dtype=float,
    )
    action_rms = float(np.sqrt(np.mean(action_rows**2))) if action_rows.size else 0.0
    delta_action_rms = (
        float(np.sqrt(np.mean(np.diff(action_rows, axis=0) ** 2)))
        if action_rows.ndim == 2 and action_rows.shape[0] > 1
        else 0.0
    )
    return {
        "experiment_id": result.get("experiment_id"),
        "phase": spec.get("phase"),
        "policy_id": spec.get("anticipatory_policy_id"),
        "target_id": spec.get("target_id"),
        "actual_delay_steps": spec.get("action_delay_steps"),
        "actual_slew_scale": spec.get("slew_scale"),
        "calibration_token": spec.get("calibration_token"),
        "environment_success": bool(result.get("success")),
        "failure_reason": result.get("failure_reason", ""),
        "formal_arrival_deadline_step": 27,
        "formal_hold_through_step": 37,
        "formal_contract_tracking_pass": bool(
            metrics.get("stage3_4_target_tracking_pass")
        ),
        "formal_contract_minimum_signed_margin": metrics.get(
            "stage3_4_tracking_minimum_signed_margin"
        ),
        "best_endpoint_step": metrics.get("stage3_4_best_endpoint_step"),
        "terminal_speed_m_per_s": metrics.get("terminal_velocity_m_per_s"),
        "post_arrival_speed_rms_m_per_s": metrics.get(
            "stage3_4_post_arrival_velocity_rms_m_per_s"
        ),
        "sustained_box_error_m": metrics.get("stage3_4_sustained_box_max_error_m"),
        "max_current_utilization": metrics.get("max_current_utilization"),
        "action_rms": action_rms,
        "delta_action_rms": delta_action_rms,
        "legacy_metrics_action_rms_was_not_used": True,
        "first_affected_state_step": damping.get("first_affected_state_step"),
        "transition_issue_start_step": damping.get("transition_issue_start_step"),
        "physics_prefix_exact": prefix["physics_prefix_exact"],
        "issued_prefix_exact": prefix["issued_prefix_exact"],
        "applied_prefix_exact": prefix["applied_prefix_exact"],
        "prefix_max_abs_difference": max(
            prefix["physics_prefix_max_abs_difference"],
            prefix["issued_prefix_max_abs_difference"],
            prefix["applied_prefix_max_abs_difference"],
        ),
        "no_future_measurement": prefix["no_future_measurement"],
        "streaming_queue_consistent": prefix["streaming_queue_consistent"],
        "anticipatory_damping_activated": prefix["anticipatory_damping_activated"],
        "first_effect_alignment_exact": prefix["first_effect_alignment_exact"],
        "r12_composite_pass": composite,
        "physics_signature": _array_digest(_physics_array(result), "physics"),
        "issued_signature": _array_digest(
            _control_array(result, "issued_mode_coefficients"), "issued"
        ),
        "applied_signature": _array_digest(
            _control_array(result, "applied_command_mode_coefficients"), "applied"
        ),
        "damping_issued_signature": _array_digest(
            _damping_array(result, "issued_mode_coefficients"), "dampingissued"
        ),
        "damping_applied_signature": _array_digest(
            _damping_array(result, "applied_command_mode_coefficients"), "dampingapplied"
        ),
    }


def _policy_summary(
    ctx: Stage41R12Context, rows: Sequence[Mapping[str, Any]], policy_id: str
) -> dict[str, Any]:
    subset = [row for row in rows if str(row.get("policy_id")) == str(policy_id)]
    expected = len(ctx.cfg["weak_slew_closure"]["actual_delay_steps"])
    coverage = bool(
        len(subset) == expected
        and {int(row["actual_delay_steps"]) for row in subset} == {1, 2}
    )
    pass_fraction = (
        sum(bool(row.get("r12_composite_pass")) for row in subset) / len(subset)
        if subset
        else 0.0
    )
    minimum_margin = min(
        (_as_float(row.get("formal_contract_minimum_signed_margin"), -1e12) for row in subset),
        default=-1e12,
    )
    mean_margin = float(
        np.mean([
            _as_float(row.get("formal_contract_minimum_signed_margin"), -1e12)
            for row in subset
        ])
    ) if subset else -1e12
    max_final_speed = max(
        (_as_float(row.get("terminal_speed_m_per_s"), math.inf) for row in subset),
        default=math.inf,
    )
    mean_action_rms = float(
        np.mean([_as_float(row.get("action_rms"), math.inf) for row in subset])
    ) if subset else math.inf
    candidate_steps = {
        int(row.get("first_affected_state_step"))
        for row in subset
        if row.get("first_affected_state_step") is not None
    }
    first_effect = next(iter(candidate_steps)) if len(candidate_steps) == 1 else None
    passed = bool(
        coverage
        and pass_fraction >= float(ctx.cfg["weak_slew_closure"]["minimum_tracking_fraction"])
        and minimum_margin >= float(ctx.cfg["weak_slew_closure"]["minimum_tracking_signed_margin"]) - 1e-12
    )
    return {
        "policy_id": policy_id,
        "n_rollouts": len(subset),
        "expected_rollouts": expected,
        "coverage_complete": coverage,
        "first_affected_state_step": first_effect,
        "composite_pass_fraction": pass_fraction,
        "minimum_original_contract_signed_margin": minimum_margin,
        "mean_original_contract_signed_margin": mean_margin,
        "maximum_terminal_speed_m_per_s": max_final_speed,
        "mean_action_rms": mean_action_rms,
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
            subset and all(bool(row.get("streaming_queue_consistent")) for row in subset)
        ),
        "passed": passed,
    }


def run_development(ctx: Stage41R12Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_development_specs(ctx)
    raw_dir = ctx.paths.oracle_development / "raw"
    results = evaluate_specs(ctx, specs, output_dir=raw_dir, backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    policies = [str(row["policy_id"]) for row in ctx.cfg["weak_slew_closure"]["candidate_bank"]]
    summaries = [_policy_summary(ctx, rows, policy_id) for policy_id in policies]
    passing = [row for row in summaries if bool(row["passed"])]
    selected = None
    if passing:
        selected = max(
            passing,
            key=lambda row: (
                float(row["minimum_original_contract_signed_margin"]),
                float(row["mean_original_contract_signed_margin"]),
                int(row.get("first_affected_state_step") or -1),
                -float(row["maximum_terminal_speed_m_per_s"]),
                -float(row["mean_action_rms"]),
            ),
        )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "oracle_development",
        "development_target_id": ctx.cfg["weak_slew_closure"]["development_target"]["target_id"],
        "holdout_target_id": ctx.cfg["weak_slew_closure"]["holdout_target"]["target_id"],
        "candidate_selection_uses_holdout": False,
        "formal_arrival_deadline_step": 27,
        "formal_hold_through_step": 37,
        "arrival_deadline_expanded": False,
        "candidate_first_effect_steps": [
            int(row["first_affected_state_step"])
            for row in ctx.cfg["weak_slew_closure"]["candidate_bank"]
        ],
        "candidate_window_ms": [280, 350],
        "candidate_first_physical_effect_is_strictly_after_270ms": True,
        "source_physics_through_270ms_is_unchanged": True,
        "unaffected_14_paths_are_not_rerun_or_modified": True,
        "n_rollouts": len(rows),
        "expected_rollouts": 12,
        "coverage_complete": len(rows) == 12 and len({row["experiment_id"] for row in rows}) == 12,
        "policy_summaries": summaries,
        "selected_policy_id": None if selected is None else selected["policy_id"],
        "selected_policy_minimum_signed_margin": None if selected is None else selected["minimum_original_contract_signed_margin"],
        "passed": selected is not None,
    }
    atomic_write_json(ctx.paths.oracle_development / "results.json", rows)
    write_csv(ctx.paths.oracle_development / "results.csv", rows)
    atomic_write_json(ctx.paths.oracle_development / "summary.json", summary)
    _update_state(ctx, oracle_development_complete=True, oracle_development_summary=summary)
    return summary


def run_holdout(ctx: Stage41R12Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_holdout_specs(ctx)
    if not specs:
        summary = {"schema_version": 1, "stage": STAGE, "phase": "oracle_holdout", "status": "not_run", "passed": False}
        atomic_write_json(ctx.paths.oracle_holdout / "summary.json", summary)
        return summary
    results = evaluate_specs(
        ctx, specs, output_dir=ctx.paths.oracle_holdout / "raw", backend=backend, resume=resume
    )
    rows = [result_row(ctx, result) for result in results]
    selected = str(specs[0]["anticipatory_policy_id"])
    policy_summary = _policy_summary(ctx, rows, selected)
    passed = bool(policy_summary["passed"] and len(rows) == 2)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "oracle_holdout",
        "selected_policy_id": selected,
        "holdout_target_id": ctx.cfg["weak_slew_closure"]["holdout_target"]["target_id"],
        "holdout_was_not_used_for_policy_selection": True,
        "formal_arrival_deadline_step": 27,
        "formal_hold_through_step": 37,
        "arrival_deadline_expanded": False,
        "n_rollouts": len(rows),
        "expected_rollouts": 2,
        "policy_summary": policy_summary,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.oracle_holdout / "results.json", rows)
    write_csv(ctx.paths.oracle_holdout / "results.csv", rows)
    atomic_write_json(ctx.paths.oracle_holdout / "summary.json", summary)
    _update_state(ctx, oracle_holdout_complete=True, oracle_holdout_summary=summary)
    return summary


def _oracle_selected_raw(ctx: Stage41R12Context) -> dict[tuple[str, int], dict[str, Any]]:
    selected = _selected_policy(ctx)
    if selected is None:
        return {}
    selected_id = str(selected["policy_id"])
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for phase in (ctx.paths.oracle_development, ctx.paths.oracle_holdout):
        for result in [read_json_gz(path) for path in sorted((phase / "raw").glob("*.json.gz"))]:
            spec = result.get("spec") or {}
            if str(spec.get("anticipatory_policy_id")) != selected_id:
                continue
            key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
            if key in output:
                raise ValueError(f"duplicate selected R12 Oracle case: {key}")
            output[key] = result
    return output


def _comparison_components(result: Mapping[str, Any]) -> dict[str, np.ndarray]:
    return {
        "physics": _physics_array(result),
        "issued": _control_array(result, "issued_mode_coefficients"),
        "applied": _control_array(result, "applied_command_mode_coefficients"),
        "damping_issued": _damping_array(result, "issued_mode_coefficients"),
        "damping_applied": _damping_array(
            result, "applied_command_mode_coefficients"
        ),
    }


def run_calibrated_confirmation(
    ctx: Stage41R12Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_calibrated_specs(ctx)
    if not specs:
        summary = {"schema_version": 1, "stage": STAGE, "phase": "calibrated_confirmation", "status": "not_run", "passed": False}
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
    oracle = _oracle_selected_raw(ctx)
    comparisons: list[dict[str, Any]] = []
    atol = float(ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"])
    for result in results:
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key not in oracle:
            raise ValueError(f"missing selected Oracle comparison for {key}")
        left = _comparison_components(result)
        right = _comparison_components(oracle[key])
        component_diff = {name: _finite_max_abs(left[name], right[name]) for name in left}
        exact = all(np.array_equal(left[name], right[name]) for name in left)
        numeric = all(
            np.allclose(left[name], right[name], rtol=0.0, atol=atol) for name in left
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
    pass_fraction = sum(bool(row.get("r12_composite_pass")) for row in rows) / len(rows)
    exact_fraction = sum(bool(row["exact_trace_equal_to_oracle"]) for row in comparisons) / len(comparisons)
    numeric_fraction = sum(bool(row["numeric_trace_equal_to_oracle"]) for row in comparisons) / len(comparisons)
    tokens = {str(row.get("calibration_token")) for row in rows if row.get("calibration_token")}
    untrusted = sum(
        not bool((result.get("spec") or {}).get("trusted_calibration_model")) for result in results
    )
    passed = bool(
        len(rows) == 4
        and pass_fraction >= 1.0
        and len(tokens) == 2
        and untrusted == 0
        and exact_fraction >= float(ctx.cfg["calibrated_confirmation"]["minimum_trace_equivalence_fraction"])
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
            (float(row["maximum_trace_abs_difference"]) for row in comparisons),
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


def _source_calibrated_map(
    ctx: Stage41R12Context,
) -> dict[tuple[str, int, float], dict[str, Any]]:
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for result in _phase_raw(
        ctx.source_stage41r11_run, "stage4_1r11_calibrated_long_hold"
    ):
        spec = result.get("spec") or {}
        key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        if key in output:
            raise ValueError(f"duplicate source R11 calibrated case: {key}")
        output[key] = result
    if len(output) != 18:
        raise ValueError(
            f"expected 18 source R11 calibrated cases, got {len(output)}"
        )
    return output


def _r12_calibrated_map(
    ctx: Stage41R12Context,
) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((ctx.paths.calibrated_confirmation / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result.get("spec") or {}
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key in output:
            raise ValueError(f"duplicate R12 calibrated case: {key}")
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


def run_formal_grid_confirmation(ctx: Stage41R12Context) -> dict[str, Any]:
    source_oracle = _source_oracle_map(ctx)
    source_calibrated = _source_calibrated_map(ctx)
    selected_oracle = _oracle_selected_raw(ctx)
    selected_calibrated = _r12_calibrated_map(ctx)
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
                raise ValueError(f"missing R12 affected formal-grid case: {pair_key}")
            oracle_result = selected_oracle[pair_key]
            calibrated_result = selected_calibrated[pair_key]
            path = "r12_anticipatory_damping"
            affected_row = result_row(ctx, oracle_result)
            path_guard = bool(affected_row["r12_composite_pass"])
        else:
            oracle_result = source_oracle[key]
            calibrated_result = source_calibrated[key]
            path = "source_unchanged_r11_prefix"
            path_guard = True
        policy = _timing_policy(
            ctx, slew, policy_id=f"formal_{target}_d{delay}_s{slew:.1f}"
        )
        horizon = int(policy["horizon_steps"])
        oracle_slice = _slice_result(oracle_result, horizon)
        calibrated_slice = _slice_result(calibrated_result, horizon)
        metrics = r8.tracking_metrics(
            ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx, oracle_slice, policy
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
    affected_rows = [row for row in rows if row["controller_path"] == "r12_anticipatory_damping"]
    unchanged_rows = [row for row in rows if row["controller_path"] != "r12_anticipatory_damping"]
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
        "affected_r12_cases": len(affected_rows),
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


def run_restart_audit(ctx: Stage41R12Context) -> dict[str, Any]:
    simulation_root = Path(
        ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg[
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
        "availability_requirement_for_stage4_1r12": False,
        "audit_completed": True,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart_audit / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


def finalize(ctx: Stage41R12Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    development = state.get("oracle_development_summary") or {}
    holdout = state.get("oracle_holdout_summary") or {}
    calibrated = state.get("calibrated_confirmation_summary") or {}
    formal_grid = state.get("formal_grid_confirmation_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    primary_pass = bool(
        source.get("passed")
        and development.get("passed")
        and holdout.get("passed")
        and calibrated.get("passed")
        and formal_grid.get("passed")
    )
    verdict_name = (
        "STAGE4_1R12_ORIGINAL_250_270MS_DEADLINE_STATIC_GRID_CLOSURE"
        if primary_pass
        else "STAGE4_1R12_ORIGINAL_DEADLINE_CLOSURE_INCOMPLETE"
    )
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "verdict": verdict_name,
        "primary_pass": primary_pass,
        "formal_timing_contract_restored": primary_pass,
        "formal_combined_case_count": 18,
        "unchanged_source_case_count": 14,
        "newly_closed_modified_case_count": 4 if primary_pass else 0,
        "normal_slew_arrival_deadline_ms": 250,
        "normal_slew_hold_through_ms": 350,
        "weak_slew_arrival_deadline_ms": 270,
        "weak_slew_hold_through_ms": 370,
        "arrival_deadline_expanded": False,
        "source_r11_long_hold_retained_as_diagnostic_only": True,
        "stage4_2r1_was_not_run_or_reused": True,
        "selected_weak_slew_policy": development.get("selected_policy_id"),
        "normal_slew_controller_changed": False,
        "weak_slew_delay0_controller_changed": False,
        "trusted_calibration_required": True,
        "true_restart_validation_available": restart.get("true_restart_validation_available", False),
        "true_restart_validation_performed": False,
        "plant_parameter_robustness_validated": False,
        "continuous_parameter_change_validated": False,
        "terminal_measurement_noise_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "finite_test_envelope_only": True,
        "next_if_pass": (
            "Proceed to true restart and hidden vessel/eddy-history validation using "
            "the original-deadline controller. Do not use the late-arrival R10/R11 "
            "trajectory as the expert timing contract, and do not start BC/DAgger/RL yet."
        ),
        "next_if_fail": (
            "Do not enlarge the 250/270 ms deadline. If every post-arrival damping onset fails, "
            "use the failed raw traces to fit a bounded late-phase local model and redesign the "
            "delay-pipeline-aware braking before 270 ms while retaining the same formal gate."
        ),
        "final_task": ctx.cfg["final_task"],
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "source_stage4_1r11_run": str(ctx.source_stage41r11_run),
        "phases": {
            "source_audit": source,
            "oracle_development": development,
            "oracle_holdout": holdout,
            "calibrated_confirmation": calibrated,
            "formal_grid_confirmation": formal_grid,
            "restart_audit": restart,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r12_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_1r12_summary.json", summary)
    _update_state(
        ctx,
        finished=True,
        stop_reason="" if primary_pass else "formal_original_deadline_closure_failed",
    )
    return summary


def execute(
    ctx: Stage41R12Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    command = str(command)
    if command not in {
        "all", "audit", "development", "holdout", "confirmation", "grid"
    }:
        raise ValueError(
            "command must be all/audit/development/holdout/confirmation/grid"
        )
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
    if command in {"all", "holdout"} and not bool(state.get("oracle_holdout_complete")):
        holdout = run_holdout(ctx, backend=backend, resume=resume)
        if not holdout.get("passed"):
            _update_state(ctx, oracle_holdout_complete=True, oracle_holdout_summary=holdout)
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "confirmation"} and not bool(
        state.get("calibrated_confirmation_complete")
    ):
        calibrated = run_calibrated_confirmation(ctx, backend=backend, resume=resume)
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
        / "stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json"
    )
    cfg = read_json(cfg_path)
    validate_config(cfg)
    candidate_steps = [
        int(row["first_affected_state_step"])
        for row in cfg["weak_slew_closure"]["candidate_bank"]
    ]
    transitions = {
        (first, delay): _transition_issue_step(first, delay)
        for first in candidate_steps
        for delay in (1, 2)
    }
    alignment = all(issue + delay + 1 == first for (first, delay), issue in transitions.items())
    no_deadline_expansion = bool(
        max(cfg["formal_timing_contract"]["normal_slew"]["allowed_arrival_steps"]) == 25
        and max(cfg["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"]) == 27
        and cfg["weak_slew_closure"]["horizon_steps"] == 37
    )
    post_deadline_only = bool(
        candidate_steps == [28, 30, 32, 33, 34, 35]
        and min(candidate_steps) > 27
        and cfg["weak_slew_closure"].get("preserve_source_physics_through_arrival_deadline")
        and not cfg["weak_slew_closure"].get("modified_paths_may_change_before_arrival_deadline")
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_valid": True,
        "transition_alignment_valid": alignment,
        "no_arrival_deadline_expansion": no_deadline_expansion,
        "post_deadline_first_effect_only": post_deadline_only,
        "candidate_first_affected_state_steps": candidate_steps,
        "candidate_count": len(cfg["weak_slew_closure"]["candidate_bank"]),
        "development_rollout_count": 12,
        "holdout_rollout_count": 2,
        "calibrated_rollout_count": 4,
        "maximum_true_tsc_rollouts": 18,
        "stage4_2r1_was_not_run_or_reused": bool(cfg.get("stage4_2r1_was_not_run_or_reused")),
        "passed": bool(
            alignment
            and no_deadline_expansion
            and post_deadline_only
            and cfg.get("stage4_2r1_was_not_run_or_reused")
        ),
    }


def _default_source(project_dir: Path) -> Path:
    env = os.environ.get("STAGE4_1R12_SOURCE_STAGE4_1R11_RUN")
    if env:
        return Path(env).expanduser().resolve()
    latest = project_dir / "stage4_1r11_runs" / "latest_stage4_1r11_run.txt"
    if latest.is_file():
        return Path(latest.read_text(encoding="utf-8").strip()).expanduser().resolve()
    raise FileNotFoundError(
        "set STAGE4_1R12_SOURCE_STAGE4_1R11_RUN or provide --source-stage4-1r11-run"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R12 original-deadline weak-slew anticipatory damping"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "configs"
        / "stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json",
    )
    parser.add_argument("--source-stage4-1r11-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command",
        choices=["all", "audit", "development", "holdout", "confirmation", "grid"],
        default=os.environ.get("STAGE4_1R12_COMMAND", "all"),
    )
    parser.add_argument(
        "--backend",
        choices=["ray", "serial"],
        default=os.environ.get("STAGE4_1R12_BACKEND", "ray"),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=os.environ.get("STAGE4_1R12_RESUME", "0") == "1",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    project_dir = args.config.expanduser().resolve().parents[1]
    if args.self_test:
        print(json.dumps(self_test(project_dir), indent=2, sort_keys=True))
        return
    source = args.source_stage4_1r11_run or _default_source(project_dir)
    ctx = load_stage41r12_config(
        args.config,
        source_stage41r11_run=source,
        run_dir_override=args.run_dir,
    )
    payload = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=args.resume,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
