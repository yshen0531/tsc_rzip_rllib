#!/usr/bin/env python3
"""ID-2Z24R1 zero-TSC exact centered co-allocation preflight."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z24_centered_coallocation_preflight.json"
SCHEMA = "rgeo-zgeo-1ms-id2z24r1-centered-coallocation-preflight-result-v1"


def _error(message: str) -> ValueError:
    return ValueError(f"ID2Z24R1: {message}")


def _inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise _error(f"{label} escapes repository") from exc
    return value


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise _error(f"JSON object required: {path}")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _format(value: Decimal) -> str:
    text = f"{float(value):.3E}"
    return text[:10] if len(text) > 10 else text + " " * (10 - len(text))


def _decimals(fields: Sequence[str]) -> tuple[Decimal, ...]:
    if len(fields) != 14:
        raise _error("Card15 field count is not fourteen")
    return tuple(Decimal(str(value).strip()) for value in fields)


def _currents(fields: Sequence[str], turns: Sequence[Decimal]) -> np.ndarray:
    values = _decimals(fields)
    return np.asarray([float(value * Decimal(1000) / turn)
                       for value, turn in zip(values, turns)], dtype=float)


def _combined_step(current: Sequence[str], delta: Sequence[Decimal]) -> tuple[str, ...]:
    values = _decimals(current)
    if len(delta) != 14:
        raise _error("delta field count is not fourteen")
    return tuple(_format(value + change) for value, change in zip(values, delta))


def _field_delta(row: dict[str, Any], issue: int) -> tuple[Decimal, ...]:
    current = _decimals(row["actions"][issue - 1]["expected_card15_fields"])
    target = _decimals(row["actions"][issue]["expected_card15_fields"])
    return tuple(right - left for left, right in zip(current, target))


def _scaled(left: Sequence[Decimal], scale: Decimal) -> tuple[Decimal, ...]:
    return tuple(scale * value for value in left)


def _plus(left: Sequence[Decimal], right: Sequence[Decimal], sign: int = 1) -> tuple[Decimal, ...]:
    return tuple(a + Decimal(sign) * b for a, b in zip(left, right))


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z24r1-centered-coallocation-preflight-v1",
        "identity": "rgeo-zgeo-1ms-id2z24r1-centered-coallocation-preflight-v1",
        "stage": "ID-2Z24R1", "takeover_time_ms": 1100,
        "control_period_ms": 1, "models_fit_or_updated": 0,
        "maximum_tsc_calls": 0, "maximum_plant_advances": 0,
        "calibration_or_holdout_reads": 0, "exact_prefix_last_issue": 15,
        "exact_prefix_last_state": 16, "center_first_issue": 16,
        "center_last_issue": 47, "held_tail_first_issue": 48,
        "held_tail_last_issue": 64, "common_horizon_steps": 65,
        "common_terminal_state_index": 65,
        "nominal_share_candidates_descending": ["0.50", "0.45", "0.40", "0.35", "0.30", "0.25"],
        "selection_rule": "largest_candidate_passing_all_exact_static_gates",
        "prospective_phase_issue_steps": [24, 32],
        "same_sign_duration_issues": 8,
        "opposite_sign_nominal_issues_before_exact_finish": 7,
        "exact_cumulative_center_finish_issue_offset": 15,
        "maximum_prospective_rollouts": 15,
        "maximum_prospective_reset_calls": 15,
        "maximum_prospective_advance_attempts": 975,
        "maximum_prospective_gotsc_calls": 975,
        "maximum_prospective_verified_plant_advances": 975,
        "maximum_prospective_retained_states": 990,
        "required_artifact_files_if_all_complete": 4950,
        "retry_after_any_advance_attempt": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field mismatch: {key}")
    axes = [(row.get("axis_id"), row.get("source_rollout"), row.get("scale"))
            for row in stage.get("residual_axes", [])]
    if axes != [("p00_minus", "issue24__p00_minus4", "0.50"),
                ("p05_plus", "issue24__p05_plus4", "1.00"),
                ("p06_plus", "issue24__p06_plus4", "0.50")]:
        raise _error("residual axes changed")
    if len(stage.get("prospective_rollout_ids", [])) != 15:
        raise _error("prospective rollout matrix changed")
    action = stage.get("action_semantics", {})
    required_action = {
        "absolute_card15_targets": True,
        "construct_combined_target_then_quantize_once": True,
        "separately_quantize_then_add": False,
        "continuous_seed_is_not_an_exact_target": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True,
        "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "odd_plant_response_symmetry_assumed": False,
        "last_opposite_sign_slot_targets_exact_center": True,
        "exact_action_closure_is_not_state_recovery": True,
    }
    if action != required_action:
        raise _error("action semantics changed")


def _evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = _inside(ROOT / spec["path"], f"evidence {name}")
        if _sha(path) != spec["sha256"]:
            raise _error(f"evidence hash mismatch: {name}")
        if path.suffix == ".json":
            values[name] = _read(path)
    result, audit = values["id2z23_result"], values["id2z23_independent"]
    if (result.get("route") != stage["evidence"]["id2z23_result"]["required_route"]
            or result.get("passed") is not False
            or result.get("execution_integrity_passed") is not True
            or result.get("raw_integrity_passed") is not True
            or audit.get("audit_passed") is not True
            or audit.get("primary_route") != result.get("route")):
        raise _error("ID2Z23 source verdict/audit mismatch")
    return values


def _response(row: dict[str, Any], baseline: dict[str, Any], state: int) -> np.ndarray:
    return np.asarray([
        float(row["states"][state]["r_geo_m"] - baseline["states"][state]["r_geo_m"]),
        float(row["states"][state]["z_geo_m"] - baseline["states"][state]["z_geo_m"]),
    ])


def _energy_fraction(rows: Sequence[np.ndarray]) -> float:
    matrix = np.asarray(rows, dtype=float)
    mean = np.mean(matrix, axis=0)
    denominator = float(np.sum(matrix * matrix))
    return float(len(matrix) * np.dot(mean, mean) / denominator) if denominator else 0.0


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator else -1.0


def _attribution(stage: dict[str, Any], evidence: dict[str, dict[str, Any]],
                 turns: Sequence[Decimal]) -> dict[str, Any]:
    baseline = evidence["baseline_full_f"]
    branch_names = ["p00_minus", "p05_minus", "p05_plus", "p06_plus"]
    branch_keys = {
        24: [f"issue24_{name}" for name in branch_names],
        32: [f"issue32_{name}" for name in branch_names],
    }
    f = _currents(baseline["actions"][24]["expected_card15_fields"], turns) - _currents(
        baseline["actions"][23]["expected_card15_fields"], turns)
    relative: list[np.ndarray] = []
    for key in branch_keys[24]:
        row = evidence[key]
        vertex = _currents(row["actions"][24]["expected_card15_fields"], turns) - _currents(
            row["actions"][23]["expected_card15_fields"], turns)
        relative.append(vertex - f)
    action_fraction = _energy_fraction(relative)
    response_fractions: dict[str, float] = {}
    for phase, keys in branch_keys.items():
        concatenated = [np.concatenate([_response(evidence[key], baseline, state)
                                        for state in range(phase + 1, phase + 9)])
                        for key in keys]
        response_fractions[str(phase)] = _energy_fraction(concatenated)
    odd: dict[int, dict[int, np.ndarray]] = {}
    for phase in (24, 32):
        plus, minus = evidence[f"issue{phase}_p05_plus"], evidence[f"issue{phase}_p05_minus"]
        odd[phase] = {h: (_response(plus, baseline, phase + h)
                          - _response(minus, baseline, phase + h)) / 2.0 for h in (4, 8)}
    cross = {str(h): _cosine(odd[24][h], odd[32][h]) for h in (4, 8)}
    gates = stage["attribution_gates"]
    passed = (
        gates["minimum_replacement_common_action_energy_fraction"] <= action_fraction
        <= gates["maximum_replacement_common_action_energy_fraction"]
        and gates["minimum_issue24_common_rz_response_energy_fraction"]
        <= response_fractions["24"] <= gates["maximum_issue24_common_rz_response_energy_fraction"]
        and gates["minimum_issue32_common_rz_response_energy_fraction"]
        <= response_fractions["32"] <= gates["maximum_issue32_common_rz_response_energy_fraction"]
        and all(value >= gates["minimum_p05_odd_cross_phase_cosine"] for value in cross.values())
    )
    return {
        "replacement_common_action_energy_fraction": action_fraction,
        "common_rz_response_energy_fraction": response_fractions,
        "p05_odd_cross_phase_cosine": cross,
        "passed": bool(passed),
    }


def _headroom(fields: Sequence[str], turns: Sequence[Decimal],
              lower: np.ndarray, upper: np.ndarray) -> float:
    current = _currents(fields, turns)
    return float(np.min(np.minimum(current - lower, upper - current)))


def _build_center(baseline: dict[str, Any], nominal: Sequence[Decimal],
                  horizon: int) -> list[tuple[str, ...]]:
    fields = [tuple(row["expected_card15_fields"]) for row in baseline["actions"][:16]]
    current = fields[-1]
    for issue in range(16, horizon):
        if issue <= 47:
            current = _combined_step(current, nominal)
        fields.append(current)
    return fields


def _build_branch(center: Sequence[tuple[str, ...]], nominal: Sequence[Decimal],
                  residual: Sequence[Decimal], phase: int, first_sign: int) -> list[tuple[str, ...]]:
    fields = list(center[:16])
    current = fields[-1]
    for issue in range(16, len(center)):
        if issue == phase + 15:
            current = center[issue]
            fields.append(current)
            continue
        delta = nominal
        if phase <= issue < phase + 8:
            delta = _plus(nominal, residual, first_sign)
        elif phase + 8 <= issue < phase + 16:
            delta = _plus(nominal, residual, -first_sign)
        if issue <= 47:
            current = _combined_step(current, delta)
        fields.append(current)
    return fields


def _stream_metrics(fields: Sequence[tuple[str, ...]], turns: Sequence[Decimal],
                    lower: np.ndarray, upper: np.ndarray) -> dict[str, Any]:
    currents = [_currents(row, turns) for row in fields]
    slews = [float(np.max(np.abs(currents[index] - currents[index - 1])))
             for index in range(1, len(currents))]
    headrooms = [_headroom(row, turns, lower, upper) for row in fields]
    return {
        "maximum_issued_delta_a": max(slews) if slews else 0.0,
        "minimum_absolute_current_headroom_a": min(headrooms),
        "terminal_card15_fields": list(fields[-1]),
    }


def _candidate(stage: dict[str, Any], evidence: dict[str, dict[str, Any]],
               turns: Sequence[Decimal], lower: np.ndarray, upper: np.ndarray,
               alpha_text: str) -> dict[str, Any]:
    baseline = evidence["baseline_full_f"]
    f = _field_delta(baseline, 24)
    nominal = _scaled(f, Decimal(alpha_text))
    residuals = {
        axis["axis_id"]: _scaled(
            _field_delta(evidence[{"issue24__p00_minus4": "issue24_p00_minus",
                                   "issue24__p05_plus4": "issue24_p05_plus",
                                   "issue24__p06_plus4": "issue24_p06_plus"}[axis["source_rollout"]]], 24),
            Decimal(axis["scale"]))
        for axis in stage["residual_axes"]
    }
    center = _build_center(baseline, nominal, int(stage["common_horizon_steps"]))
    gate = stage["static_gates"]
    failures: list[str] = []
    local_rows: list[dict[str, Any]] = []
    for issue in range(16, 48):
        previous = center[issue - 1]
        n_target = _combined_step(previous, nominal)
        n_delta = _currents(n_target, turns) - _currents(previous, turns)
        odd_columns: list[np.ndarray] = []
        maximum = 0.0
        headroom = math.inf
        for axis_id, residual in residuals.items():
            plus_target = _combined_step(previous, _plus(nominal, residual, 1))
            minus_target = _combined_step(previous, _plus(nominal, residual, -1))
            plus_delta = _currents(plus_target, turns) - _currents(previous, turns)
            minus_delta = _currents(minus_target, turns) - _currents(previous, turns)
            odd_columns.append((plus_delta - minus_delta) / 2.0)
            maximum = max(maximum, float(np.max(np.abs(plus_delta))),
                          float(np.max(np.abs(minus_delta))))
            headroom = min(headroom, _headroom(plus_target, turns, lower, upper),
                           _headroom(minus_target, turns, lower, upper))
        matrix = np.column_stack(odd_columns)
        singular = np.linalg.svd(matrix, compute_uv=False)
        tolerance = gate["structural_svd_relative_tolerance"] * float(singular[0])
        rank = int(np.sum(singular > tolerance))
        condition = float(singular[0] / singular[2]) if rank == 3 else math.inf
        passed = (rank == gate["required_residual_rank"]
                  and condition <= gate["maximum_residual_condition"]
                  and maximum <= gate["maximum_absolute_issued_delta_a"]
                  and headroom >= gate["minimum_absolute_current_headroom_a"])
        local_rows.append({"issue": issue, "nominal_delta_a": n_delta.tolist(),
                           "residual_rank": rank, "residual_condition": condition,
                           "maximum_signed_issued_delta_a": maximum,
                           "minimum_signed_target_headroom_a": headroom,
                           "passed": bool(passed)})
        if not passed:
            failures.append(f"LOCAL_VERTEX:{issue}")
    streams: list[dict[str, Any]] = [{"rollout_id": "baseline_center",
                                      **_stream_metrics(center, turns, lower, upper),
                                      "closure_exact": True, "prefix_exact": True}]
    for phase in stage["prospective_phase_issue_steps"]:
        for axis_id, residual in residuals.items():
            for first_sign, label in ((1, "plus_then_minus"), (-1, "minus_then_plus")):
                branch = _build_branch(center, nominal, residual, int(phase), first_sign)
                close_issue = int(phase) + 15
                current_before_finish = branch[close_issue - 1]
                naive_finish = _combined_step(
                    current_before_finish, _plus(nominal, residual, -first_sign))
                finish_adjustment = float(np.max(np.abs(
                    _currents(center[close_issue], turns) - _currents(naive_finish, turns))))
                prefix_exact = branch[:int(phase)] == center[:int(phase)]
                closure = branch[close_issue] == center[close_issue]
                row = {"rollout_id": f"issue{phase}__{axis_id}__{label}",
                       **_stream_metrics(branch, turns, lower, upper),
                       "prefix_exact": prefix_exact, "closure_issue": close_issue,
                       "closure_exact": closure,
                       "maximum_exact_finish_adjustment_a": finish_adjustment}
                streams.append(row)
                if (not prefix_exact or not closure
                        or row["maximum_issued_delta_a"] > gate["maximum_absolute_issued_delta_a"]
                        or row["minimum_absolute_current_headroom_a"]
                        < gate["minimum_absolute_current_headroom_a"]):
                    failures.append(f"STREAM:{row['rollout_id']}")
    passed = not failures
    return {
        "nominal_share": alpha_text,
        "nominal_field_increment": [str(value) for value in nominal],
        "residual_field_increments": {key: [str(value) for value in value]
                                      for key, value in residuals.items()},
        "local_vertex_checks": local_rows,
        "prospective_static_streams": streams,
        "passed": passed,
        "failures": failures,
    }


def execute(config: Path = CONFIG, source_revision: str = "UNKNOWN") -> dict[str, Any]:
    config = _inside(config, "config")
    if config != CONFIG.resolve():
        raise _error("alternate config forbidden")
    stage = _read(config)
    _require(stage)
    evidence = _evidence(stage)
    base = evidence["base_tsc_config"]
    turns = tuple(Decimal(str(value)) for value in base["turns_display_order"])
    lower = np.asarray(base["min_current_a_display_order"], dtype=float)
    upper = np.asarray(base["max_current_a_display_order"], dtype=float)
    attribution = _attribution(stage, evidence, turns)
    candidates = [_candidate(stage, evidence, turns, lower, upper, value)
                  for value in stage["nominal_share_candidates_descending"]]
    selected = next((row for row in candidates if row["passed"]), None)
    failures: list[str] = []
    if not attribution["passed"]:
        failures.append("ATTRIBUTION")
    if selected is None:
        failures.append("EXACT_LATTICE")
    if not attribution["passed"]:
        route = stage["routes"]["input_or_attribution_fail"]
    elif selected is None:
        route = stage["routes"]["exact_lattice_fail"]
    elif any(not row["passed"] for row in selected["local_vertex_checks"]):
        route = stage["routes"]["exact_lattice_fail"]
        failures.append("SELECTED_LOCAL_VERTEX")
    elif any(not row["closure_exact"] or not row["prefix_exact"]
             for row in selected["prospective_static_streams"]):
        route = stage["routes"]["static_stream_fail"]
        failures.append("SELECTED_STATIC_STREAM")
    else:
        route = stage["routes"]["pass"]
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": _sha(config), "route": route,
        "passed": not failures, "failures": failures,
        "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
        "calibration_or_holdout_reads": 0,
        "attribution": attribution,
        "candidate_nominal_shares": candidates,
        "selected_nominal_share": None if selected is None else selected["nominal_share"],
        "selected_construction": selected,
        "prospective_rollout_ids": stage["prospective_rollout_ids"],
        "prospective_budget": {
            "rollouts": stage["maximum_prospective_rollouts"],
            "advance_attempts": stage["maximum_prospective_advance_attempts"],
            "retained_states": stage["maximum_prospective_retained_states"],
            "required_artifact_files": stage["required_artifact_files_if_all_complete"],
        },
        "claim_boundary": stage["claim_boundary"],
    }


def _write_new(path: Path, value: dict[str, Any]) -> None:
    output = _inside(path, "output")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
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
            "schema_version": SCHEMA, "source_revision": args.source_revision,
            "stage_config_sha256": _sha(args.config),
            "route": stage["routes"]["input_or_attribution_fail"],
            "passed": False, "failures": [f"{type(exc).__name__}:{exc}"],
            "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
            "calibration_or_holdout_reads": 0,
        }
    _write_new(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
