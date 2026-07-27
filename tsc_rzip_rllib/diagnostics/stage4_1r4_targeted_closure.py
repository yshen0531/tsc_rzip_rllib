"""Stage4.1R4 targeted closure for weak-slew timing and delay/slew estimation.

This revision deliberately does not repeat the full Stage4.1R3 robustness
campaign.  It consumes a completed Stage4.1R3 run and closes the two remaining
well-isolated gaps:

1. Correct category accounting when no open-loop baseline passes exist.
2. Verify the 0.9x-slew plant with a 370 ms episode, a 270 ms latest-arrival
   deadline, and at least 100 ms of follow-up hold.
3. Evaluate a finite online delay/slew hypothesis bank using only issued
   commands and measured 14-coil current increments.

The strongest verdict is still a finite research envelope.  It is not hardware
qualification, general plant-parameter robustness, or true restart-state
validation.
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
from types import SimpleNamespace
from typing import Any, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as base
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_4_late_arrival_continuation_mpc as s34
from tsc_rzip_rllib.diagnostics import stage4_1r3_control_aware_robustness as r3
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

SCHEMA_VERSION = 1
STAGE = "Stage4.1R4"
CONTROLLER_REVISION = "targeted_weak_slew_and_online_delay_slew_estimator_v4"
STATE_FILENAME = "stage4_1r4_state.json"
MANIFEST_FILENAME = "stage4_1r4_manifest.json"
EXPECTED_SOURCE_REVISION = "control_aware_residual_observer_antiwindup_v3"
EXPECTED_SOURCE_STAGE = "Stage4.1R3"


# ---------------------------------------------------------------------------
# Strict JSON / CSV utilities
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
        return {str(key): _json_safe(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, f"{path}[{index}]") for index, item in enumerate(value)]
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
            json.dump(_json_safe(payload), handle, ensure_ascii=False, indent=2, allow_nan=False)
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _scenario_digest(*parts: Any, prefix: str = "s41r4") -> str:
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
# Paths / source context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage41R4Paths:
    run_dir: Path
    state: Path
    manifest: Path
    reclassification: Path
    weak_slew: Path
    estimator: Path
    restart: Path
    confirmation: Path
    analysis: Path
    variants: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R4Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            reclassification=run_dir / "stage4_1r4_source_reclassification",
            weak_slew=run_dir / "stage4_1r4_weak_slew_370ms",
            estimator=run_dir / "stage4_1r4_delay_slew_estimator",
            restart=run_dir / "stage4_1r4_restart_audit",
            confirmation=run_dir / "stage4_1r4_confirmation",
            analysis=run_dir / "stage4_1r4_analysis",
            variants=run_dir / "stage4_1r4_environment_variants",
            source_reference=run_dir / "source_stage4_1r3_reference",
        )


@dataclass
class Stage41R4Context:
    cfg: dict[str, Any]
    paths: Stage41R4Paths
    project_dir: Path
    source_stage41r3_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_verdict: dict[str, Any]
    source_r3_cfg: dict[str, Any]
    source_stage40_run: Path
    r3_ctx: r3.Stage41Context
    source_fingerprint: dict[str, Any]
    variants: dict[str, dict[str, Any]]


def resolve_source_stage41r3_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE4_1R3_RUN", "").strip()
    if not value:
        raise ValueError("Stage4.1R4 requires --source-stage4-1r3-run or SOURCE_STAGE4_1R3_RUN")
    run = Path(value).expanduser().resolve()
    required = [
        run / "stage4_1r3_manifest.json",
        run / "stage4_1r3_state.json",
        run / "stage4_1r3_config.resolved.json",
        run / "stage4_1r3_analysis/stage4_1r3_verdict.json",
        run / "stage4_1r3_structured_uncertainty/pairs.csv",
        run / "stage4_1r3_structured_uncertainty/summary.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage4.1R3 source run: " + ", ".join(missing))
    return run


def _resolve_source_stage40(project_dir: Path, source_manifest: dict[str, Any]) -> Path:
    raw = str(source_manifest.get("source_stage4_0_run", "")).strip()
    if not raw:
        raise ValueError("Stage4.1R3 manifest has no source_stage4_0_run")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (project_dir / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        fallback = project_dir / "stage4_0_runs" / path.name
        if fallback.exists():
            path = fallback.resolve()
    return r3.resolve_source_stage40_run(path)


def _source_inventory(source_r3: Path, source40: Path, source34: Path) -> dict[str, Any]:
    logical_paths: list[tuple[str, Path]] = [
        ("stage4_1r3/manifest.json", source_r3 / "stage4_1r3_manifest.json"),
        ("stage4_1r3/state.json", source_r3 / "stage4_1r3_state.json"),
        ("stage4_1r3/config.json", source_r3 / "stage4_1r3_config.resolved.json"),
        ("stage4_1r3/verdict.json", source_r3 / "stage4_1r3_analysis/stage4_1r3_verdict.json"),
        ("stage4_1r3/structured_pairs.csv", source_r3 / "stage4_1r3_structured_uncertainty/pairs.csv"),
        ("stage4_1r3/structured_summary.json", source_r3 / "stage4_1r3_structured_uncertainty/summary.json"),
        ("stage4_0/manifest.json", source40 / "stage4_0_manifest.json"),
        ("stage3_4/config.json", source34 / "stage3_4_config.resolved.json"),
        ("stage3_4/library.json", source34 / "stage3_4_target_library/target_library.json"),
        ("stage3_4/bundle.json", source34 / "stage3_4_identification/full_horizon_bundle.json"),
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


def validate_source_r3(ctx_cfg: dict[str, Any], state: dict[str, Any], verdict: dict[str, Any], manifest: dict[str, Any]) -> None:
    req = ctx_cfg["source_requirement"]
    if str(manifest.get("stage")) != EXPECTED_SOURCE_STAGE:
        raise ValueError(f"source stage must be {EXPECTED_SOURCE_STAGE}")
    if str(manifest.get("controller_revision")) != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R3 controller revision is unsupported")
    checks = {
        "regression_passed": bool(req.get("require_regression_passed", True)),
        "observer_ablation_passed": bool(req.get("require_observer_ablation_passed", True)),
        "failure_recovery_passed": bool(req.get("require_failure_recovery_passed", True)),
        "noise_statistics_passed": bool(req.get("require_noise_statistics_passed", True)),
        "phase_aligned_history_passed": bool(req.get("require_phase_aligned_history_passed", True)),
        "confirmation_passed": bool(req.get("require_confirmation_passed", True)),
    }
    for key, required in checks.items():
        if required and not bool(verdict.get(key, False)):
            raise ValueError(f"source Stage4.1R3 does not satisfy required flag {key}")
    if not bool(state.get("finished", False)):
        raise ValueError("source Stage4.1R3 run is not finished")
    if str(state.get("selected_observer_variant")) != "control_aware_residual":
        raise ValueError("source Stage4.1R3 did not select the control-aware residual observer")


def validate_config(cfg: dict[str, Any], source_r3_cfg: dict[str, Any]) -> None:
    if str(cfg.get("controller_revision")) != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R4 controller_revision mismatch")
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.1R4 complete package is intentionally configured for 128 workers")
    source_gate = source_r3_cfg["gate"]
    gate = cfg["gate"]
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
            raise ValueError(f"Stage4.1R4 hard gate {key} differs from Stage4.1R3")
    for key in ("terminal_abs_tolerance_A", "hold_rms_tolerance_A", "sustained_max_tolerance_A"):
        if not math.isclose(
            float(gate["ip_tracking"][key]),
            float(source_gate["ip_tracking"][key]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"Stage4.1R4 Ip tracking threshold {key} differs from Stage4.1R3")
    weak = cfg["weak_slew_closure"]
    if int(weak["horizon_steps"]) != 37 or int(weak["hold_through_step"]) != 37:
        raise ValueError("Stage4.1R4 weak-slew closure is fixed to 370 ms")
    latest = max(map(int, weak["allowed_arrival_steps"]))
    if int(weak["hold_through_step"]) - latest < int(weak["minimum_post_arrival_hold_steps"]):
        raise ValueError("weak-slew latest arrival does not have 100 ms follow-up hold")


def load_stage41r4_config(
    config_path: str | Path,
    *,
    source_stage41r3_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage41R4Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = base.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)},
    )
    source_r3 = resolve_source_stage41r3_run(source_stage41r3_run)
    source_manifest = read_json(source_r3 / "stage4_1r3_manifest.json")
    source_state = read_json(source_r3 / "stage4_1r3_state.json")
    source_verdict = read_json(source_r3 / "stage4_1r3_analysis/stage4_1r3_verdict.json")
    source_r3_cfg = read_json(source_r3 / "stage4_1r3_config.resolved.json")
    validate_source_r3(cfg, source_state, source_verdict, source_manifest)
    validate_config(cfg, source_r3_cfg)
    source40 = _resolve_source_stage40(project_dir, source_manifest)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage4_1r4_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r4_targeted_closure_370ms')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)
    r3_ctx = r3.load_stage41_config(
        source_r3 / "stage4_1r3_config.resolved.json",
        source_stage40_run=source40,
        run_dir_override=run_dir,
    )
    # The R4 package retains the validated R3 controller and only adds the
    # conditional weak-actuator trigger and estimator support.
    r3_cfg = copy.deepcopy(r3_ctx.cfg)
    r3_cfg["controller_upgrade"]["anti_windup"].update(
        copy.deepcopy(cfg.get("controller_upgrade", {}).get("anti_windup", {}))
    )
    r3_ctx.cfg = r3_cfg
    storage = cfg["storage"]
    env_cfg = copy.deepcopy(r3_ctx.source_env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"].get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_1R4_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R4_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg = copy.deepcopy(r3_ctx.source_train_cfg)
    train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 35
    r3_ctx.source_env_cfg = env_cfg
    r3_ctx.source_train_cfg = train_cfg
    r3_ctx.base34.env_cfg = env_cfg
    r3_ctx.base34.train_cfg = train_cfg
    return Stage41R4Context(
        cfg=cfg,
        paths=Stage41R4Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r3_run=source_r3,
        source_manifest=source_manifest,
        source_state=source_state,
        source_verdict=source_verdict,
        source_r3_cfg=source_r3_cfg,
        source_stage40_run=source40,
        r3_ctx=r3_ctx,
        source_fingerprint=_source_inventory(source_r3, source40, r3_ctx.source_stage34_run),
        variants={},
    )


def _available_memory_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return float(line.split()[1]) / (1024.0 * 1024.0)
    except Exception:
        pass
    return math.nan


def runtime_preflight(ctx: Stage41R4Context) -> dict[str, Any]:
    requested = int(os.environ.get("STAGE4_1R4_WORKERS", ctx.cfg["parallel"]["n_workers"]))
    logical = int(os.cpu_count() or 1)
    reserve = int(ctx.cfg["parallel"].get("reserve_logical_cpus", 16))
    ceiling = max(1, logical - reserve)
    if requested > ceiling:
        raise RuntimeError(
            f"Stage4.1R4 requests {requested} workers but safe ceiling is {ceiling} "
            f"({logical} visible, reserve={reserve}); no silent fallback is allowed"
        )
    memory = _available_memory_gb()
    configured = int(ctx.cfg["parallel"]["n_workers"])
    minimum = float(ctx.cfg["parallel"].get("minimum_available_memory_gb", 72.0)) * requested / configured
    if math.isfinite(memory) and memory < minimum:
        raise RuntimeError(f"Stage4.1R4 requires {minimum:.1f} GiB available memory; {memory:.1f} GiB visible")
    soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
    required_fd = max(1024, requested * 16)
    if soft_fd < required_fd:
        raise RuntimeError(f"open-file soft limit {soft_fd} is below required {required_fd}")
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
        "prepared": True,
        "reclassification_complete": False,
        "weak_slew_complete": False,
        "estimator_complete": False,
        "restart_audit_complete": False,
        "confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R4Context, **values: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(values)
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def initialize_run(ctx: Stage41R4Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.reclassification,
        ctx.paths.weak_slew,
        ctx.paths.estimator,
        ctx.paths.restart,
        ctx.paths.confirmation,
        ctx.paths.analysis,
        ctx.paths.variants,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if str(old.get("controller_revision")) != CONTROLLER_REVISION:
            raise ValueError("existing run uses a different Stage4.1R4 controller revision")
        if Path(old["source_stage4_1r3_run"]).resolve() != ctx.source_stage41r3_run:
            raise ValueError("existing Stage4.1R4 run points to a different Stage4.1R3 source")
        old_digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        if old_digest and old_digest != ctx.source_fingerprint["digest"]:
            raise ValueError("source Stage4.1R3/Stage4.0/Stage3.4 content changed")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r4_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.r3_ctx.source_train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.r3_ctx.source_env_cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r3_run": str(ctx.source_stage41r3_run),
        "source_stage4_0_run": str(ctx.source_stage40_run),
        "source_stage3_4_run": str(ctx.r3_ctx.source_stage34_run),
        "source_fingerprint": {key: value for key, value in ctx.source_fingerprint.items() if key != "entries"},
        "source_selected_controller_scale": float(ctx.r3_ctx.source_scale),
        "source_selected_observer_variant": ctx.source_state.get("selected_observer_variant"),
        "source_selected_anti_windup_enabled": ctx.source_state.get("selected_anti_windup_enabled"),
        "workers": runtime_preflight(ctx),
        "hard_numeric_thresholds_changed": False,
        "weak_slew_arrival_deadline_extended_to_ms": 270,
        "weak_slew_hold_through_ms": 370,
        "finite_test_envelope_only": True,
        "deployment_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    if not ctx.paths.manifest.exists():
        atomic_write_json(ctx.paths.manifest, manifest)
    inventory = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory.exists():
        atomic_write_json(inventory, ctx.source_fingerprint)
    copy_files = [
        "stage4_1r3_manifest.json",
        "stage4_1r3_state.json",
        "stage4_1r3_config.resolved.json",
        "stage4_1r3_analysis/stage4_1r3_verdict.json",
        "stage4_1r3_structured_uncertainty/pairs.csv",
        "stage4_1r3_structured_uncertainty/summary.json",
    ]
    for relative in copy_files:
        src = ctx.source_stage41r3_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())


# ---------------------------------------------------------------------------
# Environment variants and workers
# ---------------------------------------------------------------------------


def _variant_id(slew: float, horizon: int, start_folder: str | None = None) -> str:
    suffix = f"slew_{slew:.3f}_h{horizon}".replace(".", "p")
    if start_folder:
        suffix += "_" + str(start_folder).replace("/", "_")
    return suffix


def materialize_variant(
    ctx: Stage41R4Context,
    *,
    slew_scale: float,
    horizon_steps: int,
    start_folder: str | None = None,
) -> tuple[str, dict[str, Any]]:
    variant_id = _variant_id(slew_scale, horizon_steps, start_folder)
    if variant_id in ctx.variants:
        return variant_id, ctx.variants[variant_id]
    env_cfg = copy.deepcopy(ctx.r3_ctx.source_env_cfg)
    env_cfg["current_slew_a_per_ms"] = float(ctx.r3_ctx.source_env_cfg["current_slew_a_per_ms"]) * float(slew_scale)
    if start_folder is not None:
        env_cfg["start_folder"] = str(start_folder)
    env_path = ctx.paths.variants / f"env_{variant_id}.json"
    train_path = ctx.paths.variants / f"train_{variant_id}.json"
    train_cfg = copy.deepcopy(ctx.r3_ctx.source_train_cfg)
    train_cfg["env_config"] = str(env_path)
    train_cfg.setdefault("episode", {})["max_episode_steps"] = int(horizon_steps)
    atomic_write_json(env_path, env_cfg)
    atomic_write_json(train_path, train_cfg)
    payload = s34._context_payload(ctx.r3_ctx.base34)
    payload["train_cfg"] = train_cfg
    payload["env_cfg"] = env_cfg
    payload["max_delta_a"] = float(env_cfg["current_slew_a_per_ms"]) * float(env_cfg["dt_ms"])
    payload["nominal_max_delta_a"] = float(ctx.r3_ctx.source_env_cfg["current_slew_a_per_ms"]) * float(ctx.r3_ctx.source_env_cfg["dt_ms"])
    payload["stage4_1_cfg"] = copy.deepcopy(ctx.r3_ctx.cfg)
    payload["variant_id"] = variant_id
    payload["start_folder"] = env_cfg.get("start_folder")
    payload["slew_scale"] = float(slew_scale)
    payload["stage4_1r4_horizon_steps"] = int(horizon_steps)
    ctx.variants[variant_id] = payload
    return variant_id, payload


class LocalStage41R4Worker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str):
        self.inner = r3.LocalStage41Worker(payload, library, bundle, worker_id)
        self.horizon_steps = int(payload.get("stage4_1r4_horizon_steps", 35))

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        extended = bool(spec.get("extended_horizon", False))
        if not extended:
            result = self.inner.evaluate(spec)
            result["stage4_1r4_controller_revision"] = CONTROLLER_REVISION
            return _json_safe(result)
        if self.horizon_steps != 37:
            raise ValueError("extended Stage4.1R4 evaluation requires a 37-step environment")
        internal = copy.deepcopy(spec)
        internal["_defer_cleanup"] = True
        started = time.time()
        result = self.inner.evaluate(internal)
        original_spec = copy.deepcopy(spec)
        result["spec"] = original_spec
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r4_controller_revision"] = CONTROLLER_REVISION
        try:
            if result.get("success"):
                tail_steps = int(spec.get("tail_hold_steps", 2))
                policy = str(spec.get("tail_action_policy", "zero_current_increment"))
                if tail_steps != 2 or policy != "zero_current_increment":
                    raise ValueError("this Stage4.1R4 release supports exactly two zero-increment tail steps")
                trajectory = list(result.get("trajectory", []))
                zero = np.zeros(14, dtype=np.float32)
                for index in range(tail_steps):
                    _, _, terminated, truncated, info = self.inner.env.step(zero)
                    trajectory.append(base._state_record(self.inner.env, 36 + index, zero))
                    if terminated:
                        raise RuntimeError(str(info.get("failure_reason", "tail terminated")))
                    if truncated and index + 1 < tail_steps:
                        raise RuntimeError("environment truncated before the 370 ms tail completed")
                result["trajectory"] = trajectory
                result["success"] = bool(
                    len(trajectory) == 38
                    and not any(bool(row.get("abnormal", False)) for row in trajectory)
                )
                result["failure_reason"] = "" if result["success"] else "incomplete/abnormal 370 ms trajectory"
                result["stage4_1r4_tail_policy"] = policy
                result["stage4_1r4_tail_steps"] = tail_steps
            result["wall_time_s"] = float(time.time() - started)
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
            return _json_safe(result)
        finally:
            runner = getattr(self.inner.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=not bool(result.get("success")),
                    reason=str(result.get("failure_reason", "stage4_1r4_complete")),
                )

    def close(self) -> None:
        self.inner.close()


def _ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id):
            self.worker = LocalStage41R4Worker(payload, library, bundle, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor


def evaluate_specs(
    ctx: Stage41R4Context,
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
        if variant not in ctx.variants:
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
            worker = LocalStage41R4Worker(
                ctx.variants[variant],
                ctx.r3_ctx.source_library,
                ctx.r3_ctx.source_bundle,
                f"stage41r4_{variant}_serial",
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz",
                        worker.evaluate(spec),
                    )
                    print(f"[Stage4.1R4 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(os.environ.get("STAGE4_1R4_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R4 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()},
            plan.actor_count,
        )
        print(
            "[Stage4.1R4 mixed-variant] actor_allocation="
            + json.dumps(allocation, sort_keys=True, separators=(",", ":")),
            flush=True,
        )
        Actor = _ray_actor_class()
        actors_by_variant: dict[str, list[Any]] = {}
        all_actors: list[Any] = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(
                    ctx.variants[variant],
                    ctx.r3_ctx.source_library,
                    ctx.r3_ctx.source_bundle,
                    f"stage41r4_{variant}_{index:03d}",
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
                    print(f"[Stage4.1R4 mixed-variant] waiting {done}/{total_pending}", flush=True)
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
                        print(f"[Stage4.1R4 mixed-variant] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(
                all_actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


# ---------------------------------------------------------------------------
# Source reclassification
# ---------------------------------------------------------------------------


def corrected_category_summary(
    pairs: Sequence[dict[str, Any]],
    required_categories: dict[str, Any],
) -> list[dict[str, Any]]:
    categories = sorted({str(row.get("category", "")) for row in pairs})
    summaries: list[dict[str, Any]] = []
    for category in categories:
        subset = [row for row in pairs if str(row.get("category", "")) == category]
        n_pairs = len(subset)
        n_baseline_pass = sum(_as_bool(row.get("baseline_pass")) for row in subset)
        n_feedback_pass = sum(_as_bool(row.get("feedback_pass")) for row in subset)
        n_preserved = sum(_as_bool(row.get("preserved")) for row in subset)
        n_recovered = sum(_as_bool(row.get("recovered")) for row in subset)
        n_lost = sum(_as_bool(row.get("lost")) for row in subset)
        n_baseline_fail = n_pairs - n_baseline_pass
        mpc_fraction = n_feedback_pass / max(n_pairs, 1)
        preservation_applicable = n_baseline_pass > 0
        preservation = n_preserved / n_baseline_pass if preservation_applicable else None
        recovery_applicable = n_baseline_fail > 0
        recovery = n_recovered / n_baseline_fail if recovery_applicable else None
        threshold = required_categories.get(category)
        required = threshold is not None
        passed: bool | None = None
        if required:
            mpc_ok = mpc_fraction >= float(threshold.get("minimum_mpc_pass_fraction", 0.0))
            if preservation_applicable:
                preservation_ok = float(preservation) >= float(
                    threshold.get("minimum_preserved_fraction", 0.0)
                )
            else:
                preservation_ok = True
            if not preservation_applicable and recovery_applicable:
                recovery_ok = float(recovery) >= float(
                    threshold.get("minimum_recovery_fraction_when_no_baseline_pass", 0.0)
                )
            else:
                recovery_ok = True
            passed = bool(mpc_ok and preservation_ok and recovery_ok and n_lost == 0)
        summaries.append(
            {
                "category": category,
                "n_pairs": n_pairs,
                "n_baseline_pass": n_baseline_pass,
                "n_baseline_fail": n_baseline_fail,
                "n_feedback_pass": n_feedback_pass,
                "mpc_pass_fraction": mpc_fraction,
                "preservation_applicable": preservation_applicable,
                "preserved_open_loop_pass_fraction": preservation,
                "recovery_applicable": recovery_applicable,
                "failure_recovery_fraction": recovery,
                "n_recovered": n_recovered,
                "n_lost": n_lost,
                "required": required,
                "passed": passed,
            }
        )
    return summaries


def run_source_reclassification(ctx: Stage41R4Context) -> dict[str, Any]:
    pair_rows = read_csv(
        ctx.source_stage41r3_run / "stage4_1r3_structured_uncertainty/pairs.csv"
    )
    summaries = corrected_category_summary(
        pair_rows,
        ctx.cfg["source_reclassification"]["required_categories"],
    )
    required = [row for row in summaries if row["required"]]
    unresolved = [row["category"] for row in required if not bool(row["passed"])]
    unresolved_except_scheduled_slew = [
        category for category in unresolved if category != "scheduled_slew"
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_reclassification",
        "source_stage4_1r3_run": str(ctx.source_stage41r3_run),
        "category_summaries": summaries,
        "required_categories_passed_before_r4_closure": len(unresolved) == 0,
        "unresolved_required_categories": unresolved,
        "unresolved_required_categories_except_scheduled_slew": (
            unresolved_except_scheduled_slew
        ),
        "all_non_slew_required_categories_passed": (
            len(unresolved_except_scheduled_slew) == 0
        ),
        "gain_estimation_error_reclassified_without_new_tsc": bool(
            next(
                (
                    row["passed"]
                    for row in summaries
                    if row["category"] == "gain_estimation_error"
                ),
                False,
            )
        ),
    }
    atomic_write_json(ctx.paths.reclassification / "summary.json", summary)
    write_csv(ctx.paths.reclassification / "category_summary.csv", summaries)
    _update_state(
        ctx,
        reclassification_complete=True,
        reclassification_summary=summary,
    )
    return summary


# ---------------------------------------------------------------------------
# Specs and metrics
# ---------------------------------------------------------------------------


def _resolve_scale(value: Any, source_scale: float) -> float:
    if isinstance(value, str) and value == "source_selected":
        return float(source_scale)
    return float(value)


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
        "controller_revision": CONTROLLER_REVISION,
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target": target,
        "controller_scale": controller_scale,
        "environment_variant": environment_variant,
        "extra": extra,
    }
    return {
        "kind": "stage4_1r4_targeted_closure",
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


def _task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id", "scenario"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(spec.get("category", "r4")),
    }


def _metrics_context(ctx: Stage41R4Context, *, extended: bool) -> Any:
    cfg = copy.deepcopy(ctx.r3_ctx.base34.cfg)
    if extended:
        weak = ctx.cfg["weak_slew_closure"]
        cfg["gate"]["allowed_arrival_steps"] = list(map(int, weak["allowed_arrival_steps"]))
        cfg["gate"]["hold_through_step"] = int(weak["hold_through_step"])
        cfg["gate"]["minimum_post_arrival_hold_steps"] = int(
            weak["minimum_post_arrival_hold_steps"]
        )
    return SimpleNamespace(cfg=cfg, env_cfg=ctx.r3_ctx.base34.env_cfg)


def result_row(ctx: Stage41R4Context, result: dict[str, Any], *, extended: bool) -> dict[str, Any]:
    metric_ctx = _metrics_context(ctx, extended=extended)
    metrics = s34.target_metrics(metric_ctx, _task_from_spec(result["spec"]), result, None)
    spec = result["spec"]
    estimator = result.get("adaptive_estimator_summary") or {}
    trace = result.get("control_trace") or []
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
        "controller_action_delay_steps": int(
            spec.get("controller_action_delay_steps", spec.get("action_delay_steps", 0))
        ),
        "actual_slew_scale": float(spec.get("slew_scale", 1.0)),
        "controller_slew_scale_estimate": float(
            spec.get("controller_slew_scale_estimate", 1.0)
        ),
        "adaptive_estimator_enabled": bool(
            (spec.get("adaptive_delay_slew_estimator") or {}).get("enabled", False)
        ),
        "adaptive_estimated_delay_steps": estimator.get("selected_delay_steps"),
        "adaptive_estimated_slew_scale": estimator.get("selected_slew_scale"),
        "adaptive_estimator_observations": estimator.get("observations"),
        "adaptive_estimator_transitions": estimator.get("transitions"),
        "anti_windup_enabled": bool(spec.get("anti_windup_enabled", False)),
        "anti_windup_mode": spec.get("anti_windup_mode", "off"),
        "anti_windup_saturated_steps": sum(
            bool(row.get("anti_windup_saturated", False)) for row in trace
        ),
        "extended_horizon": extended,
        **metrics,
    }


# ---------------------------------------------------------------------------
# Weak-slew 370 ms closure
# ---------------------------------------------------------------------------


def build_weak_slew_specs(ctx: Stage41R4Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["weak_slew_closure"]
    variant_id, _ = materialize_variant(
        ctx,
        slew_scale=float(cfg["actual_slew_scale"]),
        horizon_steps=int(cfg["horizon_steps"]),
    )
    specs: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for variant in cfg["controller_variants"]:
            scale = _resolve_scale(variant["controller_scale"], ctx.r3_ctx.source_scale)
            extra = {
                "horizon_steps": int(cfg["horizon_steps"]),
                "extended_horizon": True,
                "tail_hold_steps": int(cfg["tail_hold_steps"]),
                "tail_action_policy": str(cfg["tail_action_policy"]),
                "slew_scale": float(cfg["actual_slew_scale"]),
                "controller_slew_scale_estimate": float(cfg["estimated_slew_scale"]),
                "actuator_gain_by_mode": [1.0, 1.0, 1.0],
                "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
                "action_delay_steps": 0,
                "controller_action_delay_steps": 0,
                "prime_action_queue_with_nominal": True,
                "observer_enabled": bool(variant["observer_enabled"]),
                "observer_variant": str(variant["observer_variant"]),
                "anti_windup_enabled": bool(variant["anti_windup_enabled"]),
                "anti_windup_mode": str(variant["anti_windup_mode"]),
                "conditional_anti_windup_use_actual_actuator_state": False,
                "force_anti_windup_in_clean": bool(
                    variant.get("force_anti_windup_in_clean", False)
                ),
                "delay_aware_enabled": True,
                "gain_slew_scheduling_enabled": True,
                "phase_aware_reference_enabled": True,
                "controller_variant": str(variant["variant"]),
            }
            specs.append(
                _make_spec(
                    phase="weak_slew_370ms",
                    scenario=f"{target['target_id']}__{variant['variant']}",
                    category="weak_slew_370ms",
                    target=target,
                    controller_scale=scale,
                    environment_variant=variant_id,
                    extra=extra,
                )
            )
    return specs


def _select_weak_slew_controller(ctx: Stage41R4Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    cfg = ctx.cfg["weak_slew_closure"]
    candidates: list[dict[str, Any]] = []
    feedback_variants = [
        row["variant"]
        for row in cfg["controller_variants"]
        if _resolve_scale(row["controller_scale"], ctx.r3_ctx.source_scale) > 0.0
    ]
    target_ids = {str(target["target_id"]) for target in cfg["targets"]}
    for variant in feedback_variants:
        subset = [row for row in rows if row["controller_variant"] == variant]
        by_target = {str(row["target_id"]): row for row in subset}
        pass_fraction = sum(
            bool(by_target.get(target, {}).get("stage3_4_target_tracking_pass", False))
            for target in target_ids
        ) / max(len(target_ids), 1)
        margins = [
            _as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12)
            for row in subset
        ]
        velocities = [
            _as_float(row.get("stage3_4_post_arrival_velocity_rms_m_per_s"), 1e12)
            for row in subset
        ]
        candidates.append(
            {
                "controller_variant": variant,
                "pass_fraction": pass_fraction,
                "minimum_signed_margin": min(margins) if margins else -1e12,
                "mean_signed_margin": float(np.mean(margins)) if margins else -1e12,
                "mean_post_arrival_velocity_rms": float(np.mean(velocities)) if velocities else 1e12,
                "all_targets_pass": pass_fraction >= float(
                    cfg["minimum_feedback_targets_pass_fraction"]
                ),
            }
        )
    eligible = [row for row in candidates if row["all_targets_pass"]]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda row: (
            row["minimum_signed_margin"],
            row["mean_signed_margin"],
            -row["mean_post_arrival_velocity_rms"],
            row["controller_variant"],
        ),
    )


def run_weak_slew(ctx: Stage41R4Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_weak_slew_specs(ctx)
    raw_dir = ctx.paths.weak_slew / "raw"
    results = evaluate_specs(ctx, specs, output_dir=raw_dir, backend=backend, resume=resume)
    rows = [result_row(ctx, result, extended=True) for result in results]
    selected = _select_weak_slew_controller(ctx, rows)
    n_successful = sum(bool(row.get("success")) for row in rows)
    execution_complete = n_successful == len(rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "weak_slew_370ms",
        "n_rollouts": len(rows),
        "n_successful": n_successful,
        "execution_complete": execution_complete,
        "selected_controller": selected,
        "passed": bool(execution_complete and selected is not None),
    }
    write_csv(ctx.paths.weak_slew / "results.csv", rows)
    atomic_write_json(ctx.paths.weak_slew / "results.json", rows)
    atomic_write_json(ctx.paths.weak_slew / "summary.json", summary)
    _update_state(
        ctx,
        weak_slew_complete=True,
        weak_slew_summary=summary,
        selected_weak_slew_controller=(
            None if selected is None else selected["controller_variant"]
        ),
    )
    return summary


# ---------------------------------------------------------------------------
# Online delay/slew hypothesis-bank POC
# ---------------------------------------------------------------------------


def build_estimator_specs(ctx: Stage41R4Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["adaptive_estimator"]
    specs: list[dict[str, Any]] = []
    for actual_slew in cfg["actual_slew_scales"]:
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(actual_slew),
            horizon_steps=int(cfg["horizon_steps"]),
        )
        for actual_delay in cfg["actual_delay_steps"]:
            for target in cfg["targets"]:
                for variant in cfg["controller_variants"]:
                    if variant == "naive":
                        modeled_delay = 0
                        estimated_slew = 1.0
                        estimator_cfg = None
                    elif variant == "oracle":
                        modeled_delay = int(actual_delay)
                        estimated_slew = float(actual_slew)
                        estimator_cfg = None
                    elif variant == "adaptive":
                        modeled_delay = int(cfg["initial_delay_steps"])
                        estimated_slew = float(cfg["initial_slew_scale"])
                        estimator_cfg = {
                            "enabled": True,
                            "delay_candidates": list(cfg["delay_candidates"]),
                            "slew_candidates": list(cfg["slew_candidates"]),
                            "score_decay": float(cfg["score_decay"]),
                            "minimum_observations": int(cfg["minimum_observations"]),
                            "switch_hysteresis_fraction": float(
                                cfg["switch_hysteresis_fraction"]
                            ),
                            "initial_delay_steps": int(cfg["initial_delay_steps"]),
                            "initial_slew_scale": float(cfg["initial_slew_scale"]),
                        }
                    else:
                        raise ValueError(f"unsupported estimator controller variant {variant}")
                    estimator_aware_variant = variant in {"oracle", "adaptive"}
                    extra = {
                        "horizon_steps": int(cfg["horizon_steps"]),
                        "extended_horizon": False,
                        "slew_scale": float(actual_slew),
                        "controller_slew_scale_estimate": estimated_slew,
                        "actuator_gain_by_mode": [1.0, 1.0, 1.0],
                        "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
                        "action_delay_steps": int(actual_delay),
                        "controller_action_delay_steps": modeled_delay,
                        "prime_action_queue_with_nominal": True,
                        "observer_enabled": True,
                        "observer_variant": "control_aware_residual",
                        # Oracle/adaptive anti-windup may react only to the
                        # controller's current estimate.  The private plant
                        # slew value is never read by the adaptive controller.
                        "anti_windup_enabled": estimator_aware_variant,
                        "anti_windup_mode": (
                            "conditional_weak_actuator"
                            if estimator_aware_variant
                            else "off"
                        ),
                        "conditional_anti_windup_use_actual_actuator_state": False,
                        "force_anti_windup_in_clean": estimator_aware_variant,
                        "delay_aware_enabled": True,
                        "gain_slew_scheduling_enabled": True,
                        "phase_aware_reference_enabled": True,
                        "known_control_effect_from_measured_current_increment": True,
                        "controller_variant": variant,
                    }
                    if estimator_cfg is not None:
                        extra["adaptive_delay_slew_estimator"] = estimator_cfg
                    specs.append(
                        _make_spec(
                            phase="adaptive_delay_slew_estimator",
                            scenario=(
                                f"{target['target_id']}__d{actual_delay}__"
                                f"s{float(actual_slew):.1f}__{variant}"
                            ),
                            category="adaptive_delay_slew_estimator",
                            target=target,
                            controller_scale=float(ctx.r3_ctx.source_scale),
                            environment_variant=variant_id,
                            extra=extra,
                        )
                    )
    return specs


def summarize_estimator(ctx: Stage41R4Context, rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["adaptive_estimator"]
    adaptive = [row for row in rows if row["controller_variant"] == "adaptive"]
    delay_correct = sum(
        int(row.get("adaptive_estimated_delay_steps", -999))
        == int(row["actual_action_delay_steps"])
        for row in adaptive
    )
    slew_errors = [
        abs(
            _as_float(row.get("adaptive_estimated_slew_scale"), 1e9)
            - float(row["actual_slew_scale"])
        )
        for row in adaptive
    ]
    delay_fraction = delay_correct / max(len(adaptive), 1)
    max_slew_error = max(slew_errors) if slew_errors else 1e9

    key_fields = ("target_id", "actual_action_delay_steps", "actual_slew_scale")
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        grouped.setdefault(key, {})[str(row["controller_variant"])] = row
    oracle_feasible = 0
    adaptive_preserved = 0
    naive_failures = 0
    adaptive_recoveries = 0
    control_rows: list[dict[str, Any]] = []
    for key, variants in grouped.items():
        naive = variants.get("naive")
        oracle = variants.get("oracle")
        adapt = variants.get("adaptive")
        if not (naive and oracle and adapt):
            continue
        oracle_pass = _as_bool(oracle.get("stage3_4_target_tracking_pass"))
        adaptive_pass = _as_bool(adapt.get("stage3_4_target_tracking_pass"))
        naive_pass = _as_bool(naive.get("stage3_4_target_tracking_pass"))
        diagnostic_weak_deadline = bool(
            cfg.get("weak_slew_deadline_cases_are_diagnostic", True)
            and math.isclose(float(key[2]), 0.9, abs_tol=1e-12)
            and not oracle_pass
        )
        if oracle_pass:
            oracle_feasible += 1
            adaptive_preserved += int(adaptive_pass)
        if not naive_pass and oracle_pass:
            naive_failures += 1
            adaptive_recoveries += int(adaptive_pass)
        control_rows.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "naive_pass": naive_pass,
                "oracle_pass": oracle_pass,
                "adaptive_pass": adaptive_pass,
                "diagnostic_weak_slew_deadline_case": diagnostic_weak_deadline,
                "naive_margin": naive.get("stage3_4_tracking_minimum_signed_margin"),
                "oracle_margin": oracle.get("stage3_4_tracking_minimum_signed_margin"),
                "adaptive_margin": adapt.get("stage3_4_tracking_minimum_signed_margin"),
                "estimated_delay_steps": adapt.get("adaptive_estimated_delay_steps"),
                "estimated_slew_scale": adapt.get("adaptive_estimated_slew_scale"),
            }
        )
    preservation = adaptive_preserved / max(oracle_feasible, 1)
    recovery = adaptive_recoveries / max(naive_failures, 1) if naive_failures else 1.0
    adaptive_pass_fraction = preservation
    accuracy_pass = bool(
        delay_fraction >= float(cfg["minimum_delay_identification_fraction"])
        and max_slew_error <= float(cfg["maximum_slew_absolute_error"])
        and all(
            int(row.get("adaptive_estimator_observations", 0))
            >= int(cfg["minimum_estimator_observations"])
            for row in adaptive
        )
    )
    control_pass = bool(
        preservation >= float(cfg["minimum_adaptive_preservation_of_oracle_passes"])
        and adaptive_pass_fraction
        >= float(cfg["minimum_adaptive_pass_fraction_on_oracle_feasible_cases"])
        and recovery >= float(cfg["minimum_naive_failure_recovery_fraction"])
    )
    n_successful = sum(bool(row.get("success")) for row in rows)
    execution_complete = n_successful == len(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "adaptive_delay_slew_estimator",
        "n_rollouts": len(rows),
        "n_successful": n_successful,
        "execution_complete": execution_complete,
        "n_adaptive_rollouts": len(adaptive),
        "delay_identification_fraction": delay_fraction,
        "maximum_slew_absolute_error": max_slew_error,
        "oracle_feasible_cases": oracle_feasible,
        "adaptive_preserved_oracle_passes": adaptive_preserved,
        "adaptive_preservation_fraction": preservation,
        "naive_failure_cases_with_oracle_pass": naive_failures,
        "adaptive_recoveries": adaptive_recoveries,
        "naive_failure_recovery_fraction": recovery,
        "estimator_accuracy_passed": accuracy_pass,
        "adaptive_control_passed": control_pass,
        "passed": bool(execution_complete and accuracy_pass and control_pass),
        "control_case_summaries": control_rows,
    }


def run_estimator(ctx: Stage41R4Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_estimator_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.estimator / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [result_row(ctx, result, extended=False) for result in results]
    summary = summarize_estimator(ctx, rows)
    write_csv(ctx.paths.estimator / "results.csv", rows)
    atomic_write_json(ctx.paths.estimator / "results.json", rows)
    write_csv(
        ctx.paths.estimator / "control_case_summary.csv",
        summary["control_case_summaries"],
    )
    atomic_write_json(ctx.paths.estimator / "summary.json", summary)
    _update_state(ctx, estimator_complete=True, estimator_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Restart availability audit
# ---------------------------------------------------------------------------


def run_restart_audit(ctx: Stage41R4Context) -> dict[str, Any]:
    cfg = ctx.cfg["restart_audit"]
    simulation_root = Path(ctx.r3_ctx.source_env_cfg["simulation_root"]).expanduser()
    base_folder = str(ctx.r3_ctx.source_env_cfg.get("start_folder", "1100ms"))
    explicit = os.environ.get(str(cfg["environment_variable"]), "").strip()
    candidates: list[str] = []
    if explicit:
        candidates.extend(item.strip() for item in explicit.split(",") if item.strip())
    if bool(cfg.get("auto_discover", True)):
        try:
            base_ms = int(base_folder.lower().replace("ms", ""))
        except ValueError:
            base_ms = 1100
        candidates.extend(
            f"{base_ms + int(offset)}ms" for offset in cfg.get("candidate_offsets_ms", [])
        )
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
        "discovered_alternate_start_folders": discovered,
        "missing_candidate_folders": missing,
        "minimum_required_for_true_validation": minimum,
        "true_restart_validation_available": len(discovered) >= minimum,
        "true_restart_validation_performed": False,
        "required_metadata": [
            "absolute start time",
            "R/Z/Ip",
            "14 coil currents",
            "vessel/eddy-current state or generation history",
            "source trajectory/history identifier",
        ],
    }
    atomic_write_json(ctx.paths.restart / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Confirmation and verdict
# ---------------------------------------------------------------------------


def run_confirmation(ctx: Stage41R4Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    weak = state.get("weak_slew_summary") or {}
    estimator = state.get("estimator_summary") or {}
    specs: list[dict[str, Any]] = []
    selected = (weak.get("selected_controller") or {}).get("controller_variant")
    if selected:
        source_rows = read_json(ctx.paths.weak_slew / "results.json")
        chosen_rows = [row for row in source_rows if row["controller_variant"] == selected]
        for row in chosen_rows:
            source_result = read_json_gz(
                ctx.paths.weak_slew / "raw" / f"{row['experiment_id']}.json.gz"
            )
            for repeat in range(
                int(ctx.cfg["weak_slew_closure"]["confirmation_repeats_per_target"])
            ):
                spec = copy.deepcopy(source_result["spec"])
                spec["phase"] = "confirmation"
                spec["category"] = "weak_slew_confirmation"
                spec["confirmation_repeat"] = repeat
                spec["source_experiment_id"] = row["experiment_id"]
                identity = {key: value for key, value in spec.items() if key != "experiment_id"}
                spec["experiment_id"] = _scenario_digest(identity, prefix="s41r4c")
                specs.append(spec)
    # Confirm the thinnest passing adaptive case for each distinct
    # (delay, slew) pair.  This avoids spending all repeats on one easy pair.
    if bool(estimator.get("passed", False)):
        estimator_cfg = ctx.cfg["adaptive_estimator"]
        estimator_rows = read_json(ctx.paths.estimator / "results.json")
        adaptive_pass = [
            row
            for row in estimator_rows
            if row["controller_variant"] == "adaptive"
            and _as_bool(row.get("stage3_4_target_tracking_pass"))
        ]
        by_pair: dict[tuple[int, float], dict[str, Any]] = {}
        for row in adaptive_pass:
            pair = (
                int(row["actual_action_delay_steps"]),
                round(float(row["actual_slew_scale"]), 6),
            )
            previous = by_pair.get(pair)
            margin = _as_float(
                row.get("stage3_4_tracking_minimum_signed_margin"), 1e12
            )
            previous_margin = (
                1e12
                if previous is None
                else _as_float(
                    previous.get("stage3_4_tracking_minimum_signed_margin"),
                    1e12,
                )
            )
            if previous is None or margin < previous_margin:
                by_pair[pair] = row
        pair_rows = sorted(
            by_pair.values(),
            key=lambda row: (
                _as_float(
                    row.get("stage3_4_tracking_minimum_signed_margin"), 1e12
                ),
                int(row["actual_action_delay_steps"]),
                float(row["actual_slew_scale"]),
            ),
        )
        maximum_pairs = int(
            estimator_cfg.get("maximum_distinct_delay_slew_pairs_to_confirm", 9)
        )
        repeats = int(estimator_cfg.get("confirmation_repeats_per_case", 2))
        for row in pair_rows[:maximum_pairs]:
            source_result = read_json_gz(
                ctx.paths.estimator / "raw" / f"{row['experiment_id']}.json.gz"
            )
            for repeat in range(repeats):
                spec = copy.deepcopy(source_result["spec"])
                spec["phase"] = "confirmation"
                spec["category"] = "adaptive_estimator_confirmation"
                spec["confirmation_repeat"] = repeat
                spec["source_experiment_id"] = row["experiment_id"]
                spec["source_actual_delay_steps"] = int(
                    row["actual_action_delay_steps"]
                )
                spec["source_actual_slew_scale"] = float(
                    row["actual_slew_scale"]
                )
                identity = {key: value for key, value in spec.items() if key != "experiment_id"}
                spec["experiment_id"] = _scenario_digest(identity, prefix="s41r4c")
                specs.append(spec)
    if not specs:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "confirmation",
            "n_rollouts": 0,
            "passed": False,
            "reason": "no eligible source scenario",
        }
        atomic_write_json(ctx.paths.confirmation / "summary.json", summary)
        _update_state(ctx, confirmation_complete=True, confirmation_summary=summary)
        return summary
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.confirmation / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [
        result_row(ctx, result, extended=bool(result["spec"].get("extended_horizon", False)))
        for result in results
    ]
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        source_id = str(
            read_json_gz(
                ctx.paths.confirmation / "raw" / f"{row['experiment_id']}.json.gz"
            )["spec"].get("source_experiment_id", "")
        )
        groups.setdefault(source_id, []).append(row)
    group_rows: list[dict[str, Any]] = []
    estimator_tolerance = float(
        ctx.cfg["adaptive_estimator"]["maximum_slew_absolute_error"]
    )
    for source_id, group in groups.items():
        is_estimator_group = bool(
            group and group[0].get("category") == "adaptive_estimator_confirmation"
        )
        identification_passes: list[bool] = []
        if is_estimator_group:
            for row in group:
                identification_passes.append(
                    int(row.get("adaptive_estimated_delay_steps", -999))
                    == int(row.get("actual_action_delay_steps", -998))
                    and abs(
                        _as_float(row.get("adaptive_estimated_slew_scale"), 1e9)
                        - float(row.get("actual_slew_scale", -1e9))
                    )
                    <= estimator_tolerance
                )
        group_rows.append(
            {
                "source_experiment_id": source_id,
                "scenario_type": (
                    "adaptive_estimator" if is_estimator_group else "weak_slew"
                ),
                "actual_action_delay_steps": (
                    group[0].get("actual_action_delay_steps")
                    if is_estimator_group
                    else None
                ),
                "actual_slew_scale": (
                    group[0].get("actual_slew_scale")
                    if is_estimator_group
                    else None
                ),
                "repeats": len(group),
                "successful_repeats": sum(bool(row.get("success")) for row in group),
                "all_repeats_tracking_pass": bool(
                    group and all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in group)
                ),
                "all_repeats_estimator_identification_pass": (
                    bool(identification_passes and all(identification_passes))
                    if is_estimator_group
                    else None
                ),
                "worst_signed_margin": min(
                    _as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12)
                    for row in group
                ),
            }
        )
    estimator_groups = [
        row for row in group_rows if row["scenario_type"] == "adaptive_estimator"
    ]
    minimum_estimator_groups = int(
        ctx.cfg["adaptive_estimator"].get(
            "minimum_distinct_delay_slew_pairs_confirmed", 6
        )
    )
    require_identification = bool(
        ctx.cfg["adaptive_estimator"].get(
            "require_identification_in_confirmation", True
        )
    )
    tracking_pass = bool(
        group_rows and all(row["all_repeats_tracking_pass"] for row in group_rows)
    )
    estimator_coverage_pass = bool(
        len(estimator_groups) >= minimum_estimator_groups
    )
    identification_pass = bool(
        not require_identification
        or all(
            bool(row["all_repeats_estimator_identification_pass"])
            for row in estimator_groups
        )
    )
    passed = bool(tracking_pass and estimator_coverage_pass and identification_pass)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "confirmation",
        "n_rollouts": len(rows),
        "n_source_scenarios": len(group_rows),
        "n_estimator_delay_slew_pairs_confirmed": len(estimator_groups),
        "minimum_estimator_delay_slew_pairs_required": minimum_estimator_groups,
        "tracking_passed": tracking_pass,
        "estimator_coverage_passed": estimator_coverage_pass,
        "estimator_identification_passed": identification_pass,
        "scenario_summaries": group_rows,
        "passed": passed,
    }
    write_csv(ctx.paths.confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.confirmation / "results.json", rows)
    write_csv(ctx.paths.confirmation / "scenario_summary.csv", group_rows)
    atomic_write_json(ctx.paths.confirmation / "summary.json", summary)
    _update_state(ctx, confirmation_complete=True, confirmation_summary=summary)
    return summary


def analyze(ctx: Stage41R4Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    reclass = state.get("reclassification_summary") or {}
    weak = state.get("weak_slew_summary") or {}
    estimator = state.get("estimator_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    confirmation = state.get("confirmation_summary") or {}
    unresolved_before = set(reclass.get("unresolved_required_categories", []))
    source_accounting_pass = bool(
        reclass.get("gain_estimation_error_reclassified_without_new_tsc", False)
        and reclass.get("all_non_slew_required_categories_passed", False)
    )
    weak_pass = bool(weak.get("passed", False))
    estimator_pass = bool(estimator.get("passed", False))
    confirmation_pass = bool(confirmation.get("passed", False))
    targeted_closure_pass = bool(
        source_accounting_pass and weak_pass and estimator_pass and confirmation_pass
    )
    true_restart_available = bool(restart.get("true_restart_validation_available", False))
    if targeted_closure_pass and not true_restart_available:
        verdict = (
            "PASS_STAGE4_1R4_TARGETED_CLOSURE_WEAK_SLEW_AND_ONLINE_ESTIMATION_"
            "CONFIRMED_TRUE_RESTART_NOT_AVAILABLE"
        )
    elif targeted_closure_pass:
        verdict = (
            "PASS_STAGE4_1R4_TARGETED_CLOSURE_WEAK_SLEW_AND_ONLINE_ESTIMATION_"
            "CONFIRMED_TRUE_RESTART_NOT_YET_VALIDATED"
        )
    else:
        verdict = "STAGE4_1R4_TARGETED_CLOSURE_INCOMPLETE"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r3_run": str(ctx.source_stage41r3_run),
        "source_unresolved_required_categories_before_r4": sorted(unresolved_before),
        "source_gain_estimation_accounting_corrected": bool(
            reclass.get("gain_estimation_error_reclassified_without_new_tsc", False)
        ),
        "source_non_slew_required_categories_passed": bool(
            reclass.get("all_non_slew_required_categories_passed", False)
        ),
        "source_accounting_passed": source_accounting_pass,
        "weak_slew_370ms_passed": weak_pass,
        "adaptive_delay_slew_estimator_passed": estimator_pass,
        "confirmation_passed": confirmation_pass,
        "true_restart_validation_available": true_restart_available,
        "true_restart_validation_performed": False,
        "finite_test_envelope_validated": targeted_closure_pass,
        "deployment_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "online_estimator_is_finite_hypothesis_bank_poc": True,
        "warning": (
            "This targeted closure covers a finite 0/1/2-step delay and "
            "0.9/1.0/1.1 slew bank. It is not deployment qualification."
        ),
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_reclassification": reclass,
            "weak_slew": weak,
            "adaptive_estimator": estimator,
            "restart_audit": restart,
            "confirmation": confirmation,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r4_analysis_summary.json", summary)
    atomic_write_json(ctx.paths.analysis / "stage4_1r4_verdict.json", summary)
    _update_state(
        ctx,
        finished=True,
        stop_reason="pipeline_complete",
        analysis_summary=summary,
    )
    return summary


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute(
    *,
    config_path: str | Path,
    source_stage41r3_run: str | Path | None,
    run_dir: str | Path | None,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx = load_stage41r4_config(
        config_path,
        source_stage41r3_run=source_stage41r3_run,
        run_dir_override=run_dir,
    )
    initialize_run(ctx)
    command = str(command)
    if command in {"all", "reclassify"}:
        run_source_reclassification(ctx)
        if command == "reclassify":
            return read_json(ctx.paths.state)
    if command in {"all", "weak_slew"}:
        run_weak_slew(ctx, backend=backend, resume=resume)
        if command == "weak_slew":
            return read_json(ctx.paths.state)
    if command in {"all", "estimator"}:
        run_estimator(ctx, backend=backend, resume=resume)
        if command == "estimator":
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
    # Deterministic synthetic delay/slew identification check.
    scheduler = r3.PhysicalCoilScheduler(
        modes_tsc=np.eye(14, 3),
        nominal_max_delta_a=3.0,
        command_max_delta_a=3.0,
        min_current=-1e6 * np.ones(14),
        max_current=1e6 * np.ones(14),
        lower_mode=np.array([-2.6, -2.6, -0.9]),
        upper_mode=np.array([2.6, 2.6, 0.9]),
    )
    estimator = r3.DelaySlewHypothesisBank(
        scheduler=scheduler,
        delay_candidates=(0, 1, 2),
        slew_candidates=(0.9, 1.0, 1.1),
        minimum_observations=2,
        switch_hysteresis_fraction=0.0,
    )
    nominal = np.asarray(
        [[0.2 + 0.03 * k, -0.1 + 0.02 * k, 0.03 * (-1) ** k] for k in range(8)],
        dtype=float,
    )
    issued: list[np.ndarray] = []
    currents = np.zeros(14)
    actual_delay = 1
    actual_slew = 0.9
    for step in range(8):
        issued.append(nominal[step].copy())
        command = nominal[step] if step < actual_delay else issued[step - actual_delay]
        observed = scheduler.predicted_delta_a(command, currents, np.ones(3), actual_slew)
        estimator.update(
            step=step,
            observed_delta_a=observed,
            currents_before_a=currents,
            issued_commands=issued,
            nominal_commands=nominal,
        )
        currents = currents + observed
    return {
        "stage": STAGE,
        "selected_delay_steps": estimator.selected_delay_steps,
        "selected_slew_scale": estimator.selected_slew_scale,
        "passed": bool(
            estimator.selected_delay_steps == actual_delay
            and math.isclose(estimator.selected_slew_scale, actual_slew, abs_tol=1e-12)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage4.1R4 targeted weak-slew and delay/slew-estimator closure")
    parser.add_argument("--config", default="configs/stage4_1r4_targeted_closure_370ms.json")
    parser.add_argument("--source-stage4-1r3-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument(
        "--command",
        default="all",
        choices=["all", "prepare", "reclassify", "weak_slew", "estimator", "restart", "confirm", "analyze"],
    )
    parser.add_argument("--backend", default="ray", choices=["ray", "serial"])
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        payload = self_test()
        print(json.dumps(payload, indent=2, allow_nan=False))
        if not payload["passed"]:
            raise SystemExit(1)
        return
    payload = execute(
        config_path=args.config,
        source_stage41r3_run=args.source_stage4_1r3_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
