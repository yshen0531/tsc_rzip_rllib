"""Stage3.0: extended-horizon real-TSC tail SQP and MPC-compatible POC.

Stage3.0 deliberately does not return to actor-critic training.  It starts from
real-TSC validated Stage2.2 100 ms nominal trajectories, extends the episode to
150 ms, freezes the first nine 10 ms actions, and optimizes six independent
three-mode controls at steps 9-14 (18 variables).

The search has four explicit parts:
1. a 96-candidate deterministic 150 ms tail screen;
2. up to three real-TSC trust-region SQP rounds;
3. a final 18-variable finite-difference identification around the best point;
4. category-aware deterministic confirmation and analysis.

The accepted arrival window is 120-150 ms.  A precise success must satisfy the
30 mm rectangular R/Z tube and speed/Ip constraints at an allowed endpoint and
remain safe through 150 ms.  The exported controller gain is an offline local
batch sensitivity POC; it is not claimed to be a deployable feedback controller.
"""

from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import json
import math
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.core.coil_order import (
    DISPLAY_COIL_NAMES,
    TSC_COIL_NAMES,
    display_to_tsc,
    tsc_matrix_to_display,
)
from tsc_rzip_rllib.diagnostics import stage1_controllability as jsonio
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2

SCHEMA_VERSION = 1
STATE_FILENAME = "stage3_0_state.json"
MANIFEST_FILENAME = "stage3_0_manifest.json"
NOMINAL_CATALOG_FILENAME = "stage3_0_nominal_catalog.json"


# ---------------------------------------------------------------------------
# JSON, CSV, numeric and path helpers
# ---------------------------------------------------------------------------


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_json(path: Path | str) -> Any:
    return jsonio.read_json(Path(path))


def read_json_gz(path: Path | str) -> Any:
    return jsonio.read_json_gz(Path(path))


