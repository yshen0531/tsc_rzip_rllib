"""Stage4.1R10 causal queue-preview terminal-transition validation.

Stage4.1R9 established a sharply structured failure: all six terminal-feedback
policies passed every delay=0 case and failed every delay=1/2 case, while the
TSC runs, solver, scheduler and explicit delay queue all completed normally.
The final one or two main-MPC commands were already issued at 330/340 ms but had
not yet affected the plant at the 350 ms boundary.  Their norms were several
times larger than the first R9 terminal correction, so they produced a common
speed kick before any post-boundary feedback could act.

R10 tests the smallest causal architecture change that can isolate this
boundary effect.  It preserves the exact physical and applied-command prefix
through 350 ms, but replaces only those last ``delay`` issue slots whose
commands provably cannot have influenced the plant by 350 ms.  Each replacement
is computed at its original issue time from only the state and queue available
at that time.  A longer continuously streaming terminal controller then runs to
750 ms.  Candidate selection uses only the nominal target; RZ_p10_m10 remains a
disjoint holdout.  Trusted R8 pair-level calibration tokens are used only after
Oracle development and holdout close.

This is still a finite, static, clean-measurement digital-twin experiment.  It
is not restart, hidden vessel/eddy-history, plant-mismatch, continuous actuator
change, noisy sensing, hardware pre-shot calibration, or deployment validation.
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
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r9.atomic_write_json
atomic_write_json_gz = r9.atomic_write_json_gz
read_json = r9.read_json
read_json_gz = r9.read_json_gz
utc_timestamp = r9.utc_timestamp
write_csv = r9.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R10"
CONTROLLER_REVISION = "queue_preview_terminal_transition_hold_v10"
EXPECTED_SOURCE_REVISION = "terminal_template_mpc_feedback_hold_v9"
PACKAGE_REVISION = "r10_queue_preview_transition_v1"
MAIN_CONTROL_STEPS = 35
N_MODES = 3


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _json_safe(value: Any) -> Any:
    return r9._json_safe(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    return r9._as_bool(value, default)


def _as_int(value: Any, default: int = 0) -> int:
    return r9._as_int(value, default)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r9._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r9._sha256_file(path)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "s41r10_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _array_digest(array: np.ndarray, prefix: str) -> str:
    return r9._array_digest(array, prefix)


def _result_complete(path: Path) -> bool:
    return r9._result_complete(path)


def _available_memory_gb() -> float:
    return r9._available_memory_gb()


def _copy_json_payload(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape:
        return math.inf
    return float(np.max(np.abs(a - b))) if a.size else 0.0


# ---------------------------------------------------------------------------
# Paths and source validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage41R10Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    oracle_development: Path
    oracle_holdout: Path
    calibrated_confirmation: Path
    restart_audit: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R10Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r10_source_reference",
            source_audit=run_dir / "stage4_1r10_source_audit",
            oracle_development=run_dir / "stage4_1r10_oracle_development",
            oracle_holdout=run_dir / "stage4_1r10_oracle_holdout",
            calibrated_confirmation=run_dir / "stage4_1r10_calibrated_confirmation",
            restart_audit=run_dir / "stage4_1r10_restart_audit",
            analysis=run_dir / "stage4_1r10_analysis",
            variants=run_dir / "stage4_1r10_environment_variants",
            state=run_dir / "stage4_1r10_state.json",
            manifest=run_dir / "stage4_1r10_manifest.json",
        )


@dataclass
class Stage41R10Context:
    cfg: dict[str, Any]
    paths: Stage41R10Paths
    project_dir: Path
    source_stage41r9_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    source_stage41r8_run: Path
    r9_ctx: r9.Stage41R9Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r9_manifest.json",
        source / "stage4_1r9_state.json",
        source / "stage4_1r9_config.resolved.json",
        source / "stage4_1r9_analysis" / "stage4_1r9_verdict.json",
        source / "stage4_1r9_analysis" / "stage4_1r9_summary.json",
        source / "stage4_1r9_source_audit" / "summary.json",
        source / "stage4_1r9_oracle_development" / "summary.json",
        source / "stage4_1r9_oracle_development" / "results.json",
    ]
    required.extend(
        sorted(
            (source / "stage4_1r9_oracle_development" / "raw").glob(
                "*.json.gz"
            )
        )
    )
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R9 source file missing: {path}")
        size = path.stat().st_size
        total += size
        rows.append(
            {
                "relative_path": path.relative_to(source).as_posix(),
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
    return r9._resolve_recorded_run(project_dir, recorded, run_root_name)


def _validate_source_stage41r9(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = source.expanduser().resolve()
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R9 source file missing: {path}")
    manifest = read_json(source / "stage4_1r9_manifest.json")
    state = read_json(source / "stage4_1r9_state.json")
    source_cfg = read_json(source / "stage4_1r9_config.resolved.json")
    verdict = read_json(source / "stage4_1r9_analysis" / "stage4_1r9_verdict.json")
    requirement = cfg["source_requirement"]
    if manifest.get("stage") != requirement["required_stage"]:
        raise ValueError("source Stage4.1R9 manifest stage mismatch")
    if manifest.get("controller_revision") != requirement["required_controller_revision"]:
        raise ValueError("source Stage4.1R9 controller revision mismatch")
    if source_cfg.get("controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R9 resolved config revision mismatch")
    if bool(requirement.get("require_finished", True)) and not bool(
        state.get("finished")
    ):
        raise ValueError("source Stage4.1R9 is not finished")
    required_stop = str(requirement.get("require_stop_reason", ""))
    if required_stop and str(state.get("stop_reason")) != required_stop:
        raise ValueError(
            "source Stage4.1R9 stop_reason mismatch: "
            f"{state.get('stop_reason')!r} != {required_stop!r}"
        )
    source_audit = state.get("source_audit_summary") or {}
    development = state.get("oracle_development_summary") or {}
    if bool(requirement.get("require_source_audit_passed", True)) and not bool(
        source_audit.get("passed")
    ):
        raise ValueError("source Stage4.1R9 source audit did not pass")
    if bool(requirement.get("require_oracle_development_failed", True)) and bool(
        development.get("passed")
    ):
        raise ValueError("R10 expects source R9 oracle development to have failed")
    if bool(requirement.get("require_holdout_not_executed", True)) and bool(
        state.get("oracle_holdout_complete")
    ):
        raise ValueError("R10 expects source R9 holdout not to have run")
    if bool(
        requirement.get("require_calibrated_confirmation_not_executed", True)
    ) and bool(state.get("calibrated_confirmation_complete")):
        raise ValueError("R10 expects source R9 calibrated confirmation not to have run")
    raw = list(
        (source / "stage4_1r9_oracle_development" / "raw").glob("*.json.gz")
    )
    expected = int(requirement["require_raw_oracle_development_count"])
    if len(raw) != expected:
        raise ValueError(
            f"source R9 raw development count mismatch: {len(raw)} != {expected}"
        )
    results = read_json(
        source / "stage4_1r9_oracle_development" / "results.json"
    )
    if len(results) != expected:
        raise ValueError("source R9 flattened development result count mismatch")
    return manifest, state, source_cfg, verdict


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R10 controller_revision mismatch")
    gate = cfg["gate"]
    if not math.isclose(float(gate["precise_tolerance_m"]), 0.03, abs_tol=1e-15):
        raise ValueError("R10 may not weaken the 30 mm position gate")
    if not math.isclose(
        float(gate["terminal_velocity_max_m_per_s"]), 0.1, abs_tol=1e-15
    ):
        raise ValueError("R10 may not weaken the 0.1 m/s terminal speed gate")
    terminal = cfg["terminal_transition"]
    if int(terminal["main_control_steps"]) != MAIN_CONTROL_STEPS:
        raise ValueError("R10 main-control boundary must remain 35 steps")
    horizon = int(terminal["horizon_steps"])
    tail = int(terminal["tail_feedback_steps"])
    if horizon != MAIN_CONTROL_STEPS + tail or horizon != 75:
        raise ValueError("R10 horizon must be 35 + 40 = 75 steps")
    delays = [int(value) for value in terminal["actual_delay_steps"]]
    slews = [float(value) for value in terminal["actual_slew_scales"]]
    if delays != [0, 1, 2] or slews != [0.9, 1.0, 1.1]:
        raise ValueError("R10 finite actuator bank must remain the frozen 3x3 grid")
    candidates = list(terminal["candidate_bank"])
    if len(candidates) != 6:
        raise ValueError("R10 development bank must contain exactly six policies")
    ids = [str(row["policy_id"]) for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate R10 policy_id")
    for row in candidates:
        template = int(row["template_step"])
        if template < 0 or template + max(delays) >= MAIN_CONTROL_STEPS:
            raise ValueError(
                f"template_step={template} leaves no free delayed terminal action"
            )
        for key in (
            "controller_scale",
            "velocity_measurement_gain",
            "position_measurement_gain",
        ):
            if float(row[key]) <= 0.0:
                raise ValueError(f"R10 candidate {key} must be positive")
    if str(terminal["development_target"]["target_id"]) == str(
        terminal["holdout_target"]["target_id"]
    ):
        raise ValueError("R10 development and holdout targets must be disjoint")
    if str(terminal.get("terminal_nominal_physical_mode")) != (
        "zero_current_increment"
    ):
        raise ValueError("R10 terminal nominal must remain zero current increment")
    if str(terminal.get("integral_mode")) != "reset_zero":
        raise ValueError("R10 terminal integral state must start from zero")
    if str(terminal.get("initial_previous_correction")) != (
        "last_main_mode_correction"
    ):
        raise ValueError(
            "R10 transition smoothing must use the last main-MPC correction"
        )
    arrivals = [int(value) for value in terminal["allowed_arrival_steps"]]
    if not arrivals or min(arrivals) < 0 or max(arrivals) >= horizon:
        raise ValueError("R10 allowed arrival steps are invalid")
    if not bool(terminal.get("preview_replaces_only_unapplied_issue_slots")):
        raise ValueError("R10 must replace only issue slots unapplied at 350 ms")
    if not bool(terminal.get("preview_uses_only_original_issue_time_information")):
        raise ValueError("R10 preview must remain causal at original issue times")
    if cfg["calibrated_confirmation"].get("online_handover_enabled"):
        raise ValueError("R10 calibrated confirmation must not use online handover")
    if not bool(cfg.get("finite_test_envelope_only", False)):
        raise ValueError("R10 must remain explicitly finite-envelope only")


def load_stage41r10_config(
    config_path: Path,
    *,
    source_stage41r9_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R10Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r9_run = source_stage41r9_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r9(
        source_stage41r9_run, cfg
    )
    source_stage41r8_run = _resolve_recorded_run(
        project_dir,
        str(manifest["source_stage4_1r8_run"]),
        "stage4_1r8_runs",
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r10_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r10')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    paths = Stage41R10Paths.from_run_dir(run_dir)

    r9_config_path = (
        project_dir
        / "configs"
        / "stage4_1r9_terminal_template_mpc_feedback_hold_550ms.json"
    )
    if not r9_config_path.is_file():
        raise FileNotFoundError(f"packaged R9 dependency config missing: {r9_config_path}")
    r9_ctx = r9.load_stage41r9_config(
        r9_config_path,
        source_stage41r8_run=source_stage41r8_run,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    base34 = r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R10_TSC_WORKSPACE_ROOT",
                storage["tsc_workspace_root"],
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R10_TSC_RUN_ROOT", storage["tsc_run_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(
        storage.get("keep_failed_episode_dir", False)
    )
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    train_cfg = copy.deepcopy(base34.train_cfg)
    train_cfg["env_config"] = str(paths.run_dir / "env_config.resolved.json")
    base34.env_cfg = env_cfg
    base34.train_cfg = train_cfg
    return Stage41R10Context(
        cfg=cfg,
        paths=paths,
        project_dir=project_dir,
        source_stage41r9_run=source_stage41r9_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        source_stage41r8_run=source_stage41r8_run,
        r9_ctx=r9_ctx,
        source_fingerprint=_source_inventory(source_stage41r9_run),
    )


# ---------------------------------------------------------------------------
# Run state, preflight and preparation
# ---------------------------------------------------------------------------


def runtime_preflight(ctx: Stage41R10Context) -> dict[str, Any]:
    requested = int(
        os.environ.get("STAGE4_1R10_WORKERS", ctx.cfg["parallel"]["n_workers"])
    )
    logical = int(os.cpu_count() or 1)
    reserve = int(ctx.cfg["parallel"].get("reserve_logical_cpus", 16))
    ceiling = max(1, logical - reserve)
    if requested > ceiling:
        raise RuntimeError(
            f"Stage4.1R10 requests {requested} workers but safe ceiling is {ceiling} "
            f"({logical} visible, reserve={reserve}); no silent fallback is allowed"
        )
    memory = _available_memory_gb()
    configured = int(ctx.cfg["parallel"]["n_workers"])
    minimum = (
        float(ctx.cfg["parallel"].get("minimum_available_memory_gb", 72.0))
        * requested
        / configured
    )
    if math.isfinite(memory) and memory < minimum:
        raise RuntimeError(
            f"Stage4.1R10 requires {minimum:.1f} GiB available memory; "
            f"{memory:.1f} GiB visible"
        )
    soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
    required_fd = max(1024, requested * 16)
    if soft_fd < required_fd:
        raise RuntimeError(
            f"open-file soft limit {soft_fd} is below required {required_fd}"
        )
    return {
        "requested_workers": requested,
        "logical_cpus": logical,
        "reserved_logical_cpus": reserve,
        "safe_worker_ceiling": ceiling,
        "available_memory_gb": None if not math.isfinite(memory) else memory,
        "open_file_soft_limit": soft_fd,
        "open_file_hard_limit": hard_fd,
    }


def initial_state() -> dict[str, Any]:
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
        "restart_audit_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R10Context, **values: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(_json_safe(values))
    state["package_revision"] = PACKAGE_REVISION
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def _validated_resume_manifest(
    old: Mapping[str, Any], current: Mapping[str, Any]
) -> dict[str, Any]:
    for key in (
        "controller_revision",
        "package_revision",
        "source_stage4_1r9_run",
        "source_fingerprint",
    ):
        if old.get(key) != current.get(key):
            raise ValueError(f"resume manifest mismatch for {key}")
    return copy.deepcopy(dict(old))


def initialize_run(ctx: Stage41R10Context, preflight: Mapping[str, Any]) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.oracle_development,
        ctx.paths.oracle_holdout,
        ctx.paths.calibrated_confirmation,
        ctx.paths.restart_audit,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        ctx.paths.run_dir / "stage4_1r10_config.resolved.json", ctx.cfg
    )
    base34 = ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    atomic_write_json(
        ctx.paths.run_dir / "env_config.resolved.json", base34.env_cfg
    )
    atomic_write_json(
        ctx.paths.run_dir / "train_config.resolved.json", base34.train_cfg
    )
    reference_files = {
        "stage4_1r9_manifest.json": ctx.source_manifest,
        "stage4_1r9_state.json": ctx.source_state,
        "stage4_1r9_config.resolved.json": ctx.source_cfg,
        "stage4_1r9_verdict.json": ctx.source_verdict,
        "source_content_inventory.json": ctx.source_fingerprint,
    }
    for name, payload in reference_files.items():
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r9_run": str(ctx.source_stage41r9_run),
        "source_stage4_1r8_run": str(ctx.source_stage41r8_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": dict(preflight),
        "physical_prefix_through_350ms_changed": False,
        "applied_command_prefix_through_350ms_changed": False,
        "issued_commands_replaced_only_if_unapplied_by_350ms": True,
        "preview_uses_original_issue_time_information_only": True,
        "observer_changed_in_applied_prefix": False,
        "target_library_changed": False,
        "jacobian_changed": False,
        "terminal_queue_semantics": (
            "causal_preview_replacement_then_continuous_streaming_explicit_delay_queue"
        ),
        "candidate_selection_target": ctx.cfg["terminal_transition"]
        ["development_target"]["target_id"],
        "disjoint_holdout_target": ctx.cfg["terminal_transition"]
        ["holdout_target"]["target_id"],
        "finite_test_envelope_only": True,
        "hardware_pre_shot_calibration_validated": False,
        "true_restart_validation_performed": False,
        "continuous_parameter_change_validated": False,
        "deployment_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    if ctx.paths.manifest.exists():
        _validated_resume_manifest(read_json(ctx.paths.manifest), manifest)
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())


def prepare(ctx: Stage41R10Context) -> dict[str, Any]:
    preflight = runtime_preflight(ctx)
    initialize_run(ctx, preflight)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "run_dir": str(ctx.paths.run_dir),
        "source_stage4_1r9_run": str(ctx.source_stage41r9_run),
        "source_fingerprint_digest": ctx.source_fingerprint["digest"],
        "preflight": preflight,
        "prepared": True,
    }


# ---------------------------------------------------------------------------
# Source R9 forensic audit
# ---------------------------------------------------------------------------


def _source_raw_results(ctx: Stage41R10Context) -> list[dict[str, Any]]:
    output = []
    for path in sorted(
        (
            ctx.source_stage41r9_run
            / "stage4_1r9_oracle_development"
            / "raw"
        ).glob("*.json.gz")
    ):
        output.append(read_json_gz(path))
    return output


def _source_raw_by_key(
    ctx: Stage41R10Context,
) -> dict[tuple[str, int, float, str], dict[str, Any]]:
    output: dict[tuple[str, int, float, str], dict[str, Any]] = {}
    for result in _source_raw_results(ctx):
        spec = result.get("spec") or {}
        key = (
            str(spec.get("target_id")),
            int(spec.get("action_delay_steps", -1)),
            float(spec.get("slew_scale", math.nan)),
            str(spec.get("terminal_policy_id")),
        )
        if key in output:
            raise ValueError(f"duplicate R9 source raw key: {key}")
        output[key] = result
    return output


def _source_rows(ctx: Stage41R10Context) -> list[dict[str, Any]]:
    return read_json(
        ctx.source_stage41r9_run
        / "stage4_1r9_oracle_development"
        / "results.json"
    )


def _speed_at_state(
    trajectory: Sequence[Mapping[str, Any]], index: int, dt_s: float
) -> float:
    return r9._speed_at_state(trajectory, index, dt_s)


def _source_transition_evidence(
    ctx: Stage41R10Context,
    raw_by_key: Mapping[tuple[str, int, float, str], Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], bool, float]:
    policies = sorted(
        {key[3] for key in raw_by_key if key[0] == "nominal"}
    )
    if not policies:
        return [], False, math.inf
    canonical = policies[0]
    dt_s = float(ctx.source_cfg["terminal_feedback"]["dt_s"])
    rows: list[dict[str, Any]] = []
    all_identical = True
    max_difference = 0.0
    for delay in (0, 1, 2):
        for slew in (0.9, 1.0, 1.1):
            case_results = [
                raw_by_key[("nominal", delay, slew, policy)]
                for policy in policies
            ]
            reference = case_results[0]
            # Through the state immediately before the first terminal-issued
            # command can affect the plant, every policy must be identical.
            state_count = MAIN_CONTROL_STEPS + delay + 1
            ref_prefix = r9._physics_prefix(reference, state_count=state_count)
            for other in case_results[1:]:
                diff = _finite_max_abs(
                    ref_prefix,
                    r9._physics_prefix(other, state_count=state_count),
                )
                max_difference = max(max_difference, diff)
                all_identical = bool(all_identical and diff == 0.0)
            selected = raw_by_key[("nominal", delay, slew, canonical)]
            trajectory = list(selected.get("trajectory") or [])
            control = list(selected.get("control_trace") or [])
            pending_rows = control[MAIN_CONTROL_STEPS - delay :]
            pending_norms = [
                float(
                    np.linalg.norm(
                        np.asarray(
                            row.get("issued_mode_coefficients", np.zeros(N_MODES)),
                            dtype=float,
                        )
                    )
                )
                for row in pending_rows
            ]
            tail = list(selected.get("terminal_feedback_trace") or [])
            first_terminal_norm = (
                float(
                    np.linalg.norm(
                        np.asarray(
                            tail[0].get(
                                "issued_desired_physical_mode_coefficients",
                                np.zeros(N_MODES),
                            ),
                            dtype=float,
                        )
                    )
                )
                if tail
                else math.nan
            )
            speed_350 = _speed_at_state(trajectory, MAIN_CONTROL_STEPS, dt_s)
            before_effect_index = MAIN_CONTROL_STEPS + delay
            after_effect_index = min(before_effect_index + 1, len(trajectory) - 1)
            speed_before = _speed_at_state(
                trajectory, before_effect_index, dt_s
            )
            speed_after = _speed_at_state(
                trajectory, after_effect_index, dt_s
            )
            rows.append(
                {
                    "actual_delay_steps": delay,
                    "actual_slew_scale": slew,
                    "speed_at_350ms_m_per_s": speed_350,
                    "speed_before_first_terminal_effect_m_per_s": speed_before,
                    "speed_after_first_terminal_effect_m_per_s": speed_after,
                    "speed_increase_from_pending_before_terminal_effect_m_per_s": (
                        speed_before - speed_350
                    ),
                    "pending_main_command_count": delay,
                    "pending_main_command_norms": pending_norms,
                    "maximum_pending_main_command_norm": max(
                        pending_norms, default=0.0
                    ),
                    "first_terminal_desired_physical_norm": first_terminal_norm,
                    "policies_identical_before_first_terminal_effect": all(
                        _finite_max_abs(
                            ref_prefix,
                            r9._physics_prefix(
                                item, state_count=state_count
                            ),
                        )
                        == 0.0
                        for item in case_results
                    ),
                }
            )
    return rows, all_identical, max_difference


def run_source_audit(ctx: Stage41R10Context) -> dict[str, Any]:
    raw = _source_raw_results(ctx)
    rows = _source_rows(ctx)
    raw_by_key = _source_raw_by_key(ctx)
    expected = int(ctx.cfg["source_requirement"]["require_raw_oracle_development_count"])
    ids = [str(result.get("experiment_id")) for result in raw]
    abnormal = sum(
        bool(state.get("abnormal", False))
        for result in raw
        for state in (result.get("trajectory") or [])
    )
    failure_reasons = sum(
        bool(str(result.get("failure_reason", "")).strip()) for result in raw
    )
    solver_failures = sum(
        not bool(step.get("solver_success", False))
        for result in raw
        for step in (result.get("terminal_feedback_trace") or [])
    )
    queue_inconsistent = sum(
        not bool(
            (result.get("terminal_feedback_summary") or {}).get(
                "streaming_queue_consistent", False
            )
        )
        for result in raw
    )
    pending_bypassed = sum(
        bool(
            (result.get("terminal_feedback_summary") or {}).get(
                "pending_queue_bypassed", True
            )
        )
        for result in raw
    )
    tracking_by_delay: dict[str, dict[str, Any]] = {}
    for delay in (0, 1, 2):
        subset = [
            row
            for row in rows
            if int(row["actual_action_delay_steps"]) == delay
        ]
        passes = sum(bool(row.get("stage3_4_target_tracking_pass")) for row in subset)
        tracking_by_delay[str(delay)] = {
            "passed": passes,
            "total": len(subset),
            "fraction": passes / max(len(subset), 1),
            "minimum_margin": min(
                (
                    _as_float(
                        row.get("stage3_4_tracking_minimum_signed_margin"),
                        math.inf,
                    )
                    for row in subset
                ),
                default=math.inf,
            ),
            "maximum_margin": max(
                (
                    _as_float(
                        row.get("stage3_4_tracking_minimum_signed_margin"),
                        -math.inf,
                    )
                    for row in subset
                ),
                default=-math.inf,
            ),
        }
    transition_rows, identical, prefix_max = _source_transition_evidence(
        ctx, raw_by_key
    )
    max_current_util = max(
        (_as_float(row.get("max_current_utilization"), 0.0) for row in rows),
        default=0.0,
    )
    all_success = len(raw) == expected and all(bool(item.get("success")) for item in raw)
    delay0_all_pass = tracking_by_delay["0"]["passed"] == tracking_by_delay["0"]["total"] == 18
    delayed_all_fail = (
        tracking_by_delay["1"]["passed"] == 0
        and tracking_by_delay["1"]["total"] == 18
        and tracking_by_delay["2"]["passed"] == 0
        and tracking_by_delay["2"]["total"] == 18
    )
    passed = bool(
        len(raw) == expected
        and len(rows) == expected
        and len(set(ids)) == expected
        and all_success
        and failure_reasons == 0
        and abnormal == 0
        and solver_failures == 0
        and queue_inconsistent == 0
        and pending_bypassed == 0
        and delay0_all_pass
        and delayed_all_fail
        and identical
        and prefix_max == 0.0
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r9_run": str(ctx.source_stage41r9_run),
        "source_finished": bool(ctx.source_state.get("finished")),
        "source_stop_reason": ctx.source_state.get("stop_reason"),
        "raw_rollouts": len(raw),
        "expected_raw_rollouts": expected,
        "raw_coverage_complete": len(raw) == expected,
        "unique_experiment_ids": len(set(ids)),
        "environment_success_count": sum(bool(item.get("success")) for item in raw),
        "failure_reason_count": failure_reasons,
        "abnormal_state_count": abnormal,
        "solver_failure_step_count": solver_failures,
        "streaming_queue_inconsistent_count": queue_inconsistent,
        "pending_queue_bypass_count": pending_bypassed,
        "tracking_by_delay": tracking_by_delay,
        "all_delay0_cases_pass": delay0_all_pass,
        "all_delay1_delay2_cases_fail": delayed_all_fail,
        "all_policies_identical_before_first_terminal_effect": identical,
        "maximum_pre_effect_prefix_difference": prefix_max,
        "maximum_current_utilization": max_current_util,
        "transition_attribution": transition_rows,
        "source_holdout_status": "not_run",
        "source_calibrated_confirmation_status": "not_run",
        "passed": passed,
        "interpretation": (
            "R9 completed normally. Every delay=0 development case passed and "
            "every delay=1/2 case failed for every candidate. Before a terminal-"
            "issued command can affect the plant, policies are exactly identical; "
            "the remaining main-MPC pipeline commands create a deterministic speed "
            "kick. R10 therefore changes the causal queue-boundary transition, not "
            "the tracking gate and not the 14-coil problem ownership."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    write_csv(ctx.paths.source_audit / "r9_transition_attribution.csv", transition_rows)
    write_csv(ctx.paths.source_audit / "r9_development_results.csv", rows)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary

# ---------------------------------------------------------------------------
# Causal preview queue and terminal measurement
# ---------------------------------------------------------------------------


def _control_item(
    row: Mapping[str, Any], *, origin: str, origin_index: int
) -> dict[str, Any]:
    return {
        "origin": str(origin),
        "origin_index": int(origin_index),
        "command": np.asarray(
            row.get("issued_mode_coefficients", np.zeros(N_MODES)), dtype=float
        ).reshape(N_MODES),
        "desired_physical": np.asarray(
            row.get(
                "issued_desired_physical_mode_coefficients",
                row.get(
                    "desired_physical_mode_coefficients",
                    row.get("issued_mode_coefficients", np.zeros(N_MODES)),
                ),
            ),
            dtype=float,
        ).reshape(N_MODES),
    }


def _initial_preview_queue(
    control_trace: Sequence[Mapping[str, Any]], delay_steps: int
) -> tuple[list[dict[str, Any]], list[int]]:
    if len(control_trace) != MAIN_CONTROL_STEPS:
        raise ValueError(
            f"expected {MAIN_CONTROL_STEPS} main-control rows, got {len(control_trace)}"
        )
    delay = max(0, int(delay_steps))
    if delay == 0:
        return [], []
    preview_indices = list(range(MAIN_CONTROL_STEPS - delay, MAIN_CONTROL_STEPS))
    queue_start = preview_indices[0] - delay
    if queue_start < 0:
        raise ValueError("insufficient main-control history for causal preview")
    queue = [
        _control_item(
            control_trace[index], origin="main_control", origin_index=index
        )
        for index in range(queue_start, preview_indices[0])
    ]
    if len(queue) != delay:
        raise AssertionError("initial preview queue length invariant broken")
    return queue, preview_indices


def _terminal_measurement_at_issue(
    trajectory: Sequence[Mapping[str, Any]],
    *,
    issue_step: int,
    target: np.ndarray,
    dt_s: float,
) -> np.ndarray:
    issue = int(issue_step)
    if issue <= 0 or issue >= len(trajectory):
        raise ValueError(f"invalid preview issue_step={issue}")
    # Only states 0..issue are visible at the issue time.  Future states are
    # intentionally excluded from the slice passed to the measurement helper.
    return r9._terminal_measurement(
        list(trajectory[: issue + 1]), target, dt_s
    )


def _queue_origins(
    queue: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return r9._queue_origins(queue)


def _stream_queue_apply(
    queue: Sequence[Mapping[str, Any]],
    issued_item: Mapping[str, Any],
    delay_steps: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return r9._stream_queue_apply(queue, issued_item, delay_steps)


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


def _replace_unapplied_issue_row(
    row: Mapping[str, Any],
    *,
    issue_step: int,
    desired_physical: np.ndarray,
    issued_command: np.ndarray,
    correction: np.ndarray,
    measurement_physical: np.ndarray,
    measurement_normalized: np.ndarray,
    measurement_for_solver: np.ndarray,
    solve: Mapping[str, Any],
    scheduled: Mapping[str, Any],
) -> dict[str, Any]:
    updated = copy.deepcopy(dict(row))
    preservation_keys = (
        "issued_mode_coefficients",
        "issued_desired_physical_mode_coefficients",
        "desired_physical_mode_coefficients",
        "mode_correction_physical",
        "feedforward_physical_mode_coefficients",
        "measurement_physical",
        "measurement_normalized",
        "scheduler_predicted_mismatch_rms_a",
        "scheduler_predicted_mismatch_max_abs_a",
    )
    for key in preservation_keys:
        if key in updated:
            updated[f"transition_original_{key}"] = copy.deepcopy(updated[key])
    updated.update(
        {
            "transition_preview_replaced_unapplied_issue": True,
            "transition_preview_issue_step": int(issue_step),
            "transition_preview_uses_future_measurement": False,
            "transition_preview_physical_prefix_effect_before_350ms": False,
            "measurement_source": "r10_causal_original_issue_time_preview",
            "measurement_physical": np.asarray(
                measurement_physical, dtype=float
            ).tolist(),
            "measurement_normalized": np.asarray(
                measurement_normalized, dtype=float
            ).tolist(),
            "transition_preview_measurement_for_solver": np.asarray(
                measurement_for_solver, dtype=float
            ).tolist(),
            "feedforward_physical_mode_coefficients": [0.0, 0.0, 0.0],
            "mode_correction_physical": np.asarray(correction, dtype=float).tolist(),
            "desired_physical_mode_coefficients": np.asarray(
                desired_physical, dtype=float
            ).tolist(),
            "issued_desired_physical_mode_coefficients": np.asarray(
                desired_physical, dtype=float
            ).tolist(),
            "issued_mode_coefficients": np.asarray(
                issued_command, dtype=float
            ).tolist(),
            "solver_success": bool(solve.get("solver_success", False)),
            "solver_status": int(solve.get("solver_status", 0)),
            "solver_cost": float(solve.get("solver_cost", 0.0)),
            "predicted_normalized_residual_rms": float(
                solve.get("predicted_normalized_residual_rms", 0.0)
            ),
            "scheduler_predicted_mismatch_rms_a": float(
                scheduled.get("mismatch_rms_a", 0.0)
            ),
            "scheduler_predicted_mismatch_max_abs_a": float(
                scheduled.get("mismatch_max_abs_a", 0.0)
            ),
            "transition_preview_scheduler_actual_mismatch_deferred_until_application": True,
        }
    )
    return updated


# ---------------------------------------------------------------------------
# R10 TSC worker
# ---------------------------------------------------------------------------


class LocalStage41R10Worker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        # R9 is retained as the complete frozen dependency chain.  Its public
        # evaluate method is not used; R10 owns the transition and tail logic.
        self.r9_worker = r9.LocalStage41R9Worker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base_worker = self.r9_worker.base_worker
        self.bundle = bundle
        self.horizon_steps = int(payload.get("stage4_1r4_horizon_steps", 35))

    def _cleanup_episode(self, *, failed: bool, reason: str) -> None:
        runner = getattr(self.base_worker.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=failed, reason=reason)

    def close(self) -> None:
        self.r9_worker.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        return self._run_queue_preview_terminal_feedback(spec)

    def _run_queue_preview_terminal_feedback(
        self, spec: dict[str, Any]
    ) -> dict[str, Any]:
        started = time.time()
        failed = True
        try:
            internal = copy.deepcopy(spec)
            internal["_defer_cleanup"] = True
            internal["extended_horizon"] = False
            internal["tail_hold_steps"] = 0
            internal["tail_action_policy"] = "none"
            result = self.base_worker.evaluate(internal)
            result["spec"] = copy.deepcopy(spec)
            if not result.get("success"):
                result["controller_revision"] = CONTROLLER_REVISION
                result["stage4_1r10_controller_revision"] = CONTROLLER_REVISION
                return _json_safe(result)

            original_control_trace = copy.deepcopy(
                list(result.get("control_trace") or [])
            )
            control_trace = copy.deepcopy(original_control_trace)
            trajectory = list(result.get("trajectory") or [])
            if len(control_trace) != MAIN_CONTROL_STEPS:
                raise ValueError("main control trace length mismatch")
            if len(trajectory) != MAIN_CONTROL_STEPS + 1:
                raise ValueError("main trajectory prefix length mismatch")

            horizon = int(spec["horizon_steps"])
            tail_steps = int(spec["tail_feedback_steps"])
            if horizon != self.horizon_steps:
                raise ValueError("environment horizon/payload mismatch")
            if horizon != MAIN_CONTROL_STEPS + tail_steps:
                raise ValueError("R10 horizon must equal 35 plus tail feedback steps")

            actual_delay = int(spec["action_delay_steps"])
            modeled_delay = int(spec["controller_action_delay_steps"])
            actual_slew = float(spec["slew_scale"])
            modeled_slew = float(spec["controller_slew_scale_estimate"])
            trusted = bool(spec.get("trusted_calibration_model", False))
            if trusted and (
                actual_delay != modeled_delay
                or not math.isclose(actual_slew, modeled_slew, abs_tol=1e-12)
            ):
                raise ValueError(
                    "trusted finite-envelope R10 spec has actual/modeled actuator mismatch"
                )

            template_step = int(spec["terminal_template_step"])
            controller_scale = float(spec["terminal_controller_scale"])
            model_scale = float(
                spec.get("terminal_controller_model_scale", 1.0)
            )
            velocity_gain = float(spec["terminal_velocity_measurement_gain"])
            position_gain = float(spec["terminal_position_measurement_gain"])
            ip_gain = float(spec.get("terminal_ip_measurement_gain", 1.0))
            if template_step + modeled_delay >= MAIN_CONTROL_STEPS:
                raise ValueError("terminal template leaves no free delayed control step")

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
            nominal_physical = np.zeros((MAIN_CONTROL_STEPS, N_MODES), dtype=float)
            nominal_feature = np.zeros(MAIN_CONTROL_STEPS * 5, dtype=float)
            integral = np.zeros(5, dtype=float)

            actual_gain = np.asarray(
                spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]),
                dtype=float,
            ).reshape(N_MODES)
            controller_gain = np.asarray(
                spec.get(
                    "controller_gain_estimate_by_mode", [1.0, 1.0, 1.0]
                ),
                dtype=float,
            ).reshape(N_MODES)
            actuator_bias = np.asarray(
                spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]),
                dtype=float,
            ).reshape(N_MODES)

            queue, preview_indices = _initial_preview_queue(
                original_control_trace, actual_delay
            )
            first_preview_step = (
                preview_indices[0] if preview_indices else MAIN_CONTROL_STEPS
            )
            previous_index = max(0, first_preview_step - 1)
            previous_correction = np.asarray(
                original_control_trace[previous_index].get(
                    "mode_correction_physical", [0.0, 0.0, 0.0]
                ),
                dtype=float,
            ).reshape(N_MODES)

            preview_trace: list[dict[str, Any]] = []
            preview_consistent = True
            preview_uses_future_measurement = False
            for issue_step in preview_indices:
                measurement_physical = _terminal_measurement_at_issue(
                    trajectory,
                    issue_step=issue_step,
                    target=target,
                    dt_s=dt_s,
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
                    raise ValueError(
                        "preview pending queue length does not match calibrated delay"
                    )
                solve = r3.solve_delay_aware_physical_correction(
                    self.base_worker.stub,
                    self.bundle,
                    current_step=template_step,
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
                    trajectory[issue_step]["currents_a_tsc"], dtype=float
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
                    "origin": "terminal_preview",
                    "origin_index": issue_step,
                    "command": issued_command,
                    "desired_physical": desired_physical,
                }
                queue_before = _queue_origins(queue)
                applied_item, queue = _stream_queue_apply(
                    queue, issued_item, actual_delay
                )
                expected_applied = np.asarray(
                    original_control_trace[issue_step].get(
                        "applied_command_mode_coefficients", np.zeros(N_MODES)
                    ),
                    dtype=float,
                ).reshape(N_MODES)
                applied_command = np.asarray(
                    applied_item["command"], dtype=float
                ).reshape(N_MODES)
                applied_exact = bool(np.array_equal(applied_command, expected_applied))
                applied_numeric = bool(
                    np.allclose(
                        applied_command,
                        expected_applied,
                        rtol=0.0,
                        atol=1e-12,
                    )
                )
                expected_origin_index = issue_step - actual_delay
                origin_correct = bool(
                    str(applied_item["origin"]) == "main_control"
                    and int(applied_item["origin_index"])
                    == expected_origin_index
                )
                preview_consistent = bool(
                    preview_consistent
                    and len(queue) == actual_delay
                    and applied_exact
                    and applied_numeric
                    and origin_correct
                )
                control_trace[issue_step] = _replace_unapplied_issue_row(
                    original_control_trace[issue_step],
                    issue_step=issue_step,
                    desired_physical=desired_physical,
                    issued_command=issued_command,
                    correction=correction,
                    measurement_physical=measurement_physical,
                    measurement_normalized=measurement_normalized,
                    measurement_for_solver=measurement_for_solver,
                    solve=solve,
                    scheduled=scheduled,
                )
                preview_trace.append(
                    {
                        "issue_step": issue_step,
                        "measurement_max_state_index_used": issue_step,
                        "future_measurement_used": False,
                        "template_step": template_step,
                        "modeled_delay_steps": modeled_delay,
                        "actual_delay_steps": actual_delay,
                        "queue_before": queue_before,
                        "queue_after": _queue_origins(queue),
                        "issued_origin": {
                            "origin": "terminal_preview",
                            "origin_index": issue_step,
                        },
                        "applied_origin": {
                            "origin": str(applied_item["origin"]),
                            "origin_index": int(applied_item["origin_index"]),
                        },
                        "expected_applied_origin_index": expected_origin_index,
                        "applied_command_exactly_matches_original_prefix": applied_exact,
                        "applied_command_matches_original_prefix_atol_1e12": applied_numeric,
                        "measurement_physical": measurement_physical.tolist(),
                        "measurement_normalized": measurement_normalized.tolist(),
                        "measurement_for_solver": measurement_for_solver.tolist(),
                        "issued_desired_physical_mode_coefficients": desired_physical.tolist(),
                        "issued_mode_coefficients": issued_command.tolist(),
                        "applied_mode_coefficients": applied_command.tolist(),
                        "mode_correction_physical": correction.tolist(),
                        "previous_correction_physical": previous_correction.tolist(),
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
                            scheduled["mismatch_rms_a"]
                        ),
                        "scheduler_predicted_mismatch_max_abs_a": float(
                            scheduled["mismatch_max_abs_a"]
                        ),
                        "currents_at_original_issue_time_A": currents_before.tolist(),
                    }
                )
                previous_correction = desired_physical.copy()

            queue_after_preview_origins = _queue_origins(queue)
            if actual_delay > 0:
                if any(str(item["origin"]) != "terminal_preview" for item in queue):
                    preview_consistent = False
                if [int(item["origin_index"]) for item in queue] != preview_indices:
                    preview_consistent = False
            elif queue or preview_trace:
                preview_consistent = False

            tail_trace: list[dict[str, Any]] = []
            failure_reason = ""
            streaming_consistent = True
            for tail_index in range(tail_steps):
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
                    raise ValueError(
                        "streaming pending queue length does not match calibrated delay"
                    )
                solve = r3.solve_delay_aware_physical_correction(
                    self.base_worker.stub,
                    self.bundle,
                    current_step=template_step,
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
                    "origin": "terminal_feedback",
                    "origin_index": tail_index,
                    "command": issued_command,
                    "desired_physical": desired_physical,
                }
                queue_before = _queue_origins(queue)
                applied_item, queue = _stream_queue_apply(
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
                state_index = MAIN_CONTROL_STEPS + tail_index + 1
                trajectory.append(
                    r3.base._state_record(
                        self.base_worker.env, state_index, action
                    )
                )
                currents_after = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                tail_trace.append(
                    {
                        "tail_index": tail_index,
                        "environment_step": state_index - 1,
                        "template_step": template_step,
                        "measurement_physical": measurement_physical.tolist(),
                        "measurement_normalized": measurement_normalized.tolist(),
                        "measurement_for_solver": measurement_for_solver.tolist(),
                        "modeled_delay_steps": modeled_delay,
                        "actual_delay_steps": actual_delay,
                        "queue_before": queue_before,
                        "queue_after": _queue_origins(queue),
                        "issued_origin": {
                            "origin": "terminal_feedback",
                            "origin_index": tail_index,
                        },
                        "applied_origin": {
                            "origin": str(applied_item["origin"]),
                            "origin_index": int(applied_item["origin_index"]),
                        },
                        "issued_desired_physical_mode_coefficients": desired_physical.tolist(),
                        "issued_mode_coefficients": issued_command.tolist(),
                        "applied_desired_physical_mode_coefficients": np.asarray(
                            applied_item["desired_physical"], dtype=float
                        ).tolist(),
                        "applied_mode_coefficients": applied_command.tolist(),
                        "effective_mode_coefficients": effective.tolist(),
                        "mode_correction_physical": correction.tolist(),
                        "previous_correction_physical": previous_correction.tolist(),
                        "solver_success": bool(solve.get("solver_success", False)),
                        "solver_status": int(solve.get("solver_status", 0)),
                        "solver_cost": float(solve.get("solver_cost", 0.0)),
                        "solver_optimality": float(
                            solve.get("solver_optimality", 0.0)
                        ),
                        "solver_effect_step": int(solve.get("effect_step", -1)),
                        "solver_fixed_pending_steps": int(
                            solve.get("fixed_pending_steps", modeled_delay)
                        ),
                        "predicted_normalized_residual_rms": float(
                            solve.get("predicted_normalized_residual_rms", 0.0)
                        ),
                        "scheduler_predicted_mismatch_rms_a": float(
                            scheduled["mismatch_rms_a"]
                        ),
                        "scheduler_predicted_mismatch_max_abs_a": float(
                            scheduled["mismatch_max_abs_a"]
                        ),
                        "currents_before_A": currents_before.tolist(),
                        "currents_after_A": currents_after.tolist(),
                        "actual_current_delta_A": (
                            currents_after - currents_before
                        ).tolist(),
                        "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                    }
                )
                previous_correction = desired_physical.copy()
                if terminated:
                    failure_reason = str(
                        info.get("failure_reason", "terminal feedback terminated")
                    )
                    break
                if truncated and state_index < horizon:
                    failure_reason = (
                        "environment truncated before R10 terminal horizon"
                    )
                    break

            result["control_trace"] = control_trace
            result["original_main_control_trace"] = original_control_trace
            result["transition_preview_trace"] = preview_trace
            result["trajectory"] = trajectory
            result["terminal_feedback_trace"] = tail_trace
            result["tail_queue_trace"] = tail_trace

            pending_command_norms = [
                float(np.linalg.norm(np.asarray(item["command"], dtype=float)))
                for item in queue
            ]
            pending_desired_norms = [
                float(
                    np.linalg.norm(
                        np.asarray(item["desired_physical"], dtype=float)
                    )
                )
                for item in queue
            ]
            preview_desired_norms = [
                float(
                    np.linalg.norm(
                        np.asarray(
                            row["issued_desired_physical_mode_coefficients"],
                            dtype=float,
                        )
                    )
                )
                for row in preview_trace
            ]
            last10 = np.asarray(
                [
                    row["issued_desired_physical_mode_coefficients"]
                    for row in tail_trace[-10:]
                ],
                dtype=float,
            )
            last10_rms = (
                float(np.sqrt(np.mean(last10**2))) if last10.size else 0.0
            )
            result["transition_preview_summary"] = {
                "policy_id": spec["terminal_policy_id"],
                "actual_delay_steps": actual_delay,
                "modeled_delay_steps": modeled_delay,
                "preview_issue_indices": preview_indices,
                "preview_replacement_count": len(preview_trace),
                "expected_preview_replacement_count": actual_delay,
                "all_replacements_unapplied_by_350ms": bool(
                    all(index >= MAIN_CONTROL_STEPS - actual_delay for index in preview_indices)
                ),
                "uses_only_original_issue_time_information": not preview_uses_future_measurement,
                "all_original_applied_commands_preserved": bool(
                    all(
                        row["applied_command_exactly_matches_original_prefix"]
                        for row in preview_trace
                    )
                ),
                "initial_preview_queue_consistent": preview_consistent,
                "post_preview_queue_origins": queue_after_preview_origins,
                "maximum_preview_desired_physical_norm": max(
                    preview_desired_norms, default=0.0
                ),
                "physical_prefix_replayed": False,
                "physical_prefix_invariance_basis": (
                    "replaced commands remain in the explicit delay queue and cannot "
                    "affect any state through index 35"
                ),
            }
            result["terminal_feedback_summary"] = {
                "policy_id": spec["terminal_policy_id"],
                "template_step": template_step,
                "horizon_steps": horizon,
                "tail_feedback_steps": tail_steps,
                "actual_delay_steps": actual_delay,
                "modeled_delay_steps": modeled_delay,
                "continuous_streaming_queue": True,
                "initial_pending_count_after_preview": actual_delay,
                "final_pending_count": len(queue),
                "final_pending_origins": _queue_origins(queue),
                "maximum_final_pending_command_norm": max(
                    pending_command_norms, default=0.0
                ),
                "maximum_final_pending_desired_physical_norm": max(
                    pending_desired_norms, default=0.0
                ),
                "last10_issued_desired_rms": last10_rms,
                "streaming_queue_consistent": streaming_consistent,
                "pending_queue_bypassed": False,
                "terminal_feedback_uses_direct_measured_RZI_and_finite_difference_velocity": True,
                "terminal_feedback_observer_noise_robustness_validated": False,
            }
            success = bool(
                not failure_reason
                and len(trajectory) == horizon + 1
                and len(tail_trace) == tail_steps
                and len(preview_trace) == actual_delay
                and not any(bool(row.get("abnormal", False)) for row in trajectory)
                and preview_consistent
                and streaming_consistent
                and len(queue) == actual_delay
                and all(bool(row.get("solver_success", False)) for row in preview_trace)
                and all(bool(row.get("solver_success", False)) for row in tail_trace)
            )
            result["success"] = success
            result["failure_reason"] = (
                ""
                if success
                else failure_reason or "incomplete R10 queue-preview terminal feedback"
            )
            result["wall_time_s"] = float(time.time() - started)
            result["controller_revision"] = CONTROLLER_REVISION
            result["stage4_1r10_controller_revision"] = CONTROLLER_REVISION
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
                    "original_main_control_trace": [],
                    "transition_preview_trace": [],
                    "terminal_feedback_trace": [],
                    "tail_queue_trace": [],
                }
            )
        finally:
            self._cleanup_episode(
                failed=failed, reason="stage4_1r10_queue_preview_terminal_feedback"
            )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1)
        class Stage41R10Actor:
            def __init__(
                self,
                payload: dict[str, Any],
                library: dict[str, Any],
                bundle: dict[str, Any],
                worker_id: str,
                selector_cfg: dict[str, Any],
            ):
                self.worker = LocalStage41R10Worker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R10Actor
    return _RAY_ACTOR

# ---------------------------------------------------------------------------
# Parallel evaluation
# ---------------------------------------------------------------------------


def materialize_variant(
    ctx: Stage41R10Context, *, slew_scale: float, horizon_steps: int
) -> tuple[str, dict[str, Any]]:
    return r9.materialize_variant(
        ctx.r9_ctx,
        slew_scale=float(slew_scale),
        horizon_steps=int(horizon_steps),
    )


def evaluate_specs(
    ctx: Stage41R10Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = (
        ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.variants
    )
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        variant = str(spec["environment_variant"])
        if variant not in variants:
            raise KeyError(f"unmaterialized environment variant {variant}")
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, rows in by_variant.items():
        pending = [
            row
            for row in rows
            if not (
                resume
                and _result_complete(
                    output_dir / f"{row['experiment_id']}.json.gz"
                )
            )
        ]
        if pending:
            pending_by_variant[variant] = pending
    library = (
        ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_library
    )
    bundle = (
        ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle
    )
    selector_cfg = ctx.r9_ctx.r8_ctx.cfg["batch_selector"]
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalStage41R10Worker(
                variants[variant],
                library,
                bundle,
                f"stage41r10_{variant}_serial",
                selector_cfg,
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz",
                        worker.evaluate(spec),
                    )
                    print(
                        f"[Stage4.1R10 {variant}] {index}/{len(pending)}",
                        flush=True,
                    )
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(
            os.environ.get(
                "STAGE4_1R10_WORKERS", ctx.cfg["parallel"]["n_workers"]
            )
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
            log_prefix="[Stage4.1R10 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {
                variant: len(rows)
                for variant, rows in pending_by_variant.items()
            },
            plan.actor_count,
        )
        print(
            "[Stage4.1R10 mixed-variant] actor_allocation="
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
                    f"stage41r10_{variant}_{index:03d}",
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
                        f"[Stage4.1R10 mixed-variant] waiting {done}/{total_pending}",
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
                            f"[Stage4.1R10 mixed-variant] {done}/{total_pending}",
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


# ---------------------------------------------------------------------------
# Specs, metrics and trace comparisons
# ---------------------------------------------------------------------------


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
        "kind": "stage4_1r10_queue_preview_terminal_transition_hold",
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


def _target_task(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(spec.get("category", "r10")),
    }


def _policy_lookup(ctx: Stage41R10Context) -> dict[str, dict[str, Any]]:
    return {
        str(row["policy_id"]): copy.deepcopy(row)
        for row in ctx.cfg["terminal_transition"]["candidate_bank"]
    }


def _main_extra(
    ctx: Stage41R10Context,
    *,
    actual_delay: int,
    actual_slew: float,
    modeled_delay: int,
    modeled_slew: float,
    policy: Mapping[str, Any],
    calibration_token: str | None,
    trusted: bool,
    controller_variant: str,
) -> dict[str, Any]:
    terminal = ctx.cfg["terminal_transition"]
    generic_policy = {
        "horizon_steps": int(terminal["horizon_steps"]),
        "tail_steps": int(terminal["tail_feedback_steps"]),
        "tail_policy": "queue_preview_then_streaming_terminal_feedback",
        "policy_id": str(policy["policy_id"]),
    }
    extra = r8._main_extra(
        ctx.r9_ctx.r8_ctx,
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
            "horizon_steps": int(terminal["horizon_steps"]),
            "tail_feedback_steps": int(terminal["tail_feedback_steps"]),
            "tail_steps": int(terminal["tail_feedback_steps"]),
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
            "terminal_ip_measurement_gain": float(
                terminal["ip_measurement_gain"]
            ),
            "terminal_controller_model_scale": float(
                terminal["controller_model_scale"]
            ),
            "terminal_integral_mode": str(terminal["integral_mode"]),
            "terminal_nominal_physical_mode": str(
                terminal["terminal_nominal_physical_mode"]
            ),
            "terminal_initial_previous_correction": str(
                terminal["initial_previous_correction"]
            ),
            "transition_preview_replaces_only_unapplied_issue_slots": True,
            "transition_preview_uses_only_original_issue_time_information": True,
            "controller_variant": controller_variant,
            "adaptive_handover": {"enabled": False},
        }
    )
    extra.pop("adaptive_delay_slew_estimator", None)
    return extra


def _physics_array(
    result: Mapping[str, Any], *, state_count: int | None = None
) -> np.ndarray:
    trajectory = list(result.get("trajectory") or [])
    if state_count is not None:
        trajectory = trajectory[: int(state_count)]
    return np.asarray(
        [
            [
                row["R"],
                row["Z"],
                row["Ip"],
                *row["currents_a_tsc"],
                *row["action_norm_tsc"],
            ]
            for row in trajectory
        ],
        dtype=float,
    )


def _control_array(
    trace: Sequence[Mapping[str, Any]], key: str
) -> np.ndarray:
    return np.asarray(
        [row.get(key, [0.0, 0.0, 0.0]) for row in trace], dtype=float
    )


def _source_prefix_comparison(
    ctx: Stage41R10Context,
    result: Mapping[str, Any],
    *,
    atol: float,
) -> dict[str, Any]:
    spec = result.get("spec") or {}
    source = r9._source_h41_by_case(ctx.r9_ctx).get(
        (
            str(spec.get("target_id")),
            int(spec.get("action_delay_steps", -1)),
            float(spec.get("slew_scale", math.nan)),
        )
    )
    if source is None:
        return {
            "source_available": False,
            "physics_exact": False,
            "applied_exact": False,
            "original_issued_exact": False,
            "pre_preview_issued_exact": False,
            "changes_confined_to_preview_slots": False,
            "maximum_abs_difference": math.inf,
        }
    delay = int(spec["action_delay_steps"])
    preview_start = MAIN_CONTROL_STEPS - delay
    result_control = list(result.get("control_trace") or [])
    original_control = list(result.get("original_main_control_trace") or [])
    source_control = list(source.get("control_trace") or [])
    physics_left = _physics_array(result, state_count=MAIN_CONTROL_STEPS + 1)
    physics_right = _physics_array(source, state_count=MAIN_CONTROL_STEPS + 1)
    applied_left = _control_array(
        result_control, "applied_command_mode_coefficients"
    )
    applied_right = _control_array(
        source_control, "applied_command_mode_coefficients"
    )
    original_issued_left = _control_array(
        original_control, "issued_mode_coefficients"
    )
    source_issued = _control_array(source_control, "issued_mode_coefficients")
    current_issued = _control_array(result_control, "issued_mode_coefficients")
    components = {
        "physics": _finite_max_abs(physics_left, physics_right),
        "applied": _finite_max_abs(applied_left, applied_right),
        "original_issued": _finite_max_abs(
            original_issued_left, source_issued
        ),
        "pre_preview_issued": _finite_max_abs(
            current_issued[:preview_start], source_issued[:preview_start]
        ),
    }
    changed_indices = [
        index
        for index in range(min(len(current_issued), len(source_issued)))
        if not np.array_equal(current_issued[index], source_issued[index])
    ]
    expected_changed_region = set(range(preview_start, MAIN_CONTROL_STEPS))
    confined = set(changed_indices).issubset(expected_changed_region)
    preview_rows = [
        index
        for index, row in enumerate(result_control)
        if bool(row.get("transition_preview_replaced_unapplied_issue", False))
    ]
    expected_preview_rows = list(range(preview_start, MAIN_CONTROL_STEPS))
    return {
        "source_available": True,
        "physics_exact": bool(np.array_equal(physics_left, physics_right)),
        "physics_numeric_equal": bool(
            np.allclose(physics_left, physics_right, rtol=0.0, atol=atol)
        ),
        "applied_exact": bool(np.array_equal(applied_left, applied_right)),
        "applied_numeric_equal": bool(
            np.allclose(applied_left, applied_right, rtol=0.0, atol=atol)
        ),
        "original_issued_exact": bool(
            np.array_equal(original_issued_left, source_issued)
        ),
        "original_issued_numeric_equal": bool(
            np.allclose(
                original_issued_left, source_issued, rtol=0.0, atol=atol
            )
        ),
        "pre_preview_issued_exact": bool(
            np.array_equal(
                current_issued[:preview_start], source_issued[:preview_start]
            )
        ),
        "changes_confined_to_preview_slots": confined,
        "changed_issued_indices": changed_indices,
        "preview_rows": preview_rows,
        "expected_preview_rows": expected_preview_rows,
        "preview_row_coverage_exact": preview_rows == expected_preview_rows,
        "component_max_abs_difference": components,
        "maximum_abs_difference": max(components.values(), default=0.0),
    }


def _tracking_metric_policy(
    ctx: Stage41R10Context, spec: Mapping[str, Any], *, phase: str
) -> dict[str, Any]:
    policy_id = str(spec.get("terminal_policy_id") or "").strip()
    if not policy_id:
        raise ValueError(
            f"Stage4.1R10 {phase} result is missing terminal_policy_id"
        )
    terminal = ctx.cfg["terminal_transition"]
    return {
        "policy_id": policy_id,
        "horizon_steps": int(terminal["horizon_steps"]),
        "allowed_arrival_steps": [
            int(value) for value in terminal["allowed_arrival_steps"]
        ],
    }


def _velocity_speed(y: np.ndarray, dt_s: float) -> np.ndarray:
    positions = np.asarray(y, dtype=float)[:, :2]
    velocity = np.zeros_like(positions)
    if len(positions) > 1:
        velocity[1:] = np.diff(positions, axis=0) / max(float(dt_s), 1e-12)
    return np.linalg.norm(velocity, axis=1)


def feedback_result_row(
    ctx: Stage41R10Context,
    result: Mapping[str, Any],
    *,
    phase: str,
) -> dict[str, Any]:
    spec = result.get("spec") or {}
    task = _target_task(spec)
    metric_policy = _tracking_metric_policy(ctx, spec, phase=phase)
    metrics = r8.tracking_metrics(ctx.r9_ctx.r8_ctx, result, metric_policy)
    trajectory = list(result.get("trajectory") or [])
    control_trace = list(result.get("control_trace") or [])
    original_control = list(result.get("original_main_control_trace") or [])
    preview_trace = list(result.get("transition_preview_trace") or [])
    terminal_trace = list(result.get("terminal_feedback_trace") or [])
    transition = result.get("transition_preview_summary") or {}
    terminal = result.get("terminal_feedback_summary") or {}
    prefix = _source_prefix_comparison(
        ctx,
        result,
        atol=float(ctx.cfg["terminal_transition"]["prefix_numeric_atol"]),
    )

    base_target = ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg[
        "target"
    ]
    target = np.asarray(
        [
            float(base_target["R"]) + float(spec.get("target_R_offset_m", 0.0)),
            float(base_target["Z"]) + float(spec.get("target_Z_offset_m", 0.0)),
            float(base_target["Ip"]) + float(spec.get("target_Ip_offset_A", 0.0)),
        ],
        dtype=float,
    )
    y = np.asarray(
        [[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float
    )
    dt_s = float(ctx.cfg["terminal_transition"]["dt_s"])
    speed = _velocity_speed(y, dt_s) if len(y) else np.zeros(0)
    error = y - target[None, :] if len(y) else np.zeros((0, 3))
    last10_speed_rms = (
        float(np.sqrt(np.mean(speed[-10:] ** 2))) if len(speed) else math.inf
    )
    last10_box = (
        float(np.max(np.abs(error[-10:, :2]))) if len(error) else math.inf
    )
    tail_box = (
        float(np.max(np.abs(error[MAIN_CONTROL_STEPS:, :2])))
        if len(error) > MAIN_CONTROL_STEPS
        else math.inf
    )
    last10_issued = np.asarray(
        [
            row.get(
                "issued_desired_physical_mode_coefficients", [0.0] * N_MODES
            )
            for row in terminal_trace[-10:]
        ],
        dtype=float,
    )
    last10_issued_rms = (
        float(np.sqrt(np.mean(last10_issued**2)))
        if last10_issued.size
        else math.inf
    )
    terminal_cfg = ctx.cfg["terminal_transition"]
    convergence_margins = {
        "last10_speed_rms": 1.0
        - last10_speed_rms
        / float(terminal_cfg["maximum_last10_speed_rms_m_per_s"]),
        "last10_box": 1.0
        - last10_box / float(terminal_cfg["maximum_last10_box_error_m"]),
        "tail_box": 1.0
        - tail_box / float(terminal_cfg["maximum_tail_box_error_m"]),
        "final_pending_desired": 1.0
        - _as_float(
            terminal.get("maximum_final_pending_desired_physical_norm"),
            math.inf,
        )
        / float(
            terminal_cfg["maximum_final_pending_desired_physical_norm"]
        ),
        "last10_issued_desired_rms": 1.0
        - last10_issued_rms
        / float(terminal_cfg["maximum_last10_issued_desired_rms"]),
        "preview_desired": 1.0
        - _as_float(
            transition.get("maximum_preview_desired_physical_norm"), 0.0
        )
        / float(terminal_cfg["maximum_preview_desired_physical_norm"]),
    }
    tracking_margin = _as_float(
        metrics.get("stage3_4_tracking_minimum_signed_margin"), -1e12
    )
    combined_margin = min(
        [tracking_margin, *convergence_margins.values()]
    )
    prefix_pass = bool(
        prefix.get("source_available")
        and prefix.get("physics_exact")
        and prefix.get("applied_exact")
        and prefix.get("original_issued_exact")
        and prefix.get("pre_preview_issued_exact")
        and prefix.get("changes_confined_to_preview_slots")
        and prefix.get("preview_row_coverage_exact")
    )
    preview_pass = bool(
        transition.get("preview_replacement_count")
        == transition.get("expected_preview_replacement_count")
        and transition.get("all_replacements_unapplied_by_350ms")
        and transition.get("uses_only_original_issue_time_information")
        and transition.get("all_original_applied_commands_preserved")
        and transition.get("initial_preview_queue_consistent")
        and _as_float(
            transition.get("maximum_preview_desired_physical_norm"),
            math.inf,
        )
        <= float(terminal_cfg["maximum_preview_desired_physical_norm"])
        + 1e-12
    )
    queue_pass = bool(
        terminal.get("continuous_streaming_queue")
        and terminal.get("streaming_queue_consistent")
        and not terminal.get("pending_queue_bypassed", True)
    )
    convergence_pass = bool(
        all(value >= -1e-12 for value in convergence_margins.values())
    )
    r10_pass = bool(
        result.get("success")
        and metrics.get("stage3_4_target_tracking_pass")
        and prefix_pass
        and preview_pass
        and queue_pass
        and convergence_pass
    )

    full_actions = np.asarray(
        [row.get("action_norm_tsc", [0.0] * 14) for row in trajectory[1:]],
        dtype=float,
    )
    terminal_actions = np.asarray(
        [row.get("action_norm_tsc", [0.0] * 14) for row in terminal_trace],
        dtype=float,
    )
    physics = _physics_array(result)
    main_issued = _control_array(control_trace, "issued_mode_coefficients")
    original_issued = _control_array(
        original_control, "issued_mode_coefficients"
    )
    main_applied = _control_array(
        control_trace, "applied_command_mode_coefficients"
    )
    preview_issued = np.asarray(
        [row.get("issued_mode_coefficients", [0.0] * N_MODES) for row in preview_trace],
        dtype=float,
    )
    terminal_issued = np.asarray(
        [row.get("issued_mode_coefficients", [0.0] * N_MODES) for row in terminal_trace],
        dtype=float,
    )
    terminal_applied = np.asarray(
        [row.get("applied_mode_coefficients", [0.0] * N_MODES) for row in terminal_trace],
        dtype=float,
    )
    row = {
        "experiment_id": result.get("experiment_id"),
        "phase": phase,
        "scenario": spec.get("scenario"),
        "target_id": spec.get("target_id"),
        "policy_id": spec.get("terminal_policy_id"),
        "controller_variant": spec.get("controller_variant"),
        "actual_action_delay_steps": spec.get("action_delay_steps"),
        "controller_action_delay_steps": spec.get("controller_action_delay_steps"),
        "actual_slew_scale": spec.get("slew_scale"),
        "controller_slew_scale_estimate": spec.get(
            "controller_slew_scale_estimate"
        ),
        "calibration_token": spec.get("calibration_token"),
        "trusted_calibration_model": bool(
            spec.get("trusted_calibration_model", False)
        ),
        "success": bool(result.get("success")),
        "failure_reason": result.get("failure_reason", ""),
        "terminal_template_step": spec.get("terminal_template_step"),
        "terminal_controller_scale": spec.get("terminal_controller_scale"),
        "terminal_velocity_measurement_gain": spec.get(
            "terminal_velocity_measurement_gain"
        ),
        "terminal_position_measurement_gain": spec.get(
            "terminal_position_measurement_gain"
        ),
        "preview_replacement_count": transition.get(
            "preview_replacement_count"
        ),
        "expected_preview_replacement_count": transition.get(
            "expected_preview_replacement_count"
        ),
        "preview_issue_indices": transition.get("preview_issue_indices"),
        "preview_uses_only_issue_time_information": transition.get(
            "uses_only_original_issue_time_information"
        ),
        "preview_original_applied_commands_preserved": transition.get(
            "all_original_applied_commands_preserved"
        ),
        "preview_initial_queue_consistent": transition.get(
            "initial_preview_queue_consistent"
        ),
        "maximum_preview_desired_physical_norm": transition.get(
            "maximum_preview_desired_physical_norm"
        ),
        "continuous_streaming_queue": bool(
            terminal.get("continuous_streaming_queue", False)
        ),
        "streaming_queue_consistent": bool(
            terminal.get("streaming_queue_consistent", False)
        ),
        "pending_queue_bypassed": bool(
            terminal.get("pending_queue_bypassed", True)
        ),
        "final_pending_count": terminal.get("final_pending_count"),
        "maximum_final_pending_desired_physical_norm": terminal.get(
            "maximum_final_pending_desired_physical_norm"
        ),
        "last10_issued_desired_rms": last10_issued_rms,
        "last10_speed_rms_m_per_s": last10_speed_rms,
        "last10_box_max_error_m": last10_box,
        "tail_box_max_error_m": tail_box,
        "convergence_margins": convergence_margins,
        "convergence_guard_pass": convergence_pass,
        "prefix_guard_pass": prefix_pass,
        "preview_guard_pass": preview_pass,
        "queue_guard_pass": queue_pass,
        "first_350ms_physics_prefix_exact": bool(prefix.get("physics_exact")),
        "first_350ms_applied_prefix_exact": bool(prefix.get("applied_exact")),
        "original_issued_prefix_exact": bool(prefix.get("original_issued_exact")),
        "pre_preview_issued_prefix_exact": bool(
            prefix.get("pre_preview_issued_exact")
        ),
        "issued_changes_confined_to_preview_slots": bool(
            prefix.get("changes_confined_to_preview_slots")
        ),
        "changed_issued_indices": prefix.get("changed_issued_indices"),
        "expected_preview_rows": prefix.get("expected_preview_rows"),
        "prefix_max_abs_difference": prefix.get("maximum_abs_difference"),
        "r10_target_tracking_pass": r10_pass,
        "r10_combined_minimum_signed_margin": combined_margin,
        "physics_signature": _array_digest(physics, "physics"),
        "main_issued_signature": _array_digest(main_issued, "mainissued"),
        "original_main_issued_signature": _array_digest(
            original_issued, "originalmainissued"
        ),
        "main_applied_signature": _array_digest(main_applied, "mainapplied"),
        "preview_issued_signature": _array_digest(
            preview_issued, "previewissued"
        ),
        "terminal_issued_signature": _array_digest(
            terminal_issued, "terminalissued"
        ),
        "terminal_applied_signature": _array_digest(
            terminal_applied, "terminalapplied"
        ),
        "n_trajectory_steps": len(trajectory),
        "full_action_rms": (
            float(np.sqrt(np.mean(full_actions**2)))
            if full_actions.size
            else 0.0
        ),
        "terminal_action_rms": (
            float(np.sqrt(np.mean(terminal_actions**2)))
            if terminal_actions.size
            else 0.0
        ),
        "wall_time_s": result.get("wall_time_s"),
        **metrics,
    }
    return _json_safe(row)


def _expected_case_keys(
    targets: Sequence[Mapping[str, Any]],
) -> set[tuple[str, int, float]]:
    return {
        (str(target["target_id"]), delay, slew)
        for target in targets
        for delay in (0, 1, 2)
        for slew in (0.9, 1.0, 1.1)
    }


def build_oracle_development_specs(
    ctx: Stage41R10Context,
) -> list[dict[str, Any]]:
    terminal = ctx.cfg["terminal_transition"]
    target = terminal["development_target"]
    source_scale = float(
        ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )
    specs: list[dict[str, Any]] = []
    for slew in terminal["actual_slew_scales"]:
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(slew),
            horizon_steps=int(terminal["horizon_steps"]),
        )
        for delay in terminal["actual_delay_steps"]:
            for policy in terminal["candidate_bank"]:
                extra = _main_extra(
                    ctx,
                    actual_delay=int(delay),
                    actual_slew=float(slew),
                    modeled_delay=int(delay),
                    modeled_slew=float(slew),
                    policy=policy,
                    calibration_token=None,
                    trusted=True,
                    controller_variant="r10_oracle_development",
                )
                specs.append(
                    _make_spec(
                        phase="oracle_development",
                        scenario=(
                            f"{policy['policy_id']}__{target['target_id']}"
                            f"__d{delay}__s{float(slew):.1f}"
                        ),
                        category="oracle_development",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra=extra,
                    )
                )
    return specs


def _policy_summary(
    ctx: Stage41R10Context,
    rows: Sequence[Mapping[str, Any]],
    *,
    policy_id: str,
    expected_target_id: str,
) -> dict[str, Any]:
    subset = [row for row in rows if str(row.get("policy_id")) == policy_id]
    observed = {
        (
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in subset
    }
    expected = {(delay, slew) for delay in (0, 1, 2) for slew in (0.9, 1.0, 1.1)}
    coverage = (
        len(subset) == len(expected)
        and observed == expected
        and all(str(row.get("target_id")) == expected_target_id for row in subset)
    )
    tracking_fraction = sum(
        bool(row.get("r10_target_tracking_pass")) for row in subset
    ) / max(len(subset), 1)
    minimum_margin = min(
        (
            _as_float(row.get("r10_combined_minimum_signed_margin"), -1e12)
            for row in subset
        ),
        default=-1e12,
    )
    minimum_tracking_margin = min(
        (
            _as_float(
                row.get("stage3_4_tracking_minimum_signed_margin"), -1e12
            )
            for row in subset
        ),
        default=-1e12,
    )
    mean_margin = sum(
        _as_float(row.get("r10_combined_minimum_signed_margin"), -1e12)
        for row in subset
    ) / max(len(subset), 1)
    all_environment_success = bool(
        subset and all(bool(row.get("success")) for row in subset)
    )
    all_prefix = bool(
        subset and all(bool(row.get("prefix_guard_pass")) for row in subset)
    )
    all_preview = bool(
        subset and all(bool(row.get("preview_guard_pass")) for row in subset)
    )
    all_queue = bool(
        subset and all(bool(row.get("queue_guard_pass")) for row in subset)
    )
    all_convergence = bool(
        subset and all(bool(row.get("convergence_guard_pass")) for row in subset)
    )
    terminal_action_rms = sum(
        _as_float(row.get("terminal_action_rms"), math.inf) for row in subset
    ) / max(len(subset), 1)
    passed = bool(
        coverage
        and all_environment_success
        and tracking_fraction
        >= float(ctx.cfg["terminal_transition"]["minimum_tracking_fraction"])
        and minimum_margin
        >= float(ctx.cfg["terminal_transition"]["minimum_signed_margin"])
        and all_prefix
        and all_preview
        and all_queue
        and all_convergence
    )
    return {
        "policy_id": policy_id,
        "n_rollouts": len(subset),
        "coverage_complete": coverage,
        "all_environment_success": all_environment_success,
        "tracking_fraction": tracking_fraction,
        "minimum_combined_signed_margin": minimum_margin,
        "minimum_tracking_signed_margin": minimum_tracking_margin,
        "mean_combined_signed_margin": mean_margin,
        "all_prefix_guards_pass": all_prefix,
        "all_preview_guards_pass": all_preview,
        "all_streaming_queue_guards_pass": all_queue,
        "all_convergence_guards_pass": all_convergence,
        "maximum_preview_desired_physical_norm": max(
            (
                _as_float(
                    row.get("maximum_preview_desired_physical_norm"), 0.0
                )
                for row in subset
            ),
            default=0.0,
        ),
        "maximum_final_pending_desired_physical_norm": max(
            (
                _as_float(
                    row.get(
                        "maximum_final_pending_desired_physical_norm"
                    ),
                    0.0,
                )
                for row in subset
            ),
            default=0.0,
        ),
        "maximum_last10_speed_rms_m_per_s": max(
            (
                _as_float(row.get("last10_speed_rms_m_per_s"), math.inf)
                for row in subset
            ),
            default=math.inf,
        ),
        "maximum_last10_box_error_m": max(
            (
                _as_float(row.get("last10_box_max_error_m"), math.inf)
                for row in subset
            ),
            default=math.inf,
        ),
        "mean_terminal_action_rms": terminal_action_rms,
        "passed": passed,
    }


def summarize_oracle_development(
    ctx: Stage41R10Context, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    terminal = ctx.cfg["terminal_transition"]
    target_id = str(terminal["development_target"]["target_id"])
    summaries = [
        _policy_summary(
            ctx,
            rows,
            policy_id=str(policy["policy_id"]),
            expected_target_id=target_id,
        )
        for policy in terminal["candidate_bank"]
    ]
    passing = [row for row in summaries if bool(row.get("passed"))]
    selected = None
    if passing:
        selected = max(
            passing,
            key=lambda row: (
                _as_float(row.get("minimum_combined_signed_margin"), -1e12),
                _as_float(row.get("minimum_tracking_signed_margin"), -1e12),
                _as_float(row.get("mean_combined_signed_margin"), -1e12),
                -_as_float(row.get("mean_terminal_action_rms"), math.inf),
            ),
        )
    coverage = len(rows) == 54 and len({row.get("experiment_id") for row in rows}) == 54
    passed = bool(coverage and selected is not None)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "oracle_development",
        "development_target_id": target_id,
        "holdout_target_id": terminal["holdout_target"]["target_id"],
        "candidate_selection_uses_holdout": False,
        "n_rollouts": len(rows),
        "expected_rollouts": 54,
        "coverage_complete": coverage,
        "policy_summaries": summaries,
        "selected_policy_id": None if selected is None else selected["policy_id"],
        "selected_policy_minimum_combined_signed_margin": (
            None
            if selected is None
            else selected["minimum_combined_signed_margin"]
        ),
        "passed": passed,
    }


def run_oracle_development(
    ctx: Stage41R10Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_oracle_development_specs(ctx)
    raw_dir = ctx.paths.oracle_development / "raw"
    results = evaluate_specs(
        ctx, specs, output_dir=raw_dir, backend=backend, resume=resume
    )
    rows = [
        feedback_result_row(ctx, result, phase="oracle_development")
        for result in results
    ]
    summary = summarize_oracle_development(ctx, rows)
    atomic_write_json(ctx.paths.oracle_development / "results.json", rows)
    atomic_write_json(ctx.paths.oracle_development / "summary.json", summary)
    write_csv(ctx.paths.oracle_development / "results.csv", rows)
    _update_state(
        ctx,
        oracle_development_complete=True,
        oracle_development_summary=summary,
    )
    return summary


def _selected_policy(ctx: Stage41R10Context) -> dict[str, Any] | None:
    path = ctx.paths.oracle_development / "summary.json"
    if not path.is_file():
        return None
    summary = read_json(path)
    policy_id = summary.get("selected_policy_id")
    if not policy_id:
        return None
    return _policy_lookup(ctx).get(str(policy_id))


def build_oracle_holdout_specs(
    ctx: Stage41R10Context,
) -> list[dict[str, Any]]:
    policy = _selected_policy(ctx)
    development_summary = (
        read_json(ctx.paths.oracle_development / "summary.json")
        if (ctx.paths.oracle_development / "summary.json").is_file()
        else {}
    )
    if policy is None or not bool(development_summary.get("passed")):
        return []
    terminal = ctx.cfg["terminal_transition"]
    target = terminal["holdout_target"]
    source_scale = float(
        ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )
    specs: list[dict[str, Any]] = []
    for slew in terminal["actual_slew_scales"]:
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(slew),
            horizon_steps=int(terminal["horizon_steps"]),
        )
        for delay in terminal["actual_delay_steps"]:
            extra = _main_extra(
                ctx,
                actual_delay=int(delay),
                actual_slew=float(slew),
                modeled_delay=int(delay),
                modeled_slew=float(slew),
                policy=policy,
                calibration_token=None,
                trusted=True,
                controller_variant="r10_oracle_holdout",
            )
            specs.append(
                _make_spec(
                    phase="oracle_holdout",
                    scenario=(
                        f"{policy['policy_id']}__{target['target_id']}"
                        f"__d{delay}__s{float(slew):.1f}"
                    ),
                    category="oracle_holdout",
                    target=target,
                    controller_scale=source_scale,
                    environment_variant=variant_id,
                    extra=extra,
                )
            )
    return specs


def summarize_oracle_holdout(
    ctx: Stage41R10Context, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    policy = _selected_policy(ctx)
    if policy is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "oracle_holdout",
            "status": "not_run_no_development_policy",
            "passed": False,
        }
    target_id = str(
        ctx.cfg["terminal_transition"]["holdout_target"]["target_id"]
    )
    policy_summary = _policy_summary(
        ctx,
        rows,
        policy_id=str(policy["policy_id"]),
        expected_target_id=target_id,
    )
    expected = {(target_id, delay, slew) for delay in (0, 1, 2) for slew in (0.9, 1.0, 1.1)}
    observed = {
        (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in rows
    }
    coverage = len(rows) == 9 and observed == expected
    passed = bool(coverage and policy_summary.get("passed"))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "oracle_holdout",
        "selected_policy_id": policy["policy_id"],
        "holdout_target_id": target_id,
        "holdout_was_not_used_for_policy_selection": True,
        "n_rollouts": len(rows),
        "expected_rollouts": 9,
        "coverage_complete": coverage,
        "policy_summary": policy_summary,
        "passed": passed,
    }


def run_oracle_holdout(
    ctx: Stage41R10Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_oracle_holdout_specs(ctx)
    if not specs:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "oracle_holdout",
            "status": "not_run_oracle_development_not_closed",
            "passed": False,
        }
        atomic_write_json(ctx.paths.oracle_holdout / "summary.json", summary)
        _update_state(
            ctx,
            oracle_holdout_complete=False,
            oracle_holdout_summary=summary,
        )
        return summary
    raw_dir = ctx.paths.oracle_holdout / "raw"
    results = evaluate_specs(
        ctx, specs, output_dir=raw_dir, backend=backend, resume=resume
    )
    rows = [
        feedback_result_row(ctx, result, phase="oracle_holdout")
        for result in results
    ]
    summary = summarize_oracle_holdout(ctx, rows)
    atomic_write_json(ctx.paths.oracle_holdout / "results.json", rows)
    atomic_write_json(ctx.paths.oracle_holdout / "summary.json", summary)
    write_csv(ctx.paths.oracle_holdout / "results.csv", rows)
    _update_state(
        ctx,
        oracle_holdout_complete=True,
        oracle_holdout_summary=summary,
    )
    return summary


def _oracle_rows_by_case(
    ctx: Stage41R10Context,
) -> dict[tuple[str, int, float], dict[str, Any]]:
    policy = _selected_policy(ctx)
    if policy is None:
        return {}
    policy_id = str(policy["policy_id"])
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for phase_dir in (ctx.paths.oracle_development, ctx.paths.oracle_holdout):
        path = phase_dir / "results.json"
        if not path.is_file():
            continue
        for row in read_json(path):
            if str(row.get("policy_id")) != policy_id:
                continue
            key = (
                str(row["target_id"]),
                int(row["actual_action_delay_steps"]),
                float(row["actual_slew_scale"]),
            )
            if key in output:
                raise ValueError(f"duplicate R10 Oracle row for {key}")
            output[key] = row
    return output


def _oracle_raw_path_for_row(
    ctx: Stage41R10Context, row: Mapping[str, Any]
) -> Path:
    phase = str(row.get("phase"))
    if phase == "oracle_development":
        root = ctx.paths.oracle_development
    elif phase == "oracle_holdout":
        root = ctx.paths.oracle_holdout
    else:
        raise ValueError(f"unsupported Oracle phase {phase!r}")
    return root / "raw" / f"{row['experiment_id']}.json.gz"


def build_calibrated_confirmation_specs(
    ctx: Stage41R10Context,
) -> list[dict[str, Any]]:
    policy = _selected_policy(ctx)
    holdout_path = ctx.paths.oracle_holdout / "summary.json"
    holdout = read_json(holdout_path) if holdout_path.is_file() else {}
    if policy is None or not bool(holdout.get("passed")):
        return []
    terminal = ctx.cfg["terminal_transition"]
    confirmation = ctx.cfg["calibrated_confirmation"]
    tokens = r9.source_calibration_tokens(ctx.r9_ctx)
    source_scale = float(
        ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )
    specs: list[dict[str, Any]] = []
    for slew in terminal["actual_slew_scales"]:
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(slew),
            horizon_steps=int(terminal["horizon_steps"]),
        )
        for delay in terminal["actual_delay_steps"]:
            token = tokens.get((int(delay), float(slew)))
            if token is None:
                raise ValueError(f"missing R8 calibration token {(delay, slew)}")
            trusted = bool(
                token.get("success")
                and token.get("batch_trusted")
                and token.get("batch_trusted_correct")
                and not token.get("batch_wrong_accept")
            )
            if not trusted:
                raise RuntimeError(
                    "untrusted Stage4.1R8 calibration token cannot start R10 "
                    f"control: delay={delay} slew={slew}"
                )
            modeled_delay = int(token["batch_selected_delay_steps"])
            modeled_slew = float(token["batch_selected_slew_scale"])
            if modeled_delay != int(delay) or not math.isclose(
                modeled_slew, float(slew), abs_tol=1e-12
            ):
                raise RuntimeError(
                    "trusted R8 token does not match actual finite-envelope pair: "
                    f"actual=({delay}, {slew}) selected=({modeled_delay}, {modeled_slew})"
                )
            for target in confirmation["targets"]:
                extra = _main_extra(
                    ctx,
                    actual_delay=int(delay),
                    actual_slew=float(slew),
                    modeled_delay=modeled_delay,
                    modeled_slew=modeled_slew,
                    policy=policy,
                    calibration_token=str(token["experiment_id"]),
                    trusted=True,
                    controller_variant="r10_calibrated_confirmation",
                )
                specs.append(
                    _make_spec(
                        phase="calibrated_confirmation",
                        scenario=(
                            f"{policy['policy_id']}__{target['target_id']}"
                            f"__d{delay}__s{float(slew):.1f}"
                        ),
                        category="calibrated_confirmation",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra=extra,
                    )
                )
    return specs


def _full_trace_arrays(
    result: Mapping[str, Any]
) -> dict[str, np.ndarray]:
    return {
        "physics": _physics_array(result),
        "main_issued": _control_array(
            list(result.get("control_trace") or []),
            "issued_mode_coefficients",
        ),
        "main_applied": _control_array(
            list(result.get("control_trace") or []),
            "applied_command_mode_coefficients",
        ),
        "original_main_issued": _control_array(
            list(result.get("original_main_control_trace") or []),
            "issued_mode_coefficients",
        ),
        "preview_issued": np.asarray(
            [
                row.get("issued_mode_coefficients", [0.0] * N_MODES)
                for row in (result.get("transition_preview_trace") or [])
            ],
            dtype=float,
        ),
        "preview_applied": np.asarray(
            [
                row.get("applied_mode_coefficients", [0.0] * N_MODES)
                for row in (result.get("transition_preview_trace") or [])
            ],
            dtype=float,
        ),
        "terminal_issued": np.asarray(
            [
                row.get("issued_mode_coefficients", [0.0] * N_MODES)
                for row in (result.get("terminal_feedback_trace") or [])
            ],
            dtype=float,
        ),
        "terminal_applied": np.asarray(
            [
                row.get("applied_mode_coefficients", [0.0] * N_MODES)
                for row in (result.get("terminal_feedback_trace") or [])
            ],
            dtype=float,
        ),
    }


def _compare_full_results(
    left: Mapping[str, Any], right: Mapping[str, Any], *, atol: float
) -> dict[str, Any]:
    left_arrays = _full_trace_arrays(left)
    right_arrays = _full_trace_arrays(right)
    exact = True
    numeric = True
    maxima: dict[str, float] = {}
    for name in left_arrays:
        a = left_arrays[name]
        b = right_arrays[name]
        if a.shape != b.shape:
            exact = False
            numeric = False
            maxima[name] = math.inf
            continue
        maxima[name] = float(np.max(np.abs(a - b))) if a.size else 0.0
        exact = bool(exact and np.array_equal(a, b))
        numeric = bool(
            numeric
            and np.allclose(a, b, rtol=0.0, atol=float(atol), equal_nan=False)
        )
    return {
        "exact_equal": exact,
        "numeric_equal": numeric,
        "max_abs_difference": max(maxima.values(), default=0.0),
        "component_max_abs_difference": maxima,
    }


def _full_trace_comparison(
    ctx: Stage41R10Context,
    calibrated_row: Mapping[str, Any],
    oracle_row: Mapping[str, Any] | None,
    *,
    atol: float,
) -> dict[str, Any]:
    calibrated_path = (
        ctx.paths.calibrated_confirmation
        / "raw"
        / f"{calibrated_row['experiment_id']}.json.gz"
    )
    if oracle_row is None:
        return {
            "raw_files_available": False,
            "exact_equal": False,
            "numeric_equal": False,
            "max_abs_difference": math.inf,
        }
    oracle_path = _oracle_raw_path_for_row(ctx, oracle_row)
    if not calibrated_path.is_file() or not oracle_path.is_file():
        return {
            "raw_files_available": False,
            "exact_equal": False,
            "numeric_equal": False,
            "max_abs_difference": math.inf,
        }
    comparison = _compare_full_results(
        read_json_gz(calibrated_path),
        read_json_gz(oracle_path),
        atol=atol,
    )
    comparison["raw_files_available"] = True
    return comparison


def summarize_calibrated_confirmation(
    ctx: Stage41R10Context, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    cfg = ctx.cfg["calibrated_confirmation"]
    expected = _expected_case_keys(cfg["targets"])
    observed = {
        (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in rows
    }
    oracle = _oracle_rows_by_case(ctx)
    atol = float(cfg["numeric_trace_equivalence_atol"])
    comparisons: list[dict[str, Any]] = []
    for row in rows:
        key = (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        oracle_row = oracle.get(key)
        comparison = _full_trace_comparison(
            ctx, row, oracle_row, atol=atol
        )
        comparisons.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "exact_trace_equal_to_oracle": bool(
                    comparison.get("exact_equal", False)
                ),
                "numeric_trace_equal_to_oracle": bool(
                    comparison.get("numeric_equal", False)
                ),
                "maximum_trace_abs_difference": comparison.get(
                    "max_abs_difference", math.inf
                ),
                "component_max_abs_difference": comparison.get(
                    "component_max_abs_difference", {}
                ),
                "calibrated_combined_margin": row.get(
                    "r10_combined_minimum_signed_margin"
                ),
                "oracle_combined_margin": (
                    None
                    if oracle_row is None
                    else oracle_row.get("r10_combined_minimum_signed_margin")
                ),
            }
        )
    coverage = len(rows) == len(expected) and observed == expected
    exact_fraction = sum(
        bool(row["exact_trace_equal_to_oracle"]) for row in comparisons
    ) / max(len(comparisons), 1)
    numeric_fraction = sum(
        bool(row["numeric_trace_equal_to_oracle"]) for row in comparisons
    ) / max(len(comparisons), 1)
    tokens = {
        str(row.get("calibration_token"))
        for row in rows
        if row.get("calibration_token")
    }
    untrusted = sum(
        not bool(row.get("trusted_calibration_model")) for row in rows
    )
    passed = bool(
        coverage
        and len(oracle) == len(expected)
        and len(tokens) == 9
        and untrusted == 0
        and all(bool(row.get("success")) for row in rows)
        and all(bool(row.get("r10_target_tracking_pass")) for row in rows)
        and exact_fraction
        >= float(cfg["minimum_trace_equivalence_fraction"])
        and numeric_fraction >= 1.0 - 1e-12
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "calibrated_confirmation",
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected),
        "coverage_complete": coverage,
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "tracking_pass_fraction": sum(
            bool(row.get("r10_target_tracking_pass")) for row in rows
        )
        / max(len(rows), 1),
        "distinct_calibration_tokens": len(tokens),
        "untrusted_main_start_count": untrusted,
        "exact_trace_equivalence_fraction": exact_fraction,
        "numeric_trace_equivalence_fraction": numeric_fraction,
        "numeric_trace_equivalence_atol": atol,
        "maximum_trace_abs_difference": max(
            (
                _as_float(row.get("maximum_trace_abs_difference"), math.inf)
                for row in comparisons
            ),
            default=math.inf,
        ),
        "comparisons": comparisons,
        "passed": passed,
    }


def run_calibrated_confirmation(
    ctx: Stage41R10Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_calibrated_confirmation_specs(ctx)
    if not specs:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "calibrated_confirmation",
            "status": "not_run_oracle_holdout_not_closed",
            "passed": False,
        }
        atomic_write_json(
            ctx.paths.calibrated_confirmation / "summary.json", summary
        )
        _update_state(
            ctx,
            calibrated_confirmation_complete=False,
            calibrated_confirmation_summary=summary,
        )
        return summary
    raw_dir = ctx.paths.calibrated_confirmation / "raw"
    results = evaluate_specs(
        ctx, specs, output_dir=raw_dir, backend=backend, resume=resume
    )
    rows = [
        feedback_result_row(ctx, result, phase="calibrated_confirmation")
        for result in results
    ]
    summary = summarize_calibrated_confirmation(ctx, rows)
    atomic_write_json(
        ctx.paths.calibrated_confirmation / "results.json", rows
    )
    atomic_write_json(
        ctx.paths.calibrated_confirmation / "summary.json", summary
    )
    write_csv(ctx.paths.calibrated_confirmation / "results.csv", rows)
    _update_state(
        ctx,
        calibrated_confirmation_complete=True,
        calibrated_confirmation_summary=summary,
    )
    return summary


# ---------------------------------------------------------------------------
# Restart availability audit and verdict
# ---------------------------------------------------------------------------


def run_restart_audit(ctx: Stage41R10Context) -> dict[str, Any]:
    folders = [str(value) for value in ctx.cfg["restart_audit"]["candidate_folders"]]
    available: list[str] = []
    roots = {
        ctx.source_stage41r9_run,
        ctx.source_stage41r8_run,
        ctx.r9_ctx.source_stage41r7_run,
        ctx.project_dir,
    }
    for name in folders:
        found = False
        for root in roots:
            for candidate in (
                root / name,
                root / "restart" / name,
                root / "restarts" / name,
            ):
                if candidate.is_dir():
                    found = True
                    break
            if found:
                break
        if found:
            available.append(name)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_audit",
        "candidate_folders": folders,
        "available_folders": available,
        "true_restart_validation_available": len(available)
        >= int(ctx.cfg["restart_audit"]["minimum_distinct_folders"]),
        "true_restart_validation_performed": False,
        "availability_requirement_for_stage4_1r10": False,
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


def analyze(ctx: Stage41R10Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    development = state.get("oracle_development_summary") or {}
    holdout = state.get("oracle_holdout_summary") or {}
    confirmation = state.get("calibrated_confirmation_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    primary_pass = bool(
        source.get("passed")
        and development.get("passed")
        and holdout.get("passed")
        and confirmation.get("passed")
    )
    verdict = (
        "STAGE4_1R10_FINITE_QUEUE_PREVIEW_TERMINAL_TRANSITION_HOLD_CLOSURE"
        if primary_pass
        else "STAGE4_1R10_QUEUE_PREVIEW_TERMINAL_TRANSITION_HOLD_INCOMPLETE"
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r9_run": str(ctx.source_stage41r9_run),
        "source_audit_status": _phase_status(
            state, "source_audit_complete", "source_audit_summary"
        ),
        "oracle_development_status": _phase_status(
            state,
            "oracle_development_complete",
            "oracle_development_summary",
        ),
        "oracle_holdout_status": _phase_status(
            state, "oracle_holdout_complete", "oracle_holdout_summary"
        ),
        "calibrated_confirmation_status": _phase_status(
            state,
            "calibrated_confirmation_complete",
            "calibrated_confirmation_summary",
        ),
        "selected_terminal_policy": development.get("selected_policy_id"),
        "finite_queue_preview_terminal_envelope_validated": primary_pass,
        "physical_prefix_through_350ms_frozen": True,
        "applied_command_prefix_through_350ms_frozen": True,
        "issued_prefix_changed_only_in_unapplied_slots": True,
        "causal_original_issue_time_preview_used": True,
        "continuous_streaming_delay_queue_used": True,
        "tracking_gate_weakened": False,
        "untrusted_default_main_start_allowed": False,
        "candidate_selection_target": ctx.cfg["terminal_transition"]
        ["development_target"]["target_id"],
        "disjoint_holdout_target": ctx.cfg["terminal_transition"]
        ["holdout_target"]["target_id"],
        "terminal_measurement_noise_robustness_validated": False,
        "true_restart_validation_available": bool(
            restart.get("true_restart_validation_available", False)
        ),
        "true_restart_validation_performed": False,
        "hardware_pre_shot_calibration_validated": False,
        "continuous_parameter_change_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "finite_test_envelope_only": True,
        "warning": (
            "R10 can only test a causal queue-boundary preview and clean terminal "
            "feedback inside the same finite static digital twin. It does not "
            "validate true restart state, hidden vessel/eddy history, continuous "
            "actuator changes, plant-model error, noisy sensing, or hardware deployment."
        ),
        "next_if_pass": (
            "Proceed to Stage4.2 true restart and plant/actuator-parameter robustness. "
            "Do not start BC/DAgger/RL yet."
        ),
        "next_if_fail": (
            "If the complete R10 Oracle development campaign fails, the queue-boundary "
            "artifact has been isolated and bounded terminal local-model identification "
            "is then justified. Redesign the terminal regulator without weakening the "
            "30 mm/0.1 m/s gates and without handing 14-coil control back to RL."
        ),
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "oracle_development": development,
            "oracle_holdout": holdout,
            "calibrated_confirmation": confirmation,
            "restart_audit": restart,
        },
    }
    verdict_payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": verdict,
        "primary_pass": primary_pass,
        "selected_terminal_policy": development.get("selected_policy_id"),
        "next_if_pass": summary["next_if_pass"],
        "next_if_fail": summary["next_if_fail"],
        "final_task": ctx.cfg["final_task"],
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r10_summary.json", summary)
    atomic_write_json(
        ctx.paths.analysis / "stage4_1r10_verdict.json", verdict_payload
    )
    _update_state(
        ctx,
        finished=True,
        stop_reason="" if primary_pass else state.get("stop_reason", ""),
        verdict=verdict,
    )
    return summary


def execute(
    ctx: Stage41R10Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepared = prepare(ctx)
    if command == "prepare":
        return prepared
    source = run_source_audit(ctx)
    if command == "audit":
        return source
    if not source.get("passed"):
        _update_state(ctx, finished=True, stop_reason="source_audit_failed")
        run_restart_audit(ctx)
        return analyze(ctx)
    if command in {"all", "oracle"}:
        development = run_oracle_development(ctx, backend=backend, resume=resume)
        if command == "oracle" and not development.get("passed"):
            return development
        if not development.get("passed"):
            _update_state(
                ctx, finished=True, stop_reason="oracle_development_failed"
            )
            run_restart_audit(ctx)
            return analyze(ctx)
        holdout = run_oracle_holdout(ctx, backend=backend, resume=resume)
        if command == "oracle":
            return holdout
        if not holdout.get("passed"):
            _update_state(ctx, finished=True, stop_reason="oracle_holdout_failed")
            run_restart_audit(ctx)
            return analyze(ctx)
    if command in {"all", "startup"}:
        confirmation = run_calibrated_confirmation(
            ctx, backend=backend, resume=resume
        )
        if command == "startup":
            return confirmation
        if not confirmation.get("passed"):
            _update_state(
                ctx,
                finished=True,
                stop_reason="calibrated_confirmation_failed",
            )
    run_restart_audit(ctx)
    return analyze(ctx)


# ---------------------------------------------------------------------------
# Self-test and CLI
# ---------------------------------------------------------------------------


def self_test() -> dict[str, Any]:
    control = []
    for index in range(MAIN_CONTROL_STEPS):
        control.append(
            {
                "issued_mode_coefficients": [
                    float(index),
                    -float(index),
                    0.1 * index,
                ],
                "issued_desired_physical_mode_coefficients": [
                    0.01 * index,
                    -0.01 * index,
                    0.001 * index,
                ],
                "applied_command_mode_coefficients": [
                    float(index - 2),
                    -float(index - 2),
                    0.1 * (index - 2),
                ],
                "mode_correction_physical": [0.0, 0.0, 0.0],
            }
        )
    queue, preview_indices = _initial_preview_queue(control, 2)
    issued33 = {
        "origin": "terminal_preview",
        "origin_index": 33,
        "command": np.asarray([100.0, 0.0, 0.0]),
        "desired_physical": np.asarray([1.0, 0.0, 0.0]),
    }
    applied33, queue = _stream_queue_apply(queue, issued33, 2)
    issued34 = {
        "origin": "terminal_preview",
        "origin_index": 34,
        "command": np.asarray([200.0, 0.0, 0.0]),
        "desired_physical": np.asarray([2.0, 0.0, 0.0]),
    }
    applied34, queue = _stream_queue_apply(queue, issued34, 2)
    queue_ok = bool(
        preview_indices == [33, 34]
        and (applied33["origin"], applied33["origin_index"])
        == ("main_control", 31)
        and (applied34["origin"], applied34["origin_index"])
        == ("main_control", 32)
        and [item["origin_index"] for item in queue] == [33, 34]
        and all(item["origin"] == "terminal_preview" for item in queue)
    )
    trajectory = [
        {"R": 1.0, "Z": -1.0, "Ip": 100.0},
        {"R": 1.001, "Z": -1.002, "Ip": 102.0},
        {"R": 1.002, "Z": -1.003, "Ip": 103.0},
    ]
    measurement = _terminal_measurement_at_issue(
        trajectory,
        issue_step=2,
        target=np.asarray([1.0, -1.0, 100.0]),
        dt_s=0.01,
    )
    measurement_ok = bool(
        np.allclose(measurement, [0.002, -0.003, 0.1, -0.1, 3.0])
    )
    config_path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "stage4_1r10_queue_preview_terminal_transition_hold_750ms.json"
    )
    config_ok = False
    if config_path.is_file():
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        validate_config(cfg)
        config_ok = bool(
            cfg["terminal_transition"]["horizon_steps"] == 75
            and len(cfg["terminal_transition"]["candidate_bank"]) == 6
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "package_revision": PACKAGE_REVISION,
        "causal_preview_queue_semantics_passed": queue_ok,
        "original_issue_time_measurement_passed": measurement_ok,
        "config_guardrails_passed": config_ok,
        "passed": bool(queue_ok and measurement_ok and config_ok),
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R10 causal queue-preview terminal transition hold"
    )
    parser.add_argument(
        "--config",
        default=(
            "configs/"
            "stage4_1r10_queue_preview_terminal_transition_hold_750ms.json"
        ),
    )
    parser.add_argument("--source-stage4-1r9-run")
    parser.add_argument("--run-dir")
    parser.add_argument("--backend", choices=["ray", "serial"], default="ray")
    parser.add_argument(
        "--command",
        choices=[
            "all",
            "prepare",
            "audit",
            "oracle",
            "startup",
            "analyze",
        ],
        default="all",
    )
    parser.add_argument("--resume", dest="resume", action="store_true")
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.set_defaults(resume=False)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        payload = self_test()
        print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))
        if not payload["passed"]:
            raise SystemExit(1)
        return
    if not args.source_stage4_1r9_run:
        parser.error("--source-stage4-1r9-run is required")
    if not args.run_dir:
        parser.error("--run-dir is required")
    ctx = load_stage41r10_config(
        Path(args.config),
        source_stage41r9_run=Path(args.source_stage4_1r9_run),
        run_dir_override=Path(args.run_dir),
    )
    if args.command == "analyze":
        prepare(ctx)
        payload = analyze(ctx)
    else:
        payload = execute(
            ctx,
            command=args.command,
            backend=args.backend,
            resume=bool(args.resume),
        )
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
