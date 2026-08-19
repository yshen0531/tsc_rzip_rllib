#!/usr/bin/env python3
"""Run the frozen ID-2Z5 joint nominal/capture development campaign."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2w2_extended_nominal_transport as w2  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier as base  # noqa: E402


CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development.json"
CONFIG_SHA256 = "244e7ebdca7675f61cc8bb83b1816c54bfe7a47ecee48ecbdd5c229dba9bddf5"
SCHEMA = "rgeo-zgeo-1ms-id2z5-joint-nominal-capture-development-result-v1"
TOKENS = {"H", "B", "F"}
z3 = base.z3


def _error(message: str) -> Exception:
    return z3.z1.y1r1.y1.x1.InputIntegrityError(message)


def _candidate_rows() -> list[tuple[str, str, int]]:
    return [
        ("hold24", "H" * 24, 1),
        ("b4_h20", "B" * 4 + "H" * 20, 1),
        ("b8_h16", "B" * 8 + "H" * 16, 1),
        ("b12_h12", "B" * 12 + "H" * 12, 1),
        ("bf_alt", "BF" * 12, 1),
        ("bbff_repeat", "BBFF" * 6, 1),
        ("bbbfff_repeat", "BBBFFF" * 4, 1),
        ("bbbbffff_repeat", "BBBBFFFF" * 3, 1),
        ("b4_f4_h16", "BBBBFFFF" + "H" * 16, 1),
        ("b8_f8_h8", "B" * 8 + "F" * 8 + "H" * 8, 1),
        ("b12_f12", "B" * 12 + "F" * 12, 1),
        ("b4_h4_f4_h12", "B" * 4 + "H" * 4 + "F" * 4 + "H" * 12, 1),
        ("bf_alt_replay", "BF" * 12, 0),
    ]


def _require(stage: dict[str, Any]) -> None:
    if (stage.get("schema_version")
            != "rgeo-zgeo-1ms-id2z5-joint-nominal-capture-development-v1"
            or stage.get("identity") != stage.get("schema_version")
            or stage.get("stage") != "ID-2Z5"):
        raise _error("ID2Z5 identity changed")
    exact = {
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "decision_state_index": 61,
        "allocation_first_issue": 61,
        "allocation_last_issue": 84,
        "tail_first_issue": 85,
        "tail_last_issue": 116,
        "horizon_steps": 117,
        "effect_state_offset": 1,
        "maximum_candidates": 13,
        "maximum_rollouts": 13,
        "maximum_reset_calls": 13,
        "maximum_advance_attempts": 1521,
        "maximum_gotsc_calls": 1521,
        "maximum_verified_plant_advances": 1521,
        "maximum_retained_states": 1534,
        "required_artifact_files_if_all_complete": 7670,
        "retry_after_any_advance_attempt": "forbidden",
        "models_fit_or_updated_during_campaign": 0,
        "replay_siblings_fit_weight": 0,
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise _error(f"ID2Z5 changed: {key}")
    observed = [(row.get("candidate_id"), row.get("tokens"), row.get("fit_weight"))
                for row in stage.get("candidate_specs", [])]
    if observed != _candidate_rows():
        raise _error("ID2Z5 candidate matrix changed")
    if any(len(tokens) != 24 or set(tokens) - TOKENS
           for _, tokens, _ in observed):
        raise _error("ID2Z5 token grammar changed")
    if stage.get("terminal_state_indices") != list(range(112, 118)):
        raise _error("ID2Z5 terminal window changed")
    if stage.get("token_semantics") != {
            "H": "hold exact current target",
            "B": "one exact p07:minus increment",
            "F": "one exact p03 forward increment"}:
        raise _error("ID2Z5 token semantics changed")
    action = stage.get("action_semantics", {})
    required_action = {
        "absolute_card15_targets": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True,
        "minimum_absolute_current_headroom_a_on_new_targets": 100.0,
        "one_coordinate_token_per_issue": True,
        "all_non_hold_streams_start_with_b": True,
        "prefix_b_minus_f_balance_nonnegative": True,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "invalid_exact_or_headroom_combination": "exclude_before_reset",
    }
    if action != required_action:
        raise _error("ID2Z5 action contract changed")
    if (stage.get("experiment_contract")
            != "tsc_only_canonical_source_state61_joint_nominal_capture_development"
            or stage.get("data_use")
            != "prospective_truth_recentered_short_horizon_model_development_only"):
        raise _error("ID2Z5 data-use contract changed")
    if stage.get("observability") != {
            "current_same_step_paired_boundary_rgeo_zgeo_and_ip":
                "exact_noiseless_before_issue",
            "post_takeover_causal_history": "available",
            "future_successor": "unknown_before_issue",
            "invalid_boundary": "fail_closed"}:
        raise _error("ID2Z5 observability changed")
    prefix = stage.get("prefix_gates", {})
    if prefix != {
            "required_state_count": 62,
            "required_action_count": 61,
            "checkpoint_indices": [0, 32, 49, 53, 57, 61],
            "exact_action_fields_all_prefix_issues": True,
            "exact_checkpoint_rgeo_zgeo_rmid_ip_coil_wire_active_command_and_semantic_hashes": True,
            "sprsina_hash_is_diagnostic_only": True}:
        raise _error("ID2Z5 prefix contract changed")
    exploration = stage.get("empirical_exploration", {})
    if exploration != {
            "novel_issue_first": 61,
            "post_successor_step_caps": {
                "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0},
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
            "simulator_only_empirical_exploration_exception": True}:
        raise _error("ID2Z5 exploration contract changed")
    gates = stage.get("measurement_gates", {})
    required_gate_values = {
        "negative_control_candidate_id": "hold24",
        "critical_replay_original_id": "bf_alt",
        "critical_replay_candidate_id": "bf_alt_replay",
        "maximum_paired_ip_response_a": 500.0,
        "maximum_terminal_source_rz_distance_m": 0.025,
        "maximum_terminal_rz_step_speed_m_per_s": 0.1,
        "maximum_terminal_absolute_source_ip_fraction": 0.05,
        "minimum_complete_non_replay_families": 8,
        "minimum_classified_non_replay_families_with_16_novel_successors": 10,
        "minimum_distinct_complete_non_replay_token_schedules": 6,
        "critical_replay_exact_checked_trajectory_required": True,
        "capture_is_descriptive_not_required_for_data_readiness": True,
        "report_nondominated_complete_candidates": True,
    }
    for key, value in required_gate_values.items():
        if gates.get(key) != value:
            raise _error(f"ID2Z5 measurement gate changed: {key}")
    if (gates.get("response_state_indices") != list(range(62, 118))
            or gates.get("capture_terminal_state_indices") != list(range(112, 118))
            or gates.get("selection_order") != [
                "minimum_terminal_max_rz_step_speed_m_per_s",
                "minimum_terminal_max_source_rz_distance_m",
                "minimum_terminal_max_absolute_source_ip_fraction",
                "minimum_non_hold_issue_count", "candidate_id"]):
        raise _error("ID2Z5 response or selection gate changed")
    if stage.get("storage_gate") != {
            "minimum_free_bytes_before_run": 140000000000,
            "maximum_estimated_raw_bytes": 95000000000,
            "minimum_free_bytes_after_estimate": 40000000000,
            "output_must_not_exist": True,
            "raw_compression": "forbidden"}:
        raise _error("ID2Z5 storage gate changed")
    if stage.get("routes") != {
            "offline_or_input_fail": "ONE_MS_ID2Z5_OFFLINE_OR_INPUT_FAIL_NO_TSC",
            "storage_fail": "ONE_MS_ID2Z5_STORAGE_FAIL_NO_TSC",
            "execution_or_interface_fail": "ONE_MS_ID2Z5_EXECUTION_OR_INTERFACE_FAIL_STOP",
            "raw_integrity_fail": "ONE_MS_ID2Z5_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
            "prefix_mismatch": "ONE_MS_ID2Z5_PREFIX_MISMATCH_STOP",
            "no_capture_candidate": "ONE_MS_ID2Z5_DEVELOPMENT_DATA_INSUFFICIENT_ACTION_SUPPORT_REVIEW_REQUIRED",
            "capture_candidate": "ONE_MS_ID2Z5_JOINT_NOMINAL_CAPTURE_DEVELOPMENT_PASS_MODEL_COMPARISON_ONLY"}:
        raise _error("ID2Z5 routes changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any],
                                        dict[str, Any], dict[str, Any]]:
    path = z3.z1.y1r1.y1.x1.inside_root(path, "ID2Z5 config")
    if base.sha256(path) != CONFIG_SHA256:
        raise _error("ID2Z5 config hash mismatch")
    stage = base.load_json(path)
    _require(stage)
    required = {
        "design", "id2w2_config", "id2w2_result_report", "id2w2_result",
        "id2w2_independent", "id2w2_compact", "id2z4r1_result_report",
        "id2z4r1_result", "id2z4r1_independent"}
    if set(stage.get("evidence", {})) != required:
        raise _error("ID2Z5 evidence set changed")
    for name, spec in stage["evidence"].items():
        evidence_path = z3.z1.y1r1.y1.x1.inside_root(ROOT / spec["path"], name)
        if base.sha256(evidence_path) != spec["sha256"]:
            raise _error(f"ID2Z5 evidence mismatch: {name}")
    w2_result = base.load_json(ROOT / stage["evidence"]["id2w2_result"]["path"])
    w2_audit = base.load_json(ROOT / stage["evidence"]["id2w2_independent"]["path"])
    compact = base.load_json(ROOT / stage["evidence"]["id2w2_compact"]["path"])
    z4_result = base.load_json(ROOT / stage["evidence"]["id2z4r1_result"]["path"])
    z4_audit = base.load_json(ROOT / stage["evidence"]["id2z4r1_independent"]["path"])
    if (w2_result.get("route") != stage["evidence"]["id2w2_result"]["required_route"]
            or w2_audit.get("audit_passed") is not True
            or len(compact.get("states", [])) < 62
            or len(compact.get("actions", [])) < 61
            or z4_result.get("route")
            != stage["evidence"]["id2z4r1_result"]["required_route"]
            or z4_audit.get("audit_passed") is not True):
        raise _error("ID2Z5 prerequisite evidence is ineligible")
    w2_stage, cfg, targets, _ = w2.load(
        ROOT / stage["evidence"]["id2w2_config"]["path"])
    selected = w2.action_stream(w2_stage, cfg, targets)
    if any(selected["actions"][issue]["expected_card15_fields"]
           != compact["actions"][issue]["expected_card15_fields"]
           for issue in range(61)):
        raise _error("ID2Z5 state61 action prefix changed")
    checkpoints = []
    for index in stage["prefix_gates"]["checkpoint_indices"]:
        row = dict(compact["states"][index])
        row["state_index"] = index
        checkpoints.append(row)
    reference = {"state_checkpoints": checkpoints}
    return stage, cfg, targets, reference, selected


def candidate_streams(stage: dict[str, Any], cfg: Any,
                      targets: dict[str, Any], selected: dict[str, Any]) -> list[dict[str, Any]]:
    q0 = targets["q0"]
    decision = int(stage["decision_state_index"])
    horizon = int(stage["horizon_steps"])
    streams: list[dict[str, Any]] = []
    for spec in stage["candidate_specs"]:
        candidate_id = str(spec["candidate_id"])
        tokens = str(spec["tokens"])
        sequence = list(selected["targets"][:decision])
        virtual = [list(row["probe_virtual_action"])
                   for row in selected["actions"][:decision]]
        current_target = sequence[-1]
        current_virtual = list(virtual[-1])
        for issue in range(decision, horizon):
            token = tokens[issue - decision] if issue <= int(
                stage["allocation_last_issue"]) else "H"
            if token != "H":
                increment = ({"coordinate": "p07:minus", "level_delta": 1}
                             if token == "B" else
                             {"coordinate": "p03", "level_delta": 1})
                delta = z3.z2._increment_target(
                    q0, targets, increment, cfg,
                    f"id2z5.{candidate_id}.delta.{issue}")
                current_target = z3.z1.c1._translated_target(
                    current_target, q0, delta, cfg,
                    f"id2z5.{candidate_id}.target.{issue}")
                current_virtual = z3.z2._virtual_step(current_virtual, increment)
            sequence.append(current_target)
            virtual.append(list(current_virtual))
        actions = z3.z1.c1._actions(sequence, cfg, candidate_id, virtual)
        streams.append({
            "rollout_id": candidate_id,
            "candidate_id": candidate_id,
            "tokens": tokens,
            "fit_weight": int(spec["fit_weight"]),
            "arm_id": candidate_id,
            "cell_id": candidate_id,
            "cell_kind": "state61_joint_nominal_capture_development",
            "context_id": "canonical_source_p03_level60_state61",
            "direction_id": "p07minus__p03forward__time_shared",
            "sign": None,
            "coordinate": "joint_nominal_capture_grammar",
            "level_delta": 0,
            "probe_issue_step": decision,
            "probe_duration_issues": horizon - decision,
            "non_nominal_issue_steps": [
                decision + i for i, token in enumerate(tokens) if token != "H"],
            "targets": sequence,
            "actions": actions,
        })
    return streams


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any) -> dict[str, Any]:
    failures: list[str] = []
    actions = stream["actions"]
    horizon = int(stage["horizon_steps"])
    decision = int(stage["decision_state_index"])
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(actions):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > 0.3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(int(stage["tail_first_issue"]), horizon):
        if (actions[issue]["expected_card15_fields"]
                != actions[int(stage["allocation_last_issue"])]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"TAIL_HOLD:{issue}")
    tokens = str(stream["tokens"])
    if any(token != "H" for token in tokens) and not tokens.startswith("B"):
        failures.append("NON_HOLD_STREAM_DOES_NOT_START_WITH_B")
    balance = 0
    for index, token in enumerate(tokens):
        balance += (1 if token == "B" else -1 if token == "F" else 0)
        if balance < 0:
            failures.append(f"NEGATIVE_B_MINUS_F_BALANCE:{index}")
    headroom = math.inf
    for target in stream["targets"][decision:]:
        headroom = min(headroom, *(min(float(value) - float(low),
                                      float(high) - float(value))
                                   for value, low, high in zip(
                                       target.current_a_tsc,
                                       cfg.min_current_a_tsc,
                                       cfg.max_current_a_tsc)))
    if headroom < float(stage["action_semantics"][
            "minimum_absolute_current_headroom_a_on_new_targets"]) - 1e-9:
        failures.append("ABSOLUTE_CURRENT_HEADROOM")
    return {
        "candidate_id": stream["candidate_id"],
        "fit_weight": stream["fit_weight"],
        "minimum_absolute_current_headroom_a": headroom,
        "maximum_issued_delta_a": max(float(row["maximum_issued_delta_a"])
                                      for row in actions),
        "minimum_prefix_b_minus_f_balance": min(
            [0] + [tokens[:i].count("B") - tokens[:i].count("F")
                   for i in range(1, len(tokens) + 1)]),
        "passed": not failures,
        "failures": failures,
    }


def prefix_check(row: dict[str, Any], reference: dict[str, Any],
                 selected: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    return base.prefix_check(row, reference, selected, stage)


def _replay_check(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    by_id = {row.get("candidate_id"): row for row in rows}
    left = by_id.get(stage["measurement_gates"]["critical_replay_original_id"])
    right = by_id.get(stage["measurement_gates"]["critical_replay_candidate_id"])
    failures: list[str] = []
    if left is None or right is None or not left.get("passed") or not right.get("passed"):
        failures.append("CRITICAL_REPLAY_INCOMPLETE")
    else:
        if len(left.get("states", [])) != len(right.get("states", [])):
            failures.append("CRITICAL_REPLAY_STATE_COUNT")
        for index, (a, b) in enumerate(zip(left.get("states", []), right.get("states", []))):
            for key in ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if a.get(key) != b.get(key):
                    failures.append(f"CRITICAL_REPLAY_STATE:{index}:{key}")
        if [row.get("expected_card15_fields") for row in left.get("actions", [])] != [
                row.get("expected_card15_fields") for row in right.get("actions", [])]:
            failures.append("CRITICAL_REPLAY_ACTIONS")
    failures = list(dict.fromkeys(failures))
    return {"passed": not failures, "failures": failures}


def metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
            cfg: Any | None = None) -> dict[str, Any]:
    descriptive = base.metrics(rows, stage, cfg)
    replay_id = stage["measurement_gates"]["critical_replay_candidate_id"]
    non_replay = [row for row in rows if row.get("candidate_id") != replay_id]
    complete = [row for row in non_replay if row.get("passed")]
    decision = int(stage["decision_state_index"])
    classified = [row for row in non_replay
                  if max(0, len(row.get("states", [])) - decision - 1) >= 16]
    distinct_complete = {row.get("tokens") for row in complete}
    replay = _replay_check(rows, stage)
    gates = stage["measurement_gates"]
    ready = bool(
        len(complete) >= int(gates["minimum_complete_non_replay_families"])
        and len(classified) >= int(
            gates["minimum_classified_non_replay_families_with_16_novel_successors"])
        and len(distinct_complete) >= int(
            gates["minimum_distinct_complete_non_replay_token_schedules"])
        and replay["passed"])
    descriptive_capture_ids = list(descriptive.get("capture_candidate_ids", []))
    descriptive["descriptive_capture_candidate_ids"] = descriptive_capture_ids
    descriptive["descriptive_capture_candidate_count"] = len(descriptive_capture_ids)
    descriptive["capture_not_required_for_data_readiness"] = True
    descriptive["complete_non_replay_families"] = len(complete)
    descriptive["classified_non_replay_families_with_16_novel_successors"] = len(classified)
    descriptive["distinct_complete_non_replay_token_schedules"] = len(distinct_complete)
    descriptive["critical_replay_check"] = replay
    descriptive["passed"] = ready
    return descriptive


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes: Sequence[dict[str, Any]], scientific: dict[str, Any]) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes or not all(value["passed"] for value in prefixes):
        return stage["routes"]["prefix_mismatch"]
    return stage["routes"][
        "capture_candidate" if scientific.get("passed") else "no_capture_candidate"]


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, _, selected = load(path)
        streams = candidate_streams(stage, cfg, targets, selected)
        checks = [validate_stream(stream, stage, cfg) for stream in streams]
        if len(streams) != 13 or not all(row["passed"] for row in checks):
            failures.append("CANDIDATE_MATRIX_NOT_FULLY_ADMISSIBLE")
        by_id = {stream["candidate_id"]: stream for stream in streams}
        if ([row["expected_card15_fields"] for row in by_id["bf_alt"]["actions"]]
                != [row["expected_card15_fields"]
                    for row in by_id["bf_alt_replay"]["actions"]]):
            failures.append("CRITICAL_REPLAY_ACTION_STREAM_CHANGED")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": "rgeo-zgeo-1ms-id2z5-offline-v1",
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": not failures,
        "failures": failures,
        "candidate_checks": checks,
        "admissible_candidate_ids": [row["candidate_id"] for row in checks if row["passed"]],
        "excluded_candidate_ids": [row["candidate_id"] for row in checks if not row["passed"]],
        "reset_calls": 0,
        "plant_advance_gotsc_calls": 0,
        "models_fit_or_updated": 0,
    }


def one_rollout(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], *, runner_cls: type | None = None) -> dict[str, Any]:
    return base.one_rollout(
        cfg, stage, stream, reference, runner_cls=runner_cls)


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
        row = execute_row(cfg, stage, stream, reference, source_revision, output)
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
            or counters["verified_plant_advances"]
            > int(stage["maximum_verified_plant_advances"])):
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
        "claim_boundary": (
            "Finite source-local fit-eligible joint nominal/capture development; "
            "not hold, recovery, controller, waypoint or reachability qualification."),
    }
    z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = z3.z1.y1r1.y1.x1.inside_root(output, "ID2Z5 output")
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
