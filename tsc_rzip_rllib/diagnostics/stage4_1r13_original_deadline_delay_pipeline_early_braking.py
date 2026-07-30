"""Stage4.1R13 original-deadline delay-pipeline early braking.

Stage4.1R12 was a useful but structurally incomplete experiment.  It preserved
all physics through the 270 ms weak-slew arrival deadline and allowed its first
new physical effect only at 280--350 ms.  The raw R12 evidence shows that the
nominal delay=1 path still fails the endpoint-late-speed constraint at 270 ms,
while the nominal delay=2 path is repaired after the deadline.  The two
RZ_p10_m10 source failures also violate the 270 ms endpoint-late-speed window.
No post-deadline controller can change those already-measured velocities.

R13 keeps the immutable timing contract:

* slew 1.0/1.1: arrive by 250 ms and hold through 350 ms;
* slew 0.9: arrive by 270 ms and hold through 370 ms.

Only the four known 0.9x-slew delay=1/2 paths may change.  The same bounded,
trusted-model, streaming delay-aware damping controller is moved into a causal
200--260 ms first-physical-effect bank.  Candidate commands are issued earlier
by exactly the known queue delay and may use only measurements available at the
original issue time.  One onset is selected independently for each trusted
delay using both required targets.  This is deliberate formal-grid closure, not
an unseen-target holdout claim.  The fourteen already-passing paths remain
source-exact and are not rerun.  No deadline or scoring horizon is expanded.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage3_2_margin_long_hold_mpc as s32
from . import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8
from . import stage4_1r10_queue_preview_terminal_transition_hold as r10
from . import stage4_1r11_frozen_terminal_long_horizon_hold as r11
from . import stage4_1r12_original_deadline_weak_slew_anticipatory_damping as r12
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r12.atomic_write_json
atomic_write_json_gz = r12.atomic_write_json_gz
read_json = r12.read_json
read_json_gz = r12.read_json_gz
utc_timestamp = r12.utc_timestamp
write_csv = r12.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R13"
CONTROLLER_REVISION = "original_deadline_delay_pipeline_early_braking_v13"
EXPECTED_SOURCE_REVISION = r12.CONTROLLER_REVISION
EXPECTED_SOURCE_PACKAGE_REVISION = r12.PACKAGE_REVISION
PACKAGE_REVISION = "r13_original_deadline_early_braking_v1"
WEAK_SLEW = 0.9
WEAK_HORIZON = 37
N_MODES = 3


def _json_safe(value: Any) -> Any:
    return r12._json_safe(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r12._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r12._sha256_file(path)


def _result_complete(path: Path) -> bool:
    return r12._result_complete(path)


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    return r12._finite_max_abs(left, right)


def _array_digest(array: np.ndarray, prefix: str) -> str:
    return r12._array_digest(np.asarray(array), prefix)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "s41r13_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class Stage41R13Paths:
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
    def from_run_dir(cls, run_dir: Path) -> "Stage41R13Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r13_source_reference",
            source_audit=run_dir / "stage4_1r13_source_audit",
            oracle_development=run_dir / "stage4_1r13_oracle_development",
            calibrated_confirmation=run_dir / "stage4_1r13_calibrated_confirmation",
            formal_grid_confirmation=run_dir / "stage4_1r13_formal_grid_confirmation",
            restart_audit=run_dir / "stage4_1r13_restart_audit",
            analysis=run_dir / "stage4_1r13_analysis",
            variants=run_dir / "stage4_1r13_environment_variants",
            state=run_dir / "stage4_1r13_state.json",
            manifest=run_dir / "stage4_1r13_manifest.json",
        )


@dataclass
class Stage41R13Context:
    cfg: dict[str, Any]
    paths: Stage41R13Paths
    project_dir: Path
    source_stage41r12_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    source_stage41r11_run: Path
    r12_ctx: r12.Stage41R12Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r12_manifest.json",
        source / "stage4_1r12_state.json",
        source / "stage4_1r12_config.resolved.json",
        source / "stage4_1r12_analysis" / "stage4_1r12_verdict.json",
        source / "stage4_1r12_analysis" / "stage4_1r12_summary.json",
        source / "stage4_1r12_source_audit" / "summary.json",
        source / "stage4_1r12_source_audit" / "original_timing_reaudit.csv",
        source / "stage4_1r12_oracle_development" / "summary.json",
        source / "stage4_1r12_oracle_development" / "results.json",
        source / "stage4_1r12_oracle_development" / "results.csv",
    ]
    required.extend(
        sorted((source / "stage4_1r12_oracle_development" / "raw").glob("*.json.gz"))
    )
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R12 source file missing: {path}")
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
    return r12._resolve_recorded_run(project_dir, recorded, root_name)


def _transition_issue_step(first_affected_state_step: int, delay_steps: int) -> int:
    return r12._transition_issue_step(first_affected_state_step, delay_steps)


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R13 controller_revision mismatch")
    req = cfg["source_requirement"]
    if req.get("required_stage") != "Stage4.1R12":
        raise ValueError("R13 source stage must remain Stage4.1R12")
    if req.get("required_controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("R13 source controller revision mismatch")
    if req.get("required_package_revision") != EXPECTED_SOURCE_PACKAGE_REVISION:
        raise ValueError("R13 source package revision mismatch")
    gate = cfg["gate"]
    if not math.isclose(float(gate["precise_tolerance_m"]), 0.03, abs_tol=1e-15):
        raise ValueError("R13 may not weaken the 30 mm position gate")
    if not math.isclose(
        float(gate["terminal_velocity_max_m_per_s"]), 0.1, abs_tol=1e-15
    ):
        raise ValueError("R13 may not weaken the 0.1 m/s speed gate")
    timing = cfg["formal_timing_contract"]
    if not bool(timing.get("immutable")):
        raise ValueError("R13 timing contract must remain immutable")
    normal = timing["normal_slew"]
    weak = timing["weak_slew"]
    if (int(normal["arrival_deadline_step"]), int(normal["horizon_steps"])) != (25, 35):
        raise ValueError("normal-slew contract must remain 250/350 ms")
    if (int(weak["arrival_deadline_step"]), int(weak["horizon_steps"])) != (27, 37):
        raise ValueError("weak-slew contract must remain 270/370 ms")
    if max(map(int, normal["allowed_arrival_steps"])) != 25:
        raise ValueError("normal-slew arrival list exceeds 250 ms")
    if max(map(int, weak["allowed_arrival_steps"])) != 27:
        raise ValueError("weak-slew arrival list exceeds 270 ms")
    if not bool(timing.get("arrival_deadline_may_not_expand")):
        raise ValueError("R13 must prohibit arrival-deadline expansion")
    closure = cfg["early_braking_closure"]
    if not math.isclose(float(closure["actual_slew_scale"]), WEAK_SLEW, abs_tol=1e-15):
        raise ValueError("R13 closure must target only 0.9x slew")
    if int(closure["horizon_steps"]) != WEAK_HORIZON:
        raise ValueError("R13 weak-slew horizon must remain 37 steps")
    if [int(x) for x in closure["actual_delay_steps"]] != [1, 2]:
        raise ValueError("R13 may modify only weak-slew delay=1/2")
    targets = list(closure["required_targets"])
    if [str(row["target_id"]) for row in targets] != ["nominal", "RZ_p10_m10"]:
        raise ValueError("R13 required target bank changed")
    candidates = list(closure["candidate_bank"])
    affected = [int(row["first_affected_state_step"]) for row in candidates]
    if affected != [20, 21, 22, 23, 24, 25, 26]:
        raise ValueError("R13 first-effect bank must remain states 20--26")
    if affected != [int(x) for x in closure["candidate_first_affected_state_steps"]]:
        raise ValueError("R13 candidate declarations disagree")
    if max(affected) > int(cfg["r12_design_audit"]["latest_globally_feasible_first_affected_state_step"]):
        raise ValueError("R13 candidate bank includes a structurally too-late first effect")
    if min(affected) < 20 or max(affected) > 26:
        raise ValueError("R13 early-braking window must remain 200--260 ms")
    if not bool(closure.get("modified_paths_may_change_before_arrival_deadline")):
        raise ValueError("R13 must explicitly allow causal pre-deadline braking")
    if not bool(closure.get("source_prefix_may_change_only_at_or_after_candidate_first_effect")):
        raise ValueError("R13 must preserve source physics until each first effect")
    if not bool(closure.get("selection_is_conditioned_only_on_trusted_delay")):
        raise ValueError("R13 selection may only branch on trusted delay")
    if not bool(closure.get("selection_uses_both_required_targets")):
        raise ValueError("R13 must select across both required targets")
    if bool(closure.get("unseen_target_holdout_claimed")):
        raise ValueError("R13 may not claim an unseen-target holdout")
    if bool(cfg["calibrated_confirmation"].get("online_handover_enabled")):
        raise ValueError("R13 calibrated path must not use online handover")
    if not bool(cfg.get("finite_test_envelope_only")):
        raise ValueError("R13 must remain finite-envelope only")
    for first in affected:
        for delay in (1, 2):
            issue = _transition_issue_step(first, delay)
            if issue + delay + 1 != first:
                raise ValueError("R13 causal transition alignment is invalid")


def _validate_source_stage41r12(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R12 source file missing: {path}")
    manifest = read_json(source / "stage4_1r12_manifest.json")
    state = read_json(source / "stage4_1r12_state.json")
    source_cfg = read_json(source / "stage4_1r12_config.resolved.json")
    verdict = read_json(source / "stage4_1r12_analysis" / "stage4_1r12_verdict.json")
    req = cfg["source_requirement"]
    if manifest.get("stage") != req["required_stage"]:
        raise ValueError("source Stage4.1R12 manifest stage mismatch")
    if manifest.get("controller_revision") != req["required_controller_revision"]:
        raise ValueError("source Stage4.1R12 controller revision mismatch")
    if manifest.get("package_revision") != req["required_package_revision"]:
        raise ValueError("source Stage4.1R12 package revision mismatch")
    if source_cfg.get("controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R12 resolved config revision mismatch")
    if bool(req.get("require_finished")) and not bool(state.get("finished")):
        raise ValueError("source Stage4.1R12 is not finished")
    if str(state.get("stop_reason", "")) != str(req.get("require_stop_reason", "")):
        raise ValueError("source Stage4.1R12 stop_reason mismatch")
    if bool(req.get("require_source_audit_passed")) and not bool(
        (state.get("source_audit_summary") or {}).get("passed")
    ):
        raise ValueError("source Stage4.1R12 source audit did not pass")
    if bool(req.get("require_oracle_development_complete")) and not bool(
        state.get("oracle_development_complete")
    ):
        raise ValueError("source Stage4.1R12 development is incomplete")
    source_dev = state.get("oracle_development_summary") or {}
    if bool(source_dev.get("passed")) != bool(req.get("require_oracle_development_passed")):
        raise ValueError("source Stage4.1R12 development pass status mismatch")
    raw_count = len(list((source / "stage4_1r12_oracle_development" / "raw").glob("*.json.gz")))
    if raw_count != int(req["require_oracle_raw_count"]):
        raise ValueError(f"source Stage4.1R12 raw count mismatch: {raw_count}")
    if bool(verdict.get("primary_pass")):
        raise ValueError("source Stage4.1R12 unexpectedly claims primary closure")
    return manifest, state, source_cfg, verdict


def load_stage41r13_config(
    config_path: Path,
    *,
    source_stage41r12_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R13Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r12_run = source_stage41r12_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r12(
        source_stage41r12_run, cfg
    )
    source_stage41r11_run = _resolve_recorded_run(
        project_dir,
        str(manifest["source_stage4_1r11_run"]),
        "stage4_1r11_runs",
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r13_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r13')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    packaged_r12_cfg = (
        project_dir
        / "configs"
        / "stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json"
    )
    if not packaged_r12_cfg.is_file():
        raise FileNotFoundError(f"packaged R12 dependency config missing: {packaged_r12_cfg}")
    r12_ctx = r12.load_stage41r12_config(
        packaged_r12_cfg,
        source_stage41r11_run=source_stage41r11_run,
        run_dir_override=run_dir,
    )
    recorded = manifest.get("source_fingerprint") or {}
    current_r11 = r12._source_inventory(source_stage41r11_run)
    if recorded.get("digest") != current_r11.get("digest"):
        raise ValueError("R13 nested Stage4.1R11 source fingerprint mismatch")
    storage = cfg["storage"]
    base34 = r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_1R13_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R13_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    base34.env_cfg = env_cfg
    return Stage41R13Context(
        cfg=cfg,
        paths=Stage41R13Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r12_run=source_stage41r12_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        source_stage41r11_run=source_stage41r11_run,
        r12_ctx=r12_ctx,
        source_fingerprint=_source_inventory(source_stage41r12_run),
    )


def _initial_state(ctx: Stage41R13Context) -> dict[str, Any]:
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


def _update_state(ctx: Stage41R13Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R13Context, *, resume: bool) -> None:
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
            raise ValueError("R13 resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R13 resume controller revision mismatch")
    elif resume:
        raise FileNotFoundError("R13 resume requested but manifest is missing")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r13_config.resolved.json", ctx.cfg)
    for name, payload in (
        ("stage4_1r12_manifest.json", ctx.source_manifest),
        ("stage4_1r12_state.json", ctx.source_state),
        ("stage4_1r12_config.resolved.json", ctx.source_cfg),
        ("stage4_1r12_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r12_run": str(ctx.source_stage41r12_run),
        "source_stage4_1r11_run": str(ctx.source_stage41r11_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": int(os.environ.get("STAGE4_1R13_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "arrival_deadline_expansion_allowed": False,
        "selection_conditioned_on_trusted_delay": True,
        "selection_targets": [row["target_id"] for row in ctx.cfg["early_braking_closure"]["required_targets"]],
        "unseen_target_holdout_claimed": False,
        "finite_test_envelope_only": True,
        "true_restart_validation_performed": False,
        "final_task": ctx.cfg["final_task"],
    }
    atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _phase_raw(source: Path, phase: str) -> list[dict[str, Any]]:
    return [read_json_gz(path) for path in sorted((source / phase / "raw").glob("*.json.gz"))]


def _source_oracle_map(ctx: Stage41R13Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    return r12._source_oracle_map(ctx.r12_ctx)


def _source_calibrated_map(ctx: Stage41R13Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    return r12._source_calibrated_map(ctx.r12_ctx)


def _timing_policy(ctx: Stage41R13Context, slew: float, *, policy_id: str) -> dict[str, Any]:
    timing = ctx.cfg["formal_timing_contract"]
    block = timing["weak_slew"] if math.isclose(float(slew), WEAK_SLEW, abs_tol=1e-12) else timing["normal_slew"]
    return {
        "policy_id": policy_id,
        "horizon_steps": int(block["horizon_steps"]),
        "allowed_arrival_steps": [int(x) for x in block["allowed_arrival_steps"]],
    }


def _slice_result(result: Mapping[str, Any], horizon: int) -> dict[str, Any]:
    return r12._slice_result(result, horizon)


def _limiting_component(endpoint_row: Mapping[str, Any]) -> tuple[str, float]:
    keys = {
        "position": "position_signed_margin",
        "endpoint_speed": "endpoint_speed_signed_margin",
        "endpoint_late_speed": "endpoint_late_speed_signed_margin",
        "post_speed": "post_speed_signed_margin",
        "final_speed": "final_speed_signed_margin",
        "ip_safety": "ip_signed_margin",
        "ip_terminal": "stage3_4_ip_terminal_signed_margin",
        "ip_hold_rms": "stage3_4_ip_hold_rms_signed_margin",
        "ip_sustained": "stage3_4_ip_sustained_signed_margin",
    }
    values = {name: _as_float(endpoint_row.get(key), math.inf) for name, key in keys.items()}
    name = min(values, key=values.get)
    return name, values[name]


def _source_failure_rows(ctx: Stage41R13Context) -> list[dict[str, Any]]:
    source = _source_oracle_map(ctx)
    rows: list[dict[str, Any]] = []
    endpoint = 27
    late_steps = [24, 25, 26, 27]
    for target in ("nominal", "RZ_p10_m10"):
        for delay in (1, 2):
            result = _slice_result(source[(target, delay, WEAK_SLEW)], WEAK_HORIZON)
            policy = _timing_policy(ctx, WEAK_SLEW, policy_id=f"source_{target}_d{delay}")
            metrics = r8.tracking_metrics(
                ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
                result,
                policy,
            )
            evals = {int(row["endpoint_step"]): row for row in metrics["stage3_4_endpoint_evaluations"]}
            chosen = evals[int(metrics["stage3_4_best_endpoint_step"])]
            limiting, limiting_margin = _limiting_component(chosen)
            y = np.asarray([[row["R"], row["Z"]] for row in result["trajectory"]], dtype=float)
            speed = np.zeros(len(y), dtype=float)
            speed[1:] = np.linalg.norm(np.diff(y, axis=0) / 0.01, axis=1)
            lower_bound_state27 = float(np.sqrt(np.sum(speed[24:27] ** 2) / 4.0))
            latest_feasible = None
            for first in range(20, 28):
                immutable = [step for step in late_steps if step < first]
                lower = float(np.sqrt(np.sum(speed[immutable] ** 2) / 4.0)) if immutable else 0.0
                if lower <= 0.1 + 1e-15:
                    latest_feasible = first
            rows.append(
                {
                    "target_id": target,
                    "actual_delay_steps": delay,
                    "actual_slew_scale": WEAK_SLEW,
                    "formal_tracking_pass": bool(metrics["stage3_4_target_tracking_pass"]),
                    "best_endpoint_step": int(metrics["stage3_4_best_endpoint_step"]),
                    "minimum_signed_margin": float(metrics["stage3_4_tracking_minimum_signed_margin"]),
                    "limiting_component": limiting,
                    "limiting_component_margin": limiting_margin,
                    "endpoint_late_speed_rms_m_per_s": float(chosen["endpoint_late_velocity_rms_m_per_s"]),
                    "final_speed_m_per_s": float(chosen["final_velocity_m_per_s"]),
                    "state27_only_lower_bound_late_rms_m_per_s": lower_bound_state27,
                    "first_effect_state27_can_never_pass_late_rms": lower_bound_state27 > 0.1 + 1e-15,
                    "latest_theoretically_feasible_first_effect_state": latest_feasible,
                    "speed_state24_m_per_s": float(speed[24]),
                    "speed_state25_m_per_s": float(speed[25]),
                    "speed_state26_m_per_s": float(speed[26]),
                    "speed_state27_m_per_s": float(speed[27]),
                }
            )
    return rows


def run_source_audit(ctx: Stage41R13Context) -> dict[str, Any]:
    raw = _phase_raw(ctx.source_stage41r12_run, "stage4_1r12_oracle_development")
    rows = [r12.result_row(ctx.r12_ctx, result) for result in raw]
    r12_rows: list[dict[str, Any]] = []
    for row, result in zip(rows, raw, strict=True):
        policy = _timing_policy(
            ctx,
            WEAK_SLEW,
            policy_id=f"r12_{row['policy_id']}_d{int(row['actual_delay_steps'])}",
        )
        metrics = r8.tracking_metrics(
            ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
            result,
            policy,
        )
        evals = {
            int(item["endpoint_step"]): item
            for item in metrics["stage3_4_endpoint_evaluations"]
        }
        chosen = evals[int(metrics["stage3_4_best_endpoint_step"])]
        limiting_component, limiting_margin = _limiting_component(chosen)
        r12_rows.append(
            {
                "experiment_id": row["experiment_id"],
                "policy_id": row["policy_id"],
                "actual_delay_steps": int(row["actual_delay_steps"]),
                "environment_success": bool(row["environment_success"]),
                "formal_contract_tracking_pass": bool(row["formal_contract_tracking_pass"]),
                "formal_contract_minimum_signed_margin": row["formal_contract_minimum_signed_margin"],
                "best_endpoint_step": row["best_endpoint_step"],
                "terminal_speed_m_per_s": row["terminal_speed_m_per_s"],
                "limiting_component_after_r12": limiting_component,
                "limiting_component_margin_after_r12": limiting_margin,
                "endpoint_late_speed_rms_after_r12_m_per_s": chosen.get(
                    "endpoint_late_velocity_rms_m_per_s"
                ),
                "final_speed_after_r12_m_per_s": chosen.get("final_velocity_m_per_s"),
                "physics_prefix_exact": bool(row["physics_prefix_exact"]),
                "issued_prefix_exact": bool(row["issued_prefix_exact"]),
                "applied_prefix_exact": bool(row["applied_prefix_exact"]),
                "no_future_measurement": bool(row["no_future_measurement"]),
                "streaming_queue_consistent": bool(row["streaming_queue_consistent"]),
            }
        )
    source_failure = _source_failure_rows(ctx)
    delay1 = [row for row in r12_rows if row["actual_delay_steps"] == 1]
    delay2 = [row for row in r12_rows if row["actual_delay_steps"] == 2]
    rz_rows = [row for row in source_failure if row["target_id"] == "RZ_p10_m10"]
    nominal_d1_source = next(
        row
        for row in source_failure
        if row["target_id"] == "nominal" and row["actual_delay_steps"] == 1
    )
    req = ctx.cfg["source_requirement"]
    audit_cfg = ctx.cfg["r12_design_audit"]
    passed = bool(
        len(r12_rows) == int(req["require_oracle_raw_count"])
        and len({row["experiment_id"] for row in r12_rows}) == len(r12_rows)
        and sum(bool(row["environment_success"]) for row in r12_rows)
        == int(req["expected_r12_environment_success_count"])
        and sum(bool(row["formal_contract_tracking_pass"]) for row in delay1)
        == int(req["expected_r12_delay1_formal_pass_count"])
        and sum(bool(row["formal_contract_tracking_pass"]) for row in delay2)
        == int(req["expected_r12_delay2_formal_pass_count"])
        and sorted({int((result.get("spec") or {})["anticipatory_first_affected_state_step"]) for result in raw})
        == [int(x) for x in req["expected_r12_candidate_first_effect_steps"]]
        and all(bool(row["physics_prefix_exact"]) for row in r12_rows)
        and all(bool(row["issued_prefix_exact"]) for row in r12_rows)
        and all(bool(row["applied_prefix_exact"]) for row in r12_rows)
        and all(bool(row["no_future_measurement"]) for row in r12_rows)
        and all(bool(row["streaming_queue_consistent"]) for row in r12_rows)
        and all(
            row["limiting_component_after_r12"]
            == audit_cfg["expected_nominal_delay1_limiting_component_after_r12"]
            for row in delay1
        )
        and float(nominal_d1_source["endpoint_late_speed_rms_m_per_s"])
        > float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"])
        and all(bool(row["first_effect_state27_can_never_pass_late_rms"]) for row in rz_rows)
        and min(int(row["latest_theoretically_feasible_first_effect_state"]) for row in rz_rows)
        == int(audit_cfg["latest_globally_feasible_first_affected_state_step"])
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r12_run": str(ctx.source_stage41r12_run),
        "source_stage4_1r11_run": str(ctx.source_stage41r11_run),
        "r12_raw_rollouts": len(r12_rows),
        "r12_environment_success_count": sum(bool(row["environment_success"]) for row in r12_rows),
        "r12_delay1_formal_pass_count": sum(bool(row["formal_contract_tracking_pass"]) for row in delay1),
        "r12_delay2_formal_pass_count": sum(bool(row["formal_contract_tracking_pass"]) for row in delay2),
        "r12_post_deadline_controller_fixed_nominal_delay2": len(delay2) == 6 and all(bool(row["formal_contract_tracking_pass"]) for row in delay2),
        "r12_delay1_residual_is_preexisting_arrival_window_violation": bool(
            delay1
            and all(
                row["limiting_component_after_r12"] == "endpoint_late_speed"
                for row in delay1
            )
            and float(nominal_d1_source["endpoint_late_speed_rms_m_per_s"])
            > float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"])
        ),
        "r12_post_deadline_bank_was_structurally_incapable_of_closing_all_four": all(bool(row["first_effect_state27_can_never_pass_late_rms"]) for row in rz_rows),
        "latest_globally_feasible_first_affected_state_step": min(int(row["latest_theoretically_feasible_first_effect_state"]) for row in rz_rows),
        "formal_timing_contract_unchanged": True,
        "r11_2000ms_remains_auxiliary_only": True,
        "stage4_2r1_was_not_run_or_reused": True,
        "passed": passed,
        "interpretation": (
            "R12 ran correctly and proved useful post-arrival damping: all six nominal delay=2 candidates pass. "
            "It cannot close the bank because the nominal delay=1 endpoint-late-speed violation already exists at 270 ms, "
            "and both RZ_p10_m10 source paths have an immutable state-27 lower bound above 0.1 m/s. "
            "R13 must change the causal pre-deadline braking trajectory while retaining the same 270/370 ms gate."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    write_csv(ctx.paths.source_audit / "r12_rollout_audit.csv", r12_rows)
    write_csv(ctx.paths.source_audit / "source_failure_feasibility.csv", source_failure)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


class LocalStage41R13Worker:
    """Thin scientific wrapper around the validated R12 streaming worker.

    R13 changes only the causal issue/first-effect schedule supplied in the spec.
    The underlying solver, actuator scheduler, queue semantics and TSC runner are
    identical to R12.  This makes the R13 comparison attributable to moving the
    physical braking onset into the formal arrival window.
    """

    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.inner = r12.LocalStage41R12Worker(
            payload, library, bundle, worker_id, selector_cfg
        )

    def close(self) -> None:
        self.inner.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.inner.evaluate(spec)
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r13_controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r13_uses_r12_validated_streaming_worker"] = True
        return _json_safe(result)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage41R13Actor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalStage41R13Worker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R13Actor
    return _RAY_ACTOR


def materialize_variant(ctx: Stage41R13Context) -> tuple[str, dict[str, Any]]:
    variant, payload = r10.materialize_variant(
        ctx.r12_ctx.r11_ctx.r10_ctx,
        slew_scale=WEAK_SLEW,
        horizon_steps=WEAK_HORIZON,
    )
    atomic_write_json(ctx.paths.variants / f"{variant}.payload.json", payload)
    return variant, payload


def evaluate_specs(
    ctx: Stage41R13Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variant, payload = materialize_variant(ctx)
    chain = ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx
    chain.variants[variant] = payload
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(output_dir / f"{spec['experiment_id']}.json.gz"))
    ]
    library = chain.r3_ctx.source_library
    bundle = chain.r3_ctx.source_bundle
    selector_cfg = ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg["batch_selector"]
    if backend == "serial":
        worker = LocalStage41R13Worker(payload, library, bundle, "stage41r13_serial", selector_cfg)
        try:
            for index, spec in enumerate(pending, 1):
                atomic_write_json_gz(
                    output_dir / f"{spec['experiment_id']}.json.gz",
                    worker.evaluate(spec),
                )
                print(f"[Stage4.1R13 {variant}] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        requested = int(os.environ.get("STAGE4_1R13_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R13 early-braking]",
        )
        Actor = _ray_actor_class()
        actors = [
            Actor.remote(payload, library, bundle, f"stage41r13_{index:03d}", selector_cfg)
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
                    print(f"[Stage4.1R13 early-braking] waiting {done}/{len(pending)}", flush=True)
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
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(f"[Stage4.1R13 early-braking] {done}/{len(pending)}", flush=True)
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


def _source_scale(ctx: Stage41R13Context) -> float:
    return float(
        ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
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
    ctx: Stage41R13Context,
) -> dict[str, Any]:
    closure = ctx.cfg["early_braking_closure"]
    first_affected = int(policy["first_affected_state_step"])
    issue_start = _transition_issue_step(first_affected, modeled_delay)
    generic_policy = {
        "horizon_steps": WEAK_HORIZON,
        "tail_steps": 0,
        "tail_policy": "r13_streaming_delay_pipeline_early_braking",
        "policy_id": str(policy["policy_id"]),
    }
    extra = r8._main_extra(
        ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
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
            "tail_policy": "r13_streaming_delay_pipeline_early_braking",
            "anticipatory_policy_id": str(policy["policy_id"]),
            "anticipatory_first_affected_state_step": first_affected,
            "anticipatory_transition_issue_step": issue_start,
            "terminal_model_phase_cap_step": int(closure["terminal_model_phase_cap_step"]),
            "terminal_controller_scale": float(closure["terminal_controller_scale"]),
            "terminal_velocity_measurement_gain": float(closure["terminal_velocity_measurement_gain"]),
            "terminal_position_measurement_gain": float(closure["terminal_position_measurement_gain"]),
            "terminal_ip_measurement_gain": float(closure["terminal_ip_measurement_gain"]),
            "terminal_controller_model_scale": float(closure["terminal_controller_model_scale"]),
            "terminal_integral_mode": str(closure["terminal_integral_mode"]),
            "terminal_nominal_physical_mode": str(closure["terminal_nominal_physical_mode"]),
            "terminal_initial_previous_correction": str(closure["terminal_initial_previous_correction"]),
            "formal_arrival_deadline_step": 27,
            "formal_hold_through_step": 37,
            "arrival_deadline_expansion_allowed": False,
            "normal_slew_controller_changed": False,
            "r13_selection_conditioned_on_trusted_delay": True,
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
        "kind": "stage4_1r13_original_deadline_delay_pipeline_early_braking",
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


def build_development_specs(ctx: Stage41R13Context) -> list[dict[str, Any]]:
    closure = ctx.cfg["early_braking_closure"]
    variant, _ = materialize_variant(ctx)
    specs: list[dict[str, Any]] = []
    for policy in closure["candidate_bank"]:
        for delay in closure["actual_delay_steps"]:
            for target in closure["required_targets"]:
                specs.append(
                    _make_spec(
                        phase="oracle_development",
                        policy=policy,
                        target=target,
                        actual_delay=int(delay),
                        modeled_delay=int(delay),
                        calibration_token=None,
                        trusted=True,
                        controller_variant="r13_oracle_development",
                        environment_variant=variant,
                        ctx=ctx,
                    )
                )
    return specs


def _selected_policy_by_delay(ctx: Stage41R13Context) -> dict[int, dict[str, Any]]:
    if not ctx.paths.state.is_file():
        return {}
    selected = (read_json(ctx.paths.state).get("oracle_development_summary") or {}).get("selected_policy_by_delay") or {}
    bank = {str(row["policy_id"]): copy.deepcopy(row) for row in ctx.cfg["early_braking_closure"]["candidate_bank"]}
    output: dict[int, dict[str, Any]] = {}
    for delay_text, policy_id in selected.items():
        if str(policy_id) not in bank:
            raise ValueError(f"selected R13 policy is not in candidate bank: {policy_id}")
        output[int(delay_text)] = bank[str(policy_id)]
    return output


def _trusted_tokens(ctx: Stage41R13Context) -> dict[tuple[int, float], dict[str, Any]]:
    return r12._trusted_tokens(ctx.r12_ctx)


def build_calibrated_specs(ctx: Stage41R13Context) -> list[dict[str, Any]]:
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
                    controller_variant="r13_calibrated_confirmation",
                    environment_variant=variant,
                    ctx=ctx,
                )
            )
    return specs


def _physics_array(result: Mapping[str, Any], *, count: int | None = None) -> np.ndarray:
    return r12._physics_array(result, count=count)


def _control_array(result: Mapping[str, Any], field: str, *, count: int | None = None) -> np.ndarray:
    return r12._control_array(result, field, count=count)


def _damping_array(result: Mapping[str, Any], field: str) -> np.ndarray:
    return r12._damping_array(result, field)


def _prefix_audit(source: Mapping[str, Any], result: Mapping[str, Any], *, atol: float) -> dict[str, Any]:
    return r12._prefix_audit(source, result, atol=atol)


def result_row(ctx: Stage41R13Context, result: Mapping[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    policy = {
        "policy_id": str(spec["anticipatory_policy_id"]),
        "horizon_steps": WEAK_HORIZON,
        "allowed_arrival_steps": [int(x) for x in ctx.cfg["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"]],
    }
    metrics = r8.tracking_metrics(ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx, result, policy)
    source = _source_oracle_map(ctx)[
        (str(spec["target_id"]), int(spec["action_delay_steps"]), WEAK_SLEW)
    ]
    prefix = _prefix_audit(
        source,
        result,
        atol=float(ctx.cfg["early_braking_closure"]["prefix_numeric_atol"]),
    )
    chosen_eval = next(
        row
        for row in metrics.get("stage3_4_endpoint_evaluations", [])
        if int(row["endpoint_step"]) == int(metrics["stage3_4_best_endpoint_step"])
    )
    limiting, limiting_margin = _limiting_component(chosen_eval)
    closure = ctx.cfg["early_braking_closure"]
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
    trajectory = list(result.get("trajectory") or [])
    action_rows = np.asarray([row.get("action_norm_tsc", [0.0] * 14) for row in trajectory[1:]], dtype=float)
    action_rms = float(np.sqrt(np.mean(action_rows**2))) if action_rows.size else 0.0
    delta_action_rms = float(np.sqrt(np.mean(np.diff(action_rows, axis=0) ** 2))) if action_rows.ndim == 2 and action_rows.shape[0] > 1 else 0.0
    damping = result.get("anticipatory_damping_summary") or {}
    return {
        "experiment_id": result.get("experiment_id"),
        "phase": spec.get("phase"),
        "policy_id": spec.get("anticipatory_policy_id"),
        "target_id": spec.get("target_id"),
        "actual_delay_steps": int(spec.get("action_delay_steps")),
        "actual_slew_scale": float(spec.get("slew_scale")),
        "calibration_token": spec.get("calibration_token"),
        "environment_success": bool(result.get("success")),
        "failure_reason": result.get("failure_reason", ""),
        "formal_arrival_deadline_step": 27,
        "formal_hold_through_step": 37,
        "formal_contract_tracking_pass": bool(metrics.get("stage3_4_target_tracking_pass")),
        "formal_contract_minimum_signed_margin": metrics.get("stage3_4_tracking_minimum_signed_margin"),
        "best_endpoint_step": metrics.get("stage3_4_best_endpoint_step"),
        "limiting_component": limiting,
        "limiting_component_margin": limiting_margin,
        "endpoint_late_speed_rms_m_per_s": chosen_eval.get("endpoint_late_velocity_rms_m_per_s"),
        "terminal_speed_m_per_s": metrics.get("terminal_velocity_m_per_s"),
        "post_arrival_speed_rms_m_per_s": metrics.get("stage3_4_post_arrival_velocity_rms_m_per_s"),
        "sustained_box_error_m": metrics.get("stage3_4_sustained_box_max_error_m"),
        "max_current_utilization": metrics.get("max_current_utilization"),
        "action_rms": action_rms,
        "delta_action_rms": delta_action_rms,
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
        "first_effect_alignment_exact": prefix["first_effect_alignment_exact"],
        "early_braking_activated": prefix["anticipatory_damping_activated"],
        "r13_composite_pass": composite,
        "physics_signature": _array_digest(_physics_array(result), "physics"),
        "issued_signature": _array_digest(_control_array(result, "issued_mode_coefficients"), "issued"),
        "applied_signature": _array_digest(_control_array(result, "applied_command_mode_coefficients"), "applied"),
        "braking_issued_signature": _array_digest(_damping_array(result, "issued_mode_coefficients"), "brakingissued"),
        "braking_applied_signature": _array_digest(_damping_array(result, "applied_command_mode_coefficients"), "brakingapplied"),
    }


def _candidate_summary(
    ctx: Stage41R13Context,
    rows: Sequence[Mapping[str, Any]],
    *,
    policy_id: str,
    delay: int,
) -> dict[str, Any]:
    subset = [
        row
        for row in rows
        if str(row.get("policy_id")) == str(policy_id)
        and int(row.get("actual_delay_steps")) == int(delay)
    ]
    required_targets = {str(row["target_id"]) for row in ctx.cfg["early_braking_closure"]["required_targets"]}
    coverage = bool(
        len(subset) == len(required_targets)
        and {str(row["target_id"]) for row in subset} == required_targets
    )
    pass_fraction = sum(bool(row.get("r13_composite_pass")) for row in subset) / len(subset) if subset else 0.0
    minimum_margin = min((_as_float(row.get("formal_contract_minimum_signed_margin"), -1e12) for row in subset), default=-1e12)
    mean_margin = float(np.mean([_as_float(row.get("formal_contract_minimum_signed_margin"), -1e12) for row in subset])) if subset else -1e12
    max_terminal_speed = max((_as_float(row.get("terminal_speed_m_per_s"), math.inf) for row in subset), default=math.inf)
    mean_action_rms = float(np.mean([_as_float(row.get("action_rms"), math.inf) for row in subset])) if subset else math.inf
    first_steps = {int(row["first_affected_state_step"]) for row in subset if row.get("first_affected_state_step") is not None}
    first_effect = next(iter(first_steps)) if len(first_steps) == 1 else None
    passed = bool(
        coverage
        and pass_fraction >= float(ctx.cfg["early_braking_closure"]["minimum_target_pass_fraction_per_delay"])
        and minimum_margin >= float(ctx.cfg["early_braking_closure"]["minimum_tracking_signed_margin"]) - 1e-12
    )
    return {
        "policy_id": policy_id,
        "actual_delay_steps": int(delay),
        "first_affected_state_step": first_effect,
        "n_rollouts": len(subset),
        "expected_rollouts": len(required_targets),
        "target_coverage_complete": coverage,
        "target_pass_fraction": pass_fraction,
        "minimum_formal_signed_margin": minimum_margin,
        "mean_formal_signed_margin": mean_margin,
        "maximum_terminal_speed_m_per_s": max_terminal_speed,
        "mean_action_rms": mean_action_rms,
        "all_prefix_guards_pass": bool(subset and all(
            bool(row.get("physics_prefix_exact"))
            and bool(row.get("issued_prefix_exact"))
            and bool(row.get("applied_prefix_exact"))
            for row in subset
        )),
        "all_no_future_measurement": bool(subset and all(bool(row.get("no_future_measurement")) for row in subset)),
        "all_streaming_queues_consistent": bool(subset and all(bool(row.get("streaming_queue_consistent")) for row in subset)),
        "passed": passed,
    }


def run_development(ctx: Stage41R13Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_development_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.oracle_development / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [result_row(ctx, result) for result in results]
    candidate_ids = [str(row["policy_id"]) for row in ctx.cfg["early_braking_closure"]["candidate_bank"]]
    summaries = [
        _candidate_summary(ctx, rows, policy_id=policy_id, delay=delay)
        for delay in (1, 2)
        for policy_id in candidate_ids
    ]
    selected_by_delay: dict[str, str] = {}
    selected_summaries: list[dict[str, Any]] = []
    for delay in (1, 2):
        passing = [row for row in summaries if int(row["actual_delay_steps"]) == delay and bool(row["passed"])]
        if not passing:
            continue
        selected = max(
            passing,
            key=lambda row: (
                float(row["minimum_formal_signed_margin"]),
                float(row["mean_formal_signed_margin"]),
                int(row.get("first_affected_state_step") or -1),
                -float(row["maximum_terminal_speed_m_per_s"]),
                -float(row["mean_action_rms"]),
            ),
        )
        selected_by_delay[str(delay)] = str(selected["policy_id"])
        selected_summaries.append(selected)
    passed = bool(
        len(rows) == 28
        and len({row["experiment_id"] for row in rows}) == 28
        and set(selected_by_delay) == {"1", "2"}
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "oracle_development",
        "required_targets": [row["target_id"] for row in ctx.cfg["early_braking_closure"]["required_targets"]],
        "candidate_selection_uses_both_required_targets": True,
        "unseen_target_holdout_claimed": False,
        "selection_conditioned_only_on_trusted_delay": True,
        "formal_arrival_deadline_step": 27,
        "formal_hold_through_step": 37,
        "arrival_deadline_expanded": False,
        "candidate_first_effect_steps": [int(row["first_affected_state_step"]) for row in ctx.cfg["early_braking_closure"]["candidate_bank"]],
        "candidate_window_ms": [200, 260],
        "n_rollouts": len(rows),
        "expected_rollouts": 28,
        "coverage_complete": len(rows) == 28 and len({row["experiment_id"] for row in rows}) == 28,
        "candidate_summaries": summaries,
        "selected_policy_by_delay": selected_by_delay,
        "selected_summaries": selected_summaries,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.oracle_development / "results.json", rows)
    write_csv(ctx.paths.oracle_development / "results.csv", rows)
    atomic_write_json(ctx.paths.oracle_development / "summary.json", summary)
    _update_state(ctx, oracle_development_complete=True, oracle_development_summary=summary)
    return summary


def _selected_oracle_raw(ctx: Stage41R13Context) -> dict[tuple[str, int], dict[str, Any]]:
    selected = _selected_policy_by_delay(ctx)
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((ctx.paths.oracle_development / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result.get("spec") or {}
        delay = int(spec.get("action_delay_steps", -1))
        policy = selected.get(delay)
        if policy is None or str(spec.get("anticipatory_policy_id")) != str(policy["policy_id"]):
            continue
        key = (str(spec["target_id"]), delay)
        if key in output:
            raise ValueError(f"duplicate selected R13 Oracle case: {key}")
        output[key] = result
    return output


def _comparison_components(result: Mapping[str, Any]) -> dict[str, np.ndarray]:
    return {
        "physics": _physics_array(result),
        "issued": _control_array(result, "issued_mode_coefficients"),
        "applied": _control_array(result, "applied_command_mode_coefficients"),
        "braking_issued": _damping_array(result, "issued_mode_coefficients"),
        "braking_applied": _damping_array(result, "applied_command_mode_coefficients"),
    }


def run_calibrated_confirmation(ctx: Stage41R13Context, *, backend: str, resume: bool) -> dict[str, Any]:
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
    oracle = _selected_oracle_raw(ctx)
    atol = float(ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"])
    comparisons: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key not in oracle:
            raise ValueError(f"missing selected R13 Oracle comparison for {key}")
        left = _comparison_components(result)
        right = _comparison_components(oracle[key])
        component_diff = {name: _finite_max_abs(left[name], right[name]) for name in left}
        exact = all(np.array_equal(left[name], right[name]) for name in left)
        numeric = all(np.allclose(left[name], right[name], rtol=0.0, atol=atol) for name in left)
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
    pass_fraction = sum(bool(row.get("r13_composite_pass")) for row in rows) / len(rows)
    exact_fraction = sum(bool(row["exact_trace_equal_to_oracle"]) for row in comparisons) / len(comparisons)
    numeric_fraction = sum(bool(row["numeric_trace_equal_to_oracle"]) for row in comparisons) / len(comparisons)
    tokens = {str(row.get("calibration_token")) for row in rows if row.get("calibration_token")}
    untrusted = sum(not bool((result.get("spec") or {}).get("trusted_calibration_model")) for result in results)
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
        "maximum_trace_abs_difference": max((float(row["maximum_trace_abs_difference"]) for row in comparisons), default=math.inf),
        "comparisons": comparisons,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.calibrated_confirmation / "results.json", rows)
    write_csv(ctx.paths.calibrated_confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.calibrated_confirmation / "summary.json", summary)
    _update_state(ctx, calibrated_confirmation_complete=True, calibrated_confirmation_summary=summary)
    return summary


def _r13_calibrated_map(ctx: Stage41R13Context) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((ctx.paths.calibrated_confirmation / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result.get("spec") or {}
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key in output:
            raise ValueError(f"duplicate R13 calibrated case: {key}")
        output[key] = result
    return output


def _formal_equivalence_components(result: Mapping[str, Any], *, horizon: int) -> dict[str, np.ndarray]:
    return {
        "physics": _physics_array(result, count=horizon + 1),
        "issued": _control_array(result, "issued_mode_coefficients", count=horizon),
        "applied": _control_array(result, "applied_command_mode_coefficients", count=horizon),
    }


def run_formal_grid_confirmation(ctx: Stage41R13Context) -> dict[str, Any]:
    source_oracle = _source_oracle_map(ctx)
    source_calibrated = _source_calibrated_map(ctx)
    selected_oracle = _selected_oracle_raw(ctx)
    selected_calibrated = _r13_calibrated_map(ctx)
    affected_keys = {
        (target, delay, WEAK_SLEW)
        for target in ("nominal", "RZ_p10_m10")
        for delay in (1, 2)
    }
    rows: list[dict[str, Any]] = []
    atol = float(ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"])
    for key in sorted(source_oracle):
        target, delay, slew = key
        affected = key in affected_keys
        if affected:
            pair_key = (target, delay)
            if pair_key not in selected_oracle or pair_key not in selected_calibrated:
                raise ValueError(f"missing R13 affected formal-grid case: {pair_key}")
            oracle_result = selected_oracle[pair_key]
            calibrated_result = selected_calibrated[pair_key]
            path = "r13_delay_conditioned_early_braking"
            path_guard = bool(result_row(ctx, oracle_result)["r13_composite_pass"])
        else:
            oracle_result = source_oracle[key]
            calibrated_result = source_calibrated[key]
            path = "source_unchanged_r11_original_deadline"
            path_guard = True
        policy = _timing_policy(ctx, slew, policy_id=f"formal_{target}_d{delay}_s{slew:.1f}")
        horizon = int(policy["horizon_steps"])
        oracle_slice = _slice_result(oracle_result, horizon)
        calibrated_slice = _slice_result(calibrated_result, horizon)
        metrics = r8.tracking_metrics(ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx, oracle_slice, policy)
        left = _formal_equivalence_components(calibrated_slice, horizon=horizon)
        right = _formal_equivalence_components(oracle_slice, horizon=horizon)
        component_diff = {name: _finite_max_abs(left[name], right[name]) for name in left}
        exact = all(np.array_equal(left[name], right[name]) for name in left)
        numeric = all(np.allclose(left[name], right[name], rtol=0.0, atol=atol) for name in left)
        passed = bool(metrics.get("stage3_4_target_tracking_pass") and path_guard and exact and numeric)
        rows.append(
            {
                "target_id": target,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "controller_path": path,
                "formal_horizon_steps": horizon,
                "formal_arrival_deadline_step": max(policy["allowed_arrival_steps"]),
                "oracle_formal_tracking_pass": bool(metrics.get("stage3_4_target_tracking_pass")),
                "oracle_minimum_signed_margin": metrics.get("stage3_4_tracking_minimum_signed_margin"),
                "calibrated_exact_equal_to_oracle": exact,
                "calibrated_numeric_equal_to_oracle": numeric,
                "maximum_trace_abs_difference": max(component_diff.values()),
                "component_max_abs_difference": component_diff,
                "path_guard_pass": path_guard,
                "formal_grid_case_pass": passed,
            }
        )
    affected_rows = [row for row in rows if row["controller_path"] == "r13_delay_conditioned_early_braking"]
    unchanged_rows = [row for row in rows if row["controller_path"] != "r13_delay_conditioned_early_braking"]
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
        "affected_r13_cases": len(affected_rows),
        "source_unchanged_cases": len(unchanged_rows),
        "formal_contract_pass_fraction": sum(bool(row["formal_grid_case_pass"]) for row in rows) / len(rows) if rows else 0.0,
        "calibrated_exact_trace_equivalence_fraction": sum(bool(row["calibrated_exact_equal_to_oracle"]) for row in rows) / len(rows) if rows else 0.0,
        "maximum_trace_abs_difference": max((float(row["maximum_trace_abs_difference"]) for row in rows), default=math.inf),
        "normal_slew_and_weak_delay0_reused_without_new_tsc": True,
        "arrival_deadline_expanded": False,
        "unseen_target_generalization_validated": False,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.formal_grid_confirmation / "results.json", rows)
    write_csv(ctx.paths.formal_grid_confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.formal_grid_confirmation / "summary.json", summary)
    _update_state(ctx, formal_grid_confirmation_complete=True, formal_grid_confirmation_summary=summary)
    return summary


def run_restart_audit(ctx: Stage41R13Context) -> dict[str, Any]:
    simulation_root = Path(
        ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg["simulation_root"]
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
        "true_restart_validation_available": len(available) >= int(ctx.cfg["restart_audit"]["minimum_distinct_folders"]),
        "true_restart_validation_performed": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "availability_requirement_for_stage4_1r13": False,
        "audit_completed": True,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart_audit / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


def finalize(ctx: Stage41R13Context) -> dict[str, Any]:
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
        "STAGE4_1R13_ORIGINAL_250_270MS_DEADLINE_STATIC_GRID_CLOSURE"
        if primary_pass
        else "STAGE4_1R13_ORIGINAL_DEADLINE_EARLY_BRAKING_INCOMPLETE"
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
        "source_r11_long_hold_retained_as_diagnostic_only": True,
        "r12_post_deadline_design_infeasibility_audited": bool(source.get("passed")),
        "stage4_2r1_was_not_run_or_reused": True,
        "selected_policy_by_delay": development.get("selected_policy_by_delay", {}),
        "selection_conditioned_only_on_trusted_delay": True,
        "selection_used_both_required_targets": True,
        "unseen_target_generalization_validated": False,
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
            "Freeze the original-deadline static-grid controller and proceed to true restart and hidden vessel/eddy-history validation. "
            "Do not reinterpret R10/R11 late-arrival trajectories as the timing contract and do not start BC/DAgger/RL yet."
        ),
        "next_if_fail": (
            "Do not enlarge the 250/270 ms deadlines. Use the complete causal 200--260 ms failed raw bank to identify a bounded early-braking local model "
            "and redesign an integrated delay-pipeline-aware main MPC; do not add another late tail and do not hand 14-coil control to RL."
        ),
        "final_task": ctx.cfg["final_task"],
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "source_stage4_1r12_run": str(ctx.source_stage41r12_run),
        "source_stage4_1r11_run": str(ctx.source_stage41r11_run),
        "phases": {
            "source_audit": source,
            "oracle_development": development,
            "calibrated_confirmation": calibrated,
            "formal_grid_confirmation": formal_grid,
            "restart_audit": restart,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r13_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_1r13_summary.json", summary)
    _update_state(
        ctx,
        finished=True,
        stop_reason="" if primary_pass else "formal_original_deadline_early_braking_failed",
    )
    return summary


def execute(
    ctx: Stage41R13Context,
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
    if command in {"all", "development"} and not bool(state.get("oracle_development_complete")):
        development = run_development(ctx, backend=backend, resume=resume)
        if not development.get("passed"):
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "confirmation"} and not bool(state.get("calibrated_confirmation_complete")):
        calibrated = run_calibrated_confirmation(ctx, backend=backend, resume=resume)
        if not calibrated.get("passed"):
            _update_state(ctx, calibrated_confirmation_complete=True, calibrated_confirmation_summary=calibrated)
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if command in {"all", "grid"} and not bool(state.get("formal_grid_confirmation_complete")):
        formal_grid = run_formal_grid_confirmation(ctx)
        if not formal_grid.get("passed"):
            run_restart_audit(ctx)
            return finalize(ctx)
    state = read_json(ctx.paths.state)
    if not bool(state.get("restart_audit_complete")):
        run_restart_audit(ctx)
    return finalize(ctx)


def self_test(project_dir: Path) -> dict[str, Any]:
    cfg_path = project_dir / "configs" / "stage4_1r13_original_deadline_delay_pipeline_early_braking_370ms.json"
    cfg = read_json(cfg_path)
    validate_config(cfg)
    candidate_steps = [int(row["first_affected_state_step"]) for row in cfg["early_braking_closure"]["candidate_bank"]]
    transitions = {
        (first, delay): _transition_issue_step(first, delay)
        for first in candidate_steps
        for delay in (1, 2)
    }
    alignment = all(issue + delay + 1 == first for (first, delay), issue in transitions.items())
    no_deadline_expansion = bool(
        max(cfg["formal_timing_contract"]["normal_slew"]["allowed_arrival_steps"]) == 25
        and max(cfg["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"]) == 27
        and cfg["early_braking_closure"]["horizon_steps"] == 37
    )
    early_window = candidate_steps == [20, 21, 22, 23, 24, 25, 26]
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_valid": True,
        "transition_alignment_valid": alignment,
        "no_arrival_deadline_expansion": no_deadline_expansion,
        "causal_early_braking_window_valid": early_window,
        "candidate_first_affected_state_steps": candidate_steps,
        "candidate_count": len(candidate_steps),
        "development_rollout_count": 28,
        "calibrated_rollout_count_if_development_passes": 4,
        "maximum_true_tsc_rollouts": 32,
        "selection_conditioned_on_trusted_delay": bool(cfg["early_braking_closure"]["selection_is_conditioned_only_on_trusted_delay"]),
        "selection_uses_both_required_targets": bool(cfg["early_braking_closure"]["selection_uses_both_required_targets"]),
        "unseen_target_holdout_claimed": bool(cfg["early_braking_closure"]["unseen_target_holdout_claimed"]),
        "stage4_2r1_was_not_run_or_reused": bool(cfg.get("stage4_2r1_was_not_run_or_reused")),
        "passed": bool(
            alignment
            and no_deadline_expansion
            and early_window
            and cfg["early_braking_closure"]["selection_is_conditioned_only_on_trusted_delay"]
            and cfg["early_braking_closure"]["selection_uses_both_required_targets"]
            and not cfg["early_braking_closure"]["unseen_target_holdout_claimed"]
            and cfg.get("stage4_2r1_was_not_run_or_reused")
        ),
    }


def _default_source(project_dir: Path) -> Path:
    env = os.environ.get("STAGE4_1R13_SOURCE_STAGE4_1R12_RUN")
    if env:
        return Path(env).expanduser().resolve()
    latest = project_dir / "stage4_1r12_runs" / "latest_stage4_1r12_run.txt"
    if latest.is_file():
        return Path(latest.read_text(encoding="utf-8").strip()).expanduser().resolve()
    raise FileNotFoundError(
        "set STAGE4_1R13_SOURCE_STAGE4_1R12_RUN or provide --source-stage4-1r12-run"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R13 immutable-deadline delay-pipeline early braking"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "configs"
        / "stage4_1r13_original_deadline_delay_pipeline_early_braking_370ms.json",
    )
    parser.add_argument("--source-stage4-1r12-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command",
        choices=["all", "audit", "development", "confirmation", "grid"],
        default=os.environ.get("STAGE4_1R13_COMMAND", "all"),
    )
    parser.add_argument(
        "--backend",
        choices=["ray", "serial"],
        default=os.environ.get("STAGE4_1R13_BACKEND", "ray"),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    project_dir = args.config.expanduser().resolve().parents[1]
    if args.self_test:
        print(json.dumps(self_test(project_dir), indent=2, sort_keys=True))
        return
    source = args.source_stage4_1r12_run or _default_source(project_dir)
    ctx = load_stage41r13_config(
        args.config,
        source_stage41r12_run=source,
        run_dir_override=args.run_dir,
    )
    payload = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume or os.environ.get("STAGE4_1R13_RESUME") == "1"),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
