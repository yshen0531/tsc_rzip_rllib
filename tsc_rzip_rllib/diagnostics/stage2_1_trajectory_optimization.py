"""Stage2.1 dual-archive local trajectory optimization.

This module is an overlay on top of the validated Stage2 implementation in
``tsc_rzip_rllib.diagnostics.stage2_trajectory_optimization``.  It deliberately
reuses the existing Stage1.1 loader, SVD-mode decoder, real-TSC evaluator and
workspace cleanup path.  Stage2.1 changes the search and the continuous
objective, but it does *not* change the hard 30 mm/velocity/Ip success gate.

Main changes from Stage2
------------------------
* warm-start from a completed Stage2 run, without mutating it;
* independent damped and precise-but-underdamped archives;
* explicit crossover between precise fronts and damped braking tails;
* most search variance is placed on the final three time nodes (9 variables);
* smooth final-window 30 mm tube-excess objective;
* optional pure-NumPy ridge velocity surrogate, activated only after
  leave-one-generation-out validation and used only for proposal ranking;
* strict confirmation requires every repeat of at least one candidate to pass.
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
import random
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2


SCHEMA_VERSION = 1
STATE_FILENAME = "stage2_1_state.json"
MANIFEST_FILENAME = "stage2_1_manifest.json"
SOURCE_COPY_DIRNAME = "source_stage2_reference"

_REQUIRED_BASE_SYMBOLS = (
    "load_stage2_config",
    "initialize_stage2_run",
    "decode_vector",
    "linear_prefilter_metrics",
    "stage2_metrics",
    "evaluate_specs",
)
for _symbol in _REQUIRED_BASE_SYMBOLS:
    if not hasattr(s2, _symbol):
        raise ImportError(
            "Stage2.1 requires the feat2-cem Stage2 implementation; missing "
            f"tsc_rzip_rllib.diagnostics.stage2_trajectory_optimization.{_symbol}"
        )


# ---------------------------------------------------------------------------
# Small, dependency-free I/O helpers
# ---------------------------------------------------------------------------


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object in {path}")
    return payload


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, default=_json_default)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def read_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected compressed JSON object in {path}")
    return payload


def atomic_write_json_gz(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with gzip.open(tmp, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, default=_json_default)
    os.replace(tmp, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, np.ndarray)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=_json_default)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
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
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key, "")) for key in fields})
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _as_float(value: Any, default: float = math.nan) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _parse_vector(value: Any, expected: int = 15) -> np.ndarray:
    if isinstance(value, np.ndarray):
        vector = np.asarray(value, dtype=float)
    elif isinstance(value, (list, tuple)):
        vector = np.asarray(value, dtype=float)
    else:
        vector = np.asarray(json.loads(str(value)), dtype=float)
    vector = vector.reshape(-1)
    if vector.shape != (expected,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"Invalid parameter vector shape/content: {vector.shape}")
    return vector


def vector_digest(vector: np.ndarray, prefix: str = "s21") -> str:
    rounded = np.round(np.asarray(vector, dtype=float).reshape(-1), 10)
    return f"{prefix}_{hashlib.sha256(rounded.tobytes()).hexdigest()[:16]}"


def _clip_vector(ctx: Any, vector: np.ndarray) -> np.ndarray:
    return np.clip(
        np.asarray(vector, dtype=float).reshape(-1),
        np.asarray(ctx.coefficient_lower, dtype=float),
        np.asarray(ctx.coefficient_upper, dtype=float),
    )


# ---------------------------------------------------------------------------
# Paths and source Stage2 loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage21Paths:
    run_dir: Path
    state: Path
    manifest: Path
    generations: Path
    evaluations: Path
    confirmations: Path
    analysis: Path
    best: Path
    source_reference: Path

    @classmethod
    def from_context(cls, ctx: Any) -> "Stage21Paths":
        run_dir = Path(ctx.paths.run_dir)
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            generations=run_dir / "stage2_1_generations",
            evaluations=run_dir / "stage2_1_evaluations",
            confirmations=run_dir / "stage2_1_confirmations",
            analysis=run_dir / "stage2_1_analysis",
            best=run_dir / "stage2_1_best",
            source_reference=run_dir / SOURCE_COPY_DIRNAME,
        )


@dataclass
class SourceStage2Data:
    run_dir: Path
    config: dict[str, Any]
    state: dict[str, Any]
    rows: list[dict[str, Any]]
    records: list[dict[str, Any]]


def resolve_source_stage2_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        env_value = os.environ.get("SOURCE_STAGE2_RUN", "").strip()
        if not env_value:
            raise ValueError(
                "A completed Stage2 run is required. Pass --source-stage2-run or set SOURCE_STAGE2_RUN."
            )
        value = env_value
    run_dir = Path(value).expanduser().resolve()
    required = [
        run_dir / "stage2_config.resolved.json",
        run_dir / "cem_state.json",
        run_dir / "analysis/all_generation_results.csv",
        run_dir / "best/best_candidate.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage2 source run: " + ", ".join(missing))
    return run_dir


def _validate_source_compatibility(ctx: Any, source_cfg: dict[str, Any]) -> None:
    for key in ("R", "Z", "Ip"):
        lhs = float(ctx.cfg["target"][key])
        rhs = float(source_cfg["target"][key])
        if not math.isclose(lhs, rhs, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Stage2.1 target {key}={lhs} differs from source Stage2 {rhs}")
    lhs_traj = ctx.cfg["trajectory"]
    rhs_traj = source_cfg["trajectory"]
    for key in ("horizon_steps", "horizon_ms", "n_modes", "node_count"):
        if int(lhs_traj[key]) != int(rhs_traj[key]):
            raise ValueError(f"Stage2.1 trajectory {key} differs from source Stage2")
    if list(lhs_traj["node_steps"]) != list(rhs_traj["node_steps"]):
        raise ValueError("Stage2.1 node_steps differ from source Stage2")
    # The hard gate is intentionally immutable.
    for key in (
        "precise_tolerance_m",
        "relaxed_tolerance_m",
        "required_terminal_streak_steps",
        "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s",
        "ip_tolerance_a",
    ):
        lhs = float(ctx.cfg["gate"][key])
        rhs = float(source_cfg["gate"][key])
        if not math.isclose(lhs, rhs, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage2.1 hard gate {key} must equal source Stage2")


def _record_from_csv_row(row: dict[str, Any], *, source_run: Path | None) -> dict[str, Any] | None:
    if not _as_bool(row.get("success"), False):
        return None
    try:
        vector = _parse_vector(row.get("parameter_vector"))
    except Exception:
        return None
    record = {
        "candidate_id": str(row.get("candidate_id", vector_digest(vector, "source"))),
        "generation": _as_int(row.get("generation"), -1),
        "vector": vector.tolist(),
        "source_type": str(row.get("source_type", "unknown")),
        "source_name": str(row.get("source_name", "unknown")),
        "source_run": str(source_run) if source_run is not None else "",
        "gate_tier": _as_int(row.get("gate_tier"), 99),
        "gate_label": str(row.get("gate_label", "")),
        "strict_gate_pass": _as_bool(row.get("strict_gate_pass"), False),
        "relaxed_gate_pass": _as_bool(row.get("relaxed_gate_pass"), False),
        "terminal_R_error_m": _as_float(row.get("terminal_R_error_m")),
        "terminal_Z_error_m": _as_float(row.get("terminal_Z_error_m")),
        "terminal_Ip_error_A": _as_float(row.get("terminal_Ip_error_A")),
        "terminal_RZ_euclidean_error_m": _as_float(row.get("terminal_RZ_euclidean_error_m")),
        "terminal_RZ_box_max_error_m": _as_float(row.get("terminal_RZ_box_max_error_m")),
        "late_RZ_euclidean_rms_m": _as_float(row.get("late_RZ_euclidean_rms_m")),
        "terminal_velocity_m_per_s": _as_float(row.get("terminal_velocity_m_per_s")),
        "late_velocity_rms_m_per_s": _as_float(row.get("late_velocity_rms_m_per_s")),
        "trailing_streak_within_30mm_steps": _as_int(
            row.get("trailing_streak_within_30mm_steps"), 0
        ),
        "trailing_streak_within_40mm_steps": _as_int(
            row.get("trailing_streak_within_40mm_steps"), 0
        ),
        "selection_score": _as_float(row.get("selection_score"), 99e6 + 1e12),
        "continuous_objective": _as_float(row.get("continuous_objective"), 1e12),
        "linear_prefilter_score": _as_float(row.get("linear_prefilter_score"), 1e12),
    }
    if not math.isfinite(record["terminal_RZ_box_max_error_m"]):
        record["terminal_RZ_box_max_error_m"] = max(
            abs(record["terminal_R_error_m"]), abs(record["terminal_Z_error_m"])
        )
    return record


def load_source_stage2(ctx: Any, source_run: str | Path | None) -> SourceStage2Data:
    run_dir = resolve_source_stage2_run(source_run)
    source_cfg = read_json(run_dir / "stage2_config.resolved.json")
    _validate_source_compatibility(ctx, source_cfg)
    source_state = read_json(run_dir / "cem_state.json")
    csv_rows = read_csv(run_dir / "analysis/all_generation_results.csv")
    rows: list[dict[str, Any]] = [dict(row) for row in csv_rows]
    records = [
        record
        for row in rows
        if (record := _record_from_csv_row(row, source_run=run_dir)) is not None
    ]
    if len(records) < 100:
        raise RuntimeError(
            f"Source Stage2 has only {len(records)} usable successful candidates; expected a completed run"
        )
    return SourceStage2Data(
        run_dir=run_dir,
        config=source_cfg,
        state=source_state,
        rows=rows,
        records=records,
    )


def initialize_stage21_run(ctx: Any, source: SourceStage2Data) -> Stage21Paths:
    # Keep the exact validated Stage2 environment/runtime setup.
    s2.initialize_stage2_run(ctx)
    paths = Stage21Paths.from_context(ctx)
    for path in (
        paths.generations,
        paths.evaluations,
        paths.confirmations,
        paths.analysis,
        paths.best,
        paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.1",
        "created_utc": utc_timestamp(),
        "source_stage1_1_run": str(ctx.source_run),
        "source_stage2_run": str(source.run_dir),
        "target": copy.deepcopy(ctx.cfg["target"]),
        "horizon_steps": int(ctx.cfg["trajectory"]["horizon_steps"]),
        "horizon_ms": int(ctx.cfg["trajectory"]["horizon_ms"]),
        "n_modes": int(ctx.cfg["trajectory"]["n_modes"]),
        "node_steps": list(ctx.cfg["trajectory"]["node_steps"]),
        "parameter_dimension": int(len(ctx.coefficient_lower)),
        "hard_gate_changed_from_stage2": False,
        "search": copy.deepcopy(ctx.cfg["search"]),
        "objective": copy.deepcopy(ctx.cfg["objective"]),
        "surrogate": copy.deepcopy(ctx.cfg["surrogate"]),
        "temporary_workspace": {
            "tsc_workspace_root": ctx.env_cfg.get("tsc_workspace_root"),
            "tsc_run_root": ctx.env_cfg.get("run_root"),
            "ray_tmpdir": os.environ.get("RAY_TMPDIR", ""),
        },
    }
    if paths.manifest.exists():
        previous = read_json(paths.manifest)
        if Path(previous["source_stage2_run"]).resolve() != source.run_dir:
            raise ValueError("Existing Stage2.1 run points to a different source Stage2 run")
    else:
        atomic_write_json(paths.manifest, manifest)

    reference_files = (
        "stage2_config.resolved.json",
        "cem_state.json",
        "analysis/all_generation_results.csv",
        "analysis/hall_of_fame.csv",
        "analysis/stage2_analysis_summary.json",
        "best/best_candidate.json",
        "STAGE2_REPORT.md",
    )
    for relative in reference_files:
        src = source.run_dir / relative
        if not src.exists():
            continue
        dst = paths.source_reference / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
    return paths


# ---------------------------------------------------------------------------
# New objective: unchanged hard gate, smoother strict-boundary signal
# ---------------------------------------------------------------------------


def stage21_metrics(ctx: Any, result: dict[str, Any], decoded: dict[str, Any] | None) -> dict[str, Any]:
    metrics = dict(s2.stage2_metrics(ctx, result, decoded))
    if not metrics.get("success"):
        metrics.update(
            {
                "stage2_1_tube_excess_mean": 1e12,
                "stage2_1_tube_excess_max": 1e12,
                "stage2_1_tube_excess_terminal": 1e12,
                "stage2_1_continuous_objective": 1e12,
                "continuous_objective": 1e12,
                "selection_score": 99e6 + 1e12,
            }
        )
        return metrics

    trajectory = result.get("trajectory", [])
    if not trajectory:
        raise ValueError("Successful TSC result has no trajectory")
    target = np.asarray(
        [ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]],
        dtype=float,
    )
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    error = y - target[None, :]
    gate = ctx.cfg["gate"]
    objective_cfg = ctx.cfg["objective"]
    weights = objective_cfg.get("weights", {})
    tol = float(gate["precise_tolerance_m"])
    tube_n = max(1, min(int(objective_cfg.get("tube_window_steps", 5)), len(error)))
    late_n = max(1, min(int(gate.get("late_window_steps", 4)), len(error)))
    tube = error[-tube_n:, :2]
    late = error[-late_n:, :2]

    excess = np.maximum(np.abs(tube) - tol, 0.0) / max(tol, 1e-12)
    excess_step = np.sum(excess**2, axis=1)
    tube_excess_mean = float(np.mean(excess_step))
    tube_excess_max = float(np.max(excess_step))
    tube_excess_terminal = float(excess_step[-1])

    late_position_core = float(np.mean(np.sum((late / tol) ** 2, axis=1)))
    terminal_position_core = float(np.sum((error[-1, :2] / tol) ** 2))

    velocity_limit = float(gate["terminal_velocity_max_m_per_s"])
    late_velocity_limit = float(gate["late_velocity_rms_max_m_per_s"])
    terminal_velocity = float(metrics["terminal_velocity_m_per_s"])
    late_velocity = float(metrics["late_velocity_rms_m_per_s"])
    velocity_excess = float(
        max(terminal_velocity / velocity_limit - 1.0, 0.0) ** 2
        + max(late_velocity / late_velocity_limit - 1.0, 0.0) ** 2
    )
    velocity_core = float(
        (terminal_velocity / velocity_limit) ** 2
        + (late_velocity / late_velocity_limit) ** 2
    )

    required_streak = int(gate["required_terminal_streak_steps"])
    precise_streak = int(metrics.get("trailing_streak_within_30mm_steps", 0))
    streak_deficit = float(max(required_streak - precise_streak, 0) / max(required_streak, 1))
    ip_tolerance = float(gate["ip_tolerance_a"])
    ip_core = float((float(metrics["terminal_Ip_error_A"]) / ip_tolerance) ** 2)

    action_rms = 0.0
    delta_action_rms = 0.0
    repair_rms = 0.0
    if decoded is not None:
        action = np.asarray(decoded["action_norm_tsc"], dtype=float)
        action_rms = float(np.sqrt(np.mean(action**2)))
        delta_action_rms = float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2)))
        repair_rms = float(np.sqrt(np.mean(np.asarray(decoded["saturation_excess"], dtype=float) ** 2)))

    continuous = (
        float(weights.get("tube_excess_mean", 90.0)) * tube_excess_mean
        + float(weights.get("tube_excess_max", 120.0)) * tube_excess_max
        + float(weights.get("tube_excess_terminal", 60.0)) * tube_excess_terminal
        + float(weights.get("velocity_excess", 80.0)) * velocity_excess
        + float(weights.get("streak_deficit", 4.0)) * streak_deficit
        + float(weights.get("late_position_core", 1.5)) * late_position_core
        + float(weights.get("terminal_position_core", 1.0)) * terminal_position_core
        + float(weights.get("velocity_core", 2.5)) * velocity_core
        + float(weights.get("terminal_ip", 0.10)) * ip_core
        + float(weights.get("action_rms", 0.02)) * action_rms**2
        + float(weights.get("delta_action_rms", 0.04)) * delta_action_rms**2
        + float(weights.get("repair", 2.0)) * repair_rms**2
    )
    tier = int(metrics["gate_tier"])
    selection = tier * float(objective_cfg.get("tier_spacing", 1e6)) + continuous
    metrics.update(
        {
            "stage2_1_tube_window_steps": tube_n,
            "stage2_1_tube_excess_mean": tube_excess_mean,
            "stage2_1_tube_excess_max": tube_excess_max,
            "stage2_1_tube_excess_terminal": tube_excess_terminal,
            "stage2_1_late_position_core": late_position_core,
            "stage2_1_terminal_position_core": terminal_position_core,
            "stage2_1_velocity_excess": velocity_excess,
            "stage2_1_velocity_core": velocity_core,
            "stage2_1_streak_deficit": streak_deficit,
            "stage2_1_continuous_objective": float(continuous),
            "continuous_objective": float(continuous),
            "selection_score": float(selection),
            "action_rms": action_rms,
            "delta_action_rms": delta_action_rms,
            "repair_excess_rms": repair_rms,
        }
    )
    return metrics


# ---------------------------------------------------------------------------
# Archives and covariance helpers
# ---------------------------------------------------------------------------


def _finite(value: Any, fallback: float) -> float:
    number = _as_float(value, fallback)
    return number if math.isfinite(number) else fallback


def _damped_eligible(record: dict[str, Any], cfg: dict[str, Any]) -> bool:
    gate = cfg["gate"]
    archives = cfg["archives"]
    speed_factor = float(archives.get("speed_margin_factor", 1.05))
    speed_ok = (
        _finite(record.get("terminal_velocity_m_per_s"), 1e9)
        <= float(gate["terminal_velocity_max_m_per_s"]) * speed_factor
        and _finite(record.get("late_velocity_rms_m_per_s"), 1e9)
        <= float(gate["late_velocity_rms_max_m_per_s"]) * speed_factor
    )
    position_ok = (
        _finite(record.get("terminal_RZ_box_max_error_m"), 1e9)
        <= float(archives.get("damped_box_limit_m", 0.045))
        or _as_int(record.get("trailing_streak_within_40mm_steps"), 0)
        >= int(gate["required_terminal_streak_steps"])
    )
    ip_ok = abs(_finite(record.get("terminal_Ip_error_A"), 1e12)) <= float(gate["ip_tolerance_a"])
    return bool(speed_ok and position_ok and ip_ok)


def _precise_eligible(record: dict[str, Any], cfg: dict[str, Any]) -> bool:
    gate = cfg["gate"]
    archives = cfg["archives"]
    position_ok = (
        _finite(record.get("terminal_RZ_box_max_error_m"), 1e9)
        <= float(archives.get("precise_box_limit_m", 0.030))
        or _as_int(record.get("trailing_streak_within_30mm_steps"), 0)
        >= int(gate["required_terminal_streak_steps"])
    )
    ip_ok = abs(_finite(record.get("terminal_Ip_error_A"), 1e12)) <= float(gate["ip_tolerance_a"])
    return bool(position_ok and ip_ok)


def _damped_archive_score(record: dict[str, Any], cfg: dict[str, Any]) -> float:
    gate = cfg["gate"]
    tol = float(gate["precise_tolerance_m"])
    box = _finite(record.get("terminal_RZ_box_max_error_m"), 1.0)
    terminal_v = _finite(record.get("terminal_velocity_m_per_s"), 10.0)
    late_v = _finite(record.get("late_velocity_rms_m_per_s"), 10.0)
    late_pos = _finite(record.get("late_RZ_euclidean_rms_m"), 1.0)
    return float(
        60.0 * max(box - tol, 0.0) / tol
        + 3.0 * (terminal_v / float(gate["terminal_velocity_max_m_per_s"])) ** 2
        + 5.0 * (late_v / float(gate["late_velocity_rms_max_m_per_s"])) ** 2
        + 1.5 * (late_pos / tol) ** 2
    )


def _precise_archive_score(record: dict[str, Any], cfg: dict[str, Any]) -> float:
    gate = cfg["gate"]
    tol = float(gate["precise_tolerance_m"])
    box = _finite(record.get("terminal_RZ_box_max_error_m"), 1.0)
    late_pos = _finite(record.get("late_RZ_euclidean_rms_m"), 1.0)
    terminal_v = _finite(record.get("terminal_velocity_m_per_s"), 10.0)
    late_v = _finite(record.get("late_velocity_rms_m_per_s"), 10.0)
    return float(
        8.0 * (box / tol) ** 2
        + 3.0 * (late_pos / tol) ** 2
        + 0.30 * (terminal_v / float(gate["terminal_velocity_max_m_per_s"])) ** 2
        + 0.45 * (late_v / float(gate["late_velocity_rms_max_m_per_s"])) ** 2
    )


def _vector_distance(lhs: dict[str, Any], rhs: dict[str, Any]) -> float:
    return float(np.linalg.norm(_parse_vector(lhs["vector"]) - _parse_vector(rhs["vector"])))


def _dedupe_diverse_records(
    records: Sequence[dict[str, Any]],
    *,
    capacity: int,
    score_key: str,
    minimum_distance: float,
) -> list[dict[str, Any]]:
    ordered = sorted(records, key=lambda row: (_finite(row.get(score_key), 1e30), str(row.get("candidate_id"))))
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for record in ordered:
        candidate_id = str(record.get("candidate_id", ""))
        vector = _parse_vector(record["vector"])
        digest = vector_digest(vector, "v")
        if candidate_id in seen_ids or digest in seen_hashes:
            continue
        if selected and min(_vector_distance(record, other) for other in selected) < minimum_distance:
            continue
        copy_record = copy.deepcopy(record)
        copy_record["vector"] = vector.tolist()
        selected.append(copy_record)
        seen_ids.add(candidate_id)
        seen_hashes.add(digest)
        if len(selected) >= capacity:
            break
    # If diversity filtering was too strict, fill without the distance test.
    if len(selected) < capacity:
        for record in ordered:
            candidate_id = str(record.get("candidate_id", ""))
            vector = _parse_vector(record["vector"])
            digest = vector_digest(vector, "v")
            if candidate_id in seen_ids or digest in seen_hashes:
                continue
            copy_record = copy.deepcopy(record)
            copy_record["vector"] = vector.tolist()
            selected.append(copy_record)
            seen_ids.add(candidate_id)
            seen_hashes.add(digest)
            if len(selected) >= capacity:
                break
    return selected


def rebuild_archives(
    cfg: dict[str, Any],
    old_archives: dict[str, list[dict[str, Any]]],
    new_records: Sequence[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    all_records = list(old_archives.get("damped", [])) + list(old_archives.get("precise", [])) + list(new_records)
    damped: list[dict[str, Any]] = []
    precise: list[dict[str, Any]] = []
    for record in all_records:
        row = copy.deepcopy(record)
        if _damped_eligible(row, cfg):
            row["damped_archive_score"] = _damped_archive_score(row, cfg)
            damped.append(row)
        if _precise_eligible(row, cfg):
            row["precise_archive_score"] = _precise_archive_score(row, cfg)
            precise.append(row)
    minimum_distance = float(cfg["archives"].get("minimum_vector_distance", 0.035))
    return {
        "damped": _dedupe_diverse_records(
            damped,
            capacity=int(cfg["archives"].get("damped_capacity", 64)),
            score_key="damped_archive_score",
            minimum_distance=minimum_distance,
        ),
        "precise": _dedupe_diverse_records(
            precise,
            capacity=int(cfg["archives"].get("precise_capacity", 32)),
            score_key="precise_archive_score",
            minimum_distance=minimum_distance,
        ),
    }


def regularize_covariance(covariance: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    search = cfg["search"]
    covariance = np.asarray(covariance, dtype=float)
    covariance = 0.5 * (covariance + covariance.T)
    diagonal = np.diag(np.diag(covariance))
    shrink = float(search.get("covariance_diagonal_shrinkage", 0.18))
    covariance = (1.0 - shrink) * covariance + shrink * diagonal
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    eigenvalues = np.clip(
        eigenvalues,
        float(search.get("covariance_eigen_floor", 0.00015)),
        float(search.get("covariance_eigen_ceiling", 0.20)),
    )
    return (eigenvectors * eigenvalues[None, :]) @ eigenvectors.T


def fit_distribution(
    vectors: Sequence[np.ndarray],
    *,
    fallback_mean: np.ndarray,
    fallback_covariance: np.ndarray,
    cfg: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    if not vectors:
        return np.asarray(fallback_mean, dtype=float), regularize_covariance(fallback_covariance, cfg)
    matrix = np.vstack([np.asarray(vector, dtype=float).reshape(-1) for vector in vectors])
    mean = np.mean(matrix, axis=0)
    if len(matrix) >= 3:
        covariance = np.cov(matrix, rowvar=False, ddof=1)
    else:
        covariance = np.asarray(fallback_covariance, dtype=float)
    return mean, regularize_covariance(covariance, cfg)


def _archive_vectors(archive: Sequence[dict[str, Any]], limit: int | None = None) -> list[np.ndarray]:
    rows = archive if limit is None else archive[:limit]
    return [_parse_vector(row["vector"]) for row in rows]


# ---------------------------------------------------------------------------
# Optional velocity surrogate
# ---------------------------------------------------------------------------


def surrogate_features(vectors: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    x = np.asarray(vectors, dtype=float)
    if x.ndim == 1:
        x = x[None, :]
    center = 0.5 * (lower + upper)
    half = np.maximum(0.5 * (upper - lower), 1e-9)
    z = (x - center[None, :]) / half[None, :]
    nodes = z.reshape(len(z), 5, 3)
    first = np.diff(nodes, axis=1).reshape(len(z), -1)
    second = np.diff(nodes, n=2, axis=1).reshape(len(z), -1)
    cross = np.stack(
        [
            nodes[:, :, 0] * nodes[:, :, 1],
            nodes[:, :, 0] * nodes[:, :, 2],
            nodes[:, :, 1] * nodes[:, :, 2],
        ],
        axis=-1,
    ).reshape(len(z), -1)
    tail = nodes[:, 2:, :]
    summaries = np.concatenate(
        [
            np.mean(nodes, axis=1),
            np.std(nodes, axis=1),
            np.mean(tail, axis=1),
            np.std(tail, axis=1),
            np.max(np.abs(tail), axis=1),
        ],
        axis=1,
    )
    return np.concatenate([z, z**2, first, second, cross, summaries], axis=1)


def _ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    mean = np.mean(x, axis=0)
    scale = np.std(x, axis=0)
    scale = np.where(scale < 1e-10, 1.0, scale)
    xs = (x - mean[None, :]) / scale[None, :]
    design = np.column_stack([np.ones(len(xs)), xs])
    penalty = np.eye(design.shape[1]) * float(alpha)
    penalty[0, 0] = 0.0
    coefficient = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return {
        "feature_mean": mean,
        "feature_scale": scale,
        "coefficient": coefficient,
    }


def _ridge_predict(model: dict[str, Any], x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    mean = np.asarray(model["feature_mean"], dtype=float)
    scale = np.asarray(model["feature_scale"], dtype=float)
    coefficient = np.asarray(model["coefficient"], dtype=float)
    xs = (x - mean[None, :]) / scale[None, :]
    return np.column_stack([np.ones(len(xs)), xs]) @ coefficient


def _r2(y: np.ndarray, pred: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    denom = float(np.sum((y - np.mean(y)) ** 2))
    if denom <= 1e-15:
        return 0.0
    return float(1.0 - np.sum((y - pred) ** 2) / denom)


def fit_velocity_surrogate(
    ctx: Any,
    source: SourceStage2Data,
    stage21_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    cfg = ctx.cfg["surrogate"]
    if not bool(cfg.get("enabled", True)):
        return {"enabled": False, "reason": "disabled_by_config"}
    records: list[tuple[int, np.ndarray, float, float]] = []
    for row in list(source.rows) + list(stage21_rows):
        if not _as_bool(row.get("success"), False):
            continue
        terminal_v = _as_float(row.get("terminal_velocity_m_per_s"))
        late_v = _as_float(row.get("late_velocity_rms_m_per_s"))
        if not (math.isfinite(terminal_v) and math.isfinite(late_v)):
            continue
        try:
            vector = _parse_vector(row.get("parameter_vector"))
        except Exception:
            continue
        # Keep source and Stage2.1 generations separated. Stage2.1 receives +1000.
        generation = _as_int(row.get("generation"), 0)
        if str(row.get("stage", "")).startswith("Stage2.1"):
            generation += 1000
        records.append((generation, vector, terminal_v, late_v))
    minimum_samples = int(cfg.get("minimum_samples", 384))
    if len(records) < minimum_samples:
        return {"enabled": False, "reason": "not_enough_samples", "n_samples": len(records)}
    generations = sorted({record[0] for record in records})
    if len(generations) < int(cfg.get("minimum_generation_folds", 4)):
        return {"enabled": False, "reason": "not_enough_generation_folds", "n_folds": len(generations)}

    vectors = np.vstack([record[1] for record in records])
    y_terminal = np.asarray([record[2] for record in records], dtype=float)
    y_late = np.asarray([record[3] for record in records], dtype=float)
    group = np.asarray([record[0] for record in records], dtype=int)
    x = surrogate_features(
        vectors,
        np.asarray(ctx.coefficient_lower, dtype=float),
        np.asarray(ctx.coefficient_upper, dtype=float),
    )
    alpha = float(cfg.get("ridge_alpha", 0.01))
    pred_terminal = np.full(len(records), np.nan, dtype=float)
    pred_late = np.full(len(records), np.nan, dtype=float)
    fold_rows: list[dict[str, Any]] = []
    for generation in generations:
        test = group == generation
        train = ~test
        if np.sum(test) == 0 or np.sum(train) < 50:
            continue
        model_terminal = _ridge_fit(x[train], y_terminal[train], alpha)
        model_late = _ridge_fit(x[train], y_late[train], alpha)
        pred_terminal[test] = _ridge_predict(model_terminal, x[test])
        pred_late[test] = _ridge_predict(model_late, x[test])
        fold_rows.append(
            {
                "generation": int(generation),
                "n_test": int(np.sum(test)),
                "terminal_r2": _r2(y_terminal[test], pred_terminal[test]),
                "terminal_mae": float(np.mean(np.abs(y_terminal[test] - pred_terminal[test]))),
                "late_r2": _r2(y_late[test], pred_late[test]),
                "late_mae": float(np.mean(np.abs(y_late[test] - pred_late[test]))),
            }
        )
    valid = np.isfinite(pred_terminal) & np.isfinite(pred_late)
    if np.sum(valid) < minimum_samples:
        return {"enabled": False, "reason": "cross_validation_incomplete", "n_valid": int(np.sum(valid))}
    terminal_r2 = _r2(y_terminal[valid], pred_terminal[valid])
    late_r2 = _r2(y_late[valid], pred_late[valid])
    terminal_mae = float(np.mean(np.abs(y_terminal[valid] - pred_terminal[valid])))
    late_mae = float(np.mean(np.abs(y_late[valid] - pred_late[valid])))
    enabled = (
        terminal_r2 >= float(cfg.get("minimum_r2_terminal_velocity", 0.10))
        and late_r2 >= float(cfg.get("minimum_r2_late_velocity", 0.10))
        and terminal_mae <= float(cfg.get("maximum_mae_terminal_velocity", 0.16))
        and late_mae <= float(cfg.get("maximum_mae_late_velocity", 0.12))
    )
    summary: dict[str, Any] = {
        "enabled": bool(enabled),
        "reason": "validated" if enabled else "cross_validation_threshold_not_met",
        "n_samples": len(records),
        "n_features": int(x.shape[1]),
        "n_folds": len(fold_rows),
        "terminal_velocity_cv_r2": terminal_r2,
        "terminal_velocity_cv_mae": terminal_mae,
        "late_velocity_cv_r2": late_r2,
        "late_velocity_cv_mae": late_mae,
        "folds": fold_rows,
    }
    if enabled:
        terminal_model = _ridge_fit(x, y_terminal, alpha)
        late_model = _ridge_fit(x, y_late, alpha)
        summary["terminal_model"] = {
            key: np.asarray(value).tolist() for key, value in terminal_model.items()
        }
        summary["late_model"] = {key: np.asarray(value).tolist() for key, value in late_model.items()}
    return summary


def surrogate_predict(
    ctx: Any, surrogate: dict[str, Any], vectors: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    n = len(np.asarray(vectors))
    if not surrogate.get("enabled"):
        return np.full(n, np.nan), np.full(n, np.nan)
    x = surrogate_features(
        np.asarray(vectors, dtype=float),
        np.asarray(ctx.coefficient_lower, dtype=float),
        np.asarray(ctx.coefficient_upper, dtype=float),
    )
    terminal = _ridge_predict(surrogate["terminal_model"], x)
    late = _ridge_predict(surrogate["late_model"], x)
    return np.maximum(terminal, 0.0), np.maximum(late, 0.0)


# ---------------------------------------------------------------------------
# State initialization and proposal generation
# ---------------------------------------------------------------------------


def initial_state(ctx: Any, source: SourceStage2Data) -> dict[str, Any]:
    archives = rebuild_archives(ctx.cfg, {"damped": [], "precise": []}, source.records)
    if not archives["damped"]:
        raise RuntimeError("No speed-safe damped candidate could be recovered from source Stage2")
    if not archives["precise"]:
        raise RuntimeError("No precise-but-underdamped candidate could be recovered from source Stage2")

    source_mean = np.asarray(source.state.get("mean"), dtype=float)
    source_covariance = np.asarray(source.state.get("covariance"), dtype=float)
    if source_mean.shape != (15,) or source_covariance.shape != (15, 15):
        # Fallback to the best source vector and a conservative diagonal covariance.
        source_mean = _parse_vector(archives["damped"][0]["vector"])
        std = np.tile(np.asarray([0.12, 0.12, 0.05]), 5)
        source_covariance = np.diag(std**2)
    source_covariance = regularize_covariance(
        source_covariance * float(ctx.cfg["search"].get("global_covariance_scale", 0.35)),
        ctx.cfg,
    )
    damped_mean, damped_cov = fit_distribution(
        _archive_vectors(archives["damped"]),
        fallback_mean=source_mean,
        fallback_covariance=source_covariance,
        cfg=ctx.cfg,
    )
    precise_mean, precise_cov = fit_distribution(
        _archive_vectors(archives["precise"]),
        fallback_mean=source_mean,
        fallback_covariance=source_covariance,
        cfg=ctx.cfg,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.1",
        "generation": 0,
        "source_stage2_run": str(source.run_dir),
        "global_mean": source_mean.tolist(),
        "global_covariance": source_covariance.tolist(),
        "damped_mean": damped_mean.tolist(),
        "damped_covariance": damped_cov.tolist(),
        "precise_mean": precise_mean.tolist(),
        "precise_covariance": precise_cov.tolist(),
        "archives": archives,
        "best_selection_score": None,
        "best_candidate_id": None,
        "best_generation": None,
        "best_vector": None,
        "strict_gate_found": False,
        "generations_without_improvement": 0,
        "finished": False,
        "stop_reason": "",
        "rng_seed": int(ctx.cfg["search"].get("random_seed", 20260721)),
        "updated_utc": utc_timestamp(),
    }


def load_or_initialize_state(
    ctx: Any,
    source: SourceStage2Data,
    paths: Stage21Paths,
    *,
    no_resume: bool,
) -> dict[str, Any]:
    if no_resume:
        if paths.state.exists():
            raise FileExistsError(
                f"--no-resume requested but state already exists: {paths.state}. Use a new run directory."
            )
        state = initial_state(ctx, source)
        atomic_write_json(paths.state, state)
        return state
    if paths.state.exists():
        state = read_json(paths.state)
        if Path(state["source_stage2_run"]).resolve() != source.run_dir:
            raise ValueError("Stage2.1 state points to a different source Stage2 run")
        return state
    state = initial_state(ctx, source)
    atomic_write_json(paths.state, state)
    return state


def _sample_multivariate(
    rng: np.random.Generator,
    mean: np.ndarray,
    covariance: np.ndarray,
    n: int,
) -> np.ndarray:
    covariance = 0.5 * (covariance + covariance.T)
    try:
        factor = np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError:
        values, vectors = np.linalg.eigh(covariance)
        factor = vectors @ np.diag(np.sqrt(np.maximum(values, 1e-12)))
    half = (n + 1) // 2
    noise = rng.standard_normal((half, len(mean))) @ factor.T
    return np.vstack([mean + noise, mean - noise])[:n]


def _node_indices(cfg: dict[str, Any], key: str) -> list[int]:
    return [int(value) for value in cfg["search"].get(key, [])]


def _add_local_noise(
    rng: np.random.Generator,
    parent: np.ndarray,
    cfg: dict[str, Any],
    *,
    precise: bool,
) -> np.ndarray:
    nodes = np.asarray(parent, dtype=float).reshape(5, 3).copy()
    early_std = np.asarray(cfg["search"]["early_node_std_by_mode"], dtype=float)
    tail_std = np.asarray(cfg["search"]["tail_std_by_mode"], dtype=float)
    multipliers = np.asarray(cfg["search"]["tail_node_std_multiplier"], dtype=float)
    if precise:
        tail_std = tail_std * float(cfg["search"].get("precise_tail_std_multiplier", 1.25))
    for node_index in _node_indices(cfg, "early_node_indices"):
        nodes[node_index] += rng.normal(0.0, early_std, size=3)
    for local_index, node_index in enumerate(_node_indices(cfg, "tail_node_indices")):
        nodes[node_index] += rng.normal(0.0, tail_std * multipliers[local_index], size=3)
    return nodes.reshape(-1)


def bridge_vectors(
    rng: np.random.Generator,
    precise: np.ndarray,
    damped: np.ndarray,
    cfg: dict[str, Any],
    operator: int | None = None,
) -> np.ndarray:
    p = np.asarray(precise, dtype=float).reshape(5, 3)
    d = np.asarray(damped, dtype=float).reshape(5, 3)
    operator = int(rng.integers(0, 4)) if operator is None else int(operator)
    if operator == 0:
        nodes = np.vstack([p[:2], d[2:]])
    elif operator == 1:
        nodes = np.vstack([p[:3], d[3:]])
    elif operator == 2:
        alpha_front = float(rng.uniform(0.65, 0.90))
        alpha_tail = float(rng.uniform(0.10, 0.35))
        nodes = d.copy()
        nodes[:2] = alpha_front * p[:2] + (1.0 - alpha_front) * d[:2]
        nodes[2:] = alpha_tail * p[2:] + (1.0 - alpha_tail) * d[2:]
    elif operator == 3:
        nodes = d.copy()
        nodes[1:3] = 0.55 * p[1:3] + 0.45 * d[1:3]
        nodes[3:] = 0.20 * p[3:] + 0.80 * d[3:]
    else:
        raise ValueError(f"Unknown bridge operator {operator}")
    noise = np.asarray(cfg["search"]["bridge_noise_by_mode"], dtype=float)
    for node_index in _node_indices(cfg, "tail_node_indices"):
        nodes[node_index] += rng.normal(0.0, noise, size=3)
    return nodes.reshape(-1)


def _candidate_row(ctx: Any, vector: np.ndarray, source_name: str, source_type: str) -> dict[str, Any]:
    vector = _clip_vector(ctx, vector)
    decoded = s2.decode_vector(ctx, vector)
    linear = dict(s2.linear_prefilter_metrics(ctx, decoded))
    return {
        "candidate_id": vector_digest(vector, "proposal"),
        "vector": vector.tolist(),
        "source_name": source_name,
        "source_type": source_type,
        **linear,
    }


def _dedupe_candidate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        digest = vector_digest(_parse_vector(row["vector"]), "v")
        if digest in seen:
            continue
        seen.add(digest)
        result.append(row)
    return result


def _family_select(
    rng: np.random.Generator,
    rows: list[dict[str, Any]],
    *,
    quota: int,
    unranked_fraction: float,
) -> list[dict[str, Any]]:
    rows = _dedupe_candidate_rows(rows)
    if len(rows) <= quota:
        return rows
    unranked_count = min(quota, int(round(quota * unranked_fraction)))
    ranked_count = quota - unranked_count
    ordered = sorted(rows, key=lambda row: float(row.get("proposal_rank_score", 1e30)))
    selected = ordered[:ranked_count]
    remainder = ordered[ranked_count:]
    if unranked_count > 0 and remainder:
        indices = rng.choice(len(remainder), size=min(unranked_count, len(remainder)), replace=False)
        selected.extend(remainder[int(index)] for index in indices)
    if len(selected) < quota:
        selected_ids = {vector_digest(_parse_vector(row["vector"]), "v") for row in selected}
        for row in ordered:
            digest = vector_digest(_parse_vector(row["vector"]), "v")
            if digest in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(digest)
            if len(selected) >= quota:
                break
    return selected[:quota]


def _apply_surrogate_ranking(
    ctx: Any,
    rows: list[dict[str, Any]],
    surrogate: dict[str, Any],
) -> None:
    vectors = np.vstack([_parse_vector(row["vector"]) for row in rows])
    pred_terminal, pred_late = surrogate_predict(ctx, surrogate, vectors)
    cfg = ctx.cfg["surrogate"]
    terminal_limit = float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"])
    late_limit = float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"])
    for index, row in enumerate(rows):
        linear_score = float(row.get("linear_prefilter_score", 1e12))
        if surrogate.get("enabled"):
            velocity_score = (
                float(cfg.get("ranking_weight_terminal_velocity", 0.35))
                * (pred_terminal[index] / terminal_limit) ** 2
                + float(cfg.get("ranking_weight_late_velocity", 0.65))
                * (pred_late[index] / late_limit) ** 2
            )
            row["predicted_terminal_velocity_m_per_s"] = float(pred_terminal[index])
            row["predicted_late_velocity_rms_m_per_s"] = float(pred_late[index])
            row["proposal_rank_score"] = float(linear_score + velocity_score)
        else:
            row["predicted_terminal_velocity_m_per_s"] = math.nan
            row["predicted_late_velocity_rms_m_per_s"] = math.nan
            row["proposal_rank_score"] = linear_score


def _anchor_rows(ctx: Any, state: dict[str, Any], quota: int) -> list[dict[str, Any]]:
    damped = list(state["archives"]["damped"])
    precise = list(state["archives"]["precise"])
    rows: list[dict[str, Any]] = []
    # Prefer boundary-near damped candidates, then all available precise candidates.
    for index, record in enumerate(damped[: max(6, quota // 2)]):
        rows.append(_candidate_row(ctx, _parse_vector(record["vector"]), f"damped_archive_{index:02d}", "anchor_damped"))
    for index, record in enumerate(precise[: max(3, quota // 3)]):
        rows.append(_candidate_row(ctx, _parse_vector(record["vector"]), f"precise_archive_{index:02d}", "anchor_precise"))
    if state.get("best_vector") is not None:
        rows.insert(0, _candidate_row(ctx, _parse_vector(state["best_vector"]), "stage2_1_best", "anchor_best"))
    rows = _dedupe_candidate_rows(rows)
    # Fill the fixed anchor quota deterministically with additional damped archive
    # members and validated Stage1.1 seed vectors.
    if len(rows) < quota:
        for index, record in enumerate(damped):
            candidate = _candidate_row(
                ctx,
                _parse_vector(record["vector"]),
                f"damped_archive_fill_{index:02d}",
                "anchor_damped",
            )
            rows = _dedupe_candidate_rows([*rows, candidate])
            if len(rows) >= quota:
                break
    if len(rows) < quota:
        for seed_name in ("svd3_uniform_0.75", "svd3_uniform_0.85", "svd3_uniform_1.00"):
            if seed_name not in getattr(ctx, "seed_vectors", {}):
                continue
            rows = _dedupe_candidate_rows(
                [*rows, _candidate_row(ctx, ctx.seed_vectors[seed_name], seed_name, "anchor_seed")]
            )
            if len(rows) >= quota:
                break
    return rows[:quota]


def build_generation_manifest(
    ctx: Any,
    source: SourceStage2Data,
    state: dict[str, Any],
    paths: Stage21Paths,
    surrogate: dict[str, Any],
) -> dict[str, Any]:
    generation = int(state["generation"])
    generation_dir = paths.generations / f"gen_{generation:03d}"
    generation_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = generation_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)

    cfg = ctx.cfg
    search = cfg["search"]
    quota = {key: int(value) for key, value in search["family_quotas"].items()}
    population = int(search["population_size"])
    if sum(quota.values()) != population:
        raise ValueError(f"Stage2.1 family quotas sum to {sum(quota.values())}, expected {population}")
    seed = int(state["rng_seed"]) + generation * 100003
    rng = np.random.default_rng(seed)
    multiplier = max(1, int(search.get("proposal_pool_multiplier", 4)))
    damped_archive = list(state["archives"]["damped"])
    precise_archive = list(state["archives"]["precise"])
    if not damped_archive or not precise_archive:
        raise RuntimeError("Both Stage2.1 archives must be non-empty")

    families: dict[str, list[dict[str, Any]]] = {}
    families["anchors"] = _anchor_rows(ctx, state, quota["anchors"])

    # Eighteen exact +/- finite-difference probes around the best damped candidate:
    # 9 tail variables x 2 signs.
    center = _parse_vector(damped_archive[0]["vector"]).reshape(5, 3)
    sensitivity_rows: list[dict[str, Any]] = []
    delta_mode = np.asarray(search["sensitivity_delta_by_mode"], dtype=float)
    for node_index in _node_indices(cfg, "tail_node_indices"):
        for mode_index in range(3):
            for sign in (-1.0, 1.0):
                nodes = center.copy()
                nodes[node_index, mode_index] += sign * delta_mode[mode_index]
                sensitivity_rows.append(
                    _candidate_row(
                        ctx,
                        nodes.reshape(-1),
                        f"tail_fd_n{node_index}_m{mode_index}_{'p' if sign > 0 else 'm'}",
                        "sensitivity",
                    )
                )
    families["sensitivity"] = sensitivity_rows[: quota["sensitivity"]]

    damped_pool: list[dict[str, Any]] = []
    for index in range(max(quota["damped_tail"] * multiplier, quota["damped_tail"])):
        parent_index = int(rng.integers(0, min(len(damped_archive), 24)))
        parent = _parse_vector(damped_archive[parent_index]["vector"])
        vector = _add_local_noise(rng, parent, cfg, precise=False)
        damped_pool.append(_candidate_row(ctx, vector, f"damped_parent_{parent_index:02d}", "damped_tail"))
    families["damped_tail"] = damped_pool

    precise_pool: list[dict[str, Any]] = []
    for index in range(max(quota["precise_tail"] * multiplier, quota["precise_tail"])):
        parent_index = int(rng.integers(0, min(len(precise_archive), 16)))
        parent = _parse_vector(precise_archive[parent_index]["vector"])
        vector = _add_local_noise(rng, parent, cfg, precise=True)
        precise_pool.append(_candidate_row(ctx, vector, f"precise_parent_{parent_index:02d}", "precise_tail"))
    families["precise_tail"] = precise_pool

    bridge_pool: list[dict[str, Any]] = []
    for index in range(max(quota["bridge"] * multiplier, quota["bridge"])):
        precise_index = int(rng.integers(0, min(len(precise_archive), 16)))
        damped_index = int(rng.integers(0, min(len(damped_archive), 32)))
        vector = bridge_vectors(
            rng,
            _parse_vector(precise_archive[precise_index]["vector"]),
            _parse_vector(damped_archive[damped_index]["vector"]),
            cfg,
        )
        bridge_pool.append(
            _candidate_row(
                ctx,
                vector,
                f"bridge_p{precise_index:02d}_d{damped_index:02d}",
                "bridge",
            )
        )
    families["bridge"] = bridge_pool

    global_mean = np.asarray(state["global_mean"], dtype=float)
    global_cov = regularize_covariance(np.asarray(state["global_covariance"], dtype=float), cfg)
    global_vectors = _sample_multivariate(
        rng,
        global_mean,
        global_cov,
        max(quota["global"] * multiplier, quota["global"]),
    )
    families["global"] = [
        _candidate_row(ctx, vector, f"global_{index:04d}", "global")
        for index, vector in enumerate(global_vectors)
    ]

    random_pool: list[dict[str, Any]] = []
    radius = np.asarray(search["random_tail_radius_by_mode"], dtype=float)
    early_std = np.asarray(search["early_node_std_by_mode"], dtype=float)
    for index in range(max(quota["random_tail"] * multiplier, quota["random_tail"])):
        if rng.random() < 0.70:
            parent_record = damped_archive[int(rng.integers(0, min(len(damped_archive), 32)))]
        else:
            parent_record = precise_archive[int(rng.integers(0, min(len(precise_archive), 16)))]
        nodes = _parse_vector(parent_record["vector"]).reshape(5, 3).copy()
        for node_index in _node_indices(cfg, "early_node_indices"):
            nodes[node_index] += rng.normal(0.0, early_std * 0.5, size=3)
        for node_index in _node_indices(cfg, "tail_node_indices"):
            nodes[node_index] += rng.uniform(-radius, radius, size=3)
        random_pool.append(_candidate_row(ctx, nodes.reshape(-1), f"random_tail_{index:04d}", "random_tail"))
    families["random_tail"] = random_pool

    selected: list[dict[str, Any]] = []
    unranked_cfg = search.get("unranked_fraction_by_family", {})
    for family_name in ("anchors", "sensitivity", "damped_tail", "precise_tail", "bridge", "global", "random_tail"):
        rows = families[family_name]
        _apply_surrogate_ranking(ctx, rows, surrogate)
        if family_name in {"anchors", "sensitivity"}:
            family_selected = rows[: quota[family_name]]
        else:
            family_selected = _family_select(
                rng,
                rows,
                quota=quota[family_name],
                unranked_fraction=float(unranked_cfg.get(family_name, 0.50)),
            )
        selected.extend(family_selected)

    selected = _dedupe_candidate_rows(selected)
    # Extremely unlikely duplicate fill path; keep the population exactly 192.
    attempts = 0
    while len(selected) < population and attempts < population * 20:
        attempts += 1
        parent = _parse_vector(damped_archive[int(rng.integers(0, len(damped_archive)))]["vector"])
        vector = _add_local_noise(rng, parent, cfg, precise=False)
        row = _candidate_row(ctx, vector, f"duplicate_fill_{attempts:04d}", "fill")
        digest = vector_digest(_parse_vector(row["vector"]), "v")
        existing = {vector_digest(_parse_vector(item["vector"]), "v") for item in selected}
        if digest not in existing:
            _apply_surrogate_ranking(ctx, [row], surrogate)
            selected.append(row)
    if len(selected) != population:
        raise RuntimeError(f"Could construct only {len(selected)} unique candidates, expected {population}")

    for population_index, row in enumerate(selected):
        vector = _parse_vector(row["vector"])
        row["candidate_id"] = vector_digest(vector, f"s21g{generation:03d}")
        row["population_index"] = population_index
        row["generation"] = generation

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.1",
        "generation": generation,
        "random_seed": seed,
        "population_size": population,
        "family_quotas": quota,
        "surrogate_enabled": bool(surrogate.get("enabled")),
        "surrogate_validation": {
            key: value
            for key, value in surrogate.items()
            if key not in {"terminal_model", "late_model"}
        },
        "candidates": selected,
    }
    atomic_write_json(manifest_path, manifest)
    write_csv(generation_dir / "candidate_manifest.csv", selected)
    return manifest


def candidate_specs_from_manifest(ctx: Any, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    horizon = int(ctx.cfg["trajectory"]["horizon_steps"])
    specs: list[dict[str, Any]] = []
    for row in manifest["candidates"]:
        vector = _parse_vector(row["vector"])
        decoded = s2.decode_vector(ctx, vector)
        specs.append(
            {
                "kind": "stage2_1_candidate",
                "experiment_id": str(row["candidate_id"]),
                "candidate_id": str(row["candidate_id"]),
                "generation": int(manifest["generation"]),
                "population_index": int(row["population_index"]),
                "source_name": str(row["source_name"]),
                "source_type": str(row["source_type"]),
                "horizon_steps": horizon,
                "parameter_vector": vector.tolist(),
                "mode_nodes": decoded["nodes"].tolist(),
                "mode_coefficients": decoded["mode_coefficients"].tolist(),
                "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
                "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
                "linear_prefilter_score": float(row["linear_prefilter_score"]),
                "predicted_terminal_R_error_m": float(row["predicted_terminal_R_error_m"]),
                "predicted_terminal_Z_error_m": float(row["predicted_terminal_Z_error_m"]),
                "predicted_terminal_Ip_error_A": float(row["predicted_terminal_Ip_error_A"]),
                "predicted_terminal_velocity_m_per_s": _as_float(
                    row.get("predicted_terminal_velocity_m_per_s")
                ),
                "predicted_late_velocity_rms_m_per_s": _as_float(
                    row.get("predicted_late_velocity_rms_m_per_s")
                ),
            }
        )
    return specs


# ---------------------------------------------------------------------------
# Generation evaluation and state update
# ---------------------------------------------------------------------------


def summarize_generation(
    ctx: Any,
    manifest: dict[str, Any],
    results: Sequence[dict[str, Any]],
    paths: Stage21Paths,
) -> list[dict[str, Any]]:
    generation = int(manifest["generation"])
    generation_dir = paths.generations / f"gen_{generation:03d}"
    by_id = {str(result.get("experiment_id")): result for result in results}
    rows: list[dict[str, Any]] = []
    for candidate in manifest["candidates"]:
        candidate_id = str(candidate["candidate_id"])
        vector = _parse_vector(candidate["vector"])
        decoded = s2.decode_vector(ctx, vector)
        result = by_id.get(candidate_id)
        if result is None:
            metrics: dict[str, Any] = {
                "success": False,
                "failure_reason": "missing result",
                "gate_tier": 99,
                "gate_label": "MISSING_RESULT",
                "strict_gate_pass": False,
                "relaxed_gate_pass": False,
                "continuous_objective": 1e12,
                "selection_score": 99e6 + 1e12,
            }
        else:
            metrics = stage21_metrics(ctx, result, decoded)
        rows.append(
            {
                "stage": "Stage2.1",
                "generation": generation,
                "candidate_id": candidate_id,
                "population_index": int(candidate["population_index"]),
                "source_name": candidate["source_name"],
                "source_type": candidate["source_type"],
                "linear_prefilter_score": float(candidate["linear_prefilter_score"]),
                "proposal_rank_score": _as_float(candidate.get("proposal_rank_score")),
                "predicted_terminal_velocity_m_per_s": _as_float(
                    candidate.get("predicted_terminal_velocity_m_per_s")
                ),
                "predicted_late_velocity_rms_m_per_s": _as_float(
                    candidate.get("predicted_late_velocity_rms_m_per_s")
                ),
                "parameter_vector": vector.tolist(),
                "validation_id": candidate_id,
                **metrics,
            }
        )
    rows.sort(key=lambda row: float(row.get("selection_score", 99e6 + 1e12)))
    for rank, row in enumerate(rows, start=1):
        row["generation_rank"] = rank
    write_csv(generation_dir / "generation_results.csv", rows)
    atomic_write_json(generation_dir / "generation_results.json", rows)
    return rows


def _record_from_stage21_row(row: dict[str, Any], run_dir: Path) -> dict[str, Any] | None:
    record = _record_from_csv_row(row, source_run=run_dir)
    if record is None:
        return None
    record["stage"] = "Stage2.1"
    for key in (
        "stage2_1_tube_excess_mean",
        "stage2_1_tube_excess_max",
        "stage2_1_tube_excess_terminal",
        "stage2_1_continuous_objective",
    ):
        record[key] = _as_float(row.get(key))
    return record


def _save_best_candidate(
    ctx: Any,
    paths: Stage21Paths,
    row: dict[str, Any],
    result: dict[str, Any] | None,
) -> None:
    paths.best.mkdir(parents=True, exist_ok=True)
    atomic_write_json(paths.best / "best_candidate.json", row)
    vector = _parse_vector(row["parameter_vector"])
    decoded = s2.decode_vector(ctx, vector)
    action_rows: list[dict[str, Any]] = []
    for step, action in enumerate(np.asarray(decoded["action_norm_tsc"], dtype=float)):
        action_rows.append(
            {
                "step_index": step,
                "mode_1": float(decoded["mode_coefficients"][step, 0]),
                "mode_2": float(decoded["mode_coefficients"][step, 1]),
                "mode_3": float(decoded["mode_coefficients"][step, 2]),
                "action_norm_tsc": action.tolist(),
                "action_norm_display": np.asarray(decoded["action_norm_display"])[step].tolist(),
            }
        )
    write_csv(paths.best / "best_action_sequence.csv", action_rows)
    if result is not None:
        atomic_write_json_gz(paths.best / "best_tsc_result.json.gz", result)


def update_state(
    ctx: Any,
    state: dict[str, Any],
    rows: list[dict[str, Any]],
    results: Sequence[dict[str, Any]],
    paths: Stage21Paths,
) -> dict[str, Any]:
    generation = int(state["generation"])
    successful_records = [
        record
        for row in rows
        if (record := _record_from_stage21_row(row, paths.run_dir)) is not None
    ]
    archives = rebuild_archives(ctx.cfg, state["archives"], successful_records)
    if not archives["damped"] or not archives["precise"]:
        raise RuntimeError("Archive update unexpectedly emptied one Stage2.1 family")

    elite_count = int(ctx.cfg["search"].get("archive_elite_count", 20))
    successful_rows = [row for row in rows if _as_bool(row.get("success"), False)]
    successful_rows.sort(key=lambda row: float(row["selection_score"]))
    global_vectors = [_parse_vector(row["parameter_vector"]) for row in successful_rows[:elite_count]]
    old_global_mean = np.asarray(state["global_mean"], dtype=float)
    old_global_cov = np.asarray(state["global_covariance"], dtype=float)
    global_mean, global_cov = fit_distribution(
        global_vectors,
        fallback_mean=old_global_mean,
        fallback_covariance=old_global_cov,
        cfg=ctx.cfg,
    )
    damped_mean, damped_cov = fit_distribution(
        _archive_vectors(archives["damped"], elite_count),
        fallback_mean=np.asarray(state["damped_mean"], dtype=float),
        fallback_covariance=np.asarray(state["damped_covariance"], dtype=float),
        cfg=ctx.cfg,
    )
    precise_mean, precise_cov = fit_distribution(
        _archive_vectors(archives["precise"], elite_count),
        fallback_mean=np.asarray(state["precise_mean"], dtype=float),
        fallback_covariance=np.asarray(state["precise_covariance"], dtype=float),
        cfg=ctx.cfg,
    )

    best_row = successful_rows[0] if successful_rows else None
    best_score = None if best_row is None else float(best_row["selection_score"])
    previous_score = state.get("best_selection_score")
    meaningful = float(ctx.cfg["search"].get("meaningful_improvement", 0.0001))
    improved = best_score is not None and (
        previous_score is None or best_score < float(previous_score) - meaningful
    )
    strict_this_generation = any(_as_bool(row.get("strict_gate_pass"), False) for row in successful_rows)
    strict_found = bool(state.get("strict_gate_found", False) or strict_this_generation)
    generations_without = 0 if improved else int(state.get("generations_without_improvement", 0)) + 1

    new_state = copy.deepcopy(state)
    new_state.update(
        {
            "generation": generation + 1,
            "global_mean": global_mean.tolist(),
            "global_covariance": global_cov.tolist(),
            "damped_mean": damped_mean.tolist(),
            "damped_covariance": damped_cov.tolist(),
            "precise_mean": precise_mean.tolist(),
            "precise_covariance": precise_cov.tolist(),
            "archives": archives,
            "strict_gate_found": strict_found,
            "generations_without_improvement": generations_without,
            "last_generation_best": None
            if best_row is None
            else {
                "candidate_id": best_row["candidate_id"],
                "selection_score": best_score,
                "gate_tier": int(best_row["gate_tier"]),
                "gate_label": best_row["gate_label"],
                "continuous_objective": float(best_row["continuous_objective"]),
            },
            "updated_utc": utc_timestamp(),
        }
    )
    if improved and best_row is not None:
        new_state["best_selection_score"] = best_score
        new_state["best_candidate_id"] = best_row["candidate_id"]
        new_state["best_generation"] = generation
        new_state["best_vector"] = _parse_vector(best_row["parameter_vector"]).tolist()
        by_id = {str(result.get("experiment_id")): result for result in results}
        _save_best_candidate(ctx, paths, best_row, by_id.get(str(best_row["candidate_id"])))

    max_generations = int(ctx.cfg["search"]["max_generations"])
    patience = int(ctx.cfg["search"].get("strict_patience_generations", 2))
    if new_state["generation"] >= max_generations:
        new_state["finished"] = True
        new_state["stop_reason"] = "max_generations"
    elif strict_found and generations_without >= patience:
        new_state["finished"] = True
        new_state["stop_reason"] = "strict_gate_patience"
    else:
        new_state["finished"] = False
        new_state["stop_reason"] = ""
    atomic_write_json(paths.state, new_state)
    return new_state


def aggregate_generation_rows(paths: Stage21Paths) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths.generations.glob("gen_*/generation_results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            rows.extend(dict(row) for row in payload)
    return rows


def run_one_generation(
    ctx: Any,
    source: SourceStage2Data,
    paths: Stage21Paths,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    state = read_json(paths.state)
    if state.get("finished"):
        return state
    historical_rows = aggregate_generation_rows(paths)
    surrogate = fit_velocity_surrogate(ctx, source, historical_rows)
    atomic_write_json(paths.analysis / "velocity_surrogate.json", surrogate)
    manifest = build_generation_manifest(ctx, source, state, paths, surrogate)
    specs = candidate_specs_from_manifest(ctx, manifest)
    evaluation_dir = paths.evaluations / f"gen_{int(manifest['generation']):03d}"
    wall_start = time.monotonic()
    results = s2.evaluate_specs(
        ctx,
        specs,
        output_dir=evaluation_dir,
        backend=backend,
        resume=resume,
    )
    rows = summarize_generation(ctx, manifest, results, paths)
    state = update_state(ctx, state, rows, results, paths)
    state["last_generation_wall_time_s"] = float(time.monotonic() - wall_start)
    atomic_write_json(paths.state, state)
    print(
        json.dumps(
            {
                "stage": "Stage2.1",
                "generation": int(manifest["generation"]),
                "successful": sum(_as_bool(row.get("success"), False) for row in rows),
                "population": len(rows),
                "strict": sum(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
                "relaxed": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in rows),
                "best": None
                if not rows
                else {
                    key: rows[0].get(key)
                    for key in (
                        "candidate_id",
                        "gate_label",
                        "selection_score",
                        "terminal_R_error_m",
                        "terminal_Z_error_m",
                        "terminal_velocity_m_per_s",
                        "late_velocity_rms_m_per_s",
                    )
                },
                "next_generation": state["generation"],
                "finished": state["finished"],
                "stop_reason": state["stop_reason"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )
    return state


def run_optimization(
    ctx: Any,
    source: SourceStage2Data,
    paths: Stage21Paths,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    state = read_json(paths.state)
    while not state.get("finished"):
        state = run_one_generation(ctx, source, paths, backend=backend, resume=resume)
    return state


# ---------------------------------------------------------------------------
# Confirmation and analysis
# ---------------------------------------------------------------------------


def _top_unique_rows(rows: Sequence[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    ordered = sorted(
        [row for row in rows if _as_bool(row.get("success"), False)],
        key=lambda row: float(row.get("selection_score", 99e6 + 1e12)),
    )
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in ordered:
        digest = vector_digest(_parse_vector(row["parameter_vector"]), "v")
        if digest in seen:
            continue
        seen.add(digest)
        selected.append(row)
        if len(selected) >= k:
            break
    return selected


def run_confirmation(
    ctx: Any,
    paths: Stage21Paths,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    rows = aggregate_generation_rows(paths)
    top_k = int(ctx.cfg["confirmation"].get("top_k_candidates", 5))
    repeats = int(ctx.cfg["confirmation"].get("repeats_per_candidate", 3))
    candidates = _top_unique_rows(rows, top_k)
    if not candidates:
        verdict = {"verdict": "NO_SUCCESSFUL_STAGE2_1_CANDIDATE", "created_utc": utc_timestamp()}
        atomic_write_json(paths.confirmations / "stage2_1_verdict.json", verdict)
        return verdict

    specs: list[dict[str, Any]] = []
    for rank, row in enumerate(candidates, start=1):
        vector = _parse_vector(row["parameter_vector"])
        decoded = s2.decode_vector(ctx, vector)
        for repeat in range(repeats):
            experiment_id = f"s21confirm_rank{rank:02d}_{row['candidate_id']}_r{repeat:02d}"
            specs.append(
                {
                    "kind": "stage2_1_confirmation",
                    "experiment_id": experiment_id,
                    "candidate_id": row["candidate_id"],
                    "hall_of_fame_rank": rank,
                    "confirmation_repeat": repeat,
                    "generation": int(row["generation"]),
                    "population_index": int(row["population_index"]),
                    "source_name": "stage2_1_hall_of_fame",
                    "source_type": "confirmation",
                    "horizon_steps": int(ctx.cfg["trajectory"]["horizon_steps"]),
                    "parameter_vector": vector.tolist(),
                    "mode_nodes": decoded["nodes"].tolist(),
                    "mode_coefficients": decoded["mode_coefficients"].tolist(),
                    "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
                    "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
                    "linear_prefilter_score": float(row["linear_prefilter_score"]),
                    "predicted_terminal_R_error_m": _as_float(row.get("predicted_terminal_R_error_m")),
                    "predicted_terminal_Z_error_m": _as_float(row.get("predicted_terminal_Z_error_m")),
                    "predicted_terminal_Ip_error_A": _as_float(row.get("predicted_terminal_Ip_error_A")),
                }
            )
    results = s2.evaluate_specs(
        ctx,
        specs,
        output_dir=paths.confirmations / "raw",
        backend=backend,
        resume=resume,
    )
    spec_by_id = {spec["experiment_id"]: spec for spec in specs}
    metric_rows: list[dict[str, Any]] = []
    for result in results:
        spec = spec_by_id[str(result["experiment_id"])]
        vector = _parse_vector(spec["parameter_vector"])
        decoded = s2.decode_vector(ctx, vector)
        metrics = stage21_metrics(ctx, result, decoded)
        metric_rows.append(
            {
                "stage": "Stage2.1 confirmation",
                "experiment_id": result["experiment_id"],
                "candidate_id": spec["candidate_id"],
                "hall_of_fame_rank": spec["hall_of_fame_rank"],
                "repeat": spec["confirmation_repeat"],
                "parameter_vector": vector.tolist(),
                **metrics,
            }
        )
    write_csv(paths.confirmations / "confirmation_results.csv", metric_rows)
    atomic_write_json(paths.confirmations / "confirmation_results.json", metric_rows)

    summary_rows: list[dict[str, Any]] = []
    for rank, candidate in enumerate(candidates, start=1):
        candidate_rows = [row for row in metric_rows if row["candidate_id"] == candidate["candidate_id"]]
        successful = [row for row in candidate_rows if _as_bool(row.get("success"), False)]
        summary_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "hall_of_fame_rank": rank,
                "repeats": repeats,
                "successful_repeats": len(successful),
                "all_repeats_strict_gate": len(successful) == repeats
                and all(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
                "all_repeats_relaxed_gate": len(successful) == repeats
                and all(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful),
                "worst_gate_tier": max((_as_int(row.get("gate_tier"), 99) for row in candidate_rows), default=99),
                "mean_terminal_RZ_error_m": float(
                    np.mean([_as_float(row.get("terminal_RZ_euclidean_error_m")) for row in successful])
                )
                if successful
                else math.nan,
                "max_terminal_velocity_m_per_s": max(
                    (_as_float(row.get("terminal_velocity_m_per_s"), 1e9) for row in successful),
                    default=math.nan,
                ),
                "max_late_velocity_rms_m_per_s": max(
                    (_as_float(row.get("late_velocity_rms_m_per_s"), 1e9) for row in successful),
                    default=math.nan,
                ),
            }
        )
    write_csv(paths.confirmations / "confirmation_summary.csv", summary_rows)
    atomic_write_json(paths.confirmations / "confirmation_summary.json", summary_rows)
    if any(row["all_repeats_strict_gate"] for row in summary_rows):
        verdict_name = "PASS_PRECISE_HOLD_30MM_CONFIRMED"
    elif any(row["all_repeats_relaxed_gate"] for row in summary_rows):
        verdict_name = "PASS_DAMPED_HOLD_40MM_CONFIRMED_ONLY"
    else:
        verdict_name = "NO_CONFIRMED_HOLD"
    verdict = {
        "verdict": verdict_name,
        "created_utc": utc_timestamp(),
        "hard_gate_changed_from_stage2": False,
        "candidate_summaries": summary_rows,
    }
    atomic_write_json(paths.confirmations / "stage2_1_verdict.json", verdict)
    print(json.dumps(verdict, indent=2, ensure_ascii=False), flush=True)
    return verdict


def _plot_analysis(ctx: Any, rows: list[dict[str, Any]], best_result: dict[str, Any] | None, paths: Stage21Paths) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[Stage2.1 analysis] matplotlib unavailable; plots skipped: {exc}", flush=True)
        return
    if rows:
        x = [_as_float(row.get("terminal_RZ_euclidean_error_m")) * 1000.0 for row in rows]
        y = [_as_float(row.get("late_velocity_rms_m_per_s")) for row in rows]
        tier = [_as_int(row.get("gate_tier"), 99) for row in rows]
        plt.figure(figsize=(8, 6))
        scatter = plt.scatter(x, y, c=tier, s=15, alpha=0.65)
        plt.axvline(30.0, linestyle="--", linewidth=1)
        plt.axvline(40.0, linestyle="--", linewidth=1)
        plt.axhline(float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"]), linestyle="--", linewidth=1)
        plt.xlabel("Terminal R-Z Euclidean error [mm]")
        plt.ylabel("Late velocity RMS [m/s]")
        plt.title("Stage2.1 accuracy-damping map")
        plt.colorbar(scatter, label="Gate tier")
        plt.tight_layout()
        plt.savefig(paths.analysis / "accuracy_damping_scatter.png", dpi=160)
        plt.close()

        by_generation: dict[int, float] = {}
        for row in rows:
            generation = _as_int(row.get("generation"), 0)
            score = _as_float(row.get("selection_score"), 1e30)
            by_generation[generation] = min(by_generation.get(generation, 1e30), score)
        plt.figure(figsize=(8, 5))
        generations = sorted(by_generation)
        plt.plot(generations, [by_generation[g] for g in generations], marker="o")
        plt.xlabel("Generation")
        plt.ylabel("Best selection score")
        plt.title("Stage2.1 best objective by generation")
        plt.tight_layout()
        plt.savefig(paths.analysis / "objective_by_generation.png", dpi=160)
        plt.close()

    if best_result and best_result.get("success") and best_result.get("trajectory"):
        trajectory = best_result["trajectory"]
        r = [(float(row["R"]) - float(ctx.cfg["target"]["R"])) * 1000.0 for row in trajectory]
        z = [(float(row["Z"]) - float(ctx.cfg["target"]["Z"])) * 1000.0 for row in trajectory]
        plt.figure(figsize=(7, 7))
        plt.plot(r, z, marker="o")
        for tol_mm in (30.0, 40.0):
            box_x = [-tol_mm, tol_mm, tol_mm, -tol_mm, -tol_mm]
            box_y = [-tol_mm, -tol_mm, tol_mm, tol_mm, -tol_mm]
            plt.plot(box_x, box_y, linestyle="--", linewidth=1)
        plt.scatter([0.0], [0.0], marker="x", s=80)
        plt.xlabel("R error [mm]")
        plt.ylabel("Z error [mm]")
        plt.title("Stage2.1 best real-TSC trajectory")
        plt.axis("equal")
        plt.tight_layout()
        plt.savefig(paths.analysis / "best_trajectory_rz.png", dpi=160)
        plt.close()


def analyze_stage21(ctx: Any, source: SourceStage2Data, paths: Stage21Paths) -> dict[str, Any]:
    rows = aggregate_generation_rows(paths)
    write_csv(paths.analysis / "all_generation_results.csv", rows)
    atomic_write_json(paths.analysis / "all_generation_results.json", rows)
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    hall = _top_unique_rows(successful, 50)
    write_csv(paths.analysis / "hall_of_fame.csv", hall)
    atomic_write_json(paths.analysis / "hall_of_fame.json", hall)
    state = read_json(paths.state)
    verdict_path = paths.confirmations / "stage2_1_verdict.json"
    verdict = read_json(verdict_path) if verdict_path.exists() else {"verdict": "NOT_CONFIRMED"}

    best_result: dict[str, Any] | None = None
    best_candidate = hall[0] if hall else None
    if best_candidate is not None:
        generation = _as_int(best_candidate["generation"], 0)
        result_path = paths.evaluations / f"gen_{generation:03d}" / f"{best_candidate['candidate_id']}.json.gz"
        if result_path.exists():
            best_result = read_json_gz(result_path)
            _save_best_candidate(ctx, paths, best_candidate, best_result)
    _plot_analysis(ctx, rows, best_result, paths)

    source_strict = sum(_as_bool(row.get("strict_gate_pass"), False) for row in source.rows)
    source_relaxed = sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in source.rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.1",
        "created_utc": utc_timestamp(),
        "source_stage2_run": str(source.run_dir),
        "n_evaluations": len(rows),
        "n_successful": len(successful),
        "n_strict_gate": sum(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
        "n_relaxed_gate": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful),
        "source_stage2_n_strict_gate": source_strict,
        "source_stage2_n_relaxed_gate": source_relaxed,
        "damped_archive_size": len(state["archives"]["damped"]),
        "precise_archive_size": len(state["archives"]["precise"]),
        "verdict": verdict["verdict"],
        "best": best_candidate,
        "state": {
            key: state.get(key)
            for key in (
                "generation",
                "strict_gate_found",
                "finished",
                "stop_reason",
                "best_candidate_id",
                "best_selection_score",
            )
        },
    }
    atomic_write_json(paths.analysis / "stage2_1_analysis_summary.json", summary)

    report_lines = [
        "# Stage2.1 Report",
        "",
        f"- Source Stage2 run: `{source.run_dir}`",
        f"- Real-TSC evaluations: **{len(rows)}**",
        f"- Successful evaluations: **{len(successful)}**",
        f"- Strict 30 mm gates: **{summary['n_strict_gate']}**",
        f"- Relaxed 40 mm gates: **{summary['n_relaxed_gate']}**",
        f"- Confirmation verdict: **{summary['verdict']}**",
        f"- Damped archive: **{summary['damped_archive_size']}**",
        f"- Precise-but-underdamped archive: **{summary['precise_archive_size']}**",
        "",
        "## Method",
        "",
        "The Stage2 hard gate was not loosened. Stage2.1 warm-started from the completed Stage2 run, kept independent damped and precise archives, concentrated search on the final three nodes, and used explicit precise-front/damped-tail bridges.",
        "",
        "The continuous objective uses mean, maximum and terminal excess outside the 30 mm box over the final window. This is a ranking signal only; strict success still requires the original final-three-step, velocity and Ip conditions.",
        "",
    ]
    if best_candidate is not None:
        report_lines.extend(
            [
                "## Best candidate",
                "",
                f"- Candidate: `{best_candidate['candidate_id']}`",
                f"- Gate: **{best_candidate['gate_label']}**",
                f"- R error: **{_as_float(best_candidate.get('terminal_R_error_m')) * 1000.0:.3f} mm**",
                f"- Z error: **{_as_float(best_candidate.get('terminal_Z_error_m')) * 1000.0:.3f} mm**",
                f"- Terminal velocity: **{_as_float(best_candidate.get('terminal_velocity_m_per_s')):.6f} m/s**",
                f"- Late velocity RMS: **{_as_float(best_candidate.get('late_velocity_rms_m_per_s')):.6f} m/s**",
                "",
            ]
        )
    (paths.run_dir / "STAGE2_1_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    return summary


# ---------------------------------------------------------------------------
# Deterministic self-test
# ---------------------------------------------------------------------------


def synthetic_self_test() -> dict[str, Any]:
    # Smooth tube excess must distinguish points just outside the hard boundary.
    tol = 0.03
    def excess(mm: float) -> float:
        return max(mm / 1000.0 - tol, 0.0) ** 2 / tol**2
    assert excess(31.0) < excess(32.0) < excess(39.0)

    cfg = {
        "search": {
            "bridge_noise_by_mode": [0.0, 0.0, 0.0],
            "tail_node_indices": [2, 3, 4],
        }
    }
    rng = np.random.default_rng(1)
    precise = np.arange(15, dtype=float)
    damped = np.arange(15, dtype=float) + 100.0
    bridge0 = bridge_vectors(rng, precise, damped, cfg, operator=0).reshape(5, 3)
    assert np.allclose(bridge0[:2], precise.reshape(5, 3)[:2])
    assert np.allclose(bridge0[2:], damped.reshape(5, 3)[2:])
    bridge1 = bridge_vectors(rng, precise, damped, cfg, operator=1).reshape(5, 3)
    assert np.allclose(bridge1[:3], precise.reshape(5, 3)[:3])
    assert np.allclose(bridge1[3:], damped.reshape(5, 3)[3:])

    feature = surrogate_features(
        np.zeros((2, 15)),
        -np.ones(15),
        np.ones(15),
    )
    assert feature.shape[0] == 2 and feature.shape[1] > 45
    result = {
        "tube_excess_monotonic": True,
        "bridge_front_tail_semantics": True,
        "surrogate_feature_dimension": int(feature.shape[1]),
    }
    return result


# ---------------------------------------------------------------------------
# Public entry point used by the CLI wrapper
# ---------------------------------------------------------------------------


def execute(
    *,
    command: str,
    config_path: str | Path,
    source_stage1_1_run: str | Path | None,
    source_stage2_run: str | Path | None,
    run_dir: str | Path | None,
    backend: str,
    no_resume: bool,
) -> Any:
    if command == "self-test":
        result = synthetic_self_test()
        print(json.dumps(result, indent=2), flush=True)
        return result
    ctx = s2.load_stage2_config(
        config_path,
        source_run=source_stage1_1_run,
        run_dir_override=run_dir,
    )
    source = load_source_stage2(ctx, source_stage2_run)
    paths = initialize_stage21_run(ctx, source)
    load_or_initialize_state(ctx, source, paths, no_resume=no_resume)
    resume = not no_resume
    if command == "prepare":
        result = read_json(paths.state)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
        return result
    if command == "generation":
        return run_one_generation(ctx, source, paths, backend=backend, resume=resume)
    if command == "optimize":
        return run_optimization(ctx, source, paths, backend=backend, resume=resume)
    if command == "confirm":
        return run_confirmation(ctx, paths, backend=backend, resume=resume)
    if command == "analyze":
        return analyze_stage21(ctx, source, paths)
    if command == "all":
        run_optimization(ctx, source, paths, backend=backend, resume=resume)
        run_confirmation(ctx, paths, backend=backend, resume=resume)
        return analyze_stage21(ctx, source, paths)
    raise ValueError(f"Unknown command: {command}")


__all__ = [
    "Stage21Paths",
    "SourceStage2Data",
    "analyze_stage21",
    "bridge_vectors",
    "build_generation_manifest",
    "candidate_specs_from_manifest",
    "execute",
    "fit_velocity_surrogate",
    "initial_state",
    "load_source_stage2",
    "rebuild_archives",
    "run_confirmation",
    "run_one_generation",
    "run_optimization",
    "stage21_metrics",
    "surrogate_features",
    "synthetic_self_test",
]