def atomic_write_json(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json(path, payload)


def atomic_write_json_gz(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json_gz(path, payload)


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def resolve_path(value: str | Path, *, root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve(strict=False)


def start_time_ms(env_cfg: dict[str, Any]) -> int:
    """Parse the numeric millisecond prefix from values such as ``1100ms``."""
    raw = str(env_cfg.get("start_folder", "0ms")).strip().lower()
    if raw.endswith("ms"):
        raw = raw[:-2]
    try:
        return int(round(float(raw)))
    except ValueError as exc:
        raise ValueError(f"Cannot parse env start_folder as milliseconds: {env_cfg.get('start_folder')!r}") from exc


def vector_digest(nominal_id: str, tail_vector: np.ndarray, prefix: str = "s30") -> str:
    rounded = np.round(np.asarray(tail_vector, dtype=float).reshape(-1), 10)
    payload = nominal_id.encode("utf-8") + b"\0" + rounded.tobytes()
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:16]}"


def _tail_vector(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        vector = np.asarray(value, dtype=float)
    elif isinstance(value, (list, tuple)):
        vector = np.asarray(value, dtype=float)
    else:
        vector = np.asarray(json.loads(str(value)), dtype=float)
    vector = vector.reshape(-1)
    if vector.shape != (18,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"Stage3.0 tail vector must contain 18 finite values, got {vector.shape}")
    return vector


def _source_vector(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        vector = np.asarray(value, dtype=float)
    elif isinstance(value, (list, tuple)):
        vector = np.asarray(value, dtype=float)
    else:
        vector = np.asarray(json.loads(str(value)), dtype=float)
    vector = vector.reshape(-1)
    if vector.shape != (15,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"Stage2.2 source vector must contain 15 finite values, got {vector.shape}")
    return vector


def _vector_key(nominal_id: str, tail: Any) -> str:
    return vector_digest(nominal_id, _tail_vector(tail), "v")


# ---------------------------------------------------------------------------
# Context and source loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage30Paths:
    run_dir: Path
    state: Path
    manifest: Path
    nominal_catalog: Path
    phases: Path
    evaluations: Path
    confirmations: Path
    analysis: Path
    best: Path
    controller: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage30Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            nominal_catalog=run_dir / NOMINAL_CATALOG_FILENAME,
            phases=run_dir / "stage3_0_phases",
            evaluations=run_dir / "stage3_0_evaluations",
            confirmations=run_dir / "stage3_0_confirmations",
            analysis=run_dir / "stage3_0_analysis",
            best=run_dir / "stage3_0_best",
            controller=run_dir / "stage3_0_controller",
            source_reference=run_dir / "source_stage2_2_reference",
        )


@dataclass
class Stage30Context:
    cfg: dict[str, Any]
    train_cfg: dict[str, Any]
    env_cfg: dict[str, Any]
    paths: Stage30Paths
    source_run: Path
    modes_tsc: np.ndarray
    initial_currents_tsc: np.ndarray
    max_delta_a: float
    min_current_tsc: np.ndarray
    max_current_tsc: np.ndarray
    tail_steps: tuple[int, ...]
    coefficient_lower: np.ndarray
    coefficient_upper: np.ndarray
    source_interpolation: np.ndarray
    nominals: list[dict[str, Any]]


_REQUIRED_SOURCE_FILES = (
    "stage2_2_config.resolved.json",
    "stage2_2_manifest.json",
    "stage2_2_analysis/all_generation_results.json",
    "stage2_2_analysis/corner_hall_of_fame.json",
    "stage2_2_analysis/speed_safe_hall_of_fame.json",
    "stage2_2_analysis/gate_hall_of_fame.json",
    "env_config.resolved.json",
    "train_config.resolved.json",
    "source_reference/analysis/coil_modes_tsc.npy",
)


def resolve_source_stage22_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE2_2_RUN", "").strip()
    if not value:
        raise ValueError(
            "A completed Stage2.2 run is required. Pass --source-stage2-2-run or set SOURCE_STAGE2_2_RUN."
        )
    run_dir = Path(value).expanduser().resolve()
    missing = [str(run_dir / relative) for relative in _REQUIRED_SOURCE_FILES if not (run_dir / relative).exists()]
    evaluation_dir = run_dir / "stage2_2_evaluations"
    if not evaluation_dir.is_dir():
        missing.append(str(evaluation_dir))
    if missing:
        raise FileNotFoundError("Incomplete Stage2.2 source run: " + ", ".join(missing))
    return run_dir


def _resolve_storage_override(value: Any, *, project_dir: Path) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return str(path.resolve(strict=False))


def validate_stage30_config(cfg: dict[str, Any]) -> None:
    trajectory = cfg["trajectory"]
    if int(trajectory.get("horizon_steps", -1)) != 15 or int(trajectory.get("horizon_ms", -1)) != 150:
        raise ValueError("Stage3.0 is fixed to a 15-step / 150 ms episode")
    if int(trajectory.get("source_horizon_steps", -1)) != 10:
        raise ValueError("Stage3.0 source_horizon_steps must be 10")
    if int(trajectory.get("n_modes", -1)) != 3:
        raise ValueError("Stage3.0 requires exactly the first three validated SVD modes")
    if list(trajectory.get("source_node_steps", [])) != [0, 2, 4, 6, 9]:
        raise ValueError("Stage3.0 requires the validated Stage2.2 source nodes [0,2,4,6,9]")
    if list(trajectory.get("tail_variable_steps", [])) != [9, 10, 11, 12, 13, 14]:
        raise ValueError("Stage3.0 tail_variable_steps must be [9,10,11,12,13,14]")
    if list(trajectory.get("frozen_action_steps", [])) != list(range(9)):
        raise ValueError("Stage3.0 must freeze source action steps 0-8")

    gate = cfg["gate"]
    if list(gate.get("allowed_arrival_steps", [])) != [12, 13, 14, 15]:
        raise ValueError("Stage3.0 allowed_arrival_steps must be [12,13,14,15]")
    if int(gate.get("required_arrival_streak_steps", 0)) != 3:
        raise ValueError("Stage3.0 requires a three-sample arrival streak")
    for key in (
        "precise_tolerance_m",
        "relaxed_tolerance_m",
        "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s",
        "ip_tolerance_a",
    ):
        number = float(gate.get(key, math.nan))
        if not math.isfinite(number) or number <= 0.0:
            raise ValueError(f"gate.{key} must be finite and positive")

    sqp = cfg["sqp"]
    if int(sqp.get("centers_per_round", 0)) != 2 or int(sqp.get("variables", 0)) != 18:
        raise ValueError("Stage3.0 uses exactly two centers and 18 tail variables per SQP round")
    for key in ("probe_delta_by_step_mode", "trust_radius_by_step_mode"):
        matrix = np.asarray(sqp.get(key, []), dtype=float)
        if matrix.shape != (6, 3) or np.any(matrix <= 0.0) or not np.all(np.isfinite(matrix)):
            raise ValueError(f"sqp.{key} must be a finite positive 6x3 matrix")
    identification = cfg["controller_identification"]
    matrix = np.asarray(identification.get("probe_delta_by_step_mode", []), dtype=float)
    if matrix.shape != (6, 3) or np.any(matrix <= 0.0) or not np.all(np.isfinite(matrix)):
        raise ValueError("controller_identification.probe_delta_by_step_mode must be a positive 6x3 matrix")

    count = int(cfg["nominals"].get("count", 0))
    category_total = sum(
        int(cfg["nominals"].get(key, 0))
        for key in (
            "corner_candidates",
            "speed_safe_candidates",
            "gate_candidates",
            "position_front_candidates",
        )
    )
    template_count = int(cfg["screen"].get("templates_per_nominal", 0))
    if count != 8 or category_total != count:
        raise ValueError("Stage3.0 nominal category quotas must sum to exactly 8")
    if template_count != 12 or count * template_count != 96:
        raise ValueError("Stage3.0 screen is fixed to 8 nominals x 12 templates = 96 candidates")
    min_success = int(cfg["screen"].get("minimum_successful_candidates", 48))
    min_nominals = int(cfg["screen"].get("minimum_successful_nominals", 4))
    if not 2 <= min_success <= 96:
        raise ValueError("screen.minimum_successful_candidates must be in [2,96]")
    if not 2 <= min_nominals <= 8:
        raise ValueError("screen.minimum_successful_nominals must be in [2,8]")
    if int(sqp.get("max_rounds", 0)) < 1:
        raise ValueError("sqp.max_rounds must be positive")
    profiles = sqp.get("linear_solver", {}).get("profiles", {})
    if set(profiles) != {"balanced", "position", "damping"}:
        raise ValueError("Stage3.0 requires balanced, position, and damping SQP profiles")


def _find_initial_currents(source_run: Path) -> np.ndarray:
    candidates = [
        source_run / "stage2_2_best/best_corner_tsc_result.json.gz",
        source_run / "best/best_tsc_result.json.gz",
    ]
    candidates.extend(sorted((source_run / "stage2_2_evaluations").glob("gen_*/*.json.gz"))[:8])
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = read_json_gz(path)
            trajectory = payload.get("trajectory", [])
            if trajectory:
                currents = np.asarray(trajectory[0]["currents_a_tsc"], dtype=float)
                if currents.shape == (14,) and np.all(np.isfinite(currents)):
                    return currents
        except Exception:
            continue
    raise RuntimeError("Could not recover the 14 initial coil currents from the Stage2.2 source run")


def _dedupe_source_rows(rows: Iterable[dict[str, Any]], minimum_distance: float) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        try:
            vector = _source_vector(row.get("parameter_vector"))
        except Exception:
            continue
        digest = hashlib.sha256(np.round(vector, 10).tobytes()).hexdigest()
        if digest in seen:
            continue
        if selected:
            distance = min(
                float(np.linalg.norm(vector - _source_vector(other["parameter_vector"])))
                for other in selected
            )
            if distance < minimum_distance:
                continue
        copy_row = copy.deepcopy(row)
        copy_row["parameter_vector"] = vector.tolist()
        selected.append(copy_row)
        seen.add(digest)
    return selected


def build_nominal_catalog(
    cfg: dict[str, Any], source_run: Path, source_interpolation: np.ndarray
) -> list[dict[str, Any]]:
    """Select a deliberately heterogeneous set of Stage2.2 source trajectories.

    Category quotas are enforced *before* the final fill.  Earlier prototypes
    concatenated all candidate lists and then deduplicated them, which allowed
    the first (corner) list to occupy every slot.  That silently defeated the
    multi-nominal design.  This implementation searches each category deeply,
    applies one global vector-distance filter, and records any quota shortfall
    explicitly in the fallback category name.
    """
    nominal_cfg = cfg["nominals"]
    minimum_distance = float(nominal_cfg.get("minimum_vector_distance", 0.01))
    all_rows = list(read_json(source_run / "stage2_2_analysis/all_generation_results.json"))
    corner = list(read_json(source_run / "stage2_2_analysis/corner_hall_of_fame.json"))
    speed = list(read_json(source_run / "stage2_2_analysis/speed_safe_hall_of_fame.json"))
    gate = list(read_json(source_run / "stage2_2_analysis/gate_hall_of_fame.json"))
    position = sorted(
        [row for row in all_rows if _as_bool(row.get("success"), False)],
        key=lambda row: (
            _finite(row.get("stage2_2_final3_box_max_error_m"), 1e9),
            _finite(row.get("late_velocity_rms_m_per_s"), 1e9),
        ),
    )

    selected: list[dict[str, Any]] = []
    selected_digests: set[str] = set()

    def try_add(raw: dict[str, Any], category: str) -> bool:
        try:
            vector = _source_vector(raw.get("parameter_vector"))
        except Exception:
            return False
        digest = hashlib.sha256(np.round(vector, 10).tobytes()).hexdigest()
        if digest in selected_digests:
            return False
        if selected:
            distance = min(
                float(np.linalg.norm(vector - _source_vector(other["parameter_vector"])))
                for other in selected
            )
            if distance < minimum_distance:
                return False
        candidate = copy.deepcopy(raw)
        candidate["parameter_vector"] = vector.tolist()
        candidate["stage3_nominal_category"] = category
        selected.append(candidate)
        selected_digests.add(digest)
        return True

    category_specs = (
        ("corner", corner, int(nominal_cfg["corner_candidates"])),
        ("speed_safe", speed, int(nominal_cfg["speed_safe_candidates"])),
        ("gate", gate, int(nominal_cfg["gate_candidates"])),
        ("position_front", position, int(nominal_cfg["position_front_candidates"])),
    )
    shortfalls: dict[str, int] = {}
    for category, rows, requested_count in category_specs:
        added = 0
        for row in rows:
            if try_add(row, category):
                added += 1
                if added >= requested_count:
                    break
        if added < requested_count:
            shortfalls[category] = requested_count - added

    target_count = int(nominal_cfg["count"])
    if len(selected) < target_count:
        fill = sorted(
            [row for row in all_rows if _as_bool(row.get("success"), False)],
            key=lambda row: (
                _finite(row.get("stage2_2_max_violation"), 1e9),
                _finite(row.get("selection_score"), 1e18),
            ),
        )
        missing_label = "+".join(sorted(shortfalls)) if shortfalls else "diversity"
        for row in fill:
            if try_add(row, f"fallback_{missing_label}") and len(selected) >= target_count:
                break
    if len(selected) < target_count:
        raise RuntimeError(f"Only {len(selected)} sufficiently distinct Stage2.2 nominals were found")

    catalog: list[dict[str, Any]] = []
    for index, row in enumerate(selected[:target_count]):
        vector = _source_vector(row["parameter_vector"])
        nodes = vector.reshape(5, 3)
        mode_coefficients = source_interpolation @ nodes
        nominal_id = f"nominal_{index:02d}_{row.get('candidate_id', 'unknown')}"
        catalog.append(
            {
                "nominal_id": nominal_id,
                "source_candidate_id": str(row.get("candidate_id", "")),
                "category": str(row.get("stage3_nominal_category", "unknown")),
                "source_generation": _as_int(row.get("generation"), -1),
                "source_type": str(row.get("source_type", "")),
                "parameter_vector_100ms": vector.tolist(),
                "mode_nodes_100ms": nodes.tolist(),
                "mode_coefficients_100ms": mode_coefficients.tolist(),
                "source_metrics": {
                    key: row.get(key)
                    for key in (
                        "stage2_2_max_violation",
                        "stage2_2_final3_box_max_error_m",
                        "terminal_R_error_m",
                        "terminal_Z_error_m",
                        "terminal_velocity_m_per_s",
                        "late_velocity_rms_m_per_s",
                        "gate_label",
                    )
                },
            }
        )
    return catalog


def load_stage30_config(
    config_path: str | Path,
    *,
    source_stage2_2_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage30Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    tsc_all_root = Path(os.environ.get("TSC_ALL_ROOT", project_dir.parent)).expanduser().resolve()
    cfg = jsonio.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(tsc_all_root)},
    )
    validate_stage30_config(cfg)
    source_run = resolve_source_stage22_run(source_stage2_2_run)
    source_cfg = read_json(source_run / "stage2_2_config.resolved.json")
    source_manifest = read_json(source_run / "stage2_2_manifest.json")
    for key in ("R", "Z", "Ip"):
        if not math.isclose(
            float(cfg["target"][key]),
            float(source_cfg["target"][key]),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(f"Stage3.0 target {key} differs from Stage2.2 source")
    source_trajectory = source_cfg.get("trajectory", {})
    if int(source_trajectory.get("horizon_steps", -1)) != 10:
        raise ValueError("Stage3.0 source must be the completed 10-step / 100 ms Stage2.2 run")
    if int(source_trajectory.get("horizon_ms", -1)) != 100:
        raise ValueError("Stage3.0 source Stage2.2 horizon_ms must be 100")
    if int(source_trajectory.get("n_modes", -1)) != 3:
        raise ValueError("Stage3.0 source Stage2.2 must use the first three validated SVD modes")
    if list(source_trajectory.get("node_steps", [])) != [0, 2, 4, 6, 9]:
        raise ValueError("Stage3.0 source Stage2.2 must use node_steps [0,2,4,6,9]")
    source_gate = source_cfg.get("gate", {})
    gate_pairs = (
        ("precise_tolerance_m", "precise_tolerance_m"),
        ("relaxed_tolerance_m", "relaxed_tolerance_m"),
        ("terminal_velocity_max_m_per_s", "terminal_velocity_max_m_per_s"),
        ("late_velocity_rms_max_m_per_s", "late_velocity_rms_max_m_per_s"),
        ("ip_tolerance_a", "ip_tolerance_a"),
    )
    for stage3_key, source_key in gate_pairs:
        if not math.isclose(
            float(cfg["gate"][stage3_key]),
            float(source_gate.get(source_key, math.nan)),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                f"Stage3.0 hard gate {stage3_key} must equal the Stage2.2 source gate"
            )
    if int(cfg["gate"]["required_arrival_streak_steps"]) != int(
        source_gate.get("required_terminal_streak_steps", -1)
    ):
        raise ValueError("Stage3.0 must preserve the Stage2.2 three-sample position streak")
    manifest_horizon = source_manifest.get("trajectory", {}).get("horizon_steps")
    if manifest_horizon is not None and int(manifest_horizon) != 10:
        raise ValueError("Stage3.0 source manifest disagrees with the 10-step Stage2.2 horizon")

    if run_dir_override is None:
        output_root = resolve_path(cfg.get("output_root", "stage3_0_runs"), root=project_dir)
        run_dir = output_root / f"{cfg.get('run_name', 'stage3_0_svd3_tail_sqp_150ms')}_{utc_timestamp()}"
    else:
        run_dir = resolve_path(run_dir_override, root=project_dir)
    paths = Stage30Paths.from_run_dir(run_dir)

    env_cfg = copy.deepcopy(read_json(source_run / "env_config.resolved.json"))
    train_cfg = copy.deepcopy(read_json(source_run / "train_config.resolved.json"))
    if int(env_cfg.get("dt_ms", -1)) != 10:
        raise ValueError("Stage3.0 requires the validated 10 ms Stage2.2 control interval")
    env_cfg["tsc_timeout_s"] = float(cfg.get("runtime", {}).get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    storage = cfg.get("storage", {})
    workspace = _resolve_storage_override(
        os.environ.get("STAGE3_TSC_WORKSPACE_ROOT") or storage.get("tsc_workspace_root"),
        project_dir=project_dir,
    )
    run_root = _resolve_storage_override(
        os.environ.get("STAGE3_TSC_RUN_ROOT") or storage.get("tsc_run_root"),
        project_dir=project_dir,
    )
    if workspace is not None:
        env_cfg["tsc_workspace_root"] = workspace
    if run_root is not None:
        env_cfg["run_root"] = run_root
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    train_cfg.setdefault("episode", {})["max_episode_steps"] = int(cfg["trajectory"]["horizon_steps"])
    train_cfg.setdefault("target", {}).update(copy.deepcopy(cfg["target"]))
    reward = train_cfg.setdefault("reward", {})
    reward["hold_start_step"] = int(cfg["trajectory"]["horizon_steps"])
    reward["hold_ramp_end_step"] = int(cfg["trajectory"]["horizon_steps"])

    modes_tsc = np.asarray(np.load(source_run / "source_reference/analysis/coil_modes_tsc.npy")[:, :3], dtype=float)
    if modes_tsc.shape != (14, 3) or not np.allclose(modes_tsc.T @ modes_tsc, np.eye(3), atol=1e-6):
        raise ValueError("Invalid first-three-mode matrix in Stage2.2 source")
    initial_currents = _find_initial_currents(source_run)
    max_delta_a = float(env_cfg["current_slew_a_per_ms"]) * float(env_cfg["dt_ms"])
    min_current_tsc = display_to_tsc(np.asarray(env_cfg["min_current_a_display_order"], dtype=float))
    max_current_tsc = display_to_tsc(np.asarray(env_cfg["max_current_a_display_order"], dtype=float))
    source_interpolation = s2.build_interpolation_matrix(10, np.asarray([0, 2, 4, 6, 9], dtype=float))
    nominals = build_nominal_catalog(cfg, source_run, source_interpolation)
    lower_mode = np.asarray(cfg["trajectory"]["coefficient_lower"], dtype=float)
    upper_mode = np.asarray(cfg["trajectory"]["coefficient_upper"], dtype=float)
    if lower_mode.shape != (3,) or upper_mode.shape != (3,) or np.any(lower_mode >= upper_mode):
        raise ValueError("Invalid Stage3.0 mode coefficient bounds")
    return Stage30Context(
        cfg=cfg,
        train_cfg=train_cfg,
        env_cfg=env_cfg,
        paths=paths,
        source_run=source_run,
        modes_tsc=modes_tsc,
        initial_currents_tsc=initial_currents,
        max_delta_a=max_delta_a,
        min_current_tsc=min_current_tsc,
        max_current_tsc=max_current_tsc,
        tail_steps=tuple(int(value) for value in cfg["trajectory"]["tail_variable_steps"]),
        coefficient_lower=np.tile(lower_mode, 6),
        coefficient_upper=np.tile(upper_mode, 6),
        source_interpolation=source_interpolation,
        nominals=nominals,
    )


def initialize_stage30_run(ctx: Stage30Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.phases,
        ctx.paths.evaluations,
        ctx.paths.confirmations,
        ctx.paths.analysis,
        ctx.paths.best,
        ctx.paths.controller,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.run_dir / "stage3_0_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.env_cfg)
    atomic_write_json(ctx.paths.nominal_catalog, ctx.nominals)

    source_files = [
        "stage2_2_config.resolved.json",
        "stage2_2_manifest.json",
        "stage2_2_analysis/stage2_2_analysis_summary.json",
        "stage2_2_analysis/corner_hall_of_fame.json",
        "stage2_2_analysis/speed_safe_hall_of_fame.json",
        "stage2_2_analysis/gate_hall_of_fame.json",
        "stage2_2_best/best_corner_candidate.json",
        "STAGE2_2_REPORT.md",
    ]
    fingerprints: dict[str, str] = {}
    for relative in source_files:
        src = ctx.source_run / relative
        if not src.exists():
            continue
        dst = ctx.paths.source_reference / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
        fingerprints[relative] = sha256_file(src)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "created_utc": utc_timestamp(),
        "source_stage2_2_run": str(ctx.source_run),
        "source_file_sha256": fingerprints,
        "target": copy.deepcopy(ctx.cfg["target"]),
        "horizon_steps": int(ctx.cfg["trajectory"]["horizon_steps"]),
        "horizon_ms": int(ctx.cfg["trajectory"]["horizon_ms"]),
        "dt_ms": int(ctx.env_cfg["dt_ms"]),
        "n_modes": 3,
        "tail_variable_steps": list(ctx.tail_steps),
        "parameter_dimension": 18,
        "arrival_window_steps": list(ctx.cfg["gate"]["allowed_arrival_steps"]),
        "hard_100ms_deadline": False,
        "final_task": (
            "A feedback controller that reaches, brakes, and robustly holds R/Z/Ip across initial-state "
            "and target variations. Stage3.0 is only the fixed-scenario nominal and local-sensitivity gate."
        ),
        "temporary_workspace": {
            "tsc_workspace_root": ctx.env_cfg.get("tsc_workspace_root"),
            "tsc_run_root": ctx.env_cfg.get("run_root"),
            "ray_tmpdir": os.environ.get("RAY_TMPDIR", ""),
        },
    }
    if ctx.paths.manifest.exists():
        previous = read_json(ctx.paths.manifest)
        if Path(previous["source_stage2_2_run"]).resolve() != ctx.source_run:
            raise ValueError("Existing Stage3.0 run points to a different Stage2.2 source")
    else:
        atomic_write_json(ctx.paths.manifest, manifest)


# ---------------------------------------------------------------------------
# Sequence decoding and screen templates
# ---------------------------------------------------------------------------


def nominal_by_id(ctx: Stage30Context, nominal_id: str) -> dict[str, Any]:
    for nominal in ctx.nominals:
        if nominal["nominal_id"] == nominal_id:
            return nominal
    raise KeyError(f"Unknown Stage3.0 nominal_id={nominal_id!r}")


def clip_tail(ctx: Stage30Context, tail: np.ndarray) -> np.ndarray:
    clipped = np.clip(_tail_vector(tail), ctx.coefficient_lower, ctx.coefficient_upper)
    if clipped.shape != (18,) or not np.all(np.isfinite(clipped)):
        raise ValueError("Invalid clipped Stage3.0 tail vector")
    return clipped


def decode_tail_sequence(
    ctx: Stage30Context, nominal: dict[str, Any], tail_vector: np.ndarray
) -> dict[str, Any]:
    tail = clip_tail(ctx, tail_vector).reshape(6, 3)
    source_modes = np.asarray(nominal["mode_coefficients_100ms"], dtype=float)
    if source_modes.shape != (10, 3):
        raise ValueError(f"Nominal {nominal['nominal_id']} has invalid 100 ms mode coefficients")
    modes = np.zeros((15, 3), dtype=float)
    modes[:10] = source_modes
    modes[np.asarray(ctx.tail_steps, dtype=int)] = tail
    action_raw = modes @ ctx.modes_tsc.T
    action = np.zeros_like(action_raw)
    currents = np.zeros((16, 14), dtype=float)
    currents[0] = ctx.initial_currents_tsc
    repair_scale: list[float] = []
    saturation_excess: list[float] = []
    for step in range(15):
        desired = np.asarray(action_raw[step], dtype=float)
        max_abs = float(np.max(np.abs(desired)))
        mode_scale = 1.0 if max_abs <= 1.0 else 1.0 / max_abs
        desired = desired * mode_scale
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
        repair_scale.append(mode_scale * current_scale)
        saturation_excess.append(max(0.0, max_abs - 1.0))
    return {
        "tail_vector": tail.reshape(-1),
        "mode_coefficients": modes,
        "action_raw_tsc": action_raw,
        "action_norm_tsc": action,
        "action_norm_display": tsc_matrix_to_display(action),
        "currents_a_tsc": currents,
        "currents_a_display": tsc_matrix_to_display(currents),
        "per_step_repair_scale": np.asarray(repair_scale, dtype=float),
        "saturation_excess": np.asarray(saturation_excess, dtype=float),
    }


def screen_tail_templates(ctx: Stage30Context, nominal: dict[str, Any]) -> list[tuple[str, np.ndarray]]:
    source = np.asarray(nominal["mode_coefficients_100ms"], dtype=float)
    m8 = source[8]
    m9 = source[9]
    residual = np.asarray(ctx.cfg["screen"]["mode_residual_amplitude"], dtype=float)
    if residual.shape != (3,):
        raise ValueError("screen.mode_residual_amplitude must have three values")

    def ramp(factors: Sequence[float]) -> np.ndarray:
        return np.asarray(factors, dtype=float)[:, None] * m9[None, :]

    templates: list[tuple[str, np.ndarray]] = []
    templates.append(("hold_last", np.tile(m9, (6, 1))))
    zero_after = np.zeros((6, 3), dtype=float)
    zero_after[0] = m9
    templates.append(("zero_after_100", zero_after))
    templates.append(("linear_ramp_zero", ramp([1.0, 0.8, 0.6, 0.4, 0.2, 0.0])))
    templates.append(("fast_ramp_zero", ramp([1.0, 0.5, 0.0, 0.0, 0.0, 0.0])))
    templates.append(("slow_ramp_zero", ramp([1.0, 0.9, 0.75, 0.55, 0.35, 0.15])))
    slope = m9 - m8
    slope_decay = np.zeros((6, 3), dtype=float)
    slope_decay[0] = m9
    for index in range(1, 6):
        slope_decay[index] = slope_decay[index - 1] + slope * (0.5**index)
    templates.append(("continue_slope_decay", slope_decay))

    base = ramp([1.0, 0.8, 0.6, 0.4, 0.2, 0.0])
    pulse = np.asarray([0.0, 1.0, 1.0, 0.7, 0.3, 0.0], dtype=float)[:, None]
    for mode, sign, name in (
        (0, +1.0, "mode1_plus_pulse"),
        (0, -1.0, "mode1_minus_pulse"),
        (1, +1.0, "mode2_plus_pulse"),
        (1, -1.0, "mode2_minus_pulse"),
    ):
        value = base.copy()
        value[:, mode] += sign * pulse[:, 0] * residual[mode]
        templates.append((name, value))
    coupled = base.copy()
    coupled[:, 0] += pulse[:, 0] * residual[0]
    coupled[:, 1] -= pulse[:, 0] * residual[1]
    coupled[:, 2] += pulse[:, 0] * residual[2] * 0.5
    templates.append(("coupled_cross_pulse", coupled))
    opposite = base.copy()
    opposite[:, 0] -= pulse[:, 0] * residual[0]
    opposite[:, 1] += pulse[:, 0] * residual[1]
    opposite[:, 2] -= pulse[:, 0] * residual[2] * 0.5
    templates.append(("opposite_cross_pulse", opposite))
    if len(templates) != 12:
        raise RuntimeError(f"Expected 12 screen templates, constructed {len(templates)}")
    return [(name, clip_tail(ctx, value.reshape(-1))) for name, value in templates]


# ---------------------------------------------------------------------------
# Extended-horizon metrics and objective
# ---------------------------------------------------------------------------


def _trailing_streak(mask: np.ndarray) -> int:
    count = 0
    for value in np.asarray(mask, dtype=bool)[::-1]:
        if not bool(value):
            break
        count += 1
    return int(count)


def _velocity_components(y: np.ndarray, dt_s: float) -> np.ndarray:
    velocity = np.zeros((len(y), 2), dtype=float)
    if len(y) > 1:
        velocity[1:] = np.diff(y[:, :2], axis=0) / dt_s
    return velocity


def trajectory_feature_vector(ctx: Stage30Context, result: dict[str, Any]) -> np.ndarray:
    trajectory = result.get("trajectory", [])
    if len(trajectory) != 16:
        raise ValueError(f"Stage3.0 feature extraction requires 16 states, got {len(trajectory)}")
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("Stage3.0 trajectory contains non-finite R/Z/Ip")
    target = np.asarray([ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]], dtype=float)
    error = y - target[None, :]
    velocity = _velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    # Six states covering relative times 100 through 150 ms, trajectory indices 10-15.
    tail = slice(10, 16)
    return np.concatenate(
        [
            error[tail, 0],
            error[tail, 1],
            velocity[tail, 0],
            velocity[tail, 1],
            error[tail, 2],
        ]
    )


def unpack_feature_vector(vector: np.ndarray) -> dict[str, np.ndarray]:
    value = np.asarray(vector, dtype=float).reshape(-1)
    if value.shape != (30,):
        raise ValueError(f"Stage3.0 feature vector must have 30 elements, got {value.shape}")
    return {
        "R": value[0:6],
        "Z": value[6:12],
        "vR": value[12:18],
        "vZ": value[18:24],
        "Ip": value[24:30],
    }


def _endpoint_constraints(
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
    if window_start < 0:
        raise ValueError("invalid arrival endpoint/streak combination")
    sustained_box = float(np.max(np.abs(error[window_start : horizon + 1, :2])))
    endpoint_speed = float(speed[endpoint])
    late_start = max(1, endpoint - late_window_steps + 1)
    endpoint_late_rms = float(np.sqrt(np.mean(speed[late_start : endpoint + 1] ** 2)))
    post_speed_rms = float(np.sqrt(np.mean(speed[endpoint : horizon + 1] ** 2)))
    final_speed = float(speed[horizon])
    sustained_ip = float(np.max(np.abs(error[window_start : horizon + 1, 2])))
    violations = {
        "position": max(sustained_box / tolerance - 1.0, 0.0),
        "endpoint_speed": max(endpoint_speed / endpoint_speed_limit - 1.0, 0.0),
        "endpoint_late_speed": max(endpoint_late_rms / rms_speed_limit - 1.0, 0.0),
        "post_speed": max(post_speed_rms / rms_speed_limit - 1.0, 0.0),
        "final_speed": max(final_speed / endpoint_speed_limit - 1.0, 0.0),
        "ip": max(sustained_ip / ip_tolerance - 1.0, 0.0),
    }
    values = np.asarray(list(violations.values()), dtype=float)
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
        "position_violation": float(violations["position"]),
        "endpoint_speed_violation": float(violations["endpoint_speed"]),
        "endpoint_late_speed_violation": float(violations["endpoint_late_speed"]),
        "post_speed_violation": float(violations["post_speed"]),
        "final_speed_violation": float(violations["final_speed"]),
        "ip_violation": float(violations["ip"]),
        "max_violation": float(np.max(values)),
        "sum_violation": float(np.sum(values)),
        "l2_violation": float(np.sqrt(np.sum(values**2))),
        "pass": bool(np.max(values) <= 1e-12),
    }


def stage30_metrics(
    ctx: Stage30Context, result: dict[str, Any], decoded: dict[str, Any] | None
) -> dict[str, Any]:
    if not result.get("success"):
        return {
            "success": False,
            "failure_reason": str(result.get("failure_reason", "TSC failure")),
            "strict_gate_pass": False,
            "relaxed_gate_pass": False,
            "gate_label": "TSC_FAILURE",
            "stage3_0_max_violation": 1e12,
            "stage3_0_sum_violation": 1e12,
            "stage3_0_l2_violation": 1e12,
            "continuous_objective": 1e12,
            "selection_score": 99e6 + 1e12,
        }
    trajectory = result.get("trajectory", [])
    if len(trajectory) != 16:
        return {
            "success": False,
            "failure_reason": f"expected 16 trajectory states, got {len(trajectory)}",
            "strict_gate_pass": False,
            "relaxed_gate_pass": False,
            "gate_label": "INCOMPLETE_150MS_TRAJECTORY",
            "stage3_0_max_violation": 1e12,
            "stage3_0_sum_violation": 1e12,
            "stage3_0_l2_violation": 1e12,
            "continuous_objective": 1e12,
            "selection_score": 99e6 + 1e12,
        }
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("Successful Stage3.0 trajectory has non-finite R/Z/Ip")
    target = np.asarray([ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]], dtype=float)
    error = y - target[None, :]
    velocity_xy = _velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0)
    speed = np.linalg.norm(velocity_xy, axis=1)
    gate = ctx.cfg["gate"]
    endpoints = [int(value) for value in gate["allowed_arrival_steps"]]
    precise_evaluations = [
        _endpoint_constraints(
            error=error,
            speed=speed,
            endpoint=endpoint,
            horizon=15,
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
        _endpoint_constraints(
            error=error,
            speed=speed,
            endpoint=endpoint,
            horizon=15,
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
    precise_passes = [row for row in precise_evaluations if row["pass"]]
    relaxed_passes = [row for row in relaxed_evaluations if row["pass"]]
    # ``chosen`` is always the precise-gate endpoint used by the minimax
    # objective.  ``gate_endpoint`` separately records the endpoint that
    # actually passed a hard gate.  Keeping these concepts distinct avoids a
    # subtle reporting bug where a relaxed pass could be labelled correctly
    # while its displayed endpoint metrics came from a different, non-passing
    # precise endpoint.
    if precise_passes:
        chosen = min(precise_passes, key=lambda row: row["endpoint_step"])
    else:
        chosen = min(
            precise_evaluations,
            key=lambda row: (row["max_violation"], row["sum_violation"], row["endpoint_step"]),
        )
    strict_pass = bool(precise_passes)
    relaxed_pass = bool(relaxed_passes)
    gate_endpoint = (
        min(precise_passes, key=lambda row: row["endpoint_step"])
        if strict_pass
        else (min(relaxed_passes, key=lambda row: row["endpoint_step"]) if relaxed_pass else None)
    )
    if strict_pass:
        label = "PASS_PRECISE_HOLD_30MM_120_150MS"
    elif relaxed_pass:
        label = "PASS_DAMPED_HOLD_40MM_120_150MS"
    else:
        label = "NEAR_FEASIBLE_120_150MS"

    currents = np.asarray([row["currents_a_display"] for row in trajectory], dtype=float)
    min_i = np.asarray(ctx.env_cfg["min_current_a_display_order"], dtype=float)
    max_i = np.asarray(ctx.env_cfg["max_current_a_display_order"], dtype=float)
    center_i = 0.5 * (min_i + max_i)
    half_i = np.maximum(0.5 * (max_i - min_i), 1e-9)
    current_util = float(np.max(np.abs((currents - center_i[None, :]) / half_i[None, :])))
    action_rms = 0.0
    delta_action_rms = 0.0
    repair_rms = 0.0
    if decoded is not None:
        action = np.asarray(decoded["action_norm_tsc"], dtype=float)
        action_rms = float(np.sqrt(np.mean(action**2)))
        delta_action_rms = float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2)))
        repair_rms = float(np.sqrt(np.mean(np.asarray(decoded["saturation_excess"], dtype=float) ** 2)))

    window_start = int(chosen["window_start_step"])
    position_core = float(
        np.mean(np.sum((error[window_start:, :2] / float(gate["precise_tolerance_m"])) ** 2, axis=1))
    )
    velocity_core = float(
        np.mean((speed[max(1, window_start) :] / float(gate["terminal_velocity_max_m_per_s"])) ** 2)
    )
    ip_core = float((error[-1, 2] / float(gate["ip_tolerance_a"])) ** 2)
    arrival_core = float((int(chosen["endpoint_step"]) - min(endpoints)) / max(max(endpoints) - min(endpoints), 1))
    quality_weights = ctx.cfg["objective"]["quality_weights"]
    quality = (
        float(quality_weights.get("position_core", 2.0)) * position_core
        + float(quality_weights.get("velocity_core", 1.5)) * velocity_core
        + float(quality_weights.get("terminal_ip_core", 0.05)) * ip_core
        + float(quality_weights.get("arrival_time_core", 0.15)) * arrival_core
        + float(quality_weights.get("action_rms", 0.02)) * action_rms**2
        + float(quality_weights.get("delta_action_rms", 0.04)) * delta_action_rms**2
        + float(quality_weights.get("repair", 2.0)) * repair_rms**2
    )
    objective = ctx.cfg["objective"]
    if strict_pass:
        selection = float(quality)
    else:
        selection = float(
            float(objective["non_strict_offset"])
            + float(objective["max_violation_weight"]) * float(chosen["max_violation"])
            + float(objective["sum_violation_weight"]) * float(chosen["sum_violation"])
            + float(objective["l2_violation_weight"]) * float(chosen["l2_violation"])
            + quality
        )

    precise_box_mask = np.max(np.abs(error[:, :2]), axis=1) <= float(gate["precise_tolerance_m"])
    relaxed_box_mask = np.max(np.abs(error[:, :2]), axis=1) <= float(gate["relaxed_tolerance_m"])
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
        "late_velocity_rms_m_per_s": float(np.sqrt(np.mean(speed[-int(gate["late_window_steps"]) :] ** 2))),
        "max_velocity_m_per_s": float(np.max(speed)),
        "max_current_utilization": current_util,
        "trailing_streak_within_30mm_steps": _trailing_streak(precise_box_mask),
        "trailing_streak_within_40mm_steps": _trailing_streak(relaxed_box_mask),
        "strict_gate_pass": strict_pass,
        "relaxed_gate_pass": relaxed_pass,
        "gate_label": label,
        "stage3_0_earliest_strict_arrival_step": min((row["endpoint_step"] for row in precise_passes), default=None),
        "stage3_0_earliest_strict_arrival_ms": min((row["arrival_time_ms"] for row in precise_passes), default=None),
        "stage3_0_earliest_relaxed_arrival_step": min((row["endpoint_step"] for row in relaxed_passes), default=None),
        "stage3_0_earliest_relaxed_arrival_ms": min((row["arrival_time_ms"] for row in relaxed_passes), default=None),
        "stage3_0_gate_endpoint_step": None if gate_endpoint is None else int(gate_endpoint["endpoint_step"]),
        "stage3_0_gate_endpoint_ms": None if gate_endpoint is None else int(gate_endpoint["arrival_time_ms"]),
        "stage3_0_gate_sustained_box_max_error_m": None
        if gate_endpoint is None
        else float(gate_endpoint["sustained_box_max_error_m"]),
        "stage3_0_gate_post_arrival_velocity_rms_m_per_s": None
        if gate_endpoint is None
        else float(gate_endpoint["post_arrival_velocity_rms_m_per_s"]),
        "stage3_0_best_endpoint_step": int(chosen["endpoint_step"]),
        "stage3_0_best_endpoint_ms": int(chosen["arrival_time_ms"]),
        "stage3_0_window_start_step": int(chosen["window_start_step"]),
        "stage3_0_sustained_box_max_error_m": float(chosen["sustained_box_max_error_m"]),
        "stage3_0_endpoint_velocity_m_per_s": float(chosen["endpoint_velocity_m_per_s"]),
        "stage3_0_endpoint_late_velocity_rms_m_per_s": float(chosen["endpoint_late_velocity_rms_m_per_s"]),
        "stage3_0_post_arrival_velocity_rms_m_per_s": float(chosen["post_arrival_velocity_rms_m_per_s"]),
        "stage3_0_final_velocity_m_per_s": float(chosen["final_velocity_m_per_s"]),
        "stage3_0_sustained_Ip_max_error_A": float(chosen["sustained_Ip_max_error_A"]),
        "stage3_0_position_violation": float(chosen["position_violation"]),
        "stage3_0_endpoint_speed_violation": float(chosen["endpoint_speed_violation"]),
        "stage3_0_endpoint_late_speed_violation": float(chosen["endpoint_late_speed_violation"]),
        "stage3_0_post_speed_violation": float(chosen["post_speed_violation"]),
        "stage3_0_final_speed_violation": float(chosen["final_speed_violation"]),
        "stage3_0_ip_violation": float(chosen["ip_violation"]),
        "stage3_0_max_violation": float(chosen["max_violation"]),
        "stage3_0_sum_violation": float(chosen["sum_violation"]),
        "stage3_0_l2_violation": float(chosen["l2_violation"]),
        "stage3_0_endpoint_evaluations": precise_evaluations,
        "stage3_0_speed_safe_at_best_endpoint": bool(
            chosen["endpoint_speed_violation"] <= 0.0
            and chosen["endpoint_late_speed_violation"] <= 0.0
            and chosen["post_speed_violation"] <= 0.0
            and chosen["final_speed_violation"] <= 0.0
            and chosen["ip_violation"] <= 0.0
        ),
        "stage3_0_position_safe_at_best_endpoint": bool(chosen["position_violation"] <= 0.0),
        "stage3_0_quality": float(quality),
        "continuous_objective": float(quality),
        "selection_score": selection,
        "action_rms": action_rms,
        "delta_action_rms": delta_action_rms,
        "repair_excess_rms": repair_rms,
        "wall_time_s": float(result.get("wall_time_s", 0.0)),
    }

