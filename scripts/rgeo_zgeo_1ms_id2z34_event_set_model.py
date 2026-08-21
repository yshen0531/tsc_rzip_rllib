#!/usr/bin/env python3
"""Fit the frozen two-candidate ID2Z34 finite event-set response model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z34_event_set_model.json"
CONFIG_SHA256 = "d682466c791b158ffada26aefcaae8d46f64b3f2434444a7a982e71bf9d3958b"
SCHEMA = "rgeo-zgeo-1ms-id2z34-event-set-model-result-v1"
OUTPUT_KEYS = ("r_geo_m", "z_geo_m", "ip_a")


def _error(message: str) -> ValueError:
    return ValueError(f"ID2Z34: {message}")


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise _error(f"{label} leaves repository") from exc
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise _error("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    if _sha(CONFIG) != CONFIG_SHA256 or stage != _read(CONFIG):
        raise _error("frozen config changed")
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z34-event-set-model-v1",
        "identity": "rgeo-zgeo-1ms-id2z34-event-set-model-v1",
        "stage": "ID-2Z34",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "phase_issues": [50, 56],
        "axis_ids": ["q_r", "q_z"],
        "signs": ["plus", "minus"],
        "effect_ages": list(range(1, 18)),
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field changed: {key}")
    candidates = stage["candidates"]
    roles = stage["data_contract"]
    if (candidates.get("candidate_count") != 2
            or candidates.get("hyperparameter_search") is not False
            or candidates.get("selection") != "minimum_complexity_a_else_b"
            or candidates.get("future_rzi") != "forbidden"
            or candidates.get("future_actual_current") != "forbidden"
            or roles.get("models_fit_or_updated") != 2
            or roles.get("calibration_or_holdout_reads") != 0
            or roles.get("id2z32_fit_weight") != 0
            or len(roles.get("prospective_fit_families", [])) != 8):
        raise _error("candidate/data contract changed")


def _evidence_name(phase: int, axis: str, sign: str) -> str:
    shorthand = "qr" if axis == "q_r" else "qz"
    return f"issue{phase}_{shorthand}_{sign}"


def load(config: Path = CONFIG) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    config = _inside(config, "config")
    if config != CONFIG.resolve():
        raise _error("alternate config forbidden")
    stage = _read(config)
    _require(stage)
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = _inside(ROOT / spec["path"], f"evidence {name}")
        if _sha(path) != spec["sha256"]:
            raise _error(f"evidence hash mismatch: {name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)
    result = evidence["id2z33_result"]
    audit = evidence["id2z33_independent"]
    if (result.get("passed") is not True
            or result.get("route") != stage["evidence"]["id2z33_result"]["required_route"]
            or result.get("models_fit_or_updated") != 0
            or result.get("fresh_calibration_or_holdout_records_read") != 0
            or audit.get("audit_passed") is not True
            or audit.get("primary_sha256") != stage["evidence"]["id2z33_result"]["sha256"]):
        raise _error("ID2Z33 identity mismatch")
    for phase in stage["phase_issues"]:
        for axis in stage["axis_ids"]:
            for sign in stage["signs"]:
                name = _evidence_name(phase, axis, sign)
                row = evidence[name]
                if (row.get("passed") is not True or row.get("fit_weight") != 1
                        or len(row.get("states", [])) != 74):
                    raise _error(f"incomplete fit row: {name}")
    if evidence["baseline"].get("fit_weight") != 0 or evidence["replay"].get("fit_weight") != 0:
        raise _error("zero-fit role mismatch")
    return stage, evidence


def response(evidence: dict[str, dict[str, Any]], phase: int,
             axis: str, sign: str) -> np.ndarray:
    center = evidence["baseline"]
    row = evidence[_evidence_name(phase, axis, sign)]
    return np.asarray([
        [float(row["states"][phase + age][key])
         - float(center["states"][phase + age][key]) for key in OUTPUT_KEYS]
        for age in range(1, 18)], dtype=float)


def _metrics(stage: dict[str, Any], observations: dict[str, list[np.ndarray]],
             centers: dict[str, np.ndarray], event_cells: set[tuple[str, int]]) -> dict[str, Any]:
    maximum = np.zeros(3, dtype=float)
    non_event_maximum = np.zeros(3, dtype=float)
    non_event_scaled = 0.0
    scales = np.asarray([stage["response_scales"][key] for key in OUTPUT_KEYS])
    for key, rows in observations.items():
        for row in rows:
            error = np.abs(row - centers[key])
            maximum = np.maximum(maximum, np.max(error, axis=0))
            for age_index, value in enumerate(error, start=1):
                if (key, age_index) not in event_cells:
                    non_event_maximum = np.maximum(non_event_maximum, value)
                    non_event_scaled = max(non_event_scaled, float(np.max(value / scales)))
    return {
        "maximum_absolute_error": dict(zip(OUTPUT_KEYS, maximum.tolist())),
        "maximum_non_event_absolute_error": dict(zip(OUTPUT_KEYS, non_event_maximum.tolist())),
        "maximum_non_event_scaled_absolute_error": non_event_scaled,
    }


def fit(stage: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    observations: dict[str, list[np.ndarray]] = {}
    centers: dict[str, np.ndarray] = {}
    spreads: dict[str, np.ndarray] = {}
    for axis in stage["axis_ids"]:
        for sign in stage["signs"]:
            key = f"{axis}:{sign}"
            rows = [response(evidence, phase, axis, sign) for phase in stage["phase_issues"]]
            observations[key] = rows
            centers[key] = np.mean(np.stack(rows), axis=0)
            spreads[key] = np.abs(rows[0] - rows[1])

    rule = stage["event_rule"]
    event_cells: set[tuple[str, int]] = set()
    event_rows: list[dict[str, Any]] = []
    for key, spread in spreads.items():
        for age_index in range(17):
            r_spread = float(spread[age_index, 0])
            adjacent = [float(spread[index, 0]) for index in (age_index - 1, age_index + 1)
                        if 0 <= index < 17]
            if (r_spread >= rule["minimum_cross_phase_r_spread_m"]
                    and all(value <= rule["maximum_adjacent_age_r_spread_m"]
                            for value in adjacent)):
                age = age_index + 1
                event_cells.add((key, age))
                deviations = np.max(np.abs(
                    np.stack(observations[key])[:, age_index, :] - centers[key][age_index]), axis=0)
                floor = np.asarray([rule["half_width_floor"][name] for name in OUTPUT_KEYS])
                half_width = deviations * float(rule["half_width_inflation"]) + floor
                event_rows.append({
                    "axis_sign": key,
                    "effect_age": age,
                    "absolute_effect_states": [phase + age for phase in stage["phase_issues"]],
                    "center": centers[key][age_index].tolist(),
                    "half_width": half_width.tolist(),
                    "full_width": (2.0 * half_width).tolist(),
                    "cross_phase_spread": spread[age_index].tolist(),
                    "adjacent_r_spreads_m": adjacent,
                })

    common_metrics = _metrics(stage, observations, centers, event_cells)
    gates = stage["development_gates"]
    a_error = common_metrics["maximum_absolute_error"]
    candidate_a_passed = bool(
        a_error["r_geo_m"] <= gates["candidate_a_maximum_r_error_m"]
        and a_error["z_geo_m"] <= gates["candidate_a_maximum_z_error_m"]
        and a_error["ip_a"] <= gates["candidate_a_maximum_ip_error_a"])

    event_count = len(event_rows)
    contained = 0
    total_event_observations = 0
    for item in event_rows:
        key = item["axis_sign"]
        index = int(item["effect_age"]) - 1
        center = np.asarray(item["center"])
        half_width = np.asarray(item["half_width"])
        for row in observations[key]:
            total_event_observations += 1
            contained += int(bool(np.all(np.abs(row[index] - center) <= half_width + 1e-15)))
    containment = contained / total_event_observations if total_event_observations else 0.0
    maximum_event_r_width = max((row["full_width"][0] for row in event_rows), default=math.inf)
    non_event = common_metrics["maximum_non_event_absolute_error"]
    candidate_b_passed = bool(
        rule["minimum_event_cell_count"] <= event_count <= rule["maximum_event_cell_count"]
        and containment >= gates["required_event_containment_fraction"]
        and maximum_event_r_width <= gates["candidate_b_maximum_event_r_full_width_m"]
        and non_event["r_geo_m"] <= gates["candidate_b_maximum_non_event_r_error_m"]
        and non_event["z_geo_m"] <= gates["candidate_b_maximum_non_event_z_error_m"]
        and non_event["ip_a"] <= gates["candidate_b_maximum_non_event_ip_error_a"]
        and common_metrics["maximum_non_event_scaled_absolute_error"]
        <= gates["candidate_b_maximum_non_event_scaled_absolute_error"])

    payload = {
        "schema_version": "rgeo-zgeo-1ms-id2z34-event-set-payload-v1",
        "effect_ages": list(range(1, 18)),
        "output_order": list(OUTPUT_KEYS),
        "point_centers": {key: value.tolist() for key, value in centers.items()},
        "event_sets": event_rows,
        "candidate_a": {"class": stage["candidates"]["candidate_a"],
                        "passed": candidate_a_passed,
                        "metrics": {"maximum_absolute_error": a_error}},
        "candidate_b": {"class": stage["candidates"]["candidate_b"],
                        "passed": candidate_b_passed,
                        "metrics": {
                            "event_cell_count": event_count,
                            "event_containment_fraction": containment,
                            "maximum_event_r_full_width_m": maximum_event_r_width,
                            "maximum_non_event_absolute_error": non_event,
                            "maximum_non_event_scaled_absolute_error":
                                common_metrics["maximum_non_event_scaled_absolute_error"],
                        }},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    payload["payload_sha256"] = hashlib.sha256(encoded).hexdigest()
    if candidate_a_passed:
        selected = "candidate_a"
    elif candidate_b_passed:
        selected = "candidate_b"
    else:
        selected = None
    return {"payload": payload, "selected_candidate": selected}


def execute(config: Path = CONFIG, source_revision: str = "UNKNOWN") -> dict[str, Any]:
    stage, evidence = load(config)
    fitted = fit(stage, evidence)
    selected = fitted["selected_candidate"]
    if selected == "candidate_a":
        route = stage["routes"]["candidate_a_pass"]
    elif selected == "candidate_b":
        route = stage["routes"]["candidate_b_pass"]
    else:
        route = stage["routes"]["both_fail"]
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": selected is not None,
        "route": route,
        "selected_candidate": selected,
        "model_payload": fitted["payload"],
        "models_fit_or_updated": 2,
        "fit_family_count": 8,
        "zero_fit_family_count": 2,
        "calibration_or_holdout_reads": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "claim_boundary": stage["claim_boundary"],
    }


def write_new(path: Path, value: dict[str, Any]) -> None:
    output = _inside(path, "output")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = execute(args.config, args.source_revision)
    except Exception as exc:
        stage = _read(args.config)
        result = {
            "schema_version": SCHEMA,
            "source_revision": args.source_revision,
            "stage_config_sha256": _sha(args.config),
            "passed": False,
            "route": stage["routes"]["input_fail"],
            "failures": [f"{type(exc).__name__}:{exc}"],
            "models_fit_or_updated": 0,
            "calibration_or_holdout_reads": 0,
            "tsc_calls": 0,
            "plant_advances": 0,
        }
    write_new(args.output, result)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
