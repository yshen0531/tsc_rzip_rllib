"""Stage3.3 target-conditioned nominal library and receding-horizon MPC POC.

Stage3.2 established a reproducible 250 ms open-loop strict hold for one fixed
R/Z/Ip target, but its single local causal gain did not track adverse target
changes.  Stage3.3 therefore separates two jobs:

1. Build and confirm a small library of target-conditioned 250 ms nominal
   trajectories.  The Stage3.2 real-TSC 125x75 Jacobian provides the initial
   feed-forward correction; failed targets are refined in a reduced real-TSC
   subspace.
2. Validate a genuine receding-horizon controller.  At every 10 ms step it
   resolves a bounded future-sequence least-squares problem, applies only the
   first three-mode correction, observes the next state, and resolves again.

The implementation keeps the validated three-SVD-mode action space and the
30 mm / 0.10 m/s / 10 kA hard safety gate.  It additionally reports explicit
Ip tracking tolerances, because Stage3.2's 10 kA gate only established safety,
not Ip target tracking.

This stage still does not establish initial-state, plant-parameter, noise, or
latency robustness.  Its final purpose is to produce a target-conditioned
nominal/MPC baseline from which expert data and, much later, bounded residual
RL can be built.
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
import shutil
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as base
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_2_margin_long_hold_mpc as s32
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
IP_TRACKING_GATE_REVISION = "2x_for_tsc_additional_heating"
REFINEMENT_MODEL_REVISION = "dimensionless_central_difference_source_prior_v2"
EXPECTED_IP_TRACKING_TOLERANCES_A = {
    "terminal_abs_tolerance_A": 2000.0,
    "hold_rms_tolerance_A": 2400.0,
    "sustained_max_tolerance_A": 4000.0,
}
STATE_FILENAME = "stage3_3_state.json"
MANIFEST_FILENAME = "stage3_3_manifest.json"
SOURCE_CATALOG_FILENAME = "source_stage3_2_catalog.json"


# ---------------------------------------------------------------------------
# Strict JSON / CSV helpers
# ---------------------------------------------------------------------------


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_json(path: Path | str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_json_gz(path: Path | str) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _json_safe(value: Any, path: str = "$") -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite JSON number at {path}: {value!r}")
        return value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, f"{path}[{index}]") for index, item in enumerate(value)]
    return value


def atomic_write_json(path: Path, payload: Any) -> None:
    path = Path(path)
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
    path = Path(path)
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
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path = Path(path)
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
                writer.writerow({field: _csv_value(row.get(field, "")) for field in fields})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _finite(value: Any, fallback: float) -> float:
    number = _as_float(value, None)
    return fallback if number is None else float(number)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _vector(value: Any, expected: int) -> np.ndarray:
    if isinstance(value, np.ndarray):
        array = np.asarray(value, dtype=float)
    elif isinstance(value, (list, tuple)):
        array = np.asarray(value, dtype=float)
    else:
        array = np.asarray(json.loads(str(value)), dtype=float)
    array = array.reshape(-1)
    if array.shape != (expected,) or not np.all(np.isfinite(array)):
        raise ValueError(f"expected finite vector of length {expected}, found {array.shape}")
    return array


def vector_digest(vector: np.ndarray, prefix: str = "s33") -> str:
    rounded = np.round(np.asarray(vector, dtype=float).reshape(-1), 10)
    return f"{prefix}_{hashlib.sha256(rounded.tobytes()).hexdigest()[:16]}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Context, paths, source loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage33Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_catalog: Path
    warmstart: Path
    refinement: Path
    library: Path
    controller: Path
    calibration: Path
    holdout: Path
    confirmations: Path
    analysis: Path
    best: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage33Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_catalog=run_dir / SOURCE_CATALOG_FILENAME,
            warmstart=run_dir / "stage3_3_nominal_warmstart",
            refinement=run_dir / "stage3_3_nominal_refinement",
            library=run_dir / "stage3_3_target_library",
            controller=run_dir / "stage3_3_controller",
            calibration=run_dir / "stage3_3_mpc_calibration",
            holdout=run_dir / "stage3_3_mpc_holdout",
            confirmations=run_dir / "stage3_3_confirmations",
            analysis=run_dir / "stage3_3_analysis",
            best=run_dir / "stage3_3_best",
            source_reference=run_dir / "source_stage3_2_reference",
        )


@dataclass
class Stage33Context:
    cfg: dict[str, Any]
    train_cfg: dict[str, Any]
    env_cfg: dict[str, Any]
    paths: Stage33Paths
    source_stage32_run: Path
    source_stage31_run: Path
    base32: s32.Stage32Context
    modes_tsc: np.ndarray
    initial_currents_tsc: np.ndarray
    max_delta_a: float
    min_current_tsc: np.ndarray
    max_current_tsc: np.ndarray
    source_bundle: dict[str, Any]
    source_center: dict[str, Any]
    source_best: dict[str, Any]
    source_center_result: dict[str, Any]
    source_best_result: dict[str, Any]
    target_tasks: list[dict[str, Any]]
    source_fingerprint: dict[str, Any]


_REQUIRED_STAGE32 = (
    "stage3_2_config.resolved.json",
    "stage3_2_manifest.json",
    "stage3_2_state.json",
    "stage3_2_analysis/all_results.json",
    "stage3_2_analysis/stage3_2_analysis_summary.json",
    "stage3_2_confirmations/stage3_2_verdict.json",
    "stage3_2_controller/mpc_poc_bundle.json",
    "stage3_2_best/controller_identification_best_candidate.json",
    "stage3_2_best/controller_identification_best_tsc_result.json.gz",
    "stage3_2_best/long_hold_best_candidate.json",
    "stage3_2_best/long_hold_best_tsc_result.json.gz",
    "env_config.resolved.json",
    "train_config.resolved.json",
)


def resolve_source_stage32_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE3_2_RUN", "").strip()
    if not value:
        raise ValueError("Pass --source-stage3-2-run or set SOURCE_STAGE3_2_RUN")
    run = Path(value).expanduser().resolve()
    missing = [str(run / relative) for relative in _REQUIRED_STAGE32 if not (run / relative).exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage3.2 source: " + ", ".join(missing))
    verdict = read_json(run / "stage3_2_confirmations/stage3_2_verdict.json")
    if str(verdict.get("verdict", "")) != "PASS_PRECISE_HOLD_30MM_250MS_OPEN_LOOP_CONFIRMED_FEEDBACK_NOT_VALIDATED":
        raise RuntimeError("Stage3.3 requires the confirmed Stage3.2 open-loop long-hold verdict")
    return run


def _project_fallback(project_dir: Path, dirname: str, basename: str) -> Path | None:
    candidate = project_dir / dirname / basename
    return candidate.resolve() if candidate.exists() else None


def resolve_stage31_from_stage32(source32: Path, project_dir: Path) -> Path:
    manifest = read_json(source32 / "stage3_2_manifest.json")
    raw = str(manifest.get("source_stage3_1_run", "")).strip()
    if raw:
        path = Path(raw).expanduser()
        if path.exists():
            return path.resolve()
        fallback = _project_fallback(project_dir, "stage3_1_runs", path.name)
        if fallback is not None:
            return fallback
    env = os.environ.get("SOURCE_STAGE3_1_RUN", "").strip()
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()
    raise FileNotFoundError("Cannot resolve Stage3.1 source referenced by Stage3.2")


def _resolve_storage(value: Any, project_dir: Path) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return str(path.resolve())


def _source_inventory(source32: Path) -> dict[str, Any]:
    include: list[Path] = []
    for relative in _REQUIRED_STAGE32:
        include.append(source32 / relative)
    for path in sorted((source32 / "stage3_2_confirmations/open_loop_raw").glob("*.json.gz")):
        include.append(path)
    for path in sorted((source32 / "stage3_2_controller").glob("*")):
        if path.is_file():
            include.append(path)
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    for path in sorted(set(include), key=lambda item: str(item)):
        if not path.exists() or not path.is_file():
            continue
        relative = str(path.relative_to(source32))
        file_digest = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"relative_path": relative, "sha256": file_digest, "size_bytes": size})
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\0")
    return {
        "schema_version": SCHEMA_VERSION,
        "source_stage3_2_run": str(source32),
        "n_files": len(entries),
        "total_bytes": int(sum(int(row["size_bytes"]) for row in entries)),
        "digest": digest.hexdigest(),
        "entries": entries,
    }


def _target_task_id(offset_r: float, offset_z: float, offset_ip: float) -> str:
    def mm(value: float) -> str:
        number = int(round(value * 1000.0))
        return ("p" if number >= 0 else "m") + str(abs(number)) + "mm"

    def amps(value: float) -> str:
        number = int(round(value))
        return ("p" if number >= 0 else "m") + str(abs(number)) + "A"

    return f"R_{mm(offset_r)}__Z_{mm(offset_z)}__Ip_{amps(offset_ip)}"


def build_target_tasks(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for index, raw in enumerate(cfg["target_library"]["targets"]):
        offset_r = float(raw.get("R_offset_m", 0.0))
        offset_z = float(raw.get("Z_offset_m", 0.0))
        offset_ip = float(raw.get("Ip_offset_A", 0.0))
        task_id = str(raw.get("task_id") or _target_task_id(offset_r, offset_z, offset_ip))
        tasks.append(
            {
                "task_index": index,
                "task_id": task_id,
                "R_offset_m": offset_r,
                "Z_offset_m": offset_z,
                "Ip_offset_A": offset_ip,
                "mandatory": bool(raw.get("mandatory", False)),
                "category": str(raw.get("category", "target")),
                "description": str(raw.get("description", "")),
            }
        )
    ids = [str(row["task_id"]) for row in tasks]
    if not tasks or len(ids) != len(set(ids)):
        raise ValueError("target_library.targets must be nonempty with unique task_id values")
    if not any(row["mandatory"] for row in tasks):
        raise ValueError("at least one target-library task must be mandatory")
    nominal = [row for row in tasks if abs(row["R_offset_m"]) < 1e-15 and abs(row["Z_offset_m"]) < 1e-15 and abs(row["Ip_offset_A"]) < 1e-9]
    if len(nominal) != 1:
        raise ValueError("target library must contain exactly one zero-offset nominal task")
    return tasks


def validate_stage33_config(cfg: dict[str, Any]) -> None:
    trajectory = cfg["trajectory"]
    if int(trajectory.get("horizon_steps", -1)) != 25 or int(trajectory.get("horizon_ms", -1)) != 250:
        raise ValueError("Stage3.3 remains fixed to 25 steps / 250 ms")
    if int(trajectory.get("n_modes", -1)) != 3:
        raise ValueError("Stage3.3 requires the three validated SVD modes")
    lower = np.asarray(trajectory.get("coefficient_lower", []), dtype=float)
    upper = np.asarray(trajectory.get("coefficient_upper", []), dtype=float)
    if lower.shape != (3,) or upper.shape != (3,) or np.any(lower >= upper) or not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)):
        raise ValueError("trajectory coefficient bounds must be finite three-vectors")

    gate = cfg["gate"]
    fixed = {
        "precise_tolerance_m": 0.03,
        "relaxed_tolerance_m": 0.04,
        "terminal_velocity_max_m_per_s": 0.10,
        "late_velocity_rms_max_m_per_s": 0.10,
        "ip_safety_tolerance_A": 10000.0,
    }
    for key, expected in fixed.items():
        value = float(gate.get(key, math.nan))
        tolerance = 1e-12 if expected < 1000 else 1e-9
        if not math.isclose(value, expected, rel_tol=0.0, abs_tol=tolerance):
            raise ValueError(f"Stage3.3 hard gate {key} must remain {expected}")
    if list(gate.get("allowed_arrival_steps", [])) != [12, 13, 14, 15]:
        raise ValueError("allowed arrival steps must remain [12,13,14,15]")
    if int(gate.get("hold_through_step", -1)) != 25 or int(gate.get("required_arrival_streak_steps", 0)) != 3:
        raise ValueError("Stage3.3 must hold through step25 after a three-sample arrival")
    ip_tracking = gate["ip_tracking"]
    for key, expected in EXPECTED_IP_TRACKING_TOLERANCES_A.items():
        value = float(ip_tracking.get(key, math.nan))
        if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                f"Stage3.3 {IP_TRACKING_GATE_REVISION} requires "
                f"gate.ip_tracking.{key}={expected}, got {value}"
            )
    revision = str(ip_tracking.get("revision", IP_TRACKING_GATE_REVISION))
    if revision != IP_TRACKING_GATE_REVISION:
        raise ValueError(
            f"gate.ip_tracking.revision must be {IP_TRACKING_GATE_REVISION!r}, got {revision!r}"
        )

    tasks = build_target_tasks(cfg)
    if len(tasks) > int(cfg["target_library"].get("maximum_targets", 24)):
        raise ValueError("target library exceeds configured maximum_targets")
    scales = [float(value) for value in cfg["warmstart"]["correction_scales"]]
    if 0.0 not in scales or len(scales) < 3 or any(value < 0.0 for value in scales):
        raise ValueError("warmstart correction_scales must include 0 and at least two positive values")
    reduced_rank = int(cfg["refinement"].get("reduced_rank", 0))
    if not 1 <= reduced_rank <= 24:
        raise ValueError("refinement.reduced_rank must be in [1,24]")
    if int(cfg["refinement"].get("max_rounds", 0)) < 0:
        raise ValueError("refinement.max_rounds must be nonnegative")
    if len(cfg["refinement"].get("proposal_requests", [])) < 3:
        raise ValueError("refinement requires at least three proposal requests")
    model_revision = str(
        cfg["refinement"].get("model_revision", REFINEMENT_MODEL_REVISION)
    )
    if model_revision != REFINEMENT_MODEL_REVISION:
        raise ValueError(
            "refinement.model_revision must be "
            f"{REFINEMENT_MODEL_REVISION!r}, got {model_revision!r}"
        )
    refinement_bounds = {
        "minimum_measured_directions": (0, reduced_rank),
        "minimum_usable_directions": (1, reduced_rank),
        "minimum_normalized_model_rank": (1, reduced_rank),
    }
    for key, (lower_bound, upper_bound) in refinement_bounds.items():
        value = int(cfg["refinement"].get(key, lower_bound))
        if not lower_bound <= value <= upper_bound:
            raise ValueError(
                f"refinement.{key} must lie in [{lower_bound},{upper_bound}]"
            )
    positive_refinement_values = (
        "minimum_probe_coordinate",
        "minimum_normalized_probe_signal",
        "curvature_ratio_soft_limit",
        "prior_difference_soft_limit",
        "residual_ratio_soft_limit",
        "minimum_measured_direction_scale",
        "source_prior_direction_scale",
        "minimum_confidence_for_measured_reliable",
    )
    for key in positive_refinement_values:
        value = float(cfg["refinement"].get(key, 0.0))
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"refinement.{key} must be finite and positive")
    bound_margin = float(cfg["refinement"].get("probe_bound_margin", 0.95))
    if not 0.0 < bound_margin <= 1.0:
        raise ValueError("refinement.probe_bound_margin must lie in (0,1]")

    mpc = cfg["mpc"]
    if int(mpc.get("library_neighbors", 0)) < 1:
        raise ValueError("mpc.library_neighbors must be positive")
    if not mpc.get("controller_scales"):
        raise ValueError("mpc.controller_scales cannot be empty")
    if not mpc.get("calibration_scenarios") or not mpc.get("holdout_scenarios"):
        raise ValueError("Stage3.3 requires separate calibration and holdout scenarios")
    calibration_names = {str(row["scenario"]) for row in mpc["calibration_scenarios"]}
    holdout_names = {str(row["scenario"]) for row in mpc["holdout_scenarios"]}
    if len(calibration_names) != len(mpc["calibration_scenarios"]) or len(holdout_names) != len(mpc["holdout_scenarios"]):
        raise ValueError("MPC scenario names must be unique within each split")
    if calibration_names & holdout_names:
        raise ValueError("calibration and holdout scenario names must be disjoint")
    per_mode = np.asarray(mpc.get("per_step_feedback_limit_by_mode", []), dtype=float)
    if per_mode.shape != (3,) or np.any(per_mode <= 0.0):
        raise ValueError("mpc.per_step_feedback_limit_by_mode must be a positive three-vector")


def load_stage33_config(
    config_path: str | Path,
    *,
    source_stage32_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage33Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    tsc_all_root = Path(os.environ.get("TSC_ALL_ROOT", project_dir.parent)).expanduser().resolve()
    cfg = base.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(tsc_all_root)},
    )
    validate_stage33_config(cfg)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage3_3_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage3_3_target_conditioned_rh_mpc_250ms')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)

    source32 = resolve_source_stage32_run(source_stage32_run)
    source31 = resolve_stage31_from_stage32(source32, project_dir)
    source32_cfg = read_json(source32 / "stage3_2_config.resolved.json")
    for key in ("R", "Z", "Ip"):
        if not math.isclose(float(cfg["target"][key]), float(source32_cfg["target"][key]), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Stage3.3 base target {key} differs from Stage3.2")
    for key in ("precise_tolerance_m", "relaxed_tolerance_m", "terminal_velocity_max_m_per_s", "late_velocity_rms_max_m_per_s"):
        if not math.isclose(float(cfg["gate"][key]), float(source32_cfg["gate"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage3.3 hard gate {key} differs from Stage3.2")

    base32 = s32.load_stage32_config(
        source32 / "stage3_2_config.resolved.json",
        source_stage31_run=source31,
        run_dir_override=run_dir,
    )
    train_cfg = copy.deepcopy(base32.train_cfg)
    env_cfg = copy.deepcopy(base32.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg.get("runtime", {}).get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    storage = cfg.get("storage", {})
    workspace = _resolve_storage(os.environ.get("STAGE3_3_TSC_WORKSPACE_ROOT") or storage.get("tsc_workspace_root"), project_dir)
    run_root = _resolve_storage(os.environ.get("STAGE3_3_TSC_RUN_ROOT") or storage.get("tsc_run_root"), project_dir)
    if workspace:
        env_cfg["tsc_workspace_root"] = workspace
    if run_root:
        env_cfg["run_root"] = run_root
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 25
    train_cfg.setdefault("target", {}).update(copy.deepcopy(cfg["target"]))

    bundle = read_json(source32 / "stage3_2_controller/mpc_poc_bundle.json")
    center = read_json(source32 / "stage3_2_best/long_hold_best_candidate.json")
    best = read_json(source32 / "stage3_2_best/controller_identification_best_candidate.json")
    center_result = read_json_gz(source32 / "stage3_2_best/long_hold_best_tsc_result.json.gz")
    best_result = read_json_gz(source32 / "stage3_2_best/controller_identification_best_tsc_result.json.gz")
    if np.asarray(bundle.get("jacobian_physical_units", [])).shape != (125, 75):
        raise ValueError("Stage3.2 controller bundle must contain a 125x75 Jacobian")
    if _vector(center["full_control_vector"], 75).shape != (75,) or _vector(best["full_control_vector"], 75).shape != (75,):
        raise ValueError("Stage3.2 source candidates must contain 75 control coefficients")
    fingerprint = _source_inventory(source32)
    tasks = build_target_tasks(cfg)
    return Stage33Context(
        cfg=cfg,
        train_cfg=train_cfg,
        env_cfg=env_cfg,
        paths=Stage33Paths.from_run_dir(run_dir),
        source_stage32_run=source32,
        source_stage31_run=source31,
        base32=base32,
        modes_tsc=np.asarray(base32.modes_tsc, dtype=float),
        initial_currents_tsc=np.asarray(base32.initial_currents_tsc, dtype=float),
        max_delta_a=float(base32.max_delta_a),
        min_current_tsc=np.asarray(base32.min_current_tsc, dtype=float),
        max_current_tsc=np.asarray(base32.max_current_tsc, dtype=float),
        source_bundle=bundle,
        source_center=center,
        source_best=best,
        source_center_result=center_result,
        source_best_result=best_result,
        target_tasks=tasks,
        source_fingerprint=fingerprint,
    )


def initialize_stage33_run(ctx: Stage33Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.warmstart,
        ctx.paths.refinement,
        ctx.paths.library,
        ctx.paths.controller,
        ctx.paths.calibration,
        ctx.paths.holdout,
        ctx.paths.confirmations,
        ctx.paths.analysis,
        ctx.paths.best,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    existing_config_path = ctx.paths.run_dir / "stage3_3_config.resolved.json"
    if ctx.paths.manifest.exists():
        old_manifest = read_json(ctx.paths.manifest)
        old_tolerances = old_manifest.get("ip_tracking_tolerances_A")
        if old_tolerances is None and existing_config_path.exists():
            old_cfg = read_json(existing_config_path)
            old_tolerances = (old_cfg.get("gate") or {}).get("ip_tracking")
        if old_tolerances is None:
            raise ValueError(
                "Existing Stage3.3 run predates the doubled Ip-tracking gate revision; "
                "start a fresh Stage3.3 run instead of resuming it."
            )
        for key, expected in EXPECTED_IP_TRACKING_TOLERANCES_A.items():
            value = float(old_tolerances.get(key, math.nan))
            if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(
                    "Existing Stage3.3 run uses different Ip-tracking tolerances; "
                    "start a fresh run so previously evaluated candidates are not re-scored "
                    "under a different gate."
                )

    atomic_write_json(existing_config_path, ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.env_cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "source_stage3_2_run": str(ctx.source_stage32_run),
        "source_stage3_1_run": str(ctx.source_stage31_run),
        "source_fingerprint": {key: value for key, value in ctx.source_fingerprint.items() if key != "entries"},
        "base_target": copy.deepcopy(ctx.cfg["target"]),
        "horizon_steps": 25,
        "horizon_ms": 250,
        "n_modes": 3,
        "target_library_size": len(ctx.target_tasks),
        "mandatory_target_count": sum(bool(row["mandatory"]) for row in ctx.target_tasks),
        "hard_gate_changed_from_stage3_2": False,
        "ip_tracking_gate_added": True,
        "ip_tracking_revision": IP_TRACKING_GATE_REVISION,
        "ip_tracking_tolerances_A": copy.deepcopy(EXPECTED_IP_TRACKING_TOLERANCES_A),
        "refinement_model_revision": REFINEMENT_MODEL_REVISION,
        "controller_type": "target-conditioned library plus receding-horizon bounded least-squares MPC POC",
        "online_feedback_validated": False,
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "noise_delay_robustness_validated": False,
        "final_task": "robust causal feedback across initial states, targets, plant uncertainty, noise, and delay",
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if Path(old["source_stage3_2_run"]).resolve() != ctx.source_stage32_run:
            raise ValueError("Existing Stage3.3 run points to a different Stage3.2 source")
        old_digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        if old_digest and old_digest != str(ctx.source_fingerprint["digest"]):
            raise ValueError("Stage3.2 source content changed since this Stage3.3 run was prepared")
        if str(old.get("ip_tracking_revision", "")) != IP_TRACKING_GATE_REVISION:
            raise ValueError(
                "Existing Stage3.3 manifest uses a different Ip-tracking revision; "
                "start a fresh run."
            )
        # The refinement fix is intentionally resume-compatible with runs that
        # already completed warm starts and real-TSC probe waves.  Record the
        # upgraded model revision, but do not invalidate those expensive raw
        # trajectories: the revised Jacobian builder consumes their stored
        # actual coordinates and re-fits the model dimensionlessly.
        if str(old.get("refinement_model_revision", "")) != REFINEMENT_MODEL_REVISION:
            old["refinement_model_revision"] = REFINEMENT_MODEL_REVISION
            old["refinement_model_revision_updated_utc"] = utc_timestamp()
            atomic_write_json(ctx.paths.manifest, old)
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.source_catalog.exists():
        atomic_write_json(
            ctx.paths.source_catalog,
            {
                "source_center_candidate_id": ctx.source_center["candidate_id"],
                "source_best_candidate_id": ctx.source_best["candidate_id"],
                "target_tasks": ctx.target_tasks,
            },
        )
    inventory_path = ctx.paths.source_reference / "source_content_inventory.json"
    if inventory_path.exists():
        previous = read_json(inventory_path)
        if str(previous.get("digest", "")) != str(ctx.source_fingerprint["digest"]):
            raise ValueError("Stored Stage3.2 source fingerprint differs from current source")
    else:
        atomic_write_json(inventory_path, ctx.source_fingerprint)
    for relative in (
        "stage3_2_config.resolved.json",
        "stage3_2_manifest.json",
        "stage3_2_state.json",
        "stage3_2_analysis/stage3_2_analysis_summary.json",
        "stage3_2_analysis/long_hold_strict_hall_of_fame.json",
        "stage3_2_controller/mpc_poc_bundle.json",
        "stage3_2_feedback_validation/feedback_validation_summary.json",
        "stage3_2_confirmations/stage3_2_verdict.json",
        "stage3_2_best/controller_identification_best_candidate.json",
        "stage3_2_best/long_hold_best_candidate.json",
        "STAGE3_2_REPORT.md",
    ):
        src = ctx.source_stage32_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# Control decoding, target metrics, generic open-loop evaluation
# ---------------------------------------------------------------------------


def clip_control(ctx: Stage33Context, vector: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(vector, dtype=float).reshape(25, 3)
    lower = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    return np.clip(coefficients, lower[None, :], upper[None, :]).reshape(-1)


def decode_control(ctx: Stage33Context, vector: np.ndarray) -> dict[str, Any]:
    return s32.decode_full_sequence(ctx.base32, clip_control(ctx, vector))


def target_absolute(ctx: Stage33Context, task: dict[str, Any]) -> np.ndarray:
    return np.asarray(
        [
            float(ctx.cfg["target"]["R"]) + float(task.get("R_offset_m", 0.0)),
            float(ctx.cfg["target"]["Z"]) + float(task.get("Z_offset_m", 0.0)),
            float(ctx.cfg["target"]["Ip"]) + float(task.get("Ip_offset_A", 0.0)),
        ],
        dtype=float,
    )


def _task_context(ctx: Stage33Context, task: dict[str, Any]) -> s32.Stage32Context:
    shifted = copy.copy(ctx.base32)
    shifted.cfg = copy.deepcopy(ctx.base32.cfg)
    target = target_absolute(ctx, task)
    shifted.cfg["target"] = {"R": float(target[0]), "Z": float(target[1]), "Ip": float(target[2])}
    return shifted


def target_metrics(
    ctx: Stage33Context,
    task: dict[str, Any],
    result: dict[str, Any],
    decoded: dict[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate one trajectory against the shifted target and tighter Ip gate.

    Stage3.2 chooses its endpoint using only the inherited hard safety gate.
    Stage3.3 adds a much tighter Ip *tracking* requirement, so the best hard-gate
    endpoint is not necessarily the best combined tracking endpoint.  Evaluate
    every allowed endpoint and select using the combined signed margin rather
    than attaching the Ip metric to Stage3.2's pre-selected endpoint.
    """
    shifted = _task_context(ctx, task)
    metrics = dict(s32.stage32_metrics(shifted, result, decoded, horizon=25))
    if not metrics.get("success"):
        metrics.update(
            {
                "stage3_3_ip_terminal_abs_error_A": 1e12,
                "stage3_3_ip_hold_rms_error_A": 1e12,
                "stage3_3_ip_sustained_max_error_A": 1e12,
                "stage3_3_ip_tracking_pass": False,
                "stage3_3_target_tracking_pass": False,
                "stage3_3_tracking_minimum_signed_margin": -1e12,
                "stage3_3_tracking_objective": 1e12,
                "stage3_3_endpoint_evaluations": [],
            }
        )
        return metrics

    trajectory = result["trajectory"]
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    target = target_absolute(ctx, task)
    error = y - target[None, :]
    ip_error = error[:, 2]
    ip_cfg = ctx.cfg["gate"]["ip_tracking"]
    ip_terminal = float(abs(ip_error[-1]))
    ip_terminal_margin = 1.0 - ip_terminal / float(ip_cfg["terminal_abs_tolerance_A"])

    endpoint_rows: list[dict[str, Any]] = []
    for hard in metrics.get("stage3_2_endpoint_evaluations", []):
        endpoint = int(hard["endpoint_step"])
        window_start = int(hard["window_start_step"])
        hold_ip = ip_error[window_start:]
        ip_hold_rms = float(np.sqrt(np.mean(hold_ip**2)))
        ip_sustained_max = float(np.max(np.abs(hold_ip)))
        ip_margins = np.asarray(
            [
                ip_terminal_margin,
                1.0 - ip_hold_rms / float(ip_cfg["hold_rms_tolerance_A"]),
                1.0 - ip_sustained_max / float(ip_cfg["sustained_max_tolerance_A"]),
            ],
            dtype=float,
        )
        hard_margin = float(hard["minimum_signed_margin"])
        combined = np.concatenate([np.asarray([hard_margin], dtype=float), ip_margins])
        combined_min = float(np.min(combined))
        combined_mean = float(np.mean(combined))
        tracking_pass = bool(hard.get("pass", False) and np.min(ip_margins) >= -1e-12)
        endpoint_rows.append(
            {
                **copy.deepcopy(hard),
                "stage3_3_ip_terminal_abs_error_A": ip_terminal,
                "stage3_3_ip_hold_rms_error_A": ip_hold_rms,
                "stage3_3_ip_sustained_max_error_A": ip_sustained_max,
                "stage3_3_ip_terminal_signed_margin": float(ip_margins[0]),
                "stage3_3_ip_hold_rms_signed_margin": float(ip_margins[1]),
                "stage3_3_ip_sustained_signed_margin": float(ip_margins[2]),
                "stage3_3_ip_tracking_pass": bool(np.min(ip_margins) >= -1e-12),
                "stage3_3_target_tracking_pass": tracking_pass,
                "stage3_3_tracking_minimum_signed_margin": combined_min,
                "stage3_3_tracking_mean_signed_margin": combined_mean,
            }
        )
    if not endpoint_rows:
        raise RuntimeError("Stage3.2 metrics did not provide endpoint evaluations")

    passing = [row for row in endpoint_rows if row["stage3_3_target_tracking_pass"]]
    pool = passing if passing else endpoint_rows
    chosen = max(
        pool,
        key=lambda row: (
            float(row["stage3_3_tracking_minimum_signed_margin"]),
            float(row["stage3_3_tracking_mean_signed_margin"]),
            -int(row["endpoint_step"]),
        ),
    )
    ip_pass = bool(chosen["stage3_3_ip_tracking_pass"])
    tracking_pass = bool(chosen["stage3_3_target_tracking_pass"])
    tracking_margin = float(chosen["stage3_3_tracking_minimum_signed_margin"])
    position_scale = float(ctx.cfg["gate"]["precise_tolerance_m"])
    speed_scale = float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"])
    terminal_rz = float(metrics["terminal_RZ_euclidean_error_m"])
    ip_hold_rms = float(chosen["stage3_3_ip_hold_rms_error_A"])
    tracking_objective = float(
        -80.0 * tracking_margin
        + 2.0 * (terminal_rz / max(position_scale, 1e-12)) ** 2
        + 1.5 * (float(chosen["post_arrival_velocity_rms_m_per_s"]) / speed_scale) ** 2
        + 0.5 * (ip_hold_rms / float(ip_cfg["hold_rms_tolerance_A"])) ** 2
        + 0.25 * (ip_terminal / float(ip_cfg["terminal_abs_tolerance_A"])) ** 2
        + 0.02 * float(metrics.get("action_rms", 0.0)) ** 2
        + 0.05 * float(metrics.get("delta_action_rms", 0.0)) ** 2
        + 2.0 * float(metrics.get("repair_excess_rms", 0.0)) ** 2
    )
    metrics.update(
        {
            "stage3_3_task_id": str(task["task_id"]),
            "stage3_3_target_R": float(target[0]),
            "stage3_3_target_Z": float(target[1]),
            "stage3_3_target_Ip": float(target[2]),
            "stage3_3_best_endpoint_step": int(chosen["endpoint_step"]),
            "stage3_3_best_endpoint_ms": int(chosen["arrival_time_ms"]),
            "stage3_3_window_start_step": int(chosen["window_start_step"]),
            "stage3_3_sustained_box_max_error_m": float(chosen["sustained_box_max_error_m"]),
            "stage3_3_endpoint_velocity_m_per_s": float(chosen["endpoint_velocity_m_per_s"]),
            "stage3_3_endpoint_late_velocity_rms_m_per_s": float(chosen["endpoint_late_velocity_rms_m_per_s"]),
            "stage3_3_post_arrival_velocity_rms_m_per_s": float(chosen["post_arrival_velocity_rms_m_per_s"]),
            "stage3_3_final_velocity_m_per_s": float(chosen["final_velocity_m_per_s"]),
            "stage3_3_sustained_Ip_safety_max_error_A": float(chosen["sustained_Ip_max_error_A"]),
            "stage3_3_hard_minimum_signed_margin": float(chosen["minimum_signed_margin"]),
            "stage3_3_ip_terminal_abs_error_A": ip_terminal,
            "stage3_3_ip_hold_rms_error_A": ip_hold_rms,
            "stage3_3_ip_sustained_max_error_A": float(chosen["stage3_3_ip_sustained_max_error_A"]),
            "stage3_3_ip_terminal_signed_margin": float(chosen["stage3_3_ip_terminal_signed_margin"]),
            "stage3_3_ip_hold_rms_signed_margin": float(chosen["stage3_3_ip_hold_rms_signed_margin"]),
            "stage3_3_ip_sustained_signed_margin": float(chosen["stage3_3_ip_sustained_signed_margin"]),
            "stage3_3_ip_tracking_pass": ip_pass,
            "stage3_3_target_tracking_pass": tracking_pass,
            "stage3_3_tracking_minimum_signed_margin": tracking_margin,
            "stage3_3_tracking_mean_signed_margin": float(chosen["stage3_3_tracking_mean_signed_margin"]),
            "stage3_3_tracking_objective": tracking_objective,
            "stage3_3_endpoint_evaluations": endpoint_rows,
            "selection_score": tracking_objective if tracking_pass else 1e6 + 1e5 * max(-tracking_margin, 0.0) + tracking_objective,
        }
    )
    return metrics


