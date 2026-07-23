"""Stage3.1 adaptive real-TSC SQP and causal-feedback proof of concept.

Stage3.1 is deliberately an overlay on the complete Stage3.0 implementation.
It reuses the validated TSC environment, first-three-SVD-mode decoder, strict
120--150 ms gate, Ray evaluator, workspace cleanup, and Stage3.0 source
catalog.  It changes only what the Stage3.0 evidence says must change:

* start from the completed Stage3.0 run instead of repeating its 96-run screen;
* expose steps 8--14 (21 mode coefficients), freezing only steps 0--7;
* use measured trust-region ratios to expand/hold/shrink each center separately;
* keep a second nominal family during the first two rounds;
* test 0.5x, 1.0x, and 1.5x real-TSC SQP steps;
* identify a dimensionless, truncated-SVD/ridge 35x21 local model;
* export time-indexed causal gains and run a limited real-TSC feedback POC.

The hard 30 mm / 0.10 m/s / Ip gate is unchanged.  The feedback POC is not a
robustness claim and is never reported as the final controller.
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
from typing import Any, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as jsonio
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_0_tail_sqp as s30
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STATE_FILENAME = "stage3_1_state.json"
MANIFEST_FILENAME = "stage3_1_manifest.json"
SOURCE_CATALOG_FILENAME = "source_stage3_0_catalog.json"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_json(path: Path | str) -> Any:
    return jsonio.read_json(Path(path))


def read_json_gz(path: Path | str) -> Any:
    return jsonio.read_json_gz(Path(path))


def atomic_write_json(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json(Path(path), _json_safe(payload))


def atomic_write_json_gz(path: Path, payload: Any) -> None:
    jsonio.atomic_write_json_gz(Path(path), _json_safe(payload))


def _json_safe(value: Any, path: str = "$") -> Any:
    """Convert numpy/path values and reject non-finite JSON numbers early."""
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
        return {str(k): _json_safe(v, f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v, f"{path}[{i}]") for i, v in enumerate(value)]
    return value


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


def _vector(value: Any, expected: int = 21) -> np.ndarray:
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


def vector_digest(vector: np.ndarray, prefix: str = "s31") -> str:
    rounded = np.round(np.asarray(vector, dtype=float).reshape(-1), 10)
    return f"{prefix}_{hashlib.sha256(rounded.tobytes()).hexdigest()[:16]}"


def _result_key(row: dict[str, Any]) -> str:
    return vector_digest(_vector(row["control_vector"]), "v21")


def _best_key(row: dict[str, Any]) -> tuple[float, float, float, float, str]:
    strict_rank = 0.0 if _as_bool(row.get("strict_gate_pass"), False) else 1.0
    return (
        strict_rank,
        _finite(row.get("stage3_1_max_violation"), 1e12),
        _finite(row.get("stage3_1_sum_violation"), 1e12),
        _finite(row.get("stage3_1_quality"), 1e12),
        str(row.get("candidate_id", "")),
    )


def _dedupe_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not _as_bool(row.get("success"), False):
            continue
        try:
            key = _result_key(row)
        except Exception:
            continue
        if key not in best or _best_key(row) < _best_key(best[key]):
            best[key] = copy.deepcopy(row)
    return sorted(best.values(), key=_best_key)


@dataclass(frozen=True)
class Stage31Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_catalog: Path
    phases: Path
    evaluations: Path
    confirmations: Path
    analysis: Path
    best: Path
    controller: Path
    feedback: Path
    source_reference: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage31Paths":
        return cls(
            run_dir=run_dir,
            state=run_dir / STATE_FILENAME,
            manifest=run_dir / MANIFEST_FILENAME,
            source_catalog=run_dir / SOURCE_CATALOG_FILENAME,
            phases=run_dir / "stage3_1_phases",
            evaluations=run_dir / "stage3_1_evaluations",
            confirmations=run_dir / "stage3_1_confirmations",
            analysis=run_dir / "stage3_1_analysis",
            best=run_dir / "stage3_1_best",
            controller=run_dir / "stage3_1_controller",
            feedback=run_dir / "stage3_1_feedback_poc",
            source_reference=run_dir / "source_stage3_0_reference",
        )


@dataclass
class Stage31Context:
    cfg: dict[str, Any]
    train_cfg: dict[str, Any]
    env_cfg: dict[str, Any]
    paths: Stage31Paths
    source_stage30_run: Path
    source_stage22_run: Path
    base30: s30.Stage30Context
    modes_tsc: np.ndarray
    initial_currents_tsc: np.ndarray
    max_delta_a: float
    min_current_tsc: np.ndarray
    max_current_tsc: np.ndarray
    variable_steps: tuple[int, ...]
    coefficient_lower: np.ndarray
    coefficient_upper: np.ndarray
    nominals: list[dict[str, Any]]
    source_rows: list[dict[str, Any]]
    source_fingerprint: dict[str, Any] | None = None


_REQUIRED_STAGE30 = (
    "stage3_0_config.resolved.json",
    "stage3_0_manifest.json",
    "stage3_0_state.json",
    "stage3_0_analysis/all_results.json",
    "stage3_0_analysis/stage3_0_analysis_summary.json",
    "stage3_0_controller/mpc_poc_bundle.json",
    "env_config.resolved.json",
    "train_config.resolved.json",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _source_inventory(
    source30: Path,
    source22: Path,
    raw_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Fingerprint the exact Stage3.0 catalog and its key Stage2.2 inputs.

    Stage3.1 resumes expensive real-TSC waves.  A path-only check is not enough:
    silently replacing or editing the source run could mix incompatible local
    Jacobians and control vectors.  The inventory is therefore content-based and
    includes every successful Stage3.0 result referenced by the 420-row catalog.
    """
    entries: list[dict[str, Any]] = []
    requested: dict[str, Path] = {}
    for relative in _REQUIRED_STAGE30:
        requested[f"stage3_0/{relative}"] = source30 / relative
    for row in raw_rows:
        if not _as_bool(row.get("success"), False):
            continue
        relative = str(row.get("result_relpath", "")).strip()
        if not relative:
            raise RuntimeError(f"successful Stage3.0 row lacks result_relpath: {row.get('candidate_id')}")
        requested[f"stage3_0/{relative}"] = source30 / relative
    for relative in (
        "stage2_2_config.resolved.json",
        "stage2_2_manifest.json",
        "stage2_2_analysis/all_generation_results.json",
        "stage2_2_analysis/corner_hall_of_fame.json",
        "stage2_2_analysis/speed_safe_hall_of_fame.json",
        "stage2_2_analysis/gate_hall_of_fame.json",
    ):
        requested[f"stage2_2/{relative}"] = source22 / relative
    initial_current_candidates = [
        source22 / "stage2_2_best/best_corner_tsc_result.json.gz",
        source22 / "best/best_tsc_result.json.gz",
        *sorted((source22 / "stage2_2_evaluations").glob("gen_*/*.json.gz"))[:1],
    ]
    initial_current_path = next((candidate for candidate in initial_current_candidates if candidate.exists()), None)
    if initial_current_path is None:
        raise FileNotFoundError("Stage2.2 source has no result from which initial currents can be recovered")
    requested[f"stage2_2/{initial_current_path.relative_to(source22)}"] = initial_current_path

    missing = [label for label, path in requested.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Stage3.1 source inventory is incomplete; missing " + ", ".join(missing[:8])
            + (" ..." if len(missing) > 8 else "")
        )
    total_bytes = 0
    for label, path in sorted(requested.items()):
        size = int(path.stat().st_size)
        total_bytes += size
        entries.append({"path": label, "size_bytes": size, "sha256": _sha256_file(path)})
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "algorithm": "sha256",
        "digest": hashlib.sha256(canonical).hexdigest(),
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "entries": entries,
    }


def resolve_source_stage30_run(value: str | Path | None) -> Path:
    if value is None or not str(value).strip():
        value = os.environ.get("SOURCE_STAGE3_0_RUN", "").strip()
    if not value:
        raise ValueError(
            "A completed Stage3.0 run is required. Pass --source-stage3-0-run or set SOURCE_STAGE3_0_RUN."
        )
    run_dir = Path(value).expanduser().resolve()
    missing = [str(run_dir / rel) for rel in _REQUIRED_STAGE30 if not (run_dir / rel).exists()]
    if missing:
        raise FileNotFoundError("Incomplete Stage3.0 source run: " + ", ".join(missing))
    return run_dir


def _find_under_project(project_dir: Path, dirname: str, basename: str) -> Path | None:
    direct = project_dir / dirname / basename
    if direct.exists():
        return direct.resolve()
    candidates = sorted((project_dir / dirname).glob(f"**/{basename}")) if (project_dir / dirname).exists() else []
    return candidates[-1].resolve() if candidates else None


def resolve_source_stage22_from_stage30(source30: Path, project_dir: Path) -> Path:
    manifest = read_json(source30 / "stage3_0_manifest.json")
    raw = str(manifest.get("source_stage2_2_run", "")).strip()
    if raw:
        path = Path(raw).expanduser()
        if path.exists():
            return path.resolve()
        fallback = _find_under_project(project_dir, "stage2_2_runs", path.name)
        if fallback is not None:
            return fallback
    env = os.environ.get("SOURCE_STAGE2_2_RUN", "").strip()
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()
    raise FileNotFoundError(
        "Cannot resolve the Stage2.2 source referenced by Stage3.0. Preserve stage2_2_runs/ or set SOURCE_STAGE2_2_RUN."
    )


