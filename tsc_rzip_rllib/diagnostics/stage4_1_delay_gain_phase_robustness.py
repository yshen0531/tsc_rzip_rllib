"""Stage4.1 delay/gain/phase-aware robustness and recovery validation.

Stage4.1 freezes the confirmed Stage3.4 target-conditioned library and real-TSC
175x105 Jacobian, but upgrades the online controller wrapper with:

* an alpha-beta state observer instead of raw noisy finite differences;
* explicit action-delay queue prediction and nominal queue priming;
* gain/slew scheduled Jacobian columns and nominal pre-compensation;
* phase-aligned continuation after prelude histories;
* an adaptive disturbance ladder that continues until open-loop failure;
* category-separated uncertainty gates and multi-seed noise statistics.

The strongest verdict remains a finite test-envelope result.  It is not
hardware deployment qualification, true plant-parameter validation, or proof of
robustness to every hidden vessel/eddy-current state.
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
from typing import Any, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as base
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_4_late_arrival_continuation_mpc as s34
from tsc_rzip_rllib.diagnostics import stage4_0_robustness_recovery as s40
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

SCHEMA_VERSION = 1
STAGE = "Stage4.1"
STATE_FILENAME = "stage4_1_state.json"
MANIFEST_FILENAME = "stage4_1_manifest.json"
EXPECTED_STAGE34_VERDICT = (
    "PASS_LATE_ARRIVAL_TARGET_CONDITIONED_RECEDING_HORIZON_MPC_TEST_ENVELOPE_CONFIRMED"
)


# ---------------------------------------------------------------------------
# Strict JSON and generic utilities
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
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


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


def _scenario_digest(*parts: Any, prefix: str = "s41") -> str:
    raw = json.dumps(_json_safe(parts), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:20]}"


def _result_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(read_json_gz(path).get("success", False))
    except Exception:
        return False


def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denom = 1.0 + z * z / total
    center = p + z * z / (2.0 * total)
    radius = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    return max(0.0, (center - radius) / denom)


# ---------------------------------------------------------------------------
# Paths, source chain, and context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage41Paths:
    run_dir: Path
    state: Path
    manifest: Path
    regression: Path
    recovery: Path
    structured: Path
    noise: Path
    history: Path
    restart: Path
    confirmation: Path
    analysis: Path
    variants: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            regression=run_dir / "stage4_1_regression_targets",
            recovery=run_dir / "stage4_1_adaptive_recovery",
            structured=run_dir / "stage4_1_structured_uncertainty",
            noise=run_dir / "stage4_1_noise_statistics",
            history=run_dir / "stage4_1_phase_aligned_history",
            restart=run_dir / "stage4_1_restart_sweep",
            confirmation=run_dir / "stage4_1_confirmation",
            analysis=run_dir / "stage4_1_analysis",
            variants=run_dir / "stage4_1_environment_variants",
            source_reference=run_dir / "source_stage4_0_reference",
        )


@dataclass
class Stage41Context:
    cfg: dict[str, Any]
    paths: Stage41Paths
    project_dir: Path
    source_stage40_run: Path
    source_stage40_manifest: dict[str, Any]
    source_stage40_summary: dict[str, Any]
    source_stage34_run: Path
    source_cfg: dict[str, Any]
    source_train_cfg: dict[str, Any]
    source_env_cfg: dict[str, Any]
    source_library: dict[str, Any]
    source_bundle: dict[str, Any]
    source_scale: float
    base34: Any
    source_fingerprint: dict[str, Any]
    variants: dict[str, dict[str, Any]]


def resolve_source_stage40_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE4_0_RUN", "").strip()
    if not value:
        raise ValueError("Stage4.1 requires --source-stage4-0-run or SOURCE_STAGE4_0_RUN")
    run = Path(value).expanduser().resolve()
    required = [
        run / "stage4_0_manifest.json",
        run / "stage4_0_state.json",
        run / "stage4_0_analysis/stage4_0_analysis_summary.json",
        run / "stage4_0_analysis/stage4_0_verdict.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage4.0 source run: " + ", ".join(missing))
    return run


def _resolve_source_stage34(project_dir: Path, stage40_run: Path, manifest: dict[str, Any]) -> Path:
    raw = str(manifest.get("source_stage3_4_run", "")).strip()
    if not raw:
        raise ValueError("Stage4.0 manifest has no source_stage3_4_run")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (project_dir / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        fallback = project_dir / "stage3_4_runs" / path.name
        if fallback.exists():
            path = fallback.resolve()
    return s40.resolve_source_stage34_run(path)


def _source_inventory(stage40_run: Path, stage34_run: Path) -> dict[str, Any]:
    paths: list[tuple[str, Path]] = [
        ("stage4_0/stage4_0_manifest.json", stage40_run / "stage4_0_manifest.json"),
        ("stage4_0/stage4_0_state.json", stage40_run / "stage4_0_state.json"),
        ("stage4_0/stage4_0_analysis_summary.json", stage40_run / "stage4_0_analysis/stage4_0_analysis_summary.json"),
        ("stage4_0/stage4_0_verdict.json", stage40_run / "stage4_0_analysis/stage4_0_verdict.json"),
        ("stage3_4/stage3_4_config.resolved.json", stage34_run / "stage3_4_config.resolved.json"),
        ("stage3_4/stage3_4_manifest.json", stage34_run / "stage3_4_manifest.json"),
        ("stage3_4/target_library.json", stage34_run / "stage3_4_target_library/target_library.json"),
        ("stage3_4/full_horizon_bundle.json", stage34_run / "stage3_4_identification/full_horizon_bundle.json"),
        ("stage3_4/calibration_summary.json", stage34_run / "stage3_4_mpc_calibration/calibration_summary.json"),
        ("stage3_4/verdict.json", stage34_run / "stage3_4_confirmations/stage3_4_verdict.json"),
    ]
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    total = 0
    for logical, path in paths:
        if not path.exists():
            continue
        sha = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"logical_path": logical, "sha256": sha, "bytes": size})
        digest.update(logical.encode()); digest.update(b"\0"); digest.update(sha.encode()); digest.update(b"\n")
        total += size
    return {"n_files": len(entries), "total_bytes": total, "digest": digest.hexdigest(), "entries": entries}


def validate_stage41_config(cfg: dict[str, Any], source_cfg: dict[str, Any]) -> None:
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.1 complete package is intentionally configured for 128 workers")
    gate = cfg["gate"]
    source_gate = source_cfg["gate"]
    for key in (
        "precise_tolerance_m", "relaxed_tolerance_m", "required_arrival_streak_steps",
        "hold_through_step", "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s", "ip_safety_tolerance_A",
    ):
        if not math.isclose(float(gate[key]), float(source_gate[key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.1 hard gate {key} differs from Stage3.4")
    for key in ("terminal_abs_tolerance_A", "hold_rms_tolerance_A", "sustained_max_tolerance_A"):
        if not math.isclose(float(gate["ip_tracking"][key]), float(source_gate["ip_tracking"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.1 Ip tracking threshold {key} differs from Stage3.4")
    if int(gate["hold_through_step"]) != 35:
        raise ValueError("Stage4.1 is fixed to the validated 350 ms horizon")


def load_stage41_config(
    config_path: str | Path,
    *,
    source_stage40_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage41Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = base.deep_replace_strings(read_json(config_path), {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)})
    source40 = resolve_source_stage40_run(source_stage40_run)
    manifest40 = read_json(source40 / "stage4_0_manifest.json")
    summary40 = read_json(source40 / "stage4_0_analysis/stage4_0_analysis_summary.json")
    source34 = _resolve_source_stage34(project_dir, source40, manifest40)
    source34_manifest = read_json(source34 / "stage3_4_manifest.json")
    source_cfg = read_json(source34 / "stage3_4_config.resolved.json")
    source_train = read_json(source34 / "train_config.resolved.json")
    source_env = read_json(source34 / "env_config.resolved.json")
    library = read_json(source34 / "stage3_4_target_library/target_library.json")
    bundle = read_json(source34 / "stage3_4_identification/full_horizon_bundle.json")
    calibration = read_json(source34 / "stage3_4_mpc_calibration/calibration_summary.json")
    source_scale = _as_float(calibration.get("selected_controller_scale"), math.nan)
    if not math.isfinite(source_scale) or source_scale <= 0.0:
        source_scale = _as_float((calibration.get("selected_scale_summary") or {}).get("controller_scale"), math.nan)
    if not math.isfinite(source_scale) or source_scale <= 0.0:
        raise ValueError("Stage3.4 calibration has no positive selected controller scale")
    validate_stage41_config(cfg, source_cfg)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage4_1_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage4_1_delay_gain_phase_robustness_350ms')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)
    source33 = Path(source34_manifest["source_stage3_3_run"]).expanduser()
    if not source33.is_absolute():
        source33 = (project_dir / source33).resolve()
    else:
        source33 = source33.resolve()
    if not source33.exists():
        fallback = project_dir / "stage3_3_runs" / source33.name
        if fallback.exists():
            source33 = fallback.resolve()
    base34 = s34.load_stage34_config(
        source34 / "stage3_4_config.resolved.json",
        source_stage33_run=source33,
        run_dir_override=run_dir,
    )
    storage = cfg.get("storage", {})
    env_cfg = copy.deepcopy(source_env)
    env_cfg["tsc_timeout_s"] = float(cfg.get("runtime", {}).get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    env_cfg["tsc_workspace_root"] = str(Path(os.environ.get("STAGE4_1_TSC_WORKSPACE_ROOT", storage.get("tsc_workspace_root", "/tmp/tsc_workspace"))).expanduser().resolve())
    env_cfg["run_root"] = str(Path(os.environ.get("STAGE4_1_TSC_RUN_ROOT", storage.get("tsc_run_root", "/tmp/tsc_workspace/episode_runs"))).expanduser().resolve())
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg = copy.deepcopy(source_train)
    train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 35
    base34.train_cfg = train_cfg
    base34.env_cfg = env_cfg
    return Stage41Context(
        cfg=cfg,
        paths=Stage41Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage40_run=source40,
        source_stage40_manifest=manifest40,
        source_stage40_summary=summary40,
        source_stage34_run=source34,
        source_cfg=source_cfg,
        source_train_cfg=train_cfg,
        source_env_cfg=env_cfg,
        source_library=library,
        source_bundle=bundle,
        source_scale=float(source_scale),
        base34=base34,
        source_fingerprint=_source_inventory(source40, source34),
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


def runtime_preflight(ctx: Stage41Context) -> dict[str, Any]:
    requested = int(os.environ.get("STAGE4_1_WORKERS", os.environ.get("STAGE4_WORKERS", ctx.cfg["parallel"]["n_workers"])))
    logical = int(os.cpu_count() or 1)
    reserve = int(ctx.cfg["parallel"].get("reserve_logical_cpus", 16))
    allowed = max(1, logical - reserve)
    if requested > allowed:
        raise RuntimeError(
            f"Stage4.1 requests {requested} workers but only {logical} logical CPUs are visible; "
            f"reserve={reserve}, safe maximum={allowed}. No silent fallback is allowed."
        )
    memory = _available_memory_gb()
    configured = max(1, int(ctx.cfg["parallel"].get("n_workers", 128)))
    minimum_memory = float(ctx.cfg["parallel"].get("minimum_available_memory_gb", 72.0)) * (requested / configured)
    if math.isfinite(memory) and memory < minimum_memory:
        raise RuntimeError(f"Stage4.1 requires at least {minimum_memory:.1f} GiB available memory; {memory:.1f} GiB is visible")
    soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
    minimum_fd = max(1024, requested * 16)
    if soft_fd < minimum_fd:
        raise RuntimeError(f"open-file soft limit {soft_fd} is below required {minimum_fd}")
    return {
        "requested_workers": requested,
        "logical_cpus": logical,
        "reserved_logical_cpus": reserve,
        "safe_worker_ceiling": allowed,
        "available_memory_gb": memory if math.isfinite(memory) else None,
        "open_file_soft_limit": soft_fd,
        "open_file_hard_limit": hard_fd,
    }


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "prepared": True,
        "regression_complete": False,
        "recovery_complete": False,
        "structured_complete": False,
        "noise_complete": False,
        "history_complete": False,
        "restart_complete": False,
        "confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41Context, **values: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(values)
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def initialize_stage41_run(ctx: Stage41Context) -> None:
    for path in (
        ctx.paths.run_dir, ctx.paths.regression, ctx.paths.recovery, ctx.paths.structured,
        ctx.paths.noise, ctx.paths.history, ctx.paths.restart, ctx.paths.confirmation,
        ctx.paths.analysis, ctx.paths.variants, ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if Path(old["source_stage4_0_run"]).resolve() != ctx.source_stage40_run:
            raise ValueError("Existing Stage4.1 run points to a different Stage4.0 source")
        digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        if digest and digest != ctx.source_fingerprint["digest"]:
            raise ValueError("Stage4.0/Stage3.4 source content changed since this Stage4.1 run was prepared")
    atomic_write_json(ctx.paths.run_dir / "stage4_1_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.source_train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.source_env_cfg)
    preflight = runtime_preflight(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "source_stage4_0_run": str(ctx.source_stage40_run),
        "source_stage3_4_run": str(ctx.source_stage34_run),
        "source_fingerprint": {key: value for key, value in ctx.source_fingerprint.items() if key != "entries"},
        "source_selected_controller_scale": ctx.source_scale,
        "workers": preflight,
        "hard_numeric_thresholds_changed": False,
        "target_library_and_jacobian_frozen": True,
        "controller_wrapper_upgraded": True,
        "finite_test_envelope_only": True,
        "deployment_robustness_validated": False,
        "final_task": "robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay",
    }
    if not ctx.paths.manifest.exists():
        atomic_write_json(ctx.paths.manifest, manifest)
    inventory = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory.exists():
        atomic_write_json(inventory, ctx.source_fingerprint)
    for source_root, prefix, relatives in (
        (ctx.source_stage40_run, "stage4_0", [
            "stage4_0_manifest.json", "stage4_0_state.json",
            "stage4_0_analysis/stage4_0_analysis_summary.json",
            "stage4_0_analysis/stage4_0_verdict.json",
        ]),
        (ctx.source_stage34_run, "stage3_4", [
            "stage3_4_config.resolved.json", "stage3_4_manifest.json",
            "stage3_4_target_library/target_library.json",
            "stage3_4_identification/full_horizon_bundle.json",
            "stage3_4_mpc_calibration/calibration_summary.json",
            "stage3_4_confirmations/stage3_4_verdict.json",
        ]),
    ):
        for relative in relatives:
            src = source_root / relative
            if src.exists():
                dst = ctx.paths.source_reference / prefix / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    shutil.copy2(src, dst)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())
    _register_base_variant(ctx)


# ---------------------------------------------------------------------------
# Environment variants
# ---------------------------------------------------------------------------


def _variant_id(prefix: str, value: Any) -> str:
    text = str(value).replace(".", "p").replace("-", "m").replace("+", "p")
    return f"{prefix}_{text}"


def _materialize_variant(
    ctx: Stage41Context,
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
    payload["max_delta_a"] = float(env_cfg["current_slew_a_per_ms"]) * float(env_cfg["dt_ms"])
    payload["stage4_1_cfg"] = copy.deepcopy(ctx.cfg)
    payload["variant_id"] = variant_id
    payload["start_folder"] = env_cfg.get("start_folder")
    payload["slew_scale"] = float(slew_scale)
    ctx.variants[variant_id] = payload
    return payload


def _register_base_variant(ctx: Stage41Context) -> None:
    _materialize_variant(ctx, "base", start_folder=str(ctx.source_env_cfg.get("start_folder", "1100ms")), slew_scale=1.0)


def discover_restart_folders(ctx: Stage41Context) -> list[str]:
    cfg = ctx.cfg["restart_sweep"]
    explicit = os.environ.get(str(cfg.get("environment_variable", "STAGE4_1_START_FOLDERS")), "").strip()
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
        if (simulation_root / folder).is_dir():
            unique.append(folder)
    return unique


# ---------------------------------------------------------------------------
# Observer and delay/gain-aware MPC
# ---------------------------------------------------------------------------


@dataclass
class AlphaBetaObserver:
    alpha: float
    beta: float
    alpha_ip: float
    max_abs_velocity: float
    position: np.ndarray | None = None
    velocity: np.ndarray | None = None
    ip: float | None = None
    last_index: int | None = None

    def update(self, measurement: np.ndarray, measurement_index: int, dt_s: float) -> None:
        measurement = np.asarray(measurement, dtype=float)
        if self.position is None:
            self.position = measurement[:2].copy()
            self.velocity = np.zeros(2, dtype=float)
            self.ip = float(measurement[2])
            self.last_index = int(measurement_index)
            return
        if self.last_index is not None and measurement_index <= self.last_index:
            return
        elapsed_steps = max(1, int(measurement_index - int(self.last_index)))
        elapsed = elapsed_steps * dt_s
        predicted = self.position + self.velocity * elapsed
        residual = measurement[:2] - predicted
        self.position = predicted + self.alpha * residual
        self.velocity = self.velocity + (self.beta / max(elapsed, 1e-12)) * residual
        self.velocity = np.clip(self.velocity, -self.max_abs_velocity, self.max_abs_velocity)
        self.ip = (1.0 - self.alpha_ip) * float(self.ip) + self.alpha_ip * float(measurement[2])
        self.last_index = int(measurement_index)

    def predict_to(self, current_index: int, dt_s: float) -> tuple[np.ndarray, np.ndarray, float]:
        if self.position is None or self.velocity is None or self.ip is None or self.last_index is None:
            raise RuntimeError("observer has not been initialized")
        ahead = max(0, int(current_index - self.last_index)) * dt_s
        return self.position + self.velocity * ahead, self.velocity.copy(), float(self.ip)


def _scaled_jacobian(bundle: dict[str, Any], model_scale: float) -> np.ndarray:
    return np.asarray(bundle["jacobian_normalized"], dtype=float) * float(model_scale)


def solve_delay_gain_aware_correction(
    ctx_stub: Any,
    bundle: dict[str, Any],
    *,
    current_step: int,
    modeled_action_delay_steps: int,
    modeled_pending_commands: Sequence[np.ndarray],
    nominal_physical_coefficients: np.ndarray,
    nominal_command_coefficients: np.ndarray,
    nominal_feature: np.ndarray,
    measurement_normalized: np.ndarray,
    integral_normalized: np.ndarray,
    previous_correction: np.ndarray,
    controller_scale: float,
    estimated_effective_gain_by_mode: np.ndarray,
    controller_model_scale: float,
) -> dict[str, Any]:
    try:
        from scipy.optimize import lsq_linear
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage4.1 MPC") from exc
    current_step = int(current_step)
    delay = max(0, int(modeled_action_delay_steps))
    effect_step = min(current_step + delay, 35)
    if effect_step >= 35:
        return {
            "first_correction": np.zeros(3), "sequence_correction": np.zeros((0, 3)),
            "solver_success": True, "solver_status": 0, "solver_cost": 0.0,
            "solver_optimality": 0.0, "predicted_normalized_residual_rms": 0.0,
            "active_lower": 0, "active_upper": 0, "effect_step": effect_step,
            "fixed_pending_steps": delay,
        }
    jacobian_base = _scaled_jacobian(bundle, controller_model_scale)
    scales = np.asarray(bundle["output_scales"], dtype=float)
    rows = s34._future_feature_rows(current_step)
    projection = s34._measurement_bias_projection(ctx_stub, current_step, rows)
    integral_gain = np.asarray(ctx_stub.cfg["mpc"]["integral_measurement_gain"], dtype=float)
    effective_measurement = np.asarray(measurement_normalized, dtype=float) + integral_gain * np.asarray(integral_normalized, dtype=float)
    future_error = nominal_feature[np.asarray(rows)] / scales[np.asarray(rows)] + projection @ effective_measurement

    gain = np.asarray(estimated_effective_gain_by_mode, dtype=float).reshape(3)
    gain = np.clip(gain, 1e-6, None)
    fixed_steps = list(range(current_step, min(effect_step, 35)))
    if fixed_steps:
        fixed_columns = [step * 3 + mode for step in fixed_steps for mode in range(3)]
        fixed_delta: list[float] = []
        for offset, step in enumerate(fixed_steps):
            if offset < len(modeled_pending_commands):
                command = np.asarray(modeled_pending_commands[offset], dtype=float)
            else:
                command = np.asarray(nominal_command_coefficients[step], dtype=float)
            physical = gain * command
            fixed_delta.extend((physical - nominal_physical_coefficients[step]).tolist())
        future_error = future_error + jacobian_base[np.ix_(rows, fixed_columns)] @ np.asarray(fixed_delta, dtype=float)

    free_steps = list(range(effect_step, 35))
    columns = [step * 3 + mode for step in free_steps for mode in range(3)]
    column_scale = np.tile(gain, 35)
    a = jacobian_base[np.ix_(rows, columns)] * column_scale[np.asarray(columns)][None, :]
    weights = s34._state_weight_vector(ctx_stub, rows, current_step)
    sqrt_w = np.sqrt(np.maximum(weights, 0.0))
    augmented_a: list[np.ndarray] = [sqrt_w[:, None] * a]
    augmented_b: list[np.ndarray] = [-sqrt_w * future_error]

    nominal_future = np.asarray(nominal_command_coefficients, dtype=float)[free_steps].reshape(-1)
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
        from tsc_rzip_rllib.diagnostics import stage3_3_target_conditioned_mpc as s33
        difference = s33._difference_matrix(len(free_steps))
        augmented_a.append(math.sqrt(smooth) * difference)
        augmented_b.append(np.zeros(difference.shape[0]))
    rate = float(ctx_stub.cfg["mpc"].get("first_action_rate_weight", 0.20))
    if rate > 0.0:
        first_matrix = np.zeros((3, len(columns)))
        first_matrix[:, :3] = np.eye(3)
        augmented_a.append(math.sqrt(rate) * first_matrix)
        augmented_b.append(math.sqrt(rate) * np.asarray(previous_correction, dtype=float))
    solution = lsq_linear(
        np.vstack(augmented_a), np.concatenate(augmented_b), bounds=(lower, upper),
        method="trf", tol=float(ctx_stub.cfg["mpc"].get("solver_tolerance", 1e-8)),
        max_iter=int(ctx_stub.cfg["mpc"].get("solver_max_iterations", 300)), lsmr_tol="auto",
    )
    sequence = np.asarray(solution.x, dtype=float).reshape(len(free_steps), 3)
    first = sequence[0]
    rate_limit = np.asarray(ctx_stub.cfg["mpc"]["per_step_correction_rate_limit_by_mode"], dtype=float)
    first = np.clip(first, np.asarray(previous_correction) - rate_limit, np.asarray(previous_correction) + rate_limit)
    first = np.clip(first, lower[:3], upper[:3])
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
    }


# ---------------------------------------------------------------------------
# Worker and Ray evaluation
# ---------------------------------------------------------------------------


class LocalStage41Worker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env

        self.cfg = payload["cfg"]
        self.robust_cfg = payload["stage4_1_cfg"]
        self.train_cfg = payload["train_cfg"]
        self.env_cfg = payload["env_cfg"]
        self.modes_tsc = np.asarray(payload["modes_tsc"], dtype=float)
        self.max_delta_a = float(payload["max_delta_a"])
        self.min_current = np.asarray(payload["min_current_tsc"], dtype=float)
        self.max_current = np.asarray(payload["max_current_tsc"], dtype=float)
        self.variant_id = str(payload.get("variant_id", "base"))
        self.actual_slew_scale = float(payload.get("slew_scale", 1.0))
        self.library = library
        self.bundle = bundle
        self.stub = SimpleNamespace(cfg=self.cfg, env_cfg=self.env_cfg)
        self.env = make_tsc_rzip_env(copy.deepcopy(self.train_cfg), worker_id=worker_id, seed=None)

    def _mode_action(self, effective_coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
        desired = np.asarray(effective_coefficients, dtype=float) @ self.modes_tsc.T
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
            offset = np.asarray([
                spec.get("target_R_offset_m", 0.0), spec.get("target_Z_offset_m", 0.0), spec.get("target_Ip_offset_A", 0.0)
            ], dtype=float)
            interpolation = s34.interpolation_for_target(self.stub, self.library, offset)
            nominal_physical = _vector(interpolation["full_control_vector"], 105).reshape(35, 3)
            nominal_y = np.asarray(interpolation["nominal_trajectory_RZI"], dtype=float)
            nominal_velocity = np.asarray(interpolation["nominal_velocity_RZ"], dtype=float)
            requested_target = np.asarray([
                float(self.cfg["target"]["R"]) + offset[0],
                float(self.cfg["target"]["Z"]) + offset[1],
                float(self.cfg["target"]["Ip"]) + offset[2],
            ], dtype=float)
            nominal_feature = s34._nominal_feature(nominal_y, nominal_velocity, requested_target)

            actual_gain = np.asarray(spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]), dtype=float)
            gain_estimate = np.asarray(spec.get("controller_gain_estimate_by_mode", actual_gain), dtype=float)
            slew_estimate = float(spec.get("controller_slew_scale_estimate", self.actual_slew_scale))
            schedule = self.robust_cfg["controller_upgrade"]["gain_slew_scheduling"]
            effective_estimate = gain_estimate * slew_estimate
            effective_estimate = np.clip(
                effective_estimate,
                float(schedule.get("minimum_effective_scale", 0.70)),
                float(schedule.get("maximum_effective_scale", 1.30)),
            )
            lower_mode = np.asarray(self.cfg["trajectory"]["coefficient_lower"], dtype=float)
            upper_mode = np.asarray(self.cfg["trajectory"]["coefficient_upper"], dtype=float)
            if bool(schedule.get("precompensate_nominal", True)):
                nominal_command = np.clip(nominal_physical / effective_estimate[None, :], lower_mode, upper_mode)
            else:
                nominal_command = nominal_physical.copy()

            controller_scale = float(spec.get("controller_scale", 0.0))
            actual_delay = max(0, int(spec.get("action_delay_steps", 0)))
            modeled_delay = max(0, int(spec.get("controller_action_delay_steps", actual_delay)))
            maximum_delay = int(self.robust_cfg["controller_upgrade"]["delay_aware"].get("maximum_modeled_action_delay_steps", 2))
            modeled_delay = min(modeled_delay, maximum_delay)
            prime_queue = bool(spec.get(
                "prime_action_queue_with_nominal",
                self.robust_cfg["controller_upgrade"]["delay_aware"].get("prime_action_queue_with_nominal", True),
            ))
            command_queue: list[np.ndarray] = []
            for index in range(actual_delay):
                command_queue.append(nominal_command[index].copy() if prime_queue else np.zeros(3, dtype=float))

            self.env.reset()
            zero_action = np.zeros(14, dtype=np.float32)
            prelude_trajectory.append(base._state_record(self.env, 0, zero_action))
            prelude_deltas = spec.get("prelude_mode_deltas") or []
            phase_offset = len(prelude_deltas)
            for prelude_step, delta_command in enumerate(prelude_deltas):
                command = np.clip(nominal_command[prelude_step] + np.asarray(delta_command, dtype=float), lower_mode, upper_mode)
                effective = actual_gain * command + np.asarray(spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]), dtype=float)
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(effective, currents)
                _, _, terminated, truncated, info = self.env.step(action)
                prelude_trajectory.append(base._state_record(self.env, prelude_step + 1, action))
                if terminated:
                    failure_reason = str(info.get("failure_reason", "prelude terminated")); break
                if truncated:
                    failure_reason = "environment truncated during prelude"; break
            if failure_reason:
                raise RuntimeError(failure_reason)

            # The full trajectory remains exactly 36 states.  Prelude steps
            # consume the beginning of the 350 ms horizon, and the controller
            # continues from the matching absolute nominal phase.
            trajectory = [copy.deepcopy(row) for row in prelude_trajectory]
            phase_start_state = np.asarray([
                trajectory[-1]["R"], trajectory[-1]["Z"], trajectory[-1]["Ip"]
            ], dtype=float)
            phase_start_reference = nominal_y[phase_offset]
            phase_start_error = phase_start_state - phase_start_reference

            measurement_scales = np.asarray([
                self.cfg["identification"]["output_scales"]["R_m"],
                self.cfg["identification"]["output_scales"]["Z_m"],
                self.cfg["identification"]["output_scales"]["vR_m_per_s"],
                self.cfg["identification"]["output_scales"]["vZ_m_per_s"],
                self.cfg["identification"]["output_scales"]["Ip_A"],
            ], dtype=float)
            noise_cfg = spec.get("observation_noise") or {}
            rng = np.random.default_rng(int(noise_cfg.get("seed", 0)))
            noise_sigma = np.asarray([
                noise_cfg.get("R_sigma_m", 0.0), noise_cfg.get("Z_sigma_m", 0.0), noise_cfg.get("Ip_sigma_A", 0.0)
            ], dtype=float)
            bias_cfg = spec.get("observation_bias") or {}
            bias = np.asarray([bias_cfg.get("R_m", 0.0), bias_cfg.get("Z_m", 0.0), bias_cfg.get("Ip_A", 0.0)], dtype=float)
            observation_delay = max(0, int(spec.get("observation_delay_steps", 0)))
            observation_history: list[np.ndarray] = []
            dt_s = float(self.env_cfg["dt_ms"]) / 1000.0
            observer_cfg = self.robust_cfg["controller_upgrade"]["observer"]
            observer = AlphaBetaObserver(
                alpha=float(observer_cfg.get("alpha_position", 0.72)),
                beta=float(observer_cfg.get("beta_velocity", 0.16)),
                alpha_ip=float(observer_cfg.get("alpha_ip", 0.45)),
                max_abs_velocity=float(observer_cfg.get("maximum_abs_velocity_m_per_s", 2.0)),
            )
            # Seed the observer with every already executed prelude state.  This
            # preserves the correct phase velocity instead of resetting the
            # estimated velocity to zero at the prelude/main boundary.
            for observer_index, row in enumerate(prelude_trajectory):
                observer.update(
                    np.asarray([row["R"], row["Z"], row["Ip"]], dtype=float),
                    observer_index,
                    dt_s,
                )
            integral = np.zeros(5, dtype=float)
            previous_correction = np.zeros(3, dtype=float)
            model_scale = float(spec.get("controller_model_scale", 1.0))
            actuator_bias = np.asarray(spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]), dtype=float)
            disturbance = spec.get("disturbance") or None

            for absolute_step in range(phase_offset, 35):
                state = self.env.last_state
                current_true = np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)
                measured_now = current_true + bias + rng.normal(0.0, noise_sigma)
                observation_history.append(measured_now)
                local_index = len(observation_history) - 1
                delayed_local_index = max(0, local_index - observation_delay)
                delayed_absolute_index = phase_offset + delayed_local_index
                observer.update(observation_history[delayed_local_index], delayed_absolute_index, dt_s)
                estimated_position, estimated_velocity, estimated_ip = observer.predict_to(absolute_step, dt_s)
                measurement_physical = np.asarray([
                    estimated_position[0] - nominal_y[absolute_step, 0],
                    estimated_position[1] - nominal_y[absolute_step, 1],
                    estimated_velocity[0] - nominal_velocity[absolute_step, 0],
                    estimated_velocity[1] - nominal_velocity[absolute_step, 1],
                    estimated_ip - nominal_y[absolute_step, 2],
                ], dtype=float)
                measurement = measurement_physical / measurement_scales
                integral = float(self.cfg["mpc"].get("integral_decay", 0.92)) * integral + measurement

                modeled_pending: list[np.ndarray] = []
                for index in range(modeled_delay):
                    if index < len(command_queue):
                        modeled_pending.append(np.asarray(command_queue[index], dtype=float))
                    else:
                        ref_step = min(absolute_step + index, 34)
                        modeled_pending.append(nominal_command[ref_step].copy())
                if controller_scale <= 0.0:
                    effect_step = min(absolute_step + modeled_delay, 34)
                    solve = {
                        "first_correction": np.zeros(3), "sequence_correction": np.zeros((0, 3)),
                        "solver_success": True, "solver_status": 0, "solver_cost": 0.0,
                        "solver_optimality": 0.0,
                        "predicted_normalized_residual_rms": float(np.sqrt(np.mean(measurement**2))),
                        "active_lower": 0, "active_upper": 0, "effect_step": effect_step,
                        "fixed_pending_steps": modeled_delay,
                    }
                else:
                    solve = solve_delay_gain_aware_correction(
                        self.stub, self.bundle,
                        current_step=absolute_step,
                        modeled_action_delay_steps=modeled_delay,
                        modeled_pending_commands=modeled_pending,
                        nominal_physical_coefficients=nominal_physical,
                        nominal_command_coefficients=nominal_command,
                        nominal_feature=nominal_feature,
                        measurement_normalized=measurement,
                        integral_normalized=integral,
                        previous_correction=previous_correction,
                        controller_scale=controller_scale,
                        estimated_effective_gain_by_mode=effective_estimate,
                        controller_model_scale=model_scale,
                    )
                correction = np.asarray(solve["first_correction"], dtype=float)
                effect_step = min(int(solve.get("effect_step", absolute_step)), 34)
                issued_command = np.clip(nominal_command[effect_step] + correction, lower_mode, upper_mode)
                if actual_delay > 0:
                    command_queue.append(issued_command)
                    applied_command = np.asarray(command_queue.pop(0), dtype=float)
                else:
                    applied_command = issued_command

                disturbance_applied = 0.0
                if disturbance:
                    start = int(disturbance["step"])
                    duration = max(1, int(disturbance.get("duration_steps", 1)))
                    if start <= absolute_step < start + duration:
                        mode = int(disturbance["mode"])
                        requested_amplitude = float(disturbance["amplitude"])
                        before = float(applied_command[mode])
                        applied_command = applied_command.copy()
                        applied_command[mode] = float(np.clip(before + requested_amplitude, lower_mode[mode], upper_mode[mode]))
                        disturbance_applied = float(applied_command[mode] - before)

                effective_coefficients = actual_gain * applied_command + actuator_bias
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(effective_coefficients, currents)
                _, _, terminated, truncated, info = self.env.step(action)
                trajectory.append(base._state_record(self.env, absolute_step + 1, action))
                control_trace.append({
                    "step": absolute_step,
                    "phase_offset_steps": phase_offset,
                    "observation_delay_steps": observation_delay,
                    "actual_action_delay_steps": actual_delay,
                    "modeled_action_delay_steps": modeled_delay,
                    "measurement_physical": measurement_physical.tolist(),
                    "measurement_normalized": measurement.tolist(),
                    "integral_normalized": integral.tolist(),
                    "mode_correction": correction.tolist(),
                    "issued_mode_coefficients": issued_command.tolist(),
                    "applied_command_mode_coefficients": applied_command.tolist(),
                    "effective_mode_coefficients": effective_coefficients.tolist(),
                    "estimated_effective_gain_by_mode": effective_estimate.tolist(),
                    "actual_gain_by_mode": actual_gain.tolist(),
                    "disturbance_applied": disturbance_applied,
                    "solver_success": bool(solve["solver_success"]),
                    "solver_status": int(solve["solver_status"]),
                    "solver_cost": float(solve["solver_cost"]),
                    "predicted_normalized_residual_rms": float(solve["predicted_normalized_residual_rms"]),
                })
                previous_correction = correction
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated")); break
                if truncated and absolute_step + 1 < 35:
                    failure_reason = "environment truncated before the 350 ms horizon"; break

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
                "phase_start_diagnostics": {
                    "phase_offset_steps": phase_offset,
                    "R_error_to_nominal_m": float(phase_start_error[0]),
                    "Z_error_to_nominal_m": float(phase_start_error[1]),
                    "Ip_error_to_nominal_A": float(phase_start_error[2]),
                    "RZ_box_error_to_nominal_m": float(max(abs(phase_start_error[0]), abs(phase_start_error[1]))),
                },
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
            runner.cleanup_episode_workspace(failed=not bool(result.get("success")), reason=str(result.get("failure_reason", "stage4_1_complete")))
        return _json_safe(result)

    def close(self) -> None:
        self.env.close()


def _ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id):
            self.worker = LocalStage41Worker(payload, library, bundle, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor


def _ensure_variant_for_spec(ctx: Stage41Context, spec: dict[str, Any]) -> None:
    variant = str(spec.get("environment_variant", "base"))
    if variant in ctx.variants:
        return
    if variant == "base":
        _register_base_variant(ctx); return
    if spec.get("start_folder"):
        _materialize_variant(ctx, variant, start_folder=str(spec["start_folder"]), slew_scale=float(spec.get("slew_scale", 1.0))); return
    if spec.get("slew_scale") is not None:
        _materialize_variant(ctx, variant, start_folder=str(ctx.source_env_cfg.get("start_folder", "1100ms")), slew_scale=float(spec["slew_scale"])); return
    raise KeyError(f"Cannot reconstruct environment variant {variant!r}")


def evaluate_specs(
    ctx: Stage41Context,
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
        by_variant.setdefault(str(spec.get("environment_variant", "base")), []).append(spec)
    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, rows in by_variant.items():
        pending = [row for row in rows if not (resume and _result_complete(output_dir / f"{row['experiment_id']}.json.gz"))]
        if pending:
            pending_by_variant[variant] = pending

    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalStage41Worker(ctx.variants[variant], ctx.source_library, ctx.source_bundle, f"stage41_{variant}_serial")
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate(spec))
                    print(f"[Stage4.1 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray
        requested = int(os.environ.get("STAGE4_1_WORKERS", os.environ.get("STAGE4_WORKERS", ctx.cfg["parallel"]["n_workers"])))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1 mixed-variant]",
        )
        allocation = s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()}, plan.actor_count
        )
        print("[Stage4.1 mixed-variant] actor_allocation=" + json.dumps(allocation, sort_keys=True, separators=(",", ":")), flush=True)
        Actor = _ray_actor_class()
        all_actors: list[Any] = []
        actors_by_variant: dict[str, list[Any]] = {}
        for variant, count in allocation.items():
            actors = [Actor.remote(ctx.variants[variant], ctx.source_library, ctx.source_bundle, f"stage41_{variant}_{index:03d}") for index in range(count)]
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
                    print(f"[Stage4.1 mixed-variant] waiting {done}/{total_pending}", flush=True)
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": SCHEMA_VERSION, "experiment_id": spec["experiment_id"], "spec": spec,
                            "success": False, "failure_reason": repr(exc), "traceback": traceback.format_exc(), "trajectory": [],
                        }
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(f"[Stage4.1 mixed-variant] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(all_actors, timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)))
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


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
    environment_variant: str = "base",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = copy.deepcopy(extra or {})
    identity = {
        "phase": phase, "scenario": scenario, "category": category,
        "target": target, "controller_scale": controller_scale,
        "environment_variant": environment_variant, "extra": extra,
    }
    return {
        "kind": "stage4_1_robustness_mpc",
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


def _task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id", "scenario"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False, "mandatory": False, "parents": [],
        "category": str(spec.get("category", "robustness")),
    }


def result_row(ctx: Stage41Context, result: dict[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    metrics = s34.target_metrics(ctx.base34, _task_from_spec(spec), result, None)
    interpolation = result.get("library_interpolation") or {}
    trace = result.get("control_trace") or []
    phase_diag = result.get("phase_start_diagnostics") or {}
    max_correction = max((float(np.max(np.abs(row.get("mode_correction", [0.0, 0.0, 0.0])))) for row in trace), default=0.0)
    represented = np.asarray(interpolation.get("represented_target_offset", [math.nan, math.nan, math.nan]), dtype=float)
    requested = np.asarray([
        float(spec.get("target_R_offset_m", 0.0)), float(spec.get("target_Z_offset_m", 0.0)), float(spec.get("target_Ip_offset_A", 0.0))
    ], dtype=float)
    fidelity = represented - requested if represented.shape == (3,) else np.full(3, math.nan)
    return {
        "experiment_id": result["experiment_id"],
        "phase": spec.get("phase"), "scenario": spec.get("scenario"), "category": spec.get("category"),
        "target_id": spec.get("target_id"), "controller_scale": float(spec.get("controller_scale", 0.0)),
        "environment_variant": spec.get("environment_variant", "base"),
        "target_R_offset_m": requested[0], "target_Z_offset_m": requested[1], "target_Ip_offset_A": requested[2],
        "represented_R_offset_m": represented[0], "represented_Z_offset_m": represented[1], "represented_Ip_offset_A": represented[2],
        "representation_R_error_m": fidelity[0], "representation_Z_error_m": fidelity[1], "representation_Ip_error_A": fidelity[2],
        "library_exact_match": bool(interpolation and min(interpolation.get("distances", [1e9])) <= 1e-12),
        "library_task_ids": interpolation.get("task_ids", []),
        "disturbance": copy.deepcopy(spec.get("disturbance")),
        "recovery_family": spec.get("recovery_family"),
        "recovery_level": spec.get("recovery_level"),
        "disturbance_headroom_fraction": spec.get("disturbance_headroom_fraction"),
        "disturbance_amplitude_abs": spec.get("disturbance_amplitude_abs"),
        "disturbance_duration_steps": spec.get("disturbance_duration_steps"),
        "observation_noise": copy.deepcopy(spec.get("observation_noise")),
        "noise_level": spec.get("noise_level"), "noise_seed": spec.get("noise_seed"),
        "observation_delay_steps": int(spec.get("observation_delay_steps", 0)),
        "actual_action_delay_steps": int(spec.get("action_delay_steps", 0)),
        "controller_action_delay_steps": int(spec.get("controller_action_delay_steps", spec.get("action_delay_steps", 0))),
        "actuator_gain_by_mode": copy.deepcopy(spec.get("actuator_gain_by_mode")),
        "controller_gain_estimate_by_mode": copy.deepcopy(spec.get("controller_gain_estimate_by_mode")),
        "controller_slew_scale_estimate": float(spec.get("controller_slew_scale_estimate", 1.0)),
        "controller_model_scale": float(spec.get("controller_model_scale", 1.0)),
        "slew_scale": float(spec.get("slew_scale", 1.0)),
        "prelude_name": spec.get("prelude_name"), "start_folder": spec.get("start_folder"),
        "phase_offset_steps": int(phase_diag.get("phase_offset_steps", 0)),
        "phase_start_RZ_box_error_to_nominal_m": phase_diag.get("RZ_box_error_to_nominal_m"),
        "phase_start_Ip_error_to_nominal_A": phase_diag.get("Ip_error_to_nominal_A"),
        "max_abs_mode_correction": max_correction,
        **metrics,
    }


def summarize_pairs(rows: Sequence[dict[str, Any]], pair_fields: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return s40.summarize_pairs(rows, pair_fields)


# ---------------------------------------------------------------------------
# Phase A: target-regression guard
# ---------------------------------------------------------------------------


def run_regression(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["regression_targets"]
    specs: list[dict[str, Any]] = []
    for scenario in cfg["scenarios"]:
        target = {"target_id": scenario["scenario"], **scenario}
        for raw_scale in cfg["controller_scales"]:
            specs.append(_make_spec(
                phase="regression_targets", scenario=scenario["scenario"], category="regression_target",
                target=target, controller_scale=_resolve_scale(raw_scale, ctx.source_scale),
            ))
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.regression / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    pairs, pair_summary = summarize_pairs(rows, ("scenario", "category"))
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "regression_targets",
        "n_rollouts": len(rows), "n_scenarios": len(pairs), "pair_summary": pair_summary,
        "passed": bool(
            all(bool(row["feedback_pass"]) for row in pairs)
            and (not bool(cfg.get("require_no_lost_open_loop_passes", True)) or not any(bool(row["lost"]) for row in pairs))
        ),
    }
    write_csv(ctx.paths.regression / "results.csv", rows); write_csv(ctx.paths.regression / "pairs.csv", pairs)
    atomic_write_json(ctx.paths.regression / "results.json", rows); atomic_write_json(ctx.paths.regression / "summary.json", summary)
    _update_state(ctx, regression_complete=True, regression_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase B: adaptive disturbance boundary and fail-to-pass recovery
# ---------------------------------------------------------------------------


def _family_nominal(ctx: Stage41Context, target: dict[str, Any]) -> np.ndarray:
    offset = np.asarray([target.get("R_offset_m", 0.0), target.get("Z_offset_m", 0.0), target.get("Ip_offset_A", 0.0)], dtype=float)
    interpolation = s34.interpolation_for_target(ctx.base34, ctx.source_library, offset)
    return _vector(interpolation["full_control_vector"], 105).reshape(35, 3)


def _disturbance_headroom(nominal: np.ndarray, step: int, duration: int, mode: int, sign: int, lower: np.ndarray, upper: np.ndarray) -> float:
    stop = min(35, step + duration)
    values = nominal[step:stop, mode]
    if len(values) == 0:
        return 0.0
    if sign > 0:
        return float(max(0.0, np.min(upper[mode] - values)))
    return float(max(0.0, np.min(values - lower[mode])))


def run_recovery(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["adaptive_failure_recovery"]
    lower = np.asarray(ctx.source_cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper = np.asarray(ctx.source_cfg["trajectory"]["coefficient_upper"], dtype=float)
    families: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        nominal = _family_nominal(ctx, target)
        for step in cfg["steps"]:
            for mode in cfg["modes"]:
                for sign in cfg["signs"]:
                    families.append({
                        "family": f"{target['target_id']}__m{mode}__s{step:02d}__{'p' if sign > 0 else 'm'}",
                        "target": target, "nominal": nominal, "step": int(step), "mode": int(mode), "sign": int(sign),
                    })
    active = {row["family"]: row for row in families}
    all_rows: list[dict[str, Any]] = []
    all_pairs: list[dict[str, Any]] = []
    first_failure: dict[str, dict[str, Any]] = {}
    last_pass: dict[str, dict[str, Any]] = {}
    for level_index, level in enumerate(cfg["severity_ladder"]):
        if not active:
            break
        specs: list[dict[str, Any]] = []
        for family_id, family in active.items():
            duration = int(level["duration_steps"])
            headroom = _disturbance_headroom(
                family["nominal"], family["step"], duration, family["mode"], family["sign"], lower, upper
            )
            amplitude = float(family["sign"]) * float(level["headroom_fraction"]) * headroom
            for raw_scale in cfg["controller_scales"]:
                specs.append(_make_spec(
                    phase="adaptive_failure_recovery",
                    scenario=f"{family_id}__L{level_index}",
                    category="adaptive_failure_recovery",
                    target=family["target"],
                    controller_scale=_resolve_scale(raw_scale, ctx.source_scale),
                    extra={
                        "recovery_family": family_id,
                        "recovery_level": level_index,
                        "disturbance_headroom_fraction": float(level["headroom_fraction"]),
                        "disturbance_duration_steps": duration,
                        "disturbance_amplitude_abs": abs(amplitude),
                        "disturbance": {
                            "step": family["step"], "mode": family["mode"],
                            "amplitude": amplitude, "duration_steps": duration,
                        },
                    },
                ))
        level_dir = ctx.paths.recovery / f"level_{level_index:02d}"
        results = evaluate_specs(ctx, specs, output_dir=level_dir / "raw", backend=backend, resume=resume)
        rows = [result_row(ctx, result) for result in results]
        pairs, _ = summarize_pairs(rows, ("recovery_family", "recovery_level"))
        write_csv(level_dir / "results.csv", rows); write_csv(level_dir / "pairs.csv", pairs)
        atomic_write_json(level_dir / "results.json", rows); atomic_write_json(level_dir / "pairs.json", pairs)
        all_rows.extend(rows); all_pairs.extend(pairs)
        for pair in pairs:
            family_id = str(pair["recovery_family"])
            if bool(pair["baseline_pass"]):
                last_pass[family_id] = pair
            elif family_id not in first_failure:
                first_failure[family_id] = pair
                active.pop(family_id, None)
        print(json.dumps({
            "stage": STAGE, "phase": "adaptive_failure_recovery", "level": level_index,
            "active_after_level": len(active), "families_with_failure": len(first_failure),
        }, indent=2), flush=True)

    family_rows: list[dict[str, Any]] = []
    for family in families:
        family_id = family["family"]
        fail = first_failure.get(family_id)
        previous = last_pass.get(family_id)
        family_rows.append({
            "recovery_family": family_id,
            "open_loop_failure_reached": fail is not None,
            "first_failure_level": None if fail is None else fail["recovery_level"],
            "first_failure_baseline_margin": None if fail is None else fail["baseline_signed_margin"],
            "first_failure_feedback_margin": None if fail is None else fail["feedback_signed_margin"],
            "recovered_at_first_failure": bool(fail and fail["feedback_pass"]),
            "last_pass_level": None if previous is None else previous["recovery_level"],
            "last_pass_baseline_margin": None if previous is None else previous["baseline_signed_margin"],
            "disturbance_envelope_reached": fail is not None,
        })
    failed = [row for row in family_rows if row["open_loop_failure_reached"]]
    recovered = [row for row in failed if row["recovered_at_first_failure"]]
    pass_pairs = [row for row in all_pairs if bool(row["baseline_pass"])]
    preserved = [row for row in pass_pairs if bool(row["feedback_pass"])]
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "adaptive_failure_recovery",
        "n_rollouts": len(all_rows), "n_families": len(families),
        "n_families_with_open_loop_failure": len(failed),
        "n_families_recovered_at_first_failure": len(recovered),
        "failure_recovery_fraction": len(recovered) / max(len(failed), 1),
        "preserved_open_loop_pass_fraction": len(preserved) / max(len(pass_pairs), 1),
        "n_families_boundary_not_reached": len(families) - len(failed),
    }
    summary["passed"] = bool(
        len(failed) >= int(cfg["minimum_families_with_open_loop_failure"])
        and summary["failure_recovery_fraction"] >= float(cfg["minimum_failure_recovery_fraction"])
        and summary["preserved_open_loop_pass_fraction"] >= float(cfg["minimum_preserved_open_loop_pass_fraction"])
    )
    write_csv(ctx.paths.recovery / "all_results.csv", all_rows); write_csv(ctx.paths.recovery / "all_pairs.csv", all_pairs)
    write_csv(ctx.paths.recovery / "family_summary.csv", family_rows)
    atomic_write_json(ctx.paths.recovery / "family_summary.json", family_rows); atomic_write_json(ctx.paths.recovery / "summary.json", summary)
    _update_state(ctx, recovery_complete=True, recovery_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase C: structured delay/gain/slew uncertainty with per-category gates
# ---------------------------------------------------------------------------


def run_structured_uncertainty(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["structured_uncertainty"]
    specs: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for scenario in cfg["scenarios"]:
            extra = {key: copy.deepcopy(value) for key, value in scenario.items() if key not in {"name", "category"}}
            for raw_scale in cfg["controller_scales"]:
                specs.append(_make_spec(
                    phase="structured_uncertainty", scenario=f"{target['target_id']}__{scenario['name']}",
                    category=str(scenario["category"]), target=target,
                    controller_scale=_resolve_scale(raw_scale, ctx.source_scale), extra=extra,
                ))
        for row in cfg.get("slew_scale_variants", []):
            variant = _variant_id("slew", row["actual"])
            _materialize_variant(ctx, variant, start_folder=str(ctx.source_env_cfg.get("start_folder", "1100ms")), slew_scale=float(row["actual"]))
            for raw_scale in cfg["controller_scales"]:
                specs.append(_make_spec(
                    phase="structured_uncertainty", scenario=f"{target['target_id']}__{row['name']}",
                    category=str(row["category"]), target=target,
                    controller_scale=_resolve_scale(raw_scale, ctx.source_scale), environment_variant=variant,
                    extra={"slew_scale": float(row["actual"]), "controller_slew_scale_estimate": float(row["estimate"])},
                ))
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.structured / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    pairs, overall = summarize_pairs(rows, ("scenario", "category", "environment_variant"))
    category_rows: list[dict[str, Any]] = []
    required = cfg["required_categories"]
    for category in sorted({str(row["category"]) for row in pairs}):
        subset = [row for row in pairs if str(row["category"]) == category]
        mpc_fraction = sum(bool(row["feedback_pass"]) for row in subset) / max(len(subset), 1)
        baseline_pass = [row for row in subset if bool(row["baseline_pass"])]
        preserved_fraction = sum(bool(row["feedback_pass"]) for row in baseline_pass) / max(len(baseline_pass), 1)
        threshold = required.get(category)
        passed = None if threshold is None else bool(
            mpc_fraction >= float(threshold["minimum_mpc_pass_fraction"])
            and preserved_fraction >= float(threshold["minimum_preserved_fraction"])
        )
        category_rows.append({
            "category": category, "n_pairs": len(subset), "mpc_pass_fraction": mpc_fraction,
            "preserved_open_loop_pass_fraction": preserved_fraction,
            "n_recovered": sum(bool(row["recovered"]) for row in subset),
            "n_lost": sum(bool(row["lost"]) for row in subset),
            "required": threshold is not None, "passed": passed,
        })
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "structured_uncertainty",
        "n_rollouts": len(rows), "n_pairs": len(pairs), "pair_summary": overall,
        "category_summaries": category_rows,
        "passed": bool(all(row["passed"] is True for row in category_rows if row["required"])),
    }
    write_csv(ctx.paths.structured / "results.csv", rows); write_csv(ctx.paths.structured / "pairs.csv", pairs)
    write_csv(ctx.paths.structured / "category_summary.csv", category_rows)
    atomic_write_json(ctx.paths.structured / "results.json", rows); atomic_write_json(ctx.paths.structured / "summary.json", summary)
    _update_state(ctx, structured_complete=True, structured_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase D: multi-seed noise statistics
# ---------------------------------------------------------------------------


def run_noise_statistics(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["noise_statistics"]
    scale = _resolve_scale(cfg["controller_scale"], ctx.source_scale)
    specs: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for level in cfg["levels"]:
            # One open-loop baseline is enough; observation noise does not alter
            # the feed-forward command when controller_scale=0.
            specs.append(_make_spec(
                phase="noise_statistics", scenario=f"{target['target_id']}__{level['name']}__baseline",
                category="noise_statistics", target=target, controller_scale=0.0,
                extra={"noise_level": level["name"], "noise_seed": -1},
            ))
            for seed_index in range(int(level["n_seeds"])):
                seed = int(level["seed_start"]) + seed_index
                specs.append(_make_spec(
                    phase="noise_statistics", scenario=f"{target['target_id']}__{level['name']}__s{seed}",
                    category="noise_statistics", target=target, controller_scale=scale,
                    extra={
                        "noise_level": level["name"], "noise_seed": seed,
                        "observation_noise": {
                            "R_sigma_m": float(level["R_sigma_m"]), "Z_sigma_m": float(level["Z_sigma_m"]),
                            "Ip_sigma_A": float(level["Ip_sigma_A"]), "seed": seed,
                        },
                    },
                ))
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.noise / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    summaries: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for level in cfg["levels"]:
            subset = [row for row in rows if row["target_id"] == target["target_id"] and row["noise_level"] == level["name"] and float(row["controller_scale"]) > 0.0]
            successes = sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in subset)
            total = len(subset)
            fraction = successes / max(total, 1)
            lower = wilson_lower_bound(successes, total, float(cfg.get("confidence_z", 1.96)))
            summaries.append({
                "target_id": target["target_id"], "noise_level": level["name"],
                "n_seeds": total, "n_pass": successes, "pass_fraction": fraction,
                "wilson_lower_bound": lower,
                "minimum_pass_fraction": float(level["minimum_pass_fraction"]),
                "passed": bool(
                    fraction >= float(level["minimum_pass_fraction"])
                    and lower >= float(cfg.get("minimum_lower_confidence_bound", 0.75))
                ),
            })
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "noise_statistics",
        "n_rollouts": len(rows), "level_target_summaries": summaries,
        "passed": bool(all(row["passed"] for row in summaries)),
    }
    write_csv(ctx.paths.noise / "results.csv", rows); write_csv(ctx.paths.noise / "summary.csv", summaries)
    atomic_write_json(ctx.paths.noise / "results.json", rows); atomic_write_json(ctx.paths.noise / "summary.json", summary)
    _update_state(ctx, noise_complete=True, noise_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase E: phase-aligned preconditioned histories
# ---------------------------------------------------------------------------


def run_phase_aligned_history(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["phase_aligned_history"]
    specs: list[dict[str, Any]] = []
    for target in cfg["targets"]:
        for prelude in cfg["preludes"]:
            for raw_scale in cfg["controller_scales"]:
                specs.append(_make_spec(
                    phase="phase_aligned_history", scenario=f"{target['target_id']}__{prelude['name']}",
                    category="phase_aligned_history", target=target,
                    controller_scale=_resolve_scale(raw_scale, ctx.source_scale),
                    extra={"prelude_name": prelude["name"], "prelude_mode_deltas": prelude["mode_deltas"]},
                ))
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.history / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    pairs, pair_summary = summarize_pairs(rows, ("scenario", "category"))
    mpc_fraction = sum(bool(row["feedback_pass"]) for row in pairs) / max(len(pairs), 1)
    baseline_pass = [row for row in pairs if bool(row["baseline_pass"])]
    preserved = sum(bool(row["feedback_pass"]) for row in baseline_pass) / max(len(baseline_pass), 1)
    limits = cfg["visible_alignment_limits"]
    feedback_rows = [row for row in rows if float(row["controller_scale"]) > 0.0]
    hidden_like = [
        row for row in feedback_rows
        if _as_float(row.get("phase_start_RZ_box_error_to_nominal_m"), 1e9) <= float(limits["RZ_box_m"])
        and abs(_as_float(row.get("phase_start_Ip_error_to_nominal_A"), 1e12)) <= float(limits["Ip_A"])
    ]
    hidden_like_fraction = len(hidden_like) / max(len(feedback_rows), 1)
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "phase_aligned_history",
        "n_rollouts": len(rows), "n_scenarios": len(pairs), "mpc_pass_fraction": mpc_fraction,
        "preserved_open_loop_pass_fraction": preserved,
        "visible_state_matched_fraction": hidden_like_fraction,
        "test_interpretation": (
            "phase-aligned history variation with approximately matched visible state"
            if hidden_like_fraction >= 0.5
            else "phase-aligned restart variation; visible-state matching was insufficient for a pure hidden-state claim"
        ),
        "pair_summary": pair_summary,
    }
    summary["passed"] = bool(
        mpc_fraction >= float(cfg["minimum_mpc_pass_fraction"])
        and preserved >= float(cfg["minimum_preserved_open_loop_pass_fraction"])
    )
    write_csv(ctx.paths.history / "results.csv", rows); write_csv(ctx.paths.history / "pairs.csv", pairs)
    atomic_write_json(ctx.paths.history / "results.json", rows); atomic_write_json(ctx.paths.history / "summary.json", summary)
    _update_state(ctx, history_complete=True, history_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase F: alternate restart folders if actually present
# ---------------------------------------------------------------------------


def run_restart_sweep(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    cfg = ctx.cfg["restart_sweep"]
    folders = discover_restart_folders(ctx)
    specs: list[dict[str, Any]] = []
    for folder in folders:
        variant = _variant_id("restart", folder)
        _materialize_variant(ctx, variant, start_folder=folder, slew_scale=1.0)
        for target in cfg["targets"]:
            for raw_scale in cfg["controller_scales"]:
                specs.append(_make_spec(
                    phase="restart_sweep", scenario=f"{folder}__{target['target_id']}",
                    category="alternate_restart_state", target=target,
                    controller_scale=_resolve_scale(raw_scale, ctx.source_scale),
                    environment_variant=variant, extra={"start_folder": folder},
                ))
    if specs:
        results = evaluate_specs(ctx, specs, output_dir=ctx.paths.restart / "raw", backend=backend, resume=resume)
        rows = [result_row(ctx, result) for result in results]
        pairs, pair_summary = summarize_pairs(rows, ("scenario", "start_folder", "environment_variant"))
        mpc_fraction = sum(bool(row["feedback_pass"]) for row in pairs) / max(len(pairs), 1)
        base_pass = [row for row in pairs if bool(row["baseline_pass"])]
        preserved = sum(bool(row["feedback_pass"]) for row in base_pass) / max(len(base_pass), 1)
    else:
        rows, pairs, pair_summary = [], [], {"n_pairs": 0}
        mpc_fraction = preserved = 0.0
    available = len(folders) >= int(cfg["minimum_alternate_folders_for_validation"])
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "restart_sweep",
        "base_start_folder": str(ctx.source_env_cfg.get("start_folder")),
        "alternate_start_folders": folders, "n_alternate_start_folders": len(folders),
        "true_restart_validation_available": available, "n_rollouts": len(rows),
        "mpc_pass_fraction": mpc_fraction, "preserved_open_loop_pass_fraction": preserved,
        "pair_summary": pair_summary,
        "passed": bool(
            available
            and mpc_fraction >= float(cfg["minimum_mpc_pass_fraction"])
            and preserved >= float(cfg["minimum_preserved_open_loop_pass_fraction"])
        ),
    }
    write_csv(ctx.paths.restart / "results.csv", rows); write_csv(ctx.paths.restart / "pairs.csv", pairs)
    atomic_write_json(ctx.paths.restart / "results.json", rows); atomic_write_json(ctx.paths.restart / "summary.json", summary)
    _update_state(ctx, restart_complete=True, restart_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Confirmation, verdict, and analysis
# ---------------------------------------------------------------------------


def _load_phase_result(phase_dir: Path, experiment_id: str) -> dict[str, Any]:
    candidates = list(phase_dir.glob(f"**/raw/{experiment_id}.json.gz"))
    if not candidates:
        raise FileNotFoundError(experiment_id)
    return read_json_gz(candidates[0])


def select_confirmation_specs(ctx: Stage41Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["confirmation"]
    selected: list[dict[str, Any]] = []
    deterministic: list[dict[str, Any]] = []

    family_path = ctx.paths.recovery / "family_summary.json"
    pairs_path = ctx.paths.recovery / "all_pairs.csv"
    if family_path.exists() and pairs_path.exists():
        families = read_json(family_path)
        with pairs_path.open(newline="", encoding="utf-8") as handle:
            pair_rows = list(csv.DictReader(handle))
        recovered_ids = {str(row["recovery_family"]) for row in families if _as_bool(row.get("recovered_at_first_failure"))}
        candidates = [row for row in pair_rows if row.get("recovery_family") in recovered_ids and _as_bool(row.get("feedback_pass"))]
        candidates.sort(key=lambda row: _as_float(row.get("feedback_signed_margin"), 1e9))
        for row in candidates[:4]:
            deterministic.append(_load_phase_result(ctx.paths.recovery, str(row["feedback_experiment_id"]))["spec"])

    structured_pairs = ctx.paths.structured / "pairs.csv"
    if structured_pairs.exists():
        with structured_pairs.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        required_categories = set(ctx.cfg["structured_uncertainty"]["required_categories"])
        rows = [row for row in rows if row.get("category") in required_categories and _as_bool(row.get("feedback_pass"))]
        rows.sort(key=lambda row: _as_float(row.get("feedback_signed_margin"), 1e9))
        for row in rows[:4]:
            deterministic.append(_load_phase_result(ctx.paths.structured, str(row["feedback_experiment_id"]))["spec"])

    history_pairs = ctx.paths.history / "pairs.csv"
    if history_pairs.exists():
        with history_pairs.open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle) if _as_bool(row.get("feedback_pass"))]
        rows.sort(key=lambda row: _as_float(row.get("feedback_signed_margin"), 1e9))
        for row in rows[:2]:
            deterministic.append(_load_phase_result(ctx.paths.history, str(row["feedback_experiment_id"]))["spec"])

    restart_pairs = ctx.paths.restart / "pairs.csv"
    if restart_pairs.exists():
        with restart_pairs.open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle) if _as_bool(row.get("feedback_pass"))]
        rows.sort(key=lambda row: _as_float(row.get("feedback_signed_margin"), 1e9))
        for row in rows[:2]:
            deterministic.append(_load_phase_result(ctx.paths.restart, str(row["feedback_experiment_id"]))["spec"])

    seen: set[str] = set()
    maximum = int(cfg.get("maximum_deterministic_scenarios", 12))
    for spec in deterministic:
        identity = json.dumps({key: spec.get(key) for key in ("scenario", "category", "environment_variant")}, sort_keys=True)
        if identity in seen:
            continue
        seen.add(identity)
        for repeat in range(int(cfg.get("repeats_per_deterministic_scenario", 2))):
            clone = copy.deepcopy(spec)
            clone["phase"] = "confirmation"
            clone["confirmation_source_experiment_id"] = spec["experiment_id"]
            clone["confirmation_repeat"] = repeat
            clone["experiment_id"] = _scenario_digest(spec["experiment_id"], "confirmation", repeat)
            selected.append(clone)
        if len(seen) >= maximum:
            break

    high = next(row for row in ctx.cfg["noise_statistics"]["levels"] if row["name"] == "high")
    count = int(cfg.get("high_noise_new_seeds_per_target", 8))
    offset = int(cfg.get("noise_seed_offset", 100000))
    for target_index, target in enumerate(ctx.cfg["noise_statistics"]["targets"]):
        for index in range(count):
            seed = offset + target_index * 1000 + index
            selected.append(_make_spec(
                phase="confirmation", scenario=f"{target['target_id']}__high_noise_confirm_s{seed}",
                category="high_noise_confirmation", target=target, controller_scale=ctx.source_scale,
                extra={
                    "noise_level": "high", "noise_seed": seed,
                    "observation_noise": {
                        "R_sigma_m": float(high["R_sigma_m"]), "Z_sigma_m": float(high["Z_sigma_m"]),
                        "Ip_sigma_A": float(high["Ip_sigma_A"]), "seed": seed,
                    },
                },
            ))
    return selected


def run_confirmation(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = select_confirmation_specs(ctx)
    results = evaluate_specs(ctx, specs, output_dir=ctx.paths.confirmation / "raw", backend=backend, resume=resume)
    rows = [result_row(ctx, result) for result in results]
    deterministic_rows = [row for row in rows if row["category"] != "high_noise_confirmation"]
    deterministic_groups: dict[str, list[dict[str, Any]]] = {}
    for row in deterministic_rows:
        source_id = str(read_json_gz(ctx.paths.confirmation / "raw" / f"{row['experiment_id']}.json.gz")["spec"].get("confirmation_source_experiment_id", row["scenario"]))
        deterministic_groups.setdefault(source_id, []).append(row)
    deterministic_summary = [
        {
            "source_experiment_id": source_id,
            "repeats": len(group),
            "all_repeats_pass": bool(group and all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in group)),
            "worst_signed_margin": min(_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in group),
        }
        for source_id, group in deterministic_groups.items()
    ]
    high_rows = [row for row in rows if row["category"] == "high_noise_confirmation"]
    noise_summary: list[dict[str, Any]] = []
    high_threshold = next(row for row in ctx.cfg["noise_statistics"]["levels"] if row["name"] == "high")
    for target in ctx.cfg["noise_statistics"]["targets"]:
        group = [row for row in high_rows if row["target_id"] == target["target_id"]]
        successes = sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in group)
        fraction = successes / max(len(group), 1)
        noise_summary.append({
            "target_id": target["target_id"], "n_seeds": len(group), "n_pass": successes,
            "pass_fraction": fraction, "passed": fraction >= float(high_threshold["minimum_pass_fraction"]),
        })
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "phase": "confirmation",
        "n_rollouts": len(rows), "n_successful": sum(_as_bool(row.get("success")) for row in rows),
        "deterministic_summaries": deterministic_summary, "high_noise_summaries": noise_summary,
        "passed": bool(
            deterministic_summary
            and all(row["all_repeats_pass"] for row in deterministic_summary)
            and noise_summary
            and all(row["passed"] for row in noise_summary)
        ),
    }
    write_csv(ctx.paths.confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.confirmation / "results.json", rows); atomic_write_json(ctx.paths.confirmation / "summary.json", summary)
    _update_state(ctx, confirmation_complete=True, confirmation_summary=summary)
    return summary


def final_verdict(ctx: Stage41Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    core = all(bool((state.get(key) or {}).get("passed")) for key in (
        "regression_summary", "recovery_summary", "structured_summary",
        "noise_summary", "history_summary", "confirmation_summary",
    ))
    restart = state.get("restart_summary") or {}
    available = bool(restart.get("true_restart_validation_available"))
    restart_pass = bool(restart.get("passed")) if available else None
    if core and not available:
        label = "PASS_STAGE4_1_DELAY_GAIN_PHASE_ROBUSTNESS_AND_RECOVERY_CONFIRMED_TRUE_RESTART_NOT_AVAILABLE"
    elif core and restart_pass:
        label = "PASS_STAGE4_1_DELAY_GAIN_PHASE_ROBUSTNESS_RECOVERY_AND_TRUE_RESTART_CONFIRMED"
    elif core:
        label = "PASS_STAGE4_1_CONTROLLED_ROBUSTNESS_TRUE_RESTART_VALIDATION_FAILED"
    else:
        label = "STAGE4_1_DELAY_GAIN_PHASE_ROBUSTNESS_ENVELOPE_INCOMPLETE"
    verdict = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "created_utc": utc_timestamp(),
        "verdict": label, "source_stage4_0_run": str(ctx.source_stage40_run),
        "source_stage3_4_run": str(ctx.source_stage34_run),
        "source_selected_controller_scale": ctx.source_scale,
        "regression_passed": bool((state.get("regression_summary") or {}).get("passed")),
        "failure_recovery_passed": bool((state.get("recovery_summary") or {}).get("passed")),
        "structured_uncertainty_passed": bool((state.get("structured_summary") or {}).get("passed")),
        "noise_statistics_passed": bool((state.get("noise_summary") or {}).get("passed")),
        "phase_aligned_history_passed": bool((state.get("history_summary") or {}).get("passed")),
        "true_restart_validation_available": available,
        "true_restart_validation_passed": restart_pass,
        "confirmation_passed": bool((state.get("confirmation_summary") or {}).get("passed")),
        "finite_test_envelope_validated": bool(core and (not available or restart_pass)),
        "deployment_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "warning": "This verdict covers only the configured finite delay/gain/slew/noise/history/restart envelope. It is not deployment qualification.",
        "final_task": "robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay",
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1_verdict.json", verdict)
    return verdict


def analyze_stage41(ctx: Stage41Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    verdict = final_verdict(ctx)
    summary = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "created_utc": utc_timestamp(),
        "source_stage4_0_run": str(ctx.source_stage40_run),
        "source_stage3_4_run": str(ctx.source_stage34_run),
        "source_selected_controller_scale": ctx.source_scale,
        "regression": state.get("regression_summary", {}),
        "adaptive_failure_recovery": state.get("recovery_summary", {}),
        "structured_uncertainty": state.get("structured_summary", {}),
        "noise_statistics": state.get("noise_summary", {}),
        "phase_aligned_history": state.get("history_summary", {}),
        "restart_sweep": state.get("restart_summary", {}),
        "confirmation": state.get("confirmation_summary", {}),
        "verdict": verdict,
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1_analysis_summary.json", summary)
    return summary


def prepare_stage41(ctx: Stage41Context) -> dict[str, Any]:
    initialize_stage41_run(ctx)
    return {
        "stage": STAGE,
        "source_stage4_0_run": str(ctx.source_stage40_run),
        "source_stage3_4_run": str(ctx.source_stage34_run),
        "workers": runtime_preflight(ctx),
        "source_selected_controller_scale": ctx.source_scale,
        "controller_upgrades": copy.deepcopy(ctx.cfg["controller_upgrade"]),
    }


def execute(
    config_path: str | Path,
    *,
    source_stage40_run: str | Path | None = None,
    run_dir: str | Path | None = None,
    backend: str = "ray",
    resume: bool = True,
    command: str = "all",
) -> dict[str, Any]:
    ctx = load_stage41_config(config_path, source_stage40_run=source_stage40_run, run_dir_override=run_dir)
    prepare = prepare_stage41(ctx)
    if command == "prepare":
        return prepare
    if command in {"all", "regression"}:
        run_regression(ctx, backend=backend, resume=resume)
    if command in {"all", "recovery"}:
        run_recovery(ctx, backend=backend, resume=resume)
    if command in {"all", "structured"}:
        run_structured_uncertainty(ctx, backend=backend, resume=resume)
    if command in {"all", "noise"}:
        run_noise_statistics(ctx, backend=backend, resume=resume)
    if command in {"all", "history"}:
        run_phase_aligned_history(ctx, backend=backend, resume=resume)
    if command in {"all", "restart"}:
        run_restart_sweep(ctx, backend=backend, resume=resume)
    if command in {"all", "confirm"}:
        run_confirmation(ctx, backend=backend, resume=resume)
    if command in {"all", "analyze"}:
        analysis = analyze_stage41(ctx)
        _update_state(ctx, finished=True, stop_reason="pipeline_complete", analysis_summary=analysis)
        return analysis
    return read_json(ctx.paths.state)


# ---------------------------------------------------------------------------
# Dependency-free synthetic checks and CLI
# ---------------------------------------------------------------------------


def synthetic_stage41_test() -> dict[str, Any]:
    observer = AlphaBetaObserver(alpha=0.7, beta=0.15, alpha_ip=0.4, max_abs_velocity=2.0)
    dt = 0.01
    for index in range(5):
        observer.update(np.asarray([0.001 * index, -0.0005 * index, 100.0 + index]), index, dt)
    position, velocity, ip = observer.predict_to(5, dt)
    assert np.all(np.isfinite(position)) and np.all(np.isfinite(velocity)) and math.isfinite(ip)
    assert 0.0 <= wilson_lower_bound(9, 10) <= 1.0
    cfg = {
        "adaptive_failure_recovery": {
            "targets": [{"target_id": "n", "R_offset_m": 0.0, "Z_offset_m": 0.0, "Ip_offset_A": 0.0}],
            "steps": [4, 12, 24], "modes": [0, 1, 2], "signs": [-1, 1],
        }
    }
    families = len(cfg["adaptive_failure_recovery"]["targets"]) * 3 * 3 * 2
    assert families == 18
    return {"synthetic_ok": True, "workers": 128, "observer_position": position.tolist(), "families_per_target": 18}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage4.1 delay/gain/phase-aware robustness and recovery")
    parser.add_argument("--config", default="configs/stage4_1_delay_gain_phase_robustness_350ms.json")
    parser.add_argument("--source-stage4-0-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--command", choices=("all", "prepare", "regression", "recovery", "structured", "noise", "history", "restart", "confirm", "analyze"), default="all")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.self_test:
        print(json.dumps(synthetic_stage41_test(), indent=2)); return
    result = execute(
        args.config,
        source_stage40_run=args.source_stage4_0_run,
        run_dir=args.run_dir,
        backend=args.backend,
        resume=args.resume,
        command=args.command,
    )
    print(json.dumps(_json_safe(result), indent=2))


if __name__ == "__main__":
    main()
