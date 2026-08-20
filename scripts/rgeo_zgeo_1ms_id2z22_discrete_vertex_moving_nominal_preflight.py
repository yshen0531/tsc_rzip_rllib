#!/usr/bin/env python3
"""ID-2Z22 zero-TSC discrete-vertex moving-nominal preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import rgeo_zgeo_1ms_id2z17_full_f_transient_remaining_basis_beam as z17
import rgeo_zgeo_1ms_id2z18_full_horizon_token_development as z18

CONFIG = (ROOT / "configs" /
          "rgeo_zgeo_1ms_id2z22_discrete_vertex_moving_nominal_preflight.json")
SCHEMA = "rgeo-zgeo-1ms-id2z22-discrete-vertex-moving-nominal-preflight-result-v1"


def _error(message: str) -> ValueError:
    return ValueError(f"ID2Z22: {message}")


def _inside(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise _error(f"{label} escapes repository") from exc
    return resolved


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_inside(path, "JSON path").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise _error(f"JSON object required: {path}")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(_inside(path, "hash path").read_bytes()).hexdigest()


def _require(stage: dict[str, Any]) -> None:
    required = {
        "schema_version": "rgeo-zgeo-1ms-id2z22-discrete-vertex-moving-nominal-preflight-v1",
        "stage": "ID-2Z22", "takeover_time_ms": 1100,
        "control_period_ms": 1, "models_fit_or_updated": 0,
        "maximum_tsc_calls": 0, "maximum_plant_advances": 0,
        "calibration_or_holdout_reads": 0,
        "selected_vertex_ids": ["p00_minus4", "p05_minus4", "p05_plus4", "p06_plus4"],
        "held_evidence_origin_state": 48,
        "held_evidence_check_states": [52, 56],
        "prospective_phase_issue_steps": [24, 32],
        "replacement_duration_issues": 4,
        "resume_full_f_after_replacement": True,
        "full_f_last_issue": 47, "common_horizon_steps": 65,
        "maximum_prospective_rollouts": 10,
        "maximum_prospective_reset_calls": 10,
        "maximum_prospective_advance_attempts": 650,
        "maximum_prospective_gotsc_calls": 650,
        "maximum_prospective_verified_plant_advances": 650,
        "replay_source_rollout_id": "issue24__p05_plus4",
        "replay_fit_weight": 0,
    }
    for key, expected in required.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field mismatch: {key}")
    expected_rollouts = ["baseline_full_f"]
    expected_rollouts += [f"issue{issue}__{arm}" for issue in (24, 32)
                          for arm in required["selected_vertex_ids"]]
    expected_rollouts += ["replay_issue24__p05_plus4"]
    if stage.get("prospective_rollout_ids") != expected_rollouts:
        raise _error("prospective rollout matrix mismatch")
    action = stage.get("action_semantics", {})
    if action != {
        "exact_card15_vertices": True, "continuous_basis_inversion": False,
        "add_then_clip": False, "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True, "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "candidate_replaces_f_within_same_slew_polytope": True,
        "after_four_replacements_resume_f_from_attained_target": True,
    }:
        raise _error("action semantics mismatch")


def _load_evidence(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for name, spec in stage["evidence"].items():
        path = _inside(ROOT / spec["path"], f"evidence {name}")
        if _sha(path) != spec["sha256"]:
            raise _error(f"evidence hash mismatch: {name}")
        if path.suffix == ".json":
            values[name] = _read(path)
    if values["id2z21_result"].get("route") != stage["evidence"]["id2z21_result"]["required_route"]:
        raise _error("ID2Z21 route mismatch")
    if values["id2z21_result"].get("passed") is not False:
        raise _error("ID2Z21 must remain failed")
    if values["id2z21_independent"].get("audit_passed") is not True:
        raise _error("ID2Z21 independent audit mismatch")
    if values["id2z17_independent"].get("audit_passed") is not True:
        raise _error("ID2Z17 independent audit mismatch")
    if values["id2w1_independent"].get("audit_passed") is not True:
        raise _error("ID2W1 independent audit mismatch")
    if values["id2z18_independent"].get("audit_passed") is not True:
        raise _error("ID2Z18 independent audit mismatch")
    return values


def _state_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ("time_ms", "r_geo_m", "z_geo_m", "ip_a", "r_mid_m",
            "active_command_card15_fields", "actual_current_decimal_a_tsc",
            "wire_current_a")
    if any(left.get(key) != right.get(key) for key in keys):
        return False
    semantic = ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv")
    return all(left.get("artifact_sha256", {}).get(key)
               == right.get("artifact_sha256", {}).get(key) for key in semantic)


def _action_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ("issue_step", "effect_state_index", "expected_card15_fields",
            "target_current_a_tsc")
    return all(left.get(key) == right.get(key) for key in keys)


def _response(candidate: dict[str, Any], hold: dict[str, Any], state: int) -> np.ndarray:
    return np.asarray([
        float(candidate["states"][state]["r_geo_m"] - hold["states"][state]["r_geo_m"]),
        float(candidate["states"][state]["z_geo_m"] - hold["states"][state]["z_geo_m"]),
    ])


def _geometry(vectors: Sequence[np.ndarray], count: int) -> dict[str, Any]:
    angles = sorted((math.degrees(math.atan2(float(v[1]), float(v[0]))) + 360.0) % 360.0
                    for v in vectors)
    gaps = [angles[(index + 1) % len(angles)] + (360.0 if index == len(angles) - 1 else 0.0)
            - angles[index] for index in range(len(angles))]
    weakest = math.inf
    weakest_angle = 0.0
    for index in range(count):
        angle = 2.0 * math.pi * index / count
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        best = max(float(np.dot(vector, direction)) for vector in vectors)
        if best < weakest:
            weakest, weakest_angle = best, math.degrees(angle)
    return {"maximum_angular_gap_deg": max(gaps),
            "weakest_best_projection_m": weakest,
            "weakest_direction_deg": weakest_angle,
            "response_vectors_m": [vector.tolist() for vector in vectors]}


def _vertex_delta(row: dict[str, Any]) -> np.ndarray:
    return np.asarray(row["actions"][48]["target_current_a_tsc"], dtype=float) - np.asarray(
        row["actions"][47]["target_current_a_tsc"], dtype=float)


def _build_prospective(stage: dict[str, Any], arm_id: str | None,
                       decision: int | None) -> dict[str, Any]:
    stage18, _, cfg, targets, parent, _ = z18.load(z18.CONFIG)
    horizon = int(stage["common_horizon_steps"])
    prefix = int(stage18["development_first_issue"])
    sequence = list(parent["targets"][:prefix])
    virtual_rows = [z17._extended(row["probe_virtual_action"])
                    for row in parent["actions"][:prefix]]
    current, virtual, q0 = sequence[-1], list(virtual_rows[-1]), targets["q0"]
    for issue in range(prefix, horizon):
        if arm_id is not None and decision is not None and decision <= issue < decision + 4:
            current, virtual = z17._apply_arm(
                current, virtual, arm_id, q0, targets, cfg,
                f"id2z22.issue{decision}.{arm_id}.{issue}")
        elif issue <= int(stage["full_f_last_issue"]):
            current, virtual = z18._apply_token(
                current, virtual, "F", q0, targets, cfg,
                f"id2z22.full_f.{issue}")
        else:
            current, virtual = z18._apply_token(
                current, virtual, "H", q0, targets, cfg,
                f"id2z22.hold.{issue}")
        sequence.append(current); virtual_rows.append(list(virtual))
    actions = z17.z6.z5.z3.z1.c1._actions(sequence, cfg, "id2z22", virtual_rows)
    failures: list[str] = []
    if len(actions) != horizon or len(sequence) != horizon:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(actions):
        if int(action["issue_step"]) != issue or int(action["effect_state_index"]) != issue + 1:
            failures.append(f"ACTION_CLOCK:{issue}")
        if float(action["maximum_issued_delta_a"]) > .3000000001:
            failures.append(f"SLEW:{issue}")
    headroom = float(z17.z6._headroom(sequence, cfg))
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    return {"arm_id": arm_id or "baseline_full_f", "decision_issue": decision,
            "minimum_absolute_current_headroom_a": headroom,
            "maximum_issued_delta_a": max(float(row["maximum_issued_delta_a"])
                                           for row in actions),
            "decision_card15_fields": None if decision is None else
                [actions[index]["expected_card15_fields"]
                 for index in range(decision, decision + 4)],
            "resume_card15_fields": None if decision is None else
                actions[decision + 4]["expected_card15_fields"],
            "passed": not failures, "failures": failures}


def execute(config: Path = CONFIG, source_revision: str = "UNKNOWN") -> dict[str, Any]:
    stage = _read(config)
    _require(stage)
    evidence = _load_evidence(stage)
    hold = evidence["id2z17_hold"]
    selected = [(arm, evidence[f"id2z17_{arm}"]) for arm in stage["selected_vertex_ids"]]

    failures: list[str] = []
    prefix_checks: list[dict[str, Any]] = []
    for arm, row in selected:
        states_exact = (len(row.get("states", [])) == 66 and
                        all(_state_equal(row["states"][index], hold["states"][index])
                            for index in range(49)))
        actions_exact = (len(row.get("actions", [])) == 65 and
                         all(_action_equal(row["actions"][index], hold["actions"][index])
                             for index in range(48)))
        prefix_checks.append({"arm_id": arm, "states_0_48_exact": states_exact,
                              "actions_0_47_exact": actions_exact})
        if not states_exact or not actions_exact:
            failures.append(f"PREFIX:{arm}")

    gates = stage["measurement_gates"]
    arm_metrics: list[dict[str, Any]] = []
    by_state: dict[int, list[np.ndarray]] = {52: [], 56: []}
    deltas: list[np.ndarray] = []
    for arm, row in selected:
        v52, v56 = _response(row, hold, 52), _response(row, hold, 56)
        n52, n56 = float(np.linalg.norm(v52)), float(np.linalg.norm(v56))
        cosine = float(np.dot(v52, v56) / (n52 * n56)) if n52 and n56 else -1.0
        delta = _vertex_delta(row)
        passed = (n52 >= gates["minimum_each_state52_rz_response_m"]
                  and n56 >= gates["minimum_each_state56_rz_response_m"]
                  and cosine >= gates["minimum_each_state52_state56_cosine"]
                  and 0.0 < float(np.max(np.abs(delta))) <= .3000000001)
        arm_metrics.append({"arm_id": arm, "state52_response_m": v52.tolist(),
                            "state56_response_m": v56.tolist(),
                            "state52_norm_m": n52, "state56_norm_m": n56,
                            "state52_state56_cosine": cosine,
                            "exact_issued_delta_a": delta.tolist(),
                            "maximum_absolute_delta_a": float(np.max(np.abs(delta))),
                            "passed": passed})
        if not passed:
            failures.append(f"HELD_RESPONSE:{arm}")
        by_state[52].append(v52); by_state[56].append(v56); deltas.append(delta)

    unique_delta_count = len({tuple(np.round(delta, 12)) for delta in deltas})
    if unique_delta_count != int(gates["minimum_unique_exact_vertex_count"]):
        failures.append("VERTEX_DUPLICATE")
    geometry: list[dict[str, Any]] = []
    for state in (52, 56):
        row = {"state_index": state,
               **_geometry(by_state[state], int(gates["direction_grid_count"]))}
        row["passed"] = (row["maximum_angular_gap_deg"]
                         <= gates["maximum_each_checkpoint_angular_gap_deg"]
                         and row["weakest_best_projection_m"]
                         >= gates["minimum_each_checkpoint_weakest_best_projection_m"])
        geometry.append(row)
        if not row["passed"]:
            failures.append(f"HELD_GEOMETRY:{state}")

    w1_geometry = evidence["id2w1_result"]["scientific_metrics"]["common_state_geometry"]
    state25 = next(row for row in w1_geometry if row["state_index"] == 25)
    state26 = next(row for row in w1_geometry if row["state_index"] == 26)
    w1_phase_warning_passed = bool(state25["passed"] and not state26["passed"])
    if not w1_phase_warning_passed:
        failures.append("W1_PHASE_WARNING_MISMATCH")

    static_streams = [_build_prospective(stage, None, None)]
    static_streams += [_build_prospective(stage, arm, issue)
                       for issue in stage["prospective_phase_issue_steps"]
                       for arm in stage["selected_vertex_ids"]]
    if any(not row["passed"] for row in static_streams):
        failures.append("STATIC_ALLOCATION")

    input_failures = [reason for reason in failures if reason.startswith(("PREFIX", "W1_"))]
    held_failures = [reason for reason in failures
                     if reason.startswith(("HELD_", "VERTEX_"))]
    static_failures = [reason for reason in failures if reason == "STATIC_ALLOCATION"]
    if input_failures:
        route = stage["routes"]["input_fail"]
    elif held_failures:
        route = stage["routes"]["held_geometry_fail"]
    elif static_failures:
        route = stage["routes"]["static_allocation_fail"]
    else:
        route = stage["routes"]["pass"]
    passed = not failures
    return {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": _sha(config), "route": route, "passed": passed,
        "models_fit_or_updated": 0, "tsc_calls": 0, "plant_advances": 0,
        "calibration_or_holdout_reads": 0, "failures": failures,
        "prefix_checks": prefix_checks, "arm_metrics": arm_metrics,
        "held_geometry": geometry, "unique_exact_vertex_count": unique_delta_count,
        "w1_phase_warning": {"passed": w1_phase_warning_passed,
                             "state25": state25, "state26": state26},
        "prospective_static_streams": static_streams,
        "prospective_rollout_ids": stage["prospective_rollout_ids"],
        "claim_boundary": stage["claim_boundary"],
    }


def _write_new(path: Path, value: dict[str, Any]) -> None:
    path = _inside(path, "output")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
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
        result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                  "stage_config_sha256": _sha(args.config),
                  "route": stage["routes"]["input_fail"], "passed": False,
                  "models_fit_or_updated": 0, "tsc_calls": 0,
                  "plant_advances": 0, "calibration_or_holdout_reads": 0,
                  "failures": [f"{type(exc).__name__}:{exc}"]}
    _write_new(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
