"""Stage4.1R6 confidence-gated persistent-prior startup closure.

This revision consumes a completed Stage4.1R5 run.  It keeps the validated
Stage3.4 target-conditioned MPC, the Stage4.1R3 control-aware observer, and the
physical 14-coil scheduler frozen.  It addresses the startup-architecture
failure isolated by R5:

* tied finite-bank scores no longer count as a lock;
* unchanged models do not trigger a destructive handover reset;
* persistent/pre-shot parameter estimates are treated as the normal path;
* adjacent priors use confidence-gated monitoring and a physical-coil-space
  handover blend;
* a conservative common-prefix cold start is retained as a diagnostic rather
  than silently being promoted to deployment success.

The result remains a finite research envelope, not deployment qualification.
"""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
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
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

SCHEMA_VERSION = 1
STAGE = "Stage4.1R6"
CONTROLLER_REVISION = "confidence_gated_persistent_prior_physical_handover_v6"
EXPECTED_SOURCE_STAGE = "Stage4.1R5"
EXPECTED_SOURCE_REVISION = "confidence_gated_bumpless_delay_slew_handover_v5"
STATE_FILENAME = "stage4_1r6_state.json"
MANIFEST_FILENAME = "stage4_1r6_manifest.json"


# Reuse the strict JSON implementation that has already survived the Stage4
# campaigns.  Aliases are kept explicit so this module remains readable.
utc_timestamp = r5.utc_timestamp
_json_safe = r5._json_safe
read_json = r5.read_json
read_json_gz = r5.read_json_gz
atomic_write_json = r5.atomic_write_json
atomic_write_json_gz = r5.atomic_write_json_gz
write_csv = r5.write_csv
read_csv = r5.read_csv
_as_bool = r5._as_bool
_as_float = r5._as_float
_as_int = r5._as_int
_sha256_file = r5._sha256_file
_result_complete = r5._result_complete


def _scenario_digest(*parts: Any, prefix: str = "s41r6") -> str:
    raw = json.dumps(_json_safe(parts), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:20]}"


def _array_digest(array: np.ndarray, prefix: str) -> str:
    arr = np.round(np.asarray(array, dtype=float), 12)
    return f"{prefix}_{hashlib.sha256(arr.tobytes()).hexdigest()[:20]}"


@dataclass(frozen=True)
class Stage41R6Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_audit: Path
    estimator_confirmation: Path
    startup: Path
    restart: Path
    confirmation: Path
    analysis: Path
    variants: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R6Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_audit=run_dir / "stage4_1r6_source_audit",
            estimator_confirmation=run_dir / "stage4_1r6_estimator_confirmation",
            startup=run_dir / "stage4_1r6_static_startup",
            restart=run_dir / "stage4_1r6_restart_audit",
            confirmation=run_dir / "stage4_1r6_confirmation",
            analysis=run_dir / "stage4_1r6_analysis",
            variants=run_dir / "stage4_1r6_environment_variants",
            source_reference=run_dir / "source_stage4_1r5_reference",
        )


@dataclass
class Stage41R6Context:
    cfg: dict[str, Any]
    paths: Stage41R6Paths
    project_dir: Path
    source_stage41r5_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_verdict: dict[str, Any]
    source_r5_cfg: dict[str, Any]
    source_stage41r4_run: Path
    r5_ctx: r5.Stage41R5Context
    source_fingerprint: dict[str, Any]


def resolve_source_stage41r5_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE4_1R5_RUN", "").strip()
    if not value:
        raise ValueError("Stage4.1R6 requires --source-stage4-1r5-run or SOURCE_STAGE4_1R5_RUN")
    run = Path(value).expanduser().resolve()
    required = [
        run / "stage4_1r5_manifest.json",
        run / "stage4_1r5_state.json",
        run / "stage4_1r5_config.resolved.json",
        run / "stage4_1r5_analysis/stage4_1r5_verdict.json",
        run / "stage4_1r5_estimator_only_confirmation/summary.json",
        run / "stage4_1r5_static_handover/summary.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage4.1R5 source run: " + ", ".join(missing))
    return run


def _resolve_source_r4(project_dir: Path, manifest: dict[str, Any]) -> Path:
    raw = str(manifest.get("source_stage4_1r4_run", "")).strip()
    if not raw:
        raise ValueError("Stage4.1R5 manifest has no source_stage4_1r4_run")
    path = Path(raw).expanduser()
    path = path.resolve() if path.is_absolute() else (project_dir / path).resolve()
    if not path.exists():
        fallback = project_dir / "stage4_1r4_runs" / path.name
        if fallback.exists():
            path = fallback.resolve()
    if not (path / "stage4_1r4_manifest.json").exists():
        raise FileNotFoundError(f"Stage4.1R4 source is unavailable: {path}")
    return path


def _source_inventory(source_r5: Path) -> dict[str, Any]:
    include = [
        source_r5 / "stage4_1r5_manifest.json",
        source_r5 / "stage4_1r5_state.json",
        source_r5 / "stage4_1r5_config.resolved.json",
        source_r5 / "stage4_1r5_analysis/stage4_1r5_verdict.json",
        source_r5 / "stage4_1r5_estimator_only_confirmation/summary.json",
        source_r5 / "stage4_1r5_static_handover/summary.json",
        source_r5 / "stage4_1r5_estimator_only_confirmation/results.json",
        source_r5 / "stage4_1r5_static_handover/results.json",
    ]
    include.extend(sorted((source_r5 / "stage4_1r5_estimator_only_confirmation/raw").glob("*.json.gz")))
    include.extend(sorted((source_r5 / "stage4_1r5_static_handover/raw").glob("*.json.gz")))
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    total = 0
    for path in include:
        if not path.is_file():
            continue
        relative = str(path.relative_to(source_r5))
        sha = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"relative_path": relative, "sha256": sha, "bytes": size})
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        digest.update(sha.encode("ascii")); digest.update(b"\n")
        total += size
    return {"n_files": len(entries), "total_bytes": total, "digest": digest.hexdigest(), "entries": entries}


