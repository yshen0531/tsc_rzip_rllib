#!/usr/bin/env python3
"""Independent evaluator for the frozen zero-TSC ID-2Z28 result."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z24_centered_coallocation_preflight as z24  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z28_event_value_model.json"
CONFIG_SHA256 = "9312d843e60a71bf9fcb785ed0e5727554493a6514d72547191a6d8461221853"
SCHEMA = "rgeo-zgeo-1ms-id2z28-event-value-model-independent-v1"
TOKENS = {
    "H": (0, 0), "R+": (1, 0), "R-": (-1, 0),
    "Z+": (0, 1), "Z-": (0, -1),
}


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository") from exc
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _response(evidence: dict[str, dict[str, Any]], phase: int,
              axis: str, sign: str) -> np.ndarray:
    shorthand = "qr" if axis == "q_r" else "qz"
    row = evidence[f"issue{phase}_{shorthand}_{sign}"]
    center = evidence["baseline"]
    return np.asarray([
        [float(row["states"][phase + h][key])
         - float(center["states"][phase + h][key])
         for key in ("r_geo_m", "z_geo_m", "ip_a")]
        for h in range(1, 9)], dtype=float)


def _model(stage: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> dict[str, np.ndarray]:
    phase = int(stage["training_phase_issue"])
    values: dict[str, np.ndarray] = {}
    for axis in stage["axis_ids"]:
        odd = (_response(evidence, phase, axis, "plus")
               - _response(evidence, phase, axis, "minus")) / 2.0
        values[axis] = np.vstack((odd[0], np.diff(odd, axis=0)))
    return values


def _predict(kernels: dict[str, np.ndarray], coefficients: np.ndarray) -> np.ndarray:
    result = np.zeros((len(coefficients), 8, 3), dtype=float)
    for issue in range(8):
        for effect in range(issue, 8):
            result[:, effect, :] += (
                coefficients[:, issue, 0, None] * kernels["q_r"][effect - issue]
                + coefficients[:, issue, 1, None] * kernels["q_z"][effect - issue])
    return result


def _score(stage: dict[str, Any], center: dict[str, Any], phase: int,
           response: np.ndarray) -> np.ndarray:
    source = center["states"][0]
    rows: list[np.ndarray] = []
    for h in stage["sequence_search"]["score_horizons"]:
        state = center["states"][phase + h]
        previous = center["states"][phase + h - 1]
        delta = response[:, h - 1]
        prior = response[:, h - 2]
        distance = np.hypot(
            float(state["r_geo_m"]) + delta[:, 0] - float(source["r_geo_m"]),
            float(state["z_geo_m"]) + delta[:, 1] - float(source["z_geo_m"])) / 0.025
        speed = np.hypot(
            float(state["r_geo_m"]) + delta[:, 0]
            - float(previous["r_geo_m"]) - prior[:, 0],
            float(state["z_geo_m"]) + delta[:, 1]
            - float(previous["z_geo_m"]) - prior[:, 1]) / 0.001 / 0.1
        ip = np.abs(float(state["ip_a"]) + delta[:, 2] - float(source["ip_a"])) \
            / abs(float(source["ip_a"])) / 0.05
        rows.append(np.maximum.reduce((distance, speed, ip)))
    return np.max(np.stack(rows), axis=0)


def _validation(stage: dict[str, Any], evidence: dict[str, dict[str, Any]],
                kernels: dict[str, np.ndarray]) -> dict[str, float | bool]:
    training_phase = int(stage["training_phase_issue"])
    validation_phase = int(stage["validation_phase_issue"])
    scales = np.asarray([0.0001, 0.0001, 25.0])
    scaled_errors: list[float] = []
    cosines: list[float] = []
    velocity_errors: list[float] = []
    truth_h8: list[np.ndarray] = []
    predicted_h8: list[np.ndarray] = []
    for axis in stage["axis_ids"]:
        plus = _response(evidence, training_phase, axis, "plus")
        minus = _response(evidence, training_phase, axis, "minus")
        odd = (plus - minus) / 2.0
        for sign_name, sign in (("plus", 1.0), ("minus", -1.0)):
            truth = _response(evidence, validation_phase, axis, sign_name)
            prediction = sign * odd
            scaled_errors.extend(((prediction - truth) / scales).ravel().tolist())
            for left, right in zip(prediction[:, :2], truth[:, :2]):
                denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
                cosines.append(float(np.dot(left, right) / denominator) if denominator else -1.0)
            velocity_errors.append(float(np.linalg.norm(
                ((prediction[7, :2] - prediction[6, :2])
                 - (truth[7, :2] - truth[6, :2])) / 0.001)))
            truth_h8.append(truth[7, :2])
            predicted_h8.append(prediction[7, :2])
    regrets: list[float] = []
    for index in range(64):
        angle = 2.0 * math.pi * index / 64.0
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        truth_value = np.asarray(truth_h8) @ direction
        predicted_value = np.asarray(predicted_h8) @ direction
        regrets.append(float(np.max(truth_value)
                             - truth_value[int(np.argmax(predicted_value))]))
    error = np.asarray(scaled_errors)
    result: dict[str, float | bool] = {
        "scaled_response_rmse": float(np.sqrt(np.mean(error ** 2))),
        "scaled_absolute_error_p95": float(np.percentile(np.abs(error), 95)),
        "minimum_rz_direction_cosine": min(cosines),
        "maximum_terminal_response_velocity_error_m_per_s": max(velocity_errors),
        "maximum_h8_action_ranking_regret_m": max(regrets),
    }
    gates = stage["validation_gates"]
    result["passed"] = bool(
        result["scaled_response_rmse"] <= gates["maximum_scaled_response_rmse"]
        and result["scaled_absolute_error_p95"] <= gates["maximum_scaled_absolute_error_p95"]
        and result["minimum_rz_direction_cosine"] >= gates["minimum_rz_direction_cosine"]
        and result["maximum_terminal_response_velocity_error_m_per_s"]
        <= gates["maximum_terminal_response_velocity_error_m_per_s"]
        and result["maximum_h8_action_ranking_regret_m"]
        <= gates["maximum_h8_action_ranking_regret_m"])
    return result


def _nomination(stage: dict[str, Any], evidence: dict[str, dict[str, Any]],
                kernels: dict[str, np.ndarray]) -> dict[str, Any]:
    token_names = list(TOKENS)
    token_rows = np.asarray([TOKENS[name] for name in token_names], dtype=float)
    best_index = -1
    best_score = math.inf
    best_tokens: list[str] = []
    center_score = math.nan
    candidate_count = 0
    # Chunking keeps this implementation structurally different from the primary's
    # one-shot Cartesian tensor while evaluating the identical frozen set.
    for prefix in itertools.product(range(5), repeat=3):
        suffix = np.indices((5,) * 5, dtype=np.int8).reshape(5, -1).T
        index_rows = np.column_stack((np.tile(prefix, (len(suffix), 1)), suffix))
        coefficients = token_rows[index_rows]
        prediction = _predict(kernels, coefficients)
        robust = np.maximum(
            _score(stage, evidence["baseline"], 32, prediction),
            _score(stage, evidence["baseline"], 40, prediction))
        local = int(np.argmin(robust))
        if float(robust[local]) < best_score:
            best_score = float(robust[local])
            best_index = candidate_count + local
            best_tokens = [token_names[int(value)] for value in index_rows[local]]
        zero = np.flatnonzero(np.all(index_rows == 0, axis=1))
        if len(zero):
            center_score = float(robust[int(zero[0])])
        candidate_count += len(index_rows)
    if candidate_count != 390625 or best_index < 0 or not math.isfinite(center_score):
        raise ValueError("candidate enumeration incomplete")
    return {
        "candidate_count": candidate_count,
        "selected_tokens": best_tokens,
        "baseline_worst_score": center_score,
        "selected_worst_score": best_score,
        "relative_worst_score_improvement": (center_score - best_score) / center_score,
    }


def _currents(fields: Sequence[str], turns: Sequence[Decimal]) -> np.ndarray:
    return np.asarray([float(Decimal(value.strip()) * Decimal("1000") / turn)
                       for value, turn in zip(fields, turns)], dtype=float)


def _stream_checks(stage: dict[str, Any], preflight: dict[str, Any],
                   primary: dict[str, Any]) -> list[dict[str, Any]]:
    base_spec = stage["evidence"]["id2z26r1_preflight"]
    if _sha(ROOT / base_spec["path"]) != base_spec["sha256"]:
        raise ValueError("preflight identity mismatch")
    center = next(row for row in preflight["prospective_static_streams"]
                  if row["rollout_id"] == "baseline_transition_center")
    center_fields = [tuple(row) for row in center["card15_targets"]]
    # Turns and limits are immutable inputs of the already qualified preflight.
    z26_config_path = ROOT / "configs/rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight.json"
    z26_stage = _read(z26_config_path)
    base_path = ROOT / z26_stage["evidence"]["base_tsc_config"]["path"]
    base = _read(base_path)
    turns = tuple(Decimal(str(value)) for value in base["turns_display_order"])
    lower = np.asarray(base["min_current_a_display_order"], dtype=float)
    upper = np.asarray(base["max_current_a_display_order"], dtype=float)
    checks: list[dict[str, Any]] = []
    for row in primary["prospective_authority_streams"]:
        fields = [tuple(values) for values in row["card15_targets"]]
        currents = [_currents(values, turns) for values in fields]
        maximum_slew = max(float(np.max(np.abs(currents[i] - currents[i - 1])))
                           for i in range(1, len(currents)))
        headroom = min(float(np.min(np.minimum(value - lower, upper - value)))
                       for value in currents)
        phase = int(row["phase_issue"])
        closure = fields[phase + 15] == center_fields[phase + 15]
        passed = bool(len(fields) == 73 and closure
                      and maximum_slew <= 0.300000000001 and headroom >= 0.0)
        checks.append({"phase_issue": phase, "tokens": row["tokens"],
                       "maximum_issued_delta_a": maximum_slew,
                       "minimum_absolute_current_headroom_a": headroom,
                       "closure_exact": closure, "passed": passed})
    return checks


def _close(left: Any, right: Any, tolerance: float = 1e-11) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)
    return left == right


def audit(config: Path, primary_path: Path, source_revision: str) -> dict[str, Any]:
    stage = _read(config)
    if _sha(config) != CONFIG_SHA256 or config.resolve() != CONFIG.resolve():
        raise ValueError("frozen config mismatch")
    evidence: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = ROOT / spec["path"]
        if _sha(path) != spec["sha256"]:
            raise ValueError(f"evidence hash mismatch: {name}")
        if path.suffix == ".json":
            evidence[name] = _read(path)
    primary = _read(primary_path)
    kernels = _model(stage, evidence)
    validation = _validation(stage, evidence, kernels)
    nomination = _nomination(stage, evidence, kernels)
    streams = _stream_checks(stage, evidence["id2z26r1_preflight"], primary)
    failures: list[str] = []
    for key, value in validation.items():
        if not _close(value, primary["validation_metrics"].get(key)):
            failures.append(f"VALIDATION:{key}")
    for key, value in nomination.items():
        if not _close(value, primary["sequence_nomination"].get(key)):
            failures.append(f"NOMINATION:{key}")
    if not all(row["passed"] for row in streams):
        failures.append("EXACT_STREAM")
    utility = nomination["relative_worst_score_improvement"] >= 0.15
    action = all(row["passed"] for row in streams)
    if not bool(validation["passed"]):
        route = stage["routes"]["model_fail"]
    elif not action:
        route = stage["routes"]["action_fail"]
    elif not utility:
        route = stage["routes"]["utility_fail"]
    else:
        route = stage["routes"]["pass"]
    if primary.get("route") != route:
        failures.append("ROUTE")
    if primary.get("source_revision") != source_revision:
        failures.append("SOURCE_REVISION")
    if primary.get("tsc_calls") != 0 or primary.get("plant_advances") != 0:
        failures.append("NONZERO_PLANT")
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "primary_sha256": _sha(primary_path), "audit_passed": not failures,
        "failures": failures, "recomputed_route": route,
        "recomputed_model_validation": validation,
        "recomputed_nomination": nomination,
        "recomputed_stream_checks": streams,
        "models_fit_or_updated": 1, "tsc_calls": 0, "plant_advances": 0,
        "calibration_or_holdout_reads": 0,
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
