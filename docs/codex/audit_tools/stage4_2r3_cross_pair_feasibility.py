#!/usr/bin/env python3
"""Exploratory same-clock cross-pair analysis for the completed R3 state bank.

R3's preregistered verdict is immutable.  This audit evaluates whether other
same-clock endpoint pairings in the completed 54-state bank can inform a new,
independently preregistered state-generation design.  It does not select R3
control cases and does not alter any R3 summary or gate.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


N_COILS = 14
N_WIRES = 48
DT_S = 0.01
VISIBLE_GATE = {
    "R_abs_difference_m_max": 0.0005,
    "Z_abs_difference_m_max": 0.0005,
    "Ip_abs_difference_A_max": 2000.0,
    "vR_abs_difference_m_per_s_max": 0.02,
    "vZ_abs_difference_m_per_s_max": 0.02,
    "coil_max_abs_difference_A_max": 2000.0,
    "coil_rms_difference_A_max": 500.0,
    "action_max_abs_difference_max": 1e-12,
}


def read_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def rms(value: np.ndarray) -> float:
    array = np.asarray(value, dtype=float)
    return float(np.sqrt(np.mean(array**2)))


def endpoint(result: dict[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    trajectory = result["trajectory"]
    final = trajectory[-1]
    previous = trajectory[-2]
    initial = trajectory[0]
    wire = np.asarray(final["wire_currents_a"], dtype=float).reshape(N_WIRES)
    return {
        "experiment_id": str(result["experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_order": str(spec["history_order"]),
        "direction_index": int(spec["nullspace_direction_index"]),
        "amplitude_fraction": float(spec["amplitude_fraction"]),
        "settle_steps": int(spec["settle_steps"]),
        "horizon_steps": int(spec["horizon_steps"]),
        "snapshot_time_ms": int(
            result["restart_snapshot"]["snapshot_time_ms"]
        ),
        "R": float(final["R"]),
        "Z": float(final["Z"]),
        "Ip": float(final["Ip"]),
        "vR": (float(final["R"]) - float(previous["R"])) / DT_S,
        "vZ": (float(final["Z"]) - float(previous["Z"])) / DT_S,
        "coil": np.asarray(final["currents_a_tsc"], dtype=float).reshape(
            N_COILS
        ),
        "action": np.asarray(final["action_norm_tsc"], dtype=float).reshape(
            N_COILS
        ),
        "wire": wire,
        "wire_rms_A": rms(wire),
        "initial_R": float(initial["R"]),
        "initial_Z": float(initial["Z"]),
        "initial_Ip": float(initial["Ip"]),
        "initial_coil": np.asarray(
            initial["currents_a_tsc"], dtype=float
        ).reshape(N_COILS),
    }


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    coil_difference = left["coil"] - right["coil"]
    action_difference = left["action"] - right["action"]
    wire_difference = left["wire"] - right["wire"]
    metrics = {
        "R_abs_difference_m": abs(left["R"] - right["R"]),
        "Z_abs_difference_m": abs(left["Z"] - right["Z"]),
        "Ip_abs_difference_A": abs(left["Ip"] - right["Ip"]),
        "vR_abs_difference_m_per_s": abs(left["vR"] - right["vR"]),
        "vZ_abs_difference_m_per_s": abs(left["vZ"] - right["vZ"]),
        "coil_max_abs_difference_A": float(
            np.max(np.abs(coil_difference))
        ),
        "coil_rms_difference_A": rms(coil_difference),
        "action_max_abs_difference": float(
            np.max(np.abs(action_difference))
        ),
        "wire_max_abs_difference_A": float(
            np.max(np.abs(wire_difference))
        ),
        "wire_rms_difference_A": rms(wire_difference),
    }
    denominator = max(
        1.0, 0.5 * (left["wire_rms_A"] + right["wire_rms_A"])
    )
    metrics["wire_relative_rms_difference"] = (
        metrics["wire_rms_difference_A"] / denominator
    )
    ratios = [
        metrics["R_abs_difference_m"]
        / VISIBLE_GATE["R_abs_difference_m_max"],
        metrics["Z_abs_difference_m"]
        / VISIBLE_GATE["Z_abs_difference_m_max"],
        metrics["Ip_abs_difference_A"]
        / VISIBLE_GATE["Ip_abs_difference_A_max"],
        metrics["vR_abs_difference_m_per_s"]
        / VISIBLE_GATE["vR_abs_difference_m_per_s_max"],
        metrics["vZ_abs_difference_m_per_s"]
        / VISIBLE_GATE["vZ_abs_difference_m_per_s_max"],
        metrics["coil_max_abs_difference_A"]
        / VISIBLE_GATE["coil_max_abs_difference_A_max"],
        metrics["coil_rms_difference_A"]
        / VISIBLE_GATE["coil_rms_difference_A_max"],
        metrics["action_max_abs_difference"]
        / VISIBLE_GATE["action_max_abs_difference_max"],
    ]
    same_clock = bool(
        left["snapshot_time_ms"] == right["snapshot_time_ms"]
        and left["horizon_steps"] == right["horizon_steps"]
    )
    visible_match = bool(same_clock and max(ratios) <= 1.0)
    centroid_coil = 0.5 * (left["coil"] + right["coil"])
    initial_coil = left["initial_coil"]
    different_initial = bool(
        abs(0.5 * (left["R"] + right["R"]) - left["initial_R"])
        >= 0.0005
        or abs(0.5 * (left["Z"] + right["Z"]) - left["initial_Z"])
        >= 0.0005
        or abs(0.5 * (left["Ip"] + right["Ip"]) - left["initial_Ip"])
        >= 2000.0
        or rms(centroid_coil - initial_coil) >= 500.0
    )
    return {
        "left_experiment_id": left["experiment_id"],
        "right_experiment_id": right["experiment_id"],
        "left_pair_id": left["pair_id"],
        "right_pair_id": right["pair_id"],
        "left_history_order": left["history_order"],
        "right_history_order": right["history_order"],
        "left_direction_index": left["direction_index"],
        "right_direction_index": right["direction_index"],
        "left_amplitude_fraction": left["amplitude_fraction"],
        "right_amplitude_fraction": right["amplitude_fraction"],
        "settle_steps": left["settle_steps"],
        "snapshot_time_ms": left["snapshot_time_ms"],
        "same_preregistered_pair": left["pair_id"] == right["pair_id"],
        "same_snapshot_clock": same_clock,
        **metrics,
        "visible_max_normalized_ratio": max(ratios),
        "visible_match_pass": visible_match,
        "frozen_r3_hidden_gate_pass": bool(
            metrics["wire_max_abs_difference_A"] >= 1000.0
            and metrics["wire_relative_rms_difference"] >= 0.05
        ),
        "exploratory_one_ampere_hidden_gate_pass": bool(
            metrics["wire_max_abs_difference_A"] >= 1.0
            and metrics["wire_relative_rms_difference"] >= 0.05
        ),
        "different_initial_state_pass": different_initial,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw_paths = sorted(args.raw_dir.expanduser().resolve().glob("*.json.gz"))
    results = [read_gzip_json(path) for path in raw_paths]
    if len(results) != 54 or not all(
        bool(result.get("success")) for result in results
    ):
        raise SystemExit("cross-pair audit requires 54 successful R3 raw files")
    endpoints = [endpoint(result) for result in results]
    pairs = [
        compare(endpoints[left], endpoints[right])
        for left in range(len(endpoints))
        for right in range(left + 1, len(endpoints))
        if endpoints[left]["snapshot_time_ms"]
        == endpoints[right]["snapshot_time_ms"]
    ]
    visible = [row for row in pairs if row["visible_match_pass"]]
    calibrated = [
        row
        for row in visible
        if row["exploratory_one_ampere_hidden_gate_pass"]
    ]
    calibrated_different = [
        row for row in calibrated if row["different_initial_state_pass"]
    ]
    top = sorted(
        visible,
        key=lambda row: (
            -float(row["wire_max_abs_difference_A"]),
            -float(row["wire_relative_rms_difference"]),
            float(row["visible_max_normalized_ratio"]),
            str(row["left_experiment_id"]),
            str(row["right_experiment_id"]),
        ),
    )[:100]
    output = {
        "schema_version": 1,
        "stage": "Stage4.2R3",
        "purpose": "exploratory_new_stage_design_only",
        "r3_verdict_changed": False,
        "raw_file_count": len(raw_paths),
        "raw_inventory_digest": hashlib.sha256(
            json.dumps(
                [
                    {
                        "name": path.name,
                        "size_bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                    for path in raw_paths
                ],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "same_clock_pair_count": len(pairs),
        "visible_match_pair_count": len(visible),
        "frozen_r3_gate_pair_count": sum(
            bool(row["frozen_r3_hidden_gate_pass"]) for row in visible
        ),
        "exploratory_one_ampere_gate_pair_count": len(calibrated),
        "exploratory_one_ampere_and_different_initial_pair_count": len(
            calibrated_different
        ),
        "maximum_visible_matched_wire_max_abs_difference_A": max(
            (
                float(row["wire_max_abs_difference_A"])
                for row in visible
            ),
            default=math.nan,
        ),
        "maximum_visible_matched_wire_relative_rms_difference": max(
            (
                float(row["wire_relative_rms_difference"])
                for row in visible
            ),
            default=math.nan,
        ),
        "wire_endpoint_rms_A_min": min(
            float(row["wire_rms_A"]) for row in endpoints
        ),
        "wire_endpoint_rms_A_max": max(
            float(row["wire_rms_A"]) for row in endpoints
        ),
        "top_visible_matched_pairs": top,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in output.items() if key != "top_visible_matched_pairs"}, sort_keys=True))


if __name__ == "__main__":
    main()
