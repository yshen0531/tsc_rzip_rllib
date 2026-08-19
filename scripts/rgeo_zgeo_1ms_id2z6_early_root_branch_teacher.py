#!/usr/bin/env python3
"""Run the frozen ID-2Z6 early-root finite branch-teacher campaign."""

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

from scripts import rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development as z5  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z6_early_root_branch_teacher.json"
CONFIG_SHA256 = "566e84a74d11468589cb3dd4cf87a602866aa0e4bf836519078327164ebf988a"
SCHEMA = "rgeo-zgeo-1ms-id2z6-early-root-branch-teacher-result-v1"
ARM_IDS = ("hold4", "b4", "f4", "b2f2", "f2b2")


def _error(message: str) -> Exception:
    return z5._error(message)


def _json(path: Path) -> dict[str, Any]:
    return z5.base.load_json(path)


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z6-early-root-branch-teacher-v1",
        "identity": "rgeo-zgeo-1ms-id2z6-early-root-branch-teacher-v1",
        "stage": "ID-2Z6",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "common_horizon_steps": 69,
        "common_terminal_state_index": 69,
        "maximum_rounds": 3,
        "maximum_branches_per_round": 5,
        "maximum_branch_rollouts": 15,
        "maximum_replay_rollouts": 1,
        "maximum_rollouts": 16,
        "maximum_reset_calls": 16,
        "maximum_advance_attempts": 1104,
        "maximum_gotsc_calls": 1104,
        "maximum_verified_plant_advances": 1104,
        "maximum_retained_states": 1120,
        "required_artifact_files_if_all_complete": 5600,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": (
            "tsc_only_canonical_source_three_decision_early_root_full_prefix_branch_teacher"),
        "data_use": "prospective_complete_causal_windows_development_only",
        "censored_window_fit_weight": 0,
        "critical_replay_fit_weight": 0,
        "id2z5_fit_weight": 0,
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise _error(f"frozen field mismatch: {key}")
    if stage.get("rounds") != [
            {"round_id": "round_a_state49", "round_index": 0,
             "decision_state_index": 49, "macro_first_issue": 49,
             "macro_last_issue": 52},
            {"round_id": "round_b_state53", "round_index": 1,
             "decision_state_index": 53, "macro_first_issue": 53,
             "macro_last_issue": 56},
            {"round_id": "round_c_state57", "round_index": 2,
             "decision_state_index": 57, "macro_first_issue": 57,
             "macro_last_issue": 60}]:
        raise _error("round specification changed")
    if stage.get("candidate_specs") != [
            {"arm_id": "hold4", "tokens": "HHHH", "fit_weight": 1},
            {"arm_id": "b4", "tokens": "BBBB", "fit_weight": 1},
            {"arm_id": "f4", "tokens": "FFFF", "fit_weight": 1},
            {"arm_id": "b2f2", "tokens": "BBFF", "fit_weight": 1},
            {"arm_id": "f2b2", "tokens": "FFBB", "fit_weight": 1}]:
        raise _error("candidate specification changed")
    actions = stage.get("action_semantics", {})
    required_actions = {
        "absolute_card15_targets": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True,
        "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "macro_length_issues": 4,
        "post_macro_target": "hold through issue 68",
        "scalar_100a_headroom_is_not_a_gate": True,
        "root_requires_all_five_macros_exactly_representable": True,
        "selected_successor_requires_next_round_h_b4_f4_exact_reserve": True,
        "invalid_exact_or_action_set_reserve": (
            "exclude_before_tsc_or_forbid_selection"),
    }
    for key, expected in required_actions.items():
        if actions.get(key) != expected:
            raise _error(f"action semantics changed: {key}")
    if stage.get("observability") != {
            "current_same_step_paired_boundary_rgeo_zgeo_and_ip": (
                "exact_noiseless_before_issue"),
            "post_takeover_causal_history": "available",
            "future_successor": "unknown_before_issue",
            "belief_is_not_used_for_current_or_past_rzi": True,
            "invalid_boundary": "fail_closed"}:
        raise _error("observability changed")
    exploration = stage.get("empirical_exploration", {})
    if exploration.get("novel_issue_first") != 49:
        raise _error("novel issue changed")
    if exploration.get("post_successor_step_caps") != {
            "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0}:
        raise _error("successor caps changed")
    if exploration.get("simulator_development_preissue_clearance") != {
            "r_geo_m": 0.035, "z_geo_m": 0.035, "ip_fraction": 0.075}:
        raise _error("development shell changed")
    if exploration.get("outer_hard_envelope") != {
            "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.1}:
        raise _error("hard envelope changed")
    if stage.get("measurement_gates", {}).get("terminal_state_indices") != [
            64, 65, 66, 67, 68, 69]:
        raise _error("terminal window changed")
    if stage.get("prefix_gates", {}).get("round_reference_state_counts") != [
            50, 54, 58]:
        raise _error("prefix state counts changed")
    if stage.get("storage_gate") != {
            "minimum_free_bytes_before_run": 120000000000,
            "maximum_estimated_raw_bytes": 70000000000,
            "minimum_free_bytes_after_estimate": 40000000000,
            "output_must_not_exist": True,
            "raw_compression": "forbidden"}:
        raise _error("storage gate changed")
    expected_routes = {
        "offline_or_input_fail": "ONE_MS_ID2Z6_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "storage_fail": "ONE_MS_ID2Z6_STORAGE_FAIL_NO_TSC",
        "execution_or_interface_fail": (
            "ONE_MS_ID2Z6_EXECUTION_OR_INTERFACE_FAIL_STOP"),
        "raw_integrity_fail": "ONE_MS_ID2Z6_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "prefix_mismatch": "ONE_MS_ID2Z6_PREFIX_MISMATCH_STOP",
        "round_no_eligible_arm": (
            "ONE_MS_ID2Z6_EARLY_ROOT_BRANCH_NO_UTILITY_ACTION_BASIS_REVIEW_REQUIRED"),
        "replay_fail": "ONE_MS_ID2Z6_SELECTED_SEQUENCE_REPLAY_FAIL_STOP",
        "teacher_progress_data_insufficient": (
            "ONE_MS_ID2Z6_TEACHER_PROGRESS_PASS_DATA_INSUFFICIENT_REVIEW"),
        "pass": (
            "ONE_MS_ID2Z6_EARLY_ROOT_BRANCH_TEACHER_PASS_REPLAY_RECOURSE_AND_SMALL_MODEL_DESIGN_ONLY"),
    }
    if stage.get("routes") != expected_routes:
        raise _error("routes changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any],
                                        dict[str, Any], dict[str, Any]]:
    path = z5.z3.z1.y1r1.y1.x1.inside_root(path, "ID2Z6 config")
    if z5.base.sha256(path) != CONFIG_SHA256:
        raise _error("ID2Z6 config hash mismatch")
    stage = _json(path)
    _require(stage)
    required = {
        "design", "id2w2_config", "id2w2_result_report", "id2w2_result",
        "id2w2_independent", "id2w2_compact", "id2z5_result_report",
        "id2z5_result", "id2z5_independent"}
    if set(stage.get("evidence", {})) != required:
        raise _error("evidence set changed")
    for name, spec in stage["evidence"].items():
        evidence = z5.z3.z1.y1r1.y1.x1.inside_root(
            ROOT / spec["path"], name)
        if z5.base.sha256(evidence) != spec["sha256"]:
            raise _error(f"evidence mismatch: {name}")
    w2_result = _json(ROOT / stage["evidence"]["id2w2_result"]["path"])
    w2_audit = _json(ROOT / stage["evidence"]["id2w2_independent"]["path"])
    compact = _json(ROOT / stage["evidence"]["id2w2_compact"]["path"])
    z5_result = _json(ROOT / stage["evidence"]["id2z5_result"]["path"])
    z5_audit = _json(ROOT / stage["evidence"]["id2z5_independent"]["path"])
    if (w2_result.get("route")
            != stage["evidence"]["id2w2_result"]["required_route"]
            or w2_audit.get("audit_passed") is not True
            or len(compact.get("states", [])) < 70
            or len(compact.get("actions", [])) < 69
            or z5_result.get("route")
            != stage["evidence"]["id2z5_result"]["required_route"]
            or z5_audit.get("audit_passed") is not True):
        raise _error("prerequisite evidence is ineligible")
    w2_stage, cfg, targets, _ = z5.w2.load(
        ROOT / stage["evidence"]["id2w2_config"]["path"])
    selected = z5.w2.action_stream(w2_stage, cfg, targets)
    if len(selected.get("actions", [])) < 69:
        raise _error("constructed W2 prefix is too short")
    for issue in range(69):
        if (selected["actions"][issue]["expected_card15_fields"]
                != compact["actions"][issue]["expected_card15_fields"]):
            raise _error(f"W2 action prefix changed at issue {issue}")
    return stage, cfg, targets, compact, selected


def _apply_token(current_target: Any, current_virtual: Sequence[float],
                 token: str, q0: Any, targets: dict[str, Any], cfg: Any,
                 name: str) -> tuple[Any, list[float]]:
    if token == "H":
        return current_target, [float(value) for value in current_virtual]
    increment = ({"coordinate": "p07:minus", "level_delta": 1}
                 if token == "B" else
                 {"coordinate": "p03", "level_delta": 1})
    delta = z5.z3.z2._increment_target(q0, targets, increment, cfg, name)
    target = z5.z3.z1.c1._translated_target(
        current_target, q0, delta, cfg, f"{name}.target")
    virtual = z5.z3.z2._virtual_step(current_virtual, increment)
    return target, virtual


def build_round_streams(stage: dict[str, Any], cfg: Any,
                        targets: dict[str, Any], parent_stream: dict[str, Any],
                        round_index: int, parent_arm_id: str | None) -> list[dict[str, Any]]:
    spec = stage["rounds"][round_index]
    decision = int(spec["decision_state_index"])
    horizon = int(stage["common_horizon_steps"])
    if (len(parent_stream.get("targets", [])) < decision
            or len(parent_stream.get("actions", [])) < decision):
        raise _error("parent stream is shorter than the decision prefix")
    q0 = targets["q0"]
    rows: list[dict[str, Any]] = []
    for candidate in stage["candidate_specs"]:
        arm_id = str(candidate["arm_id"])
        rollout_id = f"r{round_index}__{arm_id}"
        sequence = list(parent_stream["targets"][:decision])
        virtual = [list(row["probe_virtual_action"])
                   for row in parent_stream["actions"][:decision]]
        current_target = sequence[-1]
        current_virtual = list(virtual[-1])
        tokens = str(candidate["tokens"])
        for issue in range(decision, horizon):
            token = tokens[issue - decision] if issue <= int(
                spec["macro_last_issue"]) else "H"
            current_target, current_virtual = _apply_token(
                current_target, current_virtual, token, q0, targets, cfg,
                f"id2z6.{rollout_id}.{issue}.{token}")
            sequence.append(current_target)
            virtual.append(list(current_virtual))
        actions = z5.z3.z1.c1._actions(sequence, cfg, rollout_id, virtual)
        rows.append({
            "rollout_id": rollout_id,
            "candidate_id": rollout_id,
            "arm_id": arm_id,
            "tokens": tokens,
            "fit_weight": int(candidate["fit_weight"]),
            "round_index": round_index,
            "round_id": spec["round_id"],
            "parent_selected_arm_id": parent_arm_id,
            "cell_id": rollout_id,
            "cell_kind": "early_root_branch_teacher_window",
            "context_id": ("canonical_source_p03_state49" if round_index == 0
                           else f"selected_round_{round_index - 1}_{parent_arm_id}"),
            "direction_id": "p07minus__p03forward__hold_time_shared",
            "coordinate": "early_root_b_f_h_macro",
            "sign": None,
            "probe_issue_step": decision,
            "probe_duration_issues": 4,
            "non_nominal_issue_steps": list(range(decision, decision + 4)),
            "targets": sequence,
            "actions": actions,
        })
    if [row["arm_id"] for row in rows] != list(ARM_IDS):
        raise _error("arm order changed")
    return rows


def initial_round_streams(stage: dict[str, Any], cfg: Any,
                          targets: dict[str, Any], selected: dict[str, Any]) -> list[dict[str, Any]]:
    return build_round_streams(stage, cfg, targets, selected, 0, None)


def next_round_streams(stage: dict[str, Any], cfg: Any,
                       targets: dict[str, Any], parent: dict[str, Any],
                       round_index: int) -> list[dict[str, Any]]:
    return build_round_streams(
        stage, cfg, targets, parent, round_index, str(parent["arm_id"]))


def critical_replay_stream(selected: dict[str, Any]) -> dict[str, Any]:
    return {
        **{key: value for key, value in selected.items()
           if key not in ("rollout_id", "candidate_id", "cell_id", "fit_weight")},
        "rollout_id": "critical_replay",
        "candidate_id": "critical_replay",
        "cell_id": "critical_replay",
        "fit_weight": 0,
        "cell_kind": "selected_sequence_zero_fit_replay",
        "targets": list(selected["targets"]),
        "actions": [dict(row) for row in selected["actions"]],
    }


def _headroom(targets: Sequence[Any], cfg: Any) -> float:
    value = math.inf
    for target in targets:
        if len(target.current_a_tsc) != 14:
            raise _error("target width changed")
        value = min(value, *(min(float(current) - float(low),
                                float(high) - float(current))
                             for current, low, high in zip(
                                 target.current_a_tsc, cfg.min_current_a_tsc,
                                 cfg.max_current_a_tsc)))
    return value


def _future_reserve(current_target: Any, current_virtual: Sequence[float],
                    stage: dict[str, Any], cfg: Any,
                    targets: dict[str, Any], name: str) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    q0 = targets["q0"]
    by_arm = {row["arm_id"]: row["tokens"] for row in stage["candidate_specs"]}
    for arm_id in ("hold4", "b4", "f4"):
        target = current_target
        virtual = list(current_virtual)
        ok = True
        try:
            for index, token in enumerate(by_arm[arm_id]):
                target, virtual = _apply_token(
                    target, virtual, token, q0, targets, cfg,
                    f"{name}.{arm_id}.{index}")
                if any(float(value) < float(low) or float(value) > float(high)
                       for value, low, high in zip(
                           target.current_a_tsc, cfg.min_current_a_tsc,
                           cfg.max_current_a_tsc)):
                    ok = False
        except Exception:
            ok = False
        checks[arm_id] = ok
    return {"checks": checks, "passed": all(checks.values())}


def validate_stream(stream: dict[str, Any], stage: dict[str, Any], cfg: Any,
                    targets: dict[str, Any] | None = None) -> dict[str, Any]:
    failures: list[str] = []
    horizon = int(stage["common_horizon_steps"])
    round_index = int(stream["round_index"])
    decision = int(stage["rounds"][round_index]["decision_state_index"])
    macro_last = int(stage["rounds"][round_index]["macro_last_issue"])
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
            failures.append(f"TAIL_HOLD:{issue}")
    if any(token not in "HBF" for token in str(stream["tokens"])):
        failures.append("TOKEN_SET")
    headroom = _headroom(stream["targets"], cfg)
    if headroom < -1e-9:
        failures.append("ABSOLUTE_CURRENT_LIMIT")
    reserve = {"checks": {}, "passed": True}
    if round_index < int(stage["maximum_rounds"]) - 1:
        if targets is None:
            failures.append("RESERVE_TARGETS_MISSING")
        else:
            reserve = _future_reserve(
                stream["targets"][macro_last],
                stream["actions"][macro_last]["probe_virtual_action"],
                stage, cfg, targets, f"reserve.{stream['rollout_id']}")
            if not reserve["passed"]:
                failures.append("NEXT_ROUND_ACTION_SET_RESERVE")
    return {
        "rollout_id": stream["rollout_id"],
        "round_index": round_index,
        "arm_id": stream["arm_id"],
        "tokens": stream["tokens"],
        "minimum_absolute_current_headroom_a": headroom,
        "maximum_issued_delta_a": max(float(row["maximum_issued_delta_a"])
                                      for row in actions),
        "next_round_action_set_reserve": reserve,
        "passed": not failures,
        "failures": list(dict.fromkeys(failures)),
    }


def _runtime(stage: dict[str, Any], round_index: int) -> dict[str, Any]:
    value = dict(stage)
    value["horizon_steps"] = int(stage["common_horizon_steps"])
    value["decision_state_index"] = int(
        stage["rounds"][round_index]["decision_state_index"])
    value["prefix_gates"] = {
        "checkpoint_indices": list(range(value["decision_state_index"] + 1))}
    value["empirical_exploration"] = dict(stage["empirical_exploration"])
    value["empirical_exploration"]["inner_novel_issue_clearance"] = dict(
        stage["empirical_exploration"][
            "simulator_development_preissue_clearance"])
    return value


def _reference(row: dict[str, Any], state_count: int) -> dict[str, Any]:
    checkpoints = []
    for index, value in enumerate(row.get("states", [])[:state_count]):
        item = dict(value)
        item["state_index"] = index
        checkpoints.append(item)
    return {"state_checkpoints": checkpoints}


def prefix_check(row: dict[str, Any], reference: dict[str, Any],
                 state_count: int, action_count: int,
                 semantic_artifacts: Sequence[str]) -> dict[str, Any]:
    return z5.z3.z2._prefix_check(
        row, reference, state_count, action_count, semantic_artifacts)


def one_rollout(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], *, runner_cls: type | None = None) -> dict[str, Any]:
    runtime = _runtime(stage, int(stream["round_index"]))
    return z5.base.one_rollout(
        cfg, runtime, stream, reference, runner_cls=runner_cls)


def execute_row(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], source_revision: str,
                output: Path) -> dict[str, Any]:
    row = one_rollout(cfg, stage, stream, reference)
    row.update({"schema_version": SCHEMA, "source_revision": source_revision})
    z5.z3.z1.y1r1.y1.x1.write_new(output / f"{stream['rollout_id']}.json", row)
    return row


