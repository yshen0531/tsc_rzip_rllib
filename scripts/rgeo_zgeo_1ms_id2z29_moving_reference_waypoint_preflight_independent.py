#!/usr/bin/env python3
"""Independent recomputation of the zero-TSC ID-2Z29 preflight."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z28_event_value_model as z28  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z29_moving_reference_waypoint_preflight.json"
CONFIG_SHA256 = "62b7c94ea4a78e7f0181c95d79cb5d79aec2678349a97e2f597fd5646a0dcc64"
SCHEMA = "rgeo-zgeo-1ms-id2z29-moving-reference-waypoint-preflight-independent-v1"


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


def _rows(stage: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    token_ids = stage["token_ids"]
    index_rows = np.indices((5,) * 8, dtype=np.int8).reshape(8, -1).T
    token_values = np.asarray([z28.TOKEN_COEFFICIENTS[name] for name in token_ids], float)
    prediction = np.zeros((len(index_rows), 8, 3), float)
    kernels = {key: np.asarray(model["causal_fir_kernel"][key], float)
               for key in ("q_r", "q_z")}
    coefficients = token_values[index_rows]
    for issue in range(8):
        for effect in range(issue, 8):
            prediction[:, effect] += (
                coefficients[:, issue, 0, None] * kernels["q_r"][effect - issue]
                + coefficients[:, issue, 1, None] * kernels["q_z"][effect - issue])
    rows: list[dict[str, Any]] = []
    for direction_index in range(8):
        angle = direction_index * math.pi / 4.0
        direction = np.asarray((math.cos(angle), math.sin(angle)))
        reference = np.arange(1, 9)[:, None] / 8.0 * 0.0001 * direction
        error = np.linalg.norm(prediction[:, :, :2] - reference, axis=2)
        path = np.max(error, axis=1)
        endpoint = error[:, 7]
        ip = np.max(np.abs(prediction[:, :, 2]), axis=1)
        selected = int(np.lexsort((np.arange(len(index_rows)), ip, endpoint, path))[0])
        progress = float(prediction[selected, 7, :2] @ direction)
        passed = bool(path[selected] <= 0.000025 and endpoint[selected] <= 0.000025
                      and progress >= 0.00008 and ip[selected] <= 100.0)
        rows.append({"direction_index": direction_index,
                     "selected_tokens": [token_ids[int(v)] for v in index_rows[selected]],
                     "maximum_predicted_path_error_m": float(path[selected]),
                     "predicted_endpoint_error_m": float(endpoint[selected]),
                     "predicted_directional_progress_m": progress,
                     "maximum_predicted_ip_excursion_a": float(ip[selected]),
                     "passed": passed})
    return rows


def _current(fields: Sequence[str], turns: Sequence[Decimal]) -> np.ndarray:
    return np.asarray([float(Decimal(value.strip()) * Decimal("1000") / turn)
                       for value, turn in zip(fields, turns)], float)


def _stream_checks(primary: dict[str, Any]) -> list[dict[str, Any]]:
    z26_stage = _read(ROOT / "configs/rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight.json")
    base = _read(ROOT / z26_stage["evidence"]["base_tsc_config"]["path"])
    turns = tuple(Decimal(str(v)) for v in base["turns_display_order"])
    lower = np.asarray(base["min_current_a_display_order"], float)
    upper = np.asarray(base["max_current_a_display_order"], float)
    checks = []
    for row in primary["exact_action_streams"]:
        currents = [_current(fields, turns) for fields in row["card15_targets"]]
        maximum = max(float(np.max(np.abs(currents[i] - currents[i - 1])))
                      for i in range(1, len(currents)))
        headroom = min(float(np.min(np.minimum(value - lower, upper - value)))
                       for value in currents)
        phase = int(row["phase_issue"])
        closure = bool(row["closure_exact"] and row["closure_issue"] == phase + 15)
        passed = bool(len(currents) == 73 and closure and maximum <= .300000000001
                      and headroom >= 0.0)
        checks.append({"direction_index": row["direction_index"],
                       "phase_issue": phase, "maximum_issued_delta_a": maximum,
                       "minimum_absolute_current_headroom_a": headroom,
                       "closure_exact": closure, "passed": passed})
    return checks


def _close(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (float, int)) and isinstance(right, (float, int)):
        return math.isclose(float(left), float(right), rel_tol=1e-11, abs_tol=1e-11)
    return left == right


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
    expected_rows = _rows(stage, evidence["id2z28_result"]["model"])
    failures: list[str] = []
    if len(primary.get("direction_results", [])) != 8:
        failures.append("DIRECTION_COUNT")
    else:
        keys = ("direction_index", "selected_tokens", "maximum_predicted_path_error_m",
                "predicted_endpoint_error_m", "predicted_directional_progress_m",
                "maximum_predicted_ip_excursion_a", "passed")
        for expected, observed in zip(expected_rows, primary["direction_results"]):
            for key in keys:
                if not _close(expected[key], observed.get(key)):
                    failures.append(f"DIRECTION:{expected['direction_index']}:{key}")
    stream_checks = _stream_checks(primary)
    waypoint_passed = all(row["passed"] for row in expected_rows)
    action_passed = len(stream_checks) == 16 and all(row["passed"] for row in stream_checks)
    if not waypoint_passed:
        route = stage["routes"]["waypoint_fail"]
    elif not action_passed:
        route = stage["routes"]["action_fail"]
    else:
        route = stage["routes"]["pass"]
    if primary.get("route") != route:
        failures.append("ROUTE")
    if primary.get("source_revision") != source_revision:
        failures.append("SOURCE_REVISION")
    if any(primary.get(key) != 0 for key in
           ("models_fit_or_updated", "tsc_calls", "plant_advances",
            "calibration_or_holdout_reads")):
        failures.append("NONZERO_FORBIDDEN_WORK")
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "primary_sha256": _sha(primary_path), "audit_passed": not failures,
            "failures": failures, "recomputed_route": route,
            "recomputed_direction_results": expected_rows,
            "recomputed_stream_checks": stream_checks,
            "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
            "calibration_or_holdout_reads": 0,
            "claim_boundary": stage["claim_boundary"]}


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
                  "audit_passed": False,
                  "failures": [f"{type(exc).__name__}:{exc}"],
                  "models_fit_or_updated": 0, "tsc_calls": 0,
                  "plant_advances": 0, "calibration_or_holdout_reads": 0}
    write_new(args.output, result)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
