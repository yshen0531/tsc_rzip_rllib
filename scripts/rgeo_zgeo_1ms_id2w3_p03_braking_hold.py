#!/usr/bin/env python3
"""Run the frozen ID-2W3 p03 braking/hold discriminator."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, inside_root, raw_inventory, sha256, write_new,
)
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import one_rollout  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2c1_active_nominal_vector_search as c1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2w2_extended_nominal_transport as w2  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2w3_p03_braking_hold.json"
CONFIG_SHA256 = "df01e62dc7d5467ba817dd6b3f7208453a863d6d11820f008fae50d3e42e4e3c"
SCHEMA = "rgeo-zgeo-1ms-id2w3-p03-braking-hold-result-v1"
ROLLOUT_IDS = ("p03_level52_hold", "p03_level64_hold")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2w3-p03-braking-hold-discriminator-v1",
        "identity": "rgeo-zgeo-1ms-id2w3-p03-braking-hold-discriminator-v1",
        "stage": "ID-2W3", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 96, "rollout_ids": list(ROLLOUT_IDS),
        "hold_levels": [52, 64], "maximum_rollouts": 2,
        "maximum_reset_calls": 2, "maximum_advance_attempts": 192,
        "maximum_gotsc_calls": 192, "maximum_verified_plant_advances": 192,
        "maximum_retained_states": 194, "required_artifact_files_if_complete": 970,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_two_branch_p03_braking_hold_development",
        "data_use": "route_and_nominal_hold_design_only",
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
        "grammar": "p03_stride1_to_level52_or64_then_constant_hold",
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
    if (exploration.get("novel_hold_issue_steps_by_rollout") != {
            ROLLOUT_IDS[0]: list(range(53, 96)),
            ROLLOUT_IDS[1]: list(range(65, 96)),
            }
            or exploration.get("post_successor_step_caps") != {
                "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0}
            or exploration.get("inner_novel_issue_clearance") != {
                "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05}
            or exploration.get("outer_hard_envelope") != {
                "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.1}
            or exploration.get("stop_before_next_issue_after_any_failure") is not True
            or exploration.get("post_action_abort_is_not_a_pre_action_bound") is not True
            or exploration.get("simulator_only_empirical_exploration_exception") is not True):
        raise InputIntegrityError("empirical exploration contract changed")
    if stage.get("measurement_gates") != {
        "maximum_terminal_step_r_geo_m": 0.0001,
        "maximum_terminal_step_z_geo_m": 0.0001,
        "maximum_terminal_net_r_geo_m": 0.001,
        "maximum_terminal_net_z_geo_m": 0.001,
        "maximum_terminal_net_ip_a": 100.0,
        "maximum_terminal_source_r_geo_m": 0.025,
        "maximum_terminal_source_z_geo_m": 0.025,
        "maximum_terminal_source_ip_fraction": 0.05,
        "minimum_passing_branches": 1,
        "pass_is_finite_nominal_hold_candidate_only": True,
    }:
        raise InputIntegrityError("measurement gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 40000000000,
        "maximum_estimated_raw_bytes": 15000000000,
        "minimum_free_bytes_after_estimate": 25000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any]]:
    path = inside_root(path, "ID2W3 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2W3 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / stage["evidence"]["id2w2_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2w2_independent"]["path"])
    reference = _json(ROOT / stage["evidence"]["id2w2_compact"]["path"])
    if (result.get("route") != stage["evidence"]["id2w2_result"]["required_route"]
            or result.get("passed") is not False
            or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")
            or reference.get("rollout_id") != w2.ROLLOUT_ID
            or reference.get("passed") is not False
            or len(reference.get("states", [])) != 80
            or len(reference.get("actions", [])) != 79
            or reference.get("verified_plant_advances") != 79):
        raise InputIntegrityError("ID2W2 evidence is not eligible")
    _, cfg, targets, _ = w2.load(ROOT / stage["evidence"]["id2w2_config"]["path"])
    return stage, cfg, targets, reference


def action_streams(stage: dict[str, Any], cfg: Any,
                   targets: dict[str, Card15Target]) -> list[dict[str, Any]]:
    q0, p03 = targets["q0"], targets["p03:minus"]
    streams: list[dict[str, Any]] = []
    for rollout_id, hold_level in zip(stage["rollout_ids"], stage["hold_levels"]):
        sequence: list[Card15Target] = []
        virtual: list[list[float]] = []
        for issue in range(stage["horizon_steps"]):
            level = min(issue, int(hold_level))
            target = c1._offset_target(
                q0, p03, level, cfg, f"id2w3.{rollout_id}.level{level}.issue{issue}")
            sequence.append(target)
            virtual.append([float(level), 0.0, 0.0, 0.0])
        actions = c1._actions(sequence, cfg, rollout_id, virtual)
        streams.append({
            "rollout_id": rollout_id, "cell_id": rollout_id,
            "cell_kind": "p03_braking_hold", "context_id": "canonical_source",
            "direction_id": "p03", "sign": "minus",
            "probe_issue_step": int(hold_level) + 1,
            "probe_duration_issues": stage["horizon_steps"] - int(hold_level) - 1,
            "hold_level": int(hold_level),
            "non_nominal_issue_steps": list(range(int(hold_level) + 1,
                                                    stage["horizon_steps"])),
            "targets": sequence, "actions": actions,
        })
    if len(streams) != 2 or any(len(row["actions"]) != 96 for row in streams):
        raise InputIntegrityError("branch cardinality changed")
    return streams


def prefix_check(row: dict[str, Any], reference: dict[str, Any],
                 semantic_artifacts: Sequence[str]) -> dict[str, Any]:
    failures: list[str] = []
    hold_level = int(row["hold_level"])
    if len(row.get("states", [])) <= hold_level or len(row.get("actions", [])) <= hold_level:
        return {"rollout_id": row.get("rollout_id"), "last_known_issue": hold_level,
                "last_known_state": hold_level + 1, "passed": False,
                "failures": ["PREFIX_INCOMPLETE"]}
    for index in range(hold_level + 2):
        current, expected = row["states"][index], reference["states"][index]
        for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                    "actual_current_decimal_a_tsc", "wire_current_a",
                    "active_command_card15_fields"):
            if current[key] != expected[key]:
                failures.append(f"STATE:{index}:{key}")
        for name in semantic_artifacts:
            if current["artifact_sha256"].get(name) != expected["artifact_sha256"].get(name):
                failures.append(f"STATE:{index}:artifact:{name}")
    for issue in range(hold_level + 1):
        if (row["actions"][issue]["expected_card15_fields"]
                != reference["actions"][issue]["expected_card15_fields"]):
            failures.append(f"ACTION:{issue}")
    return {"rollout_id": row["rollout_id"], "last_known_issue": hold_level,
            "last_known_state": hold_level + 1, "passed": not failures,
            "failures": list(dict.fromkeys(failures))}


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    prefix_action_match: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, reference = load(path)
        streams = action_streams(stage, cfg, targets)
        for row in streams:
            if any(float(action["maximum_issued_delta_a"]) > 0.3000000001
                   for action in row["actions"]):
                raise InputIntegrityError(f"issued slew changed: {row['rollout_id']}")
            hold_level = int(row["hold_level"])
            match = all(
                row["actions"][issue]["expected_card15_fields"]
                == reference["actions"][issue]["expected_card15_fields"]
                for issue in range(hold_level + 1))
            prefix_action_match.append({"rollout_id": row["rollout_id"],
                                        "last_known_issue": hold_level, "passed": match})
            if not match:
                raise InputIntegrityError(f"known action prefix changed: {row['rollout_id']}")
            for issue in range(hold_level + 1, stage["horizon_steps"]):
                if row["actions"][issue]["expected_card15_fields"] != row["actions"][hold_level]["expected_card15_fields"]:
                    raise InputIntegrityError(f"hold target changed: {row['rollout_id']}:{issue}")
                if float(row["actions"][issue]["maximum_issued_delta_a"]) != 0.0:
                    raise InputIntegrityError(f"hold slew is not zero: {row['rollout_id']}:{issue}")
            action_rows.append({key: value for key, value in row.items() if key != "targets"})
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures,
        "known_prefix_action_checks": prefix_action_match, "action_streams": action_rows,
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def branch_metrics(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    states = row["states"]
    values = [[float(state[key]) for key in ("r_geo_m", "z_geo_m", "ip_a")]
              for state in states]
    source = values[0]
    indices = [int(index) for index in stage["terminal_state_indices"]]
    if max(indices) >= len(values):
        raise ValueError("terminal window is incomplete")
    max_step_r = max(abs(values[index][0] - values[index - 1][0]) for index in indices[1:])
    max_step_z = max(abs(values[index][1] - values[index - 1][1]) for index in indices[1:])
    first, last = values[indices[0]], values[indices[-1]]
    net = [last[i] - first[i] for i in range(3)]
    terminal_offsets = [[values[index][i] - source[i] for i in range(3)] for index in indices]
    distance = [math.hypot(value[0] - source[0], value[1] - source[1]) for value in values]
    gates = stage["measurement_gates"]
    ip_limit = abs(source[2]) * float(gates["maximum_terminal_source_ip_fraction"])
    gate_passes = {
        "terminal_step_r": max_step_r <= float(gates["maximum_terminal_step_r_geo_m"]),
        "terminal_step_z": max_step_z <= float(gates["maximum_terminal_step_z_geo_m"]),
        "terminal_net_r": abs(net[0]) <= float(gates["maximum_terminal_net_r_geo_m"]),
        "terminal_net_z": abs(net[1]) <= float(gates["maximum_terminal_net_z_geo_m"]),
        "terminal_net_ip": abs(net[2]) <= float(gates["maximum_terminal_net_ip_a"]),
        "terminal_source_r": all(abs(offset[0]) <= float(gates["maximum_terminal_source_r_geo_m"])
                                 for offset in terminal_offsets),
        "terminal_source_z": all(abs(offset[1]) <= float(gates["maximum_terminal_source_z_geo_m"])
                                 for offset in terminal_offsets),
        "terminal_source_ip": all(abs(offset[2]) <= ip_limit for offset in terminal_offsets),
    }
    arrival = int(row["hold_level"]) + 1
    return {
        "rollout_id": row["rollout_id"], "hold_level": int(row["hold_level"]),
        "arrival_state_index": arrival, "arrival_time_ms": 1100 + arrival,
        "arrival_source_offset_rzi": [values[arrival][i] - source[i] for i in range(3)],
        "terminal_state_indices": indices,
        "maximum_terminal_step_r_geo_m": max_step_r,
        "maximum_terminal_step_z_geo_m": max_step_z,
        "terminal_net_rzi": net,
        "terminal_source_offsets_rzi": terminal_offsets,
        "terminal_source_rz_distance_m": distance[-1],
        "minimum_source_rz_distance_m": min(distance),
        "minimum_source_rz_distance_state_index": distance.index(min(distance)),
        "source_rz_distance_by_state_m": distance,
        "terminal_source_ip_limit_a": ip_limit,
        "gate_passes": gate_passes, "passed": all(gate_passes.values()),
    }


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    branches = [branch_metrics(row, stage) for row in rows]
    passing = [row["rollout_id"] for row in branches if row["passed"]]
    required = int(stage["measurement_gates"]["minimum_passing_branches"])
    return {"branch_metrics": branches, "passing_branch_ids": passing,
            "passing_branch_count": len(passing), "minimum_passing_branches": required,
            "passed": len(passing) >= required}


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
        return stage["routes"]["hold_fail"]
    return stage["routes"]["pass"]


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2W3 output")
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
            "finite_nominal_hold_candidate_pending_independent": False,
            "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0,
        }
        write_new(output / "result.json", result)
        return result
    streams = action_streams(stage, cfg, targets)
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    rows: list[dict[str, Any]] = []
    for stream in streams:
        row = one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 2 and all(
        row["passed"] and row["verified_plant_advances"] == 96
        and len(row["states"]) == 97 and len(row["actions"]) == 96 for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == 970)
    prefixes = ([prefix_check(row, reference, stage["semantic_artifacts"]) for row in rows]
                if execution else [])
    metrics = scientific_metrics(rows, stage) if execution else None
    route = route_for(stage, execution, raw_ok, prefixes, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage_gate, "execution_passed": execution,
        "raw_integrity_passed": raw_ok, "known_prefix_checks": prefixes,
        "scientific_metrics": metrics, "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "finite_nominal_hold_candidate_pending_independent": passed,
        "calibration_or_holdout_records_read": 0, "models_fit_or_updated": 0,
        "claim_boundary": (
            "Finite source-local p03 braking/hold discriminator only; PASS is a nominal "
            "candidate requiring fresh repeatability and bounded-perturbation qualification, "
            "not recovery, controller, waypoint, path, crossing or reachability evidence."),
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
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2w3_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
