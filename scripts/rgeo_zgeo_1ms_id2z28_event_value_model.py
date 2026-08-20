#!/usr/bin/env python3
"""Fit and audit the frozen bounded ID-2Z28 event/value model."""

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

from scripts import rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight as z26  # noqa: E402


z24 = z26.z24
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z28_event_value_model.json"
CONFIG_SHA256 = "9312d843e60a71bf9fcb785ed0e5727554493a6514d72547191a6d8461221853"
SCHEMA = "rgeo-zgeo-1ms-id2z28-event-value-model-result-v1"
TOKEN_COEFFICIENTS = {
    "H": (0, 0), "R+": (1, 0), "R-": (-1, 0),
    "Z+": (0, 1), "Z-": (0, -1),
}


def _error(message: str) -> ValueError:
    return ValueError(f"ID2Z28: {message}")


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
        "schema_version": "rgeo-zgeo-1ms-id2z28-event-value-model-v1",
        "identity": "rgeo-zgeo-1ms-id2z28-event-value-model-v1",
        "stage": "ID-2Z28", "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "prediction_horizons": list(range(1, 9)),
        "training_phase_issue": 32, "validation_phase_issue": 40,
        "axis_ids": ["q_r", "q_z"], "signs": ["plus", "minus"],
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field changed: {key}")
    if (stage["model"].get("candidate_count") != 1
            or stage["model"].get("hyperparameter_search") is not False
            or stage["data_contract"].get("models_fit_or_updated") != 1
            or stage["data_contract"].get("calibration_or_holdout_reads") != 0
            or stage["data_contract"].get("id2z25_fit_weight") != 0):
        raise _error("model/data role changed")
    search = stage["sequence_search"]
    if (search.get("token_ids") != list(TOKEN_COEFFICIENTS)
            or search.get("sequence_length") != 8
            or search.get("candidate_count") != 390625
            or search.get("minimum_relative_worst_score_improvement") != 0.15):
        raise _error("sequence search changed")


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
    result = evidence["id2z27_result"]
    audit = evidence["id2z27_independent"]
    if (result.get("passed") is not True
            or result.get("route") != stage["evidence"]["id2z27_result"]["required_route"]
            or result.get("models_fit_or_updated") != 0
            or audit.get("audit_passed") is not True
            or audit.get("primary_sha256") != stage["evidence"]["id2z27_result"]["sha256"]):
        raise _error("ID2Z27 identity mismatch")
    for name in ("baseline", "issue32_qr_plus", "issue32_qr_minus",
                 "issue32_qz_plus", "issue32_qz_minus", "issue40_qr_plus",
                 "issue40_qr_minus", "issue40_qz_plus", "issue40_qz_minus"):
        row = evidence[name]
        if row.get("passed") is not True or len(row.get("states", [])) != 74:
            raise _error(f"incomplete fit/validation row: {name}")
    return stage, evidence


def _row_name(phase: int, axis: str, sign: str) -> str:
    return f"issue{phase}_{'qr' if axis == 'q_r' else 'qz'}_{sign}"


def response(evidence: dict[str, dict[str, Any]], phase: int,
             axis: str, sign: str) -> np.ndarray:
    baseline = evidence["baseline"]
    row = evidence[_row_name(phase, axis, sign)]
    return np.asarray([
        [float(row["states"][phase + horizon][key])
         - float(baseline["states"][phase + horizon][key])
         for key in ("r_geo_m", "z_geo_m", "ip_a")]
        for horizon in range(1, 9)], dtype=float)


