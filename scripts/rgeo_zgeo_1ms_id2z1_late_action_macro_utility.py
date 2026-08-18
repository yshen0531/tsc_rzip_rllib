#!/usr/bin/env python3
"""Run the frozen ID-2Z1 late-action macro utility campaign."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2c1_active_nominal_vector_search as c1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2y1r1_late_mixed_braking_hold as y1r1  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z1_late_action_macro_utility.json"
CONFIG_SHA256 = "88b9e65663c3fc61cae633cfcdc721161140f0cfb154d1b252b3a541ecfa38f9"
SCHEMA = "rgeo-zgeo-1ms-id2z1-late-action-macro-utility-result-v1"
ROLLOUT_IDS = (
    "p03l64_hold",
    "p03l64_p03forward4_hold4",
    "p03l64_p03unwind4_hold4",
    "p03l64_p04minus4_hold4",
    "p03l64_p04plus4_hold4",
    "p03l64_p07minus4_hold4",
    "p03l64_p07plus4_hold4",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(y1r1.y1.x1.inside_root(path, "JSON evidence").read_text(
        encoding="utf-8"))
    if not isinstance(value, dict):
        raise y1r1.y1.x1.InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2z1-late-action-macro-utility-v1",
        "identity": "rgeo-zgeo-1ms-id2z1-late-action-macro-utility-v1",
        "stage": "ID-2Z1",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 73,
        "common_prefix_last_issue": 64,
        "common_prefix_last_state": 65,
        "macro_first_issue": 65,
        "macro_last_increment_issue": 68,
        "hold_first_issue": 69,
        "rollout_ids": list(ROLLOUT_IDS),
        "maximum_rollouts": 7,
        "maximum_reset_calls": 7,
        "maximum_advance_attempts": 511,
        "maximum_gotsc_calls": 511,
        "maximum_verified_plant_advances": 511,
        "maximum_retained_states": 518,
        "required_artifact_files_if_all_complete": 2590,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": (
            "tsc_only_canonical_source_same_prefix_late_macro_control_utility"),
        "data_use": "route_and_macro_control_utility_design_only",
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise y1r1.y1.x1.InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("candidate_specs") != [
        {"rollout_id": ROLLOUT_IDS[0], "coordinate": "hold", "level_delta": 0},
        {"rollout_id": ROLLOUT_IDS[1], "coordinate": "p03", "level_delta": 4},
        {"rollout_id": ROLLOUT_IDS[2], "coordinate": "p03", "level_delta": -4},
        {"rollout_id": ROLLOUT_IDS[3], "coordinate": "p04:minus", "level_delta": 4},
        {"rollout_id": ROLLOUT_IDS[4], "coordinate": "p04:plus", "level_delta": 4},
        {"rollout_id": ROLLOUT_IDS[5], "coordinate": "p07:minus", "level_delta": 4},
        {"rollout_id": ROLLOUT_IDS[6], "coordinate": "p07:plus", "level_delta": 4},
    ]:
        raise y1r1.y1.x1.InputIntegrityError("candidate specs changed")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "minimum_absolute_current_headroom_a": 95.0,
        "enumerated_minimum_absolute_current_headroom_a": 97.6,
        "full_0p3_a_allowed": True,
        "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": (
            "p03_level64_common_prefix_then_four_exact_single_coordinate_steps_and_four_holds"),
    }:
        raise y1r1.y1.x1.InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": (
            "exact_noiseless_before_issue"),
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise y1r1.y1.x1.InputIntegrityError("observability changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise y1r1.y1.x1.InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise y1r1.y1.x1.InputIntegrityError("diagnostic artifacts changed")
    if stage.get("empirical_exploration") != {
        "novel_issue_first": 65,
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
        raise y1r1.y1.x1.InputIntegrityError("empirical exploration changed")
    if stage.get("measurement_gates") != {
        "baseline_rollout_id": ROLLOUT_IDS[0],
        "response_state_indices": list(range(66, 74)),
        "persistence_state_indices": list(range(70, 74)),
        "minimum_peak_rz_response_m": 0.00005,
        "minimum_persistent_source_distance_improvement_m": 0.00005,
        "minimum_persistent_states": 3,
        "minimum_terminal_source_distance_improvement_m": 0.0001,
        "maximum_paired_ip_response_a": 150.0,
        "minimum_nominated_arms": 1,
        "pass_is_macro_nomination_only": True,
    }:
        raise y1r1.y1.x1.InputIntegrityError("measurement gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 50000000000,
        "maximum_estimated_raw_bytes": 31000000000,
        "minimum_free_bytes_after_estimate": 25000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise y1r1.y1.x1.InputIntegrityError("storage gate changed")
    if stage.get("routes") != {
        "offline_or_input_fail": "ONE_MS_ID2Z1_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "storage_fail": "ONE_MS_ID2Z1_STORAGE_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2Z1_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2Z1_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "prefix_mismatch": "ONE_MS_ID2Z1_AUDITED_PREFIX_MISMATCH_STOP",
        "utility_fail": (
            "ONE_MS_ID2Z1_LATE_MACRO_UTILITY_FAIL_EARLIER_OR_BROADER_SEARCH_REQUIRED"),
        "pass": "ONE_MS_ID2Z1_LATE_MACRO_UTILITY_PASS_ROLLING_SEQUENCE_DESIGN_ONLY",
    }:
        raise y1r1.y1.x1.InputIntegrityError("routes changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any]]:
    path = y1r1.y1.x1.inside_root(path, "ID2Z1 config")
    if y1r1.y1.x1.sha256(path) != CONFIG_SHA256:
        raise y1r1.y1.x1.InputIntegrityError("ID2Z1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    required_evidence = {
        "design", "id2y1r1_config", "id2y1r1_result_report", "id2y1r1_result",
        "id2y1r1_independent", "id2w3r1_compact",
    }
    if set(stage.get("evidence", {})) != required_evidence:
        raise y1r1.y1.x1.InputIntegrityError("evidence set changed")
    for name, spec in stage["evidence"].items():
        evidence = y1r1.y1.x1.inside_root(ROOT / spec["path"], name)
        if y1r1.y1.x1.sha256(evidence) != spec["sha256"]:
            raise y1r1.y1.x1.InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / stage["evidence"]["id2y1r1_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2y1r1_independent"]["path"])
    if (result.get("route")
            != stage["evidence"]["id2y1r1_result"]["required_route"]
            or result.get("passed") is not False
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")):
        raise y1r1.y1.x1.InputIntegrityError("ID2Y1R1 route evidence is not eligible")
    _, cfg, targets, reference = y1r1.load(
        ROOT / stage["evidence"]["id2y1r1_config"]["path"])
    if (len(reference.get("states", [])) != 87
            or len(reference.get("actions", [])) != 86):
        raise y1r1.y1.x1.InputIntegrityError("prefix reference shape changed")
    return stage, cfg, targets, reference


def _p03_target(q0: Card15Target, targets: dict[str, Card15Target], level: int,
                cfg: Any, name: str) -> Card15Target:
    return c1._offset_target(q0, targets["p03:minus"], level, cfg, name)


def campaign_streams(stage: dict[str, Any], cfg: Any,
                     targets: dict[str, Card15Target]) -> list[dict[str, Any]]:
    q0 = targets["q0"]
    streams: list[dict[str, Any]] = []
    for spec in stage["candidate_specs"]:
        sequence: list[Card15Target] = []
        virtual: list[list[float]] = []
        coordinate = str(spec["coordinate"])
        terminal_delta = int(spec["level_delta"])
        for issue in range(stage["horizon_steps"]):
            p03_level = min(issue, 64)
            residual_level = 0
            if issue >= 65:
                step = min(issue - 64, 4)
                if coordinate == "p03":
                    p03_level = 64 + (step if terminal_delta > 0 else -step)
                else:
                    p03_level = 64
                    if coordinate != "hold":
                        residual_level = step
            target = _p03_target(
                q0, targets, p03_level, cfg,
                f"{spec['rollout_id']}.p03.{p03_level}.{issue}")
            p04_virtual = p07_virtual = 0.0
            if residual_level:
                residual = c1._offset_target(
                    q0, targets[coordinate], residual_level, cfg,
                    f"{spec['rollout_id']}.{coordinate}.{residual_level}.{issue}")
                target = c1._translated_target(
                    target, q0, residual, cfg,
                    f"{spec['rollout_id']}.translated.{issue}")
                signed_level = float(residual_level if coordinate.endswith("plus") else
                                     -residual_level)
                if coordinate.startswith("p04"):
                    p04_virtual = signed_level
                else:
                    p07_virtual = signed_level
            sequence.append(target)
            virtual.append([float(p03_level), p04_virtual, p07_virtual, 1.0])
        actions = c1._actions(sequence, cfg, spec["rollout_id"], virtual)
        streams.append({
            **spec,
            "cell_id": spec["rollout_id"],
            "cell_kind": "late_macro_utility",
            "context_id": "canonical_source_p03_level64",
            "direction_id": coordinate,
            "sign": ("plus" if coordinate.endswith("plus") else
                     "minus" if coordinate.endswith("minus") else None),
            "probe_issue_step": 65,
            "probe_duration_issues": 8,
            # Every post-prefix transition is an empirical, unsupported history cell.
            "non_nominal_issue_steps": list(range(65, 73)),
            "targets": sequence,
            "actions": actions,
        })
    if [row["rollout_id"] for row in streams] != list(ROLLOUT_IDS):
        raise y1r1.y1.x1.InputIntegrityError("stream order changed")
    return streams


common_prefix_check = y1r1.y1.common_prefix_check
safe_stop = y1r1.y1.safe_stop


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    minimum_headroom = math.inf
    try:
        stage, cfg, targets, reference = load(path)
        streams = campaign_streams(stage, cfg, targets)
        if len(streams) != stage["maximum_rollouts"]:
            raise y1r1.y1.x1.InputIntegrityError("rollout budget changed")
        for row in streams:
            actions = row["actions"]
            if len(actions) != 73 or len(row["targets"]) != 73:
                raise y1r1.y1.x1.InputIntegrityError(
                    f"stream dimensions changed: {row['rollout_id']}")
            for issue, action in enumerate(actions):
                if (action["issue_step"] != issue
                        or action["effect_state_index"] != issue + 1
                        or float(action["maximum_issued_delta_a"]) > 0.3000000001):
                    raise y1r1.y1.x1.InputIntegrityError(
                        f"action contract changed: {row['rollout_id']}:{issue}")
            for issue in range(65):
                if (actions[issue]["expected_card15_fields"]
                        != reference["actions"][issue]["expected_card15_fields"]):
                    raise y1r1.y1.x1.InputIntegrityError(
                        f"prefix action changed: {row['rollout_id']}:{issue}")
            for issue in range(69, 73):
                if (actions[issue]["expected_card15_fields"]
                        != actions[68]["expected_card15_fields"]
                        or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
                    raise y1r1.y1.x1.InputIntegrityError(
                        f"macro target not held: {row['rollout_id']}:{issue}")
            for issue in range(65, 69):
                before = actions[issue - 1]["probe_virtual_action"]
                after = actions[issue]["probe_virtual_action"]
                changes = [abs(float(a) - float(b)) for a, b in zip(after, before)]
                nonzero = [value for value in changes[:3] if value > 0.0]
                expected_count = 0 if row["coordinate"] == "hold" else 1
                if len(nonzero) != expected_count or any(value != 1.0 for value in nonzero):
                    raise y1r1.y1.x1.InputIntegrityError(
                        f"virtual macro changed: {row['rollout_id']}:{issue}")
            for target in row["targets"]:
                minimum_headroom = min(minimum_headroom, *(min(
                    float(value) - float(low), float(high) - float(value))
                    for value, low, high in zip(target.current_a_tsc,
                                                cfg.min_current_a_tsc,
                                                cfg.max_current_a_tsc)))
            action_rows.append({key: value for key, value in row.items()
                                if key != "targets"})
        minimum_required = float(stage["action_semantics"][
            "enumerated_minimum_absolute_current_headroom_a"])
        if minimum_headroom < minimum_required - 1e-9:
            raise y1r1.y1.x1.InputIntegrityError(
                "absolute-current enumerated headroom changed")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": y1r1.y1.x1.sha256(path),
        "passed": not failures,
        "failures": failures,
        "action_streams": action_rows,
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


def _trajectory_diagnostics(row: dict[str, Any], source: dict[str, Any],
                            cfg: Any, stage: dict[str, Any]) -> dict[str, Any]:
    states = list(row.get("states", []))
    offsets = [[float(state[key]) - float(source[key])
                for key in ("r_geo_m", "z_geo_m", "ip_a")]
               for state in states]
    velocities = [[
        (float(states[index]["r_geo_m"]) - float(states[index - 1]["r_geo_m"]))
        * 1000.0,
        (float(states[index]["z_geo_m"]) - float(states[index - 1]["z_geo_m"]))
        * 1000.0,
    ] for index in range(1, len(states))]
    headroom = math.inf
    for state in states:
        for value, low, high in zip(state["actual_current_a_tsc"],
                                    cfg.min_current_a_tsc, cfg.max_current_a_tsc):
            headroom = min(headroom, float(value) - float(low),
                           float(high) - float(value))
    inner = stage["empirical_exploration"]["inner_novel_issue_clearance"]
    outer = stage["empirical_exploration"]["outer_hard_envelope"]
    ip0 = abs(float(source["ip_a"]))
    inner_margins = [[
        float(inner["r_geo_m"]) - abs(value[0]),
        float(inner["z_geo_m"]) - abs(value[1]),
        float(inner["ip_fraction"]) * ip0 - abs(value[2]),
    ] for value in offsets]
    outer_margins = [[
        float(outer["r_geo_m"]) - abs(value[0]),
        float(outer["z_geo_m"]) - abs(value[1]),
        float(outer["ip_fraction"]) * ip0 - abs(value[2]),
    ] for value in offsets]
    return {
        "source_offset_rzi": offsets,
        "step_velocity_rz_m_per_s": velocities,
        "minimum_actual_current_headroom_a": (
            headroom if math.isfinite(headroom) else None),
        "minimum_inner_margin_r_z_ip": (
            [min(values[index] for values in inner_margins)
             for index in range(3)] if inner_margins else None),
        "minimum_outer_margin_r_z_ip": (
            [min(values[index] for values in outer_margins)
             for index in range(3)] if outer_margins else None),
    }


def _stopped_metric(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    states = row.get("states", [])
    source_offset = None
    distance = None
    if states:
        source_offset = [float(states[-1][key]) - float(states[0][key])
                         for key in ("r_geo_m", "z_geo_m", "ip_a")]
        distance = math.hypot(source_offset[0], source_offset[1])
    return {
        "rollout_id": row.get("rollout_id"),
        "coordinate": row.get("coordinate"),
        "level_delta": row.get("level_delta"),
        "execution_status": ("guarded_safe_stop" if safe_stop(row, stage)
                             else "failure"),
        "stop_reasons": list(row.get("reasons", [])),
        "retained_states": len(states),
        "terminal_source_offset_rzi": source_offset,
        "terminal_source_rz_distance_m": distance,
        "eligible": False,
    }


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any],
                       cfg: Any | None = None) -> dict[str, Any]:
    gates = stage["measurement_gates"]
    by_id = {row.get("rollout_id"): row for row in rows}
    baseline = by_id.get(gates["baseline_rollout_id"])
    branch_metrics: list[dict[str, Any]] = []
    if baseline is None or not baseline.get("passed") or len(baseline["states"]) != 74:
        branch_metrics.extend(_stopped_metric(row, stage) for row in rows)
        return {
            "baseline_complete": False,
            "branch_metrics": branch_metrics,
            "nominated_arm_ids": [],
            "nominated_arm_count": 0,
            "selected_arm_id": None,
            "passed": False,
        }
    source = baseline["states"][0]
    baseline_distances = [_source_distance(state, source)
                          for state in baseline["states"]]
    baseline_metric = {
        "rollout_id": baseline["rollout_id"],
        "coordinate": baseline["coordinate"],
        "level_delta": baseline["level_delta"],
        "execution_status": "complete",
        "source_rz_distance_m": baseline_distances,
        "terminal_source_rz_distance_m": baseline_distances[-1],
        "terminal_source_ip_offset_a": (
            float(baseline["states"][-1]["ip_a"]) - float(source["ip_a"])),
        "eligible": False,
        "baseline": True,
    }
    if cfg is not None:
        baseline_metric.update(_trajectory_diagnostics(baseline, source, cfg, stage))
    branch_metrics.append(baseline_metric)
    response_indices = list(gates["response_state_indices"])
    persistence_indices = list(gates["persistence_state_indices"])
    nominated: list[dict[str, Any]] = []
    for rollout_id in ROLLOUT_IDS[1:]:
        row = by_id.get(rollout_id)
        if row is None or not row.get("passed") or len(row.get("states", [])) != 74:
            metric = _stopped_metric(row or {"rollout_id": rollout_id}, stage)
            branch_metrics.append(metric)
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
        persistence = [baseline_distances[index] - distances[index]
                       for index in persistence_indices]
        persistent_count = sum(
            value >= float(gates["minimum_persistent_source_distance_improvement_m"])
            for value in persistence)
        terminal_improvement = baseline_distances[-1] - distances[-1]
        maximum_last4_step = max(math.hypot(
            float(row["states"][index]["r_geo_m"])
            - float(row["states"][index - 1]["r_geo_m"]),
            float(row["states"][index]["z_geo_m"])
            - float(row["states"][index - 1]["z_geo_m"]))
            for index in persistence_indices)
        eligible = bool(
            peak >= float(gates["minimum_peak_rz_response_m"])
            and persistent_count >= int(gates["minimum_persistent_states"])
            and terminal_improvement >= float(
                gates["minimum_terminal_source_distance_improvement_m"])
            and max_ip <= float(gates["maximum_paired_ip_response_a"]))
        metric = {
            "rollout_id": rollout_id,
            "coordinate": row["coordinate"],
            "level_delta": row["level_delta"],
            "execution_status": "complete",
            "response_state_indices": response_indices,
            "paired_rzi_response": response,
            "maximum_paired_rz_response_m": peak,
            "maximum_paired_ip_response_a": max_ip,
            "source_rz_distance_m": distances,
            "persistence_state_indices": persistence_indices,
            "persistent_source_distance_improvement_m": persistence,
            "persistent_improvement_count": persistent_count,
            "terminal_source_distance_improvement_m": terminal_improvement,
            "median_persistent_source_distance_improvement_m": statistics.median(
                persistence),
            "maximum_persistence_window_step_rz_m": maximum_last4_step,
            "terminal_source_ip_offset_a": (
                float(row["states"][-1]["ip_a"]) - float(source["ip_a"])),
            "eligible": eligible,
        }
        if cfg is not None:
            metric.update(_trajectory_diagnostics(row, source, cfg, stage))
        branch_metrics.append(metric)
        if eligible:
            nominated.append(metric)
    nominated.sort(key=lambda value: (
        -float(value["terminal_source_distance_improvement_m"]),
        -float(value["median_persistent_source_distance_improvement_m"]),
        float(value["maximum_persistence_window_step_rz_m"]),
        abs(float(value["terminal_source_ip_offset_a"])),
        str(value["rollout_id"]),
    ))
    required = int(gates["minimum_nominated_arms"])
    return {
        "baseline_complete": True,
        "branch_metrics": branch_metrics,
        "nominated_arm_ids": [value["rollout_id"] for value in nominated],
        "nominated_arm_count": len(nominated),
        "minimum_nominated_arms": required,
        "selected_arm_id": nominated[0]["rollout_id"] if nominated else None,
        "passed": len(nominated) >= required,
        "claim_boundary": (
            "Measured finite same-prefix macro utility only; no two-axis span, "
            "hold, recourse, controller, or reachability claim."),
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes: Sequence[dict[str, Any]],
              metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if len(prefixes) != 7 or not all(row["passed"] for row in prefixes):
        return stage["routes"]["prefix_mismatch"]
    if metrics is None or not metrics["passed"]:
        return stage["routes"]["utility_fail"]
    return stage["routes"]["pass"]


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = y1r1.y1.x1.inside_root(output, "ID2Z1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, reference = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = y1r1.y1.x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    y1r1.y1.x1.write_new(output / "offline_preflight.json", preflight)
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
            "macro_nomination_pending_independent": False,
            "models_fit_or_updated": 0,
            "calibration_or_holdout_records_read": 0,
        }
        y1r1.y1.x1.write_new(output / "result.json", result)
        return result
    streams = campaign_streams(stage, cfg, targets)
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    rows: list[dict[str, Any]] = []
    for stream in streams:
        row = y1r1.y1.x1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        y1r1.y1.x1.write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"] and not safe_stop(row, stage):
            break
    inventory = y1r1.y1.x1.raw_inventory(output, rows, stage)
    execution = len(rows) == 7 and all(
        row["passed"] or safe_stop(row, stage) for row in rows)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    prefixes = [common_prefix_check(row, reference, stage["semantic_artifacts"])
                for row in rows] if execution else []
    metrics = scientific_metrics(rows, stage, cfg) if execution else None
    route = route_for(stage, execution, raw_ok, prefixes, metrics)
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
        "known_prefix_checks": prefixes,
        "scientific_metrics": metrics,
        "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "complete_rollouts": sum(bool(row["passed"]) for row in rows),
        "guarded_safe_stops": sum(safe_stop(row, stage) for row in rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(
            row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(
            row["verified_plant_advances"] for row in rows),
        **inventory,
        "macro_nomination_pending_independent": passed,
        "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Finite source-local same-prefix late macro utility only; PASS is one "
            "macro nomination for later rolling-sequence design, not a controller, "
            "hold, recovery, waypoint, path, crossing or reachability result."),
    }
    y1r1.y1.x1.write_new(output / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = (offline(args.stage_config, args.source_revision) if args.mode == "offline"
              else run(args.stage_config, args.source_revision,
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2z1_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
