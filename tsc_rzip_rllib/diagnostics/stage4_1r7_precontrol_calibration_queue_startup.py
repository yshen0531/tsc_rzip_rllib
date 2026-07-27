"""Stage4.1R7 pre-control calibration and queue-consistent startup closure.

This revision consumes a completed Stage4.1R6 run.  R6 established that the
finite delay/slew bank can identify the correct static actuator model and that
an exactly persistent model reproduces the Oracle controller, while its online
physical-blend handover and common-prefix cold start failed.  R7 therefore
changes the startup architecture instead of tuning the failed blend:

* identify integer delay and discrete slew in a separate, bounded sub-slew
  calibration episode;
* reset the TSC episode before the main plasma-control trajectory;
* prime the main action queue consistently with the calibrated model;
* start the frozen Stage3.4/Stage4.1R3 MPC from that model, with no online
  handover during the primary startup test;
* independently confirm the complete calibration -> reset -> control chain.

The calibration episode is a finite digital-twin POC for pre-shot/previous-shot
power-supply calibration.  It is not a hardware calibration qualification and
it does not validate true alternate plasma restart states.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import resource
import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as base
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage4_1r3_control_aware_robustness as r3
from tsc_rzip_rllib.diagnostics import stage4_1r4_targeted_closure as r4
from tsc_rzip_rllib.diagnostics import stage4_1r5_adaptive_handover_closure as r5
from tsc_rzip_rllib.diagnostics import stage4_1r6_startup_architecture_closure as r6
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

SCHEMA_VERSION = 1
STAGE = "Stage4.1R7"
CONTROLLER_REVISION = "precontrol_calibration_queue_consistent_startup_v7"
RUNTIME_BUGFIX_REVISION = "r7a_summary_null_coverage_guard_v1"
STARTUP_MONITOR_VARIANTS = frozenset({
    "r7_precalibrated_clean_monitor",
    "r7_precalibrated_noisy_monitor",
})
EXPECTED_SOURCE_STAGE = "Stage4.1R6"
EXPECTED_SOURCE_REVISION = "confidence_gated_persistent_prior_physical_handover_v6"
STATE_FILENAME = "stage4_1r7_state.json"
MANIFEST_FILENAME = "stage4_1r7_manifest.json"

# Reuse the strict JSON helpers that survived the prior campaigns.
utc_timestamp = r6.utc_timestamp
_json_safe = r6._json_safe
read_json = r6.read_json
read_json_gz = r6.read_json_gz
atomic_write_json = r6.atomic_write_json
atomic_write_json_gz = r6.atomic_write_json_gz
write_csv = r6.write_csv
read_csv = r6.read_csv
_as_bool = r6._as_bool
_as_float = r6._as_float
_as_int = r6._as_int
_sha256_file = r6._sha256_file
_result_complete = r6._result_complete


def _scenario_digest(*parts: Any, prefix: str = "s41r7") -> str:
    raw = json.dumps(_json_safe(parts), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:20]}"


def _array_digest(array: np.ndarray, prefix: str) -> str:
    arr = np.round(np.asarray(array, dtype=float), 12)
    return f"{prefix}_{hashlib.sha256(arr.tobytes()).hexdigest()[:20]}"


@dataclass(frozen=True)
class Stage41R7Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_audit: Path
    calibration: Path
    startup: Path
    restart: Path
    confirmation: Path
    analysis: Path
    variants: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R7Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_audit=run_dir / "stage4_1r7_source_audit",
            calibration=run_dir / "stage4_1r7_precontrol_calibration",
            startup=run_dir / "stage4_1r7_queue_consistent_startup",
            restart=run_dir / "stage4_1r7_restart_audit",
            confirmation=run_dir / "stage4_1r7_paired_confirmation",
            analysis=run_dir / "stage4_1r7_analysis",
            variants=run_dir / "stage4_1r7_environment_variants",
            source_reference=run_dir / "source_stage4_1r6_reference",
        )


@dataclass
class Stage41R7Context:
    cfg: dict[str, Any]
    paths: Stage41R7Paths
    project_dir: Path
    source_stage41r6_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_verdict: dict[str, Any]
    source_r6_cfg: dict[str, Any]
    source_stage41r5_run: Path
    r6_ctx: r6.Stage41R6Context
    source_fingerprint: dict[str, Any]


# ---------------------------------------------------------------------------
# Source/config/run setup
# ---------------------------------------------------------------------------


def resolve_source_stage41r6_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE4_1R6_RUN", "").strip()
    if not value:
        raise ValueError("Stage4.1R7 requires --source-stage4-1r6-run or SOURCE_STAGE4_1R6_RUN")
    run = Path(value).expanduser().resolve()
    required = [
        run / "stage4_1r6_manifest.json",
        run / "stage4_1r6_state.json",
        run / "stage4_1r6_config.resolved.json",
        run / "stage4_1r6_analysis/stage4_1r6_verdict.json",
        run / "stage4_1r6_estimator_confirmation/summary.json",
        run / "stage4_1r6_static_startup/summary.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage4.1R6 source run: " + ", ".join(missing))
    return run


def _resolve_source_r5(project_dir: Path, manifest: dict[str, Any]) -> Path:
    raw = str(manifest.get("source_stage4_1r5_run", "")).strip()
    if not raw:
        raise ValueError("Stage4.1R6 manifest has no source_stage4_1r5_run")
    path = Path(raw).expanduser()
    path = path.resolve() if path.is_absolute() else (project_dir / path).resolve()
    if not path.exists():
        fallback = project_dir / "stage4_1r5_runs" / path.name
        if fallback.exists():
            path = fallback.resolve()
    if not (path / "stage4_1r5_manifest.json").exists():
        raise FileNotFoundError(f"Stage4.1R5 source is unavailable: {path}")
    return path


def _source_inventory(source_r6: Path) -> dict[str, Any]:
    include = [
        source_r6 / "stage4_1r6_manifest.json",
        source_r6 / "stage4_1r6_state.json",
        source_r6 / "stage4_1r6_config.resolved.json",
        source_r6 / "stage4_1r6_analysis/stage4_1r6_verdict.json",
        source_r6 / "stage4_1r6_source_audit/summary.json",
        source_r6 / "stage4_1r6_estimator_confirmation/summary.json",
        source_r6 / "stage4_1r6_static_startup/summary.json",
    ]
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    total = 0
    for path in include:
        if not path.is_file():
            continue
        relative = str(path.relative_to(source_r6))
        sha = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"relative_path": relative, "sha256": sha, "bytes": size})
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        digest.update(sha.encode("ascii")); digest.update(b"\n")
        total += size
    return {"n_files": len(entries), "total_bytes": total, "digest": digest.hexdigest(), "entries": entries}


def _combined_source_inventory(source_r6: Path, r6_ctx: r6.Stage41R6Context) -> dict[str, Any]:
    """Fingerprint the R6 run and every inherited control-model source chain.

    R7 does not merely read the R6 verdict: its worker reconstructs the frozen
    Stage3.4 target library, Jacobian, controller scale, and all inherited
    environment/coil limits.  Resume integrity therefore includes the nested
    source fingerprints already computed by R6/R5/R4/R3/Stage3.4.
    """
    direct = _source_inventory(source_r6)
    chain_objects = [
        ("stage4_1r6_source_chain", r6_ctx.source_fingerprint),
        ("stage4_1r5_source_chain", r6_ctx.r5_ctx.source_fingerprint),
        ("stage4_1r4_source_chain", r6_ctx.r5_ctx.r4_ctx.source_fingerprint),
        ("stage4_1r3_source_chain", r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_fingerprint),
        ("stage3_4_source_chain", r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.source_fingerprint),
    ]
    chain: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    digest.update(str(direct["digest"]).encode("ascii"))
    digest.update(b"\n")
    for label, payload in chain_objects:
        item = {
            "label": label,
            "digest": str(payload.get("digest", "")),
            "n_files": int(payload.get("n_files", 0)),
            "total_bytes": int(payload.get("total_bytes", 0)),
        }
        if not item["digest"]:
            raise ValueError(f"missing inherited source fingerprint for {label}")
        chain.append(item)
        digest.update(label.encode("utf-8")); digest.update(b"\0")
        digest.update(item["digest"].encode("ascii")); digest.update(b"\n")
    return {
        "schema_version": 2,
        "n_files": int(direct["n_files"]),
        "total_bytes": int(direct["total_bytes"]),
        "direct_r6_digest": str(direct["digest"]),
        "digest": digest.hexdigest(),
        "entries": direct["entries"],
        "chain_fingerprints": chain,
    }


def validate_source(manifest: dict[str, Any], state: dict[str, Any]) -> None:
    if str(manifest.get("stage")) != EXPECTED_SOURCE_STAGE:
        raise ValueError(f"source stage must be {EXPECTED_SOURCE_STAGE}")
    if str(manifest.get("controller_revision")) != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R6 controller revision is unsupported")
    if not bool(state.get("finished", False)):
        raise ValueError("source Stage4.1R6 run is not finished")
    audit = state.get("source_audit_summary") or {}
    estimator = state.get("estimator_confirmation_summary") or {}
    startup = state.get("startup_summary") or {}
    if not bool(audit.get("passed", False)):
        raise ValueError("source Stage4.1R6 audit did not pass")
    if not bool(estimator.get("passed", False)):
        raise ValueError("source Stage4.1R6 confidence-gated estimator confirmation did not pass")
    if not math.isclose(
        float(startup.get("persistent_exact_preservation_fraction", math.nan)),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("source Stage4.1R6 did not preserve the exact persistent model")
    if not math.isclose(
        float(startup.get("persistent_exact_trace_equivalence_fraction", math.nan)),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("source Stage4.1R6 exact persistent trace was not Oracle-equivalent")


def validate_config(cfg: dict[str, Any], source_cfg: dict[str, Any]) -> None:
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R7 controller_revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.1R7 complete package is configured for 128 workers")
    for key in (
        "precise_tolerance_m", "relaxed_tolerance_m", "required_arrival_streak_steps",
        "terminal_velocity_max_m_per_s", "late_velocity_rms_max_m_per_s",
        "late_window_steps", "ip_safety_tolerance_A",
    ):
        if not math.isclose(float(cfg["gate"][key]), float(source_cfg["gate"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.1R7 hard gate {key} differs from source")
    for key in ("terminal_abs_tolerance_A", "hold_rms_tolerance_A", "sustained_max_tolerance_A"):
        if not math.isclose(
            float(cfg["gate"]["ip_tracking"][key]),
            float(source_cfg["gate"]["ip_tracking"][key]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"Stage4.1R7 Ip threshold {key} differs from source")
    plan = np.asarray(cfg["precontrol_calibration"]["mode_command_plan"], dtype=float)
    if plan.ndim != 2 or plan.shape[1] != 3 or len(plan) < 6:
        raise ValueError("precontrol_calibration.mode_command_plan must have shape (N>=6,3)")
    if not np.all(np.isfinite(plan)):
        raise ValueError("calibration plan contains non-finite values")
    lower = np.asarray([-2.6, -2.6, -0.9], dtype=float)
    upper = np.asarray([2.6, 2.6, 0.9], dtype=float)
    if np.any(plan < lower) or np.any(plan > upper):
        raise ValueError("calibration plan exceeds validated mode bounds")
    startup = cfg["queue_consistent_startup"]
    if str(startup.get("weak_slew_controller_variant")) != "control_aware_no_aw":
        raise ValueError("Stage4.1R7 must preserve the validated Stage4.1R4 no-AW weak-slew closure")
    if bool(startup.get("anti_windup_enabled", True)):
        raise ValueError("Stage4.1R7 primary startup must not enable anti-windup")
    confidence = cfg["confidence_gate"]
    if float(confidence["minimum_confidence_ratio"]) <= 1.0:
        raise ValueError("Stage4.1R7 requires a confidence ratio strictly above one")
    if int(confidence["consecutive_best_observations"]) < 2:
        raise ValueError("Stage4.1R7 requires at least two consecutive best observations")


def load_stage41r7_config(
    config_path: str | Path,
    *,
    source_stage41r6_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage41R7Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = base.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)},
    )
    source_r6 = resolve_source_stage41r6_run(source_stage41r6_run)
    source_manifest = read_json(source_r6 / "stage4_1r6_manifest.json")
    source_state = read_json(source_r6 / "stage4_1r6_state.json")
    source_verdict = read_json(source_r6 / "stage4_1r6_analysis/stage4_1r6_verdict.json")
    source_r6_cfg = read_json(source_r6 / "stage4_1r6_config.resolved.json")
    validate_source(source_manifest, source_state)
    validate_config(cfg, source_r6_cfg)
    source_r5 = _resolve_source_r5(project_dir, source_manifest)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage4_1r7_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r7_precontrol_calibration_queue_startup')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)
    r6_ctx = r6.load_stage41r6_config(
        source_r6 / "stage4_1r6_config.resolved.json",
        source_stage41r5_run=source_r5,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    env_cfg = copy.deepcopy(r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"].get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_1R7_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"])).expanduser().resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R7_TSC_RUN_ROOT", storage["tsc_run_root"])).expanduser().resolve()
    )
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg = env_cfg
    r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg = copy.deepcopy(env_cfg)
    r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    return Stage41R7Context(
        cfg=cfg,
        paths=Stage41R7Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r6_run=source_r6,
        source_manifest=source_manifest,
        source_state=source_state,
        source_verdict=source_verdict,
        source_r6_cfg=source_r6_cfg,
        source_stage41r5_run=source_r5,
        r6_ctx=r6_ctx,
        source_fingerprint=_combined_source_inventory(source_r6, r6_ctx),
    )


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "calibration_complete": False,
        "startup_complete": False,
        "restart_audit_complete": False,
        "confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R7Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def resource_preflight(cfg: dict[str, Any]) -> dict[str, Any]:
    requested = int(os.environ.get("STAGE4_1R7_WORKERS", cfg["parallel"]["n_workers"]))
    logical = int(os.cpu_count() or 1)
    reserve = int(cfg["parallel"].get("reserve_logical_cpus", 16))
    safe = max(1, logical - reserve)
    if requested > safe:
        raise RuntimeError(
            f"Stage4.1R7 requests {requested} workers, but {logical} logical CPUs are visible "
            f"and {reserve} are reserved (safe ceiling={safe})"
        )
    pages = os.sysconf("SC_AVPHYS_PAGES")
    page_size = os.sysconf("SC_PAGE_SIZE")
    available_gb = pages * page_size / (1024**3)
    minimum_gb = float(cfg["parallel"].get("minimum_available_memory_gb", 72.0))
    if available_gb < minimum_gb:
        raise RuntimeError(f"available memory {available_gb:.1f} GiB is below required {minimum_gb:.1f} GiB")
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    return {
        "requested_workers": requested,
        "logical_cpus": logical,
        "reserved_logical_cpus": reserve,
        "safe_worker_ceiling": safe,
        "available_memory_gb": available_gb,
        "open_file_soft_limit": soft,
        "open_file_hard_limit": hard,
    }


def initialize_run(ctx: Stage41R7Context) -> None:
    for path in (
        ctx.paths.run_dir, ctx.paths.source_audit, ctx.paths.calibration,
        ctx.paths.startup, ctx.paths.restart, ctx.paths.confirmation,
        ctx.paths.analysis, ctx.paths.variants, ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.run_dir / "stage4_1r7_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg)
    workers = resource_preflight(ctx.cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "runtime_bugfix_revision": RUNTIME_BUGFIX_REVISION,
        "runtime_bugfix_control_law_changed": False,
        "runtime_bugfix_experiment_identity_changed": False,
        "created_utc": utc_timestamp(),
        "source_stage4_1r6_run": str(ctx.source_stage41r6_run),
        "source_stage4_1r5_run": str(ctx.source_stage41r5_run),
        "source_fingerprint": {k: v for k, v in ctx.source_fingerprint.items() if k != "entries"},
        "workers": workers,
        "hard_numeric_thresholds_changed": False,
        "precontrol_calibration_uses_separate_reset_episode": True,
        "main_queue_is_primed_from_calibrated_model": True,
        "online_handover_is_not_primary_startup_path": True,
        "finite_test_envelope_only": True,
        "deployment_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if str(old.get("controller_revision")) != CONTROLLER_REVISION:
            raise ValueError("existing Stage4.1R7 run uses another controller revision")
        if str((old.get("source_fingerprint") or {}).get("digest")) != str(ctx.source_fingerprint["digest"]):
            raise ValueError("source Stage4.1R6 content changed")
        old_bugfix = str(old.get("runtime_bugfix_revision", "")).strip()
        if old_bugfix and old_bugfix != RUNTIME_BUGFIX_REVISION:
            raise ValueError(
                "existing Stage4.1R7 run uses another runtime bugfix revision: "
                f"{old_bugfix}"
            )
        if not old_bugfix:
            old["runtime_bugfix_revision"] = RUNTIME_BUGFIX_REVISION
            old["runtime_bugfix_control_law_changed"] = False
            old["runtime_bugfix_experiment_identity_changed"] = False
            old["runtime_bugfix_applied_utc"] = utc_timestamp()
            atomic_write_json(ctx.paths.manifest, old)
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    inventory = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory.exists():
        atomic_write_json(inventory, ctx.source_fingerprint)
    for relative in (
        "stage4_1r6_manifest.json", "stage4_1r6_state.json", "stage4_1r6_config.resolved.json",
        "stage4_1r6_analysis/stage4_1r6_verdict.json",
        "stage4_1r6_estimator_confirmation/summary.json",
        "stage4_1r6_static_startup/summary.json",
    ):
        src = ctx.source_stage41r6_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())


# ---------------------------------------------------------------------------
# Environment variants, worker, calibration and evaluation
# ---------------------------------------------------------------------------


def materialize_variant(
    ctx: Stage41R7Context,
    *,
    slew_scale: float,
    horizon_steps: int,
    start_folder: str | None = None,
) -> tuple[str, dict[str, Any]]:
    return r4.materialize_variant(
        ctx.r6_ctx.r5_ctx.r4_ctx,
        slew_scale=float(slew_scale),
        horizon_steps=int(horizon_steps),
        start_folder=start_folder,
    )


def _confidence_estimator_cfg(ctx: Stage41R7Context, *, initial_delay: int = 0, initial_slew: float = 1.0) -> dict[str, Any]:
    bank = ctx.cfg["confidence_gate"]
    return {
        "enabled": True,
        "delay_candidates": list(map(int, bank["delay_candidates"])),
        "slew_candidates": list(map(float, bank["slew_candidates"])),
        "score_decay": float(bank["score_decay"]),
        "minimum_observations": int(bank["minimum_observations"]),
        "switch_hysteresis_fraction": float(bank["switch_hysteresis_fraction"]),
        "minimum_confidence_ratio": float(bank["minimum_confidence_ratio"]),
        "minimum_absolute_score_gap": float(bank["minimum_absolute_score_gap"]),
        "consecutive_best_observations": int(bank["consecutive_best_observations"]),
        "require_unique_best": bool(bank["require_unique_best"]),
        "tie_relative_tolerance": float(bank["tie_relative_tolerance"]),
        "tie_absolute_tolerance": float(bank["tie_absolute_tolerance"]),
        "initial_delay_steps": int(initial_delay),
        "initial_slew_scale": float(initial_slew),
    }


class LocalStage41R7Worker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str):
        self.inner = r4.LocalStage41R4Worker(payload, library, bundle, worker_id)
        self.base_worker = self.inner.inner

    def _cleanup_episode(self, *, failed: bool, reason: str) -> None:
        runner = getattr(self.base_worker.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=failed, reason=reason)

    def _run_calibration(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        failure_reason = ""
        success = False
        try:
            plan = np.asarray(spec["calibration_mode_command_plan"], dtype=float)
            if plan.ndim != 2 or plan.shape[1] != 3:
                raise ValueError("calibration_mode_command_plan must have shape (N,3)")
            actual_delay = max(0, int(spec.get("action_delay_steps", 0)))
            actual_slew = float(spec.get("slew_scale", 1.0))
            noise_sigma = float(spec.get("coil_current_measurement_noise_A", 0.0))
            rng = np.random.default_rng(int(spec.get("coil_current_measurement_seed", 0)))
            estimator_cfg = copy.deepcopy(spec["calibration_estimator"])
            bank = r3.DelaySlewHypothesisBank(
                scheduler=self.base_worker.scheduler,
                delay_candidates=tuple(map(int, estimator_cfg["delay_candidates"])),
                slew_candidates=tuple(map(float, estimator_cfg["slew_candidates"])),
                score_decay=float(estimator_cfg["score_decay"]),
                minimum_observations=int(estimator_cfg["minimum_observations"]),
                switch_hysteresis_fraction=float(estimator_cfg["switch_hysteresis_fraction"]),
                initial_delay_steps=int(estimator_cfg.get("initial_delay_steps", 0)),
                initial_slew_scale=float(estimator_cfg.get("initial_slew_scale", 1.0)),
                minimum_confidence_ratio=float(estimator_cfg["minimum_confidence_ratio"]),
                minimum_absolute_score_gap=float(estimator_cfg["minimum_absolute_score_gap"]),
                consecutive_best_observations=int(estimator_cfg["consecutive_best_observations"]),
                require_unique_best=bool(estimator_cfg["require_unique_best"]),
                tie_relative_tolerance=float(estimator_cfg["tie_relative_tolerance"]),
                tie_absolute_tolerance=float(estimator_cfg["tie_absolute_tolerance"]),
            )
            self.base_worker.env.reset()
            zero_action = np.zeros(14, dtype=np.float32)
            trajectory.append(base._state_record(self.base_worker.env, 0, zero_action))
            issued_commands: list[np.ndarray] = []
            # Calibration is a separate pre-shot episode.  Its actuator queue is
            # deliberately zero before the first issued calibration command.
            zero_nominal = np.zeros_like(plan)
            for step, issued in enumerate(plan):
                issued = np.asarray(issued, dtype=float).reshape(3)
                issued_commands.append(issued.copy())
                issue_index = step - actual_delay
                applied = np.zeros(3, dtype=float) if issue_index < 0 else issued_commands[issue_index]
                currents_before = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                action = self.base_worker._mode_action(applied, currents_before)
                _, _, terminated, truncated, info = self.base_worker.env.step(action)
                trajectory.append(base._state_record(self.base_worker.env, step + 1, action))
                currents_after = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                actual_delta = currents_after - currents_before
                measured_delta = actual_delta + rng.normal(0.0, noise_sigma, size=14)
                update = bank.update(
                    step=step,
                    observed_delta_a=measured_delta,
                    currents_before_a=currents_before,
                    issued_commands=issued_commands,
                    # Negative issue indices correspond to a zero prehistory,
                    # not to an Oracle-primed nominal queue.
                    nominal_commands=zero_nominal,
                    gain_for_prediction=np.ones(3, dtype=float),
                )
                trace.append({
                    "step": step,
                    "issued_mode_coefficients": issued.tolist(),
                    "applied_mode_coefficients": np.asarray(applied, dtype=float).tolist(),
                    "actual_current_delta_A": actual_delta.tolist(),
                    "measured_current_delta_A": measured_delta.tolist(),
                    "measurement_noise_A": (measured_delta - actual_delta).tolist(),
                    "estimator_update": update,
                })
                if terminated:
                    failure_reason = str(info.get("failure_reason", "calibration terminated"))
                    break
                if truncated and step + 1 < len(plan):
                    failure_reason = "environment truncated before calibration plan completed"
                    break
            summary = bank.summary()
            success = bool(
                not failure_reason
                and len(trajectory) == len(plan) + 1
                and not any(bool(row.get("abnormal", False)) for row in trajectory)
            )
            result = {
                "schema_version": SCHEMA_VERSION,
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": spec["experiment_id"],
                "spec": copy.deepcopy(spec),
                "success": success,
                "failure_reason": "" if success else (failure_reason or "incomplete/abnormal calibration"),
                "wall_time_s": float(time.time() - started),
                "trajectory": trajectory,
                "calibration_trace": trace,
                "adaptive_estimator_summary": summary,
                "calibration_queue_initialization": "zero_command_prehistory",
                "calibration_is_separate_reset_episode": True,
                "actual_delay_steps": actual_delay,
                "actual_slew_scale": actual_slew,
            }
            return _json_safe(result)
        except Exception as exc:
            failure_reason = failure_reason or repr(exc)
            return _json_safe({
                "schema_version": SCHEMA_VERSION,
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": spec.get("experiment_id", "unknown"),
                "spec": copy.deepcopy(spec),
                "success": False,
                "failure_reason": repr(exc),
                "traceback": traceback.format_exc(),
                "wall_time_s": float(time.time() - started),
                "trajectory": trajectory,
                "calibration_trace": trace,
            })
        finally:
            self._cleanup_episode(
                failed=not bool(success),
                reason="stage4_1r7_precontrol_calibration",
            )

    def _run_paired_confirmation(self, spec: dict[str, Any]) -> dict[str, Any]:
        calibration_spec = copy.deepcopy(spec["paired_calibration_spec"])
        calibration_spec["experiment_id"] = f"{spec['experiment_id']}__cal"
        calibration = self._run_calibration(calibration_spec)

        def calibration_failure(reason: str) -> dict[str, Any]:
            return _json_safe({
                "schema_version": SCHEMA_VERSION,
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": spec["experiment_id"],
                "spec": copy.deepcopy(spec),
                "success": False,
                "failure_reason": reason,
                "trajectory": [],
                "control_trace": [],
                "paired_calibration_result": calibration,
                "precontrol_calibration_is_separate_reset_episode": True,
                "paired_main_control_executed": False,
                "paired_tsc_episode_count": 1,
            })

        if not calibration.get("success"):
            return calibration_failure(
                "paired calibration failed: " + str(calibration.get("failure_reason", ""))
            )
        estimator = calibration.get("adaptive_estimator_summary") or {}
        selected_delay = estimator.get("selected_delay_steps")
        selected_slew = estimator.get("selected_slew_scale")
        try:
            if isinstance(selected_delay, bool) or isinstance(selected_slew, bool):
                raise ValueError("boolean selected model")
            estimated_delay = int(selected_delay)
            estimated_slew = float(selected_slew)
            if not math.isfinite(estimated_slew):
                raise ValueError("non-finite selected slew")
        except (TypeError, ValueError, OverflowError):
            return calibration_failure(
                "paired calibration produced no valid selected delay/slew model: "
                f"delay={selected_delay!r}, slew={selected_slew!r}"
            )
        estimator_cfg = calibration_spec.get("calibration_estimator") or {}
        delay_candidates = {int(value) for value in estimator_cfg.get("delay_candidates", [])}
        slew_candidates = [float(value) for value in estimator_cfg.get("slew_candidates", [])]
        if (
            estimated_delay not in delay_candidates
            or not any(math.isclose(estimated_slew, value, abs_tol=1e-12) for value in slew_candidates)
        ):
            return calibration_failure(
                "paired calibration selected a model outside its finite candidate bank: "
                f"delay={estimated_delay!r}, slew={estimated_slew!r}"
            )
        main_spec = copy.deepcopy(spec["paired_main_spec_template"])
        main_spec["experiment_id"] = f"{spec['experiment_id']}__main"
        main_spec["controller_action_delay_steps"] = estimated_delay
        main_spec["controller_slew_scale_estimate"] = estimated_slew
        monitor_cfg = copy.deepcopy(main_spec.get("adaptive_delay_slew_estimator") or {})
        if monitor_cfg.get("enabled"):
            monitor_cfg["initial_delay_steps"] = estimated_delay
            monitor_cfg["initial_slew_scale"] = estimated_slew
            main_spec["adaptive_delay_slew_estimator"] = monitor_cfg
        main = self.inner.evaluate(main_spec)
        main["experiment_id"] = spec["experiment_id"]
        main["spec"] = {
            **main_spec,
            "phase": spec["phase"],
            "category": spec["category"],
            "scenario": spec["scenario"],
            "confirmation_group": spec.get("confirmation_group"),
            "confirmation_repeat": spec.get("confirmation_repeat"),
            "paired_calibration_profile": calibration_spec.get("calibration_profile"),
        }
        main["controller_revision"] = CONTROLLER_REVISION
        main["stage4_1r7_controller_revision"] = CONTROLLER_REVISION
        main["paired_calibration_result"] = calibration
        main["precontrol_calibration_is_separate_reset_episode"] = True
        main["paired_main_control_executed"] = True
        main["paired_tsc_episode_count"] = 2
        return _json_safe(main)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        phase = str(spec.get("phase", ""))
        if phase == "precontrol_calibration":
            return self._run_calibration(spec)
        if phase == "paired_confirmation":
            return self._run_paired_confirmation(spec)
        result = self.inner.evaluate(spec)
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r7_controller_revision"] = CONTROLLER_REVISION
        return _json_safe(result)

    def close(self) -> None:
        self.inner.close()


def _ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id):
            self.worker = LocalStage41R7Worker(payload, library, bundle, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor


def evaluate_specs(
    ctx: Stage41R7Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = ctx.r6_ctx.r5_ctx.r4_ctx.variants
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        variant = str(spec["environment_variant"])
        if variant not in variants:
            raise KeyError(f"unmaterialized environment variant {variant}")
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, rows in by_variant.items():
        pending = [
            row for row in rows
            if not (resume and _result_complete(output_dir / f"{row['experiment_id']}.json.gz"))
        ]
        if pending:
            pending_by_variant[variant] = pending
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalStage41R7Worker(
                variants[variant],
                ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_library,
                ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle,
                f"stage41r7_{variant}_serial",
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate(spec))
                    print(f"[Stage4.1R7 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(os.environ.get("STAGE4_1R7_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R7 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()},
            plan.actor_count,
        )
        print(
            "[Stage4.1R7 mixed-variant] actor_allocation="
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
                    ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_library,
                    ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle,
                    f"stage41r7_{variant}_{index:03d}",
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
                    print(f"[Stage4.1R7 mixed-variant] waiting {done}/{total_pending}", flush=True)
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": SCHEMA_VERSION,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                        }
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(f"[Stage4.1R7 mixed-variant] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(
                all_actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


# ---------------------------------------------------------------------------
# Specs and result rows
# ---------------------------------------------------------------------------


def _make_spec(
    *,
    phase: str,
    scenario: str,
    category: str,
    target: dict[str, Any] | None,
    controller_scale: float,
    environment_variant: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = copy.deepcopy(target or {"target_id": "calibration", "R_offset_m": 0.0, "Z_offset_m": 0.0, "Ip_offset_A": 0.0})
    extra = copy.deepcopy(extra or {})
    identity = {
        "revision": CONTROLLER_REVISION,
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target": target,
        "controller_scale": controller_scale,
        "environment_variant": environment_variant,
        "extra": extra,
    }
    return {
        "kind": "stage4_1r7_precontrol_calibration_queue_startup",
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": _scenario_digest(identity),
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target_id": target.get("target_id", scenario),
        "target_R_offset_m": float(target.get("R_offset_m", 0.0)),
        "target_Z_offset_m": float(target.get("Z_offset_m", 0.0)),
        "target_Ip_offset_A": float(target.get("Ip_offset_A", 0.0)),
        "controller_scale": float(controller_scale),
        "environment_variant": environment_variant,
        **extra,
    }


def _target_task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id", "scenario"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(spec.get("category", "r7")),
    }


def calibration_result_row(result: dict[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    estimator = result.get("adaptive_estimator_summary") or {}
    actual_delay = int(spec.get("action_delay_steps", 0))
    actual_slew = float(spec.get("slew_scale", 1.0))
    selected_delay = estimator.get("selected_delay_steps")
    selected_slew = estimator.get("selected_slew_scale")
    lock_events = list(estimator.get("lock_events") or [])
    incorrect_locks = sum(
        _as_int(event.get("delay_steps"), -999) != actual_delay
        or not math.isclose(_as_float(event.get("slew_scale"), 1e9), actual_slew, abs_tol=1e-12)
        for event in lock_events
    )
    trace = result.get("calibration_trace") or []
    actual_deltas = np.asarray([row.get("actual_current_delta_A", np.zeros(14)) for row in trace], dtype=float)
    return {
        "experiment_id": result["experiment_id"],
        "phase": spec.get("phase"),
        "calibration_profile": spec.get("calibration_profile"),
        "calibration_repeat": int(spec.get("calibration_repeat", 0)),
        "coil_current_measurement_noise_A": float(spec.get("coil_current_measurement_noise_A", 0.0)),
        "actual_delay_steps": actual_delay,
        "actual_slew_scale": actual_slew,
        "estimated_delay_steps": selected_delay,
        "estimated_slew_scale": selected_slew,
        "final_identification_correct": bool(
            selected_delay is not None
            and int(selected_delay) == actual_delay
            and selected_slew is not None
            and math.isclose(float(selected_slew), actual_slew, abs_tol=1e-12)
        ),
        "observations": estimator.get("observations"),
        "first_confident_lock_step": estimator.get("first_confident_lock_step"),
        "confidence_ratio": estimator.get("confidence_ratio"),
        "score_gap": estimator.get("score_gap"),
        "incorrect_confident_lock_count": incorrect_locks,
        "lock_events": lock_events,
        "maximum_abs_actual_current_delta_A": float(np.max(np.abs(actual_deltas))) if actual_deltas.size else 0.0,
        "success": bool(result.get("success", False)),
        "wall_time_s": float(result.get("wall_time_s", 0.0)),
    }


def control_result_row(ctx: Stage41R7Context, result: dict[str, Any]) -> dict[str, Any]:
    extended = bool(result["spec"].get("extended_horizon", False))
    row = r4.result_row(ctx.r6_ctx.r5_ctx.r4_ctx, result, extended=extended)
    spec = result["spec"]
    trajectory = result.get("trajectory") or []
    trace = result.get("control_trace") or []
    if trajectory:
        state_array = np.asarray(
            [[item["R"], item["Z"], item["Ip"], *item["currents_a_tsc"]] for item in trajectory],
            dtype=float,
        )
        trajectory_signature = _array_digest(state_array, "traj")
    else:
        trajectory_signature = ""
    issued = np.asarray([item.get("issued_mode_coefficients", [0.0, 0.0, 0.0]) for item in trace], dtype=float)
    command_signature = _array_digest(issued, "cmd") if len(issued) else ""
    estimator = result.get("adaptive_estimator_summary") or {}
    transitions = list(estimator.get("transitions") or [])
    calibration = result.get("paired_calibration_result") or {}
    calibration_estimator = calibration.get("adaptive_estimator_summary") or {}
    is_paired_confirmation = str(spec.get("phase", "")) == "paired_confirmation"
    paired_main_executed = result.get("paired_main_control_executed")
    if is_paired_confirmation and paired_main_executed is None:
        # Compatibility with any pre-hotfix paired raw: a completed main result
        # carries the paired calibration and the environment-level success bit.
        paired_main_executed = bool(calibration and result.get("success", False))
    paired_episode_count = result.get("paired_tsc_episode_count")
    if is_paired_confirmation and paired_episode_count is None:
        paired_episode_count = 2 if paired_main_executed else 1
    row.update({
        "controller_revision": CONTROLLER_REVISION,
        "controller_variant": spec.get("controller_variant"),
        "calibration_source_experiment_id": spec.get("calibration_source_experiment_id"),
        "calibration_profile": spec.get("calibration_profile", spec.get("paired_calibration_profile")),
        "calibrated_delay_steps": spec.get("controller_action_delay_steps"),
        "calibrated_slew_scale": spec.get("controller_slew_scale_estimate"),
        "monitor_estimated_delay_steps": estimator.get("selected_delay_steps"),
        "monitor_estimated_slew_scale": estimator.get("selected_slew_scale"),
        "monitor_transition_count": len(transitions),
        "trajectory_signature": trajectory_signature,
        "issued_command_signature": command_signature,
        "confirmation_group": spec.get("confirmation_group"),
        "confirmation_repeat": spec.get("confirmation_repeat"),
        "paired_calibration_success": calibration.get("success") if calibration else None,
        "paired_calibration_estimated_delay_steps": calibration_estimator.get("selected_delay_steps") if calibration else None,
        "paired_calibration_estimated_slew_scale": calibration_estimator.get("selected_slew_scale") if calibration else None,
        "paired_calibration_first_confident_lock_step": calibration_estimator.get("first_confident_lock_step") if calibration else None,
        "paired_main_control_executed": paired_main_executed if is_paired_confirmation else None,
        "paired_tsc_episode_count": paired_episode_count if is_paired_confirmation else None,
    })
    return row


# ---------------------------------------------------------------------------
# Source audit
# ---------------------------------------------------------------------------


def run_source_audit(ctx: Stage41R7Context) -> dict[str, Any]:
    source_estimator = ctx.source_state.get("estimator_confirmation_summary") or {}
    source_startup = ctx.source_state.get("startup_summary") or {}
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r6_run": str(ctx.source_stage41r6_run),
        "source_finished": bool(ctx.source_state.get("finished", False)),
        "source_estimator_confirmation_passed": bool(source_estimator.get("passed", False)),
        "source_persistent_exact_preservation_fraction": source_startup.get("persistent_exact_preservation_fraction"),
        "source_persistent_exact_trace_equivalence_fraction": source_startup.get("persistent_exact_trace_equivalence_fraction"),
        "source_adjacent_handover_passed": bool(source_startup.get("precalibrated_startup_passed", False)),
        "source_cold_start_passed": bool(source_startup.get("cold_common_prefix_diagnostic_passed", False)),
        "failed_online_handover_is_not_reused_as_success": True,
        "passed": bool(
            source_estimator.get("passed", False)
            and math.isclose(float(source_startup.get("persistent_exact_preservation_fraction", 0.0)), 1.0, abs_tol=1e-12)
            and math.isclose(float(source_startup.get("persistent_exact_trace_equivalence_fraction", 0.0)), 1.0, abs_tol=1e-12)
        ),
        "warning": "R7 reuses only the validated estimator and exact persistent startup facts. R6 physical-blend and cold-start failures are not reinterpreted as success.",
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Pre-control calibration
# ---------------------------------------------------------------------------


def build_calibration_specs(ctx: Stage41R7Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["precontrol_calibration"]
    specs: list[dict[str, Any]] = []
    plan = np.asarray(cfg["mode_command_plan"], dtype=float).tolist()
    estimator_cfg = _confidence_estimator_cfg(ctx)
    for slew in cfg["actual_slew_scales"]:
        variant, _ = materialize_variant(
            ctx,
            slew_scale=float(slew),
            horizon_steps=int(cfg["environment_horizon_steps"]),
        )
        for delay in cfg["actual_delay_steps"]:
            for repeat, profile in enumerate(cfg["profiles"]):
                extra = {
                    "horizon_steps": int(cfg["environment_horizon_steps"]),
                    "slew_scale": float(slew),
                    "action_delay_steps": int(delay),
                    "calibration_mode_command_plan": plan,
                    "calibration_estimator": estimator_cfg,
                    "calibration_profile": str(profile["profile_id"]),
                    "calibration_repeat": int(repeat),
                    "coil_current_measurement_noise_A": float(profile.get("coil_current_measurement_noise_A", 0.0)),
                    "coil_current_measurement_seed": int(profile.get("seed_base", 0)) + 100 * int(delay) + int(round(10 * float(slew))),
                    "controller_variant": "precontrol_calibration_only",
                }
                specs.append(_make_spec(
                    phase="precontrol_calibration",
                    scenario=f"cal_d{delay}_s{float(slew):.1f}_{profile['profile_id']}",
                    category="precontrol_calibration",
                    target=None,
                    controller_scale=0.0,
                    environment_variant=variant,
                    extra=extra,
                ))
    return specs


def summarize_calibration(ctx: Stage41R7Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["precontrol_calibration"]
    correct = [_as_bool(row.get("final_identification_correct")) for row in rows]
    locks = [
        _as_int(row.get("first_confident_lock_step"), 999)
        if row.get("first_confident_lock_step") is not None else 999
        for row in rows
    ]
    expected_pairs = {
        (int(delay), float(slew))
        for delay in cfg["actual_delay_steps"]
        for slew in cfg["actual_slew_scales"]
    }
    expected_profiles = {str(profile["profile_id"]) for profile in cfg["profiles"]}
    groups: dict[tuple[int, float], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(
            (_as_int(row.get("actual_delay_steps"), -999), _as_float(row.get("actual_slew_scale"), math.nan)),
            [],
        ).append(row)
    group_rows = []
    for key, subset in sorted(groups.items()):
        profiles = [str(row.get("calibration_profile", "")) for row in subset]
        profile_coverage_complete = bool(
            len(profiles) == len(expected_profiles) and set(profiles) == expected_profiles
        )
        group_rows.append({
            "actual_delay_steps": key[0],
            "actual_slew_scale": key[1],
            "profiles": len(subset),
            "profile_ids": sorted(profiles),
            "profile_coverage_complete": profile_coverage_complete,
            "all_success": all(_as_bool(row.get("success")) for row in subset),
            "all_final_correct": all(_as_bool(row.get("final_identification_correct")) for row in subset),
            "incorrect_confident_lock_count": sum(_as_int(row.get("incorrect_confident_lock_count"), 0) for row in subset),
            "maximum_first_confident_lock_step": max(
                (
                    _as_int(row.get("first_confident_lock_step"), 999)
                    if row.get("first_confident_lock_step") is not None else 999
                    for row in subset
                ),
                default=999,
            ),
            "minimum_confidence_ratio": min((_as_float(row.get("confidence_ratio"), 0.0) for row in subset), default=0.0),
        })
    expected_rollouts = len(expected_pairs) * len(expected_profiles)
    coverage_complete = bool(
        len(rows) == expected_rollouts
        and set(groups) == expected_pairs
        and all(row["profile_coverage_complete"] for row in group_rows)
    )
    incorrect_lock_count = sum(_as_int(row.get("incorrect_confident_lock_count"), 0) for row in rows)
    passed = bool(
        rows
        and coverage_complete
        and all(_as_bool(row.get("success")) for row in rows)
        and all(correct)
        and incorrect_lock_count == 0
        and max(locks, default=999) <= int(cfg["maximum_first_confident_lock_step"])
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "precontrol_calibration",
        "n_rollouts": len(rows),
        "expected_rollouts": expected_rollouts,
        "coverage_complete": coverage_complete,
        "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "final_identification_fraction": float(np.mean(correct)) if correct else 0.0,
        "incorrect_confident_lock_count": incorrect_lock_count,
        "maximum_first_confident_lock_step": max(locks, default=999),
        "minimum_final_confidence_ratio": min((_as_float(row.get("confidence_ratio"), 0.0) for row in rows), default=0.0),
        "distinct_pairs_calibrated": len(group_rows),
        "calibration_is_separate_reset_episode": True,
        "passed": passed,
        "group_summaries": group_rows,
    }


def run_calibration(ctx: Stage41R7Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_calibration_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.calibration / "raw", backend=backend, resume=resume)
    rows = [calibration_result_row(result) for result in results]
    summary = summarize_calibration(ctx, rows)
    write_csv(ctx.paths.calibration / "results.csv", rows)
    atomic_write_json(ctx.paths.calibration / "results.json", rows)
    write_csv(ctx.paths.calibration / "group_summary.csv", summary["group_summaries"])
    atomic_write_json(ctx.paths.calibration / "summary.json", summary)
    _update_state(ctx, calibration_complete=True, calibration_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Queue-consistent main startup
# ---------------------------------------------------------------------------


def _calibration_lookup(ctx: Stage41R7Context) -> dict[tuple[int, float, str], dict[str, Any]]:
    rows = read_json(ctx.paths.calibration / "results.json")
    lookup: dict[tuple[int, float, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            int(row["actual_delay_steps"]),
            float(row["actual_slew_scale"]),
            str(row["calibration_profile"]),
        )
        lookup[key] = row
    return lookup


def _historical_r4_estimator_cfg(ctx: Stage41R7Context) -> dict[str, Any]:
    old = ctx.r6_ctx.source_r5_cfg["static_handover"]["estimator"]
    return {
        "enabled": True,
        "delay_candidates": list(map(int, old["delay_candidates"])),
        "slew_candidates": list(map(float, old["slew_candidates"])),
        "score_decay": float(old["score_decay"]),
        "minimum_observations": 3,
        "switch_hysteresis_fraction": 0.05,
        "initial_delay_steps": 0,
        "initial_slew_scale": 1.0,
    }


def _main_extra(
    ctx: Stage41R7Context,
    *,
    variant: str,
    actual_delay: int,
    actual_slew: float,
    modeled_delay: int,
    modeled_slew: float,
    horizon_steps: int,
    calibration_row: dict[str, Any] | None,
) -> dict[str, Any]:
    primary = variant.startswith("r7_precalibrated") or variant == "oracle"
    extra: dict[str, Any] = {
        "horizon_steps": int(horizon_steps),
        "extended_horizon": bool(horizon_steps == 37),
        "tail_hold_steps": 2 if horizon_steps == 37 else 0,
        "tail_action_policy": "zero_current_increment" if horizon_steps == 37 else "none",
        "slew_scale": float(actual_slew),
        "controller_slew_scale_estimate": float(modeled_slew),
        "actuator_gain_by_mode": [1.0, 1.0, 1.0],
        "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
        "action_delay_steps": int(actual_delay),
        "controller_action_delay_steps": int(modeled_delay),
        "prime_action_queue_with_nominal": True,
        "observer_enabled": True,
        "observer_variant": "control_aware_residual",
        # Preserve the Stage4.1R4 370 ms weak-slew closure exactly: its
        # selected controller was control_aware_no_aw.  Conditional AW was a
        # useful diagnostic, but the hard target failed under that variant.
        "anti_windup_enabled": False,
        "anti_windup_mode": "off",
        "conditional_anti_windup_use_actual_actuator_state": False,
        "force_anti_windup_in_clean": False,
        "delay_aware_enabled": True,
        "gain_slew_scheduling_enabled": True,
        "phase_aware_reference_enabled": True,
        "known_control_effect_from_measured_current_increment": True,
        "controller_variant": variant,
        "adaptive_handover": {"enabled": False},
        "calibration_source_experiment_id": None if calibration_row is None else calibration_row["experiment_id"],
        "calibration_profile": None if calibration_row is None else calibration_row["calibration_profile"],
        "precontrol_calibration_is_separate_reset_episode": calibration_row is not None,
        "queue_initialized_from_calibrated_model_before_main_control": calibration_row is not None,
    }
    if variant in STARTUP_MONITOR_VARIANTS:
        extra["adaptive_delay_slew_estimator"] = _confidence_estimator_cfg(
            ctx, initial_delay=modeled_delay, initial_slew=modeled_slew
        )
    elif variant == "r4_abrupt_unknown":
        extra["adaptive_delay_slew_estimator"] = _historical_r4_estimator_cfg(ctx)
        extra["anti_windup_enabled"] = False
        extra["anti_windup_mode"] = "off"
        extra["force_anti_windup_in_clean"] = False
    return extra


def build_startup_specs(ctx: Stage41R7Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["queue_consistent_startup"]
    lookup = _calibration_lookup(ctx)
    source_scale = float(ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale)
    specs: list[dict[str, Any]] = []
    for actual_slew in cfg["actual_slew_scales"]:
        horizon = 37 if math.isclose(float(actual_slew), 0.9, abs_tol=1e-12) else 35
        variant_id, _ = materialize_variant(ctx, slew_scale=float(actual_slew), horizon_steps=horizon)
        for actual_delay in cfg["actual_delay_steps"]:
            clean = lookup[(int(actual_delay), float(actual_slew), str(cfg["clean_profile_id"]))]
            noisy = lookup[(int(actual_delay), float(actual_slew), str(cfg["noisy_profile_id"]))]
            for target in cfg["targets"]:
                for variant in cfg["controller_variants"]:
                    calibration_row: dict[str, Any] | None = None
                    if variant in {"r7_precalibrated_clean_no_monitor", "r7_precalibrated_clean_monitor"}:
                        calibration_row = clean
                    elif variant == "r7_precalibrated_noisy_monitor":
                        calibration_row = noisy
                    if variant == "oracle":
                        modeled_delay, modeled_slew = int(actual_delay), float(actual_slew)
                    elif calibration_row is not None:
                        modeled_delay = int(calibration_row["estimated_delay_steps"])
                        modeled_slew = float(calibration_row["estimated_slew_scale"])
                    else:
                        modeled_delay, modeled_slew = 0, 1.0
                    extra = _main_extra(
                        ctx,
                        variant=str(variant),
                        actual_delay=int(actual_delay),
                        actual_slew=float(actual_slew),
                        modeled_delay=modeled_delay,
                        modeled_slew=modeled_slew,
                        horizon_steps=horizon,
                        calibration_row=calibration_row,
                    )
                    specs.append(_make_spec(
                        phase="queue_consistent_startup",
                        scenario=f"{target['target_id']}__d{actual_delay}__s{float(actual_slew):.1f}__{variant}",
                        category="queue_consistent_startup",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra=extra,
                    ))
    return specs


def summarize_startup(ctx: Stage41R7Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["queue_consistent_startup"]
    expected_variants = {str(value) for value in cfg["controller_variants"]}
    expected_cases = {
        (str(target["target_id"]), int(delay), float(slew))
        for target in cfg["targets"]
        for delay in cfg["actual_delay_steps"]
        for slew in cfg["actual_slew_scales"]
    }
    grouped: dict[tuple[str, int, float], dict[str, dict[str, Any]]] = {}
    duplicate_rows = 0
    for row in rows:
        key = (
            str(row.get("target_id", "")),
            _as_int(row.get("actual_action_delay_steps"), -999),
            _as_float(row.get("actual_slew_scale"), math.nan),
        )
        variant = str(row.get("controller_variant", ""))
        variants = grouped.setdefault(key, {})
        duplicate_rows += int(variant in variants)
        variants[variant] = row
    expected_rollouts = len(expected_cases) * len(expected_variants)
    coverage_complete = bool(
        len(rows) == expected_rollouts
        and duplicate_rows == 0
        and set(grouped) == expected_cases
        and all(set(variants) == expected_variants for variants in grouped.values())
    )
    oracle_feasible = 0
    preserve_counts = {
        "r7_precalibrated_clean_no_monitor": 0,
        "r7_precalibrated_clean_monitor": 0,
        "r7_precalibrated_noisy_monitor": 0,
    }
    equality_counts = {key: 0 for key in preserve_counts}
    monitor_correct: list[bool] = []
    diagnostics = {"naive_default": 0, "r4_abrupt_unknown": 0}
    case_rows: list[dict[str, Any]] = []
    for key, variants in sorted(grouped.items()):
        oracle = variants.get("oracle")
        if oracle is None:
            continue
        oracle_ok = _as_bool(oracle.get("stage3_4_target_tracking_pass"))
        if oracle_ok:
            oracle_feasible += 1
        row_summary: dict[str, Any] = {
            "target_id": key[0],
            "actual_delay_steps": key[1],
            "actual_slew_scale": key[2],
            "oracle_pass": oracle_ok,
            "oracle_margin": oracle.get("stage3_4_tracking_minimum_signed_margin"),
        }
        for variant in preserve_counts:
            row = variants.get(variant)
            passed = bool(row and _as_bool(row.get("stage3_4_target_tracking_pass")))
            equal = bool(
                row
                and row.get("trajectory_signature") == oracle.get("trajectory_signature")
                and row.get("issued_command_signature") == oracle.get("issued_command_signature")
            )
            if oracle_ok and passed:
                preserve_counts[variant] += 1
            if oracle_ok and equal:
                equality_counts[variant] += 1
            row_summary[f"{variant}_pass"] = passed
            row_summary[f"{variant}_trace_equal"] = equal
            row_summary[f"{variant}_margin"] = None if row is None else row.get("stage3_4_tracking_minimum_signed_margin")
            if row is not None and variant in STARTUP_MONITOR_VARIANTS:
                monitor_correct.append(
                    _as_int(row.get("monitor_estimated_delay_steps"), -999) == key[1]
                    and math.isclose(
                        _as_float(row.get("monitor_estimated_slew_scale"), 1e9),
                        key[2],
                        abs_tol=1e-12,
                    )
                    and _as_int(row.get("monitor_transition_count"), -999) == 0
                )
        for variant in diagnostics:
            row = variants.get(variant)
            passed = bool(row and _as_bool(row.get("stage3_4_target_tracking_pass")))
            diagnostics[variant] += int(oracle_ok and passed)
            row_summary[f"{variant}_pass"] = passed
            row_summary[f"{variant}_margin"] = None if row is None else row.get("stage3_4_tracking_minimum_signed_margin")
        case_rows.append(row_summary)
    denominator = max(oracle_feasible, 1)
    preservation = {key: value / denominator for key, value in preserve_counts.items()}
    equivalence = {key: value / denominator for key, value in equality_counts.items()}
    expected_monitor_rows = len(expected_cases) * len(STARTUP_MONITOR_VARIANTS)
    monitor_coverage_complete = len(monitor_correct) == expected_monitor_rows
    passed = bool(
        coverage_complete
        and oracle_feasible > 0
        and all(value >= float(cfg["minimum_oracle_feasible_preservation"]) for value in preservation.values())
        and equivalence["r7_precalibrated_clean_no_monitor"] >= float(cfg["minimum_clean_trace_equivalence"])
        and equivalence["r7_precalibrated_clean_monitor"] >= float(cfg["minimum_clean_monitor_trace_equivalence"])
        and equivalence["r7_precalibrated_noisy_monitor"] >= float(cfg["minimum_noisy_monitor_trace_equivalence"])
        and monitor_coverage_complete
        and all(monitor_correct)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "queue_consistent_startup",
        "n_rollouts": len(rows),
        "expected_rollouts": expected_rollouts,
        "coverage_complete": coverage_complete,
        "duplicate_rows": duplicate_rows,
        "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "oracle_feasible_cases": oracle_feasible,
        "precalibrated_preservation_fraction": preservation,
        "precalibrated_trace_equivalence_fraction": equivalence,
        "monitor_rows_evaluated": len(monitor_correct),
        "expected_monitor_rows": expected_monitor_rows,
        "monitor_coverage_complete": monitor_coverage_complete,
        "monitor_final_model_correct_fraction": float(np.mean(monitor_correct)) if monitor_correct else 0.0,
        "diagnostic_preservation_fraction": {
            key: value / denominator for key, value in diagnostics.items()
        },
        "queue_primed_from_model_before_first_main_action": True,
        "online_handover_used_by_primary_variants": False,
        "precalibrated_startup_passed": passed,
        "passed": passed,
        "case_summaries": case_rows,
    }


def run_startup(ctx: Stage41R7Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_startup_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.startup / "raw", backend=backend, resume=resume)
    rows = [control_result_row(ctx, result) for result in results]
    summary = summarize_startup(ctx, rows)
    write_csv(ctx.paths.startup / "results.csv", rows)
    atomic_write_json(ctx.paths.startup / "results.json", rows)
    write_csv(ctx.paths.startup / "case_summary.csv", summary["case_summaries"])
    atomic_write_json(ctx.paths.startup / "summary.json", summary)
    _update_state(ctx, startup_complete=True, startup_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Restart audit and end-to-end paired confirmation
# ---------------------------------------------------------------------------


def run_restart_audit(ctx: Stage41R7Context) -> dict[str, Any]:
    root = Path(ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg.get("simulation_root", "")).expanduser()
    available: list[str] = []
    for value in ctx.cfg["restart_audit"].get("candidate_folders", []):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            available.append(str(path.resolve()))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_audit",
        "candidate_folders": list(ctx.cfg["restart_audit"].get("candidate_folders", [])),
        "available_folders": sorted(set(available)),
        "true_restart_validation_available": len(set(available)) >= int(ctx.cfg["restart_audit"].get("minimum_distinct_folders", 2)),
        "true_restart_validation_performed": False,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


def build_confirmation_specs(ctx: Stage41R7Context) -> list[dict[str, Any]]:
    state = read_json(ctx.paths.state)
    if not bool((state.get("startup_summary") or {}).get("precalibrated_startup_passed", False)):
        return []
    cfg = ctx.cfg["confirmation"]
    source_scale = float(ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale)
    calibration_cfg = ctx.cfg["precontrol_calibration"]
    plan = np.asarray(calibration_cfg["mode_command_plan"], dtype=float).tolist()
    specs: list[dict[str, Any]] = []
    for actual_slew in cfg["actual_slew_scales"]:
        horizon = 37 if math.isclose(float(actual_slew), 0.9, abs_tol=1e-12) else 35
        variant_id, _ = materialize_variant(ctx, slew_scale=float(actual_slew), horizon_steps=horizon)
        for actual_delay in cfg["actual_delay_steps"]:
            for target in cfg["targets"]:
                group = f"d{actual_delay}_s{float(actual_slew):.1f}_{target['target_id']}"
                for repeat in range(int(cfg["repeats_per_group"])):
                    calibration_extra = {
                        "horizon_steps": int(calibration_cfg["environment_horizon_steps"]),
                        "slew_scale": float(actual_slew),
                        "action_delay_steps": int(actual_delay),
                        "calibration_mode_command_plan": plan,
                        "calibration_estimator": _confidence_estimator_cfg(ctx),
                        "calibration_profile": "confirmation_noisy",
                        "calibration_repeat": int(repeat),
                        "coil_current_measurement_noise_A": float(cfg["coil_current_measurement_noise_A"]),
                        "coil_current_measurement_seed": int(cfg["seed_base"]) + 1000 * int(actual_delay) + 100 * int(round(10 * float(actual_slew))) + repeat,
                        "controller_variant": "paired_calibration_only",
                    }
                    calibration_spec = _make_spec(
                        phase="precontrol_calibration",
                        scenario=f"paired_cal_{group}_r{repeat}",
                        category="paired_calibration",
                        target=None,
                        controller_scale=0.0,
                        environment_variant=variant_id,
                        extra=calibration_extra,
                    )
                    main_extra = _main_extra(
                        ctx,
                        variant="r7_paired_precalibrated_monitor",
                        actual_delay=int(actual_delay),
                        actual_slew=float(actual_slew),
                        modeled_delay=0,
                        modeled_slew=1.0,
                        horizon_steps=horizon,
                        calibration_row={
                            "experiment_id": calibration_spec["experiment_id"],
                            "calibration_profile": "confirmation_noisy",
                        },
                    )
                    main_extra["adaptive_delay_slew_estimator"] = _confidence_estimator_cfg(ctx)
                    main_template = _make_spec(
                        phase="paired_confirmation_main",
                        scenario=f"paired_main_{group}_r{repeat}",
                        category="paired_confirmation_main",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra=main_extra,
                    )
                    outer = _make_spec(
                        phase="paired_confirmation",
                        scenario=f"paired_{group}_r{repeat}",
                        category="paired_confirmation",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra={
                            "confirmation_group": group,
                            "confirmation_repeat": repeat,
                            "action_delay_steps": int(actual_delay),
                            "slew_scale": float(actual_slew),
                            "paired_calibration_spec": calibration_spec,
                            "paired_main_spec_template": main_template,
                        },
                    )
                    specs.append(outer)
    return specs


def summarize_confirmation(ctx: Stage41R7Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["confirmation"]
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get("confirmation_group", "")), []).append(row)
    required_repeats = int(cfg["repeats_per_group"])
    expected_groups = {
        f"d{int(delay)}_s{float(slew):.1f}_{target['target_id']}"
        for delay in cfg["actual_delay_steps"]
        for slew in cfg["actual_slew_scales"]
        for target in cfg["targets"]
    }
    expected_repeat_ids = set(range(required_repeats))
    group_rows = []
    for group, subset in sorted(groups.items()):
        repeat_ids = [_as_int(row.get("confirmation_repeat"), -999) for row in subset]
        repeat_coverage_complete = bool(
            len(subset) == required_repeats and set(repeat_ids) == expected_repeat_ids
        )
        group_rows.append({
            "confirmation_group": group,
            "repeats": len(subset),
            "repeat_ids": sorted(repeat_ids),
            "repeat_coverage_complete": repeat_coverage_complete,
            "all_success": all(_as_bool(row.get("success")) for row in subset),
            "all_calibrations_successful": all(_as_bool(row.get("paired_calibration_success")) for row in subset),
            "all_calibrations_correct": all(
                _as_int(row.get("paired_calibration_estimated_delay_steps"), -999)
                == _as_int(row.get("actual_action_delay_steps"), -998)
                and math.isclose(
                    _as_float(row.get("paired_calibration_estimated_slew_scale"), 1e9),
                    _as_float(row.get("actual_slew_scale"), -1e9),
                    abs_tol=1e-12,
                )
                for row in subset
            ),
            "all_main_controls_executed": all(
                _as_bool(row.get("paired_main_control_executed"), True) for row in subset
            ),
            "all_tracking_pass": all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in subset),
            "minimum_margin": min((_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in subset), default=-1e12),
        })
    required_groups = int(cfg["minimum_distinct_groups"])
    expected_ray_tasks = len(expected_groups) * required_repeats
    coverage_complete = bool(
        len(rows) == expected_ray_tasks
        and len(expected_groups) >= required_groups
        and set(groups) == expected_groups
        and all(row["repeat_coverage_complete"] for row in group_rows)
    )
    passed = bool(
        coverage_complete
        and all(
            row["all_success"]
            and row["all_calibrations_successful"]
            and row["all_calibrations_correct"]
            and row["all_main_controls_executed"]
            and row["all_tracking_pass"]
            for row in group_rows
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "paired_confirmation",
        "n_ray_tasks": len(rows),
        "expected_ray_tasks": expected_ray_tasks,
        "n_tsc_episodes": sum(
            _as_int(row.get("paired_tsc_episode_count"), 2) for row in rows
        ),
        "n_successful_tasks": sum(_as_bool(row.get("success")) for row in rows),
        "distinct_groups_confirmed": len(group_rows),
        "coverage_complete": coverage_complete,
        "passed": passed,
        "group_summaries": group_rows,
    }


def run_confirmation(ctx: Stage41R7Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_confirmation_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.confirmation / "raw", backend=backend, resume=resume) if specs else []
    rows = [control_result_row(ctx, result) for result in results]
    summary = summarize_confirmation(ctx, rows)
    write_csv(ctx.paths.confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.confirmation / "results.json", rows)
    write_csv(ctx.paths.confirmation / "group_summary.csv", summary["group_summaries"])
    atomic_write_json(ctx.paths.confirmation / "summary.json", summary)
    _update_state(ctx, confirmation_complete=True, confirmation_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Analysis/execution
# ---------------------------------------------------------------------------


def analyze(ctx: Stage41R7Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    calibration = state.get("calibration_summary") or {}
    startup = state.get("startup_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    confirmation = state.get("confirmation_summary") or {}
    primary_pass = bool(
        source.get("passed")
        and calibration.get("passed")
        and startup.get("precalibrated_startup_passed")
        and confirmation.get("passed")
    )
    restart_available = bool(restart.get("true_restart_validation_available", False))
    if primary_pass and not restart_available:
        verdict = "PASS_STAGE4_1R7_PRECONTROL_CALIBRATION_AND_QUEUE_CONSISTENT_STARTUP_CONFIRMED_TRUE_RESTART_NOT_AVAILABLE"
    elif primary_pass:
        verdict = "PASS_STAGE4_1R7_PRECONTROL_CALIBRATION_AND_QUEUE_CONSISTENT_STARTUP_CONFIRMED_TRUE_RESTART_NOT_YET_VALIDATED"
    else:
        verdict = "STAGE4_1R7_PRECONTROL_CALIBRATION_STARTUP_CLOSURE_INCOMPLETE"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r6_run": str(ctx.source_stage41r6_run),
        "source_audit_passed": bool(source.get("passed", False)),
        "precontrol_calibration_passed": bool(calibration.get("passed", False)),
        "queue_consistent_startup_passed": bool(startup.get("precalibrated_startup_passed", False)),
        "paired_confirmation_passed": bool(confirmation.get("passed", False)),
        "true_restart_validation_available": restart_available,
        "true_restart_validation_performed": False,
        "finite_precontrol_calibration_startup_envelope_validated": primary_pass,
        "precontrol_calibration_uses_separate_reset_episode": True,
        "hardware_pre_shot_calibration_validated": False,
        "online_change_point_handover_validated": False,
        "cold_start_deployment_validated": False,
        "deployment_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "warning": "The calibration is a separate-reset digital-twin POC. It validates parameter acquisition before the frozen main trajectory, not an in-shot hardware calibration sequence.",
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "precontrol_calibration": calibration,
            "queue_consistent_startup": startup,
            "restart_audit": restart,
            "paired_confirmation": confirmation,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r7_analysis_summary.json", summary)
    atomic_write_json(ctx.paths.analysis / "stage4_1r7_verdict.json", summary)
    stop_reason = str(state.get("stop_reason", "")).strip() or "pipeline_complete"
    _update_state(ctx, finished=True, stop_reason=stop_reason, analysis_summary=summary)
    return summary


def execute(
    *,
    config_path: str | Path,
    source_stage41r6_run: str | Path | None,
    run_dir: str | Path | None,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx = load_stage41r7_config(
        config_path,
        source_stage41r6_run=source_stage41r6_run,
        run_dir_override=run_dir,
    )
    initialize_run(ctx)
    if command in {"all", "audit"}:
        audit = run_source_audit(ctx)
        if command == "audit":
            return read_json(ctx.paths.state)
        if not audit.get("passed"):
            _update_state(ctx, finished=True, stop_reason="source_audit_failed")
            return analyze(ctx)
    if command in {"all", "calibrate"}:
        calibration = run_calibration(ctx, backend=backend, resume=resume)
        if command == "calibrate":
            return read_json(ctx.paths.state)
        if not calibration.get("passed"):
            _update_state(ctx, finished=True, stop_reason="precontrol_calibration_failed")
            return analyze(ctx)
    if command in {"all", "startup"}:
        startup = run_startup(ctx, backend=backend, resume=resume)
        if command == "startup":
            return read_json(ctx.paths.state)
        if not startup.get("precalibrated_startup_passed"):
            _update_state(ctx, finished=True, stop_reason="queue_consistent_startup_failed")
            return analyze(ctx)
    if command in {"all", "restart"}:
        run_restart_audit(ctx)
        if command == "restart":
            return read_json(ctx.paths.state)
    if command in {"all", "confirm"}:
        confirmation = run_confirmation(ctx, backend=backend, resume=resume)
        if command == "confirm":
            return read_json(ctx.paths.state)
        if not confirmation.get("passed"):
            _update_state(ctx, finished=True, stop_reason="paired_confirmation_failed")
            return analyze(ctx)
    if command in {"all", "analyze"}:
        return analyze(ctx)
    if command == "prepare":
        return read_json(ctx.paths.state)
    raise ValueError(f"unsupported command {command!r}")


def self_test() -> dict[str, Any]:
    scheduler = r3.PhysicalCoilScheduler(
        modes_tsc=np.eye(14, 3),
        nominal_max_delta_a=3.0,
        command_max_delta_a=3.0,
        min_current=-1e6 * np.ones(14),
        max_current=1e6 * np.ones(14),
        lower_mode=np.array([-2.6, -2.6, -0.9]),
        upper_mode=np.array([2.6, 2.6, 0.9]),
    )
    # Mirrors the packaged bounded zero-net v2 plan.  The largest physical
    # coil increment stays well below the 3 A/10 ms nominal slew, while the
    # signal-to-noise ratio remains sufficient for the packaged 20 mA
    # current-measurement diagnostic profile.
    plan = np.asarray([
        [0.72, 0.00, 0.00],
        [0.00, -0.60, 0.00],
        [-0.72, 0.00, 0.00],
        [0.00, 0.60, 0.00],
        [0.00, 0.00, 0.24],
        [0.00, 0.00, -0.24],
        [0.36, 0.30, 0.00],
        [-0.36, -0.30, 0.00],
        [0.00, 0.00, 0.00],
        [0.00, 0.00, 0.00],
    ], dtype=float)
    results = []
    profiles = (("clean", 0.0, 71000), ("noisy_20mA", 0.02, 72000))
    for actual_delay in (0, 1, 2):
        for actual_slew in (0.9, 1.0, 1.1):
            for profile_id, noise_sigma, seed_base in profiles:
                bank = r3.DelaySlewHypothesisBank(
                    scheduler=scheduler,
                    delay_candidates=(0, 1, 2),
                    slew_candidates=(0.9, 1.0, 1.1),
                    score_decay=0.92,
                    minimum_observations=2,
                    switch_hysteresis_fraction=0.03,
                    initial_delay_steps=0,
                    initial_slew_scale=1.0,
                    minimum_confidence_ratio=5.0,
                    minimum_absolute_score_gap=1e-10,
                    consecutive_best_observations=2,
                    require_unique_best=True,
                    tie_relative_tolerance=1e-9,
                    tie_absolute_tolerance=1e-12,
                )
                currents = np.zeros(14)
                issued: list[np.ndarray] = []
                zero_nominal = np.zeros_like(plan)
                rng = np.random.default_rng(
                    int(seed_base) + 100 * int(actual_delay) + int(round(10 * actual_slew))
                )
                for step, command in enumerate(plan):
                    issued.append(command.copy())
                    issue_index = step - actual_delay
                    applied = np.zeros(3) if issue_index < 0 else issued[issue_index]
                    actual_delta = scheduler.predicted_delta_a(
                        applied, currents, np.ones(3), actual_slew
                    )
                    measured_delta = actual_delta + rng.normal(
                        0.0, noise_sigma, size=14
                    )
                    bank.update(
                        step=step,
                        observed_delta_a=measured_delta,
                        currents_before_a=currents,
                        issued_commands=issued,
                        nominal_commands=zero_nominal,
                        gain_for_prediction=np.ones(3),
                    )
                    currents += actual_delta
                summary = bank.summary()
                results.append(
                    int(summary["selected_delay_steps"]) == actual_delay
                    and math.isclose(
                        float(summary["selected_slew_scale"]),
                        actual_slew,
                        abs_tol=1e-12,
                    )
                    and summary["first_confident_lock_step"] is not None
                )
    return {
        "stage": STAGE,
        "profiles_tested": [item[0] for item in profiles],
        "pairs_tested": len(results),
        "pairs_correct": sum(results),
        "passed": bool(results and all(results)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage4.1R7 bounded pre-control calibration and queue-consistent startup closure")
    parser.add_argument(
        "--config",
        default="configs/stage4_1r7_precontrol_calibration_queue_startup_370ms.json",
    )
    parser.add_argument("--source-stage4-1r6-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument(
        "--command",
        default="all",
        choices=["all", "prepare", "audit", "calibrate", "startup", "restart", "confirm", "analyze"],
    )
    parser.add_argument("--backend", default="ray", choices=["ray", "serial"])
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        payload = self_test()
        print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))
        if not payload["passed"]:
            raise SystemExit(1)
        return
    payload = execute(
        config_path=args.config,
        source_stage41r6_run=args.source_stage4_1r6_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
