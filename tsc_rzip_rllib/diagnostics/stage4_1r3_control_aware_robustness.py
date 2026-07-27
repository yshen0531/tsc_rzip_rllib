"""Stage4.1R3 control-aware residual observer and anti-windup robustness validation.

Stage4.1R3 freezes the confirmed Stage3.4 target-conditioned library and real-TSC
175x105 Jacobian, but upgrades the online controller wrapper with:

* a clean-sensor bypass that exactly reproduces the confirmed Stage3.4 path;
* a control-aware residual observer that subtracts the known Jacobian response
  of already-applied MPC corrections before filtering model residuals;
* optional integral anti-windup selected by a disjoint observer ablation;
* explicit action-delay queue prediction and nominal queue priming;
* physical 14-coil gain/slew scheduling and phase-aligned continuation;
* adaptive recovery, category-separated uncertainty gates, and multi-seed noise.

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

SCHEMA_VERSION = 3
STAGE = "Stage4.1R3"
CONTROLLER_REVISION = "control_aware_residual_observer_antiwindup_v3"
STATE_FILENAME = "stage4_1r3_state.json"
MANIFEST_FILENAME = "stage4_1r3_manifest.json"
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
    ablation: Path
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
            regression=run_dir / "stage4_1r3_regression_targets",
            ablation=run_dir / "stage4_1r3_observer_ablation",
            recovery=run_dir / "stage4_1r3_adaptive_recovery",
            structured=run_dir / "stage4_1r3_structured_uncertainty",
            noise=run_dir / "stage4_1r3_noise_statistics",
            history=run_dir / "stage4_1r3_phase_aligned_history",
            restart=run_dir / "stage4_1r3_restart_sweep",
            confirmation=run_dir / "stage4_1r3_confirmation",
            analysis=run_dir / "stage4_1r3_analysis",
            variants=run_dir / "stage4_1r3_environment_variants",
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
        raise ValueError("Stage4.1R3 requires --source-stage4-0-run or SOURCE_STAGE4_0_RUN")
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
    if str(cfg.get("controller_revision", "")) != CONTROLLER_REVISION:
        raise ValueError(
            f"Stage4.1R3 controller_revision must be {CONTROLLER_REVISION!r}; "
            f"got {cfg.get('controller_revision')!r}"
        )
    if int(cfg["parallel"]["n_workers"]) != 128:
        raise ValueError("Stage4.1R3 complete package is intentionally configured for 128 workers")
    gate = cfg["gate"]
    source_gate = source_cfg["gate"]
    for key in (
        "precise_tolerance_m", "relaxed_tolerance_m", "required_arrival_streak_steps",
        "hold_through_step", "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s", "ip_safety_tolerance_A",
    ):
        if not math.isclose(float(gate[key]), float(source_gate[key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.1R3 hard gate {key} differs from Stage3.4")
    for key in ("terminal_abs_tolerance_A", "hold_rms_tolerance_A", "sustained_max_tolerance_A"):
        if not math.isclose(float(gate["ip_tracking"][key]), float(source_gate["ip_tracking"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage4.1R3 Ip tracking threshold {key} differs from Stage3.4")
    if int(gate["hold_through_step"]) != 35:
        raise ValueError("Stage4.1R3 is fixed to the validated 350 ms horizon")
    observer_cfg = cfg.get("controller_upgrade", {}).get("observer", {})
    if str(observer_cfg.get("model", "")) != "control_aware_residual_alpha_beta":
        raise ValueError("Stage4.1R3 requires the control-aware residual observer model")
    if not bool(observer_cfg.get("clean_measurement_bypass", False)):
        raise ValueError("Stage4.1R3 requires clean_measurement_bypass=true")
    anti_windup = cfg.get("controller_upgrade", {}).get("anti_windup", {})
    if not bool(anti_windup.get("enabled", False)):
        raise ValueError("Stage4.1R3 requires the anti-windup implementation to be enabled")
    variants = cfg.get("observer_ablation", {}).get("variants", [])
    selectable = [row for row in variants if bool(row.get("selectable", False))]
    if not selectable or not all(str(row.get("observer_variant")) == "control_aware_residual" for row in selectable):
        raise ValueError("Stage4.1R3 ablation must select only control-aware residual observer variants")


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
        root = base.resolve_path(cfg.get("output_root", "stage4_1r3_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r3_control_aware_residual_observer_350ms')}_{utc_timestamp()}"
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
    env_cfg["tsc_workspace_root"] = str(Path(os.environ.get("STAGE4_1R3_TSC_WORKSPACE_ROOT", os.environ.get("STAGE4_1_TSC_WORKSPACE_ROOT", storage.get("tsc_workspace_root", "/tmp/tsc_workspace")))).expanduser().resolve())
    env_cfg["run_root"] = str(Path(os.environ.get("STAGE4_1R3_TSC_RUN_ROOT", os.environ.get("STAGE4_1_TSC_RUN_ROOT", storage.get("tsc_run_root", "/tmp/tsc_workspace/episode_runs")))).expanduser().resolve())
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
    requested = int(os.environ.get("STAGE4_1R3_WORKERS", os.environ.get("STAGE4_1_WORKERS", os.environ.get("STAGE4_WORKERS", ctx.cfg["parallel"]["n_workers"]))))
    logical = int(os.cpu_count() or 1)
    reserve = int(ctx.cfg["parallel"].get("reserve_logical_cpus", 16))
    allowed = max(1, logical - reserve)
    if requested > allowed:
        raise RuntimeError(
            f"Stage4.1R3 requests {requested} workers but only {logical} logical CPUs are visible; "
            f"reserve={reserve}, safe maximum={allowed}. No silent fallback is allowed."
        )
    memory = _available_memory_gb()
    configured = max(1, int(ctx.cfg["parallel"].get("n_workers", 128)))
    minimum_memory = float(ctx.cfg["parallel"].get("minimum_available_memory_gb", 72.0)) * (requested / configured)
    if math.isfinite(memory) and memory < minimum_memory:
        raise RuntimeError(f"Stage4.1R3 requires at least {minimum_memory:.1f} GiB available memory; {memory:.1f} GiB is visible")
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
        "controller_revision": CONTROLLER_REVISION,
        "prepared": True,
        "regression_complete": False,
        "ablation_complete": False,
        "selected_observer_variant": None,
        "selected_anti_windup_enabled": None,
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
        ctx.paths.run_dir, ctx.paths.regression, ctx.paths.ablation, ctx.paths.recovery, ctx.paths.structured,
        ctx.paths.noise, ctx.paths.history, ctx.paths.restart, ctx.paths.confirmation,
        ctx.paths.analysis, ctx.paths.variants, ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if str(old.get("controller_revision", "")) != CONTROLLER_REVISION:
            raise ValueError(
                "Existing run uses a different controller revision; create a fresh Stage4.1R3 run"
            )
        if Path(old["source_stage4_0_run"]).resolve() != ctx.source_stage40_run:
            raise ValueError("Existing Stage4.1R3 run points to a different Stage4.0 source")
        digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        if digest and digest != ctx.source_fingerprint["digest"]:
            raise ValueError("Stage4.0/Stage3.4 source content changed since this Stage4.1R3 run was prepared")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r3_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.source_train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.source_env_cfg)
    preflight = runtime_preflight(ctx)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
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
    payload["nominal_max_delta_a"] = float(ctx.source_env_cfg["current_slew_a_per_ms"]) * float(ctx.source_env_cfg["dt_ms"])
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
class LegacyNominalErrorStateObserver:
    """Stage4.1R2 tracking-error alpha-beta observer retained for ablation.

    It removes the time-varying nominal before filtering, so exact nominal
    motion is a zero-error invariant.  It does *not* account for the known
    response caused by the controller's own recent corrections, which is why
    it can lag during fast closed-loop reversals.
    """

    alpha: float
    beta: float
    alpha_ip: float
    max_abs_velocity_error: float
    position_error: np.ndarray | None = None
    velocity_error: np.ndarray | None = None
    ip_error: float | None = None
    last_index: int | None = None

    def update(
        self,
        measurement: np.ndarray,
        measurement_index: int,
        nominal_y: np.ndarray,
        dt_s: float,
    ) -> None:
        measurement = np.asarray(measurement, dtype=float).reshape(3)
        nominal_y = np.asarray(nominal_y, dtype=float)
        index = int(measurement_index)
        if not 0 <= index < len(nominal_y):
            raise IndexError(
                f"measurement index {index} outside nominal trajectory length {len(nominal_y)}"
            )
        error = measurement - nominal_y[index, :3]
        if self.position_error is None:
            self.position_error = error[:2].copy()
            self.velocity_error = np.zeros(2, dtype=float)
            self.ip_error = float(error[2])
            self.last_index = index
            return
        if self.last_index is not None and index <= self.last_index:
            return
        elapsed_steps = max(1, index - int(self.last_index))
        elapsed = elapsed_steps * float(dt_s)
        predicted_error = self.position_error + self.velocity_error * elapsed
        residual = error[:2] - predicted_error
        self.position_error = predicted_error + self.alpha * residual
        self.velocity_error = self.velocity_error + (self.beta / max(elapsed, 1e-12)) * residual
        self.velocity_error = np.clip(
            self.velocity_error, -self.max_abs_velocity_error, self.max_abs_velocity_error
        )
        self.ip_error = (1.0 - self.alpha_ip) * float(self.ip_error) + self.alpha_ip * float(error[2])
        self.last_index = index

    def predict_error_to(
        self, current_index: int, dt_s: float
    ) -> tuple[np.ndarray, np.ndarray, float]:
        if (
            self.position_error is None
            or self.velocity_error is None
            or self.ip_error is None
            or self.last_index is None
        ):
            raise RuntimeError("legacy nominal-error observer has not been initialized")
        ahead = max(0, int(current_index) - int(self.last_index)) * float(dt_s)
        return (
            self.position_error + self.velocity_error * ahead,
            self.velocity_error.copy(),
            float(self.ip_error),
        )


def _feature_rows_for_state(state_index: int) -> list[int]:
    """Rows [R,Z,vR,vZ,Ip] for a physical state index in the 175-row bundle."""
    index = int(state_index)
    if not 1 <= index <= 35:
        return []
    local = index - 1
    return [local, 35 + local, 70 + local, 105 + local, 140 + local]


def known_control_effect_physical(
    bundle: dict[str, Any],
    *,
    state_index: int,
    known_physical_delta_by_step: np.ndarray,
    measurement_scales: np.ndarray,
) -> np.ndarray:
    """Predict the measured tracking error caused by already-applied commands.

    ``known_physical_delta_by_step[j]`` is the controller-known physical
    3-mode deviation from the target-conditioned nominal at action step ``j``.
    Only columns strictly before ``state_index`` are causal for that state.
    The Stage3.4 Jacobian is normalized, so the result is converted back to
    physical [R,Z,vR,vZ,Ip] units before it is subtracted from measurements.
    """
    index = int(state_index)
    if index <= 0:
        return np.zeros(5, dtype=float)
    if index > 35:
        index = 35
    rows = _feature_rows_for_state(index)
    if not rows:
        return np.zeros(5, dtype=float)
    delta = np.asarray(known_physical_delta_by_step, dtype=float)
    if delta.shape != (35, 3):
        raise ValueError(f"known control delta must have shape (35,3), got {delta.shape}")
    past_steps = min(index, 35)
    columns = [step * 3 + mode for step in range(past_steps) for mode in range(3)]
    if not columns:
        return np.zeros(5, dtype=float)
    jacobian = np.asarray(bundle["jacobian_normalized"], dtype=float)
    normalized = jacobian[np.ix_(rows, columns)] @ delta[:past_steps].reshape(-1)
    scales = np.asarray(measurement_scales, dtype=float).reshape(5)
    effect = normalized * scales
    if not np.all(np.isfinite(effect)):
        raise ValueError("known control effect contains non-finite values")
    return effect


@dataclass
class ControlAwareResidualObserver:
    """Estimate only dynamics not explained by known controller corrections.

    The identified Stage3.4 Jacobian predicts the fast response caused by
    already-applied feedback commands.  An alpha-beta filter then tracks the
    slower residual (model mismatch, hidden state, noise, gain error, or an
    unannounced test disturbance).  The total estimate returned to MPC is:

        known Jacobian response + filtered residual.

    This avoids forcing a constant-velocity observer to rediscover acceleration
    that the controller itself just commanded.
    """

    alpha: float
    beta: float
    direct_velocity_blend: float
    alpha_ip: float
    max_abs_residual_velocity: float
    residual_position: np.ndarray | None = None
    residual_velocity: np.ndarray | None = None
    residual_ip: float | None = None
    last_index: int | None = None
    previous_measured_residual_position: np.ndarray | None = None

    def update(
        self,
        measurement: np.ndarray,
        measurement_index: int,
        nominal_y: np.ndarray,
        known_effect_physical_at_measurement: np.ndarray,
        dt_s: float,
    ) -> None:
        measurement = np.asarray(measurement, dtype=float).reshape(3)
        nominal_y = np.asarray(nominal_y, dtype=float)
        known = np.asarray(known_effect_physical_at_measurement, dtype=float).reshape(5)
        index = int(measurement_index)
        if not 0 <= index < len(nominal_y):
            raise IndexError(
                f"measurement index {index} outside nominal trajectory length {len(nominal_y)}"
            )
        total_error = measurement - nominal_y[index, :3]
        measured_residual_position = total_error[:2] - known[:2]
        measured_residual_ip = float(total_error[2] - known[4])
        if self.residual_position is None:
            self.residual_position = measured_residual_position.copy()
            self.residual_velocity = np.zeros(2, dtype=float)
            self.residual_ip = measured_residual_ip
            self.last_index = index
            self.previous_measured_residual_position = measured_residual_position.copy()
            return
        if self.last_index is not None and index <= self.last_index:
            return
        elapsed_steps = max(1, index - int(self.last_index))
        elapsed = elapsed_steps * float(dt_s)
        predicted = self.residual_position + self.residual_velocity * elapsed
        innovation = measured_residual_position - predicted
        alpha_beta_velocity = self.residual_velocity + (
            self.beta / max(elapsed, 1e-12)
        ) * innovation
        direct_velocity = (
            measured_residual_position - np.asarray(
                self.previous_measured_residual_position, dtype=float
            )
        ) / max(elapsed, 1e-12)
        blend = float(np.clip(self.direct_velocity_blend, 0.0, 1.0))
        velocity = (1.0 - blend) * alpha_beta_velocity + blend * direct_velocity
        self.residual_position = predicted + self.alpha * innovation
        self.residual_velocity = np.clip(
            velocity,
            -self.max_abs_residual_velocity,
            self.max_abs_residual_velocity,
        )
        self.residual_ip = (1.0 - self.alpha_ip) * float(self.residual_ip) + self.alpha_ip * measured_residual_ip
        self.last_index = index
        self.previous_measured_residual_position = measured_residual_position.copy()

    def predict_total_error_to(
        self,
        current_index: int,
        known_effect_physical_at_current: np.ndarray,
        dt_s: float,
    ) -> tuple[np.ndarray, np.ndarray, float, np.ndarray]:
        if (
            self.residual_position is None
            or self.residual_velocity is None
            or self.residual_ip is None
            or self.last_index is None
        ):
            raise RuntimeError("control-aware residual observer has not been initialized")
        known = np.asarray(known_effect_physical_at_current, dtype=float).reshape(5)
        ahead = max(0, int(current_index) - int(self.last_index)) * float(dt_s)
        residual_position = self.residual_position + self.residual_velocity * ahead
        total_position = known[:2] + residual_position
        total_velocity = known[2:4] + self.residual_velocity
        total_ip = float(known[4] + self.residual_ip)
        residual = np.asarray([
            residual_position[0], residual_position[1],
            self.residual_velocity[0], self.residual_velocity[1],
            self.residual_ip,
        ], dtype=float)
        return total_position, total_velocity, total_ip, residual


# Compatibility alias used by a few external diagnostics.
NominalErrorStateObserver = LegacyNominalErrorStateObserver
AlphaBetaObserver = LegacyNominalErrorStateObserver


def _sensor_path_is_clean(spec: dict[str, Any]) -> bool:
    noise = spec.get("observation_noise") or {}
    bias = spec.get("observation_bias") or {}
    noise_values = [
        float(noise.get("R_sigma_m", 0.0)),
        float(noise.get("Z_sigma_m", 0.0)),
        float(noise.get("Ip_sigma_A", 0.0)),
    ]
    bias_values = [
        float(bias.get("R_m", 0.0)),
        float(bias.get("Z_m", 0.0)),
        float(bias.get("Ip_A", 0.0)),
    ]
    return (
        int(spec.get("observation_delay_steps", 0)) == 0
        and max(map(abs, noise_values + bias_values), default=0.0) <= 0.0
    )


def legacy_measurement_error(
    observation_history: Sequence[np.ndarray],
    *,
    delayed_local_index: int,
    delayed_absolute_index: int,
    current_absolute_index: int,
    nominal_y: np.ndarray,
    nominal_velocity: np.ndarray,
    dt_s: float,
) -> np.ndarray:
    """Reproduce the Stage3.4 raw-measurement error path.

    With no noise and no delay this is bit-for-bit the same state/finite-
    difference construction used by the confirmed Stage3.4 controller.  For a
    delayed observation, the *error state* (not the absolute state) is propagated
    to the current phase.
    """
    y = np.asarray(observation_history[delayed_local_index], dtype=float).reshape(3)
    if delayed_local_index <= 0:
        measured_velocity = np.zeros(2, dtype=float)
    else:
        previous = np.asarray(observation_history[delayed_local_index - 1], dtype=float).reshape(3)
        measured_velocity = (y[:2] - previous[:2]) / max(float(dt_s), 1e-12)
    position_error = y[:2] - np.asarray(nominal_y[delayed_absolute_index, :2], dtype=float)
    velocity_error = measured_velocity - np.asarray(nominal_velocity[delayed_absolute_index, :2], dtype=float)
    ahead = max(0, int(current_absolute_index) - int(delayed_absolute_index)) * float(dt_s)
    position_error = position_error + velocity_error * ahead
    ip_error = float(y[2] - nominal_y[delayed_absolute_index, 2])
    return np.asarray([position_error[0], position_error[1], velocity_error[0], velocity_error[1], ip_error])

def _scaled_jacobian(bundle: dict[str, Any], model_scale: float) -> np.ndarray:
    return np.asarray(bundle["jacobian_normalized"], dtype=float) * float(model_scale)


def solve_delay_aware_physical_correction(
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
) -> dict[str, Any]:
    """Solve MPC corrections in the *nominal physical mode* coordinates.

    Stage4.1 multiplied Jacobian columns by a diagonal gain/slew estimate and
    optimized command-space corrections.  That approximation breaks when the
    3-mode command is decoded through the nonlinear 14-coil max-norm/current
    repair.  Revision v2 keeps the identified Jacobian in its native physical
    coefficient coordinates.  A separate physical-coil scheduler maps the
    desired coefficient sequence into actuator commands.
    """
    try:
        from scipy.optimize import lsq_linear
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage4.1R3 MPC") from exc
    current_step = int(current_step)
    delay = max(0, int(modeled_action_delay_steps))
    effect_step = min(current_step + delay, 35)
    if effect_step >= 35:
        return {
            "first_correction": np.zeros(3),
            "sequence_correction": np.zeros((0, 3)),
            "solver_success": True,
            "solver_status": 0,
            "solver_cost": 0.0,
            "solver_optimality": 0.0,
            "predicted_normalized_residual_rms": 0.0,
            "active_lower": 0,
            "active_upper": 0,
            "effect_step": effect_step,
            "fixed_pending_steps": delay,
        }
    jacobian = _scaled_jacobian(bundle, controller_model_scale)
    scales = np.asarray(bundle["output_scales"], dtype=float)
    rows = s34._future_feature_rows(current_step)
    projection = s34._measurement_bias_projection(ctx_stub, current_step, rows)
    integral_gain = np.asarray(ctx_stub.cfg["mpc"]["integral_measurement_gain"], dtype=float)
    effective_measurement = np.asarray(measurement_normalized, dtype=float) + integral_gain * np.asarray(
        integral_normalized, dtype=float
    )
    future_error = nominal_feature[np.asarray(rows)] / scales[np.asarray(rows)] + projection @ effective_measurement

    fixed_steps = list(range(current_step, min(effect_step, 35)))
    if fixed_steps:
        fixed_columns = [step * 3 + mode for step in fixed_steps for mode in range(3)]
        fixed_delta: list[float] = []
        for offset, step in enumerate(fixed_steps):
            if offset < len(modeled_pending_physical_coefficients):
                physical = np.asarray(modeled_pending_physical_coefficients[offset], dtype=float)
            else:
                physical = np.asarray(nominal_physical_coefficients[step], dtype=float)
            fixed_delta.extend((physical - nominal_physical_coefficients[step]).tolist())
        future_error = future_error + jacobian[np.ix_(rows, fixed_columns)] @ np.asarray(fixed_delta, dtype=float)

    free_steps = list(range(effect_step, 35))
    columns = [step * 3 + mode for step in free_steps for mode in range(3)]
    a = jacobian[np.ix_(rows, columns)]
    weights = s34._state_weight_vector(ctx_stub, rows, current_step)
    sqrt_w = np.sqrt(np.maximum(weights, 0.0))
    augmented_a: list[np.ndarray] = [sqrt_w[:, None] * a]
    augmented_b: list[np.ndarray] = [-sqrt_w * future_error]

    nominal_future = np.asarray(nominal_physical_coefficients, dtype=float)[free_steps].reshape(-1)
    lower_mode = np.asarray(ctx_stub.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx_stub.cfg["trajectory"]["coefficient_upper"], dtype=float)
    feedback_limit = np.asarray(ctx_stub.cfg["mpc"]["per_step_feedback_limit_by_mode"], dtype=float) * float(
        controller_scale
    )
    lower = np.maximum(
        np.tile(lower_mode, len(free_steps)) - nominal_future,
        -np.tile(feedback_limit, len(free_steps)),
    )
    upper = np.minimum(
        np.tile(upper_mode, len(free_steps)) - nominal_future,
        np.tile(feedback_limit, len(free_steps)),
    )
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
        np.vstack(augmented_a),
        np.concatenate(augmented_b),
        bounds=(lower, upper),
        method="trf",
        tol=float(ctx_stub.cfg["mpc"].get("solver_tolerance", 1e-8)),
        max_iter=int(ctx_stub.cfg["mpc"].get("solver_max_iterations", 300)),
        lsmr_tol="auto",
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


@dataclass
class PhysicalCoilScheduler:
    modes_tsc: np.ndarray
    nominal_max_delta_a: float
    command_max_delta_a: float
    min_current: np.ndarray
    max_current: np.ndarray
    lower_mode: np.ndarray
    upper_mode: np.ndarray
    regularization: float = 1e-4

    def _action_from_effective(self, effective_coefficients: np.ndarray, currents: np.ndarray, max_delta_a: float) -> np.ndarray:
        desired = np.asarray(effective_coefficients, dtype=float) @ np.asarray(self.modes_tsc, dtype=float).T
        max_abs = float(np.max(np.abs(desired)))
        if max_abs > 1.0:
            desired = desired / max_abs
        delta = desired * float(max_delta_a)
        scale = 1.0
        currents = np.asarray(currents, dtype=float)
        for coil in range(14):
            if delta[coil] > 0.0:
                scale = min(scale, max(0.0, (self.max_current[coil] - currents[coil]) / max(delta[coil], 1e-30)))
            elif delta[coil] < 0.0:
                scale = min(scale, max(0.0, (self.min_current[coil] - currents[coil]) / min(delta[coil], -1e-30)))
        return np.asarray(desired * float(np.clip(scale, 0.0, 1.0)), dtype=float)

    def target_delta_a(self, desired_physical_coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
        return self._action_from_effective(desired_physical_coefficients, currents, self.nominal_max_delta_a) * self.nominal_max_delta_a

    def predicted_delta_a(
        self,
        command_coefficients: np.ndarray,
        currents: np.ndarray,
        gain_estimate: np.ndarray,
        slew_estimate: float,
    ) -> np.ndarray:
        effective = np.asarray(gain_estimate, dtype=float) * np.asarray(command_coefficients, dtype=float)
        max_delta = self.nominal_max_delta_a * float(slew_estimate)
        return self._action_from_effective(effective, currents, max_delta) * max_delta

    def equivalent_physical_coefficients(
        self,
        command_coefficients: np.ndarray,
        gain_estimate: np.ndarray,
        slew_estimate: float,
    ) -> np.ndarray:
        # Used only for delay-queue prediction.  The physical-coil inverse below
        # handles the nonlinear decoder for the command actually issued.
        return np.asarray(gain_estimate, dtype=float) * float(slew_estimate) * np.asarray(
            command_coefficients, dtype=float
        )

    def solve_command(
        self,
        desired_physical_coefficients: np.ndarray,
        currents: np.ndarray,
        gain_estimate: np.ndarray,
        slew_estimate: float,
        *,
        enabled: bool,
    ) -> dict[str, Any]:
        desired_physical = np.asarray(desired_physical_coefficients, dtype=float).reshape(3)
        gain = np.clip(np.asarray(gain_estimate, dtype=float).reshape(3), 1e-6, None)
        slew = max(float(slew_estimate), 1e-6)
        target_delta = self.target_delta_a(desired_physical, currents)
        if not enabled:
            command = np.clip(desired_physical, self.lower_mode, self.upper_mode)
            predicted = self.predicted_delta_a(command, currents, np.ones(3), 1.0)
            mismatch = predicted - target_delta
            return {
                "command": command,
                "target_delta_a": target_delta,
                "predicted_delta_a": predicted,
                "mismatch_rms_a": float(np.sqrt(np.mean(mismatch**2))),
                "mismatch_max_abs_a": float(np.max(np.abs(mismatch))),
                "solver_success": True,
                "solver_status": 0,
                "identity_shortcut": True,
            }
        if np.allclose(gain, 1.0, atol=1e-14) and math.isclose(slew, 1.0, abs_tol=1e-14):
            command = np.clip(desired_physical, self.lower_mode, self.upper_mode)
            predicted = self.predicted_delta_a(command, currents, gain, slew)
            mismatch = predicted - target_delta
            return {
                "command": command,
                "target_delta_a": target_delta,
                "predicted_delta_a": predicted,
                "mismatch_rms_a": float(np.sqrt(np.mean(mismatch**2))),
                "mismatch_max_abs_a": float(np.max(np.abs(mismatch))),
                "solver_success": True,
                "solver_status": 0,
                "identity_shortcut": True,
            }
        try:
            from scipy.optimize import least_squares
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("scipy is required for physical-coil scheduling") from exc
        initial = np.clip(desired_physical / (gain * slew), self.lower_mode, self.upper_mode)
        scale_a = max(self.nominal_max_delta_a, 1.0)
        reg = math.sqrt(max(self.regularization, 0.0))

        def residual(command: np.ndarray) -> np.ndarray:
            predicted = self.predicted_delta_a(command, currents, gain, slew)
            physical_residual = (predicted - target_delta) / scale_a
            if reg <= 0.0:
                return physical_residual
            return np.concatenate([physical_residual, reg * (command - initial)])

        result = least_squares(
            residual,
            initial,
            bounds=(self.lower_mode, self.upper_mode),
            xtol=1e-10,
            ftol=1e-10,
            gtol=1e-10,
            max_nfev=100,
        )
        command = np.clip(np.asarray(result.x, dtype=float), self.lower_mode, self.upper_mode)
        predicted = self.predicted_delta_a(command, currents, gain, slew)
        mismatch = predicted - target_delta
        return {
            "command": command,
            "target_delta_a": target_delta,
            "predicted_delta_a": predicted,
            "mismatch_rms_a": float(np.sqrt(np.mean(mismatch**2))),
            "mismatch_max_abs_a": float(np.max(np.abs(mismatch))),
            "solver_success": bool(result.success),
            "solver_status": int(result.status),
            "identity_shortcut": False,
            "nfev": int(result.nfev),
        }



@dataclass
class DelaySlewHypothesisBank:
    """Online command-response hypothesis bank for delay and slew scale.

    The estimator uses only quantities that are measurable or known by a real
    controller: issued three-mode commands, measured 14-coil current changes,
    and the current coil state.  It never reads the simulated plant's private
    delay queue.  Candidate pairs are scored in physical 14-coil current-
    increment space through the same nonlinear decoder/current-room model used
    by the controller scheduler.

    This is a finite-bank POC, not a deployment-qualified adaptive estimator.
    """

    scheduler: PhysicalCoilScheduler
    delay_candidates: tuple[int, ...] = (0, 1, 2)
    slew_candidates: tuple[float, ...] = (0.9, 1.0, 1.1)
    score_decay: float = 0.92
    minimum_observations: int = 3
    switch_hysteresis_fraction: float = 0.05
    initial_delay_steps: int = 0
    initial_slew_scale: float = 1.0
    selected_delay_steps: int = 0
    selected_slew_scale: float = 1.0
    observations: int = 0
    score_sums: dict[tuple[int, float], float] | None = None
    score_weights: dict[tuple[int, float], float] | None = None
    transitions: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        delays = tuple(sorted({int(value) for value in self.delay_candidates}))
        slews = tuple(sorted({float(value) for value in self.slew_candidates}))
        if not delays or min(delays) < 0:
            raise ValueError("delay_candidates must be non-empty and non-negative")
        if not slews or min(slews) <= 0.0:
            raise ValueError("slew_candidates must be positive")
        self.delay_candidates = delays
        self.slew_candidates = slews
        self.selected_delay_steps = int(self.initial_delay_steps)
        self.selected_slew_scale = float(self.initial_slew_scale)
        if self.selected_delay_steps not in delays:
            raise ValueError("initial_delay_steps is outside the candidate bank")
        if not any(math.isclose(self.selected_slew_scale, value, abs_tol=1e-12) for value in slews):
            raise ValueError("initial_slew_scale is outside the candidate bank")
        self.score_sums = {(delay, slew): 0.0 for delay in delays for slew in slews}
        self.score_weights = {(delay, slew): 0.0 for delay in delays for slew in slews}
        self.transitions = []

    def _command_for_hypothesis(
        self,
        *,
        step: int,
        delay_steps: int,
        issued_commands: Sequence[np.ndarray],
        nominal_commands: np.ndarray,
    ) -> np.ndarray:
        issue_index = int(step) - int(delay_steps)
        if issue_index < 0:
            # The real plant queue is primed with the nominal command that is
            # supposed to act at this physical step.
            return np.asarray(nominal_commands[int(step)], dtype=float)
        if issue_index >= len(issued_commands):
            raise IndexError(
                f"issued command history is missing step {issue_index}; "
                f"available={len(issued_commands)}"
            )
        return np.asarray(issued_commands[issue_index], dtype=float)

    def update(
        self,
        *,
        step: int,
        observed_delta_a: np.ndarray,
        currents_before_a: np.ndarray,
        issued_commands: Sequence[np.ndarray],
        nominal_commands: np.ndarray,
        gain_for_prediction: np.ndarray | None = None,
    ) -> dict[str, Any]:
        observed = np.asarray(observed_delta_a, dtype=float).reshape(14)
        currents = np.asarray(currents_before_a, dtype=float).reshape(14)
        nominal = np.asarray(nominal_commands, dtype=float)
        if nominal.ndim != 2 or nominal.shape[1] != 3:
            raise ValueError(f"nominal_commands must have shape (N,3), got {nominal.shape}")
        gain = (
            np.ones(3, dtype=float)
            if gain_for_prediction is None
            else np.asarray(gain_for_prediction, dtype=float).reshape(3)
        )
        scale = max(float(self.scheduler.nominal_max_delta_a), 1.0)
        decay = float(np.clip(self.score_decay, 0.0, 1.0))
        residuals: dict[tuple[int, float], float] = {}
        for delay in self.delay_candidates:
            command = self._command_for_hypothesis(
                step=int(step),
                delay_steps=int(delay),
                issued_commands=issued_commands,
                nominal_commands=nominal,
            )
            for slew in self.slew_candidates:
                predicted = self.scheduler.predicted_delta_a(
                    command,
                    currents,
                    gain,
                    float(slew),
                )
                residual = float(np.sqrt(np.mean(((predicted - observed) / scale) ** 2)))
                key = (int(delay), float(slew))
                self.score_sums[key] = decay * float(self.score_sums[key]) + residual * residual
                self.score_weights[key] = decay * float(self.score_weights[key]) + 1.0
                residuals[key] = residual
        self.observations += 1
        normalized = {
            key: float(self.score_sums[key]) / max(float(self.score_weights[key]), 1e-12)
            for key in self.score_sums
        }
        old = (int(self.selected_delay_steps), float(self.selected_slew_scale))
        best = min(normalized, key=lambda key: (normalized[key], key[0], abs(key[1] - 1.0)))
        if self.observations >= int(self.minimum_observations):
            old_score = normalized.get(old, math.inf)
            best_score = normalized[best]
            hysteresis = float(np.clip(self.switch_hysteresis_fraction, 0.0, 0.95))
            if best == old or best_score <= old_score * (1.0 - hysteresis):
                self.selected_delay_steps = int(best[0])
                self.selected_slew_scale = float(best[1])
        new = (int(self.selected_delay_steps), float(self.selected_slew_scale))
        if new != old:
            self.transitions.append(
                {
                    "step": int(step),
                    "old_delay_steps": int(old[0]),
                    "old_slew_scale": float(old[1]),
                    "new_delay_steps": int(new[0]),
                    "new_slew_scale": float(new[1]),
                    "observations": int(self.observations),
                }
            )
        return {
            "selected_delay_steps": int(self.selected_delay_steps),
            "selected_slew_scale": float(self.selected_slew_scale),
            "instantaneous_residuals": {
                f"d{delay}_s{slew:.3f}": float(value)
                for (delay, slew), value in sorted(residuals.items())
            },
            "normalized_scores": {
                f"d{delay}_s{slew:.3f}": float(value)
                for (delay, slew), value in sorted(normalized.items())
            },
        }

    def pending_desired_physical(
        self,
        *,
        current_step: int,
        issued_items: Sequence[dict[str, Any]],
        nominal_physical: np.ndarray,
    ) -> list[np.ndarray]:
        delay = int(self.selected_delay_steps)
        nominal = np.asarray(nominal_physical, dtype=float)
        pending: list[np.ndarray] = []
        for offset in range(delay):
            issue_index = int(current_step) + offset - delay
            if issue_index < 0:
                effect_step = min(int(current_step) + offset, len(nominal) - 1)
                pending.append(np.asarray(nominal[effect_step], dtype=float).copy())
            elif issue_index < len(issued_items):
                pending.append(
                    np.asarray(issued_items[issue_index]["desired_physical"], dtype=float).copy()
                )
            else:
                effect_step = min(int(current_step) + offset, len(nominal) - 1)
                pending.append(np.asarray(nominal[effect_step], dtype=float).copy())
        return pending

    def summary(self) -> dict[str, Any]:
        normalized = {
            key: float(self.score_sums[key]) / max(float(self.score_weights[key]), 1e-12)
            for key in self.score_sums
        }
        return {
            "observations": int(self.observations),
            "selected_delay_steps": int(self.selected_delay_steps),
            "selected_slew_scale": float(self.selected_slew_scale),
            "normalized_scores": {
                f"d{delay}_s{slew:.3f}": float(value)
                for (delay, slew), value in sorted(normalized.items())
            },
            "transitions": copy.deepcopy(self.transitions),
        }

# Backward-compatible wrapper for unit tests and downstream imports.  It now
# solves in physical coordinates and ignores the deprecated diagonal gain
# approximation.
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
    pending_physical = [
        np.asarray(estimated_effective_gain_by_mode, dtype=float) * np.asarray(command, dtype=float)
        for command in modeled_pending_commands
    ]
    return solve_delay_aware_physical_correction(
        ctx_stub,
        bundle,
        current_step=current_step,
        modeled_action_delay_steps=modeled_action_delay_steps,
        modeled_pending_physical_coefficients=pending_physical,
        nominal_physical_coefficients=nominal_physical_coefficients,
        nominal_feature=nominal_feature,
        measurement_normalized=measurement_normalized,
        integral_normalized=integral_normalized,
        previous_correction=previous_correction,
        controller_scale=controller_scale,
        controller_model_scale=controller_model_scale,
    )

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
        self.nominal_max_delta_a = float(payload.get("nominal_max_delta_a", self.max_delta_a))
        self.min_current = np.asarray(payload["min_current_tsc"], dtype=float)
        self.max_current = np.asarray(payload["max_current_tsc"], dtype=float)
        self.variant_id = str(payload.get("variant_id", "base"))
        self.actual_slew_scale = float(payload.get("slew_scale", 1.0))
        self.library = library
        self.bundle = bundle
        self.stub = SimpleNamespace(cfg=self.cfg, env_cfg=self.env_cfg)
        self.env = make_tsc_rzip_env(copy.deepcopy(self.train_cfg), worker_id=worker_id, seed=None)
        self.lower_mode = np.asarray(self.cfg["trajectory"]["coefficient_lower"], dtype=float)
        self.upper_mode = np.asarray(self.cfg["trajectory"]["coefficient_upper"], dtype=float)
        scheduler_cfg = self.robust_cfg["controller_upgrade"]["gain_slew_scheduling"]
        self.scheduler = PhysicalCoilScheduler(
            modes_tsc=self.modes_tsc,
            nominal_max_delta_a=self.nominal_max_delta_a,
            command_max_delta_a=self.max_delta_a,
            min_current=self.min_current,
            max_current=self.max_current,
            lower_mode=self.lower_mode,
            upper_mode=self.upper_mode,
            regularization=float(scheduler_cfg.get("physical_inverse_regularization", 1e-4)),
        )

    def _mode_action(self, effective_coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
        return np.asarray(
            self.scheduler._action_from_effective(effective_coefficients, currents, self.max_delta_a),
            dtype=np.float32,
        )

    def _flag(self, spec: dict[str, Any], group: str, override_key: str) -> bool:
        if override_key in spec:
            return bool(spec[override_key])
        return bool(self.robust_cfg["controller_upgrade"][group].get("enabled", True))

    def _nominal_command_plan(
        self,
        nominal_physical: np.ndarray,
        initial_currents: np.ndarray,
        gain_estimate: np.ndarray,
        slew_estimate: float,
        scheduling_enabled: bool,
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        commands = np.zeros_like(nominal_physical)
        diagnostics: list[dict[str, Any]] = []
        predicted_currents = np.asarray(initial_currents, dtype=float).copy()
        for step in range(35):
            scheduled = self.scheduler.solve_command(
                nominal_physical[step], predicted_currents, gain_estimate, slew_estimate,
                enabled=scheduling_enabled,
            )
            command = np.asarray(scheduled["command"], dtype=float)
            commands[step] = command
            predicted_currents = predicted_currents + np.asarray(scheduled["predicted_delta_a"], dtype=float)
            diagnostics.append({
                "step": step,
                "mismatch_rms_a": float(scheduled["mismatch_rms_a"]),
                "mismatch_max_abs_a": float(scheduled["mismatch_max_abs_a"]),
                "identity_shortcut": bool(scheduled.get("identity_shortcut", False)),
                "solver_success": bool(scheduled.get("solver_success", True)),
            })
        return commands, diagnostics

    def _observer_variant(self, spec: dict[str, Any], observer_enabled: bool) -> str:
        if not observer_enabled:
            return "legacy_raw"
        return str(spec.get("observer_variant", "control_aware_residual"))

    def _integral_candidate(
        self,
        previous: np.ndarray,
        measurement: np.ndarray,
        *,
        reference_step: int,
        anti_windup_enabled: bool,
    ) -> np.ndarray:
        if not anti_windup_enabled:
            decay = float(self.cfg["mpc"].get("integral_decay", 0.92))
            return decay * np.asarray(previous, dtype=float) + np.asarray(measurement, dtype=float)
        aw = self.robust_cfg["controller_upgrade"]["anti_windup"]
        hold_start = int(aw.get("hold_start_step", 14))
        decay = float(
            aw.get("hold_integral_decay", 0.82)
            if int(reference_step) >= hold_start
            else aw.get("normal_integral_decay", 0.92)
        )
        candidate = decay * np.asarray(previous, dtype=float) + np.asarray(measurement, dtype=float)
        limits = np.asarray(aw.get("integral_abs_limit", [2.5, 2.5, 1.5, 1.5, 2.5]), dtype=float)
        return np.clip(candidate, -limits, limits)

    def _correction_saturated(
        self,
        correction: np.ndarray,
        previous_correction: np.ndarray,
        solve: dict[str, Any],
        controller_scale: float,
    ) -> bool:
        aw = self.robust_cfg["controller_upgrade"]["anti_windup"]
        fraction = float(aw.get("saturation_fraction", 0.98))
        feedback_limit = np.asarray(
            self.cfg["mpc"]["per_step_feedback_limit_by_mode"], dtype=float
        ) * float(controller_scale)
        rate_limit = np.asarray(
            self.cfg["mpc"]["per_step_correction_rate_limit_by_mode"], dtype=float
        )
        correction = np.asarray(correction, dtype=float)
        previous_correction = np.asarray(previous_correction, dtype=float)
        at_feedback_bound = bool(
            np.any(np.abs(correction) >= fraction * np.maximum(feedback_limit, 1e-12))
        )
        at_rate_bound = bool(
            np.any(
                np.abs(correction - previous_correction)
                >= fraction * np.maximum(rate_limit, 1e-12)
            )
        )
        solver_bound = bool(
            int(solve.get("active_lower", 0)) > 0 or int(solve.get("active_upper", 0)) > 0
        )
        return bool(
            at_feedback_bound
            or (
                bool(aw.get("freeze_on_first_correction_rate_limit", True))
                and at_rate_bound
            )
            or (
                bool(aw.get("freeze_on_solver_bound_activity", True))
                and solver_bound
            )
        )

    def _anti_windup_finalize(
        self,
        previous: np.ndarray,
        candidate: np.ndarray,
        *,
        saturated: bool,
        anti_windup_enabled: bool,
    ) -> np.ndarray:
        if not anti_windup_enabled or not saturated:
            return np.asarray(candidate, dtype=float)
        aw = self.robust_cfg["controller_upgrade"]["anti_windup"]
        decay = float(aw.get("saturated_integral_decay", 0.70))
        limits = np.asarray(aw.get("integral_abs_limit", [2.5, 2.5, 1.5, 1.5, 2.5]), dtype=float)
        return np.clip(decay * np.asarray(previous, dtype=float), -limits, limits)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        trajectory: list[dict[str, Any]] = []
        prelude_trajectory: list[dict[str, Any]] = []
        control_trace: list[dict[str, Any]] = []
        failure_reason = ""
        try:
            offset = np.asarray([
                spec.get("target_R_offset_m", 0.0),
                spec.get("target_Z_offset_m", 0.0),
                spec.get("target_Ip_offset_A", 0.0),
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

            observer_enabled = self._flag(spec, "observer", "observer_enabled")
            delay_aware_enabled = self._flag(spec, "delay_aware", "delay_aware_enabled")
            scheduling_enabled = self._flag(
                spec, "gain_slew_scheduling", "gain_slew_scheduling_enabled"
            )
            phase_aware_enabled = self._flag(
                spec, "phase_aware_reference", "phase_aware_reference_enabled"
            )
            observer_variant = self._observer_variant(spec, observer_enabled)
            anti_windup_cfg = self.robust_cfg["controller_upgrade"]["anti_windup"]
            anti_windup_requested = bool(
                spec.get("anti_windup_enabled", anti_windup_cfg.get("enabled", True))
            )
            anti_windup_mode = str(spec.get("anti_windup_mode", "explicit"))
            conditional_aw_use_actual = bool(
                spec.get("conditional_anti_windup_use_actual_actuator_state", True)
            )
            clean_sensor_path = _sensor_path_is_clean(spec)
            clean_bypass = bool(
                self.robust_cfg["controller_upgrade"]["observer"].get(
                    "clean_measurement_bypass", True
                )
            )
            force_aw_in_clean = bool(spec.get("force_anti_windup_in_clean", False))
            if clean_sensor_path and clean_bypass and not force_aw_in_clean and not bool(
                anti_windup_cfg.get("apply_in_clean_measurement_bypass", False)
            ):
                anti_windup_requested = False

            actual_gain = np.asarray(spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]), dtype=float)
            gain_estimate = np.asarray(spec.get("controller_gain_estimate_by_mode", actual_gain), dtype=float)
            slew_estimate = float(spec.get("controller_slew_scale_estimate", self.actual_slew_scale))
            schedule_cfg = self.robust_cfg["controller_upgrade"]["gain_slew_scheduling"]
            gain_estimate = np.clip(
                gain_estimate,
                float(schedule_cfg.get("minimum_effective_scale", 0.70)),
                float(schedule_cfg.get("maximum_effective_scale", 1.30)),
            )
            slew_estimate = float(np.clip(
                slew_estimate,
                float(schedule_cfg.get("minimum_effective_scale", 0.70)),
                float(schedule_cfg.get("maximum_effective_scale", 1.30)),
            ))
            def conditional_anti_windup_active(
                current_slew_estimate: float,
                current_gain_estimate: np.ndarray,
            ) -> bool:
                if not anti_windup_requested:
                    return False
                if anti_windup_mode != "conditional_weak_actuator":
                    return True
                slew_threshold = float(
                    anti_windup_cfg.get("conditional_slew_scale_threshold", 0.98)
                )
                gain_threshold = float(
                    anti_windup_cfg.get("conditional_gain_scale_threshold", 0.98)
                )
                estimated_weak = bool(
                    float(current_slew_estimate) < slew_threshold
                    or float(np.min(np.asarray(current_gain_estimate, dtype=float)))
                    < gain_threshold
                )
                actual_weak = bool(
                    conditional_aw_use_actual
                    and (
                        self.actual_slew_scale < slew_threshold
                        or float(np.min(actual_gain)) < gain_threshold
                    )
                )
                return bool(estimated_weak or actual_weak)

            controller_scale = float(spec.get("controller_scale", 0.0))
            actual_delay = max(0, int(spec.get("action_delay_steps", 0)))
            requested_modeled_delay = max(
                0, int(spec.get("controller_action_delay_steps", actual_delay))
            )
            maximum_delay = int(
                self.robust_cfg["controller_upgrade"]["delay_aware"].get(
                    "maximum_modeled_action_delay_steps", 2
                )
            )
            modeled_delay = min(requested_modeled_delay, maximum_delay) if delay_aware_enabled else 0
            prime_queue = bool(spec.get(
                "prime_action_queue_with_nominal",
                self.robust_cfg["controller_upgrade"]["delay_aware"].get(
                    "prime_action_queue_with_nominal", True
                ),
            ))
            estimator_spec = copy.deepcopy(spec.get("adaptive_delay_slew_estimator") or {})
            estimator_enabled = bool(estimator_spec.get("enabled", False))
            measured_known_effect = bool(
                spec.get("known_control_effect_from_measured_current_increment", False)
            )
            estimator: DelaySlewHypothesisBank | None = None

            self.env.reset()
            initial_currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
            nominal_command_plan, nominal_schedule_diagnostics = self._nominal_command_plan(
                nominal_physical,
                initial_currents,
                gain_estimate,
                slew_estimate,
                scheduling_enabled,
            )
            if estimator_enabled:
                estimator = DelaySlewHypothesisBank(
                    scheduler=self.scheduler,
                    delay_candidates=tuple(
                        int(value)
                        for value in estimator_spec.get("delay_candidates", [0, 1, 2])
                    ),
                    slew_candidates=tuple(
                        float(value)
                        for value in estimator_spec.get("slew_candidates", [0.9, 1.0, 1.1])
                    ),
                    score_decay=float(estimator_spec.get("score_decay", 0.92)),
                    minimum_observations=int(
                        estimator_spec.get("minimum_observations", 3)
                    ),
                    switch_hysteresis_fraction=float(
                        estimator_spec.get("switch_hysteresis_fraction", 0.05)
                    ),
                    initial_delay_steps=int(
                        estimator_spec.get("initial_delay_steps", modeled_delay)
                    ),
                    initial_slew_scale=float(
                        estimator_spec.get("initial_slew_scale", slew_estimate)
                    ),
                )
                modeled_delay = int(estimator.selected_delay_steps)
                slew_estimate = float(estimator.selected_slew_scale)

            command_queue: list[dict[str, np.ndarray]] = []
            issued_items_history: list[dict[str, np.ndarray]] = []
            issued_command_history: list[np.ndarray] = []
            for index in range(actual_delay):
                if prime_queue:
                    command_queue.append({
                        "command": nominal_command_plan[index].copy(),
                        "desired_physical": nominal_physical[index].copy(),
                    })
                else:
                    command_queue.append({
                        "command": np.zeros(3, dtype=float),
                        "desired_physical": np.zeros(3, dtype=float),
                    })

            known_physical_delta_by_step = np.zeros((35, 3), dtype=float)
            zero_action = np.zeros(14, dtype=np.float32)
            prelude_trajectory.append(base._state_record(self.env, 0, zero_action))
            prelude_deltas = spec.get("prelude_mode_deltas") or []
            env_phase_offset = len(prelude_deltas)
            actuator_bias = np.asarray(
                spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]), dtype=float
            )
            for prelude_step, delta_physical in enumerate(prelude_deltas):
                desired_physical = np.clip(
                    nominal_physical[prelude_step] + np.asarray(delta_physical, dtype=float),
                    self.lower_mode,
                    self.upper_mode,
                )
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                scheduled = self.scheduler.solve_command(
                    desired_physical,
                    currents,
                    gain_estimate,
                    slew_estimate,
                    enabled=scheduling_enabled,
                )
                command = np.asarray(scheduled["command"], dtype=float)
                effective = actual_gain * command + actuator_bias
                action = self._mode_action(effective, currents)
                _, _, terminated, truncated, info = self.env.step(action)
                prelude_trajectory.append(base._state_record(self.env, prelude_step + 1, action))
                # The controller knows the intended physical deviation.  Any
                # unmodelled plant gain/bias remains in the residual observer.
                known_physical_delta_by_step[prelude_step] = (
                    desired_physical - nominal_physical[prelude_step]
                )
                if terminated:
                    failure_reason = str(info.get("failure_reason", "prelude terminated"))
                    break
                if truncated:
                    failure_reason = "environment truncated during prelude"
                    break
            if failure_reason:
                raise RuntimeError(failure_reason)

            trajectory = [copy.deepcopy(row) for row in prelude_trajectory]
            reference_phase_offset = env_phase_offset if phase_aware_enabled else 0
            phase_reference_index = min(reference_phase_offset, 35)
            phase_start_state = np.asarray([
                trajectory[-1]["R"], trajectory[-1]["Z"], trajectory[-1]["Ip"]
            ], dtype=float)
            phase_start_reference = nominal_y[phase_reference_index]
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
                noise_cfg.get("R_sigma_m", 0.0),
                noise_cfg.get("Z_sigma_m", 0.0),
                noise_cfg.get("Ip_sigma_A", 0.0),
            ], dtype=float)
            bias_cfg = spec.get("observation_bias") or {}
            bias = np.asarray([
                bias_cfg.get("R_m", 0.0),
                bias_cfg.get("Z_m", 0.0),
                bias_cfg.get("Ip_A", 0.0),
            ], dtype=float)
            observation_delay = max(0, int(spec.get("observation_delay_steps", 0)))
            measurement_records: list[tuple[int, np.ndarray]] = []
            dt_s = float(self.env_cfg["dt_ms"]) / 1000.0
            observer_cfg = self.robust_cfg["controller_upgrade"]["observer"]
            legacy_observer = LegacyNominalErrorStateObserver(
                alpha=float(observer_cfg.get("r2_diagnostic_alpha_position", 0.72)),
                beta=float(observer_cfg.get("r2_diagnostic_beta_velocity", 0.16)),
                alpha_ip=float(observer_cfg.get("r2_diagnostic_alpha_ip", 0.45)),
                max_abs_velocity_error=float(
                    observer_cfg.get("maximum_abs_velocity_m_per_s", 2.0)
                ),
            )
            residual_observer = ControlAwareResidualObserver(
                alpha=float(observer_cfg.get("alpha_position", 0.68)),
                beta=float(observer_cfg.get("beta_velocity", 0.28)),
                direct_velocity_blend=float(
                    observer_cfg.get("direct_residual_velocity_blend", 0.20)
                ),
                alpha_ip=float(observer_cfg.get("alpha_ip", 0.40)),
                max_abs_residual_velocity=float(
                    observer_cfg.get("maximum_abs_residual_velocity_m_per_s", 1.0)
                ),
            )
            if observer_enabled and env_phase_offset:
                for env_index, row in enumerate(prelude_trajectory):
                    ref_index = (
                        env_index
                        if phase_aware_enabled
                        else max(0, env_index - env_phase_offset)
                    )
                    measurement0 = np.asarray(
                        [row["R"], row["Z"], row["Ip"]], dtype=float
                    )
                    if observer_variant == "r2_error_alpha_beta":
                        legacy_observer.update(measurement0, ref_index, nominal_y, dt_s)
                    elif observer_variant == "control_aware_residual":
                        known0 = known_control_effect_physical(
                            self.bundle,
                            state_index=ref_index,
                            known_physical_delta_by_step=known_physical_delta_by_step,
                            measurement_scales=measurement_scales,
                        )
                        residual_observer.update(
                            measurement0, ref_index, nominal_y, known0, dt_s
                        )

            integral = np.zeros(5, dtype=float)
            previous_correction = np.zeros(3, dtype=float)
            model_scale = float(spec.get("controller_model_scale", 1.0))
            disturbance = spec.get("disturbance") or None

            for env_step in range(env_phase_offset, 35):
                reference_step = env_step if phase_aware_enabled else env_step - env_phase_offset
                reference_step = int(np.clip(reference_step, 0, 34))
                if estimator is not None:
                    modeled_delay = int(estimator.selected_delay_steps)
                    slew_estimate = float(estimator.selected_slew_scale)
                anti_windup_active = conditional_anti_windup_active(
                    slew_estimate, gain_estimate
                )
                state = self.env.last_state
                current_true = np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)
                measured_now = current_true + bias + rng.normal(0.0, noise_sigma)
                measurement_records.append((reference_step, measured_now))
                delayed_record_index = max(
                    0, len(measurement_records) - 1 - observation_delay
                )
                delayed_reference_step, delayed_measurement = measurement_records[
                    delayed_record_index
                ]
                history_values = [row[1] for row in measurement_records]
                measurement_source = "legacy_raw"
                known_effect_current = np.zeros(5, dtype=float)
                known_effect_delayed = np.zeros(5, dtype=float)
                observer_residual = np.zeros(5, dtype=float)

                if (
                    not observer_enabled
                    or observer_variant == "legacy_raw"
                    or (
                        observer_variant == "control_aware_residual"
                        and clean_sensor_path
                        and clean_bypass
                    )
                ):
                    measurement_physical = legacy_measurement_error(
                        history_values,
                        delayed_local_index=delayed_record_index,
                        delayed_absolute_index=delayed_reference_step,
                        current_absolute_index=reference_step,
                        nominal_y=nominal_y,
                        nominal_velocity=nominal_velocity,
                        dt_s=dt_s,
                    )
                    measurement_source = (
                        "clean_direct_bypass"
                        if observer_variant == "control_aware_residual" and clean_sensor_path
                        else "legacy_raw"
                    )
                elif observer_variant == "r2_error_alpha_beta":
                    legacy_observer.update(
                        delayed_measurement,
                        delayed_reference_step,
                        nominal_y,
                        dt_s,
                    )
                    error_position, error_velocity, error_ip = legacy_observer.predict_error_to(
                        reference_step, dt_s
                    )
                    measurement_physical = np.asarray([
                        error_position[0], error_position[1],
                        error_velocity[0], error_velocity[1], error_ip,
                    ], dtype=float)
                    measurement_source = "r2_error_alpha_beta"
                elif observer_variant == "control_aware_residual":
                    known_effect_delayed = known_control_effect_physical(
                        self.bundle,
                        state_index=delayed_reference_step,
                        known_physical_delta_by_step=known_physical_delta_by_step,
                        measurement_scales=measurement_scales,
                    )
                    residual_observer.update(
                        delayed_measurement,
                        delayed_reference_step,
                        nominal_y,
                        known_effect_delayed,
                        dt_s,
                    )
                    known_effect_current = known_control_effect_physical(
                        self.bundle,
                        state_index=reference_step,
                        known_physical_delta_by_step=known_physical_delta_by_step,
                        measurement_scales=measurement_scales,
                    )
                    error_position, error_velocity, error_ip, observer_residual = (
                        residual_observer.predict_total_error_to(
                            reference_step, known_effect_current, dt_s
                        )
                    )
                    measurement_physical = np.asarray([
                        error_position[0], error_position[1],
                        error_velocity[0], error_velocity[1], error_ip,
                    ], dtype=float)
                    measurement_source = "control_aware_residual"
                else:
                    raise ValueError(f"unsupported observer_variant={observer_variant!r}")

                measurement = measurement_physical / measurement_scales
                integral_previous = integral.copy()
                integral_candidate = self._integral_candidate(
                    integral_previous,
                    measurement,
                    reference_step=reference_step,
                    anti_windup_enabled=anti_windup_active,
                )

                if estimator is not None:
                    modeled_pending_physical = estimator.pending_desired_physical(
                        current_step=reference_step,
                        issued_items=issued_items_history,
                        nominal_physical=nominal_physical,
                    )
                else:
                    modeled_pending_physical = []
                    for index in range(modeled_delay):
                        if index < len(command_queue):
                            modeled_pending_physical.append(
                                np.asarray(command_queue[index]["desired_physical"], dtype=float)
                            )
                        else:
                            ref_step = min(reference_step + index, 34)
                            modeled_pending_physical.append(nominal_physical[ref_step].copy())

                if controller_scale <= 0.0:
                    effect_step = min(reference_step + modeled_delay, 34)
                    solve = {
                        "first_correction": np.zeros(3),
                        "sequence_correction": np.zeros((0, 3)),
                        "solver_success": True,
                        "solver_status": 0,
                        "solver_cost": 0.0,
                        "solver_optimality": 0.0,
                        "predicted_normalized_residual_rms": float(
                            np.sqrt(np.mean(measurement**2))
                        ),
                        "active_lower": 0,
                        "active_upper": 0,
                        "effect_step": effect_step,
                        "fixed_pending_steps": modeled_delay,
                    }
                else:
                    solve = solve_delay_aware_physical_correction(
                        self.stub,
                        self.bundle,
                        current_step=reference_step,
                        modeled_action_delay_steps=modeled_delay,
                        modeled_pending_physical_coefficients=modeled_pending_physical,
                        nominal_physical_coefficients=nominal_physical,
                        nominal_feature=nominal_feature,
                        measurement_normalized=measurement,
                        integral_normalized=integral_candidate,
                        previous_correction=previous_correction,
                        controller_scale=controller_scale,
                        controller_model_scale=model_scale,
                    )

                correction = np.asarray(solve["first_correction"], dtype=float)
                saturated = self._correction_saturated(
                    correction,
                    previous_correction,
                    solve,
                    controller_scale,
                )
                integral = self._anti_windup_finalize(
                    integral_previous,
                    integral_candidate,
                    saturated=saturated,
                    anti_windup_enabled=anti_windup_active,
                )
                effect_step = min(int(solve.get("effect_step", reference_step)), 34)
                desired_physical = np.clip(
                    nominal_physical[effect_step] + correction,
                    self.lower_mode,
                    self.upper_mode,
                )
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                scheduled = self.scheduler.solve_command(
                    desired_physical,
                    currents,
                    gain_estimate,
                    slew_estimate,
                    enabled=scheduling_enabled,
                )
                issued_command = np.asarray(scheduled["command"], dtype=float)
                issued_item = {
                    "command": issued_command,
                    "desired_physical": desired_physical,
                }
                issued_items_history.append(
                    {
                        "command": issued_command.copy(),
                        "desired_physical": desired_physical.copy(),
                    }
                )
                issued_command_history.append(issued_command.copy())
                if actual_delay > 0:
                    command_queue.append(issued_item)
                    applied_item = command_queue.pop(0)
                else:
                    applied_item = issued_item
                applied_command_before_disturbance = np.asarray(
                    applied_item["command"], dtype=float
                )
                applied_command = applied_command_before_disturbance.copy()

                disturbance_applied = 0.0
                if disturbance:
                    start = int(disturbance["step"])
                    duration = max(1, int(disturbance.get("duration_steps", 1)))
                    if start <= env_step < start + duration:
                        mode = int(disturbance["mode"])
                        requested_amplitude = float(disturbance["amplitude"])
                        before = float(applied_command[mode])
                        applied_command[mode] = float(np.clip(
                            before + requested_amplitude,
                            self.lower_mode[mode],
                            self.upper_mode[mode],
                        ))
                        disturbance_applied = float(applied_command[mode] - before)

                effective_coefficients = actual_gain * applied_command + actuator_bias
                action = self._mode_action(effective_coefficients, currents)
                currents_before_step = currents.copy()
                _, _, terminated, truncated, info = self.env.step(action)
                trajectory.append(base._state_record(self.env, env_step + 1, action))
                currents_after_step = np.asarray(
                    self.env.last_state["currents_a_tsc"], dtype=float
                )
                observed_current_delta_a = currents_after_step - currents_before_step
                estimator_update: dict[str, Any] | None = None
                if estimator is not None:
                    estimator_update = estimator.update(
                        step=reference_step,
                        observed_delta_a=observed_current_delta_a,
                        currents_before_a=currents_before_step,
                        issued_commands=issued_command_history,
                        nominal_commands=nominal_command_plan,
                        gain_for_prediction=gain_estimate,
                    )

                if measured_known_effect:
                    # Deployment-realistic path for the adaptive delay/slew POC:
                    # infer the physical three-mode effect from measured coil-
                    # current increments.  This avoids consulting the simulator's
                    # private actual-delay queue.
                    known_desired = (
                        observed_current_delta_a / max(self.nominal_max_delta_a, 1e-12)
                    ) @ self.modes_tsc
                    known_effect_source = "measured_coil_current_increment"
                else:
                    # Existing robustness path: keep injected disturbances and
                    # unmodelled plant gain/bias in the residual innovation.
                    known_desired = np.asarray(
                        applied_item["desired_physical"], dtype=float
                    )
                    known_effect_source = "controller_intended_applied_item"
                known_physical_delta_by_step[reference_step] = (
                    known_desired - nominal_physical[reference_step]
                )

                actual_delta_a = np.asarray(action, dtype=float) * self.max_delta_a
                scheduler_target = np.asarray(scheduled["target_delta_a"], dtype=float)
                actual_scheduler_mismatch = actual_delta_a - scheduler_target
                control_trace.append({
                    "step": env_step,
                    "reference_step": reference_step,
                    "phase_offset_steps": env_phase_offset,
                    "phase_aware_reference_enabled": phase_aware_enabled,
                    "observer_enabled": observer_enabled,
                    "observer_variant": observer_variant,
                    "measurement_source": measurement_source,
                    "clean_sensor_path": clean_sensor_path,
                    "clean_measurement_bypass": clean_bypass,
                    "anti_windup_enabled": anti_windup_active,
                    "anti_windup_requested": anti_windup_requested,
                    "conditional_anti_windup_use_actual_actuator_state": conditional_aw_use_actual,
                    "anti_windup_saturated": saturated,
                    "delay_aware_enabled": delay_aware_enabled,
                    "gain_slew_scheduling_enabled": scheduling_enabled,
                    "observation_delay_steps": observation_delay,
                    "actual_action_delay_steps": actual_delay,
                    "modeled_action_delay_steps": modeled_delay,
                    "measurement_physical": measurement_physical.tolist(),
                    "measurement_normalized": measurement.tolist(),
                    "known_control_effect_delayed_physical": known_effect_delayed.tolist(),
                    "known_control_effect_current_physical": known_effect_current.tolist(),
                    "observer_residual_physical": observer_residual.tolist(),
                    "integral_candidate_normalized": integral_candidate.tolist(),
                    "integral_normalized": integral.tolist(),
                    "mode_correction_physical": correction.tolist(),
                    "desired_physical_mode_coefficients": desired_physical.tolist(),
                    "issued_mode_coefficients": issued_command.tolist(),
                    "applied_command_mode_coefficients": applied_command.tolist(),
                    "effective_mode_coefficients": effective_coefficients.tolist(),
                    "known_physical_delta_from_nominal": known_physical_delta_by_step[
                        reference_step
                    ].tolist(),
                    "known_control_effect_source": known_effect_source,
                    "estimated_gain_by_mode": gain_estimate.tolist(),
                    "actual_gain_by_mode": actual_gain.tolist(),
                    "estimated_slew_scale": slew_estimate,
                    "actual_slew_scale": self.actual_slew_scale,
                    "adaptive_estimator_enabled": estimator is not None,
                    "adaptive_estimated_delay_steps": (
                        None if estimator is None else int(estimator.selected_delay_steps)
                    ),
                    "adaptive_estimated_slew_scale": (
                        None if estimator is None else float(estimator.selected_slew_scale)
                    ),
                    "adaptive_estimator_update": estimator_update,
                    "scheduler_predicted_mismatch_rms_a": float(scheduled["mismatch_rms_a"]),
                    "scheduler_predicted_mismatch_max_abs_a": float(scheduled["mismatch_max_abs_a"]),
                    "scheduler_actual_mismatch_rms_a": float(
                        np.sqrt(np.mean(actual_scheduler_mismatch**2))
                    ),
                    "scheduler_actual_mismatch_max_abs_a": float(
                        np.max(np.abs(actual_scheduler_mismatch))
                    ),
                    "disturbance_applied": disturbance_applied,
                    "solver_success": bool(solve["solver_success"]),
                    "solver_status": int(solve["solver_status"]),
                    "solver_cost": float(solve["solver_cost"]),
                    "predicted_normalized_residual_rms": float(
                        solve["predicted_normalized_residual_rms"]
                    ),
                })
                previous_correction = correction
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated"))
                    break
                if truncated and env_step + 1 < 35:
                    failure_reason = "environment truncated before the 350 ms horizon"
                    break

            success = len(trajectory) == 36 and not any(
                bool(row.get("abnormal", False)) for row in trajectory
            )
            result = {
                "schema_version": SCHEMA_VERSION,
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": spec["experiment_id"],
                "spec": spec,
                "success": bool(success),
                "failure_reason": "" if success else (
                    failure_reason or "incomplete/abnormal trajectory"
                ),
                "wall_time_s": float(time.time() - started),
                "trajectory": trajectory,
                "prelude_trajectory": prelude_trajectory,
                "control_trace": control_trace,
                "nominal_schedule_diagnostics": nominal_schedule_diagnostics,
                "library_interpolation": interpolation,
                "environment_variant": self.variant_id,
                "adaptive_estimator_summary": (
                    None if estimator is None else estimator.summary()
                ),
                "phase_start_diagnostics": {
                    "phase_offset_steps": env_phase_offset,
                    "reference_phase_offset_steps": reference_phase_offset,
                    "R_error_to_nominal_m": float(phase_start_error[0]),
                    "Z_error_to_nominal_m": float(phase_start_error[1]),
                    "Ip_error_to_nominal_A": float(phase_start_error[2]),
                    "RZ_box_error_to_nominal_m": float(
                        max(abs(phase_start_error[0]), abs(phase_start_error[1]))
                    ),
                },
            }
        except Exception as exc:
            result = {
                "schema_version": SCHEMA_VERSION,
                "controller_revision": CONTROLLER_REVISION,
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
        if runner is not None and not bool(spec.get("_defer_cleanup", False)):
            runner.cleanup_episode_workspace(
                failed=not bool(result.get("success")),
                reason=str(result.get("failure_reason", "stage4_1r3_complete")),
            )
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



def _selected_controller_spec_fields(ctx: Stage41Context) -> dict[str, Any]:
    if not ctx.paths.state.exists():
        raise RuntimeError("Stage4.1R3 state is missing; observer ablation has not selected a controller")
    state = read_json(ctx.paths.state)
    variant = state.get("selected_observer_variant")
    anti_windup = state.get("selected_anti_windup_enabled")
    if not variant or anti_windup is None:
        raise RuntimeError(
            "Stage4.1R3 observer ablation has not selected an observer/anti-windup configuration"
        )
    return {
        "observer_enabled": True,
        "observer_variant": str(variant),
        "anti_windup_enabled": bool(anti_windup),
        "delay_aware_enabled": True,
        "gain_slew_scheduling_enabled": True,
        "phase_aware_reference_enabled": True,
        "controller_variant": f"selected_{variant}_{'aw' if anti_windup else 'no_aw'}",
    }


def _apply_selected_controller_settings(
    ctx: Stage41Context, specs: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Attach the ablation-selected observer to all post-ablation MPC specs."""
    selected: dict[str, Any] | None = None
    cooked: list[dict[str, Any]] = []
    for original in specs:
        spec = copy.deepcopy(original)
        phase = str(spec.get("phase", ""))
        scale = float(spec.get("controller_scale", 0.0))
        if scale > 0.0 and phase not in {"regression_targets", "observer_ablation"}:
            if selected is None:
                selected = _selected_controller_spec_fields(ctx)
            for key, value in selected.items():
                spec.setdefault(key, copy.deepcopy(value))
            identity = {key: value for key, value in spec.items() if key != "experiment_id"}
            spec["experiment_id"] = _scenario_digest(identity, prefix="s41r3")
        cooked.append(spec)
    return cooked