def validate_source(cfg: dict[str, Any], manifest: dict[str, Any], state: dict[str, Any]) -> None:
    if str(manifest.get("stage")) != EXPECTED_SOURCE_STAGE:
        raise ValueError(f"source stage must be {EXPECTED_SOURCE_STAGE}")
    if str(manifest.get("controller_revision")) != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R5 controller revision is unsupported")
    if not bool(state.get("finished", False)):
        raise ValueError("source Stage4.1R5 run is not finished")
    source_audit = state.get("source_audit_summary") or {}
    estimator = state.get("estimator_only_summary") or {}
    static = state.get("static_handover_summary") or {}
    if not bool(source_audit.get("passed", False)):
        raise ValueError("source Stage4.1R5 audit did not pass")
    if not bool(estimator.get("passed", False)):
        raise ValueError("source Stage4.1R5 final finite-bank identification did not pass")
    if not math.isclose(
        float(static.get("persistent_exact_preservation_fraction", math.nan)),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("source Stage4.1R5 did not preserve the exact persistent model")
    if not bool(cfg["source_requirement"].get("allow_source_static_handover_failure", True)) and not bool(static.get("passed", False)):
        raise ValueError("source Stage4.1R5 static handover did not pass")


def validate_config(cfg: dict[str, Any], source_cfg: dict[str, Any]) -> None:
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R6 controller_revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.1R6 complete package is configured for 128 workers")
    for key in (
        "precise_tolerance_m", "relaxed_tolerance_m", "required_arrival_streak_steps",
        "terminal_velocity_max_m_per_s", "late_velocity_rms_max_m_per_s",
        "late_window_steps", "ip_safety_tolerance_A",
    ):
        if not math.isclose(float(cfg["gate"][key]), float(source_cfg["gate"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.1R6 hard gate {key} differs from source")
    for key in ("terminal_abs_tolerance_A", "hold_rms_tolerance_A", "sustained_max_tolerance_A"):
        if not math.isclose(
            float(cfg["gate"]["ip_tracking"][key]),
            float(source_cfg["gate"]["ip_tracking"][key]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"Stage4.1R6 Ip threshold {key} differs from source")
    confidence = cfg["confidence_gate"]
    if float(confidence["minimum_confidence_ratio"]) <= 1.0:
        raise ValueError("Stage4.1R6 requires a confidence ratio strictly above one")
    if int(confidence["consecutive_best_observations"]) < 2:
        raise ValueError("Stage4.1R6 requires at least two consecutive best observations")
    if not bool(confidence.get("require_unique_best", True)):
        raise ValueError("Stage4.1R6 requires a unique best hypothesis")


def load_stage41r6_config(
    config_path: str | Path,
    *,
    source_stage41r5_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage41R6Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = base.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)},
    )
    source_r5 = resolve_source_stage41r5_run(source_stage41r5_run)
    source_manifest = read_json(source_r5 / "stage4_1r5_manifest.json")
    source_state = read_json(source_r5 / "stage4_1r5_state.json")
    source_verdict = read_json(source_r5 / "stage4_1r5_analysis/stage4_1r5_verdict.json")
    source_r5_cfg = read_json(source_r5 / "stage4_1r5_config.resolved.json")
    validate_source(cfg, source_manifest, source_state)
    validate_config(cfg, source_r5_cfg)
    source_r4 = _resolve_source_r4(project_dir, source_manifest)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage4_1r6_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r6_startup_architecture_closure_350ms')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)
    r5_ctx = r5.load_stage41r5_config(
        source_r5 / "stage4_1r5_config.resolved.json",
        source_stage41r4_run=source_r4,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    env_cfg = copy.deepcopy(r5_ctx.r4_ctx.r3_ctx.source_env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"].get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_1R6_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"])).expanduser().resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R6_TSC_RUN_ROOT", storage["tsc_run_root"])).expanduser().resolve()
    )
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    r5_ctx.r4_ctx.r3_ctx.source_env_cfg = env_cfg
    r5_ctx.r4_ctx.r3_ctx.base34.env_cfg = copy.deepcopy(env_cfg)
    r5_ctx.r4_ctx.r3_ctx.source_train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    return Stage41R6Context(
        cfg=cfg,
        paths=Stage41R6Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r5_run=source_r5,
        source_manifest=source_manifest,
        source_state=source_state,
        source_verdict=source_verdict,
        source_r5_cfg=source_r5_cfg,
        source_stage41r4_run=source_r4,
        r5_ctx=r5_ctx,
        source_fingerprint=_source_inventory(source_r5),
    )


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "estimator_confirmation_complete": False,
        "startup_complete": False,
        "restart_audit_complete": False,
        "confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R6Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def resource_preflight(cfg: dict[str, Any]) -> dict[str, Any]:
    requested = int(os.environ.get("STAGE4_1R6_WORKERS", cfg["parallel"]["n_workers"]))
    logical = int(os.cpu_count() or 1)
    reserve = int(cfg["parallel"].get("reserve_logical_cpus", 16))
    safe = max(1, logical - reserve)
    if requested > safe:
        raise RuntimeError(
            f"Stage4.1R6 requests {requested} workers, but {logical} logical CPUs are visible "
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


def initialize_run(ctx: Stage41R6Context) -> None:
    for path in (
        ctx.paths.run_dir, ctx.paths.source_audit, ctx.paths.estimator_confirmation,
        ctx.paths.startup, ctx.paths.restart, ctx.paths.confirmation,
        ctx.paths.analysis, ctx.paths.variants, ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.run_dir / "stage4_1r6_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.r5_ctx.r4_ctx.r3_ctx.source_train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg)
    workers = resource_preflight(ctx.cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r5_run": str(ctx.source_stage41r5_run),
        "source_stage4_1r4_run": str(ctx.source_stage41r4_run),
        "source_fingerprint": {k: v for k, v in ctx.source_fingerprint.items() if k != "entries"},
        "workers": workers,
        "hard_numeric_thresholds_changed": False,
        "precalibrated_persistent_startup_is_primary": True,
        "cold_start_is_diagnostic": True,
        "finite_test_envelope_only": True,
        "deployment_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if str(old.get("controller_revision")) != CONTROLLER_REVISION:
            raise ValueError("existing Stage4.1R6 run uses another controller revision")
        if str((old.get("source_fingerprint") or {}).get("digest")) != str(ctx.source_fingerprint["digest"]):
            raise ValueError("source Stage4.1R5 content changed")
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    inventory = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory.exists():
        atomic_write_json(inventory, ctx.source_fingerprint)
    for relative in (
        "stage4_1r5_manifest.json", "stage4_1r5_state.json", "stage4_1r5_config.resolved.json",
        "stage4_1r5_analysis/stage4_1r5_verdict.json",
        "stage4_1r5_estimator_only_confirmation/summary.json",
        "stage4_1r5_static_handover/summary.json",
    ):
        src = ctx.source_stage41r5_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())


# ---------------------------------------------------------------------------
# Worker/evaluation
# ---------------------------------------------------------------------------


def materialize_variant(
    ctx: Stage41R6Context, *, slew_scale: float, horizon_steps: int = 35,
    start_folder: str | None = None,
) -> tuple[str, dict[str, Any]]:
    return r5.materialize_variant(
        ctx.r5_ctx, slew_scale=float(slew_scale), horizon_steps=int(horizon_steps), start_folder=start_folder
    )


class LocalStage41R6Worker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str):
        self.inner = r5.LocalStage41R5Worker(payload, library, bundle, worker_id)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.inner.evaluate(spec)
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r6_controller_revision"] = CONTROLLER_REVISION
        return _json_safe(result)

    def close(self) -> None:
        self.inner.close()


def _ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id):
            self.worker = LocalStage41R6Worker(payload, library, bundle, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor


def evaluate_specs(
    ctx: Stage41R6Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        variant = str(spec["environment_variant"])
        if variant not in ctx.r5_ctx.r4_ctx.variants:
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
            worker = LocalStage41R6Worker(
                ctx.r5_ctx.r4_ctx.variants[variant],
                ctx.r5_ctx.r4_ctx.r3_ctx.source_library,
                ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle,
                f"stage41r6_{variant}_serial",
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate(spec))
                    print(f"[Stage4.1R6 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(os.environ.get("STAGE4_1R6_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R6 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()},
            plan.actor_count,
        )
        print(
            "[Stage4.1R6 mixed-variant] actor_allocation="
            + json.dumps(allocation, sort_keys=True, separators=(",", ":")),
            flush=True,
        )
        Actor = _ray_actor_class()
        actors_by_variant: dict[str, list[Any]] = {}
        all_actors: list[Any] = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(
                    ctx.r5_ctx.r4_ctx.variants[variant],
                    ctx.r5_ctx.r4_ctx.r3_ctx.source_library,
                    ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle,
                    f"stage41r6_{variant}_{index:03d}",
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
                    print(f"[Stage4.1R6 mixed-variant] waiting {done}/{total_pending}", flush=True)
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
                        print(f"[Stage4.1R6 mixed-variant] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(
                all_actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


# ---------------------------------------------------------------------------
# Specs and metrics
# ---------------------------------------------------------------------------


def _make_spec(
    *, phase: str, scenario: str, category: str, target: dict[str, Any],
    controller_scale: float, environment_variant: str, extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = copy.deepcopy(extra or {})
    identity = {
        "revision": CONTROLLER_REVISION, "phase": phase, "scenario": scenario,
        "category": category, "target": target, "controller_scale": controller_scale,
        "environment_variant": environment_variant, "extra": extra,
    }
    return {
        "kind": "stage4_1r6_startup_architecture_closure",
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


def _confidence_estimator_cfg(
    ctx: Stage41R6Context, *, initial_delay: int, initial_slew: float,
) -> dict[str, Any]:
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


def _adjacent_delay(actual_delay: int) -> int:
    return int(actual_delay - 1 if actual_delay > 0 else 1)


def _adjacent_slew(actual_slew: float) -> float:
    if math.isclose(actual_slew, 0.9, abs_tol=1e-12):
        return 1.0
    if math.isclose(actual_slew, 1.1, abs_tol=1e-12):
        return 1.0
    return 0.9


def _target_interpolation(ctx: Stage41R6Context, target: dict[str, Any]) -> dict[str, Any]:
    offset = np.asarray([
        target.get("R_offset_m", 0.0), target.get("Z_offset_m", 0.0), target.get("Ip_offset_A", 0.0)
    ], dtype=float)
    stub = ctx.r5_ctx.r4_ctx.r3_ctx.base34
    return r3.s34.interpolation_for_target(stub, ctx.r5_ctx.r4_ctx.r3_ctx.source_library, offset)


def common_prefix_plan(ctx: Stage41R6Context, target: dict[str, Any]) -> np.ndarray:
    interpolation = _target_interpolation(ctx, target)
    nominal = np.asarray(interpolation["full_control_vector"], dtype=float).reshape(35, 3)
    cfg = ctx.cfg["static_startup"]["cold_common_prefix"]
    delays = list(map(int, ctx.cfg["confidence_gate"]["delay_candidates"]))
    scale = float(cfg["physical_scale_fraction"])
    plan = np.zeros_like(nominal)
    for step in range(len(nominal)):
        shifted = [nominal[max(0, step - delay)] for delay in delays]
        plan[step] = scale * np.mean(np.asarray(shifted, dtype=float), axis=0)
    lower = np.asarray(ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper = np.asarray(ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg["trajectory"]["coefficient_upper"], dtype=float)
    return np.clip(plan, lower, upper)


def _task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id", "scenario"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False, "mandatory": False, "parents": [], "category": str(spec.get("category", "r6")),
    }


def result_row(ctx: Stage41R6Context, result: dict[str, Any]) -> dict[str, Any]:
    metric_ctx = type("MetricCtx", (), {
        "cfg": copy.deepcopy(ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg),
        "env_cfg": ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg,
    })()
    metrics = r3.s34.target_metrics(metric_ctx, _task_from_spec(result["spec"]), result, None)
    spec = result["spec"]
    estimator = result.get("adaptive_estimator_summary") or {}
    handover = result.get("adaptive_handover_summary") or {}
    trace = result.get("control_trace") or []
    trajectory = result.get("trajectory") or []
    if trajectory:
        state_array = np.asarray(
            [[row["R"], row["Z"], row["Ip"], *row["currents_a_tsc"]] for row in trajectory], dtype=float
        )
        trajectory_signature = _array_digest(state_array, "traj")
        currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
        deltas = np.diff(currents, axis=0)
    else:
        trajectory_signature = ""
        deltas = np.empty((0, 14), dtype=float)
    issued = np.asarray([item.get("issued_mode_coefficients", [0.0, 0.0, 0.0]) for item in trace], dtype=float)
    command_signature = _array_digest(issued, "cmd") if len(issued) else ""
    events = list(handover.get("events", []))
    event_jumps: list[float] = []
    for event in events:
        step = int(event.get("applied_at_step", -1))
        if 1 <= step < len(deltas):
            event_jumps.append(float(np.sqrt(np.mean((deltas[step] - deltas[step - 1]) ** 2))))
    actual_delay = int(spec.get("action_delay_steps", 0))
    actual_slew = float(spec.get("slew_scale", 1.0))
    lock_events = list(estimator.get("lock_events", []))
    incorrect_lock_count = sum(
        int(event.get("delay_steps", -999)) != actual_delay
        or not math.isclose(float(event.get("slew_scale", 1e9)), actual_slew, abs_tol=1e-12)
        for event in lock_events
    )
    return {
        "experiment_id": result["experiment_id"],
        "phase": spec.get("phase"),
        "scenario": spec.get("scenario"),
        "category": spec.get("category"),
        "target_id": spec.get("target_id"),
        "controller_variant": spec.get("controller_variant"),
        "controller_scale": float(spec.get("controller_scale", 0.0)),
        "environment_variant": spec.get("environment_variant"),
        "actual_action_delay_steps": actual_delay,
        "actual_slew_scale": actual_slew,
        "initial_estimated_delay_steps": int((spec.get("adaptive_delay_slew_estimator") or {}).get("initial_delay_steps", spec.get("controller_action_delay_steps", 0))),
        "initial_estimated_slew_scale": float((spec.get("adaptive_delay_slew_estimator") or {}).get("initial_slew_scale", spec.get("controller_slew_scale_estimate", 1.0))),
        "adaptive_estimator_enabled": bool((spec.get("adaptive_delay_slew_estimator") or {}).get("enabled", False)),
        "adaptive_estimated_delay_steps": estimator.get("selected_delay_steps"),
        "adaptive_estimated_slew_scale": estimator.get("selected_slew_scale"),
        "adaptive_estimator_observations": estimator.get("observations"),
        "adaptive_estimator_first_any_selection_step": estimator.get("first_any_selection_step"),
        "adaptive_estimator_first_confident_lock_step": estimator.get("first_confident_lock_step"),
        "adaptive_estimator_confidence_ratio": estimator.get("confidence_ratio"),
        "adaptive_estimator_score_gap": estimator.get("score_gap"),
        "adaptive_estimator_best_streak": estimator.get("best_streak"),
        "adaptive_estimator_lock_events": lock_events,
        "adaptive_estimator_incorrect_lock_count": incorrect_lock_count,
        "adaptive_estimator_transitions": estimator.get("transitions"),
        "handover_enabled": bool(handover.get("enabled", False)),
        "handover_event_count": len(events),
        "handover_noop_event_count": sum(
            int(event.get("old_delay_steps", -1)) == int(event.get("new_delay_steps", -2))
            and math.isclose(float(event.get("old_slew_scale", -1.0)), float(event.get("new_slew_scale", -2.0)), abs_tol=1e-12)
            for event in events
        ),
        "handover_model_switch_count": sum(str(event.get("event_type")) == "model_switch" for event in events),
        "handover_confidence_release_count": sum(str(event.get("event_type")) == "confidence_release" for event in events),
        "handover_physical_blend_steps": int(handover.get("physical_blend_steps", 0)),
        "handover_events": events,
        "handover_max_event_delta_jump_rms_a": max(event_jumps, default=0.0),
        "max_scheduler_predicted_mismatch_rms_a": max((float(item.get("scheduler_predicted_mismatch_rms_a", 0.0)) for item in trace), default=0.0),
        "max_scheduler_actual_mismatch_rms_a": max((float(item.get("scheduler_actual_mismatch_rms_a", 0.0)) for item in trace), default=0.0),
        "trajectory_signature": trajectory_signature,
        "issued_command_signature": command_signature,
        "success": bool(result.get("success", False)),
        **metrics,
    }


# ---------------------------------------------------------------------------
# Source replay and estimator confirmation
# ---------------------------------------------------------------------------


def _scheduler_for_context(ctx: Stage41R6Context) -> r3.PhysicalCoilScheduler:
    base34 = ctx.r5_ctx.r4_ctx.r3_ctx.base34
    r3ctx = ctx.r5_ctx.r4_ctx.r3_ctx
    schedule_cfg = r3ctx.cfg["controller_upgrade"]["gain_slew_scheduling"]
    return r3.PhysicalCoilScheduler(
        modes_tsc=np.asarray(r3ctx.base34.modes_tsc, dtype=float),
        nominal_max_delta_a=float(r3ctx.base34.max_delta_a),
        command_max_delta_a=float(r3ctx.base34.max_delta_a),
        min_current=np.asarray(r3ctx.base34.min_current_tsc, dtype=float),
        max_current=np.asarray(r3ctx.base34.max_current_tsc, dtype=float),
        lower_mode=np.asarray(base34.cfg["trajectory"]["coefficient_lower"], dtype=float),
        upper_mode=np.asarray(base34.cfg["trajectory"]["coefficient_upper"], dtype=float),
        regularization=float(schedule_cfg.get("physical_inverse_regularization", 1e-4)),
    )


def _replay_source_estimator(ctx: Stage41R6Context) -> list[dict[str, Any]]:
    scheduler = _scheduler_for_context(ctx)
    rows: list[dict[str, Any]] = []
    for path in sorted((ctx.source_stage41r5_run / "stage4_1r5_estimator_only_confirmation/raw").glob("*.json.gz")):
        payload = read_json_gz(path)
        spec = payload["spec"]
        actual_delay = int(spec.get("action_delay_steps", 0))
        actual_slew = float(spec.get("slew_scale", 1.0))
        estimator_cfg = _confidence_estimator_cfg(ctx, initial_delay=0, initial_slew=1.0)
        bank = r3.DelaySlewHypothesisBank(
            scheduler=scheduler,
            delay_candidates=tuple(estimator_cfg["delay_candidates"]),
            slew_candidates=tuple(estimator_cfg["slew_candidates"]),
            score_decay=float(estimator_cfg["score_decay"]),
            minimum_observations=int(estimator_cfg["minimum_observations"]),
            switch_hysteresis_fraction=float(estimator_cfg["switch_hysteresis_fraction"]),
            initial_delay_steps=0,
            initial_slew_scale=1.0,
            minimum_confidence_ratio=float(estimator_cfg["minimum_confidence_ratio"]),
            minimum_absolute_score_gap=float(estimator_cfg["minimum_absolute_score_gap"]),
            consecutive_best_observations=int(estimator_cfg["consecutive_best_observations"]),
            require_unique_best=bool(estimator_cfg["require_unique_best"]),
            tie_relative_tolerance=float(estimator_cfg["tie_relative_tolerance"]),
            tie_absolute_tolerance=float(estimator_cfg["tie_absolute_tolerance"]),
        )
        trajectory = payload.get("trajectory") or []
        trace = payload.get("control_trace") or []
        issued: list[np.ndarray] = []
        nominal_commands = np.asarray(
            [item.get("issued_mode_coefficients", [0.0, 0.0, 0.0]) for item in trace], dtype=float
        )
        if len(nominal_commands) != len(trace):
            raise RuntimeError("invalid source control trace")
        for step, item in enumerate(trace):
            issued.append(np.asarray(item["issued_mode_coefficients"], dtype=float))
            currents_before = np.asarray(trajectory[step]["currents_a_tsc"], dtype=float)
            currents_after = np.asarray(trajectory[step + 1]["currents_a_tsc"], dtype=float)
            bank.update(
                step=step,
                observed_delta_a=currents_after - currents_before,
                currents_before_a=currents_before,
                issued_commands=issued,
                nominal_commands=nominal_commands,
                gain_for_prediction=np.ones(3),
            )
        summary = bank.summary()
        incorrect = sum(
            int(event["delay_steps"]) != actual_delay
            or not math.isclose(float(event["slew_scale"]), actual_slew, abs_tol=1e-12)
            for event in summary.get("lock_events", [])
        )
        rows.append({
            "source_result": str(path.relative_to(ctx.source_stage41r5_run)),
            "actual_delay_steps": actual_delay,
            "actual_slew_scale": actual_slew,
            "selected_delay_steps": summary["selected_delay_steps"],
            "selected_slew_scale": summary["selected_slew_scale"],
            "first_any_selection_step": summary.get("first_any_selection_step"),
            "first_confident_lock_step": summary.get("first_confident_lock_step"),
            "confidence_ratio": summary.get("confidence_ratio"),
            "score_gap": summary.get("score_gap"),
            "incorrect_confident_lock_count": incorrect,
            "final_correct": bool(
                int(summary["selected_delay_steps"]) == actual_delay
                and math.isclose(float(summary["selected_slew_scale"]), actual_slew, abs_tol=1e-12)
            ),
        })
    return rows


def run_source_audit(ctx: Stage41R6Context) -> dict[str, Any]:
    replay = _replay_source_estimator(ctx)
    static = ctx.source_state.get("static_handover_summary") or {}
    cfg = ctx.cfg["source_replay"]
    replay_pass = bool(
        replay
        and all(row["final_correct"] for row in replay)
        and all(int(row["incorrect_confident_lock_count"]) == 0 for row in replay)
        and max(int(row["first_confident_lock_step"] or 999) for row in replay)
        <= int(cfg["maximum_first_confident_lock_step"])
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r5_run": str(ctx.source_stage41r5_run),
        "source_finished": bool(ctx.source_state.get("finished", False)),
        "source_persistent_exact_preservation_fraction": static.get("persistent_exact_preservation_fraction"),
        "source_unknown_bumpless_preservation_fraction": static.get("unknown_bumpless_preservation_fraction"),
        "source_delay2_unknown_preservation_fraction": static.get("delay2_unknown_bumpless_preservation_fraction"),
        "confidence_replay_cases": len(replay),
        "confidence_replay_final_correct_fraction": float(np.mean([row["final_correct"] for row in replay])) if replay else 0.0,
        "confidence_replay_incorrect_lock_count": sum(int(row["incorrect_confident_lock_count"]) for row in replay),
        "confidence_replay_max_first_confident_lock_step": max((int(row["first_confident_lock_step"] or 999) for row in replay), default=999),
        "confidence_replay_passed": replay_pass,
        "passed": bool(replay_pass),
        "warning": "R5 final identification was correct, but its first_lock_step field was not confidence-gated. R6 recomputes the semantics from raw measured coil-current traces.",
    }
    write_csv(ctx.paths.source_audit / "confidence_replay.csv", replay)
    atomic_write_json(ctx.paths.source_audit / "confidence_replay.json", replay)
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def build_estimator_confirmation_specs(ctx: Stage41R6Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["estimator_confirmation"]
    specs: list[dict[str, Any]] = []
    for actual_slew in cfg["actual_slew_scales"]:
        variant, _ = materialize_variant(ctx, slew_scale=float(actual_slew), horizon_steps=int(cfg["horizon_steps"]))
        for actual_delay in cfg["actual_delay_steps"]:
            for target in cfg["targets"]:
                for repeat in range(int(cfg["repeats_per_case"])):
                    extra = {
                        "horizon_steps": int(cfg["horizon_steps"]),
                        "extended_horizon": False,
                        "slew_scale": float(actual_slew),
                        "controller_slew_scale_estimate": 1.0,
                        "actuator_gain_by_mode": [1.0, 1.0, 1.0],
                        "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
                        "action_delay_steps": int(actual_delay),
                        "controller_action_delay_steps": 0,
                        "prime_action_queue_with_nominal": True,
                        "observer_enabled": True,
                        "observer_variant": "control_aware_residual",
                        "anti_windup_enabled": False,
                        "delay_aware_enabled": True,
                        "gain_slew_scheduling_enabled": True,
                        "phase_aware_reference_enabled": True,
                        "known_control_effect_from_measured_current_increment": True,
                        "controller_variant": "r6_estimator_confirmation",
                        "adaptive_delay_slew_estimator": _confidence_estimator_cfg(ctx, initial_delay=0, initial_slew=1.0),
                        "adaptive_handover": {"enabled": False},
                        "confirmation_group": f"d{int(actual_delay)}_s{float(actual_slew):.1f}",
                        "confirmation_repeat": repeat,
                    }
                    specs.append(_make_spec(
                        phase="estimator_confirmation",
                        scenario=f"{target['target_id']}__d{actual_delay}__s{actual_slew:.1f}__r{repeat}",
                        category="estimator_confirmation",
                        target=target,
                        controller_scale=0.0,
                        environment_variant=variant,
                        extra=extra,
                    ))
    return specs


def summarize_estimator_confirmation(ctx: Stage41R6Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["estimator_confirmation"]
    correct = [
        int(row.get("adaptive_estimated_delay_steps", -999)) == int(row["actual_action_delay_steps"])
        and math.isclose(_as_float(row.get("adaptive_estimated_slew_scale"), 1e9), float(row["actual_slew_scale"]), abs_tol=1e-12)
        for row in rows
    ]
    locks = [int(row.get("adaptive_estimator_first_confident_lock_step") or 999) for row in rows]
    groups: dict[tuple[int, float], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"])), []).append(row)
    group_rows = []
    for key, subset in sorted(groups.items()):
        group_rows.append({
            "actual_delay_steps": key[0],
            "actual_slew_scale": key[1],
            "repeats": len(subset),
            "all_success": all(_as_bool(row.get("success")) for row in subset),
            "all_final_correct": all(
                int(row.get("adaptive_estimated_delay_steps", -999)) == key[0]
                and math.isclose(_as_float(row.get("adaptive_estimated_slew_scale"), 1e9), key[1], abs_tol=1e-12)
                for row in subset
            ),
            "incorrect_confident_lock_count": sum(int(row.get("adaptive_estimator_incorrect_lock_count", 0)) for row in subset),
            "maximum_first_confident_lock_step": max((int(row.get("adaptive_estimator_first_confident_lock_step") or 999) for row in subset), default=999),
        })
    passed = bool(
        rows
        and all(_as_bool(row.get("success")) for row in rows)
        and all(correct)
        and sum(int(row.get("adaptive_estimator_incorrect_lock_count", 0)) for row in rows) == 0
        and max(locks, default=999) <= int(cfg["maximum_first_confident_lock_step"])
        and len(group_rows) == 9
        and all(int(row["repeats"]) >= int(cfg["repeats_per_case"]) for row in group_rows)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "estimator_confirmation",
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "final_identification_fraction": float(np.mean(correct)) if correct else 0.0,
        "incorrect_confident_lock_count": sum(int(row.get("adaptive_estimator_incorrect_lock_count", 0)) for row in rows),
        "maximum_first_confident_lock_step": max(locks, default=999),
        "minimum_final_confidence_ratio": min((_as_float(row.get("adaptive_estimator_confidence_ratio"), 0.0) for row in rows), default=0.0),
        "distinct_pairs_confirmed": len(group_rows),
        "passed": passed,
        "group_summaries": group_rows,
    }


def run_estimator_confirmation(ctx: Stage41R6Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_estimator_confirmation_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.estimator_confirmation / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    summary = summarize_estimator_confirmation(ctx, rows)
    write_csv(ctx.paths.estimator_confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.estimator_confirmation / "results.json", rows)
    write_csv(ctx.paths.estimator_confirmation / "group_summary.csv", summary["group_summaries"])
    atomic_write_json(ctx.paths.estimator_confirmation / "summary.json", summary)
    _update_state(ctx, estimator_confirmation_complete=True, estimator_confirmation_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Static startup architectures
# ---------------------------------------------------------------------------


def _startup_spec(
    ctx: Stage41R6Context, *, variant: str, target: dict[str, Any], actual_delay: int,
    actual_slew: float, environment_variant: str,
) -> dict[str, Any]:
    cfg = ctx.cfg["static_startup"]
    source_scale = float(ctx.r5_ctx.r4_ctx.r3_ctx.source_scale)
    estimator_cfg: dict[str, Any] | None = None
    handover_cfg: dict[str, Any] = {"enabled": False}
    modeled_delay, modeled_slew = actual_delay, actual_slew
    if variant == "oracle":
        pass
    elif variant == "r4_abrupt_unknown":
        modeled_delay, modeled_slew = 0, 1.0
        old = ctx.source_r5_cfg["static_handover"]["estimator"]
        estimator_cfg = {
            "enabled": True,
            "delay_candidates": list(map(int, old["delay_candidates"])),
            "slew_candidates": list(map(float, old["slew_candidates"])),
            "score_decay": float(old["score_decay"]),
            "minimum_observations": int(old["minimum_observations"]),
            "switch_hysteresis_fraction": float(old["switch_hysteresis_fraction"]),
            "initial_delay_steps": 0,
            "initial_slew_scale": 1.0,
        }
    elif variant == "r6_persistent_exact_monitor":
        estimator_cfg = _confidence_estimator_cfg(ctx, initial_delay=actual_delay, initial_slew=actual_slew)
        handover_cfg = copy.deepcopy(cfg["handover"])
        handover_cfg.update({
            "enabled": True,
            "initial_model_trusted": True,
            "safe_start_until_lock": False,
            "suppress_noop_initial_lock_event": True,
        })
    elif variant == "r6_persistent_adjacent_delay":
        modeled_delay, modeled_slew = _adjacent_delay(actual_delay), actual_slew
        estimator_cfg = _confidence_estimator_cfg(ctx, initial_delay=modeled_delay, initial_slew=modeled_slew)
        handover_cfg = copy.deepcopy(cfg["handover"])
        handover_cfg.update({"enabled": True, "initial_model_trusted": True, "safe_start_until_lock": False})
    elif variant == "r6_persistent_adjacent_full":
        modeled_delay, modeled_slew = _adjacent_delay(actual_delay), _adjacent_slew(actual_slew)
        estimator_cfg = _confidence_estimator_cfg(ctx, initial_delay=modeled_delay, initial_slew=modeled_slew)
        handover_cfg = copy.deepcopy(cfg["handover"])
        handover_cfg.update({"enabled": True, "initial_model_trusted": True, "safe_start_until_lock": False})
    elif variant == "r6_cold_common_prefix":
        modeled_delay, modeled_slew = 0, 1.0
        estimator_cfg = _confidence_estimator_cfg(ctx, initial_delay=0, initial_slew=1.0)
        handover_cfg = copy.deepcopy(cfg["handover"])
        handover_cfg.update({
            "enabled": True,
            "initial_model_trusted": False,
            "safe_start_until_lock": True,
            "prelock_controller_scale_fraction": 0.0,
            "prelock_nominal_scale_fraction": float(cfg["cold_common_prefix"]["physical_scale_fraction"]),
            "release_safe_start_on_confident_lock": True,
            "suppress_noop_initial_lock_event": True,
        })
    else:
        raise ValueError(f"unsupported startup variant {variant}")
    extra = {
        "horizon_steps": int(cfg["horizon_steps"]),
        "extended_horizon": False,
        "slew_scale": float(actual_slew),
        "controller_slew_scale_estimate": float(modeled_slew),
        "actuator_gain_by_mode": [1.0, 1.0, 1.0],
        "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
        "action_delay_steps": int(actual_delay),
        "controller_action_delay_steps": int(modeled_delay),
        "prime_action_queue_with_nominal": True,
        "observer_enabled": True,
        "observer_variant": "control_aware_residual",
        "anti_windup_enabled": False,
        "delay_aware_enabled": True,
        "gain_slew_scheduling_enabled": True,
        "phase_aware_reference_enabled": True,
        "known_control_effect_from_measured_current_increment": True,
        "controller_variant": variant,
        "adaptive_handover": handover_cfg,
    }
    if estimator_cfg is not None:
        extra["adaptive_delay_slew_estimator"] = estimator_cfg
    if variant == "r6_cold_common_prefix":
        extra["prelock_common_prefix_physical"] = common_prefix_plan(ctx, target).tolist()
    return _make_spec(
        phase="static_startup",
        scenario=f"{target['target_id']}__d{actual_delay}__s{actual_slew:.1f}__{variant}",
        category="static_startup",
        target=target,
        controller_scale=source_scale,
        environment_variant=environment_variant,
        extra=extra,
    )


def build_static_startup_specs(ctx: Stage41R6Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["static_startup"]
    specs: list[dict[str, Any]] = []
    for actual_slew in cfg["actual_slew_scales"]:
        environment_variant, _ = materialize_variant(ctx, slew_scale=float(actual_slew), horizon_steps=int(cfg["horizon_steps"]))
        for actual_delay in cfg["actual_delay_steps"]:
            for target in cfg["targets"]:
                for variant in cfg["controller_variants"]:
                    specs.append(_startup_spec(
                        ctx,
                        variant=str(variant),
                        target=target,
                        actual_delay=int(actual_delay),
                        actual_slew=float(actual_slew),
                        environment_variant=environment_variant,
                    ))
    return specs


def summarize_static_startup(ctx: Stage41R6Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["static_startup"]
    grouped: dict[tuple[str, int, float], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["target_id"]), int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"]))
        grouped.setdefault(key, {})[str(row["controller_variant"])] = row
    oracle_feasible = 0
    exact_pass = exact_equal = adjacent_pass = adjacent_full_pass = cold_pass = abrupt_pass = 0
    delay2_feasible = delay2_adjacent_pass = 0
    exact_noop_events = 0
    identification_correct: list[bool] = []
    physical_blend_better: list[bool] = []
    case_rows: list[dict[str, Any]] = []
    for key, variants in sorted(grouped.items()):
        oracle = variants.get("oracle")
        if oracle is None:
            continue
        oracle_ok = _as_bool(oracle.get("stage3_4_target_tracking_pass"))
        diagnostic_weak = bool(
            cfg.get("weak_slew_deadline_cases_are_diagnostic", True)
            and math.isclose(key[2], 0.9, abs_tol=1e-12)
            and not oracle_ok
        )
        exact = variants.get("r6_persistent_exact_monitor") or {}
        adjacent = variants.get("r6_persistent_adjacent_delay") or {}
        adjacent_full = variants.get("r6_persistent_adjacent_full") or {}
        cold = variants.get("r6_cold_common_prefix") or {}
        abrupt = variants.get("r4_abrupt_unknown") or {}
        if oracle_ok:
            oracle_feasible += 1
            exact_pass += int(_as_bool(exact.get("stage3_4_target_tracking_pass")))
            adjacent_pass += int(_as_bool(adjacent.get("stage3_4_target_tracking_pass")))
            adjacent_full_pass += int(_as_bool(adjacent_full.get("stage3_4_target_tracking_pass")))
            cold_pass += int(_as_bool(cold.get("stage3_4_target_tracking_pass")))
            abrupt_pass += int(_as_bool(abrupt.get("stage3_4_target_tracking_pass")))
            exact_equal += int(
                str(exact.get("trajectory_signature", "")) == str(oracle.get("trajectory_signature", "x"))
                and str(exact.get("issued_command_signature", "")) == str(oracle.get("issued_command_signature", "y"))
            )
            if key[1] == 2:
                delay2_feasible += 1
                delay2_adjacent_pass += int(_as_bool(adjacent.get("stage3_4_target_tracking_pass")))
        exact_noop_events += int(exact.get("handover_noop_event_count", 0))
        for row in (exact, adjacent, adjacent_full, cold):
            if row and row.get("adaptive_estimator_enabled"):
                identification_correct.append(
                    int(row.get("adaptive_estimated_delay_steps", -999)) == key[1]
                    and math.isclose(_as_float(row.get("adaptive_estimated_slew_scale"), 1e9), key[2], abs_tol=1e-12)
                    and int(row.get("adaptive_estimator_incorrect_lock_count", 0)) == 0
                )
        if adjacent and abrupt and int(adjacent.get("handover_model_switch_count", 0)) > 0:
            physical_blend_better.append(
                _as_float(adjacent.get("handover_max_event_delta_jump_rms_a"), 1e9)
                <= _as_float(abrupt.get("handover_max_event_delta_jump_rms_a"), 1e9) + float(cfg["maximum_blend_jump_regression_a"])
            )
        case_rows.append({
            "target_id": key[0], "actual_delay_steps": key[1], "actual_slew_scale": key[2],
            "oracle_pass": oracle_ok, "weak_slew_deadline_diagnostic": diagnostic_weak,
            "oracle_margin": oracle.get("stage3_4_tracking_minimum_signed_margin"),
            "abrupt_pass": _as_bool(abrupt.get("stage3_4_target_tracking_pass")),
            "persistent_exact_pass": _as_bool(exact.get("stage3_4_target_tracking_pass")),
            "persistent_exact_trace_equal": bool(
                str(exact.get("trajectory_signature", "")) == str(oracle.get("trajectory_signature", "x"))
                and str(exact.get("issued_command_signature", "")) == str(oracle.get("issued_command_signature", "y"))
            ),
            "adjacent_delay_pass": _as_bool(adjacent.get("stage3_4_target_tracking_pass")),
            "adjacent_full_pass": _as_bool(adjacent_full.get("stage3_4_target_tracking_pass")),
            "cold_common_prefix_pass": _as_bool(cold.get("stage3_4_target_tracking_pass")),
            "adjacent_delay_margin": adjacent.get("stage3_4_tracking_minimum_signed_margin"),
            "cold_common_prefix_margin": cold.get("stage3_4_tracking_minimum_signed_margin"),
            "adjacent_event_jump_rms_a": adjacent.get("handover_max_event_delta_jump_rms_a"),
            "abrupt_event_jump_rms_a": abrupt.get("handover_max_event_delta_jump_rms_a"),
            "exact_noop_event_count": exact.get("handover_noop_event_count"),
        })
    exact_fraction = exact_pass / max(oracle_feasible, 1)
    exact_equal_fraction = exact_equal / max(oracle_feasible, 1)
    adjacent_fraction = adjacent_pass / max(oracle_feasible, 1)
    adjacent_full_fraction = adjacent_full_pass / max(oracle_feasible, 1)
    cold_fraction = cold_pass / max(oracle_feasible, 1)
    abrupt_fraction = abrupt_pass / max(oracle_feasible, 1)
    delay2_fraction = delay2_adjacent_pass / max(delay2_feasible, 1)
    blend_fraction = float(np.mean(physical_blend_better)) if physical_blend_better else 1.0
    precalibrated_pass = bool(
        all(_as_bool(row.get("success")) for row in rows)
        and exact_fraction >= float(cfg["minimum_persistent_exact_preservation"])
        and exact_equal_fraction >= float(cfg["minimum_persistent_exact_trace_equivalence"])
        and adjacent_fraction >= float(cfg["minimum_adjacent_delay_preservation"])
        and delay2_fraction >= float(cfg["minimum_delay2_adjacent_preservation"])
        and exact_noop_events == 0
        and (all(identification_correct) if identification_correct else False)
        and blend_fraction >= float(cfg["minimum_physical_blend_nonregression_fraction"])
    )
    cold_passed = bool(cold_fraction >= float(cfg["cold_common_prefix"]["diagnostic_target_preservation_fraction"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "static_startup",
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "execution_complete": all(_as_bool(row.get("success")) for row in rows),
        "oracle_feasible_cases": oracle_feasible,
        "r4_abrupt_preservation_fraction": abrupt_fraction,
        "persistent_exact_preservation_fraction": exact_fraction,
        "persistent_exact_trace_equivalence_fraction": exact_equal_fraction,
        "persistent_adjacent_delay_preservation_fraction": adjacent_fraction,
        "persistent_adjacent_full_preservation_fraction": adjacent_full_fraction,
        "delay2_adjacent_delay_preservation_fraction": delay2_fraction,
        "cold_common_prefix_preservation_fraction": cold_fraction,
        "exact_noop_event_count": exact_noop_events,
        "adaptive_final_identification_fraction": float(np.mean(identification_correct)) if identification_correct else 0.0,
        "physical_blend_nonregression_fraction": blend_fraction,
        "precalibrated_startup_passed": precalibrated_pass,
        "cold_common_prefix_diagnostic_passed": cold_passed,
        "passed": precalibrated_pass,
        "case_summaries": case_rows,
    }


def run_static_startup(ctx: Stage41R6Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_static_startup_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.startup / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    summary = summarize_static_startup(ctx, rows)
    write_csv(ctx.paths.startup / "results.csv", rows)
    atomic_write_json(ctx.paths.startup / "results.json", rows)
    write_csv(ctx.paths.startup / "case_summary.csv", summary["case_summaries"])
    atomic_write_json(ctx.paths.startup / "summary.json", summary)
    _update_state(ctx, startup_complete=True, startup_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Restart audit and confirmation
# ---------------------------------------------------------------------------


def run_restart_audit(ctx: Stage41R6Context) -> dict[str, Any]:
    root = Path(ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg.get("simulation_root", "")).expanduser()
    candidates = []
    for value in ctx.cfg["restart_audit"].get("candidate_folders", []):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            candidates.append(str(path.resolve()))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_audit",
        "candidate_folders": list(ctx.cfg["restart_audit"].get("candidate_folders", [])),
        "available_folders": sorted(set(candidates)),
        "true_restart_validation_available": len(set(candidates)) >= int(ctx.cfg["restart_audit"].get("minimum_distinct_folders", 2)),
        "true_restart_validation_performed": False,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


def _clone_confirmation_spec(source: dict[str, Any], *, group: str, repeat: int) -> dict[str, Any]:
    spec = copy.deepcopy(source)
    spec["phase"] = "confirmation"
    spec["category"] = "startup_confirmation"
    spec["scenario"] = f"{source.get('scenario')}__confirm_r{repeat}"
    spec["confirmation_group"] = group
    spec["confirmation_repeat"] = repeat
    spec["experiment_id"] = _scenario_digest(spec, prefix="s41r6c")
    return spec


def build_confirmation_specs(ctx: Stage41R6Context) -> list[dict[str, Any]]:
    state = read_json(ctx.paths.state)
    startup = state.get("startup_summary") or {}
    if not bool(startup.get("precalibrated_startup_passed", False)):
        return []
    startup_rows = read_json(ctx.paths.startup / "results.json")
    specs: list[dict[str, Any]] = []
    repeats = int(ctx.cfg["confirmation"]["repeats_per_group"])
    # Exact persistent monitor: one target for every delay/slew pair.
    exact_rows = [
        row for row in startup_rows
        if row.get("controller_variant") == "r6_persistent_exact_monitor"
        and row.get("target_id") == "nominal"
    ]
    # Adjacent-prior: select the thinnest successful row per delay/slew pair.
    adjacent_rows = [
        row for row in startup_rows
        if row.get("controller_variant") == "r6_persistent_adjacent_delay"
        and _as_bool(row.get("stage3_4_target_tracking_pass"))
    ]
    selected: list[tuple[str, dict[str, Any]]] = []
    for row in exact_rows:
        selected.append((f"exact_d{row['actual_action_delay_steps']}_s{row['actual_slew_scale']}", row))
    grouped_adjacent: dict[tuple[int, float], list[dict[str, Any]]] = {}
    for row in adjacent_rows:
        grouped_adjacent.setdefault((int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"])), []).append(row)
    for key, rows in sorted(grouped_adjacent.items()):
        chosen = min(rows, key=lambda row: _as_float(row.get("stage3_4_tracking_minimum_signed_margin"), 1e9))
        selected.append((f"adjacent_d{key[0]}_s{key[1]}", chosen))
    max_groups = int(ctx.cfg["confirmation"]["maximum_startup_groups"])
    selected = selected[:max_groups]
    raw_dir = ctx.paths.startup / "raw"
    for group, row in selected:
        source_payload = read_json_gz(raw_dir / f"{row['experiment_id']}.json.gz")
        for repeat in range(repeats):
            specs.append(_clone_confirmation_spec(source_payload["spec"], group=group, repeat=repeat))
    return specs


def summarize_confirmation(ctx: Stage41R6Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get("confirmation_group", "")), []).append(row)
    group_rows = []
    for group, subset in sorted(groups.items()):
        group_rows.append({
            "confirmation_group": group,
            "repeats": len(subset),
            "all_success": all(_as_bool(row.get("success")) for row in subset),
            "all_tracking_pass": all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in subset),
            "all_final_identification_correct": all(
                int(row.get("adaptive_estimated_delay_steps", -999)) == int(row["actual_action_delay_steps"])
                and math.isclose(_as_float(row.get("adaptive_estimated_slew_scale"), 1e9), float(row["actual_slew_scale"]), abs_tol=1e-12)
                for row in subset
            ),
            "incorrect_confident_lock_count": sum(int(row.get("adaptive_estimator_incorrect_lock_count", 0)) for row in subset),
            "minimum_margin": min((_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in subset), default=-1e12),
        })
    required = int(ctx.cfg["confirmation"]["minimum_distinct_groups"])
    passed = bool(
        len(group_rows) >= required
        and all(row["all_success"] and row["all_tracking_pass"] and row["all_final_identification_correct"] and row["incorrect_confident_lock_count"] == 0 for row in group_rows)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "confirmation",
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "distinct_groups_confirmed": len(group_rows),
        "passed": passed,
        "group_summaries": group_rows,
    }


def run_confirmation(ctx: Stage41R6Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_confirmation_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.confirmation / "raw", backend=backend, resume=resume) if specs else []
    rows = [result_row(ctx, result) for result in results]
    for row, spec in zip(rows, specs):
        row["confirmation_group"] = spec.get("confirmation_group")
        row["confirmation_repeat"] = spec.get("confirmation_repeat")
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


def analyze(ctx: Stage41R6Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    estimator = state.get("estimator_confirmation_summary") or {}
    startup = state.get("startup_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    confirmation = state.get("confirmation_summary") or {}
    primary_pass = bool(
        source.get("passed")
        and estimator.get("passed")
        and startup.get("precalibrated_startup_passed")
        and confirmation.get("passed")
    )
    cold_pass = bool(startup.get("cold_common_prefix_diagnostic_passed", False))
    restart_available = bool(restart.get("true_restart_validation_available", False))
    if primary_pass and cold_pass and not restart_available:
        verdict = "PASS_STAGE4_1R6_PRECALIBRATED_AND_COMMON_PREFIX_STARTUP_CONFIRMED_TRUE_RESTART_NOT_AVAILABLE"
    elif primary_pass and not restart_available:
        verdict = "PASS_STAGE4_1R6_PRECALIBRATED_PERSISTENT_STARTUP_CONFIRMED_COLD_START_DIAGNOSTIC_INCOMPLETE_TRUE_RESTART_NOT_AVAILABLE"
    elif primary_pass:
        verdict = "PASS_STAGE4_1R6_PRECALIBRATED_PERSISTENT_STARTUP_CONFIRMED_TRUE_RESTART_NOT_YET_VALIDATED"
    else:
        verdict = "STAGE4_1R6_STARTUP_ARCHITECTURE_CLOSURE_INCOMPLETE"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r5_run": str(ctx.source_stage41r5_run),
        "source_audit_passed": bool(source.get("passed", False)),
        "confidence_gated_estimator_confirmation_passed": bool(estimator.get("passed", False)),
        "precalibrated_persistent_startup_passed": bool(startup.get("precalibrated_startup_passed", False)),
        "cold_common_prefix_diagnostic_passed": cold_pass,
        "confirmation_passed": bool(confirmation.get("passed", False)),
        "true_restart_validation_available": restart_available,
        "true_restart_validation_performed": False,
        "finite_precalibrated_startup_envelope_validated": primary_pass,
        "cold_start_deployment_validated": False,
        "deployment_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "warning": "The primary result assumes pre-shot or previous-shot delay/slew initialization. The cold common-prefix path remains a finite diagnostic unless separately passed.",
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "estimator_confirmation": estimator,
            "static_startup": startup,
            "restart_audit": restart,
            "confirmation": confirmation,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r6_analysis_summary.json", summary)
    atomic_write_json(ctx.paths.analysis / "stage4_1r6_verdict.json", summary)
    _update_state(ctx, finished=True, stop_reason="pipeline_complete", analysis_summary=summary)
    return summary


def execute(
    *, config_path: str | Path, source_stage41r5_run: str | Path | None,
    run_dir: str | Path | None, command: str, backend: str, resume: bool,
) -> dict[str, Any]:
    ctx = load_stage41r6_config(
        config_path, source_stage41r5_run=source_stage41r5_run, run_dir_override=run_dir
    )
    initialize_run(ctx)
    if command in {"all", "audit"}:
        audit = run_source_audit(ctx)
        if command == "audit":
            return read_json(ctx.paths.state)
        if not audit.get("passed"):
            _update_state(ctx, finished=True, stop_reason="source_confidence_replay_failed")
            return analyze(ctx)
    if command in {"all", "estimator"}:
        estimator = run_estimator_confirmation(ctx, backend=backend, resume=resume)
        if command == "estimator":
            return read_json(ctx.paths.state)
        if not estimator.get("passed"):
            _update_state(ctx, finished=True, stop_reason="confidence_gated_estimator_confirmation_failed")
            return analyze(ctx)
    if command in {"all", "startup"}:
        startup = run_static_startup(ctx, backend=backend, resume=resume)
        if command == "startup":
            return read_json(ctx.paths.state)
        if not startup.get("precalibrated_startup_passed"):
            _update_state(ctx, finished=True, stop_reason="precalibrated_startup_failed")
            return analyze(ctx)
    if command in {"all", "restart"}:
        run_restart_audit(ctx)
        if command == "restart":
            return read_json(ctx.paths.state)
    if command in {"all", "confirm"}:
        run_confirmation(ctx, backend=backend, resume=resume)
        if command == "confirm":
            return read_json(ctx.paths.state)
    if command in {"all", "analyze"}:
        return analyze(ctx)
    if command == "prepare":
        return read_json(ctx.paths.state)
    raise ValueError(f"unsupported command {command!r}")


def self_test() -> dict[str, Any]:
    scheduler = r3.PhysicalCoilScheduler(
        modes_tsc=np.eye(14, 3), nominal_max_delta_a=3.0, command_max_delta_a=3.0,
        min_current=-1e6 * np.ones(14), max_current=1e6 * np.ones(14),
        lower_mode=np.array([-2.6, -2.6, -0.9]), upper_mode=np.array([2.6, 2.6, 0.9]),
    )
    bank = r3.DelaySlewHypothesisBank(
        scheduler=scheduler, delay_candidates=(0, 1, 2), slew_candidates=(0.9, 1.0, 1.1),
        minimum_observations=2, switch_hysteresis_fraction=0.0,
        minimum_confidence_ratio=5.0, minimum_absolute_score_gap=1e-10,
        consecutive_best_observations=2, require_unique_best=True,
        tie_relative_tolerance=1e-9, tie_absolute_tolerance=1e-12,
    )
    nominal = np.asarray([[0.15 + 0.04*k, -0.10 + 0.03*k, 0.02*(-1)**k] for k in range(12)], dtype=float)
    actual_delay, actual_slew = 2, 1.1
    issued: list[np.ndarray] = []
    currents = np.zeros(14)
    confidence_at_tie = None
    for step in range(len(nominal)):
        issued.append(nominal[step].copy())
        command = nominal[step] if step < actual_delay else issued[step-actual_delay]
        observed = scheduler.predicted_delta_a(command, currents, np.ones(3), actual_slew)
        update = bank.update(
            step=step, observed_delta_a=observed, currents_before_a=currents,
            issued_commands=issued, nominal_commands=nominal,
        )
        if step == 1:
            confidence_at_tie = bool(update["locked"])
        currents += observed
    summary = bank.summary()
    return {
        "stage": STAGE,
        "selected_delay_steps": summary["selected_delay_steps"],
        "selected_slew_scale": summary["selected_slew_scale"],
        "first_confident_lock_step": summary["first_confident_lock_step"],
        "locked_during_tie": confidence_at_tie,
        "passed": bool(
            summary["selected_delay_steps"] == actual_delay
            and math.isclose(summary["selected_slew_scale"], actual_slew, abs_tol=1e-12)
            and summary["first_confident_lock_step"] is not None
            and not confidence_at_tie
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage4.1R6 startup architecture closure")
    parser.add_argument("--config", default="configs/stage4_1r6_startup_architecture_closure_350ms.json")
    parser.add_argument("--source-stage4-1r5-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument(
        "--command", default="all",
        choices=["all", "prepare", "audit", "estimator", "startup", "restart", "confirm", "analyze"],
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
        source_stage41r5_run=args.source_stage4_1r5_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