def safe_stop(row: dict[str, Any], stage: dict[str, Any]) -> bool:
    return z5.z3.z2.safe_stop(row, stage)


def _distance(state: dict[str, Any], source: dict[str, Any]) -> float:
    return math.hypot(float(state["r_geo_m"]) - float(source["r_geo_m"]),
                      float(state["z_geo_m"]) - float(source["z_geo_m"]))


def _speed(states: Sequence[dict[str, Any]], index: int) -> float:
    return math.hypot(
        (float(states[index]["r_geo_m"]) - float(states[index - 1]["r_geo_m"]))
        / 0.001,
        (float(states[index]["z_geo_m"]) - float(states[index - 1]["z_geo_m"]))
        / 0.001)


def round_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                  round_index: int, cfg: Any | None = None) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    by_arm = {row.get("arm_id"): row for row in rows}
    baseline = by_arm.get(gates["baseline_arm_id"])
    terminal = [int(value) for value in gates["terminal_state_indices"]]
    source_row = next((row for row in rows if row.get("states")), None)
    if source_row is None:
        return {"round_index": round_index, "baseline_complete": False,
                "branch_metrics": [], "selected_arm_id": None, "passed": False}
    source = source_row["states"][0]
    source_ip = abs(float(source["ip_a"]))
    values: list[dict[str, Any]] = []
    for arm_id in ARM_IDS:
        row = by_arm.get(arm_id)
        complete = bool(
            row is not None and row.get("passed")
            and len(row.get("states", [])) == int(stage["common_horizon_steps"]) + 1)
        if not complete:
            values.append({
                "arm_id": arm_id,
                "execution_status": "incomplete_or_safe_stop",
                "observed_state_count": len(row.get("states", [])) if row else 0,
                "safe_stop": bool(row and safe_stop(row, stage)),
                "capture_passed": False,
                "eligible": False,
            })
            continue
        states = row["states"]
        distances = [_distance(states[index], source) for index in terminal]
        speeds = [_speed(states, index) for index in terminal]
        ip_fractions = [abs(float(states[index]["ip_a"]) - float(source["ip_a"]))
                        / source_ip for index in terminal]
        score = max(
            max(distances) / float(gates["maximum_capture_source_rz_distance_m"]),
            max(speeds) / float(gates["maximum_capture_rz_step_speed_m_per_s"]),
            max(ip_fractions) / float(
                gates["maximum_capture_absolute_source_ip_fraction"]))
        captured = bool(
            max(distances) <= float(gates["maximum_capture_source_rz_distance_m"])
            and max(speeds) <= float(gates["maximum_capture_rz_step_speed_m_per_s"])
            and max(ip_fractions) <= float(
                gates["maximum_capture_absolute_source_ip_fraction"]))
        value = {
            "arm_id": arm_id,
            "tokens": row["tokens"],
            "execution_status": "complete",
            "terminal_state_indices": terminal,
            "terminal_source_rz_distance_m": distances,
            "terminal_rz_step_speed_m_per_s": speeds,
            "terminal_absolute_source_ip_fraction": ip_fractions,
            "terminal_max_source_rz_distance_m": max(distances),
            "terminal_max_rz_step_speed_m_per_s": max(speeds),
            "terminal_max_absolute_source_ip_fraction": max(ip_fractions),
            "terminal_worst_normalized_score": score,
            "capture_passed": captured,
            "eligible": False,
        }
        if cfg is not None:
            # ID2Z6 deliberately split the old single ``inner`` envelope into
            # a simulator-development preissue shell and a terminal capture
            # set.  The inherited helper is descriptive only, but still uses
            # the old key name.  Adapt that reporting input explicitly; the
            # values below do not participate in branch selection.
            diagnostic_stage = {
                "empirical_exploration": {
                    "inner_novel_issue_clearance": stage[
                        "empirical_exploration"
                    ]["simulator_development_preissue_clearance"],
                    "outer_hard_envelope": stage[
                        "empirical_exploration"
                    ]["outer_hard_envelope"],
                }
            }
            value.update(z5.z3.z1._trajectory_diagnostics(
                row, source, cfg, diagnostic_stage))
        values.append(value)
    baseline_value = next(
        (value for value in values if value["arm_id"] == gates["baseline_arm_id"]),
        None)
    baseline_complete = bool(
        baseline_value and baseline_value.get("execution_status") == "complete")
    nominated: list[dict[str, Any]] = []
    if baseline_complete:
        baseline_score = float(baseline_value["terminal_worst_normalized_score"])
        for value in values:
            if (value["arm_id"] == gates["baseline_arm_id"]
                    or value.get("execution_status") != "complete"):
                continue
            improvement = baseline_score - float(
                value["terminal_worst_normalized_score"])
            value["score_improvement_over_hold"] = improvement
            value["eligible"] = bool(
                value["capture_passed"]
                or improvement >= float(
                    gates["minimum_round_score_improvement_over_hold"]))
            if value["eligible"]:
                nominated.append(value)
    nominated.sort(key=lambda value: (
        not bool(value["capture_passed"]),
        float(value["terminal_worst_normalized_score"]),
        float(value["terminal_max_source_rz_distance_m"]),
        float(value["terminal_max_rz_step_speed_m_per_s"]),
        float(value["terminal_max_absolute_source_ip_fraction"]),
        str(value["arm_id"])))
    return {
        "round_index": round_index,
        "round_id": stage["rounds"][round_index]["round_id"],
        "decision_state_index": stage["rounds"][round_index][
            "decision_state_index"],
        "baseline_complete": baseline_complete,
        "baseline_terminal_worst_normalized_score": (
            baseline_value.get("terminal_worst_normalized_score")
            if baseline_value else None),
        "branch_metrics": values,
        "nominated_arm_ids": [value["arm_id"] for value in nominated],
        "selected_arm_id": nominated[0]["arm_id"] if nominated else None,
        "selected_capture_passed": bool(
            nominated and nominated[0]["capture_passed"]),
        "passed": bool(baseline_complete and nominated),
    }


