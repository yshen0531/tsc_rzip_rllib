#!/usr/bin/env python3
"""Run the frozen zero-TSC ID-2Z29 waypoint and exact-action preflight."""

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

from scripts import rgeo_zgeo_1ms_id2z28_event_value_model as z28  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z29_moving_reference_waypoint_preflight.json"
CONFIG_SHA256 = "62b7c94ea4a78e7f0181c95d79cb5d79aec2678349a97e2f597fd5646a0dcc64"
SCHEMA = "rgeo-zgeo-1ms-id2z29-moving-reference-waypoint-preflight-result-v1"


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"ID2Z29 {label} leaves repository") from exc
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ID2Z29 JSON object required")
    return value


def load(config: Path = CONFIG) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if config.resolve() != CONFIG.resolve() or _sha(config) != CONFIG_SHA256:
        raise ValueError("ID2Z29 frozen config mismatch")
    stage = _read(config)
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z29-moving-reference-waypoint-preflight-v1",
        "identity": "rgeo-zgeo-1ms-id2z29-moving-reference-waypoint-preflight-v1",
        "stage": "ID-2Z29", "takeover_time_ms": 1100,
        "control_period_ms": 1, "models_fit_or_updated": 0,
        "tsc_calls": 0, "plant_advances": 0,
        "calibration_or_holdout_reads": 0, "waypoint_radius_m": 0.0001,
        "direction_count": 8, "sequence_length": 8,
        "token_ids": ["H", "R+", "R-", "Z+", "Z-"],
        "candidate_count_per_direction": 390625,
        "exact_action_phase_issues": [32, 44],
        "exact_return_bridge_issues": 8,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise ValueError(f"ID2Z29 frozen field changed: {key}")
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"ID2Z29 evidence hash mismatch: {name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)
    result = evidence["id2z28_result"]
    audit = evidence["id2z28_independent"]
    if (result.get("route") != stage["evidence"]["id2z28_result"]["required_route"]
            or result.get("model_validation_passed") is not True
            or result.get("control_utility_passed") is not False
            or result.get("tsc_calls") != 0
            or audit.get("audit_passed") is not True
            or audit.get("primary_sha256") != stage["evidence"]["id2z28_result"]["sha256"]):
        raise ValueError("ID2Z29 ID2Z28 identity mismatch")
    return stage, evidence


def candidates(stage: dict[str, Any], model: dict[str, Any]) -> tuple[list[str], np.ndarray, np.ndarray]:
    token_ids = list(stage["token_ids"])
    indices = np.indices((len(token_ids),) * 8, dtype=np.int8).reshape(8, -1).T
    token_matrix = np.asarray([z28.TOKEN_COEFFICIENTS[token] for token in token_ids], dtype=float)
    prediction = z28.predict_sequence(model, token_matrix[indices])
    if len(indices) != stage["candidate_count_per_direction"]:
        raise ValueError("ID2Z29 candidate enumeration mismatch")
    return token_ids, indices, prediction


def waypoint_rows(stage: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    token_ids, indices, prediction = candidates(stage, model)
    radius = float(stage["waypoint_radius_m"])
    rows: list[dict[str, Any]] = []
    for direction_index in range(int(stage["direction_count"])):
        angle = 2.0 * math.pi * direction_index / int(stage["direction_count"])
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        reference = np.arange(1, 9, dtype=float)[:, None] / 8.0 * radius * direction
        error = np.linalg.norm(prediction[:, :, :2] - reference[None, :, :], axis=2)
        path_error = np.max(error, axis=1)
        endpoint_error = error[:, -1]
        ip_excursion = np.max(np.abs(prediction[:, :, 2]), axis=1)
        order = np.lexsort((np.arange(len(indices)), ip_excursion,
                            endpoint_error, path_error))
        selected = int(order[0])
        endpoint = prediction[selected, -1, :2]
        progress = float(endpoint @ direction)
        gate = stage["gates"]
        passed = bool(
            path_error[selected] <= gate["maximum_predicted_path_error_m"]
            and endpoint_error[selected] <= gate["maximum_predicted_endpoint_error_m"]
            and progress >= gate["minimum_predicted_directional_progress_m"]
            and ip_excursion[selected] <= gate["maximum_predicted_ip_excursion_a"])
        rows.append({
            "direction_index": direction_index, "angle_rad": angle,
            "unit_direction": direction.tolist(),
            "selected_tokens": [token_ids[int(value)] for value in indices[selected]],
            "maximum_predicted_path_error_m": float(path_error[selected]),
            "predicted_endpoint_error_m": float(endpoint_error[selected]),
            "predicted_directional_progress_m": progress,
            "maximum_predicted_ip_excursion_a": float(ip_excursion[selected]),
            "predicted_response": prediction[selected].tolist(),
            "passed": passed,
        })
    return rows


def execute(config: Path = CONFIG, source_revision: str = "UNKNOWN") -> dict[str, Any]:
    stage, evidence = load(config)
    model = evidence["id2z28_result"]["model"]
    rows = waypoint_rows(stage, model)
    preflight = evidence["id2z26r1_preflight"]
    action_stage = {"sequence_search": {
        "maximum_issued_delta_a": stage["gates"]["maximum_issued_delta_a"],
        "minimum_absolute_current_headroom_a":
            stage["gates"]["minimum_absolute_current_headroom_a"],
    }}
    streams: list[dict[str, Any]] = []
    for phase in stage["exact_action_phase_issues"]:
        for row in rows:
            stream = z28.exact_stream(
                action_stage, preflight, row["selected_tokens"], int(phase))
            stream["direction_index"] = row["direction_index"]
            streams.append(stream)
    waypoint_passed = all(row["passed"] for row in rows)
    action_passed = all(row["passed"] for row in streams)
    if not waypoint_passed:
        route = stage["routes"]["waypoint_fail"]
    elif not action_passed:
        route = stage["routes"]["action_fail"]
    else:
        route = stage["routes"]["pass"]
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": route == stage["routes"]["pass"],
        "route": route, "moving_reference_waypoint_passed": waypoint_passed,
        "exact_action_preflight_passed": action_passed,
        "waypoint_radius_m": stage["waypoint_radius_m"],
        "direction_results": rows, "exact_action_streams": streams,
        "cardinal_feedback_sequences": {
            name: rows[index]["selected_tokens"] for name, index in
            (("r_plus", 0), ("z_plus", 2), ("r_minus", 4), ("z_minus", 6))},
        "future_campaign_contract": stage["future_campaign_contract"],
        "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
        "calibration_or_holdout_reads": 0,
        "source_capture_status": "ID2Z28_FAIL_UNCHANGED",
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
        result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                  "stage_config_sha256": _sha(args.config), "passed": False,
                  "route": stage["routes"]["input_fail"],
                  "failures": [f"{type(exc).__name__}:{exc}"],
                  "models_fit_or_updated": 0, "tsc_calls": 0,
                  "plant_advances": 0, "calibration_or_holdout_reads": 0}
    write_new(args.output, result)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