# ---------------------------------------------------------------------------
# Candidate manifests, evaluation and result aggregation
# ---------------------------------------------------------------------------


def candidate_row(
    ctx: Stage30Context,
    *,
    nominal: dict[str, Any],
    tail_vector: np.ndarray,
    source_name: str,
    source_type: str,
    phase_name: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tail = clip_tail(ctx, tail_vector)
    decoded = decode_tail_sequence(ctx, nominal, tail)
    row: dict[str, Any] = {
        "candidate_id": vector_digest(nominal["nominal_id"], tail, prefix=f"s30{phase_name[:4]}"),
        "phase": phase_name,
        "nominal_id": nominal["nominal_id"],
        "source_candidate_id": nominal["source_candidate_id"],
        "nominal_category": nominal["category"],
        "source_name": source_name,
        "source_type": source_type,
        "tail_vector": tail.tolist(),
        "action_rms_pred": float(np.sqrt(np.mean(np.asarray(decoded["action_norm_tsc"]) ** 2))),
        "delta_action_rms_pred": float(
            np.sqrt(np.mean(np.diff(np.asarray(decoded["action_norm_tsc"]), axis=0) ** 2))
        ),
        "repair_excess_rms_pred": float(
            np.sqrt(np.mean(np.asarray(decoded["saturation_excess"]) ** 2))
        ),
    }
    if extra:
        row.update(copy.deepcopy(extra))
    return row


def _dedupe_candidates(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = _vector_key(str(row["nominal_id"]), row["tail_vector"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def build_screen_manifest(ctx: Stage30Context) -> dict[str, Any]:
    phase_dir = ctx.paths.phases / "screen"
    phase_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = phase_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)
    rows: list[dict[str, Any]] = []
    for nominal in ctx.nominals:
        for template_name, tail in screen_tail_templates(ctx, nominal):
            rows.append(
                candidate_row(
                    ctx,
                    nominal=nominal,
                    tail_vector=tail,
                    source_name=template_name,
                    source_type="screen_template",
                    phase_name="screen",
                )
            )
    rows = _dedupe_candidates(rows)
    expected = int(ctx.cfg["nominals"]["count"]) * int(ctx.cfg["screen"]["templates_per_nominal"])
    if len(rows) != expected:
        raise RuntimeError(f"Stage3.0 screen constructed {len(rows)} unique candidates, expected {expected}")
    for index, row in enumerate(rows):
        row["population_index"] = index
        row["candidate_id"] = vector_digest(row["nominal_id"], _tail_vector(row["tail_vector"]), "s30screen")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "phase": "screen",
        "population_size": len(rows),
        "candidates": rows,
    }
    atomic_write_json(manifest_path, manifest)
    write_csv(phase_dir / "candidate_manifest.csv", rows)
    return manifest


def specs_from_manifest(ctx: Stage30Context, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for row in manifest["candidates"]:
        nominal = nominal_by_id(ctx, str(row["nominal_id"]))
        tail = _tail_vector(row["tail_vector"])
        decoded = decode_tail_sequence(ctx, nominal, tail)
        spec = {
            "kind": "stage3_0_candidate",
            "experiment_id": str(row["candidate_id"]),
            "candidate_id": str(row["candidate_id"]),
            "phase": str(manifest["phase"]),
            "population_index": int(row.get("population_index", 0)),
            "nominal_id": str(row["nominal_id"]),
            "source_candidate_id": str(row["source_candidate_id"]),
            "nominal_category": str(row["nominal_category"]),
            "source_name": str(row["source_name"]),
            "source_type": str(row["source_type"]),
            "horizon_steps": 15,
            "tail_variable_steps": list(ctx.tail_steps),
            "tail_vector": tail.tolist(),
            "mode_coefficients": np.asarray(decoded["mode_coefficients"], dtype=float).tolist(),
            "action_sequence_norm_tsc": np.asarray(decoded["action_norm_tsc"], dtype=float).tolist(),
            "action_sequence_norm_display": np.asarray(decoded["action_norm_display"], dtype=float).tolist(),
        }
        for key in (
            "probe_center_candidate_id",
            "probe_variable_index",
            "probe_sign",
            "probe_requested_delta",
            "probe_actual_delta",
            "probe_scheme",
            "sqp_profile",
            "sqp_endpoint_step",
            "sqp_step_scale",
            "predicted_linear_objective",
            "predicted_max_violation",
        ):
            if key in row:
                spec[key] = row[key]
        specs.append(spec)
    jsonio.assert_json_finite(specs, context="Stage3.0 evaluation specs")
    return specs


def summarize_phase(
    ctx: Stage30Context,
    *,
    manifest: dict[str, Any],
    results: Sequence[dict[str, Any]],
    evaluation_dir: Path,
) -> list[dict[str, Any]]:
    phase_name = str(manifest["phase"])
    phase_dir = ctx.paths.phases / phase_name
    by_id = {str(result.get("experiment_id")): result for result in results}
    rows: list[dict[str, Any]] = []
    for candidate in manifest["candidates"]:
        candidate_id = str(candidate["candidate_id"])
        nominal = nominal_by_id(ctx, str(candidate["nominal_id"]))
        tail = _tail_vector(candidate["tail_vector"])
        decoded = decode_tail_sequence(ctx, nominal, tail)
        result = by_id.get(candidate_id)
        metrics = (
            stage30_metrics(ctx, result, decoded)
            if result is not None
            else {
                "success": False,
                "failure_reason": "missing result",
                "strict_gate_pass": False,
                "relaxed_gate_pass": False,
                "gate_label": "MISSING_RESULT",
                "stage3_0_max_violation": 1e12,
                "stage3_0_sum_violation": 1e12,
                "stage3_0_l2_violation": 1e12,
                "continuous_objective": 1e12,
                "selection_score": 99e6 + 1e12,
            }
        )
        row = {
            "stage": "Stage3.0",
            "phase": phase_name,
            "candidate_id": candidate_id,
            "population_index": int(candidate.get("population_index", 0)),
            "nominal_id": candidate["nominal_id"],
            "source_candidate_id": candidate["source_candidate_id"],
            "nominal_category": candidate["nominal_category"],
            "source_name": candidate["source_name"],
            "source_type": candidate["source_type"],
            "tail_vector": tail.tolist(),
            "result_relpath": str((evaluation_dir / f"{candidate_id}.json.gz").relative_to(ctx.paths.run_dir)),
            **{
                key: candidate[key]
                for key in candidate
                if key
                in {
                    "probe_center_candidate_id",
                    "probe_variable_index",
                    "probe_sign",
                    "probe_requested_delta",
                    "probe_actual_delta",
                    "probe_scheme",
                    "sqp_profile",
                    "sqp_endpoint_step",
                    "sqp_step_scale",
                    "predicted_linear_objective",
                    "predicted_max_violation",
                }
            },
            **metrics,
        }
        rows.append(row)
    rows.sort(key=lambda row: (float(row.get("selection_score", 99e18)), str(row["candidate_id"])))
    for rank, row in enumerate(rows, start=1):
        row["phase_rank"] = rank
    write_csv(phase_dir / "results.csv", rows)
    atomic_write_json(phase_dir / "results.json", rows)
    return rows


def evaluate_manifest(
    ctx: Stage30Context,
    *,
    manifest: dict[str, Any],
    backend: str,
    resume: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    phase = str(manifest["phase"])
    specs = specs_from_manifest(ctx, manifest)
    evaluation_dir = ctx.paths.evaluations / phase
    results = s2.evaluate_specs(ctx, specs, output_dir=evaluation_dir, backend=backend, resume=resume)
    rows = summarize_phase(ctx, manifest=manifest, results=results, evaluation_dir=evaluation_dir)
    return rows, list(results)


def aggregate_rows(paths: Stage30Paths) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths.phases.glob("*/results.json")):
        payload = read_json(path)
        if isinstance(payload, list):
            rows.extend(dict(row) for row in payload)
    return rows


def load_result_for_row(ctx: Stage30Context, row: dict[str, Any]) -> dict[str, Any]:
    relative = row.get("result_relpath")
    if not relative:
        raise KeyError(f"Candidate {row.get('candidate_id')} has no result_relpath")
    path = ctx.paths.run_dir / str(relative)
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json_gz(path)


# ---------------------------------------------------------------------------
# State and best-artifact management
# ---------------------------------------------------------------------------


def initial_state(ctx: Stage30Context) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "source_stage2_2_run": str(ctx.source_run),
        "screen_complete": False,
        "next_sqp_round": 0,
        "max_sqp_rounds": int(ctx.cfg["sqp"]["max_rounds"]),
        "trust_scale": float(ctx.cfg["sqp"]["initial_trust_scale"]),
        "optimization_finished": False,
        "controller_identification_complete": False,
        "confirmation_complete": False,
        "strict_gate_found": False,
        "best_candidate_id": None,
        "best_selection_score": None,
        "best_max_violation": None,
        "best_phase": None,
        "best_nominal_id": None,
        "best_tail_vector": None,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def load_or_initialize_state(ctx: Stage30Context, *, no_resume: bool) -> dict[str, Any]:
    if no_resume:
        if ctx.paths.state.exists():
            raise FileExistsError(f"--no-resume requested but state exists: {ctx.paths.state}")
        state = initial_state(ctx)
        atomic_write_json(ctx.paths.state, state)
        return state
    if ctx.paths.state.exists():
        state = read_json(ctx.paths.state)
        if Path(state["source_stage2_2_run"]).resolve() != ctx.source_run:
            raise ValueError("Stage3.0 state points to a different source Stage2.2 run")
        return state
    state = initial_state(ctx)
    atomic_write_json(ctx.paths.state, state)
    return state


def _best_sort_key(row: dict[str, Any]) -> tuple[float, float, float, str]:
    return (
        float(row.get("selection_score", 99e18)),
        float(row.get("stage3_0_max_violation", 1e12)),
        float(row.get("stage3_0_sum_violation", 1e12)),
        str(row.get("candidate_id", "")),
    )


def best_successful_row(rows: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    return min(successful, key=_best_sort_key) if successful else None


def save_best_artifacts(ctx: Stage30Context, row: dict[str, Any]) -> None:
    result = load_result_for_row(ctx, row)
    nominal = nominal_by_id(ctx, str(row["nominal_id"]))
    tail = _tail_vector(row["tail_vector"])
    decoded = decode_tail_sequence(ctx, nominal, tail)
    ctx.paths.best.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.best / "best_candidate.json", row)
    atomic_write_json_gz(ctx.paths.best / "best_tsc_result.json.gz", result)
    action_rows: list[dict[str, Any]] = []
    modes = np.asarray(decoded["mode_coefficients"], dtype=float)
    actions = np.asarray(decoded["action_norm_tsc"], dtype=float)
    display = np.asarray(decoded["action_norm_display"], dtype=float)
    for step in range(15):
        output: dict[str, Any] = {
            "step_index": step,
            "time_ms_from_start": step * int(ctx.env_cfg["dt_ms"]),
            "absolute_time_ms": start_time_ms(ctx.env_cfg) + step * int(ctx.env_cfg["dt_ms"]),
            "mode_1": float(modes[step, 0]),
            "mode_2": float(modes[step, 1]),
            "mode_3": float(modes[step, 2]),
        }
        for coil, name in enumerate(TSC_COIL_NAMES):
            output[f"action_norm_tsc_{name}"] = float(actions[step, coil])
            output[f"delta_a_tsc_{name}"] = float(actions[step, coil] * ctx.max_delta_a)
        for coil, name in enumerate(DISPLAY_COIL_NAMES):
            output[f"action_norm_display_{name}"] = float(display[step, coil])
        action_rows.append(output)
    write_csv(ctx.paths.best / "best_action_sequence.csv", action_rows)


def update_state_best(ctx: Stage30Context, state: dict[str, Any], rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    candidate = best_successful_row(rows)
    if candidate is None:
        return state
    previous = state.get("best_selection_score")
    improved = previous is None or float(candidate["selection_score"]) < float(previous) - 1e-12
    strict_found = bool(state.get("strict_gate_found", False)) or _as_bool(candidate.get("strict_gate_pass"), False)
    new_state = copy.deepcopy(state)
    new_state["strict_gate_found"] = strict_found
    if improved:
        new_state.update(
            {
                "best_candidate_id": candidate["candidate_id"],
                "best_selection_score": float(candidate["selection_score"]),
                "best_max_violation": float(candidate.get("stage3_0_max_violation", 0.0)),
                "best_phase": candidate["phase"],
                "best_nominal_id": candidate["nominal_id"],
                "best_tail_vector": _tail_vector(candidate["tail_vector"]).tolist(),
            }
        )
        save_best_artifacts(ctx, candidate)
    new_state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, new_state)
    return new_state


def run_screen(
    ctx: Stage30Context,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if state.get("screen_complete"):
        return state
    manifest = build_screen_manifest(ctx)
    rows, _ = evaluate_manifest(ctx, manifest=manifest, backend=backend, resume=resume)
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    successful_nominals = {str(row.get("nominal_id")) for row in successful}
    minimum_success = int(ctx.cfg["screen"].get("minimum_successful_candidates", 48))
    minimum_nominals = int(ctx.cfg["screen"].get("minimum_successful_nominals", 4))
    if len(successful) < minimum_success or len(successful_nominals) < minimum_nominals:
        failure_reasons: dict[str, int] = {}
        for row in rows:
            if _as_bool(row.get("success"), False):
                continue
            reason = str(row.get("failure_reason", "unknown"))
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        raise RuntimeError(
            "Stage3.0 150 ms screen did not meet the minimum runtime-validity threshold. "
            f"success={len(successful)}/{len(rows)} (required {minimum_success}), "
            f"successful_nominals={len(successful_nominals)}/8 (required {minimum_nominals}), "
            f"failures={failure_reasons}. This may indicate that the TSC restart chain cannot "
            "advance reliably beyond 1200 ms; do not fit a local controller to a tiny survivor set."
        )
    state = update_state_best(ctx, state, rows)
    state["screen_complete"] = True
    if state.get("strict_gate_found"):
        state["optimization_finished"] = True
        state["stop_reason"] = "strict_gate_found_in_screen"
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    best = best_successful_row(rows)
    print(
        json.dumps(
            {
                "stage": "Stage3.0",
                "phase": "screen",
                "successful": len(successful),
                "population": len(rows),
                "strict": sum(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
                "relaxed": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in rows),
                "best": None
                if best is None
                else {
                    key: best.get(key)
                    for key in (
                        "candidate_id",
                        "nominal_id",
                        "gate_label",
                        "stage3_0_best_endpoint_ms",
                        "stage3_0_sustained_box_max_error_m",
                        "stage3_0_post_arrival_velocity_rms_m_per_s",
                        "stage3_0_max_violation",
                    )
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )
    return state

# ---------------------------------------------------------------------------
# Real-TSC finite differences and trust-region SQP rounds
# ---------------------------------------------------------------------------


def _full_mode_vector(ctx: Stage30Context, row: dict[str, Any]) -> np.ndarray:
    nominal = nominal_by_id(ctx, str(row["nominal_id"]))
    decoded = decode_tail_sequence(ctx, nominal, _tail_vector(row["tail_vector"]))
    return np.asarray(decoded["mode_coefficients"], dtype=float).reshape(-1)


def _candidate_distance(ctx: Stage30Context, lhs: dict[str, Any], rhs: dict[str, Any]) -> float:
    return float(np.linalg.norm(_full_mode_vector(ctx, lhs) - _full_mode_vector(ctx, rhs)))


def select_sqp_centers(ctx: Stage30Context, rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    if not successful:
        raise RuntimeError("No successful Stage3.0 candidates are available as SQP centers")
    primary = min(
        successful,
        key=lambda row: (
            float(row.get("stage3_0_max_violation", 1e12)),
            float(row.get("stage3_0_sum_violation", 1e12)),
            float(row.get("selection_score", 99e18)),
        ),
    )
    minimum_distance = float(ctx.cfg["sqp"].get("center_minimum_distance", 0.03))
    speed_safe = sorted(
        [row for row in successful if _as_bool(row.get("stage3_0_speed_safe_at_best_endpoint"), False)],
        key=lambda row: (
            float(row.get("stage3_0_position_violation", 1e12)),
            float(row.get("stage3_0_max_violation", 1e12)),
        ),
    )
    alternatives = speed_safe + sorted(
        successful,
        key=lambda row: (
            float(row.get("stage3_0_max_violation", 1e12)),
            float(row.get("stage3_0_sum_violation", 1e12)),
        ),
    )
    secondary = None
    for row in alternatives:
        if row["candidate_id"] == primary["candidate_id"]:
            continue
        if row.get("nominal_id") != primary.get("nominal_id") or _candidate_distance(ctx, primary, row) >= minimum_distance:
            secondary = row
            break
    if secondary is None:
        secondary = next((row for row in alternatives if row["candidate_id"] != primary["candidate_id"]), None)
    if secondary is None:
        raise RuntimeError("Could not select two distinct Stage3.0 SQP centers")
    return [primary, secondary]


def build_probe_manifest(
    ctx: Stage30Context,
    *,
    round_index: int,
    centers: Sequence[dict[str, Any]],
    delta_matrix: np.ndarray | None = None,
    phase_prefix: str = "round",
) -> dict[str, Any]:
    delta = (
        np.asarray(delta_matrix, dtype=float)
        if delta_matrix is not None
        else np.asarray(ctx.cfg["sqp"]["probe_delta_by_step_mode"], dtype=float)
    )
    if delta.shape != (6, 3):
        raise ValueError("Stage3.0 probe delta matrix must be 6x3")
    phase = f"{phase_prefix}_{round_index:03d}_probes"
    phase_dir = ctx.paths.phases / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = phase_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)
    rows: list[dict[str, Any]] = []
    for center_index, center in enumerate(centers):
        nominal = nominal_by_id(ctx, str(center["nominal_id"]))
        center_tail = _tail_vector(center["tail_vector"])
        for variable_index in range(18):
            requested = float(delta.reshape(-1)[variable_index])
            center_value = float(center_tail[variable_index])
            lower = float(ctx.coefficient_lower[variable_index])
            upper = float(ctx.coefficient_upper[variable_index])
            lower_room = max(center_value - lower, 0.0)
            upper_room = max(upper - center_value, 0.0)
            eps = 1e-10
            if lower_room > eps and upper_room > eps:
                low_value = center_value - min(requested, lower_room)
                high_value = center_value + min(requested, upper_room)
                scheme = "two_sided"
            elif lower_room > eps:
                full = min(requested, lower_room)
                if full <= eps:
                    raise RuntimeError(f"No finite-difference room for variable {variable_index}")
                low_value = center_value - full
                high_value = center_value - 0.5 * full
                scheme = "upper_bound_inward_secant"
            elif upper_room > eps:
                full = min(requested, upper_room)
                if full <= eps:
                    raise RuntimeError(f"No finite-difference room for variable {variable_index}")
                low_value = center_value + 0.5 * full
                high_value = center_value + full
                scheme = "lower_bound_inward_secant"
            else:
                raise RuntimeError(f"Stage3.0 coefficient variable {variable_index} has no feasible probe span")
            if high_value - low_value <= eps:
                raise RuntimeError(f"Finite-difference points collapsed for variable {variable_index}")
            for sign, probe_value in ((-1, low_value), (1, high_value)):
                tail = center_tail.copy()
                tail[variable_index] = probe_value
                tail = clip_tail(ctx, tail)
                actual = float(tail[variable_index] - center_tail[variable_index])
                rows.append(
                    candidate_row(
                        ctx,
                        nominal=nominal,
                        tail_vector=tail,
                        source_name=f"center{center_index}_v{variable_index}_{'p' if sign > 0 else 'm'}",
                        source_type="real_tsc_fd_probe",
                        phase_name=phase,
                        extra={
                            "probe_center_candidate_id": center["candidate_id"],
                            "probe_center_nominal_id": center["nominal_id"],
                            "probe_variable_index": variable_index,
                            "probe_sign": int(sign),
                            "probe_requested_delta": requested,
                            "probe_actual_delta": actual,
                            "probe_scheme": scheme,
                        },
                    )
                )
    # Keep every center/variable/sign experiment even if two centers happen to
    # generate the same physical sequence.  Dropping a cross-center duplicate
    # would make one Jacobian column disappear and previously caused the whole
    # round to abort.  IDs include probe provenance, so result files remain
    # unique and auditable.
    expected = len(centers) * 18 * 2
    if len(rows) != expected:
        raise RuntimeError(f"Constructed {len(rows)} probes, expected {expected}")
    for index, row in enumerate(rows):
        row["population_index"] = index
        identity = (
            f"{row['probe_center_candidate_id']}|{row['probe_variable_index']}|"
            f"{row['probe_sign']}|{_vector_key(row['nominal_id'], row['tail_vector'])}"
        )
        row["candidate_id"] = f"s30r{round_index:02d}p_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "phase": phase,
        "round_index": round_index,
        "population_size": len(rows),
        "centers": [
            {
                "candidate_id": center["candidate_id"],
                "nominal_id": center["nominal_id"],
                "tail_vector": _tail_vector(center["tail_vector"]).tolist(),
                "result_relpath": center["result_relpath"],
            }
            for center in centers
        ],
        "candidates": rows,
    }
    atomic_write_json(manifest_path, manifest)
    write_csv(phase_dir / "candidate_manifest.csv", rows)
    return manifest


def feature_names() -> list[str]:
    names: list[str] = []
    for prefix in ("R_error_m", "Z_error_m", "vR_m_per_s", "vZ_m_per_s", "Ip_error_A"):
        for state_index in range(10, 16):
            names.append(f"{prefix}_state{state_index}")
    return names


def build_real_tsc_jacobian(
    ctx: Stage30Context,
    *,
    center: dict[str, Any],
    probe_manifest: dict[str, Any],
    probe_rows: Sequence[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    center_result = load_result_for_row(ctx, center)
    center_feature = trajectory_feature_vector(ctx, center_result)
    center_tail = _tail_vector(center["tail_vector"])
    probe_by_id = {str(row["candidate_id"]): row for row in probe_rows}
    manifest_rows = [
        row
        for row in probe_manifest["candidates"]
        if str(row.get("probe_center_candidate_id")) == str(center["candidate_id"])
    ]
    grouped: dict[int, dict[int, dict[str, Any]]] = {}
    for spec_row in manifest_rows:
        grouped.setdefault(int(spec_row["probe_variable_index"]), {})[int(spec_row["probe_sign"])] = spec_row

    jacobian = np.zeros((30, 18), dtype=float)
    column_rows: list[dict[str, Any]] = []
    reliable = 0
    for variable_index in range(18):
        pair = grouped.get(variable_index, {})
        plus_spec = pair.get(1)
        minus_spec = pair.get(-1)
        plus_row = None if plus_spec is None else probe_by_id.get(str(plus_spec["candidate_id"]))
        minus_row = None if minus_spec is None else probe_by_id.get(str(minus_spec["candidate_id"]))
        plus_ok = plus_row is not None and _as_bool(plus_row.get("success"), False)
        minus_ok = minus_row is not None and _as_bool(minus_row.get("success"), False)
        method = "unavailable"
        denominator: float | None = None
        if plus_ok and minus_ok:
            plus_result = load_result_for_row(ctx, plus_row)
            minus_result = load_result_for_row(ctx, minus_row)
            plus_feature = trajectory_feature_vector(ctx, plus_result)
            minus_feature = trajectory_feature_vector(ctx, minus_result)
            plus_tail = _tail_vector(plus_row["tail_vector"])
            minus_tail = _tail_vector(minus_row["tail_vector"])
            denominator = float(plus_tail[variable_index] - minus_tail[variable_index])
            if abs(denominator) > 1e-12:
                jacobian[:, variable_index] = (plus_feature - minus_feature) / denominator
                method = "central"
                reliable += 1
        elif plus_ok:
            plus_result = load_result_for_row(ctx, plus_row)
            plus_feature = trajectory_feature_vector(ctx, plus_result)
            plus_tail = _tail_vector(plus_row["tail_vector"])
            denominator = float(plus_tail[variable_index] - center_tail[variable_index])
            if abs(denominator) > 1e-12:
                jacobian[:, variable_index] = (plus_feature - center_feature) / denominator
                method = "forward"
                reliable += 1
        elif minus_ok:
            minus_result = load_result_for_row(ctx, minus_row)
            minus_feature = trajectory_feature_vector(ctx, minus_result)
            minus_tail = _tail_vector(minus_row["tail_vector"])
            denominator = float(center_tail[variable_index] - minus_tail[variable_index])
            if abs(denominator) > 1e-12:
                jacobian[:, variable_index] = (center_feature - minus_feature) / denominator
                method = "backward"
                reliable += 1
        column_rows.append(
            {
                "variable_index": variable_index,
                "tail_step": int(ctx.tail_steps[variable_index // 3]),
                "mode_index": int(variable_index % 3),
                "method": method,
                "denominator": denominator,
                "column_norm": float(np.linalg.norm(jacobian[:, variable_index])),
                "plus_success": plus_ok,
                "minus_success": minus_ok,
            }
        )
    if reliable < 12:
        raise RuntimeError(
            f"Only {reliable}/18 Stage3.0 finite-difference columns are usable around {center['candidate_id']}"
        )
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    nonzero = singular_values[singular_values > max(singular_values[0], 1.0) * 1e-10]
    condition = float(nonzero[0] / nonzero[-1]) if len(nonzero) >= 2 else math.inf
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_dir / f"jacobian_{center['candidate_id']}.npz",
        center_feature=center_feature,
        jacobian=jacobian,
        center_tail=center_tail,
        feature_names=np.asarray(feature_names(), dtype="U64"),
    )
    write_csv(output_dir / f"jacobian_{center['candidate_id']}_columns.csv", column_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "center_candidate_id": center["candidate_id"],
        "center_nominal_id": center["nominal_id"],
        "center_tail_vector": center_tail.tolist(),
        "center_feature": center_feature.tolist(),
        "feature_names": feature_names(),
        "jacobian": jacobian.tolist(),
        "reliable_columns": reliable,
        "singular_values": singular_values.tolist(),
        "numerical_rank": int(len(nonzero)),
        "condition_nonzero": condition if math.isfinite(condition) else None,
        "columns": column_rows,
    }
    atomic_write_json(output_dir / f"jacobian_{center['candidate_id']}.json", summary)
    return summary


def _soft_hinge(value: np.ndarray, beta: float) -> np.ndarray:
    scaled = beta * np.asarray(value, dtype=float)
    return np.logaddexp(0.0, scaled) / beta


def _linear_model_objective(
    ctx: Stage30Context,
    *,
    center_tail: np.ndarray,
    center_feature: np.ndarray,
    jacobian: np.ndarray,
    delta: np.ndarray,
    endpoint: int,
    profile: dict[str, float],
    source_step8: np.ndarray,
) -> float:
    predicted = unpack_feature_vector(center_feature + jacobian @ delta)
    local_start = max(0, endpoint - 2 - 10)
    velocity_start = max(0, endpoint - int(ctx.cfg["gate"]["late_window_steps"]) + 1 - 10)
    tolerance = float(ctx.cfg["gate"]["precise_tolerance_m"])
    speed_limit = float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"])
    beta = float(ctx.cfg["sqp"]["linear_solver"].get("softplus_beta", 80.0))
    r = predicted["R"][local_start:]
    z = predicted["Z"][local_start:]
    vr = predicted["vR"][velocity_start:]
    vz = predicted["vZ"][velocity_start:]
    position_core = float(np.mean((r / tolerance) ** 2 + (z / tolerance) ** 2))
    excess_r = _soft_hinge(np.sqrt(r**2 + 1e-12) - tolerance, beta) / tolerance
    excess_z = _soft_hinge(np.sqrt(z**2 + 1e-12) - tolerance, beta) / tolerance
    tube_excess = float(np.mean(excess_r**2 + excess_z**2))
    velocity_core = float(np.mean((vr / speed_limit) ** 2 + (vz / speed_limit) ** 2))
    ip_core = float((predicted["Ip"][-1] / float(ctx.cfg["gate"]["ip_tolerance_a"])) ** 2)
    trial_tail = (center_tail + delta).reshape(6, 3)
    source_step8 = np.asarray(source_step8, dtype=float).reshape(1, 3)
    delta_l2 = float(ctx.cfg["sqp"]["linear_solver"].get("delta_l2", 0.05)) * float(np.mean(delta**2))
    # Include the frozen step-8 -> optimized step-9 boundary.  Omitting this
    # transition can make the local optimizer exploit a sharp mode jump that
    # is later hidden by per-coil action repair.
    tail_with_boundary = np.vstack([source_step8, trial_tail])
    smoothness = float(ctx.cfg["sqp"]["linear_solver"].get("tail_smoothness", 0.03)) * float(
        np.mean(np.diff(tail_with_boundary, axis=0) ** 2)
    )
    return float(
        float(profile.get("position", 1.0)) * position_core
        + float(profile.get("velocity", 1.0)) * velocity_core
        + float(profile.get("tube_excess", 3.0)) * tube_excess
        + 0.05 * ip_core
        + delta_l2
        + smoothness
    )


def _predicted_constraints_from_feature(ctx: Stage30Context, feature: np.ndarray, endpoint: int) -> dict[str, float]:
    values = unpack_feature_vector(feature)
    local_start = endpoint - 2 - 10
    position = float(
        np.max(
            np.abs(
                np.column_stack([values["R"][local_start:], values["Z"][local_start:]])
            )
        )
    )
    speed = np.sqrt(values["vR"] ** 2 + values["vZ"] ** 2)
    endpoint_local = endpoint - 10
    late_start = max(0, endpoint_local - int(ctx.cfg["gate"]["late_window_steps"]) + 1)
    endpoint_speed = float(speed[endpoint_local])
    endpoint_late = float(np.sqrt(np.mean(speed[late_start : endpoint_local + 1] ** 2)))
    post_speed = float(np.sqrt(np.mean(speed[endpoint_local:] ** 2)))
    final_speed = float(speed[-1])
    ip = float(np.max(np.abs(values["Ip"][local_start:])))
    violations = np.asarray(
        [
            max(position / float(ctx.cfg["gate"]["precise_tolerance_m"]) - 1.0, 0.0),
            max(endpoint_speed / float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"]) - 1.0, 0.0),
            max(endpoint_late / float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"]) - 1.0, 0.0),
            max(post_speed / float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"]) - 1.0, 0.0),
            max(final_speed / float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"]) - 1.0, 0.0),
            max(ip / float(ctx.cfg["gate"]["ip_tolerance_a"]) - 1.0, 0.0),
        ],
        dtype=float,
    )
    return {
        "max_violation": float(np.max(violations)),
        "sum_violation": float(np.sum(violations)),
        "position_box_m": position,
        "endpoint_speed_m_per_s": endpoint_speed,
        "late_speed_m_per_s": endpoint_late,
        "post_speed_m_per_s": post_speed,
    }


def solve_linearized_tail_proposals(
    ctx: Stage30Context,
    *,
    center: dict[str, Any],
    jacobian_summary: dict[str, Any],
    trust_scale: float,
    round_index: int,
) -> list[dict[str, Any]]:
    try:
        from scipy.optimize import minimize
    except Exception as exc:  # pragma: no cover - server dependency
        raise RuntimeError("scipy is required for Stage3.0 trust-region SQP proposals") from exc
    nominal = nominal_by_id(ctx, str(center["nominal_id"]))
    center_tail = _tail_vector(center["tail_vector"])
    source_step8 = np.asarray(nominal["mode_coefficients_100ms"], dtype=float)[8]
    center_feature = np.asarray(jacobian_summary["center_feature"], dtype=float)
    jacobian = np.asarray(jacobian_summary["jacobian"], dtype=float)
    radius = np.asarray(ctx.cfg["sqp"]["trust_radius_by_step_mode"], dtype=float).reshape(-1) * float(trust_scale)
    lower_delta = np.maximum(ctx.coefficient_lower - center_tail, -radius)
    upper_delta = np.minimum(ctx.coefficient_upper - center_tail, radius)
    # Do not let the local solver move a variable whose real-TSC finite-
    # difference column was unavailable. A zero Jacobian column alone is not
    # sufficient protection because the smoothness regularizer can otherwise
    # move that variable despite having no measured plant sensitivity. Older
    # summaries/tests without column metadata are treated as fully reliable.
    column_metadata = jacobian_summary.get("columns")
    unavailable_variables: list[int] = []
    if isinstance(column_metadata, list) and len(column_metadata) == 18:
        for variable_index, column in enumerate(column_metadata):
            if str(column.get("method", "unavailable")) == "unavailable":
                lower_delta[variable_index] = 0.0
                upper_delta[variable_index] = 0.0
                unavailable_variables.append(variable_index)
    bounds = list(zip(lower_delta.tolist(), upper_delta.tolist()))
    profile_cfg = ctx.cfg["sqp"]["linear_solver"]["profiles"]
    base_requests: list[tuple[int, str]] = [(endpoint, "balanced") for endpoint in (12, 13, 14, 15)]
    base_requests.extend([(15, "position"), (15, "damping")])
    rows: list[dict[str, Any]] = []
    for endpoint, profile_name in base_requests:
        profile = dict(profile_cfg[profile_name])
        objective = lambda delta: _linear_model_objective(
            ctx,
            center_tail=center_tail,
            center_feature=center_feature,
            jacobian=jacobian,
            delta=np.asarray(delta, dtype=float),
            endpoint=endpoint,
            profile=profile,
            source_step8=source_step8,
        )
        result = minimize(
            objective,
            np.zeros(18, dtype=float),
            method="SLSQP",
            bounds=bounds,
            options={
                "maxiter": int(ctx.cfg["sqp"]["linear_solver"].get("max_iterations", 400)),
                "ftol": 1e-12,
                "disp": False,
            },
        )
        solution = np.asarray(result.x, dtype=float)
        for step_scale in (0.5, 1.0):
            delta = solution * step_scale
            tail = clip_tail(ctx, center_tail + delta)
            predicted_feature = center_feature + jacobian @ (tail - center_tail)
            predicted = _predicted_constraints_from_feature(ctx, predicted_feature, endpoint)
            rows.append(
                candidate_row(
                    ctx,
                    nominal=nominal,
                    tail_vector=tail,
                    source_name=f"center_{center['candidate_id']}_{profile_name}_e{endpoint}_s{step_scale:.1f}",
                    source_type="real_tsc_sqp_step",
                    phase_name=f"round_{round_index:03d}_steps",
                    extra={
                        "sqp_center_candidate_id": center["candidate_id"],
                        "sqp_profile": profile_name,
                        "sqp_endpoint_step": endpoint,
                        "sqp_step_scale": step_scale,
                        "sqp_solver_success": bool(result.success),
                        "sqp_solver_message": str(result.message),
                        "predicted_linear_objective": float(objective(tail - center_tail)),
                        "predicted_max_violation": float(predicted["max_violation"]),
                        "predicted_sum_violation": float(predicted["sum_violation"]),
                        "predicted_position_box_m": float(predicted["position_box_m"]),
                        "predicted_endpoint_speed_m_per_s": float(predicted["endpoint_speed_m_per_s"]),
                        "predicted_late_speed_m_per_s": float(predicted["late_speed_m_per_s"]),
                        "unavailable_jacobian_variables_frozen": unavailable_variables,
                    },
                )
            )
    rows = _dedupe_candidates(rows)
    # Degenerate linear models can produce duplicate zero steps. Fill to exactly
    # twelve proposals with deterministic trust-box perturbations around the
    # best predicted solution. These fills are explicit and remain real-TSC tested.
    rng = np.random.default_rng(20260723 + round_index * 1009 + int(hashlib.sha256(str(center["candidate_id"]).encode()).hexdigest()[:6], 16))
    attempts = 0
    while len(rows) < 12 and attempts < 500:
        attempts += 1
        delta = rng.uniform(lower_delta, upper_delta) * 0.35
        tail = clip_tail(ctx, center_tail + delta)
        predicted_feature = center_feature + jacobian @ (tail - center_tail)
        predicted = _predicted_constraints_from_feature(ctx, predicted_feature, 15)
        rows = _dedupe_candidates(
            [
                *rows,
                candidate_row(
                    ctx,
                    nominal=nominal,
                    tail_vector=tail,
                    source_name=f"linear_fill_{attempts:03d}",
                    source_type="real_tsc_sqp_fill",
                    phase_name=f"round_{round_index:03d}_steps",
                    extra={
                        "sqp_center_candidate_id": center["candidate_id"],
                        "sqp_profile": "fill",
                        "sqp_endpoint_step": 15,
                        "sqp_step_scale": 1.0,
                        "sqp_solver_success": True,
                        "predicted_linear_objective": float(
                            _linear_model_objective(
                                ctx,
                                center_tail=center_tail,
                                center_feature=center_feature,
                                jacobian=jacobian,
                                delta=tail - center_tail,
                                endpoint=15,
                                profile=dict(profile_cfg["balanced"]),
                                source_step8=source_step8,
                            )
                        ),
                        "predicted_max_violation": float(predicted["max_violation"]),
                        "predicted_sum_violation": float(predicted["sum_violation"]),
                        "unavailable_jacobian_variables_frozen": unavailable_variables,
                    },
                ),
            ]
        )
    if len(rows) < 12:
        raise RuntimeError(f"Only {len(rows)} unique SQP proposals were produced for center {center['candidate_id']}")
    rows.sort(key=lambda row: (_finite(row.get("predicted_max_violation"), 1e9), _finite(row.get("predicted_linear_objective"), 1e9)))
    return rows[:12]


def build_step_manifest(
    ctx: Stage30Context,
    *,
    round_index: int,
    centers: Sequence[dict[str, Any]],
    jacobians: Sequence[dict[str, Any]],
    trust_scale: float,
) -> dict[str, Any]:
    phase = f"round_{round_index:03d}_steps"
    phase_dir = ctx.paths.phases / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = phase_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)
    rows: list[dict[str, Any]] = []
    for center, jacobian in zip(centers, jacobians):
        rows.extend(
            solve_linearized_tail_proposals(
                ctx,
                center=center,
                jacobian_summary=jacobian,
                trust_scale=trust_scale,
                round_index=round_index,
            )
        )
    # Each center contributes twelve proposals.  Preserve all 24 even if two
    # local models converge to the same tail, because provenance matters for
    # diagnosing the trust-region models and a global dedupe must not make the
    # fixed-size wave fail.
    if len(rows) != 24:
        raise RuntimeError(f"Stage3.0 SQP step wave has {len(rows)} candidates, expected 24")
    for index, row in enumerate(rows):
        row["population_index"] = index
        identity = (
            f"{row.get('sqp_center_candidate_id','')}|{row.get('sqp_profile','')}|"
            f"{row.get('sqp_endpoint_step','')}|{row.get('sqp_step_scale','')}|"
            f"{_vector_key(row['nominal_id'], row['tail_vector'])}"
        )
        row["candidate_id"] = f"s30r{round_index:02d}s_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "phase": phase,
        "round_index": round_index,
        "trust_scale": trust_scale,
        "population_size": len(rows),
        "centers": [
            {"candidate_id": center["candidate_id"], "nominal_id": center["nominal_id"]}
            for center in centers
        ],
        "candidates": rows,
    }
    atomic_write_json(manifest_path, manifest)
    write_csv(phase_dir / "candidate_manifest.csv", rows)
    return manifest


def run_one_sqp_round(
    ctx: Stage30Context,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if not state.get("screen_complete"):
        state = run_screen(ctx, backend=backend, resume=resume)
    if state.get("optimization_finished"):
        return state
    round_index = int(state["next_sqp_round"])
    max_rounds = int(state["max_sqp_rounds"])
    if round_index >= max_rounds:
        state["optimization_finished"] = True
        state["stop_reason"] = "max_sqp_rounds"
        atomic_write_json(ctx.paths.state, state)
        return state
    historical = aggregate_rows(ctx.paths)
    centers = select_sqp_centers(ctx, historical)
    previous_best = min(
        (float(row.get("stage3_0_max_violation", 1e12)) for row in historical if _as_bool(row.get("success"), False)),
        default=1e12,
    )
    probe_manifest = build_probe_manifest(ctx, round_index=round_index, centers=centers)
    probe_rows, _ = evaluate_manifest(ctx, manifest=probe_manifest, backend=backend, resume=resume)
    state = update_state_best(ctx, state, probe_rows)
    jacobian_dir = ctx.paths.phases / f"round_{round_index:03d}_jacobians"
    jacobians = [
        build_real_tsc_jacobian(
            ctx,
            center=center,
            probe_manifest=probe_manifest,
            probe_rows=probe_rows,
            output_dir=jacobian_dir,
        )
        for center in centers
    ]
    step_manifest = build_step_manifest(
        ctx,
        round_index=round_index,
        centers=centers,
        jacobians=jacobians,
        trust_scale=float(state["trust_scale"]),
    )
    step_rows, _ = evaluate_manifest(ctx, manifest=step_manifest, backend=backend, resume=resume)
    state = update_state_best(ctx, state, step_rows)
    current_rows = [*probe_rows, *step_rows]
    current_best = min(
        (float(row.get("stage3_0_max_violation", 1e12)) for row in current_rows if _as_bool(row.get("success"), False)),
        default=1e12,
    )
    meaningful = float(ctx.cfg["sqp"].get("meaningful_improvement", 0.0001))
    improved = current_best < previous_best - meaningful
    factor = float(
        ctx.cfg["sqp"]["trust_shrink_on_improvement"]
        if improved
        else ctx.cfg["sqp"]["trust_shrink_without_improvement"]
    )
    state["trust_scale"] = max(
        float(ctx.cfg["sqp"]["minimum_trust_scale"]),
        float(state["trust_scale"]) * factor,
    )
    state["next_sqp_round"] = round_index + 1
    state["last_round"] = {
        "round_index": round_index,
        "centers": [center["candidate_id"] for center in centers],
        "previous_best_max_violation": previous_best,
        "round_best_max_violation": current_best,
        "meaningful_improvement": improved,
        "next_trust_scale": state["trust_scale"],
    }
    if state.get("strict_gate_found"):
        state["optimization_finished"] = True
        state["stop_reason"] = "strict_gate_found"
    elif int(state["next_sqp_round"]) >= max_rounds:
        state["optimization_finished"] = True
        state["stop_reason"] = "max_sqp_rounds"
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    best = best_successful_row(current_rows)
    print(
        json.dumps(
            {
                "stage": "Stage3.0",
                "round": round_index,
                "probe_success": sum(_as_bool(row.get("success"), False) for row in probe_rows),
                "step_success": sum(_as_bool(row.get("success"), False) for row in step_rows),
                "strict": sum(_as_bool(row.get("strict_gate_pass"), False) for row in current_rows),
                "best": None
                if best is None
                else {
                    key: best.get(key)
                    for key in (
                        "candidate_id",
                        "nominal_id",
                        "source_type",
                        "stage3_0_best_endpoint_ms",
                        "stage3_0_sustained_box_max_error_m",
                        "stage3_0_post_arrival_velocity_rms_m_per_s",
                        "stage3_0_max_violation",
                    )
                },
                "next_round": state["next_sqp_round"],
                "trust_scale": state["trust_scale"],
                "finished": state["optimization_finished"],
                "stop_reason": state["stop_reason"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )
    return state


def run_optimization(ctx: Stage30Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if not state.get("screen_complete"):
        state = run_screen(ctx, backend=backend, resume=resume)
    while not state.get("optimization_finished"):
        state = run_one_sqp_round(ctx, backend=backend, resume=resume)
    return state

# ---------------------------------------------------------------------------
# Final local identification and MPC-compatible batch gain export
# ---------------------------------------------------------------------------


def run_controller_identification(
    ctx: Stage30Context,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if state.get("controller_identification_complete"):
        bundle_path = ctx.paths.controller / "mpc_poc_bundle.json"
        return read_json(bundle_path) if bundle_path.exists() else state
    rows = aggregate_rows(ctx.paths)
    center = best_successful_row(rows)
    if center is None:
        raise RuntimeError("No successful Stage3.0 candidate is available for controller identification")
    delta = np.asarray(ctx.cfg["controller_identification"]["probe_delta_by_step_mode"], dtype=float)
    manifest = build_probe_manifest(
        ctx,
        round_index=999,
        centers=[center],
        delta_matrix=delta,
        phase_prefix="controller_identification",
    )
    probe_rows, _ = evaluate_manifest(ctx, manifest=manifest, backend=backend, resume=resume)
    state = update_state_best(ctx, state, probe_rows)
    jacobian_summary = build_real_tsc_jacobian(
        ctx,
        center=center,
        probe_manifest=manifest,
        probe_rows=probe_rows,
        output_dir=ctx.paths.controller,
    )
    center_feature = np.asarray(jacobian_summary["center_feature"], dtype=float)
    jacobian = np.asarray(jacobian_summary["jacobian"], dtype=float)
    endpoint = int(center.get("stage3_0_best_endpoint_step", 15))
    local_start = max(0, endpoint - 2 - 10)
    indices: list[int] = []
    weights: list[float] = []
    # Position and velocity outputs from the requested arrival window through 150 ms.
    for block, weight in ((0, 1.0), (6, 1.0), (12, 0.7), (18, 0.7)):
        for local in range(local_start, 6):
            indices.append(block + local)
            weights.append(weight)
    # Terminal Ip is retained with a weak weight.
    indices.append(24 + 5)
    weights.append(0.05)
    j_selected = jacobian[np.asarray(indices, dtype=int)]
    w = np.diag(np.asarray(weights, dtype=float))
    ridge = float(ctx.cfg["controller_identification"].get("ridge_lambda", 0.05))
    lhs = j_selected.T @ w @ j_selected + np.eye(18) * ridge
    gain = -np.linalg.solve(lhs, j_selected.T @ w)
    selected_feature = center_feature[np.asarray(indices, dtype=int)]
    nominal_correction = gain @ selected_feature
    radius = np.asarray(ctx.cfg["sqp"]["trust_radius_by_step_mode"], dtype=float).reshape(-1)
    nominal_correction_clipped = np.clip(nominal_correction, -radius, radius)
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "created_utc": utc_timestamp(),
        "center_candidate_id": center["candidate_id"],
        "center_nominal_id": center["nominal_id"],
        "center_best_endpoint_step": endpoint,
        "center_best_endpoint_ms": endpoint * int(ctx.env_cfg["dt_ms"]),
        "tail_variable_steps": list(ctx.tail_steps),
        "feature_names_all": jacobian_summary["feature_names"],
        "selected_feature_indices": indices,
        "selected_feature_names": [jacobian_summary["feature_names"][index] for index in indices],
        "selected_feature_weights": weights,
        "center_selected_feature": selected_feature.tolist(),
        "jacobian_selected": j_selected.tolist(),
        "ridge_lambda": ridge,
        "batch_gain": gain.tolist(),
        "nominal_linear_correction": nominal_correction.tolist(),
        "nominal_linear_correction_clipped": nominal_correction_clipped.tolist(),
        "online_feedback_validated": False,
        "deployment_status": "OFFLINE_MPC_COMPATIBLE_POC_ONLY",
        "warning": (
            "This gain maps a batch of nominal future-output errors to six remaining tail controls. "
            "It has not been tested in receding-horizon closed loop or under changed initial states."
        ),
    }
    ctx.paths.controller.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.controller / "mpc_poc_bundle.json", bundle)
    np.savez_compressed(
        ctx.paths.controller / "mpc_poc_bundle.npz",
        center_feature=center_feature,
        jacobian=jacobian,
        selected_indices=np.asarray(indices, dtype=int),
        selected_weights=np.asarray(weights, dtype=float),
        batch_gain=gain,
        nominal_correction=nominal_correction,
        nominal_correction_clipped=nominal_correction_clipped,
    )
    state["controller_identification_complete"] = True
    state["controller_identification_center"] = center["candidate_id"]
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(
        json.dumps(
            {
                "stage": "Stage3.0",
                "phase": "controller_identification",
                "center": center["candidate_id"],
                "successful_probes": sum(_as_bool(row.get("success"), False) for row in probe_rows),
                "reliable_columns": jacobian_summary["reliable_columns"],
                "numerical_rank": jacobian_summary["numerical_rank"],
                "online_feedback_validated": False,
            },
            indent=2,
        ),
        flush=True,
    )
    return bundle


# ---------------------------------------------------------------------------
# Category-aware confirmation
# ---------------------------------------------------------------------------


def _unique_ranked(rows: Sequence[dict[str, Any]], key_fn: Any, limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted([row for row in rows if _as_bool(row.get("success"), False)], key=key_fn):
        key = _vector_key(str(row["nominal_id"]), row["tail_vector"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def select_confirmation_candidates(ctx: Stage30Context, rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    cfg = ctx.cfg["confirmation"]
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    strict = [row for row in rows if _as_bool(row.get("strict_gate_pass"), False)]
    corner = list(rows)
    speed_safe = [row for row in rows if _as_bool(row.get("stage3_0_speed_safe_at_best_endpoint"), False)]
    relaxed = [row for row in rows if _as_bool(row.get("relaxed_gate_pass"), False)]
    earliest = [row for row in rows if row.get("stage3_0_earliest_strict_arrival_step") is not None]
    groups.append(
        (
            "strict",
            _unique_ranked(strict, lambda row: (row.get("stage3_0_earliest_strict_arrival_step", 99), _best_sort_key(row)), int(cfg["strict_candidates"])),
        )
    )
    groups.append(
        (
            "corner",
            _unique_ranked(
                corner,
                lambda row: (
                    float(row.get("stage3_0_max_violation", 1e12)),
                    float(row.get("stage3_0_sum_violation", 1e12)),
                ),
                int(cfg["corner_candidates"]),
            ),
        )
    )
    groups.append(
        (
            "speed_safe",
            _unique_ranked(
                speed_safe,
                lambda row: (
                    float(row.get("stage3_0_position_violation", 1e12)),
                    float(row.get("stage3_0_max_violation", 1e12)),
                ),
                int(cfg["speed_safe_candidates"]),
            ),
        )
    )
    groups.append(
        (
            "relaxed",
            _unique_ranked(relaxed, _best_sort_key, int(cfg["relaxed_candidates"])),
        )
    )
    groups.append(
        (
            "earliest_arrival",
            _unique_ranked(
                earliest,
                lambda row: (row.get("stage3_0_earliest_strict_arrival_step", 99), _best_sort_key(row)),
                int(cfg["earliest_arrival_candidates"]),
            ),
        )
    )
    selected: list[dict[str, Any]] = []
    reasons: dict[str, list[str]] = {}
    seen: set[str] = set()
    for reason, group in groups:
        for row in group:
            key = _vector_key(str(row["nominal_id"]), row["tail_vector"])
            reasons.setdefault(key, []).append(reason)
            if key in seen:
                continue
            seen.add(key)
            selected.append(copy.deepcopy(row))
    selected.sort(key=_best_sort_key)
    selected = selected[: int(cfg["max_unique_candidates"])]
    for rank, row in enumerate(selected, start=1):
        key = _vector_key(str(row["nominal_id"]), row["tail_vector"])
        row["confirmation_rank"] = rank
        row["confirmation_reasons"] = reasons.get(key, [])
    return selected


def run_confirmation(
    ctx: Stage30Context,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    rows = aggregate_rows(ctx.paths)
    candidates = select_confirmation_candidates(ctx, rows)
    if not candidates:
        verdict = {"verdict": "NO_SUCCESSFUL_STAGE3_0_CANDIDATE", "created_utc": utc_timestamp()}
        atomic_write_json(ctx.paths.confirmations / "stage3_0_verdict.json", verdict)
        return verdict
    repeats = int(ctx.cfg["confirmation"]["repeats_per_candidate"])
    specs: list[dict[str, Any]] = []
    for candidate in candidates:
        nominal = nominal_by_id(ctx, str(candidate["nominal_id"]))
        tail = _tail_vector(candidate["tail_vector"])
        decoded = decode_tail_sequence(ctx, nominal, tail)
        for repeat in range(repeats):
            experiment_id = f"s30confirm_rank{candidate['confirmation_rank']:02d}_{candidate['candidate_id']}_r{repeat:02d}"
            specs.append(
                {
                    "kind": "stage3_0_confirmation",
                    "experiment_id": experiment_id,
                    "candidate_id": candidate["candidate_id"],
                    "confirmation_rank": candidate["confirmation_rank"],
                    "confirmation_reasons": candidate["confirmation_reasons"],
                    "confirmation_repeat": repeat,
                    "nominal_id": candidate["nominal_id"],
                    "source_candidate_id": candidate["source_candidate_id"],
                    "horizon_steps": 15,
                    "tail_vector": tail.tolist(),
                    "mode_coefficients": np.asarray(decoded["mode_coefficients"], dtype=float).tolist(),
                    "action_sequence_norm_tsc": np.asarray(decoded["action_norm_tsc"], dtype=float).tolist(),
                    "action_sequence_norm_display": np.asarray(decoded["action_norm_display"], dtype=float).tolist(),
                }
            )
    results = s2.evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.confirmations / "raw",
        backend=backend,
        resume=resume,
    )
    spec_by_id = {spec["experiment_id"]: spec for spec in specs}
    metric_rows: list[dict[str, Any]] = []
    for result in results:
        spec = spec_by_id[str(result["experiment_id"])]
        nominal = nominal_by_id(ctx, str(spec["nominal_id"]))
        tail = _tail_vector(spec["tail_vector"])
        metrics = stage30_metrics(ctx, result, decode_tail_sequence(ctx, nominal, tail))
        metric_rows.append(
            {
                "stage": "Stage3.0 confirmation",
                "experiment_id": result["experiment_id"],
                "candidate_id": spec["candidate_id"],
                "confirmation_rank": spec["confirmation_rank"],
                "confirmation_reasons": spec["confirmation_reasons"],
                "repeat": spec["confirmation_repeat"],
                "nominal_id": spec["nominal_id"],
                "tail_vector": tail.tolist(),
                **metrics,
            }
        )
    write_csv(ctx.paths.confirmations / "confirmation_results.csv", metric_rows)
    atomic_write_json(ctx.paths.confirmations / "confirmation_results.json", metric_rows)
    summary_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        subset = [row for row in metric_rows if row["candidate_id"] == candidate["candidate_id"]]
        successful = [row for row in subset if _as_bool(row.get("success"), False)]
        strict_all = len(successful) == repeats and all(_as_bool(row.get("strict_gate_pass"), False) for row in successful)
        relaxed_all = len(successful) == repeats and all(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful)
        summary_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "confirmation_rank": candidate["confirmation_rank"],
                "confirmation_reasons": candidate["confirmation_reasons"],
                "nominal_id": candidate["nominal_id"],
                "repeats": repeats,
                "successful_repeats": len(successful),
                "all_repeats_strict_gate": strict_all,
                "all_repeats_relaxed_gate": relaxed_all,
                "worst_stage3_0_max_violation": max(
                    (_finite(row.get("stage3_0_max_violation"), 1e12) for row in subset), default=None
                ),
                "latest_confirmed_arrival_ms": max(
                    (
                        _as_int(row.get("stage3_0_earliest_strict_arrival_ms"), -1)
                        for row in successful
                        if row.get("stage3_0_earliest_strict_arrival_ms") is not None
                    ),
                    default=None,
                ),
                "worst_sustained_box_max_error_m": max(
                    (_finite(row.get("stage3_0_sustained_box_max_error_m"), 1e12) for row in successful),
                    default=None,
                ),
                "max_post_arrival_velocity_rms_m_per_s": max(
                    (
                        _finite(row.get("stage3_0_post_arrival_velocity_rms_m_per_s"), 1e12)
                        for row in successful
                    ),
                    default=None,
                ),
            }
        )
    write_csv(ctx.paths.confirmations / "confirmation_summary.csv", summary_rows)
    atomic_write_json(ctx.paths.confirmations / "confirmation_summary.json", summary_rows)
    if any(row["all_repeats_strict_gate"] for row in summary_rows):
        verdict_name = "PASS_PRECISE_HOLD_30MM_120_150MS_CONFIRMED"
    elif any(row["all_repeats_relaxed_gate"] for row in summary_rows):
        verdict_name = "PASS_DAMPED_HOLD_40MM_120_150MS_CONFIRMED_ONLY"
    else:
        verdict_name = "NO_CONFIRMED_120_150MS_HOLD"
    verdict = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "verdict": verdict_name,
        "created_utc": utc_timestamp(),
        "arrival_window_ms": [120, 130, 140, 150],
        "hard_100ms_deadline": False,
        "candidate_summaries": summary_rows,
        "robustness_validated": False,
        "robustness_warning": (
            "Repeated deterministic rollouts confirm reproducibility only. Initial-state, target, noise and model-parameter robustness remain untested."
        ),
    }
    atomic_write_json(ctx.paths.confirmations / "stage3_0_verdict.json", verdict)
    state = read_json(ctx.paths.state)
    state["confirmation_complete"] = True
    state["confirmation_verdict"] = verdict_name
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(json.dumps(verdict, indent=2, ensure_ascii=False), flush=True)
    return verdict

# ---------------------------------------------------------------------------
# Analysis, plots and report
# ---------------------------------------------------------------------------


def unique_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not _as_bool(row.get("success"), False):
            continue
        key = _vector_key(str(row["nominal_id"]), row["tail_vector"])
        previous = best_by_key.get(key)
        if previous is None or _best_sort_key(row) < _best_sort_key(previous):
            best_by_key[key] = row
    return list(best_by_key.values())


def hall_of_fames(rows: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    unique = unique_rows(rows)
    strict = sorted(
        [row for row in unique if _as_bool(row.get("strict_gate_pass"), False)],
        key=lambda row: (row.get("stage3_0_earliest_strict_arrival_step", 99), _best_sort_key(row)),
    )
    minimax = sorted(
        unique,
        key=lambda row: (
            float(row.get("stage3_0_max_violation", 1e12)),
            float(row.get("stage3_0_sum_violation", 1e12)),
            _best_sort_key(row),
        ),
    )
    speed_safe = sorted(
        [row for row in unique if _as_bool(row.get("stage3_0_speed_safe_at_best_endpoint"), False)],
        key=lambda row: (
            float(row.get("stage3_0_position_violation", 1e12)),
            float(row.get("stage3_0_max_violation", 1e12)),
        ),
    )
    relaxed = sorted(
        [row for row in unique if _as_bool(row.get("relaxed_gate_pass"), False)],
        key=_best_sort_key,
    )
    earliest = sorted(
        strict,
        key=lambda row: (row.get("stage3_0_earliest_strict_arrival_step", 99), _best_sort_key(row)),
    )
    return {
        "strict": strict,
        "minimax": minimax,
        "speed_safe": speed_safe,
        "relaxed": relaxed,
        "earliest_arrival": earliest,
    }


def generate_stage30_plots(ctx: Stage30Context, rows: Sequence[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[Stage3.0 analysis] matplotlib unavailable; plots skipped: {exc}", flush=True)
        return
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    if not successful:
        return
    phase_order: dict[str, int] = {}
    for row in successful:
        phase = str(row["phase"])
        if phase not in phase_order:
            phase_order[phase] = len(phase_order)
    phase_best = []
    for phase, index in phase_order.items():
        subset = [row for row in successful if row["phase"] == phase]
        best = min(subset, key=lambda row: float(row.get("stage3_0_max_violation", 1e12)))
        phase_best.append((index, phase, best))
    phase_best.sort()
    plt.figure(figsize=(10, 5))
    plt.plot(
        [item[0] for item in phase_best],
        [100.0 * float(item[2].get("stage3_0_max_violation", 1e12)) for item in phase_best],
        marker="o",
    )
    plt.xticks([item[0] for item in phase_best], [item[1] for item in phase_best], rotation=45, ha="right")
    plt.ylabel("Best maximum normalized violation [%]")
    plt.title("Stage3.0 real-TSC extended-horizon progress")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(ctx.paths.analysis / "max_violation_by_phase.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 6))
    x = [1000.0 * float(row.get("stage3_0_sustained_box_max_error_m", 1.0)) for row in successful]
    y = [float(row.get("stage3_0_post_arrival_velocity_rms_m_per_s", 1.0)) for row in successful]
    c = [int(row.get("stage3_0_best_endpoint_ms", 150)) for row in successful]
    scatter = plt.scatter(x, y, c=c, s=16, alpha=0.65)
    plt.axvline(30.0, linestyle="--", linewidth=1)
    plt.axvline(40.0, linestyle=":", linewidth=1)
    plt.axhline(float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"]), linestyle="--", linewidth=1)
    plt.xlabel("Sustained rectangular R/Z box error through 150 ms [mm]")
    plt.ylabel("Post-arrival velocity RMS [m/s]")
    plt.title("Stage3.0 120-150 ms feasibility map")
    plt.colorbar(scatter, label="Selected arrival endpoint [ms]")
    plt.tight_layout()
    plt.savefig(ctx.paths.analysis / "extended_horizon_feasibility_scatter.png", dpi=180)
    plt.close()

    best_result_path = ctx.paths.best / "best_tsc_result.json.gz"
    if best_result_path.exists():
        result = read_json_gz(best_result_path)
        trajectory = result.get("trajectory", [])
        if trajectory:
            time_ms = [int(row["time_ms"]) for row in trajectory]
            r_error = [1000.0 * (float(row["R"]) - float(ctx.cfg["target"]["R"])) for row in trajectory]
            z_error = [1000.0 * (float(row["Z"]) - float(ctx.cfg["target"]["Z"])) for row in trajectory]
            y = np.asarray([[row["R"], row["Z"]] for row in trajectory], dtype=float)
            velocity = np.linalg.norm(_velocity_components(y, float(ctx.env_cfg["dt_ms"]) / 1000.0), axis=1)
            absolute_arrival_start = start_time_ms(ctx.env_cfg) + min(ctx.cfg["gate"]["allowed_arrival_steps"]) * int(ctx.env_cfg["dt_ms"])
            absolute_arrival_end = start_time_ms(ctx.env_cfg) + max(ctx.cfg["gate"]["allowed_arrival_steps"]) * int(ctx.env_cfg["dt_ms"])
            plt.figure(figsize=(10, 5))
            plt.plot(time_ms, r_error, marker="o", label="R error")
            plt.plot(time_ms, z_error, marker="o", label="Z error")
            plt.axhline(30.0, linestyle="--", linewidth=1)
            plt.axhline(-30.0, linestyle="--", linewidth=1)
            plt.axvspan(absolute_arrival_start, absolute_arrival_end, alpha=0.08, label="Allowed arrival endpoints")
            plt.xlabel("TSC time [ms]")
            plt.ylabel("Error [mm]")
            plt.title("Stage3.0 best real-TSC 150 ms trajectory")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.savefig(ctx.paths.analysis / "best_trajectory_rz_vs_time.png", dpi=180)
            plt.close()

            plt.figure(figsize=(10, 4))
            plt.plot(time_ms, velocity, marker="o")
            plt.axhline(float(ctx.cfg["gate"]["terminal_velocity_max_m_per_s"]), linestyle="--", linewidth=1)
            plt.axvspan(absolute_arrival_start, absolute_arrival_end, alpha=0.08)
            plt.xlabel("TSC time [ms]")
            plt.ylabel("R/Z speed [m/s]")
            plt.title("Stage3.0 best trajectory speed")
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(ctx.paths.analysis / "best_trajectory_speed.png", dpi=180)
            plt.close()


def write_stage30_report(
    ctx: Stage30Context,
    *,
    rows: Sequence[dict[str, Any]],
    hofs: dict[str, list[dict[str, Any]]],
    confirmation: dict[str, Any] | None,
) -> Path:
    state = read_json(ctx.paths.state)
    best = best_successful_row(rows)
    lines = [
        "# Stage3.0 extended-horizon tail SQP and MPC-compatible POC",
        "",
        f"- Source Stage2.2 run: `{ctx.source_run}`",
        "- TSC control step: 10 ms",
        "- Episode horizon: 150 ms",
        "- Allowed arrival endpoints: 120, 130, 140, or 150 ms",
        "- Action space: first three validated SVD modes",
        "- Frozen nominal actions: steps 0-8",
        "- Independent optimized controls: steps 9-14 x three modes = 18 variables",
        "- Optimizer: real-TSC finite-difference trust-region SQP",
        "- Hard success is always decided by real TSC",
        "",
        "## Optimization state",
        "",
        f"- Screen complete: {state.get('screen_complete', False)}",
        f"- SQP rounds completed: {state.get('next_sqp_round', 0)}",
        f"- Optimization finished: {state.get('optimization_finished', False)}",
        f"- Stop reason: `{state.get('stop_reason', '')}`",
        f"- Strict fixed-scenario trajectory found: {state.get('strict_gate_found', False)}",
        f"- Controller identification complete: {state.get('controller_identification_complete', False)}",
        f"- Total real-TSC optimization/identification evaluations: {len(rows)}",
        f"- Successful evaluations: {sum(_as_bool(row.get('success'), False) for row in rows)}",
        f"- Precise sustained 30 mm passes: {sum(_as_bool(row.get('strict_gate_pass'), False) for row in rows)}",
        f"- Relaxed sustained 40 mm passes: {sum(_as_bool(row.get('relaxed_gate_pass'), False) for row in rows)}",
    ]
    if best is not None:
        lines.extend(
            [
                "",
                "## Best real-TSC candidate",
                "",
                f"- Candidate: `{best['candidate_id']}`",
                f"- Nominal: `{best['nominal_id']}`",
                f"- Source phase: `{best['phase']}` / `{best['source_type']}`",
                f"- Gate: `{best['gate_label']}`",
                f"- Selected arrival endpoint: {best.get('stage3_0_best_endpoint_ms')} ms",
                f"- Earliest strict arrival: {best.get('stage3_0_earliest_strict_arrival_ms')} ms",
                f"- Sustained R/Z box error through 150 ms: {1000.0 * float(best.get('stage3_0_sustained_box_max_error_m', math.nan)):.3f} mm",
                f"- Endpoint velocity: {float(best.get('stage3_0_endpoint_velocity_m_per_s', math.nan)):.6f} m/s",
                f"- Endpoint late velocity RMS: {float(best.get('stage3_0_endpoint_late_velocity_rms_m_per_s', math.nan)):.6f} m/s",
                f"- Post-arrival velocity RMS: {float(best.get('stage3_0_post_arrival_velocity_rms_m_per_s', math.nan)):.6f} m/s",
                f"- Maximum normalized violation: {100.0 * float(best.get('stage3_0_max_violation', math.nan)):.4f}%",
            ]
        )
    if confirmation is not None:
        lines.extend(["", "## Deterministic confirmation", "", f"- Verdict: `{confirmation.get('verdict')}`"])
    lines.extend(
        [
            "",
            "## MPC-compatible artifact",
            "",
            "`stage3_0_controller/mpc_poc_bundle.json` contains a real-TSC finite-difference tail Jacobian and a regularized batch correction gain.",
            "It is an offline local sensitivity POC. It has not been tested in closed loop, and it is not a deployable PCS controller.",
            "",
            "## Final-task reminder",
            "",
            "The final project objective is not one fixed 150 ms open-loop sequence. The objective is a feedback controller that reaches, brakes, and robustly holds R/Z/Ip across initial-state, target, noise, and model variations.",
            "A confirmed Stage3.0 strict trajectory is only the nominal-trajectory gate before perturbation experiments, behavior cloning, MPC/feedback validation, and eventually bounded residual RL.",
        ]
    )
    report = ctx.paths.run_dir / "STAGE3_0_REPORT.md"
    jsonio.atomic_write_text(report, "\n".join(lines) + "\n")
    return report


def analyze_stage30(ctx: Stage30Context) -> dict[str, Any]:
    rows = aggregate_rows(ctx.paths)
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    write_csv(ctx.paths.analysis / "all_results.csv", rows)
    atomic_write_json(ctx.paths.analysis / "all_results.json", rows)
    hofs = hall_of_fames(rows)
    for name, hall in hofs.items():
        write_csv(ctx.paths.analysis / f"{name}_hall_of_fame.csv", hall[:100])
        atomic_write_json(ctx.paths.analysis / f"{name}_hall_of_fame.json", hall[:100])
    confirmation_path = ctx.paths.confirmations / "stage3_0_verdict.json"
    confirmation = read_json(confirmation_path) if confirmation_path.exists() else None
    generate_stage30_plots(ctx, rows)
    report = write_stage30_report(ctx, rows=rows, hofs=hofs, confirmation=confirmation)
    best = best_successful_row(rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.0",
        "created_utc": utc_timestamp(),
        "source_stage2_2_run": str(ctx.source_run),
        "n_evaluations": len(rows),
        "n_successful": sum(_as_bool(row.get("success"), False) for row in rows),
        "n_strict_gate": sum(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
        "n_relaxed_gate": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in rows),
        "n_unique_candidates": len(unique_rows(rows)),
        "best": best,
        "confirmation_verdict": None if confirmation is None else confirmation.get("verdict"),
        "controller_bundle": str(ctx.paths.controller / "mpc_poc_bundle.json"),
        "online_feedback_validated": False,
        "robustness_validated": False,
        "report": str(report),
    }
    atomic_write_json(ctx.paths.analysis / "stage3_0_analysis_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    return summary


# ---------------------------------------------------------------------------
# Synthetic self-test and public executor
# ---------------------------------------------------------------------------


def _synthetic_context() -> Stage30Context:
    cfg = {
        "target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0},
        "trajectory": {
            "horizon_steps": 15,
            "horizon_ms": 150,
            "source_horizon_steps": 10,
            "n_modes": 3,
            "source_node_steps": [0, 2, 4, 6, 9],
            "tail_variable_steps": [9, 10, 11, 12, 13, 14],
            "frozen_action_steps": list(range(9)),
            "coefficient_lower": [-2.6, -2.6, -0.9],
            "coefficient_upper": [2.6, 2.6, 0.9],
        },
        "gate": {
            "precise_tolerance_m": 0.03,
            "relaxed_tolerance_m": 0.04,
            "required_arrival_streak_steps": 3,
            "allowed_arrival_steps": [12, 13, 14, 15],
            "terminal_velocity_max_m_per_s": 0.1,
            "late_velocity_rms_max_m_per_s": 0.1,
            "late_window_steps": 4,
            "ip_tolerance_a": 10000.0,
        },
        "objective": {
            "non_strict_offset": 1e6,
            "max_violation_weight": 1e5,
            "sum_violation_weight": 4000.0,
            "l2_violation_weight": 1000.0,
            "quality_weights": {
                "position_core": 2.0,
                "velocity_core": 1.5,
                "terminal_ip_core": 0.05,
                "arrival_time_core": 0.15,
                "action_rms": 0.02,
                "delta_action_rms": 0.04,
                "repair": 2.0,
            },
        },
        "screen": {"mode_residual_amplitude": [0.08, 0.08, 0.03], "templates_per_nominal": 12},
        "nominals": {"count": 8},
        "sqp": {
            "probe_delta_by_step_mode": [[0.02, 0.02, 0.008]] * 6,
            "trust_radius_by_step_mode": [[0.1, 0.1, 0.04]] * 6,
            "linear_solver": {
                "softplus_beta": 80.0,
                "delta_l2": 0.05,
                "tail_smoothness": 0.03,
                "max_iterations": 100,
                "profiles": {
                    "balanced": {"position": 1.0, "velocity": 1.0, "tube_excess": 3.0},
                    "position": {"position": 2.0, "velocity": 0.55, "tube_excess": 5.0},
                    "damping": {"position": 0.75, "velocity": 2.2, "tube_excess": 2.0},
                },
            },
        },
    }
    modes = np.zeros((14, 3), dtype=float)
    modes[:3, :3] = np.eye(3)
    source_modes = np.linspace(0.4, -0.2, 30).reshape(10, 3)
    nominals = [
        {
            "nominal_id": "nominal_test",
            "source_candidate_id": "source_test",
            "category": "test",
            "mode_coefficients_100ms": source_modes.tolist(),
        }
    ]
    paths = Stage30Paths.from_run_dir(Path("/tmp/stage3_0_synthetic"))
    return Stage30Context(
        cfg=cfg,
        train_cfg={},
        env_cfg={
            "dt_ms": 10,
            "min_current_a_display_order": [-400.0] * 14,
            "max_current_a_display_order": [400.0] * 14,
        },
        paths=paths,
        source_run=Path("/tmp/source"),
        modes_tsc=modes,
        initial_currents_tsc=np.zeros(14),
        max_delta_a=3.0,
        min_current_tsc=np.full(14, -400.0),
        max_current_tsc=np.full(14, 400.0),
        tail_steps=(9, 10, 11, 12, 13, 14),
        coefficient_lower=np.tile(np.asarray([-2.6, -2.6, -0.9]), 6),
        coefficient_upper=np.tile(np.asarray([2.6, 2.6, 0.9]), 6),
        source_interpolation=s2.build_interpolation_matrix(10, np.asarray([0, 2, 4, 6, 9], dtype=float)),
        nominals=nominals,
    )


def _synthetic_result(ctx: Stage30Context, *, leave_after_arrival: bool = False) -> dict[str, Any]:
    rows = []
    for step in range(16):
        if step <= 10:
            r_error, z_error = -0.045, 0.045
        else:
            r_error, z_error = -0.020, 0.020
        if leave_after_arrival and step >= 13:
            r_error, z_error = -0.045, 0.045
        rows.append(
            {
                "step_index": step,
                "time_ms": 1100 + 10 * step,
                "R": ctx.cfg["target"]["R"] + r_error,
                "Z": ctx.cfg["target"]["Z"] + z_error,
                "Ip": ctx.cfg["target"]["Ip"] + 500.0,
                "currents_a_tsc": [0.0] * 14,
                "currents_a_display": [0.0] * 14,
                "action_norm_tsc": [0.0] * 14,
                "action_norm_display": [0.0] * 14,
                "abnormal": False,
            }
        )
    return {"experiment_id": "synthetic", "success": True, "failure_reason": "", "trajectory": rows}


def synthetic_stage30_test() -> dict[str, Any]:
    ctx = _synthetic_context()
    nominal = ctx.nominals[0]
    templates = screen_tail_templates(ctx, nominal)
    assert len(templates) == 12
    assert len({_vector_key(nominal["nominal_id"], tail) for _, tail in templates}) == 12
    decoded = decode_tail_sequence(ctx, nominal, templates[0][1])
    assert np.asarray(decoded["mode_coefficients"]).shape == (15, 3)
    assert np.allclose(
        np.asarray(decoded["mode_coefficients"])[0:9],
        np.asarray(nominal["mode_coefficients_100ms"])[0:9],
    )
    good = stage30_metrics(ctx, _synthetic_result(ctx), decoded)
    assert good["strict_gate_pass"]
    assert good["stage3_0_earliest_strict_arrival_step"] == 15
    bad = stage30_metrics(ctx, _synthetic_result(ctx, leave_after_arrival=True), decoded)
    assert not bad["strict_gate_pass"]
    feature = trajectory_feature_vector(ctx, _synthetic_result(ctx))
    assert feature.shape == (30,)
    unpacked = unpack_feature_vector(feature)
    assert all(value.shape == (6,) for value in unpacked.values())
    jsonio.assert_json_finite(good, context="Stage3.0 synthetic metrics")
    return {
        "screen_templates": len(templates),
        "frozen_first_nine_actions": True,
        "extended_horizon_gate_pass": True,
        "post_arrival_persistence_rejection": True,
        "feature_dimension": int(feature.shape[0]),
    }


def execute(
    *,
    command: str,
    config_path: str | Path,
    source_stage2_2_run: str | Path | None,
    run_dir: str | Path | None,
    backend: str,
    no_resume: bool,
) -> Any:
    if command == "self-test":
        result = synthetic_stage30_test()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    ctx = load_stage30_config(
        config_path,
        source_stage2_2_run=source_stage2_2_run,
        run_dir_override=run_dir,
    )
    initialize_stage30_run(ctx)
    load_or_initialize_state(ctx, no_resume=no_resume)
    resume = not no_resume
    if command == "prepare":
        payload = {
            "stage": "Stage3.0",
            "run_dir": str(ctx.paths.run_dir),
            "source_stage2_2_run": str(ctx.source_run),
            "nominal_count": len(ctx.nominals),
            "horizon_steps": 15,
            "tail_variables": 18,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return payload
    if command == "screen":
        return run_screen(ctx, backend=backend, resume=resume)
    if command == "round":
        return run_one_sqp_round(ctx, backend=backend, resume=resume)
    if command == "optimize":
        return run_optimization(ctx, backend=backend, resume=resume)
    if command == "identify":
        return run_controller_identification(ctx, backend=backend, resume=resume)
    if command == "confirm":
        return run_confirmation(ctx, backend=backend, resume=resume)
    if command == "analyze":
        return analyze_stage30(ctx)
    if command == "all":
        run_optimization(ctx, backend=backend, resume=resume)
        if bool(ctx.cfg["controller_identification"].get("enabled", True)):
            run_controller_identification(ctx, backend=backend, resume=resume)
        run_confirmation(ctx, backend=backend, resume=resume)
        return analyze_stage30(ctx)
    raise ValueError(f"Unsupported Stage3.0 command {command!r}")