def evaluate_specs(
    ctx: Stage41Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    specs = _apply_selected_controller_settings(ctx, specs)
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
                    print(f"[Stage4.1R3 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray
        requested = int(os.environ.get("STAGE4_1R3_WORKERS", os.environ.get("STAGE4_1_WORKERS", os.environ.get("STAGE4_WORKERS", ctx.cfg["parallel"]["n_workers"]))))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R3 mixed-variant]",
        )
        allocation = s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()}, plan.actor_count
        )
        print("[Stage4.1R3 mixed-variant] actor_allocation=" + json.dumps(allocation, sort_keys=True, separators=(",", ":")), flush=True)
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
                    print(f"[Stage4.1R3 mixed-variant] waiting {done}/{total_pending}", flush=True)
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
                        print(f"[Stage4.1R3 mixed-variant] {done}/{total_pending}", flush=True)
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
        "controller_revision": CONTROLLER_REVISION,
        "phase": phase, "scenario": scenario, "category": category,
        "target": target, "controller_scale": controller_scale,
        "environment_variant": environment_variant, "extra": extra,
    }
    return {
        "kind": "stage4_1r3_robustness_mpc",
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": _scenario_digest(identity, prefix="s41r3"),
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
    max_correction = max((float(np.max(np.abs(row.get("mode_correction_physical", row.get("mode_correction", [0.0, 0.0, 0.0]))))) for row in trace), default=0.0)
    scheduler_rms = max((float(row.get("scheduler_actual_mismatch_rms_a", 0.0)) for row in trace), default=0.0)
    scheduler_max = max((float(row.get("scheduler_actual_mismatch_max_abs_a", 0.0)) for row in trace), default=0.0)
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
        "controller_revision": result.get("controller_revision", spec.get("controller_revision", "")),
        "controller_variant": spec.get("controller_variant", "default"),
        "observer_enabled": bool(spec.get("observer_enabled", True)),
        "observer_variant": spec.get("observer_variant", "legacy_raw"),
        "anti_windup_enabled": bool(spec.get("anti_windup_enabled", False)),
        "clean_bypass_steps": sum(
            str(row.get("measurement_source", "")) == "clean_direct_bypass" for row in trace
        ),
        "anti_windup_saturated_steps": sum(
            bool(row.get("anti_windup_saturated", False)) for row in trace
        ),
        "delay_aware_enabled": bool(spec.get("delay_aware_enabled", True)),
        "gain_slew_scheduling_enabled": bool(spec.get("gain_slew_scheduling_enabled", True)),
        "phase_aware_reference_enabled": bool(spec.get("phase_aware_reference_enabled", True)),
        "max_abs_mode_correction": max_correction,
        "max_scheduler_actual_mismatch_rms_a": scheduler_rms,
        "max_scheduler_actual_mismatch_abs_a": scheduler_max,
        **metrics,
    }


