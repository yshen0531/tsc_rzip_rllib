"""Stage2.2 strict-corner feasibility search for real-TSC trajectory control.

Stage2.2 is a focused continuation of the validated Stage2 and Stage2.1
pipeline.  It does not change the plant model, the three SVD action modes, the
five-node/100 ms trajectory parameterization, or the hard success gate.

The source data are the complete Stage2 and Stage2.1 real-TSC runs.  Stage2.2
recomputes the final-three-sample position condition directly from every raw
trajectory, merges and deduplicates the two histories, and searches around the
narrow intersection of:

* final three R/Z samples inside the +/-30 mm rectangular box;
* terminal R/Z speed <= 0.10 m/s;
* late-window R/Z speed RMS <= 0.10 m/s;
* terminal Ip error inside the unchanged safety tolerance.

The optimizer maintains independent damped, precise, corner and strict
archives.  Its primary score is the largest normalized hard-constraint
violation, followed by total and L2 violation.  Real TSC remains the only source
of hard-gate truth.  Linear and learned surrogates are proposal-ranking aids
only.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as jsonio
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage2_1_trajectory_optimization as s21


SCHEMA_VERSION = 1
STATE_FILENAME = "stage2_2_state.json"
MANIFEST_FILENAME = "stage2_2_manifest.json"
SOURCE_CATALOG_FILENAME = "source_candidate_catalog.json.gz"
SOURCE_CATALOG_SUMMARY_FILENAME = "source_candidate_catalog_summary.json"

_REQUIRED_SYMBOLS: tuple[tuple[Any, str], ...] = (
    (s2, "load_stage2_config"),
    (s2, "initialize_stage2_run"),
    (s2, "decode_vector"),
    (s2, "linear_prefilter_metrics"),
    (s2, "stage2_metrics"),
    (s2, "evaluate_specs"),
    (s21, "surrogate_features"),
    (s21, "_ridge_fit"),
    (s21, "_ridge_predict"),
    (s21, "_r2"),
)
for _module, _symbol in _REQUIRED_SYMBOLS:
    if not hasattr(_module, _symbol):
        raise ImportError(
            "The standalone Stage2.2 tree is incomplete; missing bundled symbol "
            f"{_module.__name__}.{_symbol}"
        )


# ---------------------------------------------------------------------------
# Strict JSON / CSV helpers
# ---------------------------------------------------------------------------


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_json(path: Path | str) -> dict[str, Any]:
    payload = jsonio.read_json(path)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object in {path}")
    return payload


def read_json_any(path: Path | str) -> Any:
    return jsonio.read_json_any(path)


def read_json_gz(path: Path | str) -> dict[str, Any]:
    payload = jsonio.read_json_gz(path)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected compressed JSON object in {path}")
    return payload


def atomic_write_json(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json(path, payload)


def atomic_write_json_gz(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json_gz(path, payload)


def strict_json_text(payload: Any, *, indent: int = 2) -> str:
    safe = jsonio.json_safe_value(payload, nonfinite="raise")
    return json.dumps(safe, indent=indent, ensure_ascii=False, allow_nan=False)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, np.ndarray)):
        safe = jsonio.json_safe_value(value, nonfinite="null")
        return json.dumps(safe, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else ""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
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


def _as_float(value: Any, default: float = math.nan) -> float:
    try:
        if value is None or value == "":
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _finite(value: Any, fallback: float) -> float:
    number = _as_float(value, fallback)
    return number if math.isfinite(number) else fallback


def _finite_or_none(value: Any) -> float | None:
    number = _as_float(value, math.nan)
    return float(number) if math.isfinite(number) else None


def _finite_values(values: Iterable[Any]) -> list[float]:
    output: list[float] = []
    for value in values:
        number = _finite_or_none(value)
        if number is not None:
            output.append(number)
    return output


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


def vector_digest(vector: np.ndarray, prefix: str = "s22") -> str:
    rounded = np.round(np.asarray(vector, dtype=float).reshape(-1), 10)
    return f"{prefix}_{hashlib.sha256(rounded.tobytes()).hexdigest()[:16]}"


def _clip_vector(ctx: Any, vector: np.ndarray) -> np.ndarray:
    clipped = np.clip(
        np.asarray(vector, dtype=float).reshape(-1),
        np.asarray(ctx.coefficient_lower, dtype=float),
        np.asarray(ctx.coefficient_upper, dtype=float),
    )
    if clipped.shape != (15,) or not np.all(np.isfinite(clipped)):
        raise ValueError("Clipped Stage2.2 vector is invalid")
    return clipped


def _vector_key(vector: Any) -> str:
    return vector_digest(_parse_vector(vector), "v")


# ---------------------------------------------------------------------------
# Configuration and path validation
# ---------------------------------------------------------------------------


def validate_stage22_config(ctx: Any) -> None:
    trajectory = ctx.cfg["trajectory"]
    if int(trajectory.get("n_modes", -1)) != 3:
        raise ValueError("Stage2.2 requires exactly the first three validated SVD modes")
    if int(trajectory.get("node_count", -1)) != 5:
        raise ValueError("Stage2.2 requires exactly five time nodes")
    if list(trajectory.get("node_steps", [])) != [0, 2, 4, 6, 9]:
        raise ValueError("Stage2.2 requires node_steps [0, 2, 4, 6, 9]")
    if len(ctx.coefficient_lower) != 15 or len(ctx.coefficient_upper) != 15:
        raise ValueError("Stage2.2 requires a 15-dimensional parameter vector")

    gate = ctx.cfg["gate"]
    for key in (
        "precise_tolerance_m",
        "relaxed_tolerance_m",
        "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s",
        "ip_tolerance_a",
    ):
        value = float(gate.get(key, math.nan))
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"gate.{key} must be finite and positive")
    if int(gate.get("required_terminal_streak_steps", 0)) != 3:
        raise ValueError("Stage2.2 is fixed to the unchanged final-three-sample hard gate")
    if int(gate.get("late_window_steps", 0)) <= 0:
        raise ValueError("gate.late_window_steps must be positive")

    search = ctx.cfg["search"]
    population = int(search.get("population_size", 0))
    quotas = {str(key): int(value) for key, value in search.get("family_quotas", {}).items()}
    required_families = {
        "anchors",
        "multi_center_probes",
        "corner_local",
        "boundary_bridge",
        "trust_mix",
        "random_local",
    }
    if set(quotas) != required_families:
        raise ValueError(f"search.family_quotas must contain exactly {sorted(required_families)}")
    if population <= 0 or sum(quotas.values()) != population:
        raise ValueError("Stage2.2 family quotas must sum exactly to population_size")
    if quotas["multi_center_probes"] != 24:
        raise ValueError("Stage2.2 uses exactly 24 multi-center antithetic probes")
    fixed_nodes = [int(value) for value in search.get("fixed_node_indices", [])]
    active_nodes = [int(value) for value in search.get("active_node_indices", [])]
    if fixed_nodes != [0] or active_nodes != [1, 2, 3, 4]:
        raise ValueError("Stage2.2 must fix node 0 and search node indices [1,2,3,4]")
    for key in (
        "local_std_by_node_mode",
        "probe_delta_by_node_mode",
        "bridge_noise_by_node_mode",
        "random_radius_by_node_mode",
    ):
        matrix = np.asarray(search.get(key, []), dtype=float)
        if matrix.shape != (5, 3) or np.any(matrix < 0.0) or not np.all(np.isfinite(matrix)):
            raise ValueError(f"search.{key} must be a finite non-negative 5x3 matrix")
    if np.any(np.asarray(search["probe_delta_by_node_mode"], dtype=float)[0] != 0.0):
        raise ValueError("Stage2.2 probe deltas at fixed node 0 must be zero")

    archives = ctx.cfg["archives"]
    for key in ("damped_capacity", "precise_capacity", "corner_capacity", "strict_capacity"):
        if int(archives.get(key, 0)) <= 0:
            raise ValueError(f"archives.{key} must be positive")
    if float(archives.get("corner_max_violation_limit", -1.0)) <= 0.0:
        raise ValueError("archives.corner_max_violation_limit must be positive")

    objective = ctx.cfg["objective"]
    for key in (
        "non_strict_offset",
        "max_violation_weight",
        "sum_violation_weight",
        "l2_violation_weight",
    ):
        value = float(objective.get(key, math.nan))
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"objective.{key} must be finite and non-negative")

    confirmation = ctx.cfg["confirmation"]
    if int(confirmation.get("max_unique_candidates", 0)) <= 0:
        raise ValueError("confirmation.max_unique_candidates must be positive")
    if int(confirmation.get("repeats_per_candidate", 0)) <= 0:
        raise ValueError("confirmation.repeats_per_candidate must be positive")


@dataclass(frozen=True)
class Stage22Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_catalog: Path
    source_catalog_summary: Path
    generations: Path
    evaluations: Path
    confirmations: Path
    analysis: Path
    best: Path
    source_reference: Path

    @classmethod
    def from_context(cls, ctx: Any) -> "Stage22Paths":
        run_dir = Path(ctx.paths.run_dir)
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_catalog=run_dir / SOURCE_CATALOG_FILENAME,
            source_catalog_summary=run_dir / SOURCE_CATALOG_SUMMARY_FILENAME,
            generations=run_dir / "stage2_2_generations",
            evaluations=run_dir / "stage2_2_evaluations",
            confirmations=run_dir / "stage2_2_confirmations",
            analysis=run_dir / "stage2_2_analysis",
            best=run_dir / "stage2_2_best",
            source_reference=run_dir / "source_history_reference",
        )


@dataclass
class SourceHistory:
    stage1_run: Path
    stage2_run: Path
    stage21_run: Path
    stage2_config: dict[str, Any]
    stage21_config: dict[str, Any]
    records: list[dict[str, Any]]
    catalog_summary: dict[str, Any]


# ---------------------------------------------------------------------------
# Source run resolution and compatibility
# ---------------------------------------------------------------------------


def _resolve_reference_path(raw: str | Path, *, project_dir: Path, fallback_folder: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    if path.exists():
        return path.resolve()
    fallback = project_dir / fallback_folder / Path(raw).name
    if fallback.exists():
        return fallback.resolve()
    return path.resolve(strict=False)


def resolve_source_stage21_run(value: str | Path | None, *, project_dir: Path) -> Path:
    if value is None or not str(value).strip():
        env_value = os.environ.get("SOURCE_STAGE2_1_RUN", "").strip()
        if not env_value:
            raise ValueError(
                "A completed Stage2.1 run is required. Pass --source-stage2-1-run "
                "or set SOURCE_STAGE2_1_RUN."
            )
        value = env_value
    run_dir = _resolve_reference_path(value, project_dir=project_dir, fallback_folder="stage2_1_runs")
    required = [
        run_dir / "stage2_1_manifest.json",
        run_dir / "stage2_1_state.json",
        run_dir / "stage2_1_analysis/all_generation_results.csv",
        run_dir / "stage2_1_evaluations",
    ]
    config_candidates = [
        run_dir / "stage2_1_config.resolved.json",
        run_dir / "stage2_config.resolved.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if not any(path.is_file() for path in config_candidates):
        missing.append("one of " + " or ".join(str(path) for path in config_candidates))
    if missing:
        raise FileNotFoundError("Incomplete Stage2.1 source run: " + ", ".join(missing))
    return run_dir


def _load_stage21_config(run_dir: Path) -> dict[str, Any]:
    preferred = run_dir / "stage2_1_config.resolved.json"
    fallback = run_dir / "stage2_config.resolved.json"
    return read_json(preferred if preferred.exists() else fallback)


def _resolve_source_paths_from_stage21(
    stage21_run: Path,
    *,
    project_dir: Path,
    explicit_stage1: str | Path | None,
    explicit_stage2: str | Path | None,
) -> tuple[Path, Path]:
    manifest = read_json(stage21_run / "stage2_1_manifest.json")
    if explicit_stage2 is not None and str(explicit_stage2).strip():
        stage2_run = _resolve_reference_path(
            explicit_stage2, project_dir=project_dir, fallback_folder="stage2_runs"
        )
    else:
        raw = str(manifest.get("source_stage2_run", "")).strip()
        if not raw:
            raise ValueError("Stage2.1 manifest does not record source_stage2_run")
        stage2_run = _resolve_reference_path(raw, project_dir=project_dir, fallback_folder="stage2_runs")

    if explicit_stage1 is not None and str(explicit_stage1).strip():
        stage1_run = _resolve_reference_path(
            explicit_stage1, project_dir=project_dir, fallback_folder="stage1_1_runs"
        )
    else:
        raw = str(manifest.get("source_stage1_1_run", "")).strip()
        if not raw:
            stage2_manifest = read_json(stage2_run / "stage2_manifest.json")
            raw = str(stage2_manifest.get("source_stage1_1_run", "")).strip()
        if not raw:
            raise ValueError("Neither Stage2.1 nor Stage2 manifest records the Stage1.1 source run")
        stage1_run = _resolve_reference_path(raw, project_dir=project_dir, fallback_folder="stage1_1_runs")
    return stage1_run, stage2_run


def _validate_source_stage2(run_dir: Path) -> None:
    required = [
        run_dir / "stage2_config.resolved.json",
        run_dir / "cem_state.json",
        run_dir / "stage2_manifest.json",
        run_dir / "analysis/all_generation_results.csv",
        run_dir / "evaluations",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage2 source run: " + ", ".join(missing))


def _validate_source_stage1(run_dir: Path) -> None:
    required = [
        run_dir / "analysis/coil_modes_tsc.npy",
        run_dir / "analysis/response_tensor_dy_per_a.npy",
        run_dir / "analysis/baseline_trajectory.csv",
        run_dir / "candidate_sequences/svd03_target1p00.json",
        run_dir / "raw_experiments/baseline_r00.json.gz",
        run_dir / "train_config.resolved.json",
        run_dir / "env_config.resolved.json",
        run_dir / "stage1_config.resolved.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage1.1 source run: " + ", ".join(missing))


def _validate_source_compatibility(
    ctx: Any,
    stage2_cfg: dict[str, Any],
    stage21_cfg: dict[str, Any],
) -> None:
    for source_name, source_cfg in (("Stage2", stage2_cfg), ("Stage2.1", stage21_cfg)):
        for key in ("R", "Z", "Ip"):
            lhs = float(ctx.cfg["target"][key])
            rhs = float(source_cfg["target"][key])
            if not math.isclose(lhs, rhs, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"Stage2.2 target {key} differs from {source_name}")
        for key in ("horizon_steps", "horizon_ms", "n_modes", "node_count"):
            if int(ctx.cfg["trajectory"][key]) != int(source_cfg["trajectory"][key]):
                raise ValueError(f"Stage2.2 trajectory {key} differs from {source_name}")
        if list(ctx.cfg["trajectory"]["node_steps"]) != list(source_cfg["trajectory"]["node_steps"]):
            raise ValueError(f"Stage2.2 node_steps differ from {source_name}")
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
                raise ValueError(f"Stage2.2 hard gate {key} differs from {source_name}")


# ---------------------------------------------------------------------------
# Constraint metrics and primary Stage2.2 objective
# ---------------------------------------------------------------------------


def _trajectory_constraint_details(ctx: Any, result: dict[str, Any]) -> dict[str, Any]:
    trajectory = result.get("trajectory", [])
    required = int(ctx.cfg["gate"]["required_terminal_streak_steps"])
    if len(trajectory) < required:
        raise ValueError(
            f"trajectory has only {len(trajectory)} samples; at least {required} are required"
        )
    target = np.asarray(
        [ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]],
        dtype=float,
    )
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if y.ndim != 2 or y.shape[1] != 3 or not np.all(np.isfinite(y)):
        raise ValueError("real-TSC trajectory contains non-finite R/Z/Ip values")
    error = y - target[None, :]
    box = np.max(np.abs(error[:, :2]), axis=1)
    final = box[-required:]
    return {
        "final3_box_errors_m": final.tolist(),
        "final3_box_max_error_m": float(np.max(final)),
        "final3_box_mean_error_m": float(np.mean(final)),
        "terminal_box_error_m": float(final[-1]),
        "final3_R_abs_max_error_m": float(np.max(np.abs(error[-required:, 0]))),
        "final3_Z_abs_max_error_m": float(np.max(np.abs(error[-required:, 1]))),
    }


def _constraint_violations(
    ctx: Any,
    *,
    final3_box_max_error_m: float,
    terminal_velocity_m_per_s: float,
    late_velocity_rms_m_per_s: float,
    terminal_Ip_error_A: float,
) -> dict[str, float]:
    gate = ctx.cfg["gate"]
    position = max(
        float(final3_box_max_error_m) / float(gate["precise_tolerance_m"]) - 1.0,
        0.0,
    )
    terminal_speed = max(
        float(terminal_velocity_m_per_s) / float(gate["terminal_velocity_max_m_per_s"]) - 1.0,
        0.0,
    )
    late_speed = max(
        float(late_velocity_rms_m_per_s) / float(gate["late_velocity_rms_max_m_per_s"]) - 1.0,
        0.0,
    )
    ip = max(abs(float(terminal_Ip_error_A)) / float(gate["ip_tolerance_a"]) - 1.0, 0.0)
    values = np.asarray([position, terminal_speed, late_speed, ip], dtype=float)
    return {
        "stage2_2_position_violation": float(position),
        "stage2_2_terminal_speed_violation": float(terminal_speed),
        "stage2_2_late_speed_violation": float(late_speed),
        "stage2_2_ip_violation": float(ip),
        "stage2_2_max_violation": float(np.max(values)),
        "stage2_2_sum_violation": float(np.sum(values)),
        "stage2_2_l2_violation": float(np.linalg.norm(values)),
    }


def stage22_metrics(ctx: Any, result: dict[str, Any], decoded: dict[str, Any] | None) -> dict[str, Any]:
    base_metrics = dict(s2.stage2_metrics(ctx, result, decoded))
    legacy_selection = _finite_or_none(base_metrics.get("selection_score"))
    legacy_continuous = _finite_or_none(base_metrics.get("continuous_objective"))
    if not base_metrics.get("success"):
        base_metrics.update(
            {
                "stage2_legacy_selection_score": legacy_selection,
                "stage2_legacy_continuous_objective": legacy_continuous,
                "stage2_2_final3_box_max_error_m": None,
                "stage2_2_final3_box_mean_error_m": None,
                "stage2_2_position_violation": 1e6,
                "stage2_2_terminal_speed_violation": 1e6,
                "stage2_2_late_speed_violation": 1e6,
                "stage2_2_ip_violation": 1e6,
                "stage2_2_max_violation": 1e6,
                "stage2_2_sum_violation": 4e6,
                "stage2_2_l2_violation": 2e6,
                "stage2_2_quality": 1e12,
                "stage2_2_selection_score": 99e12,
                "continuous_objective": 1e12,
                "selection_score": 99e12,
            }
        )
        return base_metrics

    details = _trajectory_constraint_details(ctx, result)
    violations = _constraint_violations(
        ctx,
        final3_box_max_error_m=float(details["final3_box_max_error_m"]),
        terminal_velocity_m_per_s=float(base_metrics["terminal_velocity_m_per_s"]),
        late_velocity_rms_m_per_s=float(base_metrics["late_velocity_rms_m_per_s"]),
        terminal_Ip_error_A=float(base_metrics["terminal_Ip_error_A"]),
    )
    gate = ctx.cfg["gate"]
    strict_recomputed = bool(
        float(details["final3_box_max_error_m"]) <= float(gate["precise_tolerance_m"])
        and float(base_metrics["terminal_velocity_m_per_s"])
        <= float(gate["terminal_velocity_max_m_per_s"])
        and float(base_metrics["late_velocity_rms_m_per_s"])
        <= float(gate["late_velocity_rms_max_m_per_s"])
        and abs(float(base_metrics["terminal_Ip_error_A"])) <= float(gate["ip_tolerance_a"])
    )
    if strict_recomputed != bool(base_metrics.get("strict_gate_pass", False)):
        raise RuntimeError(
            "Stage2.2 strict-gate recomputation disagrees with the bundled Stage2 gate; "
            "the hard gate must not drift"
        )

    objective = ctx.cfg["objective"]
    weights = objective.get("quality_weights", {})
    position_tol = float(gate["precise_tolerance_m"])
    terminal_speed_limit = float(gate["terminal_velocity_max_m_per_s"])
    late_speed_limit = float(gate["late_velocity_rms_max_m_per_s"])
    ip_limit = float(gate["ip_tolerance_a"])

    final3_core = (float(details["final3_box_max_error_m"]) / position_tol) ** 2
    final3_mean_core = (float(details["final3_box_mean_error_m"]) / position_tol) ** 2
    terminal_box_core = (float(details["terminal_box_error_m"]) / position_tol) ** 2
    terminal_speed_core = (
        float(base_metrics["terminal_velocity_m_per_s"]) / terminal_speed_limit
    ) ** 2
    late_speed_core = (
        float(base_metrics["late_velocity_rms_m_per_s"]) / late_speed_limit
    ) ** 2
    ip_core = (float(base_metrics["terminal_Ip_error_A"]) / ip_limit) ** 2

    action_rms = _finite(base_metrics.get("action_rms"), 0.0)
    delta_action_rms = _finite(base_metrics.get("delta_action_rms"), 0.0)
    repair_rms = _finite(base_metrics.get("repair_excess_rms"), 0.0)
    quality = (
        float(weights.get("final3_box_core", 2.0)) * final3_core
        + float(weights.get("final3_box_mean_core", 0.8)) * final3_mean_core
        + float(weights.get("terminal_box_core", 0.6)) * terminal_box_core
        + float(weights.get("terminal_velocity_core", 0.5)) * terminal_speed_core
        + float(weights.get("late_velocity_core", 1.5)) * late_speed_core
        + float(weights.get("terminal_ip_core", 0.05)) * ip_core
        + float(weights.get("action_rms", 0.02)) * action_rms**2
        + float(weights.get("delta_action_rms", 0.04)) * delta_action_rms**2
        + float(weights.get("repair", 2.0)) * repair_rms**2
    )
    non_strict_offset = 0.0 if strict_recomputed else float(objective["non_strict_offset"])
    score = (
        non_strict_offset
        + float(objective["max_violation_weight"])
        * violations["stage2_2_max_violation"]
        + float(objective["sum_violation_weight"])
        * violations["stage2_2_sum_violation"]
        + float(objective["l2_violation_weight"])
        * violations["stage2_2_l2_violation"]
        + quality
    )
    base_metrics.update(
        {
            "stage2_legacy_selection_score": legacy_selection,
            "stage2_legacy_continuous_objective": legacy_continuous,
            "stage2_2_final3_box_errors_m": details["final3_box_errors_m"],
            "stage2_2_final3_box_max_error_m": details["final3_box_max_error_m"],
            "stage2_2_final3_box_mean_error_m": details["final3_box_mean_error_m"],
            "stage2_2_terminal_box_error_m": details["terminal_box_error_m"],
            "stage2_2_final3_R_abs_max_error_m": details["final3_R_abs_max_error_m"],
            "stage2_2_final3_Z_abs_max_error_m": details["final3_Z_abs_max_error_m"],
            **violations,
            "stage2_2_quality": float(quality),
            "stage2_2_selection_score": float(score),
            "continuous_objective": float(
                score - (0.0 if strict_recomputed else float(objective["non_strict_offset"]))
            ),
            "selection_score": float(score),
        }
    )
    return base_metrics


# ---------------------------------------------------------------------------
# Combined Stage2 + Stage2.1 source catalog
# ---------------------------------------------------------------------------


def _source_result_path(run_dir: Path, stage: str, generation: int, candidate_id: str) -> Path:
    if stage == "Stage2":
        return run_dir / "evaluations" / f"gen_{generation:03d}" / f"{candidate_id}.json.gz"
    if stage == "Stage2.1":
        return (
            run_dir
            / "stage2_1_evaluations"
            / f"gen_{generation:03d}"
            / f"{candidate_id}.json.gz"
        )
    raise ValueError(f"Unsupported source stage {stage!r}")


def _source_csv_path(run_dir: Path, stage: str) -> Path:
    if stage == "Stage2":
        return run_dir / "analysis/all_generation_results.csv"
    if stage == "Stage2.1":
        return run_dir / "stage2_1_analysis/all_generation_results.csv"
    raise ValueError(f"Unsupported source stage {stage!r}")


def _source_record(
    ctx: Any,
    *,
    row: dict[str, Any],
    source_stage: str,
    source_run: Path,
) -> dict[str, Any] | None:
    if not _as_bool(row.get("success"), False):
        return None
    try:
        vector = _parse_vector(row.get("parameter_vector"))
    except Exception:
        return None
    generation = _as_int(row.get("generation"), -1)
    candidate_id = str(row.get("candidate_id", "")).strip()
    if generation < 0 or not candidate_id:
        return None
    result_path = _source_result_path(source_run, source_stage, generation, candidate_id)
    if not result_path.is_file():
        return None
    try:
        result = read_json_gz(result_path)
        decoded = s2.decode_vector(ctx, vector)
        metrics = stage22_metrics(ctx, result, decoded)
    except Exception:
        return None
    if not metrics.get("success"):
        return None
    record = {
        "source_stage": source_stage,
        "source_run": str(source_run),
        "source_generation_group": generation + (0 if source_stage == "Stage2" else 1000),
        "generation": generation,
        "candidate_id": candidate_id,
        "source_name": str(row.get("source_name", "unknown")),
        "source_type": str(row.get("source_type", "unknown")),
        "vector": vector.tolist(),
        "vector_digest": _vector_key(vector),
        "result_relative_path": str(result_path.relative_to(source_run)),
    }
    for key, value in metrics.items():
        if key in {"parameter_vector", "trajectory"}:
            continue
        record[key] = value
    return record


def _raw_result_tree_fingerprint(run_dir: Path, stage: str) -> dict[str, Any]:
    if stage == "Stage2":
        root = run_dir / "evaluations"
    elif stage == "Stage2.1":
        root = run_dir / "stage2_1_evaluations"
    else:
        raise ValueError(f"Unsupported source stage {stage!r}")
    paths = sorted(root.glob("gen_*/*.json.gz"))
    digest = hashlib.sha256()
    total_bytes = 0
    for path in paths:
        relative = path.relative_to(run_dir).as_posix()
        size = path.stat().st_size
        total_bytes += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(jsonio.sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return {
        "count": len(paths),
        "total_bytes": total_bytes,
        "sha256": digest.hexdigest(),
    }


def _catalog_fingerprint(stage2_run: Path, stage21_run: Path) -> dict[str, Any]:
    stage2_csv = _source_csv_path(stage2_run, "Stage2")
    stage21_csv = _source_csv_path(stage21_run, "Stage2.1")
    stage21_config = (
        stage21_run / "stage2_1_config.resolved.json"
        if (stage21_run / "stage2_1_config.resolved.json").exists()
        else stage21_run / "stage2_config.resolved.json"
    )
    return {
        "stage2_run": str(stage2_run),
        "stage2_1_run": str(stage21_run),
        "stage2_csv_sha256": jsonio.sha256_file(stage2_csv),
        "stage2_1_csv_sha256": jsonio.sha256_file(stage21_csv),
        "stage2_config_sha256": jsonio.sha256_file(stage2_run / "stage2_config.resolved.json"),
        "stage2_1_config_sha256": jsonio.sha256_file(stage21_config),
        "stage2_raw_results": _raw_result_tree_fingerprint(stage2_run, "Stage2"),
        "stage2_1_raw_results": _raw_result_tree_fingerprint(stage21_run, "Stage2.1"),
    }


def _dedupe_source_records(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        key = str(record["vector_digest"])
        previous = unique.get(key)
        if previous is None or _constraint_sort_key(record) < _constraint_sort_key(previous):
            unique[key] = copy.deepcopy(record)
    return sorted(unique.values(), key=_constraint_sort_key)


def build_source_catalog(
    ctx: Any,
    *,
    stage2_run: Path,
    stage21_run: Path,
    paths: Stage22Paths,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fingerprint = _catalog_fingerprint(stage2_run, stage21_run)
    if paths.source_catalog.exists() and paths.source_catalog_summary.exists():
        summary = read_json(paths.source_catalog_summary)
        if summary.get("fingerprint") != fingerprint:
            raise ValueError(
                "Existing Stage2.2 source catalog was built from different source runs/files"
            )
        payload = read_json_gz(paths.source_catalog)
        records = payload.get("records", [])
        if not isinstance(records, list) or len(records) < 100:
            raise RuntimeError("Existing Stage2.2 source catalog is incomplete")
        return [dict(record) for record in records], summary

    all_records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    stage_counts: dict[str, dict[str, int]] = {}
    for stage, run_dir in (("Stage2", stage2_run), ("Stage2.1", stage21_run)):
        rows = read_csv(_source_csv_path(run_dir, stage))
        successful_rows = sum(_as_bool(row.get("success"), False) for row in rows)
        before = len(all_records)
        for row in rows:
            record = _source_record(ctx, row=row, source_stage=stage, source_run=run_dir)
            if record is None:
                if _as_bool(row.get("success"), False):
                    skipped.append(
                        {
                            "source_stage": stage,
                            "candidate_id": str(row.get("candidate_id", "")),
                            "generation": _as_int(row.get("generation"), -1),
                            "reason": "missing/invalid raw result or vector",
                        }
                    )
                continue
            all_records.append(record)
        stage_counts[stage] = {
            "rows": len(rows),
            "successful_rows": successful_rows,
            "catalog_records": len(all_records) - before,
        }

    if skipped:
        examples = ", ".join(
            f"{row['source_stage']}:{row['generation']}:{row['candidate_id']}"
            for row in skipped[:8]
        )
        raise RuntimeError(
            f"Failed to reconstruct {len(skipped)} source rows that were marked successful; "
            f"the Stage2.2 catalog must be complete. First entries: {examples}"
        )
    if len(all_records) < 2000:
        raise RuntimeError(
            f"Only {len(all_records)} usable real-TSC source records were recovered; "
            "a complete Stage2 + Stage2.1 history is required"
        )
    unique_records = _dedupe_source_records(all_records)
    strict_count = sum(_as_bool(record.get("strict_gate_pass"), False) for record in unique_records)
    speed_safe_count = sum(_strict_speed_safe(record, ctx.cfg) for record in unique_records)
    position_safe_count = sum(_strict_position_safe(record) for record in unique_records)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": utc_timestamp(),
        "fingerprint": fingerprint,
        "stage_counts": stage_counts,
        "n_records_before_deduplication": len(all_records),
        "n_unique_records": len(unique_records),
        "n_skipped_success_rows": len(skipped),
        "n_strict": strict_count,
        "n_strict_speed_safe": speed_safe_count,
        "n_strict_position_safe": position_safe_count,
        "best_constraint_record": _record_summary(unique_records[0]) if unique_records else None,
        "skipped_examples": skipped[:25],
    }
    atomic_write_json_gz(
        paths.source_catalog,
        {
            "schema_version": SCHEMA_VERSION,
            "fingerprint": fingerprint,
            "records": unique_records,
        },
    )
    atomic_write_json(paths.source_catalog_summary, summary)
    write_csv(paths.analysis / "source_catalog_top_corner.csv", unique_records[:100])
    return unique_records, summary


def load_source_history(
    ctx: Any,
    *,
    source_stage1_run: str | Path | None,
    source_stage2_run: str | Path | None,
    source_stage21_run: str | Path | None,
    paths: Stage22Paths | None = None,
) -> SourceHistory:
    project_dir = Path(ctx.paths.project_dir)
    stage21_run = resolve_source_stage21_run(source_stage21_run, project_dir=project_dir)
    stage1_run, stage2_run = _resolve_source_paths_from_stage21(
        stage21_run,
        project_dir=project_dir,
        explicit_stage1=source_stage1_run,
        explicit_stage2=source_stage2_run,
    )
    _validate_source_stage1(stage1_run)
    _validate_source_stage2(stage2_run)
    stage2_cfg = read_json(stage2_run / "stage2_config.resolved.json")
    stage21_cfg = _load_stage21_config(stage21_run)
    _validate_source_compatibility(ctx, stage2_cfg, stage21_cfg)
    if paths is None:
        return SourceHistory(
            stage1_run=stage1_run,
            stage2_run=stage2_run,
            stage21_run=stage21_run,
            stage2_config=stage2_cfg,
            stage21_config=stage21_cfg,
            records=[],
            catalog_summary={},
        )
    records, summary = build_source_catalog(
        ctx,
        stage2_run=stage2_run,
        stage21_run=stage21_run,
        paths=paths,
    )
    return SourceHistory(
        stage1_run=stage1_run,
        stage2_run=stage2_run,
        stage21_run=stage21_run,
        stage2_config=stage2_cfg,
        stage21_config=stage21_cfg,
        records=records,
        catalog_summary=summary,
    )


def initialize_stage22_run(ctx: Any, history_stub: SourceHistory) -> Stage22Paths:
    s2.initialize_stage2_run(ctx)
    paths = Stage22Paths.from_context(ctx)
    for path in (
        paths.generations,
        paths.evaluations,
        paths.confirmations,
        paths.analysis,
        paths.best,
        paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(paths.run_dir / "stage2_2_config.resolved.json", ctx.cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.2",
        "created_utc": utc_timestamp(),
        "source_stage1_1_run": str(history_stub.stage1_run),
        "source_stage2_run": str(history_stub.stage2_run),
        "source_stage2_1_run": str(history_stub.stage21_run),
        "target": copy.deepcopy(ctx.cfg["target"]),
        "trajectory": copy.deepcopy(ctx.cfg["trajectory"]),
        "gate": copy.deepcopy(ctx.cfg["gate"]),
        "hard_gate_changed_from_stage2": False,
        "search": copy.deepcopy(ctx.cfg["search"]),
        "objective": copy.deepcopy(ctx.cfg["objective"]),
        "temporary_workspace": {
            "tsc_workspace_root": ctx.env_cfg.get("tsc_workspace_root"),
            "tsc_run_root": ctx.env_cfg.get("run_root"),
            "ray_tmpdir": os.environ.get("RAY_TMPDIR", ""),
        },
    }
    if paths.manifest.exists():
        previous = read_json(paths.manifest)
        for key, expected in (
            ("source_stage1_1_run", history_stub.stage1_run),
            ("source_stage2_run", history_stub.stage2_run),
            ("source_stage2_1_run", history_stub.stage21_run),
        ):
            raw = str(previous.get(key, "")).strip()
            if not raw or Path(raw).expanduser().resolve() != Path(expected).resolve():
                raise ValueError(f"Existing Stage2.2 run points to a different {key}")
    else:
        atomic_write_json(paths.manifest, manifest)

    reference_files = (
        (history_stub.stage2_run, "stage2_config.resolved.json"),
        (history_stub.stage2_run, "cem_state.json"),
        (history_stub.stage2_run, "analysis/stage2_analysis_summary.json"),
        (history_stub.stage2_run, "analysis/hall_of_fame.csv"),
        (history_stub.stage21_run, "stage2_1_config.resolved.json"),
        (history_stub.stage21_run, "stage2_1_state.json"),
        (history_stub.stage21_run, "stage2_1_analysis/stage2_1_analysis_summary.json"),
        (history_stub.stage21_run, "stage2_1_analysis/hall_of_fame.csv"),
        (history_stub.stage21_run, "STAGE2_1_REPORT.md"),
    )
    for source_root, relative in reference_files:
        source = source_root / relative
        if not source.exists():
            continue
        stage_folder = "stage2" if source_root == history_stub.stage2_run else "stage2_1"
        destination = paths.source_reference / stage_folder / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
    return paths


# ---------------------------------------------------------------------------
# Feasibility archives and local covariance
# ---------------------------------------------------------------------------


def _strict_speed_safe(record: dict[str, Any], cfg: dict[str, Any]) -> bool:
    gate = cfg["gate"]
    return bool(
        _finite(record.get("terminal_velocity_m_per_s"), 1e9)
        <= float(gate["terminal_velocity_max_m_per_s"])
        and _finite(record.get("late_velocity_rms_m_per_s"), 1e9)
        <= float(gate["late_velocity_rms_max_m_per_s"])
        and abs(_finite(record.get("terminal_Ip_error_A"), 1e12))
        <= float(gate["ip_tolerance_a"])
    )


def _strict_position_safe(record: dict[str, Any]) -> bool:
    return bool(_finite(record.get("stage2_2_position_violation"), 1e9) <= 1e-12)


def _constraint_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    strict = _as_bool(record.get("strict_gate_pass"), False)
    return (
        0 if strict else 1,
        _finite(record.get("stage2_2_max_violation"), 1e9),
        _finite(record.get("stage2_2_sum_violation"), 1e9),
        _finite(record.get("stage2_2_l2_violation"), 1e9),
        _finite(record.get("stage2_2_quality"), 1e12),
        str(record.get("candidate_id", "")),
    )


def _damped_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _finite(record.get("stage2_2_position_violation"), 1e9),
        _finite(record.get("stage2_2_final3_box_max_error_m"), 1e9),
        _finite(record.get("late_velocity_rms_m_per_s"), 1e9),
        _finite(record.get("terminal_velocity_m_per_s"), 1e9),
        _finite(record.get("stage2_2_quality"), 1e12),
        str(record.get("candidate_id", "")),
    )


def _precise_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    gate_position = _finite(record.get("stage2_2_position_violation"), 1e9)
    terminal_position = max(
        _finite(record.get("stage2_2_terminal_box_error_m"), 1e9)
        / 0.03
        - 1.0,
        0.0,
    )
    speed_max = max(
        _finite(record.get("stage2_2_terminal_speed_violation"), 1e9),
        _finite(record.get("stage2_2_late_speed_violation"), 1e9),
    )
    speed_sum = (
        _finite(record.get("stage2_2_terminal_speed_violation"), 1e9)
        + _finite(record.get("stage2_2_late_speed_violation"), 1e9)
    )
    # The corrected precise front explicitly favors nearly damped transition
    # candidates instead of deep 30 mm penetrations that are still moving fast.
    score = 8.0 * gate_position**2 + 4.0 * terminal_position**2 + 2.0 * speed_max**2 + 1.5 * speed_sum**2
    return (
        score,
        speed_max,
        gate_position,
        _finite(record.get("stage2_2_final3_box_max_error_m"), 1e9),
        str(record.get("candidate_id", "")),
    )


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "source_stage",
        "generation",
        "candidate_id",
        "source_type",
        "gate_label",
        "strict_gate_pass",
        "relaxed_gate_pass",
        "stage2_2_final3_box_max_error_m",
        "stage2_2_terminal_box_error_m",
        "terminal_velocity_m_per_s",
        "late_velocity_rms_m_per_s",
        "terminal_Ip_error_A",
        "stage2_2_position_violation",
        "stage2_2_terminal_speed_violation",
        "stage2_2_late_speed_violation",
        "stage2_2_ip_violation",
        "stage2_2_max_violation",
        "stage2_2_sum_violation",
        "stage2_2_l2_violation",
        "stage2_2_selection_score",
    )
    return {key: record.get(key) for key in keys if key in record}


def _record_vector(record: dict[str, Any]) -> np.ndarray:
    value = record.get("vector", record.get("parameter_vector"))
    return _parse_vector(value)


def _vector_distance(lhs: dict[str, Any], rhs: dict[str, Any]) -> float:
    return float(np.linalg.norm(_record_vector(lhs) - _record_vector(rhs)))


def _dedupe_diverse(
    records: Sequence[dict[str, Any]],
    *,
    capacity: int,
    sort_key: Callable[[dict[str, Any]], tuple[Any, ...]],
    minimum_distance: float,
) -> list[dict[str, Any]]:
    ordered = sorted(records, key=sort_key)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in ordered:
        vector = _record_vector(record)
        digest = _vector_key(vector)
        if digest in seen:
            continue
        if selected and min(_vector_distance(record, other) for other in selected) < minimum_distance:
            continue
        copy_record = copy.deepcopy(record)
        copy_record["vector"] = vector.tolist()
        copy_record["vector_digest"] = digest
        selected.append(copy_record)
        seen.add(digest)
        if len(selected) >= capacity:
            break
    if len(selected) < capacity:
        for record in ordered:
            vector = _record_vector(record)
            digest = _vector_key(vector)
            if digest in seen:
                continue
            copy_record = copy.deepcopy(record)
            copy_record["vector"] = vector.tolist()
            copy_record["vector_digest"] = digest
            selected.append(copy_record)
            seen.add(digest)
            if len(selected) >= capacity:
                break
    return selected


def _damped_eligible(record: dict[str, Any], cfg: dict[str, Any]) -> bool:
    archives = cfg["archives"]
    return bool(
        _strict_speed_safe(record, cfg)
        and _finite(record.get("stage2_2_final3_box_max_error_m"), 1e9)
        <= float(archives["damped_final3_box_limit_m"])
    )


def _precise_eligible(record: dict[str, Any], cfg: dict[str, Any]) -> bool:
    archives = cfg["archives"]
    final3 = _finite(record.get("stage2_2_final3_box_max_error_m"), 1e9)
    terminal = _finite(record.get("stage2_2_terminal_box_error_m"), 1e9)
    position_ok = (
        final3 <= float(archives["precise_final3_box_limit_m"])
        or terminal <= float(archives["precise_terminal_box_limit_m"])
        or _as_int(record.get("trailing_streak_within_30mm_steps"), 0) >= 2
    )
    speed_cap_ok = (
        _finite(record.get("terminal_velocity_m_per_s"), 1e9)
        <= float(archives["precise_terminal_velocity_cap_m_per_s"])
        and _finite(record.get("late_velocity_rms_m_per_s"), 1e9)
        <= float(archives["precise_late_velocity_cap_m_per_s"])
    )
    ip_ok = _finite(record.get("stage2_2_ip_violation"), 1e9) <= 1e-12
    return bool(position_ok and speed_cap_ok and ip_ok)


def rebuild_archives(
    cfg: dict[str, Any],
    old_archives: dict[str, list[dict[str, Any]]],
    new_records: Sequence[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    for key in ("damped", "precise", "corner", "strict"):
        candidates.extend(old_archives.get(key, []))
    candidates.extend(new_records)
    unique: dict[str, dict[str, Any]] = {}
    for record in candidates:
        try:
            vector = _record_vector(record)
        except Exception:
            continue
        digest = _vector_key(vector)
        row = copy.deepcopy(record)
        row["vector"] = vector.tolist()
        row["vector_digest"] = digest
        previous = unique.get(digest)
        if previous is None or _constraint_sort_key(row) < _constraint_sort_key(previous):
            unique[digest] = row
    all_records = list(unique.values())
    archives_cfg = cfg["archives"]
    distance = float(archives_cfg["minimum_vector_distance"])

    strict = [row for row in all_records if _as_bool(row.get("strict_gate_pass"), False)]
    damped = [row for row in all_records if _damped_eligible(row, cfg)]
    precise = [row for row in all_records if _precise_eligible(row, cfg)]
    corner_limit = float(archives_cfg["corner_max_violation_limit"])
    corner = [
        row
        for row in all_records
        if _finite(row.get("stage2_2_max_violation"), 1e9) <= corner_limit
        and _finite(row.get("stage2_2_ip_violation"), 1e9) <= 1e-12
    ]
    if len(corner) < int(archives_cfg["corner_capacity"]):
        corner = all_records

    return {
        "strict": _dedupe_diverse(
            strict,
            capacity=int(archives_cfg["strict_capacity"]),
            sort_key=_constraint_sort_key,
            minimum_distance=distance,
        ),
        "corner": _dedupe_diverse(
            corner,
            capacity=int(archives_cfg["corner_capacity"]),
            sort_key=_constraint_sort_key,
            minimum_distance=distance,
        ),
        "damped": _dedupe_diverse(
            damped,
            capacity=int(archives_cfg["damped_capacity"]),
            sort_key=_damped_sort_key,
            minimum_distance=distance,
        ),
        "precise": _dedupe_diverse(
            precise,
            capacity=int(archives_cfg["precise_capacity"]),
            sort_key=_precise_sort_key,
            minimum_distance=distance,
        ),
    }


def _node_matrix(cfg: dict[str, Any], key: str) -> np.ndarray:
    matrix = np.asarray(cfg["search"][key], dtype=float)
    if matrix.shape != (5, 3):
        raise ValueError(f"search.{key} must have shape (5,3)")
    return matrix


def _local_std_vector(cfg: dict[str, Any], trust_scale: float) -> np.ndarray:
    return (_node_matrix(cfg, "local_std_by_node_mode") * float(trust_scale)).reshape(-1)


def fit_corner_covariance(
    vectors: Sequence[np.ndarray],
    *,
    cfg: dict[str, Any],
    trust_scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    if not vectors:
        raise ValueError("At least one vector is required to fit the corner distribution")
    matrix = np.vstack([np.asarray(vector, dtype=float).reshape(-1) for vector in vectors])
    mean = np.mean(matrix, axis=0)
    # Preserve the best corner candidate's initial node exactly; Stage2.2 is a
    # tail/corner refinement rather than a new launch-profile search.
    mean[:3] = matrix[0, :3]
    std_target = np.maximum(_local_std_vector(cfg, trust_scale), 1e-6)
    if len(matrix) >= 3:
        empirical = np.cov(matrix, rowvar=False, ddof=1)
        empirical = 0.5 * (empirical + empirical.T)
        empirical_std = np.sqrt(np.maximum(np.diag(empirical), 1e-12))
        correlation = empirical / np.outer(empirical_std, empirical_std)
        correlation = np.nan_to_num(correlation, nan=0.0, posinf=0.0, neginf=0.0)
        np.fill_diagonal(correlation, 1.0)
    else:
        correlation = np.eye(15)
    shrink = float(cfg["search"].get("covariance_diagonal_shrinkage", 0.35))
    correlation = (1.0 - shrink) * correlation + shrink * np.eye(15)
    covariance = correlation * np.outer(std_target, std_target)
    covariance = 0.5 * (covariance + covariance.T)
    values, vectors_eig = np.linalg.eigh(covariance)
    values = np.clip(
        values,
        float(cfg["search"].get("covariance_eigen_floor", 2e-5)),
        float(cfg["search"].get("covariance_eigen_ceiling", 3e-2)),
    )
    covariance = (vectors_eig * values[None, :]) @ vectors_eig.T
    # Node 0 is not a search variable. Keep only a tiny numerical variance so
    # Cholesky remains well-defined without moving the initial drive.
    covariance[:3, :] = 0.0
    covariance[:, :3] = 0.0
    covariance[:3, :3] = np.eye(3) * 1e-8
    return mean, covariance


def select_probe_centers(archives: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if not archives.get("corner") or not archives.get("damped") or not archives.get("precise"):
        raise RuntimeError("Stage2.2 requires non-empty corner, damped and precise archives")
    proposed = [archives["corner"][0], archives["damped"][0], archives["precise"][0]]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in proposed + archives["corner"] + archives["damped"] + archives["precise"]:
        digest = _vector_key(_record_vector(record))
        if digest in seen:
            continue
        selected.append(record)
        seen.add(digest)
        if len(selected) >= 3:
            break
    if len(selected) != 3:
        raise RuntimeError("Could not select three unique Stage2.2 probe centers")
    return selected


# ---------------------------------------------------------------------------
# Three-target proposal surrogate (ranking only)
# ---------------------------------------------------------------------------


def _ridge_model_to_json(model: dict[str, Any]) -> dict[str, Any]:
    return {key: np.asarray(value).tolist() for key, value in model.items()}


def _records_for_surrogate(
    source_records: Sequence[dict[str, Any]],
    stage22_rows: Sequence[dict[str, Any]],
) -> list[tuple[int, np.ndarray, float, float, float]]:
    records: list[tuple[int, np.ndarray, float, float, float]] = []
    for record in source_records:
        try:
            vector = _record_vector(record)
            final3 = _finite(record.get("stage2_2_final3_box_max_error_m"), math.nan)
            terminal_v = _finite(record.get("terminal_velocity_m_per_s"), math.nan)
            late_v = _finite(record.get("late_velocity_rms_m_per_s"), math.nan)
        except Exception:
            continue
        if not all(math.isfinite(value) for value in (final3, terminal_v, late_v)):
            continue
        group = _as_int(record.get("source_generation_group"), 0)
        records.append((group, vector, final3, terminal_v, late_v))
    for row in stage22_rows:
        if not _as_bool(row.get("success"), False):
            continue
        try:
            vector = _parse_vector(row.get("parameter_vector"))
            final3 = _finite(row.get("stage2_2_final3_box_max_error_m"), math.nan)
            terminal_v = _finite(row.get("terminal_velocity_m_per_s"), math.nan)
            late_v = _finite(row.get("late_velocity_rms_m_per_s"), math.nan)
        except Exception:
            continue
        if not all(math.isfinite(value) for value in (final3, terminal_v, late_v)):
            continue
        group = 2000 + _as_int(row.get("generation"), 0)
        records.append((group, vector, final3, terminal_v, late_v))
    return records


def fit_corner_surrogate(
    ctx: Any,
    source_records: Sequence[dict[str, Any]],
    stage22_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    cfg = ctx.cfg["surrogate"]
    if not bool(cfg.get("enabled", True)):
        return {"enabled": False, "reason": "disabled_by_config"}
    records = _records_for_surrogate(source_records, stage22_rows)
    minimum_samples = int(cfg.get("minimum_samples", 768))
    if len(records) < minimum_samples:
        return {"enabled": False, "reason": "not_enough_samples", "n_samples": len(records)}
    groups = np.asarray([record[0] for record in records], dtype=int)
    unique_groups = sorted(set(groups.tolist()))
    if len(unique_groups) < int(cfg.get("minimum_generation_folds", 8)):
        return {
            "enabled": False,
            "reason": "not_enough_generation_folds",
            "n_folds": len(unique_groups),
        }
    vectors = np.vstack([record[1] for record in records])
    targets = np.asarray([[record[2], record[3], record[4]] for record in records], dtype=float)
    features = s21.surrogate_features(
        vectors,
        np.asarray(ctx.coefficient_lower, dtype=float),
        np.asarray(ctx.coefficient_upper, dtype=float),
    )
    alpha = float(cfg.get("ridge_alpha", 1.0))
    predictions = np.full_like(targets, np.nan)
    fold_rows: list[dict[str, Any]] = []
    names = ("final3_box", "terminal_velocity", "late_velocity")
    for group in unique_groups:
        test = groups == group
        train = ~test
        if np.sum(test) == 0 or np.sum(train) < 100:
            continue
        fold: dict[str, Any] = {"generation_group": int(group), "n_test": int(np.sum(test))}
        for index, name in enumerate(names):
            model = s21._ridge_fit(features[train], targets[train, index], alpha)
            predictions[test, index] = s21._ridge_predict(model, features[test])
            fold[f"{name}_r2"] = s21._r2(targets[test, index], predictions[test, index])
            fold[f"{name}_mae"] = float(
                np.mean(np.abs(targets[test, index] - predictions[test, index]))
            )
        fold_rows.append(fold)
    valid = np.all(np.isfinite(predictions), axis=1)
    if int(np.sum(valid)) < minimum_samples:
        return {
            "enabled": False,
            "reason": "cross_validation_incomplete",
            "n_valid": int(np.sum(valid)),
        }
    metrics: dict[str, float] = {}
    for index, name in enumerate(names):
        metrics[f"{name}_cv_r2"] = s21._r2(targets[valid, index], predictions[valid, index])
        metrics[f"{name}_cv_mae"] = float(
            np.mean(np.abs(targets[valid, index] - predictions[valid, index]))
        )
    enabled = bool(
        metrics["final3_box_cv_r2"] >= float(cfg["minimum_r2_final3_box"])
        and metrics["final3_box_cv_mae"] <= float(cfg["maximum_mae_final3_box_m"])
        and metrics["terminal_velocity_cv_r2"]
        >= float(cfg["minimum_r2_terminal_velocity"])
        and metrics["terminal_velocity_cv_mae"]
        <= float(cfg["maximum_mae_terminal_velocity"])
        and metrics["late_velocity_cv_r2"] >= float(cfg["minimum_r2_late_velocity"])
        and metrics["late_velocity_cv_mae"] <= float(cfg["maximum_mae_late_velocity"])
    )
    summary: dict[str, Any] = {
        "enabled": enabled,
        "reason": "validated" if enabled else "cross_validation_threshold_not_met",
        "n_samples": len(records),
        "n_features": int(features.shape[1]),
        "n_folds": len(fold_rows),
        **metrics,
        "folds": fold_rows,
    }
    if enabled:
        for index, name in enumerate(names):
            model = s21._ridge_fit(features, targets[:, index], alpha)
            summary[f"{name}_model"] = _ridge_model_to_json(model)
    return summary


def surrogate_predict(
    ctx: Any,
    surrogate: dict[str, Any],
    vectors: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vectors = np.asarray(vectors, dtype=float)
    if vectors.ndim == 1:
        vectors = vectors[None, :]
    n = len(vectors)
    if not surrogate.get("enabled"):
        return np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    features = s21.surrogate_features(
        vectors,
        np.asarray(ctx.coefficient_lower, dtype=float),
        np.asarray(ctx.coefficient_upper, dtype=float),
    )
    output = []
    for name in ("final3_box", "terminal_velocity", "late_velocity"):
        prediction = s21._ridge_predict(surrogate[f"{name}_model"], features)
        output.append(np.maximum(np.asarray(prediction, dtype=float), 0.0))
    return output[0], output[1], output[2]


def _proposal_row(ctx: Any, vector: np.ndarray, source_name: str, source_type: str) -> dict[str, Any]:
    vector = _clip_vector(ctx, vector)
    decoded = s2.decode_vector(ctx, vector)
    linear = s2.linear_prefilter_metrics(ctx, decoded)
    return {
        "candidate_id": vector_digest(vector, "proposal"),
        "vector": vector.tolist(),
        "source_name": source_name,
        "source_type": source_type,
        **linear,
    }


def _dedupe_proposals(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        digest = _vector_key(row["vector"])
        if digest in seen:
            continue
        copy_row = copy.deepcopy(row)
        copy_row["vector_digest"] = digest
        output.append(copy_row)
        seen.add(digest)
    return output


def _apply_surrogate_ranking(
    ctx: Any,
    rows: list[dict[str, Any]],
    surrogate: dict[str, Any],
) -> None:
    if not rows:
        return
    vectors = np.vstack([_parse_vector(row["vector"]) for row in rows])
    pred_box, pred_terminal_v, pred_late_v = surrogate_predict(ctx, surrogate, vectors)
    gate = ctx.cfg["gate"]
    cfg = ctx.cfg["surrogate"]
    for index, row in enumerate(rows):
        if surrogate.get("enabled"):
            position = max(pred_box[index] / float(gate["precise_tolerance_m"]) - 1.0, 0.0)
            terminal = max(
                pred_terminal_v[index] / float(gate["terminal_velocity_max_m_per_s"]) - 1.0,
                0.0,
            )
            late = max(
                pred_late_v[index] / float(gate["late_velocity_rms_max_m_per_s"]) - 1.0,
                0.0,
            )
            max_violation = max(position, terminal, late)
            sum_violation = position + terminal + late
            rank = (
                float(cfg["ranking_weight_max_violation"]) * max_violation
                + float(cfg["ranking_weight_sum_violation"]) * sum_violation
                + float(cfg["ranking_weight_linear_score"])
                * float(row.get("linear_prefilter_score", 1e9))
            )
            row.update(
                {
                    "predicted_final3_box_max_error_m": float(pred_box[index]),
                    "predicted_terminal_velocity_m_per_s": float(pred_terminal_v[index]),
                    "predicted_late_velocity_rms_m_per_s": float(pred_late_v[index]),
                    "predicted_corner_max_violation": float(max_violation),
                    "predicted_corner_sum_violation": float(sum_violation),
                    "proposal_rank_score": float(rank),
                }
            )
        else:
            row.update(
                {
                    "predicted_final3_box_max_error_m": None,
                    "predicted_terminal_velocity_m_per_s": None,
                    "predicted_late_velocity_rms_m_per_s": None,
                    "predicted_corner_max_violation": None,
                    "predicted_corner_sum_violation": None,
                    "proposal_rank_score": float(row.get("linear_prefilter_score", 1e9)),
                }
            )


def _family_select(
    rng: np.random.Generator,
    rows: list[dict[str, Any]],
    *,
    quota: int,
    unranked_fraction: float,
) -> list[dict[str, Any]]:
    rows = _dedupe_proposals(rows)
    if len(rows) <= quota:
        return rows
    unranked_count = min(quota, int(round(quota * unranked_fraction)))
    ranked_count = quota - unranked_count
    ordered = sorted(rows, key=lambda row: _finite(row.get("proposal_rank_score"), 1e30))
    selected = ordered[:ranked_count]
    remainder = ordered[ranked_count:]
    if unranked_count > 0 and remainder:
        indices = rng.choice(
            len(remainder), size=min(unranked_count, len(remainder)), replace=False
        )
        selected.extend(remainder[int(index)] for index in indices)
    selected = _dedupe_proposals(selected)
    if len(selected) < quota:
        seen = {_vector_key(row["vector"]) for row in selected}
        for row in ordered:
            digest = _vector_key(row["vector"])
            if digest in seen:
                continue
            selected.append(row)
            seen.add(digest)
            if len(selected) >= quota:
                break
    return selected[:quota]


# ---------------------------------------------------------------------------
# State initialization and proposal generation
# ---------------------------------------------------------------------------


def initial_state(ctx: Any, history: SourceHistory) -> dict[str, Any]:
    archives = rebuild_archives(ctx.cfg, {}, history.records)
    for key in ("corner", "damped", "precise"):
        if not archives[key]:
            raise RuntimeError(f"No usable {key} archive could be built from Stage2 + Stage2.1")
    trust_scale = float(ctx.cfg["search"].get("initial_trust_scale", 1.0))
    elite_count = int(ctx.cfg["search"].get("archive_elite_count", 24))
    corner_vectors = [_record_vector(record) for record in archives["corner"][:elite_count]]
    corner_mean, corner_covariance = fit_corner_covariance(
        corner_vectors,
        cfg=ctx.cfg,
        trust_scale=trust_scale,
    )
    best = archives["corner"][0]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.2",
        "generation": 0,
        "source_stage1_1_run": str(history.stage1_run),
        "source_stage2_run": str(history.stage2_run),
        "source_stage2_1_run": str(history.stage21_run),
        "source_unique_record_count": len(history.records),
        "archives": archives,
        "corner_mean": corner_mean.tolist(),
        "corner_covariance": corner_covariance.tolist(),
        "trust_scale": trust_scale,
        "best_selection_score": float(best["stage2_2_selection_score"]),
        "best_candidate_id": str(best["candidate_id"]),
        "best_generation": None,
        "best_vector": _record_vector(best).tolist(),
        "best_record_origin": "source_history",
        "strict_gate_found": bool(archives["strict"]),
        "generations_without_improvement": 0,
        "finished": False,
        "stop_reason": "",
        "rng_seed": int(ctx.cfg["search"].get("random_seed", 20260722)),
        "updated_utc": utc_timestamp(),
    }


def load_or_initialize_state(
    ctx: Any,
    history: SourceHistory,
    paths: Stage22Paths,
    *,
    no_resume: bool,
) -> dict[str, Any]:
    if no_resume:
        if paths.state.exists():
            raise FileExistsError(
                f"--no-resume requested but state already exists: {paths.state}. Use a new run directory."
            )
        state = initial_state(ctx, history)
        atomic_write_json(paths.state, state)
        return state
    if paths.state.exists():
        state = read_json(paths.state)
        for key, expected in (
            ("source_stage1_1_run", history.stage1_run),
            ("source_stage2_run", history.stage2_run),
            ("source_stage2_1_run", history.stage21_run),
        ):
            raw = str(state.get(key, "")).strip()
            if not raw or Path(raw).expanduser().resolve() != Path(expected).resolve():
                raise ValueError(f"Stage2.2 state points to a different {key}")
        return state
    state = initial_state(ctx, history)
    atomic_write_json(paths.state, state)
    return state


def _sample_multivariate(
    rng: np.random.Generator,
    mean: np.ndarray,
    covariance: np.ndarray,
    n: int,
    *,
    antithetic: bool = True,
) -> np.ndarray:
    covariance = 0.5 * (np.asarray(covariance, dtype=float) + np.asarray(covariance, dtype=float).T)
    try:
        factor = np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError:
        values, vectors = np.linalg.eigh(covariance)
        factor = vectors @ np.diag(np.sqrt(np.maximum(values, 1e-12)))
    if antithetic:
        half = (n + 1) // 2
        noise = rng.standard_normal((half, len(mean))) @ factor.T
        return np.vstack([mean + noise, mean - noise])[:n]
    return mean[None, :] + rng.standard_normal((n, len(mean))) @ factor.T


def _hadamard(order: int = 16) -> np.ndarray:
    if order < 1 or order & (order - 1):
        raise ValueError("Hadamard order must be a positive power of two")
    matrix = np.asarray([[1.0]])
    while matrix.shape[0] < order:
        matrix = np.block([[matrix, matrix], [matrix, -matrix]])
    return matrix


def _active_flat_indices(cfg: dict[str, Any]) -> np.ndarray:
    indices: list[int] = []
    for node in [int(value) for value in cfg["search"]["active_node_indices"]]:
        indices.extend(range(node * 3, node * 3 + 3))
    return np.asarray(indices, dtype=int)


def _anchor_rows(ctx: Any, archives: dict[str, list[dict[str, Any]]], quota: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    families = (
        ("strict", 3),
        ("corner", 5),
        ("damped", 3),
        ("precise", 3),
    )
    for family, limit in families:
        for index, record in enumerate(archives.get(family, [])[:limit]):
            rows.append(
                _proposal_row(
                    ctx,
                    _record_vector(record),
                    f"{family}_archive_{index:02d}",
                    f"anchor_{family}",
                )
            )
    rows = _dedupe_proposals(rows)
    if len(rows) < quota:
        for record in archives["corner"] + archives["damped"] + archives["precise"]:
            rows = _dedupe_proposals(
                [
                    *rows,
                    _proposal_row(
                        ctx,
                        _record_vector(record),
                        f"anchor_fill_{len(rows):02d}",
                        "anchor_fill",
                    ),
                ]
            )
            if len(rows) >= quota:
                break
    if len(rows) < quota:
        for name, vector in getattr(ctx, "seed_vectors", {}).items():
            rows = _dedupe_proposals(
                [*rows, _proposal_row(ctx, vector, str(name), "anchor_seed")]
            )
            if len(rows) >= quota:
                break
    if len(rows) < quota:
        raise RuntimeError(f"Could construct only {len(rows)} unique Stage2.2 anchors")
    return rows[:quota]


def _probe_rows(
    ctx: Any,
    archives: dict[str, list[dict[str, Any]]],
    *,
    generation: int,
    trust_scale: float,
) -> list[dict[str, Any]]:
    centers = select_probe_centers(archives)
    active = _active_flat_indices(ctx.cfg)
    delta = (_node_matrix(ctx.cfg, "probe_delta_by_node_mode") * trust_scale).reshape(-1)
    hadamard = _hadamard(16)
    rows: list[dict[str, Any]] = []
    for center_index, center in enumerate(centers):
        vector = _record_vector(center)
        start = (generation * 4 + center_index * 5) % 16
        for direction_index in range(4):
            direction = hadamard[(start + direction_index) % 16, : len(active)]
            perturbation = np.zeros(15, dtype=float)
            perturbation[active] = direction * delta[active]
            for sign in (-1.0, 1.0):
                rows.append(
                    _proposal_row(
                        ctx,
                        vector + sign * perturbation,
                        f"probe_c{center_index}_h{(start + direction_index) % 16:02d}_{'p' if sign > 0 else 'm'}",
                        "multi_center_probes",
                    )
                )
    rows = _dedupe_proposals(rows)
    if len(rows) != 24:
        raise RuntimeError(f"Expected 24 unique multi-center probes, generated {len(rows)}")
    return rows


def _local_noise(
    rng: np.random.Generator,
    cfg: dict[str, Any],
    trust_scale: float,
) -> np.ndarray:
    std = _local_std_vector(cfg, trust_scale)
    noise = rng.normal(0.0, std, size=15)
    noise[:3] = 0.0
    return noise


def _bridge_vector(
    rng: np.random.Generator,
    damped: np.ndarray,
    precise: np.ndarray,
    corner: np.ndarray,
    cfg: dict[str, Any],
    trust_scale: float,
) -> np.ndarray:
    d = np.asarray(damped, dtype=float).reshape(5, 3)
    p = np.asarray(precise, dtype=float).reshape(5, 3)
    c = np.asarray(corner, dtype=float).reshape(5, 3)
    output = c.copy()
    # Node 0 is kept at the already validated corner drive.  The step-2 and
    # step-4 nodes receive more of the precise parent; the final braking nodes
    # remain closer to the damped parent.
    precise_weights = np.asarray(
        [
            0.0,
            rng.uniform(0.35, 0.65),
            rng.uniform(0.40, 0.75),
            rng.uniform(0.20, 0.55),
            rng.uniform(0.10, 0.40),
        ],
        dtype=float,
    )
    corner_weights = np.asarray([1.0, 0.20, 0.20, 0.20, 0.20], dtype=float)
    for node in range(1, 5):
        residual = max(1.0 - precise_weights[node] - corner_weights[node], 0.0)
        total = precise_weights[node] + corner_weights[node] + residual
        output[node] = (
            precise_weights[node] * p[node]
            + corner_weights[node] * c[node]
            + residual * d[node]
        ) / max(total, 1e-12)
    noise_std = _node_matrix(cfg, "bridge_noise_by_node_mode") * trust_scale
    output += rng.normal(0.0, noise_std, size=(5, 3))
    output[0] = c[0]
    return output.reshape(-1)


def _corner_local_pool(
    ctx: Any,
    state: dict[str, Any],
    rng: np.random.Generator,
    count: int,
) -> list[dict[str, Any]]:
    archive = state["archives"]["corner"]
    mean = np.asarray(state["corner_mean"], dtype=float)
    covariance = np.asarray(state["corner_covariance"], dtype=float)
    vectors = _sample_multivariate(rng, mean, covariance, count, antithetic=True)
    rows: list[dict[str, Any]] = []
    for index, vector in enumerate(vectors):
        if index % 2 == 1:
            parent = _record_vector(archive[int(rng.integers(0, min(len(archive), 24)))])
            vector = parent + _local_noise(rng, ctx.cfg, float(state["trust_scale"]))
            vector[:3] = parent[:3]
        else:
            vector[:3] = mean[:3]
        rows.append(_proposal_row(ctx, vector, f"corner_local_{index:04d}", "corner_local"))
    return rows


def _bridge_pool(
    ctx: Any,
    state: dict[str, Any],
    rng: np.random.Generator,
    count: int,
) -> list[dict[str, Any]]:
    archives = state["archives"]
    rows: list[dict[str, Any]] = []
    for index in range(count):
        damped_index = int(rng.integers(0, min(len(archives["damped"]), 20)))
        precise_index = int(rng.integers(0, min(len(archives["precise"]), 20)))
        corner_index = int(rng.integers(0, min(len(archives["corner"]), 24)))
        vector = _bridge_vector(
            rng,
            _record_vector(archives["damped"][damped_index]),
            _record_vector(archives["precise"][precise_index]),
            _record_vector(archives["corner"][corner_index]),
            ctx.cfg,
            float(state["trust_scale"]),
        )
        rows.append(
            _proposal_row(
                ctx,
                vector,
                f"bridge_d{damped_index:02d}_p{precise_index:02d}_c{corner_index:02d}_{index:03d}",
                "boundary_bridge",
            )
        )
    return rows


def _trust_mix_pool(
    ctx: Any,
    state: dict[str, Any],
    rng: np.random.Generator,
    count: int,
) -> list[dict[str, Any]]:
    corner = state["archives"]["corner"]
    rows: list[dict[str, Any]] = []
    for index in range(count):
        n_parent = 2 if rng.random() < 0.6 else 3
        indices = rng.choice(min(len(corner), 32), size=n_parent, replace=False)
        weights = rng.dirichlet(np.full(n_parent, 2.0))
        parent_vectors = [
            _record_vector(corner[int(parent_index)]) for parent_index in indices
        ]
        vector = sum(
            float(weight) * parent
            for weight, parent in zip(weights, parent_vectors)
        )
        vector += 0.55 * _local_noise(rng, ctx.cfg, float(state["trust_scale"]))
        # Node 0 is selected from an already validated parent rather than
        # interpolated into an untested launch profile. Only nodes 1--4 are
        # continuous Stage2.2 search variables.
        vector[:3] = parent_vectors[int(np.argmax(weights))][:3]
        rows.append(_proposal_row(ctx, vector, f"trust_mix_{index:04d}", "trust_mix"))
    return rows


def _random_local_pool(
    ctx: Any,
    state: dict[str, Any],
    rng: np.random.Generator,
    count: int,
) -> list[dict[str, Any]]:
    corner = state["archives"]["corner"]
    radius = _node_matrix(ctx.cfg, "random_radius_by_node_mode") * float(state["trust_scale"])
    rows: list[dict[str, Any]] = []
    for index in range(count):
        parent_index = int(rng.integers(0, min(len(corner), 32)))
        nodes = _record_vector(corner[parent_index]).reshape(5, 3).copy()
        nodes += rng.uniform(-radius, radius, size=(5, 3))
        nodes[0] = _record_vector(corner[parent_index]).reshape(5, 3)[0]
        rows.append(
            _proposal_row(
                ctx,
                nodes.reshape(-1),
                f"random_corner_parent_{parent_index:02d}_{index:04d}",
                "random_local",
            )
        )
    return rows


def build_generation_manifest(
    ctx: Any,
    history: SourceHistory,
    state: dict[str, Any],
    paths: Stage22Paths,
    surrogate: dict[str, Any],
) -> dict[str, Any]:
    generation = int(state["generation"])
    generation_dir = paths.generations / f"gen_{generation:03d}"
    generation_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = generation_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)

    search = ctx.cfg["search"]
    quota = {str(key): int(value) for key, value in search["family_quotas"].items()}
    population = int(search["population_size"])
    if sum(quota.values()) != population:
        raise ValueError("Stage2.2 family quotas do not sum to population_size")
    seed = int(state["rng_seed"]) + generation * 200003
    rng = np.random.default_rng(seed)
    multiplier = max(1, int(search.get("proposal_pool_multiplier", 4)))

    families: dict[str, list[dict[str, Any]]] = {
        "anchors": _anchor_rows(ctx, state["archives"], quota["anchors"]),
        "multi_center_probes": _probe_rows(
            ctx,
            state["archives"],
            generation=generation,
            trust_scale=float(state["trust_scale"]),
        ),
        "corner_local": _corner_local_pool(
            ctx,
            state,
            rng,
            max(quota["corner_local"] * multiplier, quota["corner_local"]),
        ),
        "boundary_bridge": _bridge_pool(
            ctx,
            state,
            rng,
            max(quota["boundary_bridge"] * multiplier, quota["boundary_bridge"]),
        ),
        "trust_mix": _trust_mix_pool(
            ctx,
            state,
            rng,
            max(quota["trust_mix"] * multiplier, quota["trust_mix"]),
        ),
        "random_local": _random_local_pool(
            ctx,
            state,
            rng,
            max(quota["random_local"] * multiplier, quota["random_local"]),
        ),
    }

    selected: list[dict[str, Any]] = []
    unranked_cfg = search.get("unranked_fraction_by_family", {})
    for family_name in (
        "anchors",
        "multi_center_probes",
        "corner_local",
        "boundary_bridge",
        "trust_mix",
        "random_local",
    ):
        rows = families[family_name]
        _apply_surrogate_ranking(ctx, rows, surrogate)
        if family_name in {"anchors", "multi_center_probes"}:
            chosen = rows[: quota[family_name]]
        else:
            chosen = _family_select(
                rng,
                rows,
                quota=quota[family_name],
                unranked_fraction=float(unranked_cfg.get(family_name, 0.5)),
            )
        selected.extend(chosen)
    selected = _dedupe_proposals(selected)

    attempts = 0
    while len(selected) < population and attempts < population * 100:
        attempts += 1
        fill = _random_local_pool(ctx, state, rng, 1)[0]
        _apply_surrogate_ranking(ctx, [fill], surrogate)
        selected = _dedupe_proposals([*selected, fill])
    if len(selected) != population:
        raise RuntimeError(f"Could construct only {len(selected)} unique Stage2.2 candidates")

    for population_index, row in enumerate(selected):
        vector = _parse_vector(row["vector"])
        row["candidate_id"] = vector_digest(vector, f"s22g{generation:03d}")
        row["population_index"] = population_index
        row["generation"] = generation
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.2",
        "generation": generation,
        "random_seed": seed,
        "population_size": population,
        "family_quotas": quota,
        "trust_scale": float(state["trust_scale"]),
        "probe_centers": [
            _record_summary(record) for record in select_probe_centers(state["archives"])
        ],
        "surrogate_enabled": bool(surrogate.get("enabled")),
        "surrogate_validation": {
            key: value
            for key, value in surrogate.items()
            if not key.endswith("_model")
        },
        "candidates": selected,
    }
    jsonio.assert_json_finite(manifest, context="Stage2.2 generation manifest")
    atomic_write_json(manifest_path, manifest)
    write_csv(generation_dir / "candidate_manifest.csv", selected)
    return manifest


def candidate_specs_from_manifest(ctx: Any, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    horizon = int(ctx.cfg["trajectory"]["horizon_steps"])
    specs: list[dict[str, Any]] = []
    optional_prediction_keys = (
        "predicted_final3_box_max_error_m",
        "predicted_terminal_velocity_m_per_s",
        "predicted_late_velocity_rms_m_per_s",
        "predicted_corner_max_violation",
        "predicted_corner_sum_violation",
    )
    for row in manifest["candidates"]:
        vector = _parse_vector(row["vector"])
        decoded = s2.decode_vector(ctx, vector)
        spec: dict[str, Any] = {
            "kind": "stage2_2_candidate",
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
        }
        for key in optional_prediction_keys:
            value = _finite_or_none(row.get(key))
            spec[key] = value
        specs.append(spec)
    jsonio.assert_json_finite(specs, context="Stage2.2 generation specs")
    return specs


# ---------------------------------------------------------------------------
# Generation evaluation and state update
# ---------------------------------------------------------------------------


def summarize_generation(
    ctx: Any,
    manifest: dict[str, Any],
    results: Sequence[dict[str, Any]],
    paths: Stage22Paths,
) -> list[dict[str, Any]]:
    generation = int(manifest["generation"])
    generation_dir = paths.generations / f"gen_{generation:03d}"
    by_id = {str(result.get("experiment_id")): result for result in results}
    rows: list[dict[str, Any]] = []
    prediction_keys = (
        "predicted_final3_box_max_error_m",
        "predicted_terminal_velocity_m_per_s",
        "predicted_late_velocity_rms_m_per_s",
        "predicted_corner_max_violation",
        "predicted_corner_sum_violation",
    )
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
                "stage2_2_max_violation": 1e6,
                "stage2_2_sum_violation": 4e6,
                "stage2_2_l2_violation": 2e6,
                "stage2_2_quality": 1e12,
                "continuous_objective": 1e12,
                "selection_score": 99e12,
            }
        else:
            metrics = stage22_metrics(ctx, result, decoded)
        row: dict[str, Any] = {
            "stage": "Stage2.2",
            "generation": generation,
            "candidate_id": candidate_id,
            "population_index": int(candidate["population_index"]),
            "source_name": candidate["source_name"],
            "source_type": candidate["source_type"],
            "linear_prefilter_score": float(candidate["linear_prefilter_score"]),
            "proposal_rank_score": _finite_or_none(candidate.get("proposal_rank_score")),
            "parameter_vector": vector.tolist(),
            "validation_id": candidate_id,
        }
        for key in prediction_keys:
            row[key] = _finite_or_none(candidate.get(key))
        row.update(metrics)
        rows.append(row)
    rows.sort(key=lambda row: (_finite(row.get("selection_score"), 99e12), str(row["candidate_id"])))
    for rank, row in enumerate(rows, start=1):
        row["generation_rank"] = rank
    write_csv(generation_dir / "generation_results.csv", rows)
    atomic_write_json(generation_dir / "generation_results.json", rows)
    return rows


def _record_from_stage22_row(row: dict[str, Any], run_dir: Path) -> dict[str, Any] | None:
    if not _as_bool(row.get("success"), False):
        return None
    try:
        vector = _parse_vector(row.get("parameter_vector"))
    except Exception:
        return None
    record = copy.deepcopy(row)
    record.update(
        {
            "source_stage": "Stage2.2",
            "source_run": str(run_dir),
            "source_generation_group": 2000 + _as_int(row.get("generation"), 0),
            "vector": vector.tolist(),
            "vector_digest": _vector_key(vector),
        }
    )
    return record


def _save_best_candidate(
    ctx: Any,
    paths: Stage22Paths,
    row: dict[str, Any],
    result: dict[str, Any] | None,
) -> None:
    paths.best.mkdir(parents=True, exist_ok=True)
    atomic_write_json(paths.best / "best_corner_candidate.json", row)
    vector = _parse_vector(row["parameter_vector"])
    decoded = s2.decode_vector(ctx, vector)
    action_rows: list[dict[str, Any]] = []
    for step in range(len(decoded["action_norm_tsc"])):
        action_rows.append(
            {
                "step_index": step,
                "mode_1": float(decoded["mode_coefficients"][step, 0]),
                "mode_2": float(decoded["mode_coefficients"][step, 1]),
                "mode_3": float(decoded["mode_coefficients"][step, 2]),
                "action_norm_tsc": np.asarray(decoded["action_norm_tsc"])[step].tolist(),
                "action_norm_display": np.asarray(decoded["action_norm_display"])[step].tolist(),
            }
        )
    write_csv(paths.best / "best_corner_action_sequence.csv", action_rows)
    if result is not None:
        atomic_write_json_gz(paths.best / "best_corner_tsc_result.json.gz", result)


def update_state(
    ctx: Any,
    state: dict[str, Any],
    rows: list[dict[str, Any]],
    results: Sequence[dict[str, Any]],
    paths: Stage22Paths,
) -> dict[str, Any]:
    generation = int(state["generation"])
    successful_records = [
        record
        for row in rows
        if (record := _record_from_stage22_row(row, paths.run_dir)) is not None
    ]
    if not successful_records:
        raise RuntimeError(f"No successful Stage2.2 candidates in generation {generation}")
    archives = rebuild_archives(ctx.cfg, state["archives"], successful_records)
    for key in ("corner", "damped", "precise"):
        if not archives[key]:
            raise RuntimeError(f"Stage2.2 archive update unexpectedly emptied {key}")

    successful_rows = [row for row in rows if _as_bool(row.get("success"), False)]
    successful_rows.sort(key=lambda row: _finite(row.get("selection_score"), 99e12))
    best_row = successful_rows[0]
    best_score = float(best_row["selection_score"])
    previous_score = _finite(state.get("best_selection_score"), math.inf)
    meaningful = float(ctx.cfg["search"].get("meaningful_improvement", 1e-5))
    improved = best_score < previous_score - meaningful
    strict_this_generation = any(
        _as_bool(row.get("strict_gate_pass"), False) for row in successful_rows
    )
    strict_found = bool(state.get("strict_gate_found", False) or strict_this_generation)
    generations_without = 0 if improved else int(state.get("generations_without_improvement", 0)) + 1

    trust = float(state.get("trust_scale", 1.0))
    search = ctx.cfg["search"]
    if improved:
        trust *= float(search.get("trust_shrink_on_improvement", 0.9))
    else:
        trust *= float(search.get("trust_shrink_without_improvement", 0.78))
    trust = max(float(search.get("minimum_trust_scale", 0.35)), trust)

    elite_count = int(search.get("archive_elite_count", 24))
    corner_vectors = [_record_vector(record) for record in archives["corner"][:elite_count]]
    corner_mean, corner_covariance = fit_corner_covariance(
        corner_vectors,
        cfg=ctx.cfg,
        trust_scale=trust,
    )
    new_state = copy.deepcopy(state)
    new_state.update(
        {
            "generation": generation + 1,
            "archives": archives,
            "corner_mean": corner_mean.tolist(),
            "corner_covariance": corner_covariance.tolist(),
            "trust_scale": float(trust),
            "strict_gate_found": strict_found,
            "generations_without_improvement": generations_without,
            "last_generation_best": _record_summary(best_row),
            "updated_utc": utc_timestamp(),
        }
    )
    if improved:
        new_state.update(
            {
                "best_selection_score": best_score,
                "best_candidate_id": best_row["candidate_id"],
                "best_generation": generation,
                "best_vector": _parse_vector(best_row["parameter_vector"]).tolist(),
                "best_record_origin": "Stage2.2",
            }
        )
        by_id = {str(result.get("experiment_id")): result for result in results}
        _save_best_candidate(ctx, paths, best_row, by_id.get(str(best_row["candidate_id"])))

    max_generations = int(search["max_generations"])
    strict_patience = int(search.get("strict_patience_generations", 1))
    if new_state["generation"] >= max_generations:
        new_state["finished"] = True
        new_state["stop_reason"] = "max_generations"
    elif strict_found and generations_without >= strict_patience:
        new_state["finished"] = True
        new_state["stop_reason"] = "strict_gate_patience"
    else:
        new_state["finished"] = False
        new_state["stop_reason"] = ""

    generation_dir = paths.generations / f"gen_{generation:03d}"
    for key in ("strict", "corner", "damped", "precise"):
        write_csv(generation_dir / f"{key}_archive_after.csv", archives[key])
    atomic_write_json(paths.state, new_state)
    return new_state


def aggregate_generation_rows(paths: Stage22Paths) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths.generations.glob("gen_*/generation_results.json")):
        payload = read_json_any(path)
        if isinstance(payload, list):
            rows.extend(dict(row) for row in payload)
    return rows


def run_one_generation(
    ctx: Any,
    history: SourceHistory,
    paths: Stage22Paths,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    state = read_json(paths.state)
    if state.get("finished"):
        return state
    historical_rows = aggregate_generation_rows(paths)
    surrogate = fit_corner_surrogate(ctx, history.records, historical_rows)
    atomic_write_json(paths.analysis / "corner_surrogate.json", surrogate)
    manifest = build_generation_manifest(ctx, history, state, paths, surrogate)
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
    best = rows[0] if rows else None
    print(
        strict_json_text(
            {
                "stage": "Stage2.2",
                "generation": int(manifest["generation"]),
                "successful": sum(_as_bool(row.get("success"), False) for row in rows),
                "population": len(rows),
                "strict": sum(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
                "relaxed": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in rows),
                "best": None
                if best is None
                else {
                    "candidate_id": best.get("candidate_id"),
                    "gate_label": best.get("gate_label"),
                    "selection_score": best.get("selection_score"),
                    "final3_box_max_error_m": best.get("stage2_2_final3_box_max_error_m"),
                    "terminal_velocity_m_per_s": best.get("terminal_velocity_m_per_s"),
                    "late_velocity_rms_m_per_s": best.get("late_velocity_rms_m_per_s"),
                    "max_violation": best.get("stage2_2_max_violation"),
                    "sum_violation": best.get("stage2_2_sum_violation"),
                },
                "trust_scale": state["trust_scale"],
                "next_generation": state["generation"],
                "finished": state["finished"],
                "stop_reason": state["stop_reason"],
            }
        ),
        flush=True,
    )
    return state


def run_optimization(
    ctx: Any,
    history: SourceHistory,
    paths: Stage22Paths,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    state = read_json(paths.state)
    while not state.get("finished"):
        state = run_one_generation(ctx, history, paths, backend=backend, resume=resume)
    return state


# ---------------------------------------------------------------------------
# Category-aware confirmation and analysis
# ---------------------------------------------------------------------------


def _unique_best_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not _as_bool(row.get("success"), False):
            continue
        try:
            digest = _vector_key(row.get("parameter_vector"))
        except Exception:
            continue
        previous = unique.get(digest)
        if previous is None or _constraint_sort_key(row) < _constraint_sort_key(previous):
            unique[digest] = row
    return list(unique.values())


def select_confirmation_candidates(
    rows: Sequence[dict[str, Any]],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    unique = _unique_best_rows(rows)
    confirmation = cfg["confirmation"]
    categories: list[tuple[str, list[dict[str, Any]], int]] = []
    strict = sorted(
        [row for row in unique if _as_bool(row.get("strict_gate_pass"), False)],
        key=_constraint_sort_key,
    )
    corner = sorted(unique, key=_constraint_sort_key)
    speed_safe = sorted(
        [row for row in unique if _strict_speed_safe(row, cfg)],
        key=_damped_sort_key,
    )
    position_front = sorted(
        [row for row in unique if _strict_position_safe(row)],
        key=lambda row: (
            max(
                _finite(row.get("stage2_2_terminal_speed_violation"), 1e9),
                _finite(row.get("stage2_2_late_speed_violation"), 1e9),
            ),
            _finite(row.get("stage2_2_sum_violation"), 1e9),
            _finite(row.get("stage2_2_final3_box_max_error_m"), 1e9),
        ),
    )
    gate_hall = sorted(
        unique,
        key=lambda row: (
            _as_int(row.get("gate_tier"), 99),
            _finite(row.get("stage2_legacy_continuous_objective"), 1e12),
            _finite(row.get("stage2_legacy_selection_score"), 99e12),
        ),
    )
    categories.extend(
        [
            ("strict", strict, int(confirmation.get("strict_candidates", 3))),
            ("corner", corner, int(confirmation.get("corner_candidates", 5))),
            ("speed_safe", speed_safe, int(confirmation.get("speed_safe_candidates", 2))),
            ("position_front", position_front, int(confirmation.get("position_front_candidates", 2))),
            ("gate_hall", gate_hall, int(confirmation.get("gate_hall_candidates", 2))),
        ]
    )
    selected: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for reason, candidates, limit in categories:
        for row in candidates[: max(limit, 0)]:
            digest = _vector_key(row["parameter_vector"])
            if digest not in selected:
                copy_row = copy.deepcopy(row)
                copy_row["confirmation_reasons"] = [reason]
                selected[digest] = copy_row
                order.append(digest)
            elif reason not in selected[digest]["confirmation_reasons"]:
                selected[digest]["confirmation_reasons"].append(reason)
    maximum = int(confirmation["max_unique_candidates"])
    result = [selected[digest] for digest in order[:maximum]]
    if len(result) < maximum:
        seen = set(order)
        for row in corner:
            digest = _vector_key(row["parameter_vector"])
            if digest in seen:
                continue
            copy_row = copy.deepcopy(row)
            copy_row["confirmation_reasons"] = ["corner_fill"]
            result.append(copy_row)
            seen.add(digest)
            if len(result) >= maximum:
                break
    return result[:maximum]


def run_confirmation(
    ctx: Any,
    paths: Stage22Paths,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    rows = aggregate_generation_rows(paths)
    candidates = select_confirmation_candidates(rows, ctx.cfg)
    repeats = int(ctx.cfg["confirmation"]["repeats_per_candidate"])
    if not candidates:
        verdict = {"verdict": "NO_SUCCESSFUL_STAGE2_2_CANDIDATE", "created_utc": utc_timestamp()}
        atomic_write_json(paths.confirmations / "stage2_2_verdict.json", verdict)
        return verdict

    specs: list[dict[str, Any]] = []
    for rank, row in enumerate(candidates, start=1):
        vector = _parse_vector(row["parameter_vector"])
        decoded = s2.decode_vector(ctx, vector)
        linear = s2.linear_prefilter_metrics(ctx, decoded)
        for repeat in range(repeats):
            experiment_id = f"s22confirm_rank{rank:02d}_{row['candidate_id']}_r{repeat:02d}"
            specs.append(
                {
                    "kind": "stage2_2_confirmation",
                    "experiment_id": experiment_id,
                    "candidate_id": row["candidate_id"],
                    "hall_of_fame_rank": rank,
                    "confirmation_repeat": repeat,
                    "confirmation_reasons": list(row.get("confirmation_reasons", [])),
                    "generation": int(row["generation"]),
                    "population_index": int(row["population_index"]),
                    "source_name": "stage2_2_category_hall_of_fame",
                    "source_type": "confirmation",
                    "horizon_steps": int(ctx.cfg["trajectory"]["horizon_steps"]),
                    "parameter_vector": vector.tolist(),
                    "mode_nodes": decoded["nodes"].tolist(),
                    "mode_coefficients": decoded["mode_coefficients"].tolist(),
                    "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
                    "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
                    "linear_prefilter_score": float(linear["linear_prefilter_score"]),
                    "predicted_terminal_R_error_m": float(linear["predicted_terminal_R_error_m"]),
                    "predicted_terminal_Z_error_m": float(linear["predicted_terminal_Z_error_m"]),
                    "predicted_terminal_Ip_error_A": float(linear["predicted_terminal_Ip_error_A"]),
                }
            )
    jsonio.assert_json_finite(specs, context="Stage2.2 confirmation specs")
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
        metrics = stage22_metrics(ctx, result, s2.decode_vector(ctx, vector))
        metric_rows.append(
            {
                "stage": "Stage2.2 confirmation",
                "experiment_id": result["experiment_id"],
                "candidate_id": spec["candidate_id"],
                "hall_of_fame_rank": spec["hall_of_fame_rank"],
                "repeat": spec["confirmation_repeat"],
                "confirmation_reasons": spec["confirmation_reasons"],
                "parameter_vector": vector.tolist(),
                **metrics,
            }
        )
    write_csv(paths.confirmations / "confirmation_results.csv", metric_rows)
    atomic_write_json(paths.confirmations / "confirmation_results.json", metric_rows)

    summary_rows: list[dict[str, Any]] = []
    for rank, candidate in enumerate(candidates, start=1):
        subset = [row for row in metric_rows if row["candidate_id"] == candidate["candidate_id"]]
        successful = [row for row in subset if _as_bool(row.get("success"), False)]
        final3_values = _finite_values(
            row.get("stage2_2_final3_box_max_error_m") for row in successful
        )
        terminal_velocities = _finite_values(
            row.get("terminal_velocity_m_per_s") for row in successful
        )
        late_velocities = _finite_values(
            row.get("late_velocity_rms_m_per_s") for row in successful
        )
        max_violations = _finite_values(row.get("stage2_2_max_violation") for row in successful)
        summary_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "hall_of_fame_rank": rank,
                "confirmation_reasons": candidate.get("confirmation_reasons", []),
                "repeats": repeats,
                "successful_repeats": len(successful),
                "all_repeats_strict_gate": len(successful) == repeats
                and all(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
                "all_repeats_relaxed_gate": len(successful) == repeats
                and all(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful),
                "worst_gate_tier": max(
                    (_as_int(row.get("gate_tier"), 99) for row in subset), default=99
                ),
                "worst_final3_box_max_error_m": max(final3_values) if final3_values else None,
                "max_terminal_velocity_m_per_s": max(terminal_velocities)
                if terminal_velocities
                else None,
                "max_late_velocity_rms_m_per_s": max(late_velocities)
                if late_velocities
                else None,
                "worst_stage2_2_max_violation": max(max_violations) if max_violations else None,
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
    atomic_write_json(paths.confirmations / "stage2_2_verdict.json", verdict)
    print(strict_json_text(verdict), flush=True)
    return verdict


def _category_hall_rows(
    rows: Sequence[dict[str, Any]], cfg: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    unique = _unique_best_rows(rows)
    return {
        "corner": sorted(unique, key=_constraint_sort_key),
        "gate": sorted(
            unique,
            key=lambda row: (
                _as_int(row.get("gate_tier"), 99),
                _finite(row.get("stage2_legacy_continuous_objective"), 1e12),
                _finite(row.get("selection_score"), 99e12),
            ),
        ),
        "speed_safe": sorted(
            [row for row in unique if _strict_speed_safe(row, cfg)],
            key=_damped_sort_key,
        ),
        "position": sorted(
            [row for row in unique if _strict_position_safe(row)],
            key=lambda row: (
                max(
                    _finite(row.get("stage2_2_terminal_speed_violation"), 1e9),
                    _finite(row.get("stage2_2_late_speed_violation"), 1e9),
                ),
                _finite(row.get("stage2_2_sum_violation"), 1e9),
            ),
        ),
        "strict": sorted(
            [row for row in unique if _as_bool(row.get("strict_gate_pass"), False)],
            key=_constraint_sort_key,
        ),
    }


def _result_for_row(paths: Stage22Paths, row: dict[str, Any]) -> dict[str, Any] | None:
    generation = _as_int(row.get("generation"), -1)
    candidate_id = str(row.get("candidate_id", ""))
    if generation < 0 or not candidate_id:
        return None
    path = paths.evaluations / f"gen_{generation:03d}" / f"{candidate_id}.json.gz"
    return read_json_gz(path) if path.exists() else None


def _plot_analysis(
    ctx: Any,
    rows: list[dict[str, Any]],
    best_result: dict[str, Any] | None,
    paths: Stage22Paths,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[Stage2.2 analysis] matplotlib unavailable; plots skipped: {exc}", flush=True)
        return
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    if successful:
        x = [
            1000.0 * _finite(row.get("stage2_2_final3_box_max_error_m"), math.nan)
            for row in successful
        ]
        y = [_finite(row.get("late_velocity_rms_m_per_s"), math.nan) for row in successful]
        color = [_finite(row.get("terminal_velocity_m_per_s"), math.nan) for row in successful]
        plt.figure(figsize=(8, 6))
        scatter = plt.scatter(x, y, c=color, s=18, alpha=0.7)
        plt.axvline(30.0, linestyle="--", linewidth=1)
        plt.axhline(float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"]), linestyle="--", linewidth=1)
        plt.xlabel("Maximum R/Z box error over final three samples [mm]")
        plt.ylabel("Late velocity RMS [m/s]")
        plt.title("Stage2.2 strict-corner feasibility map")
        plt.colorbar(scatter, label="Terminal R/Z speed [m/s]")
        plt.tight_layout()
        plt.savefig(paths.analysis / "corner_feasibility_scatter.png", dpi=170)
        plt.close()

        best_by_generation: dict[int, dict[str, Any]] = {}
        for row in successful:
            generation = _as_int(row.get("generation"), 0)
            previous = best_by_generation.get(generation)
            if previous is None or _constraint_sort_key(row) < _constraint_sort_key(previous):
                best_by_generation[generation] = row
        generations = sorted(best_by_generation)
        plt.figure(figsize=(8, 5))
        plt.plot(
            generations,
            [
                _finite(best_by_generation[g].get("stage2_2_max_violation"), math.nan)
                for g in generations
            ],
            marker="o",
        )
        plt.axhline(0.0, linestyle="--", linewidth=1)
        plt.xlabel("Generation")
        plt.ylabel("Best maximum normalized strict-constraint violation")
        plt.title("Stage2.2 feasibility progress")
        plt.tight_layout()
        plt.savefig(paths.analysis / "max_violation_by_generation.png", dpi=170)
        plt.close()

    if best_result and best_result.get("success") and best_result.get("trajectory"):
        trajectory = best_result["trajectory"]
        r = [
            (float(row["R"]) - float(ctx.cfg["target"]["R"])) * 1000.0
            for row in trajectory
        ]
        z = [
            (float(row["Z"]) - float(ctx.cfg["target"]["Z"])) * 1000.0
            for row in trajectory
        ]
        plt.figure(figsize=(7, 7))
        plt.plot(r, z, marker="o")
        for tol_mm in (30.0, 40.0):
            box_x = [-tol_mm, tol_mm, tol_mm, -tol_mm, -tol_mm]
            box_y = [-tol_mm, -tol_mm, tol_mm, tol_mm, -tol_mm]
            plt.plot(box_x, box_y, linestyle="--", linewidth=1)
        plt.scatter([0.0], [0.0], marker="x", s=80)
        plt.xlabel("R error [mm]")
        plt.ylabel("Z error [mm]")
        plt.title("Stage2.2 best corner real-TSC trajectory")
        plt.axis("equal")
        plt.tight_layout()
        plt.savefig(paths.analysis / "best_corner_trajectory_rz.png", dpi=170)
        plt.close()


def analyze_stage22(
    ctx: Any,
    history: SourceHistory,
    paths: Stage22Paths,
) -> dict[str, Any]:
    rows = aggregate_generation_rows(paths)
    write_csv(paths.analysis / "all_generation_results.csv", rows)
    atomic_write_json(paths.analysis / "all_generation_results.json", rows)
    halls = _category_hall_rows(rows, ctx.cfg)
    for name, hall in halls.items():
        write_csv(paths.analysis / f"{name}_hall_of_fame.csv", hall[:100])
        atomic_write_json(paths.analysis / f"{name}_hall_of_fame.json", hall[:100])
    state = read_json(paths.state)
    verdict_path = paths.confirmations / "stage2_2_verdict.json"
    verdict = read_json(verdict_path) if verdict_path.exists() else {"verdict": "NOT_CONFIRMED"}
    best = halls["corner"][0] if halls["corner"] else None
    best_result = _result_for_row(paths, best) if best is not None else None
    if best is not None:
        _save_best_candidate(ctx, paths, best, best_result)
    _plot_analysis(ctx, rows, best_result, paths)

    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage2.2",
        "created_utc": utc_timestamp(),
        "source_stage1_1_run": str(history.stage1_run),
        "source_stage2_run": str(history.stage2_run),
        "source_stage2_1_run": str(history.stage21_run),
        "source_unique_candidates": len(history.records),
        "n_evaluations": len(rows),
        "n_successful": len(successful),
        "n_strict_gate": sum(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
        "n_relaxed_gate": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful),
        "n_max_violation_le_0p05": sum(
            _finite(row.get("stage2_2_max_violation"), 1e9) <= 0.05 for row in successful
        ),
        "n_max_violation_le_0p10": sum(
            _finite(row.get("stage2_2_max_violation"), 1e9) <= 0.10 for row in successful
        ),
        "n_strict_speed_safe": sum(_strict_speed_safe(row, ctx.cfg) for row in successful),
        "n_strict_position_safe": sum(_strict_position_safe(row) for row in successful),
        "archives": {key: len(value) for key, value in state["archives"].items()},
        "verdict": verdict["verdict"],
        "best_corner": best,
        "state": {
            key: state.get(key)
            for key in (
                "generation",
                "trust_scale",
                "strict_gate_found",
                "finished",
                "stop_reason",
                "best_candidate_id",
                "best_selection_score",
            )
        },
    }
    atomic_write_json(paths.analysis / "stage2_2_analysis_summary.json", summary)

    report = [
        "# Stage2.2 strict-corner feasibility report",
        "",
        f"- Source Stage2 run: `{history.stage2_run}`",
        f"- Source Stage2.1 run: `{history.stage21_run}`",
        f"- Combined unique real-TSC source vectors: **{len(history.records)}**",
        f"- New Stage2.2 real-TSC evaluations: **{len(rows)}**",
        f"- Successful evaluations: **{len(successful)}**",
        f"- Strict 30 mm holds: **{summary['n_strict_gate']}**",
        f"- Relaxed 40 mm holds: **{summary['n_relaxed_gate']}**",
        f"- Confirmation verdict: **{summary['verdict']}**",
        "",
        "## Method",
        "",
        "The hard Stage2 gate is unchanged. Stage2.2 recomputes the final-three-sample rectangular-box condition from every raw Stage2 and Stage2.1 TSC trajectory, then minimizes the largest normalized violation among final-three position, terminal speed, late speed and terminal Ip.",
        "",
        "The search uses strict-speed damped, near-position precise, minimum-violation corner and strict archives. Three independent centers receive deterministic antithetic probes; all model predictions are ranking aids only.",
        "",
    ]
    if best is not None:
        report.extend(
            [
                "## Best new corner candidate",
                "",
                f"- Candidate: `{best['candidate_id']}`",
                f"- Gate: **{best['gate_label']}**",
                f"- Final-three maximum box error: **{1000.0 * _finite(best.get('stage2_2_final3_box_max_error_m'), math.nan):.3f} mm**",
                f"- Terminal speed: **{_finite(best.get('terminal_velocity_m_per_s'), math.nan):.6f} m/s**",
                f"- Late speed RMS: **{_finite(best.get('late_velocity_rms_m_per_s'), math.nan):.6f} m/s**",
                f"- Maximum normalized violation: **{_finite(best.get('stage2_2_max_violation'), math.nan):.6f}**",
                f"- Sum normalized violation: **{_finite(best.get('stage2_2_sum_violation'), math.nan):.6f}**",
                "",
            ]
        )
    jsonio.atomic_write_text(paths.run_dir / "STAGE2_2_REPORT.md", "\n".join(report) + "\n")
    print(strict_json_text(summary), flush=True)
    return summary


# ---------------------------------------------------------------------------
# Deterministic self-test and public entry point
# ---------------------------------------------------------------------------


def synthetic_self_test() -> dict[str, Any]:
    class Dummy:
        pass

    dummy = Dummy()
    dummy.cfg = {
        "gate": {
            "precise_tolerance_m": 0.03,
            "terminal_velocity_max_m_per_s": 0.1,
            "late_velocity_rms_max_m_per_s": 0.1,
            "ip_tolerance_a": 10000.0,
        },
        "archives": {
            "damped_capacity": 4,
            "precise_capacity": 4,
            "corner_capacity": 5,
            "strict_capacity": 2,
            "minimum_vector_distance": 0.001,
            "damped_final3_box_limit_m": 0.036,
            "precise_final3_box_limit_m": 0.033,
            "precise_terminal_box_limit_m": 0.0305,
            "precise_terminal_velocity_cap_m_per_s": 0.2,
            "precise_late_velocity_cap_m_per_s": 0.22,
            "corner_max_violation_limit": 0.25,
        },
        "search": {
            "local_std_by_node_mode": [
                [0.0, 0.0, 0.0],
                [0.02, 0.02, 0.01],
                [0.04, 0.04, 0.02],
                [0.05, 0.05, 0.02],
                [0.05, 0.05, 0.02],
            ],
            "covariance_diagonal_shrinkage": 0.35,
            "covariance_eigen_floor": 2e-5,
            "covariance_eigen_ceiling": 0.03,
        },
    }
    violations = _constraint_violations(
        dummy,
        final3_box_max_error_m=0.0312,
        terminal_velocity_m_per_s=0.05,
        late_velocity_rms_m_per_s=0.102,
        terminal_Ip_error_A=500.0,
    )
    assert math.isclose(violations["stage2_2_position_violation"], 0.04)
    assert math.isclose(violations["stage2_2_late_speed_violation"], 0.02)
    assert math.isclose(violations["stage2_2_max_violation"], 0.04)

    def record(index: int, final3: float, tv: float, lv: float) -> dict[str, Any]:
        vp = max(final3 / 0.03 - 1.0, 0.0)
        vt = max(tv / 0.1 - 1.0, 0.0)
        vl = max(lv / 0.1 - 1.0, 0.0)
        values = np.asarray([vp, vt, vl, 0.0])
        return {
            "candidate_id": f"r{index}",
            "vector": (np.arange(15, dtype=float) * 0.001 + index * 0.02).tolist(),
            "strict_gate_pass": bool(np.max(values) == 0.0),
            "relaxed_gate_pass": True,
            "stage2_2_final3_box_max_error_m": final3,
            "stage2_2_terminal_box_error_m": final3 - 0.0002,
            "terminal_velocity_m_per_s": tv,
            "late_velocity_rms_m_per_s": lv,
            "terminal_Ip_error_A": 100.0,
            "stage2_2_position_violation": vp,
            "stage2_2_terminal_speed_violation": vt,
            "stage2_2_late_speed_violation": vl,
            "stage2_2_ip_violation": 0.0,
            "stage2_2_max_violation": float(np.max(values)),
            "stage2_2_sum_violation": float(np.sum(values)),
            "stage2_2_l2_violation": float(np.linalg.norm(values)),
            "stage2_2_quality": 1.0 + index,
            "stage2_2_selection_score": 1e6 + index,
            "trailing_streak_within_30mm_steps": 0,
        }

    records = [
        record(0, 0.0312, 0.05, 0.102),
        record(1, 0.0313, 0.02, 0.099),
        record(2, 0.0299, 0.11, 0.17),
        record(3, 0.0300, 0.05, 0.09),
        record(4, 0.0320, 0.03, 0.095),
    ]
    archives = rebuild_archives(dummy.cfg, {}, records)
    assert archives["corner"][0]["candidate_id"] == "r3"
    assert all(_strict_speed_safe(row, dummy.cfg) for row in archives["damped"])
    assert archives["strict"][0]["candidate_id"] == "r3"

    vectors = [np.arange(15, dtype=float) * 0.01 + i * 0.001 for i in range(5)]
    mean, covariance = fit_corner_covariance(vectors, cfg=dummy.cfg, trust_scale=1.0)
    assert mean.shape == (15,) and covariance.shape == (15, 15)
    assert np.allclose(covariance[:3, 3:], 0.0)
    assert np.allclose(covariance[3:, :3], 0.0)
    assert np.all(np.linalg.eigvalsh(covariance) > 0.0)
    assert _hadamard(16).shape == (16, 16)
    feature = s21.surrogate_features(np.zeros((2, 15)), -np.ones(15), np.ones(15))
    assert feature.shape[0] == 2 and feature.shape[1] > 45
    return {
        "constraint_violation_math": True,
        "archive_separation": True,
        "fixed_node_covariance": True,
        "hadamard_probe_basis": True,
        "surrogate_feature_dimension": int(feature.shape[1]),
    }


def _resolve_sources_before_context(
    *,
    source_stage1_run: str | Path | None,
    source_stage2_run: str | Path | None,
    source_stage21_run: str | Path | None,
) -> tuple[Path, Path, Path]:
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    stage21_run = resolve_source_stage21_run(source_stage21_run, project_dir=project_dir)
    stage1_run, stage2_run = _resolve_source_paths_from_stage21(
        stage21_run,
        project_dir=project_dir,
        explicit_stage1=source_stage1_run,
        explicit_stage2=source_stage2_run,
    )
    _validate_source_stage1(stage1_run)
    _validate_source_stage2(stage2_run)
    return stage1_run, stage2_run, stage21_run


def execute(
    *,
    command: str,
    config_path: str | Path,
    source_stage1_1_run: str | Path | None,
    source_stage2_run: str | Path | None,
    source_stage2_1_run: str | Path | None,
    run_dir: str | Path | None,
    backend: str,
    no_resume: bool,
) -> Any:
    if command == "self-test":
        result = synthetic_self_test()
        print(strict_json_text(result), flush=True)
        return result

    stage1_run, stage2_run, stage21_run = _resolve_sources_before_context(
        source_stage1_run=source_stage1_1_run,
        source_stage2_run=source_stage2_run,
        source_stage21_run=source_stage2_1_run,
    )
    ctx = s2.load_stage2_config(
        config_path,
        source_run=stage1_run,
        run_dir_override=run_dir,
    )
    validate_stage22_config(ctx)
    history_stub = load_source_history(
        ctx,
        source_stage1_run=stage1_run,
        source_stage2_run=stage2_run,
        source_stage21_run=stage21_run,
        paths=None,
    )
    paths = initialize_stage22_run(ctx, history_stub)
    history = load_source_history(
        ctx,
        source_stage1_run=stage1_run,
        source_stage2_run=stage2_run,
        source_stage21_run=stage21_run,
        paths=paths,
    )
    load_or_initialize_state(ctx, history, paths, no_resume=no_resume)
    resume = not no_resume

    if command == "prepare":
        state = read_json(paths.state)
        payload = {
            "state": {
                "generation": state.get("generation"),
                "source_unique_record_count": state.get("source_unique_record_count"),
                "archive_sizes": {
                    key: len(value) for key, value in state.get("archives", {}).items()
                },
                "best_candidate_id": state.get("best_candidate_id"),
                "best_selection_score": state.get("best_selection_score"),
                "strict_gate_found": state.get("strict_gate_found"),
                "trust_scale": state.get("trust_scale"),
            },
            "source_catalog_summary": history.catalog_summary,
        }
        print(strict_json_text(payload), flush=True)
        return payload
    if command == "generation":
        return run_one_generation(ctx, history, paths, backend=backend, resume=resume)
    if command == "optimize":
        return run_optimization(ctx, history, paths, backend=backend, resume=resume)
    if command == "confirm":
        return run_confirmation(ctx, paths, backend=backend, resume=resume)
    if command == "analyze":
        return analyze_stage22(ctx, history, paths)
    if command == "all":
        run_optimization(ctx, history, paths, backend=backend, resume=resume)
        run_confirmation(ctx, paths, backend=backend, resume=resume)
        return analyze_stage22(ctx, history, paths)
    raise ValueError(f"Unknown command: {command}")


__all__ = [
    "SourceHistory",
    "Stage22Paths",
    "analyze_stage22",
    "build_generation_manifest",
    "build_source_catalog",
    "candidate_specs_from_manifest",
    "execute",
    "fit_corner_covariance",
    "fit_corner_surrogate",
    "initial_state",
    "load_source_history",
    "rebuild_archives",
    "run_confirmation",
    "run_one_generation",
    "run_optimization",
    "select_confirmation_candidates",
    "select_probe_centers",
    "stage22_metrics",
    "surrogate_predict",
    "synthetic_self_test",
    "validate_stage22_config",
]
