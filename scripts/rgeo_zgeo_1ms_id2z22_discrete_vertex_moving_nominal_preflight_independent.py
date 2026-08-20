#!/usr/bin/env python3
"""Structurally separate recomputation of the ID-2Z22 compact result."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z22_discrete_vertex_moving_nominal_preflight.json"
PRIMARY = (ROOT / "docs/codex/audits" /
           "rgeo_zgeo_1ms_id2z22_20260820_db07ba95_v1/result.json")
SCHEMA = "rgeo-zgeo-1ms-id2z22-discrete-vertex-moving-nominal-preflight-independent-v1"


def _inside(path: Path) -> Path:
    value = path.resolve()
    value.relative_to(ROOT)
    return value


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path).read_bytes()).hexdigest()


def _geometry(vectors: Sequence[Sequence[float]], directions: int) -> tuple[float, float]:
    angles = sorted((math.degrees(math.atan2(row[1], row[0])) + 360.0) % 360.0
                    for row in vectors)
    gap = max(angles[(index + 1) % len(angles)]
              + (360.0 if index == len(angles) - 1 else 0.0) - angles[index]
              for index in range(len(angles)))
    weakest = math.inf
    for index in range(directions):
        angle = 2.0 * math.pi * index / directions
        weakest = min(weakest, max(row[0] * math.cos(angle) + row[1] * math.sin(angle)
                                   for row in vectors))
    return gap, weakest


def execute(config: Path = CONFIG, primary_path: Path = PRIMARY) -> dict[str, Any]:
    cfg, primary = _read(config), _read(primary_path)
    failures: list[str] = []
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in cfg["evidence"].items():
        path = _inside(ROOT / spec["path"])
        if _sha(path) != spec["sha256"]:
            failures.append(f"EVIDENCE_HASH:{name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)

    hold = evidence["id2z17_hold"]
    vectors_by_state: dict[int, list[list[float]]] = {52: [], 56: []}
    arm_rows: list[dict[str, Any]] = []
    delta_rows: list[tuple[float, ...]] = []
    for arm in cfg["selected_vertex_ids"]:
        row = evidence[f"id2z17_{arm}"]
        prefix_states = True
        for index in range(49):
            for key in ("time_ms", "r_geo_m", "z_geo_m", "ip_a", "r_mid_m",
                        "active_command_card15_fields", "actual_current_decimal_a_tsc",
                        "wire_current_a"):
                if row["states"][index].get(key) != hold["states"][index].get(key):
                    prefix_states = False
        prefix_actions = all(row["actions"][index]["expected_card15_fields"]
                             == hold["actions"][index]["expected_card15_fields"]
                             for index in range(48))
        if not prefix_states or not prefix_actions:
            failures.append(f"PREFIX:{arm}")
        vectors: dict[int, list[float]] = {}
        for state in (52, 56):
            vectors[state] = [row["states"][state]["r_geo_m"] - hold["states"][state]["r_geo_m"],
                              row["states"][state]["z_geo_m"] - hold["states"][state]["z_geo_m"]]
            vectors_by_state[state].append(vectors[state])
        norms = {state: math.hypot(*vectors[state]) for state in (52, 56)}
        cosine = sum(vectors[52][i] * vectors[56][i] for i in range(2)) / (norms[52] * norms[56])
        delta = tuple(round(row["actions"][48]["target_current_a_tsc"][i]
                            - row["actions"][47]["target_current_a_tsc"][i], 12)
                      for i in range(14))
        delta_rows.append(delta)
        passed = (norms[52] >= cfg["measurement_gates"]["minimum_each_state52_rz_response_m"]
                  and norms[56] >= cfg["measurement_gates"]["minimum_each_state56_rz_response_m"]
                  and cosine >= cfg["measurement_gates"]["minimum_each_state52_state56_cosine"]
                  and max(abs(value) for value in delta) <= .3000000001)
        if not passed:
            failures.append(f"ARM:{arm}")
        arm_rows.append({"arm_id": arm, "state52_norm_m": norms[52],
                         "state56_norm_m": norms[56],
                         "state52_state56_cosine": cosine, "delta_a": list(delta),
                         "passed": passed})

    if len(set(delta_rows)) != 4:
        failures.append("VERTEX_DUPLICATE")
    geometry_rows: list[dict[str, Any]] = []
    for state in (52, 56):
        gap, weakest = _geometry(vectors_by_state[state],
                                 cfg["measurement_gates"]["direction_grid_count"])
        passed = (gap <= cfg["measurement_gates"]["maximum_each_checkpoint_angular_gap_deg"]
                  and weakest >= cfg["measurement_gates"]["minimum_each_checkpoint_weakest_best_projection_m"])
        if not passed:
            failures.append(f"GEOMETRY:{state}")
        geometry_rows.append({"state_index": state, "maximum_angular_gap_deg": gap,
                              "weakest_best_projection_m": weakest, "passed": passed})

    w1_rows = evidence["id2w1_result"]["scientific_metrics"]["common_state_geometry"]
    w25 = next(row for row in w1_rows if row["state_index"] == 25)
    w26 = next(row for row in w1_rows if row["state_index"] == 26)
    if not w25["passed"] or w26["passed"]:
        failures.append("W1_PHASE_WARNING")

    static = primary.get("prospective_static_streams", [])
    if (len(static) != 9 or any(not row.get("passed") for row in static)
            or any(row.get("maximum_issued_delta_a", 1.0) > .3000000001 for row in static)
            or any(row.get("minimum_absolute_current_headroom_a", -1.0) < 0.0 for row in static)):
        failures.append("PRIMARY_STATIC_STREAMS")
    if primary.get("prospective_rollout_ids") != cfg["prospective_rollout_ids"]:
        failures.append("ROLLOUT_MATRIX")

    if primary.get("passed") is not True or primary.get("route") != cfg["routes"]["pass"]:
        failures.append("PRIMARY_VERDICT")
    if primary.get("stage_config_sha256") != _sha(config):
        failures.append("PRIMARY_STAGE_CONFIG")
    for row in geometry_rows:
        match = next(item for item in primary["held_geometry"]
                     if item["state_index"] == row["state_index"])
        if (abs(match["maximum_angular_gap_deg"] - row["maximum_angular_gap_deg"]) > 1e-12
                or abs(match["weakest_best_projection_m"] - row["weakest_best_projection_m"]) > 1e-15):
            failures.append(f"PRIMARY_GEOMETRY:{row['state_index']}")
    return {"schema_version": SCHEMA, "primary_sha256": _sha(primary_path),
            "stage_config_sha256": _sha(config), "audit_passed": not failures,
            "failures": failures, "recomputed_route": (cfg["routes"]["pass"]
                if not failures else cfg["routes"]["input_fail"]),
            "recomputed_arm_metrics": arm_rows,
            "recomputed_held_geometry": geometry_rows,
            "tsc_calls": 0, "plant_advances": 0, "models_fit_or_updated": 0}


def _write_new(path: Path, value: dict[str, Any]) -> None:
    path = _inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--primary", type=Path, default=PRIMARY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.config, args.primary)
    _write_new(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
