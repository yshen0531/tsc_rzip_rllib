#!/usr/bin/env python3
"""Run the frozen ID-2Z7 fresh later-round branch continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z6_early_root_branch_teacher as z6  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z7_branch_continuation.json"
CONFIG_SHA256 = "c313a9c1ebb7d0e92ef60982b9e8d4a4e80f844e227b75c9b25e6709f7d37468"
SCHEMA = "rgeo-zgeo-1ms-id2z7-branch-continuation-result-v1"
ARM_IDS = z6.ARM_IDS
FRESH_ROUNDS = (1, 2)


def _error(message: str) -> Exception:
    return z6._error(message)


def _inside(path: Path, label: str) -> Path:
    return z6.z5.z3.z1.y1r1.y1.x1.inside_root(path, label)


def _json(path: Path) -> dict[str, Any]:
    return z6._json(path)


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z7-branch-continuation-v1",
        "identity": "rgeo-zgeo-1ms-id2z7-branch-continuation-v1",
        "stage": "ID-2Z7",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "inherited_round0_selected_arm_id": "f4",
        "fresh_round_indices": [1, 2],
        "common_horizon_steps": 69,
        "common_terminal_state_index": 69,
        "maximum_fresh_rounds": 2,
        "maximum_branches_per_round": 5,
        "maximum_branch_rollouts": 10,
        "maximum_replay_rollouts": 1,
        "maximum_rollouts": 11,
        "maximum_reset_calls": 11,
        "maximum_advance_attempts": 759,
        "maximum_gotsc_calls": 759,
        "maximum_verified_plant_advances": 759,
        "maximum_retained_states": 770,
        "required_artifact_files_if_all_complete": 3850,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": (
            "new_identity_fresh_round1_round2_canonical_source_branch_continuation"),
        "data_use": (
            "combined_id2z6_round0_plus_fresh_id2z7_complete_windows_development_only"),
        "external_round0_fit_weight_windows": 5,
        "interrupted_id2z6_round1_fit_and_selection_weight": 0,
        "id2z5_fit_weight": 0,
        "critical_replay_fit_weight": 0,
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field mismatch: {key}")
    if stage.get("candidate_specs") != [
            {"arm_id": "hold4", "tokens": "HHHH", "fit_weight": 1},
            {"arm_id": "b4", "tokens": "BBBB", "fit_weight": 1},
            {"arm_id": "f4", "tokens": "FFFF", "fit_weight": 1},
            {"arm_id": "b2f2", "tokens": "BBFF", "fit_weight": 1},
            {"arm_id": "f2b2", "tokens": "FFBB", "fit_weight": 1}]:
        raise _error("candidate specification changed")
    if stage.get("run_root_isolation") != {
            "required_value": "<new_output>/rollouts",
            "historical_default_root_forbidden": "rgeo_zgeo_1ms_nr1_runs",
            "verify_before_runner_construction": True,
            "every_rollout_must_resolve_under_required_root": True,
            "fake_runner_server_test_required": True,
            "no_existing_output": True}:
        raise _error("run-root isolation contract changed")
    if stage.get("observability") != {
            "current_same_step_paired_boundary_rgeo_zgeo_and_ip": (
                "exact_noiseless_before_issue"),
            "post_takeover_causal_history": "available",
            "future_successor": "unknown_before_issue",
            "belief_is_not_used_for_current_or_past_rzi": True,
            "invalid_boundary": "fail_closed"}:
        raise _error("observability changed")
    if stage.get("action_semantics") != {
            "absolute_card15_targets": True,
            "maximum_per_coil_issue_delta_a": 0.3,
            "full_0p3_a_allowed": True,
            "issue_to_effect_state_offset": 1,
            "software_queue_added": False,
            "legacy_runner_clipping_may_be_relied_on": False,
            "future_actual_current": "forbidden",
            "token_h": "hold exact current target",
            "token_b": "one exact p07:minus increment",
            "token_f": "one exact p03 forward increment",
            "macro_length_issues": 4,
            "post_macro_target": "hold through issue 68",
            "selected_successor_requires_next_round_h_b4_f4_exact_reserve": True}:
        raise _error("action semantics changed")
    exploration = stage.get("empirical_exploration", {})
    if exploration != {
            "novel_issue_first": 53,
            "post_successor_step_caps": {
                "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0},
            "simulator_development_preissue_clearance": {
                "r_geo_m": 0.035, "z_geo_m": 0.035, "ip_fraction": 0.075},
            "outer_hard_envelope": {
                "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.1},
            "development_to_hard_axis_guard_m": 0.015,
            "development_to_hard_ip_fraction_guard": 0.025,
            "allowed_branch_safe_stop_reasons": [
                "PULSE_CLEARANCE_R", "PULSE_CLEARANCE_Z",
                "PULSE_CLEARANCE_IP", "EMPIRICAL_STEP_R",
                "EMPIRICAL_STEP_Z", "EMPIRICAL_STEP_IP"],
            "continue_next_sibling_after_only_allowed_branch_safe_stop": True,
            "abort_campaign_after_any_other_failure": True,
            "stop_before_next_issue_after_any_failure": True,
            "post_action_abort_is_not_a_pre_action_bound": True,
            "development_shell_is_not_capture_recovery_or_safety": True,
            "simulator_only_empirical_exploration_exception": True}:
        raise _error("exploration contract changed")
    gates = stage.get("measurement_gates", {})
    expected_gates = {
        "baseline_arm_id": "hold4",
        "terminal_state_indices": [64, 65, 66, 67, 68, 69],
        "maximum_capture_source_rz_distance_m": 0.025,
        "maximum_capture_rz_step_speed_m_per_s": 0.1,
        "maximum_capture_absolute_source_ip_fraction": 0.05,
        "minimum_round_score_improvement_over_hold": 0.02,
        "minimum_final_score_improvement_over_external_round0_hold": 0.25,
        "minimum_combined_complete_fit_weight_windows_for_model_readiness": 15,
        "critical_replay_exact_checked_trajectory_required": True,
        "selection_order": [
            "capture_first", "minimum_terminal_worst_normalized_score",
            "minimum_terminal_max_source_rz_distance",
            "minimum_terminal_max_rz_step_speed",
            "minimum_terminal_max_absolute_source_ip_fraction", "stable_arm_id"],
        "both_fresh_rounds_required": True,
        "pass_is_teacher_utility_and_development_data_only": True,
    }
    if gates != expected_gates:
        raise _error("measurement gates changed")
    if stage.get("storage_gate") != {
            "minimum_free_bytes_before_run": 120000000000,
            "maximum_estimated_raw_bytes": 50000000000,
            "minimum_free_bytes_after_estimate": 40000000000,
            "output_must_not_exist": True,
            "raw_compression": "forbidden"}:
        raise _error("storage gate changed")
    if stage.get("prefix_gates") != {
            "fresh_round_reference_state_counts": [54, 58],
            "fresh_round_reference_action_counts": [53, 57],
            "external_round0_all_five_prefix_checks_passed": True,
            "fresh_siblings_exact": True,
            "next_round_matches_selected_parent": True,
            "critical_replay_matches_selected_full_sequence": True,
            "sprsina_hash_is_diagnostic_only": True}:
        raise _error("prefix gates changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise _error("semantic artifact contract changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise _error("diagnostic artifact contract changed")
    expected_routes = {
        "offline_or_input_fail": "ONE_MS_ID2Z7_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "storage_fail": "ONE_MS_ID2Z7_STORAGE_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2Z7_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2Z7_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "prefix_mismatch": "ONE_MS_ID2Z7_PREFIX_MISMATCH_STOP",
        "round_no_eligible_arm": (
            "ONE_MS_ID2Z7_FRESH_BRANCH_NO_UTILITY_ACTION_BASIS_REVIEW_REQUIRED"),
        "replay_fail": "ONE_MS_ID2Z7_SELECTED_SEQUENCE_REPLAY_FAIL_STOP",
        "teacher_progress_data_insufficient": (
            "ONE_MS_ID2Z7_TEACHER_PROGRESS_PASS_DATA_INSUFFICIENT_REVIEW"),
        "pass": (
            "ONE_MS_ID2Z7_BRANCH_CONTINUATION_PASS_REPLAY_RECOURSE_AND_SMALL_MODEL_DESIGN_ONLY"),
    }
    if stage.get("routes") != expected_routes:
        raise _error("routes changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], dict[str, Any], Any, dict[str, Any], dict[str, Any],
        list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = _inside(path, "ID2Z7 config")
    if z6.z5.base.sha256(path) != CONFIG_SHA256:
        raise _error("ID2Z7 config hash mismatch")
    stage = _json(path)
    _require(stage)
    required = {
        "design", "id2z6_config", "id2z6_result_report", "id2z6_result",
        "id2z6_corrected_independent", "id2z6_round0_hold4",
        "id2z6_round0_b4", "id2z6_round0_f4", "id2z6_round0_b2f2",
        "id2z6_round0_f2b2"}
    if set(stage.get("evidence", {})) != required:
        raise _error("evidence set changed")
    for name, spec in stage["evidence"].items():
        evidence = _inside(ROOT / spec["path"], name)
        if z6.z5.base.sha256(evidence) != spec["sha256"]:
            raise _error(f"evidence mismatch: {name}")
    z6_result = _json(ROOT / stage["evidence"]["id2z6_result"]["path"])
    z6_audit = _json(
        ROOT / stage["evidence"]["id2z6_corrected_independent"]["path"])
    if (z6_result.get("route")
            != stage["evidence"]["id2z6_result"]["required_route"]
            or z6_result.get("passed") is not False
            or z6_audit.get("audit_passed") is not True
            or z6_audit.get("primary_sha256")
            != stage["evidence"]["id2z6_result"]["sha256"]):
        raise _error("ID2Z6 result/audit is ineligible")
    round_values = z6_result.get("round_metrics", [])
    if (len(round_values) != 1 or round_values[0].get("passed") is not True
            or round_values[0].get("selected_arm_id") != "f4"
            or z6_result.get("selected_three_macro_sequence") != ["f4"]):
        raise _error("ID2Z6 round-0 selection changed")

    z6_stage, cfg, targets, w2_compact, w2_selected = z6.load(
        ROOT / stage["evidence"]["id2z6_config"]["path"])
    generated = z6.initial_round_streams(
        z6_stage, cfg, targets, w2_selected)
    compact_names = [
        "id2z6_round0_hold4", "id2z6_round0_b4", "id2z6_round0_f4",
        "id2z6_round0_b2f2", "id2z6_round0_f2b2"]
    round0_rows = [_json(ROOT / stage["evidence"][name]["path"])
                   for name in compact_names]
    if [row.get("arm_id") for row in round0_rows] != list(ARM_IDS):
        raise _error("ID2Z6 round-0 compact order changed")
    generated_by_arm = {row["arm_id"]: row for row in generated}
    for row in round0_rows:
        arm = str(row.get("arm_id"))
        expected = generated_by_arm[arm]
        if (row.get("passed") is not True or int(row.get("fit_weight", 0)) != 1
                or len(row.get("states", [])) != 70
                or len(row.get("actions", [])) != 69
                or [value.get("expected_card15_fields")
                    for value in row["actions"]]
                != [value.get("expected_card15_fields")
                    for value in expected["actions"]]):
            raise _error(f"ID2Z6 round-0 compact mismatch: {arm}")
    parent_constructed = generated_by_arm["f4"]
    parent_compact = next(row for row in round0_rows if row["arm_id"] == "f4")
    return (stage, z6_stage, cfg, targets, w2_compact, round0_rows,
            parent_constructed, parent_compact, z6_result)


def configure_run_root(cfg: Any, output: Path) -> dict[str, Any]:
    output = _inside(output, "ID2Z7 output")
    required = (output / "rollouts").resolve()
    if "rgeo_zgeo_1ms_nr1_runs" in required.parts:
        raise _error("historical default run root selected")
    try:
        required.relative_to(output.resolve())
    except ValueError as exc:
        raise _error("run root leaves output") from exc
    cfg.run_root = required
    if Path(cfg.run_root).resolve() != required:
        raise _error("run root assignment failed")
    return {
        "passed": True,
        "output": str(output),
        "required_run_root": str(required),
        "configured_run_root": str(Path(cfg.run_root).resolve()),
        "historical_default_forbidden": True,
        "verified_before_runner_construction": True,
    }


def fresh_round_streams(z6_stage: dict[str, Any], cfg: Any,
                        targets: dict[str, Any], parent: dict[str, Any],
                        round_index: int) -> list[dict[str, Any]]:
    if round_index not in FRESH_ROUNDS:
        raise _error("fresh round index changed")
    return z6.next_round_streams(z6_stage, cfg, targets, parent, round_index)


def execute_row(cfg: Any, z6_stage: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], source_revision: str,
                output: Path, *, runner_cls: type | None = None) -> dict[str, Any]:
    required = (output / "rollouts").resolve()
    if Path(cfg.run_root).resolve() != required:
        raise _error("run root isolation failed before runner construction")
    row = z6.one_rollout(
        cfg, z6_stage, stream, z6._reference(reference, len(reference["states"])),
        runner_cls=runner_cls)
    row.update({"schema_version": SCHEMA, "source_revision": source_revision})
    z6.z5.z3.z1.y1r1.y1.x1.write_new(
        output / f"{stream['rollout_id']}.json", row)
    return row


def _combined_final_metrics(external_round: dict[str, Any],
                            fresh_rounds: Sequence[dict[str, Any]],
                            external_rows: Sequence[dict[str, Any]],
                            fresh_rows: Sequence[dict[str, Any]],
                            z6_stage: dict[str, Any],
                            selected: dict[str, Any] | None,
                            replay: dict[str, Any] | None) -> dict[str, Any]:
    value = z6.final_metrics(
        [external_round, *fresh_rounds], [*external_rows, *fresh_rows],
        z6_stage, selected, replay)
    value["external_round0_fit_weight_windows"] = sum(
        bool(row.get("passed") and int(row.get("fit_weight", 0)) == 1)
        for row in external_rows)
    value["fresh_complete_fit_weight_windows"] = sum(
        bool(row.get("passed") and int(row.get("fit_weight", 0)) == 1)
        for row in fresh_rows)
    return value


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, fresh_rounds: Sequence[dict[str, Any]],
              scientific: dict[str, Any]) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if len(fresh_rounds) != 2 or not all(
            value and value.get("passed") for value in fresh_rounds):
        return stage["routes"]["round_no_eligible_arm"]
    if not scientific.get("critical_replay_check", {}).get("passed"):
        return stage["routes"]["replay_fail"]
    if not scientific.get("teacher_utility_passed"):
        return stage["routes"]["round_no_eligible_arm"]
    if not scientific.get("development_data_ready"):
        return stage["routes"]["teacher_progress_data_insufficient"]
    return stage["routes"]["pass"]


def _static_matrix(z6_stage: dict[str, Any], cfg: Any,
                   targets: dict[str, Any], parent: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for b in fresh_round_streams(z6_stage, cfg, targets, parent, 1):
        b_check = z6.validate_stream(b, z6_stage, cfg, targets)
        for c in fresh_round_streams(z6_stage, cfg, targets, b, 2):
            c_check = z6.validate_stream(c, z6_stage, cfg, targets)
            checks.append({
                "sequence": ["f4", b["arm_id"], c["arm_id"]],
                "passed": bool(b_check["passed"] and c_check["passed"]),
                "minimum_absolute_current_headroom_a": min(
                    b_check["minimum_absolute_current_headroom_a"],
                    c_check["minimum_absolute_current_headroom_a"]),
                "failures": list(dict.fromkeys(
                    b_check["failures"] + c_check["failures"])),
            })
    return checks


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    isolation: dict[str, Any] = {}
    try:
        stage, z6_stage, cfg, targets, _, _, parent, _, _ = load(path)
        checks = _static_matrix(z6_stage, cfg, targets, parent)
        if len(checks) != 25 or not all(value["passed"] for value in checks):
            failures.append("FRESH_TWO_ROUND_ACTION_MATRIX_NOT_ADMISSIBLE")
        probe_output = ROOT / "id2z7_offline_run_root_probe"
        isolation = configure_run_root(cfg, probe_output)
        if Path(cfg.run_root).resolve() != (probe_output / "rollouts").resolve():
            failures.append("RUN_ROOT_ISOLATION")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": "rgeo-zgeo-1ms-id2z7-offline-v1",
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": not failures,
        "failures": failures,
        "static_two_round_sequence_count": len(checks),
        "static_two_round_sequences_passed": sum(bool(row["passed"]) for row in checks),
        "minimum_constructed_headroom_a": (
            min(row["minimum_absolute_current_headroom_a"] for row in checks)
            if checks else None),
        "sequence_checks": checks,
        "run_root_isolation": isolation,
        "external_round0_fit_weight_windows": 5,
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "models_fit_or_updated": 0,
    }


def execute(stage: dict[str, Any], z6_stage: dict[str, Any], cfg: Any,
            targets: dict[str, Any], external_rows: list[dict[str, Any]],
            parent_constructed: dict[str, Any], parent_compact: dict[str, Any],
            z6_result: dict[str, Any], source_revision: str, output: Path,
            storage_gate: dict[str, Any]) -> dict[str, Any]:
    isolation = configure_run_root(cfg, output)
    rows: list[dict[str, Any]] = []
    fresh_round_values: list[dict[str, Any]] = []
    prefix_values: list[dict[str, Any]] = []
    selected_constructed = parent_constructed
    selected_row: dict[str, Any] | None = None
    reference_row = parent_compact
    execution = True
    for round_index in FRESH_ROUNDS:
        streams = fresh_round_streams(
            z6_stage, cfg, targets, selected_constructed, round_index)
        if not all(z6.validate_stream(row, z6_stage, cfg, targets)["passed"]
                   for row in streams):
            execution = False
            break
        decision = int(z6_stage["rounds"][round_index]["decision_state_index"])
        round_rows: list[dict[str, Any]] = []
        for stream in streams:
            row = execute_row(
                cfg, z6_stage, stream, reference_row, source_revision, output)
            rows.append(row)
            round_rows.append(row)
            prefix_values.append(z6.prefix_check(
                row, reference_row, decision + 1, decision,
                stage["semantic_artifacts"]))
            if not row.get("passed") and not z6.safe_stop(row, z6_stage):
                execution = False
                break
        if not execution:
            break
        value = z6.round_metrics(round_rows, z6_stage, round_index, cfg)
        fresh_round_values.append(value)
        if not value.get("passed"):
            break
        selected_arm = str(value["selected_arm_id"])
        selected_constructed = next(
            stream for stream in streams if stream["arm_id"] == selected_arm)
        selected_row = next(row for row in round_rows
                            if row["arm_id"] == selected_arm)
        reference_row = selected_row

    replay_row: dict[str, Any] | None = None
    if len(fresh_round_values) == 2 and all(
            value.get("passed") for value in fresh_round_values):
        replay_stream = z6.critical_replay_stream(selected_constructed)
        replay_stream["round_index"] = 2
        replay_row = execute_row(
            cfg, z6_stage, replay_stream, selected_row or {},
            source_revision, output)
        rows.append(replay_row)
        prefix_values.append(z6.prefix_check(
            replay_row, selected_row or {}, 70, 69, stage["semantic_artifacts"]))
        if not replay_row.get("passed") and not z6.safe_stop(replay_row, z6_stage):
            execution = False

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
    prefixes_ok = bool(prefix_values and all(row.get("passed") for row in prefix_values))
    inventory = z6.z5.z3.z1.y1r1.y1.x1.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    external_round = z6_result["round_metrics"][0]
    scientific = _combined_final_metrics(
        external_round, fresh_round_values, external_rows, rows,
        z6_stage, selected_row, replay_row)
    route = route_for(
        stage, execution, raw_ok, prefixes_ok, fresh_round_values, scientific)
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": route == stage["routes"]["pass"],
        "route": route,
        "storage_gate": storage_gate,
        "run_root_isolation": isolation,
        "execution_integrity_passed": execution,
        "raw_integrity_passed": raw_ok,
        "external_round0_metric": external_round,
        "fresh_prefix_checks": prefix_values,
        "fresh_round_metrics": fresh_round_values,
        "scientific_metrics": scientific,
        "selected_three_macro_sequence": scientific[
            "selected_three_macro_sequence"],
        "fresh_rollouts_completed": len(rows),
        "fresh_complete_rollouts": sum(bool(row.get("passed")) for row in rows),
        "fresh_guarded_safe_stops": sum(z6.safe_stop(row, z6_stage) for row in rows),
        **counters,
        **inventory,
        "external_round0_rollouts_read": 5,
        "interrupted_id2z6_round1_records_read_for_fit_or_selection": 0,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "compact_data_role": stage["data_use"],
        "claim_boundary": (
            "Finite source-local fresh later-round branch continuation and "
            "prospective complete-window development evidence; not hold, "
            "recovery, controller, waypoint, crossing or reachability qualification."),
    }
    z6.z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def _failure_result(stage: dict[str, Any], source_revision: str, output: Path,
                    storage_gate: dict[str, Any], exc: Exception) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(output.glob("*.json")):
        if path.name in {"offline_preflight.json", "result.json",
                          "independent_raw_audit.json"}:
            continue
        try:
            row = _json(path)
        except Exception:
            continue
        if "rollout_id" in row:
            rows.append(row)
    counters = {
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in rows),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in rows),
        "plant_advance_gotsc_calls": sum(
            int(row.get("plant_advance_gotsc_calls", 0)) for row in rows),
        "verified_plant_advances": sum(
            int(row.get("verified_plant_advances", 0)) for row in rows),
    }
    try:
        inventory = z6.z5.z3.z1.y1r1.y1.x1.raw_inventory(output, rows, stage)
    except Exception as inventory_exc:
        inventory = {
            "required_artifact_files": 0,
            "required_artifact_bytes": 0,
            "required_artifact_inventory_sha256": None,
            "missing_required_artifacts": [
                f"FINALIZER:{type(inventory_exc).__name__}:{inventory_exc}"],
        }
    return {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": False,
        "route": stage["routes"]["execution_or_interface_fail"],
        "failure": f"{type(exc).__name__}:{exc}",
        "storage_gate": storage_gate,
        "run_root_isolation": {
            "passed": True,
            "output": str(output.resolve()),
            "required_run_root": str((output / "rollouts").resolve()),
            "configured_run_root": str((output / "rollouts").resolve()),
            "historical_default_forbidden": True,
            "verified_before_runner_construction": True,
        },
        "fresh_rollouts_completed": len(rows),
        "fresh_complete_rollouts": sum(bool(row.get("passed")) for row in rows),
        **counters,
        **inventory,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": "Best-effort classified ID2Z7 execution failure; no scientific verdict.",
    }


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = _inside(output, "ID2Z7 output")
    if output.exists():
        raise FileExistsError(str(output))
    (stage, z6_stage, cfg, targets, _, external_rows, parent_constructed,
     parent_compact, z6_result) = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = z6.z5.z3.z1.y1r1.y1.x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    z6.z5.z3.z1.y1r1.y1.x1.write_new(
        output / "offline_preflight.json", preflight)
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
            "fresh_rollouts_completed": 0,
            "reset_calls": 0,
            "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0,
            "verified_plant_advances": 0,
            "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
        }
        z6.z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
        return result
    try:
        return execute(
            stage, z6_stage, cfg, targets, external_rows, parent_constructed,
            parent_compact, z6_result, source_revision, output, storage_gate)
    except Exception as exc:
        result = _failure_result(stage, source_revision, output, storage_gate, exc)
        if not (output / "result.json").exists():
            z6.z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
        return result


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
