from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.rgeo_zgeo_1ms_id2z3_bounded_braking_rolling_search as z3  # noqa: E402
from scripts.rgeo_zgeo_1ms_id0_vector_tail import CountingRunner  # noqa: E402


CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier.json"
CONFIG_SHA256 = "1e0be886b8787966549d7925cf37d4eeac22379bf9770e9ba28ccf3b1ae63cbd"
SCHEMA = "rgeo-zgeo-1ms-id2z4r1-earlier-switch-capture-frontier-result-v1"
TOKENS = {"H", "B", "U"}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _require(stage: dict[str, Any]) -> None:
    if (stage.get("schema_version") != "rgeo-zgeo-1ms-id2z4r1-earlier-switch-capture-frontier-v1"
            or stage.get("identity") != stage.get("schema_version")
            or stage.get("stage") != "ID-2Z4R1"):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("ID2Z4R1 identity changed")
    exact = {
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "decision_state_index": 93,
        "capture_first_issue": 93,
        "capture_last_issue": 104,
        "tail_first_issue": 105,
        "tail_last_issue": 116,
        "horizon_steps": 117,
        "effect_state_offset": 1,
        "maximum_candidates": 12,
        "maximum_rollouts": 12,
        "maximum_reset_calls": 12,
        "maximum_advance_attempts": 1404,
        "maximum_gotsc_calls": 1404,
        "maximum_verified_plant_advances": 1404,
        "maximum_retained_states": 1416,
        "required_artifact_files_if_all_complete": 7080,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated": 0,
        "replay_siblings_fit_weight": 0,
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise z3.z1.y1r1.y1.x1.InputIntegrityError(f"ID2Z4R1 changed: {key}")
    candidates = [
        ("hold12", "HHHHHHHHHHHH"),
        ("b4_h8", "BBBBHHHHHHHH"),
        ("b8_h4", "BBBBBBBBHHHH"),
        ("b12", "BBBBBBBBBBBB"),
        ("u2_h10", "UUHHHHHHHHHH"),
        ("b4_u2_h6", "BBBBUUHHHHHH"),
        ("b8_u2_h2", "BBBBBBBBUUHH"),
        ("b4_u4_h4", "BBBBUUUUHHHH"),
        ("b6_u4_h2", "BBBBBBUUUUHH"),
        ("b8_u4", "BBBBBBBBUUUU"),
        ("b4_u4_b4", "BBBBUUUUBBBB"),
        ("b4_u2_b4_u2", "BBBBUUBBBBUU"),
    ]
    observed = [(row.get("candidate_id"), row.get("tokens"))
                for row in stage.get("candidate_specs", [])]
    if observed != candidates or any(set(tokens) - TOKENS for _, tokens in observed):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("candidate grammar changed")
    if stage.get("terminal_state_indices") != list(range(112, 118)):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("terminal window changed")
    action = stage.get("action_semantics", {})
    if (action.get("maximum_per_coil_issue_delta_a") != 0.3
            or action.get("minimum_absolute_current_headroom_a") != 100.0
            or action.get("full_0p3_a_allowed") is not True
            or action.get("one_coordinate_token_per_issue") is not True
            or action.get("software_queue_added") is not False
            or action.get("legacy_runner_clipping_may_be_relied_on") is not False
            or action.get("future_actual_current") != "forbidden"):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("action contract changed")
    if stage.get("token_semantics") != {
        "H": "hold exact current target",
        "B": "one exact p07:minus increment",
        "U": "one exact p03 unwind increment",
    }:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("token semantics changed")
    if (stage.get("experiment_contract")
            != "tsc_only_canonical_source_state93_earlier_switch_two_axis_capture_frontier"
            or stage.get("data_use")
            != "prospective_short_horizon_model_development_and_capture_route_evidence_only"):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("data-use contract changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip":
            "exact_noiseless_before_issue",
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("observability changed")
    if (stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]
            or stage.get("diagnostic_artifacts") != ["sprsina"]):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("artifact contract changed")
    prefix = stage.get("prefix_gates", {})
    if prefix != {
        "required_state_count": 94,
        "required_action_count": 93,
        "checkpoint_indices": [0, 32, 64, 69, 73, 77, 81, 85, 89, 93],
        "exact_action_fields_all_prefix_issues": True,
        "exact_checkpoint_rgeo_zgeo_rmid_ip_coil_wire_active_command_and_semantic_hashes": True,
        "sprsina_hash_is_diagnostic_only": True,
    }:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("prefix gates changed")
    exploration = stage.get("empirical_exploration", {})
    if exploration != {
        "novel_issue_first": 93,
        "post_successor_step_caps": {
            "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0},
        "inner_novel_issue_clearance": {
            "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05},
        "outer_hard_envelope": {
            "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.1},
        "allowed_branch_safe_stop_reasons": [
            "PULSE_CLEARANCE_R", "PULSE_CLEARANCE_Z", "PULSE_CLEARANCE_IP",
            "EMPIRICAL_STEP_R", "EMPIRICAL_STEP_Z", "EMPIRICAL_STEP_IP"],
        "continue_next_reset_after_only_allowed_branch_safe_stop": True,
        "abort_campaign_after_any_other_failure": True,
        "stop_before_next_issue_after_any_failure": True,
        "post_action_abort_is_not_a_pre_action_bound": True,
        "simulator_only_empirical_exploration_exception": True,
    }:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("exploration contract changed")
    gates = stage.get("measurement_gates", {})
    if (gates.get("negative_control_candidate_id") != "hold12"
            or gates.get("negative_control_may_be_incomplete") is not True
            or gates.get("negative_control_completion_required_for_other_candidate_science") is not False
            or gates.get("paired_response_role") != "descriptive_only_on_overlapping_observed_states"
            or gates.get("response_state_indices") != list(range(94, 118))
            or gates.get("capture_terminal_state_indices") != list(range(112, 118))
            or gates.get("maximum_paired_ip_response_a") != 400.0
            or gates.get("maximum_terminal_source_rz_distance_m") != 0.025
            or gates.get("maximum_terminal_rz_step_speed_m_per_s") != 0.1
            or gates.get("maximum_terminal_absolute_source_ip_fraction") != 0.05
            or gates.get("minimum_statically_admissible_mixed_b_u_candidates") != 1
            or gates.get("report_nondominated_complete_candidates") is not True):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("measurement gates changed")
    if gates.get("selection_order") != [
        "minimum_terminal_max_rz_speed_m_per_s",
        "minimum_terminal_max_source_rz_distance_m",
        "minimum_terminal_max_absolute_source_ip_fraction",
        "minimum_non_hold_issue_count", "candidate_id"]:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("selection order changed")
    storage = stage.get("storage_gate", {})
    if storage != {
        "minimum_free_bytes_before_run": 145000000000,
        "maximum_estimated_raw_bytes": 90000000000,
        "minimum_free_bytes_after_estimate": 55000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("storage gate changed")
    if stage.get("routes") != {
        "offline_or_input_fail": "ONE_MS_ID2Z4R1_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "storage_fail": "ONE_MS_ID2Z4R1_STORAGE_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2Z4R1_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2Z4R1_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "prefix_mismatch": "ONE_MS_ID2Z4R1_PREFIX_MISMATCH_STOP",
        "no_capture_candidate": "ONE_MS_ID2Z4R1_EARLIER_SWITCH_FRONTIER_FAIL_ACTION_BASIS_REVIEW_REQUIRED",
        "capture_candidate": "ONE_MS_ID2Z4R1_FINITE_CAPTURE_CANDIDATE_PASS_FRESH_REPLAY_AND_RECOURSE_DESIGN_ONLY",
    }:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("routes changed")


def reconstruct_selected_prefix(stage: dict[str, Any], cfg: Any,
                                targets: dict[str, Any],
                                id2z2_stream: dict[str, Any]) -> dict[str, Any]:
    parent = id2z2_stream
    history: list[str] = []
    for round_index in range(4):
        streams = (z3.initial_round_streams(stage, cfg, targets, parent)
                   if round_index == 0 else z3.next_round_streams(
                       stage, cfg, targets, parent, round_index, history))
        parent = next(row for row in streams if row["arm_id"] == "p07minus4")
        history.append("p07minus4")
    return parent


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any],
                                        dict[str, Any], dict[str, Any]]:
    path = z3.z1.y1r1.y1.x1.inside_root(path, "ID2Z4R1 config")
    if sha256(path) != CONFIG_SHA256:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("ID2Z4R1 config hash mismatch")
    stage = load_json(path)
    _require(stage)
    required = {"design", "id2z3_config", "id2z3_result_report",
                "id2z3_compact_evidence", "id2z3_state97_reference"}
    if set(stage.get("evidence", {})) != required:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("evidence set changed")
    for name, spec in stage["evidence"].items():
        evidence = z3.z1.y1r1.y1.x1.inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise z3.z1.y1r1.y1.x1.InputIntegrityError(f"evidence mismatch: {name}")
    evidence = load_json(ROOT / stage["evidence"]["id2z3_compact_evidence"]["path"])
    if (evidence.get("route") != stage["evidence"]["id2z3_compact_evidence"]["required_route"]
            or evidence.get("repaired_independent_audit_passed") is not True
            or evidence.get("selected_arm_sequence") != ["p07minus4"] * 5):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("ID2Z3 result is not eligible")
    reference = load_json(ROOT / stage["evidence"]["id2z3_state97_reference"]["path"])
    spec = stage["evidence"]["id2z3_state97_reference"]
    if (reference.get("source_compact_sha256") != spec["required_source_compact_sha256"]
            or int(reference.get("required_state_count", 0)) < spec["required_state_count_at_least"]
            or int(reference.get("required_action_count", 0)) < spec["required_action_count_at_least"]
            or reference.get("selected_arm_history") != ["p07minus4"] * 5):
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("state97 reference changed")
    id2z3_stage, cfg, targets, _, id2z2_stream = z3.load(
        ROOT / stage["evidence"]["id2z3_config"]["path"])
    selected = reconstruct_selected_prefix(id2z3_stage, cfg, targets, id2z2_stream)
    if len(selected["actions"]) < 93 or len(selected["targets"]) < 93:
        raise z3.z1.y1r1.y1.x1.InputIntegrityError("selected prefix incomplete")
    return stage, cfg, targets, reference, selected


def candidate_streams(stage: dict[str, Any], cfg: Any,
                      targets: dict[str, Any], selected: dict[str, Any]) -> list[dict[str, Any]]:
    q0 = targets["q0"]
    decision = int(stage["decision_state_index"])
    horizon = int(stage["horizon_steps"])
    rows: list[dict[str, Any]] = []
    for spec in stage["candidate_specs"]:
        candidate_id = str(spec["candidate_id"])
        tokens = str(spec["tokens"])
        sequence = list(selected["targets"][:decision])
        virtual = [list(row["probe_virtual_action"])
                   for row in selected["actions"][:decision]]
        current_target = sequence[-1]
        current_virtual = list(virtual[-1])
        for issue in range(decision, horizon):
            token = tokens[issue - decision] if issue <= int(stage["capture_last_issue"]) else "H"
            if token != "H":
                increment = ({"coordinate": "p07:minus", "level_delta": 1}
                             if token == "B" else
                             {"coordinate": "p03", "level_delta": -1})
                delta = z3.z2._increment_target(
                    q0, targets, increment, cfg,
                    f"id2z4r1.{candidate_id}.delta.{issue}")
                current_target = z3.z1.c1._translated_target(
                    current_target, q0, delta, cfg,
                    f"id2z4r1.{candidate_id}.target.{issue}")
                current_virtual = z3.z2._virtual_step(current_virtual, increment)
            sequence.append(current_target)
            virtual.append(list(current_virtual))
        actions = z3.z1.c1._actions(sequence, cfg, candidate_id, virtual)
        rows.append({
            "rollout_id": candidate_id,
            "candidate_id": candidate_id,
            "tokens": tokens,
            "arm_id": candidate_id,
            "cell_id": candidate_id,
            "cell_kind": "state93_earlier_switch_two_axis_capture_frontier",
            "context_id": "canonical_source_id2z3_selected_state93",
            "direction_id": "p07minus__p03unwind__time_shared",
            "sign": None,
            "coordinate": "capture_grammar",
            "level_delta": 0,
            "probe_issue_step": decision,
            "probe_duration_issues": horizon - decision,
            "non_nominal_issue_steps": [decision + i for i, token in enumerate(tokens)
                                         if token != "H"],
            "targets": sequence,
            "actions": actions,
        })
    return rows


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    actions = stream["actions"]
    if len(actions) != stage["horizon_steps"] or len(stream["targets"]) != stage["horizon_steps"]:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(actions):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > 0.3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(stage["tail_first_issue"], stage["horizon_steps"]):
        if (actions[issue]["expected_card15_fields"]
                != actions[stage["capture_last_issue"]]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"TAIL_HOLD:{issue}")
    decision = int(stage["decision_state_index"])
    headroom = min(
        min(float(value) - float(low), float(high) - float(value))
        for target in stream["targets"][decision:]
        for value, low, high in zip(
            target.current_a_tsc, cfg.min_current_a_tsc, cfg.max_current_a_tsc))
    if headroom < stage["action_semantics"]["minimum_absolute_current_headroom_a"] - 1e-9:
        failures.append("ABSOLUTE_CURRENT_HEADROOM")
    return {
        "candidate_id": stream["candidate_id"],
        "minimum_absolute_current_headroom_a": headroom,
        "maximum_issued_delta_a": max(float(row["maximum_issued_delta_a"])
                                      for row in actions),
        "non_hold_issue_count": len(stream["non_nominal_issue_steps"]),
        "passed": not failures,
        "failures": failures,
    }


def prefix_check(row: dict[str, Any], reference: dict[str, Any],
                 selected: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    decision = int(stage["decision_state_index"])
    if (len(row.get("states", [])) < decision + 1
            or len(row.get("actions", [])) < decision):
        failures.append("PREFIX_INCOMPLETE")
    else:
        by_index = {int(value["state_index"]): value
                    for value in reference["state_checkpoints"]}
        for index in stage["prefix_gates"]["checkpoint_indices"]:
            current, expected = row["states"][index], by_index[index]
            for key in ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "side", "r_inner_m", "r_outer_m",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if current.get(key) != expected.get(key):
                    failures.append(f"STATE:{index}:{key}")
            for name in stage["semantic_artifacts"]:
                if (name == "inputa"
                        and row.get("recovered_from_complete_raw_without_tsc")):
                    continue
                if (current.get("artifact_sha256", {}).get(name)
                        != expected.get("artifact_sha256", {}).get(name)):
                    failures.append(f"STATE:{index}:artifact:{name}")
        for issue in range(decision):
            if (row["actions"][issue].get("expected_card15_fields")
                    != selected["actions"][issue].get("expected_card15_fields")):
                failures.append(f"ACTION:{issue}")
    return {"candidate_id": row.get("candidate_id"), "passed": not failures,
            "failures": list(dict.fromkeys(failures))}


def checkpoint_reasons(record: dict[str, Any], state_index: int,
                       reference: dict[str, Any],
                       stage: dict[str, Any]) -> list[str]:
    """Fail closed on a frozen live prefix checkpoint before any later issue."""
    by_index = {int(value["state_index"]): value
                for value in reference["state_checkpoints"]}
    if state_index not in stage["prefix_gates"]["checkpoint_indices"]:
        return []
    expected = by_index.get(state_index)
    if expected is None:
        return [f"LIVE_PREFIX:{state_index}:REFERENCE_MISSING"]
    failures: list[str] = []
    for key in ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                "side", "r_inner_m", "r_outer_m",
                "actual_current_decimal_a_tsc", "wire_current_a",
                "active_command_card15_fields"):
        if record.get(key) != expected.get(key):
            failures.append(f"LIVE_PREFIX:{state_index}:{key}")
    for name in stage["semantic_artifacts"]:
        if (record.get("artifact_sha256", {}).get(name)
                != expected.get("artifact_sha256", {}).get(name)):
            failures.append(f"LIVE_PREFIX:{state_index}:artifact:{name}")
    return failures


def _distance(state: dict[str, Any], source: dict[str, Any]) -> float:
    return math.hypot(float(state["r_geo_m"]) - float(source["r_geo_m"]),
                      float(state["z_geo_m"]) - float(source["z_geo_m"]))


def _velocity(states: Sequence[dict[str, Any]], index: int) -> list[float]:
    return [(float(states[index][key]) - float(states[index - 1][key])) / 0.001
            for key in ("r_geo_m", "z_geo_m")]


def metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
            cfg: Any | None = None) -> dict[str, Any]:
    by_id = {row.get("candidate_id"): row for row in rows}
    baseline_id = stage["measurement_gates"]["negative_control_candidate_id"]
    baseline = by_id.get(baseline_id)
    source_row = next((row for row in rows if row.get("states")), None)
    if source_row is None:
        return {"negative_control_complete": False,
                "candidate_metrics": [], "capture_candidate_ids": [],
                "nondominated_complete_candidate_ids": [],
                "selected_candidate_id": None, "passed": False}
    source = source_row["states"][0]
    response_indices = stage["measurement_gates"]["response_state_indices"]
    terminal = stage["measurement_gates"]["capture_terminal_state_indices"]
    values: list[dict[str, Any]] = []
    captures: list[dict[str, Any]] = []
    ip_cap = (stage["measurement_gates"]["maximum_terminal_absolute_source_ip_fraction"]
              * abs(float(source["ip_a"])))
    for spec in stage["candidate_specs"]:
        candidate_id = spec["candidate_id"]
        row = by_id.get(candidate_id)
        if (row is None or not row.get("passed")
                or len(row.get("states", [])) != int(stage["horizon_steps"]) + 1):
            values.append({"candidate_id": candidate_id,
                           "execution_status": "incomplete_or_excluded",
                           "observed_state_count": len(row.get("states", [])) if row else 0,
                           "safe_stop": bool(row and z3.z2.safe_stop(row, stage)),
                           "capture_passed": False})
            continue
        states = row["states"]
        overlap = []
        if baseline is not None:
            overlap = [i for i in response_indices
                       if i < len(states) and i < len(baseline.get("states", []))]
        response = [[float(states[i][key]) - float(baseline["states"][i][key])
                     for key in ("r_geo_m", "z_geo_m", "ip_a")]
                    for i in overlap]
        distances = [_distance(states[i], source) for i in terminal]
        velocities = [_velocity(states, i) for i in terminal]
        speeds = [math.hypot(*value) for value in velocities]
        ip_offsets = [abs(float(states[i]["ip_a"]) - float(source["ip_a"]))
                      for i in terminal]
        max_paired_ip = (max(abs(value[2]) for value in response)
                         if response else None)
        captured = bool(
            max(distances) <= stage["measurement_gates"]["maximum_terminal_source_rz_distance_m"]
            and max(speeds) <= stage["measurement_gates"]["maximum_terminal_rz_step_speed_m_per_s"]
            and max(ip_offsets) <= ip_cap)
        value = {
            "candidate_id": candidate_id,
            "tokens": spec["tokens"],
            "execution_status": "complete",
            "non_hold_issue_count": sum(token != "H" for token in spec["tokens"]),
            "paired_response_state_indices": overlap,
            "paired_rzi_response": response,
            "maximum_paired_rz_response_m": (max(math.hypot(x[0], x[1])
                                                  for x in response)
                                               if response else None),
            "maximum_paired_ip_response_a": max_paired_ip,
            "terminal_source_rz_distance_m": distances,
            "terminal_velocity_rz_m_per_s": velocities,
            "terminal_rz_step_speed_m_per_s": speeds,
            "terminal_absolute_source_ip_offset_a": ip_offsets,
            "terminal_max_source_rz_distance_m": max(distances),
            "terminal_max_rz_step_speed_m_per_s": max(speeds),
            "terminal_max_absolute_source_ip_offset_a": max(ip_offsets),
            "terminal_max_absolute_source_ip_fraction": (
                max(ip_offsets) / abs(float(source["ip_a"]))),
            "source_ip_cap_a": ip_cap,
            "capture_passed": captured,
        }
        if cfg is not None:
            value.update(z3.z1._trajectory_diagnostics(row, source, cfg, stage))
        values.append(value)
        if captured:
            captures.append(value)
    complete = [value for value in values
                if value.get("execution_status") == "complete"]
    nondominated: list[dict[str, Any]] = []
    for value in complete:
        vector = (value["terminal_max_rz_step_speed_m_per_s"],
                  value["terminal_max_source_rz_distance_m"],
                  value["terminal_max_absolute_source_ip_fraction"])
        dominated = False
        for other in complete:
            if other is value:
                continue
            other_vector = (other["terminal_max_rz_step_speed_m_per_s"],
                            other["terminal_max_source_rz_distance_m"],
                            other["terminal_max_absolute_source_ip_fraction"])
            if (all(a <= b for a, b in zip(other_vector, vector))
                    and any(a < b for a, b in zip(other_vector, vector))):
                dominated = True
                break
        if not dominated:
            nondominated.append(value)
    captures.sort(key=lambda value: (
        value["terminal_max_rz_step_speed_m_per_s"],
        value["terminal_max_source_rz_distance_m"],
        value["terminal_max_absolute_source_ip_fraction"],
        value["non_hold_issue_count"], value["candidate_id"]))
    selected = captures[0] if captures else None
    return {
        "negative_control_complete": bool(
            baseline is not None and baseline.get("passed")
            and len(baseline.get("states", [])) == int(stage["horizon_steps"]) + 1),
        "negative_control_observed_state_count": (
            len(baseline.get("states", [])) if baseline else 0),
        "candidate_metrics": values,
        "nondominated_complete_candidate_ids": sorted(
            row["candidate_id"] for row in nondominated),
        "capture_candidate_ids": [row["candidate_id"] for row in captures],
        "capture_candidate_count": len(captures),
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "passed": bool(captures),
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes: Sequence[dict[str, Any]], scientific: dict[str, Any]) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes or not all(value["passed"] for value in prefixes):
        return stage["routes"]["prefix_mismatch"]
    if scientific.get("passed"):
        return stage["routes"]["capture_candidate"]
    return stage["routes"]["no_capture_candidate"]


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    minimum_headroom = math.inf
    try:
        stage, cfg, targets, _, selected = load(path)
        streams = candidate_streams(stage, cfg, targets, selected)
        for stream in streams:
            check = validate_stream(stream, stage, cfg)
            checks.append(check)
            minimum_headroom = min(minimum_headroom,
                                   check["minimum_absolute_current_headroom_a"])
        if not any(row["candidate_id"] == "hold12" and row["passed"] for row in checks):
            failures.append("NEGATIVE_CONTROL_NOT_ADMISSIBLE")
        mixed_ids = {spec["candidate_id"] for spec in stage["candidate_specs"]
                     if "B" in spec["tokens"] and "U" in spec["tokens"]}
        if not any(row["candidate_id"] in mixed_ids and row["passed"]
                   for row in checks):
            failures.append("NO_MIXED_B_U_CANDIDATE_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": "rgeo-zgeo-1ms-id2z4r1-offline-v1",
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": not failures,
        "failures": failures,
        "candidate_checks": checks,
        "admissible_candidate_ids": [row["candidate_id"] for row in checks if row["passed"]],
        "excluded_candidate_ids": [row["candidate_id"] for row in checks if not row["passed"]],
        "minimum_constructed_headroom_a": (
            minimum_headroom if math.isfinite(minimum_headroom) else None),
        "reset_calls": 0,
        "plant_advance_gotsc_calls": 0,
        "models_fit_or_updated": 0,
    }


def _runtime(stage: dict[str, Any]) -> dict[str, Any]:
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    return runtime


def one_rollout(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any],
                *, runner_cls: type | None = None) -> dict[str, Any]:
    """Execute one branch with inner clearance before every novel issue."""
    x1 = z3.z1.y1r1.y1.x1
    runner_type = runner_cls or CountingRunner
    runner = None
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempted: list[dict[str, Any]] = []
    reasons: list[str] = []
    reset_calls = attempts = successes = 0
    started = time.perf_counter()
    try:
        runner = runner_type(
            cfg, worker_id=f"id2z4r1_{stream['rollout_id']}", keep_workspace=False)
        reset_calls += 1
        state = runner.reset(episode_name=stream["rollout_id"])
        states.append(x1._record(cfg, state))
        x1._validate_record(states[-1], f"{stream['rollout_id']}.state0")
        reasons.extend(checkpoint_reasons(states[-1], 0, reference, stage))
        if (states[0]["time_ms"] != 1100
                or int(state.get("returncode", 0)) != 0
                or bool(state.get("abnormal", False))):
            reasons.append("SOURCE_RESET_INVALID")
        source_signal = x1.RGeoZGeoSignal.from_tsc_state(state)
        envelope = x1.OneMsNR1SafetyEnvelope.from_signal(source_signal)
        runtime = _runtime(stage)
        for issue, (target, frozen_action) in enumerate(
                zip(stream["targets"], stream["actions"])):
            if reasons:
                break
            signal = x1.RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(
                signal, state["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(x1._outer_reasons(runtime, source_signal, signal))
            if issue >= int(stage["empirical_exploration"]["novel_issue_first"]):
                reasons.extend(x1._pulse_clearance(runtime, source_signal, signal))
            target_exact = x1.card15_target_decimal_a(
                target, cfg.turns_tsc,
                name=f"id2z4r1.run.{stream['rollout_id']}.{issue}")
            try:
                maximum = x1.assert_exact_slew(
                    states[-1]["active_command_decimal_a_tsc"], target_exact,
                    name=f"id2z4r1.issue.{stream['rollout_id']}.{issue}")
                if any(value < Decimal(str(low)) or value > Decimal(str(high))
                       for value, low, high in zip(
                           target_exact, cfg.min_current_a_tsc,
                           cfg.max_current_a_tsc)):
                    raise x1.ContractError("target leaves absolute current limits")
            except Exception as exc:
                reasons.append(
                    f"ISSUED_ACTION:{issue}:{type(exc).__name__}:{exc}")
                break
            if reasons:
                break
            action = x1._action(frozen_action)
            action["maximum_issued_delta_a"] = maximum
            attempted.append(action)
            attempts += 1
            try:
                successor = runner.step_current_a(
                    np.asarray(target.current_a_tsc, dtype=float))
            except Exception as exc:
                reasons.append(
                    f"STEP_EXECUTION:{issue}:{type(exc).__name__}:{exc}")
                break
            try:
                record = x1._record(cfg, successor)
                x1._validate_record(
                    record, f"{stream['rollout_id']}.state{issue + 1}")
            except Exception as exc:
                reasons.append(
                    f"SUCCESSOR_RECORD:{issue}:{type(exc).__name__}:{exc}")
                break
            if record["time_ms"] == 1101 + issue:
                states.append(record)
                reasons.extend(checkpoint_reasons(
                    record, issue + 1, reference, stage))
            else:
                reasons.append(f"TIME:{issue}:{record['time_ms']}")
                break
            if (int(successor.get("returncode", 0)) != 0
                    or bool(successor.get("abnormal", False))):
                reasons.append(
                    f"TSC_STATUS:{issue}:{successor.get('returncode', 0)}:"
                    f"{successor.get('done_reason', '')}")
                break
            actions.append(action)
            successes += 1
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                reasons.append(f"CARD15:{issue}")
            try:
                record["maximum_observed_delta_a"] = x1.assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"],
                    record["actual_current_decimal_a_tsc"],
                    name=f"id2z4r1.observed.{stream['rollout_id']}.{issue}")
            except Exception as exc:
                reasons.append(
                    f"OBSERVED_SLEW:{issue}:{type(exc).__name__}:{exc}")
            successor_signal = x1.RGeoZGeoSignal.from_tsc_state(successor)
            reasons.extend(envelope.state_reasons(
                successor_signal, successor["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(x1._outer_reasons(
                runtime, source_signal, successor_signal))
            reasons.extend(x1._step_cap_reasons(
                runtime, states[-2], states[-1]))
            state = successor
            if reasons:
                break
    except Exception as exc:
        reasons.append(f"ROLLOUT_EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        if runner is not None:
            try:
                runner.cleanup_runtime_workspace()
            except Exception as exc:
                reasons.append(f"CLEANUP:{type(exc).__name__}:{exc}")
    reasons = list(dict.fromkeys(reasons))
    gotsc = (0 if runner is None else int(getattr(
        runner, "plant_advance_gotsc_calls", attempts)))
    complete = bool(
        not reasons and reset_calls == 1
        and attempts == successes == int(stage["horizon_steps"])
        and len(actions) == int(stage["horizon_steps"])
        and len(states) == int(stage["horizon_steps"]) + 1)
    return {
        **{key: value for key, value in stream.items()
           if key not in ("targets", "actions")},
        "schema_version": SCHEMA,
        "passed": complete,
        "reasons": reasons,
        "reset_calls": reset_calls,
        "advance_attempts": attempts,
        "plant_advance_gotsc_calls": gotsc,
        "verified_plant_advances": successes,
        "states": states,
        "actions": actions,
        "attempted_actions": attempted,
        "retry_attempted": False,
        "wall_time_s": time.perf_counter() - started,
    }


def execute_row(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], source_revision: str,
                output: Path) -> dict[str, Any]:
    row = one_rollout(cfg, stage, stream, reference)
    row.update({"schema_version": SCHEMA, "source_revision": source_revision})
    z3.z1.y1r1.y1.x1.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def execute(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
            reference: dict[str, Any], selected: dict[str, Any],
            source_revision: str, output: Path,
            storage_gate: dict[str, Any]) -> dict[str, Any]:
    cfg.run_root = output / "rollouts"
    streams = candidate_streams(stage, cfg, targets, selected)
    checks = [validate_stream(stream, stage, cfg) for stream in streams]
    admissible = [stream for stream, check in zip(streams, checks) if check["passed"]]
    rows: list[dict[str, Any]] = []
    execution = True
    for stream in admissible:
        row = execute_row(
            cfg, stage, stream, reference, source_revision, output)
        rows.append(row)
        if not row.get("passed") and not z3.z2.safe_stop(row, stage):
            execution = False
            break
    counters = {
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in rows),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in rows),
        "plant_advance_gotsc_calls": sum(
            int(row.get("plant_advance_gotsc_calls", 0)) for row in rows),
        "verified_plant_advances": sum(
            int(row.get("verified_plant_advances", 0)) for row in rows),
    }
    if (len(rows) > int(stage["maximum_rollouts"])
            or counters["reset_calls"] > int(stage["maximum_reset_calls"])
            or counters["advance_attempts"] > int(stage["maximum_advance_attempts"])
            or counters["plant_advance_gotsc_calls"] > int(stage["maximum_gotsc_calls"])
            or counters["verified_plant_advances"] > int(
                stage["maximum_verified_plant_advances"])):
        execution = False
    prefixes = [prefix_check(row, reference, selected, stage) for row in rows]
    if prefixes and not all(value["passed"] for value in prefixes):
        execution = False
    inventory = z3.z1.y1r1.y1.x1.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    scientific = metrics(rows, stage, cfg)
    route = route_for(stage, execution, raw_ok, prefixes, scientific)
    passed = route == stage["routes"]["capture_candidate"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage_gate,
        "execution_integrity_passed": execution,
        "raw_integrity_passed": raw_ok,
        "offline_exclusions": [row for row in checks if not row["passed"]],
        "prefix_checks": prefixes,
        "scientific_metrics": scientific,
        "selected_candidate_id": scientific.get("selected_candidate_id"),
        "rollouts_completed": len(rows),
        "complete_rollouts": sum(bool(row.get("passed")) for row in rows),
        "guarded_safe_stops": sum(z3.z2.safe_stop(row, stage) for row in rows),
        **counters,
        **inventory,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "compact_data_role": stage["data_use"],
        "claim_boundary": "Finite source-local earlier-switch capture frontier; not hold, recovery, controller, waypoint or reachability qualification.",
    }
    z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = z3.z1.y1r1.y1.x1.inside_root(output, "ID2Z4R1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, reference, selected = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = z3.z1.y1r1.y1.x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    z3.z1.y1r1.y1.x1.write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"]
                                else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage_gate,
                  "reasons": preflight["failures"], "rollouts_completed": 0,
                  "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "models_fit_or_updated": 0,
                  "calibration_or_holdout_records_read": 0}
        z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
        return result
    return execute(stage, cfg, targets, reference, selected,
                   source_revision, output, storage_gate)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args(argv)
    if args.offline_only:
        result = offline(args.stage_config, args.source_revision)
    else:
        if args.output is None:
            parser.error("--output is required unless --offline-only")
        result = run(args.stage_config, args.source_revision, args.output)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