def candidate_id(prefix: str, task_id: str, vector: np.ndarray, *metadata: Any) -> str:
    digest = hashlib.sha256()
    digest.update(np.round(np.asarray(vector, dtype=float).reshape(-1), 10).tobytes())
    digest.update(task_id.encode("utf-8"))
    for item in metadata:
        digest.update(b"|")
        digest.update(str(item).encode("utf-8"))
    return f"{prefix}_{digest.hexdigest()[:16]}"


def open_loop_spec(ctx: Stage33Context, row: dict[str, Any], *, phase: str, population_index: int) -> dict[str, Any]:
    vector = clip_control(ctx, _vector(row["full_control_vector"], 75))
    decoded = decode_control(ctx, vector)
    task = row["task"]
    return {
        "kind": "stage3_3_target_nominal",
        "experiment_id": str(row["candidate_id"]),
        "candidate_id": str(row["candidate_id"]),
        "phase": phase,
        "population_index": int(population_index),
        "task_id": str(task["task_id"]),
        "target_R_offset_m": float(task["R_offset_m"]),
        "target_Z_offset_m": float(task["Z_offset_m"]),
        "target_Ip_offset_A": float(task["Ip_offset_A"]),
        "source_name": str(row.get("source_name", "unknown")),
        "source_type": str(row.get("source_type", "unknown")),
        "parent_candidate_id": row.get("parent_candidate_id"),
        "horizon_steps": 25,
        "full_control_vector": vector.tolist(),
        "mode_coefficients": decoded["mode_coefficients"].tolist(),
        "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
        "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
    }


