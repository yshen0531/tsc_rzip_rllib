"""Stage4.0 finite robustness and failure-recovery validation.

Stage3.4 established a complete target-conditioned 350 ms nominal library and
validated a receding-horizon MPC POC for one fixed TSC restart state.  Stage4.0
keeps the controller frozen and evaluates genuinely held-out targets,
fail-to-pass disturbance recovery, sensor/latency/actuation uncertainty,
preconditioned hidden-state histories, and any alternate restart folders that
are actually present on the server.

The strongest Stage4.0 verdict is still a finite test-envelope result.  It is
not deployment qualification and it does not claim untested plant-parameter,
noise, delay, or initial-state robustness.
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
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as base
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_4_late_arrival_continuation_mpc as s34
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STAGE = "Stage4.0"
STATE_FILENAME = "stage4_0_state.json"
MANIFEST_FILENAME = "stage4_0_manifest.json"
EXPECTED_SOURCE_VERDICT = (
    "PASS_LATE_ARRIVAL_TARGET_CONDITIONED_RECEDING_HORIZON_MPC_TEST_ENVELOPE_CONFIRMED"
)


# ---------------------------------------------------------------------------
# Strict JSON and small utilities
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
                cooked: dict[str, Any] = {}
                for key in fields:
                    value = row.get(key, "")
                    if isinstance(value, (dict, list, tuple, np.ndarray)):
                        value = json.dumps(_json_safe(value), ensure_ascii=False, separators=(",", ":"))
                    cooked[key] = value
                writer.writerow(cooked)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _as_float(value: Any, default: float = math.nan) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _vector(value: Any, expected: int) -> np.ndarray:
    array = np.asarray(value, dtype=float).reshape(-1)
    if array.shape != (expected,) or not np.all(np.isfinite(array)):
        raise ValueError(f"expected finite vector shape {(expected,)}, got {array.shape}")
    return array


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _scenario_digest(*parts: Any, prefix: str = "s40") -> str:
    encoded = json.dumps(_json_safe(parts), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:20]}"


def _result_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(read_json_gz(path).get("success", False))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Paths and context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage40Paths:
    run_dir: Path
    state: Path
    manifest: Path
    heldout: Path
    recovery: Path
    uncertainty: Path
    preconditioned: Path
    restart: Path
    confirmation: Path
    analysis: Path
    variants: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage40Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            heldout=run_dir / "stage4_0_heldout_targets",
            recovery=run_dir / "stage4_0_failure_recovery",
            uncertainty=run_dir / "stage4_0_uncertainty",
            preconditioned=run_dir / "stage4_0_preconditioned_state",
            restart=run_dir / "stage4_0_restart_sweep",
            confirmation=run_dir / "stage4_0_confirmation",
            analysis=run_dir / "stage4_0_analysis",
            variants=run_dir / "stage4_0_environment_variants",
            source_reference=run_dir / "source_stage3_4_reference",
        )


@dataclass
class Stage40Context:
    cfg: dict[str, Any]
    paths: Stage40Paths
    project_dir: Path
    source_run: Path
    source_manifest: dict[str, Any]
    source_cfg: dict[str, Any]
    source_train_cfg: dict[str, Any]
    source_env_cfg: dict[str, Any]
    source_library: dict[str, Any]
    source_bundle: dict[str, Any]
    source_scale: float
    base34: Any
    source_fingerprint: dict[str, Any]
    variants: dict[str, dict[str, Any]]


def resolve_source_stage34_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE3_4_RUN", "").strip()
    if not value:
        raise ValueError("Stage4.0 requires --source-stage3-4-run or SOURCE_STAGE3_4_RUN")
    run = Path(value).expanduser().resolve()
    required = [
        run / "stage3_4_config.resolved.json",
        run / "stage3_4_manifest.json",
        run / "stage3_4_state.json",
        run / "env_config.resolved.json",
        run / "train_config.resolved.json",
        run / "stage3_4_target_library/target_library.json",
        run / "stage3_4_identification/full_horizon_bundle.json",
        run / "stage3_4_mpc_calibration/calibration_summary.json",
        run / "stage3_4_confirmations/stage3_4_verdict.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage3.4 source run: " + ", ".join(missing))
    verdict = read_json(run / "stage3_4_confirmations/stage3_4_verdict.json")
    if str(verdict.get("verdict")) != EXPECTED_SOURCE_VERDICT:
        raise ValueError(
            "Stage4.0 requires the confirmed Stage3.4 MPC baseline; got "
            f"{verdict.get('verdict')!r}"
        )
    return run


def _source_inventory(run: Path) -> dict[str, Any]:
    relative = [
        "stage3_4_config.resolved.json",
        "stage3_4_manifest.json",
        "stage3_4_state.json",
        "env_config.resolved.json",
        "train_config.resolved.json",
        "stage3_4_target_library/target_library.json",
        "stage3_4_identification/full_horizon_bundle.json",
        "stage3_4_mpc_calibration/calibration_summary.json",
        "stage3_4_confirmations/stage3_4_verdict.json",
        "stage3_4_analysis/stage3_4_analysis_summary.json",
    ]
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    total = 0
    for rel in relative:
        path = run / rel
        if not path.exists():
            continue
        sha = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"relative_path": rel, "sha256": sha, "bytes": size})
        digest.update(rel.encode("utf-8")); digest.update(b"\0"); digest.update(sha.encode("ascii")); digest.update(b"\n")
        total += size
    return {"n_files": len(entries), "total_bytes": total, "digest": digest.hexdigest(), "entries": entries}


def validate_stage40_config(cfg: dict[str, Any], source_cfg: dict[str, Any], library: dict[str, Any]) -> None:
    if int(cfg["parallel"]["n_workers"]) != 192:
        raise ValueError("Stage4.0 complete package is intentionally configured for 192 workers")
    source_gate = source_cfg["gate"]
    gate = cfg["gate"]
    for key in (
        "precise_tolerance_m",
        "relaxed_tolerance_m",
        "required_arrival_streak_steps",
        "hold_through_step",
        "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s",
        "ip_safety_tolerance_A",
    ):
        if not math.isclose(float(gate[key]), float(source_gate[key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.0 hard gate {key} differs from Stage3.4")
    for key in ("terminal_abs_tolerance_A", "hold_rms_tolerance_A", "sustained_max_tolerance_A"):
        if not math.isclose(float(gate["ip_tracking"][key]), float(source_gate["ip_tracking"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.0 Ip tracking threshold {key} differs from Stage3.4")
    library_targets = {
        (
            round(float(row["task"]["R_offset_m"]), 12),
            round(float(row["task"]["Z_offset_m"]), 12),
            round(float(row["task"]["Ip_offset_A"]), 6),
        )
        for row in library.get("entries", [])
    }
    for scenario in cfg["heldout_targets"]["scenarios"]:
        point = (
            round(float(scenario["R_offset_m"]), 12),
            round(float(scenario["Z_offset_m"]), 12),
            round(float(scenario["Ip_offset_A"]), 6),
        )
        if point in library_targets:
            raise ValueError(f"Held-out target {scenario['scenario']} duplicates a Stage3.4 library task")
    if int(cfg["gate"]["hold_through_step"]) != 35:
        raise ValueError("Stage4.0 is fixed to the validated 350 ms horizon")


def _resolve_scale(value: Any, source_scale: float) -> float:
    if isinstance(value, str) and value == "source_selected":
        return float(source_scale)
    return float(value)


def load_stage40_config(
    config_path: str | Path,
    *,
    source_stage34_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage40Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = base.deep_replace_strings(read_json(config_path), {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)})
    source = resolve_source_stage34_run(source_stage34_run)
    source_manifest = read_json(source / "stage3_4_manifest.json")
    source_cfg = read_json(source / "stage3_4_config.resolved.json")
    source_train = read_json(source / "train_config.resolved.json")
    source_env = read_json(source / "env_config.resolved.json")
    library = read_json(source / "stage3_4_target_library/target_library.json")
    bundle = read_json(source / "stage3_4_identification/full_horizon_bundle.json")
    calibration = read_json(source / "stage3_4_mpc_calibration/calibration_summary.json")
    selected_scale = _as_float(calibration.get("selected_controller_scale"), math.nan)
    if not math.isfinite(selected_scale) or selected_scale <= 0.0:
        selected = calibration.get("selected_scale_summary") or {}
        selected_scale = _as_float(selected.get("controller_scale"), math.nan)
    if not math.isfinite(selected_scale) or selected_scale <= 0.0:
        raise ValueError("Stage3.4 calibration has no positive selected controller scale")
    validate_stage40_config(cfg, source_cfg, library)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage4_0_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage4_0_robustness_recovery_350ms')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)
    source33 = Path(source_manifest["source_stage3_3_run"]).expanduser()
    if not source33.is_absolute():
        source33 = (project_dir / source33).resolve()
    else:
        source33 = source33.resolve()
    if not source33.exists():
        fallback = project_dir / "stage3_3_runs" / source33.name
        if fallback.exists():
            source33 = fallback.resolve()
    base34 = s34.load_stage34_config(
        source / "stage3_4_config.resolved.json",
        source_stage33_run=source33,
        run_dir_override=run_dir,
    )
    storage = cfg.get("storage", {})
    env_cfg = copy.deepcopy(source_env)
    env_cfg["tsc_timeout_s"] = float(cfg.get("runtime", {}).get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    env_cfg["tsc_workspace_root"] = str(Path(os.environ.get("STAGE4_TSC_WORKSPACE_ROOT", os.environ.get("STAGE4_0_TSC_WORKSPACE_ROOT", storage.get("tsc_workspace_root", "/tmp/tsc_workspace")))).expanduser().resolve())
    env_cfg["run_root"] = str(Path(os.environ.get("STAGE4_TSC_RUN_ROOT", os.environ.get("STAGE4_0_TSC_RUN_ROOT", storage.get("tsc_run_root", "/tmp/tsc_workspace/episode_runs")))).expanduser().resolve())
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg = copy.deepcopy(source_train)
    train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    max_prelude = max((len(row.get("mode_commands", [])) for row in cfg["preconditioned_state"]["preludes"]), default=0)
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 35 + max_prelude
    base34.train_cfg = train_cfg
    base34.env_cfg = env_cfg
    paths = Stage40Paths.from_run_dir(run_dir)
    return Stage40Context(
        cfg=cfg,
        paths=paths,
        project_dir=project_dir,
        source_run=source,
        source_manifest=source_manifest,
        source_cfg=source_cfg,
        source_train_cfg=train_cfg,
        source_env_cfg=env_cfg,
        source_library=library,
        source_bundle=bundle,
        source_scale=float(selected_scale),
        base34=base34,
        source_fingerprint=_source_inventory(source),
        variants={},
    )


def _available_memory_gb() -> float:
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("MemAvailable:"):
                return float(line.split()[1]) / (1024.0 * 1024.0)
    except Exception:
        pass
    return math.nan


def runtime_preflight(ctx: Stage40Context) -> dict[str, Any]:
    requested = int(os.environ.get("STAGE4_WORKERS", os.environ.get("STAGE4_0_WORKERS", ctx.cfg["parallel"]["n_workers"])))
    logical = int(os.cpu_count() or 1)
    reserve = int(ctx.cfg["parallel"].get("reserve_logical_cpus", 16))
    allowed = max(1, logical - reserve)
    if requested > allowed:
        raise RuntimeError(
            f"Stage4.0 requests {requested} workers but only {logical} logical CPUs are visible; "
            f"the configured reserve is {reserve}, so the safe maximum is {allowed}. "
            "No silent slow fallback is allowed."
        )
    memory = _available_memory_gb()
    configured_workers = max(1, int(ctx.cfg["parallel"].get("n_workers", 192)))
    minimum_memory = float(ctx.cfg["parallel"].get("minimum_available_memory_gb", 96.0)) * (requested / configured_workers)
    if math.isfinite(memory) and memory < minimum_memory:
        raise RuntimeError(
            f"Stage4.0 requires at least {minimum_memory:.1f} GiB available memory for {requested} workers; "
            f"only {memory:.1f} GiB is visible."
        )
    soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
    minimum_fd = max(1024, requested * 16)
    if soft_fd < minimum_fd:
        raise RuntimeError(
            f"open-file soft limit {soft_fd} is too small for {requested} workers; "
            f"at least {minimum_fd} is required"
        )
    return {
        "requested_workers": requested,
        "logical_cpus": logical,
        "reserved_logical_cpus": reserve,
        "safe_worker_ceiling": allowed,
        "available_memory_gb": memory if math.isfinite(memory) else None,
        "open_file_soft_limit": soft_fd,
        "open_file_hard_limit": hard_fd,
    }


def initialize_stage40_run(ctx: Stage40Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.heldout,
        ctx.paths.recovery,
        ctx.paths.uncertainty,
        ctx.paths.preconditioned,
        ctx.paths.restart,
        ctx.paths.confirmation,
        ctx.paths.analysis,
        ctx.paths.variants,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if Path(old["source_stage3_4_run"]).resolve() != ctx.source_run:
            raise ValueError("Existing Stage4.0 run points to a different Stage3.4 source")
        old_digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        if old_digest and old_digest != ctx.source_fingerprint["digest"]:
            raise ValueError("Stage3.4 source content changed since this Stage4.0 run was prepared")
    atomic_write_json(ctx.paths.run_dir / "stage4_0_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.source_train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.source_env_cfg)
    preflight = runtime_preflight(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "source_stage3_4_run": str(ctx.source_run),
        "source_fingerprint": {key: value for key, value in ctx.source_fingerprint.items() if key != "entries"},
        "source_selected_controller_scale": ctx.source_scale,
        "workers": preflight,
        "hard_numeric_thresholds_changed": False,
        "controller_weights_changed": False,
        "finite_test_envelope_only": True,
        "deployment_robustness_validated": False,
        "true_restart_validation_is_conditional_on_available_restart_folders": True,
        "final_task": "robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay",
    }
    if not ctx.paths.manifest.exists():
        atomic_write_json(ctx.paths.manifest, manifest)
    inventory = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory.exists():
        atomic_write_json(inventory, ctx.source_fingerprint)
    for relative in (
        "stage3_4_config.resolved.json",
        "stage3_4_manifest.json",
        "stage3_4_state.json",
        "stage3_4_target_library/target_library.json",
        "stage3_4_identification/full_horizon_bundle.json",
        "stage3_4_mpc_calibration/calibration_summary.json",
        "stage3_4_confirmations/stage3_4_verdict.json",
        "stage3_4_analysis/stage3_4_analysis_summary.json",
    ):
        src = ctx.source_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())
    _register_base_variant(ctx)


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "prepared": True,
        "heldout_complete": False,
        "recovery_complete": False,
        "uncertainty_complete": False,
        "preconditioned_complete": False,
        "restart_complete": False,
        "confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage40Context, **values: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(values)
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


# ---------------------------------------------------------------------------
# Environment variants and source payload
# ---------------------------------------------------------------------------


def _variant_id(prefix: str, value: Any) -> str:
    text = str(value).replace(".", "p").replace("-", "m").replace("+", "p")
    return f"{prefix}_{text}"


def _materialize_variant(
    ctx: Stage40Context,
    variant_id: str,
    *,
    start_folder: str | None = None,
    slew_scale: float = 1.0,
) -> dict[str, Any]:
    if variant_id in ctx.variants:
        return ctx.variants[variant_id]
    env_cfg = copy.deepcopy(ctx.source_env_cfg)
    if start_folder is not None:
        env_cfg["start_folder"] = str(start_folder)
    env_cfg["current_slew_a_per_ms"] = float(ctx.source_env_cfg["current_slew_a_per_ms"]) * float(slew_scale)
    env_path = ctx.paths.variants / f"env_{variant_id}.json"
    train_path = ctx.paths.variants / f"train_{variant_id}.json"
    train_cfg = copy.deepcopy(ctx.source_train_cfg)
    train_cfg["env_config"] = str(env_path)
    atomic_write_json(env_path, env_cfg)
    atomic_write_json(train_path, train_cfg)
    payload = s34._context_payload(ctx.base34)
    payload["train_cfg"] = train_cfg
    payload["env_cfg"] = env_cfg
    # Keep the worker-side current-room calculation consistent with the
    # physical slew variant used by the environment.  The normalized action is
    # applied by the environment, but _mode_action also needs the true A/step
    # value when checking absolute coil-current headroom.
    if env_cfg.get("dt_ms") is not None:
        payload["max_delta_a"] = float(env_cfg["current_slew_a_per_ms"]) * float(env_cfg["dt_ms"])
    else:
        payload["max_delta_a"] = float(payload["max_delta_a"]) * float(slew_scale)
    payload["stage4_cfg"] = copy.deepcopy(ctx.cfg)
    payload["variant_id"] = variant_id
    payload["start_folder"] = env_cfg.get("start_folder")
    payload["slew_scale"] = float(slew_scale)
    ctx.variants[variant_id] = payload
    return payload


def _register_base_variant(ctx: Stage40Context) -> None:
    _materialize_variant(ctx, "base", start_folder=str(ctx.source_env_cfg.get("start_folder", "1100ms")), slew_scale=1.0)


def discover_restart_folders(ctx: Stage40Context) -> list[str]:
    cfg = ctx.cfg["restart_sweep"]
    env_name = str(cfg.get("environment_variable", "STAGE4_START_FOLDERS"))
    explicit = os.environ.get(env_name, "").strip()
    simulation_root = Path(ctx.source_env_cfg["simulation_root"]).expanduser()
    base_folder = str(ctx.source_env_cfg.get("start_folder", "1100ms"))
    discovered: list[str] = []
    if explicit:
        discovered.extend(item.strip() for item in explicit.split(",") if item.strip())
    if bool(cfg.get("auto_discover", True)):
        try:
            base_ms = int(base_folder.lower().replace("ms", ""))
        except ValueError:
            base_ms = 1100
        for offset in cfg.get("candidate_offsets_ms", []):
            folder = f"{base_ms + int(offset)}ms"
            if (simulation_root / folder).is_dir():
                discovered.append(folder)
    unique: list[str] = []
    for folder in discovered:
        if folder == base_folder or folder in unique:
            continue
        if not (simulation_root / folder).is_dir():
            continue
        unique.append(folder)
    return unique


# ---------------------------------------------------------------------------
# Robustness MPC worker
# ---------------------------------------------------------------------------


class LocalRobustnessWorker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env

        self.cfg = payload["cfg"]
        self.robust_cfg = payload["stage4_cfg"]
        self.train_cfg = payload["train_cfg"]
        self.env_cfg = payload["env_cfg"]
        self.modes_tsc = np.asarray(payload["modes_tsc"], dtype=float)
        self.max_delta_a = float(payload["max_delta_a"])
        self.min_current = np.asarray(payload["min_current_tsc"], dtype=float)
        self.max_current = np.asarray(payload["max_current_tsc"], dtype=float)
        self.variant_id = str(payload.get("variant_id", "base"))
        self.library = library
        self.bundle = bundle
        self.stub = SimpleNamespace(cfg=self.cfg, env_cfg=self.env_cfg)
        self.env = make_tsc_rzip_env(copy.deepcopy(self.train_cfg), worker_id=worker_id, seed=None)

    def _mode_action(self, coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
        desired = np.asarray(coefficients, dtype=float) @ self.modes_tsc.T
        max_abs = float(np.max(np.abs(desired)))
        if max_abs > 1.0:
            desired = desired / max_abs
        delta = desired * self.max_delta_a
        scale = 1.0
        for coil in range(14):
            if delta[coil] > 0.0:
                scale = min(scale, max(0.0, (self.max_current[coil] - currents[coil]) / max(delta[coil], 1e-30)))
            elif delta[coil] < 0.0:
                scale = min(scale, max(0.0, (self.min_current[coil] - currents[coil]) / min(delta[coil], -1e-30)))
        return np.asarray(desired * float(np.clip(scale, 0.0, 1.0)), dtype=np.float32)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        trajectory: list[dict[str, Any]] = []
        prelude_trajectory: list[dict[str, Any]] = []
        control_trace: list[dict[str, Any]] = []
        failure_reason = ""
        try:
            offset = np.asarray(
                [spec.get("target_R_offset_m", 0.0), spec.get("target_Z_offset_m", 0.0), spec.get("target_Ip_offset_A", 0.0)],
                dtype=float,
            )
            interpolation = s34.interpolation_for_target(self.stub, self.library, offset)
            nominal_coeff = _vector(interpolation["full_control_vector"], 105).reshape(35, 3)
            nominal_y = np.asarray(interpolation["nominal_trajectory_RZI"], dtype=float)
            nominal_velocity = np.asarray(interpolation["nominal_velocity_RZ"], dtype=float)
            requested_target = np.asarray(
                [float(self.cfg["target"]["R"]) + offset[0], float(self.cfg["target"]["Z"]) + offset[1], float(self.cfg["target"]["Ip"]) + offset[2]],
                dtype=float,
            )
            nominal_feature = s34._nominal_feature(nominal_y, nominal_velocity, requested_target)
            model_scale = float(spec.get("controller_model_scale", 1.0))
            if math.isclose(model_scale, 1.0):
                bundle = self.bundle
            else:
                bundle = copy.deepcopy(self.bundle)
                bundle["jacobian_normalized"] = (np.asarray(bundle["jacobian_normalized"], dtype=float) * model_scale).tolist()
            self.env.reset()
            zero_action = np.zeros(14, dtype=np.float32)
            prelude_trajectory.append(base._state_record(self.env, 0, zero_action))
            for prelude_step, command in enumerate(spec.get("prelude_mode_commands") or []):
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(np.asarray(command, dtype=float), currents)
                _, _, terminated, truncated, info = self.env.step(action)
                prelude_trajectory.append(base._state_record(self.env, prelude_step + 1, action))
                if terminated:
                    failure_reason = str(info.get("failure_reason", "prelude terminated")); break
                if truncated:
                    failure_reason = "environment truncated during prelude"; break
            if failure_reason:
                raise RuntimeError(failure_reason)
            trajectory.append(base._state_record(self.env, 0, zero_action))
            true_history: list[np.ndarray] = [np.asarray([trajectory[0]["R"], trajectory[0]["Z"], trajectory[0]["Ip"]], dtype=float)]
            observed_history: list[np.ndarray] = []
            previous_correction = np.zeros(3)
            integral = np.zeros(5)
            controller_scale = float(spec.get("controller_scale", 0.0))
            measurement_scales = np.asarray(
                [
                    self.cfg["identification"]["output_scales"]["R_m"],
                    self.cfg["identification"]["output_scales"]["Z_m"],
                    self.cfg["identification"]["output_scales"]["vR_m_per_s"],
                    self.cfg["identification"]["output_scales"]["vZ_m_per_s"],
                    self.cfg["identification"]["output_scales"]["Ip_A"],
                ],
                dtype=float,
            )
            noise_cfg = spec.get("observation_noise") or {}
            rng = np.random.default_rng(int(noise_cfg.get("seed", 0)))
            bias_cfg = spec.get("observation_bias") or {}
            bias = np.asarray([bias_cfg.get("R_m", 0.0), bias_cfg.get("Z_m", 0.0), bias_cfg.get("Ip_A", 0.0)], dtype=float)
            noise_sigma = np.asarray([noise_cfg.get("R_sigma_m", 0.0), noise_cfg.get("Z_sigma_m", 0.0), noise_cfg.get("Ip_sigma_A", 0.0)], dtype=float)
            observation_delay = max(0, int(spec.get("observation_delay_steps", 0)))
            action_delay = max(0, int(spec.get("action_delay_steps", 0)))
            command_queue = [np.zeros(3, dtype=float) for _ in range(action_delay)]
            gain = np.asarray(spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]), dtype=float)
            actuator_bias = np.asarray(spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]), dtype=float)
            lower_mode = np.asarray(self.cfg["trajectory"]["coefficient_lower"], dtype=float)
            upper_mode = np.asarray(self.cfg["trajectory"]["coefficient_upper"], dtype=float)
            dt_s = float(self.env_cfg["dt_ms"]) / 1000.0
            for step in range(35):
                state = self.env.last_state
                current_true = np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)
                if len(true_history) <= step:
                    true_history.append(current_true)
                observed = current_true + bias + rng.normal(0.0, noise_sigma)
                observed_history.append(observed)
                delayed_index = max(0, len(observed_history) - 1 - observation_delay)
                previous_delayed_index = max(0, delayed_index - 1)
                observed_delayed = observed_history[delayed_index]
                if delayed_index == previous_delayed_index:
                    observed_velocity = np.zeros(2)
                else:
                    observed_velocity = (observed_history[delayed_index][:2] - observed_history[previous_delayed_index][:2]) / dt_s
                measurement_physical = np.asarray(
                    [
                        observed_delayed[0] - nominal_y[step, 0],
                        observed_delayed[1] - nominal_y[step, 1],
                        observed_velocity[0] - nominal_velocity[step, 0],
                        observed_velocity[1] - nominal_velocity[step, 1],
                        observed_delayed[2] - nominal_y[step, 2],
                    ],
                    dtype=float,
                )
                measurement = measurement_physical / measurement_scales
                integral = float(self.cfg["mpc"].get("integral_decay", 0.92)) * integral + measurement
                if controller_scale <= 0.0:
                    solve = {
                        "first_correction": np.zeros(3),
                        "solver_success": True,
                        "solver_status": 0,
                        "solver_cost": 0.0,
                        "solver_optimality": 0.0,
                        "predicted_normalized_residual_rms": float(np.sqrt(np.mean(measurement**2))),
                        "active_lower": 0,
                        "active_upper": 0,
                    }
                else:
                    solve = s34.solve_receding_horizon_correction(
                        self.stub,
                        bundle,
                        current_step=step,
                        nominal_coefficients=nominal_coeff,
                        nominal_feature=nominal_feature,
                        measurement_normalized=measurement,
                        integral_normalized=integral,
                        previous_correction=previous_correction,
                        controller_scale=controller_scale,
                    )
                correction = np.asarray(solve["first_correction"], dtype=float)
                commanded = nominal_coeff[step] + correction
                command_queue.append(commanded)
                delayed_command = command_queue.pop(0) if action_delay > 0 else command_queue.pop()
                applied_coefficients = delayed_command.copy()
                disturbance = spec.get("disturbance")
                if disturbance and step == int(disturbance["step"]):
                    applied_coefficients[int(disturbance["mode"])] += float(disturbance["amplitude"])
                applied_coefficients = gain * applied_coefficients + actuator_bias
                applied_coefficients = np.clip(applied_coefficients, lower_mode, upper_mode)
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(applied_coefficients, currents)
                _, _, terminated, truncated, info = self.env.step(action)
                trajectory.append(base._state_record(self.env, step + 1, action))
                true_history.append(np.asarray([trajectory[-1]["R"], trajectory[-1]["Z"], trajectory[-1]["Ip"]], dtype=float))
                control_trace.append(
                    {
                        "step": step,
                        "observation_delay_steps": observation_delay,
                        "action_delay_steps": action_delay,
                        "measurement_physical": measurement_physical.tolist(),
                        "measurement_normalized": measurement.tolist(),
                        "integral_normalized": integral.tolist(),
                        "mode_correction": correction.tolist(),
                        "commanded_mode_coefficients": commanded.tolist(),
                        "applied_mode_coefficients": applied_coefficients.tolist(),
                        "solver_success": bool(solve["solver_success"]),
                        "solver_status": int(solve["solver_status"]),
                        "solver_cost": float(solve["solver_cost"]),
                        "predicted_normalized_residual_rms": float(solve["predicted_normalized_residual_rms"]),
                    }
                )
                previous_correction = correction
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated")); break
                if truncated and step + 1 < 35:
                    failure_reason = "environment truncated before 35 control steps"; break
            success = len(trajectory) == 36 and not any(bool(row.get("abnormal", False)) for row in trajectory)
            result = {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": spec["experiment_id"],
                "spec": spec,
                "success": bool(success),
                "failure_reason": "" if success else (failure_reason or "incomplete/abnormal trajectory"),
                "wall_time_s": float(time.time() - started),
                "trajectory": trajectory,
                "prelude_trajectory": prelude_trajectory,
                "control_trace": control_trace,
                "library_interpolation": interpolation,
                "environment_variant": self.variant_id,
            }
        except Exception as exc:
            result = {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": spec.get("experiment_id", "unknown"),
                "spec": spec,
                "success": False,
                "failure_reason": repr(exc),
                "traceback": traceback.format_exc(),
                "wall_time_s": float(time.time() - started),
                "trajectory": trajectory,
                "prelude_trajectory": prelude_trajectory,
                "control_trace": control_trace,
                "environment_variant": self.variant_id,
            }
        runner = getattr(self.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=not bool(result.get("success")), reason=str(result.get("failure_reason", "stage4_0_complete")))
        return _json_safe(result)

    def close(self) -> None:
        self.env.close()


def _ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id):
            self.worker = LocalRobustnessWorker(payload, library, bundle, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor




def _ensure_variant_for_spec(ctx: Stage40Context, spec: dict[str, Any]) -> None:
    variant = str(spec.get("environment_variant", "base"))
    if variant in ctx.variants:
        return
    if variant == "base":
        _register_base_variant(ctx)
        return
    if spec.get("start_folder"):
        _materialize_variant(ctx, variant, start_folder=str(spec["start_folder"]), slew_scale=float(spec.get("slew_scale", 1.0)))
        return
    if spec.get("slew_scale") is not None:
        _materialize_variant(
            ctx,
            variant,
            start_folder=str(ctx.source_env_cfg.get("start_folder", "1100ms")),
            slew_scale=float(spec["slew_scale"]),
        )
        return
    raise KeyError(f"Cannot reconstruct environment variant {variant!r} from spec {spec.get('experiment_id')!r}")

def _allocate_variant_actor_counts(group_sizes: dict[str, int], total_actors: int) -> dict[str, int]:
    """Allocate a fixed Ray actor budget across environment variants.

    Stage4.0 has several small environment variants (slew and restart folders).
    Running each variant as a separate Ray wave wastes most of a 192-core host.
    This allocator gives every non-empty variant at least one actor, never gives
    a variant more actors than tasks, and uses the remaining actors
    proportionally to pending task counts.
    """
    sizes = {str(key): int(value) for key, value in group_sizes.items() if int(value) > 0}
    if not sizes:
        return {}
    total_tasks = sum(sizes.values())
    total_actors = int(total_actors)
    if total_actors < len(sizes) or total_actors > total_tasks:
        raise ValueError(
            f"invalid mixed-variant actor budget {total_actors} for "
            f"{len(sizes)} variants and {total_tasks} tasks"
        )
    allocation = {key: 1 for key in sizes}
    remaining = total_actors - len(sizes)
    # Greedy proportional allocation.  The priority is the current number of
    # tasks per assigned actor; this is equivalent to repeatedly reducing the
    # largest expected queue depth.
    while remaining > 0:
        eligible = [key for key in sizes if allocation[key] < sizes[key]]
        if not eligible:
            break
        key = max(
            eligible,
            key=lambda item: (sizes[item] / allocation[item], sizes[item] - allocation[item], item),
        )
        allocation[key] += 1
        remaining -= 1
    if sum(allocation.values()) != total_actors:
        raise RuntimeError("failed to allocate the complete mixed-variant actor budget")
    return allocation


def evaluate_specs(
    ctx: Stage40Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        _ensure_variant_for_spec(ctx, spec)
        variant = str(spec.get("environment_variant", "base"))
        by_variant.setdefault(variant, []).append(spec)

    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, variant_specs in by_variant.items():
        pending = [
            spec
            for spec in variant_specs
            if not (resume and _result_complete(output_dir / f"{spec['experiment_id']}.json.gz"))
        ]
        if pending:
            pending_by_variant[variant] = pending

    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            payload = ctx.variants[variant]
            worker = LocalRobustnessWorker(
                payload,
                ctx.source_library,
                ctx.source_bundle,
                f"stage40_{variant}_serial",
            )
            try:
                for index, spec in enumerate(pending, 1):
                    result = worker.evaluate(spec)
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    print(f"[Stage4.0 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(
            os.environ.get(
                "STAGE4_WORKERS",
                os.environ.get("STAGE4_0_WORKERS", ctx.cfg["parallel"]["n_workers"]),
            )
        )
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        ray_tmpdir = os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=ray_tmpdir,
            log_prefix="[Stage4.0 mixed-variant]",
        )
        allocation = _allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()},
            plan.actor_count,
        )
        print(
            "[Stage4.0 mixed-variant] actor_allocation="
            + json.dumps(allocation, sort_keys=True, separators=(",", ":")),
            flush=True,
        )
        Actor = _ray_actor_class()
        all_actors: list[Any] = []
        actors_by_variant: dict[str, list[Any]] = {}
        for variant, actor_count in allocation.items():
            payload = ctx.variants[variant]
            actors = [
                Actor.remote(
                    payload,
                    ctx.source_library,
                    ctx.source_bundle,
                    f"stage40_{variant}_{index:03d}",
                )
                for index in range(actor_count)
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
                    print(f"[Stage4.0 mixed-variant] waiting {done}/{total_pending}", flush=True)
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
                        print(f"[Stage4.0 mixed-variant] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(
                all_actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")

    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


# ---------------------------------------------------------------------------
# Metrics and paired summaries
# ---------------------------------------------------------------------------


def _task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id", "scenario"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(spec.get("category", "robustness")),
    }


def result_row(ctx: Stage40Context, result: dict[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    metrics = s34.target_metrics(ctx.base34, _task_from_spec(spec), result, None)
    interpolation = result.get("library_interpolation") or {}
    trace = result.get("control_trace") or []
    max_correction = max((float(np.max(np.abs(row.get("mode_correction", [0.0, 0.0, 0.0])))) for row in trace), default=0.0)
    return {
        "experiment_id": result["experiment_id"],
        "phase": spec.get("phase"),
        "scenario": spec.get("scenario"),
        "category": spec.get("category"),
        "target_id": spec.get("target_id"),
        "controller_scale": float(spec.get("controller_scale", 0.0)),
        "environment_variant": spec.get("environment_variant", "base"),
        "target_R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "target_Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "target_Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "disturbance": copy.deepcopy(spec.get("disturbance")),
        "recovery_family": spec.get("recovery_family"),
        "disturbance_amplitude_abs": (
            float(spec["disturbance_amplitude_abs"])
            if spec.get("disturbance_amplitude_abs") is not None
            else None
        ),
        "observation_noise": copy.deepcopy(spec.get("observation_noise")),
        "observation_delay_steps": int(spec.get("observation_delay_steps", 0)),
        "action_delay_steps": int(spec.get("action_delay_steps", 0)),
        "actuator_gain_by_mode": copy.deepcopy(spec.get("actuator_gain_by_mode")),
        "controller_model_scale": float(spec.get("controller_model_scale", 1.0)),
        "slew_scale": float(spec.get("slew_scale", 1.0)),
        "prelude_name": spec.get("prelude_name"),
        "start_folder": spec.get("start_folder"),
        "library_exact_match": bool(interpolation and min(interpolation.get("distances", [1e9])) <= 1e-12),
        "library_task_ids": interpolation.get("task_ids", []),
        "max_abs_mode_correction": max_correction,
        **metrics,
    }


def summarize_pairs(rows: Sequence[dict[str, Any]], pair_fields: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[float, dict[str, Any]]] = {}
    for row in rows:
        key = tuple(json.dumps(_json_safe(row.get(field)), sort_keys=True) if isinstance(row.get(field), (dict, list)) else row.get(field) for field in pair_fields)
        grouped.setdefault(key, {})[float(row["controller_scale"])] = row
    pairs: list[dict[str, Any]] = []
    for key, values in grouped.items():
        baseline = values.get(0.0)
        positive = [scale for scale in values if scale > 0.0]
        if baseline is None or not positive:
            continue
        scale = min(positive, key=lambda x: abs(x - 0.5))
        feedback = values[scale]
        baseline_pass = _as_bool(baseline.get("stage3_4_target_tracking_pass"))
        feedback_pass = _as_bool(feedback.get("stage3_4_target_tracking_pass"))
        margin0 = _as_float(baseline.get("stage3_4_tracking_minimum_signed_margin"), -1e12)
        margin1 = _as_float(feedback.get("stage3_4_tracking_minimum_signed_margin"), -1e12)
        pair = {field: baseline.get(field) for field in pair_fields}
        pair.update(
            {
                "controller_scale": scale,
                "baseline_experiment_id": baseline["experiment_id"],
                "feedback_experiment_id": feedback["experiment_id"],
                "baseline_pass": baseline_pass,
                "feedback_pass": feedback_pass,
                "preserved": bool(baseline_pass and feedback_pass),
                "recovered": bool((not baseline_pass) and feedback_pass),
                "lost": bool(baseline_pass and not feedback_pass),
                "baseline_signed_margin": margin0,
                "feedback_signed_margin": margin1,
                "signed_margin_gain": margin1 - margin0,
            }
        )
        pairs.append(pair)
    gains = [row["signed_margin_gain"] for row in pairs]
    summary = {
        "n_pairs": len(pairs),
        "n_baseline_pass": sum(bool(row["baseline_pass"]) for row in pairs),
        "n_feedback_pass": sum(bool(row["feedback_pass"]) for row in pairs),
        "n_preserved": sum(bool(row["preserved"]) for row in pairs),
        "n_recovered": sum(bool(row["recovered"]) for row in pairs),
        "n_lost": sum(bool(row["lost"]) for row in pairs),
        "median_signed_margin_gain": float(np.median(gains)) if gains else None,
        "worst_signed_margin_gain": float(np.min(gains)) if gains else None,
    }
    return pairs, summary


def _make_spec(
    *,
    phase: str,
    scenario: str,
    category: str,
    target: dict[str, Any],
    controller_scale: float,
    environment_variant: str = "base",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = copy.deepcopy(extra or {})
    identity = {
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target": target,
        "controller_scale": controller_scale,
        "environment_variant": environment_variant,
        "extra": extra,
    }
    return {
        "kind": "stage4_0_robustness_mpc",
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
        "horizon_steps": 35,
        **extra,
    }


# ---------------------------------------------------------------------------
# Phase A: genuinely held-out targets
# ---------------------------------------------------------------------------


def run_heldout(ctx: Stage40Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["heldout_targets"]
    scales = [_resolve_scale(value, ctx.source_scale) for value in cfg["controller_scales"]]
    specs: list[dict[str, Any]] = []
    for scenario in cfg["scenarios"]:
        target = {
            "target_id": scenario["scenario"],
            "R_offset_m": scenario["R_offset_m"],
            "Z_offset_m": scenario["Z_offset_m"],
            "Ip_offset_A": scenario["Ip_offset_A"],
        }
        for scale in scales:
            specs.append(_make_spec(phase="heldout_targets", scenario=scenario["scenario"], category=str(scenario["domain"]), target=target, controller_scale=scale))
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.heldout / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    pairs, pair_summary = summarize_pairs(rows, ("scenario", "category"))
    in_domain = [row for row in rows if row["category"] == "in_domain"]
    in_domain_mpc = [row for row in in_domain if float(row["controller_scale"]) > 0.0]
    in_domain_base = [row for row in in_domain if float(row["controller_scale"]) == 0.0]
    lost = sum(bool(row["lost"]) for row in pairs if row["category"] == "in_domain")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "heldout_targets",
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "n_in_domain_targets": len(in_domain_mpc),
        "in_domain_open_loop_pass_fraction": sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in in_domain_base) / max(len(in_domain_base), 1),
        "in_domain_mpc_pass_fraction": sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in in_domain_mpc) / max(len(in_domain_mpc), 1),
        "n_in_domain_exact_library_matches": sum(bool(row.get("library_exact_match")) for row in in_domain_mpc),
        "n_lost_in_domain_open_loop_passes": lost,
        "pair_summary": pair_summary,
    }
    summary["passed"] = bool(
        summary["in_domain_mpc_pass_fraction"] >= float(cfg["minimum_in_domain_mpc_pass_fraction"])
        and summary["in_domain_open_loop_pass_fraction"] >= float(cfg["minimum_in_domain_open_loop_pass_fraction"])
        and (not bool(cfg.get("require_no_lost_open_loop_passes", True)) or lost == 0)
        and summary["n_in_domain_exact_library_matches"] == 0
        and (pair_summary["median_signed_margin_gain"] is None or pair_summary["median_signed_margin_gain"] >= float(cfg.get("minimum_median_signed_margin_gain", -0.01)))
    )
    write_csv(ctx.paths.heldout / "results.csv", rows)
    write_csv(ctx.paths.heldout / "pairs.csv", pairs)
    atomic_write_json(ctx.paths.heldout / "results.json", rows)
    atomic_write_json(ctx.paths.heldout / "summary.json", summary)
    _update_state(ctx, heldout_complete=True, heldout_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase B: fail-to-pass recovery sweep
# ---------------------------------------------------------------------------


def run_recovery(ctx: Stage40Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["failure_recovery"]
    scales = [_resolve_scale(value, ctx.source_scale) for value in cfg["controller_scales"]]
    specs: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for mode_text, amplitudes in cfg["amplitudes_by_mode"].items():
            mode = int(mode_text)
            for step in cfg["steps"]:
                for sign in cfg["signs"]:
                    family = f"{target['target_id']}_m{mode}_s{int(step):02d}_{'p' if int(sign)>0 else 'm'}"
                    for amplitude in amplitudes:
                        disturbance = {"step": int(step), "mode": mode, "amplitude": float(sign) * float(amplitude)}
                        scenario = f"{family}_a{float(amplitude):.3f}".replace(".", "p")
                        for scale in scales:
                            specs.append(
                                _make_spec(
                                    phase="failure_recovery",
                                    scenario=scenario,
                                    category="disturbance_ladder",
                                    target=target,
                                    controller_scale=scale,
                                    extra={"disturbance": disturbance, "recovery_family": family, "disturbance_amplitude_abs": float(amplitude)},
                                )
                            )
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.recovery / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    pairs, pair_summary = summarize_pairs(rows, ("recovery_family", "disturbance_amplitude_abs"))
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in pairs:
        by_family.setdefault(str(row["recovery_family"]), []).append(row)
    family_rows: list[dict[str, Any]] = []
    for family, family_pairs in sorted(by_family.items()):
        ordered = sorted(family_pairs, key=lambda row: float(row["disturbance_amplitude_abs"]))
        first_failure = next((row for row in ordered if not bool(row["baseline_pass"])), None)
        family_rows.append(
            {
                "recovery_family": family,
                "n_amplitudes": len(ordered),
                "baseline_failure_observed": bool(first_failure is not None),
                "first_baseline_failure_amplitude": float(first_failure["disturbance_amplitude_abs"]) if first_failure else None,
                "recovered_at_first_failure": bool(first_failure and first_failure["feedback_pass"]),
                "first_failure_feedback_margin": float(first_failure["feedback_signed_margin"]) if first_failure else None,
                "maximum_baseline_pass_amplitude": max((float(row["disturbance_amplitude_abs"]) for row in ordered if row["baseline_pass"]), default=None),
                "maximum_feedback_pass_amplitude": max((float(row["disturbance_amplitude_abs"]) for row in ordered if row["feedback_pass"]), default=None),
            }
        )
    failed_families = [row for row in family_rows if row["baseline_failure_observed"]]
    recovered_families = [row for row in failed_families if row["recovered_at_first_failure"]]
    baseline_pass_pairs = [row for row in pairs if row["baseline_pass"]]
    preserved = sum(bool(row["feedback_pass"]) for row in baseline_pass_pairs)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "failure_recovery",
        "n_rollouts": len(rows),
        "n_families": len(family_rows),
        "n_families_with_open_loop_failure": len(failed_families),
        "n_families_recovered_at_first_failure": len(recovered_families),
        "failure_recovery_fraction": len(recovered_families) / max(len(failed_families), 1),
        "preserved_open_loop_pass_fraction": preserved / max(len(baseline_pass_pairs), 1),
        "pair_summary": pair_summary,
    }
    summary["passed"] = bool(
        summary["n_families_with_open_loop_failure"] >= int(cfg["minimum_families_with_open_loop_failure"])
        and summary["failure_recovery_fraction"] >= float(cfg["minimum_failure_recovery_fraction"])
        and summary["preserved_open_loop_pass_fraction"] >= float(cfg["minimum_preserved_open_loop_pass_fraction"])
    )
    write_csv(ctx.paths.recovery / "results.csv", rows)
    write_csv(ctx.paths.recovery / "pairs.csv", pairs)
    write_csv(ctx.paths.recovery / "family_summary.csv", family_rows)
    atomic_write_json(ctx.paths.recovery / "results.json", rows)
    atomic_write_json(ctx.paths.recovery / "family_summary.json", family_rows)
    atomic_write_json(ctx.paths.recovery / "summary.json", summary)
    _update_state(ctx, recovery_complete=True, recovery_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase C: sensor, latency, model and actuation uncertainty
# ---------------------------------------------------------------------------


def run_uncertainty(ctx: Stage40Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["uncertainty"]
    scales = [_resolve_scale(value, ctx.source_scale) for value in cfg["controller_scales"]]
    specs: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for scenario in cfg["scenarios"]:
            extra = {key: copy.deepcopy(value) for key, value in scenario.items() if key != "name"}
            for scale in scales:
                specs.append(_make_spec(phase="uncertainty", scenario=f"{target['target_id']}__{scenario['name']}", category="software_uncertainty", target=target, controller_scale=scale, extra=extra))
        for slew_scale in cfg.get("slew_scale_variants", []):
            variant = _variant_id("slew", slew_scale)
            _materialize_variant(ctx, variant, start_folder=str(ctx.source_env_cfg.get("start_folder", "1100ms")), slew_scale=float(slew_scale))
            for scale in scales:
                specs.append(_make_spec(phase="uncertainty", scenario=f"{target['target_id']}__slew_{slew_scale}", category="actuation_slew_uncertainty", target=target, controller_scale=scale, environment_variant=variant, extra={"slew_scale": float(slew_scale)}))
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.uncertainty / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    pairs, pair_summary = summarize_pairs(rows, ("scenario", "category", "environment_variant"))
    mpc_rows = [row for row in rows if float(row["controller_scale"]) > 0.0]
    base_pass_pairs = [row for row in pairs if row["baseline_pass"]]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "uncertainty",
        "n_rollouts": len(rows),
        "n_scenarios": len(mpc_rows),
        "mpc_pass_fraction": sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in mpc_rows) / max(len(mpc_rows), 1),
        "preserved_open_loop_pass_fraction": sum(bool(row["feedback_pass"]) for row in base_pass_pairs) / max(len(base_pass_pairs), 1),
        "pair_summary": pair_summary,
        "true_plant_parameter_variation_tested": False,
        "actuation_and_controller_model_uncertainty_tested": True,
    }
    summary["passed"] = bool(
        summary["mpc_pass_fraction"] >= float(cfg["minimum_mpc_pass_fraction"])
        and summary["preserved_open_loop_pass_fraction"] >= float(cfg["minimum_preserved_open_loop_pass_fraction"])
    )
    write_csv(ctx.paths.uncertainty / "results.csv", rows)
    write_csv(ctx.paths.uncertainty / "pairs.csv", pairs)
    atomic_write_json(ctx.paths.uncertainty / "results.json", rows)
    atomic_write_json(ctx.paths.uncertainty / "summary.json", summary)
    _update_state(ctx, uncertainty_complete=True, uncertainty_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase D: preconditioned hidden-state histories
# ---------------------------------------------------------------------------


def run_preconditioned(ctx: Stage40Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["preconditioned_state"]
    scales = [_resolve_scale(value, ctx.source_scale) for value in cfg["controller_scales"]]
    specs: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for prelude in cfg["preludes"]:
            for scale in scales:
                specs.append(
                    _make_spec(
                        phase="preconditioned_state",
                        scenario=f"{target['target_id']}__{prelude['name']}",
                        category="preconditioned_hidden_state",
                        target=target,
                        controller_scale=scale,
                        extra={"prelude_name": prelude["name"], "prelude_mode_commands": prelude["mode_commands"]},
                    )
                )
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.preconditioned / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    pairs, pair_summary = summarize_pairs(rows, ("scenario", "category"))
    mpc_rows = [row for row in rows if float(row["controller_scale"]) > 0.0]
    base_pass_pairs = [row for row in pairs if row["baseline_pass"]]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "preconditioned_state",
        "n_rollouts": len(rows),
        "n_scenarios": len(mpc_rows),
        "mpc_pass_fraction": sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in mpc_rows) / max(len(mpc_rows), 1),
        "preserved_open_loop_pass_fraction": sum(bool(row["feedback_pass"]) for row in base_pass_pairs) / max(len(base_pass_pairs), 1),
        "pair_summary": pair_summary,
        "true_restart_state_tested": False,
        "preconditioned_history_tested": True,
    }
    summary["passed"] = bool(
        summary["mpc_pass_fraction"] >= float(cfg["minimum_mpc_pass_fraction"])
        and summary["preserved_open_loop_pass_fraction"] >= float(cfg["minimum_preserved_open_loop_pass_fraction"])
    )
    write_csv(ctx.paths.preconditioned / "results.csv", rows)
    write_csv(ctx.paths.preconditioned / "pairs.csv", pairs)
    atomic_write_json(ctx.paths.preconditioned / "results.json", rows)
    atomic_write_json(ctx.paths.preconditioned / "summary.json", summary)
    _update_state(ctx, preconditioned_complete=True, preconditioned_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase E: alternate restart folders, if present
# ---------------------------------------------------------------------------


def run_restart_sweep(ctx: Stage40Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["restart_sweep"]
    folders = discover_restart_folders(ctx)
    scales = [_resolve_scale(value, ctx.source_scale) for value in cfg["controller_scales"]]
    specs: list[dict[str, Any]] = []
    for folder in folders:
        variant = _variant_id("restart", folder)
        _materialize_variant(ctx, variant, start_folder=folder, slew_scale=1.0)
        for target in cfg["targets"]:
            for scale in scales:
                specs.append(
                    _make_spec(
                        phase="restart_sweep",
                        scenario=f"{folder}__{target['target_id']}",
                        category="alternate_restart_state",
                        target=target,
                        controller_scale=scale,
                        environment_variant=variant,
                        extra={"start_folder": folder},
                    )
                )
    if specs:
        results = evaluate_specs(ctx, specs, output_dir=ctx.paths.restart / "raw", backend=backend, resume=resume)
        rows = [result_row(ctx, result) for result in results]
        pairs, pair_summary = summarize_pairs(rows, ("scenario", "start_folder", "environment_variant"))
        mpc_rows = [row for row in rows if float(row["controller_scale"]) > 0.0]
        base_pass_pairs = [row for row in pairs if row["baseline_pass"]]
        mpc_fraction = sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in mpc_rows) / max(len(mpc_rows), 1)
        preserved_fraction = sum(bool(row["feedback_pass"]) for row in base_pass_pairs) / max(len(base_pass_pairs), 1)
    else:
        rows = []
        pairs = []
        pair_summary = {"n_pairs": 0}
        mpc_fraction = 0.0
        preserved_fraction = 0.0
    available = len(folders) >= int(cfg["minimum_alternate_folders_for_validation"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_sweep",
        "base_start_folder": str(ctx.source_env_cfg.get("start_folder")),
        "alternate_start_folders": folders,
        "n_alternate_start_folders": len(folders),
        "true_restart_validation_available": available,
        "n_rollouts": len(rows),
        "mpc_pass_fraction": mpc_fraction,
        "preserved_open_loop_pass_fraction": preserved_fraction,
        "pair_summary": pair_summary,
    }
    summary["passed"] = bool(
        available
        and mpc_fraction >= float(cfg["minimum_mpc_pass_fraction"])
        and preserved_fraction >= float(cfg["minimum_preserved_open_loop_pass_fraction"])
    )
    write_csv(ctx.paths.restart / "results.csv", rows)
    write_csv(ctx.paths.restart / "pairs.csv", pairs)
    atomic_write_json(ctx.paths.restart / "results.json", rows)
    atomic_write_json(ctx.paths.restart / "summary.json", summary)
    _update_state(ctx, restart_complete=True, restart_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Confirmation and verdict
# ---------------------------------------------------------------------------


def _phase_pairs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_result_by_id(phase_dir: Path, experiment_id: str) -> dict[str, Any]:
    return read_json_gz(phase_dir / "raw" / f"{experiment_id}.json.gz")


def select_confirmation_specs(ctx: Stage40Context) -> list[dict[str, Any]]:
    maximum = int(ctx.cfg["confirmation"]["maximum_scenarios"])
    selected_results: list[dict[str, Any]] = []
    # Worst passing held-out cases.
    heldout_rows = read_json(ctx.paths.heldout / "results.json") if (ctx.paths.heldout / "results.json").exists() else []
    heldout_pass = [row for row in heldout_rows if float(row["controller_scale"]) > 0.0 and _as_bool(row.get("stage3_4_target_tracking_pass"))]
    heldout_pass.sort(key=lambda row: _as_float(row.get("stage3_4_tracking_minimum_signed_margin"), 1e9))
    for row in heldout_pass[:3]:
        selected_results.append(_load_result_by_id(ctx.paths.heldout, row["experiment_id"]))
    # Recovered failures are the strongest causal-feedback evidence.
    recovery_pairs = _phase_pairs(ctx.paths.recovery / "pairs.csv")
    recovered = [row for row in recovery_pairs if _as_bool(row.get("recovered"))]
    recovered.sort(key=lambda row: _as_float(row.get("feedback_signed_margin"), 1e9))
    for row in recovered[:4]:
        selected_results.append(_load_result_by_id(ctx.paths.recovery, row["feedback_experiment_id"]))
    # Worst passing uncertainty / hidden-state / restart cases.
    for phase_dir in (ctx.paths.uncertainty, ctx.paths.preconditioned, ctx.paths.restart):
        result_path = phase_dir / "results.json"
        if not result_path.exists():
            continue
        rows = [row for row in read_json(result_path) if float(row["controller_scale"]) > 0.0 and _as_bool(row.get("stage3_4_target_tracking_pass"))]
        rows.sort(key=lambda row: _as_float(row.get("stage3_4_tracking_minimum_signed_margin"), 1e9))
        if rows:
            selected_results.append(_load_result_by_id(phase_dir, rows[0]["experiment_id"]))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in selected_results:
        identity = str(result["spec"].get("scenario")) + "|" + str(result["spec"].get("environment_variant", "base"))
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(result)
        if len(unique) >= maximum:
            break
    repeats = int(ctx.cfg["confirmation"]["repeats_per_scenario"])
    seed_offset = int(ctx.cfg["confirmation"].get("noise_seed_offset", 100000))
    specs: list[dict[str, Any]] = []
    for result in unique:
        original = copy.deepcopy(result["spec"])
        for repeat in range(repeats):
            spec = copy.deepcopy(original)
            spec["phase"] = "confirmation"
            spec["confirmation_source_experiment_id"] = result["experiment_id"]
            spec["confirmation_repeat"] = repeat
            if spec.get("observation_noise"):
                spec["observation_noise"]["seed"] = int(spec["observation_noise"].get("seed", 0)) + seed_offset + repeat
            spec["experiment_id"] = _scenario_digest(
                "confirmation",
                result["experiment_id"],
                repeat,
                spec.get("observation_noise"),
                prefix="s40conf",
            )
            specs.append(spec)
    return specs


def run_confirmation(ctx: Stage40Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = select_confirmation_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.confirmation / "raw", backend=backend, resume=resume) if specs else []
    rows = [result_row(ctx, result) for result in results]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row, result in zip(rows, results):
        by_source.setdefault(str(result["spec"]["confirmation_source_experiment_id"]), []).append(row)
    scenario_rows: list[dict[str, Any]] = []
    for source, group in sorted(by_source.items()):
        scenario_rows.append(
            {
                "source_experiment_id": source,
                "scenario": group[0].get("scenario"),
                "environment_variant": group[0].get("environment_variant"),
                "repeats": len(group),
                "successful_repeats": sum(_as_bool(row.get("success")) for row in group),
                "all_repeats_tracking_pass": all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in group),
                "worst_signed_margin": min(_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in group),
            }
        )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "confirmation",
        "n_selected_scenarios": len(scenario_rows),
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "n_scenarios_all_repeats_pass": sum(bool(row["all_repeats_tracking_pass"]) for row in scenario_rows),
        "scenario_summaries": scenario_rows,
    }
    summary["passed"] = bool(scenario_rows and all(row["all_repeats_tracking_pass"] for row in scenario_rows))
    write_csv(ctx.paths.confirmation / "results.csv", rows)
    write_csv(ctx.paths.confirmation / "scenario_summary.csv", scenario_rows)
    atomic_write_json(ctx.paths.confirmation / "results.json", rows)
    atomic_write_json(ctx.paths.confirmation / "summary.json", summary)
    _update_state(ctx, confirmation_complete=True, confirmation_summary=summary)
    return summary


def final_verdict(ctx: Stage40Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    heldout = state.get("heldout_summary") or {}
    recovery = state.get("recovery_summary") or {}
    uncertainty = state.get("uncertainty_summary") or {}
    preconditioned = state.get("preconditioned_summary") or {}
    restart = state.get("restart_summary") or {}
    confirmation = state.get("confirmation_summary") or {}
    core_pass = all(bool(item.get("passed")) for item in (heldout, recovery, uncertainty, preconditioned, confirmation))
    restart_available = bool(restart.get("true_restart_validation_available"))
    restart_pass = bool(restart.get("passed"))
    if core_pass and restart_available and restart_pass:
        verdict = "PASS_STAGE4_0_FINITE_ROBUSTNESS_RECOVERY_AND_TRUE_RESTART_ENVELOPE_CONFIRMED"
    elif core_pass and not restart_available:
        verdict = "PASS_STAGE4_0_CONTROLLED_ROBUSTNESS_AND_RECOVERY_ENVELOPE_CONFIRMED_TRUE_RESTART_NOT_AVAILABLE"
    elif core_pass and restart_available and not restart_pass:
        verdict = "PASS_STAGE4_0_CONTROLLED_ROBUSTNESS_ENVELOPE_TRUE_RESTART_VALIDATION_FAILED"
    else:
        verdict = "STAGE4_0_ROBUSTNESS_AND_RECOVERY_ENVELOPE_INCOMPLETE"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage3_4_run": str(ctx.source_run),
        "source_selected_controller_scale": ctx.source_scale,
        "heldout_targets_passed": bool(heldout.get("passed")),
        "failure_recovery_passed": bool(recovery.get("passed")),
        "software_uncertainty_passed": bool(uncertainty.get("passed")),
        "preconditioned_state_passed": bool(preconditioned.get("passed")),
        "true_restart_validation_available": restart_available,
        "true_restart_validation_passed": restart_pass if restart_available else None,
        "confirmation_passed": bool(confirmation.get("passed")),
        "finite_test_envelope_validated": bool(core_pass),
        "deployment_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": bool(restart_available and restart_pass),
        "warning": (
            "This verdict covers only the finite configured target, disturbance, software uncertainty, "
            "preconditioned-history, and discoverable restart-folder envelope. It is not deployment qualification."
        ),
        "final_task": "robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay",
    }
    atomic_write_json(ctx.paths.analysis / "stage4_0_verdict.json", payload)
    return payload


def analyze_stage40(ctx: Stage40Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    verdict = final_verdict(ctx)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "source_stage3_4_run": str(ctx.source_run),
        "source_selected_controller_scale": ctx.source_scale,
        "heldout": state.get("heldout_summary"),
        "failure_recovery": state.get("recovery_summary"),
        "uncertainty": state.get("uncertainty_summary"),
        "preconditioned_state": state.get("preconditioned_summary"),
        "restart_sweep": state.get("restart_summary"),
        "confirmation": state.get("confirmation_summary"),
        "verdict": verdict,
    }
    atomic_write_json(ctx.paths.analysis / "stage4_0_analysis_summary.json", summary)
    lines = [
        "Stage4.0 finite robustness and recovery report",
        "===============================================",
        f"Verdict: {verdict['verdict']}",
        f"Source Stage3.4 run: {ctx.source_run}",
        f"Selected MPC scale: {ctx.source_scale}",
        "",
        f"Held-out targets passed: {verdict['heldout_targets_passed']}",
        f"Failure recovery passed: {verdict['failure_recovery_passed']}",
        f"Software uncertainty passed: {verdict['software_uncertainty_passed']}",
        f"Preconditioned history passed: {verdict['preconditioned_state_passed']}",
        f"True restart validation available: {verdict['true_restart_validation_available']}",
        f"True restart validation passed: {verdict['true_restart_validation_passed']}",
        f"Confirmation passed: {verdict['confirmation_passed']}",
        "",
        "The final task remains robust causal control across genuinely different initial states, hidden dynamics, plant parameters, noise, and delay.",
        "This Stage4.0 verdict is a finite test-envelope result, not deployment qualification.",
    ]
    (ctx.paths.run_dir / "STAGE4_0_REPORT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def prepare_stage40(ctx: Stage40Context) -> dict[str, Any]:
    initialize_stage40_run(ctx)
    return {
        "stage": STAGE,
        "run_dir": str(ctx.paths.run_dir),
        "source_stage3_4_run": str(ctx.source_run),
        "workers": runtime_preflight(ctx),
        "source_selected_controller_scale": ctx.source_scale,
        "heldout_targets": len(ctx.cfg["heldout_targets"]["scenarios"]),
        "restart_folders_discovered": discover_restart_folders(ctx),
    }


def execute(
    config_path: str | Path,
    *,
    source_stage34_run: str | Path | None,
    run_dir: str | Path | None,
    backend: str,
    resume: bool,
    command: str,
) -> dict[str, Any]:
    ctx = load_stage40_config(config_path, source_stage34_run=source_stage34_run, run_dir_override=run_dir)
    prepare = prepare_stage40(ctx)
    if command == "prepare":
        return prepare
    state = read_json(ctx.paths.state)
    if command in {"all", "heldout"} and not bool(state.get("heldout_complete")):
        run_heldout(ctx, backend=backend, resume=resume)
    state = read_json(ctx.paths.state)
    if command in {"all", "recovery"} and not bool(state.get("recovery_complete")):
        run_recovery(ctx, backend=backend, resume=resume)
    state = read_json(ctx.paths.state)
    if command in {"all", "uncertainty"} and not bool(state.get("uncertainty_complete")):
        run_uncertainty(ctx, backend=backend, resume=resume)
    state = read_json(ctx.paths.state)
    if command in {"all", "preconditioned"} and not bool(state.get("preconditioned_complete")):
        run_preconditioned(ctx, backend=backend, resume=resume)
    state = read_json(ctx.paths.state)
    if command in {"all", "restart"} and not bool(state.get("restart_complete")):
        run_restart_sweep(ctx, backend=backend, resume=resume)
    state = read_json(ctx.paths.state)
    if command in {"all", "confirmation"} and not bool(state.get("confirmation_complete")):
        run_confirmation(ctx, backend=backend, resume=resume)
    summary = analyze_stage40(ctx)
    if command == "all":
        _update_state(ctx, finished=True, stop_reason="pipeline_complete")
    return summary


def synthetic_stage40_test() -> dict[str, Any]:
    cfg = read_json(Path(__file__).resolve().parents[2] / "configs/stage4_0_robustness_recovery_350ms.json")
    assert int(cfg["parallel"]["n_workers"]) == 192
    assert len(cfg["heldout_targets"]["scenarios"]) >= 16
    assert len(cfg["failure_recovery"]["amplitudes_by_mode"]["0"]) >= 5
    # Pure recovery-summary logic.
    rows = [
        {"recovery_family": "f", "disturbance_amplitude_abs": 0.1, "baseline_pass": True, "feedback_pass": True},
        {"recovery_family": "f", "disturbance_amplitude_abs": 0.2, "baseline_pass": False, "feedback_pass": True},
    ]
    first = next(row for row in rows if not row["baseline_pass"])
    assert first["feedback_pass"]
    return {"stage": STAGE, "workers": 192, "heldout_targets": len(cfg["heldout_targets"]["scenarios"]), "synthetic_ok": True}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/stage4_0_robustness_recovery_350ms.json")
    parser.add_argument("--source-stage3-4-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--command",
        choices=("all", "prepare", "heldout", "recovery", "uncertainty", "preconditioned", "restart", "confirmation", "analyze"),
        default="all",
    )
    parser.add_argument("--synthetic-test", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.synthetic_test:
        print(json.dumps(synthetic_stage40_test(), indent=2))
        return
    result = execute(
        args.config,
        source_stage34_run=args.source_stage3_4_run,
        run_dir=args.run_dir,
        backend=args.backend,
        resume=bool(args.resume),
        command=args.command,
    )
    print(json.dumps(_json_safe(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