def summarize_pairs(rows: Sequence[dict[str, Any]], pair_fields: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return s40.summarize_pairs(rows, pair_fields)


# ---------------------------------------------------------------------------
# Phase A: target-regression guard
# ---------------------------------------------------------------------------


def _trajectory_action_matrix(result: dict[str, Any]) -> np.ndarray:
    trajectory = result.get("trajectory") or []
    if not trajectory:
        return np.zeros((0, 14), dtype=float)
    return np.asarray([row.get("action_norm_tsc", np.zeros(14)) for row in trajectory], dtype=float)


def _trajectory_state_matrix(result: dict[str, Any]) -> np.ndarray:
    trajectory = result.get("trajectory") or []
    if not trajectory:
        return np.zeros((0, 3), dtype=float)
    return np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)


def run_regression(ctx: Stage41Context, *, backend: str, resume: bool) -> dict[str, Any]:
    """Exact clean-condition integration guard before observer calibration.

    The upgraded R3 path deliberately bypasses filtering when measurements are
    noise-free and undelayed.  Under unity gain/slew and zero action delay it
    must therefore reproduce the confirmed Stage3.4 controller, not merely
    remain on the positive side of the hard gate.
    """
    cfg = ctx.cfg["regression_targets"]
    variants = [
        {
            "name": "open_loop",
            "controller_scale": 0.0,
            "observer_enabled": False,
            "observer_variant": "legacy_raw",
            "anti_windup_enabled": False,
            "delay_aware_enabled": False,
            "gain_slew_scheduling_enabled": False,
            "phase_aware_reference_enabled": True,
        },
        {
            "name": "legacy_stage3_4",
            "controller_scale": ctx.source_scale,
            "observer_enabled": False,
            "observer_variant": "legacy_raw",
            "anti_windup_enabled": False,
            "delay_aware_enabled": False,
            "gain_slew_scheduling_enabled": False,
            "phase_aware_reference_enabled": True,
        },
        {
            "name": "r3_clean_direct",
            "controller_scale": ctx.source_scale,
            "observer_enabled": True,
            "observer_variant": "control_aware_residual",
            "anti_windup_enabled": False,
            "delay_aware_enabled": True,
            "gain_slew_scheduling_enabled": True,
            "phase_aware_reference_enabled": True,
        },
    ]
    specs: list[dict[str, Any]] = []
    for scenario in cfg["scenarios"]:
        target = {"target_id": scenario["scenario"], **scenario}
        for variant in variants:
            specs.append(
                _make_spec(
                    phase="regression_targets",
                    scenario=scenario["scenario"],
                    category="regression_target",
                    target=target,
                    controller_scale=float(variant["controller_scale"]),
                    extra={key: value for key, value in variant.items() if key != "name"}
                    | {"controller_variant": variant["name"]},
                )
            )
    results = evaluate_specs(
        ctx, specs, output_dir=ctx.paths.regression / "raw", backend=backend, resume=resume
    )
    rows = [result_row(ctx, result) for result in results]
    by_scenario: dict[str, dict[str, dict[str, Any]]] = {}
    raw_by_scenario: dict[str, dict[str, dict[str, Any]]] = {}
    for row, result in zip(rows, results):
        scenario = str(row["scenario"])
        variant = str(row["controller_variant"])
        by_scenario.setdefault(scenario, {})[variant] = row
        raw_by_scenario.setdefault(scenario, {})[variant] = result

    comparison_rows: list[dict[str, Any]] = []
    for scenario in [str(item["scenario"]) for item in cfg["scenarios"]]:
        group = by_scenario.get(scenario, {})
        raw_group = raw_by_scenario.get(scenario, {})
        names = ("open_loop", "legacy_stage3_4", "r3_clean_direct")
        missing = [name for name in names if name not in group or name not in raw_group]
        if missing:
            raise RuntimeError(f"regression scenario {scenario} missing variants {missing}")
        open_row = group["open_loop"]
        legacy_row = group["legacy_stage3_4"]
        upgraded_row = group["r3_clean_direct"]
        legacy_result = raw_group["legacy_stage3_4"]
        upgraded_result = raw_group["r3_clean_direct"]
        open_pass = _as_bool(open_row.get("stage3_4_target_tracking_pass"))
        legacy_pass = _as_bool(legacy_row.get("stage3_4_target_tracking_pass"))
        upgraded_pass = _as_bool(upgraded_row.get("stage3_4_target_tracking_pass"))
        legacy_margin = _as_float(
            legacy_row.get("stage3_4_tracking_minimum_signed_margin"), -1e12
        )
        upgraded_margin = _as_float(
            upgraded_row.get("stage3_4_tracking_minimum_signed_margin"), -1e12
        )
        legacy_action = _trajectory_action_matrix(legacy_result)
        upgraded_action = _trajectory_action_matrix(upgraded_result)
        legacy_state = _trajectory_state_matrix(legacy_result)
        upgraded_state = _trajectory_state_matrix(upgraded_result)
        if legacy_action.shape == upgraded_action.shape and legacy_action.size:
            action_rms_difference = float(
                np.sqrt(np.mean((legacy_action - upgraded_action) ** 2))
            )
            action_max_difference = float(np.max(np.abs(legacy_action - upgraded_action)))
        else:
            action_rms_difference = 1e12
            action_max_difference = 1e12
        if legacy_state.shape == upgraded_state.shape and legacy_state.size:
            state_max_difference = float(np.max(np.abs(legacy_state - upgraded_state)))
        else:
            state_max_difference = 1e12
        comparison_rows.append({
            "scenario": scenario,
            "open_loop_pass": open_pass,
            "legacy_stage3_4_pass": legacy_pass,
            "upgraded_pass": upgraded_pass,
            "upgraded_lost_open_loop_pass": bool(open_pass and not upgraded_pass),
            "upgraded_lost_legacy_pass": bool(legacy_pass and not upgraded_pass),
            "legacy_signed_margin": legacy_margin,
            "upgraded_signed_margin": upgraded_margin,
            "upgraded_minus_legacy_margin": upgraded_margin - legacy_margin,
            "legacy_post_arrival_velocity_rms": _as_float(
                legacy_row.get("stage3_4_post_arrival_velocity_rms_m_per_s"), 1e12
            ),
            "upgraded_post_arrival_velocity_rms": _as_float(
                upgraded_row.get("stage3_4_post_arrival_velocity_rms_m_per_s"), 1e12
            ),
            "legacy_final_velocity": _as_float(
                legacy_row.get("stage3_4_final_velocity_m_per_s"), 1e12
            ),
            "upgraded_final_velocity": _as_float(
                upgraded_row.get("stage3_4_final_velocity_m_per_s"), 1e12
            ),
            "action_rms_difference_vs_legacy": action_rms_difference,
            "action_max_difference_vs_legacy": action_max_difference,
            "trajectory_state_max_abs_difference_vs_legacy": state_max_difference,
            "upgraded_scheduler_mismatch_rms_a": _as_float(
                upgraded_row.get("max_scheduler_actual_mismatch_rms_a"), 0.0
            ),
        })

    margin_deltas = [row["upgraded_minus_legacy_margin"] for row in comparison_rows]
    minimum_median_delta = float(
        cfg.get("minimum_median_margin_delta_vs_legacy", -0.005)
    )
    minimum_worst_delta = float(
        cfg.get("minimum_worst_margin_delta_vs_legacy", -0.02)
    )
    maximum_action_rms_difference = float(
        cfg.get("maximum_action_rms_difference_vs_legacy", 1e-6)
    )
    maximum_state_difference = float(
        cfg.get("maximum_trajectory_state_abs_difference_vs_legacy", 1e-9)
    )
    maximum_scheduler_mismatch = float(
        ctx.cfg["controller_upgrade"]["gain_slew_scheduling"].get(
            "maximum_allowed_regression_scheduler_mismatch_rms_A", 0.05
        )
    )
    observed_scheduler_mismatch = max(
        row["upgraded_scheduler_mismatch_rms_a"] for row in comparison_rows
    )
    observed_action_rms_difference = max(
        row["action_rms_difference_vs_legacy"] for row in comparison_rows
    )
    observed_state_difference = max(
        row["trajectory_state_max_abs_difference_vs_legacy"] for row in comparison_rows
    )
    passed = bool(
        all(row["open_loop_pass"] for row in comparison_rows)
        and all(row["legacy_stage3_4_pass"] for row in comparison_rows)
        and all(row["upgraded_pass"] for row in comparison_rows)
        and not any(row["upgraded_lost_open_loop_pass"] for row in comparison_rows)
        and not any(row["upgraded_lost_legacy_pass"] for row in comparison_rows)
        and float(np.median(margin_deltas)) >= minimum_median_delta
        and min(margin_deltas) >= minimum_worst_delta
        and observed_scheduler_mismatch <= maximum_scheduler_mismatch
        and observed_action_rms_difference <= maximum_action_rms_difference
        and observed_state_difference <= maximum_state_difference
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "phase": "regression_targets",
        "n_rollouts": len(rows),
        "n_scenarios": len(comparison_rows),
        "open_loop_passes": sum(row["open_loop_pass"] for row in comparison_rows),
        "legacy_passes": sum(row["legacy_stage3_4_pass"] for row in comparison_rows),
        "upgraded_passes": sum(row["upgraded_pass"] for row in comparison_rows),
        "n_lost_open_loop": sum(
            row["upgraded_lost_open_loop_pass"] for row in comparison_rows
        ),
        "n_lost_legacy": sum(
            row["upgraded_lost_legacy_pass"] for row in comparison_rows
        ),
        "median_margin_delta_vs_legacy": float(np.median(margin_deltas)),
        "worst_margin_delta_vs_legacy": float(min(margin_deltas)),
        "minimum_median_margin_delta_vs_legacy": minimum_median_delta,
        "minimum_worst_margin_delta_vs_legacy": minimum_worst_delta,
        "maximum_action_rms_difference_vs_legacy": maximum_action_rms_difference,
        "observed_max_action_rms_difference_vs_legacy": observed_action_rms_difference,
        "maximum_trajectory_state_abs_difference_vs_legacy": maximum_state_difference,
        "observed_max_trajectory_state_abs_difference_vs_legacy": observed_state_difference,
        "maximum_scheduler_mismatch_rms_a": maximum_scheduler_mismatch,
        "observed_scheduler_mismatch_rms_a": observed_scheduler_mismatch,
        "passed": passed,
    }
    write_csv(ctx.paths.regression / "results.csv", rows)
    write_csv(ctx.paths.regression / "comparison.csv", comparison_rows)
    atomic_write_json(ctx.paths.regression / "results.json", rows)
    atomic_write_json(ctx.paths.regression / "comparison.json", comparison_rows)
    atomic_write_json(ctx.paths.regression / "summary.json", summary)
    _update_state(ctx, regression_complete=True, regression_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Phase A2: observer/anti-windup calibration on a disjoint finite envelope
# ---------------------------------------------------------------------------


def run_observer_ablation(
    ctx: Stage41Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    cfg = ctx.cfg["observer_ablation"]
    specs: list[dict[str, Any]] = []
    variants = {str(row["name"]): row for row in cfg["variants"]}
    for target in cfg["targets"]:
        for condition in cfg["conditions"]:
            scenario = f"{target['target_id']}__{condition['name']}"
            condition_extra = {
                key: copy.deepcopy(value)
                for key, value in condition.items()
                if key != "name"
            }
            for variant in variants.values():
                extra = {
                    **condition_extra,
                    "controller_variant": str(variant["name"]),
                    "observer_enabled": str(variant["observer_variant"]) != "legacy_raw",
                    "observer_variant": str(variant["observer_variant"]),
                    "anti_windup_enabled": bool(variant["anti_windup_enabled"]),
                    "delay_aware_enabled": True,
                    "gain_slew_scheduling_enabled": True,
                    "phase_aware_reference_enabled": True,
                }
                specs.append(
                    _make_spec(
                        phase="observer_ablation",
                        scenario=scenario,
                        category="observer_ablation",
                        target=target,
                        controller_scale=ctx.source_scale,
                        extra=extra,
                    )
                )
    results = evaluate_specs(
        ctx, specs, output_dir=ctx.paths.ablation / "raw", backend=backend, resume=resume
    )
    rows = [result_row(ctx, result) for result in results]
    by_scenario: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), {})[
            str(row["controller_variant"])
        ] = row
    scenario_rows: list[dict[str, Any]] = []
    for scenario, group in sorted(by_scenario.items()):
        if "legacy_raw" not in group:
            raise RuntimeError(f"observer ablation scenario {scenario} lacks legacy_raw")
        legacy = group["legacy_raw"]
        legacy_pass = _as_bool(legacy.get("stage3_4_target_tracking_pass"))
        legacy_margin = _as_float(
            legacy.get("stage3_4_tracking_minimum_signed_margin"), -1e12
        )
        for variant_name, row in group.items():
            passed = _as_bool(row.get("stage3_4_target_tracking_pass"))
            margin = _as_float(
                row.get("stage3_4_tracking_minimum_signed_margin"), -1e12
            )
            scenario_rows.append({
                "scenario": scenario,
                "target_id": row.get("target_id"),
                "condition": scenario.split("__", 1)[1] if "__" in scenario else scenario,
                "variant": variant_name,
                "selectable": bool(variants[variant_name].get("selectable", False)),
                "tracking_pass": passed,
                "legacy_tracking_pass": legacy_pass,
                "preserved_legacy_pass": bool(not legacy_pass or passed),
                "signed_margin": margin,
                "legacy_signed_margin": legacy_margin,
                "margin_delta_vs_legacy": margin - legacy_margin,
                "post_arrival_velocity_rms": _as_float(
                    row.get("stage3_4_post_arrival_velocity_rms_m_per_s"), 1e12
                ),
                "final_velocity": _as_float(
                    row.get("stage3_4_final_velocity_m_per_s"), 1e12
                ),
            })

    clean_name = str(cfg.get("clean_condition_name", "clean"))
    variant_summaries: list[dict[str, Any]] = []
    selection_weights = cfg.get("selection_weights", {})
    for variant_name, variant_cfg in variants.items():
        subset = [row for row in scenario_rows if row["variant"] == variant_name]
        clean = [row for row in subset if row["condition"] == clean_name]
        legacy_pass_subset = [row for row in subset if row["legacy_tracking_pass"]]
        pass_fraction = sum(row["tracking_pass"] for row in subset) / max(len(subset), 1)
        preserved_fraction = sum(row["preserved_legacy_pass"] for row in legacy_pass_subset) / max(
            len(legacy_pass_subset), 1
        )
        deltas = [float(row["margin_delta_vs_legacy"]) for row in subset]
        median_delta = float(np.median(deltas)) if deltas else -1e12
        worst_delta = float(min(deltas)) if deltas else -1e12
        clean_pass = bool(clean and all(row["tracking_pass"] for row in clean))
        selectable = bool(variant_cfg.get("selectable", False))
        eligible = bool(
            selectable
            and (clean_pass or not bool(cfg.get("require_all_clean_pass", True)))
            and pass_fraction >= float(cfg.get("minimum_overall_pass_fraction", 0.75))
            and preserved_fraction >= float(
                cfg.get("minimum_preserved_legacy_pass_fraction", 0.95)
            )
            and median_delta >= float(
                cfg.get("minimum_median_margin_delta_vs_legacy", -0.05)
            )
            and worst_delta >= float(
                cfg.get("minimum_worst_margin_delta_vs_legacy", -0.20)
            )
        )
        score = (
            float(selection_weights.get("pass_count", 1000.0))
            * sum(row["tracking_pass"] for row in subset)
            + float(selection_weights.get("preserved_count", 200.0))
            * sum(row["preserved_legacy_pass"] for row in legacy_pass_subset)
            + float(selection_weights.get("median_margin", 10.0)) * median_delta
            + float(selection_weights.get("worst_margin", 2.0)) * worst_delta
            + float(selection_weights.get("anti_windup_preference", 0.01))
            * bool(variant_cfg.get("anti_windup_enabled", False))
        )
        variant_summaries.append({
            "variant": variant_name,
            "observer_variant": variant_cfg["observer_variant"],
            "anti_windup_enabled": bool(variant_cfg["anti_windup_enabled"]),
            "selectable": selectable,
            "eligible": eligible,
            "n_scenarios": len(subset),
            "n_pass": sum(row["tracking_pass"] for row in subset),
            "pass_fraction": pass_fraction,
            "n_legacy_pass_scenarios": len(legacy_pass_subset),
            "preserved_legacy_pass_fraction": preserved_fraction,
            "all_clean_pass": clean_pass,
            "median_margin_delta_vs_legacy": median_delta,
            "worst_margin_delta_vs_legacy": worst_delta,
            "selection_score": float(score),
        })

    eligible = [row for row in variant_summaries if row["eligible"]]
    selected = max(
        eligible,
        key=lambda row: (float(row["selection_score"]), str(row["variant"])),
        default=None,
    )
    passed = selected is not None
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "phase": "observer_ablation",
        "n_rollouts": len(rows),
        "n_scenarios": len(by_scenario),
        "variant_summaries": variant_summaries,
        "selected_variant": None if selected is None else selected["variant"],
        "selected_observer_variant": None
        if selected is None
        else selected["observer_variant"],
        "selected_anti_windup_enabled": None
        if selected is None
        else bool(selected["anti_windup_enabled"]),
        "passed": passed,
    }
    write_csv(ctx.paths.ablation / "results.csv", rows)
    write_csv(ctx.paths.ablation / "scenario_comparison.csv", scenario_rows)
    write_csv(ctx.paths.ablation / "variant_summary.csv", variant_summaries)
    atomic_write_json(ctx.paths.ablation / "results.json", rows)
    atomic_write_json(ctx.paths.ablation / "scenario_comparison.json", scenario_rows)
    atomic_write_json(ctx.paths.ablation / "summary.json", summary)
    _update_state(
        ctx,
        ablation_complete=True,
        ablation_summary=summary,
        selected_observer_variant=summary["selected_observer_variant"],
        selected_anti_windup_enabled=summary["selected_anti_windup_enabled"],
    )
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
        "regression_summary", "ablation_summary", "recovery_summary", "structured_summary",
        "noise_summary", "history_summary", "confirmation_summary",
    ))
    restart = state.get("restart_summary") or {}
    available = bool(restart.get("true_restart_validation_available"))
    restart_pass = bool(restart.get("passed")) if available else None
    regression_passed = bool((state.get("regression_summary") or {}).get("passed"))
    ablation_passed = bool((state.get("ablation_summary") or {}).get("passed"))
    if not regression_passed:
        label = "STAGE4_1R3_CONTROLLER_INTEGRATION_REGRESSION_FAILED"
    elif not ablation_passed:
        label = "STAGE4_1R3_CONTROL_AWARE_OBSERVER_CALIBRATION_FAILED"
    elif core and not available:
        label = "PASS_STAGE4_1R3_DELAY_GAIN_PHASE_ROBUSTNESS_AND_RECOVERY_CONFIRMED_TRUE_RESTART_NOT_AVAILABLE"
    elif core and restart_pass:
        label = "PASS_STAGE4_1R3_DELAY_GAIN_PHASE_ROBUSTNESS_RECOVERY_AND_TRUE_RESTART_CONFIRMED"
    elif core:
        label = "PASS_STAGE4_1R3_CONTROLLED_ROBUSTNESS_TRUE_RESTART_VALIDATION_FAILED"
    else:
        label = "STAGE4_1R3_DELAY_GAIN_PHASE_ROBUSTNESS_ENVELOPE_INCOMPLETE"
    verdict = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE, "created_utc": utc_timestamp(),
        "verdict": label, "source_stage4_0_run": str(ctx.source_stage40_run),
        "source_stage3_4_run": str(ctx.source_stage34_run),
        "source_selected_controller_scale": ctx.source_scale,
        "controller_revision": CONTROLLER_REVISION,
        "regression_passed": regression_passed,
        "observer_ablation_passed": ablation_passed,
        "selected_observer_variant": state.get("selected_observer_variant"),
        "selected_anti_windup_enabled": state.get("selected_anti_windup_enabled"),
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
    atomic_write_json(ctx.paths.analysis / "stage4_1r3_verdict.json", verdict)
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
        "observer_ablation": state.get("ablation_summary", {}),
        "selected_observer_variant": state.get("selected_observer_variant"),
        "selected_anti_windup_enabled": state.get("selected_anti_windup_enabled"),
        "adaptive_failure_recovery": state.get("recovery_summary", {}),
        "structured_uncertainty": state.get("structured_summary", {}),
        "noise_statistics": state.get("noise_summary", {}),
        "phase_aligned_history": state.get("history_summary", {}),
        "restart_sweep": state.get("restart_summary", {}),
        "confirmation": state.get("confirmation_summary", {}),
        "verdict": verdict,
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r3_analysis_summary.json", summary)
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
        regression = run_regression(ctx, backend=backend, resume=resume)
        if command == "all" and not bool(regression.get("passed")):
            analysis = analyze_stage41(ctx)
            _update_state(
                ctx,
                finished=True,
                stop_reason="controller_integration_regression_failed",
                analysis_summary=analysis,
            )
            return analysis
    if command in {"all", "ablation"}:
        ablation = run_observer_ablation(ctx, backend=backend, resume=resume)
        if command == "all" and not bool(ablation.get("passed")):
            analysis = analyze_stage41(ctx)
            _update_state(
                ctx,
                finished=True,
                stop_reason="control_aware_observer_calibration_failed",
                analysis_summary=analysis,
            )
            return analysis
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
    dt = 0.01
    nominal = np.zeros((36, 3), dtype=float)
    measurement_scales = np.asarray([0.03, 0.03, 0.10, 0.10, 1000.0])
    jacobian = np.zeros((175, 105), dtype=float)
    # A step-0 mode-0 correction causes a known state-1 response.
    jacobian[[0, 35, 70, 105, 140], 0] = np.asarray([0.2, -0.1, 0.3, -0.2, 0.05])
    bundle = {"jacobian_normalized": jacobian.tolist()}
    known_delta = np.zeros((35, 3), dtype=float)
    known_delta[0, 0] = 0.5
    known = known_control_effect_physical(
        bundle,
        state_index=1,
        known_physical_delta_by_step=known_delta,
        measurement_scales=measurement_scales,
    )
    measurement = np.asarray([known[0], known[1], known[4]])
    observer = ControlAwareResidualObserver(
        alpha=0.68,
        beta=0.28,
        direct_velocity_blend=0.20,
        alpha_ip=0.40,
        max_abs_residual_velocity=1.0,
    )
    observer.update(measurement, 1, nominal, known, dt)
    position, velocity, ip, residual = observer.predict_total_error_to(1, known, dt)
    np.testing.assert_allclose(position, known[:2], atol=1e-14)
    np.testing.assert_allclose(velocity, known[2:4], atol=1e-14)
    assert abs(ip - known[4]) <= 1e-14
    np.testing.assert_allclose(residual, 0.0, atol=1e-14)
    assert _sensor_path_is_clean({"observation_delay_steps": 0})
    assert not _sensor_path_is_clean(
        {"observation_noise": {"R_sigma_m": 1e-4}}
    )
    assert 0.0 <= wilson_lower_bound(9, 10) <= 1.0
    return {
        "synthetic_ok": True,
        "workers": 128,
        "controller_revision": CONTROLLER_REVISION,
        "known_effect_physical": known.tolist(),
        "observer_residual": residual.tolist(),
        "ablation_variants": 4,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage4.1R3 control-aware residual observer and anti-windup robustness validation")
    parser.add_argument("--config", default="configs/stage4_1r3_control_aware_residual_observer_350ms.json")
    parser.add_argument("--source-stage4-0-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--command", choices=("all", "prepare", "regression", "ablation", "recovery", "structured", "noise", "history", "restart", "confirm", "analyze"), default="all")
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
