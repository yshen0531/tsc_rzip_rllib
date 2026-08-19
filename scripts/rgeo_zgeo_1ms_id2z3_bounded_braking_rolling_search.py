#!/usr/bin/env python3
"""Run the frozen ID-2Z3 bounded braking rolling-search campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch as z2  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


z1 = z2.z1
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z3_bounded_braking_rolling_search.json"
CONFIG_SHA256 = "434d4629362e154a9d4f26e88b677ab428e75baf26c2d0500a3f113e2baded86"
SCHEMA = "rgeo-zgeo-1ms-id2z3-bounded-braking-rolling-search-result-v1"
ARM_IDS = ("hold", "p03forward4", "p07minus4")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(z1.y1r1.y1.x1.inside_root(path, "JSON evidence").read_text(
        encoding="utf-8"))
    if not isinstance(value, dict):
        raise z1.y1r1.y1.x1.InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z3-bounded-braking-rolling-search-v1",
        "identity": "rgeo-zgeo-1ms-id2z3-bounded-braking-rolling-search-v1",
        "stage": "ID-2Z3",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "maximum_rounds": 5,
        "maximum_branches_per_round": 3,
        "maximum_rollouts": 15,
        "maximum_reset_calls": 15,
        "maximum_advance_attempts": 1455,
        "maximum_gotsc_calls": 1455,
        "maximum_verified_plant_advances": 1455,
        "maximum_retained_states": 1470,
        "required_artifact_files_if_all_complete": 7350,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": (
            "tsc_only_canonical_source_bounded_braking_rolling_search"),
        "data_use": "braking_sequence_search_and_route_evidence_only",
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise z1.y1r1.y1.x1.InputIntegrityError(f"frozen field mismatch: {key}")
    expected_rounds = []
    for index, decision in enumerate((77, 81, 85, 89, 93)):
        expected_rounds.append({
            "round_id": f"round_{index}_state{decision}",
            "decision_state_index": decision,
            "macro_first_issue": decision,
            "macro_last_issue": decision + 3,
            "hold_first_issue": decision + 4,
            "hold_last_issue": decision + 11,
            "horizon_steps": decision + 12,
            "terminal_state_index": decision + 12,
        })
    if stage.get("rounds") != expected_rounds:
        raise z1.y1r1.y1.x1.InputIntegrityError("round matrix changed")
    if stage.get("candidate_specs") != [
        {"arm_id": "hold", "coordinate": "hold", "level_delta": 0},
        {"arm_id": "p03forward4", "coordinate": "p03", "level_delta": 4},
        {"arm_id": "p07minus4", "coordinate": "p07:minus", "level_delta": 4},
    ]:
        raise z1.y1r1.y1.x1.InputIntegrityError("candidate matrix changed")
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
            "relative_four_issue_macro_then_eight_hold_composed_with_current_exact_target"),
        "invalid_exact_or_headroom_combination": (
            "exclude_before_tsc_and_forbid_selection"),
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("action semantics changed")
    if stage.get("measurement_gates") != {
        "baseline_arm_id": "hold",
        "response_horizon_offsets": list(range(1, 13)),
        "active_terminal_offset": 4,
        "terminal_speed_state_count": 4,
        "minimum_peak_rz_response_m": 0.00005,
        "maximum_paired_ip_response_a": 150.0,
        "maximum_terminal_distance_regression_vs_hold_m": 0.00025,
        "minimum_terminal_max_speed_improvement_m_per_s": 0.01,
        "minimum_nominated_arms_per_round": 1,
        "selection_order": [
            "minimum_terminal_max_rz_speed_m_per_s",
            "minimum_terminal_source_rz_distance",
            "minimum_absolute_terminal_source_ip_offset",
            "stable_arm_id",
        ],
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("measurement gates changed")
    if stage.get("stabilization_gate") != {
        "terminal_state_count": 4,
        "maximum_source_rz_distance_m": 0.025,
        "maximum_rz_step_speed_m_per_s": 0.1,
        "maximum_absolute_source_ip_fraction": 0.05,
        "identity": (
            "coarse_source_corridor_stabilization_candidate_not_5mm_short_hold"),
        "pass_authorizes": "fresh_repeat_and_recourse_design_only",
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("stabilization gate changed")
    if stage.get("prefix_gates") != {
        "initial_reference_state_count": 78,
        "initial_reference_action_count": 77,
        "all_siblings_exact": True,
        "later_round_matches_prior_selected_logical_prefix": True,
        "lookahead_hold_is_not_main_path": True,
        "sprsina_hash_is_diagnostic_only": True,
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("prefix gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 140000000000,
        "maximum_estimated_raw_bytes": 90000000000,
        "minimum_free_bytes_after_estimate": 50000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise z1.y1r1.y1.x1.InputIntegrityError("storage gate changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any], dict[str, Any]]:
    path = z1.y1r1.y1.x1.inside_root(path, "ID2Z3 config")
    if z1.y1r1.y1.x1.sha256(path) != CONFIG_SHA256:
        raise z1.y1r1.y1.x1.InputIntegrityError("ID2Z3 config hash mismatch")
    stage = _json(path)
    _require(stage)
    required = {
        "design", "id2z2_config", "id2z2_result_report", "id2z2_result",
        "id2z2_independent", "id2z2_selected_compact",
    }
    if set(stage.get("evidence", {})) != required:
        raise z1.y1r1.y1.x1.InputIntegrityError("evidence set changed")
    for name, spec in stage["evidence"].items():
        evidence = z1.y1r1.y1.x1.inside_root(ROOT / spec["path"], name)
        if z1.y1r1.y1.x1.sha256(evidence) != spec["sha256"]:
            raise z1.y1r1.y1.x1.InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / stage["evidence"]["id2z2_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2z2_independent"]["path"])
    selected = _json(ROOT / stage["evidence"]["id2z2_selected_compact"]["path"])
    result_spec = stage["evidence"]["id2z2_result"]
    compact_spec = stage["evidence"]["id2z2_selected_compact"]
    if (result.get("passed") is not True
            or result.get("route") != result_spec["required_route"]
            or result.get("selected_two_macro_sequence")
            != result_spec["required_selected_sequence"]
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")):
        raise z1.y1r1.y1.x1.InputIntegrityError("ID2Z2 result is not eligible")
    state_count = int(compact_spec["required_logical_state_count"])
    action_count = int(compact_spec["required_logical_action_count"])
    if (selected.get("rollout_id") != "r1__p03forward4"
            or selected.get("passed") is not True
            or len(selected.get("states", [])) < state_count
            or len(selected.get("actions", [])) < action_count):
        raise z1.y1r1.y1.x1.InputIntegrityError("ID2Z2 logical prefix changed")

    z2_stage, cfg, targets, z1_reference, z1_stream = z2.load(
        ROOT / stage["evidence"]["id2z2_config"]["path"])
    round_a = z2.initial_round_streams(z2_stage, cfg, targets, z1_stream)
    selected_a = next(row for row in round_a if row["arm_id"] == "p03forward4")
    round_b = z2.next_round_streams(z2_stage, cfg, targets, selected_a)
    selected_b = next(row for row in round_b if row["arm_id"] == "p03forward4")
    for issue in range(action_count):
        if (selected_b["actions"][issue]["expected_card15_fields"]
                != selected["actions"][issue]["expected_card15_fields"]):
            raise z1.y1r1.y1.x1.InputIntegrityError(
                f"ID2Z2 selected action mismatch: {issue}")
    return stage, cfg, targets, selected, selected_b


def build_round_streams(stage: dict[str, Any], cfg: Any,
                        targets: dict[str, Card15Target],
                        prefix_targets: Sequence[Card15Target],
                        prefix_virtual: Sequence[Sequence[float]],
                        round_index: int,
                        selected_arm_history: Sequence[str]) -> list[dict[str, Any]]:
    spec = stage["rounds"][round_index]
    decision = int(spec["decision_state_index"])
    horizon = int(spec["horizon_steps"])
    if len(prefix_targets) != decision or len(prefix_virtual) != decision:
        raise z1.y1r1.y1.x1.InputIntegrityError("round prefix dimensions changed")
    q0 = targets["q0"]
    rows: list[dict[str, Any]] = []
    for candidate in stage["candidate_specs"]:
        arm_id = str(candidate["arm_id"])
        sequence = list(prefix_targets)
        virtual = [[float(value) for value in row] for row in prefix_virtual]
        current_target = sequence[-1]
        current_virtual = list(virtual[-1])
        for issue in range(decision, horizon):
            if issue <= int(spec["macro_last_issue"]) and arm_id != "hold":
                delta = z2._increment_target(
                    q0, targets, candidate, cfg,
                    f"id2z3.r{round_index}.{arm_id}.delta.{issue}")
                current_target = z1.c1._translated_target(
                    current_target, q0, delta, cfg,
                    f"id2z3.r{round_index}.{arm_id}.target.{issue}")
                current_virtual = z2._virtual_step(current_virtual, candidate)
            sequence.append(current_target)
            virtual.append(list(current_virtual))
        rollout_id = f"r{round_index}__{arm_id}"
        actions = z1.c1._actions(sequence, cfg, rollout_id, virtual)
        rows.append({
            **candidate,
            "rollout_id": rollout_id,
            "round_index": round_index,
            "round_id": spec["round_id"],
            "parent_selected_arm_history": list(selected_arm_history),
            "cell_id": rollout_id,
            "cell_kind": "bounded_braking_rolling_search",
            "context_id": (
                "canonical_source_id2z2_selected_state77__"
                + "__".join(selected_arm_history)),
            "direction_id": candidate["coordinate"],
            "sign": "minus" if arm_id == "p07minus4" else None,
            "probe_issue_step": decision,
            "probe_duration_issues": 12,
            "logical_macro_issue_steps": list(range(decision, decision + 4)),
            "lookahead_hold_issue_steps": list(range(decision + 4, horizon)),
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
    decision = int(stage["rounds"][0]["decision_state_index"])
    return build_round_streams(
        stage, cfg, targets, selected_stream["targets"][:decision],
        [row["probe_virtual_action"]
         for row in selected_stream["actions"][:decision]], 0, [])


def next_round_streams(stage: dict[str, Any], cfg: Any,
                       targets: dict[str, Card15Target],
                       selected_stream: dict[str, Any], round_index: int,
                       selected_arm_history: Sequence[str]) -> list[dict[str, Any]]:
    decision = int(stage["rounds"][round_index]["decision_state_index"])
    return build_round_streams(
        stage, cfg, targets, selected_stream["targets"][:decision],
        [row["probe_virtual_action"]
         for row in selected_stream["actions"][:decision]],
        round_index, selected_arm_history)


def validate_stream(stream: dict[str, Any], stage: dict[str, Any],
                    cfg: Any) -> dict[str, Any]:
    spec = stage["rounds"][int(stream["round_index"])]
    failures: list[str] = []
    horizon = int(spec["horizon_steps"])
    decision = int(spec["decision_state_index"])
    macro_last = int(spec["macro_last_issue"])
    actions = stream["actions"]
    if len(actions) != horizon or len(stream["targets"]) != horizon:
        failures.append("STREAM_DIMENSIONS")
    for issue, action in enumerate(actions):
        if (int(action["issue_step"]) != issue
                or int(action["effect_state_index"]) != issue + 1
                or float(action["maximum_issued_delta_a"]) > 0.3000000001):
            failures.append(f"ACTION_CONTRACT:{issue}")
    for issue in range(macro_last + 1, horizon):
        if (actions[issue]["expected_card15_fields"]
                != actions[macro_last]["expected_card15_fields"]
                or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
            failures.append(f"LOOKAHEAD_HOLD:{issue}")
    expected_nonzero = 0 if stream["arm_id"] == "hold" else 1
    for issue in range(decision, macro_last + 1):
        before = actions[issue - 1]["probe_virtual_action"]
        after = actions[issue]["probe_virtual_action"]
        changed = [abs(float(a) - float(b))
                   for a, b in zip(after[:3], before[:3])]
        nonzero = [value for value in changed if value > 0.0]
        if len(nonzero) != expected_nonzero or any(value != 1.0 for value in nonzero):
            failures.append(f"VIRTUAL_STEP:{issue}")
    headroom = z2._headroom(stream, cfg)
    if headroom < float(stage["action_semantics"][
            "minimum_absolute_current_headroom_a"]) - 1e-9:
        failures.append("ABSOLUTE_CURRENT_HEADROOM")
    return {
        "rollout_id": stream["rollout_id"],
        "round_index": stream["round_index"],
        "arm_id": stream["arm_id"],
        "minimum_absolute_current_headroom_a": headroom,
        "maximum_issued_delta_a": max(
            float(action["maximum_issued_delta_a"]) for action in actions),
        "passed": not failures,
        "failures": failures,
    }


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    minimum_headroom = math.inf
    try:
        stage, cfg, targets, _, selected_stream = load(path)
        frontier: list[tuple[dict[str, Any], list[str]]] = [
            (selected_stream, [])]
        for round_index in range(int(stage["maximum_rounds"])):
            next_frontier: list[tuple[dict[str, Any], list[str]]] = []
            for parent, history in frontier:
                streams = (initial_round_streams(stage, cfg, targets, parent)
                           if round_index == 0 else next_round_streams(
                               stage, cfg, targets, parent, round_index, history))
                parent_checks = []
                for stream in streams:
                    check = validate_stream(stream, stage, cfg)
                    check["parent_selected_arm_history"] = list(history)
                    check["combination_id"] = "__then__".join(
                        [*history, str(stream["arm_id"])])
                    checks.append(check)
                    parent_checks.append(check)
                    minimum_headroom = min(
                        minimum_headroom,
                        float(check["minimum_absolute_current_headroom_a"]))
                    if check["passed"]:
                        next_frontier.append(
                            (stream, [*history, str(stream["arm_id"])]))
                hold = next(value for value in parent_checks
                            if value["arm_id"] == "hold")
                if not hold["passed"]:
                    raise z1.y1r1.y1.x1.InputIntegrityError(
                        f"mandatory hold inadmissible: {history}")
            frontier = next_frontier
        if len(checks) > 363:
            raise z1.y1r1.y1.x1.InputIntegrityError("offline tree budget changed")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": z1.y1r1.y1.x1.sha256(path),
        "passed": not failures,
        "failures": failures,
        "candidate_stream_checks": checks,
        "candidate_stream_check_count": len(checks),
        "admissible_stream_count": sum(bool(value["passed"]) for value in checks),
        "excluded_stream_count": sum(not value["passed"] for value in checks),
        "minimum_absolute_current_headroom_a_over_all_constructed": (
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


def _step_speed(states: Sequence[dict[str, Any]], index: int) -> float:
    return math.hypot(
        float(states[index]["r_geo_m"]) - float(states[index - 1]["r_geo_m"]),
        float(states[index]["z_geo_m"]) - float(states[index - 1]["z_geo_m"]),
    ) / 0.001


def stabilization_metrics(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    states = row.get("states", [])
    gate = stage["stabilization_gate"]
    count = int(gate["terminal_state_count"])
    if not row.get("passed") or len(states) < count + 1:
        return {"passed": False, "reason": "incomplete"}
    source = states[0]
    indices = list(range(len(states) - count, len(states)))
    distances = [_source_distance(states[index], source) for index in indices]
    speeds = [_step_speed(states, index) for index in indices]
    ip_offsets = [abs(float(states[index]["ip_a"]) - float(source["ip_a"]))
                  for index in indices]
    ip_cap = float(gate["maximum_absolute_source_ip_fraction"]) * abs(
        float(source["ip_a"]))
    passed = bool(
        max(distances) <= float(gate["maximum_source_rz_distance_m"])
        and max(speeds) <= float(gate["maximum_rz_step_speed_m_per_s"])
        and max(ip_offsets) <= ip_cap)
    return {
        "terminal_state_indices": indices,
        "source_rz_distance_m": distances,
        "rz_step_speed_m_per_s": speeds,
        "absolute_source_ip_offset_a": ip_offsets,
        "maximum_source_rz_distance_m": max(distances),
        "maximum_rz_step_speed_m_per_s": max(speeds),
        "maximum_absolute_source_ip_offset_a": max(ip_offsets),
        "source_ip_cap_a": ip_cap,
        "passed": passed,
    }


def round_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                  round_index: int, cfg: Any | None = None) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    spec = stage["rounds"][round_index]
    decision = int(spec["decision_state_index"])
    terminal = int(spec["terminal_state_index"])
    indices = [decision + int(value)
               for value in gates["response_horizon_offsets"]]
    by_arm = {row.get("arm_id"): row for row in rows}
    baseline = by_arm.get("hold")
    metrics: list[dict[str, Any]] = []
    if (baseline is None or not baseline.get("passed")
            or len(baseline.get("states", [])) != terminal + 1):
        return {
            "round_index": round_index,
            "round_id": spec["round_id"],
            "baseline_complete": False,
            "branch_metrics": [],
            "nominated_arm_ids": [],
            "selected_arm_id": None,
            "selected_rollout_id": None,
            "stabilization_reached": False,
            "passed": False,
        }
    source = baseline["states"][0]
    baseline_distances = [_source_distance(state, source)
                          for state in baseline["states"]]
    speed_count = int(gates["terminal_speed_state_count"])
    speed_indices = list(range(terminal - speed_count + 1, terminal + 1))
    baseline_speeds = [_step_speed(baseline["states"], index)
                       for index in speed_indices]

    def common(row: dict[str, Any]) -> dict[str, Any]:
        distances = [_source_distance(state, source) for state in row["states"]]
        speeds = [_step_speed(row["states"], index) for index in speed_indices]
        value = {
            "rollout_id": row["rollout_id"],
            "arm_id": row["arm_id"],
            "coordinate": row["coordinate"],
            "execution_status": "complete",
            "decision_source_rz_distance_m": distances[decision],
            "terminal_source_rz_distance_m": distances[terminal],
            "terminal_source_ip_offset_a": (
                float(row["states"][terminal]["ip_a"]) - float(source["ip_a"])),
            "terminal_speed_state_indices": speed_indices,
            "terminal_rz_step_speed_m_per_s": speeds,
            "terminal_max_rz_step_speed_m_per_s": max(speeds),
            "stabilization": stabilization_metrics(row, stage),
        }
        if cfg is not None:
            value.update(z1._trajectory_diagnostics(row, source, cfg, stage))
        return value

    baseline_metric = common(baseline)
    baseline_metric.update({"baseline": True, "eligible": False})
    metrics.append(baseline_metric)
    nominated: list[dict[str, Any]] = []
    stabilized: list[dict[str, Any]] = []
    if baseline_metric["stabilization"]["passed"]:
        stabilized.append(baseline_metric)
    for arm_id in ARM_IDS[1:]:
        row = by_arm.get(arm_id)
        if (row is None or not row.get("passed")
                or len(row.get("states", [])) != terminal + 1):
            metrics.append({
                "rollout_id": row.get("rollout_id") if row else None,
                "arm_id": arm_id,
                "execution_status": "incomplete_or_excluded",
                "eligible": False,
            })
            continue
        metric = common(row)
        response = [[
            float(row["states"][index]["r_geo_m"])
            - float(baseline["states"][index]["r_geo_m"]),
            float(row["states"][index]["z_geo_m"])
            - float(baseline["states"][index]["z_geo_m"]),
            float(row["states"][index]["ip_a"])
            - float(baseline["states"][index]["ip_a"]),
        ] for index in indices]
        peak = max(math.hypot(value[0], value[1]) for value in response)
        max_ip = max(abs(value[2]) for value in response)
        terminal_regression = (
            float(metric["terminal_source_rz_distance_m"])
            - float(baseline_metric["terminal_source_rz_distance_m"]))
        speed_improvement = (
            float(baseline_metric["terminal_max_rz_step_speed_m_per_s"])
            - float(metric["terminal_max_rz_step_speed_m_per_s"]))
        eligible = bool(
            peak >= float(gates["minimum_peak_rz_response_m"])
            and max_ip <= float(gates["maximum_paired_ip_response_a"])
            and terminal_regression <= float(
                gates["maximum_terminal_distance_regression_vs_hold_m"])
            and speed_improvement >= float(
                gates["minimum_terminal_max_speed_improvement_m_per_s"]))
        metric.update({
            "response_state_indices": indices,
            "paired_rzi_response": response,
            "maximum_paired_rz_response_m": peak,
            "maximum_paired_ip_response_a": max_ip,
            "terminal_source_distance_regression_vs_hold_m": terminal_regression,
            "terminal_max_speed_improvement_vs_hold_m_per_s": speed_improvement,
            "eligible": eligible,
        })
        metrics.append(metric)
        if eligible:
            nominated.append(metric)
        if metric["stabilization"]["passed"]:
            stabilized.append(metric)

    def order(value: dict[str, Any]) -> tuple[float, float, float, str]:
        return (
            float(value["terminal_max_rz_step_speed_m_per_s"]),
            float(value["terminal_source_rz_distance_m"]),
            abs(float(value["terminal_source_ip_offset_a"])),
            str(value["arm_id"]),
        )

    stabilized.sort(key=order)
    nominated.sort(key=order)
    selected = stabilized[0] if stabilized else (nominated[0] if nominated else None)
    return {
        "round_index": round_index,
        "round_id": spec["round_id"],
        "decision_state_index": decision,
        "baseline_complete": True,
        "branch_metrics": metrics,
        "nominated_arm_ids": [value["arm_id"] for value in nominated],
        "nominated_arm_count": len(nominated),
        "minimum_nominated_arms": int(gates["minimum_nominated_arms_per_round"]),
        "stabilized_arm_ids": [value["arm_id"] for value in stabilized],
        "stabilization_reached": bool(stabilized),
        "selected_arm_id": selected["arm_id"] if selected else None,
        "selected_rollout_id": selected["rollout_id"] if selected else None,
        "passed": bool(selected),
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefix_checks: Sequence[dict[str, Any]],
              rounds: Sequence[dict[str, Any]]) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefix_checks or not all(value["passed"] for value in prefix_checks):
        return stage["routes"]["prefix_mismatch"]
    if rounds and rounds[-1].get("stabilization_reached"):
        return stage["routes"]["stabilization_candidate"]
    if not rounds or not rounds[-1].get("passed"):
        return stage["routes"]["no_braking_arm"]
    return stage["routes"]["budget_exhausted"]


def _runtime(stage: dict[str, Any], round_index: int) -> dict[str, Any]:
    runtime = dict(stage)
    runtime["horizon_steps"] = int(stage["rounds"][round_index]["horizon_steps"])
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    return runtime


def execute_row(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                source_revision: str, output: Path) -> dict[str, Any]:
    row = z1.y1r1.y1.x1.one_rollout(
        cfg, _runtime(stage, int(stream["round_index"])), stream)
    row.update({
        "schema_version": SCHEMA,
        "source_revision": source_revision,
    })
    z1.y1r1.y1.x1.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def _inventory(output: Path, rows: Sequence[dict[str, Any]],
               stage: dict[str, Any]) -> dict[str, Any]:
    return z1.y1r1.y1.x1.raw_inventory(output, rows, stage)


def execute(stage: dict[str, Any], cfg: Any,
            targets: dict[str, Card15Target], reference: dict[str, Any],
            selected_stream: dict[str, Any], source_revision: str,
            output: Path, storage_gate: dict[str, Any]) -> dict[str, Any]:
    cfg.run_root = output / "rollouts"
    rows: list[dict[str, Any]] = []
    prefixes: list[dict[str, Any]] = []
    round_results: list[dict[str, Any]] = []
    selected_history: list[str] = []
    parent_stream = selected_stream
    parent_reference = reference
    execution_ok = True
    offline_exclusions: list[dict[str, Any]] = []

    for round_index in range(int(stage["maximum_rounds"])):
        streams = (initial_round_streams(stage, cfg, targets, parent_stream)
                   if round_index == 0 else next_round_streams(
                       stage, cfg, targets, parent_stream, round_index,
                       selected_history))
        admissible: list[dict[str, Any]] = []
        for stream in streams:
            check = validate_stream(stream, stage, cfg)
            if check["passed"]:
                admissible.append(stream)
            else:
                offline_exclusions.append(check)
        if not any(stream["arm_id"] == "hold" for stream in admissible):
            execution_ok = False
            break
        round_rows: list[dict[str, Any]] = []
        for stream in admissible:
            row = execute_row(cfg, stage, stream, source_revision, output)
            rows.append(row)
            round_rows.append(row)
            if not row.get("passed") and not z2.safe_stop(row, stage):
                execution_ok = False
                break
        if not execution_ok:
            break
        decision = int(stage["rounds"][round_index]["decision_state_index"])
        for row in round_rows:
            prefixes.append(z2._prefix_check(
                row, parent_reference, decision + 1, decision,
                stage["semantic_artifacts"]))
        if not all(value["passed"] for value in prefixes[-len(round_rows):]):
            execution_ok = False
            break
        metrics = round_metrics(round_rows, stage, round_index, cfg)
        round_results.append(metrics)
        if not metrics["passed"] or metrics["stabilization_reached"]:
            break
        selected_arm = str(metrics["selected_arm_id"])
        parent_stream = next(stream for stream in admissible
                             if stream["arm_id"] == selected_arm)
        parent_reference = next(row for row in round_rows
                                if row["arm_id"] == selected_arm)
        selected_history.append(selected_arm)

    inventory = _inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(
        execution_ok and not inventory["missing_required_artifacts"]
        and inventory["required_artifact_files"] == expected_files)
    route = route_for(stage, execution_ok, raw_ok, prefixes, round_results)
    passed = route == stage["routes"]["stabilization_candidate"]
    selected_sequence = [str(value["selected_arm_id"])
                         for value in round_results if value.get("selected_arm_id")]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage_gate,
        "execution_integrity_passed": execution_ok,
        "raw_integrity_passed": raw_ok,
        "offline_exclusions": offline_exclusions,
        "prefix_checks": prefixes,
        "round_metrics": round_results,
        "selected_arm_sequence": selected_sequence,
        "stabilization_reached": bool(
            round_results and round_results[-1].get("stabilization_reached")),
        "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "complete_rollouts": sum(bool(row.get("passed")) for row in rows),
        "guarded_safe_stops": sum(z2.safe_stop(row, stage) for row in rows),
        "reset_calls": sum(int(row.get("reset_calls", 0)) for row in rows),
        "advance_attempts": sum(int(row.get("advance_attempts", 0)) for row in rows),
        "plant_advance_gotsc_calls": sum(
            int(row.get("plant_advance_gotsc_calls", 0)) for row in rows),
        "verified_plant_advances": sum(
            int(row.get("verified_plant_advances", 0)) for row in rows),
        **inventory,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Finite source-local bounded braking search; even a PASS is only a "
            "coarse stabilization candidate, not hold, recovery or controller."),
    }
    z1.y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = z1.y1r1.y1.x1.inside_root(output, "ID2Z3 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, reference, selected_stream = load(path)
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
    return execute(stage, cfg, targets, reference, selected_stream,
                   source_revision, output, storage_gate)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "offline":
        result = offline(args.stage_config, args.source_revision)
    else:
        result = run(
            args.stage_config, args.source_revision,
            args.output or ROOT / f"rgeo_zgeo_1ms_id2z3_{args.source_revision[:8]}")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