def evaluate_open_loop_rows(
    ctx: Stage33Context,
    rows: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    phase: str,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = [open_loop_spec(ctx, row, phase=phase, population_index=index) for index, row in enumerate(rows)]
    results = s2.evaluate_specs(ctx.base32, specs, output_dir=output_dir, backend=backend, resume=resume)
    by_id = {str(result["experiment_id"]): result for result in results}
    output: list[dict[str, Any]] = []
    for row in rows:
        candidate = copy.deepcopy(row)
        result = by_id.get(str(candidate["candidate_id"]))
        vector = _vector(candidate["full_control_vector"], 75)
        decoded = decode_control(ctx, vector)
        metrics = target_metrics(
            ctx,
            candidate["task"],
            result if result is not None else {"success": False, "failure_reason": "missing result"},
            decoded,
        )
        candidate["result_relpath"] = None if result is None else str((output_dir / f"{candidate['candidate_id']}.json.gz").relative_to(ctx.paths.run_dir))
        candidate.update(metrics)
        output.append(candidate)
    output.sort(key=library_sort_key)
    for rank, row in enumerate(output, 1):
        row["phase_rank"] = rank
    return output


def library_sort_key(row: dict[str, Any]) -> tuple[float, float, float, str]:
    return (
        0.0 if _as_bool(row.get("stage3_3_target_tracking_pass"), False) else 1.0,
        -_finite(row.get("stage3_3_tracking_minimum_signed_margin"), -1e12),
        _finite(row.get("stage3_3_tracking_objective"), 1e12),
        str(row.get("candidate_id", "")),
    )


def best_by_task(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_id = str(row["task"]["task_id"] if isinstance(row.get("task"), dict) else row.get("task_id", ""))
        if not task_id:
            continue
        if task_id not in best or library_sort_key(row) < library_sort_key(best[task_id]):
            best[task_id] = copy.deepcopy(row)
    return best


# ---------------------------------------------------------------------------
# Phase A: Stage3.2-Jacobian target-conditioned warm starts
# ---------------------------------------------------------------------------


def _source_feature(ctx: Stage33Context) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    bundle = ctx.source_bundle
    center_feature = np.asarray(bundle["center_feature_physical_units"], dtype=float)
    jacobian = np.asarray(bundle["jacobian_physical_units"], dtype=float)
    scales = np.asarray(bundle["output_scales"], dtype=float)
    weights = np.asarray(bundle["output_weights"], dtype=float)
    radius = np.asarray(bundle["control_radius"], dtype=float)
    if center_feature.shape != (125,) or jacobian.shape != (125, 75) or scales.shape != (125,) or weights.shape != (125,) or radius.shape != (75,):
        raise ValueError("Stage3.2 controller bundle has inconsistent dimensions")
    return center_feature, jacobian, scales, weights, radius


def _target_feature_shift(task: dict[str, Any]) -> np.ndarray:
    shift = np.zeros(125, dtype=float)
    shift[0:25] = -float(task["R_offset_m"])
    shift[25:50] = -float(task["Z_offset_m"])
    shift[100:125] = -float(task["Ip_offset_A"])
    return shift


def _difference_matrix(n_steps: int, n_modes: int = 3) -> np.ndarray:
    rows: list[np.ndarray] = []
    for step in range(1, n_steps):
        for mode in range(n_modes):
            row = np.zeros(n_steps * n_modes, dtype=float)
            row[(step - 1) * n_modes + mode] = -1.0
            row[step * n_modes + mode] = 1.0
            rows.append(row)
    return np.vstack(rows) if rows else np.zeros((0, n_steps * n_modes), dtype=float)


def solve_target_feedforward(ctx: Stage33Context, task: dict[str, Any]) -> dict[str, Any]:
    try:
        from scipy.optimize import lsq_linear
    except Exception as exc:  # pragma: no cover - server dependency
        raise RuntimeError("scipy is required for Stage3.3 target feed-forward solves") from exc
    center_feature, jacobian, scales, weights, radius_source = _source_feature(ctx)
    center_vector = clip_control(ctx, _vector(ctx.source_center["full_control_vector"], 75))
    target_error = center_feature + _target_feature_shift(task)
    warm = ctx.cfg["warmstart"]
    selected_states = [int(value) for value in warm["tracking_states"]]
    rows: list[int] = []
    for block in range(5):
        for state in selected_states:
            if not 1 <= state <= 25:
                raise ValueError("warmstart tracking state must be in [1,25]")
            rows.append(block * 25 + (state - 1))
    rows_array = np.asarray(rows, dtype=int)
    a = jacobian[rows_array] / scales[rows_array, None]
    b = -(target_error[rows_array] / scales[rows_array])
    w = np.sqrt(np.maximum(weights[rows_array], 0.0))
    a = w[:, None] * a
    b = w * b
    radius_cfg = np.asarray(warm["control_radius_by_step_mode"], dtype=float)
    if radius_cfg.shape != (25, 3):
        raise ValueError("warmstart.control_radius_by_step_mode must be 25x3")
    radius = np.minimum(radius_source, radius_cfg.reshape(-1))
    lower_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    lower = np.maximum(-radius, np.tile(lower_mode, 25) - center_vector)
    upper = np.minimum(radius, np.tile(upper_mode, 25) - center_vector)
    ridge = float(warm.get("ridge_lambda", 0.04))
    smooth = float(warm.get("temporal_smoothness", 0.05))
    action = float(warm.get("correction_energy", 0.02))
    augmented_a = [a]
    augmented_b = [b]
    if ridge + action > 0.0:
        augmented_a.append(math.sqrt(ridge + action) * np.diag(1.0 / np.maximum(radius, 1e-9)))
        augmented_b.append(np.zeros(75, dtype=float))
    if smooth > 0.0:
        difference = _difference_matrix(25)
        augmented_a.append(math.sqrt(smooth) * difference)
        augmented_b.append(np.zeros(difference.shape[0], dtype=float))
    solution = lsq_linear(
        np.vstack(augmented_a),
        np.concatenate(augmented_b),
        bounds=(lower, upper),
        method="trf",
        tol=float(warm.get("solver_tolerance", 1e-10)),
        max_iter=int(warm.get("solver_max_iterations", 500)),
        lsmr_tol="auto",
        verbose=0,
    )
    delta = np.asarray(solution.x, dtype=float)
    predicted = target_error + jacobian @ delta
    return {
        "delta": delta,
        "predicted_feature": predicted,
        "solver_success": bool(solution.success),
        "solver_status": int(solution.status),
        "solver_message": str(solution.message),
        "solver_cost": float(solution.cost),
        "active_lower": int(np.sum(np.isclose(delta, lower, atol=1e-7))),
        "active_upper": int(np.sum(np.isclose(delta, upper, atol=1e-7))),
        "radius": radius,
    }


def build_warmstart_manifest(ctx: Stage33Context) -> dict[str, Any]:
    manifest_path = ctx.paths.warmstart / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)
    source_center = clip_control(ctx, _vector(ctx.source_center["full_control_vector"], 75))
    source_best = clip_control(ctx, _vector(ctx.source_best["full_control_vector"], 75))
    scales = [float(value) for value in ctx.cfg["warmstart"]["correction_scales"]]
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task in ctx.target_tasks:
        solve = solve_target_feedforward(ctx, task)
        for scale in scales:
            base = source_best if scale == 0.0 else source_center
            vector = clip_control(ctx, base + scale * solve["delta"])
            cid = candidate_id("s33warm", str(task["task_id"]), vector, scale)
            if cid in seen:
                continue
            seen.add(cid)
            candidates.append(
                {
                    "candidate_id": cid,
                    "task": copy.deepcopy(task),
                    "full_control_vector": vector.tolist(),
                    "source_name": f"linear_correction_scale_{scale:.2f}",
                    "source_type": "stage3_2_jacobian_warmstart",
                    "parent_candidate_id": str(ctx.source_best["candidate_id"] if scale == 0.0 else ctx.source_center["candidate_id"]),
                    "correction_scale": scale,
                    "linear_solver_success": bool(solve["solver_success"]),
                    "linear_solver_status": int(solve["solver_status"]),
                    "linear_solver_cost": float(solve["solver_cost"]),
                    "linear_active_lower": int(solve["active_lower"]),
                    "linear_active_upper": int(solve["active_upper"]),
                }
            )
    for index, row in enumerate(candidates):
        row["population_index"] = index
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "phase": "target_nominal_warmstart",
        "created_utc": utc_timestamp(),
        "horizon_steps": 25,
        "n_targets": len(ctx.target_tasks),
        "n_candidates": len(candidates),
        "candidates": candidates,
    }
    atomic_write_json(manifest_path, manifest)
    return manifest


def run_warmstart(ctx: Stage33Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    summary_path = ctx.paths.warmstart / "warmstart_summary.json"
    if state.get("warmstart_complete") and summary_path.exists():
        return read_json(summary_path)
    manifest = build_warmstart_manifest(ctx)
    rows = evaluate_open_loop_rows(
        ctx,
        manifest["candidates"],
        output_dir=ctx.paths.warmstart / "raw",
        phase="target_nominal_warmstart",
        backend=backend,
        resume=resume,
    )
    atomic_write_json(ctx.paths.warmstart / "warmstart_results.json", rows)
    write_csv(ctx.paths.warmstart / "warmstart_results.csv", rows)
    best = best_by_task(rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "phase": "target_nominal_warmstart",
        "created_utc": utc_timestamp(),
        "n_targets": len(ctx.target_tasks),
        "n_candidates": len(rows),
        "n_successful": sum(_as_bool(row.get("success"), False) for row in rows),
        "n_targets_tracking_pass": sum(_as_bool(row.get("stage3_3_target_tracking_pass"), False) for row in best.values()),
        "mandatory_targets_tracking_pass": sum(
            _as_bool(best.get(str(task["task_id"]), {}).get("stage3_3_target_tracking_pass"), False)
            for task in ctx.target_tasks
            if task["mandatory"]
        ),
        "best_by_task": {task_id: row for task_id, row in best.items()},
    }
    atomic_write_json(summary_path, summary)
    state["warmstart_complete"] = True
    state["warmstart_targets_passed"] = int(summary["n_targets_tracking_pass"])
    atomic_write_json(ctx.paths.state, state)
    return summary


# ---------------------------------------------------------------------------
# Phase B: reduced real-TSC refinement for targets that remain infeasible
# ---------------------------------------------------------------------------


def reduced_control_basis(ctx: Stage33Context) -> dict[str, Any]:
    cache = ctx.paths.refinement / "reduced_control_basis.json"
    if cache.exists():
        return read_json(cache)
    _, jacobian, scales, weights, radius_source = _source_feature(ctx)
    cfg = ctx.cfg["refinement"]
    tracking_states = [int(value) for value in cfg["tracking_states"]]
    rows: list[int] = []
    for block in range(5):
        for state in tracking_states:
            rows.append(block * 25 + (state - 1))
    rows_array = np.asarray(rows, dtype=int)
    radius_cfg = np.asarray(cfg["control_radius_by_step_mode"], dtype=float)
    if radius_cfg.shape != (25, 3):
        raise ValueError("refinement.control_radius_by_step_mode must be 25x3")
    radius = np.minimum(radius_source, radius_cfg.reshape(-1))
    a = np.sqrt(np.maximum(weights[rows_array], 0.0))[:, None] * (
        jacobian[rows_array] / scales[rows_array, None]
    )
    a_scaled = a * radius[None, :]
    _, singular, vt = np.linalg.svd(a_scaled, full_matrices=False)
    rank = min(int(cfg["reduced_rank"]), len(singular))
    basis = radius[:, None] * vt[:rank].T
    # Normalize every direction so one reduced-coordinate unit is inside the
    # configured physical control radius in every coefficient.
    relative = np.max(np.abs(basis) / np.maximum(radius[:, None], 1e-12), axis=0)
    basis = basis / np.maximum(relative[None, :], 1.0)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "rank": rank,
        "tracking_states": tracking_states,
        "selected_feature_indices": rows,
        "singular_values": singular.tolist(),
        "control_radius": radius.tolist(),
        "basis": basis.tolist(),
    }
    atomic_write_json(cache, payload)
    return payload


