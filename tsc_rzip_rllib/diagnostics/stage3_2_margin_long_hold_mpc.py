"""Stage3.2 signed-margin, 250 ms long-hold, and causal-MPC validation.

Stage3.2 starts from a completed Stage3.1 run that already contains real-TSC
30 mm strict candidates.  It deliberately does not move the finish line:

* arrival must still be completed by 150 ms;
* R and Z must remain inside the 30 mm rectangular tube;
* velocity and Ip limits remain 0.10 m/s and 10 kA;
* the new requirement is to sustain the gate through 250 ms.

The workflow is split into evidence-preserving phases:

1. optimize *signed safety margin* at 150 ms instead of stopping at the first
   zero-clipped strict pass;
2. screen deterministic 250 ms tail templates;
3. optimize ten independent tail controls (steps 15--24) with real-TSC finite
   differences and trust-region SQP;
4. identify a full 125x75 local real-TSC model around the best 250 ms nominal;
5. build dimensionless truncated-SVD/ridge causal gains from steps 0--24;
6. validate one globally fixed feedback scale on target-shift and injected-mode
   scenarios using signed margins, preservation, and recovery rather than a
   zero-clipped violation score;
7. confirm open-loop long hold and representative feedback scenarios.

Passing Stage3.2 is still not the final project objective.  It does not validate
initial-state, plant-parameter, measurement-noise, delay, or long-discharge
robustness, and it does not turn residual RL into the primary controller.
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
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as jsonio
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_0_tail_sqp as s30
from tsc_rzip_rllib.diagnostics import stage3_1_adaptive_sqp_mpc as s31
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STATE_FILENAME = "stage3_2_state.json"
MANIFEST_FILENAME = "stage3_2_manifest.json"
SOURCE_CATALOG_FILENAME = "source_stage3_1_catalog.json"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_json(path: Path | str) -> Any:
    return jsonio.read_json(Path(path))


def read_json_gz(path: Path | str) -> Any:
    return jsonio.read_json_gz(Path(path))


def _json_safe(value: Any, path: str = "$") -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite JSON number at {path}: {value!r}")
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, f"{path}[{index}]") for index, item in enumerate(value)]
    return value


def atomic_write_json(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json(Path(path), _json_safe(payload))


def atomic_write_json_gz(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json_gz(Path(path), _json_safe(payload))


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, np.ndarray)):
        return json.dumps(_json_safe(value), ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, Path):
        return str(value)
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
        jsonio.atomic_write_text(path, "")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
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


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def _finite(value: Any, fallback: float) -> float:
    out = _as_float(value, None)
    return fallback if out is None else float(out)


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
        out = np.asarray(value, dtype=float)
    elif isinstance(value, (list, tuple)):
        out = np.asarray(value, dtype=float)
    else:
        out = np.asarray(json.loads(str(value)), dtype=float)
    out = out.reshape(-1)
    if out.shape != (expected,) or not np.all(np.isfinite(out)):
        raise ValueError(f"invalid {expected}-vector: shape={out.shape}")
    return out


def vector_digest(vector: np.ndarray, prefix: str = "s32") -> str:
    rounded = np.round(np.asarray(vector, dtype=float).reshape(-1), 10)
    return f"{prefix}_{hashlib.sha256(rounded.tobytes()).hexdigest()[:16]}"


def full_vector_key(row: dict[str, Any]) -> str:
    return vector_digest(_vector(row["full_control_vector"], 75), "v75")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Stage32Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_catalog: Path
    margin_phases: Path
    margin_evaluations: Path
    extension: Path
    hold_phases: Path
    hold_evaluations: Path
    controller: Path
    feedback: Path
    confirmations: Path
    analysis: Path
    best: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage32Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_catalog=run_dir / SOURCE_CATALOG_FILENAME,
            margin_phases=run_dir / "stage3_2_margin_phases",
            margin_evaluations=run_dir / "stage3_2_margin_evaluations",
            extension=run_dir / "stage3_2_extension_screen",
            hold_phases=run_dir / "stage3_2_hold_phases",
            hold_evaluations=run_dir / "stage3_2_hold_evaluations",
            controller=run_dir / "stage3_2_controller",
            feedback=run_dir / "stage3_2_feedback_validation",
            confirmations=run_dir / "stage3_2_confirmations",
            analysis=run_dir / "stage3_2_analysis",
            best=run_dir / "stage3_2_best",
            source_reference=run_dir / "source_stage3_1_reference",
        )


@dataclass
class Stage32Context:
    cfg: dict[str, Any]
    train_cfg: dict[str, Any]
    env_cfg: dict[str, Any]
    paths: Stage32Paths
    source_stage31_run: Path
    source_stage30_run: Path
    source_stage22_run: Path
    base31: s31.Stage31Context
    modes_tsc: np.ndarray
    initial_currents_tsc: np.ndarray
    max_delta_a: float
    min_current_tsc: np.ndarray
    max_current_tsc: np.ndarray
    margin_steps: tuple[int, ...]
    hold_steps: tuple[int, ...]
    full_steps: tuple[int, ...]
    coefficient_lower_mode: np.ndarray
    coefficient_upper_mode: np.ndarray
    source_rows: list[dict[str, Any]]
    source_fingerprint: dict[str, Any] | None = None


_REQUIRED_STAGE31 = (
    "stage3_1_config.resolved.json",
    "stage3_1_manifest.json",
    "stage3_1_state.json",
    "stage3_1_analysis/all_results.json",
    "stage3_1_analysis/stage3_1_analysis_summary.json",
    "stage3_1_confirmations/stage3_1_verdict.json",
    "stage3_1_controller/mpc_poc_bundle.json",
    "stage3_1_best/best_candidate.json",
    "stage3_1_best/best_tsc_result.json.gz",
    "env_config.resolved.json",
    "train_config.resolved.json",
)


def resolve_source_stage31_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE3_1_RUN", "").strip()
    if not value:
        raise ValueError("Pass --source-stage3-1-run or set SOURCE_STAGE3_1_RUN")
    run = Path(value).expanduser().resolve()
    missing = [str(run / relative) for relative in _REQUIRED_STAGE31 if not (run / relative).exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage3.1 source: " + ", ".join(missing))
    return run


def _find_under_project(project_dir: Path, dirname: str, basename: str) -> Path | None:
    candidate = project_dir / dirname / basename
    return candidate.resolve() if candidate.exists() else None


def resolve_stage30_from_stage31(source31: Path, project_dir: Path) -> Path:
    manifest = read_json(source31 / "stage3_1_manifest.json")
    raw = str(manifest.get("source_stage3_0_run", "")).strip()
    if raw:
        path = Path(raw).expanduser()
        if path.exists():
            return path.resolve()
        fallback = _find_under_project(project_dir, "stage3_0_runs", path.name)
        if fallback is not None:
            return fallback
    env = os.environ.get("SOURCE_STAGE3_0_RUN", "").strip()
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()
    raise FileNotFoundError("Cannot resolve Stage3.0 source referenced by Stage3.1")


def resolve_stage22_from_stage31(source31: Path, source30: Path, project_dir: Path) -> Path:
    manifest31 = read_json(source31 / "stage3_1_manifest.json")
    raw = str(manifest31.get("source_stage2_2_run", "")).strip()
    if raw:
        path = Path(raw).expanduser()
        if path.exists():
            return path.resolve()
        fallback = _find_under_project(project_dir, "stage2_2_runs", path.name)
        if fallback is not None:
            return fallback
    return s31.resolve_source_stage22_from_stage30(source30, project_dir)


def validate_stage32_config(cfg: dict[str, Any]) -> None:
    trajectory = cfg["trajectory"]
    if int(trajectory.get("source_horizon_steps", -1)) != 15:
        raise ValueError("Stage3.2 source horizon must remain 15 steps")
    if int(trajectory.get("horizon_steps", -1)) != 25 or int(trajectory.get("horizon_ms", -1)) != 250:
        raise ValueError("Stage3.2 is fixed to 25 steps / 250 ms")
    if int(trajectory.get("n_modes", -1)) != 3:
        raise ValueError("Stage3.2 requires exactly three validated SVD modes")
    if list(trajectory.get("margin_variable_steps", [])) != list(range(8, 15)):
        raise ValueError("margin_variable_steps must be [8..14]")
    if list(trajectory.get("hold_variable_steps", [])) != list(range(15, 25)):
        raise ValueError("hold_variable_steps must be [15..24]")
    if list(trajectory.get("full_feedback_steps", [])) != list(range(25)):
        raise ValueError("full_feedback_steps must be [0..24]")
    lower = np.asarray(trajectory.get("coefficient_lower", []), dtype=float)
    upper = np.asarray(trajectory.get("coefficient_upper", []), dtype=float)
    if lower.shape != (3,) or upper.shape != (3,) or not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)) or np.any(lower >= upper):
        raise ValueError("coefficient bounds must be finite three-vectors with lower < upper")

    gate = cfg["gate"]
    if list(gate.get("allowed_arrival_steps", [])) != [12, 13, 14, 15]:
        raise ValueError("arrival steps must remain [12,13,14,15]")
    if int(gate.get("arrival_deadline_step", -1)) != 15 or int(gate.get("hold_through_step", -1)) != 25:
        raise ValueError("arrival deadline/hold endpoint must be 15/25")
    if int(gate.get("required_arrival_streak_steps", 0)) != 3:
        raise ValueError("three-sample arrival streak is required")
    fixed = {
        "precise_tolerance_m": 0.03,
        "relaxed_tolerance_m": 0.04,
        "terminal_velocity_max_m_per_s": 0.10,
        "late_velocity_rms_max_m_per_s": 0.10,
        "ip_tolerance_a": 10000.0,
    }
    for key, expected in fixed.items():
        if not math.isclose(float(gate.get(key, math.nan)), expected, rel_tol=0.0, abs_tol=1e-12 if expected < 1000 else 1e-9):
            raise ValueError(f"Stage3.2 hard gate {key} must remain {expected}")

    goal = cfg["margin_goal"]
    internal_tolerance = float(goal.get("internal_tolerance_m", math.nan))
    internal_velocity = float(goal.get("internal_velocity_m_per_s", math.nan))
    if not (0.0 < internal_tolerance < float(gate["precise_tolerance_m"])):
        raise ValueError("internal_tolerance_m must be inside the hard tube")
    if not (0.0 < internal_velocity < float(gate["terminal_velocity_max_m_per_s"])):
        raise ValueError("internal_velocity_m_per_s must be below the hard speed limit")

    for section, expected_shape, expected_variables in (
        ("margin_sqp", (7, 3), 21),
        ("hold_sqp", (10, 3), 30),
    ):
        sqp = cfg[section]
        if int(sqp.get("centers_per_round", 0)) != 2 or int(sqp.get("variables", 0)) != expected_variables:
            raise ValueError(f"{section} requires two centers and {expected_variables} variables")
        for key in ("probe_delta_by_step_mode", "trust_radius_by_step_mode"):
            matrix = np.asarray(sqp.get(key, []), dtype=float)
            if matrix.shape != expected_shape or np.any(matrix <= 0.0) or not np.all(np.isfinite(matrix)):
                raise ValueError(f"{section}.{key} must be a positive finite {expected_shape[0]}x3 matrix")
        requests = list(sqp.get("proposal_requests", []))
        if len(requests) != 12:
            raise ValueError(f"{section} must define exactly 12 proposals per center")
        if set(sqp.get("profiles", {})) != {"balanced", "position", "damping"}:
            raise ValueError(f"{section} profiles must be balanced/position/damping")
        if sorted({float(value) for value in sqp.get("proposal_step_scales", [])}) != [0.5, 1.0, 1.5, 2.0]:
            raise ValueError(f"{section} proposal step scales must be [0.5,1.0,1.5,2.0]")

    identification = cfg["full_controller_identification"]
    if int(identification.get("variables", 0)) != 75:
        raise ValueError("full controller identification requires 75 variables")
    groups = list(identification.get("probe_delta_by_step_groups", []))
    covered: list[int] = []
    for group in groups:
        start, end = int(group["start_step"]), int(group["end_step"])
        delta = np.asarray(group["delta_by_mode"], dtype=float)
        if start < 0 or end < start or end > 24 or delta.shape != (3,) or np.any(delta <= 0.0):
            raise ValueError("invalid full-identification delta group")
        covered.extend(range(start, end + 1))
    if sorted(covered) != list(range(25)) or len(covered) != 25:
        raise ValueError("full-identification groups must cover each step 0..24 exactly once")
    if not 1 <= int(identification.get("minimum_reliable_columns", 0)) <= 75:
        raise ValueError("minimum_reliable_columns must lie in [1,75]")
    if not 0 <= int(identification.get("maximum_recenter_passes", -1)) <= 1:
        raise ValueError("full identification supports zero or one recenter pass")

    mpc = cfg["mpc"]
    scales = mpc.get("output_scales", {})
    if set(scales) != {"R_m", "Z_m", "vR_m_per_s", "vZ_m_per_s", "Ip_A"} or any(float(value) <= 0.0 for value in scales.values()):
        raise ValueError("mpc.output_scales must contain five positive values")
    if sorted(float(value) for value in mpc.get("controller_scales", [])) != [0.0, 0.5, 1.0]:
        raise ValueError("mpc.controller_scales must be [0.0,0.5,1.0]")
    limit = np.asarray(mpc.get("per_step_feedback_limit_by_mode", []), dtype=float)
    if limit.shape != (3,) or np.any(limit <= 0.0) or not np.all(np.isfinite(limit)):
        raise ValueError("per-step feedback limits must be a positive finite three-vector")


def _resolve_storage(value: Any, project_dir: Path) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return str(path.resolve(strict=False))


def _source_inventory(source31: Path, source30: Path, source22: Path, raw_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    # Hash logical paths plus content so a repository move does not invalidate an
    # otherwise identical source tree.  Absolute paths are retained only as
    # diagnostic metadata and are excluded from the digest.
    logical_to_path: dict[str, Path] = {}
    for relative in _REQUIRED_STAGE31:
        path = source31 / relative
        if path.exists():
            logical_to_path[f"stage3_1/{relative}"] = path.resolve()
    for row in raw_rows:
        relative = str(row.get("result_relpath", "")).strip()
        if relative:
            path = source31 / relative
            if path.exists():
                logical_to_path[f"stage3_1/{relative}"] = path.resolve()
    for prefix, root, relatives in (
        ("stage3_0", source30, ("stage3_0_manifest.json", "stage3_0_state.json", "stage3_0_config.resolved.json")),
        ("stage2_2", source22, ("stage2_2_manifest.json", "stage2_2_state.json", "stage2_2_config.resolved.json")),
    ):
        for relative in relatives:
            path = root / relative
            if path.exists():
                logical_to_path[f"{prefix}/{relative}"] = path.resolve()
    entries = []
    digest = hashlib.sha256()
    total_bytes = 0
    for logical_path, path in sorted(logical_to_path.items()):
        sha = _sha256_file(path)
        size = path.stat().st_size
        total_bytes += size
        entry = {
            "logical_path": logical_path,
            "source_path": str(path),
            "sha256": sha,
            "size_bytes": size,
        }
        entries.append(entry)
        digest.update(logical_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\n")
    return {
        "schema_version": 2,
        "stage": "Stage3.2 source inventory",
        "source_stage3_1_run": str(source31),
        "source_stage3_0_run": str(source30),
        "source_stage2_2_run": str(source22),
        "source_rows": len(raw_rows),
        "fingerprinted_files": len(entries),
        "total_bytes": total_bytes,
        "digest": digest.hexdigest(),
        "digest_uses_logical_paths": True,
        "entries": entries,
    }


def _source_row_to_stage32(base31: s31.Stage31Context, source31: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    if not _as_bool(row.get("success"), False) or not _as_bool(row.get("strict_gate_pass"), False):
        return None
    if str(row.get("stage", "")).startswith("Stage3.0"):
        return None
    try:
        nominal = s31.nominal_by_id(base31, str(row["nominal_id"]))
        control = _vector(row["control_vector"], 21)
        decoded = s31.decode_control_sequence(base31, nominal, control)
    except Exception:
        return None
    relative = str(row.get("result_relpath", "")).strip()
    if not relative:
        return None
    result_path = (source31 / relative).resolve()
    if not result_path.exists():
        return None
    coefficients = np.zeros((25, 3), dtype=float)
    coefficients[:15] = np.asarray(decoded["mode_coefficients"], dtype=float)
    coefficients[15:] = coefficients[14]
    out = copy.deepcopy(row)
    out.update(
        {
            "stage": "Stage3.1-source",
            "source_stage3_1_candidate_id": str(row.get("candidate_id", "")),
            "source_result_path": str(result_path),
            "result_relpath": None,
            "full_control_vector": coefficients.reshape(-1).tolist(),
            "margin_control_vector": coefficients[8:15].reshape(-1).tolist(),
            "hold_control_vector": coefficients[15:25].reshape(-1).tolist(),
        }
    )
    return out


def load_stage32_config(
    config_path: str | Path,
    *,
    source_stage31_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage32Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = jsonio.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)},
    )
    validate_stage32_config(cfg)
    if run_dir_override is None:
        root = jsonio.resolve_path(cfg.get("output_root", "stage3_2_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name','stage3_2_margin_long_hold')}_{utc_timestamp()}"
    else:
        run_dir = jsonio.resolve_path(run_dir_override, base_dir=project_dir)

    source31 = resolve_source_stage31_run(source_stage31_run)
    source30 = resolve_stage30_from_stage31(source31, project_dir)
    source22 = resolve_stage22_from_stage31(source31, source30, project_dir)
    source31_cfg = read_json(source31 / "stage3_1_config.resolved.json")
    source31_state = read_json(source31 / "stage3_1_state.json")
    source31_verdict = read_json(source31 / "stage3_1_confirmations/stage3_1_verdict.json")
    for key in ("R", "Z", "Ip"):
        if not math.isclose(float(cfg["target"][key]), float(source31_cfg["target"][key]), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Stage3.2 target {key} differs from Stage3.1")
    for key in (
        "precise_tolerance_m",
        "relaxed_tolerance_m",
        "required_arrival_streak_steps",
        "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s",
        "ip_tolerance_a",
    ):
        if not math.isclose(float(cfg["gate"][key]), float(source31_cfg["gate"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage3.2 hard gate {key} differs from Stage3.1")
    if bool(cfg["source"].get("require_strict_confirmation", True)):
        if str(source31_verdict.get("verdict", "")) != "PASS_PRECISE_HOLD_30MM_120_150MS_CONFIRMED":
            raise RuntimeError("Stage3.1 source does not contain the required confirmed strict verdict")
    if bool(cfg["source"].get("require_controller_identification", True)) and not source31_state.get("controller_identification_complete"):
        raise RuntimeError("Stage3.1 controller identification is incomplete")

    base31 = s31.load_stage31_config(
        source31 / "stage3_1_config.resolved.json",
        source_stage30_run=source30,
        run_dir_override=run_dir,
    )
    env_cfg = copy.deepcopy(base31.env_cfg)
    train_cfg = copy.deepcopy(base31.train_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg.get("runtime", {}).get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    storage = cfg.get("storage", {})
    workspace = _resolve_storage(os.environ.get("STAGE3_2_TSC_WORKSPACE_ROOT") or storage.get("tsc_workspace_root"), project_dir)
    run_root = _resolve_storage(os.environ.get("STAGE3_2_TSC_RUN_ROOT") or storage.get("tsc_run_root"), project_dir)
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

    raw_rows = read_json(source31 / "stage3_1_analysis/all_results.json")
    if not isinstance(raw_rows, list):
        raise TypeError("Stage3.1 all_results.json must contain a list")
    fingerprint = _source_inventory(source31, source30, source22, raw_rows)
    source_rows = [converted for row in raw_rows if (converted := _source_row_to_stage32(base31, source31, row)) is not None]
    minimum_rows = int(cfg["source"].get("minimum_successful_stage3_1_rows", 400))
    successful_stage31 = sum(
        _as_bool(row.get("success"), False)
        for row in raw_rows
        if str(row.get("stage", "")) == "Stage3.1"
    )
    if successful_stage31 < minimum_rows:
        raise RuntimeError(f"Only {successful_stage31} successful Stage3.1 rows; expected at least {minimum_rows}")
    minimum_strict = int(cfg["source"].get("minimum_strict_stage3_1_rows", 8))
    if len(source_rows) < minimum_strict:
        raise RuntimeError(f"Only {len(source_rows)} usable strict Stage3.1 candidates; expected at least {minimum_strict}")

    margin_steps = tuple(int(value) for value in cfg["trajectory"]["margin_variable_steps"])
    hold_steps = tuple(int(value) for value in cfg["trajectory"]["hold_variable_steps"])
    full_steps = tuple(int(value) for value in cfg["trajectory"]["full_feedback_steps"])
    return Stage32Context(
        cfg=cfg,
        train_cfg=train_cfg,
        env_cfg=env_cfg,
        paths=Stage32Paths.from_run_dir(run_dir),
        source_stage31_run=source31,
        source_stage30_run=source30,
        source_stage22_run=source22,
        base31=base31,
        modes_tsc=np.asarray(base31.modes_tsc, dtype=float),
        initial_currents_tsc=np.asarray(base31.initial_currents_tsc, dtype=float),
        max_delta_a=float(base31.max_delta_a),
        min_current_tsc=np.asarray(base31.min_current_tsc, dtype=float),
        max_current_tsc=np.asarray(base31.max_current_tsc, dtype=float),
        margin_steps=margin_steps,
        hold_steps=hold_steps,
        full_steps=full_steps,
        coefficient_lower_mode=np.asarray(cfg["trajectory"]["coefficient_lower"], dtype=float),
        coefficient_upper_mode=np.asarray(cfg["trajectory"]["coefficient_upper"], dtype=float),
        source_rows=source_rows,
        source_fingerprint=fingerprint,
    )


def initialize_stage32_run(ctx: Stage32Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.margin_phases,
        ctx.paths.margin_evaluations,
        ctx.paths.extension,
        ctx.paths.hold_phases,
        ctx.paths.hold_evaluations,
        ctx.paths.controller,
        ctx.paths.feedback,
        ctx.paths.confirmations,
        ctx.paths.analysis,
        ctx.paths.best,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.run_dir / "stage3_2_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.env_cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "created_utc": utc_timestamp(),
        "source_stage3_1_run": str(ctx.source_stage31_run),
        "source_stage3_0_run": str(ctx.source_stage30_run),
        "source_stage2_2_run": str(ctx.source_stage22_run),
        "source_strict_candidates": len(ctx.source_rows),
        "source_fingerprint": None if ctx.source_fingerprint is None else {
            key: value for key, value in ctx.source_fingerprint.items() if key != "entries"
        },
        "target": copy.deepcopy(ctx.cfg["target"]),
        "horizon_steps": 25,
        "horizon_ms": 250,
        "arrival_deadline_ms": 150,
        "hard_gate_changed_from_stage3_1": False,
        "parameter_dimensions": {"margin": 21, "long_hold_tail": 30, "full_feedback": 75},
        "final_task": "robust causal feedback across initial states, targets, plant uncertainty, noise, and delay",
        "tested_scope": "fixed initial state; target shifts and injected mode disturbances only",
        "robustness_validated": False,
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if Path(old["source_stage3_1_run"]).resolve() != ctx.source_stage31_run:
            raise ValueError("Existing Stage3.2 run points to a different Stage3.1 source")
        old_digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        new_digest = "" if ctx.source_fingerprint is None else str(ctx.source_fingerprint.get("digest", ""))
        if old_digest and new_digest and old_digest != new_digest:
            raise ValueError("Stage3.1 source content changed since this Stage3.2 run was prepared")
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.source_catalog.exists():
        atomic_write_json(ctx.paths.source_catalog, ctx.source_rows)
    if ctx.source_fingerprint is not None:
        inventory_path = ctx.paths.source_reference / "source_content_inventory.json"
        if inventory_path.exists():
            previous = read_json(inventory_path)
            if str(previous.get("digest", "")) != str(ctx.source_fingerprint.get("digest", "")):
                raise ValueError("Stored source inventory differs from current Stage3.1 content")
        else:
            atomic_write_json(inventory_path, ctx.source_fingerprint)
    for relative in (
        "stage3_1_config.resolved.json",
        "stage3_1_manifest.json",
        "stage3_1_state.json",
        "stage3_1_analysis/stage3_1_analysis_summary.json",
        "stage3_1_analysis/strict_hall_of_fame.json",
        "stage3_1_controller/mpc_poc_bundle.json",
        "stage3_1_feedback_poc/feedback_poc_summary.json",
        "stage3_1_confirmations/stage3_1_verdict.json",
        "stage3_1_best/best_candidate.json",
        "STAGE3_1_REPORT.md",
    ):
        src = ctx.source_stage31_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# Full-sequence decoding and 150/250 ms metrics
# ---------------------------------------------------------------------------


def clip_full_control(ctx: Stage32Context, vector: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(vector, dtype=float).reshape(25, 3)
    coefficients = np.clip(
        coefficients,
        ctx.coefficient_lower_mode[None, :],
        ctx.coefficient_upper_mode[None, :],
    )
    return coefficients.reshape(-1)


def decode_full_sequence(ctx: Stage32Context, full_control_vector: np.ndarray) -> dict[str, Any]:
    control = clip_full_control(ctx, full_control_vector)
    coefficients = control.reshape(25, 3)
    raw = coefficients @ ctx.modes_tsc.T
    action = np.zeros_like(raw)
    currents = np.zeros((26, 14), dtype=float)
    currents[0] = ctx.initial_currents_tsc
    scales: list[float] = []
    excess: list[float] = []
    for step in range(25):
        desired = np.asarray(raw[step], dtype=float)
        max_abs = float(np.max(np.abs(desired)))
        action_scale = 1.0 if max_abs <= 1.0 else 1.0 / max_abs
        desired = desired * action_scale
        delta = desired * ctx.max_delta_a
        current_scale = 1.0
        for coil in range(14):
            if delta[coil] > 0.0:
                room = ctx.max_current_tsc[coil] - currents[step, coil]
                current_scale = min(current_scale, max(0.0, room / max(delta[coil], 1e-30)))
            elif delta[coil] < 0.0:
                room = ctx.min_current_tsc[coil] - currents[step, coil]
                current_scale = min(current_scale, max(0.0, room / min(delta[coil], -1e-30)))
        current_scale = float(np.clip(current_scale, 0.0, 1.0))
        actual = desired * current_scale
        action[step] = actual
        currents[step + 1] = currents[step] + actual * ctx.max_delta_a
        scales.append(action_scale * current_scale)
        excess.append(max(0.0, max_abs - 1.0))
    return {
        "full_control_vector": control,
        "mode_coefficients": coefficients,
        "action_raw_tsc": raw,
        "action_norm_tsc": action,
        "action_norm_display": s30.tsc_matrix_to_display(action),
        "currents_a_tsc": currents,
        "currents_a_display": s30.tsc_matrix_to_display(currents),
        "per_step_repair_scale": np.asarray(scales, dtype=float),
        "saturation_excess": np.asarray(excess, dtype=float),
    }


def _mode_action_from_current(ctx: Stage32Context, coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
    desired = np.asarray(coefficients, dtype=float) @ ctx.modes_tsc.T
    max_abs = float(np.max(np.abs(desired)))
    if max_abs > 1.0:
        desired = desired / max_abs
    delta = desired * ctx.max_delta_a
    current_scale = 1.0
    for coil in range(14):
        if delta[coil] > 0.0:
            room = ctx.max_current_tsc[coil] - currents[coil]
            current_scale = min(current_scale, max(0.0, room / max(delta[coil], 1e-30)))
        elif delta[coil] < 0.0:
            room = ctx.min_current_tsc[coil] - currents[coil]
            current_scale = min(current_scale, max(0.0, room / min(delta[coil], -1e-30)))
    return np.asarray(desired * float(np.clip(current_scale, 0.0, 1.0)), dtype=np.float32)


def _velocity_components(y: np.ndarray, dt_s: float) -> np.ndarray:
    velocity = np.zeros((len(y), 2), dtype=float)
    if len(y) > 1:
        velocity[1:] = np.diff(y[:, :2], axis=0) / dt_s
    return velocity


def _trailing_streak(mask: np.ndarray) -> int:
    count = 0
    for value in np.asarray(mask, dtype=bool)[::-1]:
        if not bool(value):
            break
        count += 1
    return int(count)


def _endpoint_constraints_signed(
    *,
    error: np.ndarray,
    speed: np.ndarray,
    endpoint: int,
    horizon: int,
    tolerance: float,
    endpoint_speed_limit: float,
    rms_speed_limit: float,
    late_window_steps: int,
    ip_tolerance: float,
    streak_steps: int,
    dt_ms: int,
) -> dict[str, Any]:
    window_start = endpoint - streak_steps + 1
    if window_start < 0 or endpoint > horizon:
        raise ValueError("invalid endpoint/streak/horizon combination")
    sustained_box = float(np.max(np.abs(error[window_start : horizon + 1, :2])))
    endpoint_speed = float(speed[endpoint])
    late_start = max(1, endpoint - late_window_steps + 1)
    endpoint_late_rms = float(np.sqrt(np.mean(speed[late_start : endpoint + 1] ** 2)))
    post_speed_rms = float(np.sqrt(np.mean(speed[endpoint : horizon + 1] ** 2)))
    final_speed = float(speed[horizon])
    sustained_ip = float(np.max(np.abs(error[window_start : horizon + 1, 2])))
    signed = {
        "position": 1.0 - sustained_box / tolerance,
        "endpoint_speed": 1.0 - endpoint_speed / endpoint_speed_limit,
        "endpoint_late_speed": 1.0 - endpoint_late_rms / rms_speed_limit,
        "post_speed": 1.0 - post_speed_rms / rms_speed_limit,
        "final_speed": 1.0 - final_speed / endpoint_speed_limit,
        "ip": 1.0 - sustained_ip / ip_tolerance,
    }
    signed_values = np.asarray(list(signed.values()), dtype=float)
    violations = np.maximum(-signed_values, 0.0)
    return {
        "endpoint_step": int(endpoint),
        "arrival_time_ms": int(endpoint * dt_ms),
        "window_start_step": int(window_start),
        "sustained_box_max_error_m": sustained_box,
        "endpoint_velocity_m_per_s": endpoint_speed,
        "endpoint_late_velocity_rms_m_per_s": endpoint_late_rms,
        "post_arrival_velocity_rms_m_per_s": post_speed_rms,
        "final_velocity_m_per_s": final_speed,
        "sustained_Ip_max_error_A": sustained_ip,
        "position_signed_margin": float(signed["position"]),
        "endpoint_speed_signed_margin": float(signed["endpoint_speed"]),
        "endpoint_late_speed_signed_margin": float(signed["endpoint_late_speed"]),
        "post_speed_signed_margin": float(signed["post_speed"]),
        "final_speed_signed_margin": float(signed["final_speed"]),
        "ip_signed_margin": float(signed["ip"]),
        "minimum_signed_margin": float(np.min(signed_values)),
        "mean_signed_margin": float(np.mean(signed_values)),
        "position_violation": float(violations[0]),
        "endpoint_speed_violation": float(violations[1]),
        "endpoint_late_speed_violation": float(violations[2]),
        "post_speed_violation": float(violations[3]),
        "final_speed_violation": float(violations[4]),
        "ip_violation": float(violations[5]),
        "max_violation": float(np.max(violations)),
        "sum_violation": float(np.sum(violations)),
        "l2_violation": float(np.sqrt(np.sum(violations**2))),
        "pass": bool(np.min(signed_values) >= -1e-12),
    }


def _failed_metrics(reason: str, *, horizon: int) -> dict[str, Any]:
    return {
        "success": False,
        "failure_reason": reason,
        "n_trajectory_steps": 0,
        "strict_gate_pass": False,
        "relaxed_gate_pass": False,
        "gate_label": "TSC_FAILURE",
        "stage3_2_horizon_steps": horizon,
        "stage3_2_minimum_signed_margin": -1e12,
        "stage3_2_internal_minimum_signed_margin": -1e12,
        "stage3_2_max_violation": 1e12,
        "stage3_2_sum_violation": 1e12,
        "stage3_2_margin_objective": 1e12,
        "continuous_objective": 1e12,
        "selection_score": 99e6 + 1e12,
    }


def stage32_metrics(
    ctx: Stage32Context,
    result: dict[str, Any],
    decoded: dict[str, Any] | None,
    *,
    horizon: int,
) -> dict[str, Any]:
    if not result.get("success"):
        return _failed_metrics(str(result.get("failure_reason", "TSC failure")), horizon=horizon)
    trajectory = result.get("trajectory", [])
    if len(trajectory) != horizon + 1:
        return _failed_metrics(f"expected {horizon + 1} trajectory states, got {len(trajectory)}", horizon=horizon)
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("successful Stage3.2 trajectory contains non-finite R/Z/Ip")
    target = np.asarray([ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]], dtype=float)
    error = y - target[None, :]
    velocity_xy = _velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    speed = np.linalg.norm(velocity_xy, axis=1)
    gate = ctx.cfg["gate"]
    endpoints = [endpoint for endpoint in map(int, gate["allowed_arrival_steps"]) if endpoint <= horizon]
    precise_evaluations = [
        _endpoint_constraints_signed(
            error=error,
            speed=speed,
            endpoint=endpoint,
            horizon=horizon,
            tolerance=float(gate["precise_tolerance_m"]),
            endpoint_speed_limit=float(gate["terminal_velocity_max_m_per_s"]),
            rms_speed_limit=float(gate["late_velocity_rms_max_m_per_s"]),
            late_window_steps=int(gate["late_window_steps"]),
            ip_tolerance=float(gate["ip_tolerance_a"]),
            streak_steps=int(gate["required_arrival_streak_steps"]),
            dt_ms=int(ctx.env_cfg["dt_ms"]),
        )
        for endpoint in endpoints
    ]
    relaxed_evaluations = [
        _endpoint_constraints_signed(
            error=error,
            speed=speed,
            endpoint=endpoint,
            horizon=horizon,
            tolerance=float(gate["relaxed_tolerance_m"]),
            endpoint_speed_limit=float(gate["terminal_velocity_max_m_per_s"]),
            rms_speed_limit=float(gate["late_velocity_rms_max_m_per_s"]),
            late_window_steps=int(gate["late_window_steps"]),
            ip_tolerance=float(gate["ip_tolerance_a"]),
            streak_steps=int(gate["required_arrival_streak_steps"]),
            dt_ms=int(ctx.env_cfg["dt_ms"]),
        )
        for endpoint in endpoints
    ]
    strict_passes = [row for row in precise_evaluations if row["pass"]]
    relaxed_passes = [row for row in relaxed_evaluations if row["pass"]]
    strict_pass = bool(strict_passes)
    relaxed_pass = bool(relaxed_passes)
    if strict_pass:
        chosen = max(strict_passes, key=lambda row: (row["minimum_signed_margin"], -row["endpoint_step"]))
        gate_endpoint = min(strict_passes, key=lambda row: row["endpoint_step"])
        label = "PASS_PRECISE_HOLD_30MM_120_250MS" if horizon == 25 else "PASS_PRECISE_MARGIN_30MM_120_150MS"
    else:
        chosen = max(
            precise_evaluations,
            key=lambda row: (row["minimum_signed_margin"], row["mean_signed_margin"], -row["endpoint_step"]),
        )
        gate_endpoint = min(relaxed_passes, key=lambda row: row["endpoint_step"]) if relaxed_pass else None
        label = (
            "PASS_DAMPED_HOLD_40MM_120_250MS"
            if relaxed_pass and horizon == 25
            else ("PASS_DAMPED_MARGIN_40MM_120_150MS" if relaxed_pass else "NEAR_FEASIBLE_STAGE3_2")
        )

    internal_tolerance = float(ctx.cfg["margin_goal"]["internal_tolerance_m"])
    internal_velocity = float(ctx.cfg["margin_goal"]["internal_velocity_m_per_s"])
    internal_evaluations = [
        _endpoint_constraints_signed(
            error=error,
            speed=speed,
            endpoint=endpoint,
            horizon=horizon,
            tolerance=internal_tolerance,
            endpoint_speed_limit=internal_velocity,
            rms_speed_limit=internal_velocity,
            late_window_steps=int(gate["late_window_steps"]),
            ip_tolerance=float(gate["ip_tolerance_a"]),
            streak_steps=int(gate["required_arrival_streak_steps"]),
            dt_ms=int(ctx.env_cfg["dt_ms"]),
        )
        for endpoint in endpoints
    ]
    internal_chosen = max(
        internal_evaluations,
        key=lambda row: (row["minimum_signed_margin"], row["mean_signed_margin"], -row["endpoint_step"]),
    )
    internal_goal_pass = bool(internal_chosen["pass"])

    currents = np.asarray([row["currents_a_display"] for row in trajectory], dtype=float)
    min_i = np.asarray(ctx.env_cfg["min_current_a_display_order"], dtype=float)
    max_i = np.asarray(ctx.env_cfg["max_current_a_display_order"], dtype=float)
    center_i = 0.5 * (min_i + max_i)
    half_i = np.maximum(0.5 * (max_i - min_i), 1e-9)
    current_util = float(np.max(np.abs((currents - center_i[None, :]) / half_i[None, :])))
    action_rms = delta_action_rms = repair_rms = 0.0
    if decoded is not None:
        action = np.asarray(decoded["action_norm_tsc"], dtype=float)[:horizon]
        action_rms = float(np.sqrt(np.mean(action**2)))
        delta_action_rms = float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2))) if len(action) > 1 else 0.0
        repair_rms = float(np.sqrt(np.mean(np.asarray(decoded["saturation_excess"], dtype=float)[:horizon] ** 2)))

    window_start = int(chosen["window_start_step"])
    hard_tolerance = float(gate["precise_tolerance_m"])
    position_core = float(np.mean(np.sum((error[window_start:, :2] / hard_tolerance) ** 2, axis=1)))
    velocity_core = float(np.mean((speed[max(1, window_start):] / float(gate["terminal_velocity_max_m_per_s"])) ** 2))
    ip_core = float((error[-1, 2] / float(gate["ip_tolerance_a"])) ** 2)
    internal_min_margin = float(internal_chosen["minimum_signed_margin"])
    hard_min_margin = float(chosen["minimum_signed_margin"])
    # Lower is better.  The soft term remains informative on both sides of the
    # hard boundary and explicitly rewards interior safety margin.
    margin_objective = float(
        -80.0 * internal_min_margin
        -20.0 * hard_min_margin
        + 1.5 * position_core
        + 1.0 * velocity_core
        + 0.05 * ip_core
        + 0.02 * action_rms**2
        + 0.05 * delta_action_rms**2
        + 2.0 * repair_rms**2
    )
    selection = margin_objective if strict_pass else float(1e6 + 1e5 * chosen["max_violation"] + 4e3 * chosen["sum_violation"] + margin_objective)

    precise_mask = np.max(np.abs(error[:, :2]), axis=1) <= float(gate["precise_tolerance_m"])
    relaxed_mask = np.max(np.abs(error[:, :2]), axis=1) <= float(gate["relaxed_tolerance_m"])
    return {
        "success": True,
        "failure_reason": "",
        "n_trajectory_steps": len(trajectory),
        "terminal_R_error_m": float(error[-1, 0]),
        "terminal_Z_error_m": float(error[-1, 1]),
        "terminal_Ip_error_A": float(error[-1, 2]),
        "terminal_RZ_euclidean_error_m": float(np.linalg.norm(error[-1, :2])),
        "terminal_RZ_box_max_error_m": float(np.max(np.abs(error[-1, :2]))),
        "terminal_velocity_m_per_s": float(speed[-1]),
        "late_velocity_rms_m_per_s": float(np.sqrt(np.mean(speed[-int(gate["late_window_steps"]):] ** 2))),
        "max_velocity_m_per_s": float(np.max(speed)),
        "max_current_utilization": current_util,
        "trailing_streak_within_30mm_steps": _trailing_streak(precise_mask),
        "trailing_streak_within_40mm_steps": _trailing_streak(relaxed_mask),
        "strict_gate_pass": strict_pass,
        "relaxed_gate_pass": relaxed_pass,
        "gate_label": label,
        "stage3_2_horizon_steps": horizon,
        "stage3_2_earliest_strict_arrival_step": min((row["endpoint_step"] for row in strict_passes), default=None),
        "stage3_2_earliest_strict_arrival_ms": min((row["arrival_time_ms"] for row in strict_passes), default=None),
        "stage3_2_earliest_relaxed_arrival_step": min((row["endpoint_step"] for row in relaxed_passes), default=None),
        "stage3_2_earliest_relaxed_arrival_ms": min((row["arrival_time_ms"] for row in relaxed_passes), default=None),
        "stage3_2_gate_endpoint_step": None if gate_endpoint is None else int(gate_endpoint["endpoint_step"]),
        "stage3_2_gate_endpoint_ms": None if gate_endpoint is None else int(gate_endpoint["arrival_time_ms"]),
        "stage3_2_best_endpoint_step": int(chosen["endpoint_step"]),
        "stage3_2_best_endpoint_ms": int(chosen["arrival_time_ms"]),
        "stage3_2_window_start_step": int(chosen["window_start_step"]),
        "stage3_2_sustained_box_max_error_m": float(chosen["sustained_box_max_error_m"]),
        "stage3_2_endpoint_velocity_m_per_s": float(chosen["endpoint_velocity_m_per_s"]),
        "stage3_2_endpoint_late_velocity_rms_m_per_s": float(chosen["endpoint_late_velocity_rms_m_per_s"]),
        "stage3_2_post_arrival_velocity_rms_m_per_s": float(chosen["post_arrival_velocity_rms_m_per_s"]),
        "stage3_2_final_velocity_m_per_s": float(chosen["final_velocity_m_per_s"]),
        "stage3_2_sustained_Ip_max_error_A": float(chosen["sustained_Ip_max_error_A"]),
        "stage3_2_minimum_signed_margin": hard_min_margin,
        "stage3_2_mean_signed_margin": float(chosen["mean_signed_margin"]),
        "stage3_2_position_signed_margin": float(chosen["position_signed_margin"]),
        "stage3_2_post_speed_signed_margin": float(chosen["post_speed_signed_margin"]),
        "stage3_2_max_violation": float(chosen["max_violation"]),
        "stage3_2_sum_violation": float(chosen["sum_violation"]),
        "stage3_2_l2_violation": float(chosen["l2_violation"]),
        "stage3_2_internal_goal_pass": internal_goal_pass,
        "stage3_2_internal_best_endpoint_step": int(internal_chosen["endpoint_step"]),
        "stage3_2_internal_sustained_box_max_error_m": float(internal_chosen["sustained_box_max_error_m"]),
        "stage3_2_internal_post_arrival_velocity_rms_m_per_s": float(internal_chosen["post_arrival_velocity_rms_m_per_s"]),
        "stage3_2_internal_minimum_signed_margin": internal_min_margin,
        "stage3_2_endpoint_evaluations": precise_evaluations,
        "stage3_2_internal_endpoint_evaluations": internal_evaluations,
        "stage3_2_margin_objective": margin_objective,
        "continuous_objective": margin_objective,
        "selection_score": selection,
        "action_rms": action_rms,
        "delta_action_rms": delta_action_rms,
        "repair_excess_rms": repair_rms,
        "wall_time_s": float(result.get("wall_time_s", 0.0)),
    }


def _margin_sort_key(row: dict[str, Any]) -> tuple[float, float, float, str]:
    return (
        0.0 if _as_bool(row.get("strict_gate_pass"), False) else 1.0,
        -_finite(row.get("stage3_2_internal_minimum_signed_margin"), -1e12),
        _finite(row.get("stage3_2_margin_objective"), 1e12),
        str(row.get("candidate_id", "")),
    )


def _long_hold_sort_key(row: dict[str, Any]) -> tuple[float, float, float, str]:
    return (
        0.0 if _as_bool(row.get("strict_gate_pass"), False) else 1.0,
        -_finite(row.get("stage3_2_minimum_signed_margin"), -1e12),
        _finite(row.get("stage3_2_margin_objective"), 1e12),
        str(row.get("candidate_id", "")),
    )


def _dedupe_rows(rows: Iterable[dict[str, Any]], *, key_fn: Callable[[dict[str, Any]], tuple]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not _as_bool(row.get("success"), False):
            continue
        try:
            key = full_vector_key(row)
        except Exception:
            continue
        if key not in best or key_fn(row) < key_fn(best[key]):
            best[key] = copy.deepcopy(row)
    return sorted(best.values(), key=key_fn)


# ---------------------------------------------------------------------------
# Candidate records, persistence, and evaluator integration
# ---------------------------------------------------------------------------


def _source_rows_with_metrics(ctx: Stage32Context) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for source in ctx.source_rows:
        row = copy.deepcopy(source)
        result = read_json_gz(Path(row["source_result_path"]))
        decoded = decode_full_sequence(ctx, _vector(row["full_control_vector"], 75))
        metrics = stage32_metrics(ctx, result, decoded, horizon=15)
        row.update(metrics)
        row["candidate_id"] = str(row.get("source_stage3_1_candidate_id", row.get("candidate_id", "source")))
        prepared.append(row)
    return sorted(prepared, key=_margin_sort_key)


def candidate_row(
    ctx: Stage32Context,
    *,
    full_control_vector: np.ndarray,
    source_name: str,
    source_type: str,
    phase_name: str,
    parent_candidate_id: str | None = None,
    source_stage3_1_candidate_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    full = clip_full_control(ctx, full_control_vector)
    row: dict[str, Any] = {
        "stage": "Stage3.2",
        "phase": phase_name,
        "candidate_id": vector_digest(full, "proposal"),
        "source_name": source_name,
        "source_type": source_type,
        "parent_candidate_id": parent_candidate_id,
        "source_stage3_1_candidate_id": source_stage3_1_candidate_id,
        "full_control_vector": full.tolist(),
        "margin_control_vector": full.reshape(25, 3)[8:15].reshape(-1).tolist(),
        "hold_control_vector": full.reshape(25, 3)[15:25].reshape(-1).tolist(),
    }
    if extra:
        row.update(copy.deepcopy(extra))
    return row


def specs_from_manifest(ctx: Stage32Context, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    horizon = int(manifest["horizon_steps"])
    specs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in manifest["candidates"]:
        candidate_id = str(row["candidate_id"])
        if not candidate_id or candidate_id in seen_ids:
            raise ValueError(f"empty/duplicate Stage3.2 candidate id: {candidate_id!r}")
        seen_ids.add(candidate_id)
        full = _vector(row["full_control_vector"], 75)
        decoded = decode_full_sequence(ctx, full)
        spec = {
            "kind": "stage3_2_candidate",
            "experiment_id": candidate_id,
            "candidate_id": candidate_id,
            "phase": str(manifest["phase"]),
            "population_index": int(row["population_index"]),
            "source_name": str(row.get("source_name", "unknown")),
            "source_type": str(row.get("source_type", "unknown")),
            "parent_candidate_id": row.get("parent_candidate_id"),
            "source_stage3_1_candidate_id": row.get("source_stage3_1_candidate_id"),
            "horizon_steps": horizon,
            "full_control_vector": full.tolist(),
            "mode_coefficients": decoded["mode_coefficients"][:horizon].tolist(),
            "action_sequence_norm_tsc": decoded["action_norm_tsc"][:horizon].tolist(),
            "action_sequence_norm_display": decoded["action_norm_display"][:horizon].tolist(),
        }
        for key, value in row.items():
            if key.startswith("probe_") or key.startswith("sqp_") or key.startswith("screen_"):
                spec[key] = copy.deepcopy(value)
        _json_safe(spec)
        specs.append(spec)
    return specs


def summarize_phase(
    ctx: Stage32Context,
    manifest: dict[str, Any],
    results: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
) -> list[dict[str, Any]]:
    horizon = int(manifest["horizon_steps"])
    by_id = {str(result["experiment_id"]): result for result in results}
    rows: list[dict[str, Any]] = []
    for candidate in manifest["candidates"]:
        candidate_id = str(candidate["candidate_id"])
        result = by_id.get(candidate_id)
        full = _vector(candidate["full_control_vector"], 75)
        decoded = decode_full_sequence(ctx, full)
        metrics = (
            _failed_metrics("missing result", horizon=horizon)
            if result is None
            else stage32_metrics(ctx, result, decoded, horizon=horizon)
        )
        relative = None if result is None else str((output_dir / f"{candidate_id}.json.gz").relative_to(ctx.paths.run_dir))
        row = {
            **copy.deepcopy(candidate),
            "result_relpath": relative,
            **metrics,
        }
        rows.append(row)
    key_fn = _margin_sort_key if horizon == 15 else _long_hold_sort_key
    rows.sort(key=key_fn)
    for rank, row in enumerate(rows, start=1):
        row["phase_rank"] = rank
    return rows


def evaluate_manifest(
    ctx: Stage32Context,
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    specs = specs_from_manifest(ctx, manifest)
    results = s2.evaluate_specs(ctx, specs, output_dir=output_dir, backend=backend, resume=resume)
    return summarize_phase(ctx, manifest, results, output_dir=output_dir)


def load_result_for_row(ctx: Stage32Context, row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source_result_path", "")).strip()
    if source:
        return read_json_gz(Path(source))
    relative = str(row.get("result_relpath", "")).strip()
    if not relative:
        raise FileNotFoundError(f"candidate {row.get('candidate_id')} has no result path")
    path = ctx.paths.run_dir / relative
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json_gz(path)


def aggregate_new_rows(ctx: Stage32Context) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    patterns = (
        ctx.paths.margin_phases.glob("round_*/probe_results.json"),
        ctx.paths.margin_phases.glob("round_*/proposal_results.json"),
        [ctx.paths.extension / "extension_results.json"],
        ctx.paths.hold_phases.glob("round_*/probe_results.json"),
        ctx.paths.hold_phases.glob("round_*/proposal_results.json"),
        [ctx.paths.controller / "full_identification_probe_results.json"],
    )
    for group in patterns:
        for path in group:
            if Path(path).exists():
                payload = read_json(path)
                if isinstance(payload, list):
                    rows.extend(payload)
    return rows


def aggregate_rows(ctx: Stage32Context) -> list[dict[str, Any]]:
    return [*ctx.source_rows, *aggregate_new_rows(ctx)]


def unique_rows(ctx: Stage32Context, *, horizon: int | None = None) -> list[dict[str, Any]]:
    rows = aggregate_rows(ctx)
    if horizon is not None:
        rows = [row for row in rows if _as_int(row.get("stage3_2_horizon_steps"), 0) == horizon]
    key_fn = _margin_sort_key if horizon == 15 else _long_hold_sort_key
    return _dedupe_rows(rows, key_fn=key_fn)


def save_best_artifacts(ctx: Stage32Context, row: dict[str, Any], *, label: str) -> None:
    result = load_result_for_row(ctx, row)
    full = _vector(row["full_control_vector"], 75)
    decoded = decode_full_sequence(ctx, full)
    horizon = _as_int(row.get("stage3_2_horizon_steps"), len(result.get("trajectory", [])) - 1)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "label": label,
        "candidate_id": row["candidate_id"],
        "source_type": row.get("source_type"),
        "parent_candidate_id": row.get("parent_candidate_id"),
        "source_stage3_1_candidate_id": row.get("source_stage3_1_candidate_id"),
        "horizon_steps": horizon,
        "full_control_vector": full.tolist(),
        "mode_coefficients": decoded["mode_coefficients"].tolist(),
        "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
        "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
        "metrics": {key: value for key, value in row.items() if key != "full_control_vector"},
    }
    atomic_write_json(ctx.paths.best / f"{label}_candidate.json", payload)
    atomic_write_json_gz(ctx.paths.best / f"{label}_tsc_result.json.gz", result)
    csv_rows: list[dict[str, Any]] = []
    for step in range(25):
        output: dict[str, Any] = {
            "step_index": step,
            "time_ms_from_start": step * int(ctx.env_cfg["dt_ms"]),
        }
        for mode in range(3):
            output[f"mode_{mode+1}_coefficient"] = float(decoded["mode_coefficients"][step, mode])
        for coil, name in enumerate(s30.TSC_COIL_NAMES):
            output[f"action_norm_tsc_{name}"] = float(decoded["action_norm_tsc"][step, coil])
        csv_rows.append(output)
    write_csv(ctx.paths.best / f"{label}_action_sequence.csv", csv_rows)


def initial_state(ctx: Stage32Context) -> dict[str, Any]:
    source = _source_rows_with_metrics(ctx)
    ctx.source_rows[:] = source
    best = source[0]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "source_stage3_1_run": str(ctx.source_stage31_run),
        "margin_next_round": 0,
        "margin_max_rounds": int(ctx.cfg["margin_sqp"]["max_rounds"]),
        "margin_trust_scale": float(ctx.cfg["margin_sqp"]["initial_trust_scale"]),
        "margin_rounds_without_improvement": 0,
        "margin_finished": False,
        "margin_stop_reason": "",
        "margin_best_candidate_id": str(best["candidate_id"]),
        "margin_best_full_control_vector": _vector(best["full_control_vector"], 75).tolist(),
        "margin_best_internal_signed_margin": float(best["stage3_2_internal_minimum_signed_margin"]),
        "extension_complete": False,
        "hold_next_round": 0,
        "hold_max_rounds": int(ctx.cfg["hold_sqp"]["max_rounds"]),
        "hold_trust_scale": float(ctx.cfg["hold_sqp"]["initial_trust_scale"]),
        "hold_rounds_without_improvement": 0,
        "hold_finished": False,
        "hold_stop_reason": "",
        "hold_best_candidate_id": None,
        "hold_best_full_control_vector": None,
        "hold_best_signed_margin": None,
        "full_controller_identification_complete": False,
        "feedback_validation_complete": False,
        "confirmation_complete": False,
        "analysis_complete": False,
        "online_feedback_validated": False,
        "robustness_validated": False,
        "updated_utc": utc_timestamp(),
    }


def load_or_initialize_state(ctx: Stage32Context, *, no_resume: bool = False) -> dict[str, Any]:
    if no_resume and ctx.paths.state.exists():
        raise FileExistsError(f"--no-resume requested but state exists: {ctx.paths.state}")
    if ctx.paths.state.exists():
        state = read_json(ctx.paths.state)
        if Path(state["source_stage3_1_run"]).resolve() != ctx.source_stage31_run:
            raise ValueError("Stage3.2 state points to a different Stage3.1 source")
        # Recreate the in-memory source metrics deterministically on every process.
        ctx.source_rows[:] = _source_rows_with_metrics(ctx)
        return state
    state = initial_state(ctx)
    atomic_write_json(ctx.paths.state, state)
    atomic_write_json(ctx.paths.source_catalog, ctx.source_rows)
    return state


# ---------------------------------------------------------------------------
# Generic real-TSC finite differences and local feature models
# ---------------------------------------------------------------------------


def feature_names(state_start: int, horizon: int) -> list[str]:
    names: list[str] = []
    for prefix in ("R_error_m", "Z_error_m", "vR_m_per_s", "vZ_m_per_s", "Ip_error_A"):
        for state in range(state_start, horizon + 1):
            names.append(f"{prefix}_state{state}")
    return names


def trajectory_feature_vector(
    ctx: Stage32Context,
    result: dict[str, Any],
    *,
    state_start: int,
    horizon: int,
    target_override: np.ndarray | None = None,
) -> np.ndarray:
    trajectory = result.get("trajectory", [])
    if len(trajectory) != horizon + 1:
        raise ValueError(f"expected {horizon + 1} states, found {len(trajectory)}")
    target = (
        np.asarray(target_override, dtype=float)
        if target_override is not None
        else np.asarray([ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]], dtype=float)
    )
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("trajectory contains non-finite state")
    error = y - target[None, :]
    velocity = _velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    states = np.arange(state_start, horizon + 1, dtype=int)
    return np.concatenate(
        [
            error[states, 0],
            error[states, 1],
            velocity[states, 0],
            velocity[states, 1],
            error[states, 2],
        ]
    )


def unpack_feature(vector: np.ndarray, n_states: int) -> dict[str, np.ndarray]:
    vector = np.asarray(vector, dtype=float).reshape(5 * n_states)
    return {
        "R": vector[0:n_states],
        "Z": vector[n_states : 2 * n_states],
        "vR": vector[2 * n_states : 3 * n_states],
        "vZ": vector[3 * n_states : 4 * n_states],
        "Ip": vector[4 * n_states : 5 * n_states],
    }


def variable_indices_for_steps(steps: Sequence[int]) -> list[int]:
    return [step * 3 + mode for step in steps for mode in range(3)]


def _candidate_id_with_metadata(prefix: str, vector: np.ndarray, *metadata: Any) -> str:
    digest = hashlib.sha256()
    digest.update(np.round(np.asarray(vector, dtype=float).reshape(-1), 10).tobytes())
    for item in metadata:
        digest.update(b"|")
        digest.update(str(item).encode("utf-8"))
    return f"{prefix}_{digest.hexdigest()[:16]}"


def _probe_points(value: float, lower: float, upper: float, delta: float) -> tuple[list[float], str]:
    if value - delta >= lower and value + delta <= upper:
        return [value - delta, value + delta], "two_sided"
    upper_room = upper - value
    lower_room = value - lower
    if upper_room >= lower_room and upper_room > 1e-10:
        first = value + min(delta, upper_room * 0.45)
        second = value + min(2.0 * delta, upper_room * 0.90)
        if second <= first + 1e-12:
            first = value + upper_room * 0.33
            second = value + upper_room * 0.67
        return [first, second], "upper_bound_inward_secant"
    if lower_room > 1e-10:
        first = value - min(delta, lower_room * 0.45)
        second = value - min(2.0 * delta, lower_room * 0.90)
        if second >= first - 1e-12:
            first = value - lower_room * 0.33
            second = value - lower_room * 0.67
        return [first, second], "lower_bound_inward_secant"
    raise RuntimeError("control variable has no finite-difference room")


def build_probe_manifest(
    ctx: Stage32Context,
    *,
    phase: str,
    round_index: int,
    centers: Sequence[dict[str, Any]],
    variable_steps: Sequence[int],
    delta_by_step_mode: np.ndarray,
    horizon: int,
) -> dict[str, Any]:
    variable_indices = variable_indices_for_steps(variable_steps)
    deltas = np.asarray(delta_by_step_mode, dtype=float).reshape(len(variable_steps), 3).reshape(-1)
    lower_full = np.tile(ctx.coefficient_lower_mode, 25)
    upper_full = np.tile(ctx.coefficient_upper_mode, 25)
    candidates: list[dict[str, Any]] = []
    for center_index, center in enumerate(centers):
        full = _vector(center["full_control_vector"], 75)
        for local_index, full_index in enumerate(variable_indices):
            points, scheme = _probe_points(
                float(full[full_index]),
                float(lower_full[full_index]),
                float(upper_full[full_index]),
                float(deltas[local_index]),
            )
            for slot, point in enumerate(points):
                vector = full.copy()
                vector[full_index] = point
                row = candidate_row(
                    ctx,
                    full_control_vector=vector,
                    source_name=f"center{center_index}_v{local_index}_{slot}",
                    source_type="real_tsc_fd_probe",
                    phase_name=f"{phase}_round_{round_index:03d}_probes",
                    parent_candidate_id=str(center["candidate_id"]),
                    source_stage3_1_candidate_id=center.get("source_stage3_1_candidate_id"),
                    extra={
                        "probe_center_candidate_id": str(center["candidate_id"]),
                        "probe_center_index": center_index,
                        "probe_variable_local_index": local_index,
                        "probe_variable_full_index": full_index,
                        "probe_step": int(variable_steps[local_index // 3]),
                        "probe_mode": int(local_index % 3),
                        "probe_slot": slot,
                        "probe_scheme": scheme,
                        "probe_requested_delta": float(deltas[local_index]),
                        "probe_actual_delta": float(point - full[full_index]),
                    },
                )
                row["candidate_id"] = _candidate_id_with_metadata(
                    f"s32{phase[:1]}r{round_index:03d}p",
                    vector,
                    center["candidate_id"],
                    local_index,
                    slot,
                )
                candidates.append(row)
    for index, row in enumerate(candidates):
        row["population_index"] = index
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "phase": f"{phase}_round_{round_index:03d}_probes",
        "round_index": round_index,
        "horizon_steps": horizon,
        "variable_steps": list(variable_steps),
        "variable_indices": variable_indices,
        "center_candidate_ids": [str(center["candidate_id"]) for center in centers],
        "population_size": len(candidates),
        "candidates": candidates,
    }


def build_real_tsc_jacobian(
    ctx: Stage32Context,
    *,
    center: dict[str, Any],
    probe_manifest: dict[str, Any],
    probe_rows: Sequence[dict[str, Any]],
    state_start: int,
    horizon: int,
    output_dir: Path,
    minimum_reliable_columns: int,
) -> dict[str, Any]:
    variable_indices = [int(value) for value in probe_manifest["variable_indices"]]
    center_result = load_result_for_row(ctx, center)
    center_feature = trajectory_feature_vector(ctx, center_result, state_start=state_start, horizon=horizon)
    center_full = _vector(center["full_control_vector"], 75)
    by_id = {str(row["candidate_id"]): row for row in probe_rows}
    specs = [
        candidate
        for candidate in probe_manifest["candidates"]
        if str(candidate["probe_center_candidate_id"]) == str(center["candidate_id"])
    ]
    n_outputs = len(center_feature)
    jacobian = np.zeros((n_outputs, len(variable_indices)), dtype=float)
    diagnostics: list[dict[str, Any]] = []
    reliable = 0
    for local_index, full_index in enumerate(variable_indices):
        samples_x = [float(center_full[full_index])]
        samples_y = [center_feature]
        sample_ids = [str(center["candidate_id"])]
        for spec in specs:
            if int(spec["probe_variable_local_index"]) != local_index:
                continue
            row = by_id.get(str(spec["candidate_id"]))
            if row is None or not _as_bool(row.get("success"), False):
                continue
            try:
                result = load_result_for_row(ctx, row)
                feature = trajectory_feature_vector(ctx, result, state_start=state_start, horizon=horizon)
            except Exception:
                continue
            full = _vector(row["full_control_vector"], 75)
            samples_x.append(float(full[full_index]))
            samples_y.append(feature)
            sample_ids.append(str(row["candidate_id"]))
        x = np.asarray(samples_x, dtype=float)
        y = np.vstack(samples_y)
        x_centered = x - np.mean(x)
        denominator = float(np.sum(x_centered**2))
        if len(np.unique(np.round(x, 12))) >= 2 and denominator > 1e-14 and np.all(np.isfinite(y)):
            slope = np.sum(x_centered[:, None] * (y - np.mean(y, axis=0)[None, :]), axis=0) / denominator
            jacobian[:, local_index] = slope
            reliable += 1
            method = "local_least_squares"
            denom_payload: float | None = denominator
        else:
            method = "unavailable"
            denom_payload = None
        diagnostics.append(
            {
                "variable_local_index": local_index,
                "variable_full_index": full_index,
                "step": int(full_index // 3),
                "mode": int(full_index % 3),
                "method": method,
                "n_samples": len(samples_x),
                "denominator": denom_payload,
                "sample_candidate_ids": sample_ids,
                "sample_values": x.tolist(),
            }
        )
    if reliable < int(minimum_reliable_columns):
        raise RuntimeError(
            f"Only {reliable}/{len(variable_indices)} reliable Jacobian columns; "
            f"minimum is {minimum_reliable_columns}"
        )
    singular = np.linalg.svd(jacobian, compute_uv=False)
    rank = int(np.linalg.matrix_rank(jacobian))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "center_candidate_id": str(center["candidate_id"]),
        "state_start": state_start,
        "horizon_steps": horizon,
        "feature_names": feature_names(state_start, horizon),
        "variable_indices": variable_indices,
        "center_feature": center_feature.tolist(),
        "jacobian": jacobian.tolist(),
        "reliable_columns": reliable,
        "numerical_rank": rank,
        "singular_values": singular.tolist(),
        "column_diagnostics": diagnostics,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_dir / f"jacobian_{center['candidate_id']}.json", summary)
    np.savez_compressed(
        output_dir / f"jacobian_{center['candidate_id']}.npz",
        center_feature=center_feature,
        jacobian=jacobian,
        variable_indices=np.asarray(variable_indices, dtype=int),
    )
    write_csv(output_dir / f"jacobian_{center['candidate_id']}_columns.csv", diagnostics)
    return summary


# ---------------------------------------------------------------------------
# Signed-margin local SQP for 150 ms margin and 250 ms hold
# ---------------------------------------------------------------------------


def _softplus(x: np.ndarray, beta: float) -> np.ndarray:
    z = np.asarray(x, dtype=float) * float(beta)
    return np.where(z > 35.0, np.asarray(x, dtype=float), np.log1p(np.exp(np.clip(z, -60.0, 60.0))) / float(beta))


def _smooth_abs(x: np.ndarray, epsilon: float = 1e-8) -> np.ndarray:
    return np.sqrt(np.asarray(x, dtype=float) ** 2 + epsilon)


def predicted_endpoint_metrics(
    ctx: Stage32Context,
    feature: np.ndarray,
    *,
    state_start: int,
    horizon: int,
    endpoint: int,
    tolerance: float,
    speed_limit: float,
) -> dict[str, float]:
    n_states = horizon - state_start + 1
    unpacked = unpack_feature(feature, n_states)
    state_values = np.arange(state_start, horizon + 1, dtype=int)
    index = {int(state): local for local, state in enumerate(state_values)}
    window_start = endpoint - int(ctx.cfg["gate"]["required_arrival_streak_steps"]) + 1
    if window_start < state_start:
        raise ValueError("feature window starts after requested arrival window")
    selected = np.asarray([index[state] for state in range(window_start, horizon + 1)], dtype=int)
    endpoint_local = index[endpoint]
    late_start = max(1, endpoint - int(ctx.cfg["gate"]["late_window_steps"]) + 1)
    late_selected = np.asarray([index[state] for state in range(max(late_start, state_start), endpoint + 1)], dtype=int)
    post_selected = np.asarray([index[state] for state in range(endpoint, horizon + 1)], dtype=int)
    speed = np.sqrt(unpacked["vR"] ** 2 + unpacked["vZ"] ** 2)
    box = np.maximum(np.abs(unpacked["R"]), np.abs(unpacked["Z"]))
    sustained_box = float(np.max(box[selected]))
    endpoint_speed = float(speed[endpoint_local])
    endpoint_late = float(np.sqrt(np.mean(speed[late_selected] ** 2)))
    post_speed = float(np.sqrt(np.mean(speed[post_selected] ** 2)))
    final_speed = float(speed[-1])
    sustained_ip = float(np.max(np.abs(unpacked["Ip"][selected])))
    margins = np.asarray(
        [
            1.0 - sustained_box / tolerance,
            1.0 - endpoint_speed / speed_limit,
            1.0 - endpoint_late / speed_limit,
            1.0 - post_speed / speed_limit,
            1.0 - final_speed / speed_limit,
            1.0 - sustained_ip / float(ctx.cfg["gate"]["ip_tolerance_a"]),
        ],
        dtype=float,
    )
    return {
        "endpoint_step": int(endpoint),
        "window_start_step": int(window_start),
        "sustained_box_max_error_m": sustained_box,
        "endpoint_velocity_m_per_s": endpoint_speed,
        "endpoint_late_velocity_rms_m_per_s": endpoint_late,
        "post_arrival_velocity_rms_m_per_s": post_speed,
        "final_velocity_m_per_s": final_speed,
        "sustained_Ip_max_error_A": sustained_ip,
        "minimum_signed_margin": float(np.min(margins)),
        "mean_signed_margin": float(np.mean(margins)),
        "max_violation": float(np.max(np.maximum(-margins, 0.0))),
    }


def linear_model_objective(
    ctx: Stage32Context,
    *,
    center_full: np.ndarray,
    center_feature: np.ndarray,
    jacobian: np.ndarray,
    variable_indices: Sequence[int],
    delta: np.ndarray,
    state_start: int,
    horizon: int,
    endpoint: int,
    profile: dict[str, Any],
    solver_cfg: dict[str, Any],
) -> float:
    feature = np.asarray(center_feature, dtype=float) + np.asarray(jacobian, dtype=float) @ np.asarray(delta, dtype=float)
    n_states = horizon - state_start + 1
    unpacked = unpack_feature(feature, n_states)
    states = np.arange(state_start, horizon + 1, dtype=int)
    index = {int(state): local for local, state in enumerate(states)}
    window_start = endpoint - int(ctx.cfg["gate"]["required_arrival_streak_steps"]) + 1
    selected = np.asarray([index[state] for state in range(window_start, horizon + 1)], dtype=int)
    internal_tol = float(ctx.cfg["margin_goal"]["internal_tolerance_m"])
    internal_v = float(ctx.cfg["margin_goal"]["internal_velocity_m_per_s"])
    beta = float(solver_cfg["softplus_beta"])
    r = unpacked["R"][selected]
    z = unpacked["Z"][selected]
    speed = np.sqrt(unpacked["vR"][selected] ** 2 + unpacked["vZ"][selected] ** 2 + 1e-12)
    ip = unpacked["Ip"][selected]
    tube_excess = _softplus(_smooth_abs(r) - internal_tol, beta) / internal_tol
    tube_excess += _softplus(_smooth_abs(z) - internal_tol, beta) / internal_tol
    speed_excess = _softplus(speed - internal_v, beta) / internal_v
    position_core = np.mean((r / internal_tol) ** 2 + (z / internal_tol) ** 2)
    velocity_core = np.mean((speed / internal_v) ** 2)
    ip_core = np.mean((ip / float(ctx.cfg["gate"]["ip_tolerance_a"])) ** 2)
    full = np.asarray(center_full, dtype=float).copy()
    full[np.asarray(variable_indices, dtype=int)] += np.asarray(delta, dtype=float)
    coefficients = full.reshape(25, 3)
    smooth = float(np.mean(np.diff(coefficients, axis=0) ** 2))
    return float(
        float(profile["tube_excess"]) * np.mean(tube_excess**2)
        + float(profile["position"]) * position_core
        + float(profile["velocity"]) * (velocity_core + 2.0 * np.mean(speed_excess**2))
        + 0.05 * ip_core
        + float(solver_cfg["delta_l2"]) * np.mean(np.asarray(delta, dtype=float) ** 2)
        + float(solver_cfg["trajectory_smoothness"]) * smooth
    )


def solve_linearized_proposals(
    ctx: Stage32Context,
    *,
    phase: str,
    round_index: int,
    center: dict[str, Any],
    jacobian_summary: dict[str, Any],
    variable_steps: Sequence[int],
    trust_scale: float,
    sqp_cfg: dict[str, Any],
    horizon: int,
) -> list[dict[str, Any]]:
    try:
        from scipy.optimize import minimize
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage3.2 SQP") from exc
    center_full = _vector(center["full_control_vector"], 75)
    center_feature = np.asarray(jacobian_summary["center_feature"], dtype=float)
    jacobian = np.asarray(jacobian_summary["jacobian"], dtype=float)
    variable_indices = [int(value) for value in jacobian_summary["variable_indices"]]
    reliable = np.asarray(
        [row["method"] != "unavailable" for row in jacobian_summary["column_diagnostics"]],
        dtype=bool,
    )
    base_radius = np.asarray(sqp_cfg["trust_radius_by_step_mode"], dtype=float).reshape(-1)
    radius = base_radius * float(trust_scale)
    lower_full = np.tile(ctx.coefficient_lower_mode, 25)
    upper_full = np.tile(ctx.coefficient_upper_mode, 25)
    lower_delta = np.maximum(-radius, lower_full[np.asarray(variable_indices)] - center_full[np.asarray(variable_indices)])
    upper_delta = np.minimum(radius, upper_full[np.asarray(variable_indices)] - center_full[np.asarray(variable_indices)])
    lower_delta[~reliable] = 0.0
    upper_delta[~reliable] = 0.0
    bounds = list(zip(lower_delta.tolist(), upper_delta.tolist()))
    solver_cfg = sqp_cfg
    profiles = sqp_cfg["profiles"]
    solved: dict[tuple[int, str], np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    for request_index, request in enumerate(sqp_cfg["proposal_requests"]):
        endpoint = int(request["endpoint_step"])
        profile_name = str(request["profile"])
        step_scale = float(request["step_scale"])
        key = (endpoint, profile_name)
        if key not in solved:
            objective = lambda delta: linear_model_objective(
                ctx,
                center_full=center_full,
                center_feature=center_feature,
                jacobian=jacobian,
                variable_indices=variable_indices,
                delta=np.asarray(delta, dtype=float),
                state_start=int(jacobian_summary["state_start"]),
                horizon=horizon,
                endpoint=endpoint,
                profile=profiles[profile_name],
                solver_cfg=solver_cfg,
            )
            result = minimize(
                objective,
                np.zeros(len(variable_indices), dtype=float),
                method="SLSQP",
                bounds=bounds,
                options={"maxiter": int(solver_cfg["max_iterations"]), "ftol": 1e-10, "disp": False},
            )
            solved[key] = np.asarray(result.x, dtype=float)
        base_delta = solved[key]
        applied = np.clip(base_delta * step_scale, lower_delta, upper_delta)
        full = center_full.copy()
        full[np.asarray(variable_indices)] += applied
        predicted_feature = center_feature + jacobian @ applied
        predicted_hard = predicted_endpoint_metrics(
            ctx,
            predicted_feature,
            state_start=int(jacobian_summary["state_start"]),
            horizon=horizon,
            endpoint=endpoint,
            tolerance=float(ctx.cfg["gate"]["precise_tolerance_m"]),
            speed_limit=float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"]),
        )
        predicted_internal = predicted_endpoint_metrics(
            ctx,
            predicted_feature,
            state_start=int(jacobian_summary["state_start"]),
            horizon=horizon,
            endpoint=endpoint,
            tolerance=float(ctx.cfg["margin_goal"]["internal_tolerance_m"]),
            speed_limit=float(ctx.cfg["margin_goal"]["internal_velocity_m_per_s"]),
        )
        boundary_fraction = float(np.max(np.abs(applied) / np.maximum(radius, 1e-12)))
        row = candidate_row(
            ctx,
            full_control_vector=full,
            source_name=f"center_{center['candidate_id']}_{profile_name}_e{endpoint}_x{step_scale:g}",
            source_type="real_tsc_sqp_margin_step" if phase == "margin" else "real_tsc_sqp_hold_step",
            phase_name=f"{phase}_round_{round_index:03d}_proposals",
            parent_candidate_id=str(center["candidate_id"]),
            source_stage3_1_candidate_id=center.get("source_stage3_1_candidate_id"),
            extra={
                "sqp_center_candidate_id": str(center["candidate_id"]),
                "sqp_endpoint_step": endpoint,
                "sqp_profile": profile_name,
                "sqp_step_scale": step_scale,
                "sqp_request_index": request_index,
                "sqp_delta": applied.tolist(),
                "predicted_hard_minimum_signed_margin": predicted_hard["minimum_signed_margin"],
                "predicted_internal_minimum_signed_margin": predicted_internal["minimum_signed_margin"],
                "predicted_sustained_box_max_error_m": predicted_hard["sustained_box_max_error_m"],
                "predicted_post_arrival_velocity_rms_m_per_s": predicted_hard["post_arrival_velocity_rms_m_per_s"],
                "predicted_linear_objective": linear_model_objective(
                    ctx,
                    center_full=center_full,
                    center_feature=center_feature,
                    jacobian=jacobian,
                    variable_indices=variable_indices,
                    delta=applied,
                    state_start=int(jacobian_summary["state_start"]),
                    horizon=horizon,
                    endpoint=endpoint,
                    profile=profiles[profile_name],
                    solver_cfg=solver_cfg,
                ),
                "predicted_margin_objective": predicted_margin_merit(
                    ctx,
                    predicted_feature,
                    state_start=int(jacobian_summary["state_start"]),
                    horizon=horizon,
                    full_control_vector=full,
                ),
                "trust_boundary_fraction": boundary_fraction,
                "trust_scale": float(trust_scale),
            },
        )
        row["candidate_id"] = _candidate_id_with_metadata(
            f"s32{phase[:1]}r{round_index:03d}s",
            full,
            center["candidate_id"],
            endpoint,
            profile_name,
            step_scale,
        )
        rows.append(row)
    return rows


def select_centers(
    rows: Sequence[dict[str, Any]],
    *,
    count: int,
    minimum_distance: float,
    key_fn: Callable[[dict[str, Any]], tuple],
) -> list[dict[str, Any]]:
    ordered = sorted([row for row in rows if _as_bool(row.get("success"), False)], key=key_fn)
    selected: list[dict[str, Any]] = []
    for row in ordered:
        vector = _vector(row["full_control_vector"], 75)
        if selected:
            distance = min(np.linalg.norm(vector - _vector(other["full_control_vector"], 75)) for other in selected)
            if distance < minimum_distance:
                continue
        selected.append(copy.deepcopy(row))
        if len(selected) >= count:
            break
    if len(selected) < count:
        ids = {str(row["candidate_id"]) for row in selected}
        for row in ordered:
            if str(row["candidate_id"]) in ids:
                continue
            selected.append(copy.deepcopy(row))
            ids.add(str(row["candidate_id"]))
            if len(selected) >= count:
                break
    if len(selected) < count:
        raise RuntimeError(f"Could select only {len(selected)} centers, expected {count}")
    return selected


def trust_update(
    *,
    center: dict[str, Any],
    proposal_rows: Sequence[dict[str, Any]],
    current_scale: float,
    sqp_cfg: dict[str, Any],
    key_fn: Callable[[dict[str, Any]], tuple],
) -> dict[str, Any]:
    candidates = [
        row
        for row in proposal_rows
        if str(row.get("sqp_center_candidate_id", "")) == str(center["candidate_id"])
        and _as_bool(row.get("success"), False)
    ]
    if not candidates:
        return {
            "center_candidate_id": center["candidate_id"],
            "accepted": False,
            "action": "shrink_rejected",
            "rho": None,
            "old_trust_scale": current_scale,
            "new_trust_scale": max(float(sqp_cfg["minimum_trust_scale"]), current_scale * float(sqp_cfg["trust_shrink_rejected"])),
        }
    best = min(candidates, key=key_fn)
    center_objective = _finite(center.get("stage3_2_margin_objective"), 1e12)
    real_objective = _finite(best.get("stage3_2_margin_objective"), 1e12)
    predicted_objective = _finite(best.get("predicted_margin_objective"), real_objective)
    predicted_reduction = center_objective - predicted_objective
    actual_reduction = center_objective - real_objective
    rho = None if predicted_reduction <= 1e-12 else actual_reduction / predicted_reduction
    accepted = actual_reduction > float(sqp_cfg["meaningful_improvement"])
    boundary = _finite(best.get("trust_boundary_fraction"), 0.0)
    if not accepted:
        action = "shrink_rejected"
        new_scale = current_scale * float(sqp_cfg["trust_shrink_rejected"])
    elif rho is not None and rho < float(sqp_cfg["ratio_poor_threshold"]):
        action = "shrink_poor_ratio"
        new_scale = current_scale * float(sqp_cfg["trust_shrink_poor_ratio"])
    elif rho is not None and rho >= float(sqp_cfg["ratio_expand_threshold"]) and boundary >= float(sqp_cfg["boundary_fraction_for_expand"]):
        action = "expand"
        new_scale = current_scale * float(sqp_cfg["trust_expand_factor"])
    else:
        action = "hold"
        new_scale = current_scale
    new_scale = float(np.clip(new_scale, float(sqp_cfg["minimum_trust_scale"]), float(sqp_cfg["maximum_trust_scale"])))
    return {
        "center_candidate_id": center["candidate_id"],
        "best_step_candidate_id": best["candidate_id"],
        "center_objective": center_objective,
        "predicted_objective": predicted_objective,
        "real_objective": real_objective,
        "predicted_reduction": predicted_reduction,
        "actual_reduction": actual_reduction,
        "rho": rho,
        "trust_boundary_fraction": boundary,
        "accepted": accepted,
        "action": action,
        "old_trust_scale": current_scale,
        "new_trust_scale": new_scale,
    }


def predicted_margin_merit(
    ctx: Stage32Context,
    feature: np.ndarray,
    *,
    state_start: int,
    horizon: int,
    full_control_vector: np.ndarray | None = None,
) -> float:
    endpoints = [endpoint for endpoint in map(int, ctx.cfg["gate"]["allowed_arrival_steps"]) if endpoint <= horizon]
    hard_rows = [
        predicted_endpoint_metrics(
            ctx,
            feature,
            state_start=state_start,
            horizon=horizon,
            endpoint=endpoint,
            tolerance=float(ctx.cfg["gate"]["precise_tolerance_m"]),
            speed_limit=float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"]),
        )
        for endpoint in endpoints
    ]
    internal_rows = [
        predicted_endpoint_metrics(
            ctx,
            feature,
            state_start=state_start,
            horizon=horizon,
            endpoint=endpoint,
            tolerance=float(ctx.cfg["margin_goal"]["internal_tolerance_m"]),
            speed_limit=float(ctx.cfg["margin_goal"]["internal_velocity_m_per_s"]),
        )
        for endpoint in endpoints
    ]
    hard = max(hard_rows, key=lambda row: (row["minimum_signed_margin"], row["mean_signed_margin"]))
    internal = max(internal_rows, key=lambda row: (row["minimum_signed_margin"], row["mean_signed_margin"]))
    n_states = horizon - state_start + 1
    unpacked = unpack_feature(feature, n_states)
    window_start = int(hard["window_start_step"])
    local_start = max(window_start - state_start, 0)
    r = unpacked["R"][local_start:]
    z = unpacked["Z"][local_start:]
    speed = np.sqrt(unpacked["vR"][local_start:] ** 2 + unpacked["vZ"][local_start:] ** 2)
    position_core = float(
        np.mean(
            (r / float(ctx.cfg["gate"]["precise_tolerance_m"])) ** 2
            + (z / float(ctx.cfg["gate"]["precise_tolerance_m"])) ** 2
        )
    )
    velocity_core = float(
        np.mean((speed / float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"])) ** 2)
    )
    ip_core = float((unpacked["Ip"][-1] / float(ctx.cfg["gate"]["ip_tolerance_a"])) ** 2)
    action_rms = delta_action_rms = repair_rms = 0.0
    if full_control_vector is not None:
        decoded = decode_full_sequence(ctx, np.asarray(full_control_vector, dtype=float))
        action = np.asarray(decoded["action_norm_tsc"], dtype=float)[:horizon]
        action_rms = float(np.sqrt(np.mean(action**2)))
        delta_action_rms = (
            float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2))) if len(action) > 1 else 0.0
        )
        repair_rms = float(
            np.sqrt(np.mean(np.asarray(decoded["saturation_excess"], dtype=float)[:horizon] ** 2))
        )
    return float(
        -80.0 * float(internal["minimum_signed_margin"])
        -20.0 * float(hard["minimum_signed_margin"])
        + 1.5 * position_core
        + 1.0 * velocity_core
        + 0.05 * ip_core
        + 0.02 * action_rms**2
        + 0.05 * delta_action_rms**2
        + 2.0 * repair_rms**2
    )


# ---------------------------------------------------------------------------
# Phase A: signed-margin optimization at 150 ms
# ---------------------------------------------------------------------------


def run_one_margin_round(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if state.get("margin_finished"):
        return state
    round_index = int(state["margin_next_round"])
    sqp_cfg = ctx.cfg["margin_sqp"]
    all_margin_rows = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 15) == 15],
        key_fn=_margin_sort_key,
    )
    centers = select_centers(
        all_margin_rows,
        count=int(sqp_cfg["centers_per_round"]),
        minimum_distance=float(sqp_cfg["center_minimum_distance"]),
        key_fn=_margin_sort_key,
    )
    round_dir = ctx.paths.margin_phases / f"round_{round_index:03d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    probe_manifest_path = round_dir / "probe_manifest.json"
    if probe_manifest_path.exists():
        probe_manifest = read_json(probe_manifest_path)
    else:
        probe_manifest = build_probe_manifest(
            ctx,
            phase="margin",
            round_index=round_index,
            centers=centers,
            variable_steps=ctx.margin_steps,
            delta_by_step_mode=np.asarray(sqp_cfg["probe_delta_by_step_mode"], dtype=float),
            horizon=15,
        )
        atomic_write_json(probe_manifest_path, probe_manifest)
        write_csv(round_dir / "probe_manifest.csv", probe_manifest["candidates"])
    probe_output = ctx.paths.margin_evaluations / f"round_{round_index:03d}_probes"
    probe_rows = evaluate_manifest(ctx, probe_manifest, output_dir=probe_output, backend=backend, resume=resume)
    atomic_write_json(round_dir / "probe_results.json", probe_rows)
    write_csv(round_dir / "probe_results.csv", probe_rows)

    jacobians: dict[str, dict[str, Any]] = {}
    proposal_candidates: list[dict[str, Any]] = []
    trust_scale = float(state["margin_trust_scale"])
    for center in centers:
        summary = build_real_tsc_jacobian(
            ctx,
            center=center,
            probe_manifest=probe_manifest,
            probe_rows=probe_rows,
            state_start=9,
            horizon=15,
            output_dir=round_dir / "jacobians",
            minimum_reliable_columns=max(15, len(ctx.margin_steps) * 2),
        )
        jacobians[str(center["candidate_id"])] = summary
        proposal_candidates.extend(
            solve_linearized_proposals(
                ctx,
                phase="margin",
                round_index=round_index,
                center=center,
                jacobian_summary=summary,
                variable_steps=ctx.margin_steps,
                trust_scale=trust_scale,
                sqp_cfg=sqp_cfg,
                horizon=15,
            )
        )
    for index, row in enumerate(proposal_candidates):
        row["population_index"] = index
    proposal_manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "phase": f"margin_round_{round_index:03d}_proposals",
        "round_index": round_index,
        "horizon_steps": 15,
        "population_size": len(proposal_candidates),
        "center_candidate_ids": [str(center["candidate_id"]) for center in centers],
        "candidates": proposal_candidates,
    }
    atomic_write_json(round_dir / "proposal_manifest.json", proposal_manifest)
    write_csv(round_dir / "proposal_manifest.csv", proposal_candidates)
    proposal_output = ctx.paths.margin_evaluations / f"round_{round_index:03d}_proposals"
    proposal_rows = evaluate_manifest(ctx, proposal_manifest, output_dir=proposal_output, backend=backend, resume=resume)
    atomic_write_json(round_dir / "proposal_results.json", proposal_rows)
    write_csv(round_dir / "proposal_results.csv", proposal_rows)

    diagnostics = [
        trust_update(
            center=center,
            proposal_rows=proposal_rows,
            current_scale=trust_scale,
            sqp_cfg=sqp_cfg,
            key_fn=_margin_sort_key,
        )
        for center in centers
    ]
    atomic_write_json(round_dir / "trust_diagnostics.json", diagnostics)
    successful = [row for row in proposal_rows if _as_bool(row.get("success"), False)]
    probe_successful = [row for row in probe_rows if _as_bool(row.get("success"), False)]
    if not successful and not probe_successful:
        raise RuntimeError("No successful Stage3.2 margin probe or proposal")
    round_best = min([*probe_successful, *successful], key=_margin_sort_key)
    previous_best_margin = float(state["margin_best_internal_signed_margin"])
    new_best_margin = float(round_best["stage3_2_internal_minimum_signed_margin"])
    meaningful = new_best_margin > previous_best_margin + float(sqp_cfg["meaningful_improvement"])
    if meaningful:
        state["margin_best_candidate_id"] = str(round_best["candidate_id"])
        state["margin_best_full_control_vector"] = _vector(round_best["full_control_vector"], 75).tolist()
        state["margin_best_internal_signed_margin"] = new_best_margin
        state["margin_rounds_without_improvement"] = 0
        save_best_artifacts(ctx, round_best, label="margin_best")
    else:
        state["margin_rounds_without_improvement"] = int(state["margin_rounds_without_improvement"]) + 1
    primary_diag = diagnostics[0]
    state["margin_trust_scale"] = float(primary_diag["new_trust_scale"])
    state["margin_next_round"] = round_index + 1
    target_margin = float(ctx.cfg["margin_goal"]["minimum_hard_signed_margin"])
    achieved = bool(
        _as_bool(round_best.get("stage3_2_internal_goal_pass"), False)
        and _finite(round_best.get("stage3_2_minimum_signed_margin"), -1e12) >= target_margin
    )
    if achieved:
        state["margin_finished"] = True
        state["margin_stop_reason"] = "internal_margin_goal_found"
    elif state["margin_next_round"] >= int(state["margin_max_rounds"]):
        state["margin_finished"] = True
        state["margin_stop_reason"] = "max_margin_rounds"
    elif int(state["margin_rounds_without_improvement"]) >= int(sqp_cfg["max_rounds_without_improvement"]):
        state["margin_finished"] = True
        state["margin_stop_reason"] = "margin_no_improvement"
    state["last_margin_round"] = {
        "round_index": round_index,
        "centers": [str(center["candidate_id"]) for center in centers],
        "round_best_candidate_id": str(round_best["candidate_id"]),
        "round_best_internal_signed_margin": new_best_margin,
        "meaningful_improvement": meaningful,
        "trust_diagnostics": diagnostics,
    }
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(
        json.dumps(
            {
                "stage": "Stage3.2",
                "phase": "margin",
                "round": round_index,
                "probe_success": sum(_as_bool(row.get("success"), False) for row in probe_rows),
                "proposal_success": len(successful),
                "best": {
                    "candidate_id": round_best["candidate_id"],
                    "strict": round_best["strict_gate_pass"],
                    "sustained_box_m": round_best["stage3_2_sustained_box_max_error_m"],
                    "post_arrival_velocity_rms": round_best["stage3_2_post_arrival_velocity_rms_m_per_s"],
                    "hard_signed_margin": round_best["stage3_2_minimum_signed_margin"],
                    "internal_signed_margin": round_best["stage3_2_internal_minimum_signed_margin"],
                },
                "next_round": state["margin_next_round"],
                "finished": state["margin_finished"],
                "stop_reason": state["margin_stop_reason"],
            },
            indent=2,
        ),
        flush=True,
    )
    return state


def run_margin_optimization(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    while True:
        state = read_json(ctx.paths.state)
        if state.get("margin_finished"):
            return state
        state = run_one_margin_round(ctx, backend=backend, resume=resume)
        if state.get("margin_finished"):
            return state


# ---------------------------------------------------------------------------
# Phase B: deterministic 250 ms tail screen
# ---------------------------------------------------------------------------


def extension_tail_templates(source_coefficients: np.ndarray) -> list[tuple[str, np.ndarray]]:
    coefficients = np.asarray(source_coefficients, dtype=float).reshape(25, 3)
    last = coefficients[14].copy()
    previous = coefficients[13].copy()
    slope = last - previous
    templates: list[tuple[str, np.ndarray]] = []

    hold = np.tile(last, (10, 1))
    templates.append(("hold_last", hold))
    templates.append(("zero", np.zeros((10, 3), dtype=float)))
    templates.append(("linear_decay", np.linspace(last, np.zeros(3), 10)))
    templates.append(("exponential_decay", np.asarray([last * (0.78 ** (index + 1)) for index in range(10)])))
    fast = np.zeros((10, 3), dtype=float)
    fast[0] = 0.50 * last
    fast[1] = 0.20 * last
    templates.append(("fast_decay", fast))
    continuation = np.asarray([last + slope * (index + 1) * (0.75 ** index) for index in range(10)])
    templates.append(("continue_slope_decay", continuation))
    for mode, amplitude, name in ((0, 0.05, "mode1"), (1, 0.05, "mode2"), (2, 0.018, "mode3")):
        for sign in (-1.0, 1.0):
            tail = hold.copy()
            pulse = np.asarray([sign * amplitude * math.exp(-0.45 * index) for index in range(10)])
            tail[:, mode] += pulse
            templates.append((f"{name}_{'plus' if sign > 0 else 'minus'}_pulse", tail))
    if len(templates) != 12:
        raise RuntimeError(f"expected 12 extension templates, built {len(templates)}")
    return templates


def run_extension_screen(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if not state.get("margin_finished"):
        raise RuntimeError("margin optimization must finish before the extension screen")
    summary_path = ctx.paths.extension / "extension_summary.json"
    if state.get("extension_complete") and summary_path.exists():
        return read_json(summary_path)
    margin_rows = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 15) == 15],
        key_fn=_margin_sort_key,
    )
    selected_sources = margin_rows[: int(ctx.cfg["extension_screen"]["source_candidates"])]
    candidates: list[dict[str, Any]] = []
    for source_index, source in enumerate(selected_sources):
        source_full = _vector(source["full_control_vector"], 75).reshape(25, 3)
        for template_index, (name, tail) in enumerate(extension_tail_templates(source_full)):
            full = source_full.copy()
            full[15:25] = np.clip(
                tail,
                ctx.coefficient_lower_mode[None, :],
                ctx.coefficient_upper_mode[None, :],
            )
            row = candidate_row(
                ctx,
                full_control_vector=full.reshape(-1),
                source_name=f"source{source_index}_{name}",
                source_type="extension_template",
                phase_name="extension_screen",
                parent_candidate_id=str(source["candidate_id"]),
                source_stage3_1_candidate_id=source.get("source_stage3_1_candidate_id"),
                extra={
                    "screen_source_rank": source_index + 1,
                    "screen_template_index": template_index,
                    "screen_template_name": name,
                },
            )
            row["candidate_id"] = _candidate_id_with_metadata("s32screen", full, source["candidate_id"], name)
            candidates.append(row)
    for index, row in enumerate(candidates):
        row["population_index"] = index
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "phase": "extension_screen",
        "horizon_steps": 25,
        "population_size": len(candidates),
        "source_candidate_ids": [str(row["candidate_id"]) for row in selected_sources],
        "candidates": candidates,
    }
    atomic_write_json(ctx.paths.extension / "extension_manifest.json", manifest)
    write_csv(ctx.paths.extension / "extension_manifest.csv", candidates)
    results = evaluate_manifest(
        ctx,
        manifest,
        output_dir=ctx.paths.extension / "raw",
        backend=backend,
        resume=resume,
    )
    atomic_write_json(ctx.paths.extension / "extension_results.json", results)
    write_csv(ctx.paths.extension / "extension_results.csv", results)
    successful = [row for row in results if _as_bool(row.get("success"), False)]
    successful_families = {str(row.get("parent_candidate_id")) for row in successful}
    minimum_success = int(ctx.cfg["extension_screen"]["minimum_successful_candidates"])
    minimum_families = int(ctx.cfg["extension_screen"]["minimum_successful_source_families"])
    if len(successful) < minimum_success or len(successful_families) < minimum_families:
        raise RuntimeError(
            f"250 ms extension screen insufficient: success={len(successful)}, families={len(successful_families)}"
        )
    ranked = sorted(successful, key=_long_hold_sort_key)
    best = ranked[0]
    save_best_artifacts(ctx, best, label="extension_best")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "phase": "extension_screen",
        "created_utc": utc_timestamp(),
        "n_candidates": len(results),
        "n_successful": len(successful),
        "n_source_families_successful": len(successful_families),
        "n_strict_long_hold": sum(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
        "n_relaxed_long_hold": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful),
        "best_candidate_id": best["candidate_id"],
        "best_signed_margin": best["stage3_2_minimum_signed_margin"],
        "best_sustained_box_m": best["stage3_2_sustained_box_max_error_m"],
        "best_post_arrival_velocity_rms": best["stage3_2_post_arrival_velocity_rms_m_per_s"],
    }
    atomic_write_json(summary_path, summary)
    state["extension_complete"] = True
    state["hold_best_candidate_id"] = str(best["candidate_id"])
    state["hold_best_full_control_vector"] = _vector(best["full_control_vector"], 75).tolist()
    state["hold_best_signed_margin"] = float(best["stage3_2_minimum_signed_margin"])
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


# ---------------------------------------------------------------------------
# Phase C: 250 ms long-hold tail SQP
# ---------------------------------------------------------------------------


def run_one_hold_round(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if state.get("hold_finished"):
        return state
    if not state.get("extension_complete"):
        raise RuntimeError("extension screen must finish before long-hold SQP")
    round_index = int(state["hold_next_round"])
    sqp_cfg = ctx.cfg["hold_sqp"]
    all_hold_rows = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25],
        key_fn=_long_hold_sort_key,
    )
    centers = select_centers(
        all_hold_rows,
        count=int(sqp_cfg["centers_per_round"]),
        minimum_distance=float(sqp_cfg["center_minimum_distance"]),
        key_fn=_long_hold_sort_key,
    )
    round_dir = ctx.paths.hold_phases / f"round_{round_index:03d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    probe_manifest_path = round_dir / "probe_manifest.json"
    if probe_manifest_path.exists():
        probe_manifest = read_json(probe_manifest_path)
    else:
        probe_manifest = build_probe_manifest(
            ctx,
            phase="hold",
            round_index=round_index,
            centers=centers,
            variable_steps=ctx.hold_steps,
            delta_by_step_mode=np.asarray(sqp_cfg["probe_delta_by_step_mode"], dtype=float),
            horizon=25,
        )
        atomic_write_json(probe_manifest_path, probe_manifest)
        write_csv(round_dir / "probe_manifest.csv", probe_manifest["candidates"])
    probe_output = ctx.paths.hold_evaluations / f"round_{round_index:03d}_probes"
    probe_rows = evaluate_manifest(ctx, probe_manifest, output_dir=probe_output, backend=backend, resume=resume)
    atomic_write_json(round_dir / "probe_results.json", probe_rows)
    write_csv(round_dir / "probe_results.csv", probe_rows)

    proposal_candidates: list[dict[str, Any]] = []
    trust_scale = float(state["hold_trust_scale"])
    for center in centers:
        summary = build_real_tsc_jacobian(
            ctx,
            center=center,
            probe_manifest=probe_manifest,
            probe_rows=probe_rows,
            state_start=10,
            horizon=25,
            output_dir=round_dir / "jacobians",
            minimum_reliable_columns=22,
        )
        proposal_candidates.extend(
            solve_linearized_proposals(
                ctx,
                phase="hold",
                round_index=round_index,
                center=center,
                jacobian_summary=summary,
                variable_steps=ctx.hold_steps,
                trust_scale=trust_scale,
                sqp_cfg=sqp_cfg,
                horizon=25,
            )
        )
    for index, row in enumerate(proposal_candidates):
        row["population_index"] = index
    proposal_manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "phase": f"hold_round_{round_index:03d}_proposals",
        "round_index": round_index,
        "horizon_steps": 25,
        "population_size": len(proposal_candidates),
        "center_candidate_ids": [str(center["candidate_id"]) for center in centers],
        "candidates": proposal_candidates,
    }
    atomic_write_json(round_dir / "proposal_manifest.json", proposal_manifest)
    write_csv(round_dir / "proposal_manifest.csv", proposal_candidates)
    proposal_output = ctx.paths.hold_evaluations / f"round_{round_index:03d}_proposals"
    proposal_rows = evaluate_manifest(ctx, proposal_manifest, output_dir=proposal_output, backend=backend, resume=resume)
    atomic_write_json(round_dir / "proposal_results.json", proposal_rows)
    write_csv(round_dir / "proposal_results.csv", proposal_rows)

    diagnostics = [
        trust_update(
            center=center,
            proposal_rows=proposal_rows,
            current_scale=trust_scale,
            sqp_cfg=sqp_cfg,
            key_fn=_long_hold_sort_key,
        )
        for center in centers
    ]
    atomic_write_json(round_dir / "trust_diagnostics.json", diagnostics)
    successful = [row for row in proposal_rows if _as_bool(row.get("success"), False)]
    probe_successful = [row for row in probe_rows if _as_bool(row.get("success"), False)]
    if not successful and not probe_successful:
        raise RuntimeError("No successful Stage3.2 long-hold probe or proposal")
    round_best = min([*probe_successful, *successful], key=_long_hold_sort_key)
    previous_margin_raw = state.get("hold_best_signed_margin")
    previous_margin = -1e12 if previous_margin_raw is None else float(previous_margin_raw)
    new_margin = float(round_best["stage3_2_minimum_signed_margin"])
    meaningful = new_margin > previous_margin + float(sqp_cfg["meaningful_improvement"])
    if meaningful:
        state["hold_best_candidate_id"] = str(round_best["candidate_id"])
        state["hold_best_full_control_vector"] = _vector(round_best["full_control_vector"], 75).tolist()
        state["hold_best_signed_margin"] = new_margin
        state["hold_rounds_without_improvement"] = 0
        save_best_artifacts(ctx, round_best, label="long_hold_best")
    else:
        state["hold_rounds_without_improvement"] = int(state["hold_rounds_without_improvement"]) + 1
    state["hold_trust_scale"] = float(diagnostics[0]["new_trust_scale"])
    state["hold_next_round"] = round_index + 1
    target_margin = float(ctx.cfg["margin_goal"]["minimum_hard_signed_margin"])
    achieved = bool(
        _as_bool(round_best.get("stage3_2_internal_goal_pass"), False)
        and _finite(round_best.get("stage3_2_minimum_signed_margin"), -1e12) >= target_margin
    )
    if achieved:
        state["hold_finished"] = True
        state["hold_stop_reason"] = "long_hold_internal_margin_goal_found"
    elif state["hold_next_round"] >= int(state["hold_max_rounds"]):
        state["hold_finished"] = True
        state["hold_stop_reason"] = "max_hold_rounds"
    elif int(state["hold_rounds_without_improvement"]) >= int(sqp_cfg["max_rounds_without_improvement"]):
        state["hold_finished"] = True
        state["hold_stop_reason"] = "hold_no_improvement"
    state["last_hold_round"] = {
        "round_index": round_index,
        "centers": [str(center["candidate_id"]) for center in centers],
        "round_best_candidate_id": str(round_best["candidate_id"]),
        "round_best_signed_margin": new_margin,
        "meaningful_improvement": meaningful,
        "trust_diagnostics": diagnostics,
    }
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(
        json.dumps(
            {
                "stage": "Stage3.2",
                "phase": "long_hold",
                "round": round_index,
                "probe_success": sum(_as_bool(row.get("success"), False) for row in probe_rows),
                "proposal_success": len(successful),
                "best": {
                    "candidate_id": round_best["candidate_id"],
                    "strict": round_best["strict_gate_pass"],
                    "sustained_box_m": round_best["stage3_2_sustained_box_max_error_m"],
                    "post_arrival_velocity_rms": round_best["stage3_2_post_arrival_velocity_rms_m_per_s"],
                    "signed_margin": round_best["stage3_2_minimum_signed_margin"],
                    "internal_signed_margin": round_best["stage3_2_internal_minimum_signed_margin"],
                },
                "next_round": state["hold_next_round"],
                "finished": state["hold_finished"],
                "stop_reason": state["hold_stop_reason"],
            },
            indent=2,
        ),
        flush=True,
    )
    return state


def run_hold_optimization(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    while True:
        state = read_json(ctx.paths.state)
        if state.get("hold_finished"):
            return state
        state = run_one_hold_round(ctx, backend=backend, resume=resume)
        if state.get("hold_finished"):
            return state


# ---------------------------------------------------------------------------
# Phase D: full 125x75 identification and dimensionless causal gains
# ---------------------------------------------------------------------------


def full_identification_delta_matrix(cfg: dict[str, Any]) -> np.ndarray:
    matrix = np.zeros((25, 3), dtype=float)
    for group in cfg["full_controller_identification"]["probe_delta_by_step_groups"]:
        delta = np.asarray(group["delta_by_mode"], dtype=float)
        for step in range(int(group["start_step"]), int(group["end_step"]) + 1):
            matrix[step] = delta
    if np.any(matrix <= 0.0):
        raise ValueError("full-identification delta matrix is incomplete")
    return matrix


def _normalization_vectors(ctx: Stage32Context, *, state_start: int, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    n = horizon - state_start + 1
    scales_cfg = ctx.cfg["mpc"]["output_scales"]
    weights_cfg = ctx.cfg["mpc"]["output_weights"]
    scales = np.concatenate(
        [
            np.full(n, float(scales_cfg["R_m"])),
            np.full(n, float(scales_cfg["Z_m"])),
            np.full(n, float(scales_cfg["vR_m_per_s"])),
            np.full(n, float(scales_cfg["vZ_m_per_s"])),
            np.full(n, float(scales_cfg["Ip_A"])),
        ]
    )
    weights = np.concatenate(
        [
            np.full(n, float(weights_cfg["R"])),
            np.full(n, float(weights_cfg["Z"])),
            np.full(n, float(weights_cfg["vR"])),
            np.full(n, float(weights_cfg["vZ"])),
            np.full(n, float(weights_cfg["Ip"])),
        ]
    )
    return scales, weights


def _regularized_gain(
    jacobian_normalized: np.ndarray,
    weights: np.ndarray,
    control_radius: np.ndarray,
    *,
    ridge_lambda: float,
    relative_cutoff: float,
    maximum_condition: float,
    bias_projection: np.ndarray | None = None,
) -> dict[str, Any]:
    j = np.asarray(jacobian_normalized, dtype=float)
    weights = np.asarray(weights, dtype=float).reshape(-1)
    radius = np.asarray(control_radius, dtype=float).reshape(-1)
    if j.shape != (len(weights), len(radius)):
        raise ValueError(f"gain shape mismatch: J={j.shape}, weights={len(weights)}, radius={len(radius)}")
    sqrt_w = np.sqrt(np.maximum(weights, 0.0))
    a = sqrt_w[:, None] * (j * radius[None, :])
    u, singular, vt = np.linalg.svd(a, full_matrices=False)
    if len(singular) == 0 or singular[0] <= 0.0:
        raise RuntimeError("normalized controller Jacobian has no nonzero singular value")
    threshold = max(
        singular[0] * float(relative_cutoff),
        singular[0] / max(float(maximum_condition), 1.0),
    )
    keep = singular >= threshold
    if not np.any(keep):
        keep[0] = True
    filt = np.zeros_like(singular)
    filt[keep] = singular[keep] / (singular[keep] ** 2 + float(ridge_lambda))
    gain_error = -(radius[:, None] * (vt.T * filt[None, :])) @ u.T
    gain_error = gain_error * sqrt_w[None, :]
    output: dict[str, Any] = {
        "singular_values": singular.tolist(),
        "retained_mask": keep.tolist(),
        "retained_rank": int(np.sum(keep)),
        "retained_condition": float(singular[keep][0] / singular[keep][-1]) if np.sum(keep) >= 2 else 1.0,
        "gain_from_normalized_output_error": gain_error.tolist(),
    }
    if bias_projection is not None:
        projection = np.asarray(bias_projection, dtype=float)
        if projection.shape[0] != j.shape[0]:
            raise ValueError("bias projection row count differs from selected outputs")
        output["gain_from_normalized_measurement"] = (gain_error @ projection).tolist()
    return output


def _measurement_bias_projection(
    ctx: Stage32Context,
    *,
    current_step: int,
    state_start: int,
    horizon: int,
    selected_rows: Sequence[int],
) -> np.ndarray:
    dt = float(ctx.env_cfg["dt_ms"]) / 1000.0
    scales = ctx.cfg["mpc"]["output_scales"]
    r_ratio = float(scales["vR_m_per_s"]) / float(scales["R_m"])
    z_ratio = float(scales["vZ_m_per_s"]) / float(scales["Z_m"])
    n = horizon - state_start + 1
    full = np.zeros((5 * n, 5), dtype=float)
    for local, state in enumerate(range(state_start, horizon + 1)):
        future = max(state - current_step, 0) * dt
        full[local, 0] = 1.0
        full[local, 2] = future * r_ratio
        full[n + local, 1] = 1.0
        full[n + local, 3] = future * z_ratio
        full[2 * n + local, 2] = 1.0
        full[3 * n + local, 3] = 1.0
        full[4 * n + local, 4] = 1.0
    return full[np.asarray(selected_rows, dtype=int)]


def build_mpc_bundle(
    ctx: Stage32Context,
    *,
    center: dict[str, Any],
    jacobian_summary: dict[str, Any],
) -> dict[str, Any]:
    state_start = int(jacobian_summary["state_start"])
    horizon = int(jacobian_summary["horizon_steps"])
    center_feature = np.asarray(jacobian_summary["center_feature"], dtype=float)
    jacobian = np.asarray(jacobian_summary["jacobian"], dtype=float)
    scales, weights = _normalization_vectors(ctx, state_start=state_start, horizon=horizon)
    j_norm = jacobian / scales[:, None]
    e_norm = center_feature / scales
    per_mode_limit = np.asarray(ctx.cfg["mpc"]["per_step_feedback_limit_by_mode"], dtype=float)
    radius = np.tile(per_mode_limit, 25)
    batch = _regularized_gain(
        j_norm,
        weights,
        radius,
        ridge_lambda=float(ctx.cfg["mpc"]["ridge_lambda"]),
        relative_cutoff=float(ctx.cfg["mpc"]["svd_relative_cutoff"]),
        maximum_condition=float(ctx.cfg["mpc"]["maximum_normalized_condition"]),
    )
    batch_gain = np.asarray(batch["gain_from_normalized_output_error"], dtype=float)
    nominal_delta = batch_gain @ e_norm
    nominal_delta_clipped = np.clip(nominal_delta, -radius, radius)
    control_steps = np.repeat(np.arange(25, dtype=int), 3)
    n = horizon - state_start + 1
    causal: list[dict[str, Any]] = []
    names = feature_names(state_start, horizon)
    for current_step in range(25):
        control_indices = [index for index, step in enumerate(control_steps) if int(step) >= current_step]
        first_future_state = current_step + 1
        selected_rows: list[int] = []
        for block in range(5):
            for local, state in enumerate(range(state_start, horizon + 1)):
                if state >= first_future_state:
                    selected_rows.append(block * n + local)
        if not selected_rows:
            continue
        j_selected = j_norm[np.asarray(selected_rows, dtype=int)][:, np.asarray(control_indices, dtype=int)]
        weights_selected = weights[np.asarray(selected_rows, dtype=int)]
        radius_selected = radius[np.asarray(control_indices, dtype=int)]
        projection = _measurement_bias_projection(
            ctx,
            current_step=current_step,
            state_start=state_start,
            horizon=horizon,
            selected_rows=selected_rows,
        )
        gain = _regularized_gain(
            j_selected,
            weights_selected,
            radius_selected,
            ridge_lambda=float(ctx.cfg["mpc"]["ridge_lambda"]),
            relative_cutoff=float(ctx.cfg["mpc"]["svd_relative_cutoff"]),
            maximum_condition=float(ctx.cfg["mpc"]["maximum_normalized_condition"]),
            bias_projection=projection,
        )
        sequence_gain = np.asarray(gain["gain_from_normalized_measurement"], dtype=float)
        causal.append(
            {
                "current_step": current_step,
                "control_variable_indices": control_indices,
                "selected_feature_indices": selected_rows,
                "selected_feature_names": [names[index] for index in selected_rows],
                "measurement_names": ["dR_norm", "dZ_norm", "dvR_norm", "dvZ_norm", "dIp_norm"],
                "sequence_gain": sequence_gain.tolist(),
                "first_action_gain": sequence_gain[:3].tolist(),
                "retained_rank": int(gain["retained_rank"]),
                "singular_values": gain["singular_values"],
                "retained_condition": float(gain["retained_condition"]),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "created_utc": utc_timestamp(),
        "center_candidate_id": str(center["candidate_id"]),
        "center_full_control_vector": _vector(center["full_control_vector"], 75).tolist(),
        "feature_names": names,
        "center_feature_physical_units": center_feature.tolist(),
        "output_scales": scales.tolist(),
        "center_feature_normalized": e_norm.tolist(),
        "output_weights": weights.tolist(),
        "jacobian_physical_units": jacobian.tolist(),
        "jacobian_normalized": j_norm.tolist(),
        "control_radius": radius.tolist(),
        "batch_gain": batch_gain.tolist(),
        "batch_retained_rank": int(batch["retained_rank"]),
        "batch_singular_values": batch["singular_values"],
        "batch_retained_condition": float(batch["retained_condition"]),
        "nominal_linear_correction": nominal_delta.tolist(),
        "nominal_linear_correction_clipped": nominal_delta_clipped.tolist(),
        "causal_time_indexed_gains": causal,
        "feedback_starts_at_step": 0,
        "target_disturbance_feedback_validated": False,
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "online_feedback_validated": False,
        "robustness_validated": False,
        "deployment_status": "OFFLINE_FULL_HORIZON_CAUSAL_MPC_CANDIDATE_ONLY",
        "warning": (
            "The gains use one local real-TSC Jacobian and a constant-velocity bias projection. "
            "They must pass the Stage3.2 target/disturbance campaign and later initial-state/plant tests before deployment."
        ),
    }


def run_full_controller_identification(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    bundle_path = ctx.paths.controller / "mpc_poc_bundle.json"
    if state.get("full_controller_identification_complete") and bundle_path.exists():
        return read_json(bundle_path)
    if not state.get("hold_finished"):
        raise RuntimeError("long-hold optimization must finish before full identification")
    hold_rows = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25],
        key_fn=_long_hold_sort_key,
    )
    center = hold_rows[0]
    maximum_recenter = int(ctx.cfg["full_controller_identification"].get("maximum_recenter_passes", 1))
    recentered = False
    final_summary: dict[str, Any] | None = None
    final_probe_rows: list[dict[str, Any]] = []
    all_probe_rows: list[dict[str, Any]] = []
    for pass_index in range(maximum_recenter + 1):
        pass_dir = ctx.paths.controller / f"identification_pass_{pass_index:02d}"
        manifest_path = pass_dir / "probe_manifest.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
        else:
            manifest = build_probe_manifest(
                ctx,
                phase="controller",
                round_index=pass_index,
                centers=[center],
                variable_steps=ctx.full_steps,
                delta_by_step_mode=full_identification_delta_matrix(ctx.cfg),
                horizon=25,
            )
            atomic_write_json(manifest_path, manifest)
            write_csv(pass_dir / "probe_manifest.csv", manifest["candidates"])
        output = ctx.paths.controller / f"identification_pass_{pass_index:02d}_raw"
        probe_rows = evaluate_manifest(ctx, manifest, output_dir=output, backend=backend, resume=resume)
        atomic_write_json(pass_dir / "probe_results.json", probe_rows)
        write_csv(pass_dir / "probe_results.csv", probe_rows)
        summary = build_real_tsc_jacobian(
            ctx,
            center=center,
            probe_manifest=manifest,
            probe_rows=probe_rows,
            state_start=1,
            horizon=25,
            output_dir=pass_dir,
            minimum_reliable_columns=int(ctx.cfg["full_controller_identification"]["minimum_reliable_columns"]),
        )
        final_summary = summary
        final_probe_rows = probe_rows
        all_probe_rows.extend(copy.deepcopy(probe_rows))
        candidates = [row for row in probe_rows if _as_bool(row.get("success"), False)]
        best_probe = min(candidates, key=_long_hold_sort_key) if candidates else center
        improvement = _finite(best_probe.get("stage3_2_minimum_signed_margin"), -1e12) - _finite(center.get("stage3_2_minimum_signed_margin"), -1e12)
        if pass_index < maximum_recenter and improvement > 0.002:
            center = best_probe
            recentered = True
            continue
        break
    if final_summary is None:
        raise RuntimeError("controller identification did not produce a Jacobian")
    # Persist every real-TSC identification probe in the common candidate catalog.
    # Stage3.1's best strict nominal was itself an identification probe; silently
    # excluding these rows would prevent Stage3.2 confirmation and expert export
    # from seeing a potentially better 250 ms trajectory.
    raw_identification_probe_rollouts = len(all_probe_rows)
    all_probe_rows = _dedupe_rows(all_probe_rows, key_fn=_long_hold_sort_key)
    atomic_write_json(ctx.paths.controller / "full_identification_probe_results.json", all_probe_rows)
    write_csv(ctx.paths.controller / "full_identification_probe_results.csv", all_probe_rows)
    successful_all = [row for row in all_probe_rows if _as_bool(row.get("success"), False)]
    if successful_all:
        best_identification_probe = min(successful_all, key=_long_hold_sort_key)
        save_best_artifacts(ctx, best_identification_probe, label="controller_identification_best")

    bundle = build_mpc_bundle(ctx, center=center, jacobian_summary=final_summary)
    bundle["identification_recentered"] = recentered
    bundle["successful_probes"] = sum(_as_bool(row.get("success"), False) for row in final_probe_rows)
    bundle["final_pass_successful_probes"] = bundle["successful_probes"]
    bundle["total_identification_probe_rollouts"] = raw_identification_probe_rollouts
    bundle["unique_identification_probe_candidates"] = len(all_probe_rows)
    bundle["total_successful_identification_probes"] = len(successful_all)
    bundle["reliable_columns"] = int(final_summary["reliable_columns"])
    bundle["numerical_rank"] = int(final_summary["numerical_rank"])
    atomic_write_json(bundle_path, bundle)
    np.savez_compressed(
        ctx.paths.controller / "mpc_poc_bundle.npz",
        jacobian=np.asarray(bundle["jacobian_physical_units"], dtype=float),
        jacobian_normalized=np.asarray(bundle["jacobian_normalized"], dtype=float),
        batch_gain=np.asarray(bundle["batch_gain"], dtype=float),
        center_full_control_vector=np.asarray(bundle["center_full_control_vector"], dtype=float),
    )
    state["full_controller_identification_complete"] = True
    state["controller_center_candidate_id"] = str(center["candidate_id"])
    state["controller_identification_recentered"] = recentered
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(
        json.dumps(
            {
                "stage": "Stage3.2",
                "phase": "full_controller_identification",
                "center": center["candidate_id"],
                "recentered": recentered,
                "successful_probes": bundle["successful_probes"],
                "reliable_columns": bundle["reliable_columns"],
                "numerical_rank": bundle["numerical_rank"],
                "batch_retained_rank": bundle["batch_retained_rank"],
                "online_feedback_validated": False,
            },
            indent=2,
        ),
        flush=True,
    )
    return bundle


# ---------------------------------------------------------------------------
# Phase E: full-horizon causal feedback validation with signed margins
# ---------------------------------------------------------------------------


def feedback_scenarios(ctx: Stage32Context) -> list[dict[str, Any]]:
    design = ctx.cfg["mpc"]["scenario_design"]
    scenarios: list[dict[str, Any]] = [
        {
            "scenario": "nominal",
            "category": "nominal",
            "target_R_offset_m": 0.0,
            "target_Z_offset_m": 0.0,
            "target_Ip_offset_A": 0.0,
            "disturbance": None,
        }
    ]
    for value in design["target_R_shifts_m"]:
        value = float(value)
        scenarios.append(
            {
                "scenario": f"target_R_{value:+.3f}m".replace("+", "p").replace("-", "m").replace(".", "p"),
                "category": "target",
                "target_R_offset_m": value,
                "target_Z_offset_m": 0.0,
                "target_Ip_offset_A": 0.0,
                "disturbance": None,
            }
        )
    for value in design["target_Z_shifts_m"]:
        value = float(value)
        scenarios.append(
            {
                "scenario": f"target_Z_{value:+.3f}m".replace("+", "p").replace("-", "m").replace(".", "p"),
                "category": "target",
                "target_R_offset_m": 0.0,
                "target_Z_offset_m": value,
                "target_Ip_offset_A": 0.0,
                "disturbance": None,
            }
        )
    shift = float(design["target_RZ_quadrant_shift_m"])
    for sign_r, sign_z in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        scenarios.append(
            {
                "scenario": f"target_RZ_{'p' if sign_r > 0 else 'm'}_{'p' if sign_z > 0 else 'm'}_{int(round(shift*1000))}mm",
                "category": "target",
                "target_R_offset_m": sign_r * shift,
                "target_Z_offset_m": sign_z * shift,
                "target_Ip_offset_A": 0.0,
                "disturbance": None,
            }
        )
    for value in design["target_Ip_shifts_A"]:
        value = float(value)
        scenarios.append(
            {
                "scenario": f"target_Ip_{int(value):+d}A".replace("+", "p").replace("-", "m"),
                "category": "target",
                "target_R_offset_m": 0.0,
                "target_Z_offset_m": 0.0,
                "target_Ip_offset_A": value,
                "disturbance": None,
            }
        )
    for mode, steps_key, amplitude_key in (
        (0, "mode1_disturbance_steps", "mode1_disturbance_amplitude"),
        (1, "mode2_disturbance_steps", "mode2_disturbance_amplitude"),
        (2, "mode3_disturbance_steps", "mode3_disturbance_amplitude"),
    ):
        amplitude = float(design[amplitude_key])
        for step in design[steps_key]:
            for sign in (-1.0, 1.0):
                scenarios.append(
                    {
                        "scenario": f"disturbance_m{mode+1}_{'p' if sign > 0 else 'm'}_s{int(step):02d}",
                        "category": "disturbance",
                        "target_R_offset_m": 0.0,
                        "target_Z_offset_m": 0.0,
                        "target_Ip_offset_A": 0.0,
                        "disturbance": {"step": int(step), "mode": mode, "amplitude": sign * amplitude},
                    }
                )
    names = [str(row["scenario"]) for row in scenarios]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate Stage3.2 feedback scenario name")
    return scenarios


def _nominal_reference(ctx: Stage32Context, center: dict[str, Any]) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    result = load_result_for_row(ctx, center)
    trajectory = result["trajectory"]
    if len(trajectory) != 26:
        raise ValueError("feedback nominal must be a 250 ms trajectory")
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    velocity = _velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    return result, y, velocity


def feedback_specs(ctx: Stage32Context, bundle: dict[str, Any], center: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in feedback_scenarios(ctx):
        for scale in ctx.cfg["mpc"]["controller_scales"]:
            scale = float(scale)
            experiment_id = (
                f"s32fb_{scenario['scenario']}_scale{scale:.2f}_{center['candidate_id']}"
                .replace(".", "p")
                .replace("-", "m")
            )
            rows.append(
                {
                    "kind": "stage3_2_feedback_validation",
                    "experiment_id": experiment_id,
                    "candidate_id": experiment_id,
                    "center_candidate_id": str(center["candidate_id"]),
                    "full_control_vector": _vector(center["full_control_vector"], 75).tolist(),
                    "controller_scale": scale,
                    **copy.deepcopy(scenario),
                }
            )
    return rows


class LocalFeedbackWorker:
    def __init__(
        self,
        ctx_payload: dict[str, Any],
        bundle: dict[str, Any],
        center: dict[str, Any],
        nominal_y: np.ndarray,
        nominal_velocity: np.ndarray,
        worker_id: str,
    ):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env

        self.cfg = ctx_payload["cfg"]
        self.train_cfg = ctx_payload["train_cfg"]
        self.env_cfg = ctx_payload["env_cfg"]
        self.modes_tsc = np.asarray(ctx_payload["modes_tsc"], dtype=float)
        self.max_delta_a = float(ctx_payload["max_delta_a"])
        self.min_current = np.asarray(ctx_payload["min_current_tsc"], dtype=float)
        self.max_current = np.asarray(ctx_payload["max_current_tsc"], dtype=float)
        self.bundle = bundle
        self.center = center
        self.nominal_y = np.asarray(nominal_y, dtype=float)
        self.nominal_velocity = np.asarray(nominal_velocity, dtype=float)
        self.env = make_tsc_rzip_env(copy.deepcopy(self.train_cfg), worker_id=worker_id, seed=None)
        self.gains = {
            int(row["current_step"]): np.asarray(row["first_action_gain"], dtype=float)
            for row in bundle["causal_time_indexed_gains"]
        }
        self.nominal_coefficients = _vector(center["full_control_vector"], 75).reshape(25, 3)
        scales = self.cfg["mpc"]["output_scales"]
        self.measurement_scale = np.asarray(
            [scales["R_m"], scales["Z_m"], scales["vR_m_per_s"], scales["vZ_m_per_s"], scales["Ip_A"]],
            dtype=float,
        )
        self.feedback_limit = np.asarray(self.cfg["mpc"]["per_step_feedback_limit_by_mode"], dtype=float)

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
        feedback_trace: list[dict[str, Any]] = []
        failure_reason = ""
        try:
            self.env.reset()
            zero = np.zeros(14, dtype=float)
            trajectory.append(jsonio._state_record(self.env, 0, zero))
            target_offset = np.asarray(
                [
                    float(spec["target_R_offset_m"]),
                    float(spec["target_Z_offset_m"]),
                    float(spec["target_Ip_offset_A"]),
                ],
                dtype=float,
            )
            scale = float(spec["controller_scale"])
            dt = float(self.env_cfg["dt_ms"]) / 1000.0
            for step in range(25):
                state = self.env.last_state
                current_y = np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)
                if step > 0 and len(trajectory) >= 2:
                    previous_rz = np.asarray([trajectory[-2]["R"], trajectory[-2]["Z"]], dtype=float)
                    current_velocity = (current_y[:2] - previous_rz) / dt
                else:
                    current_velocity = np.zeros(2, dtype=float)
                measurement_physical = np.asarray(
                    [
                        current_y[0] - self.nominal_y[step, 0] - target_offset[0],
                        current_y[1] - self.nominal_y[step, 1] - target_offset[1],
                        current_velocity[0] - self.nominal_velocity[step, 0],
                        current_velocity[1] - self.nominal_velocity[step, 1],
                        current_y[2] - self.nominal_y[step, 2] - target_offset[2],
                    ],
                    dtype=float,
                )
                measurement = measurement_physical / self.measurement_scale
                gain = self.gains.get(step)
                correction = np.zeros(3, dtype=float) if gain is None else scale * (gain @ measurement)
                correction = np.clip(correction, -self.feedback_limit, self.feedback_limit)
                coefficients = self.nominal_coefficients[step] + correction
                disturbance = spec.get("disturbance")
                if disturbance and step == int(disturbance["step"]):
                    coefficients = coefficients.copy()
                    coefficients[int(disturbance["mode"])] += float(disturbance["amplitude"])
                current_tsc = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(coefficients, current_tsc)
                _, _, terminated, truncated, info = self.env.step(action)
                trajectory.append(jsonio._state_record(self.env, step + 1, action))
                feedback_trace.append(
                    {
                        "step": step,
                        "measurement_physical": measurement_physical.tolist(),
                        "measurement_normalized": measurement.tolist(),
                        "mode_correction": correction.tolist(),
                        "mode_command": np.asarray(coefficients, dtype=float).tolist(),
                    }
                )
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
                "feedback_trace": feedback_trace,
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
                "feedback_trace": feedback_trace,
            }
        runner = getattr(self.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(
                failed=not bool(result.get("success", False)),
                reason=str(result.get("failure_reason", "stage3_2_feedback_complete")),
            )
        return _json_safe(result)

    def close(self) -> None:
        self.env.close()


def _feedback_ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class FeedbackActor:
        def __init__(self, ctx_payload, bundle, center, nominal_y, nominal_velocity, worker_id):
            self.worker = LocalFeedbackWorker(ctx_payload, bundle, center, nominal_y, nominal_velocity, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return FeedbackActor


def evaluate_feedback_specs(
    ctx: Stage32Context,
    specs: Sequence[dict[str, Any]],
    *,
    bundle: dict[str, Any],
    center: dict[str, Any],
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _, nominal_y, nominal_velocity = _nominal_reference(ctx, center)
    payload = {
        "cfg": ctx.cfg,
        "train_cfg": ctx.train_cfg,
        "env_cfg": ctx.env_cfg,
        "modes_tsc": ctx.modes_tsc.tolist(),
        "max_delta_a": ctx.max_delta_a,
        "min_current_tsc": ctx.min_current_tsc.tolist(),
        "max_current_tsc": ctx.max_current_tsc.tolist(),
    }
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
    if pending and backend == "serial":
        worker = LocalFeedbackWorker(payload, bundle, center, nominal_y, nominal_velocity, "stage32_feedback_serial")
        try:
            for index, spec in enumerate(pending, 1):
                result = worker.evaluate(spec)
                atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                print(f"[Stage3.2 feedback] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif pending and backend == "ray":
        import ray

        requested = int(os.environ.get("STAGE3_2_WORKERS", ctx.cfg.get("parallel", {}).get("n_workers", 96)))
        ray_tmpdir = os.environ.get("RAY_TMPDIR", ctx.cfg.get("parallel", {}).get("ray_tmpdir", "")) or None
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=ray_tmpdir,
            log_prefix="[Stage3.2 feedback]",
        )
        n_workers = plan.actor_count
        Actor = _feedback_ray_actor_class()
        actors = [
            Actor.remote(payload, bundle, center, nominal_y, nominal_velocity, f"stage32_feedback_{index:03d}")
            for index in range(n_workers)
        ]
        refs = {actors[index % n_workers].evaluate.remote(spec): spec for index, spec in enumerate(pending)}
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage3.2 feedback] waiting {done}/{len(pending)}", flush=True)
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
                            "feedback_trace": [],
                        }
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    print(f"[Stage3.2 feedback] {done}/{len(pending)}", flush=True)
        finally:
            s2._close_ray_actors(actors, timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 900.0)))
    elif pending:
        raise ValueError("backend must be ray or serial")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


def feedback_scale_summaries(ctx: Stage32Context, rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    by_scenario: dict[str, dict[float, dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), {})[float(row["controller_scale"])] = row
    positive_scales = sorted({float(row["controller_scale"]) for row in rows if float(row["controller_scale"]) > 0.0})
    validation = ctx.cfg["mpc"]["validation"]
    summaries: list[dict[str, Any]] = []
    for scale in positive_scales:
        comparisons: list[dict[str, Any]] = []
        nonnominal_feedback_margins: list[float] = []
        nonnominal_baseline_margins: list[float] = []
        gains: list[float] = []
        lost = recovered = preserved = strict_feedback = strict_baseline = 0
        all_success = True
        nominal_strict = False
        for scenario, values in sorted(by_scenario.items()):
            baseline = values.get(0.0)
            feedback = values.get(scale)
            if baseline is None or feedback is None:
                all_success = False
                continue
            pair_success = _as_bool(baseline.get("success"), False) and _as_bool(feedback.get("success"), False)
            all_success = all_success and pair_success
            base_margin = _finite(baseline.get("stage3_2_minimum_signed_margin"), -1e12)
            feedback_margin = _finite(feedback.get("stage3_2_minimum_signed_margin"), -1e12)
            gain = feedback_margin - base_margin
            base_strict = _as_bool(baseline.get("strict_gate_pass"), False)
            feedback_strict = _as_bool(feedback.get("strict_gate_pass"), False)
            if scenario == "nominal":
                nominal_strict = feedback_strict
            else:
                nonnominal_baseline_margins.append(base_margin)
                nonnominal_feedback_margins.append(feedback_margin)
                gains.append(gain)
                strict_baseline += int(base_strict)
                strict_feedback += int(feedback_strict)
                lost += int(base_strict and not feedback_strict)
                recovered += int((not base_strict) and feedback_strict)
                preserved += int(base_strict and feedback_strict)
            comparisons.append(
                {
                    "scenario": scenario,
                    "category": feedback.get("scenario_category"),
                    "controller_scale": scale,
                    "baseline_signed_margin": base_margin,
                    "feedback_signed_margin": feedback_margin,
                    "signed_margin_gain": gain,
                    "baseline_strict": base_strict,
                    "feedback_strict": feedback_strict,
                    "recovered": (not base_strict) and feedback_strict,
                    "lost": base_strict and not feedback_strict,
                    "preserved": base_strict and feedback_strict,
                    "pair_success": pair_success,
                }
            )
        n_nonnominal = len(nonnominal_feedback_margins)
        strict_fraction = strict_feedback / max(n_nonnominal, 1)
        median_gain = None if not gains else float(np.median(gains))
        worst_baseline = None if not nonnominal_baseline_margins else float(np.min(nonnominal_baseline_margins))
        worst_feedback = None if not nonnominal_feedback_margins else float(np.min(nonnominal_feedback_margins))
        # Worst-case gain is evaluated scenario-by-scenario.  Subtracting the
        # two independent minima can pair different scenarios and hide a loss.
        worst_gain = None if not gains else float(np.min(gains))
        passed = bool(
            all_success
            and (nominal_strict or not bool(validation.get("require_nominal_strict", True)))
            and lost <= int(validation["maximum_lost_baseline_strict_scenarios"])
            and strict_fraction >= float(validation["minimum_nonnominal_strict_fraction"])
            and median_gain is not None
            and median_gain >= float(validation["minimum_median_signed_margin_gain"])
            and worst_gain is not None
            and worst_gain >= float(validation["minimum_worst_case_signed_margin_gain"])
        )
        summaries.append(
            {
                "controller_scale": scale,
                "comparisons": comparisons,
                "n_nonnominal_scenarios": n_nonnominal,
                "n_baseline_strict": strict_baseline,
                "n_feedback_strict": strict_feedback,
                "n_preserved": preserved,
                "n_recovered": recovered,
                "n_lost": lost,
                "nonnominal_strict_fraction": strict_fraction,
                "median_signed_margin_gain": median_gain,
                "worst_baseline_signed_margin": worst_baseline,
                "worst_feedback_signed_margin": worst_feedback,
                "worst_case_signed_margin_gain": worst_gain,
                "nominal_strict": nominal_strict,
                "all_required_rollouts_successful": all_success,
                "target_disturbance_feedback_validation_pass": passed,
            }
        )
    if not summaries:
        return [], None
    passing = [row for row in summaries if row["target_disturbance_feedback_validation_pass"]]
    pool = passing if passing else summaries
    selected = min(
        pool,
        key=lambda row: (
            int(row["n_lost"]),
            0 if row["nominal_strict"] else 1,
            -int(row["n_feedback_strict"]),
            -int(row["n_recovered"]),
            -_finite(row.get("worst_feedback_signed_margin"), -1e12),
            -_finite(row.get("median_signed_margin_gain"), -1e12),
            float(row["controller_scale"]),
        ),
    )
    return summaries, selected


def run_feedback_validation(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    summary_path = ctx.paths.feedback / "feedback_validation_summary.json"
    if state.get("feedback_validation_complete") and summary_path.exists():
        return read_json(summary_path)
    bundle = run_full_controller_identification(ctx, backend=backend, resume=resume)
    all_hold_rows = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25],
        key_fn=_long_hold_sort_key,
    )
    center = next((row for row in all_hold_rows if str(row["candidate_id"]) == str(bundle["center_candidate_id"])), None)
    if center is None:
        raise RuntimeError("controller center is missing from Stage3.2 catalog")
    specs = feedback_specs(ctx, bundle, center)
    results = evaluate_feedback_specs(
        ctx,
        specs,
        bundle=bundle,
        center=center,
        output_dir=ctx.paths.feedback / "raw",
        backend=backend,
        resume=resume,
    )
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        shifted_ctx = copy.copy(ctx)
        shifted_ctx.cfg = copy.deepcopy(ctx.cfg)
        shifted_ctx.cfg["target"]["R"] += float(spec["target_R_offset_m"])
        shifted_ctx.cfg["target"]["Z"] += float(spec["target_Z_offset_m"])
        shifted_ctx.cfg["target"]["Ip"] += float(spec["target_Ip_offset_A"])
        metrics = stage32_metrics(shifted_ctx, result, None, horizon=25)
        rows.append(
            {
                "scenario": spec["scenario"],
                "scenario_category": spec["category"],
                "controller_scale": float(spec["controller_scale"]),
                "candidate_id": spec["experiment_id"],
                **metrics,
            }
        )
    rows.sort(key=lambda row: (str(row["scenario"]), float(row["controller_scale"])))
    write_csv(ctx.paths.feedback / "feedback_validation_results.csv", rows)
    atomic_write_json(ctx.paths.feedback / "feedback_validation_results.json", rows)
    scale_summaries, selected = feedback_scale_summaries(ctx, rows)
    passed = bool(selected is not None and selected["target_disturbance_feedback_validation_pass"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "created_utc": utc_timestamp(),
        "center_candidate_id": center["candidate_id"],
        "n_scenarios": len(feedback_scenarios(ctx)),
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success"), False) for row in rows),
        "n_strict": sum(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
        "selected_controller_scale": None if selected is None else float(selected["controller_scale"]),
        "selected_scale_summary": selected,
        "scale_summaries": scale_summaries,
        "target_disturbance_feedback_validated": passed,
        "online_feedback_validated": passed,
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "robustness_validated": False,
        "scope_warning": (
            "The validation covers one initial state, configured target shifts, and injected mode disturbances. "
            "It does not establish robustness to initial-state, plant-parameter, noise, or delay variation."
        ),
    }
    atomic_write_json(summary_path, summary)
    bundle["feedback_validation_run"] = True
    bundle["selected_controller_scale"] = summary["selected_controller_scale"]
    bundle["target_disturbance_feedback_validated"] = passed
    bundle["online_feedback_validated"] = passed
    bundle["robustness_validated"] = False
    bundle["deployment_status"] = (
        "TARGET_DISTURBANCE_CAUSAL_FEEDBACK_VALIDATED_POC"
        if passed
        else "OFFLINE_FULL_HORIZON_CAUSAL_MPC_CANDIDATE_ONLY"
    )
    atomic_write_json(ctx.paths.controller / "mpc_poc_bundle.json", bundle)
    state["feedback_validation_complete"] = True
    state["selected_controller_scale"] = summary["selected_controller_scale"]
    state["online_feedback_validated"] = passed
    state["target_disturbance_feedback_validated"] = passed
    state["robustness_validated"] = False
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


# ---------------------------------------------------------------------------
# Phase F: deterministic confirmation of long hold and selected feedback
# ---------------------------------------------------------------------------


def select_open_loop_confirmation_candidates(ctx: Stage32Context) -> list[dict[str, Any]]:
    rows = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25],
        key_fn=_long_hold_sort_key,
    )
    strict = [row for row in rows if _as_bool(row.get("strict_gate_pass"), False)]
    pool = strict if strict else rows
    return pool[: int(ctx.cfg["confirmation"]["open_loop_candidates"])]


def run_open_loop_confirmation(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    candidates = select_open_loop_confirmation_candidates(ctx)
    if not candidates:
        return {"verdict": "NO_LONG_HOLD_CANDIDATE", "candidate_summaries": []}
    repeats = int(ctx.cfg["confirmation"]["open_loop_repeats"])
    specs: list[dict[str, Any]] = []
    for rank, candidate in enumerate(candidates, start=1):
        full = _vector(candidate["full_control_vector"], 75)
        decoded = decode_full_sequence(ctx, full)
        for repeat in range(repeats):
            experiment_id = f"s32confirm_open_rank{rank:02d}_{candidate['candidate_id']}_r{repeat:02d}"
            specs.append(
                {
                    "kind": "stage3_2_open_loop_confirmation",
                    "experiment_id": experiment_id,
                    "candidate_id": candidate["candidate_id"],
                    "confirmation_rank": rank,
                    "confirmation_repeat": repeat,
                    "horizon_steps": 25,
                    "full_control_vector": full.tolist(),
                    "mode_coefficients": decoded["mode_coefficients"].tolist(),
                    "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
                    "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
                }
            )
    output = ctx.paths.confirmations / "open_loop_raw"
    results = s2.evaluate_specs(ctx, specs, output_dir=output, backend=backend, resume=resume)
    spec_by_id = {spec["experiment_id"]: spec for spec in specs}
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = spec_by_id[str(result["experiment_id"])]
        decoded = decode_full_sequence(ctx, _vector(spec["full_control_vector"], 75))
        rows.append(
            {
                "experiment_id": result["experiment_id"],
                "candidate_id": spec["candidate_id"],
                "confirmation_rank": spec["confirmation_rank"],
                "repeat": spec["confirmation_repeat"],
                **stage32_metrics(ctx, result, decoded, horizon=25),
            }
        )
    rows.sort(key=lambda row: (int(row["confirmation_rank"]), int(row["repeat"])))
    write_csv(ctx.paths.confirmations / "open_loop_confirmation_results.csv", rows)
    atomic_write_json(ctx.paths.confirmations / "open_loop_confirmation_results.json", rows)
    grouped: list[dict[str, Any]] = []
    for candidate in candidates:
        subset = [row for row in rows if str(row["candidate_id"]) == str(candidate["candidate_id"])]
        successful = [row for row in subset if _as_bool(row.get("success"), False)]
        grouped.append(
            {
                "candidate_id": candidate["candidate_id"],
                "repeats": len(subset),
                "successful_repeats": len(successful),
                "all_repeats_strict_gate": bool(successful) and len(successful) == len(subset) and all(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
                "worst_signed_margin": None if not successful else float(min(row["stage3_2_minimum_signed_margin"] for row in successful)),
                "worst_sustained_box_m": None if not successful else float(max(row["stage3_2_sustained_box_max_error_m"] for row in successful)),
                "max_post_arrival_velocity_rms": None if not successful else float(max(row["stage3_2_post_arrival_velocity_rms_m_per_s"] for row in successful)),
            }
        )
    n_confirmed_strict = sum(bool(row["all_repeats_strict_gate"]) for row in grouped)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "created_utc": utc_timestamp(),
        "n_candidates_all_repeats_strict": n_confirmed_strict,
        "any_candidate_confirmed_strict": n_confirmed_strict > 0,
        "all_selected_candidates_confirmed_strict": bool(grouped)
        and n_confirmed_strict == len(grouped),
        # Backward-compatible alias.  Verdict logic intentionally uses the
        # existential criterion above: one candidate with every repeat strict is
        # sufficient to establish a reproducible nominal expert.
        "all_candidates_confirmed_strict": bool(grouped)
        and n_confirmed_strict == len(grouped),
        "candidate_summaries": grouped,
    }
    atomic_write_json(ctx.paths.confirmations / "open_loop_confirmation_summary.json", summary)
    write_csv(ctx.paths.confirmations / "open_loop_confirmation_summary.csv", grouped)
    return summary


def select_feedback_confirmation_scenarios(ctx: Stage32Context, feedback_summary: dict[str, Any]) -> list[dict[str, Any]]:
    selected = feedback_summary.get("selected_scale_summary") or {}
    comparisons = list(selected.get("comparisons", []))
    by_name = {row["scenario"]: row for row in feedback_scenarios(ctx)}
    ordered = sorted(
        [row for row in comparisons if row.get("scenario") != "nominal"],
        key=lambda row: (
            _finite(row.get("feedback_signed_margin"), -1e12),
            _finite(row.get("signed_margin_gain"), -1e12),
            str(row.get("scenario")),
        ),
    )
    names = ["nominal"]
    for row in ordered:
        name = str(row["scenario"])
        if name not in names:
            names.append(name)
        if len(names) >= int(ctx.cfg["confirmation"]["feedback_scenarios"]):
            break
    return [copy.deepcopy(by_name[name]) for name in names if name in by_name]


def run_feedback_confirmation(
    ctx: Stage32Context,
    *,
    bundle: dict[str, Any],
    center: dict[str, Any],
    feedback_summary: dict[str, Any],
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    scale_raw = feedback_summary.get("selected_controller_scale")
    if scale_raw is None:
        return {"confirmed": False, "reason": "no selected feedback scale", "scenario_summaries": []}
    scale = float(scale_raw)
    scenarios = select_feedback_confirmation_scenarios(ctx, feedback_summary)
    repeats = int(ctx.cfg["confirmation"]["feedback_repeats"])
    specs: list[dict[str, Any]] = []
    for scenario in scenarios:
        for repeat in range(repeats):
            experiment_id = (
                f"s32confirm_fb_{scenario['scenario']}_scale{scale:.2f}_r{repeat:02d}_{center['candidate_id']}"
                .replace(".", "p")
                .replace("-", "m")
            )
            specs.append(
                {
                    "kind": "stage3_2_feedback_confirmation",
                    "experiment_id": experiment_id,
                    "candidate_id": experiment_id,
                    "center_candidate_id": center["candidate_id"],
                    "full_control_vector": _vector(center["full_control_vector"], 75).tolist(),
                    "controller_scale": scale,
                    "confirmation_repeat": repeat,
                    **copy.deepcopy(scenario),
                }
            )
    results = evaluate_feedback_specs(
        ctx,
        specs,
        bundle=bundle,
        center=center,
        output_dir=ctx.paths.confirmations / "feedback_raw",
        backend=backend,
        resume=resume,
    )
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        shifted = copy.copy(ctx)
        shifted.cfg = copy.deepcopy(ctx.cfg)
        shifted.cfg["target"]["R"] += float(spec["target_R_offset_m"])
        shifted.cfg["target"]["Z"] += float(spec["target_Z_offset_m"])
        shifted.cfg["target"]["Ip"] += float(spec["target_Ip_offset_A"])
        rows.append(
            {
                "scenario": spec["scenario"],
                "scenario_category": spec["category"],
                "repeat": spec["confirmation_repeat"],
                "controller_scale": scale,
                **stage32_metrics(shifted, result, None, horizon=25),
            }
        )
    rows.sort(key=lambda row: (str(row["scenario"]), int(row["repeat"])))
    write_csv(ctx.paths.confirmations / "feedback_confirmation_results.csv", rows)
    atomic_write_json(ctx.paths.confirmations / "feedback_confirmation_results.json", rows)
    grouped: list[dict[str, Any]] = []
    for scenario in scenarios:
        subset = [row for row in rows if str(row["scenario"]) == str(scenario["scenario"])]
        successful = [row for row in subset if _as_bool(row.get("success"), False)]
        grouped.append(
            {
                "scenario": scenario["scenario"],
                "category": scenario["category"],
                "repeats": len(subset),
                "successful_repeats": len(successful),
                "all_repeats_strict_gate": bool(successful) and len(successful) == len(subset) and all(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
                "worst_signed_margin": None if not successful else float(min(row["stage3_2_minimum_signed_margin"] for row in successful)),
            }
        )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "created_utc": utc_timestamp(),
        "selected_controller_scale": scale,
        "all_scenarios_confirmed_strict": bool(grouped) and all(row["all_repeats_strict_gate"] for row in grouped),
        "scenario_summaries": grouped,
    }
    atomic_write_json(ctx.paths.confirmations / "feedback_confirmation_summary.json", summary)
    write_csv(ctx.paths.confirmations / "feedback_confirmation_summary.csv", grouped)
    return summary


def open_loop_confirmation_passed(summary: dict[str, Any]) -> bool:
    """Return whether at least one candidate reproduced strict hold on every repeat.

    Older partial runs only contain ``all_candidates_confirmed_strict``; retain
    that field as a fallback so JSON-safe resume remains backward compatible.
    """
    if "any_candidate_confirmed_strict" in summary:
        return bool(summary.get("any_candidate_confirmed_strict"))
    return bool(summary.get("all_candidates_confirmed_strict", False))


def run_confirmation(ctx: Stage32Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    verdict_path = ctx.paths.confirmations / "stage3_2_verdict.json"
    if state.get("confirmation_complete") and verdict_path.exists():
        return read_json(verdict_path)
    open_summary = run_open_loop_confirmation(ctx, backend=backend, resume=resume)
    feedback_summary = run_feedback_validation(ctx, backend=backend, resume=resume)
    bundle = read_json(ctx.paths.controller / "mpc_poc_bundle.json")
    hold_rows = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25],
        key_fn=_long_hold_sort_key,
    )
    center = next((row for row in hold_rows if str(row["candidate_id"]) == str(bundle["center_candidate_id"])), None)
    if center is None:
        raise RuntimeError("feedback confirmation center not found")
    feedback_confirm = run_feedback_confirmation(
        ctx,
        bundle=bundle,
        center=center,
        feedback_summary=feedback_summary,
        backend=backend,
        resume=resume,
    )
    open_pass = open_loop_confirmation_passed(open_summary)
    feedback_validated = bool(feedback_summary.get("target_disturbance_feedback_validated", False))
    feedback_confirmed = bool(feedback_confirm.get("all_scenarios_confirmed_strict", False))
    if open_pass and feedback_validated and feedback_confirmed:
        verdict_name = "PASS_30MM_LONG_HOLD_250MS_AND_TARGET_DISTURBANCE_FEEDBACK_CONFIRMED"
    elif open_pass:
        verdict_name = "PASS_PRECISE_HOLD_30MM_250MS_OPEN_LOOP_CONFIRMED_FEEDBACK_NOT_VALIDATED"
    else:
        verdict_name = "NO_CONFIRMED_30MM_LONG_HOLD_250MS"
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "verdict": verdict_name,
        "created_utc": utc_timestamp(),
        "open_loop_confirmation": open_summary,
        "feedback_validation": feedback_summary,
        "feedback_confirmation": feedback_confirm,
        "online_feedback_validated": feedback_validated and feedback_confirmed,
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "robustness_validated": False,
        "final_task_warning": (
            "Stage3.2 does not validate different initial states, plant parameters, noise, delay, or discharge-scale hold. "
            "It is not the final robust controller and does not justify replacing causal feedback with residual RL."
        ),
    }
    atomic_write_json(verdict_path, verdict)
    state["confirmation_complete"] = True
    state["confirmation_verdict"] = verdict_name
    state["online_feedback_validated"] = bool(verdict["online_feedback_validated"])
    state["robustness_validated"] = False
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(json.dumps(verdict, indent=2), flush=True)
    return verdict


# ---------------------------------------------------------------------------
# Analysis, plots, report, synthetic checks, and CLI
# ---------------------------------------------------------------------------


def hall_of_fames(ctx: Stage32Context) -> dict[str, list[dict[str, Any]]]:
    margin = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 0) == 15],
        key_fn=_margin_sort_key,
    )
    hold = _dedupe_rows(
        [row for row in aggregate_rows(ctx) if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25],
        key_fn=_long_hold_sort_key,
    )
    return {
        "margin": margin,
        "margin_internal_goal": [row for row in margin if _as_bool(row.get("stage3_2_internal_goal_pass"), False)],
        "long_hold": hold,
        "long_hold_strict": [row for row in hold if _as_bool(row.get("strict_gate_pass"), False)],
        "long_hold_relaxed": [row for row in hold if _as_bool(row.get("relaxed_gate_pass"), False)],
        "long_hold_speed_safe": [
            row
            for row in hold
            if _finite(row.get("stage3_2_post_arrival_velocity_rms_m_per_s"), 1e12)
            <= float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"])
            and _finite(row.get("stage3_2_final_velocity_m_per_s"), 1e12)
            <= float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"])
        ],
    }


def _phase_counts(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_phase: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_phase.setdefault(str(row.get("phase", "source")), []).append(row)
    output: list[dict[str, Any]] = []
    for phase, subset in sorted(by_phase.items()):
        successful = [row for row in subset if _as_bool(row.get("success"), False)]
        output.append(
            {
                "phase": phase,
                "n_rows": len(subset),
                "n_successful": len(successful),
                "n_strict": sum(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
                "n_relaxed": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful),
                "best_signed_margin": None
                if not successful
                else float(max(_finite(row.get("stage3_2_minimum_signed_margin"), -1e12) for row in successful)),
            }
        )
    return output


def generate_plots(ctx: Stage32Context, rows: Sequence[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    if successful:
        phase_rows = _phase_counts(successful)
        labels = [row["phase"] for row in phase_rows]
        values = [
            float(row["best_signed_margin"]) if row["best_signed_margin"] is not None else float("nan")
            for row in phase_rows
        ]
        plt.figure(figsize=(max(9, 0.8 * len(labels)), 5))
        plt.plot(np.arange(len(labels)), values, marker="o")
        plt.axhline(0.0, linestyle="--")
        plt.xticks(np.arange(len(labels)), labels, rotation=60, ha="right")
        plt.ylabel("Best hard signed margin")
        plt.title("Stage3.2 signed-margin progress by phase")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(ctx.paths.analysis / "signed_margin_by_phase.png", dpi=180)
        plt.close()

    hold = [
        row
        for row in successful
        if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25
        and _as_float(row.get("stage3_2_sustained_box_max_error_m"), None) is not None
    ]
    if hold:
        x = 1000.0 * np.asarray([float(row["stage3_2_sustained_box_max_error_m"]) for row in hold])
        y = np.asarray([float(row["stage3_2_post_arrival_velocity_rms_m_per_s"]) for row in hold])
        plt.figure(figsize=(7, 6))
        plt.scatter(x, y, s=18)
        plt.axvline(30.0, linestyle="--")
        plt.axhline(0.10, linestyle="--")
        plt.xlabel("Sustained rectangular-box error through 250 ms (mm)")
        plt.ylabel("Post-arrival velocity RMS (m/s)")
        plt.title("Stage3.2 long-hold position–damping frontier")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(ctx.paths.analysis / "long_hold_position_damping_scatter.png", dpi=180)
        plt.close()

        best = min(hold, key=_long_hold_sort_key)
        try:
            result = load_result_for_row(ctx, best)
            target = np.asarray([ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"]], dtype=float)
            y_state = np.asarray([[row["R"], row["Z"]] for row in result["trajectory"]], dtype=float)
            error = 1000.0 * (y_state - target[None, :])
            time_ms = np.arange(len(error)) * int(ctx.env_cfg["dt_ms"])
            plt.figure(figsize=(9, 5))
            plt.plot(time_ms, error[:, 0], marker="o", label="R error")
            plt.plot(time_ms, error[:, 1], marker="o", label="Z error")
            plt.axhline(30.0, linestyle="--")
            plt.axhline(-30.0, linestyle="--")
            plt.axvline(150.0, linestyle=":")
            plt.xlabel("Time from 1100 ms start (ms)")
            plt.ylabel("Error (mm)")
            plt.title("Best Stage3.2 250 ms nominal trajectory")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.savefig(ctx.paths.analysis / "best_long_hold_trajectory_rz.png", dpi=180)
            plt.close()
        except Exception:
            pass

    feedback_path = ctx.paths.feedback / "feedback_validation_results.json"
    summary_path = ctx.paths.feedback / "feedback_validation_summary.json"
    if feedback_path.exists() and summary_path.exists():
        feedback_rows = read_json(feedback_path)
        feedback_summary = read_json(summary_path)
        selected_scale = feedback_summary.get("selected_controller_scale")
        if selected_scale is not None:
            scale = float(selected_scale)
            scenarios = sorted({str(row["scenario"]) for row in feedback_rows})
            baseline = []
            controlled = []
            labels = []
            for scenario in scenarios:
                b = next(
                    (
                        row
                        for row in feedback_rows
                        if str(row["scenario"]) == scenario and float(row["controller_scale"]) == 0.0
                    ),
                    None,
                )
                f = next(
                    (
                        row
                        for row in feedback_rows
                        if str(row["scenario"]) == scenario and float(row["controller_scale"]) == scale
                    ),
                    None,
                )
                if b is None or f is None:
                    continue
                labels.append(scenario)
                baseline.append(float(b["stage3_2_minimum_signed_margin"]))
                controlled.append(float(f["stage3_2_minimum_signed_margin"]))
            if labels:
                index = np.arange(len(labels))
                width = 0.38
                plt.figure(figsize=(max(12, len(labels) * 0.45), 6))
                plt.bar(index - width / 2, baseline, width=width, label="Open-loop")
                plt.bar(index + width / 2, controlled, width=width, label=f"Feedback scale {scale:g}")
                plt.axhline(0.0, linestyle="--")
                plt.xticks(index, labels, rotation=70, ha="right")
                plt.ylabel("Minimum signed safety margin")
                plt.title("Stage3.2 target/disturbance feedback validation")
                plt.grid(True, axis="y")
                plt.legend()
                plt.tight_layout()
                plt.savefig(ctx.paths.analysis / "feedback_signed_margin_comparison.png", dpi=180)
                plt.close()


def write_report(ctx: Stage32Context, summary: dict[str, Any]) -> Path:
    state = summary.get("state") or {}
    best_margin = summary.get("best_margin") or {}
    best_hold = summary.get("best_long_hold") or {}
    confirmation = summary.get("confirmation") or {}
    feedback = summary.get("feedback_validation") or {}
    lines = [
        "# Stage3.2 signed-margin, 250 ms long-hold, and causal-MPC report",
        "",
        "## Scope and immutable hard gate",
        "",
        "Stage3.2 starts from the real-TSC Stage3.1 strict nominal. It keeps the validated three-mode action space and the original 30 mm / 0.10 m/s / 10 kA hard limits. Arrival must be completed by 150 ms and the trajectory must remain safe through 250 ms.",
        "",
        "The final project task is still a robust causal feedback controller across initial states, targets, plant uncertainty, measurement noise, and delay. This run does not validate that full scope and does not justify making residual RL the primary controller.",
        "",
        "## Run summary",
        "",
        f"- Source Stage3.1: `{ctx.source_stage31_run}`",
        f"- New real-TSC optimization/identification evaluations: {summary.get('n_new_evaluations', 0)}",
        f"- New successful evaluations: {summary.get('n_new_successful', 0)}",
        f"- New 250 ms strict candidates: {summary.get('n_new_long_hold_strict', 0)}",
        f"- Margin stop reason: `{state.get('margin_stop_reason', '')}`",
        f"- Long-hold stop reason: `{state.get('hold_stop_reason', '')}`",
        "",
        "## Best 150 ms margin candidate",
        "",
        f"- Candidate: `{best_margin.get('candidate_id')}`",
        f"- Hard signed margin: {best_margin.get('stage3_2_minimum_signed_margin')}",
        f"- Internal signed margin: {best_margin.get('stage3_2_internal_minimum_signed_margin')}",
        f"- Sustained box: {best_margin.get('stage3_2_sustained_box_max_error_m')} m",
        f"- Post-arrival velocity RMS: {best_margin.get('stage3_2_post_arrival_velocity_rms_m_per_s')} m/s",
        "",
        "## Best 250 ms long-hold candidate",
        "",
        f"- Candidate: `{best_hold.get('candidate_id')}`",
        f"- Strict long hold: {best_hold.get('strict_gate_pass')}",
        f"- Minimum signed margin: {best_hold.get('stage3_2_minimum_signed_margin')}",
        f"- Sustained box through 250 ms: {best_hold.get('stage3_2_sustained_box_max_error_m')} m",
        f"- Post-arrival velocity RMS: {best_hold.get('stage3_2_post_arrival_velocity_rms_m_per_s')} m/s",
        "",
        "## Causal feedback validation",
        "",
        f"- Tested scenarios: {feedback.get('n_scenarios')}",
        f"- Selected controller scale: {feedback.get('selected_controller_scale')}",
        f"- Target/disturbance feedback validated: {feedback.get('target_disturbance_feedback_validated', False)}",
        f"- Online feedback validated in the tested scope: {feedback.get('online_feedback_validated', False)}",
        f"- Initial-state robustness validated: {feedback.get('initial_state_robustness_validated', False)}",
        f"- Plant-parameter robustness validated: {feedback.get('plant_parameter_robustness_validated', False)}",
        "",
        "## Confirmation",
        "",
        f"- Verdict: `{confirmation.get('verdict', 'NOT_RUN')}`",
        f"- Online feedback validated: {confirmation.get('online_feedback_validated', False)}",
        f"- Overall robustness validated: {confirmation.get('robustness_validated', False)}",
        "",
        "## Interpretation boundary",
        "",
        "A confirmed 250 ms nominal establishes a stronger expert trajectory than Stage3.1, but it is not the final controller. A feedback pass covers only the configured target shifts and injected-mode disturbances from one initial state. Initial-state, vessel/eddy-current, plant-parameter, noise, delay, and longer-discharge validation remain mandatory before behavior cloning, DAgger, or bounded residual RL can be treated as deployment steps.",
    ]
    report = ctx.paths.run_dir / "STAGE3_2_REPORT.md"
    jsonio.atomic_write_text(report, "\n".join(lines) + "\n")
    return report


def analyze_stage32(ctx: Stage32Context) -> dict[str, Any]:
    source_rows = _source_rows_with_metrics(ctx)
    ctx.source_rows[:] = source_rows
    new_rows = aggregate_new_rows(ctx)
    all_rows = [*source_rows, *new_rows]
    hofs = hall_of_fames(ctx)
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.analysis / "all_results.json", all_rows)
    write_csv(ctx.paths.analysis / "all_results.csv", all_rows)
    for name, rows in hofs.items():
        atomic_write_json(ctx.paths.analysis / f"{name}_hall_of_fame.json", rows[:100])
        write_csv(ctx.paths.analysis / f"{name}_hall_of_fame.csv", rows[:100])
    phase_counts = _phase_counts(new_rows)
    atomic_write_json(ctx.paths.analysis / "phase_counts.json", phase_counts)
    write_csv(ctx.paths.analysis / "phase_counts.csv", phase_counts)
    generate_plots(ctx, all_rows)

    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else None
    feedback = read_json(ctx.paths.feedback / "feedback_validation_summary.json") if (ctx.paths.feedback / "feedback_validation_summary.json").exists() else None
    confirmation = read_json(ctx.paths.confirmations / "stage3_2_verdict.json") if (ctx.paths.confirmations / "stage3_2_verdict.json").exists() else None
    best_margin = hofs["margin"][0] if hofs["margin"] else None
    best_hold = hofs["long_hold"][0] if hofs["long_hold"] else None
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.2",
        "created_utc": utc_timestamp(),
        "source_stage3_1_run": str(ctx.source_stage31_run),
        "source_strict_candidates": len(source_rows),
        "n_new_evaluations": len(new_rows),
        "n_new_successful": sum(_as_bool(row.get("success"), False) for row in new_rows),
        "n_new_150ms_strict": sum(
            _as_bool(row.get("strict_gate_pass"), False)
            for row in new_rows
            if _as_int(row.get("stage3_2_horizon_steps"), 0) == 15
        ),
        "n_new_long_hold_strict": sum(
            _as_bool(row.get("strict_gate_pass"), False)
            for row in new_rows
            if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25
        ),
        "n_new_long_hold_relaxed": sum(
            _as_bool(row.get("relaxed_gate_pass"), False)
            for row in new_rows
            if _as_int(row.get("stage3_2_horizon_steps"), 0) == 25
        ),
        "phase_counts": phase_counts,
        "best_margin": best_margin,
        "best_long_hold": best_hold,
        "state": state,
        "feedback_validation": feedback,
        "confirmation": confirmation,
        "online_feedback_validated": bool((confirmation or {}).get("online_feedback_validated", False)),
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "robustness_validated": False,
        "final_task": "robust causal feedback across initial states, targets, plant uncertainty, noise, and delay",
    }
    report = write_report(ctx, summary)
    summary["report"] = str(report)
    atomic_write_json(ctx.paths.analysis / "stage3_2_analysis_summary.json", summary)
    if state is not None:
        state["analysis_complete"] = True
        state["updated_utc"] = utc_timestamp()
        atomic_write_json(ctx.paths.state, state)
    print(json.dumps(_json_safe(summary), indent=2), flush=True)
    return summary


def _synthetic_result(ctx: Stage32Context, *, horizon: int, drift_after_150: bool = False) -> dict[str, Any]:
    target = np.asarray([ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]], dtype=float)
    trajectory: list[dict[str, Any]] = []
    for step in range(horizon + 1):
        r_error = -0.0245 + 0.00005 * min(step, 12)
        z_error = 0.0260 - 0.00004 * min(step, 12)
        if drift_after_150 and step > 15:
            z_error += 0.0012 * (step - 15)
        trajectory.append(
            {
                "step_index": step,
                "time_ms": 1100 + step * 10,
                "R": float(target[0] + r_error),
                "Z": float(target[1] + z_error),
                "Ip": float(target[2] + 200.0 - 3.0 * step),
                "currents_a_tsc": np.zeros(14).tolist(),
                "currents_a_display": np.zeros(14).tolist(),
                "action_norm_tsc": np.zeros(14).tolist(),
                "action_norm_display": np.zeros(14).tolist(),
                "abnormal": False,
            }
        )
    return {
        "schema_version": 1,
        "experiment_id": f"synthetic_{horizon}_{int(drift_after_150)}",
        "spec": {"experiment_id": "synthetic", "horizon_steps": horizon},
        "success": True,
        "failure_reason": "",
        "wall_time_s": 0.0,
        "trajectory": trajectory,
    }


def _synthetic_context(root: Path | None = None) -> Stage32Context:
    project = Path(__file__).resolve().parents[2]
    cfg = read_json(project / "configs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms.json")
    validate_stage32_config(cfg)
    base30 = s30._synthetic_context()
    run_dir = Path(root or "/tmp/stage3_2_margin_long_hold_synthetic")
    paths = Stage32Paths.from_run_dir(run_dir)
    for path in (
        paths.run_dir,
        paths.margin_phases,
        paths.margin_evaluations,
        paths.extension,
        paths.hold_phases,
        paths.hold_evaluations,
        paths.controller,
        paths.feedback,
        paths.confirmations,
        paths.analysis,
        paths.best,
        paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    train_cfg = copy.deepcopy(base30.train_cfg)
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 25
    env_cfg = copy.deepcopy(base30.env_cfg)
    env_cfg["dt_ms"] = 10
    full = np.zeros((25, 3), dtype=float)
    source_result = _synthetic_result(
        SimpleNamespace(cfg=cfg),  # type: ignore[arg-type]
        horizon=15,
        drift_after_150=False,
    )
    source_path = run_dir / "synthetic_source.json.gz"
    atomic_write_json_gz(source_path, source_result)
    source_row = {
        "stage": "Stage3.1-source",
        "phase": "source",
        "candidate_id": "synthetic_stage31_strict",
        "source_stage3_1_candidate_id": "synthetic_stage31_strict",
        "source_result_path": str(source_path),
        "result_relpath": None,
        "source_type": "synthetic",
        "full_control_vector": full.reshape(-1).tolist(),
        "margin_control_vector": full[8:15].reshape(-1).tolist(),
        "hold_control_vector": full[15:25].reshape(-1).tolist(),
        "success": True,
        "strict_gate_pass": True,
    }
    dummy31 = SimpleNamespace(
        cfg=copy.deepcopy(cfg),
        train_cfg=train_cfg,
        env_cfg=env_cfg,
        modes_tsc=np.asarray(base30.modes_tsc),
        initial_currents_tsc=np.asarray(base30.initial_currents_tsc),
        max_delta_a=float(base30.max_delta_a),
        min_current_tsc=np.asarray(base30.min_current_tsc),
        max_current_tsc=np.asarray(base30.max_current_tsc),
    )
    return Stage32Context(
        cfg=cfg,
        train_cfg=train_cfg,
        env_cfg=env_cfg,
        paths=paths,
        source_stage31_run=run_dir / "source31",
        source_stage30_run=run_dir / "source30",
        source_stage22_run=run_dir / "source22",
        base31=dummy31,  # type: ignore[arg-type]
        modes_tsc=np.asarray(base30.modes_tsc),
        initial_currents_tsc=np.asarray(base30.initial_currents_tsc),
        max_delta_a=float(base30.max_delta_a),
        min_current_tsc=np.asarray(base30.min_current_tsc),
        max_current_tsc=np.asarray(base30.max_current_tsc),
        margin_steps=tuple(range(8, 15)),
        hold_steps=tuple(range(15, 25)),
        full_steps=tuple(range(25)),
        coefficient_lower_mode=np.asarray(cfg["trajectory"]["coefficient_lower"], dtype=float),
        coefficient_upper_mode=np.asarray(cfg["trajectory"]["coefficient_upper"], dtype=float),
        source_rows=[source_row],
        source_fingerprint=None,
    )


def synthetic_stage32_test() -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory() as temporary:
        ctx = _synthetic_context(Path(temporary))
        decoded = decode_full_sequence(ctx, np.zeros(75, dtype=float))
        source_result = _synthetic_result(ctx, horizon=15)
        hold_result = _synthetic_result(ctx, horizon=25)
        drift_result = _synthetic_result(ctx, horizon=25, drift_after_150=True)
        source_metrics = stage32_metrics(ctx, source_result, decoded, horizon=15)
        hold_metrics = stage32_metrics(ctx, hold_result, decoded, horizon=25)
        drift_metrics = stage32_metrics(ctx, drift_result, decoded, horizon=25)
        if decoded["action_norm_tsc"].shape != (25, 14):
            raise AssertionError("Stage3.2 decoder did not produce 25x14 actions")
        if not source_metrics["strict_gate_pass"] or not hold_metrics["strict_gate_pass"]:
            raise AssertionError("synthetic source/long-hold gate should pass")
        if drift_metrics["strict_gate_pass"]:
            raise AssertionError("post-150 ms drift must fail the 250 ms hold gate")
        source = copy.deepcopy(ctx.source_rows[0])
        source.update(source_metrics)
        second = copy.deepcopy(source)
        second["candidate_id"] = "synthetic_second"
        second_full = np.zeros(75)
        second_full[24] = 0.04
        second["full_control_vector"] = second_full.tolist()
        margin_manifest = build_probe_manifest(
            ctx,
            phase="margin",
            round_index=0,
            centers=[source, second],
            variable_steps=ctx.margin_steps,
            delta_by_step_mode=np.asarray(ctx.cfg["margin_sqp"]["probe_delta_by_step_mode"], dtype=float),
            horizon=15,
        )
        hold_manifest = build_probe_manifest(
            ctx,
            phase="hold",
            round_index=0,
            centers=[source, second],
            variable_steps=ctx.hold_steps,
            delta_by_step_mode=np.asarray(ctx.cfg["hold_sqp"]["probe_delta_by_step_mode"], dtype=float),
            horizon=25,
        )
        full_manifest = build_probe_manifest(
            ctx,
            phase="controller",
            round_index=0,
            centers=[source],
            variable_steps=ctx.full_steps,
            delta_by_step_mode=full_identification_delta_matrix(ctx.cfg),
            horizon=25,
        )
        if margin_manifest["population_size"] != 84:
            raise AssertionError("margin probe population must be 84")
        if hold_manifest["population_size"] != 120:
            raise AssertionError("hold probe population must be 120")
        if full_manifest["population_size"] != 150:
            raise AssertionError("full-controller probe population must be 150")
        scenarios = feedback_scenarios(ctx)
        if len(scenarios) != 33:
            raise AssertionError(f"expected 33 feedback scenarios, got {len(scenarios)}")
        # Signed margins must credit interior improvements even when both rows pass.
        synthetic_feedback_rows: list[dict[str, Any]] = []
        for scenario in ("nominal", "scenario_a", "scenario_b"):
            synthetic_feedback_rows.extend(
                [
                    {
                        "scenario": scenario,
                        "scenario_category": "nominal" if scenario == "nominal" else "target",
                        "controller_scale": 0.0,
                        "success": True,
                        "strict_gate_pass": True,
                        "stage3_2_minimum_signed_margin": 0.01,
                    },
                    {
                        "scenario": scenario,
                        "scenario_category": "nominal" if scenario == "nominal" else "target",
                        "controller_scale": 0.5,
                        "success": True,
                        "strict_gate_pass": True,
                        "stage3_2_minimum_signed_margin": 0.02,
                    },
                ]
            )
        summaries, selected = feedback_scale_summaries(ctx, synthetic_feedback_rows)
        if selected is None or selected["median_signed_margin_gain"] <= 0.0:
            raise AssertionError("signed-margin feedback ranking failed")
        return {
            "stage": "Stage3.2",
            "hard_gate_changed": False,
            "source_parameter_dimension": 21,
            "long_hold_tail_dimension": 30,
            "full_feedback_dimension": 75,
            "margin_probe_population": margin_manifest["population_size"],
            "hold_probe_population": hold_manifest["population_size"],
            "full_identification_probe_population": full_manifest["population_size"],
            "extension_templates": len(extension_tail_templates(np.zeros((25, 3)))),
            "feedback_scenarios": len(scenarios),
            "synthetic_250ms_hold_pass": True,
            "post_150ms_drift_rejected": True,
            "signed_margin_feedback_ranking": True,
            "final_task_boundary_present": True,
        }


def prepare_stage32(ctx: Stage32Context, *, no_resume: bool = False) -> dict[str, Any]:
    initialize_stage32_run(ctx)
    state = load_or_initialize_state(ctx, no_resume=no_resume)
    source = _source_rows_with_metrics(ctx)
    ctx.source_rows[:] = source
    best = source[0]
    raw_source_rows = read_json(ctx.source_stage31_run / "stage3_1_analysis/all_results.json")
    successful_stage31_rows = sum(
        _as_bool(row.get("success"), False)
        for row in raw_source_rows
        if str(row.get("stage", "")) == "Stage3.1"
    )
    summary = {
        "stage": "Stage3.2",
        "run_dir": str(ctx.paths.run_dir),
        "source_stage3_1_run": str(ctx.source_stage31_run),
        "source_catalog_rows": len(raw_source_rows),
        "source_successful_stage3_1_rows": successful_stage31_rows,
        "source_strict_candidates": len(source),
        "best_source_candidate_id": best["candidate_id"],
        "best_source_hard_signed_margin": best["stage3_2_minimum_signed_margin"],
        "best_source_internal_signed_margin": best["stage3_2_internal_minimum_signed_margin"],
        "margin_variables": 21,
        "long_hold_tail_variables": 30,
        "full_feedback_variables": 75,
        "arrival_deadline_ms": 150,
        "hold_through_ms": 250,
        "hard_gate_changed": False,
        "source_fingerprint": None
        if ctx.source_fingerprint is None
        else {key: value for key, value in ctx.source_fingerprint.items() if key != "entries"},
        "state": state,
        "final_task": "robust causal feedback across initial states, targets, plant uncertainty, noise, and delay",
    }
    atomic_write_json(ctx.paths.analysis / "prepare_summary.json", summary)
    print(json.dumps(_json_safe(summary), indent=2), flush=True)
    return summary


def execute(
    *,
    config_path: str | Path,
    source_stage31_run: str | Path | None,
    run_dir: str | Path | None,
    command: str,
    backend: str,
    no_resume: bool,
) -> Any:
    if command == "self-test":
        return synthetic_stage32_test()
    ctx = load_stage32_config(
        config_path,
        source_stage31_run=source_stage31_run,
        run_dir_override=run_dir,
    )
    initialize_stage32_run(ctx)
    load_or_initialize_state(ctx, no_resume=no_resume)
    resume = not no_resume
    if command == "prepare":
        return prepare_stage32(ctx, no_resume=False)
    if command == "margin-round":
        return run_one_margin_round(ctx, backend=backend, resume=resume)
    if command == "margin":
        return run_margin_optimization(ctx, backend=backend, resume=resume)
    if command == "extension":
        return run_extension_screen(ctx, backend=backend, resume=resume)
    if command == "hold-round":
        return run_one_hold_round(ctx, backend=backend, resume=resume)
    if command == "hold":
        return run_hold_optimization(ctx, backend=backend, resume=resume)
    if command == "identify":
        return run_full_controller_identification(ctx, backend=backend, resume=resume)
    if command == "feedback":
        return run_feedback_validation(ctx, backend=backend, resume=resume)
    if command == "confirm":
        return run_confirmation(ctx, backend=backend, resume=resume)
    if command == "analyze":
        return analyze_stage32(ctx)
    if command == "all":
        run_margin_optimization(ctx, backend=backend, resume=resume)
        run_extension_screen(ctx, backend=backend, resume=resume)
        run_hold_optimization(ctx, backend=backend, resume=resume)
        run_full_controller_identification(ctx, backend=backend, resume=resume)
        run_feedback_validation(ctx, backend=backend, resume=resume)
        run_confirmation(ctx, backend=backend, resume=resume)
        state = read_json(ctx.paths.state)
        state["finished"] = True
        state["stop_reason"] = "all_phases_complete"
        state["updated_utc"] = utc_timestamp()
        atomic_write_json(ctx.paths.state, state)
        return analyze_stage32(ctx)
    raise ValueError(f"unknown command {command!r}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--source-stage3-1-run")
    parser.add_argument("--run-dir")
    parser.add_argument(
        "--command",
        choices=[
            "prepare",
            "margin-round",
            "margin",
            "extension",
            "hold-round",
            "hold",
            "identify",
            "feedback",
            "confirm",
            "analyze",
            "all",
            "self-test",
        ],
        default="all",
    )
    parser.add_argument("--backend", choices=["ray", "serial"], default="ray")
    parser.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    result = execute(
        config_path=args.config,
        source_stage31_run=args.source_stage3_1_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        no_resume=bool(args.no_resume),
    )
    if result is not None:
        print(json.dumps(_json_safe(result), indent=2), flush=True)


if __name__ == "__main__":
    main()