def replay_check(selected: dict[str, Any] | None,
                 replay: dict[str, Any] | None,
                 semantic_artifacts: Sequence[str]) -> dict[str, Any]:
    failures: list[str] = []
    if selected is None or replay is None or not selected.get("passed") or not replay.get("passed"):
        failures.append("REPLAY_INCOMPLETE")
    else:
        if len(selected["states"]) != len(replay["states"]):
            failures.append("REPLAY_STATE_COUNT")
        for index, (left, right) in enumerate(zip(
                selected.get("states", []), replay.get("states", []))):
            for key in ("time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if left.get(key) != right.get(key):
                    failures.append(f"REPLAY_STATE:{index}:{key}")
            for name in semantic_artifacts:
                if (left.get("artifact_sha256", {}).get(name)
                        != right.get("artifact_sha256", {}).get(name)):
                    failures.append(f"REPLAY_ARTIFACT:{index}:{name}")
        if [row.get("expected_card15_fields") for row in selected.get("actions", [])] != [
                row.get("expected_card15_fields") for row in replay.get("actions", [])]:
            failures.append("REPLAY_ACTIONS")
    failures = list(dict.fromkeys(failures))
    return {"passed": not failures, "failures": failures}


def final_metrics(rounds: Sequence[dict[str, Any] | None],
                  rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                  selected: dict[str, Any] | None,
                  replay: dict[str, Any] | None) -> dict[str, Any]:
    complete_fit = sum(bool(row.get("passed") and int(row.get("fit_weight", 0)) == 1)
                       for row in rows)
    first_hold = next((row for row in rows
                       if row.get("round_index") == 0 and row.get("arm_id") == "hold4"), None)
    final_score = None
    first_hold_score = None
    capture = False
    if selected is not None and selected.get("passed"):
        last = round_metrics([selected], stage, 2)
        # A single selected row has no hold baseline; compute its terminal values directly.
        source = selected["states"][0]
        terminal = stage["measurement_gates"]["terminal_state_indices"]
        distances = [_distance(selected["states"][i], source) for i in terminal]
        speeds = [_speed(selected["states"], i) for i in terminal]
        ipf = [abs(float(selected["states"][i]["ip_a"]) - float(source["ip_a"]))
               / abs(float(source["ip_a"])) for i in terminal]
        final_score = max(max(distances) / 0.025, max(speeds) / 0.1,
                          max(ipf) / 0.05)
        capture = bool(max(distances) <= 0.025 and max(speeds) <= 0.1
                       and max(ipf) <= 0.05)
        del last
    if first_hold is not None and first_hold.get("passed"):
        source = first_hold["states"][0]
        terminal = stage["measurement_gates"]["terminal_state_indices"]
        distances = [_distance(first_hold["states"][i], source) for i in terminal]
        speeds = [_speed(first_hold["states"], i) for i in terminal]
        ipf = [abs(float(first_hold["states"][i]["ip_a"]) - float(source["ip_a"]))
               / abs(float(source["ip_a"])) for i in terminal]
        first_hold_score = max(max(distances) / 0.025, max(speeds) / 0.1,
                               max(ipf) / 0.05)
    improvement = (first_hold_score - final_score
                   if first_hold_score is not None and final_score is not None else None)
    replay_value = replay_check(selected, replay, stage["semantic_artifacts"])
    all_rounds = len(rounds) == 3 and all(value and value.get("passed") for value in rounds)
    utility = bool(all_rounds and final_score is not None and (
        capture or (improvement is not None and improvement >= float(
            stage["measurement_gates"][
                "minimum_final_score_improvement_over_round_a_hold"]))))
    data_ready = complete_fit >= int(stage["measurement_gates"][
        "minimum_complete_fit_weight_windows_for_model_readiness"])
    return {
        "rounds_passed": sum(bool(value and value.get("passed")) for value in rounds),
        "selected_three_macro_sequence": [
            value.get("selected_arm_id") if value else None for value in rounds],
        "selected_path_capture_passed": capture,
        "round_a_hold_terminal_worst_normalized_score": first_hold_score,
        "selected_path_terminal_worst_normalized_score": final_score,
        "selected_path_score_improvement_over_round_a_hold": improvement,
        "teacher_utility_passed": utility,
        "complete_fit_weight_windows": complete_fit,
        "minimum_complete_fit_weight_windows": int(stage["measurement_gates"][
            "minimum_complete_fit_weight_windows_for_model_readiness"]),
        "development_data_ready": data_ready,
        "critical_replay_check": replay_value,
        "passed": bool(utility and data_ready and replay_value["passed"]),
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes_ok: bool, rounds: Sequence[dict[str, Any] | None],
              scientific: dict[str, Any]) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes_ok:
        return stage["routes"]["prefix_mismatch"]
    if len(rounds) != 3 or not all(value and value.get("passed") for value in rounds):
        return stage["routes"]["round_no_eligible_arm"]
    if not scientific.get("critical_replay_check", {}).get("passed"):
        return stage["routes"]["replay_fail"]
    if not scientific.get("teacher_utility_passed"):
        return stage["routes"]["round_no_eligible_arm"]
    if not scientific.get("development_data_ready"):
        return stage["routes"]["teacher_progress_data_insufficient"]
    return stage["routes"]["pass"]


def _enumerate_static_sequences(stage: dict[str, Any], cfg: Any,
                                targets: dict[str, Any],
                                selected: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    round_a = initial_round_streams(stage, cfg, targets, selected)
    for a in round_a:
        a_check = validate_stream(a, stage, cfg, targets)
        for b in next_round_streams(stage, cfg, targets, a, 1):
            b_check = validate_stream(b, stage, cfg, targets)
            for c in next_round_streams(stage, cfg, targets, b, 2):
                c_check = validate_stream(c, stage, cfg, targets)
                checks.append({
                    "sequence": [a["arm_id"], b["arm_id"], c["arm_id"]],
                    "passed": bool(a_check["passed"] and b_check["passed"]
                                   and c_check["passed"]),
                    "minimum_absolute_current_headroom_a": min(
                        a_check["minimum_absolute_current_headroom_a"],
                        b_check["minimum_absolute_current_headroom_a"],
                        c_check["minimum_absolute_current_headroom_a"]),
                    "failures": list(dict.fromkeys(
                        a_check["failures"] + b_check["failures"]
                        + c_check["failures"])),
                })
    return checks


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, _, selected = load(path)
        checks = _enumerate_static_sequences(stage, cfg, targets, selected)
        if len(checks) != 125 or not all(value["passed"] for value in checks):
            failures.append("FULL_THREE_ROUND_ACTION_MATRIX_NOT_ADMISSIBLE")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": "rgeo-zgeo-1ms-id2z6-offline-v1",
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": not failures,
        "failures": failures,
        "static_three_round_sequence_count": len(checks),
        "static_three_round_sequences_passed": sum(
            bool(value["passed"]) for value in checks),
        "minimum_constructed_headroom_a": (
            min(value["minimum_absolute_current_headroom_a"] for value in checks)
            if checks else None),
        "sequence_checks": checks,
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "models_fit_or_updated": 0,
    }


def execute(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
            compact_reference: dict[str, Any], selected_stream: dict[str, Any],
            source_revision: str, output: Path,
            storage_gate: dict[str, Any]) -> dict[str, Any]:
    cfg.run_root = output / "rollouts"
    rows: list[dict[str, Any]] = []
    round_values: list[dict[str, Any] | None] = []
    prefix_values: list[dict[str, Any]] = []
    selected_row: dict[str, Any] | None = None
    selected_constructed = selected_stream
    reference_row = compact_reference
    execution = True
    for round_index in range(3):
        streams = (initial_round_streams(stage, cfg, targets, selected_stream)
                   if round_index == 0 else
                   next_round_streams(
                       stage, cfg, targets, selected_constructed, round_index))
        checks = [validate_stream(stream, stage, cfg, targets) for stream in streams]
        if not all(value["passed"] for value in checks):
            execution = False
            break
        decision = int(stage["rounds"][round_index]["decision_state_index"])
        reference = _reference(reference_row, decision + 1)
        round_rows: list[dict[str, Any]] = []
        for stream in streams:
            row = execute_row(
                cfg, stage, stream, reference, source_revision, output)
            rows.append(row)
            round_rows.append(row)
            prefix_values.append(prefix_check(
                row, reference_row, decision + 1, decision,
                stage["semantic_artifacts"]))
            if not row.get("passed") and not safe_stop(row, stage):
                execution = False
                break
        if not execution:
            break
        value = round_metrics(round_rows, stage, round_index, cfg)
        round_values.append(value)
        if not value["passed"]:
            break
        selected_arm = str(value["selected_arm_id"])
        selected_constructed = next(
            stream for stream in streams if stream["arm_id"] == selected_arm)
        selected_row = next(
            row for row in round_rows if row["arm_id"] == selected_arm)
        reference_row = selected_row
    replay_row: dict[str, Any] | None = None
    if len(round_values) == 3 and all(value and value.get("passed")
                                      for value in round_values):
        replay_stream = critical_replay_stream(selected_constructed)
        replay_stream["round_index"] = 2
        replay_reference = _reference(selected_row or {}, 70)
        replay_row = execute_row(
            cfg, stage, replay_stream, replay_reference, source_revision, output)
        rows.append(replay_row)
        prefix_values.append(prefix_check(
            replay_row, selected_row or {}, 70, 69, stage["semantic_artifacts"]))
        if not replay_row.get("passed") and not safe_stop(replay_row, stage):
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
    prefixes_ok = bool(prefix_values and all(value["passed"] for value in prefix_values))
    inventory = z5.z3.z1.y1r1.y1.x1.raw_inventory(output, rows, stage)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    scientific = final_metrics(
        round_values, rows, stage, selected_row, replay_row)
    route = route_for(
        stage, execution, raw_ok, prefixes_ok, round_values, scientific)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage_gate,
        "execution_integrity_passed": execution,
        "raw_integrity_passed": raw_ok,
        "prefix_checks": prefix_values,
        "round_metrics": round_values,
        "scientific_metrics": scientific,
        "selected_three_macro_sequence": scientific[
            "selected_three_macro_sequence"],
        "rollouts_completed": len(rows),
        "complete_rollouts": sum(bool(row.get("passed")) for row in rows),
        "guarded_safe_stops": sum(safe_stop(row, stage) for row in rows),
        **counters,
        **inventory,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "id2z5_records_read_for_fit": 0,
        "compact_data_role": stage["data_use"],
        "claim_boundary": (
            "Finite source-local early-root branch-teacher and prospective "
            "complete-window development evidence; not hold, recovery, "
            "controller, waypoint, crossing or reachability qualification."),
    }
    z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = z5.z3.z1.y1r1.y1.x1.inside_root(output, "ID2Z6 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, compact, selected = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = z5.z3.z1.y1r1.y1.x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    z5.z3.z1.y1r1.y1.x1.write_new(output / "offline_preflight.json", preflight)
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
        z5.z3.z1.y1r1.y1.x1.write_new(output / "result.json", result)
        return result
    return execute(stage, cfg, targets, compact, selected,
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
