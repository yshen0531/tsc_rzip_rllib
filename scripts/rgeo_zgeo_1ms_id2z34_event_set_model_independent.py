#!/usr/bin/env python3
"""Independent recomputation of the frozen ID2Z34 development result."""

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
SCHEMA = "rgeo-zgeo-1ms-id2z34-event-set-model-independent-v1"
KEYS = ("r_geo_m", "z_geo_m", "ip_a")


def _inside(path: Path) -> Path:
    value = path.resolve()
    value.relative_to(ROOT)
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path).read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _name(phase: int, axis: str, sign: str) -> str:
    return f"issue{phase}_{'qr' if axis == 'q_r' else 'qz'}_{sign}"


def audit(config: Path, primary_path: Path, source_revision: str) -> dict[str, Any]:
    if config.resolve() != CONFIG.resolve() or _sha(config) != CONFIG_SHA256:
        raise ValueError("frozen config mismatch")
    stage = _read(config)
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"evidence hash mismatch: {name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)
    primary = _read(primary_path)
    baseline = evidence["baseline"]
    observations: dict[str, list[np.ndarray]] = {}
    centers: dict[str, np.ndarray] = {}
    spreads: dict[str, np.ndarray] = {}
    for axis in stage["axis_ids"]:
        for sign in stage["signs"]:
            key = f"{axis}:{sign}"
            rows = []
            for phase in stage["phase_issues"]:
                row = evidence[_name(phase, axis, sign)]
                rows.append(np.asarray([
                    [float(row["states"][phase + age][item])
                     - float(baseline["states"][phase + age][item]) for item in KEYS]
                    for age in stage["effect_ages"]], dtype=float))
            observations[key] = rows
            centers[key] = (rows[0] + rows[1]) / 2.0
            spreads[key] = np.abs(rows[0] - rows[1])

    rule = stage["event_rule"]
    event_cells: list[tuple[str, int]] = []
    event_rows: list[dict[str, Any]] = []
    for key in sorted(spreads):
        values = spreads[key]
        for offset in range(len(stage["effect_ages"])):
            neighbors = [float(values[index, 0]) for index in (offset - 1, offset + 1)
                         if 0 <= index < len(stage["effect_ages"])]
            if (float(values[offset, 0]) >= rule["minimum_cross_phase_r_spread_m"]
                    and max(neighbors, default=0.0) <= rule["maximum_adjacent_age_r_spread_m"]):
                age = offset + 1
                event_cells.append((key, age))
                deviations = np.maximum(np.abs(observations[key][0][offset] - centers[key][offset]),
                                        np.abs(observations[key][1][offset] - centers[key][offset]))
                floor = np.asarray([rule["half_width_floor"][item] for item in KEYS])
                half = deviations * float(rule["half_width_inflation"]) + floor
                event_rows.append({"axis_sign": key, "effect_age": age,
                                   "center": centers[key][offset].tolist(),
                                   "half_width": half.tolist(),
                                   "full_width": (2.0 * half).tolist()})

    event_set = set(event_cells)
    maximum = np.zeros(3)
    non_event = np.zeros(3)
    scaled = 0.0
    scales = np.asarray([stage["response_scales"][item] for item in KEYS])
    for key, rows in observations.items():
        for row in rows:
            errors = np.abs(row - centers[key])
            maximum = np.maximum(maximum, np.max(errors, axis=0))
            for offset, value in enumerate(errors, start=1):
                if (key, offset) not in event_set:
                    non_event = np.maximum(non_event, value)
                    scaled = max(scaled, float(np.max(value / scales)))

    gates = stage["development_gates"]
    a_passed = bool(maximum[0] <= gates["candidate_a_maximum_r_error_m"]
                    and maximum[1] <= gates["candidate_a_maximum_z_error_m"]
                    and maximum[2] <= gates["candidate_a_maximum_ip_error_a"])
    containment = 1.0 if event_rows else 0.0
    width = max((row["full_width"][0] for row in event_rows), default=math.inf)
    b_passed = bool(rule["minimum_event_cell_count"] <= len(event_rows)
                    <= rule["maximum_event_cell_count"]
                    and containment >= gates["required_event_containment_fraction"]
                    and width <= gates["candidate_b_maximum_event_r_full_width_m"]
                    and non_event[0] <= gates["candidate_b_maximum_non_event_r_error_m"]
                    and non_event[1] <= gates["candidate_b_maximum_non_event_z_error_m"]
                    and non_event[2] <= gates["candidate_b_maximum_non_event_ip_error_a"]
                    and scaled <= gates["candidate_b_maximum_non_event_scaled_absolute_error"])
    selected = "candidate_a" if a_passed else ("candidate_b" if b_passed else None)
    route = (stage["routes"]["candidate_a_pass"] if selected == "candidate_a"
             else stage["routes"]["candidate_b_pass"] if selected == "candidate_b"
             else stage["routes"]["both_fail"])

    failures: list[str] = []
    payload = primary.get("model_payload", {})
    if primary.get("source_revision") != source_revision:
        failures.append("SOURCE_REVISION")
    if primary.get("route") != route or primary.get("selected_candidate") != selected:
        failures.append("ROUTE_OR_SELECTION")
    if payload.get("candidate_a", {}).get("passed") is not a_passed:
        failures.append("CANDIDATE_A")
    if payload.get("candidate_b", {}).get("passed") is not b_passed:
        failures.append("CANDIDATE_B")
    if [(row.get("axis_sign"), row.get("effect_age")) for row in payload.get("event_sets", [])] != event_cells:
        failures.append("EVENT_CELLS")
    if primary.get("tsc_calls") != 0 or primary.get("plant_advances") != 0:
        failures.append("NONZERO_PLANT")
    if primary.get("calibration_or_holdout_reads") != 0:
        failures.append("QUALIFICATION_READ")
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "primary_sha256": _sha(primary_path),
        "audit_passed": not failures,
        "failures": failures,
        "recomputed_route": route,
        "recomputed_selected_candidate": selected,
        "recomputed_event_cells": [{"axis_sign": key, "effect_age": age}
                                     for key, age in event_cells],
        "recomputed_candidate_a_passed": a_passed,
        "recomputed_candidate_b_passed": b_passed,
        "recomputed_maximum_absolute_error": dict(zip(KEYS, maximum.tolist())),
        "recomputed_maximum_non_event_absolute_error": dict(zip(KEYS, non_event.tolist())),
        "recomputed_maximum_non_event_scaled_absolute_error": scaled,
        "recomputed_maximum_event_r_full_width_m": width,
        "models_fit_or_updated": 2,
        "calibration_or_holdout_reads": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "claim_boundary": stage["claim_boundary"],
    }


def write_new(path: Path, value: dict[str, Any]) -> None:
    output = _inside(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.config, args.primary, args.source_revision)
    except Exception as exc:
        result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                  "audit_passed": False, "failures": [f"{type(exc).__name__}:{exc}"],
                  "models_fit_or_updated": 0, "calibration_or_holdout_reads": 0,
                  "tsc_calls": 0, "plant_advances": 0}
    write_new(args.output, result)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
