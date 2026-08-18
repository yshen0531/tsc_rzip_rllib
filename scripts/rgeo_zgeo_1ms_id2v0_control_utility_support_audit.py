#!/usr/bin/env python3
"""ID-2V0 zero-TSC, zero-fit control-utility/support decision audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

import rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison as u2


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2v0_control_utility_support_audit.json"
SCHEMA = "rgeo-zgeo-1ms-id2v0-control-utility-support-audit-result-v1"
FAMILIES = ("u00", "u02", "u04", "u06")
LABELS = ("p04_minus", "p04_plus", "p07_minus", "p07_plus")
BLOCKS = (
    ("time_level_age", 0, 3),
    ("current_rgeo_zgeo_ip", 3, 6),
    ("velocity_lag1", 6, 9),
    ("velocity_lag2", 9, 12),
    ("velocity_lag4", 12, 15),
    ("actual_current_action_coordinates", 15, 18),
    ("action_memory_pole_0p25", 18, 21),
    ("action_memory_pole_0p5", 21, 24),
    ("action_memory_pole_0p75", 24, 27),
    ("action_memory_pole_0p9", 27, 30),
)


class IntegrityError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inside_root(value: str) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError(f"path escapes repository: {value}") from exc
    return path


def require_stage(path: Path = CONFIG) -> dict[str, Any]:
    stage = read_json(path)
    if stage.get("schema_version") != "rgeo-zgeo-1ms-id2v0-control-utility-support-audit-v1":
        raise IntegrityError("stage schema mismatch")
    if stage.get("stage") != "ID-2V0":
        raise IntegrityError("stage identity mismatch")
    if stage.get("development_family_ids") != list(FAMILIES):
        raise IntegrityError("development families changed")
    if stage.get("required_development_trajectories") != 20 or stage.get("required_probe_cells") != 16:
        raise IntegrityError("required source counts changed")
    if stage.get("unopened_calibration_family_ids") != ["u01", "u03"]:
        raise IntegrityError("calibration identities changed")
    if stage.get("unopened_blind_holdout_family_ids") != ["u05", "u07"]:
        raise IntegrityError("blind identities changed")
    if stage.get("prediction_horizons_ms") != list(range(1, 9)):
        raise IntegrityError("horizons changed")
    if stage.get("direction_grid_count") != 64:
        raise IntegrityError("direction grid changed")
    expected_blocks = [name for name, _, _ in BLOCKS]
    if stage["support_decomposition"].get("feature_blocks") != expected_blocks:
        raise IntegrityError("feature blocks changed")
    if stage["support_decomposition"].get("fixed_action_memory_poles") != [0.25, 0.5, 0.75, 0.9]:
        raise IntegrityError("action-memory poles changed")
    counts = stage.get("counts", {})
    if any(counts.get(key) != 0 for key in (
        "new_tsc_calls", "reset_calls", "plant_advances", "models_fit_or_trained",
        "calibration_records_read", "blind_holdout_records_read",
    )):
        raise IntegrityError("zero-execution counts changed")
    for key, spec in stage["source"].items():
        if key in {"directory", "trajectory_glob", "tracked_compact_inventory_files", "tracked_compact_inventory_digest"}:
            continue
        source_path = inside_root(spec["path"])
        if not source_path.is_file() or sha256(source_path) != spec["sha256"]:
            raise IntegrityError(f"source hash mismatch: {key}")
    u1_result = read_json(inside_root(stage["source"]["id2u1_result"]["path"]))
    if u1_result.get("route") != stage["source"]["id2u1_result"]["required_route"] or not u1_result.get("passed"):
        raise IntegrityError("U1 route mismatch")
    if u1_result.get("calibration_or_holdout_records_read") != 0:
        raise IntegrityError("U1 unopened roles were consumed")
    u2_result = read_json(inside_root(stage["source"]["id2u2_result"]["path"]))
    if u2_result.get("route") != stage["source"]["id2u2_result"]["required_route"] or u2_result.get("passed"):
        raise IntegrityError("U2 route mismatch")
    if u2_result.get("calibration_family_ids_read") or u2_result.get("blind_holdout_family_ids_read"):
        raise IntegrityError("U2 unopened roles were consumed")
    return stage


def _feature_by_family(data: u2.Dataset, u2_stage: dict[str, Any]) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for family in FAMILIES:
        cell = next(cell for cell in data.cells if cell.family_id == family and cell.kind == "probe")
        result[family] = u2.causal_prefix_feature(cell, cell.probe_issue, data, u2_stage)
    return result


def support_decomposition(data: u2.Dataset, u2_stage: dict[str, Any]) -> list[dict[str, Any]]:
    features = _feature_by_family(data, u2_stage)
    rows: list[dict[str, Any]] = []
    for held in FAMILIES:
        train = tuple(family for family in FAMILIES if family != held)
        matrix = np.asarray([features[family] for family in train])
        center, scale = u2._scaler(matrix)
        normalized_train = (matrix - center) / scale
        singular = np.linalg.svd(normalized_train, compute_uv=False)
        rank = int(np.linalg.matrix_rank(normalized_train))
        condition = float(singular[0] / singular[rank - 1]) if rank else math.inf
        query = features[held]
        normalized_delta = (matrix - query) / scale
        distances = np.linalg.norm(normalized_delta, axis=1)
        nearest_index = int(np.argmin(distances))
        nearest = train[nearest_index]
        delta = normalized_delta[nearest_index]
        local_model = u2.LocalEventModel(train, data, u2_stage)
        block_rows = []
        total_sq = float(np.dot(delta, delta))
        for name, begin, end in BLOCKS:
            block_sq = float(np.dot(delta[begin:end], delta[begin:end]))
            block_rows.append({
                "block": name,
                "squared_distance": block_sq,
                "fraction": block_sq / total_sq if total_sq else 0.0,
                "distance": math.sqrt(block_sq),
            })
        largest = np.argsort(np.abs(delta))[::-1][:10]
        rows.append({
            "fold_id": f"hold_{held}",
            "held_family": held,
            "training_families": list(train),
            "nearest_training_family": nearest,
            "distance": float(distances[nearest_index]),
            "support_threshold": float(local_model.support_threshold),
            "supported": bool(distances[nearest_index] <= local_model.support_threshold),
            "feature_rank": rank,
            "feature_condition": condition,
            "block_contributions": block_rows,
            "largest_feature_contributions": [
                {
                    "feature_index": int(index),
                    "normalized_abs_difference": float(abs(delta[index])),
                    "held_value": float(query[index]),
                    "nearest_value": float(features[nearest][index]),
                    "fold_scale": float(scale[index]),
                }
                for index in largest
            ],
        })
    return rows


def _directions(count: int) -> np.ndarray:
    return np.asarray([
        [math.cos(angle), math.sin(angle)]
        for angle in np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)
    ])


def _maximum_angular_gap(vectors: Iterable[np.ndarray]) -> float:
    angles = sorted(
        math.atan2(float(vector[1]), float(vector[0])) % (2.0 * math.pi)
        for vector in vectors if float(np.linalg.norm(vector)) > 1.0e-15
    )
    if len(angles) < 2:
        return 360.0
    gaps = [
        (angles[(index + 1) % len(angles)] - angles[index]) % (2.0 * math.pi)
        for index in range(len(angles))
    ]
    return float(max(gaps) * 180.0 / math.pi)


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator else -1.0


def _issued_max_slew(cell: u2.Cell, source_current: np.ndarray) -> float:
    previous = source_current
    maximum = 0.0
    for target in cell.issued:
        maximum = max(maximum, float(np.max(np.abs(target - previous))))
        previous = target
    return maximum


def family_utility(family: str, data: u2.Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    baseline = data.baselines[family]
    probes = sorted(
        [cell for cell in data.cells if cell.family_id == family and cell.kind == "probe"],
        key=lambda cell: cell.cell_id,
    )
    issue = probes[0].probe_issue
    if any(cell.probe_issue != issue for cell in probes):
        raise IntegrityError(f"probe issue mismatch: {family}")
    baseline_motion = baseline.states[issue + 1 : issue + 9, :2] - baseline.states[issue, :2]
    response = np.asarray([
        cell.states[issue + 1 : issue + 9] - baseline.states[issue + 1 : issue + 9]
        for cell in probes
    ])
    response_rz_norm = np.linalg.norm(response[:, :, :2], axis=2)
    baseline_rz_norm = np.linalg.norm(baseline_motion, axis=1)
    maximum_response_by_horizon = np.max(response_rz_norm, axis=0)
    ratio = np.divide(
        maximum_response_by_horizon,
        baseline_rz_norm,
        out=np.zeros_like(maximum_response_by_horizon),
        where=baseline_rz_norm > 0.0,
    )
    state40 = np.asarray([
        cell.states[40] - baseline.states[40]
        for cell in probes
    ])
    directions = _directions(int(stage["direction_grid_count"]))
    h8_projection = response[:, 7, :2] @ directions.T
    h8_best = np.max(h8_projection, axis=0)
    all_projection = np.einsum("ahd,qd->ahq", response[:, :, :2], directions)
    all_best = np.max(all_projection, axis=(0, 1))
    utilities = np.max(all_projection, axis=1)
    sorted_utility = np.sort(utilities, axis=0)
    best_second_gap = sorted_utility[-1] - sorted_utility[-2]
    equivalence_floor = float(stage["action_equivalence_floor_m"])

    action_rows = []
    for index, cell in enumerate(probes):
        rz = response[index, :, :2]
        peak_index = int(np.argmax(np.linalg.norm(rz, axis=1)))
        next_norm = float(np.linalg.norm(rz[peak_index + 1])) if peak_index + 1 < len(rz) else 0.0
        action_rows.append({
            "cell_id": cell.cell_id,
            "peak_horizon": peak_index + 1,
            "peak_rz_m": rz[peak_index].tolist(),
            "peak_rz_norm_m": float(np.linalg.norm(rz[peak_index])),
            "next_horizon_rz_norm_m": next_norm,
            "peak_to_next_ratio": float(np.linalg.norm(rz[peak_index]) / max(next_norm, 1.0e-15)),
            "h8_rz_m": rz[7].tolist(),
            "state40_rz_m": state40[index, :2].tolist(),
            "maximum_abs_ip_response_a": float(np.max(np.abs(response[index, :, 2]))),
            "maximum_issued_slew_a": _issued_max_slew(cell, data.source_current),
        })

    odd_even_rows = []
    by_label = {cell.cell_id.split("__", 1)[1]: response[index] for index, cell in enumerate(probes)}
    for direction in ("p04", "p07"):
        minus = by_label[f"{direction}_minus"][:, :2]
        plus = by_label[f"{direction}_plus"][:, :2]
        closure = float(np.linalg.norm(plus + minus) / max(np.linalg.norm(plus) + np.linalg.norm(minus), 1.0e-15))
        odd_even_rows.append({
            "direction": direction,
            "signed_opposite_cosine": _cosine(plus.reshape(-1), (-minus).reshape(-1)),
            "closure_ratio": closure,
        })

    criteria = stage["retrospective_program_criteria"]
    checks = {
        "h8_residual_to_baseline_motion": bool(
            ratio[7] >= criteria["minimum_each_family_h8_residual_to_baseline_motion_fraction"]
        ),
        "state40_residual": bool(
            float(np.max(np.linalg.norm(state40[:, :2], axis=1)))
            >= criteria["minimum_each_family_state40_max_residual_rz_norm_m"]
        ),
        "h8_all_direction_progress": bool(
            float(np.min(h8_best)) >= criteria["minimum_each_family_h8_all_direction_best_progress_m"]
        ),
        "action_integrity": bool(max(row["maximum_issued_slew_a"] for row in action_rows) <= 0.300000000001),
    }
    return {
        "family_id": family,
        "probe_issue": issue,
        "nominal_level": baseline.nominal_level,
        "baseline_rz_motion_m_by_horizon": baseline_rz_norm.tolist(),
        "maximum_residual_rz_norm_m_by_horizon": maximum_response_by_horizon.tolist(),
        "residual_to_baseline_motion_fraction_by_horizon": ratio.tolist(),
        "maximum_state40_residual_rz_norm_m": float(np.max(np.linalg.norm(state40[:, :2], axis=1))),
        "minimum_h8_all_direction_best_progress_m": float(np.min(h8_best)),
        "minimum_all_horizon_direction_best_progress_m": float(np.min(all_best)),
        "h8_maximum_angular_gap_deg": _maximum_angular_gap(response[:, 7, :2]),
        "all_horizon_maximum_angular_gap_deg": _maximum_angular_gap(response[:, :, :2].reshape(-1, 2)),
        "best_second_utility_gap_m": {
            "minimum": float(np.min(best_second_gap)),
            "median": float(np.median(best_second_gap)),
            "maximum": float(np.max(best_second_gap)),
            "equivalent_direction_count": int(np.sum(best_second_gap <= equivalence_floor)),
            "direction_count": int(len(best_second_gap)),
        },
        "maximum_abs_ip_response_a": float(np.max(np.abs(response[:, :, 2]))),
        "maximum_issued_slew_a": float(max(row["maximum_issued_slew_a"] for row in action_rows)),
        "action_rows": action_rows,
        "odd_even_rows": odd_even_rows,
        "program_criteria": checks,
        "program_criteria_passed": bool(all(checks.values())),
        "observation_replanning": {
            "truth_observation_period_ms": 1,
            "earliest_new_truth_after_issue_ms": 1,
            "macro_schedule_evaluation_horizon_ms": 8,
            "macro_commitment_is_not_a_queue_or_observation_delay": True,
        },
    }


def execute(stage_path: Path = CONFIG, source_revision: str = "UNSPECIFIED") -> dict[str, Any]:
    stage = require_stage(stage_path)
    u2_stage = u2.load_stage(inside_root(stage["source"]["id2u2_config"]["path"]))
    data = u2.load_dataset(u2_stage)
    if tuple(sorted(data.baselines)) != FAMILIES:
        raise IntegrityError("loaded families changed")
    if len(data.cells) != 20 or sum(cell.kind == "probe" for cell in data.cells) != 16:
        raise IntegrityError("loaded trajectory counts changed")
    support = support_decomposition(data, u2_stage)
    utility = [family_utility(family, data, stage) for family in FAMILIES]
    all_utility_passed = bool(all(row["program_criteria_passed"] for row in utility))
    route = (
        stage["routes"]["history_support_extension"]
        if all_utility_passed else stage["routes"]["branch_design_required"]
    )
    dominant_u02 = next(row for row in support if row["held_family"] == "u02")
    dominant_blocks = sorted(
        dominant_u02["block_contributions"], key=lambda row: row["squared_distance"], reverse=True
    )
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": sha256(stage_path),
        "route": route,
        "passed": True,
        "decision": "history_support_extension" if all_utility_passed else "branch_design_required",
        "support_decomposition": support,
        "u02_dominant_support_blocks": dominant_blocks[:5],
        "family_utility": utility,
        "all_families_program_criteria_passed": all_utility_passed,
        "independent_history_family_count": 4,
        "probe_cell_count": 16,
        "action_rank": int(data.action_rank),
        "new_tsc_calls": 0,
        "reset_calls": 0,
        "plant_advances": 0,
        "models_fit_or_trained": 0,
        "calibration_records_read": 0,
        "blind_holdout_records_read": 0,
        "next_stage_boundary": (
            "separate balanced history-support campaign design only"
            if all_utility_passed else
            "separate fixed-budget same-prefix multi-arm action-grammar branch design only"
        ),
        "claim_boundary": stage["claim_boundary"],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise IntegrityError(f"refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    try:
        output.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError("output must remain inside repository") from exc
    result = execute(args.config.resolve(), args.source_revision)
    write_json(output / "result.json", result)
    print(json.dumps({"route": result["route"], "passed": result["passed"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