def validate_stage31_config(cfg: dict[str, Any]) -> None:
    trajectory = cfg["trajectory"]
    if int(trajectory.get("horizon_steps", -1)) != 15 or int(trajectory.get("horizon_ms", -1)) != 150:
        raise ValueError("Stage3.1 is fixed to 15 steps / 150 ms")
    if int(trajectory.get("n_modes", -1)) != 3:
        raise ValueError("Stage3.1 requires exactly three validated SVD modes")
    if list(trajectory.get("variable_steps", [])) != list(range(8, 15)):
        raise ValueError("Stage3.1 variable_steps must be [8,9,10,11,12,13,14]")
    if list(trajectory.get("frozen_action_steps", [])) != list(range(8)):
        raise ValueError("Stage3.1 must freeze steps 0-7")
    lower = np.asarray(trajectory.get("coefficient_lower", []), dtype=float)
    upper = np.asarray(trajectory.get("coefficient_upper", []), dtype=float)
    if lower.shape != (3,) or upper.shape != (3,) or not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)) or np.any(lower >= upper):
        raise ValueError("trajectory coefficient bounds must be finite three-vectors with lower < upper")

    sqp = cfg["sqp"]
    if int(sqp.get("centers_per_round", 0)) != 2 or int(sqp.get("variables", 0)) != 21:
        raise ValueError("Stage3.1 requires two centers and 21 variables")
    if int(sqp.get("max_rounds", 0)) < 1:
        raise ValueError("sqp.max_rounds must be positive")
    if int(sqp.get("max_rounds_without_improvement", -1)) < 1:
        raise ValueError("sqp.max_rounds_without_improvement must be at least one")
    if int(sqp.get("force_distinct_nominal_rounds", -1)) < 0:
        raise ValueError("sqp.force_distinct_nominal_rounds must be non-negative")
    for key in ("probe_delta_by_step_mode", "trust_radius_by_step_mode"):
        matrix = np.asarray(sqp.get(key, []), dtype=float)
        if matrix.shape != (7, 3) or np.any(matrix <= 0.0) or not np.all(np.isfinite(matrix)):
            raise ValueError(f"sqp.{key} must be a positive finite 7x3 matrix")
    trust_min = float(sqp.get("minimum_trust_scale", math.nan))
    trust_initial = float(sqp.get("initial_trust_scale", math.nan))
    trust_max = float(sqp.get("maximum_trust_scale", math.nan))
    if not all(math.isfinite(x) and x > 0.0 for x in (trust_min, trust_initial, trust_max)) or not trust_min <= trust_initial <= trust_max:
        raise ValueError("trust scales must be positive and minimum <= initial <= maximum")
    if float(sqp.get("trust_expand_factor", 0.0)) <= 1.0:
        raise ValueError("trust_expand_factor must be greater than one")
    if not 0.0 < float(sqp.get("trust_hold_factor", 0.0)) <= 1.0:
        raise ValueError("trust_hold_factor must lie in (0,1]")
    for key in ("trust_shrink_poor_ratio", "trust_shrink_rejected"):
        if not 0.0 < float(sqp.get(key, 0.0)) < 1.0:
            raise ValueError(f"{key} must lie in (0,1)")
    poor = float(sqp.get("ratio_poor_threshold", math.nan))
    expand = float(sqp.get("ratio_expand_threshold", math.nan))
    if not (math.isfinite(poor) and math.isfinite(expand) and 0.0 <= poor < expand):
        raise ValueError("trust ratio thresholds must satisfy 0 <= poor < expand")
    boundary = float(sqp.get("boundary_fraction_for_expand", math.nan))
    if not math.isfinite(boundary) or not 0.0 <= boundary <= 1.0:
        raise ValueError("boundary_fraction_for_expand must lie in [0,1]")
    step_scales = sorted({float(value) for value in sqp.get("proposal_step_scales", [])})
    if step_scales != [0.5, 1.0, 1.5]:
        raise ValueError("proposal_step_scales must be exactly [0.5,1.0,1.5]")

    linear_solver = sqp.get("linear_solver", {})
    profiles = linear_solver.get("profiles", {})
    if set(profiles) != {"balanced", "position", "damping"}:
        raise ValueError("linear solver profiles must be balanced, position, and damping")
    requests = list(linear_solver.get("proposal_requests", []))
    if len(requests) != int(sqp.get("proposals_per_center", 0)):
        raise ValueError("proposal_requests length must equal proposals_per_center")
    if int(sqp.get("proposals_per_center", 0)) != 15:
        raise ValueError("Stage3.1 requires 15 SQP proposals per center")
    for request in requests:
        if int(request.get("endpoint_step", -1)) not in {12, 13, 14, 15}:
            raise ValueError("SQP proposal endpoint must be 12, 13, 14, or 15")
        if str(request.get("profile")) not in profiles:
            raise ValueError("SQP proposal references an unknown profile")
        if float(request.get("step_scale", math.nan)) not in {0.5, 1.0, 1.5}:
            raise ValueError("SQP proposal step scale must be 0.5, 1.0, or 1.5")

    identification = cfg["controller_identification"]
    ident = np.asarray(identification.get("probe_delta_by_step_mode", []), dtype=float)
    if ident.shape != (7, 3) or np.any(ident <= 0.0) or not np.all(np.isfinite(ident)):
        raise ValueError("controller identification delta must be a positive finite 7x3 matrix")
    if not 0 <= int(identification.get("maximum_recenter_passes", -1)) <= 1:
        raise ValueError("controller identification supports zero or one recenter pass")
    if not 1 <= int(identification.get("minimum_reliable_columns", 0)) <= 21:
        raise ValueError("minimum_reliable_columns must lie in [1,21]")

    gate = cfg["gate"]
    if list(gate.get("allowed_arrival_steps", [])) != [12, 13, 14, 15]:
        raise ValueError("allowed arrival steps must remain [12,13,14,15]")
    if int(gate.get("required_arrival_streak_steps", 0)) != 3:
        raise ValueError("three-sample arrival streak is required")
    if not math.isclose(float(gate.get("precise_tolerance_m", math.nan)), 0.03, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Stage3.1 precise tolerance must remain 30 mm")
    if not math.isclose(float(gate.get("terminal_velocity_max_m_per_s", math.nan)), 0.10, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Stage3.1 terminal velocity limit must remain 0.10 m/s")
    if not math.isclose(float(gate.get("late_velocity_rms_max_m_per_s", math.nan)), 0.10, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Stage3.1 late velocity RMS limit must remain 0.10 m/s")
    if not math.isclose(float(gate.get("ip_tolerance_a", math.nan)), 10000.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Stage3.1 Ip tolerance must remain 10 kA")

    mpc = cfg["mpc"]
    scales_cfg = mpc.get("output_scales", {})
    required_scale_keys = {"R_m", "Z_m", "vR_m_per_s", "vZ_m_per_s", "Ip_A"}
    if set(scales_cfg) != required_scale_keys or any(float(scales_cfg[key]) <= 0.0 for key in required_scale_keys):
        raise ValueError("mpc.output_scales must contain five positive gate-scale values")
    if sorted(float(value) for value in mpc.get("controller_scales", [])) != [0.0, 0.5, 1.0]:
        raise ValueError("mpc.controller_scales must be exactly [0.0,0.5,1.0]")
    scenarios = list(mpc.get("scenarios", []))
    if len(scenarios) != 8 or len(set(map(str, scenarios))) != 8:
        raise ValueError("Stage3.1 feedback POC requires eight unique scenarios")
    known_scenarios = {
        "nominal", "target_R_plus", "target_R_minus", "target_Z_plus",
        "target_Z_minus", "target_RZ_plus", "disturbance_mode1_plus",
        "disturbance_mode1_minus",
    }
    if set(map(str, scenarios)) != known_scenarios:
        raise ValueError("mpc.scenarios differ from the fixed limited feedback POC design")
    feedback_limit = np.asarray(mpc.get("per_step_feedback_limit_by_mode", []), dtype=float)
    if feedback_limit.shape != (3,) or np.any(feedback_limit <= 0.0) or not np.all(np.isfinite(feedback_limit)):
        raise ValueError("per-step feedback limits must be a positive finite three-vector")


def _resolve_storage(value: Any, project_dir: Path) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return str(path.resolve(strict=False))


def _source_row_to_stage31(base30: s30.Stage30Context, source30: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    if not _as_bool(row.get("success"), False):
        return None
    try:
        nominal = s30.nominal_by_id(base30, str(row["nominal_id"]))
        decoded = s30.decode_tail_sequence(base30, nominal, np.asarray(row["tail_vector"], dtype=float))
        control = np.asarray(decoded["mode_coefficients"], dtype=float)[8:15].reshape(-1)
    except Exception:
        return None
    out = copy.deepcopy(row)
    out.update(
        {
            "stage": "Stage3.0-source",
            "control_vector": control.tolist(),
            "source_stage3_0_candidate_id": str(row.get("candidate_id", "")),
            "source_result_path": str((source30 / str(row["result_relpath"])).resolve()),
            "result_relpath": None,
        }
    )
    for key, value in list(row.items()):
        if key.startswith("stage3_0_"):
            out["stage3_1_" + key[len("stage3_0_"):]] = copy.deepcopy(value)
    return out


def load_stage31_config(
    config_path: str | Path,
    *,
    source_stage30_run: str | Path | None,
    run_dir_override: str | Path | None,
) -> Stage31Context:
    config_path = Path(config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    cfg = jsonio.deep_replace_strings(
        read_json(config_path),
        {"PROJECT_DIR": str(project_dir), "TSC_ALL_ROOT": str(project_dir.parent)},
    )
    validate_stage31_config(cfg)
    if run_dir_override is None:
        root = jsonio.resolve_path(cfg.get("output_root", "stage3_1_runs"), base_dir=project_dir)
        run_dir = root / f"{cfg.get('run_name','stage3_1_adaptive_sqp')}_{utc_timestamp()}"
    else:
        run_dir = jsonio.resolve_path(run_dir_override, base_dir=project_dir)
    source30 = resolve_source_stage30_run(source_stage30_run)
    source22 = resolve_source_stage22_from_stage30(source30, project_dir)

    # Reconstruct the exact Stage3.0 physical context from its resolved config
    # and underlying Stage2.2 run, but direct all future worker config paths to
    # the new Stage3.1 run.
    base30 = s30.load_stage30_config(
        source30 / "stage3_0_config.resolved.json",
        source_stage2_2_run=source22,
        run_dir_override=run_dir,
    )
    source_cfg = read_json(source30 / "stage3_0_config.resolved.json")
    for key in ("R", "Z", "Ip"):
        if not math.isclose(float(cfg["target"][key]), float(source_cfg["target"][key]), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Stage3.1 target {key} differs from Stage3.0")
    for key in (
        "precise_tolerance_m",
        "relaxed_tolerance_m",
        "required_arrival_streak_steps",
        "terminal_velocity_max_m_per_s",
        "late_velocity_rms_max_m_per_s",
        "ip_tolerance_a",
    ):
        if not math.isclose(float(cfg["gate"][key]), float(source_cfg["gate"][key]), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Stage3.1 hard gate {key} differs from Stage3.0")

    env_cfg = copy.deepcopy(base30.env_cfg)
    train_cfg = copy.deepcopy(base30.train_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg.get("runtime", {}).get("tsc_timeout_s", env_cfg.get("tsc_timeout_s", 180.0)))
    storage = cfg.get("storage", {})
    workspace = _resolve_storage(os.environ.get("STAGE3_1_TSC_WORKSPACE_ROOT") or storage.get("tsc_workspace_root"), project_dir)
    run_root = _resolve_storage(os.environ.get("STAGE3_1_TSC_RUN_ROOT") or storage.get("tsc_run_root"), project_dir)
    if workspace:
        env_cfg["tsc_workspace_root"] = workspace
    if run_root:
        env_cfg["run_root"] = run_root
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg["env_config"] = str(run_dir / "env_config.resolved.json")
    train_cfg.setdefault("episode", {})["max_episode_steps"] = 15
    train_cfg.setdefault("target", {}).update(copy.deepcopy(cfg["target"]))

    raw_rows = read_json(source30 / "stage3_0_analysis/all_results.json")
    if not isinstance(raw_rows, list):
        raise TypeError("Stage3.0 all_results.json must contain a list")
    source_fingerprint = _source_inventory(source30, source22, raw_rows)
    source_rows = [converted for row in raw_rows if (converted := _source_row_to_stage31(base30, source30, row)) is not None]
    missing_source_results = [
        str(row.get("source_result_path"))
        for row in source_rows
        if not Path(str(row.get("source_result_path", ""))).exists()
    ]
    if missing_source_results:
        raise FileNotFoundError(
            "Stage3.0 catalog references missing raw results: " + ", ".join(missing_source_results[:5])
        )
    minimum = int(cfg.get("source", {}).get("minimum_successful_stage3_0_rows", 300))
    if len(source_rows) < minimum:
        raise RuntimeError(f"Only {len(source_rows)} usable Stage3.0 rows; expected at least {minimum}")
    state30 = read_json(source30 / "stage3_0_state.json")
    if bool(cfg.get("source", {}).get("require_completed_optimization", True)) and not state30.get("optimization_finished"):
        raise RuntimeError("Stage3.0 optimization is not complete")
    if bool(cfg.get("source", {}).get("require_controller_identification", True)) and not state30.get("controller_identification_complete"):
        raise RuntimeError("Stage3.0 controller identification is not complete")

    variable_steps = tuple(int(x) for x in cfg["trajectory"]["variable_steps"])
    low_mode = np.asarray(cfg["trajectory"]["coefficient_lower"], dtype=float)
    high_mode = np.asarray(cfg["trajectory"]["coefficient_upper"], dtype=float)
    lower = np.tile(low_mode, len(variable_steps))
    upper = np.tile(high_mode, len(variable_steps))
    return Stage31Context(
        cfg=cfg,
        train_cfg=train_cfg,
        env_cfg=env_cfg,
        paths=Stage31Paths.from_run_dir(run_dir),
        source_stage30_run=source30,
        source_stage22_run=source22,
        base30=base30,
        modes_tsc=np.asarray(base30.modes_tsc, dtype=float),
        initial_currents_tsc=np.asarray(base30.initial_currents_tsc, dtype=float),
        max_delta_a=float(base30.max_delta_a),
        min_current_tsc=np.asarray(base30.min_current_tsc, dtype=float),
        max_current_tsc=np.asarray(base30.max_current_tsc, dtype=float),
        variable_steps=variable_steps,
        coefficient_lower=lower,
        coefficient_upper=upper,
        nominals=copy.deepcopy(base30.nominals),
        source_rows=source_rows,
        source_fingerprint=source_fingerprint,
    )


def initialize_stage31_run(ctx: Stage31Context) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.phases,
        ctx.paths.evaluations,
        ctx.paths.confirmations,
        ctx.paths.analysis,
        ctx.paths.best,
        ctx.paths.controller,
        ctx.paths.feedback,
        ctx.paths.source_reference,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.run_dir / "stage3_1_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.run_dir / "train_config.resolved.json", ctx.train_cfg)
    atomic_write_json(ctx.paths.run_dir / "env_config.resolved.json", ctx.env_cfg)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "created_utc": utc_timestamp(),
        "source_stage3_0_run": str(ctx.source_stage30_run),
        "source_stage2_2_run": str(ctx.source_stage22_run),
        "source_stage3_0_rows": len(ctx.source_rows),
        "source_fingerprint": None if ctx.source_fingerprint is None else {
            key: value for key, value in ctx.source_fingerprint.items() if key != "entries"
        },
        "target": copy.deepcopy(ctx.cfg["target"]),
        "horizon_steps": 15,
        "horizon_ms": 150,
        "variable_steps": list(ctx.variable_steps),
        "frozen_action_steps": list(ctx.cfg["trajectory"]["frozen_action_steps"]),
        "parameter_dimension": 21,
        "hard_gate_changed_from_stage3_0": False,
        "final_task": "robust causal feedback control across initial states and targets",
        "robustness_validated": False,
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        if Path(old["source_stage3_0_run"]).resolve() != ctx.source_stage30_run:
            raise ValueError("Existing Stage3.1 run points to a different Stage3.0 source")
        old_digest = str((old.get("source_fingerprint") or {}).get("digest", ""))
        new_digest = "" if ctx.source_fingerprint is None else str(ctx.source_fingerprint.get("digest", ""))
        if old_digest and new_digest and old_digest != new_digest:
            raise ValueError("Stage3.0/Stage2.2 source content changed since this Stage3.1 run was prepared")
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.source_catalog.exists():
        atomic_write_json(ctx.paths.source_catalog, ctx.source_rows)
    if ctx.source_fingerprint is not None:
        inventory_path = ctx.paths.source_reference / "source_content_inventory.json"
        if inventory_path.exists():
            previous_inventory = read_json(inventory_path)
            if str(previous_inventory.get("digest", "")) != str(ctx.source_fingerprint.get("digest", "")):
                raise ValueError("Stored Stage3.1 source inventory differs from current source content")
        else:
            atomic_write_json(inventory_path, ctx.source_fingerprint)
    for relative in (
        "stage3_0_config.resolved.json",
        "stage3_0_manifest.json",
        "stage3_0_state.json",
        "stage3_0_analysis/stage3_0_analysis_summary.json",
        "stage3_0_analysis/minimax_hall_of_fame.json",
        "stage3_0_analysis/speed_safe_hall_of_fame.json",
        "stage3_0_analysis/relaxed_hall_of_fame.json",
        "stage3_0_controller/mpc_poc_bundle.json",
        "STAGE3_0_REPORT.md",
    ):
        src = ctx.source_stage30_run / relative
        if src.exists():
            dst = ctx.paths.source_reference / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)


def nominal_by_id(ctx: Stage31Context, nominal_id: str) -> dict[str, Any]:
    return s30.nominal_by_id(ctx.base30, nominal_id)


def clip_control(ctx: Stage31Context, vector: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(vector, dtype=float).reshape(-1), ctx.coefficient_lower, ctx.coefficient_upper)


def decode_control_sequence(ctx: Stage31Context, nominal: dict[str, Any], control_vector: np.ndarray) -> dict[str, Any]:
    control = clip_control(ctx, control_vector)
    coefficients = np.zeros((15, 3), dtype=float)
    source_coefficients = np.asarray(nominal["mode_coefficients_100ms"], dtype=float)
    coefficients[:10] = source_coefficients
    coefficients[10:] = source_coefficients[-1]
    coefficients[np.asarray(ctx.variable_steps, dtype=int)] = control.reshape(len(ctx.variable_steps), 3)
    raw = coefficients @ ctx.modes_tsc.T
    action = np.zeros_like(raw)
    currents = np.zeros((16, 14), dtype=float)
    currents[0] = ctx.initial_currents_tsc
    scales: list[float] = []
    excess: list[float] = []
    for step in range(15):
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
        "control_vector": control,
        "mode_coefficients": coefficients,
        "action_raw_tsc": raw,
        "action_norm_tsc": action,
        "action_norm_display": s30.tsc_matrix_to_display(action),
        "currents_a_tsc": currents,
        "currents_a_display": s30.tsc_matrix_to_display(currents),
        "per_step_repair_scale": np.asarray(scales, dtype=float),
        "saturation_excess": np.asarray(excess, dtype=float),
    }


def stage31_metrics(ctx: Stage31Context, result: dict[str, Any], decoded: dict[str, Any] | None) -> dict[str, Any]:
    proxy = SimpleNamespace(cfg=ctx.cfg, env_cfg=ctx.env_cfg)
    base_metrics = dict(s30.stage30_metrics(proxy, result, decoded))
    for key, value in list(base_metrics.items()):
        if key.startswith("stage3_0_"):
            base_metrics["stage3_1_" + key[len("stage3_0_"):]] = copy.deepcopy(value)
    base_metrics["stage"] = "Stage3.1"
    return base_metrics


def feature_names() -> list[str]:
    names: list[str] = []
    for prefix in ("R_error_m", "Z_error_m", "vR_m_per_s", "vZ_m_per_s", "Ip_error_A"):
        for state in range(9, 16):
            names.append(f"{prefix}_state{state}")
    return names


def trajectory_feature_vector(ctx: Stage31Context, result: dict[str, Any]) -> np.ndarray:
    trajectory = result.get("trajectory", [])
    if len(trajectory) != 16:
        raise ValueError(f"expected 16 states, found {len(trajectory)}")
    target = np.asarray([ctx.cfg["target"]["R"], ctx.cfg["target"]["Z"], ctx.cfg["target"]["Ip"]], dtype=float)
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("trajectory contains non-finite state")
    error = y - target[None, :]
    dt_s = float(ctx.env_cfg["dt_ms"]) / 1000.0
    velocity = np.zeros((16, 2), dtype=float)
    velocity[1:] = np.diff(y[:, :2], axis=0) / dt_s
    states = np.arange(9, 16, dtype=int)
    return np.concatenate(
        [
            error[states, 0],
            error[states, 1],
            velocity[states, 0],
            velocity[states, 1],
            error[states, 2],
        ]
    )


def unpack_feature(vector: np.ndarray) -> dict[str, np.ndarray]:
    vector = np.asarray(vector, dtype=float).reshape(35)
    return {
        "R": vector[0:7],
        "Z": vector[7:14],
        "vR": vector[14:21],
        "vZ": vector[21:28],
        "Ip": vector[28:35],
    }

# ---------------------------------------------------------------------------
# Candidate records, persistence, and source-aware result loading
# ---------------------------------------------------------------------------


def candidate_row(
    ctx: Stage31Context,
    *,
    nominal: dict[str, Any],
    control_vector: np.ndarray,
    source_name: str,
    source_type: str,
    phase_name: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    control = clip_control(ctx, control_vector)
    row: dict[str, Any] = {
        "stage": "Stage3.1",
        "phase": phase_name,
        "candidate_id": vector_digest(control, "proposal"),
        "nominal_id": str(nominal["nominal_id"]),
        "source_candidate_id": str(nominal.get("source_candidate_id", "")),
        "nominal_category": str(nominal.get("category", "unknown")),
        "source_name": source_name,
        "source_type": source_type,
        "control_vector": control.tolist(),
    }
    if extra:
        row.update(copy.deepcopy(extra))
    return row


def specs_from_manifest(ctx: Stage31Context, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in manifest["candidates"]:
        candidate_id = str(row["candidate_id"])
        if not candidate_id or candidate_id in seen_ids:
            raise ValueError(f"empty/duplicate Stage3.1 candidate id: {candidate_id!r}")
        seen_ids.add(candidate_id)
        nominal = nominal_by_id(ctx, str(row["nominal_id"]))
        control = _vector(row["control_vector"])
        decoded = decode_control_sequence(ctx, nominal, control)
        spec = {
            "kind": "stage3_1_candidate",
            "experiment_id": candidate_id,
            "candidate_id": candidate_id,
            "phase": str(manifest["phase"]),
            "population_index": int(row["population_index"]),
            "nominal_id": str(row["nominal_id"]),
            "source_candidate_id": str(row.get("source_candidate_id", "")),
            "nominal_category": str(row.get("nominal_category", "unknown")),
            "source_name": str(row.get("source_name", "unknown")),
            "source_type": str(row.get("source_type", "unknown")),
            "horizon_steps": 15,
            "control_vector": control.tolist(),
            "mode_coefficients": decoded["mode_coefficients"].tolist(),
            "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
            "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
        }
        for key, value in row.items():
            if key.startswith(("probe_", "sqp_", "predicted_", "trust_")):
                spec[key] = copy.deepcopy(value)
        # Fail before Ray/TSC if an optional metadata field has leaked NaN.
        _json_safe(spec)
        specs.append(spec)
    return specs


def summarize_phase(
    ctx: Stage31Context,
    manifest: dict[str, Any],
    results: Sequence[dict[str, Any]],
    *,
    result_dir: Path,
) -> list[dict[str, Any]]:
    by_id = {str(result.get("experiment_id")): result for result in results}
    rows: list[dict[str, Any]] = []
    for candidate in manifest["candidates"]:
        candidate_id = str(candidate["candidate_id"])
        nominal = nominal_by_id(ctx, str(candidate["nominal_id"]))
        control = _vector(candidate["control_vector"])
        decoded = decode_control_sequence(ctx, nominal, control)
        result = by_id.get(candidate_id)
        if result is None:
            metrics: dict[str, Any] = {
                "success": False,
                "failure_reason": "missing result",
                "strict_gate_pass": False,
                "relaxed_gate_pass": False,
                "gate_label": "MISSING_RESULT",
                "stage3_1_max_violation": 1e12,
                "stage3_1_sum_violation": 1e12,
                "stage3_1_l2_violation": 1e12,
                "stage3_1_quality": 1e12,
                "continuous_objective": 1e12,
                "selection_score": 99e18,
            }
        else:
            metrics = stage31_metrics(ctx, result, decoded)
        row = {
            "stage": "Stage3.1",
            "phase": str(manifest["phase"]),
            "candidate_id": candidate_id,
            "population_index": int(candidate["population_index"]),
            "nominal_id": str(candidate["nominal_id"]),
            "source_candidate_id": str(candidate.get("source_candidate_id", "")),
            "nominal_category": str(candidate.get("nominal_category", "unknown")),
            "source_name": str(candidate.get("source_name", "unknown")),
            "source_type": str(candidate.get("source_type", "unknown")),
            "control_vector": control.tolist(),
            "result_relpath": str((result_dir / f"{candidate_id}.json.gz").relative_to(ctx.paths.run_dir)),
            **metrics,
        }
        for key, value in candidate.items():
            if key.startswith(("probe_", "sqp_", "predicted_", "trust_")):
                row[key] = copy.deepcopy(value)
        rows.append(row)
    rows.sort(key=_best_key)
    for rank, row in enumerate(rows, start=1):
        row["phase_rank"] = rank
    return rows


def evaluate_manifest(
    ctx: Stage31Context,
    *,
    manifest: dict[str, Any],
    backend: str,
    resume: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    phase = str(manifest["phase"])
    result_dir = ctx.paths.evaluations / phase
    specs = specs_from_manifest(ctx, manifest)
    results = s2.evaluate_specs(ctx, specs, output_dir=result_dir, backend=backend, resume=resume)
    rows = summarize_phase(ctx, manifest, results, result_dir=result_dir)
    phase_dir = ctx.paths.phases / phase
    write_csv(phase_dir / "phase_results.csv", rows)
    atomic_write_json(phase_dir / "phase_results.json", rows)
    return rows, results


def load_result_for_row(ctx: Stage31Context, row: dict[str, Any]) -> dict[str, Any]:
    source_path = str(row.get("source_result_path", "")).strip()
    if source_path:
        path = Path(source_path)
    else:
        relative = str(row.get("result_relpath", "")).strip()
        if not relative:
            raise FileNotFoundError(f"row {row.get('candidate_id')} has no result path")
        path = ctx.paths.run_dir / relative
    if not path.exists():
        raise FileNotFoundError(path)
    return read_json_gz(path)


def aggregate_new_rows(paths: Stage31Paths) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths.phases.glob("*/phase_results.json")):
        payload = read_json(path)
        if isinstance(payload, list):
            rows.extend(dict(row) for row in payload)
    return rows


def aggregate_rows(ctx: Stage31Context) -> list[dict[str, Any]]:
    return [*copy.deepcopy(ctx.source_rows), *aggregate_new_rows(ctx.paths)]


def unique_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return _dedupe_rows(rows)


def save_best_artifacts(ctx: Stage31Context, row: dict[str, Any]) -> None:
    ctx.paths.best.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.best / "best_candidate.json", row)
    result = load_result_for_row(ctx, row)
    atomic_write_json_gz(ctx.paths.best / "best_tsc_result.json.gz", result)
    nominal = nominal_by_id(ctx, str(row["nominal_id"]))
    decoded = decode_control_sequence(ctx, nominal, _vector(row["control_vector"]))
    action_rows: list[dict[str, Any]] = []
    for step in range(15):
        action_rows.append(
            {
                "step_index": step,
                "time_ms_from_start": step * int(ctx.env_cfg["dt_ms"]),
                "mode_1": float(decoded["mode_coefficients"][step, 0]),
                "mode_2": float(decoded["mode_coefficients"][step, 1]),
                "mode_3": float(decoded["mode_coefficients"][step, 2]),
                "action_norm_tsc": decoded["action_norm_tsc"][step].tolist(),
                "action_norm_display": decoded["action_norm_display"][step].tolist(),
            }
        )
    write_csv(ctx.paths.best / "best_action_sequence.csv", action_rows)


# ---------------------------------------------------------------------------
# State, center selection, finite differences, and 35x21 Jacobian
# ---------------------------------------------------------------------------


def initial_state(ctx: Stage31Context) -> dict[str, Any]:
    rows = unique_rows(ctx.source_rows)
    if not rows:
        raise RuntimeError("Stage3.0 source catalog is empty")
    best = min(rows, key=_best_key)
    trust_default = float(ctx.cfg["sqp"].get("initial_trust_scale", 1.0))
    state = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "source_stage3_0_run": str(ctx.source_stage30_run),
        "next_sqp_round": 0,
        "max_sqp_rounds": int(ctx.cfg["sqp"]["max_rounds"]),
        "trust_scale_by_nominal": {str(n["nominal_id"]): trust_default for n in ctx.nominals},
        "trust_scale_by_slot": {"primary": trust_default, "secondary": trust_default},
        "trust_scale_by_slot_nominal": {},
        "best_candidate_id": str(best["candidate_id"]),
        "best_nominal_id": str(best["nominal_id"]),
        "best_max_violation": float(best["stage3_1_max_violation"]),
        "best_phase": str(best.get("phase", "Stage3.0-source")),
        "best_control_vector": _vector(best["control_vector"]).tolist(),
        "rounds_without_improvement": 0,
        "strict_gate_found": any(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
        "optimization_finished": False,
        "controller_identification_complete": False,
        "feedback_poc_complete": False,
        "confirmation_complete": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }
    save_best_artifacts(ctx, best)
    return state


def load_or_initialize_state(ctx: Stage31Context, *, no_resume: bool = False) -> dict[str, Any]:
    if no_resume and ctx.paths.state.exists():
        raise FileExistsError(f"--no-resume requested but state exists: {ctx.paths.state}")
    if ctx.paths.state.exists():
        state = read_json(ctx.paths.state)
        if Path(state["source_stage3_0_run"]).resolve() != ctx.source_stage30_run:
            raise ValueError("Stage3.1 state points to a different Stage3.0 source")
        return state
    state = initial_state(ctx)
    atomic_write_json(ctx.paths.state, state)
    return state


def update_state_best(ctx: Stage31Context, state: dict[str, Any], rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    if not successful:
        return state
    best = min(successful, key=_best_key)
    previous = float(state.get("best_max_violation", 1e12))
    meaningful = float(ctx.cfg["sqp"].get("meaningful_improvement", 1e-4))
    improved = _as_bool(best.get("strict_gate_pass"), False) or float(best["stage3_1_max_violation"]) < previous - meaningful
    if improved:
        state["best_candidate_id"] = str(best["candidate_id"])
        state["best_nominal_id"] = str(best["nominal_id"])
        state["best_max_violation"] = float(best["stage3_1_max_violation"])
        state["best_phase"] = str(best["phase"])
        state["best_control_vector"] = _vector(best["control_vector"]).tolist()
        save_best_artifacts(ctx, best)
    state["strict_gate_found"] = bool(
        state.get("strict_gate_found", False)
        or any(_as_bool(row.get("strict_gate_pass"), False) for row in successful)
    )
    state["updated_utc"] = utc_timestamp()
    return state


def _candidate_distance(lhs: dict[str, Any], rhs: dict[str, Any]) -> float:
    return float(np.linalg.norm(_vector(lhs["control_vector"]) - _vector(rhs["control_vector"])))


def select_sqp_centers(
    ctx: Stage31Context,
    rows: Sequence[dict[str, Any]],
    *,
    round_index: int,
) -> list[dict[str, Any]]:
    successful = unique_rows([row for row in rows if _as_bool(row.get("success"), False)])
    if len(successful) < 2:
        raise RuntimeError("Need at least two successful candidates for Stage3.1 centers")
    primary = min(successful, key=_best_key)
    sqp = ctx.cfg["sqp"]
    minimum_distance = float(sqp.get("center_minimum_distance", 0.04))
    forced_rounds = int(sqp.get("force_distinct_nominal_rounds", 2))
    alternatives = [row for row in successful if str(row["nominal_id"]) != str(primary["nominal_id"])]
    preferred_categories = ("position_front", "corner", "speed_safe", "gate")
    alternatives.sort(
        key=lambda row: (
            preferred_categories.index(str(row.get("nominal_category")))
            if str(row.get("nominal_category")) in preferred_categories
            else 99,
            _best_key(row),
        )
    )
    secondary: dict[str, Any] | None = None
    if round_index < forced_rounds:
        secondary = next((row for row in alternatives if _candidate_distance(primary, row) >= minimum_distance), None)
        if secondary is None and alternatives:
            secondary = alternatives[0]
    else:
        factor = float(sqp.get("alternative_nominal_max_factor_after_forced_rounds", 3.0))
        eligible_alt = [
            row
            for row in alternatives
            if _finite(row.get("stage3_1_max_violation"), 1e12)
            <= factor * max(_finite(primary.get("stage3_1_max_violation"), 1e-12), 1e-12)
        ]
        secondary = next((row for row in eligible_alt if _candidate_distance(primary, row) >= minimum_distance), None)
    if secondary is None:
        same = [row for row in successful if row["candidate_id"] != primary["candidate_id"]]
        same.sort(
            key=lambda row: (
                0 if _as_bool(row.get("stage3_1_speed_safe_at_best_endpoint"), False) else 1,
                _finite(row.get("stage3_1_position_violation"), 1e12),
                -_candidate_distance(primary, row),
                _best_key(row),
            )
        )
        secondary = next((row for row in same if _candidate_distance(primary, row) >= minimum_distance), same[0])
    return [primary, secondary]


def build_probe_manifest(
    ctx: Stage31Context,
    *,
    round_index: int,
    centers: Sequence[dict[str, Any]],
    delta_matrix: np.ndarray | None = None,
    phase_prefix: str = "round",
) -> dict[str, Any]:
    delta = np.asarray(
        delta_matrix if delta_matrix is not None else ctx.cfg["sqp"]["probe_delta_by_step_mode"],
        dtype=float,
    )
    if delta.shape != (7, 3):
        raise ValueError("Stage3.1 finite-difference delta must be 7x3")
    phase = f"{phase_prefix}_{round_index:03d}_probes"
    phase_dir = ctx.paths.phases / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = phase_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)
    rows: list[dict[str, Any]] = []
    for center_index, center in enumerate(centers):
        nominal = nominal_by_id(ctx, str(center["nominal_id"]))
        center_vector = _vector(center["control_vector"])
        for variable_index in range(21):
            requested = float(delta.reshape(-1)[variable_index])
            center_value = float(center_vector[variable_index])
            lower = float(ctx.coefficient_lower[variable_index])
            upper = float(ctx.coefficient_upper[variable_index])
            lower_room = max(center_value - lower, 0.0)
            upper_room = max(upper - center_value, 0.0)
            eps = 1e-12
            if lower_room > eps and upper_room > eps:
                low = center_value - min(requested, lower_room)
                high = center_value + min(requested, upper_room)
                scheme = "two_sided"
            elif lower_room > eps:
                span = min(requested, lower_room)
                low, high = center_value - span, center_value - 0.5 * span
                scheme = "upper_bound_inward_secant"
            elif upper_room > eps:
                span = min(requested, upper_room)
                low, high = center_value + 0.5 * span, center_value + span
                scheme = "lower_bound_inward_secant"
            else:
                raise RuntimeError(f"variable {variable_index} has no probe room")
            if high - low <= eps:
                raise RuntimeError(f"probe collapsed for variable {variable_index}")
            for sign, value in ((-1, low), (1, high)):
                vector = center_vector.copy()
                vector[variable_index] = value
                vector = clip_control(ctx, vector)
                row = candidate_row(
                    ctx,
                    nominal=nominal,
                    control_vector=vector,
                    source_name=f"center{center_index}_v{variable_index}_{'p' if sign > 0 else 'm'}",
                    source_type="real_tsc_fd_probe",
                    phase_name=phase,
                    extra={
                        "probe_center_candidate_id": str(center["candidate_id"]),
                        "probe_center_nominal_id": str(center["nominal_id"]),
                        "probe_variable_index": variable_index,
                        "probe_sign": sign,
                        "probe_requested_delta": requested,
                        "probe_actual_delta": float(vector[variable_index] - center_vector[variable_index]),
                        "probe_scheme": scheme,
                    },
                )
                identity = (
                    f"{phase}|{center['candidate_id']}|{variable_index}|{sign}|"
                    f"{vector_digest(vector, 'v')}"
                )
                row["candidate_id"] = f"s31r{round_index:03d}p_{hashlib.sha256(identity.encode()).hexdigest()[:16]}"
                rows.append(row)
    expected = len(centers) * 21 * 2
    if len(rows) != expected:
        raise RuntimeError(f"constructed {len(rows)} probes, expected {expected}")
    for index, row in enumerate(rows):
        row["population_index"] = index
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "phase": phase,
        "round_index": round_index,
        "population_size": len(rows),
        "centers": [
            {
                "candidate_id": str(center["candidate_id"]),
                "nominal_id": str(center["nominal_id"]),
                "control_vector": _vector(center["control_vector"]).tolist(),
            }
            for center in centers
        ],
        "candidates": rows,
    }
    atomic_write_json(manifest_path, manifest)
    write_csv(phase_dir / "candidate_manifest.csv", rows)
    return manifest


def build_real_tsc_jacobian(
    ctx: Stage31Context,
    *,
    center: dict[str, Any],
    probe_manifest: dict[str, Any],
    probe_rows: Sequence[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    center_result = load_result_for_row(ctx, center)
    center_feature = trajectory_feature_vector(ctx, center_result)
    center_vector = _vector(center["control_vector"])
    row_by_id = {str(row["candidate_id"]): row for row in probe_rows}
    specs = [
        row
        for row in probe_manifest["candidates"]
        if str(row.get("probe_center_candidate_id")) == str(center["candidate_id"])
    ]
    grouped: dict[int, dict[int, dict[str, Any]]] = {}
    for spec in specs:
        grouped.setdefault(int(spec["probe_variable_index"]), {})[int(spec["probe_sign"])] = spec
    jacobian = np.zeros((35, 21), dtype=float)
    columns: list[dict[str, Any]] = []
    reliable = 0
    unavailable: list[int] = []
    for variable_index in range(21):
        pair = grouped.get(variable_index, {})
        plus_spec, minus_spec = pair.get(1), pair.get(-1)
        plus_row = row_by_id.get(str(plus_spec["candidate_id"])) if plus_spec else None
        minus_row = row_by_id.get(str(minus_spec["candidate_id"])) if minus_spec else None
        plus_ok = plus_row is not None and _as_bool(plus_row.get("success"), False)
        minus_ok = minus_row is not None and _as_bool(minus_row.get("success"), False)
        method = "unavailable"
        denominator: float | None = None
        if plus_ok and minus_ok:
            plus_feature = trajectory_feature_vector(ctx, load_result_for_row(ctx, plus_row))
            minus_feature = trajectory_feature_vector(ctx, load_result_for_row(ctx, minus_row))
            plus_vector = _vector(plus_row["control_vector"])
            minus_vector = _vector(minus_row["control_vector"])
            denominator = float(plus_vector[variable_index] - minus_vector[variable_index])
            if abs(denominator) > 1e-12:
                jacobian[:, variable_index] = (plus_feature - minus_feature) / denominator
                method = "secant"
                reliable += 1
        elif plus_ok:
            plus_feature = trajectory_feature_vector(ctx, load_result_for_row(ctx, plus_row))
            plus_vector = _vector(plus_row["control_vector"])
            denominator = float(plus_vector[variable_index] - center_vector[variable_index])
            if abs(denominator) > 1e-12:
                jacobian[:, variable_index] = (plus_feature - center_feature) / denominator
                method = "forward"
                reliable += 1
        elif minus_ok:
            minus_feature = trajectory_feature_vector(ctx, load_result_for_row(ctx, minus_row))
            minus_vector = _vector(minus_row["control_vector"])
            denominator = float(center_vector[variable_index] - minus_vector[variable_index])
            if abs(denominator) > 1e-12:
                jacobian[:, variable_index] = (center_feature - minus_feature) / denominator
                method = "backward"
                reliable += 1
        if method == "unavailable":
            unavailable.append(variable_index)
        columns.append(
            {
                "variable_index": variable_index,
                "control_step": int(ctx.variable_steps[variable_index // 3]),
                "mode_index": variable_index % 3,
                "method": method,
                "denominator": denominator,
                "column_norm": float(np.linalg.norm(jacobian[:, variable_index])),
            }
        )
    minimum = int(ctx.cfg["controller_identification"].get("minimum_reliable_columns", 15))
    if reliable < minimum:
        raise RuntimeError(f"Only {reliable}/21 reliable Jacobian columns; need {minimum}")
    singular = np.linalg.svd(jacobian[:, [i for i in range(21) if i not in unavailable]], compute_uv=False)
    rank = int(np.linalg.matrix_rank(jacobian))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "center_candidate_id": str(center["candidate_id"]),
        "center_nominal_id": str(center["nominal_id"]),
        "center_control_vector": center_vector.tolist(),
        "center_feature": center_feature.tolist(),
        "feature_names": feature_names(),
        "jacobian": jacobian.tolist(),
        "reliable_columns": reliable,
        "unavailable_variables": unavailable,
        "numerical_rank": rank,
        "singular_values": singular.tolist(),
        "column_diagnostics": columns,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"jacobian_{center['candidate_id']}"
    atomic_write_json(output_dir / f"{stem}.json", summary)
    write_csv(output_dir / f"{stem}_columns.csv", columns)
    np.savez_compressed(
        output_dir / f"{stem}.npz",
        center_feature=center_feature,
        center_control_vector=center_vector,
        jacobian=jacobian,
        unavailable_variables=np.asarray(unavailable, dtype=int),
    )
    return summary

# ---------------------------------------------------------------------------
# Dimensionless local SQP model and adaptive trust-region rounds
# ---------------------------------------------------------------------------


def _soft_hinge(value: np.ndarray, beta: float) -> np.ndarray:
    scaled = beta * np.asarray(value, dtype=float)
    return np.logaddexp(0.0, scaled) / beta


def predicted_constraints(ctx: Stage31Context, feature: np.ndarray, endpoint: int) -> dict[str, float]:
    values = unpack_feature(feature)
    endpoint_local = endpoint - 9
    window_start = endpoint - 2 - 9
    if not (0 <= window_start <= endpoint_local < 7):
        raise ValueError(f"invalid endpoint {endpoint}")
    position = float(
        np.max(
            np.abs(
                np.column_stack(
                    [values["R"][window_start:], values["Z"][window_start:]]
                )
            )
        )
    )
    speed = np.sqrt(values["vR"] ** 2 + values["vZ"] ** 2)
    late_start = max(0, endpoint_local - int(ctx.cfg["gate"]["late_window_steps"]) + 1)
    endpoint_speed = float(speed[endpoint_local])
    endpoint_late = float(np.sqrt(np.mean(speed[late_start : endpoint_local + 1] ** 2)))
    post_speed = float(np.sqrt(np.mean(speed[endpoint_local:] ** 2)))
    final_speed = float(speed[-1])
    ip = float(np.max(np.abs(values["Ip"][window_start:])))
    gate = ctx.cfg["gate"]
    violation = np.asarray(
        [
            max(position / float(gate["precise_tolerance_m"]) - 1.0, 0.0),
            max(endpoint_speed / float(gate["terminal_velocity_max_m_per_s"]) - 1.0, 0.0),
            max(endpoint_late / float(gate["late_velocity_rms_max_m_per_s"]) - 1.0, 0.0),
            max(post_speed / float(gate["late_velocity_rms_max_m_per_s"]) - 1.0, 0.0),
            max(final_speed / float(gate["terminal_velocity_max_m_per_s"]) - 1.0, 0.0),
            max(ip / float(gate["ip_tolerance_a"]) - 1.0, 0.0),
        ],
        dtype=float,
    )
    return {
        "max_violation": float(np.max(violation)),
        "sum_violation": float(np.sum(violation)),
        "l2_violation": float(np.linalg.norm(violation)),
        "position_box_m": position,
        "endpoint_speed_m_per_s": endpoint_speed,
        "late_speed_m_per_s": endpoint_late,
        "post_speed_m_per_s": post_speed,
        "final_speed_m_per_s": final_speed,
        "ip_max_error_A": ip,
    }


def linear_model_objective(
    ctx: Stage31Context,
    *,
    center_vector: np.ndarray,
    center_feature: np.ndarray,
    jacobian: np.ndarray,
    delta: np.ndarray,
    endpoint: int,
    profile: dict[str, float],
    source_step7: np.ndarray,
) -> float:
    values = unpack_feature(center_feature + jacobian @ delta)
    endpoint_local = endpoint - 9
    window_start = endpoint - 2 - 9
    velocity_start = max(0, endpoint_local - int(ctx.cfg["gate"]["late_window_steps"]) + 1)
    tolerance = float(ctx.cfg["gate"]["precise_tolerance_m"])
    speed_limit = float(ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"])
    ip_limit = float(ctx.cfg["gate"]["ip_tolerance_a"])
    beta = float(ctx.cfg["sqp"]["linear_solver"].get("softplus_beta", 80.0))
    r = values["R"][window_start:]
    z = values["Z"][window_start:]
    vr = values["vR"][velocity_start:]
    vz = values["vZ"][velocity_start:]
    position_core = float(np.mean((r / tolerance) ** 2 + (z / tolerance) ** 2))
    excess_r = _soft_hinge(np.abs(r) - tolerance, beta) / tolerance
    excess_z = _soft_hinge(np.abs(z) - tolerance, beta) / tolerance
    tube_excess = float(np.mean(excess_r**2 + excess_z**2))
    velocity_core = float(np.mean((vr / speed_limit) ** 2 + (vz / speed_limit) ** 2))
    ip_core = float(np.mean((values["Ip"][window_start:] / ip_limit) ** 2))
    trial = (center_vector + delta).reshape(7, 3)
    with_boundary = np.vstack([np.asarray(source_step7, dtype=float).reshape(1, 3), trial])
    solver_cfg = ctx.cfg["sqp"]["linear_solver"]
    delta_l2 = float(solver_cfg.get("delta_l2", 0.035)) * float(np.mean(delta**2))
    smoothness = float(solver_cfg.get("trajectory_smoothness", 0.025)) * float(
        np.mean(np.diff(with_boundary, axis=0) ** 2)
    )
    return float(
        float(profile.get("position", 1.0)) * position_core
        + float(profile.get("velocity", 1.0)) * velocity_core
        + float(profile.get("tube_excess", 3.0)) * tube_excess
        + 0.05 * ip_core
        + delta_l2
        + smoothness
    )


def solve_linearized_proposals(
    ctx: Stage31Context,
    *,
    center: dict[str, Any],
    jacobian_summary: dict[str, Any],
    trust_scale: float,
    round_index: int,
) -> list[dict[str, Any]]:
    try:
        from scipy.optimize import minimize
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for Stage3.1 SQP") from exc
    nominal = nominal_by_id(ctx, str(center["nominal_id"]))
    center_vector = _vector(center["control_vector"])
    center_feature = np.asarray(jacobian_summary["center_feature"], dtype=float)
    jacobian = np.asarray(jacobian_summary["jacobian"], dtype=float)
    source_step7 = np.asarray(nominal["mode_coefficients_100ms"], dtype=float)[7]
    radius = np.asarray(ctx.cfg["sqp"]["trust_radius_by_step_mode"], dtype=float).reshape(-1) * float(trust_scale)
    lower_delta = np.maximum(ctx.coefficient_lower - center_vector, -radius)
    upper_delta = np.minimum(ctx.coefficient_upper - center_vector, radius)
    unavailable = [int(x) for x in jacobian_summary.get("unavailable_variables", [])]
    for index in unavailable:
        lower_delta[index] = 0.0
        upper_delta[index] = 0.0
    bounds = list(zip(lower_delta.tolist(), upper_delta.tolist()))
    solver_cfg = ctx.cfg["sqp"]["linear_solver"]
    profiles = solver_cfg["profiles"]
    requests = list(solver_cfg["proposal_requests"])
    solved: dict[tuple[int, str], tuple[np.ndarray, Any, Any]] = {}
    rows: list[dict[str, Any]] = []
    for request_index, request in enumerate(requests):
        endpoint = int(request["endpoint_step"])
        profile_name = str(request["profile"])
        step_scale = float(request["step_scale"])
        key = (endpoint, profile_name)
        if key not in solved:
            profile = dict(profiles[profile_name])
            objective = lambda d: linear_model_objective(
                ctx,
                center_vector=center_vector,
                center_feature=center_feature,
                jacobian=jacobian,
                delta=np.asarray(d, dtype=float),
                endpoint=endpoint,
                profile=profile,
                source_step7=source_step7,
            )
            result = minimize(
                objective,
                np.zeros(21, dtype=float),
                method="SLSQP",
                bounds=bounds,
                options={
                    "maxiter": int(solver_cfg.get("max_iterations", 600)),
                    "ftol": 1e-12,
                    "disp": False,
                },
            )
            solved[key] = (np.asarray(result.x, dtype=float), result, objective)
        solution, result, objective = solved[key]
        delta = solution * step_scale
        vector = clip_control(ctx, center_vector + delta)
        actual_delta = vector - center_vector
        predicted_feature = center_feature + jacobian @ actual_delta
        predicted = predicted_constraints(ctx, predicted_feature, endpoint)
        normalized = np.abs(actual_delta) / np.maximum(radius, 1e-12)
        row = candidate_row(
            ctx,
            nominal=nominal,
            control_vector=vector,
            source_name=f"center_{center['candidate_id']}_{profile_name}_e{endpoint}_s{step_scale:.1f}",
            source_type="real_tsc_sqp_step",
            phase_name=f"round_{round_index:03d}_steps",
            extra={
                "sqp_center_candidate_id": str(center["candidate_id"]),
                "sqp_profile": profile_name,
                "sqp_endpoint_step": endpoint,
                "sqp_step_scale": step_scale,
                "sqp_request_index": request_index,
                "sqp_solver_success": bool(result.success),
                "sqp_solver_message": str(result.message),
                "predicted_linear_objective": float(objective(actual_delta)),
                "predicted_max_violation": float(predicted["max_violation"]),
                "predicted_sum_violation": float(predicted["sum_violation"]),
                "predicted_l2_violation": float(predicted["l2_violation"]),
                "predicted_position_box_m": float(predicted["position_box_m"]),
                "predicted_endpoint_speed_m_per_s": float(predicted["endpoint_speed_m_per_s"]),
                "predicted_late_speed_m_per_s": float(predicted["late_speed_m_per_s"]),
                "trust_scale": float(trust_scale),
                "trust_boundary_fraction": float(np.max(normalized)),
                "unavailable_jacobian_variables_frozen": unavailable,
            },
        )
        identity = (
            f"r{round_index}|{center['candidate_id']}|{request_index}|{profile_name}|"
            f"{endpoint}|{step_scale}|{vector_digest(vector, 'v')}"
        )
        row["candidate_id"] = f"s31r{round_index:03d}s_{hashlib.sha256(identity.encode()).hexdigest()[:16]}"
        rows.append(row)
    expected = int(ctx.cfg["sqp"]["proposals_per_center"])
    if len(rows) != expected:
        raise RuntimeError(f"center produced {len(rows)} proposals, expected {expected}")
    return rows


def build_step_manifest(
    ctx: Stage31Context,
    *,
    round_index: int,
    centers: Sequence[dict[str, Any]],
    jacobians: Sequence[dict[str, Any]],
    trust_scales: Sequence[float],
) -> dict[str, Any]:
    phase = f"round_{round_index:03d}_steps"
    phase_dir = ctx.paths.phases / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = phase_dir / "candidate_manifest.json"
    if manifest_path.exists():
        return read_json(manifest_path)
    rows: list[dict[str, Any]] = []
    for center, jacobian, trust_scale in zip(centers, jacobians, trust_scales):
        rows.extend(
            solve_linearized_proposals(
                ctx,
                center=center,
                jacobian_summary=jacobian,
                trust_scale=trust_scale,
                round_index=round_index,
            )
        )
    expected = len(centers) * int(ctx.cfg["sqp"]["proposals_per_center"])
    if len(rows) != expected:
        raise RuntimeError(f"step wave has {len(rows)} candidates, expected {expected}")
    for index, row in enumerate(rows):
        row["population_index"] = index
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "phase": phase,
        "round_index": round_index,
        "population_size": len(rows),
        "centers": [
            {
                "candidate_id": str(center["candidate_id"]),
                "nominal_id": str(center["nominal_id"]),
                "trust_scale": float(scale),
            }
            for center, scale in zip(centers, trust_scales)
        ],
        "candidates": rows,
    }
    atomic_write_json(manifest_path, manifest)
    write_csv(phase_dir / "candidate_manifest.csv", rows)
    return manifest


def _endpoint_max_violation(row: dict[str, Any], endpoint_step: int) -> float:
    """Return the real-TSC hard-constraint violation at one requested endpoint.

    SQP predictions are endpoint-specific.  Trust-region ratios must therefore
    compare the prediction with the real result at the same endpoint, rather
    than with whichever endpoint happens to be globally best for that rollout.
    Historical Stage3.0 rows and new Stage3.1 rows both carry endpoint
    evaluations; the scalar best-endpoint violation is only a compatibility
    fallback for synthetic tests or incomplete legacy rows.
    """
    evaluations = row.get("stage3_1_endpoint_evaluations")
    if not isinstance(evaluations, list):
        evaluations = row.get("stage3_0_endpoint_evaluations")
    if isinstance(evaluations, list):
        for item in evaluations:
            if not isinstance(item, dict):
                continue
            if _as_int(item.get("endpoint_step"), -1) == int(endpoint_step):
                return _finite(item.get("max_violation"), 1e12)
    return _finite(
        row.get("stage3_1_max_violation", row.get("stage3_0_max_violation")),
        1e12,
    )


def _trust_update_for_center(
    ctx: Stage31Context,
    *,
    center: dict[str, Any],
    step_rows: Sequence[dict[str, Any]],
    current_scale: float,
) -> dict[str, Any]:
    center_id = str(center["candidate_id"])
    candidates = [
        row
        for row in step_rows
        if _as_bool(row.get("success"), False)
        and str(row.get("sqp_center_candidate_id", "")) == center_id
    ]
    if not candidates:
        return {
            "center_candidate_id": center_id,
            "accepted": False,
            "rho": None,
            "action": "shrink_no_results",
            "old_trust_scale": current_scale,
            "new_trust_scale": max(
                float(ctx.cfg["sqp"]["minimum_trust_scale"]),
                current_scale * float(ctx.cfg["sqp"]["trust_shrink_rejected"]),
            ),
        }

    def comparison(row: dict[str, Any]) -> tuple[float, tuple[Any, ...]]:
        endpoint = _as_int(row.get("sqp_endpoint_step"), 15)
        return (_endpoint_max_violation(row, endpoint), _best_key(row))

    best = min(candidates, key=comparison)
    endpoint = _as_int(best.get("sqp_endpoint_step"), 15)
    center_value = _endpoint_max_violation(center, endpoint)
    actual_value = _endpoint_max_violation(best, endpoint)
    predicted_value = _finite(best.get("predicted_max_violation"), center_value)
    actual_reduction = center_value - actual_value
    predicted_reduction = center_value - predicted_value
    rho: float | None = None
    if predicted_reduction > 1e-12:
        rho = actual_reduction / predicted_reduction
    meaningful = float(ctx.cfg["sqp"].get("meaningful_improvement", 1e-4))
    accepted = _as_bool(best.get("strict_gate_pass"), False) or actual_reduction > meaningful
    boundary = _finite(best.get("trust_boundary_fraction"), 0.0)
    sqp = ctx.cfg["sqp"]
    minimum = float(sqp["minimum_trust_scale"])
    maximum = float(sqp["maximum_trust_scale"])
    if accepted and rho is not None and rho >= float(sqp["ratio_expand_threshold"]) and boundary >= float(sqp["boundary_fraction_for_expand"]):
        action = "expand"
        new_scale = current_scale * float(sqp["trust_expand_factor"])
    elif accepted and (rho is None or rho >= float(sqp["ratio_poor_threshold"])):
        action = "hold"
        new_scale = current_scale * float(sqp.get("trust_hold_factor", 1.0))
    elif accepted:
        action = "shrink_poor_ratio"
        new_scale = current_scale * float(sqp["trust_shrink_poor_ratio"])
    else:
        action = "shrink_rejected"
        new_scale = current_scale * float(sqp["trust_shrink_rejected"])
    new_scale = float(np.clip(new_scale, minimum, maximum))
    return {
        "center_candidate_id": center_id,
        "center_nominal_id": str(center["nominal_id"]),
        "best_step_candidate_id": str(best["candidate_id"]),
        "comparison_endpoint_step": int(endpoint),
        "comparison_endpoint_ms": int(endpoint * int(ctx.env_cfg.get("dt_ms", 10))),
        "center_max_violation_at_endpoint": center_value,
        "predicted_max_violation_at_endpoint": predicted_value,
        "real_max_violation_at_endpoint": actual_value,
        # Keep the old names for downstream compatibility, but they now refer
        # explicitly to the common requested endpoint.
        "center_max_violation": center_value,
        "predicted_max_violation": predicted_value,
        "real_max_violation": actual_value,
        "predicted_reduction": predicted_reduction,
        "actual_reduction": actual_reduction,
        "rho": rho,
        "trust_boundary_fraction": boundary,
        "accepted": accepted,
        "action": action,
        "old_trust_scale": current_scale,
        "new_trust_scale": new_scale,
    }


def run_one_sqp_round(ctx: Stage31Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    if state.get("optimization_finished"):
        return state
    round_index = int(state["next_sqp_round"])
    if round_index >= int(state["max_sqp_rounds"]):
        state["optimization_finished"] = True
        state["stop_reason"] = "max_sqp_rounds"
        atomic_write_json(ctx.paths.state, state)
        return state
    historical = aggregate_rows(ctx)
    previous_best = min(
        (_finite(row.get("stage3_1_max_violation"), 1e12) for row in historical if _as_bool(row.get("success"), False)),
        default=1e12,
    )
    centers = select_sqp_centers(ctx, historical, round_index=round_index)
    trust_map = dict(state.get("trust_scale_by_nominal", {}))
    slot_map = dict(state.get("trust_scale_by_slot", {}))
    slot_nominal_map = dict(state.get("trust_scale_by_slot_nominal", {}))
    default_trust = float(ctx.cfg["sqp"]["initial_trust_scale"])
    slot_names = ["primary", "secondary"]
    trust_scales: list[float] = []
    for slot, center in zip(slot_names, centers):
        nominal_id = str(center["nominal_id"])
        composite = f"{slot}|{nominal_id}"
        trust_scales.append(
            float(
                slot_nominal_map.get(
                    composite,
                    trust_map.get(nominal_id, slot_map.get(slot, default_trust)),
                )
            )
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
        trust_scales=trust_scales,
    )
    step_rows, _ = evaluate_manifest(ctx, manifest=step_manifest, backend=backend, resume=resume)
    state = update_state_best(ctx, state, step_rows)

    diagnostics = []
    for slot, center, scale in zip(slot_names, centers, trust_scales):
        diagnostic = _trust_update_for_center(
            ctx, center=center, step_rows=step_rows, current_scale=scale
        )
        diagnostic["center_slot"] = slot
        diagnostics.append(diagnostic)
        new_scale = float(diagnostic["new_trust_scale"])
        slot_map[slot] = new_scale
        nominal_id = str(diagnostic["center_nominal_id"])
        trust_map[nominal_id] = new_scale
        slot_nominal_map[f"{slot}|{nominal_id}"] = new_scale
    state["trust_scale_by_nominal"] = trust_map
    state["trust_scale_by_slot"] = slot_map
    state["trust_scale_by_slot_nominal"] = slot_nominal_map
    all_after = aggregate_rows(ctx)
    round_best = min(
        (_finite(row.get("stage3_1_max_violation"), 1e12) for row in all_after if _as_bool(row.get("success"), False)),
        default=previous_best,
    )
    meaningful = round_best < previous_best - float(ctx.cfg["sqp"]["meaningful_improvement"])
    state["rounds_without_improvement"] = 0 if meaningful else int(state.get("rounds_without_improvement", 0)) + 1
    state["next_sqp_round"] = round_index + 1
    state["last_round"] = {
        "round_index": round_index,
        "centers": [str(center["candidate_id"]) for center in centers],
        "center_nominals": [str(center["nominal_id"]) for center in centers],
        "previous_best_max_violation": previous_best,
        "round_best_max_violation": round_best,
        "meaningful_improvement": meaningful,
        "trust_diagnostics": diagnostics,
    }
    atomic_write_json(ctx.paths.phases / f"round_{round_index:03d}_trust_diagnostics.json", state["last_round"])
    if state.get("strict_gate_found"):
        state["optimization_finished"] = True
        state["stop_reason"] = "strict_gate_found"
    elif state["next_sqp_round"] >= int(state["max_sqp_rounds"]):
        state["optimization_finished"] = True
        state["stop_reason"] = "max_sqp_rounds"
    elif int(state["rounds_without_improvement"]) >= int(ctx.cfg["sqp"]["max_rounds_without_improvement"]):
        state["optimization_finished"] = True
        state["stop_reason"] = "no_improvement_patience"
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    successful_steps = [row for row in step_rows if _as_bool(row.get("success"), False)]
    best_step = min(successful_steps, key=_best_key) if successful_steps else None
    print(
        json.dumps(
            {
                "stage": "Stage3.1",
                "round": round_index,
                "probe_success": sum(_as_bool(row.get("success"), False) for row in probe_rows),
                "step_success": len(successful_steps),
                "best": None
                if best_step is None
                else {
                    "candidate_id": best_step["candidate_id"],
                    "nominal_id": best_step["nominal_id"],
                    "strict": best_step.get("strict_gate_pass"),
                    "sustained_box_m": best_step.get("stage3_1_sustained_box_max_error_m"),
                    "post_arrival_velocity_rms": best_step.get("stage3_1_post_arrival_velocity_rms_m_per_s"),
                    "max_violation": best_step.get("stage3_1_max_violation"),
                },
                "trust": diagnostics,
                "next_round": state["next_sqp_round"],
                "finished": state["optimization_finished"],
                "stop_reason": state["stop_reason"],
            },
            indent=2,
        ),
        flush=True,
    )
    return state


def run_optimization(ctx: Stage31Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    while not state.get("optimization_finished"):
        state = run_one_sqp_round(ctx, backend=backend, resume=resume)
    return state

# ---------------------------------------------------------------------------
# Dimensionless final identification and time-indexed causal gains
# ---------------------------------------------------------------------------


def _normalization_vectors(ctx: Stage31Context) -> tuple[np.ndarray, np.ndarray]:
    scales_cfg = ctx.cfg["mpc"]["output_scales"]
    weights_cfg = ctx.cfg["mpc"]["output_weights"]
    scales = np.concatenate(
        [
            np.full(7, float(scales_cfg["R_m"])),
            np.full(7, float(scales_cfg["Z_m"])),
            np.full(7, float(scales_cfg["vR_m_per_s"])),
            np.full(7, float(scales_cfg["vZ_m_per_s"])),
            np.full(7, float(scales_cfg["Ip_A"])),
        ]
    )
    weights = np.concatenate(
        [
            np.full(7, float(weights_cfg["R"])),
            np.full(7, float(weights_cfg["Z"])),
            np.full(7, float(weights_cfg["vR"])),
            np.full(7, float(weights_cfg["vZ"])),
            np.full(7, float(weights_cfg["Ip"])),
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
    # z = -V diag(filter) U^T sqrt(W) e; delta = diag(radius) z.
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


def _measurement_bias_projection(ctx: Stage31Context, *, current_step: int, selected_rows: list[int]) -> np.ndarray:
    """Map [dR,dZ,dvR,dvZ,dIp] normalized at current_step to future normalized outputs.

    A constant-velocity bias model is intentionally modest: it is used only to
    turn the real-TSC batch sensitivity into a causal first-action POC.  The
    exported bundle says so explicitly and the gains are subsequently tested in
    real TSC rather than trusted analytically.
    """
    dt = float(ctx.env_cfg["dt_ms"]) / 1000.0
    scales_cfg = ctx.cfg["mpc"]["output_scales"]
    r_ratio = float(scales_cfg["vR_m_per_s"]) / float(scales_cfg["R_m"])
    z_ratio = float(scales_cfg["vZ_m_per_s"]) / float(scales_cfg["Z_m"])
    full = np.zeros((35, 5), dtype=float)
    for local, state in enumerate(range(9, 16)):
        horizon = max(state - current_step, 0) * dt
        full[local, 0] = 1.0
        full[local, 2] = horizon * r_ratio
        full[7 + local, 1] = 1.0
        full[7 + local, 3] = horizon * z_ratio
        full[14 + local, 2] = 1.0
        full[21 + local, 3] = 1.0
        full[28 + local, 4] = 1.0
    return full[np.asarray(selected_rows, dtype=int)]


def build_mpc_bundle(
    ctx: Stage31Context,
    *,
    center: dict[str, Any],
    jacobian_summary: dict[str, Any],
) -> dict[str, Any]:
    center_feature = np.asarray(jacobian_summary["center_feature"], dtype=float)
    jacobian = np.asarray(jacobian_summary["jacobian"], dtype=float)
    scales, weights = _normalization_vectors(ctx)
    j_norm = jacobian / scales[:, None]
    e_norm = center_feature / scales
    state_payload = read_json(ctx.paths.state) if ctx.paths.state.exists() else {}
    slot_map = state_payload.get("trust_scale_by_slot", {})
    trust_map = state_payload.get("trust_scale_by_nominal", {})
    slot_nominal_map = state_payload.get("trust_scale_by_slot_nominal", {})
    nominal_id = str(center["nominal_id"])
    trust_scale = float(
        slot_nominal_map.get(
            f"primary|{nominal_id}",
            trust_map.get(
                nominal_id,
                slot_map.get("primary", ctx.cfg["sqp"]["initial_trust_scale"]),
            ),
        )
    )
    radius = (
        np.asarray(ctx.cfg["sqp"]["trust_radius_by_step_mode"], dtype=float).reshape(-1)
        * trust_scale
        * float(ctx.cfg["mpc"].get("control_scale_from_trust_radius", 1.0))
    )
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

    causal: list[dict[str, Any]] = []
    for current_step in ctx.variable_steps:
        control_indices = [
            i for i, step in enumerate(np.repeat(np.asarray(ctx.variable_steps), 3)) if int(step) >= current_step
        ]
        first_future_state = current_step + 1
        selected_rows: list[int] = []
        for block in range(5):
            for local, state in enumerate(range(9, 16)):
                if state >= first_future_state:
                    selected_rows.append(block * 7 + local)
        j_selected = j_norm[np.asarray(selected_rows, dtype=int)][:, np.asarray(control_indices, dtype=int)]
        weights_selected = weights[np.asarray(selected_rows, dtype=int)]
        radius_selected = radius[np.asarray(control_indices, dtype=int)]
        projection = _measurement_bias_projection(ctx, current_step=current_step, selected_rows=selected_rows)
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
                "current_step": int(current_step),
                "control_variable_indices": control_indices,
                "selected_feature_indices": selected_rows,
                "selected_feature_names": [feature_names()[i] for i in selected_rows],
                "measurement_names": ["dR_norm", "dZ_norm", "dvR_norm", "dvZ_norm", "dIp_norm"],
                "sequence_gain": sequence_gain.tolist(),
                "first_action_gain": sequence_gain[:3].tolist(),
                "retained_rank": int(gain["retained_rank"]),
                "singular_values": gain["singular_values"],
                "retained_condition": float(gain["retained_condition"]),
            }
        )
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "created_utc": utc_timestamp(),
        "center_candidate_id": str(center["candidate_id"]),
        "center_nominal_id": str(center["nominal_id"]),
        "center_control_vector": _vector(center["control_vector"]).tolist(),
        "variable_steps": list(ctx.variable_steps),
        "feature_names": feature_names(),
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
        "limited_causal_feedback_poc_run": False,
        "online_feedback_validated": False,
        "robustness_validated": False,
        "deployment_status": "OFFLINE_DIMENSIONLESS_CAUSAL_MPC_POC_ONLY",
        "warning": (
            "The gains use a local real-TSC Jacobian and a constant-velocity bias projection. "
            "They are not a validated online MPC or a robust controller."
        ),
    }
    return bundle


def run_controller_identification(ctx: Stage31Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    bundle_path = ctx.paths.controller / "mpc_poc_bundle.json"
    if state.get("controller_identification_complete") and bundle_path.exists():
        return read_json(bundle_path)
    rows = aggregate_rows(ctx)
    center = min([row for row in unique_rows(rows) if _as_bool(row.get("success"), False)], key=_best_key)
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
    first_best = min([center, *[row for row in probe_rows if _as_bool(row.get("success"), False)]], key=_best_key)
    meaningful = float(ctx.cfg["sqp"].get("meaningful_improvement", 1e-4))
    recentered = (
        str(first_best["candidate_id"]) != str(center["candidate_id"])
        and _finite(first_best.get("stage3_1_max_violation"), 1e12)
        < _finite(center.get("stage3_1_max_violation"), 1e12) - meaningful
    )
    if recentered and int(ctx.cfg["controller_identification"].get("maximum_recenter_passes", 1)) >= 1:
        recenter_manifest = build_probe_manifest(
            ctx,
            round_index=1000,
            centers=[first_best],
            delta_matrix=delta,
            phase_prefix="controller_recenter",
        )
        recenter_rows, _ = evaluate_manifest(ctx, manifest=recenter_manifest, backend=backend, resume=resume)
        state = update_state_best(ctx, state, recenter_rows)
        center = first_best
        manifest = recenter_manifest
        probe_rows = recenter_rows
    jacobian = build_real_tsc_jacobian(
        ctx,
        center=center,
        probe_manifest=manifest,
        probe_rows=probe_rows,
        output_dir=ctx.paths.controller,
    )
    bundle = build_mpc_bundle(ctx, center=center, jacobian_summary=jacobian)
    recenter_performed = bool(recentered and int(ctx.cfg["controller_identification"].get("maximum_recenter_passes", 1)) >= 1)
    bundle["identification_recentered_once"] = recenter_performed
    atomic_write_json(bundle_path, bundle)
    np.savez_compressed(
        ctx.paths.controller / "mpc_poc_bundle.npz",
        center_feature=np.asarray(jacobian["center_feature"], dtype=float),
        jacobian=np.asarray(jacobian["jacobian"], dtype=float),
        output_scales=np.asarray(bundle["output_scales"], dtype=float),
        output_weights=np.asarray(bundle["output_weights"], dtype=float),
        control_radius=np.asarray(bundle["control_radius"], dtype=float),
        batch_gain=np.asarray(bundle["batch_gain"], dtype=float),
    )
    state["controller_identification_complete"] = True
    state["controller_identification_center"] = str(center["candidate_id"])
    state["controller_identification_recentered"] = recenter_performed
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(
        json.dumps(
            {
                "stage": "Stage3.1",
                "phase": "controller_identification",
                "center": center["candidate_id"],
                "recentered_once": recenter_performed,
                "successful_probes": sum(_as_bool(row.get("success"), False) for row in probe_rows),
                "reliable_columns": jacobian["reliable_columns"],
                "numerical_rank": jacobian["numerical_rank"],
                "batch_retained_rank": bundle["batch_retained_rank"],
                "online_feedback_validated": False,
            },
            indent=2,
        ),
        flush=True,
    )
    return bundle


# ---------------------------------------------------------------------------
# Limited causal-feedback real-TSC POC
# ---------------------------------------------------------------------------


def _nominal_reference(ctx: Stage31Context, center: dict[str, Any]) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    result = load_result_for_row(ctx, center)
    trajectory = result["trajectory"]
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    dt = float(ctx.env_cfg["dt_ms"]) / 1000.0
    velocity = np.zeros((16, 2), dtype=float)
    velocity[1:] = np.diff(y[:, :2], axis=0) / dt
    return result, y, velocity


def _scenario_definition(ctx: Stage31Context, name: str) -> dict[str, Any]:
    shift = float(ctx.cfg["mpc"].get("target_shift_m", 0.002))
    disturbance = float(ctx.cfg["mpc"].get("disturbance_mode_amplitude", 0.04))
    step = int(ctx.cfg["mpc"].get("disturbance_step", 10))
    table = {
        "nominal": (0.0, 0.0, None),
        "target_R_plus": (shift, 0.0, None),
        "target_R_minus": (-shift, 0.0, None),
        "target_Z_plus": (0.0, shift, None),
        "target_Z_minus": (0.0, -shift, None),
        "target_RZ_plus": (shift, shift, None),
        "disturbance_mode1_plus": (0.0, 0.0, {"step": step, "mode": 0, "amplitude": disturbance}),
        "disturbance_mode1_minus": (0.0, 0.0, {"step": step, "mode": 0, "amplitude": -disturbance}),
    }
    if name not in table:
        raise KeyError(name)
    dr, dz, pulse = table[name]
    return {"scenario": name, "target_R_offset_m": dr, "target_Z_offset_m": dz, "disturbance": pulse}


def feedback_specs(ctx: Stage31Context, bundle: dict[str, Any], center: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario_name in ctx.cfg["mpc"]["scenarios"]:
        scenario = _scenario_definition(ctx, str(scenario_name))
        for scale in ctx.cfg["mpc"]["controller_scales"]:
            scale = float(scale)
            experiment_id = (
                f"s31fb_{scenario_name}_scale{scale:.2f}_{center['candidate_id']}"
                .replace(".", "p")
                .replace("-", "m")
            )
            rows.append(
                {
                    "kind": "stage3_1_feedback_poc",
                    "experiment_id": experiment_id,
                    "candidate_id": experiment_id,
                    "center_candidate_id": str(center["candidate_id"]),
                    "nominal_id": str(center["nominal_id"]),
                    "control_vector": _vector(center["control_vector"]).tolist(),
                    "controller_scale": scale,
                    **scenario,
                }
            )
    return rows


def _mode_action_from_current(ctx: Stage31Context, coefficients: np.ndarray, currents: np.ndarray) -> np.ndarray:
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
        self.gains = {int(row["current_step"]): np.asarray(row["first_action_gain"], dtype=float) for row in bundle["causal_time_indexed_gains"]}
        self.control = _vector(center["control_vector"]).reshape(7, 3)
        self.variable_steps = list(range(8, 15))
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
        corrections: list[dict[str, Any]] = []
        failure_reason = ""
        try:
            self.env.reset()
            zero = np.zeros(14, dtype=float)
            trajectory.append(jsonio._state_record(self.env, 0, zero))
            target_offset = np.asarray(
                [float(spec["target_R_offset_m"]), float(spec["target_Z_offset_m"]), 0.0],
                dtype=float,
            )
            controller_scale = float(spec["controller_scale"])
            dt = float(self.env_cfg["dt_ms"]) / 1000.0
            for step in range(15):
                nominal_coeff = self.control[step - 8].copy() if step >= 8 else None
                if step < 8:
                    # Recover frozen nominal coefficients by projecting the
                    # stored physical nominal action onto the orthonormal modes.
                    nominal_action = np.asarray(self.center["full_mode_coefficients"])[step]
                    coefficients = np.asarray(nominal_action, dtype=float)
                    correction = np.zeros(3, dtype=float)
                    measurement = np.zeros(5, dtype=float)
                else:
                    state = self.env.last_state
                    current_y = np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)
                    current_rz = current_y[:2]
                    if step > 0 and len(trajectory) >= 2:
                        previous_state_rz = np.asarray([trajectory[-2]["R"], trajectory[-2]["Z"]], dtype=float)
                        current_velocity = (current_rz - previous_state_rz) / dt
                    else:
                        current_velocity = np.zeros(2, dtype=float)
                    measurement_physical = np.asarray(
                        [
                            current_y[0] - self.nominal_y[step, 0] - target_offset[0],
                            current_y[1] - self.nominal_y[step, 1] - target_offset[1],
                            current_velocity[0] - self.nominal_velocity[step, 0],
                            current_velocity[1] - self.nominal_velocity[step, 1],
                            current_y[2] - self.nominal_y[step, 2],
                        ],
                        dtype=float,
                    )
                    measurement = measurement_physical / self.measurement_scale
                    gain = self.gains[step]
                    correction = controller_scale * (gain @ measurement)
                    correction = np.clip(correction, -self.feedback_limit, self.feedback_limit)
                    coefficients = nominal_coeff + correction
                disturbance = spec.get("disturbance")
                if disturbance and step == int(disturbance["step"]):
                    coefficients = coefficients.copy()
                    coefficients[int(disturbance["mode"])] += float(disturbance["amplitude"])
                current_tsc = np.asarray(self.env.last_state["currents_a_tsc"], dtype=float)
                action = self._mode_action(coefficients, current_tsc)
                _, _, terminated, truncated, info = self.env.step(action)
                trajectory.append(jsonio._state_record(self.env, step + 1, action))
                corrections.append(
                    {
                        "step": step,
                        "measurement_normalized": measurement.tolist(),
                        "mode_correction": correction.tolist(),
                        "mode_command": np.asarray(coefficients, dtype=float).tolist(),
                    }
                )
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated"))
                    break
                if truncated and step + 1 < 15:
                    failure_reason = "environment truncated before 15 steps"
                    break
            success = len(trajectory) == 16 and not any(bool(row.get("abnormal", False)) for row in trajectory)
            result = {
                "schema_version": SCHEMA_VERSION,
                "experiment_id": spec["experiment_id"],
                "spec": spec,
                "success": bool(success),
                "failure_reason": "" if success else (failure_reason or "incomplete/abnormal trajectory"),
                "wall_time_s": float(time.time() - started),
                "trajectory": trajectory,
                "feedback_trace": corrections,
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
                "feedback_trace": corrections,
            }
        runner = getattr(self.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(
                failed=not bool(result.get("success", False)),
                reason=str(result.get("failure_reason", "stage3_1_feedback_complete")),
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
    ctx: Stage31Context,
    specs: list[dict[str, Any]],
    *,
    bundle: dict[str, Any],
    center: dict[str, Any],
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir = ctx.paths.feedback / "raw"
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
    center_payload = copy.deepcopy(center)
    nominal = nominal_by_id(ctx, str(center["nominal_id"]))
    decoded = decode_control_sequence(ctx, nominal, _vector(center["control_vector"]))
    center_payload["full_mode_coefficients"] = decoded["mode_coefficients"].tolist()
    pending = []
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
        worker = LocalFeedbackWorker(payload, bundle, center_payload, nominal_y, nominal_velocity, "stage31_feedback_serial")
        try:
            for index, spec in enumerate(pending, 1):
                result = worker.evaluate(spec)
                atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                print(f"[Stage3.1 feedback] {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif pending and backend == "ray":
        import ray

        requested = int(os.environ.get("STAGE3_1_WORKERS", ctx.cfg.get("parallel", {}).get("n_workers", 96)))
        ray_tmpdir = os.environ.get("RAY_TMPDIR", ctx.cfg.get("parallel", {}).get("ray_tmpdir", "")) or None
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=ray_tmpdir,
            log_prefix="[Stage3.1 feedback]",
        )
        n_workers = plan.actor_count
        Actor = _feedback_ray_actor_class()
        actors = [
            Actor.remote(payload, bundle, center_payload, nominal_y, nominal_velocity, f"stage31_feedback_{i:03d}")
            for i in range(n_workers)
        ]
        refs = {actors[i % n_workers].evaluate.remote(spec): spec for i, spec in enumerate(pending)}
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage3.1 feedback] waiting {done}/{len(pending)}", flush=True)
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
                    print(f"[Stage3.1 feedback] {done}/{len(pending)}", flush=True)
        finally:
            s2._close_ray_actors(actors, timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 600.0)))
    elif pending:
        raise ValueError("backend must be ray or serial")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


def _feedback_scale_summaries(
    rows: Sequence[dict[str, Any]],
    *,
    meaningful_improvement: float,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Evaluate one globally fixed feedback scale across all POC scenarios.

    A controller scale may not be selected independently after seeing each
    scenario; that would overstate performance.  The function therefore scores
    0.5 and 1.0 as two global controller choices and selects one scale for the
    POC summary.
    """
    by_scenario: dict[str, dict[float, dict[str, Any]]] = {}
    for row in rows:
        by_scenario.setdefault(str(row["scenario"]), {})[float(row["controller_scale"])] = row
    positive_scales = sorted(
        {
            float(row["controller_scale"])
            for row in rows
            if float(row["controller_scale"]) > 0.0
        }
    )
    scale_summaries: list[dict[str, Any]] = []
    for scale in positive_scales:
        comparisons: list[dict[str, Any]] = []
        ratios: list[float] = []
        improved = 0
        nonnominal = 0
        all_success = True
        for scenario, values in sorted(by_scenario.items()):
            baseline = values.get(0.0)
            feedback = values.get(scale)
            if baseline is None or feedback is None:
                all_success = False
                continue
            pair_success = _as_bool(baseline.get("success"), False) and _as_bool(
                feedback.get("success"), False
            )
            all_success = all_success and pair_success
            base_value = _finite(baseline.get("stage3_1_max_violation"), 1e12)
            feedback_value = _finite(feedback.get("stage3_1_max_violation"), 1e12)
            ratio = feedback_value / max(base_value, 1e-12)
            is_improved = feedback_value < base_value - meaningful_improvement
            if scenario != "nominal":
                nonnominal += 1
                ratios.append(ratio)
                improved += int(is_improved)
            comparisons.append(
                {
                    "scenario": scenario,
                    "controller_scale": scale,
                    "baseline_max_violation": base_value,
                    "feedback_max_violation": feedback_value,
                    "feedback_to_baseline_ratio": ratio,
                    "improved": is_improved,
                    "pair_success": pair_success,
                }
            )
        nominal = next((row for row in comparisons if row["scenario"] == "nominal"), None)
        nominal_safe = nominal is not None and nominal["feedback_max_violation"] <= max(
            nominal["baseline_max_violation"] * 1.10,
            nominal["baseline_max_violation"] + 0.01,
        )
        median_ratio = None if not ratios else float(np.median(ratios))
        limited_pass = bool(
            nonnominal > 0
            and improved >= math.ceil(0.60 * nonnominal)
            and median_ratio is not None
            and median_ratio < 0.95
            and nominal_safe
            and all_success
        )
        scale_summaries.append(
            {
                "controller_scale": scale,
                "comparisons": comparisons,
                "n_nonnominal_scenarios": nonnominal,
                "n_nonnominal_improved": improved,
                "median_nonnominal_feedback_ratio": median_ratio,
                "nominal_not_materially_worsened": nominal_safe,
                "all_required_rollouts_successful": all_success,
                "limited_causal_feedback_poc_pass": limited_pass,
            }
        )
    if not scale_summaries:
        return [], None
    passing = [row for row in scale_summaries if row["limited_causal_feedback_poc_pass"]]
    pool = passing if passing else scale_summaries
    selected = min(
        pool,
        key=lambda row: (
            0 if row["nominal_not_materially_worsened"] else 1,
            1e12
            if row["median_nonnominal_feedback_ratio"] is None
            else float(row["median_nonnominal_feedback_ratio"]),
            -int(row["n_nonnominal_improved"]),
            float(row["controller_scale"]),
        ),
    )
    return scale_summaries, selected


def run_feedback_poc(ctx: Stage31Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    summary_path = ctx.paths.feedback / "feedback_poc_summary.json"
    if state.get("feedback_poc_complete") and summary_path.exists():
        return read_json(summary_path)
    bundle = run_controller_identification(ctx, backend=backend, resume=resume)
    all_rows = unique_rows(aggregate_rows(ctx))
    center = next((row for row in all_rows if str(row["candidate_id"]) == str(bundle["center_candidate_id"])), None)
    if center is None:
        raise RuntimeError("controller center is missing from Stage3.1 catalog")
    specs = feedback_specs(ctx, bundle, center)
    results = evaluate_feedback_specs(ctx, specs, bundle=bundle, center=center, backend=backend, resume=resume)
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        shifted_ctx = copy.copy(ctx)
        shifted_ctx.cfg = copy.deepcopy(ctx.cfg)
        shifted_ctx.cfg["target"]["R"] += float(spec["target_R_offset_m"])
        shifted_ctx.cfg["target"]["Z"] += float(spec["target_Z_offset_m"])
        metrics = stage31_metrics(shifted_ctx, result, None)
        rows.append(
            {
                "scenario": spec["scenario"],
                "controller_scale": float(spec["controller_scale"]),
                "candidate_id": spec["experiment_id"],
                **metrics,
            }
        )
    rows.sort(key=lambda row: (str(row["scenario"]), float(row["controller_scale"])))
    write_csv(ctx.paths.feedback / "feedback_poc_results.csv", rows)
    atomic_write_json(ctx.paths.feedback / "feedback_poc_results.json", rows)
    scale_summaries, selected_scale_summary = _feedback_scale_summaries(
        rows,
        meaningful_improvement=float(ctx.cfg["sqp"]["meaningful_improvement"]),
    )
    comparisons = [] if selected_scale_summary is None else list(selected_scale_summary["comparisons"])
    limited_pass = bool(
        selected_scale_summary is not None
        and selected_scale_summary["limited_causal_feedback_poc_pass"]
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "created_utc": utc_timestamp(),
        "center_candidate_id": center["candidate_id"],
        "n_rollouts": len(rows),
        "n_successful": sum(_as_bool(row.get("success"), False) for row in rows),
        "n_strict": sum(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
        "selected_controller_scale": None
        if selected_scale_summary is None
        else float(selected_scale_summary["controller_scale"]),
        "comparisons": comparisons,
        "scale_summaries": scale_summaries,
        "n_nonnominal_scenarios": 0
        if selected_scale_summary is None
        else int(selected_scale_summary["n_nonnominal_scenarios"]),
        "n_nonnominal_improved_at_selected_scale": 0
        if selected_scale_summary is None
        else int(selected_scale_summary["n_nonnominal_improved"]),
        "median_nonnominal_feedback_ratio": None
        if selected_scale_summary is None
        else selected_scale_summary["median_nonnominal_feedback_ratio"],
        "nominal_not_materially_worsened": False
        if selected_scale_summary is None
        else bool(selected_scale_summary["nominal_not_materially_worsened"]),
        "limited_causal_feedback_poc_pass": limited_pass,
        "online_feedback_validated": False,
        "robustness_validated": False,
        "warning": (
            "This limited POC uses one initial state, +/-2 mm target shifts, and one injected mode disturbance. "
            "It does not validate robustness across initial states, plant parameters, noise, or long hold durations."
        ),
    }
    atomic_write_json(summary_path, summary)
    write_csv(ctx.paths.feedback / "feedback_poc_comparisons.csv", comparisons)
    bundle["limited_causal_feedback_poc_run"] = True
    bundle["limited_causal_feedback_poc_pass"] = limited_pass
    bundle["feedback_poc_summary"] = str(summary_path)
    bundle["online_feedback_validated"] = False
    bundle["robustness_validated"] = False
    atomic_write_json(ctx.paths.controller / "mpc_poc_bundle.json", bundle)
    state["feedback_poc_complete"] = True
    state["limited_causal_feedback_poc_pass"] = limited_pass
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(json.dumps(summary, indent=2), flush=True)
    return summary

# ---------------------------------------------------------------------------
# Category-aware confirmation and reporting
# ---------------------------------------------------------------------------


def _take_unique(
    destination: list[tuple[dict[str, Any], list[str]]],
    candidates: Sequence[dict[str, Any]],
    reason: str,
    limit: int,
) -> None:
    existing = {_result_key(row) for row, _ in destination}
    count = 0
    for row in candidates:
        key = _result_key(row)
        if key in existing:
            for existing_row, reasons in destination:
                if _result_key(existing_row) == key and reason not in reasons:
                    reasons.append(reason)
            continue
        destination.append((row, [reason]))
        existing.add(key)
        count += 1
        if count >= limit:
            break


def select_confirmation_candidates(ctx: Stage31Context, rows: Sequence[dict[str, Any]]) -> list[tuple[dict[str, Any], list[str]]]:
    cfg = ctx.cfg["confirmation"]
    successful = unique_rows([row for row in rows if _as_bool(row.get("success"), False)])
    selected: list[tuple[dict[str, Any], list[str]]] = []
    strict = sorted([row for row in successful if _as_bool(row.get("strict_gate_pass"), False)], key=_best_key)
    corner = sorted(successful, key=_best_key)
    speed_safe = sorted(
        [row for row in successful if _as_bool(row.get("stage3_1_speed_safe_at_best_endpoint"), False)],
        key=lambda row: (
            _finite(row.get("stage3_1_position_violation"), 1e12),
            _best_key(row),
        ),
    )
    relaxed = sorted(
        [row for row in successful if _as_bool(row.get("relaxed_gate_pass"), False)],
        key=_best_key,
    )
    _take_unique(selected, strict, "strict", int(cfg.get("strict_candidates", 3)))
    _take_unique(selected, corner, "corner", int(cfg.get("corner_candidates", 4)))
    _take_unique(selected, speed_safe, "speed_safe", int(cfg.get("speed_safe_candidates", 2)))
    _take_unique(selected, relaxed, "relaxed", int(cfg.get("relaxed_candidates", 2)))
    # Explicitly preserve different nominal families when they exist.
    used_nominals = {str(row["nominal_id"]) for row, _ in selected}
    different = [row for row in corner if str(row["nominal_id"]) not in used_nominals]
    _take_unique(selected, different, "different_nominal", int(cfg.get("different_nominal_candidates", 2)))
    return selected[: int(cfg.get("max_unique_candidates", 8))]


def run_confirmation(ctx: Stage31Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    verdict_path = ctx.paths.confirmations / "stage3_1_verdict.json"
    if state.get("confirmation_complete") and verdict_path.exists():
        return read_json(verdict_path)
    candidates = select_confirmation_candidates(ctx, aggregate_rows(ctx))
    if not candidates:
        raise RuntimeError("No Stage3.1 candidates are available for confirmation")
    repeats = int(ctx.cfg["confirmation"]["repeats_per_candidate"])
    specs: list[dict[str, Any]] = []
    for rank, (row, reasons) in enumerate(candidates, 1):
        nominal = nominal_by_id(ctx, str(row["nominal_id"]))
        decoded = decode_control_sequence(ctx, nominal, _vector(row["control_vector"]))
        for repeat in range(repeats):
            experiment_id = f"s31confirm_rank{rank:02d}_{row['candidate_id']}_r{repeat:02d}"
            specs.append(
                {
                    "kind": "stage3_1_confirmation",
                    "experiment_id": experiment_id,
                    "candidate_id": str(row["candidate_id"]),
                    "confirmation_rank": rank,
                    "confirmation_reasons": reasons,
                    "nominal_id": str(row["nominal_id"]),
                    "repeat": repeat,
                    "horizon_steps": 15,
                    "control_vector": _vector(row["control_vector"]).tolist(),
                    "action_sequence_norm_tsc": decoded["action_norm_tsc"].tolist(),
                    "action_sequence_norm_display": decoded["action_norm_display"].tolist(),
                }
            )
    raw_dir = ctx.paths.confirmations / "raw"
    results = s2.evaluate_specs(ctx, specs, output_dir=raw_dir, backend=backend, resume=resume)
    spec_by_id = {spec["experiment_id"]: spec for spec in specs}
    rows: list[dict[str, Any]] = []
    for result in results:
        spec = spec_by_id[str(result["experiment_id"])]
        source = next(row for row, _ in candidates if str(row["candidate_id"]) == str(spec["candidate_id"]))
        nominal = nominal_by_id(ctx, str(source["nominal_id"]))
        decoded = decode_control_sequence(ctx, nominal, _vector(source["control_vector"]))
        rows.append(
            {
                "candidate_id": spec["candidate_id"],
                "confirmation_rank": spec["confirmation_rank"],
                "confirmation_reasons": spec["confirmation_reasons"],
                "nominal_id": spec["nominal_id"],
                "repeat": spec["repeat"],
                **stage31_metrics(ctx, result, decoded),
            }
        )
    rows.sort(key=lambda row: (int(row["confirmation_rank"]), int(row["repeat"])))
    write_csv(ctx.paths.confirmations / "confirmation_results.csv", rows)
    atomic_write_json(ctx.paths.confirmations / "confirmation_results.json", rows)
    summaries: list[dict[str, Any]] = []
    for candidate_id in sorted({str(row["candidate_id"]) for row in rows}):
        subset = [row for row in rows if str(row["candidate_id"]) == candidate_id]
        successful = [row for row in subset if _as_bool(row.get("success"), False)]
        summaries.append(
            {
                "candidate_id": candidate_id,
                "confirmation_rank": min(int(row["confirmation_rank"]) for row in subset),
                "confirmation_reasons": subset[0]["confirmation_reasons"],
                "nominal_id": subset[0]["nominal_id"],
                "repeats": len(subset),
                "successful_repeats": len(successful),
                "all_repeats_strict_gate": bool(successful)
                and len(successful) == len(subset)
                and all(_as_bool(row.get("strict_gate_pass"), False) for row in successful),
                "all_repeats_relaxed_gate": bool(successful)
                and len(successful) == len(subset)
                and all(_as_bool(row.get("relaxed_gate_pass"), False) for row in successful),
                "worst_stage3_1_max_violation": None
                if not successful
                else float(max(float(row["stage3_1_max_violation"]) for row in successful)),
                "latest_confirmed_strict_arrival_ms": None
                if not successful
                else max(
                    (row.get("stage3_1_earliest_strict_arrival_ms") for row in successful if row.get("stage3_1_earliest_strict_arrival_ms") is not None),
                    default=None,
                ),
                "latest_confirmed_relaxed_arrival_ms": None
                if not successful
                else max(
                    (row.get("stage3_1_earliest_relaxed_arrival_ms") for row in successful if row.get("stage3_1_earliest_relaxed_arrival_ms") is not None),
                    default=None,
                ),
                "worst_sustained_box_max_error_m": None
                if not successful
                else float(max(float(row["stage3_1_sustained_box_max_error_m"]) for row in successful)),
                "max_post_arrival_velocity_rms_m_per_s": None
                if not successful
                else float(max(float(row["stage3_1_post_arrival_velocity_rms_m_per_s"]) for row in successful)),
            }
        )
    summaries.sort(key=lambda row: int(row["confirmation_rank"]))
    write_csv(ctx.paths.confirmations / "confirmation_summary.csv", summaries)
    atomic_write_json(ctx.paths.confirmations / "confirmation_summary.json", summaries)
    if any(row["all_repeats_strict_gate"] for row in summaries):
        verdict = "PASS_PRECISE_HOLD_30MM_120_150MS_CONFIRMED"
    elif any(row["all_repeats_relaxed_gate"] for row in summaries):
        verdict = "PASS_DAMPED_HOLD_40MM_120_150MS_CONFIRMED_ONLY"
    else:
        verdict = "NO_CONFIRMED_HOLD_120_150MS"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "verdict": verdict,
        "created_utc": utc_timestamp(),
        "candidate_summaries": summaries,
        "robustness_validated": False,
        "robustness_warning": (
            "Repeated deterministic rollouts confirm reproducibility only. Initial-state, target, noise, "
            "delay, vessel-current, and plant-parameter robustness remain untested."
        ),
    }
    atomic_write_json(verdict_path, payload)
    state["confirmation_complete"] = True
    state["confirmation_verdict"] = verdict
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    print(json.dumps(payload, indent=2), flush=True)
    return payload


def hall_of_fames(rows: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    successful = unique_rows([row for row in rows if _as_bool(row.get("success"), False)])
    return {
        "strict": sorted([row for row in successful if _as_bool(row.get("strict_gate_pass"), False)], key=_best_key)[:50],
        "minimax": sorted(successful, key=_best_key)[:50],
        "speed_safe": sorted(
            [row for row in successful if _as_bool(row.get("stage3_1_speed_safe_at_best_endpoint"), False)],
            key=lambda row: (_finite(row.get("stage3_1_position_violation"), 1e12), _best_key(row)),
        )[:50],
        "relaxed": sorted([row for row in successful if _as_bool(row.get("relaxed_gate_pass"), False)], key=_best_key)[:50],
    }


def generate_plots(ctx: Stage31Context, rows: Sequence[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    if not successful:
        return
    phases = []
    best_values = []
    for phase in dict.fromkeys(str(row.get("phase", "source")) for row in successful):
        subset = [row for row in successful if str(row.get("phase", "source")) == phase]
        phases.append(phase)
        best_values.append(min(float(row["stage3_1_max_violation"]) for row in subset))
    plt.figure(figsize=(11, 5))
    plt.plot(range(len(phases)), best_values, marker="o")
    plt.xticks(range(len(phases)), phases, rotation=60, ha="right")
    plt.ylabel("Best maximum normalized hard-gate violation")
    plt.title("Stage3.1 adaptive real-TSC SQP progress")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(ctx.paths.analysis / "max_violation_by_phase.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.scatter(
        [1000.0 * float(row["stage3_1_sustained_box_max_error_m"]) for row in successful],
        [float(row["stage3_1_post_arrival_velocity_rms_m_per_s"]) for row in successful],
        s=12,
    )
    plt.axvline(30.0, linewidth=1)
    plt.axhline(0.10, linewidth=1)
    plt.xlabel("Sustained rectangular R/Z box error (mm)")
    plt.ylabel("Post-arrival R/Z velocity RMS (m/s)")
    plt.title("Stage3.1 position-damping feasibility")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(ctx.paths.analysis / "position_damping_scatter.png", dpi=180)
    plt.close()

    best = min(successful, key=_best_key)
    result = load_result_for_row(ctx, best)
    trajectory = result["trajectory"]
    time_ms = [int(row["time_ms"]) for row in trajectory]
    r = [1000.0 * (float(row["R"]) - float(ctx.cfg["target"]["R"])) for row in trajectory]
    z = [1000.0 * (float(row["Z"]) - float(ctx.cfg["target"]["Z"])) for row in trajectory]
    plt.figure(figsize=(9, 5))
    plt.plot(time_ms, r, marker="o", label="R error")
    plt.plot(time_ms, z, marker="o", label="Z error")
    plt.axhline(30.0, linewidth=1)
    plt.axhline(-30.0, linewidth=1)
    plt.xlabel("TSC time (ms)")
    plt.ylabel("Error (mm)")
    plt.title(f"Stage3.1 best trajectory: {best.get('gate_label','')}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ctx.paths.analysis / "best_trajectory_rz.png", dpi=180)
    plt.close()


def write_report(ctx: Stage31Context, summary: dict[str, Any]) -> Path:
    best = summary.get("best")
    feedback = summary.get("feedback_poc")
    confirmation = summary.get("confirmation")
    lines = [
        "# Stage3.1 adaptive SQP and causal-feedback POC",
        "",
        f"- Source Stage3.0: `{ctx.source_stage30_run}`",
        "- Horizon: 150 ms at 10 ms control intervals",
        "- Control space: first 3 validated SVD modes",
        "- Frozen controls: steps 0-7",
        "- Optimized controls: steps 8-14 (21 variables)",
        "- Hard gate changed from Stage3.0: **no**",
        "",
        "## Fixed-scenario optimization",
        "",
        f"- Real-TSC evaluations in Stage3.1 catalog: {summary['n_stage3_1_evaluations']}",
        f"- Successful: {summary['n_stage3_1_successful']}",
        f"- Strict 30 mm candidates: {summary['n_strict_gate']}",
        f"- Relaxed 40 mm candidates: {summary['n_relaxed_gate']}",
    ]
    if best:
        lines.extend(
            [
                "",
                "## Best fixed-scenario candidate",
                "",
                f"- Candidate: `{best['candidate_id']}`",
                f"- Nominal family: `{best['nominal_id']}`",
                f"- Gate: `{best.get('gate_label','')}`",
                f"- Best endpoint: {best.get('stage3_1_best_endpoint_ms')} ms",
                f"- Sustained box error: {1000.0 * float(best['stage3_1_sustained_box_max_error_m']):.3f} mm",
                f"- Post-arrival velocity RMS: {float(best['stage3_1_post_arrival_velocity_rms_m_per_s']):.6f} m/s",
                f"- Maximum normalized violation: {float(best['stage3_1_max_violation']):.6f}",
            ]
        )
    if confirmation:
        lines.extend(["", "## Deterministic confirmation", "", f"- Verdict: `{confirmation['verdict']}`"])
    if feedback:
        lines.extend(
            [
                "",
                "## Limited causal-feedback POC",
                "",
                f"- Rollouts: {feedback['n_rollouts']}",
                f"- Limited POC pass: {feedback['limited_causal_feedback_poc_pass']}",
                "- Online feedback validated: **false**",
                "- Robustness validated: **false**",
            ]
        )
    lines.extend(
        [
            "",
            "## Final-task boundary",
            "",
            "Stage3.1 is not the final controller. The project target remains a causal, robust feedback controller that reaches, decelerates, and holds R/Z/Ip across initial states and targets.",
            "",
            "A fixed-state open-loop strict trajectory is only an expert/nominal entry point. The limited target-shift/disturbance POC does not validate robustness, long-duration hold, or deployable online MPC.",
        ]
    )
    report = ctx.paths.run_dir / "STAGE3_1_REPORT.md"
    jsonio.atomic_write_text(report, "\n".join(lines) + "\n")
    return report


def analyze_stage31(ctx: Stage31Context) -> dict[str, Any]:
    rows = aggregate_rows(ctx)
    new_rows = aggregate_new_rows(ctx.paths)
    hofs = hall_of_fames(rows)
    atomic_write_json(ctx.paths.analysis / "all_results.json", rows)
    write_csv(ctx.paths.analysis / "all_results.csv", rows)
    for name, values in hofs.items():
        atomic_write_json(ctx.paths.analysis / f"{name}_hall_of_fame.json", values)
        write_csv(ctx.paths.analysis / f"{name}_hall_of_fame.csv", values)
    generate_plots(ctx, rows)
    verdict_path = ctx.paths.confirmations / "stage3_1_verdict.json"
    feedback_path = ctx.paths.feedback / "feedback_poc_summary.json"
    confirmation = read_json(verdict_path) if verdict_path.exists() else None
    feedback = read_json(feedback_path) if feedback_path.exists() else None
    successful = [row for row in rows if _as_bool(row.get("success"), False)]
    best = min(successful, key=_best_key) if successful else None
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": "Stage3.1",
        "created_utc": utc_timestamp(),
        "source_stage3_0_run": str(ctx.source_stage30_run),
        "source_stage3_0_rows": len(ctx.source_rows),
        "n_stage3_1_evaluations": len(new_rows),
        "n_stage3_1_successful": sum(_as_bool(row.get("success"), False) for row in new_rows),
        "n_total_catalog_rows": len(rows),
        "n_strict_gate": sum(_as_bool(row.get("strict_gate_pass"), False) for row in rows),
        "n_relaxed_gate": sum(_as_bool(row.get("relaxed_gate_pass"), False) for row in rows),
        "best": best,
        "confirmation": confirmation,
        "feedback_poc": feedback,
        "online_feedback_validated": False,
        "robustness_validated": False,
    }
    report = write_report(ctx, summary)
    summary["report"] = str(report)
    atomic_write_json(ctx.paths.analysis / "stage3_1_analysis_summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


# ---------------------------------------------------------------------------
# Dependency-free self-test and CLI
# ---------------------------------------------------------------------------


def synthetic_stage31_test() -> dict[str, Any]:
    # Test normalized truncated-SVD gain on a deterministic, rank-deficient map.
    rng = np.random.default_rng(31)
    j = rng.normal(size=(20, 8))
    j[:, -1] = j[:, 0] + 1e-8 * j[:, 1]
    gain = _regularized_gain(
        j,
        np.ones(20),
        np.ones(8) * 0.2,
        ridge_lambda=0.08,
        relative_cutoff=1e-3,
        maximum_condition=1e6,
    )
    assert 1 <= gain["retained_rank"] < 8
    # Confirm Stage3.1 feature ordering/constraint math.
    cfg = {
        "gate": {
            "precise_tolerance_m": 0.03,
            "terminal_velocity_max_m_per_s": 0.1,
            "late_velocity_rms_max_m_per_s": 0.1,
            "late_window_steps": 4,
            "ip_tolerance_a": 10000.0,
        }
    }
    ctx = SimpleNamespace(cfg=cfg)
    feature = np.zeros(35, dtype=float)
    feature[0:7] = 0.029
    feature[7:14] = 0.029
    predicted = predicted_constraints(ctx, feature, 15)
    assert predicted["max_violation"] == 0.0
    feature[6] = 0.031
    predicted2 = predicted_constraints(ctx, feature, 15)
    assert predicted2["max_violation"] > 0.0
    return {
        "dimensionless_gain_retained_rank": gain["retained_rank"],
        "strict_constraint_math": True,
        "parameter_dimension": 21,
        "final_task_boundary_present": True,
    }


def execute(
    *,
    config_path: str | Path,
    source_stage30_run: str | Path | None,
    run_dir: str | Path | None,
    command: str,
    backend: str,
    resume: bool,
    no_resume: bool = False,
) -> Any:
    if command == "self-test":
        result = synthetic_stage31_test()
        print(json.dumps(result, indent=2), flush=True)
        return result
    ctx = load_stage31_config(
        config_path,
        source_stage30_run=source_stage30_run,
        run_dir_override=run_dir,
    )
    initialize_stage31_run(ctx)
    state = load_or_initialize_state(ctx, no_resume=no_resume)
    if command == "prepare":
        payload = {
            "stage": "Stage3.1",
            "run_dir": str(ctx.paths.run_dir),
            "source_stage3_0_run": str(ctx.source_stage30_run),
            "source_rows": len(ctx.source_rows),
            "source_unique_vectors": len(unique_rows(ctx.source_rows)),
            "source_fingerprint": None if ctx.source_fingerprint is None else {
                key: value for key, value in ctx.source_fingerprint.items() if key != "entries"
            },
            "initial_best_candidate_id": state["best_candidate_id"],
            "initial_best_max_violation": state["best_max_violation"],
            "variable_steps": list(ctx.variable_steps),
            "variables": 21,
            "hard_gate_changed": False,
            "final_task": "robust causal feedback control across initial states and targets",
        }
        print(json.dumps(payload, indent=2), flush=True)
        return payload
    if command == "round":
        return run_one_sqp_round(ctx, backend=backend, resume=resume)
    if command == "optimize":
        return run_optimization(ctx, backend=backend, resume=resume)
    if command == "identify":
        return run_controller_identification(ctx, backend=backend, resume=resume)
    if command == "feedback":
        return run_feedback_poc(ctx, backend=backend, resume=resume)
    if command == "confirm":
        return run_confirmation(ctx, backend=backend, resume=resume)
    if command == "analyze":
        return analyze_stage31(ctx)
    if command == "all":
        run_optimization(ctx, backend=backend, resume=resume)
        run_controller_identification(ctx, backend=backend, resume=resume)
        run_feedback_poc(ctx, backend=backend, resume=resume)
        run_confirmation(ctx, backend=backend, resume=resume)
        return analyze_stage31(ctx)
    raise ValueError(f"unknown Stage3.1 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage3.1 adaptive real-TSC SQP and causal feedback POC")
    parser.add_argument("--config", required=True)
    parser.add_argument("--source-stage3-0-run", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument(
        "--command",
        choices=("prepare", "round", "optimize", "identify", "feedback", "confirm", "analyze", "all", "self-test"),
        default="all",
    )
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> Any:
    args = _parser().parse_args(argv)
    return execute(
        config_path=args.config,
        source_stage30_run=args.source_stage3_0_run,
        run_dir=args.run_dir,
        command=args.command,
        backend=args.backend,
        resume=not args.no_resume,
        no_resume=args.no_resume,
    )


if __name__ == "__main__":
    main()
