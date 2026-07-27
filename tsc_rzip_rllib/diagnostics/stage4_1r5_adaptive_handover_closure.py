"""Stage4.1R5 confidence-gated bumpless delay/slew handover closure.

This targeted revision consumes a completed Stage4.1R4 run.  It does not
repeat the earlier observer, disturbance, noise, history, or weak-slew
campaigns.  It separates three questions that Stage4.1R4 had mixed together:

1. Can the finite delay/slew bank identify the plant independently of control?
2. Can a controller start from an unknown or nearby model and hand over without
   injecting a destructive transient?
3. Can the same mechanism track a finite mid-episode parameter change under an
   explicitly defined diagnostic delay/slew schedule?

The strongest result remains a finite research envelope.  It is not deployment
qualification, true restart-state robustness, or general plant identification.
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
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

SCHEMA_VERSION = 1
STAGE = "Stage4.1R5"
CONTROLLER_REVISION = "confidence_gated_bumpless_delay_slew_handover_v5"
EXPECTED_SOURCE_STAGE = "Stage4.1R4"
EXPECTED_SOURCE_REVISION = "targeted_weak_slew_and_online_delay_slew_estimator_v4"
STATE_FILENAME = "stage4_1r5_state.json"
MANIFEST_FILENAME = "stage4_1r5_manifest.json"


# ---------------------------------------------------------------------------
# Strict I/O helpers
# ---------------------------------------------------------------------------


def utc_timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _json_safe(value: Any, path: str = "$") -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"non-finite JSON number at {path}: {number!r}")
        return number
    if isinstance(value, dict):
        return {str(k): _json_safe(v, f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v, f"{path}[{i}]") for i, v in enumerate(value)]
    return value


def read_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_json_gz(path: Path | str) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(_json_safe(payload), handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_json_gz(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        with gzip.open(tmp, "wt", encoding="utf-8") as handle:
            json.dump(_json_safe(payload), handle, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, np.ndarray)):
        return json.dumps(_json_safe(value), ensure_ascii=False, separators=(",", ":"))
    return value


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: _csv_value(row.get(key, "")) for key in fields})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_float(value: Any, default: float = math.nan) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _scenario_digest(*parts: Any, prefix: str = "s41r5") -> str:
    raw = json.dumps(_json_safe(parts), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:20]}"


def _result_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(read_json_gz(path).get("success", False))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Paths and source context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage41R5Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_audit: Path
    estimator_only: Path
    static_handover: Path
    change_point: Path
    restart: Path
    confirmation: Path
    analysis: Path
    variants: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R5Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_audit=run_dir / "stage4_1r5_source_audit",
            estimator_only=run_dir / "stage4_1r5_estimator_only_confirmation",
            static_handover=run_dir / "stage4_1r5_static_handover",
            change_point=run_dir / "stage4_1r5_change_point_diagnostics",
            restart=run_dir / "stage4_1r5_restart_audit",
            confirmation=run_dir / "stage4_1r5_confirmation",
            analysis=run_dir / "stage4_1r5_analysis",
            variants=run_dir / "stage4_1r5_environment_variants",
            source_reference=run_dir / "source_stage4_1r4_reference",
        )


@dataclass
class Stage41R5Context:
    cfg: dict[str, Any]
    paths: Stage41R5Paths
    project_dir: Path
    source_stage41r4_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_verdict: dict[str, Any]
    source_r4_cfg: dict[str, Any]
    source_stage41r3_run: Path
    r4_ctx: r4.Stage41R4Context
    source_fingerprint: dict[str, Any]


def resolve_source_stage41r4_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE4_1R4_RUN", "").strip()
    if not value:
        raise ValueError("Stage4.1R5 requires --source-stage4-1r4-run or SOURCE_STAGE4_1R4_RUN")
    run = Path(value).expanduser().resolve()
    required = [
        run / "stage4_1r4_manifest.json",
        run / "stage4_1r4_state.json",
        run / "stage4_1r4_config.resolved.json",
        run / "stage4_1r4_analysis/stage4_1r4_verdict.json",
        run / "stage4_1r4_weak_slew_370ms/summary.json",
        run / "stage4_1r4_delay_slew_estimator/summary.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage4.1R4 source run: " + ", ".join(missing))
    return run


def _resolve_source_r3(project_dir: Path, manifest: dict[str, Any]) -> Path:
    raw = str(manifest.get("source_stage4_1r3_run", "")).strip()
    if not raw:
        raise ValueError("Stage4.1R4 manifest has no source_stage4_1r3_run")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (project_dir / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        fallback = project_dir / "stage4_1r3_runs" / path.name
        if fallback.exists():
            path = fallback.resolve()
    required = [path / "stage4_1r3_manifest.json", path / "stage4_1r3_config.resolved.json"]
    missing = [str(item) for item in required if not item.exists()]
    if missing:
        raise FileNotFoundError("Stage4.1R4 source Stage4.1R3 run is unavailable: " + ", ".join(missing))
    return path


def _source_inventory(source_r4: Path, source_r3: Path) -> dict[str, Any]:
    logical_paths: list[tuple[str, Path]] = [
        ("stage4_1r4/manifest.json", source_r4 / "stage4_1r4_manifest.json"),
        ("stage4_1r4/state.json", source_r4 / "stage4_1r4_state.json"),
        ("stage4_1r4/config.json", source_r4 / "stage4_1r4_config.resolved.json"),
        ("stage4_1r4/verdict.json", source_r4 / "stage4_1r4_analysis/stage4_1r4_verdict.json"),
        ("stage4_1r4/weak_slew.json", source_r4 / "stage4_1r4_weak_slew_370ms/summary.json"),
        ("stage4_1r4/estimator.json", source_r4 / "stage4_1r4_delay_slew_estimator/summary.json"),
        ("stage4_1r3/manifest.json", source_r3 / "stage4_1r3_manifest.json"),
        ("stage4_1r3/config.json", source_r3 / "stage4_1r3_config.resolved.json"),
    ]
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    total = 0
    for logical, path in logical_paths:
        if not path.exists():
            continue
        sha = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"logical_path": logical, "sha256": sha, "bytes": size})
        digest.update(logical.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\n")
        total += size
    return {"n_files": len(entries), "total_bytes": total, "digest": digest.hexdigest(), "entries": entries}


def validate_source(cfg: dict[str, Any], manifest: dict[str, Any], state: dict[str, Any]) -> None:
    req = cfg["source_requirement"]
    if str(manifest.get("stage")) != EXPECTED_SOURCE_STAGE:
        raise ValueError(f"source stage must be {EXPECTED_SOURCE_STAGE}")
    if str(manifest.get("controller_revision")) != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R4 controller revision is unsupported")
    if bool(req.get("require_finished", True)) and not bool(state.get("finished", False)):
        raise ValueError("source Stage4.1R4 run is not finished")
    reclass = state.get("reclassification_summary") or {}
    weak = state.get("weak_slew_summary") or {}
    estimator = state.get("estimator_summary") or {}
    if bool(req.get("require_source_accounting_passed", True)) and not bool(
        reclass.get("gain_estimation_error_reclassified_without_new_tsc", False)
        and reclass.get("all_non_slew_required_categories_passed", False)
    ):
        raise ValueError("source Stage4.1R4 accounting/non-slew closure is incomplete")
    if bool(req.get("require_weak_slew_370ms_passed", True)) and not bool(weak.get("passed", False)):
        raise ValueError("source Stage4.1R4 weak-slew closure did not pass")
    if bool(req.get("require_estimator_accuracy_passed", True)) and not bool(
        estimator.get("estimator_accuracy_passed", False)
    ):
        raise ValueError("source Stage4.1R4 estimator accuracy did not pass")


def validate_config(cfg: dict[str, Any], source_cfg: dict[str, Any]) -> None:
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R5 controller_revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.1R5 complete package is configured for 128 workers")
    gate = cfg["gate"]
    source_gate = source_cfg["gate"]
    for key in (
        "precise_tolerance_m",
        "relaxed_tolerance_m",
        "required_arrival_streak_steps",
        "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s",
        "late_window_steps",
        "ip_safety_tolerance_A",
    ):
        if not math.isclose(float(gate[key]), float(source_gate[key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.1R5 hard gate {key} differs from source Stage4.1R4")
    for key in ("terminal_abs_tolerance_A", "hold_rms_tolerance_A", "sustained_max_tolerance_A"):
        if not math.isclose(
            float(gate["ip_tracking"][key]),
            float(source_gate["ip_tracking"][key]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"Stage4.1R5 Ip tracking threshold {key} differs from source")
    handover = cfg["static_handover"]["handover"]
    ramp = [float(v) for v in handover["ramp_scale_fractions"]]
    if not ramp or ramp[0] != 0.0 or ramp[-1] != 1.0 or any(b < a for a, b in zip(ramp, ramp[1:])):
        raise ValueError("Stage4.1R5 bumpless ramp must increase from 0 to 1")
    if int(cfg["estimator_only_confirmation"]["minimum_observations"]) != 2:
        raise ValueError("Stage4.1R5 estimator-only confirmation is locked to two observations")


def load_stage41r5_config(
    config_path: str | Path,
    *,
    source_stage41r4_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage41R5Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = base.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)},
    )
    source_r4 = resolve_source_stage41r4_run(source_stage41r4_run)
    source_manifest = read_json(source_r4 / "stage4_1r4_manifest.json")
    source_state = read_json(source_r4 / "stage4_1r4_state.json")
    source_verdict = read_json(source_r4 / "stage4_1r4_analysis/stage4_1r4_verdict.json")
    source_r4_cfg = read_json(source_r4 / "stage4_1r4_config.resolved.json")
    validate_source(cfg, source_manifest, source_state)
    validate_config(cfg, source_r4_cfg)
    source_r3 = _resolve_source_r3(project_dir, source_manifest)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage4_1r5_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r5_adaptive_handover_closure_350ms')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)
    r4_ctx = r4.load_stage41r4_config(
        source_r4 / "stage4_1r4_config.resolved.json",
        source_stage41r3_run=source_r3,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    env_cfg = copy.deepcopy(r4_ctx.r3_ctx.source_env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"].get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_1R5_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"])).expanduser().resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R5_TSC_RUN_ROOT", storage["tsc_run_root"])).expanduser().resolve()
    )
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    r4_ctx.r3_ctx.source_env_cfg = env_cfg
    r4_ctx.r3_ctx.base34.env_cfg = copy.deepcopy(env_cfg)
    r4_ctx.r3_ctx.source_train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    paths = Stage41R5Paths.from_run_dir(run_dir)
    return Stage41R5Context(
        cfg=cfg,
        paths=paths,
        project_dir=project_dir,
        source_stage41r4_run=source_r4,
        source_manifest=source_manifest,
        source_state=source_state,
        source_verdict=source_verdict,
        source_r4_cfg=source_r4_cfg,
        source_stage41r3_run=source_r3,
        r4_ctx=r4_ctx,
        source_fingerprint=_source_inventory(source_r4, source_r3),
    )


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "estimator_only_complete": False,
        "static_handover_complete": False,
        "change_point_complete": False,
        "restart_audit_complete": False,
        "confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R5Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def resource_preflight(cfg: dict[str, Any]) -> dict[str, Any]:
    requested = int(os.environ.get("STAGE4_1R5_WORKERS", cfg["parallel"]["n_workers"]))
    logical = int(os.cpu_count() or 1)
    reserve = int(cfg["parallel"].get("reserve_logical_cpus", 16))
    safe = max(1, logical - reserve)
    if requested > safe:
        raise RuntimeError(
            f"Stage4.1R5 requests {requested} workers, but only {logical} logical CPUs are visible "
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


def initialize_run(ctx: Stage41R5Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_audit,
        ctx.paths.estimator_only,
        ctx.paths.static_handover,
        ctx.paths.change_point,
        ctx.paths.restart,
        ctx.paths.confirmation,
        ctx.paths.analysis,
        ctx.paths.variants,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.run_dir / "stage4_1r5_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.r4_ctx.r3_ctx.source_train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.r4_ctx.r3_ctx.source_env_cfg)
    workers = resource_preflight(ctx.cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r4_run": str(ctx.source_stage41r4_run),
        "source_stage4_1r3_run": str(ctx.source_stage41r3_run),
        "source_fingerprint": {
            "n_files": ctx.source_fingerprint["n_files"],
            "total_bytes": ctx.source_fingerprint["total_bytes"],
            "digest": ctx.source_fingerprint["digest"],
        },
        "workers": workers,
        "hard_numeric_thresholds_changed": False,
        "finite_test_envelope_only": True,
        "deployment_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if str(old.get("controller_revision")) != CONTROLLER_REVISION:
            raise ValueError("existing Stage4.1R5 run uses another controller revision")
        if str(old.get("source_fingerprint", {}).get("digest")) != str(ctx.source_fingerprint["digest"]):
            raise ValueError("source Stage4.1R4 content changed since the run was created")
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    inventory = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory.exists():
        atomic_write_json(inventory, ctx.source_fingerprint)
    for relative in (
        "stage4_1r4_manifest.json",
        "stage4_1r4_state.json",
        "stage4_1r4_config.resolved.json",
        "stage4_1r4_analysis/stage4_1r4_verdict.json",
        "stage4_1r4_weak_slew_370ms/summary.json",
        "stage4_1r4_delay_slew_estimator/summary.json",
    ):
        src = ctx.source_stage41r4_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())


# ---------------------------------------------------------------------------
# Environment variants and evaluation
# ---------------------------------------------------------------------------


def materialize_variant(
    ctx: Stage41R5Context,
    *,
    slew_scale: float,
    horizon_steps: int = 35,
    start_folder: str | None = None,
) -> tuple[str, dict[str, Any]]:
    return r4.materialize_variant(
        ctx.r4_ctx,
        slew_scale=float(slew_scale),
        horizon_steps=int(horizon_steps),
        start_folder=start_folder,
    )


class LocalStage41R5Worker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str):
        self.inner = r4.LocalStage41R4Worker(payload, library, bundle, worker_id)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.inner.evaluate(spec)
        result["stage4_1r5_controller_revision"] = CONTROLLER_REVISION
        return _json_safe(result)

    def close(self) -> None:
        self.inner.close()


def _ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id):
            self.worker = LocalStage41R5Worker(payload, library, bundle, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor


def evaluate_specs(
    ctx: Stage41R5Context,
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
        if variant not in ctx.r4_ctx.variants:
            raise KeyError(f"unmaterialized environment variant {variant}")
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, rows in by_variant.items():
        pending = [
            row
            for row in rows
            if not (resume and _result_complete(output_dir / f"{row['experiment_id']}.json.gz"))
        ]
        if pending:
            pending_by_variant[variant] = pending
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalStage41R5Worker(
                ctx.r4_ctx.variants[variant],
                ctx.r4_ctx.r3_ctx.source_library,
                ctx.r4_ctx.r3_ctx.source_bundle,
                f"stage41r5_{variant}_serial",
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate(spec))
                    print(f"[Stage4.1R5 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(os.environ.get("STAGE4_1R5_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R5 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()},
            plan.actor_count,
        )
        print(
            "[Stage4.1R5 mixed-variant] actor_allocation="
            + json.dumps(allocation, sort_keys=True, separators=(",", ":")),
            flush=True,
        )
        Actor = _ray_actor_class()
        actors_by_variant: dict[str, list[Any]] = {}
        all_actors: list[Any] = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(
                    ctx.r4_ctx.variants[variant],
                    ctx.r4_ctx.r3_ctx.source_library,
                    ctx.r4_ctx.r3_ctx.source_bundle,
                    f"stage41r5_{variant}_{index:03d}",
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
                    print(f"[Stage4.1R5 mixed-variant] waiting {done}/{total_pending}", flush=True)
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
                        print(f"[Stage4.1R5 mixed-variant] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(
                all_actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


# ---------------------------------------------------------------------------
# Specs and rows
# ---------------------------------------------------------------------------


def _make_spec(
    *,
    phase: str,
    scenario: str,
    category: str,
    target: dict[str, Any],
    controller_scale: float,
    environment_variant: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "kind": "stage4_1r5_adaptive_handover_closure",
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


def _estimator_cfg(cfg: dict[str, Any], *, initial_delay: int, initial_slew: float) -> dict[str, Any]:
    return {
        "enabled": True,
        "delay_candidates": list(map(int, cfg["delay_candidates"])),
        "slew_candidates": list(map(float, cfg["slew_candidates"])),
        "score_decay": float(cfg["score_decay"]),
        "minimum_observations": int(cfg["minimum_observations"]),
        "switch_hysteresis_fraction": float(cfg["switch_hysteresis_fraction"]),
        "initial_delay_steps": int(initial_delay),
        "initial_slew_scale": float(initial_slew),
    }


def _adjacent_initial(actual_delay: int, actual_slew: float) -> tuple[int, float]:
    adjacent_delay = actual_delay - 1 if actual_delay > 0 else 1
    return int(adjacent_delay), float(actual_slew)


def _task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id", "scenario"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(spec.get("category", "r5")),
    }


def result_row(ctx: Stage41R5Context, result: dict[str, Any]) -> dict[str, Any]:
    metric_ctx = type("MetricCtx", (), {
        "cfg": copy.deepcopy(ctx.r4_ctx.r3_ctx.base34.cfg),
        "env_cfg": ctx.r4_ctx.r3_ctx.base34.env_cfg,
    })()
    metrics = r3.s34.target_metrics(metric_ctx, _task_from_spec(result["spec"]), result, None)
    spec = result["spec"]
    estimator = result.get("adaptive_estimator_summary") or {}
    handover = result.get("adaptive_handover_summary") or {}
    trace = result.get("control_trace") or []
    delay_schedule = spec.get("actual_action_delay_schedule") or []
    slew_schedule = spec.get("actual_slew_scale_schedule") or []
    return {
        "experiment_id": result["experiment_id"],
        "phase": spec.get("phase"),
        "scenario": spec.get("scenario"),
        "category": spec.get("category"),
        "target_id": spec.get("target_id"),
        "controller_variant": spec.get("controller_variant"),
        "controller_scale": float(spec.get("controller_scale", 0.0)),
        "environment_variant": spec.get("environment_variant"),
        "actual_action_delay_steps": int(spec.get("action_delay_steps", 0)),
        "actual_slew_scale": float(spec.get("slew_scale", 1.0)),
        "actual_action_delay_schedule": delay_schedule,
        "actual_slew_scale_schedule": slew_schedule,
        "final_actual_delay_steps": int(
            delay_schedule[-1]["delay_steps"] if delay_schedule else spec.get("action_delay_steps", 0)
        ),
        "final_actual_slew_scale": float(
            slew_schedule[-1]["slew_scale"] if slew_schedule else spec.get("slew_scale", 1.0)
        ),
        "initial_estimated_delay_steps": int(
            (spec.get("adaptive_delay_slew_estimator") or {}).get(
                "initial_delay_steps", spec.get("controller_action_delay_steps", 0)
            )
        ),
        "initial_estimated_slew_scale": float(
            (spec.get("adaptive_delay_slew_estimator") or {}).get(
                "initial_slew_scale", spec.get("controller_slew_scale_estimate", 1.0)
            )
        ),
        "adaptive_estimator_enabled": bool((spec.get("adaptive_delay_slew_estimator") or {}).get("enabled", False)),
        "adaptive_estimated_delay_steps": estimator.get("selected_delay_steps"),
        "adaptive_estimated_slew_scale": estimator.get("selected_slew_scale"),
        "adaptive_estimator_observations": estimator.get("observations"),
        "adaptive_estimator_first_lock_step": estimator.get("first_lock_step"),
        "adaptive_estimator_confidence_ratio": estimator.get("confidence_ratio"),
        "adaptive_estimator_transitions": estimator.get("transitions"),
        "handover_enabled": bool(handover.get("enabled", False)),
        "handover_model_locked": bool(handover.get("model_locked", False)),
        "handover_prelock_steps": int(handover.get("prelock_steps", 0)),
        "handover_ramp_steps": int(handover.get("ramp_steps", 0)),
        "handover_event_count": len(handover.get("events", [])),
        "handover_events": handover.get("events", []),
        "anti_windup_saturated_steps": sum(bool(item.get("anti_windup_saturated", False)) for item in trace),
        "success": bool(result.get("success", False)),
        **metrics,
    }


# ---------------------------------------------------------------------------
# Source audit
# ---------------------------------------------------------------------------


def run_source_audit(ctx: Stage41R5Context) -> dict[str, Any]:
    weak = ctx.source_state.get("weak_slew_summary") or {}
    estimator = ctx.source_state.get("estimator_summary") or {}
    reclass = ctx.source_state.get("reclassification_summary") or {}
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r4_run": str(ctx.source_stage41r4_run),
        "source_finished": bool(ctx.source_state.get("finished", False)),
        "source_accounting_passed": bool(
            reclass.get("gain_estimation_error_reclassified_without_new_tsc", False)
            and reclass.get("all_non_slew_required_categories_passed", False)
        ),
        "source_weak_slew_passed": bool(weak.get("passed", False)),
        "source_weak_slew_minimum_margin": (weak.get("selected_controller") or {}).get("minimum_signed_margin"),
        "source_estimator_accuracy_passed": bool(estimator.get("estimator_accuracy_passed", False)),
        "source_adaptive_control_passed": bool(estimator.get("adaptive_control_passed", False)),
        "source_adaptive_control_failure_expected": True,
        "passed": bool(
            ctx.source_state.get("finished", False)
            and weak.get("passed", False)
            and estimator.get("estimator_accuracy_passed", False)
        ),
        "warning": (
            "The source 0.9x-slew hard-target closure has extremely thin signed margin; "
            "R5 does not reinterpret it as deployment robustness."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Estimator-only independent confirmation
# ---------------------------------------------------------------------------


def build_estimator_only_specs(ctx: Stage41R5Context, *, repeats: bool = False) -> list[dict[str, Any]]:
    cfg = ctx.cfg["estimator_only_confirmation"]
    specs: list[dict[str, Any]] = []
    targets = cfg["targets"] if not repeats else [cfg["targets"][0]]
    repeat_count = int(cfg["confirmation_repeats_per_pair"]) if repeats else 1
    for actual_slew in cfg["actual_slew_scales"]:
        variant_id, _ = materialize_variant(ctx, slew_scale=float(actual_slew), horizon_steps=int(cfg["horizon_steps"]))
        for actual_delay in cfg["actual_delay_steps"]:
            for target in targets:
                for repeat in range(repeat_count):
                    estimator_cfg = _estimator_cfg(
                        cfg,
                        initial_delay=int(cfg["initial_delay_steps"]),
                        initial_slew=float(cfg["initial_slew_scale"]),
                    )
                    specs.append(
                        _make_spec(
                            phase=("estimator_only_confirmation" if repeats else "estimator_only"),
                            scenario=(
                                f"{target['target_id']}__d{int(actual_delay)}__s{float(actual_slew):.1f}"
                                + (f"__rep{repeat}" if repeats else "")
                            ),
                            category="estimator_only",
                            target=target,
                            controller_scale=0.0,
                            environment_variant=variant_id,
                            extra={
                                "horizon_steps": int(cfg["horizon_steps"]),
                                "extended_horizon": False,
                                "slew_scale": float(actual_slew),
                                "controller_slew_scale_estimate": float(cfg["initial_slew_scale"]),
                                "actuator_gain_by_mode": [1.0, 1.0, 1.0],
                                "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
                                "action_delay_steps": int(actual_delay),
                                "controller_action_delay_steps": int(cfg["initial_delay_steps"]),
                                "prime_action_queue_with_nominal": True,
                                "observer_enabled": False,
                                "observer_variant": "legacy_raw",
                                "anti_windup_enabled": False,
                                "anti_windup_mode": "off",
                                "delay_aware_enabled": True,
                                "gain_slew_scheduling_enabled": True,
                                "phase_aware_reference_enabled": True,
                                "known_control_effect_from_measured_current_increment": True,
                                "controller_variant": "estimator_only",
                                "adaptive_delay_slew_estimator": estimator_cfg,
                                "adaptive_handover": {"enabled": False},
                                "confirmation_repeat": repeat if repeats else None,
                                "confirmation_group": (
                                    f"estimator_d{int(actual_delay)}_s{float(actual_slew):.1f}"
                                    if repeats else None
                                ),
                            },
                        )
                    )
    return specs


def summarize_estimator_only(ctx: Stage41R5Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["estimator_only_confirmation"]
    correct = [
        int(row.get("adaptive_estimated_delay_steps", -999)) == int(row["actual_action_delay_steps"])
        and math.isclose(
            _as_float(row.get("adaptive_estimated_slew_scale"), 1e9),
            float(row["actual_slew_scale"]),
            abs_tol=1e-12,
        )
        for row in rows
    ]
    lock_steps = [_as_int(row.get("adaptive_estimator_first_lock_step"), 999) for row in rows]
    ratios = [_as_float(row.get("adaptive_estimator_confidence_ratio"), 0.0) for row in rows]
    execution_complete = all(bool(row.get("success")) for row in rows)
    passed = bool(
        execution_complete
        and (all(correct) if cfg.get("require_all_final_identifications_correct", True) else np.mean(correct) >= 0.9)
        and max(lock_steps, default=999) <= int(cfg["maximum_first_lock_step"])
        and min(ratios, default=0.0) >= float(cfg["minimum_confidence_ratio"])
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "estimator_only",
        "n_rollouts": len(rows),
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "execution_complete": execution_complete,
        "identification_fraction": float(np.mean(correct)) if correct else 0.0,
        "maximum_first_lock_step": max(lock_steps, default=None),
        "minimum_confidence_ratio": min(ratios, default=None),
        "passed": passed,
    }


def run_estimator_only(ctx: Stage41R5Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_estimator_only_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.estimator_only / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    summary = summarize_estimator_only(ctx, rows)
    write_csv(ctx.paths.estimator_only / "results.csv", rows)
    atomic_write_json(ctx.paths.estimator_only / "results.json", rows)
    atomic_write_json(ctx.paths.estimator_only / "summary.json", summary)
    _update_state(ctx, estimator_only_complete=True, estimator_only_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Static startup and bumpless handover
# ---------------------------------------------------------------------------


def _static_variant_spec(
    ctx: Stage41R5Context,
    *,
    variant: str,
    target: dict[str, Any],
    actual_delay: int,
    actual_slew: float,
    environment_variant: str,
) -> dict[str, Any]:
    cfg = ctx.cfg["static_handover"]
    estimator_cfg: dict[str, Any] | None = None
    handover_cfg: dict[str, Any] = {"enabled": False}
    anti_windup = variant != "r4_abrupt_unknown"
    if variant == "oracle":
        initial_delay, initial_slew = actual_delay, actual_slew
        modeled_delay, modeled_slew = actual_delay, actual_slew
    elif variant == "r4_abrupt_unknown":
        initial_delay, initial_slew = 0, 1.0
        modeled_delay, modeled_slew = 0, 1.0
        old_cfg = copy.deepcopy(cfg["estimator"])
        old_cfg["minimum_observations"] = 3
        old_cfg["score_decay"] = 0.92
        old_cfg["switch_hysteresis_fraction"] = 0.05
        estimator_cfg = _estimator_cfg(old_cfg, initial_delay=initial_delay, initial_slew=initial_slew)
    elif variant == "r5_bumpless_unknown":
        initial_delay, initial_slew = 0, 1.0
        modeled_delay, modeled_slew = 0, 1.0
        estimator_cfg = _estimator_cfg(cfg["estimator"], initial_delay=initial_delay, initial_slew=initial_slew)
        handover_cfg = copy.deepcopy(cfg["handover"])
        handover_cfg["initial_model_trusted"] = False
    elif variant == "r5_bumpless_adjacent":
        initial_delay, initial_slew = _adjacent_initial(actual_delay, actual_slew)
        modeled_delay, modeled_slew = initial_delay, initial_slew
        estimator_cfg = _estimator_cfg(cfg["estimator"], initial_delay=initial_delay, initial_slew=initial_slew)
        handover_cfg = copy.deepcopy(cfg["handover"])
        handover_cfg["initial_model_trusted"] = False
    elif variant == "r5_persistent_exact":
        initial_delay, initial_slew = actual_delay, actual_slew
        modeled_delay, modeled_slew = actual_delay, actual_slew
        estimator_cfg = _estimator_cfg(cfg["estimator"], initial_delay=initial_delay, initial_slew=initial_slew)
        handover_cfg = copy.deepcopy(cfg["handover"])
        handover_cfg["initial_model_trusted"] = True
        handover_cfg["safe_start_until_lock"] = False
    else:
        raise ValueError(f"unsupported static handover variant {variant}")
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
        "anti_windup_enabled": bool(anti_windup),
        "anti_windup_mode": "conditional_weak_actuator" if anti_windup else "off",
        "conditional_anti_windup_use_actual_actuator_state": False,
        "force_anti_windup_in_clean": bool(anti_windup),
        "delay_aware_enabled": True,
        "gain_slew_scheduling_enabled": True,
        "phase_aware_reference_enabled": True,
        "known_control_effect_from_measured_current_increment": True,
        "controller_variant": variant,
        "adaptive_handover": handover_cfg,
    }
    if estimator_cfg is not None:
        extra["adaptive_delay_slew_estimator"] = estimator_cfg
    return _make_spec(
        phase="static_handover",
        scenario=f"{target['target_id']}__d{actual_delay}__s{actual_slew:.1f}__{variant}",
        category="static_handover",
        target=target,
        controller_scale=float(ctx.r4_ctx.r3_ctx.source_scale),
        environment_variant=environment_variant,
        extra=extra,
    )


def build_static_handover_specs(ctx: Stage41R5Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["static_handover"]
    specs: list[dict[str, Any]] = []
    for actual_slew in cfg["actual_slew_scales"]:
        variant_id, _ = materialize_variant(ctx, slew_scale=float(actual_slew), horizon_steps=int(cfg["horizon_steps"]))
        for actual_delay in cfg["actual_delay_steps"]:
            for target in cfg["targets"]:
                for variant in cfg["controller_variants"]:
                    specs.append(
                        _static_variant_spec(
                            ctx,
                            variant=str(variant),
                            target=target,
                            actual_delay=int(actual_delay),
                            actual_slew=float(actual_slew),
                            environment_variant=variant_id,
                        )
                    )
    return specs


def summarize_static_handover(ctx: Stage41R5Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["static_handover"]
    grouped: dict[tuple[str, int, float], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (str(row["target_id"]), int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"]))
        grouped.setdefault(key, {})[str(row["controller_variant"])] = row
    variants_to_check = {
        "r4_abrupt_unknown",
        "r5_bumpless_unknown",
        "r5_bumpless_adjacent",
        "r5_persistent_exact",
    }
    identification_correct = []
    oracle_feasible = 0
    persistent_pass = 0
    unknown_pass = 0
    adjacent_pass = 0
    delay2_oracle_feasible = 0
    delay2_unknown_pass = 0
    abrupt_fail_oracle_pass = 0
    unknown_recoveries = 0
    case_rows: list[dict[str, Any]] = []
    for key, variants in sorted(grouped.items()):
        oracle = variants.get("oracle")
        if oracle is None:
            continue
        oracle_ok = _as_bool(oracle.get("stage3_4_target_tracking_pass"))
        weak_deadline_diagnostic = bool(
            cfg.get("weak_slew_deadline_cases_are_diagnostic", True)
            and math.isclose(key[2], 0.9, abs_tol=1e-12)
            and not oracle_ok
        )
        if oracle_ok:
            oracle_feasible += 1
        for name in variants_to_check:
            row = variants.get(name)
            if row is None:
                continue
            identification_correct.append(
                int(row.get("adaptive_estimated_delay_steps", -999)) == int(key[1])
                and math.isclose(_as_float(row.get("adaptive_estimated_slew_scale"), 1e9), float(key[2]), abs_tol=1e-12)
            )
        persistent = variants.get("r5_persistent_exact")
        unknown = variants.get("r5_bumpless_unknown")
        adjacent = variants.get("r5_bumpless_adjacent")
        abrupt = variants.get("r4_abrupt_unknown")
        if oracle_ok:
            persistent_pass += int(_as_bool((persistent or {}).get("stage3_4_target_tracking_pass")))
            unknown_pass += int(_as_bool((unknown or {}).get("stage3_4_target_tracking_pass")))
            adjacent_pass += int(_as_bool((adjacent or {}).get("stage3_4_target_tracking_pass")))
            if key[1] == 2:
                delay2_oracle_feasible += 1
                delay2_unknown_pass += int(_as_bool((unknown or {}).get("stage3_4_target_tracking_pass")))
            if abrupt is not None and not _as_bool(abrupt.get("stage3_4_target_tracking_pass")):
                abrupt_fail_oracle_pass += 1
                unknown_recoveries += int(_as_bool((unknown or {}).get("stage3_4_target_tracking_pass")))
        case_rows.append({
            "target_id": key[0],
            "actual_delay_steps": key[1],
            "actual_slew_scale": key[2],
            "oracle_pass": oracle_ok,
            "weak_slew_deadline_diagnostic": weak_deadline_diagnostic,
            "abrupt_pass": _as_bool((abrupt or {}).get("stage3_4_target_tracking_pass")),
            "unknown_bumpless_pass": _as_bool((unknown or {}).get("stage3_4_target_tracking_pass")),
            "adjacent_bumpless_pass": _as_bool((adjacent or {}).get("stage3_4_target_tracking_pass")),
            "persistent_exact_pass": _as_bool((persistent or {}).get("stage3_4_target_tracking_pass")),
            "oracle_margin": (oracle or {}).get("stage3_4_tracking_minimum_signed_margin"),
            "unknown_margin": (unknown or {}).get("stage3_4_tracking_minimum_signed_margin"),
            "unknown_handover_events": (unknown or {}).get("handover_events"),
        })
    persistent_fraction = persistent_pass / max(oracle_feasible, 1)
    unknown_fraction = unknown_pass / max(oracle_feasible, 1)
    adjacent_fraction = adjacent_pass / max(oracle_feasible, 1)
    delay2_fraction = delay2_unknown_pass / max(delay2_oracle_feasible, 1)
    recovery_fraction = unknown_recoveries / max(abrupt_fail_oracle_pass, 1) if abrupt_fail_oracle_pass else 1.0
    execution_complete = all(bool(row.get("success")) for row in rows)
    identification_pass = bool(all(identification_correct)) if identification_correct else False
    passed = bool(
        execution_complete
        and identification_pass
        and persistent_fraction >= float(cfg["minimum_persistent_preservation_of_oracle_passes"])
        and unknown_fraction >= float(cfg["minimum_unknown_bumpless_preservation_of_oracle_passes"])
        and adjacent_fraction >= float(cfg["minimum_adjacent_bumpless_preservation_of_oracle_passes"])
        and delay2_fraction >= float(cfg["minimum_delay2_unknown_bumpless_preservation"])
        and recovery_fraction >= float(cfg["minimum_recovery_over_r4_abrupt"])
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "static_handover",
        "n_rollouts": len(rows),
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "execution_complete": execution_complete,
        "adaptive_identification_fraction": float(np.mean(identification_correct)) if identification_correct else 0.0,
        "oracle_feasible_cases": oracle_feasible,
        "persistent_exact_preservation_fraction": persistent_fraction,
        "unknown_bumpless_preservation_fraction": unknown_fraction,
        "adjacent_bumpless_preservation_fraction": adjacent_fraction,
        "delay2_unknown_bumpless_preservation_fraction": delay2_fraction,
        "r4_abrupt_failures_with_oracle_pass": abrupt_fail_oracle_pass,
        "unknown_bumpless_recoveries": unknown_recoveries,
        "recovery_over_r4_abrupt_fraction": recovery_fraction,
        "passed": passed,
        "case_summaries": case_rows,
    }


def run_static_handover(ctx: Stage41R5Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_static_handover_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.static_handover / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    summary = summarize_static_handover(ctx, rows)
    write_csv(ctx.paths.static_handover / "results.csv", rows)
    atomic_write_json(ctx.paths.static_handover / "results.json", rows)
    write_csv(ctx.paths.static_handover / "case_summary.csv", summary["case_summaries"])
    atomic_write_json(ctx.paths.static_handover / "summary.json", summary)
    _update_state(ctx, static_handover_complete=True, static_handover_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Finite mid-episode change diagnostics
# ---------------------------------------------------------------------------


def _schedule_rows(change_step: int, initial: float | int, final: float | int, key: str) -> list[dict[str, Any]]:
    return [
        {"start_step": 0, key: initial},
        {"start_step": int(change_step), key: final},
    ]


def build_change_point_specs(ctx: Stage41R5Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["change_point_diagnostics"]
    if not bool(cfg.get("enabled", True)):
        return []
    base_slew = float(cfg["environment_max_slew_scale"])
    variant_id, _ = materialize_variant(ctx, slew_scale=base_slew, horizon_steps=int(cfg["horizon_steps"]))
    specs: list[dict[str, Any]] = []
    for scenario_cfg in cfg["scenarios"]:
        delay_schedule = _schedule_rows(
            int(scenario_cfg["change_step"]),
            int(scenario_cfg["initial_delay"]),
            int(scenario_cfg["final_delay"]),
            "delay_steps",
        )
        slew_schedule = _schedule_rows(
            int(scenario_cfg["change_step"]),
            float(scenario_cfg["initial_slew"]),
            float(scenario_cfg["final_slew"]),
            "slew_scale",
        )
        for target in cfg["targets"]:
            for variant in cfg["controller_variants"]:
                estimator_cfg = None
                handover_cfg = {"enabled": False}
                controller_delay_schedule = []
                controller_slew_schedule = []
                modeled_delay = int(scenario_cfg["initial_delay"])
                modeled_slew = float(scenario_cfg["initial_slew"])
                if variant == "oracle_schedule":
                    controller_delay_schedule = copy.deepcopy(delay_schedule)
                    controller_slew_schedule = copy.deepcopy(slew_schedule)
                elif variant == "fixed_initial":
                    pass
                elif variant == "adaptive_bumpless":
                    estimator_cfg = _estimator_cfg(
                        cfg["estimator"],
                        initial_delay=modeled_delay,
                        initial_slew=modeled_slew,
                    )
                    handover_cfg = copy.deepcopy(cfg["handover"])
                else:
                    raise ValueError(f"unsupported change-point variant {variant}")
                extra = {
                    "horizon_steps": int(cfg["horizon_steps"]),
                    "extended_horizon": False,
                    "slew_scale": base_slew,
                    "controller_slew_scale_estimate": modeled_slew,
                    "actuator_gain_by_mode": [1.0, 1.0, 1.0],
                    "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
                    "action_delay_steps": modeled_delay,
                    "controller_action_delay_steps": modeled_delay,
                    "actual_action_delay_schedule": delay_schedule,
                    "actual_slew_scale_schedule": slew_schedule,
                    "controller_action_delay_schedule": controller_delay_schedule,
                    "controller_slew_scale_schedule": controller_slew_schedule,
                    "prime_action_queue_with_nominal": True,
                    "observer_enabled": True,
                    "observer_variant": "control_aware_residual",
                    "anti_windup_enabled": variant != "fixed_initial",
                    "anti_windup_mode": "conditional_weak_actuator" if variant != "fixed_initial" else "off",
                    "conditional_anti_windup_use_actual_actuator_state": False,
                    "force_anti_windup_in_clean": variant != "fixed_initial",
                    "delay_aware_enabled": True,
                    "gain_slew_scheduling_enabled": True,
                    "phase_aware_reference_enabled": True,
                    "known_control_effect_from_measured_current_increment": True,
                    "controller_variant": variant,
                    "adaptive_handover": handover_cfg,
                    "change_point_step": int(scenario_cfg["change_step"]),
                    "change_point_scenario_id": str(scenario_cfg["scenario_id"]),
                }
                if estimator_cfg is not None:
                    extra["adaptive_delay_slew_estimator"] = estimator_cfg
                specs.append(
                    _make_spec(
                        phase="change_point_diagnostics",
                        scenario=f"{scenario_cfg['scenario_id']}__{target['target_id']}__{variant}",
                        category="change_point_diagnostics",
                        target=target,
                        controller_scale=float(ctx.r4_ctx.r3_ctx.source_scale),
                        environment_variant=variant_id,
                        extra=extra,
                    )
                )
    return specs


def summarize_change_point(ctx: Stage41R5Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["change_point_diagnostics"]
    if not rows:
        return {"schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "change_point_diagnostics", "enabled": False, "passed": True}
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (str(row.get("scenario", "")).split("__")[0], str(row["target_id"]))
        grouped.setdefault(key, {})[str(row["controller_variant"])] = row
    final_correct: list[bool] = []
    latencies: list[int] = []
    oracle_feasible = 0
    adaptive_passes = 0
    fixed_fail_oracle_pass = 0
    recoveries = 0
    case_rows: list[dict[str, Any]] = []
    scenario_by_id = {str(row["scenario_id"]): row for row in cfg["scenarios"]}
    for key, variants in sorted(grouped.items()):
        scenario_cfg = scenario_by_id[key[0]]
        oracle = variants.get("oracle_schedule")
        fixed = variants.get("fixed_initial")
        adaptive = variants.get("adaptive_bumpless")
        if not (oracle and fixed and adaptive):
            continue
        oracle_pass = _as_bool(oracle.get("stage3_4_target_tracking_pass"))
        adaptive_pass = _as_bool(adaptive.get("stage3_4_target_tracking_pass"))
        fixed_pass = _as_bool(fixed.get("stage3_4_target_tracking_pass"))
        if oracle_pass:
            oracle_feasible += 1
            adaptive_passes += int(adaptive_pass)
            if not fixed_pass:
                fixed_fail_oracle_pass += 1
                recoveries += int(adaptive_pass)
        correct = (
            int(adaptive.get("adaptive_estimated_delay_steps", -999)) == int(scenario_cfg["final_delay"])
            and math.isclose(
                _as_float(adaptive.get("adaptive_estimated_slew_scale"), 1e9),
                float(scenario_cfg["final_slew"]),
                abs_tol=1e-12,
            )
        )
        final_correct.append(correct)
        change_step = int(scenario_cfg["change_step"])
        transition_steps = [
            int(item.get("step", -999))
            for item in (adaptive.get("adaptive_estimator_transitions") or [])
            if int(item.get("step", -999)) >= change_step
            and int(item.get("new_delay_steps", -999)) == int(scenario_cfg["final_delay"])
            and math.isclose(
                _as_float(item.get("new_slew_scale"), 1e9),
                float(scenario_cfg["final_slew"]),
                abs_tol=1e-12,
            )
        ]
        latency = min(transition_steps) - change_step if transition_steps else 999
        latencies.append(latency)
        case_rows.append({
            "scenario_id": key[0],
            "target_id": key[1],
            "change_step": change_step,
            "oracle_pass": oracle_pass,
            "fixed_initial_pass": fixed_pass,
            "adaptive_pass": adaptive_pass,
            "final_identification_correct": correct,
            "detection_latency_steps": latency,
            "oracle_margin": oracle.get("stage3_4_tracking_minimum_signed_margin"),
            "adaptive_margin": adaptive.get("stage3_4_tracking_minimum_signed_margin"),
        })
    identification_fraction = float(np.mean(final_correct)) if final_correct else 0.0
    preservation = adaptive_passes / max(oracle_feasible, 1)
    recovery = recoveries / max(fixed_fail_oracle_pass, 1) if fixed_fail_oracle_pass else 1.0
    max_latency = max(latencies, default=999)
    execution_complete = all(bool(row.get("success")) for row in rows)
    passed = bool(
        execution_complete
        and identification_fraction >= float(cfg["minimum_final_identification_fraction"])
        and max_latency <= int(cfg["maximum_detection_latency_steps"])
        and preservation >= float(cfg["minimum_adaptive_preservation_of_oracle_passes"])
        and recovery >= float(cfg["minimum_recovery_over_fixed_initial"])
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "change_point_diagnostics",
        "enabled": True,
        "n_rollouts": len(rows),
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "execution_complete": execution_complete,
        "final_identification_fraction": identification_fraction,
        "maximum_detection_latency_steps": max_latency,
        "oracle_feasible_cases": oracle_feasible,
        "adaptive_preservation_fraction": preservation,
        "fixed_initial_failures_with_oracle_pass": fixed_fail_oracle_pass,
        "adaptive_recoveries": recoveries,
        "recovery_fraction": recovery,
        "passed": passed,
        "diagnostic_only_if_control_gate_fails": bool(cfg.get("diagnostic_only_if_control_gate_fails", True)),
        "case_summaries": case_rows,
        "warning": "Instantaneous integer-delay changes use the explicitly defined finite diagnostic command-index model; they are not a hardware actuator model.",
    }


def run_change_point(ctx: Stage41R5Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_change_point_specs(ctx)
    if not specs:
        summary = summarize_change_point(ctx, [])
    else:
        results = evaluate_specs(ctx, specs, output_dir=ctx.paths.change_point / "raw", backend=backend, resume=resume)
        rows = [result_row(ctx, result) for result in results]
        summary = summarize_change_point(ctx, rows)
        write_csv(ctx.paths.change_point / "results.csv", rows)
        atomic_write_json(ctx.paths.change_point / "results.json", rows)
        write_csv(ctx.paths.change_point / "case_summary.csv", summary["case_summaries"])
    atomic_write_json(ctx.paths.change_point / "summary.json", summary)
    _update_state(ctx, change_point_complete=True, change_point_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Restart audit
# ---------------------------------------------------------------------------


def run_restart_audit(ctx: Stage41R5Context) -> dict[str, Any]:
    cfg = ctx.cfg["restart_audit"]
    simulation_root = Path(ctx.r4_ctx.r3_ctx.source_env_cfg["simulation_root"]).expanduser()
    base_folder = str(ctx.r4_ctx.r3_ctx.source_env_cfg.get("start_folder", "1100ms"))
    explicit = os.environ.get(str(cfg["environment_variable"]), "").strip()
    candidates: list[str] = []
    if explicit:
        candidates.extend(item.strip() for item in explicit.split(",") if item.strip())
    if bool(cfg.get("auto_discover", True)):
        try:
            base_ms = int(base_folder.lower().replace("ms", ""))
        except ValueError:
            base_ms = 1100
        candidates.extend(f"{base_ms + int(offset)}ms" for offset in cfg.get("candidate_offsets_ms", []))
    discovered: list[str] = []
    missing: list[str] = []
    for folder in dict.fromkeys(candidates):
        if folder == base_folder:
            continue
        if (simulation_root / folder).is_dir():
            discovered.append(folder)
        else:
            missing.append(folder)
    minimum = int(cfg["minimum_alternate_folders_for_true_validation"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_audit",
        "simulation_root": str(simulation_root),
        "base_start_folder": base_folder,
        "discovered_alternate_folders": discovered,
        "missing_candidates": missing,
        "minimum_required": minimum,
        "true_restart_validation_available": len(discovered) >= minimum,
        "true_restart_validation_performed": False,
    }
    atomic_write_json(ctx.paths.restart / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------


def _load_phase_result(phase_dir: Path, experiment_id: str) -> dict[str, Any]:
    return read_json_gz(phase_dir / "raw" / f"{experiment_id}.json.gz")


def _clone_confirmation_spec(
    source_spec: dict[str, Any],
    *,
    group: str,
    repeat: int,
    category: str,
) -> dict[str, Any]:
    spec = copy.deepcopy(source_spec)
    spec["phase"] = "confirmation"
    spec["category"] = category
    spec["confirmation_group"] = group
    spec["confirmation_repeat"] = int(repeat)
    spec["scenario"] = f"{group}__rep{repeat}"
    spec["experiment_id"] = _scenario_digest(
        CONTROLLER_REVISION,
        "confirmation",
        group,
        repeat,
        spec.get("target_id"),
        spec.get("controller_variant"),
        spec.get("actual_action_delay_schedule"),
        spec.get("actual_slew_scale_schedule"),
    )
    spec["controller_revision"] = CONTROLLER_REVISION
    return spec


def _ensure_variants_for_specs(ctx: Stage41R5Context, specs: Sequence[dict[str, Any]]) -> None:
    for spec in specs:
        schedule = spec.get("actual_slew_scale_schedule") or []
        if schedule:
            slew = max(float(item["slew_scale"]) for item in schedule)
        else:
            slew = float(spec.get("slew_scale", 1.0))
        variant_id, _ = materialize_variant(ctx, slew_scale=slew, horizon_steps=35)
        spec["environment_variant"] = variant_id


def build_confirmation_specs(ctx: Stage41R5Context) -> list[dict[str, Any]]:
    state = read_json(ctx.paths.state)
    specs: list[dict[str, Any]] = []
    estimator_summary = state.get("estimator_only_summary") or {}
    if estimator_summary.get("passed"):
        specs.extend(build_estimator_only_specs(ctx, repeats=True))

    static_summary = state.get("static_handover_summary") or {}
    if static_summary.get("passed"):
        rows = read_json(ctx.paths.static_handover / "results.json")
        candidates = [
            row for row in rows
            if row.get("controller_variant") == "r5_bumpless_unknown"
            and _as_bool(row.get("stage3_4_target_tracking_pass"))
        ]
        by_pair: dict[tuple[int, float], list[dict[str, Any]]] = {}
        for row in candidates:
            key = (int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"]))
            by_pair.setdefault(key, []).append(row)
        repeats = int(ctx.cfg["static_handover"]["confirmation_repeats_per_pair"])
        for key, group_rows in sorted(by_pair.items()):
            selected = min(
                group_rows,
                key=lambda row: _as_float(row.get("stage3_4_tracking_minimum_signed_margin"), 1e9),
            )
            source = _load_phase_result(ctx.paths.static_handover, selected["experiment_id"])
            group = f"static_d{key[0]}_s{key[1]:.1f}"
            for repeat in range(repeats):
                specs.append(_clone_confirmation_spec(source["spec"], group=group, repeat=repeat, category="static_handover_confirmation"))

    change_summary = state.get("change_point_summary") or {}
    if change_summary.get("passed"):
        rows = read_json(ctx.paths.change_point / "results.json")
        candidates = [
            row for row in rows
            if row.get("controller_variant") == "adaptive_bumpless"
            and _as_bool(row.get("stage3_4_target_tracking_pass"))
        ]
        by_scenario: dict[str, list[dict[str, Any]]] = {}
        for row in candidates:
            scenario_id = str(row.get("scenario", "")).split("__")[0]
            by_scenario.setdefault(scenario_id, []).append(row)
        repeats = int(ctx.cfg["change_point_diagnostics"]["confirmation_repeats_per_scenario"])
        for scenario_id, group_rows in sorted(by_scenario.items()):
            selected = min(
                group_rows,
                key=lambda row: _as_float(row.get("stage3_4_tracking_minimum_signed_margin"), 1e9),
            )
            source = _load_phase_result(ctx.paths.change_point, selected["experiment_id"])
            for repeat in range(repeats):
                specs.append(_clone_confirmation_spec(source["spec"], group=f"change_{scenario_id}", repeat=repeat, category="change_point_confirmation"))
    _ensure_variants_for_specs(ctx, specs)
    return specs


def summarize_confirmation(ctx: Stage41R5Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("confirmation_group")), []).append(row)
    group_rows: list[dict[str, Any]] = []
    estimator_pairs = 0
    estimator_pairs_pass = 0
    static_pairs = 0
    static_pairs_pass = 0
    change_scenarios = 0
    change_scenarios_pass = 0
    max_slew_error = float(ctx.cfg["estimator_only_confirmation"].get("maximum_slew_absolute_error", 0.051))
    for group, subset in sorted(grouped.items()):
        category = str(subset[0].get("category", "")) if subset else ""
        success = all(bool(row.get("success")) for row in subset)
        identification = all(
            int(row.get("adaptive_estimated_delay_steps", -999)) == int(row.get("final_actual_delay_steps", row.get("actual_action_delay_steps", -999)))
            and abs(
                _as_float(row.get("adaptive_estimated_slew_scale"), 1e9)
                - _as_float(row.get("final_actual_slew_scale", row.get("actual_slew_scale", 1e9)))
            ) <= max_slew_error
            for row in subset
        )
        tracking_required = category != "estimator_only"
        tracking = all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in subset) if tracking_required else True
        passed = bool(success and identification and tracking)
        scenario_type = (
            "estimator" if category == "estimator_only"
            else "change_point" if category == "change_point_confirmation"
            else "static_handover"
        )
        if scenario_type == "estimator":
            estimator_pairs += 1
            estimator_pairs_pass += int(passed)
        elif scenario_type == "static_handover":
            static_pairs += 1
            static_pairs_pass += int(passed)
        else:
            change_scenarios += 1
            change_scenarios_pass += int(passed)
        group_rows.append({
            "confirmation_group": group,
            "scenario_type": scenario_type,
            "repeats": len(subset),
            "all_successful": success,
            "all_identification_correct": identification,
            "all_tracking_pass": tracking,
            "passed": passed,
        })
    estimator_ok = estimator_pairs >= int(ctx.cfg["estimator_only_confirmation"]["minimum_distinct_pairs_confirmed"]) and estimator_pairs_pass == estimator_pairs
    static_ok = static_pairs >= int(ctx.cfg["static_handover"]["minimum_distinct_pairs_confirmed"]) and static_pairs_pass == static_pairs
    change_required = bool((read_json(ctx.paths.state).get("change_point_summary") or {}).get("passed", False))
    change_ok = (
        not change_required
        or (
            change_scenarios >= int(ctx.cfg["change_point_diagnostics"]["minimum_change_scenarios_confirmed"])
            and change_scenarios_pass == change_scenarios
        )
    )
    passed = bool(estimator_ok and static_ok and change_ok)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "confirmation",
        "n_rollouts": len(rows),
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "n_estimator_pairs": estimator_pairs,
        "n_estimator_pairs_passed": estimator_pairs_pass,
        "n_static_pairs": static_pairs,
        "n_static_pairs_passed": static_pairs_pass,
        "n_change_scenarios": change_scenarios,
        "n_change_scenarios_passed": change_scenarios_pass,
        "change_confirmation_required": change_required,
        "passed": passed,
        "group_summaries": group_rows,
    }


def run_confirmation(ctx: Stage41R5Context, *, backend: str, resume: bool) -> dict[str, Any]:
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
# Analysis and execution
# ---------------------------------------------------------------------------


def analyze(ctx: Stage41R5Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    estimator = state.get("estimator_only_summary") or {}
    static = state.get("static_handover_summary") or {}
    change = state.get("change_point_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    confirmation = state.get("confirmation_summary") or {}
    static_closure = bool(source.get("passed") and estimator.get("passed") and static.get("passed") and confirmation.get("passed"))
    change_pass = bool(change.get("passed", False))
    true_restart_available = bool(restart.get("true_restart_validation_available", False))
    if static_closure and change_pass and not true_restart_available:
        verdict = "PASS_STAGE4_1R5_BUMPLESS_HANDOVER_AND_CHANGE_POINT_FINITE_BANK_CONFIRMED_TRUE_RESTART_NOT_AVAILABLE"
    elif static_closure and change_pass:
        verdict = "PASS_STAGE4_1R5_BUMPLESS_HANDOVER_AND_CHANGE_POINT_FINITE_BANK_CONFIRMED_TRUE_RESTART_NOT_YET_VALIDATED"
    elif static_closure:
        verdict = "PASS_STAGE4_1R5_STATIC_BUMPLESS_HANDOVER_CONFIRMED_CHANGE_POINT_DIAGNOSTIC_INCOMPLETE"
    else:
        verdict = "STAGE4_1R5_ADAPTIVE_HANDOVER_CLOSURE_INCOMPLETE"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r4_run": str(ctx.source_stage41r4_run),
        "source_audit_passed": bool(source.get("passed", False)),
        "estimator_only_confirmation_passed": bool(estimator.get("passed", False)),
        "static_bumpless_handover_passed": bool(static.get("passed", False)),
        "change_point_diagnostic_passed": change_pass,
        "confirmation_passed": bool(confirmation.get("passed", False)),
        "source_weak_slew_370ms_passed": bool(source.get("source_weak_slew_passed", False)),
        "source_weak_slew_minimum_margin": source.get("source_weak_slew_minimum_margin"),
        "true_restart_validation_available": true_restart_available,
        "true_restart_validation_performed": False,
        "finite_static_handover_envelope_validated": static_closure,
        "finite_change_point_diagnostic_validated": bool(static_closure and change_pass),
        "deployment_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "online_estimator_is_finite_hypothesis_bank_poc": True,
        "warning": (
            "The delay bank is limited to integer 0/1/2-step latency and slew 0.9/1.0/1.1. "
            "The change-point delay model is a finite diagnostic mapping, not a hardware actuator model."
        ),
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "estimator_only": estimator,
            "static_handover": static,
            "change_point": change,
            "restart_audit": restart,
            "confirmation": confirmation,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r5_analysis_summary.json", summary)
    atomic_write_json(ctx.paths.analysis / "stage4_1r5_verdict.json", summary)
    _update_state(ctx, finished=True, stop_reason="pipeline_complete", analysis_summary=summary)
    return summary


def execute(
    *,
    config_path: str | Path,
    source_stage41r4_run: str | Path | None,
    run_dir: str | Path | None,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx = load_stage41r5_config(
        config_path,
        source_stage41r4_run=source_stage41r4_run,
        run_dir_override=run_dir,
    )
    initialize_run(ctx)
    command = str(command)
    if command in {"all", "audit"}:
        run_source_audit(ctx)
        if command == "audit":
            return read_json(ctx.paths.state)
    if command in {"all", "estimator_only"}:
        estimator_summary = run_estimator_only(ctx, backend=backend, resume=resume)
        if command == "estimator_only":
            return read_json(ctx.paths.state)
        if not bool(estimator_summary.get("passed", False)):
            _update_state(
                ctx,
                finished=True,
                stop_reason="estimator_only_confirmation_failed",
            )
            return analyze(ctx)
    if command in {"all", "handover"}:
        handover_summary = run_static_handover(ctx, backend=backend, resume=resume)
        if command == "handover":
            return read_json(ctx.paths.state)
        if not bool(handover_summary.get("passed", False)):
            _update_state(
                ctx,
                finished=True,
                stop_reason="static_bumpless_handover_failed",
            )
            return analyze(ctx)
    if command in {"all", "change_point"}:
        run_change_point(ctx, backend=backend, resume=resume)
        if command == "change_point":
            return read_json(ctx.paths.state)
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
        modes_tsc=np.eye(14, 3),
        nominal_max_delta_a=3.0,
        command_max_delta_a=3.0,
        min_current=-1e6 * np.ones(14),
        max_current=1e6 * np.ones(14),
        lower_mode=np.array([-2.6, -2.6, -0.9]),
        upper_mode=np.array([2.6, 2.6, 0.9]),
    )
    bank = r3.DelaySlewHypothesisBank(
        scheduler=scheduler,
        delay_candidates=(0, 1, 2),
        slew_candidates=(0.9, 1.0, 1.1),
        minimum_observations=2,
        switch_hysteresis_fraction=0.0,
    )
    nominal = np.asarray(
        [[0.15 + 0.04 * k, -0.10 + 0.03 * k, 0.02 * (-1) ** k] for k in range(10)],
        dtype=float,
    )
    actual_delay = 2
    actual_slew = 1.1
    issued: list[np.ndarray] = []
    currents = np.zeros(14)
    for step in range(len(nominal)):
        issued.append(nominal[step].copy())
        command = nominal[step] if step < actual_delay else issued[step - actual_delay]
        observed = scheduler.predicted_delta_a(command, currents, np.ones(3), actual_slew)
        bank.update(
            step=step,
            observed_delta_a=observed,
            currents_before_a=currents,
            issued_commands=issued,
            nominal_commands=nominal,
        )
        currents += observed
    return {
        "stage": STAGE,
        "selected_delay_steps": bank.selected_delay_steps,
        "selected_slew_scale": bank.selected_slew_scale,
        "first_lock_step": bank.first_lock_step,
        "confidence_ratio": bank.last_confidence_ratio,
        "passed": bool(
            bank.selected_delay_steps == actual_delay
            and math.isclose(bank.selected_slew_scale, actual_slew, abs_tol=1e-12)
            and bank.first_lock_step is not None
            and bank.first_lock_step <= 2
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage4.1R5 adaptive bumpless delay/slew handover closure")
    parser.add_argument("--config", default="configs/stage4_1r5_adaptive_handover_closure_350ms.json")
    parser.add_argument("--source-stage4-1r4-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument(
        "--command",
        default="all",
        choices=["all", "prepare", "audit", "estimator_only", "handover", "change_point", "restart", "confirm", "analyze"],
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
        source_stage41r4_run=args.source_stage4_1r4_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
