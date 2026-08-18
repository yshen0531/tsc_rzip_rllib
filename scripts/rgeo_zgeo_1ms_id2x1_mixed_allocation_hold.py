#!/usr/bin/env python3
"""Run the frozen ID-2X1 mixed-allocation hold shooting campaign."""

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
from scripts import rgeo_zgeo_1ms_id2w3_p03_braking_hold as w3  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2w3r1_level64_hold as w3r1  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2x1_mixed_allocation_hold.json"
CONFIG_SHA256 = "53eab001330b3d3610cc66c3280a5cbcbec899fd6302938a89a3780024861622"
SCHEMA = "rgeo-zgeo-1ms-id2x1-mixed-allocation-hold-result-v1"
ROLLOUT_IDS = (
    "p03_level32_hold", "p04_minus_depth18_hold",
    "p04m18_p07p6_hold", "p04m24_p07p8_hold",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2x1-mixed-allocation-hold-v1",
        "identity": "rgeo-zgeo-1ms-id2x1-mixed-allocation-hold-v1",
        "stage": "ID-2X1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 96, "common_prefix_last_issue": 32,
        "common_prefix_last_state": 33, "rollout_ids": list(ROLLOUT_IDS),
        "maximum_rollouts": 4, "maximum_reset_calls": 4,
        "maximum_advance_attempts": 384, "maximum_gotsc_calls": 384,
        "maximum_verified_plant_advances": 384, "maximum_retained_states": 388,
        "required_artifact_files_if_all_complete": 1940,
        "retry_after_any_advance_attempt": "forbidden",
        "terminal_state_indices": list(range(88, 97)),
        "experiment_contract": "tsc_only_canonical_source_mixed_allocation_hold_shooting",
        "data_use": "route_and_action_allocation_design_only",
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("branch_specs") != [
        {"rollout_id": ROLLOUT_IDS[0], "p04_minus_depth": 0, "p07_plus_depth": 0,
         "mixed_candidate": False, "hold_start_issue": 33},
        {"rollout_id": ROLLOUT_IDS[1], "p04_minus_depth": 18, "p07_plus_depth": 0,
         "mixed_candidate": True, "hold_start_issue": 51},
        {"rollout_id": ROLLOUT_IDS[2], "p04_minus_depth": 18, "p07_plus_depth": 6,
         "mixed_candidate": True, "hold_start_issue": 57},
        {"rollout_id": ROLLOUT_IDS[3], "p04_minus_depth": 24, "p07_plus_depth": 8,
         "mixed_candidate": True, "hold_start_issue": 65},
    ]:
        raise InputIntegrityError("branch specs changed")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True, "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True, "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": "p03_level32_center_then_p04minus_and_optional_p07plus_sustained_offsets",
    }:
        raise InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_history": "available", "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise InputIntegrityError("observability changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")
    exp = stage.get("empirical_exploration", {})
    if (exp.get("novel_issue_first_by_rollout") != {name: 33 for name in ROLLOUT_IDS}
            or exp.get("post_successor_step_caps") != {
                "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0}
            or exp.get("inner_novel_issue_clearance") != {
                "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05}
            or exp.get("outer_hard_envelope") != {
                "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.1}
            or exp.get("allowed_branch_safe_stop_reasons") != [
                "PULSE_CLEARANCE_R", "PULSE_CLEARANCE_Z", "PULSE_CLEARANCE_IP"]
            or exp.get("continue_next_reset_after_only_allowed_branch_safe_stop") is not True
            or exp.get("abort_campaign_after_any_other_failure") is not True
            or exp.get("stop_before_next_issue_after_any_failure") is not True
            or exp.get("post_action_abort_is_not_a_pre_action_bound") is not True
            or exp.get("simulator_only_empirical_exploration_exception") is not True):
        raise InputIntegrityError("empirical exploration changed")
    if stage.get("measurement_gates") != {
        "maximum_terminal_step_r_geo_m": 0.0001,
        "maximum_terminal_step_z_geo_m": 0.0001,
        "maximum_terminal_net_r_geo_m": 0.001,
        "maximum_terminal_net_z_geo_m": 0.001,
        "maximum_terminal_net_ip_a": 100.0,
        "maximum_terminal_source_r_geo_m": 0.025,
        "maximum_terminal_source_z_geo_m": 0.025,
        "maximum_terminal_source_ip_fraction": 0.05,
        "minimum_passing_mixed_branches": 1,
        "baseline_cannot_create_campaign_pass": True,
        "pass_is_finite_nominal_hold_candidate_only": True,
    }:
        raise InputIntegrityError("measurement gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 65000000000,
        "maximum_estimated_raw_bytes": 30000000000,
        "minimum_free_bytes_after_estimate": 35000000000,
        "output_must_not_exist": True, "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any]]:
    path = inside_root(path, "ID2X1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2X1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / stage["evidence"]["id2w3r1_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2w3r1_independent"]["path"])
    compact = _json(ROOT / stage["evidence"]["id2w3r1_compact"]["path"])
    w1_result = _json(ROOT / stage["evidence"]["id2w1_result"]["path"])
    p04 = _json(ROOT / stage["evidence"]["id2w1_p04_minus"]["path"])
    p07 = _json(ROOT / stage["evidence"]["id2w1_p07_plus"]["path"])
    if (result.get("route") != stage["evidence"]["id2w3r1_result"]["required_route"]
            or result.get("passed") is not False or audit.get("audit_passed") is not True
            or compact.get("reasons") != ["PULSE_CLEARANCE_R"]
            or len(compact.get("states", [])) != 87
            or len(compact.get("actions", [])) != 86
            or w1_result.get("route") != stage["evidence"]["id2w1_result"]["required_route"]
            or p04.get("rollout_id") != "p04_minus_depth6" or p04.get("passed") is not True
            or p07.get("rollout_id") != "p07_plus_depth6" or p07.get("passed") is not True):
        raise InputIntegrityError("route evidence is not eligible")
    _, cfg, targets, reference = w3r1.load(
        ROOT / stage["evidence"]["id2w3r1_config"]["path"])
    return stage, cfg, targets, reference


def campaign_streams(stage: dict[str, Any], cfg: Any,
                     targets: dict[str, Card15Target]) -> list[dict[str, Any]]:
    q0 = targets["q0"]
    streams: list[dict[str, Any]] = []
    for spec in stage["branch_specs"]:
        a_max, b_max = int(spec["p04_minus_depth"]), int(spec["p07_plus_depth"])
        sequence: list[Card15Target] = []
        virtual: list[list[float]] = []
        for issue in range(stage["horizon_steps"]):
            p03_level = min(issue, 32)
            a_level = min(max(issue - 32, 0), a_max)
            b_level = min(max(issue - (32 + a_max), 0), b_max)
            target = c1._offset_target(q0, targets["p03:minus"], p03_level, cfg,
                                       f"{spec['rollout_id']}.p03.{p03_level}.{issue}")
            if a_level:
                residual = c1._offset_target(
                    q0, targets["p04:minus"], a_level, cfg,
                    f"{spec['rollout_id']}.p04m.{a_level}.{issue}")
                target = c1._translated_target(target, q0, residual, cfg,
                                               f"{spec['rollout_id']}.add_p04.{issue}")
            if b_level:
                residual = c1._offset_target(
                    q0, targets["p07:plus"], b_level, cfg,
                    f"{spec['rollout_id']}.p07p.{b_level}.{issue}")
                target = c1._translated_target(target, q0, residual, cfg,
                                               f"{spec['rollout_id']}.add_p07.{issue}")
            sequence.append(target)
            virtual.append([float(p03_level), float(a_level), float(b_level), 1.0])
        actions = c1._actions(sequence, cfg, spec["rollout_id"], virtual)
        streams.append({
            **spec, "cell_id": spec["rollout_id"], "cell_kind": "mixed_hold_shooting",
            "context_id": "canonical_source_p03_level32",
            "direction_id": "mixed" if spec["mixed_candidate"] else "baseline",
            "sign": None, "probe_issue_step": 33,
            "probe_duration_issues": stage["horizon_steps"] - 33,
            "non_nominal_issue_steps": list(range(33, 96)),
            "targets": sequence, "actions": actions,
        })
    if [row["rollout_id"] for row in streams] != list(ROLLOUT_IDS):
        raise InputIntegrityError("stream order changed")
    return streams


def common_prefix_check(row: dict[str, Any], reference: dict[str, Any],
                        semantic_artifacts: Sequence[str]) -> dict[str, Any]:
    failures: list[str] = []
    if len(row.get("states", [])) < 34 or len(row.get("actions", [])) < 33:
        failures.append("PREFIX_INCOMPLETE")
    else:
        for index in range(34):
            current, expected = row["states"][index], reference["states"][index]
            for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if current[key] != expected[key]:
                    failures.append(f"STATE:{index}:{key}")
            for name in semantic_artifacts:
                if current["artifact_sha256"].get(name) != expected["artifact_sha256"].get(name):
                    failures.append(f"STATE:{index}:artifact:{name}")
        for issue in range(33):
            if (row["actions"][issue]["expected_card15_fields"]
                    != reference["actions"][issue]["expected_card15_fields"]):
                failures.append(f"ACTION:{issue}")
    return {"rollout_id": row.get("rollout_id"), "passed": not failures,
            "failures": list(dict.fromkeys(failures))}


def safe_stop(row: dict[str, Any], stage: dict[str, Any]) -> bool:
    reasons = list(row.get("reasons", []))
    allowed = set(stage["empirical_exploration"]["allowed_branch_safe_stop_reasons"])
    return bool(reasons) and set(reasons).issubset(allowed)


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    minimum_headroom = math.inf
    try:
        stage, cfg, targets, reference = load(path)
        for row in campaign_streams(stage, cfg, targets):
            actions = row["actions"]
            if any(float(action["maximum_issued_delta_a"]) > 0.3000000001 for action in actions):
                raise InputIntegrityError(f"issued slew changed: {row['rollout_id']}")
            for issue in range(33):
                if (actions[issue]["expected_card15_fields"]
                        != reference["actions"][issue]["expected_card15_fields"]):
                    raise InputIntegrityError(f"prefix action changed: {row['rollout_id']}:{issue}")
            start = int(row["hold_start_issue"])
            for issue in range(start, 96):
                if (actions[issue]["expected_card15_fields"]
                        != actions[start - 1]["expected_card15_fields"]
                        or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
                    raise InputIntegrityError(f"terminal target is not held: {row['rollout_id']}:{issue}")
            for target in row["targets"]:
                minimum_headroom = min(minimum_headroom, *(
                    min(float(value) - float(low), float(high) - float(value))
                    for value, low, high in zip(target.current_a_tsc,
                                                cfg.min_current_a_tsc,
                                                cfg.max_current_a_tsc)))
            action_rows.append({key: value for key, value in row.items() if key != "targets"})
        if minimum_headroom < 98.79:
            raise InputIntegrityError("absolute-current headroom changed")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures, "action_streams": action_rows,
        "minimum_absolute_current_headroom_a": minimum_headroom if math.isfinite(minimum_headroom) else None,
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def branch_metric(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    if row.get("passed"):
        shim = dict(row)
        shim["hold_level"] = int(row["hold_start_issue"]) - 1
        metric = w3.branch_metrics(shim, stage)
        metric.update({"mixed_candidate": bool(row["mixed_candidate"]),
                       "execution_status": "complete", "stop_reasons": []})
        return metric
    states = row.get("states", [])
    offsets = None
    terminal_distance = None
    if states:
        source, last = states[0], states[-1]
        offsets = [float(last[key]) - float(source[key])
                   for key in ("r_geo_m", "z_geo_m", "ip_a")]
        terminal_distance = math.hypot(offsets[0], offsets[1])
    return {"rollout_id": row.get("rollout_id"),
            "mixed_candidate": bool(row.get("mixed_candidate")),
            "execution_status": "guarded_safe_stop" if safe_stop(row, stage) else "failure",
            "stop_reasons": list(row.get("reasons", [])),
            "retained_states": len(states), "terminal_source_offset_rzi": offsets,
            "terminal_source_rz_distance_m": terminal_distance, "passed": False}


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    branches = [branch_metric(row, stage) for row in rows]
    passing = [row["rollout_id"] for row in branches
               if row.get("mixed_candidate") and row["passed"]]
    required = int(stage["measurement_gates"]["minimum_passing_mixed_branches"])
    return {"branch_metrics": branches, "passing_mixed_branch_ids": passing,
            "passing_mixed_branch_count": len(passing),
            "minimum_passing_mixed_branches": required, "passed": len(passing) >= required}


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
    if len(prefixes) != 4 or not all(row["passed"] for row in prefixes):
        return stage["routes"]["prefix_mismatch"]
    if metrics is None or not metrics["passed"]:
        return stage["routes"]["hold_fail"]
    return stage["routes"]["pass"]


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2X1 output")
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
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": route, "storage_gate": storage_gate,
                  "reasons": preflight["failures"], "rollouts_completed": 0,
                  "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "finite_nominal_hold_candidate_pending_independent": False,
                  "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0}
        write_new(output / "result.json", result)
        return result
    streams = campaign_streams(stage, cfg, targets)
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
        if not row["passed"] and not safe_stop(row, stage):
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 4 and all(row["passed"] or safe_stop(row, stage) for row in rows)
    expected_files = 5 * sum(len(row.get("states", [])) for row in rows)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == expected_files)
    prefixes = [common_prefix_check(row, reference, stage["semantic_artifacts"])
                for row in rows] if execution else []
    metrics = scientific_metrics(rows, stage) if execution else None
    route = route_for(stage, execution, raw_ok, prefixes, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage_gate, "execution_integrity_passed": execution,
        "raw_integrity_passed": raw_ok, "known_prefix_checks": prefixes,
        "scientific_metrics": metrics, "rollouts_completed": len(rows),
        "unique_cells_completed": len({row["cell_id"] for row in rows}),
        "complete_rollouts": sum(bool(row["passed"]) for row in rows),
        "guarded_safe_stops": sum(safe_stop(row, stage) for row in rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "finite_nominal_hold_candidate_pending_independent": passed,
        "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Finite source-local canonical branch shooting only; PASS requires fresh "
            "repeatability and bounded-perturbation qualification and is not recovery, "
            "controller, waypoint, path, crossing or reachability evidence."),
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
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2x1_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
