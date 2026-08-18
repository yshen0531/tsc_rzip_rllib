#!/usr/bin/env python3
"""Run the frozen ID-2W1 sustained same-prefix branch campaign."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, inside_root, raw_inventory, sha256, write_new,
)
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import one_rollout  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2c1_active_nominal_vector_search as c1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2u0_nominal_realign_preflight as u0  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2w1_sustained_branch_campaign.json"
CONFIG_SHA256 = "bff3a6c24edd43bbb5590f64e9b0de4ea23a55892546dd5b6e83ec948236bd6f"
SCHEMA = "rgeo-zgeo-1ms-id2w1-sustained-branch-result-v1"
KINDS = (
    "uninterrupted_nominal", "pause_catchup_baseline",
    "p04_plus_depth6", "p04_minus_depth6",
    "p07_plus_depth6", "p07_minus_depth6",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2w1-sustained-branch-campaign-v1",
        "identity": "rgeo-zgeo-1ms-id2w1-sustained-branch-campaign-v1",
        "stage": "ID-2W1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 48, "common_prefix_last_issue": 18,
        "common_prefix_nominal_level": 18, "residual_start_issue": 19,
        "residual_ramp_depth": 6,
        "residual_ramp_issue_steps": [19, 20, 21, 22, 23, 24],
        "residual_plateau_issue_steps": [25, 26],
        "residual_return_issue_steps": [27, 28, 29, 30, 31, 32],
        "p03_catchup_issue_steps": list(range(33, 46)),
        "terminal_hold_issue_steps": [46, 47],
        "primary_plateau_state_indices": [25, 26],
        "diagnostic_hybrid_state_index": 27,
        "terminal_state_indices": [46, 47, 48],
        "rollout_ids": list(KINDS), "residual_directions": ["p04", "p07"],
        "residual_signs": ["plus", "minus"], "maximum_rollouts": 6,
        "maximum_reset_calls": 6, "maximum_advance_attempts": 288,
        "maximum_gotsc_calls": 288, "maximum_verified_plant_advances": 288,
        "maximum_retained_states": 294, "required_artifact_files_if_complete": 1470,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_same_prefix_sustained_multi_arm_branch_development",
        "data_use": "prospective_development_action_grammar_only_after_all_execution_raw_prefix_signal_geometry_ip_and_independent_gates_pass",
        "calibration_holdout_controller_expert_bc_dagger_rl_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True,
        "maximum_residual_offset_a": 1.8,
        "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": "p03_level18_pause_residual_ramp6_hold2_return6_catchup_to31",
    }:
        raise InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise InputIntegrityError("observability changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")
    if stage.get("measurement_gates") != {
        "maximum_absolute_paired_ip_response_a": 350.0,
        "minimum_each_arm_peak_rz_norm_m": 0.00025,
        "minimum_each_arm_plateau_median_rz_norm_m": 0.00020,
        "minimum_each_arm_state25_state26_cosine": 0.5,
        "direction_grid_count": 64,
        "maximum_each_primary_state_angular_gap_deg": 180.0,
        "minimum_each_primary_state_all_direction_best_progress_m": 0.00002,
        "maximum_each_terminal_rz_norm_m": 0.002,
        "maximum_each_terminal_abs_ip_response_a": 350.0,
        "state27_may_not_repair_primary_state_failure": True,
        "absolute_source_and_uninterrupted_nominal_metrics_are_descriptive": True,
    }:
        raise InputIntegrityError("measurement gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 50000000000,
        "maximum_estimated_raw_bytes": 25000000000,
        "minimum_free_bytes_after_estimate": 25000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")
    exploration = stage.get("empirical_exploration", {})
    if (exploration.get("novel_cumulative_branch_cells") != 4
            or exploration.get("post_successor_step_caps") != {
                "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0}
            or exploration.get("inner_probe_issue_clearance") != {
                "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05}
            or exploration.get("outer_hard_envelope") != {
                "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10}
            or not exploration.get("stop_before_next_issue_after_any_failure")
            or not exploration.get("post_action_abort_is_not_a_pre_action_bound")
            or not exploration.get("simulator_only_empirical_exploration_exception")):
        raise InputIntegrityError("empirical exploration contract changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Card15Target]]:
    path = inside_root(path, "ID2W1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2W1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    v0 = _json(ROOT / stage["evidence"]["id2v0_result"]["path"])
    v0_audit = _json(ROOT / stage["evidence"]["id2v0_independent"]["path"])
    if (v0.get("route") != stage["evidence"]["id2v0_result"]["required_route"]
            or v0.get("decision") != "branch_design_required"
            or v0.get("passed") is not True or v0_audit.get("audit_passed") is not True):
        raise InputIntegrityError("ID2V0 evidence is not eligible")
    u0_result = _json(ROOT / stage["evidence"]["id2u0_result"]["path"])
    u0_audit = _json(ROOT / stage["evidence"]["id2u0_independent"]["path"])
    if (u0_result.get("route") != stage["evidence"]["id2u0_result"]["required_route"]
            or u0_result.get("passed") is not True or u0_audit.get("audit_passed") is not True):
        raise InputIntegrityError("ID2U0 evidence is not eligible")
    u1_result = _json(ROOT / stage["evidence"]["id2u1_result"]["path"])
    u1_audit = _json(ROOT / stage["evidence"]["id2u1_independent"]["path"])
    if (u1_result.get("route") != stage["evidence"]["id2u1_result"]["required_route"]
            or u1_result.get("passed") is not True or u1_audit.get("audit_passed") is not True):
        raise InputIntegrityError("ID2U1 evidence is not eligible")
    _, cfg, _, targets = u0.load_stage(ROOT / stage["evidence"]["id2u0_config"]["path"])
    return stage, cfg, targets


def _nominal_level(issue: int, paused: bool) -> int:
    if issue == 0:
        return 0
    if not paused:
        return min(issue, 31)
    if issue <= 18:
        return issue
    if issue <= 32:
        return 18
    if issue <= 45:
        return issue - 14
    return 31


def _residual_level(issue: int) -> int:
    if 19 <= issue <= 24:
        return issue - 18
    if 25 <= issue <= 26:
        return 6
    if 27 <= issue <= 32:
        return 32 - issue
    return 0


def campaign_streams(stage: dict[str, Any], cfg: Any,
                     targets: dict[str, Card15Target]) -> list[dict[str, Any]]:
    q0, p03 = targets["q0"], targets["p03:minus"]
    rows: list[dict[str, Any]] = []
    specs: list[tuple[str, str | None, str | None]] = [
        ("uninterrupted_nominal", None, None),
        ("pause_catchup_baseline", None, None),
    ]
    specs.extend((f"{direction}_{sign}_depth6", direction, sign)
                 for direction in stage["residual_directions"]
                 for sign in stage["residual_signs"])
    if [item[0] for item in specs] != list(KINDS):
        raise InputIntegrityError("branch order changed")
    for rollout_id, direction, sign in specs:
        paused = rollout_id != "uninterrupted_nominal"
        sequence: list[Card15Target] = []
        virtual: list[list[float]] = []
        for issue in range(stage["horizon_steps"]):
            level = _nominal_level(issue, paused)
            target = c1._offset_target(q0, p03, level, cfg,
                                       f"{rollout_id}.p03_level{level}.issue{issue}")
            residual_level = 0
            if direction is not None:
                residual_level = _residual_level(issue)
                if residual_level:
                    residual = c1._offset_target(
                        q0, targets[f"{direction}:{sign}"], residual_level, cfg,
                        f"{rollout_id}.{direction}_{sign}_level{residual_level}.issue{issue}")
                    target = c1._translated_target(
                        target, q0, residual, cfg,
                        f"{rollout_id}.translated.issue{issue}")
            virtual.append([
                float(level),
                float(residual_level if direction == "p04" and sign == "plus" else
                      -residual_level if direction == "p04" else 0),
                float(residual_level if direction == "p07" and sign == "plus" else
                      -residual_level if direction == "p07" else 0),
                1.0 if paused else 0.0,
            ])
            sequence.append(target)
        actions = c1._actions(sequence, cfg, rollout_id, virtual)
        rows.append({
            "rollout_id": rollout_id, "cell_id": rollout_id,
            "group_id": "common_p03_level18_prefix", "context_id": "common_prefix",
            "cell_kind": ("uninterrupted_baseline" if rollout_id == "uninterrupted_nominal"
                          else "paused_baseline" if rollout_id == "pause_catchup_baseline"
                          else "residual_branch"),
            "direction_id": direction, "sign": sign,
            "probe_issue_step": None if direction is None else 19,
            "probe_duration_issues": 14 if direction is not None else 0,
            "non_nominal_issue_steps": list(range(19, 27)) if direction is not None else [],
            "targets": sequence, "actions": actions,
        })
    if len(rows) != 6 or any(len(row["targets"]) != 48 for row in rows):
        raise InputIntegrityError("campaign cardinality changed")
    return rows


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    try:
        stage, cfg, targets = load(path)
        rows = campaign_streams(stage, cfg, targets)
        for row in rows:
            if any(float(action["maximum_issued_delta_a"]) > 0.3000000001
                   for action in row["actions"]):
                raise InputIntegrityError(f"action slew invalid: {row['rollout_id']}")
            if row["actions"][18]["expected_card15_fields"] != rows[0]["actions"][18]["expected_card15_fields"]:
                raise InputIntegrityError("common action prefix changed")
        action_rows = [{key: value for key, value in row.items() if key != "targets"}
                       for row in rows]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures, "action_streams": action_rows,
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def matched_prefix_checks(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    reference = next(row for row in rows if row["rollout_id"] == "uninterrupted_nominal")
    checks = []
    for row in rows:
        failures: list[str] = []
        for index in range(20):
            for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if reference["states"][index][key] != row["states"][index][key]:
                    failures.append(f"STATE:{index}:{key}")
        for issue in range(19):
            if (reference["actions"][issue]["expected_card15_fields"]
                    != row["actions"][issue]["expected_card15_fields"]):
                failures.append(f"ACTION:{issue}")
        checks.append({"rollout_id": row["rollout_id"], "passed": not failures,
                       "failures": list(dict.fromkeys(failures))})
    return checks


def _vector_geometry(vectors: np.ndarray, count: int) -> dict[str, Any]:
    norms = np.linalg.norm(vectors, axis=1)
    usable = vectors[norms > 1e-15]
    if len(usable) < 2:
        return {"maximum_angular_gap_deg": 360.0,
                "minimum_all_direction_best_progress_m": 0.0,
                "direction_count": count}
    angles = np.mod(np.arctan2(usable[:, 1], usable[:, 0]), 2.0 * math.pi)
    angles.sort()
    gaps = np.diff(np.concatenate([angles, angles[:1] + 2.0 * math.pi]))
    directions = np.asarray([[math.cos(2.0 * math.pi * i / count),
                              math.sin(2.0 * math.pi * i / count)]
                             for i in range(count)], dtype=float)
    best = np.max(directions @ usable.T, axis=1)
    return {"maximum_angular_gap_deg": float(np.max(gaps) * 180.0 / math.pi),
            "minimum_all_direction_best_progress_m": float(np.min(best)),
            "direction_count": count}


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return -1.0 if denominator <= 1e-18 else float(np.dot(a, b) / denominator)


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    baseline = next(row for row in rows if row["rollout_id"] == "pause_catchup_baseline")
    uninterrupted = next(row for row in rows if row["rollout_id"] == "uninterrupted_nominal")
    branches = [row for row in rows if row["cell_kind"] == "residual_branch"]
    base_values = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                              for state in baseline["states"]], dtype=float)
    uninterrupted_values = np.asarray(
        [[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
         for state in uninterrupted["states"]], dtype=float)
    gates = stage["measurement_gates"]
    arm_rows = []
    responses: dict[str, np.ndarray] = {}
    for branch in branches:
        values = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                             for state in branch["states"]], dtype=float)
        response = values - base_values
        responses[branch["rollout_id"]] = response
        window = response[20:33]
        norms = np.linalg.norm(window[:, :2], axis=1)
        plateau_norms = np.linalg.norm(response[[25, 26], :2], axis=1)
        terminal_norms = np.linalg.norm(response[stage["terminal_state_indices"], :2], axis=1)
        row = {
            "rollout_id": branch["rollout_id"], "direction_id": branch["direction_id"],
            "sign": branch["sign"], "peak_state_index": int(20 + np.argmax(norms)),
            "peak_rz_norm_m": float(np.max(norms)),
            "plateau_state25_rz_m": response[25, :2].tolist(),
            "plateau_state26_rz_m": response[26, :2].tolist(),
            "plateau_median_rz_norm_m": float(np.median(plateau_norms)),
            "state25_state26_cosine": _cosine(response[25, :2], response[26, :2]),
            "state27_rzi_response": response[27].tolist(),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(response[:, 2]))),
            "terminal_rzi_response_by_state": [response[index].tolist()
                                                for index in stage["terminal_state_indices"]],
            "maximum_terminal_rz_norm_m": float(np.max(terminal_norms)),
            "maximum_terminal_absolute_ip_response_a": float(
                np.max(np.abs(response[stage["terminal_state_indices"], 2]))),
        }
        row["signal_and_persistence_passed"] = bool(
            row["peak_rz_norm_m"] >= gates["minimum_each_arm_peak_rz_norm_m"]
            and row["plateau_median_rz_norm_m"] >= gates["minimum_each_arm_plateau_median_rz_norm_m"]
            and row["state25_state26_cosine"] >= gates["minimum_each_arm_state25_state26_cosine"])
        row["ip_passed"] = row["maximum_absolute_ip_response_a"] <= gates["maximum_absolute_paired_ip_response_a"]
        row["bounded_tail_passed"] = bool(
            row["maximum_terminal_rz_norm_m"] <= gates["maximum_each_terminal_rz_norm_m"]
            and row["maximum_terminal_absolute_ip_response_a"] <= gates["maximum_each_terminal_abs_ip_response_a"])
        arm_rows.append(row)
    geometry_rows = []
    for state_index in [25, 26, 27]:
        vectors = np.asarray([responses[row["rollout_id"]][state_index, :2] for row in arm_rows])
        geometry = _vector_geometry(vectors, int(gates["direction_grid_count"]))
        geometry["state_index"] = state_index
        geometry["response_vectors_m"] = vectors.tolist()
        geometry["primary_gate"] = state_index in stage["primary_plateau_state_indices"]
        geometry["passed"] = bool(
            geometry["maximum_angular_gap_deg"] <= gates["maximum_each_primary_state_angular_gap_deg"]
            and geometry["minimum_all_direction_best_progress_m"]
            >= gates["minimum_each_primary_state_all_direction_best_progress_m"])
        geometry_rows.append(geometry)
    source = base_values[0, :2]
    absolute_rows = []
    for row in rows:
        values = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                             for state in row["states"]], dtype=float)
        distance = np.linalg.norm(values[:, :2] - source, axis=1)
        absolute_rows.append({
            "rollout_id": row["rollout_id"],
            "minimum_source_rz_distance_m": float(np.min(distance)),
            "minimum_source_rz_distance_state_index": int(np.argmin(distance)),
            "terminal_source_rz_distance_m": float(distance[-1]),
        })
    opportunity = base_values - uninterrupted_values
    gate_passes = {
        "signal_and_persistence": all(row["signal_and_persistence_passed"] for row in arm_rows),
        "paired_ip": all(row["ip_passed"] for row in arm_rows),
        "primary_common_state_geometry": all(
            row["passed"] for row in geometry_rows if row["primary_gate"]),
        "bounded_tail": all(row["bounded_tail_passed"] for row in arm_rows),
    }
    return {
        "arm_metrics": arm_rows, "common_state_geometry": geometry_rows,
        "absolute_source_metrics": absolute_rows,
        "pause_opportunity_cost_rzi_by_state": opportunity.tolist(),
        "gate_passes": gate_passes, "passed": all(gate_passes.values()),
    }


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    estimate = int(stage["storage_gate"]["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(stage["storage_gate"]["minimum_free_bytes_before_run"])
            and free - estimate >= int(stage["storage_gate"]["minimum_free_bytes_after_estimate"])}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes: Sequence[dict[str, Any]], metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefixes or not all(row["passed"] for row in prefixes):
        return stage["routes"]["prefix_mismatch"]
    if metrics is None or not metrics["passed"]:
        return stage["routes"]["control_utility_fail"]
    return stage["routes"]["pass"]


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2W1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"] else "offline_or_input_fail"]
        result = {
            "schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
            "storage_gate": storage_gate, "reasons": preflight["failures"],
            "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
            "development_action_grammar_eligible_pending_independent": False,
            "models_fit_or_updated": 0,
        }
        write_new(output / "result.json", result)
        return result
    streams = campaign_streams(stage, cfg, targets)
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_probe_issue_clearance"])
    rows = []
    for stream in streams:
        row = one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 6 and all(row["passed"] for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == 1470)
    prefixes = matched_prefix_checks(rows) if execution else []
    metrics = scientific_metrics(rows, stage) if execution else None
    route = route_for(stage, execution, raw_ok, prefixes, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage_gate, "execution_passed": execution,
        "raw_integrity_passed": raw_ok, "matched_prefix_checks": prefixes,
        "scientific_metrics": metrics, "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "development_action_grammar_eligible_pending_independent": passed,
        "calibration_or_holdout_records_read": 0, "models_fit_or_updated": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    write_new(output / "result.json", result)
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
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2w1_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

