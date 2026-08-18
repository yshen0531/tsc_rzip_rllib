#!/usr/bin/env python3
"""Run the frozen ID-2W2 extended p03 nominal transport discriminator."""

from __future__ import annotations

import argparse
import json
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
from scripts import rgeo_zgeo_1ms_id2w1_sustained_branch_campaign as w1  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2w2_extended_nominal_transport.json"
CONFIG_SHA256 = "ac695e3ee86a7ec960d9f4375a71af830a6b50b154bdc8a00d59767941abc9b4"
SCHEMA = "rgeo-zgeo-1ms-id2w2-extended-nominal-transport-result-v1"
ROLLOUT_ID = "p03_minus_stride1_levels1_through79"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2w2-extended-nominal-transport-v1",
        "identity": "rgeo-zgeo-1ms-id2w2-extended-nominal-transport-v1",
        "stage": "ID-2W2", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 80, "maximum_rollouts": 1, "maximum_reset_calls": 1,
        "maximum_advance_attempts": 80, "maximum_gotsc_calls": 80,
        "maximum_verified_plant_advances": 80, "maximum_retained_states": 81,
        "required_artifact_files_if_complete": 405,
        "retry_after_any_advance_attempt": "forbidden",
        "known_prefix_last_issue": 31, "known_prefix_last_state": 32,
        "first_novel_issue": 32, "final_p03_level": 79,
        "experiment_contract": "tsc_only_single_extended_p03_nominal_development",
        "data_use": "route_and_slowdown_braking_design_only",
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True,
        "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True,
        "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": "q0_then_p03_minus_stride1_levels1_through79",
    }:
        raise InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise InputIntegrityError("observability changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")
    exploration = stage.get("empirical_exploration", {})
    if (exploration.get("novel_issue_steps") != list(range(32, 80))
            or exploration.get("post_successor_step_caps") != {
                "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0}
            or exploration.get("inner_novel_issue_clearance") != {
                "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05}
            or exploration.get("outer_hard_envelope") != {
                "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.1}
            or not exploration.get("stop_before_next_issue_after_any_failure")
            or not exploration.get("post_action_abort_is_not_a_pre_action_bound")
            or not exploration.get("simulator_only_empirical_exploration_exception")):
        raise InputIntegrityError("empirical exploration contract changed")
    if stage.get("measurement_gates") != {
        "reference_state_index": 32,
        "reference_source_rz_distance_m": 0.019292294758661708,
        "evaluation_first_state_index": 33,
        "maximum_corridor_source_rz_distance_m": 0.015,
        "minimum_consecutive_corridor_states": 3,
        "report_one_ms_velocity": True,
        "transport_pass_is_not_hold_or_recovery": True,
    }:
        raise InputIntegrityError("measurement gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 35000000000,
        "maximum_estimated_raw_bytes": 8000000000,
        "minimum_free_bytes_after_estimate": 25000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any,
                                        dict[str, Card15Target], dict[str, Any]]:
    path = inside_root(path, "ID2W2 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2W2 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / stage["evidence"]["id2w1_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2w1_independent"]["path"])
    reference = _json(ROOT / stage["evidence"]["id2w1_uninterrupted"]["path"])
    if (result.get("route") != stage["evidence"]["id2w1_result"]["required_route"]
            or result.get("passed") is not False
            or result.get("execution_passed") is not True
            or result.get("raw_integrity_passed") is not True
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")
            or reference.get("rollout_id") != "uninterrupted_nominal"
            or reference.get("passed") is not True
            or len(reference.get("states", [])) != 49
            or len(reference.get("actions", [])) != 48):
        raise InputIntegrityError("ID2W1 evidence is not eligible")
    _, cfg, targets = w1.load(ROOT / stage["evidence"]["id2w1_config"]["path"])
    return stage, cfg, targets, reference


def action_stream(stage: dict[str, Any], cfg: Any,
                  targets: dict[str, Card15Target]) -> dict[str, Any]:
    q0, p03 = targets["q0"], targets["p03:minus"]
    sequence: list[Card15Target] = []
    virtual: list[list[float]] = []
    for issue in range(stage["horizon_steps"]):
        level = issue
        target = c1._offset_target(q0, p03, level, cfg, f"id2w2.level{level}.issue{issue}")
        sequence.append(target)
        virtual.append([float(level), 0.0, 0.0, 0.0])
    actions = c1._actions(sequence, cfg, ROLLOUT_ID, virtual)
    return {
        "rollout_id": ROLLOUT_ID, "cell_id": ROLLOUT_ID,
        "cell_kind": "extended_nominal_transport", "context_id": "canonical_source",
        "direction_id": "p03", "sign": "minus", "probe_issue_step": 32,
        "probe_duration_issues": 48,
        "non_nominal_issue_steps": list(range(32, 80)),
        "targets": sequence, "actions": actions,
    }


def prefix_check(row: dict[str, Any], reference: dict[str, Any],
                 semantic_artifacts: Sequence[str]) -> dict[str, Any]:
    failures: list[str] = []
    for index in range(33):
        current, expected = row["states"][index], reference["states"][index]
        for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                    "actual_current_decimal_a_tsc", "wire_current_a",
                    "active_command_card15_fields"):
            if current[key] != expected[key]:
                failures.append(f"STATE:{index}:{key}")
        for name in semantic_artifacts:
            if current["artifact_sha256"].get(name) != expected["artifact_sha256"].get(name):
                failures.append(f"STATE:{index}:artifact:{name}")
    for issue in range(32):
        if (row["actions"][issue]["expected_card15_fields"]
                != reference["actions"][issue]["expected_card15_fields"]):
            failures.append(f"ACTION:{issue}")
    return {"passed": not failures, "failures": list(dict.fromkeys(failures))}


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action = None
    prefix_action_match = False
    try:
        stage, cfg, targets, reference = load(path)
        stream = action_stream(stage, cfg, targets)
        action = {key: value for key, value in stream.items() if key != "targets"}
        if len(stream["actions"]) != 80:
            raise InputIntegrityError("action count changed")
        if any(float(row["maximum_issued_delta_a"]) > 0.3000000001
               for row in stream["actions"]):
            raise InputIntegrityError("issued slew changed")
        prefix_action_match = all(
            stream["actions"][issue]["expected_card15_fields"]
            == reference["actions"][issue]["expected_card15_fields"]
            for issue in range(32))
        if not prefix_action_match:
            raise InputIntegrityError("known action prefix changed")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures,
        "known_prefix_action_match": prefix_action_match, "action_stream": action,
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def scientific_metrics(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    values = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                         for state in row["states"]], dtype=float)
    source = values[0]
    offset = values - source
    distance = np.linalg.norm(offset[:, :2], axis=1)
    gates = stage["measurement_gates"]
    first = int(gates["evaluation_first_state_index"])
    evaluated = distance[first:]
    minimum_offset = int(np.argmin(evaluated))
    minimum_index = first + minimum_offset
    threshold = float(gates["maximum_corridor_source_rz_distance_m"])
    qualifying = [index for index in range(first, len(distance)) if distance[index] <= threshold]
    best_start = best_end = None
    best_streak = current_start = 0
    current_length = 0
    for index in range(first, len(distance)):
        if distance[index] <= threshold:
            if current_length == 0:
                current_start = index
            current_length += 1
            if current_length > best_streak:
                best_streak = current_length
                best_start, best_end = current_start, index
        else:
            current_length = 0
    velocity = ((values[minimum_index, :2] - values[minimum_index - 1, :2]) / 0.001
                if minimum_index > 0 else np.asarray([0.0, 0.0]))
    passed = bool(
        distance[minimum_index] <= threshold
        and best_streak >= int(gates["minimum_consecutive_corridor_states"]))
    return {
        "reference_state_index": int(gates["reference_state_index"]),
        "reference_source_rz_distance_m": float(distance[int(gates["reference_state_index"])]),
        "minimum_post_reference_source_rz_distance_m": float(distance[minimum_index]),
        "minimum_state_index": minimum_index,
        "minimum_time_ms": 1100 + minimum_index,
        "minimum_source_offset_rzi": offset[minimum_index].tolist(),
        "minimum_state_one_ms_rz_velocity_m_per_s": velocity.tolist(),
        "corridor_state_indices": qualifying,
        "longest_consecutive_corridor_states": best_streak,
        "longest_corridor_first_state_index": best_start,
        "longest_corridor_last_state_index": best_end,
        "terminal_source_offset_rzi": offset[-1].tolist(),
        "terminal_source_rz_distance_m": float(distance[-1]),
        "source_rz_distance_by_state_m": distance.tolist(),
        "passed": passed,
    }


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    estimate = int(stage["storage_gate"]["maximum_estimated_raw_bytes"])
    return {
        "free_bytes_before_run": free, "estimated_raw_bytes": estimate,
        "estimated_free_bytes_after_run": free - estimate,
        "passed": bool(
            free >= int(stage["storage_gate"]["minimum_free_bytes_before_run"])
            and free - estimate >= int(stage["storage_gate"]["minimum_free_bytes_after_estimate"])),
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefix: dict[str, Any] | None, metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefix or not prefix["passed"]:
        return stage["routes"]["prefix_mismatch"]
    if metrics is None or not metrics["passed"]:
        return stage["routes"]["transport_utility_fail"]
    return stage["routes"]["pass"]


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2W2 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, reference = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"]
                                else "offline_or_input_fail"]
        result = {
            "schema_version": SCHEMA, "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
            "storage_gate": storage_gate, "reasons": preflight["failures"],
            "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
            "transport_design_eligible_pending_independent": False,
            "models_fit_or_updated": 0,
        }
        write_new(output / "result.json", result)
        return result
    stream = action_stream(stage, cfg, targets)
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    row = one_rollout(cfg, runtime, stream)
    row.update({"schema_version": SCHEMA, "source_revision": source_revision})
    write_new(output / f"{ROLLOUT_ID}.json", row)
    rows = [row]
    inventory = raw_inventory(output, rows, stage)
    execution = bool(row["passed"] and row["verified_plant_advances"] == 80
                     and len(row["states"]) == 81)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == 405)
    prefix = prefix_check(row, reference, stage["semantic_artifacts"]) if execution else None
    metrics = scientific_metrics(row, stage) if execution else None
    route = route_for(stage, execution, raw_ok, prefix, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage_gate, "execution_passed": execution,
        "raw_integrity_passed": raw_ok, "known_prefix_check": prefix,
        "scientific_metrics": metrics, "rollouts_completed": 1,
        "unique_cells_completed": 1, "reset_calls": row["reset_calls"],
        "advance_attempts": row["advance_attempts"],
        "plant_advance_gotsc_calls": row["plant_advance_gotsc_calls"],
        "verified_plant_advances": row["verified_plant_advances"],
        **inventory,
        "transport_design_eligible_pending_independent": passed,
        "calibration_or_holdout_records_read": 0, "models_fit_or_updated": 0,
        "claim_boundary": (
            "Finite source-local extended-p03 transport development only; not hold, "
            "recovery, controller, waypoint, path, crossing or reachability evidence."),
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
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2w2_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
