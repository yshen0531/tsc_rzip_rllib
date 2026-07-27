"""Stage3.4 late-arrival target continuation and 350 ms causal MPC POC.

The stage consumes the completed Stage3.3 target-library campaign.  Arrival may
complete through 250 ms, but every accepted target trajectory must then remain
inside the unchanged 30 mm / 0.10 m/s gate through 350 ms.  Difficult targets
are reached by explicit continuation milestones and real-TSC reduced-space
refinement.  Physical trajectories are globally cached by the 105-dimensional
control vector, so the same TSC rollout is never repeated merely because it is
scored against several targets.

Only after every mandatory target has a confirmed 350 ms nominal trajectory is
a 175 x 105 real-TSC Jacobian identified and a per-step receding-horizon MPC POC
is calibrated and tested.  This remains a limited fixed-initial-state test, not
robustness or deployment validation.
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
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as base
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_2_margin_long_hold_mpc as s32
from tsc_rzip_rllib.diagnostics import stage3_3_target_conditioned_mpc as s33
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

SCHEMA_VERSION = 1
STAGE = "Stage3.4"
STATE_FILENAME = "stage3_4_state.json"
MANIFEST_FILENAME = "stage3_4_manifest.json"
SOURCE_CATALOG_FILENAME = "source_stage3_3_catalog.json"
IP_TRACKING_REVISION = "2x_for_tsc_additional_heating"
EXPECTED_IP_TRACKING = {
    "terminal_abs_tolerance_A": 2000.0,
    "hold_rms_tolerance_A": 2400.0,
    "sustained_max_tolerance_A": 4000.0,
}

# ---------------------------------------------------------------------------
# Strict JSON and small helpers
# ---------------------------------------------------------------------------


def utc_timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def read_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_json_gz(path: Path | str) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _json_safe(value: Any, path: str = "$") -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"non-finite JSON number at {path}: {number!r}")
        return number
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
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


def _as_float(value: Any, default: float = math.nan) -> float:
    try:
        result = float(value)
    except Exception:
        return default
    return result if math.isfinite(result) else default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
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
        raise ValueError(f"expected finite vector of shape ({expected},), got {array.shape}")
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


def physical_digest(vector: np.ndarray, prefix: str = "s34phys") -> str:
    rounded = np.round(np.asarray(vector, dtype=float).reshape(-1), 10)
    return f"{prefix}_{hashlib.sha256(rounded.tobytes()).hexdigest()[:20]}"


def candidate_digest(task_id: str, vector: np.ndarray, *metadata: Any, prefix: str = "s34cand") -> str:
    digest = hashlib.sha256()
    digest.update(np.round(np.asarray(vector, dtype=float).reshape(-1), 10).tobytes())
    digest.update(task_id.encode("utf-8"))
    for item in metadata:
        digest.update(b"|")
        digest.update(str(item).encode("utf-8"))
    return f"{prefix}_{digest.hexdigest()[:20]}"


# ---------------------------------------------------------------------------
# Context and source loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage34Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_catalog: Path
    physical_cache: Path
    task_root: Path
    library: Path
    identification: Path
    controller: Path
    calibration: Path
    holdout: Path
    confirmations: Path
    analysis: Path
    best: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage34Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_catalog=run_dir / SOURCE_CATALOG_FILENAME,
            physical_cache=run_dir / "stage3_4_physical_cache",
            task_root=run_dir / "stage3_4_continuation_tasks",
            library=run_dir / "stage3_4_target_library",
            identification=run_dir / "stage3_4_identification",
            controller=run_dir / "stage3_4_controller",
            calibration=run_dir / "stage3_4_mpc_calibration",
            holdout=run_dir / "stage3_4_mpc_holdout",
            confirmations=run_dir / "stage3_4_confirmations",
            analysis=run_dir / "stage3_4_analysis",
            best=run_dir / "stage3_4_best",
            source_reference=run_dir / "source_stage3_3_reference",
        )


@dataclass
class Stage34Context:
    cfg: dict[str, Any]
    train_cfg: dict[str, Any]
    env_cfg: dict[str, Any]
    paths: Stage34Paths
    project_dir: Path
    source_stage33_run: Path
    source_stage32_run: Path
    source_stage31_run: Path
    base32: s32.Stage32Context
    modes_tsc: np.ndarray
    initial_currents_tsc: np.ndarray
    max_delta_a: float
    min_current_tsc: np.ndarray
    max_current_tsc: np.ndarray
    source_bundle: dict[str, Any]
    source_library: dict[str, Any]
    source_entries: dict[str, dict[str, Any]]
    tasks: list[dict[str, Any]]
    task_map: dict[str, dict[str, Any]]
    source_fingerprint: dict[str, Any]


_REQUIRED_STAGE33 = (
    "stage3_3_config.resolved.json",
    "stage3_3_manifest.json",
    "stage3_3_state.json",
    "stage3_3_target_library/target_library.json",
    "stage3_3_confirmations/stage3_3_verdict.json",
    "env_config.resolved.json",
    "train_config.resolved.json",
)


def resolve_source_stage33_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE3_3_RUN", "").strip()
    if not value:
        raise ValueError("Pass --source-stage3-3-run or set SOURCE_STAGE3_3_RUN")
    run = Path(value).expanduser().resolve()
    missing = [str(run / item) for item in _REQUIRED_STAGE33 if not (run / item).exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage3.3 source: " + ", ".join(missing))
    verdict = read_json(run / "stage3_3_confirmations/stage3_3_verdict.json")
    allowed = {
        "TARGET_CONDITIONED_LIBRARY_INCOMPLETE_MPC_NOT_VALIDATED",
        "PASS_TARGET_CONDITIONED_NOMINAL_LIBRARY_CONFIRMED_MPC_NOT_VALIDATED",
        "PASS_TARGET_CONDITIONED_RECEDING_HORIZON_MPC_TEST_ENVELOPE_CONFIRMED",
    }
    if str(verdict.get("verdict", "")) not in allowed:
        raise RuntimeError(f"Unsupported Stage3.3 verdict: {verdict.get('verdict')!r}")
    return run


def _project_fallback(project_dir: Path, dirname: str, basename: str) -> Path | None:
    candidate = project_dir / dirname / basename
    return candidate.resolve() if candidate.exists() else None


def resolve_stage32_from_stage33(source33: Path, project_dir: Path) -> Path:
    manifest = read_json(source33 / "stage3_3_manifest.json")
    raw = str(manifest.get("source_stage3_2_run", "")).strip()
    if raw:
        path = Path(raw).expanduser()
        if path.exists():
            return path.resolve()
        fallback = _project_fallback(project_dir, "stage3_2_runs", path.name)
        if fallback is not None:
            return fallback
    env = os.environ.get("SOURCE_STAGE3_2_RUN", "").strip()
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()
    raise FileNotFoundError("Cannot resolve Stage3.2 source referenced by Stage3.3")


def _resolve_storage(value: Any, project_dir: Path) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return str(path.resolve())


def _source_inventory(source33: Path) -> dict[str, Any]:
    include: list[Path] = [source33 / item for item in _REQUIRED_STAGE33]
    library = read_json(source33 / "stage3_3_target_library/target_library.json")
    for entry in library.get("entries", []):
        relative = str(entry.get("result_relpath", "")).strip()
        if relative:
            include.append(source33 / relative)
    for path in sorted((source33 / "stage3_3_target_library/confirmation_raw").glob("*.json.gz")):
        include.append(path)
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    for path in sorted(set(include), key=lambda item: str(item)):
        if not path.is_file():
            continue
        relative = str(path.relative_to(source33))
        file_digest = _sha256_file(path)
        size = path.stat().st_size
        entries.append({"relative_path": relative, "sha256": file_digest, "size_bytes": size})
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        digest.update(file_digest.encode("ascii")); digest.update(b"\0")
    return {
        "schema_version": SCHEMA_VERSION,
        "source_stage3_3_run": str(source33),
        "n_files": len(entries),
        "total_bytes": int(sum(int(row["size_bytes"]) for row in entries)),
        "digest": digest.hexdigest(),
        "entries": entries,
    }


def build_tasks(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    raw_tasks = cfg["continuation"]["tasks"]
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_tasks):
        task_id = str(raw["task_id"])
        if not task_id or task_id in seen:
            raise ValueError(f"duplicate/empty continuation task id {task_id!r}")
        parents = [str(item) for item in raw.get("parents", [])]
        missing = [parent for parent in parents if parent not in seen]
        if missing:
            raise ValueError(f"task {task_id} references parents that are not earlier in order: {missing}")
        task = {
            "task_index": index,
            "task_id": task_id,
            "R_offset_m": float(raw.get("R_offset_m", 0.0)),
            "Z_offset_m": float(raw.get("Z_offset_m", 0.0)),
            "Ip_offset_A": float(raw.get("Ip_offset_A", 0.0)),
            "final": bool(raw.get("final", False)),
            "mandatory": bool(raw.get("mandatory", False)),
            "parents": parents,
            "source_task_id": str(raw.get("source_task_id", "")).strip() or None,
            "category": "target",
        }
        tasks.append(task)
        seen.add(task_id)
    final_mandatory = [row for row in tasks if row["final"] and row["mandatory"]]
    if not final_mandatory:
        raise ValueError("at least one final mandatory continuation task is required")
    nominal = [row for row in tasks if abs(row["R_offset_m"]) < 1e-15 and abs(row["Z_offset_m"]) < 1e-15 and abs(row["Ip_offset_A"]) < 1e-9]
    if len(nominal) != 1:
        raise ValueError("continuation task list must contain exactly one zero-offset nominal")
    return tasks


def validate_stage34_config(cfg: dict[str, Any]) -> None:
    trajectory = cfg["trajectory"]
    if int(trajectory.get("horizon_steps", -1)) != 35 or int(trajectory.get("horizon_ms", -1)) != 350:
        raise ValueError("Stage3.4 is fixed to 35 steps / 350 ms")
    if int(trajectory.get("n_modes", -1)) != 3:
        raise ValueError("Stage3.4 requires the three validated SVD modes")
    lower = np.asarray(trajectory.get("coefficient_lower", []), dtype=float)
    upper = np.asarray(trajectory.get("coefficient_upper", []), dtype=float)
    if lower.shape != (3,) or upper.shape != (3,) or np.any(lower >= upper):
        raise ValueError("invalid three-mode coefficient bounds")
    gate = cfg["gate"]
    fixed = {
        "precise_tolerance_m": 0.03,
        "relaxed_tolerance_m": 0.04,
        "terminal_velocity_max_m_per_s": 0.10,
        "late_velocity_rms_max_m_per_s": 0.10,
        "ip_safety_tolerance_A": 10000.0,
    }
    for key, expected in fixed.items():
        if not math.isclose(float(gate.get(key, math.nan)), expected, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Stage3.4 hard gate {key} must remain {expected}")
    endpoints = list(map(int, gate.get("allowed_arrival_steps", [])))
    if endpoints != list(range(12, 26)):
        raise ValueError("allowed_arrival_steps must be every step from 12 through 25")
    if int(gate.get("hold_through_step", -1)) != 35:
        raise ValueError("Stage3.4 must hold through step 35")
    if int(gate.get("minimum_post_arrival_hold_steps", -1)) != 10:
        raise ValueError("latest arrival must leave 10 control intervals of hold")
    ip_cfg = gate["ip_tracking"]
    if str(ip_cfg.get("revision", "")) != IP_TRACKING_REVISION:
        raise ValueError("wrong Ip tracking revision")
    for key, expected in EXPECTED_IP_TRACKING.items():
        if not math.isclose(float(ip_cfg.get(key, math.nan)), expected, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"gate.ip_tracking.{key} must be {expected}")
    internal_goal = cfg["continuation"].get("internal_goal", {})
    nominal_box = float(internal_goal.get("nominal_box_m", math.nan))
    final_box = float(internal_goal.get("final_box_m", math.nan))
    support_box = float(internal_goal.get("support_box_m", math.nan))
    internal_speed = float(internal_goal.get("post_arrival_velocity_rms_m_per_s", math.nan))
    if not (0.0 < nominal_box <= final_box <= support_box <= float(gate["precise_tolerance_m"])):
        raise ValueError("continuation.internal_goal box limits must be positive and ordered nominal <= final <= support <= 30 mm")
    if not (0.0 < internal_speed <= float(gate["late_velocity_rms_max_m_per_s"])):
        raise ValueError("continuation.internal_goal post-arrival velocity must be within the hard velocity gate")
    max_rounds = int(cfg["refinement"].get("max_rounds_per_task", 0))
    for key in ("minimum_refinement_rounds_nominal", "minimum_refinement_rounds_final", "minimum_refinement_rounds_support"):
        value = int(internal_goal.get(key, -1))
        if not 0 <= value <= max_rounds:
            raise ValueError(f"continuation.internal_goal.{key} must lie in [0, max_rounds_per_task]")
    tasks = build_tasks(cfg)
    final_ids = {row["task_id"] for row in tasks if row["final"]}
    confirmation = cfg["confirmation"]
    if int(confirmation.get("library_repeats_per_mandatory", 0)) < 2:
        raise ValueError("mandatory target-library confirmation requires at least two repeats")
    if not cfg["mpc"].get("calibration_scenarios") or not cfg["mpc"].get("holdout_scenarios"):
        raise ValueError("separate MPC calibration and holdout scenario sets are required")
    if not set(confirmation.get("mpc_scenarios", [])).issubset(
        {str(x["scenario"]) for x in cfg["mpc"]["calibration_scenarios"] + cfg["mpc"]["holdout_scenarios"]}
    ):
        raise ValueError("confirmation.mpc_scenarios must be present in calibration or holdout scenarios")
    if len(final_ids) < 8:
        raise ValueError("Stage3.4 final library is unexpectedly small")


def load_stage34_config(
    config_path: str | Path,
    *,
    source_stage33_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage34Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    tsc_all_root = Path(os.environ.get("TSC_ALL_ROOT", project_dir.parent)).expanduser().resolve()
    cfg = base.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(tsc_all_root)},
    )
    validate_stage34_config(cfg)
    if run_dir_override is None:
        root = base.resolve_path(cfg.get("output_root", "stage3_4_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name', 'stage3_4_late_arrival_continuation_mpc_350ms')}_{utc_timestamp()}"
    else:
        run_dir = base.resolve_path(run_dir_override, base_dir=project_dir)

    source33 = resolve_source_stage33_run(source_stage33_run)
    source32 = resolve_stage32_from_stage33(source33, project_dir)
    source31 = s33.resolve_stage31_from_stage32(source32, project_dir)
    source33_cfg = read_json(source33 / "stage3_3_config.resolved.json")
    for key in ("R", "Z", "Ip"):
        if not math.isclose(float(cfg["target"][key]), float(source33_cfg["target"][key]), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Stage3.4 base target {key} differs from Stage3.3")

    base32_ctx = s32.load_stage32_config(
        source32 / "stage3_2_config.resolved.json",
        source_stage31_run=source31,
        run_dir_override=run_dir,
    )
    train_cfg = copy.deepcopy(base32_ctx.train_cfg)
    env_cfg = copy.deepcopy(base32_ctx.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg.get("runtime", {}).get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    storage = cfg.get("storage", {})
    workspace = _resolve_storage(os.environ.get("STAGE3_4_TSC_WORKSPACE_ROOT") or storage.get("tsc_workspace_root"), project_dir)
    run_root = _resolve_storage(os.environ.get("STAGE3_4_TSC_RUN_ROOT") or storage.get("tsc_run_root"), project_dir)
    if workspace:
        env_cfg["tsc_workspace_root"] = workspace
    if run_root:
        env_cfg["run_root"] = run_root
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 35
    train_cfg.setdefault("target", {}).update(copy.deepcopy(cfg["target"]))
    base32_ctx.train_cfg = train_cfg
    base32_ctx.env_cfg = env_cfg

    source_library = read_json(source33 / "stage3_3_target_library/target_library.json")
    source_entries = {str(row["task"]["task_id"]): copy.deepcopy(row) for row in source_library.get("entries", [])}
    source_bundle = read_json(source32 / "stage3_2_controller/mpc_poc_bundle.json")
    if np.asarray(source_bundle.get("jacobian_physical_units", [])).shape != (125, 75):
        raise ValueError("Stage3.2 source bundle must contain a 125 x 75 Jacobian")
    tasks = build_tasks(cfg)
    fingerprint = _source_inventory(source33)
    return Stage34Context(
        cfg=cfg,
        train_cfg=train_cfg,
        env_cfg=env_cfg,
        paths=Stage34Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage33_run=source33,
        source_stage32_run=source32,
        source_stage31_run=source31,
        base32=base32_ctx,
        modes_tsc=np.asarray(base32_ctx.modes_tsc, dtype=float),
        initial_currents_tsc=np.asarray(base32_ctx.initial_currents_tsc, dtype=float),
        max_delta_a=float(base32_ctx.max_delta_a),
        min_current_tsc=np.asarray(base32_ctx.min_current_tsc, dtype=float),
        max_current_tsc=np.asarray(base32_ctx.max_current_tsc, dtype=float),
        source_bundle=source_bundle,
        source_library=source_library,
        source_entries=source_entries,
        tasks=tasks,
        task_map={str(row["task_id"]): row for row in tasks},
        source_fingerprint=fingerprint,
    )


def initialize_stage34_run(ctx: Stage34Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.physical_cache,
        ctx.paths.physical_cache / "raw",
        ctx.paths.task_root,
        ctx.paths.library,
        ctx.paths.identification,
        ctx.paths.controller,
        ctx.paths.calibration,
        ctx.paths.holdout,
        ctx.paths.confirmations,
        ctx.paths.analysis,
        ctx.paths.best,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    config_path = ctx.paths.run_dir / "stage3_4_config.resolved.json"
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if Path(old["source_stage3_3_run"]).resolve() != ctx.source_stage33_run:
            raise ValueError("Existing Stage3.4 run points to a different Stage3.3 source")
        old_digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        if old_digest and old_digest != str(ctx.source_fingerprint["digest"]):
            raise ValueError("Stage3.3 source content changed since this Stage3.4 run was prepared")
    atomic_write_json(config_path, ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.env_cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "source_stage3_3_run": str(ctx.source_stage33_run),
        "source_stage3_2_run": str(ctx.source_stage32_run),
        "source_fingerprint": {key: value for key, value in ctx.source_fingerprint.items() if key != "entries"},
        "horizon_steps": 35,
        "horizon_ms": 350,
        "latest_allowed_arrival_ms": 250,
        "minimum_post_arrival_hold_ms": 100,
        "hard_numeric_thresholds_changed": False,
        "timing_requirement_changed": True,
        "ip_tracking_revision": IP_TRACKING_REVISION,
        "ip_tracking_tolerances_A": copy.deepcopy(EXPECTED_IP_TRACKING),
        "physical_trajectory_cache": True,
        "target_continuation": True,
        "online_mpc_validated": False,
        "robustness_validated": False,
        "final_task": "robust causal feedback across initial states, targets, plant uncertainty, noise, and delay",
    }
    if not ctx.paths.manifest.exists():
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.source_catalog.exists():
        atomic_write_json(
            ctx.paths.source_catalog,
            {
                "source_stage3_3_run": str(ctx.source_stage33_run),
                "source_library_entries": len(ctx.source_library.get("entries", [])),
                "tasks": ctx.tasks,
                "fingerprint": ctx.source_fingerprint,
            },
        )
    inventory_path = ctx.paths.source_reference / "source_content_inventory.json"
    if not inventory_path.exists():
        atomic_write_json(inventory_path, ctx.source_fingerprint)
    for relative in (
        "stage3_3_config.resolved.json",
        "stage3_3_manifest.json",
        "stage3_3_state.json",
        "stage3_3_target_library/target_library.json",
        "stage3_3_confirmations/stage3_3_verdict.json",
        "stage3_3_analysis/stage3_3_analysis_summary.json",
    ):
        source = ctx.source_stage33_run / relative
        if source.exists():
            destination = ctx.paths.source_reference / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(source, destination)


# ---------------------------------------------------------------------------
# 35-step decoding and target metrics
# ---------------------------------------------------------------------------


def clip_control(ctx: Stage34Context, vector: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(vector, dtype=float).reshape(35, 3)
    lower = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    return np.clip(coefficients, lower[None, :], upper[None, :]).reshape(-1)


def decode_control(ctx: Stage34Context, vector: np.ndarray) -> dict[str, Any]:
    full = clip_control(ctx, vector)
    coefficients = full.reshape(35, 3)
    raw = coefficients @ ctx.modes_tsc.T
    action = np.zeros_like(raw)
    currents = np.zeros((36, 14), dtype=float)
    currents[0] = ctx.initial_currents_tsc
    scales: list[float] = []
    excess: list[float] = []
    for step in range(35):
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
        "full_control_vector": full,
        "mode_coefficients": coefficients,
        "action_raw_tsc": raw,
        "action_norm_tsc": action,
        "action_norm_display": s2.tsc_matrix_to_display(action),
        "currents_a_tsc": currents,
        "currents_a_display": s2.tsc_matrix_to_display(currents),
        "per_step_repair_scale": np.asarray(scales, dtype=float),
        "saturation_excess": np.asarray(excess, dtype=float),
    }


def target_absolute(ctx: Stage34Context, task: dict[str, Any]) -> np.ndarray:
    return np.asarray(
        [
            float(ctx.cfg["target"]["R"]) + float(task.get("R_offset_m", 0.0)),
            float(ctx.cfg["target"]["Z"]) + float(task.get("Z_offset_m", 0.0)),
            float(ctx.cfg["target"]["Ip"]) + float(task.get("Ip_offset_A", 0.0)),
        ],
        dtype=float,
    )


def _failed_metrics(reason: str, horizon: int) -> dict[str, Any]:
    return {
        "success": False,
        "failure_reason": reason,
        "n_trajectory_steps": 0,
        "stage3_4_horizon_steps": horizon,
        "stage3_4_target_tracking_pass": False,
        "stage3_4_tracking_minimum_signed_margin": -1e12,
        "stage3_4_tracking_objective": 1e12,
        "stage3_4_endpoint_evaluations": [],
        "selection_score": 1e12,
    }


def target_metrics(
    ctx: Stage34Context,
    task: dict[str, Any],
    result: dict[str, Any],
    decoded: dict[str, Any] | None,
) -> dict[str, Any]:
    if not result.get("success"):
        return _failed_metrics(str(result.get("failure_reason", "TSC failure")), horizon=max(len(result.get("trajectory", [])) - 1, 0))
    trajectory = result.get("trajectory", [])
    horizon = len(trajectory) - 1
    if horizon not in {25, 35, 37}:
        return _failed_metrics(f"unexpected trajectory horizon {horizon}", horizon=horizon)
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("successful Stage3.4 trajectory contains non-finite R/Z/Ip")
    target = target_absolute(ctx, task)
    error = y - target[None, :]
    velocity_xy = s32._velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    speed = np.linalg.norm(velocity_xy, axis=1)
    gate = ctx.cfg["gate"]
    endpoints = [step for step in map(int, gate["allowed_arrival_steps"]) if step <= horizon]
    endpoint_rows: list[dict[str, Any]] = []
    ip_cfg = gate["ip_tracking"]
    terminal_ip_abs = float(abs(error[-1, 2]))
    terminal_ip_margin = 1.0 - terminal_ip_abs / float(ip_cfg["terminal_abs_tolerance_A"])
    for endpoint in endpoints:
        hard = s32._endpoint_constraints_signed(
            error=error,
            speed=speed,
            endpoint=endpoint,
            horizon=horizon,
            tolerance=float(gate["precise_tolerance_m"]),
            endpoint_speed_limit=float(gate["terminal_velocity_max_m_per_s"]),
            rms_speed_limit=float(gate["late_velocity_rms_max_m_per_s"]),
            late_window_steps=int(gate["late_window_steps"]),
            ip_tolerance=float(gate["ip_safety_tolerance_A"]),
            streak_steps=int(gate["required_arrival_streak_steps"]),
            dt_ms=int(ctx.env_cfg["dt_ms"]),
        )
        window_start = int(hard["window_start_step"])
        hold_ip = error[window_start:, 2]
        ip_hold_rms = float(np.sqrt(np.mean(hold_ip**2)))
        ip_max = float(np.max(np.abs(hold_ip)))
        ip_margins = np.asarray(
            [
                terminal_ip_margin,
                1.0 - ip_hold_rms / float(ip_cfg["hold_rms_tolerance_A"]),
                1.0 - ip_max / float(ip_cfg["sustained_max_tolerance_A"]),
            ],
            dtype=float,
        )
        combined = np.concatenate([[float(hard["minimum_signed_margin"])], ip_margins])
        row = {
            **copy.deepcopy(hard),
            "stage3_4_ip_terminal_abs_error_A": terminal_ip_abs,
            "stage3_4_ip_hold_rms_error_A": ip_hold_rms,
            "stage3_4_ip_sustained_max_error_A": ip_max,
            "stage3_4_ip_terminal_signed_margin": float(ip_margins[0]),
            "stage3_4_ip_hold_rms_signed_margin": float(ip_margins[1]),
            "stage3_4_ip_sustained_signed_margin": float(ip_margins[2]),
            "stage3_4_ip_tracking_pass": bool(np.min(ip_margins) >= -1e-12),
            "stage3_4_target_tracking_pass": bool(hard.get("pass", False) and np.min(ip_margins) >= -1e-12),
            "stage3_4_tracking_minimum_signed_margin": float(np.min(combined)),
            "stage3_4_tracking_mean_signed_margin": float(np.mean(combined)),
        }
        endpoint_rows.append(row)
    if not endpoint_rows:
        raise RuntimeError("no Stage3.4 arrival endpoint is available for this trajectory")
    passing = [row for row in endpoint_rows if row["stage3_4_target_tracking_pass"]]
    pool = passing if passing else endpoint_rows
    chosen = max(
        pool,
        key=lambda row: (
            float(row["stage3_4_tracking_minimum_signed_margin"]),
            float(row["stage3_4_tracking_mean_signed_margin"]),
            -int(row["endpoint_step"]),
        ),
    )
    window_start = int(chosen["window_start_step"])
    hold_rz = error[window_start:, :2]
    hold_rz_rms = float(np.sqrt(np.mean(np.sum(hold_rz**2, axis=1))))
    terminal_rz = float(np.linalg.norm(error[-1, :2]))
    position_scale = float(gate["precise_tolerance_m"])
    speed_scale = float(gate["terminal_velocity_max_m_per_s"])
    ip_hold_scale = float(ip_cfg["hold_rms_tolerance_A"])
    action_rms = delta_rms = repair_rms = 0.0
    max_current_util = 0.0
    if decoded is not None:
        action = np.asarray(decoded["action_norm_tsc"], dtype=float)[:horizon]
        action_rms = float(np.sqrt(np.mean(action**2)))
        delta_rms = float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2))) if len(action) > 1 else 0.0
        repair_rms = float(np.sqrt(np.mean(np.asarray(decoded["saturation_excess"], dtype=float)[:horizon] ** 2)))
    currents = np.asarray([row["currents_a_display"] for row in trajectory], dtype=float)
    min_i = np.asarray(ctx.env_cfg["min_current_a_display_order"], dtype=float)
    max_i = np.asarray(ctx.env_cfg["max_current_a_display_order"], dtype=float)
    center_i = 0.5 * (min_i + max_i)
    half_i = np.maximum(0.5 * (max_i - min_i), 1e-9)
    max_current_util = float(np.max(np.abs((currents - center_i[None, :]) / half_i[None, :])))
    margin = float(chosen["stage3_4_tracking_minimum_signed_margin"])
    tracking_pass = bool(chosen["stage3_4_target_tracking_pass"])
    tracking_objective = float(
        -60.0 * margin
        + float(ctx.cfg["continuation"].get("center_position_weight", 4.0)) * (hold_rz_rms / position_scale) ** 2
        + 1.5 * (terminal_rz / position_scale) ** 2
        + float(ctx.cfg["continuation"].get("center_velocity_weight", 1.0))
        * (float(chosen["post_arrival_velocity_rms_m_per_s"]) / speed_scale) ** 2
        + float(ctx.cfg["continuation"].get("center_ip_weight", 0.15))
        * (float(chosen["stage3_4_ip_hold_rms_error_A"]) / ip_hold_scale) ** 2
        + 0.02 * action_rms**2
        + 0.05 * delta_rms**2
        + 2.0 * repair_rms**2
    )
    selection = tracking_objective if tracking_pass else float(
        1e6
        + 1e5 * max(-margin, 0.0)
        + 2e3 * float(chosen.get("sum_violation", 0.0))
        + tracking_objective
    )
    precise_mask = np.max(np.abs(error[:, :2]), axis=1) <= float(gate["precise_tolerance_m"])
    relaxed_mask = np.max(np.abs(error[:, :2]), axis=1) <= float(gate["relaxed_tolerance_m"])
    return {
        "success": True,
        "failure_reason": "",
        "n_trajectory_steps": len(trajectory),
        "terminal_R_error_m": float(error[-1, 0]),
        "terminal_Z_error_m": float(error[-1, 1]),
        "terminal_Ip_error_A": float(error[-1, 2]),
        "terminal_RZ_euclidean_error_m": terminal_rz,
        "terminal_RZ_box_max_error_m": float(np.max(np.abs(error[-1, :2]))),
        "terminal_velocity_m_per_s": float(speed[-1]),
        "late_velocity_rms_m_per_s": float(np.sqrt(np.mean(speed[-int(gate["late_window_steps"]):] ** 2))),
        "max_velocity_m_per_s": float(np.max(speed)),
        "max_current_utilization": max_current_util,
        "trailing_streak_within_30mm_steps": s32._trailing_streak(precise_mask),
        "trailing_streak_within_40mm_steps": s32._trailing_streak(relaxed_mask),
        "stage3_4_task_id": str(task["task_id"]),
        "stage3_4_horizon_steps": horizon,
        "stage3_4_best_endpoint_step": int(chosen["endpoint_step"]),
        "stage3_4_best_endpoint_ms": int(chosen["arrival_time_ms"]),
        "stage3_4_window_start_step": window_start,
        "stage3_4_sustained_box_max_error_m": float(chosen["sustained_box_max_error_m"]),
        "stage3_4_endpoint_velocity_m_per_s": float(chosen["endpoint_velocity_m_per_s"]),
        "stage3_4_endpoint_late_velocity_rms_m_per_s": float(chosen["endpoint_late_velocity_rms_m_per_s"]),
        "stage3_4_post_arrival_velocity_rms_m_per_s": float(chosen["post_arrival_velocity_rms_m_per_s"]),
        "stage3_4_final_velocity_m_per_s": float(chosen["final_velocity_m_per_s"]),
        "stage3_4_sustained_Ip_safety_max_error_A": float(chosen["sustained_Ip_max_error_A"]),
        "stage3_4_ip_terminal_abs_error_A": float(chosen["stage3_4_ip_terminal_abs_error_A"]),
        "stage3_4_ip_hold_rms_error_A": float(chosen["stage3_4_ip_hold_rms_error_A"]),
        "stage3_4_ip_sustained_max_error_A": float(chosen["stage3_4_ip_sustained_max_error_A"]),
        "stage3_4_ip_tracking_pass": bool(chosen["stage3_4_ip_tracking_pass"]),
        "stage3_4_target_tracking_pass": tracking_pass,
        "stage3_4_tracking_minimum_signed_margin": margin,
        "stage3_4_tracking_mean_signed_margin": float(chosen["stage3_4_tracking_mean_signed_margin"]),
        "stage3_4_hold_rz_rms_m": hold_rz_rms,
        "stage3_4_tracking_objective": tracking_objective,
        "stage3_4_endpoint_evaluations": endpoint_rows,
        "strict_gate_pass": tracking_pass,
        "relaxed_gate_pass": bool(
            float(chosen["sustained_box_max_error_m"]) <= float(gate["relaxed_tolerance_m"]) + 1e-12
            and float(chosen["endpoint_velocity_m_per_s"]) <= float(gate["terminal_velocity_max_m_per_s"]) + 1e-12
            and float(chosen["post_arrival_velocity_rms_m_per_s"]) <= float(gate["late_velocity_rms_max_m_per_s"]) + 1e-12
        ),
        "gate_label": (
            "PASS_PRECISE_HOLD_30MM_BY_270MS_THROUGH_370MS"
            if tracking_pass and horizon == 37
            else (
                "PASS_PRECISE_HOLD_30MM_BY_250MS_THROUGH_350MS"
                if tracking_pass and horizon == 35
                else ("PASS_LATE_ARRIVAL_SEED_30MM_BY_250MS" if tracking_pass else "NEAR_FEASIBLE_STAGE3_4")
            )
        ),
        "action_rms": action_rms,
        "delta_action_rms": delta_rms,
        "repair_excess_rms": repair_rms,
        "continuous_objective": tracking_objective,
        "selection_score": selection,
        "wall_time_s": float(result.get("wall_time_s", 0.0)),
    }


def task_internal_goal(ctx: Stage34Context | SimpleNamespace, task: dict[str, Any], row: dict[str, Any]) -> bool:
    if not _as_bool(row.get("stage3_4_target_tracking_pass"), False):
        return False
    goal = ctx.cfg["continuation"].get("internal_goal", {})
    if str(task.get("task_id")) == "nominal":
        box_limit = float(goal.get("nominal_box_m", 0.020))
    elif bool(task.get("final", False)):
        box_limit = float(goal.get("final_box_m", 0.025))
    else:
        box_limit = float(goal.get("support_box_m", 0.028))
    speed_limit = float(goal.get("post_arrival_velocity_rms_m_per_s", 0.070))
    return bool(
        _as_float(row.get("stage3_4_sustained_box_max_error_m"), 1e12) <= box_limit + 1e-12
        and _as_float(row.get("stage3_4_post_arrival_velocity_rms_m_per_s"), 1e12) <= speed_limit + 1e-12
    )


def task_minimum_refinement_rounds(ctx: Stage34Context | SimpleNamespace, task: dict[str, Any]) -> int:
    goal = ctx.cfg["continuation"].get("internal_goal", {})
    if str(task.get("task_id")) == "nominal":
        return int(goal.get("minimum_refinement_rounds_nominal", 2))
    if bool(task.get("final", False)):
        return int(goal.get("minimum_refinement_rounds_final", 1))
    return int(goal.get("minimum_refinement_rounds_support", 0))


def task_sort_key(row: dict[str, Any]) -> tuple[float, float, float, float, str]:
    return (
        0.0 if _as_bool(row.get("stage3_4_target_tracking_pass"), False) else 1.0,
        _as_float(row.get("stage3_4_tracking_objective"), 1e12),
        -_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12),
        _as_float(row.get("stage3_4_sustained_box_max_error_m"), 1e12),
        str(row.get("candidate_id", "")),
    )


# ---------------------------------------------------------------------------
# Global physical-trajectory cache and source seeds
# ---------------------------------------------------------------------------


def physical_spec(ctx: Stage34Context, vector: np.ndarray, physical_id: str, phase: str) -> dict[str, Any]:
    full = clip_control(ctx, vector)
    decoded = decode_control(ctx, full)
    return {
        "kind": "stage3_4_physical_trajectory",
        "experiment_id": physical_id,
        "candidate_id": physical_id,
        "phase": phase,
        "horizon_steps": 35,
        "full_control_vector": full.tolist(),
        "mode_coefficients": decoded["mode_coefficients"].tolist(),
        "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
        "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
    }


def evaluate_task_candidates(
    ctx: Stage34Context,
    rows: Sequence[dict[str, Any]],
    *,
    phase: str,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    unique: dict[str, np.ndarray] = {}
    prepared: list[dict[str, Any]] = []
    for raw in rows:
        row = copy.deepcopy(raw)
        vector = clip_control(ctx, _vector(row["full_control_vector"], 105))
        physical_id = physical_digest(vector)
        row["full_control_vector"] = vector.tolist()
        row["physical_id"] = physical_id
        row.setdefault("candidate_id", candidate_digest(str(row["task"]["task_id"]), vector, phase, row.get("source_name", "")))
        unique.setdefault(physical_id, vector)
        prepared.append(row)
    specs = [physical_spec(ctx, vector, physical_id, phase) for physical_id, vector in sorted(unique.items())]
    # Physical cache entries are keyed only by the clipped 105-D control
    # vector.  Reuse a successful cached rollout even during a fresh logical
    # phase/run command; otherwise identical controls scored for another
    # target would be needlessly sent through TSC again.
    results = s2.evaluate_specs(
        ctx.base32,
        specs,
        output_dir=ctx.paths.physical_cache / "raw",
        backend=backend,
        resume=True,
    )
    by_id = {str(result["experiment_id"]): result for result in results}
    output: list[dict[str, Any]] = []
    for row in prepared:
        vector = _vector(row["full_control_vector"], 105)
        result = by_id.get(str(row["physical_id"]))
        decoded = decode_control(ctx, vector)
        metrics = target_metrics(
            ctx,
            row["task"],
            result if result is not None else {"success": False, "failure_reason": "missing physical result"},
            decoded,
        )
        row.update(metrics)
        row["result_relpath"] = str((ctx.paths.physical_cache / "raw" / f"{row['physical_id']}.json.gz").relative_to(ctx.paths.run_dir))
        output.append(row)
    output.sort(key=task_sort_key)
    for rank, row in enumerate(output, 1):
        row["phase_rank"] = rank
    return output


def load_physical_result(ctx: Stage34Context, row: dict[str, Any]) -> dict[str, Any]:
    relative = str(row.get("result_relpath", "")).strip()
    if relative:
        path = ctx.paths.run_dir / relative
    else:
        path = ctx.paths.physical_cache / "raw" / f"{row['physical_id']}.json.gz"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json_gz(path)


def source_entry_result(ctx: Stage34Context, entry: dict[str, Any]) -> dict[str, Any]:
    relative = str(entry.get("result_relpath", "")).strip()
    if not relative:
        raise FileNotFoundError(f"source entry {entry.get('candidate_id')} has no result_relpath")
    path = ctx.source_stage33_run / relative
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json_gz(path)


def source_seed_catalog(ctx: Stage34Context) -> list[dict[str, Any]]:
    path = ctx.paths.source_reference / "late_arrival_source_seed_catalog.json"
    if path.exists():
        payload = read_json(path)
        if isinstance(payload, list):
            return payload
    rows: list[dict[str, Any]] = []
    for task in ctx.tasks:
        source_id = task.get("source_task_id")
        if not source_id or source_id not in ctx.source_entries:
            continue
        entry = copy.deepcopy(ctx.source_entries[source_id])
        result = source_entry_result(ctx, entry)
        vector75 = _vector(entry["full_control_vector"], 75)
        fake = np.concatenate([vector75, np.tile(vector75.reshape(25, 3)[-1], 10)])
        decoded = decode_control(ctx, fake)
        metrics = target_metrics(ctx, task, result, decoded)
        rows.append(
            {
                "task": copy.deepcopy(task),
                "source_candidate_id": entry["candidate_id"],
                "source_result_relpath": entry["result_relpath"],
                "source_control_vector_25": vector75.tolist(),
                **metrics,
            }
        )
    atomic_write_json(path, rows)
    write_csv(ctx.paths.source_reference / "late_arrival_source_seed_catalog.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# Continuation seeds and target-specific warm starts
# ---------------------------------------------------------------------------


def extend_25_to_35(ctx: Stage34Context, vector75: np.ndarray, template: str) -> np.ndarray:
    first = _vector(vector75, 75).reshape(25, 3)
    last = first[-1]
    previous = first[-2]
    tail = np.zeros((10, 3), dtype=float)
    if template == "hold_last":
        tail[:] = last
    elif template == "zero":
        tail[:] = 0.0
    elif template == "linear_zero":
        for index in range(10):
            tail[index] = last * max(1.0 - (index + 1) / 6.0, 0.0)
    elif template == "exp_decay":
        for index in range(10):
            tail[index] = last * (0.78 ** (index + 1))
    elif template == "slope_decay":
        slope = last - previous
        current = last.copy()
        for index in range(10):
            current = current + slope * (0.70 ** (index + 1))
            tail[index] = current * (0.90 ** (index + 1))
    elif template in {"mode1_positive", "mode1_negative", "mode2_positive", "mode2_negative"}:
        sign = 1.0 if template.endswith("positive") else -1.0
        mode = 0 if template.startswith("mode1") else 1
        tail[:] = last
        pulse = np.asarray([math.sin(math.pi * (index + 1) / 11.0) for index in range(10)], dtype=float)
        tail[:, mode] += sign * 0.10 * pulse
        tail *= np.linspace(0.95, 0.70, 10)[:, None]
    else:
        raise ValueError(f"unknown tail template {template!r}")
    full = np.vstack([first, tail]).reshape(-1)
    return clip_control(ctx, full)


def source_jacobian_correction(
    ctx: Stage34Context,
    *,
    parent_task: dict[str, Any],
    child_task: dict[str, Any],
) -> np.ndarray:
    try:
        from scipy.optimize import lsq_linear
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage3.4 continuation warm starts") from exc
    jacobian = np.asarray(ctx.source_bundle["jacobian_physical_units"], dtype=float)
    delta_target = target_absolute(ctx, child_task) - target_absolute(ctx, parent_task)
    desired = np.concatenate(
        [
            np.full(25, delta_target[0]),
            np.full(25, delta_target[1]),
            np.zeros(25),
            np.zeros(25),
            np.full(25, delta_target[2]),
        ]
    )
    states = list(map(int, ctx.cfg["continuation"]["source_tracking_states"]))
    rows: list[int] = []
    for block in range(5):
        rows.extend([block * 25 + state - 1 for state in states])
    selected = np.asarray(rows, dtype=int)
    scales = np.concatenate(
        [
            np.full(25, 0.03),
            np.full(25, 0.03),
            np.full(25, 0.10),
            np.full(25, 0.10),
            np.full(25, 2000.0),
        ]
    )
    a = jacobian[selected] / scales[selected, None]
    b = desired[selected] / scales[selected]
    radius_mode = np.asarray(ctx.cfg["continuation"]["source_control_radius_by_mode"], dtype=float)
    radius = np.tile(radius_mode, 25)
    ridge = 0.06
    smooth = 0.05
    augmented_a = [a, math.sqrt(ridge) * np.diag(1.0 / np.maximum(radius, 1e-9))]
    augmented_b = [b, np.zeros(75)]
    if smooth > 0.0:
        difference = s33._difference_matrix(25)
        augmented_a.append(math.sqrt(smooth) * difference)
        augmented_b.append(np.zeros(difference.shape[0]))
    result = lsq_linear(
        np.vstack(augmented_a),
        np.concatenate(augmented_b),
        bounds=(-radius, radius),
        method="trf",
        tol=1e-9,
        max_iter=500,
        lsmr_tol="auto",
    )
    return np.asarray(result.x, dtype=float)


def _task_dir(ctx: Stage34Context, task: dict[str, Any]) -> Path:
    safe = str(task["task_id"]).replace("/", "_")
    return ctx.paths.task_root / f"{int(task['task_index']):02d}_{safe}"


def _task_summary_path(ctx: Stage34Context, task: dict[str, Any]) -> Path:
    return _task_dir(ctx, task) / "task_summary.json"


def load_completed_task_best(ctx: Stage34Context, task_id: str) -> dict[str, Any] | None:
    task = ctx.task_map[task_id]
    path = _task_summary_path(ctx, task)
    if not path.exists():
        return None
    payload = read_json(path)
    best = payload.get("best")
    return copy.deepcopy(best) if isinstance(best, dict) else None


def initial_candidates_for_task(ctx: Stage34Context, task: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    templates = [str(item) for item in ctx.cfg["continuation"]["tail_templates"]]
    source_id = task.get("source_task_id")
    if source_id and source_id in ctx.source_entries:
        entry = ctx.source_entries[source_id]
        vector75 = _vector(entry["full_control_vector"], 75)
        for template in templates:
            full = extend_25_to_35(ctx, vector75, template)
            candidates.append(
                {
                    "task": copy.deepcopy(task),
                    "candidate_id": candidate_digest(task["task_id"], full, "source", template),
                    "full_control_vector": full.tolist(),
                    "source_type": "stage3_3_source_extension",
                    "source_name": f"{source_id}_{template}",
                    "parent_candidate_id": str(entry["candidate_id"]),
                    "tail_template": template,
                }
            )
    parent_rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for parent_id in task.get("parents", []):
        best = load_completed_task_best(ctx, parent_id)
        if best is not None:
            parent_rows.append((ctx.task_map[parent_id], best))
    parent_rows.sort(key=lambda item: task_sort_key(item[1]))
    for parent_task, parent in parent_rows[:3]:
        parent_vector = _vector(parent["full_control_vector"], 105)
        candidates.append(
            {
                "task": copy.deepcopy(task),
                "candidate_id": candidate_digest(task["task_id"], parent_vector, "parent_identity", parent_task["task_id"]),
                "full_control_vector": parent_vector.tolist(),
                "source_type": "continuation_parent_identity",
                "source_name": f"parent_{parent_task['task_id']}",
                "parent_candidate_id": str(parent["candidate_id"]),
            }
        )
        correction = source_jacobian_correction(ctx, parent_task=parent_task, child_task=task)
        scales = [float(value) for value in ctx.cfg["continuation"]["feedforward_scales"]]
        for scale in scales:
            full = parent_vector.copy()
            first = full[:75] + scale * correction
            full[:75] = first
            full = clip_control(ctx, full)
            candidates.append(
                {
                    "task": copy.deepcopy(task),
                    "candidate_id": candidate_digest(task["task_id"], full, "parent_ff", parent_task["task_id"], scale),
                    "full_control_vector": full.tolist(),
                    "source_type": "continuation_source_jacobian_feedforward",
                    "source_name": f"parent_{parent_task['task_id']}_ff_{scale:g}",
                    "parent_candidate_id": str(parent["candidate_id"]),
                    "feedforward_scale": scale,
                }
            )
    # If no explicit parent is available, nominal is always a safe fallback.
    if not candidates and task["task_id"] != "nominal":
        nominal = load_completed_task_best(ctx, "nominal")
        if nominal is not None:
            full = _vector(nominal["full_control_vector"], 105)
            candidates.append(
                {
                    "task": copy.deepcopy(task),
                    "candidate_id": candidate_digest(task["task_id"], full, "nominal_fallback"),
                    "full_control_vector": full.tolist(),
                    "source_type": "nominal_fallback",
                    "source_name": "nominal_fallback",
                    "parent_candidate_id": str(nominal["candidate_id"]),
                }
            )
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in candidates:
        key = (str(row["task"]["task_id"]), physical_digest(_vector(row["full_control_vector"], 105)))
        dedup.setdefault(key, row)
    return list(dedup.values())


# ---------------------------------------------------------------------------
# Real-TSC reduced continuation refinement
# ---------------------------------------------------------------------------


def temporal_reduced_basis(ctx: Stage34Context) -> np.ndarray:
    cfg = ctx.cfg["refinement"]
    centers = np.asarray(cfg["temporal_centers"], dtype=float)
    widths = np.asarray(cfg["temporal_widths"], dtype=float)
    if centers.shape != widths.shape or len(centers) != 5:
        raise ValueError("refinement temporal centers/widths must each have five values")
    time_index = np.arange(35, dtype=float)
    profiles = [np.exp(-0.5 * ((time_index - center) / width) ** 2) for center, width in zip(centers, widths)]
    if bool(cfg.get("include_global_mode_directions", True)):
        profiles.append(np.ones(35, dtype=float))
    matrix = np.stack(profiles, axis=1)
    q, _ = np.linalg.qr(matrix)
    temporal = q[:, :6]
    columns: list[np.ndarray] = []
    for mode in range(3):
        for index in range(temporal.shape[1]):
            column = np.zeros((35, 3), dtype=float)
            column[:, mode] = temporal[:, index]
            columns.append(column.reshape(-1))
    basis = np.stack(columns, axis=1)
    expected = int(cfg.get("basis_rank", 18))
    if basis.shape != (105, expected) or np.linalg.matrix_rank(basis) != expected:
        raise RuntimeError(f"invalid Stage3.4 reduced basis shape/rank: {basis.shape}")
    return basis


def _coordinate_room(
    center: np.ndarray,
    direction: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    sign: float,
) -> float:
    signed = sign * np.asarray(direction, dtype=float)
    rooms: list[float] = []
    for index, component in enumerate(signed):
        if component > 1e-14:
            rooms.append(float((upper[index] - center[index]) / component))
        elif component < -1e-14:
            rooms.append(float((lower[index] - center[index]) / component))
    return max(0.0, min(rooms)) if rooms else 0.0


def _probe_coordinates(
    center: np.ndarray,
    direction: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    requested: float,
    bound_margin: float,
    minimum: float,
) -> list[float]:
    pos = min(requested, bound_margin * _coordinate_room(center, direction, lower, upper, +1.0))
    neg = min(requested, bound_margin * _coordinate_room(center, direction, lower, upper, -1.0))
    coordinates: list[float] = []
    if pos >= minimum:
        coordinates.append(pos)
    if neg >= minimum:
        coordinates.append(-neg)
    if len(coordinates) >= 2:
        return coordinates
    # At a boundary, use two inward secant points rather than a zero-length probe.
    room = pos if pos >= minimum else neg
    sign = 1.0 if pos >= minimum else -1.0
    if room >= minimum:
        coordinates = [sign * room, sign * max(0.5 * room, minimum)]
    return list(dict.fromkeys(float(value) for value in coordinates if abs(value) >= minimum))


def feature_from_result(ctx: Stage34Context, task: dict[str, Any], result: dict[str, Any]) -> np.ndarray:
    trajectory = result.get("trajectory", [])
    if not result.get("success") or len(trajectory) != 36:
        raise ValueError("Stage3.4 feature requires a successful 35-step trajectory")
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    velocity = s32._velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    target = target_absolute(ctx, task)
    error = y - target[None, :]
    return np.concatenate([error[1:, 0], error[1:, 1], velocity[1:, 0], velocity[1:, 1], error[1:, 2]])


def absolute_feature_from_result(ctx: Stage34Context, result: dict[str, Any]) -> np.ndarray:
    trajectory = result.get("trajectory", [])
    if not result.get("success") or len(trajectory) != 36:
        raise ValueError("Stage3.4 absolute feature requires a successful 35-step trajectory")
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    velocity = s32._velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    return np.concatenate([y[1:, 0], y[1:, 1], velocity[1:, 0], velocity[1:, 1], y[1:, 2]])


def feature_scales(ctx: Stage34Context) -> np.ndarray:
    cfg = ctx.cfg["identification"]["output_scales"]
    return np.concatenate(
        [
            np.full(35, float(cfg["R_m"])),
            np.full(35, float(cfg["Z_m"])),
            np.full(35, float(cfg["vR_m_per_s"])),
            np.full(35, float(cfg["vZ_m_per_s"])),
            np.full(35, float(cfg["Ip_A"])),
        ]
    )


def source_prior_jacobian(ctx: Stage34Context) -> np.ndarray:
    prior = np.zeros((175, 105), dtype=float)
    source = np.asarray(ctx.source_bundle["jacobian_physical_units"], dtype=float)
    prior[:25, :75] = source[:25]
    prior[35:60, :75] = source[25:50]
    prior[70:95, :75] = source[50:75]
    prior[105:130, :75] = source[75:100]
    prior[140:165, :75] = source[100:125]
    return prior


def build_probe_rows(
    ctx: Stage34Context,
    task: dict[str, Any],
    center: dict[str, Any],
    *,
    round_index: int,
    trust_radius: float,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    basis = temporal_reduced_basis(ctx)
    center_vector = _vector(center["full_control_vector"], 105)
    lower_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    lower = np.tile(lower_mode, 35)
    upper = np.tile(upper_mode, 35)
    cfg = ctx.cfg["refinement"]
    requested = float(trust_radius) * float(cfg.get("probe_fraction_of_trust", 0.65))
    rows: list[dict[str, Any]] = []
    for direction_index in range(basis.shape[1]):
        direction = basis[:, direction_index]
        coordinates = _probe_coordinates(
            center_vector,
            direction,
            lower,
            upper,
            requested,
            float(cfg.get("probe_bound_margin", 0.95)),
            float(cfg.get("minimum_probe_coordinate", 1e-4)),
        )
        for slot, coordinate in enumerate(coordinates):
            full = center_vector + coordinate * direction
            full = clip_control(ctx, full)
            rows.append(
                {
                    "task": copy.deepcopy(task),
                    "candidate_id": candidate_digest(task["task_id"], full, "probe", round_index, direction_index, slot),
                    "full_control_vector": full.tolist(),
                    "source_type": "stage3_4_reduced_real_tsc_probe",
                    "source_name": f"basis_{direction_index:02d}_{slot}",
                    "parent_candidate_id": str(center["candidate_id"]),
                    "probe_round": round_index,
                    "probe_direction_index": direction_index,
                    "probe_coordinate": float(coordinate),
                }
            )
    return basis, rows


def fit_reduced_model(
    ctx: Stage34Context,
    task: dict[str, Any],
    center: dict[str, Any],
    center_result: dict[str, Any],
    basis: np.ndarray,
    probe_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    center_feature = feature_from_result(ctx, task, center_result)
    rank = basis.shape[1]
    jacobian = np.zeros((175, rank), dtype=float)
    curvature = np.zeros((175, rank), dtype=float)
    confidence = np.zeros(rank, dtype=float)
    prior_reduced = source_prior_jacobian(ctx) @ basis
    scales = feature_scales(ctx)
    for direction_index in range(rank):
        group = [row for row in probe_rows if _as_int(row.get("probe_direction_index"), -1) == direction_index and row.get("success")]
        x_values: list[float] = []
        deltas: list[np.ndarray] = []
        for row in group:
            result = load_physical_result(ctx, row)
            x_values.append(float(row["probe_coordinate"]))
            deltas.append(feature_from_result(ctx, task, result) - center_feature)
        if not x_values:
            jacobian[:, direction_index] = prior_reduced[:, direction_index]
            confidence[direction_index] = 0.0
            continue
        x = np.asarray(x_values, dtype=float)
        y = np.stack(deltas, axis=0)
        if len(x) >= 2:
            design = np.column_stack([x, x**2])
            coefficient, *_ = np.linalg.lstsq(design, y, rcond=None)
            measured = coefficient[0]
            curvature[:, direction_index] = coefficient[1]
            prediction = design @ coefficient
            residual_ratio = float(np.linalg.norm((y - prediction) / scales[None, :]) / max(np.linalg.norm(y / scales[None, :]), 1e-12))
        else:
            measured = y[0] / x[0]
            residual_ratio = 0.5
        signal = float(np.linalg.norm((np.mean(np.abs(x)) * measured) / scales))
        conf = float(np.clip((1.0 - residual_ratio) * min(signal / 0.02, 1.0), 0.0, 1.0))
        blend_floor = float(ctx.cfg["refinement"].get("source_prior_blend", 0.20))
        measured_weight = max(conf, 1.0 - blend_floor)
        prior = prior_reduced[:, direction_index]
        if np.linalg.norm(prior / scales) < 1e-12:
            measured_weight = 1.0
        jacobian[:, direction_index] = measured_weight * measured + (1.0 - measured_weight) * prior
        confidence[direction_index] = conf
    return {
        "center_candidate_id": str(center["candidate_id"]),
        "center_feature": center_feature.tolist(),
        "basis": basis.tolist(),
        "jacobian": jacobian.tolist(),
        "curvature": curvature.tolist(),
        "direction_confidence": confidence.tolist(),
        "usable_directions": int(np.sum(np.linalg.norm(jacobian, axis=0) > 1e-12)),
    }


def _profile_weights(ctx: Stage34Context, profile: str) -> np.ndarray:
    profile_cfg = ctx.cfg["refinement"]["profiles"][profile]
    block = np.asarray(
        [profile_cfg["R"], profile_cfg["Z"], profile_cfg["vR"], profile_cfg["vZ"], profile_cfg["Ip"]],
        dtype=float,
    )
    weights = np.zeros(175, dtype=float)
    start = int(ctx.cfg["refinement"].get("state_weight_start", 8))
    hold_start = int(ctx.cfg["refinement"].get("hold_weight_start", 14))
    hold_multiplier = float(ctx.cfg["refinement"].get("hold_weight_multiplier", 2.5))
    for block_index in range(5):
        for state in range(1, 36):
            weight = block[block_index]
            if state < start:
                weight *= 0.15
            elif state >= hold_start:
                weight *= hold_multiplier
            weights[block_index * 35 + state - 1] = weight
    return weights


def solve_reduced_step(
    ctx: Stage34Context,
    center: dict[str, Any],
    model: dict[str, Any],
    *,
    profile: str,
    trust_radius: float,
) -> dict[str, Any]:
    try:
        from scipy.optimize import Bounds, LinearConstraint, minimize
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage3.4 reduced refinement") from exc
    center_vector = _vector(center["full_control_vector"], 105)
    center_feature = np.asarray(model["center_feature"], dtype=float)
    basis = np.asarray(model["basis"], dtype=float)
    jacobian = np.asarray(model["jacobian"], dtype=float)
    scales = feature_scales(ctx)
    weights = _profile_weights(ctx, profile)
    normalized_center = center_feature / scales
    normalized_jacobian = jacobian / scales[:, None]
    lower_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    lower_control = np.tile(lower_mode, 35) - center_vector
    upper_control = np.tile(upper_mode, 35) - center_vector
    radius = float(trust_radius)
    ridge = float(ctx.cfg["refinement"].get("ridge_lambda", 0.06))

    def objective(z: np.ndarray) -> float:
        residual = normalized_center + normalized_jacobian @ z
        return float(np.sum(weights * residual**2) + ridge * np.sum((z / max(radius, 1e-9)) ** 2))

    constraint = LinearConstraint(basis, lower_control, upper_control)
    result = minimize(
        objective,
        np.zeros(basis.shape[1], dtype=float),
        method="SLSQP",
        bounds=Bounds(-np.full(basis.shape[1], radius), np.full(basis.shape[1], radius)),
        constraints=[constraint],
        options={"maxiter": 500, "ftol": 1e-10, "disp": False},
    )
    z = np.asarray(result.x, dtype=float)
    return {
        "coordinate": z,
        "solver_success": bool(result.success),
        "solver_status": int(result.status),
        "solver_message": str(result.message),
        "solver_objective": float(result.fun),
        "boundary_fraction": float(np.max(np.abs(z)) / max(radius, 1e-12)),
    }


def build_proposal_rows(
    ctx: Stage34Context,
    task: dict[str, Any],
    center: dict[str, Any],
    model: dict[str, Any],
    *,
    round_index: int,
    trust_radius: float,
) -> list[dict[str, Any]]:
    basis = np.asarray(model["basis"], dtype=float)
    center_vector = _vector(center["full_control_vector"], 105)
    rows: list[dict[str, Any]] = []
    for profile in ctx.cfg["refinement"]["profiles"]:
        solved = solve_reduced_step(ctx, center, model, profile=profile, trust_radius=trust_radius)
        coordinate = np.asarray(solved["coordinate"], dtype=float)
        for scale in map(float, ctx.cfg["refinement"]["proposal_step_scales"]):
            full = clip_control(ctx, center_vector + scale * (basis @ coordinate))
            rows.append(
                {
                    "task": copy.deepcopy(task),
                    "candidate_id": candidate_digest(task["task_id"], full, "proposal", round_index, profile, scale),
                    "full_control_vector": full.tolist(),
                    "source_type": "stage3_4_reduced_real_tsc_step",
                    "source_name": f"{profile}_scale_{scale:g}",
                    "parent_candidate_id": str(center["candidate_id"]),
                    "refinement_round": round_index,
                    "proposal_profile": profile,
                    "proposal_step_scale": scale,
                    "proposal_coordinate": (scale * coordinate).tolist(),
                    "solver_success": solved["solver_success"],
                    "solver_status": solved["solver_status"],
                    "solver_message": solved["solver_message"],
                    "solver_objective": solved["solver_objective"],
                    "trust_boundary_fraction": solved["boundary_fraction"],
                }
            )
    return rows


def run_task(
    ctx: Stage34Context,
    task: dict[str, Any],
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    task_dir = _task_dir(ctx, task)
    task_dir.mkdir(parents=True, exist_ok=True)
    summary_path = _task_summary_path(ctx, task)
    if resume and summary_path.exists():
        summary = read_json(summary_path)
        if bool(summary.get("finished", False)):
            return summary
    initial_manifest_path = task_dir / "initial_manifest.json"
    initial_results_path = task_dir / "initial_results.json"
    if not initial_manifest_path.exists():
        initial_rows = initial_candidates_for_task(ctx, task)
        if not initial_rows:
            raise RuntimeError(f"no initial candidate can be built for task {task['task_id']}")
        atomic_write_json(initial_manifest_path, {"task": task, "candidates": initial_rows})
    else:
        initial_rows = read_json(initial_manifest_path)["candidates"]
    if not initial_results_path.exists() or not resume:
        initial_results = evaluate_task_candidates(ctx, initial_rows, phase=f"task_{task['task_id']}_initial", backend=backend, resume=resume)
        atomic_write_json(initial_results_path, initial_results)
        write_csv(task_dir / "initial_results.csv", initial_results)
    else:
        initial_results = read_json(initial_results_path)
    all_rows = list(initial_results)
    best = min(all_rows, key=task_sort_key)
    trust = float(ctx.cfg["refinement"].get("initial_trust_radius", 0.30))
    no_improvement = 0
    rounds: list[dict[str, Any]] = []
    maximum_rounds = int(ctx.cfg["refinement"].get("max_rounds_per_task", 5))
    minimum_rounds = task_minimum_refinement_rounds(ctx, task)
    for round_index in range(maximum_rounds):
        if round_index >= minimum_rounds and task_internal_goal(ctx, task, best):
            break
        round_dir = task_dir / f"round_{round_index:03d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        probe_manifest_path = round_dir / "probe_manifest.json"
        probe_results_path = round_dir / "probe_results.json"
        model_path = round_dir / "reduced_model.json"
        proposal_manifest_path = round_dir / "proposal_manifest.json"
        proposal_results_path = round_dir / "proposal_results.json"
        if not probe_manifest_path.exists():
            basis, probe_rows = build_probe_rows(ctx, task, best, round_index=round_index, trust_radius=trust)
            atomic_write_json(
                probe_manifest_path,
                {"task": task, "center": best, "trust_radius": trust, "basis": basis.tolist(), "candidates": probe_rows},
            )
        probe_manifest = read_json(probe_manifest_path)
        basis = np.asarray(probe_manifest["basis"], dtype=float)
        probe_rows = probe_manifest["candidates"]
        if not probe_results_path.exists() or not resume:
            probe_results = evaluate_task_candidates(ctx, probe_rows, phase=f"task_{task['task_id']}_round_{round_index}_probes", backend=backend, resume=resume)
            atomic_write_json(probe_results_path, probe_results)
            write_csv(round_dir / "probe_results.csv", probe_results)
        else:
            probe_results = read_json(probe_results_path)
        if not model_path.exists() or not resume:
            center_result = load_physical_result(ctx, best)
            model = fit_reduced_model(ctx, task, best, center_result, basis, probe_results)
            atomic_write_json(model_path, model)
        else:
            model = read_json(model_path)
        if not proposal_manifest_path.exists():
            proposal_rows = build_proposal_rows(ctx, task, best, model, round_index=round_index, trust_radius=trust)
            atomic_write_json(proposal_manifest_path, {"task": task, "center": best, "trust_radius": trust, "candidates": proposal_rows})
        else:
            proposal_rows = read_json(proposal_manifest_path)["candidates"]
        if not proposal_results_path.exists() or not resume:
            proposal_results = evaluate_task_candidates(ctx, proposal_rows, phase=f"task_{task['task_id']}_round_{round_index}_proposals", backend=backend, resume=resume)
            atomic_write_json(proposal_results_path, proposal_results)
            write_csv(round_dir / "proposal_results.csv", proposal_results)
        else:
            proposal_results = read_json(proposal_results_path)
        all_rows.extend(probe_results)
        all_rows.extend(proposal_results)
        candidate_best = min([best, *probe_results, *proposal_results], key=task_sort_key)
        old_margin = _as_float(best.get("stage3_4_tracking_minimum_signed_margin"), -1e12)
        new_margin = _as_float(candidate_best.get("stage3_4_tracking_minimum_signed_margin"), -1e12)
        improvement = new_margin - old_margin
        if task_sort_key(candidate_best) < task_sort_key(best):
            best = copy.deepcopy(candidate_best)
        if improvement >= float(ctx.cfg["refinement"].get("minimum_margin_improvement", 0.0015)):
            trust = min(
                float(ctx.cfg["refinement"].get("maximum_trust_radius", 1.20)),
                trust * float(ctx.cfg["refinement"].get("trust_expand", 1.25)),
            )
            no_improvement = 0
            trust_action = "expand"
        else:
            trust = max(
                float(ctx.cfg["refinement"].get("minimum_trust_radius", 0.05)),
                trust * float(ctx.cfg["refinement"].get("trust_shrink", 0.60)),
            )
            no_improvement += 1
            trust_action = "shrink"
        round_summary = {
            "round": round_index,
            "probe_success": int(sum(_as_bool(row.get("success")) for row in probe_results)),
            "proposal_success": int(sum(_as_bool(row.get("success")) for row in proposal_results)),
            "old_margin": old_margin,
            "new_margin": new_margin,
            "margin_improvement": improvement,
            "trust_action": trust_action,
            "next_trust_radius": trust,
            "best": best,
        }
        atomic_write_json(round_dir / "round_summary.json", round_summary)
        rounds.append(round_summary)
        if (round_index + 1) >= minimum_rounds and task_internal_goal(ctx, task, best):
            break
        if no_improvement >= int(ctx.cfg["refinement"].get("no_improvement_patience", 2)):
            break
    all_rows.sort(key=task_sort_key)
    atomic_write_json(task_dir / "all_task_results.json", all_rows)
    write_csv(task_dir / "all_task_results.csv", all_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "task": task,
        "finished": True,
        "tracking_pass": bool(best.get("stage3_4_target_tracking_pass", False)),
        "internal_goal_pass": task_internal_goal(ctx, task, best),
        "minimum_refinement_rounds": minimum_rounds,
        "best": best,
        "rounds": rounds,
        "n_candidates": len(all_rows),
        "n_unique_physical_vectors": len({str(row.get("physical_id", "")) for row in all_rows if row.get("physical_id")}),
        "stop_reason": (
            "internal_margin_goal"
            if task_internal_goal(ctx, task, best)
            else (
                "no_improvement_patience"
                if no_improvement >= int(ctx.cfg["refinement"].get("no_improvement_patience", 2))
                else ("hard_gate_pass_without_internal_margin" if bool(best.get("stage3_4_target_tracking_pass", False)) else "max_rounds")
            )
        ),
    }
    atomic_write_json(summary_path, summary)
    return summary


def run_continuation(ctx: Stage34Context, *, backend: str, resume: bool) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    for task in ctx.tasks:
        summary = run_task(ctx, task, backend=backend, resume=resume)
        summaries.append(summary)
        print(
            json.dumps(
                {
                    "stage": STAGE,
                    "phase": "target_continuation",
                    "task_id": task["task_id"],
                    "tracking_pass": summary["tracking_pass"],
                    "internal_goal_pass": summary.get("internal_goal_pass", False),
                    "arrival_ms": summary["best"].get("stage3_4_best_endpoint_ms"),
                    "sustained_box_m": summary["best"].get("stage3_4_sustained_box_max_error_m"),
                    "signed_margin": summary["best"].get("stage3_4_tracking_minimum_signed_margin"),
                },
                indent=2,
            ),
            flush=True,
        )
    final = [row for row in summaries if row["task"]["final"]]
    mandatory = [row for row in final if row["task"]["mandatory"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "n_tasks": len(summaries),
        "n_tasks_pass": int(sum(bool(row["tracking_pass"]) for row in summaries)),
        "n_final_tasks": len(final),
        "n_final_pass": int(sum(bool(row["tracking_pass"]) for row in final)),
        "n_mandatory": len(mandatory),
        "n_mandatory_pass": int(sum(bool(row["tracking_pass"]) for row in mandatory)),
        "mandatory_complete": bool(mandatory and all(bool(row["tracking_pass"]) for row in mandatory)),
        "task_summaries": summaries,
    }


# ---------------------------------------------------------------------------
# Target library, deterministic confirmation, and full-horizon identification
# ---------------------------------------------------------------------------


def materialize_library(ctx: Stage34Context) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    final_entries: list[dict[str, Any]] = []
    for task in ctx.tasks:
        summary_path = _task_summary_path(ctx, task)
        if not summary_path.exists():
            continue
        summary = read_json(summary_path)
        best = copy.deepcopy(summary["best"])
        if not _as_bool(best.get("stage3_4_target_tracking_pass"), False):
            if task["final"]:
                final_entries.append(best)
            continue
        result = load_physical_result(ctx, best)
        y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]], dtype=float)
        velocity = s32._velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
        best["nominal_trajectory_RZI"] = y.tolist()
        best["nominal_velocity_RZ"] = velocity.tolist()
        best["library_support"] = not bool(task["final"])
        entries.append(best)
        if task["final"]:
            final_entries.append(best)
    mandatory = [row for row in final_entries if bool(row["task"]["mandatory"])]
    library = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "base_target": copy.deepcopy(ctx.cfg["target"]),
        "horizon_steps": 35,
        "latest_allowed_arrival_ms": 250,
        "hold_through_ms": 350,
        "entries": entries,
        "final_entries": final_entries,
        "n_entries": len(entries),
        "n_final_entries": len(final_entries),
        "n_mandatory": len(mandatory),
        "n_mandatory_pass": int(sum(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in mandatory)),
        "mandatory_complete": bool(mandatory and all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in mandatory)),
    }
    atomic_write_json(ctx.paths.library / "target_library.json", library)
    write_csv(ctx.paths.library / "target_library.csv", entries)
    return library


def _confirmation_spec(ctx: Stage34Context, row: dict[str, Any], repeat: int, prefix: str) -> dict[str, Any]:
    vector = _vector(row["full_control_vector"], 105)
    decoded = decode_control(ctx, vector)
    experiment_id = candidate_digest(str(row["task"]["task_id"]), vector, prefix, repeat, prefix=f"s34{prefix}")
    return {
        "kind": "stage3_4_confirmation",
        "experiment_id": experiment_id,
        "candidate_id": str(row["candidate_id"]),
        "task": copy.deepcopy(row["task"]),
        "repeat": int(repeat),
        "horizon_steps": 35,
        "full_control_vector": vector.tolist(),
        "mode_coefficients": decoded["mode_coefficients"].tolist(),
        "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
        "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
    }


def run_library_confirmation(ctx: Stage34Context, *, backend: str, resume: bool) -> dict[str, Any]:
    library = read_json(ctx.paths.library / "target_library.json") if (ctx.paths.library / "target_library.json").exists() else materialize_library(ctx)
    final_entries = [row for row in library.get("final_entries", []) if _as_bool(row.get("stage3_4_target_tracking_pass"), False)]
    repeats = int(ctx.cfg["confirmation"]["library_repeats_per_mandatory"])
    specs: list[dict[str, Any]] = []
    for row in final_entries:
        count = repeats if bool(row["task"]["mandatory"]) else 1
        specs.extend(_confirmation_spec(ctx, row, repeat, "libconf") for repeat in range(count))
    output_dir = ctx.paths.library / "confirmation_raw"
    results = s2.evaluate_specs(ctx.base32, specs, output_dir=output_dir, backend=backend, resume=resume)
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    entry_by_id = {str(row["candidate_id"]): row for row in final_entries}
    for result in results:
        spec = result["spec"]
        entry = entry_by_id[str(spec["candidate_id"])]
        metrics = target_metrics(ctx, entry["task"], result, decode_control(ctx, _vector(entry["full_control_vector"], 105)))
        row = {
            "experiment_id": result["experiment_id"],
            "candidate_id": entry["candidate_id"],
            "task_id": entry["task"]["task_id"],
            "mandatory": bool(entry["task"]["mandatory"]),
            "repeat": int(spec["repeat"]),
            **metrics,
        }
        rows.append(row)
        by_candidate.setdefault(str(entry["candidate_id"]), []).append(row)
    task_summaries: list[dict[str, Any]] = []
    for task in [row for row in ctx.tasks if row["final"]]:
        entry = next((row for row in final_entries if row["task"]["task_id"] == task["task_id"]), None)
        repeats_rows = [] if entry is None else by_candidate.get(str(entry["candidate_id"]), [])
        task_summaries.append(
            {
                "task_id": task["task_id"],
                "mandatory": bool(task["mandatory"]),
                "candidate_id": None if entry is None else entry["candidate_id"],
                "repeats": len(repeats_rows),
                "successful_repeats": int(sum(_as_bool(row.get("success")) for row in repeats_rows)),
                "all_repeats_tracking_pass": bool(repeats_rows and all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in repeats_rows)),
                "worst_tracking_signed_margin": None if not repeats_rows else min(_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in repeats_rows),
                "worst_sustained_box_m": None if not repeats_rows else max(_as_float(row.get("stage3_4_sustained_box_max_error_m"), 1e12) for row in repeats_rows),
            }
        )
    mandatory_rows = [row for row in task_summaries if row["mandatory"]]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "n_rollouts": len(rows),
        "n_successful": int(sum(_as_bool(row.get("success")) for row in rows)),
        "mandatory_all_confirmed": bool(mandatory_rows and all(row["all_repeats_tracking_pass"] for row in mandatory_rows)),
        "task_summaries": task_summaries,
    }
    atomic_write_json(ctx.paths.library / "target_library_confirmation_results.json", rows)
    write_csv(ctx.paths.library / "target_library_confirmation_results.csv", rows)
    atomic_write_json(ctx.paths.library / "target_library_confirmation_summary.json", summary)
    library["confirmation"] = summary
    library["mandatory_confirmed"] = summary["mandatory_all_confirmed"]
    atomic_write_json(ctx.paths.library / "target_library.json", library)
    return summary


def identification_feature_names() -> list[str]:
    names: list[str] = []
    for label in ("R", "Z", "vR", "vZ", "Ip"):
        names.extend([f"{label}_state_{state:02d}" for state in range(1, 36)])
    return names


def build_identification_probe_rows(ctx: Stage34Context, center: dict[str, Any]) -> list[dict[str, Any]]:
    center_vector = _vector(center["full_control_vector"], 105)
    lower = np.tile(np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float), 35)
    upper = np.tile(np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float), 35)
    delta_mode = np.asarray(ctx.cfg["identification"]["probe_delta_by_mode"], dtype=float)
    rows: list[dict[str, Any]] = []
    for variable in range(105):
        requested = float(delta_mode[variable % 3])
        positive = min(requested, 0.95 * max(upper[variable] - center_vector[variable], 0.0))
        negative = min(requested, 0.95 * max(center_vector[variable] - lower[variable], 0.0))
        coordinates: list[float]
        if positive > 1e-6 and negative > 1e-6:
            coordinates = [positive, -negative]
        elif positive > 1e-6:
            coordinates = [positive, 0.5 * positive]
        elif negative > 1e-6:
            coordinates = [-negative, -0.5 * negative]
        else:
            coordinates = []
        for slot, coordinate in enumerate(coordinates):
            full = center_vector.copy()
            full[variable] += coordinate
            full = clip_control(ctx, full)
            rows.append(
                {
                    "task": copy.deepcopy(ctx.task_map["nominal"]),
                    "candidate_id": candidate_digest("nominal", full, "identify", variable, slot),
                    "full_control_vector": full.tolist(),
                    "source_type": "stage3_4_full_real_tsc_probe",
                    "source_name": f"variable_{variable:03d}_{slot}",
                    "parent_candidate_id": str(center["candidate_id"]),
                    "probe_variable_index": variable,
                    "probe_coordinate": float(coordinate),
                }
            )
    return rows


def run_identification(ctx: Stage34Context, *, backend: str, resume: bool) -> dict[str, Any]:
    bundle_path = ctx.paths.identification / "full_horizon_bundle.json"
    if resume and bundle_path.exists():
        return read_json(bundle_path)
    library = read_json(ctx.paths.library / "target_library.json")
    nominal = next(
        (row for row in library.get("entries", []) if row["task"]["task_id"] == "nominal" and _as_bool(row.get("stage3_4_target_tracking_pass"))),
        None,
    )
    if nominal is None:
        raise RuntimeError("a confirmed nominal Stage3.4 library entry is required for identification")
    center_result = load_physical_result(ctx, nominal)
    center_feature = absolute_feature_from_result(ctx, center_result)
    probe_manifest_path = ctx.paths.identification / "probe_manifest.json"
    probe_results_path = ctx.paths.identification / "probe_results.json"
    if not probe_manifest_path.exists():
        probe_rows = build_identification_probe_rows(ctx, nominal)
        atomic_write_json(probe_manifest_path, {"center": nominal, "candidates": probe_rows})
    else:
        probe_rows = read_json(probe_manifest_path)["candidates"]
    if not probe_results_path.exists() or not resume:
        probe_results = evaluate_task_candidates(ctx, probe_rows, phase="full_horizon_identification", backend=backend, resume=resume)
        atomic_write_json(probe_results_path, probe_results)
        write_csv(ctx.paths.identification / "probe_results.csv", probe_results)
    else:
        probe_results = read_json(probe_results_path)
    jacobian = np.zeros((175, 105), dtype=float)
    reliable = np.zeros(105, dtype=bool)
    metadata: list[dict[str, Any]] = []
    for variable in range(105):
        group = [row for row in probe_results if _as_int(row.get("probe_variable_index"), -1) == variable and _as_bool(row.get("success"))]
        x: list[float] = []
        y: list[np.ndarray] = []
        for row in group:
            x.append(float(row["probe_coordinate"]))
            y.append(absolute_feature_from_result(ctx, load_physical_result(ctx, row)) - center_feature)
        if not x:
            metadata.append({"variable_index": variable, "reliable": False, "method": "unavailable"})
            continue
        xv = np.asarray(x, dtype=float)
        yv = np.stack(y, axis=0)
        if len(xv) >= 2:
            design = np.column_stack([xv, xv**2])
            coefficient, *_ = np.linalg.lstsq(design, yv, rcond=None)
            derivative = coefficient[0]
            residual = yv - design @ coefficient
            residual_ratio = float(np.linalg.norm(residual) / max(np.linalg.norm(yv), 1e-12))
            method = "central_or_secant_quadratic"
        else:
            derivative = yv[0] / xv[0]
            residual_ratio = 1.0
            method = "one_sided"
        jacobian[:, variable] = derivative
        reliable[variable] = bool(np.all(np.isfinite(derivative)) and np.linalg.norm(derivative) > 1e-12)
        metadata.append({"variable_index": variable, "reliable": bool(reliable[variable]), "method": method, "relative_residual": residual_ratio, "coordinates": xv.tolist()})
    minimum = int(ctx.cfg["identification"].get("minimum_reliable_columns", 90))
    if int(np.sum(reliable)) < minimum:
        raise RuntimeError(f"full-horizon identification has only {int(np.sum(reliable))}/105 reliable columns")
    scales = feature_scales(ctx)
    j_normalized = jacobian / scales[:, None]
    singular = np.linalg.svd(j_normalized[:, reliable], compute_uv=False)
    relative_cutoff = float(ctx.cfg["identification"].get("svd_relative_cutoff", 0.002))
    retained = int(np.sum(singular / max(float(singular[0]), 1e-30) >= relative_cutoff))
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "center_candidate_id": nominal["candidate_id"],
        "center_full_control_vector": nominal["full_control_vector"],
        "center_trajectory_RZI": nominal["nominal_trajectory_RZI"],
        "center_velocity_RZ": nominal["nominal_velocity_RZ"],
        "center_feature_physical_units": center_feature.tolist(),
        "feature_names": identification_feature_names(),
        "jacobian_physical_units": jacobian.tolist(),
        "jacobian_normalized": j_normalized.tolist(),
        "output_scales": scales.tolist(),
        "reliable_columns": reliable.tolist(),
        "successful_probes": int(sum(_as_bool(row.get("success")) for row in probe_results)),
        "column_metadata": metadata,
        "numerical_rank": int(np.linalg.matrix_rank(j_normalized[:, reliable])),
        "singular_values": singular.tolist(),
        "retained_rank": retained,
        "online_feedback_validated": False,
        "robustness_validated": False,
        "deployment_status": "OFFLINE_350MS_RECEDING_HORIZON_MPC_POC_ONLY",
    }
    atomic_write_json(bundle_path, bundle)
    np.savez_compressed(
        ctx.paths.identification / "full_horizon_bundle.npz",
        jacobian_physical_units=jacobian,
        jacobian_normalized=j_normalized,
        output_scales=scales,
        reliable_columns=reliable,
    )
    return bundle


# ---------------------------------------------------------------------------
# 350 ms target-conditioned receding-horizon MPC POC
# ---------------------------------------------------------------------------


def usable_library_entries(library: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        copy.deepcopy(row)
        for row in library.get("entries", [])
        if _as_bool(row.get("stage3_4_target_tracking_pass"), False)
        and row.get("nominal_trajectory_RZI") is not None
        and row.get("nominal_velocity_RZ") is not None
    ]
    if not entries:
        raise RuntimeError("Stage3.4 target library has no usable entry")
    return entries


def library_target_vector(entry: dict[str, Any]) -> np.ndarray:
    task = entry["task"]
    return np.asarray([task["R_offset_m"], task["Z_offset_m"], task["Ip_offset_A"]], dtype=float)


def interpolation_for_target(ctx: Stage34Context | SimpleNamespace, library: dict[str, Any], target_offset: np.ndarray) -> dict[str, Any]:
    entries = usable_library_entries(library)
    target_offset = np.asarray(target_offset, dtype=float).reshape(3)
    scales = np.asarray(ctx.cfg["mpc"]["target_distance_scales"], dtype=float)
    distances = np.asarray([np.linalg.norm((library_target_vector(entry) - target_offset) / scales) for entry in entries])
    exact = np.flatnonzero(distances <= 1e-12)
    if len(exact):
        indices = [int(exact[0])]
        weights = np.asarray([1.0])
    else:
        count = min(int(ctx.cfg["mpc"]["library_neighbors"]), len(entries))
        indices = [int(index) for index in np.argsort(distances)[:count]]
        power = float(ctx.cfg["mpc"].get("inverse_distance_power", 2.0))
        raw = 1.0 / np.maximum(distances[np.asarray(indices)], 1e-9) ** power
        weights = raw / np.sum(raw)
    selected = [entries[index] for index in indices]
    controls = np.stack([_vector(entry["full_control_vector"], 105) for entry in selected])
    trajectories = np.stack([np.asarray(entry["nominal_trajectory_RZI"], dtype=float) for entry in selected])
    velocities = np.stack([np.asarray(entry["nominal_velocity_RZ"], dtype=float) for entry in selected])
    return {
        "entry_ids": [entry["candidate_id"] for entry in selected],
        "task_ids": [entry["task"]["task_id"] for entry in selected],
        "weights": weights.tolist(),
        "distances": [float(distances[index]) for index in indices],
        "requested_target_offset": target_offset.tolist(),
        "represented_target_offset": np.sum(weights[:, None] * np.stack([library_target_vector(entry) for entry in selected]), axis=0).tolist(),
        "full_control_vector": clip_control(ctx, np.sum(weights[:, None] * controls, axis=0)).tolist(),
        "nominal_trajectory_RZI": np.sum(weights[:, None, None] * trajectories, axis=0).tolist(),
        "nominal_velocity_RZ": np.sum(weights[:, None, None] * velocities, axis=0).tolist(),
    }


def _future_feature_rows(current_step: int) -> list[int]:
    rows: list[int] = []
    for block in range(5):
        for state in range(current_step + 1, 36):
            rows.append(block * 35 + state - 1)
    return rows


def _future_control_columns(current_step: int) -> list[int]:
    return [step * 3 + mode for step in range(current_step, 35) for mode in range(3)]


def _measurement_bias_projection(ctx: Stage34Context | SimpleNamespace, current_step: int, selected_rows: Sequence[int]) -> np.ndarray:
    dt = float(ctx.env_cfg["dt_ms"]) / 1000.0
    scales = ctx.cfg["identification"]["output_scales"]
    r_ratio = float(scales["vR_m_per_s"]) / float(scales["R_m"])
    z_ratio = float(scales["vZ_m_per_s"]) / float(scales["Z_m"])
    full = np.zeros((175, 5), dtype=float)
    for state in range(1, 36):
        local = state - 1
        future = max(state - current_step, 0) * dt
        full[local, 0] = 1.0
        full[local, 2] = future * r_ratio
        full[35 + local, 1] = 1.0
        full[35 + local, 3] = future * z_ratio
        full[70 + local, 2] = 1.0
        full[105 + local, 3] = 1.0
        full[140 + local, 4] = 1.0
    return full[np.asarray(selected_rows, dtype=int)]


def _state_weight_vector(ctx: Stage34Context | SimpleNamespace, rows: Sequence[int], current_step: int) -> np.ndarray:
    mpc = ctx.cfg["mpc"]
    block_weights = np.asarray([mpc["output_weights"][key] for key in ("R", "Z", "vR", "vZ", "Ip")], dtype=float)
    discount = float(mpc.get("future_discount", 0.988))
    weights: list[float] = []
    for row in rows:
        block = row // 35
        state = row % 35 + 1
        horizon = max(state - current_step, 1)
        weight = block_weights[block] * (discount ** (horizon - 1))
        if state >= int(mpc.get("hold_weight_start_state", 14)):
            weight *= float(mpc.get("hold_weight_multiplier", 2.5))
        weights.append(weight)
    return np.asarray(weights, dtype=float)


def _nominal_feature(nominal_y: np.ndarray, nominal_velocity: np.ndarray, requested_target: np.ndarray) -> np.ndarray:
    error = np.asarray(nominal_y, dtype=float) - requested_target[None, :]
    velocity = np.asarray(nominal_velocity, dtype=float)
    return np.concatenate([error[1:, 0], error[1:, 1], velocity[1:, 0], velocity[1:, 1], error[1:, 2]])


def solve_receding_horizon_correction(
    ctx: Stage34Context | SimpleNamespace,
    bundle: dict[str, Any],
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
        raise RuntimeError("scipy is required for Stage3.4 MPC") from exc
    jacobian_norm = np.asarray(bundle["jacobian_normalized"], dtype=float)
    scales = np.asarray(bundle["output_scales"], dtype=float)
    rows = _future_feature_rows(current_step)
    columns = _future_control_columns(current_step)
    projection = _measurement_bias_projection(ctx, current_step, rows)
    integral_gain = np.asarray(ctx.cfg["mpc"]["integral_measurement_gain"], dtype=float)
    effective_measurement = np.asarray(measurement_normalized) + integral_gain * np.asarray(integral_normalized)
    future_error = nominal_feature[np.asarray(rows)] / scales[np.asarray(rows)] + projection @ effective_measurement
    a = jacobian_norm[np.ix_(rows, columns)]
    weights = _state_weight_vector(ctx, rows, current_step)
    sqrt_w = np.sqrt(np.maximum(weights, 0.0))
    augmented_a: list[np.ndarray] = [sqrt_w[:, None] * a]
    augmented_b: list[np.ndarray] = [-sqrt_w * future_error]
    future_steps = list(range(current_step, 35))
    nominal_future = np.asarray(nominal_coefficients)[future_steps].reshape(-1)
    lower_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(ctx.cfg["trajectory"]["coefficient_upper"], dtype=float)
    feedback_limit = np.asarray(ctx.cfg["mpc"]["per_step_feedback_limit_by_mode"], dtype=float) * float(controller_scale)
    lower = np.maximum(np.tile(lower_mode, len(future_steps)) - nominal_future, -np.tile(feedback_limit, len(future_steps)))
    upper = np.minimum(np.tile(upper_mode, len(future_steps)) - nominal_future, np.tile(feedback_limit, len(future_steps)))
    ridge = float(ctx.cfg["mpc"].get("ridge_lambda", 0.08))
    if ridge > 0.0:
        radius = np.maximum(np.tile(feedback_limit, len(future_steps)), 1e-8)
        augmented_a.append(math.sqrt(ridge) * np.diag(1.0 / radius))
        augmented_b.append(np.zeros(len(columns)))
    smooth = float(ctx.cfg["mpc"].get("future_correction_smoothness", 0.08))
    if smooth > 0.0 and len(future_steps) > 1:
        difference = s33._difference_matrix(len(future_steps))
        augmented_a.append(math.sqrt(smooth) * difference)
        augmented_b.append(np.zeros(difference.shape[0]))
    rate = float(ctx.cfg["mpc"].get("first_action_rate_weight", 0.20))
    if rate > 0.0:
        first = np.zeros((3, len(columns)))
        first[:, :3] = np.eye(3)
        augmented_a.append(math.sqrt(rate) * first)
        augmented_b.append(math.sqrt(rate) * np.asarray(previous_correction, dtype=float))
    solution = lsq_linear(
        np.vstack(augmented_a),
        np.concatenate(augmented_b),
        bounds=(lower, upper),
        method="trf",
        tol=float(ctx.cfg["mpc"].get("solver_tolerance", 1e-8)),
        max_iter=int(ctx.cfg["mpc"].get("solver_max_iterations", 300)),
        lsmr_tol="auto",
    )
    sequence = np.asarray(solution.x).reshape(len(future_steps), 3)
    first = sequence[0]
    rate_limit = np.asarray(ctx.cfg["mpc"]["per_step_correction_rate_limit_by_mode"], dtype=float)
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
    }


class LocalMpcWorker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env

        self.cfg = payload["cfg"]
        self.train_cfg = payload["train_cfg"]
        self.env_cfg = payload["env_cfg"]
        self.modes_tsc = np.asarray(payload["modes_tsc"], dtype=float)
        self.max_delta_a = float(payload["max_delta_a"])
        self.min_current = np.asarray(payload["min_current_tsc"], dtype=float)
        self.max_current = np.asarray(payload["max_current_tsc"], dtype=float)
        self.library = library
        self.bundle = bundle
        self.stub = SimpleNamespace(cfg=self.cfg, env_cfg=self.env_cfg)
        self.env = make_tsc_rzip_env(copy.deepcopy(self.train_cfg), worker_id=worker_id, seed=None)

    def _mode_action(self, coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
        desired = np.asarray(coefficients) @ self.modes_tsc.T
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
        control_trace: list[dict[str, Any]] = []
        failure_reason = ""
        try:
            offset = np.asarray([spec["target_R_offset_m"], spec["target_Z_offset_m"], spec["target_Ip_offset_A"]], dtype=float)
            interpolation = interpolation_for_target(self.stub, self.library, offset)
            nominal_coeff = _vector(interpolation["full_control_vector"], 105).reshape(35, 3)
            nominal_y = np.asarray(interpolation["nominal_trajectory_RZI"], dtype=float)
            nominal_velocity = np.asarray(interpolation["nominal_velocity_RZ"], dtype=float)
            requested_target = np.asarray(
                [
                    float(self.cfg["target"]["R"]) + offset[0],
                    float(self.cfg["target"]["Z"]) + offset[1],
                    float(self.cfg["target"]["Ip"]) + offset[2],
                ]
            )
            nominal_feature = _nominal_feature(nominal_y, nominal_velocity, requested_target)
            self.env.reset()
            zero = np.zeros(14, dtype=np.float32)
            trajectory.append(base._state_record(self.env, 0, zero))
            previous_y = np.asarray([trajectory[0]["R"], trajectory[0]["Z"], trajectory[0]["Ip"]], dtype=float)
            previous_correction = np.zeros(3)
            integral = np.zeros(5)
            controller_scale = float(spec["controller_scale"])
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
            for step in range(35):
                state = self.env.last_state
                current_y = np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)
                if step == 0:
                    current_velocity = np.zeros(2)
                else:
                    current_velocity = (current_y[:2] - previous_y[:2]) / (float(self.env_cfg["dt_ms"]) / 1000.0)
                measurement_physical = np.asarray(
                    [
                        current_y[0] - nominal_y[step, 0],
                        current_y[1] - nominal_y[step, 1],
                        current_velocity[0] - nominal_velocity[step, 0],
                        current_velocity[1] - nominal_velocity[step, 1],
                        current_y[2] - nominal_y[step, 2],
                    ]
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
                    solve = solve_receding_horizon_correction(
                        self.stub,
                        self.bundle,
                        current_step=step,
                        nominal_coefficients=nominal_coeff,
                        nominal_feature=nominal_feature,
                        measurement_normalized=measurement,
                        integral_normalized=integral,
                        previous_correction=previous_correction,
                        controller_scale=controller_scale,
                    )
                correction = np.asarray(solve["first_correction"], dtype=float)
                coefficients = nominal_coeff[step] + correction
                disturbance = spec.get("disturbance")
                if disturbance and step == int(disturbance["step"]):
                    coefficients = coefficients.copy()
                    coefficients[int(disturbance["mode"])] += float(disturbance["amplitude"])
                currents = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(coefficients, currents)
                _, _, terminated, truncated, info = self.env.step(action)
                trajectory.append(base._state_record(self.env, step + 1, action))
                control_trace.append(
                    {
                        "step": step,
                        "measurement_physical": measurement_physical.tolist(),
                        "measurement_normalized": measurement.tolist(),
                        "integral_normalized": integral.tolist(),
                        "mode_correction": correction.tolist(),
                        "mode_command": np.asarray(coefficients).tolist(),
                        "solver_success": bool(solve["solver_success"]),
                        "solver_status": int(solve["solver_status"]),
                        "solver_cost": float(solve["solver_cost"]),
                        "solver_optimality": float(solve["solver_optimality"]),
                        "predicted_normalized_residual_rms": float(solve["predicted_normalized_residual_rms"]),
                        "active_lower": int(solve["active_lower"]),
                        "active_upper": int(solve["active_upper"]),
                    }
                )
                previous_y = current_y
                previous_correction = correction
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated")); break
                if truncated and step + 1 < 35:
                    failure_reason = "environment truncated before 35 steps"; break
            success = len(trajectory) == 36 and not any(bool(row.get("abnormal", False)) for row in trajectory)
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
            runner.cleanup_episode_workspace(failed=not bool(result.get("success")), reason=str(result.get("failure_reason", "stage3_4_mpc_complete")))
        return _json_safe(result)

    def close(self) -> None:
        self.env.close()


def _mpc_ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id):
            self.worker = LocalMpcWorker(payload, library, bundle, worker_id)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor


def _context_payload(ctx: Stage34Context) -> dict[str, Any]:
    return {
        "cfg": copy.deepcopy(ctx.cfg),
        "train_cfg": copy.deepcopy(ctx.train_cfg),
        "env_cfg": copy.deepcopy(ctx.env_cfg),
        "modes_tsc": ctx.modes_tsc.tolist(),
        "max_delta_a": ctx.max_delta_a,
        "min_current_tsc": ctx.min_current_tsc.tolist(),
        "max_current_tsc": ctx.max_current_tsc.tolist(),
    }


def scenario_task(ctx: Stage34Context, scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(scenario["scenario"]),
        "R_offset_m": float(scenario.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(scenario.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(scenario.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(scenario.get("category", "validation")),
    }


def build_mpc_specs(ctx: Stage34Context, scenarios: Sequence[dict[str, Any]], scales: Sequence[float], split: str) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for scenario in scenarios:
        for scale in scales:
            experiment_id = (
                f"s34mpc_{split}_{scenario['scenario']}_scale{float(scale):.2f}"
                .replace(".", "p").replace("-", "m").replace("+", "p")
            )
            specs.append(
                {
                    "kind": "stage3_4_receding_horizon_mpc",
                    "experiment_id": experiment_id,
                    "scenario": str(scenario["scenario"]),
                    "scenario_split": split,
                    "category": str(scenario.get("category", "target")),
                    "target_R_offset_m": float(scenario.get("target_R_offset_m", 0.0)),
                    "target_Z_offset_m": float(scenario.get("target_Z_offset_m", 0.0)),
                    "target_Ip_offset_A": float(scenario.get("target_Ip_offset_A", 0.0)),
                    "disturbance": copy.deepcopy(scenario.get("disturbance")),
                    "controller_scale": float(scale),
                    "horizon_steps": 35,
                }
            )
    if len({spec["experiment_id"] for spec in specs}) != len(specs):
        raise RuntimeError("duplicate Stage3.4 MPC experiment id")
    return specs


def evaluate_mpc_specs(
    ctx: Stage34Context,
    specs: Sequence[dict[str, Any]],
    *,
    library: dict[str, Any],
    bundle: dict[str, Any],
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
        worker = LocalMpcWorker(payload, library, bundle, "stage34_mpc_serial")
        try:
            for index, spec in enumerate(pending, 1):
                result = worker.evaluate(spec)
                atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                print(f"[Stage3.4 MPC] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif pending and backend == "ray":
        import ray

        requested = int(os.environ.get("STAGE3_4_WORKERS", ctx.cfg.get("parallel", {}).get("n_workers", 96)))
        ray_tmpdir = os.environ.get("RAY_TMPDIR", ctx.cfg.get("parallel", {}).get("ray_tmpdir", "")) or None
        plan = ensure_ray_worker_plan(ray, requested_workers=requested, pending_tasks=len(pending), ray_tmpdir=ray_tmpdir, log_prefix="[Stage3.4 MPC]")
        Actor = _mpc_ray_actor_class()
        actors = [Actor.remote(payload, library, bundle, f"stage34_mpc_{index:03d}") for index in range(plan.actor_count)]
        refs = {actors[index % plan.actor_count].evaluate.remote(spec): spec for index, spec in enumerate(pending)}
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage3.4 MPC] waiting {done}/{len(pending)}", flush=True); continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {"schema_version": SCHEMA_VERSION, "experiment_id": spec["experiment_id"], "spec": spec, "success": False, "failure_reason": repr(exc), "traceback": traceback.format_exc(), "trajectory": [], "control_trace": []}
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    print(f"[Stage3.4 MPC] {done}/{len(pending)}", flush=True)
        finally:
            s2._close_ray_actors(actors, timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1200.0)))
    elif pending:
        raise ValueError("backend must be ray or serial")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


def summarize_mpc_results(ctx: Stage34Context, results: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        task = scenario_task(ctx, spec)
        metrics = target_metrics(ctx, task, result, None)
        trace = result.get("control_trace", [])
        max_correction = max((float(np.max(np.abs(row.get("mode_correction", [0, 0, 0])))) for row in trace), default=0.0)
        rows.append(
            {
                "experiment_id": result["experiment_id"],
                "scenario": spec["scenario"],
                "scenario_split": spec["scenario_split"],
                "category": spec["category"],
                "controller_scale": float(spec["controller_scale"]),
                "target_R_offset_m": float(spec["target_R_offset_m"]),
                "target_Z_offset_m": float(spec["target_Z_offset_m"]),
                "target_Ip_offset_A": float(spec["target_Ip_offset_A"]),
                "disturbance": copy.deepcopy(spec.get("disturbance")),
                "max_abs_mode_correction": max_correction,
                **metrics,
            }
        )
    return rows


def scale_summaries(ctx: Stage34Context, rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    by_scenario: dict[str, dict[float, dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), {})[float(row["controller_scale"])] = row
    summaries: list[dict[str, Any]] = []
    for scale in sorted({float(row["controller_scale"]) for row in rows if float(row["controller_scale"]) > 0.0}):
        comparisons: list[dict[str, Any]] = []
        for scenario, values in sorted(by_scenario.items()):
            baseline = values.get(0.0)
            feedback = values.get(scale)
            if baseline is None or feedback is None:
                continue
            base_pass = _as_bool(baseline.get("stage3_4_target_tracking_pass"))
            fb_pass = _as_bool(feedback.get("stage3_4_target_tracking_pass"))
            gain = _as_float(feedback.get("stage3_4_tracking_minimum_signed_margin"), -1e12) - _as_float(baseline.get("stage3_4_tracking_minimum_signed_margin"), -1e12)
            comparisons.append(
                {
                    "scenario": scenario,
                    "baseline_pass": base_pass,
                    "feedback_pass": fb_pass,
                    "preserved": bool(base_pass and fb_pass),
                    "recovered": bool((not base_pass) and fb_pass),
                    "lost": bool(base_pass and not fb_pass),
                    "signed_margin_gain": gain,
                }
            )
        gains = [row["signed_margin_gain"] for row in comparisons]
        summary = {
            "controller_scale": scale,
            "n_scenarios": len(comparisons),
            "feedback_pass_fraction": float(np.mean([row["feedback_pass"] for row in comparisons])) if comparisons else 0.0,
            "n_preserved": int(sum(row["preserved"] for row in comparisons)),
            "n_recovered": int(sum(row["recovered"] for row in comparisons)),
            "n_lost": int(sum(row["lost"] for row in comparisons)),
            "median_signed_margin_gain": float(np.median(gains)) if gains else -1e12,
            "worst_signed_margin_gain": float(np.min(gains)) if gains else -1e12,
            "comparisons": comparisons,
        }
        summary["eligible"] = bool(
            summary["feedback_pass_fraction"] >= float(ctx.cfg["mpc"].get("minimum_calibration_tracking_fraction", 0.80))
            and (not bool(ctx.cfg["mpc"].get("require_no_lost_baseline_passes", True)) or summary["n_lost"] == 0)
            and summary["median_signed_margin_gain"] >= float(ctx.cfg["mpc"].get("minimum_median_margin_gain", -0.005))
        )
        summaries.append(summary)
    eligible = [row for row in summaries if row["eligible"]]
    selected = max(eligible, key=lambda row: (row["feedback_pass_fraction"], row["n_recovered"], row["median_signed_margin_gain"], -row["controller_scale"])) if eligible else None
    return summaries, selected


def run_mpc_calibration(ctx: Stage34Context, *, backend: str, resume: bool) -> dict[str, Any]:
    library = read_json(ctx.paths.library / "target_library.json")
    bundle = read_json(ctx.paths.identification / "full_horizon_bundle.json")
    scenarios = ctx.cfg["mpc"]["calibration_scenarios"]
    scales = ctx.cfg["mpc"]["controller_scales"]
    specs = build_mpc_specs(ctx, scenarios, scales, "calibration")
    results = evaluate_mpc_specs(ctx, specs, library=library, bundle=bundle, output_dir=ctx.paths.calibration / "raw", backend=backend, resume=resume)
    rows = summarize_mpc_results(ctx, results)
    summaries, selected = scale_summaries(ctx, rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "n_rollouts": len(rows),
        "n_successful": int(sum(_as_bool(row.get("success")) for row in rows)),
        "scale_summaries": summaries,
        "selected_scale_summary": selected,
        "selected_controller_scale": None if selected is None else selected["controller_scale"],
        "calibration_pass": bool(selected is not None),
    }
    atomic_write_json(ctx.paths.calibration / "calibration_results.json", rows)
    write_csv(ctx.paths.calibration / "calibration_results.csv", rows)
    atomic_write_json(ctx.paths.calibration / "calibration_summary.json", summary)
    return summary


def run_mpc_holdout(ctx: Stage34Context, *, backend: str, resume: bool) -> dict[str, Any]:
    calibration = read_json(ctx.paths.calibration / "calibration_summary.json")
    selected = calibration.get("selected_controller_scale")
    if selected is None:
        return {"holdout_pass": False, "reason": "no calibrated controller scale"}
    library = read_json(ctx.paths.library / "target_library.json")
    bundle = read_json(ctx.paths.identification / "full_horizon_bundle.json")
    scenarios = ctx.cfg["mpc"]["holdout_scenarios"]
    specs = build_mpc_specs(ctx, scenarios, [0.0, float(selected)], "holdout")
    results = evaluate_mpc_specs(ctx, specs, library=library, bundle=bundle, output_dir=ctx.paths.holdout / "raw", backend=backend, resume=resume)
    rows = summarize_mpc_results(ctx, results)
    by_scenario: dict[str, dict[float, dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), {})[float(row["controller_scale"])] = row
    comparisons: list[dict[str, Any]] = []
    for scenario, values in sorted(by_scenario.items()):
        baseline = values[0.0]; feedback = values[float(selected)]
        base_pass = _as_bool(baseline.get("stage3_4_target_tracking_pass")); fb_pass = _as_bool(feedback.get("stage3_4_target_tracking_pass"))
        comparisons.append(
            {
                "scenario": scenario,
                "baseline_pass": base_pass,
                "feedback_pass": fb_pass,
                "preserved": bool(base_pass and fb_pass),
                "recovered": bool((not base_pass) and fb_pass),
                "lost": bool(base_pass and not fb_pass),
                "signed_margin_gain": _as_float(feedback.get("stage3_4_tracking_minimum_signed_margin"), -1e12) - _as_float(baseline.get("stage3_4_tracking_minimum_signed_margin"), -1e12),
            }
        )
    pass_fraction = float(np.mean([row["feedback_pass"] for row in comparisons])) if comparisons else 0.0
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "selected_controller_scale": float(selected),
        "n_scenarios": len(comparisons),
        "feedback_pass_fraction": pass_fraction,
        "n_preserved": int(sum(row["preserved"] for row in comparisons)),
        "n_recovered": int(sum(row["recovered"] for row in comparisons)),
        "n_lost": int(sum(row["lost"] for row in comparisons)),
        "median_signed_margin_gain": float(np.median([row["signed_margin_gain"] for row in comparisons])) if comparisons else -1e12,
        "worst_signed_margin_gain": float(np.min([row["signed_margin_gain"] for row in comparisons])) if comparisons else -1e12,
        "comparisons": comparisons,
    }
    summary["holdout_pass"] = bool(
        pass_fraction >= float(ctx.cfg["mpc"].get("minimum_holdout_tracking_fraction", 0.75))
        and (not bool(ctx.cfg["mpc"].get("require_no_lost_baseline_passes", True)) or summary["n_lost"] == 0)
    )
    atomic_write_json(ctx.paths.holdout / "holdout_results.json", rows)
    write_csv(ctx.paths.holdout / "holdout_results.csv", rows)
    atomic_write_json(ctx.paths.holdout / "holdout_summary.json", summary)
    return summary



def _scenario_lookup(ctx: Stage34Context) -> dict[str, dict[str, Any]]:
    return {
        str(row["scenario"]): copy.deepcopy(row)
        for row in ctx.cfg["mpc"]["calibration_scenarios"] + ctx.cfg["mpc"]["holdout_scenarios"]
    }


def run_mpc_confirmation(ctx: Stage34Context, *, backend: str, resume: bool) -> dict[str, Any]:
    calibration = read_json(ctx.paths.calibration / "calibration_summary.json")
    holdout = read_json(ctx.paths.holdout / "holdout_summary.json")
    selected = calibration.get("selected_controller_scale")
    if selected is None or not bool(holdout.get("holdout_pass", False)):
        return {"mpc_confirmation_pass": False, "reason": "calibration/holdout did not pass"}
    lookup = _scenario_lookup(ctx)
    scenarios = [lookup[name] for name in ctx.cfg["confirmation"]["mpc_scenarios"]]
    repeats = int(ctx.cfg["confirmation"]["mpc_repeats_per_scenario"])
    specs: list[dict[str, Any]] = []
    for scenario in scenarios:
        for repeat in range(repeats):
            base_spec = build_mpc_specs(ctx, [scenario], [float(selected)], "confirmation")[0]
            base_spec["repeat"] = repeat
            base_spec["experiment_id"] = f"{base_spec['experiment_id']}_r{repeat:02d}"
            specs.append(base_spec)
    library = read_json(ctx.paths.library / "target_library.json")
    bundle = read_json(ctx.paths.identification / "full_horizon_bundle.json")
    results = evaluate_mpc_specs(ctx, specs, library=library, bundle=bundle, output_dir=ctx.paths.confirmations / "mpc_raw", backend=backend, resume=resume)
    rows = summarize_mpc_results(ctx, results)
    summaries: list[dict[str, Any]] = []
    for scenario in scenarios:
        group = [row for row in rows if row["scenario"] == scenario["scenario"]]
        summaries.append(
            {
                "scenario": scenario["scenario"],
                "repeats": len(group),
                "successful_repeats": int(sum(_as_bool(row.get("success")) for row in group)),
                "all_repeats_tracking_pass": bool(group and all(_as_bool(row.get("stage3_4_target_tracking_pass")) for row in group)),
                "worst_tracking_signed_margin": None if not group else min(_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in group),
            }
        )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "selected_controller_scale": float(selected),
        "n_rollouts": len(rows),
        "n_successful": int(sum(_as_bool(row.get("success")) for row in rows)),
        "scenario_summaries": summaries,
        "mpc_confirmation_pass": bool(summaries and all(row["all_repeats_tracking_pass"] for row in summaries)),
    }
    atomic_write_json(ctx.paths.confirmations / "mpc_confirmation_results.json", rows)
    write_csv(ctx.paths.confirmations / "mpc_confirmation_results.csv", rows)
    atomic_write_json(ctx.paths.confirmations / "mpc_confirmation_summary.json", summary)
    return summary


# ---------------------------------------------------------------------------
# Verdict, analysis, state machine, and CLI
# ---------------------------------------------------------------------------


def final_verdict(ctx: Stage34Context) -> dict[str, Any]:
    library = read_json(ctx.paths.library / "target_library.json") if (ctx.paths.library / "target_library.json").exists() else {}
    library_confirmation = read_json(ctx.paths.library / "target_library_confirmation_summary.json") if (ctx.paths.library / "target_library_confirmation_summary.json").exists() else {}
    calibration = read_json(ctx.paths.calibration / "calibration_summary.json") if (ctx.paths.calibration / "calibration_summary.json").exists() else {}
    holdout = read_json(ctx.paths.holdout / "holdout_summary.json") if (ctx.paths.holdout / "holdout_summary.json").exists() else {}
    confirmation = read_json(ctx.paths.confirmations / "mpc_confirmation_summary.json") if (ctx.paths.confirmations / "mpc_confirmation_summary.json").exists() else {}
    library_pass = bool(library.get("mandatory_complete", False) and library_confirmation.get("mandatory_all_confirmed", False))
    mpc_pass = bool(calibration.get("calibration_pass", False) and holdout.get("holdout_pass", False) and confirmation.get("mpc_confirmation_pass", False))
    if library_pass and mpc_pass:
        verdict = "PASS_LATE_ARRIVAL_TARGET_CONDITIONED_RECEDING_HORIZON_MPC_TEST_ENVELOPE_CONFIRMED"
    elif library_pass:
        verdict = "PASS_LATE_ARRIVAL_350MS_TARGET_LIBRARY_CONFIRMED_MPC_NOT_VALIDATED"
    else:
        verdict = "LATE_ARRIVAL_TARGET_LIBRARY_INCOMPLETE_MPC_NOT_VALIDATED"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "latest_allowed_arrival_ms": 250,
        "hold_through_ms": 350,
        "target_library": {
            "mandatory_complete": bool(library.get("mandatory_complete", False)),
            "mandatory_confirmed": bool(library_confirmation.get("mandatory_all_confirmed", False)),
            "n_entries": int(library.get("n_entries", 0)),
            "n_mandatory_pass": int(library.get("n_mandatory_pass", 0)),
            "n_mandatory": int(library.get("n_mandatory", 0)),
        },
        "mpc_calibration": calibration,
        "mpc_holdout": holdout,
        "mpc_confirmation": confirmation,
        "online_receding_horizon_mpc_validated_for_tested_target_envelope": mpc_pass,
        "initial_state_robustness_validated": False,
        "plant_parameter_robustness_validated": False,
        "noise_delay_robustness_validated": False,
        "robustness_validated": False,
        "final_task_warning": "This fixed-initial-state target/disturbance envelope is not deployment or full robustness validation. Residual RL remains bounded and secondary.",
    }
    atomic_write_json(ctx.paths.confirmations / "stage3_4_verdict.json", payload)
    return payload


def analyze_stage34(ctx: Stage34Context) -> dict[str, Any]:
    task_summaries: list[dict[str, Any]] = []
    for task in ctx.tasks:
        path = _task_summary_path(ctx, task)
        if path.exists():
            task_summaries.append(read_json(path))
    library = read_json(ctx.paths.library / "target_library.json") if (ctx.paths.library / "target_library.json").exists() else {}
    cache_files = list((ctx.paths.physical_cache / "raw").glob("*.json.gz"))
    successful_cache = 0
    for path in cache_files:
        try:
            successful_cache += int(bool(read_json_gz(path).get("success")))
        except Exception:
            pass
    verdict = final_verdict(ctx)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "n_continuation_tasks": len(task_summaries),
        "n_continuation_tasks_pass": int(sum(bool(row.get("tracking_pass")) for row in task_summaries)),
        "n_physical_cache_files": len(cache_files),
        "n_successful_physical_cache_files": successful_cache,
        "n_library_entries": int(library.get("n_entries", 0)),
        "n_mandatory_pass": int(library.get("n_mandatory_pass", 0)),
        "n_mandatory": int(library.get("n_mandatory", 0)),
        "verdict": verdict["verdict"],
        "task_summaries": [
            {
                "task_id": row["task"]["task_id"],
                "final": row["task"]["final"],
                "mandatory": row["task"]["mandatory"],
                "tracking_pass": row["tracking_pass"],
                "arrival_ms": row["best"].get("stage3_4_best_endpoint_ms"),
                "sustained_box_m": row["best"].get("stage3_4_sustained_box_max_error_m"),
                "hold_rz_rms_m": row["best"].get("stage3_4_hold_rz_rms_m"),
                "signed_margin": row["best"].get("stage3_4_tracking_minimum_signed_margin"),
                "stop_reason": row.get("stop_reason"),
            }
            for row in task_summaries
        ],
    }
    atomic_write_json(ctx.paths.analysis / "stage3_4_analysis_summary.json", summary)
    write_csv(ctx.paths.analysis / "task_summary.csv", summary["task_summaries"])
    report_lines = [
        "STAGE3.4 LATE-ARRIVAL CONTINUATION AND MPC REPORT",
        "",
        f"Verdict: {summary['verdict']}",
        f"Arrival allowed through: 250 ms",
        f"Hold required through: 350 ms",
        f"Mandatory target library: {summary['n_mandatory_pass']}/{summary['n_mandatory']}",
        f"Unique real-TSC physical cache results: {summary['n_physical_cache_files']}",
        "",
        "This stage does not validate new initial states, plant parameters, noise, or latency.",
        "The final task remains a robust causal controller; residual RL is bounded and secondary.",
    ]
    (ctx.paths.run_dir / "STAGE3_4_REPORT.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return summary


def initial_state(ctx: Stage34Context) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "prepared": True,
        "continuation_complete": False,
        "library_confirmed": False,
        "identification_complete": False,
        "calibration_complete": False,
        "holdout_complete": False,
        "confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage34Context, **values: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state(ctx)
    state.update(values)
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare_stage34(ctx: Stage34Context) -> dict[str, Any]:
    initialize_stage34_run(ctx)
    source_rows = source_seed_catalog(ctx)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state(ctx))
    return {
        "stage": STAGE,
        "source_stage3_3_run": str(ctx.source_stage33_run),
        "source_seed_entries": len(source_rows),
        "tasks": len(ctx.tasks),
        "final_mandatory_tasks": sum(bool(row["final"] and row["mandatory"]) for row in ctx.tasks),
        "horizon_steps": 35,
        "latest_arrival_ms": 250,
        "hold_through_ms": 350,
    }


def execute(
    *,
    config_path: str | Path,
    source_stage33_run: str | Path | None,
    run_dir: str | Path | None,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx = load_stage34_config(config_path, source_stage33_run=source_stage33_run, run_dir_override=run_dir)
    prepared = prepare_stage34(ctx)
    if command == "prepare":
        return prepared
    if command in {"continue", "all"}:
        continuation = run_continuation(ctx, backend=backend, resume=resume)
        _update_state(ctx, continuation_complete=True, continuation_summary=continuation)
        materialize_library(ctx)
    if command in {"library-confirm", "all"}:
        if not (ctx.paths.library / "target_library.json").exists():
            materialize_library(ctx)
        confirmation = run_library_confirmation(ctx, backend=backend, resume=resume)
        _update_state(ctx, library_confirmed=bool(confirmation.get("mandatory_all_confirmed")), library_confirmation=confirmation)
    library_confirmation = read_json(ctx.paths.library / "target_library_confirmation_summary.json") if (ctx.paths.library / "target_library_confirmation_summary.json").exists() else {}
    library_ready = bool(library_confirmation.get("mandatory_all_confirmed", False))
    if command in {"identify", "all"} and library_ready:
        bundle = run_identification(ctx, backend=backend, resume=resume)
        _update_state(ctx, identification_complete=True, identification_summary={"reliable_columns": int(sum(bundle["reliable_columns"])), "retained_rank": bundle["retained_rank"]})
    if command in {"calibrate", "all"} and library_ready:
        calibration = run_mpc_calibration(ctx, backend=backend, resume=resume)
        _update_state(ctx, calibration_complete=True, calibration_summary=calibration)
    calibration_ready = (ctx.paths.calibration / "calibration_summary.json").exists() and bool(read_json(ctx.paths.calibration / "calibration_summary.json").get("calibration_pass", False))
    if command in {"holdout", "all"} and library_ready and calibration_ready:
        holdout = run_mpc_holdout(ctx, backend=backend, resume=resume)
        _update_state(ctx, holdout_complete=True, holdout_summary=holdout)
    holdout_ready = (ctx.paths.holdout / "holdout_summary.json").exists() and bool(read_json(ctx.paths.holdout / "holdout_summary.json").get("holdout_pass", False))
    if command in {"confirm", "all"} and library_ready and holdout_ready:
        confirmation = run_mpc_confirmation(ctx, backend=backend, resume=resume)
        _update_state(ctx, confirmation_complete=True, mpc_confirmation=confirmation)
    summary = analyze_stage34(ctx)
    verdict = read_json(ctx.paths.confirmations / "stage3_4_verdict.json")
    _update_state(ctx, finished=True, stop_reason="pipeline_complete", verdict=verdict["verdict"])
    return {"prepared": prepared, "summary": summary, "verdict": verdict}


def synthetic_stage34_test() -> dict[str, Any]:
    # Pure structural test; no TSC runtime is used.
    cfg = read_json(Path(__file__).resolve().parents[2] / "configs/stage3_4_late_arrival_continuation_mpc_350ms.json")
    validate_stage34_config(cfg)
    tasks = build_tasks(cfg)
    basis_cfg = cfg["refinement"]
    time_index = np.arange(35, dtype=float)
    profiles = [np.exp(-0.5 * ((time_index - c) / w) ** 2) for c, w in zip(basis_cfg["temporal_centers"], basis_cfg["temporal_widths"])] + [np.ones(35)]
    q, _ = np.linalg.qr(np.stack(profiles, axis=1))
    basis = np.zeros((105, 18))
    column = 0
    for mode in range(3):
        for index in range(6):
            block = np.zeros((35, 3)); block[:, mode] = q[:, index]
            basis[:, column] = block.reshape(-1); column += 1
    assert basis.shape == (105, 18) and np.linalg.matrix_rank(basis) == 18
    assert list(cfg["gate"]["allowed_arrival_steps"]) == list(range(12, 26))
    assert int(cfg["gate"]["hold_through_step"]) == 35
    assert all(parent in {row["task_id"] for row in tasks[:row["task_index"]]} for row in tasks for parent in row["parents"])
    return {"stage": STAGE, "tasks": len(tasks), "basis_shape": list(basis.shape), "status": "ok"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--source-stage3-3-run")
    parser.add_argument("--run-dir")
    parser.add_argument("--command", default="all", choices=["prepare", "continue", "library-confirm", "identify", "calibrate", "holdout", "confirm", "analyze", "all", "self-test"])
    parser.add_argument("--backend", default="ray", choices=["ray", "serial"])
    parser.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "self-test":
        print(json.dumps(synthetic_stage34_test(), indent=2)); return
    result = execute(
        config_path=args.config,
        source_stage33_run=args.source_stage3_3_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        resume=not args.no_resume,
    )
    print(json.dumps(_json_safe(result), indent=2))


if __name__ == "__main__":
    main()
