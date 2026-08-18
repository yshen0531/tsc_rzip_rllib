#!/usr/bin/env python3
"""Run the frozen ID-2Z2 two-decision rolling branch campaign."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z1_late_action_macro_utility as z1  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch.json"
CONFIG_SHA256 = "7560895635e9dfa6e732459ca81dd0f15d96240904f0892b465c53dfcf7318c5"
SCHEMA = "rgeo-zgeo-1ms-id2z2-two-decision-rolling-branch-result-v1"
ARM_IDS = (
    "hold", "p03forward4", "p03unwind4", "p04minus4", "p04plus4",
    "p07minus4", "p07plus4",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(z1.y1r1.y1.x1.inside_root(path, "JSON evidence").read_text(
        encoding="utf-8"))
    if not isinstance(value, dict):
        raise z1.y1r1.y1.x1.InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z2-two-decision-rolling-branch-v1",
        "identity": "rgeo-zgeo-1ms-id2z2-two-decision-rolling-branch-v1",
        "stage": "ID-2Z2",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "maximum_rounds": 2,
        "maximum_branches_per_round": 7,
        "maximum_rollouts": 14,
        "maximum_reset_calls": 14,
        "maximum_advance_attempts": 1106,
        "maximum_gotsc_calls": 1106,
        "maximum_verified_plant_advances": 1106,
        "maximum_retained_states": 1120,
        "required_artifact_files_if_all_complete": 5600,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": (
            "tsc_only_canonical_source_two_decision_full_prefix_branch_search"),
        "data_use": "rolling_sequence_search_and_route_evidence_only",
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise z1.y1r1.y1.x1.InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("rounds") != [
        {"round_id": "round_a_state69", "decision_state_index": 69,
         "macro_first_issue": 69, "macro_last_issue": 72,
         "hold_first_issue": 73, "hold_last_issue": 76,
         "horizon_steps": 77, "terminal_state_index": 77},
        {"round_id": "round_b_state73", "decision_state_index": 73,
         "macro_first_issue": 73, "macro_last_issue": 76,
         "hold_first_issue": 77, "hold_last_issue": 80,
         "horizon_steps": 81, "terminal_state_index": 81},
    ]:
        raise z1.y1r1.y1.x1.InputIntegrityError("round specification changed")
    specs = [
        {"arm_id": "hold", "coordinate": "hold", "level_delta": 0},
        {"arm_id": "p03forward4", "coordinate": "p03", "level_delta": 4},
        {"arm_id": "p03unwind4", "coordinate": "p03", "level_delta": -4},
        {"arm_id": "p04minus4", "coordinate": "p04:minus", "level_delta": 4},
        {"arm_id": "p04plus4", "coordinate": "p04:plus", "level_delta": 4},
        {"arm_id": "p07minus4", "coordinate": "p07:minus", "level_delta": 4},
        {"arm_id": "p07plus4", "coordinate": "p07:plus", "level_delta": 4},
    ]
    if stage.get("candidate_specs") != specs:
        raise z1.y1r1.y1.x1.InputIntegrityError("candidate specs changed")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "minimum_absolute_current_headroom_a": 95.0,
        "full_0p3_a_allowed": True,
        "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": (
            "relative_four_issue_macro_then_four_hold_composed_with_current_exact_target"),
        "offline_round_a_round_b_combination_count": 49,
        "invalid_exact_or_headroom_combination": (
            "exclude_before_tsc_and_forbid_selection"),
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": (
            "exact_noiseless_before_issue"),
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("observability changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise z1.y1r1.y1.x1.InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise z1.y1r1.y1.x1.InputIntegrityError("diagnostic artifacts changed")
    if stage.get("empirical_exploration") != {
        "novel_issue_first": 69,
        "post_successor_step_caps": {"r_geo_m": 0.002, "z_geo_m": 0.002,
                                     "ip_a": 150.0},
        "inner_novel_issue_clearance": {"r_geo_m": 0.025, "z_geo_m": 0.025,
                                         "ip_fraction": 0.05},
        "outer_hard_envelope": {"r_geo_m": 0.05, "z_geo_m": 0.05,
                                "ip_fraction": 0.1},
        "allowed_branch_safe_stop_reasons": [
            "PULSE_CLEARANCE_R", "PULSE_CLEARANCE_Z", "PULSE_CLEARANCE_IP"],
        "continue_next_reset_after_only_allowed_branch_safe_stop": True,
        "abort_campaign_after_any_other_failure": True,
        "stop_before_next_issue_after_any_failure": True,
        "post_action_abort_is_not_a_pre_action_bound": True,
        "simulator_only_empirical_exploration_exception": True,
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("empirical exploration changed")
    if stage.get("measurement_gates") != {
        "baseline_arm_id": "hold",
        "response_horizon_offsets": list(range(1, 9)),
        "active_terminal_offset": 4,
        "persistence_horizon_offsets": list(range(5, 9)),
        "minimum_peak_rz_response_m": 0.00005,
        "minimum_persistent_source_distance_improvement_m": 0.00005,
        "minimum_persistent_states": 3,
        "minimum_active_terminal_source_distance_improvement_m": 0.0001,
        "minimum_terminal_source_distance_improvement_m": 0.0001,
        "maximum_paired_ip_response_a": 150.0,
        "minimum_nominated_arms_per_round": 1,
        "selection_order": [
            "minimum_terminal_source_rz_distance",
            "minimum_active_terminal_source_rz_distance",
            "maximum_median_persistent_improvement",
            "minimum_absolute_terminal_source_ip_offset", "stable_arm_id"],
        "both_rounds_required_for_pass": True,
        "pass_is_two_macro_sequence_nomination_only": True,
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("measurement gates changed")
    if stage.get("prefix_gates") != {
        "round_a_reference_state_count": 70,
        "round_a_reference_action_count": 69,
        "round_b_reference_state_count": 74,
        "round_b_reference_action_count": 73,
        "round_a_all_siblings_exact": True,
        "round_b_all_siblings_exact": True,
        "round_b_matches_selected_round_a": True,
        "sprsina_hash_is_diagnostic_only": True,
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("prefix gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 110000000000,
        "maximum_estimated_raw_bytes": 68000000000,
        "minimum_free_bytes_after_estimate": 40000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("storage gate changed")
    expected_routes = {
        "offline_or_input_fail": "ONE_MS_ID2Z2_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "storage_fail": "ONE_MS_ID2Z2_STORAGE_FAIL_NO_TSC",
        "execution_or_interface_fail": (
            "ONE_MS_ID2Z2_EXECUTION_OR_INTERFACE_FAIL_STOP"),
        "raw_integrity_fail": "ONE_MS_ID2Z2_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "round_a_prefix_mismatch": "ONE_MS_ID2Z2_ROUND_A_PREFIX_MISMATCH_STOP",
        "round_a_utility_fail": (
            "ONE_MS_ID2Z2_ROUND_A_NO_MACRO_STOP_GRAMMAR_REDESIGN"),
        "round_b_prefix_mismatch": "ONE_MS_ID2Z2_ROUND_B_PREFIX_MISMATCH_STOP",
        "round_b_utility_fail": (
            "ONE_MS_ID2Z2_ROUND_B_NO_MACRO_STOP_GRAMMAR_REDESIGN"),
        "pass": (
            "ONE_MS_ID2Z2_TWO_DECISION_ROLLING_BRANCH_PASS_HOLD_CONTROLLER_DESIGN_ONLY"),
    }
    if stage.get("routes") != expected_routes:
        raise z1.y1r1.y1.x1.InputIntegrityError("routes changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any], dict[str, Any]]:
    path = z1.y1r1.y1.x1.inside_root(path, "ID2Z2 config")
    if z1.y1r1.y1.x1.sha256(path) != CONFIG_SHA256:
        raise z1.y1r1.y1.x1.InputIntegrityError("ID2Z2 config hash mismatch")
    stage = _json(path)
    _require(stage)
    required = {
        "design", "id2z1_config", "id2z1_result_report", "id2z1_result",
        "id2z1_independent", "id2z1_selected_compact",
    }
    if set(stage.get("evidence", {})) != required:
        raise z1.y1r1.y1.x1.InputIntegrityError("evidence set changed")
    for name, spec in stage["evidence"].items():
        evidence = z1.y1r1.y1.x1.inside_root(ROOT / spec["path"], name)
        if z1.y1r1.y1.x1.sha256(evidence) != spec["sha256"]:
            raise z1.y1r1.y1.x1.InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / stage["evidence"]["id2z1_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2z1_independent"]["path"])
    selected = _json(ROOT / stage["evidence"]["id2z1_selected_compact"]["path"])
    result_spec = stage["evidence"]["id2z1_result"]
    if (result.get("route") != result_spec["required_route"]
            or result.get("passed") is not True
            or result.get("scientific_metrics", {}).get("selected_arm_id")
            != result_spec["required_selected_arm_id"]
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")):
        raise z1.y1r1.y1.x1.InputIntegrityError("ID2Z1 result is not eligible")
    if (selected.get("rollout_id") != result_spec["required_selected_arm_id"]
            or selected.get("passed") is not True
            or len(selected.get("states", [])) != 74
            or len(selected.get("actions", [])) != 73):
        raise z1.y1r1.y1.x1.InputIntegrityError("selected compact shape changed")
    z1_stage, cfg, targets, _ = z1.load(
        ROOT / stage["evidence"]["id2z1_config"]["path"])
    streams = z1.campaign_streams(z1_stage, cfg, targets)
    selected_stream = next(row for row in streams
                           if row["rollout_id"] == selected["rollout_id"])
    return stage, cfg, targets, selected, selected_stream


def _increment_target(q0: Card15Target, targets: dict[str, Card15Target],
                      spec: dict[str, Any], cfg: Any, name: str) -> Card15Target:
    coordinate = str(spec["coordinate"])
    if coordinate == "p03":
        if int(spec["level_delta"]) > 0:
            return targets["p03:minus"]
        fields = [z1.c1.format_number(float(
            Decimal(q0_field.strip()) * Decimal(2)
            - Decimal(direction_field.strip())))
                  for q0_field, direction_field in zip(
                      q0.card15_fields, targets["p03:minus"].card15_fields)]
        return z1.c1.target_from_fields(fields, cfg, name)
    return targets[coordinate]


def _virtual_step(current: Sequence[float], spec: dict[str, Any]) -> list[float]:
    value = [float(v) for v in current]
    coordinate = str(spec["coordinate"])
    if coordinate == "hold":
        return value
    direction = 1.0
    if coordinate == "p03":
        index = 0
        direction = 1.0 if int(spec["level_delta"]) > 0 else -1.0
    elif coordinate.startswith("p04"):
        index = 1
        direction = 1.0 if coordinate.endswith("plus") else -1.0
    else:
        index = 2
        direction = 1.0 if coordinate.endswith("plus") else -1.0
    value[index] += direction
    return value


def build_round_streams(stage: dict[str, Any], cfg: Any,
                        targets: dict[str, Card15Target],
                        prefix_targets: Sequence[Card15Target],
                        prefix_virtual: Sequence[Sequence[float]],
                        round_index: int, parent_arm_id: str | None) -> list[dict[str, Any]]:
    round_spec = stage["rounds"][round_index]
    decision = int(round_spec["macro_first_issue"])
    horizon = int(round_spec["horizon_steps"])
    if len(prefix_targets) != decision or len(prefix_virtual) != decision:
        raise z1.y1r1.y1.x1.InputIntegrityError("round prefix dimensions changed")
    q0 = targets["q0"]
    rows: list[dict[str, Any]] = []
    for spec in stage["candidate_specs"]:
        arm_id = str(spec["arm_id"])
        rollout_id = f"r{round_index}__{arm_id}"
        sequence = list(prefix_targets)
        virtual = [[float(v) for v in row] for row in prefix_virtual]
        current_target = sequence[-1]
        current_virtual = list(virtual[-1])
        for issue in range(decision, horizon):
            if issue <= int(round_spec["macro_last_issue"]) and arm_id != "hold":
                delta = _increment_target(
                    q0, targets, spec, cfg, f"{rollout_id}.delta.{issue}")
                current_target = z1.c1._translated_target(
                    current_target, q0, delta, cfg, f"{rollout_id}.target.{issue}")
                current_virtual = _virtual_step(current_virtual, spec)
            sequence.append(current_target)
            virtual.append(list(current_virtual))
        actions = z1.c1._actions(sequence, cfg, rollout_id, virtual)
        rows.append({
            **spec,
            "rollout_id": rollout_id,
            "round_index": round_index,
            "round_id": round_spec["round_id"],
            "parent_selected_arm_id": parent_arm_id,
            "cell_id": rollout_id,
            "cell_kind": "two_decision_rolling_branch",
            "context_id": ("canonical_source_selected_z1_state69" if round_index == 0
                           else f"canonical_source_selected_{parent_arm_id}_state73"),
            "direction_id": spec["coordinate"],
            "sign": ("plus" if str(spec["coordinate"]).endswith("plus") else
                     "minus" if str(spec["coordinate"]).endswith("minus") else None),
            "probe_issue_step": decision,
            "probe_duration_issues": 8,
            "non_nominal_issue_steps": list(range(decision, horizon)),
            "targets": sequence,
            "actions": actions,
        })
    if [row["arm_id"] for row in rows] != list(ARM_IDS):
        raise z1.y1r1.y1.x1.InputIntegrityError("arm order changed")
    return rows


def initial_round_streams(stage: dict[str, Any], cfg: Any,
                          targets: dict[str, Card15Target],
                          selected_stream: dict[str, Any]) -> list[dict[str, Any]]:
    decision = int(stage["rounds"][0]["macro_first_issue"])
    prefix_targets = selected_stream["targets"][:decision]
    prefix_virtual = [row["probe_virtual_action"]
                      for row in selected_stream["actions"][:decision]]
    return build_round_streams(
        stage, cfg, targets, prefix_targets, prefix_virtual, 0, None)


def next_round_streams(stage: dict[str, Any], cfg: Any,
                       targets: dict[str, Card15Target],
                       selected_round_a: dict[str, Any]) -> list[dict[str, Any]]:
    decision = int(stage["rounds"][1]["macro_first_issue"])
    return build_round_streams(
        stage, cfg, targets, selected_round_a["targets"][:decision],
        [row["probe_virtual_action"]
         for row in selected_round_a["actions"][:decision]],
        1, str(selected_round_a["arm_id"]))


def _headroom(stream: dict[str, Any], cfg: Any) -> float:
    value = math.inf
    for target in stream["targets"]:
        if len(target.current_a_tsc) != 14:
            raise z1.y1r1.y1.x1.InputIntegrityError("target width changed")
        value = min(value, *(min(float(current) - float(low),
                                float(high) - float(current))
                             for current, low, high in zip(
                                 target.current_a_tsc, cfg.min_current_a_tsc,
                                 cfg.max_current_a_tsc)))
    return value


def _validate_stream(stream: dict[str, Any], round_spec: dict[str, Any],
                     minimum_headroom: float, cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    actions = stream["actions"]
    horizon = int(round_spec["horizon_steps"])
    decision = int(round_spec["macro_first_issue"])
    macro_last = int(round_spec["macro_last_issue"])
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(actions):
        if (action["issue_step"] != issue
                or action["effect_state_index"] != issue + 1
                or float(action["maximum_issued_delta_a"]) > 0.3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(macro_last + 1, horizon):
        if (actions[issue]["expected_card15_fields"]
                != actions[macro_last]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"HOLD_CONTRACT:{issue}")
    for issue in range(decision, macro_last + 1):
        before = actions[issue - 1]["probe_virtual_action"]
        after = actions[issue]["probe_virtual_action"]
        changes = [abs(float(a) - float(b)) for a, b in zip(after, before)]
        nonzero = [value for value in changes[:3] if value > 0.0]
        expected = 0 if stream["arm_id"] == "hold" else 1
        if len(nonzero) != expected or any(value != 1.0 for value in nonzero):
            failures.append(f"VIRTUAL_STEP:{issue}")
    headroom = _headroom(stream, cfg)
    if headroom < minimum_headroom - 1e-9:
        failures.append("ABSOLUTE_CURRENT_HEADROOM")
    return {
        "rollout_id": stream["rollout_id"],
        "round_index": stream["round_index"],
        "arm_id": stream["arm_id"],
        "minimum_absolute_current_headroom_a": headroom,
        "maximum_issued_delta_a": max(float(a["maximum_issued_delta_a"])
                                      for a in actions),
        "passed": not failures,
        "failures": failures,
    }


def _prefix_check(row: dict[str, Any], reference: dict[str, Any],
                  state_count: int, action_count: int,
                  semantic_artifacts: Sequence[str]) -> dict[str, Any]:
    failures: list[str] = []
    if (len(row.get("states", [])) < state_count
            or len(row.get("actions", [])) < action_count):
        failures.append("PREFIX_INCOMPLETE")
    elif (len(reference.get("states", [])) < state_count
          or len(reference.get("actions", [])) < action_count):
        failures.append("REFERENCE_INCOMPLETE")
    else:
        for index in range(state_count):
            current, expected = row["states"][index], reference["states"][index]
            for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if current.get(key) != expected.get(key):
                    failures.append(f"STATE:{index}:{key}")
            for name in semantic_artifacts:
                if (current.get("artifact_sha256", {}).get(name)
                        != expected.get("artifact_sha256", {}).get(name)):
                    failures.append(f"STATE:{index}:artifact:{name}")
        for issue in range(action_count):
            if (row["actions"][issue].get("expected_card15_fields")
                    != reference["actions"][issue].get("expected_card15_fields")):
                failures.append(f"ACTION:{issue}")
    return {"rollout_id": row.get("rollout_id"), "passed": not failures,
            "failures": list(dict.fromkeys(failures))}


safe_stop = z1.safe_stop


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    round_a_rows: list[dict[str, Any]] = []
    combinations: list[dict[str, Any]] = []
    minimum_headroom = math.inf
    try:
        stage, cfg, targets, selected, selected_stream = load(path)
        round_a = initial_round_streams(stage, cfg, targets, selected_stream)
        if len(round_a) != 7:
            raise z1.y1r1.y1.x1.InputIntegrityError("round A budget changed")
        for stream in round_a:
            check = _validate_stream(
                stream, stage["rounds"][0],
                float(stage["action_semantics"]["minimum_absolute_current_headroom_a"]),
                cfg)
            for issue in range(69):
                if (stream["actions"][issue]["expected_card15_fields"]
                        != selected["actions"][issue]["expected_card15_fields"]):
                    check["failures"].append(f"Z1_ACTION_PREFIX:{issue}")
            check["passed"] = not check["failures"]
            minimum_headroom = min(minimum_headroom,
                                   check["minimum_absolute_current_headroom_a"])
            round_a_rows.append(check)
            for child in next_round_streams(stage, cfg, targets, stream):
                child_check = _validate_stream(
                    child, stage["rounds"][1],
                    float(stage["action_semantics"][
                        "minimum_absolute_current_headroom_a"]), cfg)
                child_check["parent_arm_id"] = stream["arm_id"]
                child_check["combination_id"] = (
                    f"{stream['arm_id']}__then__{child['arm_id']}")
                minimum_headroom = min(
                    minimum_headroom,
                    child_check["minimum_absolute_current_headroom_a"])
                combinations.append(child_check)
        if len(combinations) != 49:
            raise z1.y1r1.y1.x1.InputIntegrityError("combination count changed")
        if not all(row["passed"] for row in round_a_rows + combinations):
            raise z1.y1r1.y1.x1.InputIntegrityError(
                "one or more exact candidate combinations are inadmissible")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": z1.y1r1.y1.x1.sha256(path),
        "passed": not failures,
        "failures": failures,
        "round_a_stream_checks": round_a_rows,
        "round_b_combination_checks": combinations,
        "round_b_combination_count": len(combinations),
        "minimum_absolute_current_headroom_a": (
            minimum_headroom if math.isfinite(minimum_headroom) else None),
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def _source_distance(state: dict[str, Any], source: dict[str, Any]) -> float:
    return math.hypot(float(state["r_geo_m"]) - float(source["r_geo_m"]),
                      float(state["z_geo_m"]) - float(source["z_geo_m"]))


def _stopped_metric(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    states = row.get("states", [])
    distance = _source_distance(states[-1], states[0]) if states else None
    return {
        "rollout_id": row.get("rollout_id"),
        "arm_id": row.get("arm_id"),
        "coordinate": row.get("coordinate"),
        "execution_status": ("guarded_safe_stop" if safe_stop(row, stage)
                             else "failure"),
        "stop_reasons": list(row.get("reasons", [])),
        "retained_states": len(states),
        "terminal_source_rz_distance_m": distance,
        "eligible": False,
    }


def round_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                  round_index: int, cfg: Any | None = None) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    spec = stage["rounds"][round_index]
    decision = int(spec["decision_state_index"])
    terminal = int(spec["terminal_state_index"])
    response_indices = [decision + int(value)
                        for value in gates["response_horizon_offsets"]]
    persistence_indices = [decision + int(value)
                           for value in gates["persistence_horizon_offsets"]]
    active_terminal = decision + int(gates["active_terminal_offset"])
    by_arm = {row.get("arm_id"): row for row in rows}
    baseline = by_arm.get(gates["baseline_arm_id"])
    metrics: list[dict[str, Any]] = []
    if (baseline is None or not baseline.get("passed")
            or len(baseline.get("states", [])) != terminal + 1):
        metrics.extend(_stopped_metric(row, stage) for row in rows)
        return {
            "round_index": round_index,
            "round_id": spec["round_id"],
            "baseline_complete": False,
            "branch_metrics": metrics,
            "nominated_arm_ids": [],
            "selected_arm_id": None,
            "selected_rollout_id": None,
            "passed": False,
        }
    source = baseline["states"][0]
    baseline_distances = [_source_distance(state, source)
                          for state in baseline["states"]]
    baseline_metric = {
        "rollout_id": baseline["rollout_id"],
        "arm_id": baseline["arm_id"],
        "coordinate": baseline["coordinate"],
        "execution_status": "complete",
        "source_rz_distance_m": baseline_distances,
        "decision_source_rz_distance_m": baseline_distances[decision],
        "active_terminal_source_rz_distance_m": baseline_distances[active_terminal],
        "terminal_source_rz_distance_m": baseline_distances[terminal],
        "terminal_source_ip_offset_a": (
            float(baseline["states"][terminal]["ip_a"]) - float(source["ip_a"])),
        "eligible": False,
        "baseline": True,
    }
    if cfg is not None:
        baseline_metric.update(z1._trajectory_diagnostics(baseline, source, cfg, stage))
    metrics.append(baseline_metric)
    nominated: list[dict[str, Any]] = []
    for arm_id in ARM_IDS[1:]:
        row = by_arm.get(arm_id)
        if (row is None or not row.get("passed")
                or len(row.get("states", [])) != terminal + 1):
            metrics.append(_stopped_metric(row or {"arm_id": arm_id}, stage))
            continue
        response = [[
            float(row["states"][index]["r_geo_m"])
            - float(baseline["states"][index]["r_geo_m"]),
            float(row["states"][index]["z_geo_m"])
            - float(baseline["states"][index]["z_geo_m"]),
            float(row["states"][index]["ip_a"])
            - float(baseline["states"][index]["ip_a"]),
        ] for index in response_indices]
        peak = max(math.hypot(value[0], value[1]) for value in response)
        max_ip = max(abs(value[2]) for value in response)
        distances = [_source_distance(state, source) for state in row["states"]]
        persistent = [baseline_distances[index] - distances[index]
                      for index in persistence_indices]
        persistent_count = sum(
            value >= float(gates[
                "minimum_persistent_source_distance_improvement_m"])
            for value in persistent)
        active_improvement = (baseline_distances[active_terminal]
                              - distances[active_terminal])
        terminal_improvement = baseline_distances[terminal] - distances[terminal]
        eligible = bool(
            peak >= float(gates["minimum_peak_rz_response_m"])
            and persistent_count >= int(gates["minimum_persistent_states"])
            and active_improvement >= float(gates[
                "minimum_active_terminal_source_distance_improvement_m"])
            and terminal_improvement >= float(gates[
                "minimum_terminal_source_distance_improvement_m"])
            and max_ip <= float(gates["maximum_paired_ip_response_a"]))
        metric = {
            "rollout_id": row["rollout_id"],
            "arm_id": arm_id,
            "coordinate": row["coordinate"],
            "execution_status": "complete",
            "response_state_indices": response_indices,
            "paired_rzi_response": response,
            "maximum_paired_rz_response_m": peak,
            "maximum_paired_ip_response_a": max_ip,
            "source_rz_distance_m": distances,
            "decision_source_rz_distance_m": distances[decision],
            "active_terminal_state_index": active_terminal,
            "active_terminal_source_rz_distance_m": distances[active_terminal],
            "active_terminal_source_distance_improvement_m": active_improvement,
            "persistence_state_indices": persistence_indices,
            "persistent_source_distance_improvement_m": persistent,
            "persistent_improvement_count": persistent_count,
            "median_persistent_source_distance_improvement_m": statistics.median(
                persistent),
            "terminal_source_rz_distance_m": distances[terminal],
            "terminal_source_distance_improvement_m": terminal_improvement,
            "terminal_source_ip_offset_a": (
                float(row["states"][terminal]["ip_a"]) - float(source["ip_a"])),
            "eligible": eligible,
        }
        if cfg is not None:
            metric.update(z1._trajectory_diagnostics(row, source, cfg, stage))
        metrics.append(metric)
        if eligible:
            nominated.append(metric)
    nominated.sort(key=lambda value: (
        float(value["terminal_source_rz_distance_m"]),
        float(value["active_terminal_source_rz_distance_m"]),
        -float(value["median_persistent_source_distance_improvement_m"]),
        abs(float(value["terminal_source_ip_offset_a"])),
        str(value["arm_id"]),
    ))
    required = int(gates["minimum_nominated_arms_per_round"])
    return {
        "round_index": round_index,
        "round_id": spec["round_id"],
        "decision_state_index": decision,
        "baseline_complete": True,
        "branch_metrics": metrics,
        "nominated_arm_ids": [value["arm_id"] for value in nominated],
        "nominated_arm_count": len(nominated),
        "minimum_nominated_arms": required,
        "selected_arm_id": nominated[0]["arm_id"] if nominated else None,
        "selected_rollout_id": nominated[0]["rollout_id"] if nominated else None,
        "passed": len(nominated) >= required,
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              round_a_prefixes: Sequence[dict[str, Any]],
              round_a_metrics: dict[str, Any] | None,
              round_b_prefixes: Sequence[dict[str, Any]],
              round_b_metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if len(round_a_prefixes) != 7 or not all(
            value["passed"] for value in round_a_prefixes):
        return stage["routes"]["round_a_prefix_mismatch"]
    if round_a_metrics is None or not round_a_metrics["passed"]:
        return stage["routes"]["round_a_utility_fail"]
    if len(round_b_prefixes) != 7 or not all(
            value["passed"] for value in round_b_prefixes):
        return stage["routes"]["round_b_prefix_mismatch"]
    if round_b_metrics is None or not round_b_metrics["passed"]:
        return stage["routes"]["round_b_utility_fail"]
    return stage["routes"]["pass"]


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = z1.y1r1.y1.x1.inside_root(output, "ID2Z2 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, selected_reference, selected_stream = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = z1.y1r1.y1.x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    z1.y1r1.y1.x1.write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"]
                                else "offline_or_input_fail"]
        result = {
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": route,
            "storage_gate": storage_gate,
            "reasons": preflight["failures"],
            "rollouts_completed": 0,
            "reset_calls": 0,
            "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0,
            "verified_plant_advances": 0,
            "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
        }
        z1.y1r1.y1.x1.write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    rows: list[dict[str, Any]] = []
    round_a_streams = initial_round_streams(stage, cfg, targets, selected_stream)
    for stream in round_a_streams:
        row = z1.y1r1.y1.x1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        z1.y1r1.y1.x1.write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"] and not safe_stop(row, stage):
            break
    round_a_rows = [row for row in rows if row.get("round_index") == 0]
    round_a_execution = len(round_a_rows) == 7 and all(
        row["passed"] or safe_stop(row, stage) for row in round_a_rows)
    round_a_prefixes = [_prefix_check(
        row, selected_reference,
        int(stage["prefix_gates"]["round_a_reference_state_count"]),
        int(stage["prefix_gates"]["round_a_reference_action_count"]),
        stage["semantic_artifacts"]) for row in round_a_rows] if round_a_execution else []
    round_a_science = (round_metrics(round_a_rows, stage, 0, cfg)
                       if round_a_execution else None)
    round_b_rows: list[dict[str, Any]] = []
    selected_round_a_stream: dict[str, Any] | None = None
    selected_round_a_row: dict[str, Any] | None = None
    if (round_a_execution and len(round_a_prefixes) == 7
            and all(value["passed"] for value in round_a_prefixes)
            and round_a_science and round_a_science["passed"]):
        selected_arm = str(round_a_science["selected_arm_id"])
        selected_round_a_stream = next(
            stream for stream in round_a_streams if stream["arm_id"] == selected_arm)
        selected_round_a_row = next(
            row for row in round_a_rows if row["arm_id"] == selected_arm)
        for stream in next_round_streams(stage, cfg, targets, selected_round_a_stream):
            row = z1.y1r1.y1.x1.one_rollout(cfg, runtime, stream)
            row.update({"schema_version": SCHEMA, "source_revision": source_revision})
            rows.append(row)
            round_b_rows.append(row)
            z1.y1r1.y1.x1.write_new(output / f"{row['rollout_id']}.json", row)
            if not row["passed"] and not safe_stop(row, stage):
                break
    round_b_execution = bool(selected_round_a_row) and len(round_b_rows) == 7 and all(
        row["passed"] or safe_stop(row, stage) for row in round_b_rows)
    round_b_prefixes = [_prefix_check(
        row, selected_round_a_row or {},
        int(stage["prefix_gates"]["round_b_reference_state_count"]),
        int(stage["prefix_gates"]["round_b_reference_action_count"]),
        stage["semantic_artifacts"]) for row in round_b_rows] if round_b_execution else []
    round_b_science = (round_metrics(round_b_rows, stage, 1, cfg)
                       if round_b_execution else None)
    inventory = z1.y1r1.y1.x1.raw_inventory(output, rows, stage)
    execution = bool(round_a_execution and (
        not (round_a_science and round_a_science["passed"]) or round_b_execution))
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    route = route_for(stage, execution, raw_ok, round_a_prefixes,
                      round_a_science, round_b_prefixes, round_b_science)
    passed = route == stage["routes"]["pass"]
    selected_sequence = [
        round_a_science.get("selected_arm_id") if round_a_science else None,
        round_b_science.get("selected_arm_id") if round_b_science else None,
    ]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage_gate,
        "execution_integrity_passed": execution,
        "raw_integrity_passed": raw_ok,
        "round_a_prefix_checks": round_a_prefixes,
        "round_b_prefix_checks": round_b_prefixes,
        "round_a_metrics": round_a_science,
        "round_b_metrics": round_b_science,
        "selected_two_macro_sequence": selected_sequence,
        "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "complete_rollouts": sum(bool(row["passed"]) for row in rows),
        "guarded_safe_stops": sum(safe_stop(row, stage) for row in rows),
        "reset_calls": sum(int(row["reset_calls"]) for row in rows),
        "advance_attempts": sum(int(row["advance_attempts"]) for row in rows),
        "plant_advance_gotsc_calls": sum(
            int(row["plant_advance_gotsc_calls"]) for row in rows),
        "verified_plant_advances": sum(
            int(row["verified_plant_advances"]) for row in rows),
        **inventory,
        "sequence_nomination_pending_independent": passed,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Finite source-local two-decision canonical-prefix branch evidence; "
            "not hold, recovery, controller, waypoint, crossing or reachability."),
    }
    z1.y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = (offline(args.stage_config, args.source_revision)
              if args.mode == "offline" else run(
                  args.stage_config, args.source_revision,
                  args.output or ROOT / f"rgeo_zgeo_1ms_id2z2_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