def fit_kernel(stage: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    phase = int(stage["training_phase_issue"])
    odd: dict[str, np.ndarray] = {}
    even: dict[str, np.ndarray] = {}
    kernels: dict[str, np.ndarray] = {}
    for axis in stage["axis_ids"]:
        plus = response(evidence, phase, axis, "plus")
        minus = response(evidence, phase, axis, "minus")
        odd[axis] = (plus - minus) / 2.0
        even[axis] = (plus + minus) / 2.0
        kernels[axis] = np.vstack([odd[axis][0], np.diff(odd[axis], axis=0)])
    payload = {
        "class": stage["model"]["class"], "training_phase_issue": phase,
        "horizons": list(range(1, 9)),
        "odd_step_response": {key: value.tolist() for key, value in odd.items()},
        "even_diagnostic": {key: value.tolist() for key, value in even.items()},
        "causal_fir_kernel": {key: value.tolist() for key, value in kernels.items()},
        "output_order": ["r_geo_m", "z_geo_m", "ip_a"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["payload_sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def validate(stage: dict[str, Any], evidence: dict[str, dict[str, Any]],
             model: dict[str, Any]) -> dict[str, Any]:
    phase = int(stage["validation_phase_issue"])
    scales = np.asarray([stage["response_scales"][key]
                         for key in ("r_geo_m", "z_geo_m", "ip_a")])
    errors: list[float] = []
    cosines: list[float] = []
    velocity_errors: list[float] = []
    true_h8: list[np.ndarray] = []
    pred_h8: list[np.ndarray] = []
    rows: list[dict[str, Any]] = []
    for axis in stage["axis_ids"]:
        odd = np.asarray(model["odd_step_response"][axis], dtype=float)
        for sign_name, sign in (("plus", 1.0), ("minus", -1.0)):
            truth = response(evidence, phase, axis, sign_name)
            predicted = sign * odd
            scaled = (predicted - truth) / scales
            errors.extend(scaled.ravel().tolist())
            local_cosines = []
            for left, right in zip(predicted[:, :2], truth[:, :2]):
                denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
                cosine = float(np.dot(left, right) / denominator) if denominator else -1.0
                cosines.append(cosine); local_cosines.append(cosine)
            velocity_error = float(np.linalg.norm(
                ((predicted[7, :2] - predicted[6, :2])
                 - (truth[7, :2] - truth[6, :2])) / 0.001))
            velocity_errors.append(velocity_error)
            true_h8.append(truth[7, :2]); pred_h8.append(predicted[7, :2])
            rows.append({"axis_id": axis, "sign": sign_name,
                         "scaled_rmse": float(np.sqrt(np.mean(scaled ** 2))),
                         "scaled_absolute_error_p95": float(np.percentile(np.abs(scaled), 95)),
                         "minimum_rz_direction_cosine": min(local_cosines),
                         "terminal_response_velocity_error_m_per_s": velocity_error})
    regrets: list[float] = []
    for index in range(int(stage["validation_gates"]["direction_grid_count"])):
        angle = 2.0 * math.pi * index / int(stage["validation_gates"]["direction_grid_count"])
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        truth_values = np.asarray(true_h8) @ direction
        predicted_values = np.asarray(pred_h8) @ direction
        regrets.append(float(np.max(truth_values) - truth_values[int(np.argmax(predicted_values))]))
    metrics = {
        "scaled_response_rmse": float(np.sqrt(np.mean(np.asarray(errors) ** 2))),
        "scaled_absolute_error_p95": float(np.percentile(np.abs(errors), 95)),
        "minimum_rz_direction_cosine": min(cosines),
        "maximum_terminal_response_velocity_error_m_per_s": max(velocity_errors),
        "maximum_h8_action_ranking_regret_m": max(regrets),
        "per_branch": rows,
    }
    gates = stage["validation_gates"]
    metrics["passed"] = bool(
        metrics["scaled_response_rmse"] <= gates["maximum_scaled_response_rmse"]
        and metrics["scaled_absolute_error_p95"] <= gates["maximum_scaled_absolute_error_p95"]
        and metrics["minimum_rz_direction_cosine"] >= gates["minimum_rz_direction_cosine"]
        and metrics["maximum_terminal_response_velocity_error_m_per_s"]
        <= gates["maximum_terminal_response_velocity_error_m_per_s"]
        and metrics["maximum_h8_action_ranking_regret_m"]
        <= gates["maximum_h8_action_ranking_regret_m"])
    return metrics


def predict_sequence(model: dict[str, Any], coefficients: np.ndarray) -> np.ndarray:
    kernels = {axis: np.asarray(model["causal_fir_kernel"][axis], dtype=float)
               for axis in ("q_r", "q_z")}
    output = np.zeros((len(coefficients), 8, 3), dtype=float)
    for issue in range(8):
        for horizon in range(issue, 8):
            output[:, horizon, :] += (
                coefficients[:, issue, 0, None] * kernels["q_r"][horizon - issue]
                + coefficients[:, issue, 1, None] * kernels["q_z"][horizon - issue])
    return output


def _scores(stage: dict[str, Any], baseline: dict[str, Any], phase: int,
            predicted: np.ndarray) -> np.ndarray:
    source = baseline["states"][0]
    source_ip = abs(float(source["ip_a"]))
    values: list[np.ndarray] = []
    for horizon in stage["sequence_search"]["score_horizons"]:
        state = baseline["states"][phase + horizon]
        previous = baseline["states"][phase + horizon - 1]
        now = predicted[:, horizon - 1, :]
        before = predicted[:, horizon - 2, :]
        distance = np.hypot(
            float(state["r_geo_m"]) + now[:, 0] - float(source["r_geo_m"]),
            float(state["z_geo_m"]) + now[:, 1] - float(source["z_geo_m"])) \
            / float(stage["sequence_search"]["distance_scale_m"])
        speed = np.hypot(
            float(state["r_geo_m"]) + now[:, 0]
            - float(previous["r_geo_m"]) - before[:, 0],
            float(state["z_geo_m"]) + now[:, 1]
            - float(previous["z_geo_m"]) - before[:, 1]) / 0.001 \
            / float(stage["sequence_search"]["speed_scale_m_per_s"])
        ip = np.abs(float(state["ip_a"]) + now[:, 2] - float(source["ip_a"])) \
            / source_ip / float(stage["sequence_search"]["ip_fraction_scale"])
        values.append(np.maximum.reduce([distance, speed, ip]))
    return np.max(np.stack(values), axis=0)


def nominate(stage: dict[str, Any], evidence: dict[str, dict[str, Any]],
             model: dict[str, Any]) -> dict[str, Any]:
    token_ids = list(stage["sequence_search"]["token_ids"])
    indices = np.indices((len(token_ids),) * 8, dtype=np.int8).reshape(8, -1).T
    token_matrix = np.asarray([TOKEN_COEFFICIENTS[token] for token in token_ids], dtype=float)
    predicted = predict_sequence(model, token_matrix[indices])
    phase_scores = {phase: _scores(stage, evidence["baseline"], phase, predicted)
                    for phase in (32, 40)}
    robust = np.maximum(phase_scores[32], phase_scores[40])
    selected = int(np.argmin(robust))
    center_index = int(np.flatnonzero(np.all(indices == 0, axis=1))[0])
    tokens = [token_ids[int(value)] for value in indices[selected]]
    inverse = {"H": "H", "R+": "R-", "R-": "R+", "Z+": "Z-", "Z-": "Z+"}
    baseline_score = float(robust[center_index])
    selected_score = float(robust[selected])
    return {
        "candidate_count": len(indices), "selected_tokens": tokens,
        "opposite_tokens": [inverse[token] for token in tokens],
        "baseline_worst_score": baseline_score,
        "selected_worst_score": selected_score,
        "absolute_worst_score_improvement": baseline_score - selected_score,
        "relative_worst_score_improvement": (baseline_score - selected_score) / baseline_score,
        "phase32_baseline_score": float(phase_scores[32][center_index]),
        "phase32_selected_score": float(phase_scores[32][selected]),
        "phase40_baseline_score": float(phase_scores[40][center_index]),
        "phase40_selected_score": float(phase_scores[40][selected]),
    }


def _combine(left: Sequence[Decimal], right: Sequence[Decimal], sign: int = 1) -> tuple[Decimal, ...]:
    return tuple(a + Decimal(sign) * b for a, b in zip(left, right))


def exact_stream(stage: dict[str, Any], preflight: dict[str, Any], tokens: Sequence[str],
                 phase: int) -> dict[str, Any]:
    center_row = next(row for row in preflight["prospective_static_streams"]
                      if row["rollout_id"] == "baseline_transition_center")
    center = [tuple(row) for row in center_row["card15_targets"]]
    nominal = tuple(Decimal(value) for value in preflight["nominal_field_increment"])
    axes = {key: tuple(Decimal(value) for value in values)
            for key, values in preflight["output_aligned_field_increments"].items()}
    fields = list(center[:phase])
    current = fields[-1]
    for offset, token in enumerate(tokens):
        r_value, z_value = TOKEN_COEFFICIENTS[token]
        increment = nominal
        if r_value:
            increment = _combine(increment, axes["q_r"], r_value)
        if z_value:
            increment = _combine(increment, axes["q_z"], z_value)
        current = z24._combined_step(current, increment)
        fields.append(current)
    return_start = current
    for offset in range(1, 9):
        current = z24._interpolate_target(return_start, center[phase + 15], offset, 8)
        fields.append(current)
    fields.extend(center[phase + 16:])
    preflight_stage = z26._read(z26.CONFIG)
    base = z26._evidence(preflight_stage)["base_tsc_config"]
    turns = tuple(Decimal(str(value)) for value in base["turns_display_order"])
    lower = np.asarray(base["min_current_a_display_order"], dtype=float)
    upper = np.asarray(base["max_current_a_display_order"], dtype=float)
    metrics = z26._metrics(fields, turns, lower, upper)
    closure = fields[phase + 15] == center[phase + 15]
    passed = bool(
        len(fields) == 73 and closure
        and metrics["maximum_issued_delta_a"]
        <= stage["sequence_search"]["maximum_issued_delta_a"] + 1e-12
        and metrics["minimum_absolute_current_headroom_a"]
        >= stage["sequence_search"]["minimum_absolute_current_headroom_a"])
    return {"phase_issue": phase, "tokens": list(tokens),
            "card15_targets": [list(row) for row in fields],
            "closure_issue": phase + 15, "closure_exact": closure,
            **metrics, "passed": passed}


def execute(config: Path = CONFIG, source_revision: str = "UNKNOWN") -> dict[str, Any]:
    stage, evidence = load(config)
    model = fit_kernel(stage, evidence)
    validation = validate(stage, evidence, model)
    nomination = nominate(stage, evidence, model)
    preflight = evidence["id2z26r1_preflight"]
    streams = [exact_stream(stage, preflight, tokens, phase)
               for phase in (32, 40)
               for tokens in (nomination["selected_tokens"], nomination["opposite_tokens"])]
    action_passed = all(row["passed"] for row in streams)
    utility_passed = bool(
        nomination["relative_worst_score_improvement"]
        >= stage["sequence_search"]["minimum_relative_worst_score_improvement"])
    if not validation["passed"]:
        route = stage["routes"]["model_fail"]
    elif not action_passed:
        route = stage["routes"]["action_fail"]
    elif not utility_passed:
        route = stage["routes"]["utility_fail"]
    else:
        route = stage["routes"]["pass"]
    return {"schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "passed": route == stage["routes"]["pass"], "route": route,
            "model_validation_passed": validation["passed"],
            "exact_action_preflight_passed": action_passed,
            "control_utility_passed": utility_passed,
            "model": model, "validation_metrics": validation,
            "sequence_nomination": nomination,
            "prospective_authority_streams": streams,
            "models_fit_or_updated": 1, "tsc_calls": 0, "plant_advances": 0,
            "calibration_or_holdout_reads": 0,
            "claim_boundary": stage["claim_boundary"]}


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