def aggregate_library_rows(ctx: Stage33Context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    warm = ctx.paths.warmstart / "warmstart_results.json"
    if warm.exists():
        payload = read_json(warm)
        if isinstance(payload, list):
            rows.extend(payload)
    for path in sorted(ctx.paths.refinement.glob("round_*/probe_results.json")):
        payload = read_json(path)
        if isinstance(payload, list):
            rows.extend(payload)
    for path in sorted(ctx.paths.refinement.glob("round_*/proposal_results.json")):
        payload = read_json(path)
        if isinstance(payload, list):
            rows.extend(payload)
    return rows


def load_result_for_candidate(ctx: Stage33Context, row: dict[str, Any]) -> dict[str, Any]:
    relative = str(row.get("result_relpath", "")).strip()
    if not relative:
        raise FileNotFoundError(f"candidate {row.get('candidate_id')} has no result_relpath")
    path = ctx.paths.run_dir / relative
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json_gz(path)


def _feature_for_task(ctx: Stage33Context, task: dict[str, Any], result: dict[str, Any]) -> np.ndarray:
    return s32.trajectory_feature_vector(
        ctx.base32,
        result,
        state_start=1,
        horizon=25,
        target_override=target_absolute(ctx, task),
    )


def active_refinement_targets(ctx: Stage33Context, rows: Sequence[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    best = best_by_task(rows)
    refine_optional = bool(ctx.cfg["refinement"].get("refine_optional_targets", True))
    active: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for task in ctx.target_tasks:
        center = best.get(str(task["task_id"]))
        if center is None:
            continue
        if _as_bool(center.get("stage3_3_target_tracking_pass"), False):
            continue
        if task["mandatory"] or refine_optional:
            active.append((task, center))
    active.sort(key=lambda pair: (0 if pair[0]["mandatory"] else 1, library_sort_key(pair[1])))
    maximum = int(ctx.cfg["refinement"].get("maximum_targets_per_round", len(active)))
    return active[:maximum]


def _control_bounds(ctx: Stage33Context) -> tuple[np.ndarray, np.ndarray]:
    lower_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    return np.tile(lower_mode, 25), np.tile(upper_mode, 25)


def _maximum_coordinate_room(
    center: np.ndarray,
    direction: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> tuple[float, float]:
    """Return feasible positive and negative coordinate magnitudes.

    Unlike componentwise clipping, stepping by one of these coordinates keeps
    the perturbation exactly collinear with the reduced direction.  This is
    important because the reduced basis is radius-scaled rather than Euclidean
    orthogonal in the original 75-dimensional coefficient space.
    """

    positive = float("inf")
    negative = float("inf")
    for value, component, low, high in zip(center, direction, lower, upper):
        if component > 1e-15:
            positive = min(positive, float((high - value) / component))
            negative = min(negative, float((value - low) / component))
        elif component < -1e-15:
            positive = min(positive, float((value - low) / (-component)))
            negative = min(negative, float((high - value) / (-component)))
    if not math.isfinite(positive):
        positive = 0.0
    if not math.isfinite(negative):
        negative = 0.0
    return max(positive, 0.0), max(negative, 0.0)


def _probe_coordinates_for_direction(
    ctx: Stage33Context,
    center: np.ndarray,
    direction: np.ndarray,
) -> tuple[list[float], str]:
    cfg = ctx.cfg["refinement"]
    requested = float(cfg.get("probe_scale", 0.24))
    margin = float(cfg.get("probe_bound_margin", 0.95))
    minimum = float(cfg.get("minimum_probe_coordinate", 1e-4))
    lower, upper = _control_bounds(ctx)
    positive_room, negative_room = _maximum_coordinate_room(
        center, direction, lower, upper
    )
    symmetric = min(requested, margin * positive_room, margin * negative_room)
    if symmetric >= minimum:
        return [-symmetric, symmetric], "two_sided_feasible"

    # A center can legitimately lie on a coefficient boundary.  In that case
    # use two inward secants on the roomier side instead of clipping a nominal
    # +/- pair into non-collinear perturbations.
    sign = 1.0 if positive_room >= negative_room else -1.0
    room = positive_room if sign > 0.0 else negative_room
    largest = min(requested, margin * room)
    if largest < minimum:
        raise RuntimeError("reduced direction has no finite probe room")
    smaller = max(minimum, 0.5 * largest)
    if smaller >= largest * (1.0 - 1e-9):
        return [sign * largest], "one_sided_single_feasible"
    return [sign * smaller, sign * largest], "one_sided_inward_secant"


def _refinement_quality_geometry(
    ctx: Stage33Context,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    basis_payload = reduced_control_basis(ctx)
    rows = np.asarray(basis_payload["selected_feature_indices"], dtype=int)
    scales = np.asarray(ctx.source_bundle["output_scales"], dtype=float)
    profile = str(ctx.cfg["refinement"].get("quality_profile", "balanced"))
    if profile not in ctx.cfg["refinement"]["profiles"]:
        raise ValueError(f"unknown refinement quality_profile {profile!r}")
    weights = _profile_weights(ctx, profile)
    if scales.shape != (125,) or weights.shape != (125,):
        raise ValueError("refinement quality geometry has inconsistent dimensions")
    return rows, scales, weights


def _normalized_weighted_norm(
    vector: np.ndarray,
    *,
    rows: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
) -> float:
    selected = np.asarray(vector, dtype=float)[rows]
    normalized = selected / np.maximum(scales[rows], 1e-12)
    normalized *= np.sqrt(np.maximum(weights[rows], 0.0))
    return float(np.linalg.norm(normalized))


def _fit_reduced_direction(
    ctx: Stage33Context,
    *,
    direction_index: int,
    samples: Sequence[tuple[float, np.ndarray, str]],
    source_slope: np.ndarray,
) -> dict[str, Any]:
    """Fit one local reduced derivative with a real-TSC/source prior blend.

    The previous implementation fitted a through-origin line to exactly two
    physical-unit samples and rejected a direction when the raw-unit residual
    exceeded a hard threshold.  That test mixes metres, m/s and amperes and
    treats symmetric second-order curvature as if it invalidated the central
    derivative.  For weak directions it can reject almost the whole reduced
    subspace even though every TSC rollout succeeded.

    Here a linear-plus-quadratic secant separates the central derivative from
    even curvature.  Quality is measured in the same dimensionless weighted
    feature geometry used by refinement.  The previously validated Stage3.2
    125x75 real-TSC Jacobian supplies a conservative prior for weak directions;
    source-prior directions receive much smaller coordinate bounds and can
    never declare success without a subsequent real-TSC rollout.
    """

    cfg = ctx.cfg["refinement"]
    rows, scales, weights = _refinement_quality_geometry(ctx)
    source_slope = np.asarray(source_slope, dtype=float).reshape(125)
    finite_source = bool(np.all(np.isfinite(source_slope)))

    clean: list[tuple[float, np.ndarray, str]] = []
    for coordinate, delta_feature, candidate_id in samples:
        coordinate = float(coordinate)
        delta_feature = np.asarray(delta_feature, dtype=float).reshape(125)
        if (
            math.isfinite(coordinate)
            and abs(coordinate) >= float(cfg.get("minimum_probe_coordinate", 1e-4))
            and np.all(np.isfinite(delta_feature))
        ):
            clean.append((coordinate, delta_feature, candidate_id))

    measurement_available = bool(clean)
    measured_slope = np.zeros(125, dtype=float)
    curvature = np.zeros(125, dtype=float)
    fit_relative_residual = 1.0
    legacy_relative_residual = 1.0
    coordinates: list[float] = []
    sample_ids: list[str] = []
    fit_method = "source_prior_only"
    characteristic_coordinate = 0.0

    if clean:
        x = np.asarray([item[0] for item in clean], dtype=float)
        dy = np.stack([item[1] for item in clean], axis=0)
        coordinates = x.tolist()
        sample_ids = [item[2] for item in clean]
        characteristic_coordinate = float(np.max(np.abs(x)))

        legacy_denom = float(np.dot(x, x))
        legacy_slope = np.tensordot(x, dy, axes=(0, 0)) / max(
            legacy_denom, 1e-15
        )
        legacy_residual = dy - x[:, None] * legacy_slope[None, :]
        legacy_relative_residual = float(
            np.linalg.norm(legacy_residual) / max(np.linalg.norm(dy), 1e-12)
        )

        design = np.column_stack([x, x**2])
        if len(clean) >= 2 and np.linalg.matrix_rank(design) >= 2:
            coefficient, *_ = np.linalg.lstsq(design, dy, rcond=None)
            measured_slope = coefficient[0]
            curvature = coefficient[1]
            prediction = design @ coefficient
            fit_method = "linear_quadratic_secant"
        else:
            measured_slope = legacy_slope
            prediction = x[:, None] * measured_slope[None, :]
            fit_method = "single_secant_with_prior"
        fit_residual = dy - prediction
        fit_relative_residual = float(
            np.linalg.norm(fit_residual) / max(np.linalg.norm(dy), 1e-12)
        )

    signal_norm = 0.0
    curvature_norm = 0.0
    source_signal_norm = 0.0
    prior_difference_ratio = 0.0
    curvature_ratio = 0.0
    if measurement_available:
        signal_norm = _normalized_weighted_norm(
            measured_slope * characteristic_coordinate,
            rows=rows,
            scales=scales,
            weights=weights,
        )
        curvature_norm = _normalized_weighted_norm(
            curvature * characteristic_coordinate**2,
            rows=rows,
            scales=scales,
            weights=weights,
        )
        curvature_ratio = curvature_norm / max(signal_norm, 1e-12)
    if finite_source:
        source_signal_norm = _normalized_weighted_norm(
            source_slope * max(characteristic_coordinate, 1.0),
            rows=rows,
            scales=scales,
            weights=weights,
        )
    if measurement_available and finite_source:
        prior_difference = _normalized_weighted_norm(
            (measured_slope - source_slope) * characteristic_coordinate,
            rows=rows,
            scales=scales,
            weights=weights,
        )
        prior_reference = _normalized_weighted_norm(
            source_slope * characteristic_coordinate,
            rows=rows,
            scales=scales,
            weights=weights,
        )
        prior_difference_ratio = prior_difference / max(prior_reference, 1e-12)

    minimum_signal = float(cfg.get("minimum_normalized_probe_signal", 0.02))
    curvature_soft = float(cfg.get("curvature_ratio_soft_limit", 1.0))
    prior_soft = float(cfg.get("prior_difference_soft_limit", 2.0))
    residual_soft = float(cfg.get("residual_ratio_soft_limit", 0.5))
    signal_confidence = min(1.0, signal_norm / max(minimum_signal, 1e-12))
    curvature_confidence = 1.0 / (
        1.0 + (curvature_ratio / max(curvature_soft, 1e-12)) ** 2
    )
    prior_confidence = 1.0 / (
        1.0 + (prior_difference_ratio / max(prior_soft, 1e-12)) ** 2
    )
    residual_confidence = 1.0 / (
        1.0 + (fit_relative_residual / max(residual_soft, 1e-12)) ** 2
    )
    measurement_confidence = 0.0
    if measurement_available:
        measurement_confidence = signal_confidence
        measurement_confidence *= 0.35 + 0.65 * curvature_confidence
        measurement_confidence *= 0.50 + 0.50 * prior_confidence
        measurement_confidence *= 0.50 + 0.50 * residual_confidence
        if len(clean) == 1:
            measurement_confidence *= 0.5
        measurement_confidence = float(np.clip(measurement_confidence, 0.05, 1.0))

    if measurement_available and finite_source:
        blend_floor = float(cfg.get("measurement_blend_floor", 0.35))
        blend_ceiling = float(cfg.get("measurement_blend_ceiling", 0.95))
        blend = float(
            np.clip(
                blend_floor
                + (blend_ceiling - blend_floor) * measurement_confidence,
                0.0,
                1.0,
            )
        )
        slope = blend * measured_slope + (1.0 - blend) * source_slope
        source_prior_used = bool(blend < 1.0 - 1e-12)
    elif measurement_available:
        blend = 1.0
        slope = measured_slope
        source_prior_used = False
    elif finite_source:
        blend = 0.0
        slope = source_slope
        source_prior_used = True
    else:
        blend = 0.0
        slope = np.zeros(125, dtype=float)
        source_prior_used = False

    measured_scale_floor = float(
        cfg.get("minimum_measured_direction_scale", 0.25)
    )
    source_scale = float(cfg.get("source_prior_direction_scale", 0.12))
    if measurement_available:
        direction_scale = max(measured_scale_floor, measurement_confidence)
    elif finite_source:
        direction_scale = source_scale
    else:
        direction_scale = 0.0
    direction_scale = float(np.clip(direction_scale, 0.0, 1.0))
    usable = bool(np.all(np.isfinite(slope)) and direction_scale > 0.0)
    measured_reliable = bool(
        measurement_available
        and measurement_confidence
        >= float(cfg.get("minimum_confidence_for_measured_reliable", 0.20))
    )
    legacy_reliable = bool(
        measurement_available
        and legacy_relative_residual
        <= float(cfg.get("maximum_probe_relative_residual", 0.45))
    )
    return {
        "direction": int(direction_index),
        "slope": slope,
        "usable": usable,
        "measurement_available": measurement_available,
        "measured_reliable": measured_reliable,
        "source_prior_used": source_prior_used,
        "fit_method": fit_method,
        "n_samples": len(clean),
        "coordinates": coordinates,
        "sample_ids": sample_ids,
        "characteristic_coordinate": characteristic_coordinate,
        "normalized_signal_norm": signal_norm,
        "normalized_curvature_norm": curvature_norm,
        "normalized_source_signal_norm_per_unit": source_signal_norm,
        "curvature_ratio": curvature_ratio,
        "prior_difference_ratio": prior_difference_ratio,
        "fit_relative_residual": fit_relative_residual,
        "legacy_through_origin_relative_residual": legacy_relative_residual,
        "legacy_reliable": legacy_reliable,
        "measurement_confidence": measurement_confidence,
        "measurement_blend": blend,
        "direction_coordinate_scale": direction_scale,
    }


def build_refinement_probe_manifest(
    ctx: Stage33Context,
    *,
    round_index: int,
    active: Sequence[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    round_dir = ctx.paths.refinement / f"round_{round_index:03d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    path = round_dir / "probe_manifest.json"
    if path.exists():
        return read_json(path)
    basis_payload = reduced_control_basis(ctx)
    basis = np.asarray(basis_payload["basis"], dtype=float)
    lower, upper = _control_bounds(ctx)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task, center in active:
        center_vector = _vector(center["full_control_vector"], 75)
        for direction in range(basis.shape[1]):
            direction_vector = np.asarray(basis[:, direction], dtype=float)
            coordinates, scheme = _probe_coordinates_for_direction(
                ctx, center_vector, direction_vector
            )
            direction_norm_sq = float(np.dot(direction_vector, direction_vector))
            for slot, coordinate in enumerate(coordinates):
                vector = center_vector + float(coordinate) * direction_vector
                if np.any(vector < lower - 1e-10) or np.any(vector > upper + 1e-10):
                    raise RuntimeError("feasible reduced probe escaped coefficient bounds")
                vector = np.clip(vector, lower, upper)
                actual = vector - center_vector
                actual_coordinate = float(
                    np.dot(actual, direction_vector)
                    / max(direction_norm_sq, 1e-15)
                )
                leakage = float(
                    np.linalg.norm(actual - actual_coordinate * direction_vector)
                )
                if leakage > 1e-9:
                    raise RuntimeError(
                        "reduced probe is not collinear with its basis direction"
                    )
                cid = candidate_id(
                    "s33probe",
                    str(task["task_id"]),
                    vector,
                    round_index,
                    direction,
                    slot,
                    actual_coordinate,
                )
                if cid in seen:
                    continue
                seen.add(cid)
                candidates.append(
                    {
                        "candidate_id": cid,
                        "task": copy.deepcopy(task),
                        "full_control_vector": vector.tolist(),
                        "source_name": (
                            f"basis_{direction:02d}_"
                            f"{'p' if actual_coordinate > 0 else 'm'}_{slot}"
                        ),
                        "source_type": "target_reduced_real_tsc_probe",
                        "parent_candidate_id": str(center["candidate_id"]),
                        "refinement_round": round_index,
                        "probe_direction": direction,
                        "probe_sign": 1 if actual_coordinate > 0 else -1,
                        "probe_coordinate_slot": slot,
                        "probe_requested_coordinate": float(coordinate),
                        "probe_actual_coordinate": actual_coordinate,
                        "probe_scheme": scheme,
                        "probe_direction_norm": float(np.sqrt(direction_norm_sq)),
                        "probe_collinearity_leakage_norm": leakage,
                        "refinement_model_revision": REFINEMENT_MODEL_REVISION,
                    }
                )
    for index, row in enumerate(candidates):
        row["population_index"] = index
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "phase": "target_nominal_refinement_probes",
        "round": round_index,
        "horizon_steps": 25,
        "n_active_targets": len(active),
        "n_candidates": len(candidates),
        "refinement_model_revision": REFINEMENT_MODEL_REVISION,
        "active_targets": [str(task["task_id"]) for task, _ in active],
        "centers": {str(task["task_id"]): center for task, center in active},
        "candidates": candidates,
    }
    atomic_write_json(path, manifest)
    return manifest


def build_reduced_jacobian(
    ctx: Stage33Context,
    *,
    task: dict[str, Any],
    center: dict[str, Any],
    probe_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    basis_payload = reduced_control_basis(ctx)
    basis = np.asarray(basis_payload["basis"], dtype=float)
    center_result = load_result_for_candidate(ctx, center)
    center_feature = _feature_for_task(ctx, task, center_result)
    source_full_jacobian = np.asarray(
        ctx.source_bundle["jacobian_physical_units"], dtype=float
    )
    if source_full_jacobian.shape != (125, 75):
        raise ValueError("Stage3.2 source Jacobian must have shape 125x75")
    source_reduced_jacobian = source_full_jacobian @ basis

    jacobian = np.zeros((125, basis.shape[1]), dtype=float)
    columns: list[dict[str, Any]] = []
    usable: list[bool] = []
    measured_available: list[bool] = []
    measured_reliable: list[bool] = []
    direction_confidence: list[float] = []
    direction_coordinate_limits: list[float] = []
    for direction in range(basis.shape[1]):
        samples: list[tuple[float, np.ndarray, str]] = []
        for row in probe_rows:
            if (
                str(row["task"]["task_id"]) != str(task["task_id"])
                or _as_int(row.get("probe_direction"), -1) != direction
            ):
                continue
            if not _as_bool(row.get("success"), False):
                continue
            coordinate = _finite(row.get("probe_actual_coordinate"), 0.0)
            if abs(coordinate) < float(
                ctx.cfg["refinement"].get("minimum_probe_coordinate", 1e-4)
            ):
                continue
            result = load_result_for_candidate(ctx, row)
            feature = _feature_for_task(ctx, task, result)
            samples.append(
                (coordinate, feature - center_feature, str(row["candidate_id"]))
            )
        fit = _fit_reduced_direction(
            ctx,
            direction_index=direction,
            samples=samples,
            source_slope=source_reduced_jacobian[:, direction],
        )
        jacobian[:, direction] = np.asarray(fit.pop("slope"), dtype=float)
        columns.append(fit)
        usable.append(bool(fit["usable"]))
        measured_available.append(bool(fit["measurement_available"]))
        measured_reliable.append(bool(fit["measured_reliable"]))
        direction_confidence.append(float(fit["measurement_confidence"]))
        direction_coordinate_limits.append(float(fit["direction_coordinate_scale"]))

    usable_array = np.asarray(usable, dtype=bool)
    measured_available_array = np.asarray(measured_available, dtype=bool)
    measured_reliable_array = np.asarray(measured_reliable, dtype=bool)
    minimum_measured = int(
        ctx.cfg["refinement"].get("minimum_measured_directions", 1)
    )
    minimum_usable = int(
        ctx.cfg["refinement"].get("minimum_usable_directions", 4)
    )
    if int(np.sum(measured_available_array)) < minimum_measured:
        raise RuntimeError(
            f"Target {task['task_id']} has only "
            f"{int(np.sum(measured_available_array))}/{basis.shape[1]} measured "
            f"reduced directions; minimum is {minimum_measured}"
        )
    if int(np.sum(usable_array)) < minimum_usable:
        raise RuntimeError(
            f"Target {task['task_id']} has only "
            f"{int(np.sum(usable_array))}/{basis.shape[1]} usable reduced "
            f"directions after source-prior regularization; minimum is "
            f"{minimum_usable}"
        )

    quality_rows, quality_scales, quality_weights = _refinement_quality_geometry(ctx)
    normalized = (
        jacobian[quality_rows][:, usable_array]
        / np.maximum(quality_scales[quality_rows, None], 1e-12)
    )
    normalized *= np.sqrt(
        np.maximum(quality_weights[quality_rows, None], 0.0)
    )
    normalized_rank = int(np.linalg.matrix_rank(normalized))
    minimum_rank = int(
        ctx.cfg["refinement"].get("minimum_normalized_model_rank", 2)
    )
    if normalized_rank < minimum_rank:
        raise RuntimeError(
            f"Target {task['task_id']} reduced model rank is {normalized_rank}; "
            f"minimum is {minimum_rank}"
        )
    singular_values = np.linalg.svd(normalized, compute_uv=False)
    legacy_reliable_count = sum(bool(row.get("legacy_reliable")) for row in columns)
    source_fallback_count = sum(bool(row.get("source_prior_used")) for row in columns)
    return {
        "schema_version": SCHEMA_VERSION,
        "refinement_model_revision": REFINEMENT_MODEL_REVISION,
        "task_id": str(task["task_id"]),
        "center_candidate_id": str(center["candidate_id"]),
        "center_feature": center_feature.tolist(),
        "basis": basis.tolist(),
        "jacobian": jacobian.tolist(),
        "usable_directions": usable_array.tolist(),
        # Kept for compatibility with older downstream readers.  In the new
        # model this means directly measured with adequate dimensionless
        # confidence, not the old raw-unit two-point residual gate.
        "reliable_directions": measured_reliable_array.tolist(),
        "measured_available_directions": measured_available_array.tolist(),
        "direction_confidence": direction_confidence,
        "direction_coordinate_limits": direction_coordinate_limits,
        "columns": columns,
        "n_measured_directions": int(np.sum(measured_available_array)),
        "n_measured_reliable_directions": int(np.sum(measured_reliable_array)),
        "n_usable_directions": int(np.sum(usable_array)),
        "n_source_prior_directions": int(source_fallback_count),
        "legacy_raw_unit_reliable_directions": int(legacy_reliable_count),
        "normalized_model_rank": normalized_rank,
        "normalized_singular_values": singular_values.tolist(),
    }


def _profile_weights(ctx: Stage33Context, profile: str) -> np.ndarray:
    cfg = ctx.cfg["refinement"]["profiles"][profile]
    weights = np.zeros(125, dtype=float)
    weights[0:25] = float(cfg["R"])
    weights[25:50] = float(cfg["Z"])
    weights[50:75] = float(cfg["vR"])
    weights[75:100] = float(cfg["vZ"])
    weights[100:125] = float(cfg["Ip"])
    state_weights = np.asarray(ctx.cfg["refinement"]["state_weights"], dtype=float)
    if state_weights.shape != (25,):
        raise ValueError("refinement.state_weights must have 25 values")
    return weights * np.tile(state_weights, 5)


def solve_reduced_proposal(
    ctx: Stage33Context,
    *,
    model: dict[str, Any],
    profile: str,
) -> np.ndarray:
    try:
        from scipy.optimize import lsq_linear
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage3.3 reduced refinement") from exc
    center_feature = np.asarray(model["center_feature"], dtype=float)
    jacobian = np.asarray(model["jacobian"], dtype=float)
    usable = np.asarray(
        model.get("usable_directions", model.get("reliable_directions", [])),
        dtype=bool,
    )
    confidence = np.asarray(
        model.get("direction_confidence", np.ones(jacobian.shape[1])),
        dtype=float,
    )
    coordinate_limits = np.asarray(
        model.get("direction_coordinate_limits", np.ones(jacobian.shape[1])),
        dtype=float,
    )
    if (
        usable.shape != (jacobian.shape[1],)
        or confidence.shape != (jacobian.shape[1],)
        or coordinate_limits.shape != (jacobian.shape[1],)
    ):
        raise ValueError("reduced model direction metadata has inconsistent dimensions")
    scales = np.asarray(ctx.source_bundle["output_scales"], dtype=float)
    weights = _profile_weights(ctx, profile)
    rows = np.flatnonzero(weights > 0.0)
    cols = np.flatnonzero(usable)
    if len(cols) == 0:
        raise RuntimeError("reduced model has no usable directions")
    a = jacobian[np.ix_(rows, cols)] / scales[rows, None]
    b = -(center_feature[rows] / scales[rows])
    w = np.sqrt(weights[rows])
    a = w[:, None] * a
    b = w * b
    ridge = float(ctx.cfg["refinement"].get("ridge_lambda", 0.06))
    if ridge > 0.0:
        # Low-confidence and source-prior-only directions remain usable, but
        # are penalized more heavily and receive smaller coordinate bounds.
        confidence_floor = float(
            ctx.cfg["refinement"].get("source_prior_direction_scale", 0.12)
        )
        penalty = 1.0 / np.maximum(confidence[cols], confidence_floor)
        a = np.vstack(
            [a, math.sqrt(ridge) * np.diag(penalty)]
        )
        b = np.concatenate([b, np.zeros(len(cols), dtype=float)])
    trust = float(ctx.cfg["refinement"].get("reduced_trust_radius", 0.8))
    bounds = trust * np.clip(coordinate_limits[cols], 1e-6, 1.0)
    solution = lsq_linear(
        a,
        b,
        bounds=(-bounds, bounds),
        method="trf",
        tol=float(ctx.cfg["refinement"].get("solver_tolerance", 1e-10)),
        max_iter=int(ctx.cfg["refinement"].get("solver_max_iterations", 500)),
        lsmr_tol="auto",
    )
    coordinate = np.zeros(jacobian.shape[1], dtype=float)
    coordinate[cols] = solution.x
    return coordinate


def build_refinement_proposal_manifest(
    ctx: Stage33Context,
    *,
    round_index: int,
    active: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    probe_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    round_dir = ctx.paths.refinement / f"round_{round_index:03d}"
    path = round_dir / "proposal_manifest.json"
    if path.exists():
        existing = read_json(path)
        if (
            str(existing.get("refinement_model_revision", ""))
            == REFINEMENT_MODEL_REVISION
        ):
            return existing
        backup = path.with_name(
            f"proposal_manifest.pre_{REFINEMENT_MODEL_REVISION}.json"
        )
        if not backup.exists():
            shutil.copy2(path, backup)
    candidates: list[dict[str, Any]] = []
    models: dict[str, Any] = {}
    skipped_models: dict[str, Any] = {}
    seen: set[str] = set()
    requests = list(ctx.cfg["refinement"]["proposal_requests"])
    for task, center in active:
        task_id = str(task["task_id"])
        try:
            model = build_reduced_jacobian(
                ctx, task=task, center=center, probe_rows=probe_rows
            )
        except Exception as exc:
            # One locally awkward target must not discard every other target's
            # completed real-TSC probes.  Keep an explicit failure record and
            # let the library verdict remain incomplete if this target cannot
            # be refined.  No scientific pass is inferred from the exception.
            skipped_models[task_id] = {
                "task_id": task_id,
                "center_candidate_id": str(center.get("candidate_id", "")),
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            continue
        models[task_id] = model
        basis = np.asarray(model["basis"], dtype=float)
        center_vector = _vector(center["full_control_vector"], 75)
        solved: dict[str, np.ndarray] = {}
        for request_index, request in enumerate(requests):
            profile = str(request["profile"])
            if profile not in solved:
                solved[profile] = solve_reduced_proposal(ctx, model=model, profile=profile)
            step_scale = float(request["step_scale"])
            vector = clip_control(ctx, center_vector + step_scale * (basis @ solved[profile]))
            cid = candidate_id("s33step", str(task["task_id"]), vector, round_index, profile, step_scale)
            if cid in seen:
                continue
            seen.add(cid)
            candidates.append(
                {
                    "candidate_id": cid,
                    "task": copy.deepcopy(task),
                    "full_control_vector": vector.tolist(),
                    "source_name": f"{profile}_scale_{step_scale:.2f}",
                    "source_type": "target_reduced_real_tsc_step",
                    "parent_candidate_id": str(center["candidate_id"]),
                    "refinement_round": round_index,
                    "proposal_request_index": request_index,
                    "proposal_profile": profile,
                    "proposal_step_scale": step_scale,
                    "predicted_reduced_coordinate": solved[profile].tolist(),
                    "refinement_model_revision": REFINEMENT_MODEL_REVISION,
                    "model_measured_directions": int(
                        model.get("n_measured_directions", 0)
                    ),
                    "model_measured_reliable_directions": int(
                        model.get("n_measured_reliable_directions", 0)
                    ),
                    "model_usable_directions": int(
                        model.get("n_usable_directions", 0)
                    ),
                }
            )
    for index, row in enumerate(candidates):
        row["population_index"] = index
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "phase": "target_nominal_refinement_proposals",
        "round": round_index,
        "horizon_steps": 25,
        "n_candidates": len(candidates),
        "refinement_model_revision": REFINEMENT_MODEL_REVISION,
        "n_models_built": len(models),
        "n_models_skipped": len(skipped_models),
        "models": models,
        "skipped_models": skipped_models,
        "candidates": candidates,
    }
    atomic_write_json(path, manifest)
    return manifest


def run_one_refinement_round(ctx: Stage33Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    round_index = int(state.get("refinement_round", 0))
    max_rounds = int(ctx.cfg["refinement"]["max_rounds"])
    if round_index >= max_rounds:
        state["refinement_complete"] = True
        state["refinement_stop_reason"] = "max_rounds"
        atomic_write_json(ctx.paths.state, state)
        return {"finished": True, "stop_reason": "max_rounds", "round": round_index}
    rows_before = aggregate_library_rows(ctx)
    active = active_refinement_targets(ctx, rows_before)
    if not active:
        state["refinement_complete"] = True
        state["refinement_stop_reason"] = "all_selected_targets_passed"
        atomic_write_json(ctx.paths.state, state)
        return {"finished": True, "stop_reason": "all_selected_targets_passed", "round": round_index}
    round_dir = ctx.paths.refinement / f"round_{round_index:03d}"
    probe_manifest = build_refinement_probe_manifest(ctx, round_index=round_index, active=active)
    probe_rows = evaluate_open_loop_rows(
        ctx,
        probe_manifest["candidates"],
        output_dir=round_dir / "probe_raw",
        phase=f"target_nominal_refinement_round_{round_index:03d}_probes",
        backend=backend,
        resume=resume,
    )
    atomic_write_json(round_dir / "probe_results.json", probe_rows)
    write_csv(round_dir / "probe_results.csv", probe_rows)
    proposal_manifest = build_refinement_proposal_manifest(
        ctx,
        round_index=round_index,
        active=active,
        probe_rows=probe_rows,
    )
    proposal_rows = evaluate_open_loop_rows(
        ctx,
        proposal_manifest["candidates"],
        output_dir=round_dir / "proposal_raw",
        phase=f"target_nominal_refinement_round_{round_index:03d}_proposals",
        backend=backend,
        resume=resume,
    )
    atomic_write_json(round_dir / "proposal_results.json", proposal_rows)
    write_csv(round_dir / "proposal_results.csv", proposal_rows)
    rows_after = aggregate_library_rows(ctx)
    best = best_by_task(rows_after)
    mandatory_passed = sum(
        _as_bool(best.get(str(task["task_id"]), {}).get("stage3_3_target_tracking_pass"), False)
        for task in ctx.target_tasks
        if task["mandatory"]
    )
    total_mandatory = sum(bool(task["mandatory"]) for task in ctx.target_tasks)
    state["refinement_round"] = round_index + 1
    state["mandatory_targets_passed"] = mandatory_passed
    state["target_library_best_ids"] = {task_id: row["candidate_id"] for task_id, row in best.items()}
    finished = mandatory_passed == total_mandatory or round_index + 1 >= max_rounds
    if finished:
        state["refinement_complete"] = True
        state["refinement_stop_reason"] = "mandatory_targets_passed" if mandatory_passed == total_mandatory else "max_rounds"
    atomic_write_json(ctx.paths.state, state)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "phase": "target_nominal_refinement",
        "round": round_index,
        "refinement_model_revision": REFINEMENT_MODEL_REVISION,
        "active_targets": [str(task["task_id"]) for task, _ in active],
        "probe_success": sum(_as_bool(row.get("success"), False) for row in probe_rows),
        "proposal_success": sum(_as_bool(row.get("success"), False) for row in proposal_rows),
        "models_built": int(proposal_manifest.get("n_models_built", 0)),
        "models_skipped": int(proposal_manifest.get("n_models_skipped", 0)),
        "skipped_models": copy.deepcopy(proposal_manifest.get("skipped_models", {})),
        "mandatory_targets_passed": mandatory_passed,
        "total_mandatory_targets": total_mandatory,
        "finished": finished,
        "stop_reason": state.get("refinement_stop_reason", ""),
        "best_by_task": best,
    }
    atomic_write_json(round_dir / "round_summary.json", summary)
    print(
        json.dumps(
            {
                "stage": "Stage3.3",
                "phase": "target_nominal_refinement",
                "round": round_index,
                "active_targets": len(active),
                "probe_success": summary["probe_success"],
                "proposal_success": summary["proposal_success"],
                "models_built": summary["models_built"],
                "models_skipped": summary["models_skipped"],
                "mandatory_targets_passed": mandatory_passed,
                "mandatory_targets_total": total_mandatory,
                "finished": finished,
            },
            indent=2,
        ),
        flush=True,
    )
    return summary


def run_refinement(ctx: Stage33Context, *, backend: str, resume: bool) -> dict[str, Any]:
    while True:
        state = read_json(ctx.paths.state)
        if state.get("refinement_complete"):
            break
        summary = run_one_refinement_round(ctx, backend=backend, resume=resume)
        if summary.get("finished"):
            break
    rows = aggregate_library_rows(ctx)
    best = best_by_task(rows)
    return {
        "finished": True,
        "best_by_task": best,
        "mandatory_targets_passed": sum(
            _as_bool(best.get(str(task["task_id"]), {}).get("stage3_3_target_tracking_pass"), False)
            for task in ctx.target_tasks
            if task["mandatory"]
        ),
    }


# ---------------------------------------------------------------------------
# Phase C: target-library materialization and deterministic confirmation
# ---------------------------------------------------------------------------


def materialize_target_library(ctx: Stage33Context) -> dict[str, Any]:
    library_path = ctx.paths.library / "target_library.json"
    rows = aggregate_library_rows(ctx)
    best = best_by_task(rows)
    entries: list[dict[str, Any]] = []
    for task in ctx.target_tasks:
        row = best.get(str(task["task_id"]))
        if row is None:
            continue
        entry = copy.deepcopy(row)
        entry["task"] = copy.deepcopy(task)
        entry["target_absolute"] = target_absolute(ctx, task).tolist()
        if row.get("result_relpath"):
            result = load_result_for_candidate(ctx, row)
            trajectory = np.asarray([[state["R"], state["Z"], state["Ip"]] for state in result["trajectory"]], dtype=float)
            velocity = s32._velocity_components(trajectory, float(ctx.env_cfg["dt_ms"]) / 1000.0)
            entry["nominal_trajectory_RZI"] = trajectory.tolist()
            entry["nominal_velocity_RZ"] = velocity.tolist()
        entries.append(entry)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "base_target": copy.deepcopy(ctx.cfg["target"]),
        "n_configured_targets": len(ctx.target_tasks),
        "n_entries": len(entries),
        "n_tracking_pass_entries": sum(_as_bool(row.get("stage3_3_target_tracking_pass"), False) for row in entries),
        "n_mandatory_targets": sum(bool(task["mandatory"]) for task in ctx.target_tasks),
        "n_mandatory_tracking_pass": sum(
            _as_bool(best.get(str(task["task_id"]), {}).get("stage3_3_target_tracking_pass"), False)
            for task in ctx.target_tasks
            if task["mandatory"]
        ),
        "entries": entries,
    }
    atomic_write_json(library_path, payload)
    write_csv(ctx.paths.library / "target_library.csv", entries)
    return payload


def build_library_confirmation_rows(ctx: Stage33Context, library: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mandatory_repeats = int(ctx.cfg["confirmation"].get("mandatory_target_repeats", 2))
    optional_repeats = int(ctx.cfg["confirmation"].get("optional_target_repeats", 1))
    for entry in library["entries"]:
        if not _as_bool(entry.get("stage3_3_target_tracking_pass"), False):
            continue
        task = entry["task"]
        repeats = mandatory_repeats if bool(task["mandatory"]) else optional_repeats
        for repeat in range(repeats):
            vector = _vector(entry["full_control_vector"], 75)
            cid = candidate_id("s33libconf", str(task["task_id"]), vector, repeat)
            rows.append(
                {
                    "candidate_id": cid,
                    "task": copy.deepcopy(task),
                    "full_control_vector": vector.tolist(),
                    "source_name": f"library_confirmation_repeat_{repeat}",
                    "source_type": "target_library_confirmation",
                    "parent_candidate_id": str(entry["candidate_id"]),
                    "confirmation_repeat": repeat,
                }
            )
    return rows


def run_library_confirmation(ctx: Stage33Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    summary_path = ctx.paths.library / "target_library_confirmation_summary.json"
    if state.get("library_confirmation_complete") and summary_path.exists():
        return read_json(summary_path)
    library = materialize_target_library(ctx)
    rows_to_run = build_library_confirmation_rows(ctx, library)
    rows = evaluate_open_loop_rows(
        ctx,
        rows_to_run,
        output_dir=ctx.paths.library / "confirmation_raw",
        phase="target_library_confirmation",
        backend=backend,
        resume=resume,
    )
    atomic_write_json(ctx.paths.library / "target_library_confirmation_results.json", rows)
    write_csv(ctx.paths.library / "target_library_confirmation_results.csv", rows)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["task"]["task_id"]), []).append(row)
    summaries: list[dict[str, Any]] = []
    task_by_id = {str(task["task_id"]): task for task in ctx.target_tasks}
    for task_id, task in task_by_id.items():
        group = grouped.get(task_id, [])
        summaries.append(
            {
                "task_id": task_id,
                "mandatory": bool(task["mandatory"]),
                "repeats": len(group),
                "successful_repeats": sum(_as_bool(row.get("success"), False) for row in group),
                "all_repeats_tracking_pass": bool(group) and all(_as_bool(row.get("stage3_3_target_tracking_pass"), False) for row in group),
                "worst_tracking_signed_margin": None if not group else float(min(_finite(row.get("stage3_3_tracking_minimum_signed_margin"), -1e12) for row in group)),
                "worst_sustained_box_m": None if not group else float(max(_finite(row.get("stage3_3_sustained_box_max_error_m", row.get("stage3_2_sustained_box_max_error_m")), 1e12) for row in group)),
                "worst_ip_hold_rms_A": None if not group else float(max(_finite(row.get("stage3_3_ip_hold_rms_error_A"), 1e12) for row in group)),
            }
        )
    mandatory = [row for row in summaries if row["mandatory"]]
    optional = [row for row in summaries if not row["mandatory"]]
    mandatory_all = bool(mandatory) and all(bool(row["all_repeats_tracking_pass"]) for row in mandatory)
    optional_fraction = sum(bool(row["all_repeats_tracking_pass"]) for row in optional) / max(len(optional), 1)
    passed = bool(
        mandatory_all
        and optional_fraction >= float(ctx.cfg["confirmation"].get("minimum_optional_target_pass_fraction", 0.70))
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success"), False) for row in rows),
        "mandatory_all_confirmed": mandatory_all,
        "optional_confirmed_fraction": optional_fraction,
        "target_library_confirmed": passed,
        "task_summaries": summaries,
    }
    atomic_write_json(summary_path, summary)
    state["library_confirmation_complete"] = True
    state["target_library_confirmed"] = passed
    atomic_write_json(ctx.paths.state, state)
    return summary


# ---------------------------------------------------------------------------
# Target-library interpolation
# ---------------------------------------------------------------------------


def usable_library_entries(library: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        copy.deepcopy(row)
        for row in library.get("entries", [])
        if _as_bool(row.get("stage3_3_target_tracking_pass"), False)
        and row.get("nominal_trajectory_RZI") is not None
        and row.get("nominal_velocity_RZ") is not None
    ]
    if not entries:
        raise RuntimeError("Stage3.3 target library has no usable tracking-pass entry")
    return entries


def library_target_vector(entry: dict[str, Any]) -> np.ndarray:
    task = entry["task"]
    return np.asarray([task["R_offset_m"], task["Z_offset_m"], task["Ip_offset_A"]], dtype=float)


def interpolation_for_target(
    ctx: Stage33Context,
    library: dict[str, Any],
    target_offset: np.ndarray,
) -> dict[str, Any]:
    entries = usable_library_entries(library)
    target_offset = np.asarray(target_offset, dtype=float).reshape(3)
    scales = np.asarray(ctx.cfg["mpc"]["target_distance_scales"], dtype=float)
    if scales.shape != (3,) or np.any(scales <= 0.0):
        raise ValueError("mpc.target_distance_scales must be a positive three-vector")
    distances = np.asarray(
        [np.linalg.norm((library_target_vector(entry) - target_offset) / scales) for entry in entries],
        dtype=float,
    )
    exact = np.flatnonzero(distances <= 1e-12)
    if len(exact):
        selected_indices = [int(exact[0])]
        weights = np.asarray([1.0], dtype=float)
    else:
        count = min(int(ctx.cfg["mpc"]["library_neighbors"]), len(entries))
        selected_indices = [int(index) for index in np.argsort(distances)[:count]]
        power = float(ctx.cfg["mpc"].get("inverse_distance_power", 2.0))
        raw = 1.0 / np.maximum(distances[np.asarray(selected_indices, dtype=int)], 1e-9) ** power
        weights = raw / np.sum(raw)
    selected = [entries[index] for index in selected_indices]
    controls = np.stack([_vector(entry["full_control_vector"], 75) for entry in selected], axis=0)
    trajectories = np.stack([np.asarray(entry["nominal_trajectory_RZI"], dtype=float) for entry in selected], axis=0)
    velocities = np.stack([np.asarray(entry["nominal_velocity_RZ"], dtype=float) for entry in selected], axis=0)
    represented_target = np.sum(
        weights[:, None] * np.stack([library_target_vector(entry) for entry in selected], axis=0),
        axis=0,
    )
    return {
        "entry_ids": [str(entry["candidate_id"]) for entry in selected],
        "task_ids": [str(entry["task"]["task_id"]) for entry in selected],
        "weights": weights.tolist(),
        "distances": [float(distances[index]) for index in selected_indices],
        "represented_target_offset": represented_target.tolist(),
        "requested_target_offset": target_offset.tolist(),
        "full_control_vector": clip_control(ctx, np.sum(weights[:, None] * controls, axis=0)).tolist(),
        "nominal_trajectory_RZI": np.sum(weights[:, None, None] * trajectories, axis=0).tolist(),
        "nominal_velocity_RZ": np.sum(weights[:, None, None] * velocities, axis=0).tolist(),
    }


# ---------------------------------------------------------------------------
# Phase D/E: true receding-horizon bounded least-squares MPC
# ---------------------------------------------------------------------------


def scenario_task(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(scenario["scenario"]),
        "R_offset_m": float(scenario.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(scenario.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(scenario.get("target_Ip_offset_A", 0.0)),
        "mandatory": False,
        "category": str(scenario.get("category", "validation")),
        "description": str(scenario.get("description", "")),
    }


def validation_scenarios(ctx: Stage33Context, split: str) -> list[dict[str, Any]]:
    key = "calibration_scenarios" if split == "calibration" else "holdout_scenarios"
    scenarios: list[dict[str, Any]] = []
    for raw in ctx.cfg["mpc"][key]:
        row = copy.deepcopy(raw)
        row.setdefault("category", "target")
        row.setdefault("target_R_offset_m", 0.0)
        row.setdefault("target_Z_offset_m", 0.0)
        row.setdefault("target_Ip_offset_A", 0.0)
        row.setdefault("disturbance", None)
        scenarios.append(row)
    names = [str(row["scenario"]) for row in scenarios]
    if len(names) != len(set(names)):
        raise ValueError(f"duplicate {split} scenario name")
    return scenarios


def _full_nominal_feature(
    ctx: Stage33Context,
    nominal_y: np.ndarray,
    nominal_velocity: np.ndarray,
    requested_target: np.ndarray,
) -> np.ndarray:
    error = np.asarray(nominal_y, dtype=float) - requested_target[None, :]
    velocity = np.asarray(nominal_velocity, dtype=float)
    return np.concatenate(
        [
            error[1:, 0],
            error[1:, 1],
            velocity[1:, 0],
            velocity[1:, 1],
            error[1:, 2],
        ]
    )


def _future_feature_rows(current_step: int) -> list[int]:
    first_state = current_step + 1
    rows: list[int] = []
    for block in range(5):
        for state in range(first_state, 26):
            rows.append(block * 25 + (state - 1))
    return rows


def _future_control_columns(current_step: int) -> list[int]:
    return [step * 3 + mode for step in range(current_step, 25) for mode in range(3)]


def _state_weight_vector(ctx: Stage33Context, rows: Sequence[int], current_step: int) -> np.ndarray:
    mpc = ctx.cfg["mpc"]
    block_weights = np.asarray(
        [
            float(mpc["output_weights"]["R"]),
            float(mpc["output_weights"]["Z"]),
            float(mpc["output_weights"]["vR"]),
            float(mpc["output_weights"]["vZ"]),
            float(mpc["output_weights"]["Ip"]),
        ],
        dtype=float,
    )
    discount = float(mpc.get("future_discount", 0.985))
    weights: list[float] = []
    for row in rows:
        block = row // 25
        state = row % 25 + 1
        horizon = max(state - current_step, 1)
        weight = block_weights[block] * (discount ** (horizon - 1))
        if state >= int(mpc.get("hold_weight_start_state", 12)):
            weight *= float(mpc.get("hold_weight_multiplier", 2.0))
        weights.append(weight)
    return np.asarray(weights, dtype=float)


def solve_receding_horizon_correction(
    ctx: Stage33Context,
    *,
    current_step: int,
    nominal_coefficients: np.ndarray,
    nominal_feature: np.ndarray,
    measurement_normalized: np.ndarray,
    integral_normalized: np.ndarray,
    previous_correction: np.ndarray,
    controller_scale: float,
) -> dict[str, Any]:
    try:
        from scipy.optimize import lsq_linear
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage3.3 receding-horizon MPC") from exc
    bundle = ctx.source_bundle
    jacobian_norm = np.asarray(bundle["jacobian_normalized"], dtype=float)
    scales = np.asarray(bundle["output_scales"], dtype=float)
    rows = _future_feature_rows(current_step)
    columns = _future_control_columns(current_step)
    projection = s32._measurement_bias_projection(
        ctx,
        current_step=current_step,
        state_start=1,
        horizon=25,
        selected_rows=rows,
    )
    integral_gain = np.asarray(ctx.cfg["mpc"]["integral_measurement_gain"], dtype=float)
    if integral_gain.shape != (5,):
        raise ValueError("mpc.integral_measurement_gain must have five values")
    effective_measurement = np.asarray(measurement_normalized, dtype=float) + integral_gain * np.asarray(integral_normalized, dtype=float)
    future_error = nominal_feature[np.asarray(rows, dtype=int)] / scales[np.asarray(rows, dtype=int)] + projection @ effective_measurement
    a = jacobian_norm[np.ix_(rows, columns)]
    weights = _state_weight_vector(ctx, rows, current_step)
    sqrt_w = np.sqrt(np.maximum(weights, 0.0))
    a_weighted = sqrt_w[:, None] * a
    b_weighted = -sqrt_w * future_error

    future_steps = list(range(current_step, 25))
    nominal_future = np.asarray(nominal_coefficients, dtype=float)[future_steps].reshape(-1)
    lower_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    feedback_limit = np.asarray(ctx.cfg["mpc"]["per_step_feedback_limit_by_mode"], dtype=float) * float(controller_scale)
    lower = np.maximum(np.tile(lower_mode, len(future_steps)) - nominal_future, -np.tile(feedback_limit, len(future_steps)))
    upper = np.minimum(np.tile(upper_mode, len(future_steps)) - nominal_future, np.tile(feedback_limit, len(future_steps)))

    augmented_a: list[np.ndarray] = [a_weighted]
    augmented_b: list[np.ndarray] = [b_weighted]
    ridge = float(ctx.cfg["mpc"].get("ridge_lambda", 0.08))
    if ridge > 0.0:
        radius = np.maximum(np.tile(feedback_limit, len(future_steps)), 1e-8)
        augmented_a.append(math.sqrt(ridge) * np.diag(1.0 / radius))
        augmented_b.append(np.zeros(len(columns), dtype=float))
    smooth = float(ctx.cfg["mpc"].get("future_correction_smoothness", 0.08))
    if smooth > 0.0 and len(future_steps) > 1:
        difference = _difference_matrix(len(future_steps))
        augmented_a.append(math.sqrt(smooth) * difference)
        augmented_b.append(np.zeros(difference.shape[0], dtype=float))
    rate = float(ctx.cfg["mpc"].get("first_action_rate_weight", 0.20))
    if rate > 0.0:
        first = np.zeros((3, len(columns)), dtype=float)
        first[:, :3] = np.eye(3)
        augmented_a.append(math.sqrt(rate) * first)
        augmented_b.append(math.sqrt(rate) * np.asarray(previous_correction, dtype=float))

    solution = lsq_linear(
        np.vstack(augmented_a),
        np.concatenate(augmented_b),
        bounds=(lower, upper),
        method="trf",
        tol=float(ctx.cfg["mpc"].get("solver_tolerance", 1e-8)),
        max_iter=int(ctx.cfg["mpc"].get("solver_max_iterations", 200)),
        lsmr_tol="auto",
        verbose=0,
    )
    sequence = np.asarray(solution.x, dtype=float).reshape(len(future_steps), 3)
    first = sequence[0]
    rate_limit = np.asarray(ctx.cfg["mpc"]["per_step_correction_rate_limit_by_mode"], dtype=float)
    first = np.clip(first, np.asarray(previous_correction) - rate_limit, np.asarray(previous_correction) + rate_limit)
    first = np.clip(first, lower[:3], upper[:3])
    predicted_residual = a @ np.asarray(solution.x, dtype=float) + future_error
    return {
        "first_correction": first,
        "sequence_correction": sequence,
        "solver_success": bool(solution.success),
        "solver_status": int(solution.status),
        "solver_cost": float(solution.cost),
        "solver_optimality": float(solution.optimality),
        "predicted_normalized_residual_rms": float(np.sqrt(np.mean(predicted_residual**2))),
        "active_lower": int(np.sum(np.isclose(solution.x, lower, atol=1e-7))),
        "active_upper": int(np.sum(np.isclose(solution.x, upper, atol=1e-7))),
    }


class LocalRecedingMpcWorker:
    def __init__(self, ctx_payload: dict[str, Any], library: dict[str, Any], worker_id: str):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env

        self.cfg = ctx_payload["cfg"]
        self.train_cfg = ctx_payload["train_cfg"]
        self.env_cfg = ctx_payload["env_cfg"]
        self.modes_tsc = np.asarray(ctx_payload["modes_tsc"], dtype=float)
        self.max_delta_a = float(ctx_payload["max_delta_a"])
        self.min_current = np.asarray(ctx_payload["min_current_tsc"], dtype=float)
        self.max_current = np.asarray(ctx_payload["max_current_tsc"], dtype=float)
        self.bundle = ctx_payload["source_bundle"]
        self.library = library
        self.env = make_tsc_rzip_env(copy.deepcopy(self.train_cfg), worker_id=worker_id, seed=None)
        self.context_stub = copy.copy(ctx_payload["context_stub"])

    def _mode_action(self, coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
        desired = np.asarray(coefficients, dtype=float) @ self.modes_tsc.T
        max_abs = float(np.max(np.abs(desired)))
        if max_abs > 1.0:
            desired = desired / max_abs
        delta = desired * self.max_delta_a
        current_scale = 1.0
        for coil in range(14):
            if delta[coil] > 0.0:
                current_scale = min(current_scale, max(0.0, (self.max_current[coil] - currents[coil]) / max(delta[coil], 1e-30)))
            elif delta[coil] < 0.0:
                current_scale = min(current_scale, max(0.0, (self.min_current[coil] - currents[coil]) / min(delta[coil], -1e-30)))
        return np.asarray(desired * float(np.clip(current_scale, 0.0, 1.0)), dtype=np.float32)

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        trajectory: list[dict[str, Any]] = []
        control_trace: list[dict[str, Any]] = []
        failure_reason = ""
        try:
            target_offset = np.asarray(
                [spec["target_R_offset_m"], spec["target_Z_offset_m"], spec["target_Ip_offset_A"]],
                dtype=float,
            )
            interpolation = interpolation_for_target(self.context_stub, self.library, target_offset)
            nominal_coefficients = _vector(interpolation["full_control_vector"], 75).reshape(25, 3)
            nominal_y = np.asarray(interpolation["nominal_trajectory_RZI"], dtype=float)
            nominal_velocity = np.asarray(interpolation["nominal_velocity_RZ"], dtype=float)
            requested_target = np.asarray(
                [
                    float(self.cfg["target"]["R"]) + target_offset[0],
                    float(self.cfg["target"]["Z"]) + target_offset[1],
                    float(self.cfg["target"]["Ip"]) + target_offset[2],
                ],
                dtype=float,
            )
            nominal_feature = _full_nominal_feature(self.context_stub, nominal_y, nominal_velocity, requested_target)
            measurement_scale = np.asarray(
                [
                    self.cfg["mpc"]["output_scales"]["R_m"],
                    self.cfg["mpc"]["output_scales"]["Z_m"],
                    self.cfg["mpc"]["output_scales"]["vR_m_per_s"],
                    self.cfg["mpc"]["output_scales"]["vZ_m_per_s"],
                    self.cfg["mpc"]["output_scales"]["Ip_A"],
                ],
                dtype=float,
            )
            integral = np.zeros(5, dtype=float)
            previous_correction = np.zeros(3, dtype=float)
            controller_scale = float(spec["controller_scale"])
            self.env.reset()
            zero = np.zeros(14, dtype=float)
            trajectory.append(s32.jsonio._state_record(self.env, 0, zero))
            dt = float(self.env_cfg["dt_ms"]) / 1000.0
            for step in range(25):
                state = self.env.last_state
                current_y = np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)
                if step > 0:
                    previous_rz = np.asarray([trajectory[-2]["R"], trajectory[-2]["Z"]], dtype=float)
                    current_velocity = (current_y[:2] - previous_rz) / dt
                else:
                    current_velocity = np.zeros(2, dtype=float)
                measurement_physical = np.asarray(
                    [
                        current_y[0] - nominal_y[step, 0],
                        current_y[1] - nominal_y[step, 1],
                        current_velocity[0] - nominal_velocity[step, 0],
                        current_velocity[1] - nominal_velocity[step, 1],
                        current_y[2] - nominal_y[step, 2],
                    ],
                    dtype=float,
                )
                measurement = measurement_physical / measurement_scale
                integral_decay = float(self.cfg["mpc"].get("integral_decay", 0.92))
                integral = integral_decay * integral + (1.0 - integral_decay) * measurement
                if controller_scale <= 0.0:
                    solve = {
                        "first_correction": np.zeros(3, dtype=float),
                        "solver_success": True,
                        "solver_status": 0,
                        "solver_cost": 0.0,
                        "solver_optimality": 0.0,
                        "predicted_normalized_residual_rms": float(np.sqrt(np.mean(measurement**2))),
                        "active_lower": 0,
                        "active_upper": 0,
                    }
                else:
                    solve = solve_receding_horizon_correction(
                        self.context_stub,
                        current_step=step,
                        nominal_coefficients=nominal_coefficients,
                        nominal_feature=nominal_feature,
                        measurement_normalized=measurement,
                        integral_normalized=integral,
                        previous_correction=previous_correction,
                        controller_scale=controller_scale,
                    )
                correction = np.asarray(solve["first_correction"], dtype=float)
                coefficients = nominal_coefficients[step] + correction
                disturbance = spec.get("disturbance")
                if disturbance and step == int(disturbance["step"]):
                    coefficients = coefficients.copy()
                    coefficients[int(disturbance["mode"])] += float(disturbance["amplitude"])
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(coefficients, currents)
                _, _, terminated, truncated, info = self.env.step(action)
                trajectory.append(s32.jsonio._state_record(self.env, step + 1, action))
                control_trace.append(
                    {
                        "step": step,
                        "measurement_physical": measurement_physical.tolist(),
                        "measurement_normalized": measurement.tolist(),
                        "integral_normalized": integral.tolist(),
                        "mode_correction": correction.tolist(),
                        "mode_command": np.asarray(coefficients, dtype=float).tolist(),
                        "solver_success": bool(solve["solver_success"]),
                        "solver_status": int(solve["solver_status"]),
                        "solver_cost": float(solve["solver_cost"]),
                        "solver_optimality": float(solve["solver_optimality"]),
                        "predicted_normalized_residual_rms": float(solve["predicted_normalized_residual_rms"]),
                        "active_lower": int(solve["active_lower"]),
                        "active_upper": int(solve["active_upper"]),
                    }
                )
                previous_correction = correction
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated"))
                    break
                if truncated and step + 1 < 25:
                    failure_reason = "environment truncated before 25 steps"
                    break
            success = len(trajectory) == 26 and not any(bool(row.get("abnormal", False)) for row in trajectory)
            result = {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": spec["experiment_id"],
                "spec": spec,
                "success": bool(success),
                "failure_reason": "" if success else (failure_reason or "incomplete/abnormal trajectory"),
                "wall_time_s": float(time.time() - started),
                "trajectory": trajectory,
                "control_trace": control_trace,
                "library_interpolation": interpolation,
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
                "control_trace": control_trace,
            }
        runner = getattr(self.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(
                failed=not bool(result.get("success", False)),
                reason=str(result.get("failure_reason", "stage3_3_mpc_complete")),
            )
        return _json_safe(result)

    def close(self) -> None:
        self.env.close()


def _mpc_ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class MpcActor:
        def __init__(self, ctx_payload, library, worker_id):
            self.worker = LocalRecedingMpcWorker(ctx_payload, library, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return MpcActor


def _context_payload(ctx: Stage33Context) -> dict[str, Any]:
    stub = SimpleNamespace(
        cfg=copy.deepcopy(ctx.cfg),
        env_cfg=copy.deepcopy(ctx.env_cfg),
        source_bundle=copy.deepcopy(ctx.source_bundle),
    )
    return {
        "cfg": ctx.cfg,
        "train_cfg": ctx.train_cfg,
        "env_cfg": ctx.env_cfg,
        "modes_tsc": ctx.modes_tsc.tolist(),
        "max_delta_a": ctx.max_delta_a,
        "min_current_tsc": ctx.min_current_tsc.tolist(),
        "max_current_tsc": ctx.max_current_tsc.tolist(),
        "source_bundle": ctx.source_bundle,
        "context_stub": stub,
    }


def build_mpc_specs(
    ctx: Stage33Context,
    *,
    scenarios: Sequence[dict[str, Any]],
    controller_scales: Sequence[float],
    split: str,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for scenario in scenarios:
        for scale in controller_scales:
            scale = float(scale)
            experiment_id = (
                f"s33mpc_{split}_{scenario['scenario']}_scale{scale:.2f}"
                .replace(".", "p")
                .replace("-", "m")
                .replace("+", "p")
            )
            specs.append(
                {
                    "kind": "stage3_3_receding_horizon_mpc",
                    "experiment_id": experiment_id,
                    "scenario": str(scenario["scenario"]),
                    "scenario_split": split,
                    "category": str(scenario.get("category", "target")),
                    "target_R_offset_m": float(scenario.get("target_R_offset_m", 0.0)),
                    "target_Z_offset_m": float(scenario.get("target_Z_offset_m", 0.0)),
                    "target_Ip_offset_A": float(scenario.get("target_Ip_offset_A", 0.0)),
                    "disturbance": copy.deepcopy(scenario.get("disturbance")),
                    "controller_scale": scale,
                    "horizon_steps": 25,
                }
            )
    ids = [str(spec["experiment_id"]) for spec in specs]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate Stage3.3 MPC experiment id")
    return specs


def evaluate_mpc_specs(
    ctx: Stage33Context,
    specs: Sequence[dict[str, Any]],
    *,
    library: dict[str, Any],
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pending: list[dict[str, Any]] = []
    for spec in specs:
        path = output_dir / f"{spec['experiment_id']}.json.gz"
        if resume and path.exists():
            try:
                if read_json_gz(path).get("success"):
                    continue
            except Exception:
                pass
        pending.append(spec)
    payload = _context_payload(ctx)
    if pending and backend == "serial":
        worker = LocalRecedingMpcWorker(payload, library, "stage33_mpc_serial")
        try:
            for index, spec in enumerate(pending, 1):
                result = worker.evaluate(spec)
                atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                print(f"[Stage3.3 MPC] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif pending and backend == "ray":
        import ray

        requested = int(os.environ.get("STAGE3_3_WORKERS", ctx.cfg.get("parallel", {}).get("n_workers", 96)))
        ray_tmpdir = os.environ.get("RAY_TMPDIR", ctx.cfg.get("parallel", {}).get("ray_tmpdir", "")) or None
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=ray_tmpdir,
            log_prefix="[Stage3.3 MPC]",
        )
        Actor = _mpc_ray_actor_class()
        actors = [Actor.remote(payload, library, f"stage33_mpc_{index:03d}") for index in range(plan.actor_count)]
        refs = {actors[index % plan.actor_count].evaluate.remote(spec): spec for index, spec in enumerate(pending)}
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage3.3 MPC] waiting {done}/{len(pending)}", flush=True)
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
                            "control_trace": [],
                        }
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    print(f"[Stage3.3 MPC] {done}/{len(pending)}", flush=True)
        finally:
            s2._close_ray_actors(actors, timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 900.0)))
    elif pending:
        raise ValueError("backend must be ray or serial")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


def summarize_mpc_results(ctx: Stage33Context, results: Sequence[dict[str, Any]], *, output_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        task = scenario_task(spec)
        metrics = target_metrics(ctx, task, result, None)
        trace = result.get("control_trace", [])
        max_correction = 0.0
        correction_rms = 0.0
        solver_failures = 0
        if trace:
            correction = np.asarray([row["mode_correction"] for row in trace], dtype=float)
            max_correction = float(np.max(np.abs(correction)))
            correction_rms = float(np.sqrt(np.mean(correction**2)))
            solver_failures = sum(not bool(row.get("solver_success", False)) for row in trace)
        rows.append(
            {
                "scenario": str(spec["scenario"]),
                "scenario_split": str(spec["scenario_split"]),
                "scenario_category": str(spec["category"]),
                "controller_scale": float(spec["controller_scale"]),
                "target_R_offset_m": float(spec["target_R_offset_m"]),
                "target_Z_offset_m": float(spec["target_Z_offset_m"]),
                "target_Ip_offset_A": float(spec["target_Ip_offset_A"]),
                "disturbance": copy.deepcopy(spec.get("disturbance")),
                "result_relpath": str((output_dir / f"{spec['experiment_id']}.json.gz").relative_to(ctx.paths.run_dir)),
                "maximum_abs_mode_correction": max_correction,
                "mode_correction_rms": correction_rms,
                "solver_failure_steps": solver_failures,
                **metrics,
            }
        )
    return rows


def mpc_scale_summaries(ctx: Stage33Context, rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    by_scenario: dict[str, dict[float, dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), {})[float(row["controller_scale"])] = row
    positive = sorted({float(row["controller_scale"]) for row in rows if float(row["controller_scale"]) > 0.0})
    summaries: list[dict[str, Any]] = []
    validation = ctx.cfg["mpc"]["calibration_validation"]
    for scale in positive:
        comparisons: list[dict[str, Any]] = []
        gained: list[float] = []
        lost = recovered = preserved = baseline_pass = feedback_pass = 0
        all_success = True
        for scenario, group in sorted(by_scenario.items()):
            baseline = group.get(0.0)
            feedback = group.get(scale)
            if baseline is None or feedback is None:
                all_success = False
                continue
            pair_success = _as_bool(baseline.get("success"), False) and _as_bool(feedback.get("success"), False)
            all_success = all_success and pair_success
            base_pass = _as_bool(baseline.get("stage3_3_target_tracking_pass"), False)
            fb_pass = _as_bool(feedback.get("stage3_3_target_tracking_pass"), False)
            base_margin = _finite(baseline.get("stage3_3_tracking_minimum_signed_margin"), -1e12)
            fb_margin = _finite(feedback.get("stage3_3_tracking_minimum_signed_margin"), -1e12)
            gain = fb_margin - base_margin
            baseline_pass += int(base_pass)
            feedback_pass += int(fb_pass)
            lost += int(base_pass and not fb_pass)
            recovered += int((not base_pass) and fb_pass)
            preserved += int(base_pass and fb_pass)
            gained.append(gain)
            comparisons.append(
                {
                    "scenario": scenario,
                    "baseline_tracking_pass": base_pass,
                    "mpc_tracking_pass": fb_pass,
                    "baseline_signed_margin": base_margin,
                    "mpc_signed_margin": fb_margin,
                    "signed_margin_gain": gain,
                    "lost": base_pass and not fb_pass,
                    "recovered": (not base_pass) and fb_pass,
                    "preserved": base_pass and fb_pass,
                    "pair_success": pair_success,
                }
            )
        n = len(comparisons)
        fraction = feedback_pass / max(n, 1)
        median_gain = None if not gained else float(np.median(gained))
        worst_gain = None if not gained else float(np.min(gained))
        baseline_failures = max(n - baseline_pass, 0)
        recovery_ok = baseline_failures == 0 or recovered >= int(validation["minimum_recovered_scenarios"])
        passed = bool(
            all_success
            and lost <= int(validation["maximum_lost_baseline_pass_scenarios"])
            and fraction >= float(validation["minimum_tracking_pass_fraction"])
            and recovery_ok
            and median_gain is not None
            and median_gain >= float(validation["minimum_median_signed_margin_gain"])
            and worst_gain is not None
            and worst_gain >= float(validation["minimum_worst_case_signed_margin_gain"])
        )
        summaries.append(
            {
                "controller_scale": scale,
                "n_scenarios": n,
                "n_baseline_tracking_pass": baseline_pass,
                "n_mpc_tracking_pass": feedback_pass,
                "n_preserved": preserved,
                "n_recovered": recovered,
                "n_lost": lost,
                "n_baseline_failures": baseline_failures,
                "recovery_requirement_met": recovery_ok,
                "tracking_pass_fraction": fraction,
                "median_signed_margin_gain": median_gain,
                "worst_case_signed_margin_gain": worst_gain,
                "all_rollouts_successful": all_success,
                "calibration_pass": passed,
                "comparisons": comparisons,
            }
        )
    if not summaries:
        return [], None
    passing = [row for row in summaries if row["calibration_pass"]]
    pool = passing if passing else summaries
    selected = min(
        pool,
        key=lambda row: (
            int(row["n_lost"]),
            -int(row["n_mpc_tracking_pass"]),
            -int(row["n_recovered"]),
            -_finite(row.get("worst_case_signed_margin_gain"), -1e12),
            -_finite(row.get("median_signed_margin_gain"), -1e12),
            float(row["controller_scale"]),
        ),
    )
    return summaries, selected


def run_mpc_calibration(ctx: Stage33Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    summary_path = ctx.paths.calibration / "calibration_summary.json"
    if state.get("mpc_calibration_complete") and summary_path.exists():
        return read_json(summary_path)
    library = materialize_target_library(ctx)
    scenarios = validation_scenarios(ctx, "calibration")
    specs = build_mpc_specs(
        ctx,
        scenarios=scenarios,
        controller_scales=[0.0, *[float(value) for value in ctx.cfg["mpc"]["controller_scales"]]],
        split="calibration",
    )
    results = evaluate_mpc_specs(
        ctx,
        specs,
        library=library,
        output_dir=ctx.paths.calibration / "raw",
        backend=backend,
        resume=resume,
    )
    rows = summarize_mpc_results(ctx, results, output_dir=ctx.paths.calibration / "raw")
    atomic_write_json(ctx.paths.calibration / "calibration_results.json", rows)
    write_csv(ctx.paths.calibration / "calibration_results.csv", rows)
    scale_rows, selected = mpc_scale_summaries(ctx, rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "n_scenarios": len(scenarios),
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success"), False) for row in rows),
        "scale_summaries": scale_rows,
        "selected_scale_summary": selected,
        "selected_controller_scale": None if selected is None else float(selected["controller_scale"]),
        "mpc_calibration_pass": bool(selected and selected["calibration_pass"]),
    }
    atomic_write_json(summary_path, summary)
    state["mpc_calibration_complete"] = True
    state["selected_controller_scale"] = summary["selected_controller_scale"]
    state["mpc_calibration_pass"] = summary["mpc_calibration_pass"]
    atomic_write_json(ctx.paths.state, state)
    return summary


def holdout_summary(ctx: Stage33Context, rows: Sequence[dict[str, Any]], *, selected_scale: float) -> dict[str, Any]:
    by_scenario: dict[str, dict[float, dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), {})[float(row["controller_scale"])] = row
    comparisons: list[dict[str, Any]] = []
    lost = recovered = preserved = baseline_pass = mpc_pass = 0
    gains: list[float] = []
    all_success = True
    for scenario, group in sorted(by_scenario.items()):
        baseline = group.get(0.0)
        feedback = group.get(float(selected_scale))
        if baseline is None or feedback is None:
            all_success = False
            continue
        pair_success = _as_bool(baseline.get("success"), False) and _as_bool(feedback.get("success"), False)
        all_success = all_success and pair_success
        base_ok = _as_bool(baseline.get("stage3_3_target_tracking_pass"), False)
        mpc_ok = _as_bool(feedback.get("stage3_3_target_tracking_pass"), False)
        base_margin = _finite(baseline.get("stage3_3_tracking_minimum_signed_margin"), -1e12)
        mpc_margin = _finite(feedback.get("stage3_3_tracking_minimum_signed_margin"), -1e12)
        gain = mpc_margin - base_margin
        baseline_pass += int(base_ok)
        mpc_pass += int(mpc_ok)
        lost += int(base_ok and not mpc_ok)
        recovered += int((not base_ok) and mpc_ok)
        preserved += int(base_ok and mpc_ok)
        gains.append(gain)
        comparisons.append(
            {
                "scenario": scenario,
                "baseline_tracking_pass": base_ok,
                "mpc_tracking_pass": mpc_ok,
                "baseline_signed_margin": base_margin,
                "mpc_signed_margin": mpc_margin,
                "signed_margin_gain": gain,
                "lost": base_ok and not mpc_ok,
                "recovered": (not base_ok) and mpc_ok,
                "preserved": base_ok and mpc_ok,
                "pair_success": pair_success,
            }
        )
    validation = ctx.cfg["mpc"]["holdout_validation"]
    fraction = mpc_pass / max(len(comparisons), 1)
    baseline_failures = max(len(comparisons) - baseline_pass, 0)
    recovery_fraction = 1.0 if baseline_failures == 0 else recovered / baseline_failures
    median_gain = None if not gains else float(np.median(gains))
    worst_gain = None if not gains else float(np.min(gains))
    passed = bool(
        all_success
        and lost <= int(validation["maximum_lost_baseline_pass_scenarios"])
        and fraction >= float(validation["minimum_tracking_pass_fraction"])
        and recovery_fraction >= float(validation["minimum_recovery_fraction"])
        and median_gain is not None
        and median_gain >= float(validation["minimum_median_signed_margin_gain"])
        and worst_gain is not None
        and worst_gain >= float(validation["minimum_worst_case_signed_margin_gain"])
    )
    return {
        "selected_controller_scale": float(selected_scale),
        "n_scenarios": len(comparisons),
        "n_baseline_tracking_pass": baseline_pass,
        "n_mpc_tracking_pass": mpc_pass,
        "n_preserved": preserved,
        "n_recovered": recovered,
        "n_lost": lost,
        "tracking_pass_fraction": fraction,
        "recovery_fraction": recovery_fraction,
        "median_signed_margin_gain": median_gain,
        "worst_case_signed_margin_gain": worst_gain,
        "all_rollouts_successful": all_success,
        "holdout_validation_pass": passed,
        "comparisons": comparisons,
    }


def run_mpc_holdout(ctx: Stage33Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    summary_path = ctx.paths.holdout / "holdout_summary.json"
    if state.get("mpc_holdout_complete") and summary_path.exists():
        return read_json(summary_path)
    calibration = run_mpc_calibration(ctx, backend=backend, resume=resume)
    selected_scale = calibration.get("selected_controller_scale")
    if selected_scale is None:
        raise RuntimeError("No Stage3.3 controller scale was selected during calibration")
    library = materialize_target_library(ctx)
    scenarios = validation_scenarios(ctx, "holdout")
    specs = build_mpc_specs(
        ctx,
        scenarios=scenarios,
        controller_scales=[0.0, float(selected_scale)],
        split="holdout",
    )
    results = evaluate_mpc_specs(
        ctx,
        specs,
        library=library,
        output_dir=ctx.paths.holdout / "raw",
        backend=backend,
        resume=resume,
    )
    rows = summarize_mpc_results(ctx, results, output_dir=ctx.paths.holdout / "raw")
    atomic_write_json(ctx.paths.holdout / "holdout_results.json", rows)
    write_csv(ctx.paths.holdout / "holdout_results.csv", rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        **holdout_summary(ctx, rows, selected_scale=float(selected_scale)),
    }
    atomic_write_json(summary_path, summary)
    state["mpc_holdout_complete"] = True
    state["mpc_holdout_pass"] = bool(summary["holdout_validation_pass"])
    atomic_write_json(ctx.paths.state, state)
    return summary


# ---------------------------------------------------------------------------
# Phase F: confirmation, artifacts, analysis, report
# ---------------------------------------------------------------------------


def _scenario_lookup(ctx: Stage33Context) -> dict[str, dict[str, Any]]:
    rows = [*validation_scenarios(ctx, "calibration"), *validation_scenarios(ctx, "holdout")]
    return {str(row["scenario"]): row for row in rows}


def run_mpc_confirmation(ctx: Stage33Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    summary_path = ctx.paths.confirmations / "mpc_confirmation_summary.json"
    if state.get("mpc_confirmation_complete") and summary_path.exists():
        return read_json(summary_path)
    calibration = run_mpc_calibration(ctx, backend=backend, resume=resume)
    holdout = run_mpc_holdout(ctx, backend=backend, resume=resume)
    scale = calibration.get("selected_controller_scale")
    if scale is None:
        raise RuntimeError("Stage3.3 confirmation has no selected MPC scale")
    lookup = _scenario_lookup(ctx)
    names = [str(value) for value in ctx.cfg["confirmation"]["mpc_scenarios"]]
    repeats = int(ctx.cfg["confirmation"].get("mpc_repeats", 2))
    specs: list[dict[str, Any]] = []
    for name in names:
        if name not in lookup:
            raise KeyError(f"confirmation scenario {name!r} is absent from calibration/holdout design")
        scenario = lookup[name]
        for repeat in range(repeats):
            experiment_id = f"s33confirm_mpc_{name}_scale{float(scale):.2f}_r{repeat:02d}".replace(".", "p").replace("-", "m").replace("+", "p")
            specs.append(
                {
                    "kind": "stage3_3_mpc_confirmation",
                    "experiment_id": experiment_id,
                    "scenario": name,
                    "scenario_split": "confirmation",
                    "category": str(scenario.get("category", "target")),
                    "target_R_offset_m": float(scenario.get("target_R_offset_m", 0.0)),
                    "target_Z_offset_m": float(scenario.get("target_Z_offset_m", 0.0)),
                    "target_Ip_offset_A": float(scenario.get("target_Ip_offset_A", 0.0)),
                    "disturbance": copy.deepcopy(scenario.get("disturbance")),
                    "controller_scale": float(scale),
                    "confirmation_repeat": repeat,
                    "horizon_steps": 25,
                }
            )
    library = materialize_target_library(ctx)
    results = evaluate_mpc_specs(
        ctx,
        specs,
        library=library,
        output_dir=ctx.paths.confirmations / "mpc_raw",
        backend=backend,
        resume=resume,
    )
    rows = summarize_mpc_results(ctx, results, output_dir=ctx.paths.confirmations / "mpc_raw")
    atomic_write_json(ctx.paths.confirmations / "mpc_confirmation_results.json", rows)
    write_csv(ctx.paths.confirmations / "mpc_confirmation_results.csv", rows)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["scenario"]), []).append(row)
    scenarios: list[dict[str, Any]] = []
    for name in names:
        group = grouped.get(name, [])
        scenarios.append(
            {
                "scenario": name,
                "repeats": len(group),
                "successful_repeats": sum(_as_bool(row.get("success"), False) for row in group),
                "all_repeats_tracking_pass": bool(group) and all(_as_bool(row.get("stage3_3_target_tracking_pass"), False) for row in group),
                "worst_tracking_signed_margin": None if not group else float(min(_finite(row.get("stage3_3_tracking_minimum_signed_margin"), -1e12) for row in group)),
                "worst_sustained_box_m": None if not group else float(max(_finite(row.get("stage3_3_sustained_box_max_error_m", row.get("stage3_2_sustained_box_max_error_m")), 1e12) for row in group)),
                "worst_ip_hold_rms_A": None if not group else float(max(_finite(row.get("stage3_3_ip_hold_rms_error_A"), 1e12) for row in group)),
            }
        )
    required_fraction = float(ctx.cfg["confirmation"].get("minimum_mpc_scenario_pass_fraction", 0.80))
    pass_fraction = sum(bool(row["all_repeats_tracking_pass"]) for row in scenarios) / max(len(scenarios), 1)
    passed = bool(pass_fraction >= required_fraction)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "selected_controller_scale": float(scale),
        "n_scenarios": len(scenarios),
        "n_rollouts": len(rows),
        "scenario_pass_fraction": pass_fraction,
        "mpc_confirmation_pass": passed,
        "scenario_summaries": scenarios,
        "calibration_pass": bool(calibration.get("mpc_calibration_pass", False)),
        "holdout_pass": bool(holdout.get("holdout_validation_pass", False)),
    }
    atomic_write_json(summary_path, summary)
    state["mpc_confirmation_complete"] = True
    state["mpc_confirmation_pass"] = passed
    atomic_write_json(ctx.paths.state, state)
    return summary


def write_controller_artifact(ctx: Stage33Context) -> dict[str, Any]:
    library = materialize_target_library(ctx)
    calibration_path = ctx.paths.calibration / "calibration_summary.json"
    holdout_path = ctx.paths.holdout / "holdout_summary.json"
    confirmation_path = ctx.paths.confirmations / "mpc_confirmation_summary.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "controller_type": "target-conditioned nominal interpolation plus per-step receding-horizon bounded least-squares MPC",
        "source_stage3_2_controller_center": ctx.source_bundle["center_candidate_id"],
        "source_stage3_2_jacobian_physical_units": ctx.source_bundle["jacobian_physical_units"],
        "source_stage3_2_jacobian_normalized": ctx.source_bundle["jacobian_normalized"],
        "source_stage3_2_output_scales": ctx.source_bundle["output_scales"],
        "target_library": library,
        "mpc_config": copy.deepcopy(ctx.cfg["mpc"]),
        "selected_controller_scale": None,
        "target_library_confirmed": False,
        "mpc_calibration_pass": False,
        "mpc_holdout_pass": False,
        "mpc_confirmation_pass": False,
        "online_receding_horizon_mpc_validated_for_tested_target_envelope": False,
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "noise_delay_robustness_validated": False,
        "deployment_status": "OFFLINE_STAGE3_3_CONTROLLER_ARTIFACT_ONLY",
        "warning": (
            "This artifact may pass a finite target/disturbance campaign, but it does not validate new initial states, "
            "plant parameters, measurement noise, delay, or long-discharge operation. Residual RL must remain bounded and secondary."
        ),
    }
    library_confirmation = ctx.paths.library / "target_library_confirmation_summary.json"
    if library_confirmation.exists():
        summary = read_json(library_confirmation)
        payload["target_library_confirmed"] = bool(summary.get("target_library_confirmed", False))
    if calibration_path.exists():
        summary = read_json(calibration_path)
        payload["selected_controller_scale"] = summary.get("selected_controller_scale")
        payload["mpc_calibration_pass"] = bool(summary.get("mpc_calibration_pass", False))
    if holdout_path.exists():
        payload["mpc_holdout_pass"] = bool(read_json(holdout_path).get("holdout_validation_pass", False))
    if confirmation_path.exists():
        payload["mpc_confirmation_pass"] = bool(read_json(confirmation_path).get("mpc_confirmation_pass", False))
    payload["online_receding_horizon_mpc_validated_for_tested_target_envelope"] = bool(
        payload["target_library_confirmed"]
        and payload["mpc_calibration_pass"]
        and payload["mpc_holdout_pass"]
        and payload["mpc_confirmation_pass"]
    )
    if payload["online_receding_horizon_mpc_validated_for_tested_target_envelope"]:
        payload["deployment_status"] = "TESTED_TARGET_ENVELOPE_POC_PASSED_NOT_ROBUSTNESS_VALIDATED"
    atomic_write_json(ctx.paths.controller / "stage3_3_controller_bundle.json", payload)
    return payload


def final_verdict(ctx: Stage33Context) -> dict[str, Any]:
    library_path = ctx.paths.library / "target_library_confirmation_summary.json"
    calibration_path = ctx.paths.calibration / "calibration_summary.json"
    holdout_path = ctx.paths.holdout / "holdout_summary.json"
    confirmation_path = ctx.paths.confirmations / "mpc_confirmation_summary.json"
    library_confirmation = read_json(library_path) if library_path.exists() else {}
    calibration = read_json(calibration_path) if calibration_path.exists() else {}
    holdout = read_json(holdout_path) if holdout_path.exists() else {}
    mpc_confirmation = read_json(confirmation_path) if confirmation_path.exists() else {}
    strong = bool(
        library_confirmation.get("target_library_confirmed", False)
        and calibration.get("mpc_calibration_pass", False)
        and holdout.get("holdout_validation_pass", False)
        and mpc_confirmation.get("mpc_confirmation_pass", False)
    )
    if strong:
        verdict = "PASS_TARGET_CONDITIONED_RECEDING_HORIZON_MPC_TEST_ENVELOPE_CONFIRMED"
    elif library_confirmation.get("target_library_confirmed", False):
        verdict = "PASS_TARGET_CONDITIONED_NOMINAL_LIBRARY_CONFIRMED_MPC_NOT_VALIDATED"
    else:
        verdict = "TARGET_CONDITIONED_LIBRARY_INCOMPLETE_MPC_NOT_VALIDATED"
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "target_library_confirmation": library_confirmation,
        "mpc_calibration": calibration,
        "mpc_holdout": holdout,
        "mpc_confirmation": mpc_confirmation,
        "online_receding_horizon_mpc_validated_for_tested_target_envelope": strong,
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "noise_delay_robustness_validated": False,
        "robustness_validated": False,
        "final_task_warning": (
            "Passing the finite Stage3.3 target/disturbance envelope is not the final tokamak controller. "
            "Different initial states, hidden vessel/eddy-current states, plant parameters, measurement noise, and latency remain untested."
        ),
    }


def _plot_results(ctx: Stage33Context) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    library = materialize_target_library(ctx)
    entries = library["entries"]
    if entries:
        x = [float(row["task"]["R_offset_m"]) * 1000.0 for row in entries]
        y = [float(row["task"]["Z_offset_m"]) * 1000.0 for row in entries]
        margin = [_finite(row.get("stage3_3_tracking_minimum_signed_margin"), -1.0) for row in entries]
        passed = [_as_bool(row.get("stage3_3_target_tracking_pass"), False) for row in entries]
        fig, ax = plt.subplots(figsize=(7.5, 6.0))
        scatter = ax.scatter(x, y, c=margin, s=[80 if value else 40 for value in passed])
        for row, xx, yy in zip(entries, x, y):
            ax.annotate(str(row["task"]["task_id"]), (xx, yy), fontsize=6, xytext=(3, 3), textcoords="offset points")
        ax.axhline(0.0, linewidth=0.8)
        ax.axvline(0.0, linewidth=0.8)
        ax.set_xlabel("Target R offset [mm]")
        ax.set_ylabel("Target Z offset [mm]")
        ax.set_title("Stage3.3 target-conditioned nominal library")
        fig.colorbar(scatter, ax=ax, label="Tracking signed margin")
        fig.tight_layout()
        fig.savefig(ctx.paths.analysis / "target_library_rz_map.png", dpi=160)
        plt.close(fig)
    holdout_path = ctx.paths.holdout / "holdout_results.json"
    if holdout_path.exists():
        rows = read_json(holdout_path)
        scenarios = sorted({str(row["scenario"]) for row in rows})
        baseline = []
        mpc = []
        selected = read_json(ctx.paths.holdout / "holdout_summary.json")["selected_controller_scale"]
        for scenario in scenarios:
            group = [row for row in rows if str(row["scenario"]) == scenario]
            baseline.append(next(_finite(row.get("stage3_3_tracking_minimum_signed_margin"), -1.0) for row in group if float(row["controller_scale"]) == 0.0))
            mpc.append(next(_finite(row.get("stage3_3_tracking_minimum_signed_margin"), -1.0) for row in group if math.isclose(float(row["controller_scale"]), float(selected))))
        positions = np.arange(len(scenarios))
        fig, ax = plt.subplots(figsize=(max(10.0, 0.55 * len(scenarios)), 5.5))
        ax.bar(positions - 0.2, baseline, width=0.4, label="Interpolated nominal")
        ax.bar(positions + 0.2, mpc, width=0.4, label=f"RH-MPC scale {selected}")
        ax.axhline(0.0, linewidth=1.0)
        ax.set_xticks(positions)
        ax.set_xticklabels(scenarios, rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("Target tracking signed margin")
        ax.set_title("Stage3.3 held-out target/disturbance comparison")
        ax.legend()
        fig.tight_layout()
        fig.savefig(ctx.paths.analysis / "holdout_tracking_margin_comparison.png", dpi=160)
        plt.close(fig)


def write_report(ctx: Stage33Context, summary: dict[str, Any]) -> Path:
    verdict = summary["verdict"]
    library = summary["target_library"]
    calibration = summary.get("mpc_calibration", {})
    holdout = summary.get("mpc_holdout", {})
    confirmation = summary.get("mpc_confirmation", {})
    lines = [
        "# Stage3.3 Target-Conditioned Nominal Library and Receding-Horizon MPC",
        "",
        f"- Verdict: **{verdict['verdict']}**",
        f"- Configured targets: {library['n_configured_targets']}",
        f"- Tracking-pass library entries: {library['n_tracking_pass_entries']}",
        f"- Mandatory target passes: {library['n_mandatory_tracking_pass']}/{library['n_mandatory_targets']}",
        f"- Target library confirmed: {bool(verdict['target_library_confirmation'].get('target_library_confirmed', False))}",
        f"- Selected MPC scale: {calibration.get('selected_controller_scale')}",
        f"- MPC calibration pass: {bool(calibration.get('mpc_calibration_pass', False))}",
        f"- MPC holdout pass: {bool(holdout.get('holdout_validation_pass', False))}",
        f"- MPC confirmation pass: {bool(confirmation.get('mpc_confirmation_pass', False))}",
        "",
        "## What this stage proves",
        "",
        "Stage3.3 first builds separate real-TSC 250 ms nominal sequences for multiple R/Z/Ip targets. "
        "It then runs a bounded least-squares receding-horizon controller that resolves at every 10 ms step and applies only the first correction.",
        "",
        "## What this stage does not prove",
        "",
        "The campaign does not change the simulator restart state.  Action injections are not equivalent to genuine initial-state variation. "
        "Plant-parameter, hidden vessel/eddy-current state, measurement-noise, and delay robustness remain untested. "
        "The final controller must ultimately handle all of those effects; residual RL remains bounded and secondary.",
        "",
        "## Target library",
        "",
        "| Task | Mandatory | Tracking pass | Signed margin | Sustained box [mm] | Ip hold RMS [A] |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in library["entries"]:
        lines.append(
            "| {task} | {mandatory} | {passed} | {margin:.5f} | {box:.3f} | {ip:.1f} |".format(
                task=row["task"]["task_id"],
                mandatory=int(bool(row["task"]["mandatory"])),
                passed=int(_as_bool(row.get("stage3_3_target_tracking_pass"), False)),
                margin=_finite(row.get("stage3_3_tracking_minimum_signed_margin"), -1e12),
                box=1000.0 * _finite(row.get("stage3_3_sustained_box_max_error_m", row.get("stage3_2_sustained_box_max_error_m")), 1e12),
                ip=_finite(row.get("stage3_3_ip_hold_rms_error_A"), 1e12),
            )
        )
    lines.extend(
        [
            "",
            "## Final task",
            "",
            "The project objective is not a finite library or one MPC test envelope.  It is a causal robust controller across initial states, targets, "
            "plant uncertainty, hidden dynamic state, noise, and delay.  The intended architecture remains nominal + causal MPC/feedback + bounded residual RL.",
            "",
        ]
    )
    path = ctx.paths.run_dir / "STAGE3_3_REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def analyze_stage33(ctx: Stage33Context) -> dict[str, Any]:
    library = materialize_target_library(ctx)
    library_confirmation = read_json(ctx.paths.library / "target_library_confirmation_summary.json") if (ctx.paths.library / "target_library_confirmation_summary.json").exists() else {}
    calibration = read_json(ctx.paths.calibration / "calibration_summary.json") if (ctx.paths.calibration / "calibration_summary.json").exists() else {}
    holdout = read_json(ctx.paths.holdout / "holdout_summary.json") if (ctx.paths.holdout / "holdout_summary.json").exists() else {}
    mpc_confirmation = read_json(ctx.paths.confirmations / "mpc_confirmation_summary.json") if (ctx.paths.confirmations / "mpc_confirmation_summary.json").exists() else {}
    verdict = final_verdict(ctx)
    atomic_write_json(ctx.paths.confirmations / "stage3_3_verdict.json", verdict)
    controller = write_controller_artifact(ctx)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "source_stage3_2_run": str(ctx.source_stage32_run),
        "target_library": library,
        "target_library_confirmation": library_confirmation,
        "mpc_calibration": calibration,
        "mpc_holdout": holdout,
        "mpc_confirmation": mpc_confirmation,
        "controller_artifact": controller,
        "verdict": verdict,
        "online_receding_horizon_mpc_validated_for_tested_target_envelope": bool(verdict["online_receding_horizon_mpc_validated_for_tested_target_envelope"]),
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "noise_delay_robustness_validated": False,
        "robustness_validated": False,
        "final_task": "robust causal control across initial states, targets, plant uncertainty, hidden dynamics, noise, and delay",
    }
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.analysis / "stage3_3_analysis_summary.json", summary)
    _plot_results(ctx)
    report = write_report(ctx, summary)
    summary["report"] = str(report)
    atomic_write_json(ctx.paths.analysis / "stage3_3_analysis_summary.json", summary)
    return summary


# ---------------------------------------------------------------------------
# Run orchestration and CLI
# ---------------------------------------------------------------------------


def initial_state(ctx: Stage33Context) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "created_utc": utc_timestamp(),
        "warmstart_complete": False,
        "refinement_round": 0,
        "refinement_complete": False,
        "refinement_stop_reason": "",
        "library_confirmation_complete": False,
        "target_library_confirmed": False,
        "mpc_calibration_complete": False,
        "mpc_calibration_pass": False,
        "selected_controller_scale": None,
        "mpc_holdout_complete": False,
        "mpc_holdout_pass": False,
        "mpc_confirmation_complete": False,
        "mpc_confirmation_pass": False,
        "finished": False,
        "stop_reason": "",
    }


def prepare_stage33(ctx: Stage33Context, *, no_resume: bool = False) -> dict[str, Any]:
    initialize_stage33_run(ctx)
    if no_resume and ctx.paths.state.exists():
        raise FileExistsError(f"fresh Stage3.3 run already has state: {ctx.paths.state}")
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state(ctx))
    state = read_json(ctx.paths.state)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.3",
        "run_dir": str(ctx.paths.run_dir),
        "source_stage3_2_run": str(ctx.source_stage32_run),
        "source_stage3_2_fingerprint": ctx.source_fingerprint["digest"],
        "n_target_tasks": len(ctx.target_tasks),
        "n_mandatory_target_tasks": sum(bool(task["mandatory"]) for task in ctx.target_tasks),
        "source_center_candidate_id": ctx.source_center["candidate_id"],
        "source_best_candidate_id": ctx.source_best["candidate_id"],
        "source_jacobian_shape": list(np.asarray(ctx.source_bundle["jacobian_physical_units"]).shape),
        "state": state,
    }


def execute(
    *,
    config_path: str | Path,
    source_stage32_run: str | Path | None,
    run_dir: str | Path | None,
    command: str,
    backend: str,
    no_resume: bool,
) -> dict[str, Any]:
    ctx = load_stage33_config(
        config_path,
        source_stage32_run=source_stage32_run,
        run_dir_override=run_dir,
    )
    prepare = prepare_stage33(ctx, no_resume=no_resume)
    resume = not no_resume
    if command == "prepare":
        return prepare
    if command == "warmstart":
        return run_warmstart(ctx, backend=backend, resume=resume)
    if command == "refine-round":
        run_warmstart(ctx, backend=backend, resume=resume)
        return run_one_refinement_round(ctx, backend=backend, resume=resume)
    if command == "refine":
        run_warmstart(ctx, backend=backend, resume=resume)
        return run_refinement(ctx, backend=backend, resume=resume)
    if command == "library-confirm":
        run_warmstart(ctx, backend=backend, resume=resume)
        run_refinement(ctx, backend=backend, resume=resume)
        return run_library_confirmation(ctx, backend=backend, resume=resume)
    if command == "calibrate":
        run_warmstart(ctx, backend=backend, resume=resume)
        run_refinement(ctx, backend=backend, resume=resume)
        confirmation = run_library_confirmation(ctx, backend=backend, resume=resume)
        if not confirmation.get("target_library_confirmed") and not bool(ctx.cfg["mpc"].get("allow_incomplete_library", False)):
            raise RuntimeError("Target library is not confirmed; MPC calibration is disabled by configuration")
        return run_mpc_calibration(ctx, backend=backend, resume=resume)
    if command == "holdout":
        return run_mpc_holdout(ctx, backend=backend, resume=resume)
    if command == "confirm":
        run_library_confirmation(ctx, backend=backend, resume=resume)
        run_mpc_calibration(ctx, backend=backend, resume=resume)
        run_mpc_holdout(ctx, backend=backend, resume=resume)
        return run_mpc_confirmation(ctx, backend=backend, resume=resume)
    if command == "analyze":
        return analyze_stage33(ctx)
    if command != "all":
        raise ValueError(f"unsupported Stage3.3 command {command!r}")

    run_warmstart(ctx, backend=backend, resume=resume)
    run_refinement(ctx, backend=backend, resume=resume)
    library_confirmation = run_library_confirmation(ctx, backend=backend, resume=resume)
    if library_confirmation.get("target_library_confirmed") or bool(ctx.cfg["mpc"].get("allow_incomplete_library", False)):
        run_mpc_calibration(ctx, backend=backend, resume=resume)
        run_mpc_holdout(ctx, backend=backend, resume=resume)
        run_mpc_confirmation(ctx, backend=backend, resume=resume)
    state = read_json(ctx.paths.state)
    state["finished"] = True
    state["stop_reason"] = "pipeline_complete"
    atomic_write_json(ctx.paths.state, state)
    return analyze_stage33(ctx)


def synthetic_stage33_test() -> dict[str, Any]:
    # Pure numerical smoke test.  It intentionally does not claim to simulate
    # real TSC physics.
    source_bundle = {
        "center_feature_physical_units": np.zeros(125).tolist(),
        "jacobian_physical_units": np.eye(125, 75).tolist(),
        "output_scales": np.ones(125).tolist(),
        "output_weights": np.ones(125).tolist(),
        "control_radius": np.ones(75).tolist(),
        "jacobian_normalized": np.eye(125, 75).tolist(),
    }
    cfg = {
        "target": {"R": 0.75, "Z": 0.0, "Ip": 29779.724},
        "trajectory": {"coefficient_lower": [-2.6, -2.6, -0.9], "coefficient_upper": [2.6, 2.6, 0.9]},
        "gate": {
            "precise_tolerance_m": 0.03,
            "relaxed_tolerance_m": 0.04,
            "required_arrival_streak_steps": 3,
            "allowed_arrival_steps": [12, 13, 14, 15],
            "terminal_velocity_max_m_per_s": 0.1,
            "late_velocity_rms_max_m_per_s": 0.1,
            "late_window_steps": 4,
            "ip_safety_tolerance_A": 10000.0,
            "ip_tracking": {"terminal_abs_tolerance_A": 2000.0, "hold_rms_tolerance_A": 2400.0, "sustained_max_tolerance_A": 4000.0, "revision": IP_TRACKING_GATE_REVISION},
        },
        "mpc": {
            "output_scales": {"R_m": 0.03, "Z_m": 0.03, "vR_m_per_s": 0.1, "vZ_m_per_s": 0.1, "Ip_A": 1000.0},
            "output_weights": {"R": 1.0, "Z": 1.0, "vR": 0.5, "vZ": 0.5, "Ip": 0.2},
            "integral_measurement_gain": [0.2, 0.2, 0.0, 0.0, 0.1],
            "per_step_feedback_limit_by_mode": [0.1, 0.1, 0.035],
            "per_step_correction_rate_limit_by_mode": [0.06, 0.06, 0.02],
            "future_discount": 0.98,
            "hold_weight_start_state": 12,
            "hold_weight_multiplier": 2.0,
            "ridge_lambda": 0.1,
            "future_correction_smoothness": 0.05,
            "first_action_rate_weight": 0.1,
            "solver_tolerance": 1e-8,
            "solver_max_iterations": 100,
        },
    }
    from types import SimpleNamespace

    ctx = SimpleNamespace(cfg=cfg, source_bundle=source_bundle, env_cfg={"dt_ms": 10})
    correction = solve_receding_horizon_correction(
        ctx,
        current_step=8,
        nominal_coefficients=np.zeros((25, 3)),
        nominal_feature=np.zeros(125),
        measurement_normalized=np.asarray([0.1, -0.1, 0.0, 0.0, 0.0]),
        integral_normalized=np.zeros(5),
        previous_correction=np.zeros(3),
        controller_scale=1.0,
    )
    first = np.asarray(correction["first_correction"], dtype=float)
    if first.shape != (3,) or not np.all(np.isfinite(first)):
        raise RuntimeError("synthetic receding-horizon solve produced invalid first action")
    return {
        "stage": "Stage3.3",
        "synthetic_test": "passed",
        "first_correction": first.tolist(),
        "warning": "Numerical smoke test only; no real TSC control claim.",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage3.3 target-conditioned nominal library and receding-horizon MPC")
    parser.add_argument("--config", required=True)
    parser.add_argument("--source-stage3-2-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument(
        "--command",
        choices=("prepare", "warmstart", "refine-round", "refine", "library-confirm", "calibrate", "holdout", "confirm", "analyze", "all", "self-test"),
        default="all",
    )
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "self-test":
        print(json.dumps(synthetic_stage33_test(), indent=2), flush=True)
        return
    result = execute(
        config_path=args.config,
        source_stage32_run=args.source_stage3_2_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        no_resume=bool(args.no_resume),
    )
    print(json.dumps(_json_safe(result), indent=2), flush=True)


if __name__ == "__main__":
    main()
