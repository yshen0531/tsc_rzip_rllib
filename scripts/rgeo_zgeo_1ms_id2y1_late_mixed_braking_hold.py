#!/usr/bin/env python3
"""Run the frozen ID-2Y1 late mixed-braking hold campaign."""

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

from scripts import rgeo_zgeo_1ms_id2c1_active_nominal_vector_search as c1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2x1_mixed_allocation_hold as x1  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2y1_late_mixed_braking_hold.json"
CONFIG_SHA256 = "07cc93d131ccd76e397c756925c2fdf4a21584ffd9c52fec0172a4010bb2d30f"
SCHEMA = "rgeo-zgeo-1ms-id2y1-late-mixed-braking-hold-result-v1"
ROLLOUT_IDS = (
    "p03l64_p04m6_hold", "p03l64_p04m12_hold",
    "p03l64_p04m12_p07p4_hold", "p03l64_p04m16_p07p4_hold",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(x1.inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise x1.InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2y1-late-mixed-braking-hold-v1",
        "identity": "rgeo-zgeo-1ms-id2y1-late-mixed-braking-hold-v1",
        "stage": "ID-2Y1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 104, "common_prefix_last_issue": 64,
        "common_prefix_last_state": 65, "rollout_ids": list(ROLLOUT_IDS),
        "maximum_rollouts": 4, "maximum_reset_calls": 4,
        "maximum_advance_attempts": 416, "maximum_gotsc_calls": 416,
        "maximum_verified_plant_advances": 416, "maximum_retained_states": 420,
        "required_artifact_files_if_all_complete": 2100,
        "retry_after_any_advance_attempt": "forbidden",
        "terminal_state_indices": list(range(96, 105)),
        "experiment_contract": (
            "tsc_only_canonical_source_late_mixed_braking_hold_shooting"),
        "data_use": "route_and_action_allocation_design_only",
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise x1.InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("branch_specs") != [
        {"rollout_id": ROLLOUT_IDS[0], "p04_minus_depth": 6,
         "p07_plus_depth": 0, "hold_start_issue": 71},
        {"rollout_id": ROLLOUT_IDS[1], "p04_minus_depth": 12,
         "p07_plus_depth": 0, "hold_start_issue": 77},
        {"rollout_id": ROLLOUT_IDS[2], "p04_minus_depth": 12,
         "p07_plus_depth": 4, "hold_start_issue": 81},
        {"rollout_id": ROLLOUT_IDS[3], "p04_minus_depth": 16,
         "p07_plus_depth": 4, "hold_start_issue": 85},
    ]:
        raise x1.InputIntegrityError("branch specs changed")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True, "maximum_per_coil_issue_delta_a": 0.3,
        "minimum_absolute_current_headroom_a": 95.0,
        "full_0p3_a_allowed": True, "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": (
            "p03_level64_transport_then_p04minus_and_optional_p07plus_late_braking"),
    }:
        raise x1.InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": (
            "exact_noiseless_before_issue"),
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue", "invalid_boundary": "fail_closed",
    }:
        raise x1.InputIntegrityError("observability changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise x1.InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise x1.InputIntegrityError("diagnostic artifacts changed")
    exp = stage.get("empirical_exploration", {})
    if (exp.get("novel_issue_first") != 65
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
        raise x1.InputIntegrityError("empirical exploration changed")
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
        raise x1.InputIntegrityError("measurement gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 65000000000,
        "maximum_estimated_raw_bytes": 28000000000,
        "minimum_free_bytes_after_estimate": 35000000000,
        "output_must_not_exist": True, "raw_compression": "forbidden",
    }:
        raise x1.InputIntegrityError("storage gate changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any]]:
    path = x1.inside_root(path, "ID2Y1 config")
    if x1.sha256(path) != CONFIG_SHA256:
        raise x1.InputIntegrityError("ID2Y1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = x1.inside_root(ROOT / spec["path"], name)
        if x1.sha256(evidence) != spec["sha256"]:
            raise x1.InputIntegrityError(f"evidence mismatch: {name}")
    x1_result = _json(ROOT / stage["evidence"]["id2x1_result"]["path"])
    x1_audit = _json(ROOT / stage["evidence"]["id2x1_independent"]["path"])
    w3_result = _json(ROOT / stage["evidence"]["id2w3r1_result"]["path"])
    w3_audit = _json(ROOT / stage["evidence"]["id2w3r1_independent"]["path"])
    reference = _json(ROOT / stage["evidence"]["id2w3r1_compact"]["path"])
    if (x1_result.get("route") != stage["evidence"]["id2x1_result"]["required_route"]
            or x1_result.get("passed") is not False
            or x1_audit.get("audit_passed") is not True
            or x1_audit.get("recomputed_route") != x1_result.get("route")
            or w3_result.get("route") != stage["evidence"]["id2w3r1_result"]["required_route"]
            or w3_result.get("passed") is not False or w3_audit.get("audit_passed") is not True
            or reference.get("reasons") != ["PULSE_CLEARANCE_R"]
            or len(reference.get("states", [])) != 87
            or len(reference.get("actions", [])) != 86):
        raise x1.InputIntegrityError("route evidence is not eligible")
    _, cfg, targets, _ = x1.load(ROOT / stage["evidence"]["id2x1_config"]["path"])
    return stage, cfg, targets, reference


def campaign_streams(stage: dict[str, Any], cfg: Any,
                     targets: dict[str, Card15Target], *,
                     expected_ids: Sequence[str] = ROLLOUT_IDS) -> list[dict[str, Any]]:
    q0 = targets["q0"]
    streams: list[dict[str, Any]] = []
    for spec in stage["branch_specs"]:
        a_max, b_max = int(spec["p04_minus_depth"]), int(spec["p07_plus_depth"])
        sequence: list[Card15Target] = []
        virtual: list[list[float]] = []
        for issue in range(stage["horizon_steps"]):
            p03_level = min(issue, 64)
            a_level = min(max(issue - 64, 0), a_max)
            b_level = min(max(issue - (64 + a_max), 0), b_max)
            target = c1._offset_target(
                q0, targets["p03:minus"], p03_level, cfg,
                f"{spec['rollout_id']}.p03.{p03_level}.{issue}")
            if a_level:
                residual = c1._offset_target(
                    q0, targets["p04:minus"], a_level, cfg,
                    f"{spec['rollout_id']}.p04m.{a_level}.{issue}")
                target = c1._translated_target(
                    target, q0, residual, cfg, f"{spec['rollout_id']}.add_p04.{issue}")
            if b_level:
                residual = c1._offset_target(
                    q0, targets["p07:plus"], b_level, cfg,
                    f"{spec['rollout_id']}.p07p.{b_level}.{issue}")
                target = c1._translated_target(
                    target, q0, residual, cfg, f"{spec['rollout_id']}.add_p07.{issue}")
            sequence.append(target)
            virtual.append([float(p03_level), float(a_level), float(b_level), 1.0])
        actions = c1._actions(sequence, cfg, spec["rollout_id"], virtual)
        streams.append({
            **spec, "mixed_candidate": True, "cell_id": spec["rollout_id"],
            "cell_kind": "late_mixed_hold_shooting",
            "context_id": "canonical_source_p03_level64",
            "direction_id": "late_mixed", "sign": None,
            "probe_issue_step": 65,
            "probe_duration_issues": stage["horizon_steps"] - 65,
            "non_nominal_issue_steps": list(range(65, stage["horizon_steps"])),
            "targets": sequence, "actions": actions,
        })
    if [row["rollout_id"] for row in streams] != list(expected_ids):
        raise x1.InputIntegrityError("stream order changed")
    return streams


def common_prefix_check(row: dict[str, Any], reference: dict[str, Any],
                        semantic_artifacts: Sequence[str]) -> dict[str, Any]:
    failures: list[str] = []
    if len(row.get("states", [])) < 66 or len(row.get("actions", [])) < 65:
        failures.append("PREFIX_INCOMPLETE")
    else:
        for index in range(66):
            current, expected = row["states"][index], reference["states"][index]
            for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a",
                        "active_command_card15_fields"):
                if current[key] != expected[key]:
                    failures.append(f"STATE:{index}:{key}")
            for name in semantic_artifacts:
                if current["artifact_sha256"].get(name) != expected[
                        "artifact_sha256"].get(name):
                    failures.append(f"STATE:{index}:artifact:{name}")
        for issue in range(65):
            if (row["actions"][issue]["expected_card15_fields"]
                    != reference["actions"][issue]["expected_card15_fields"]):
                failures.append(f"ACTION:{issue}")
    return {"rollout_id": row.get("rollout_id"), "passed": not failures,
            "failures": list(dict.fromkeys(failures))}


def safe_stop(row: dict[str, Any], stage: dict[str, Any]) -> bool:
    return x1.safe_stop(row, stage)


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action_rows: list[dict[str, Any]] = []
    minimum_headroom = math.inf
    try:
        stage, cfg, targets, reference = load(path)
        for row in campaign_streams(stage, cfg, targets):
            actions = row["actions"]
            if any(float(action["maximum_issued_delta_a"]) > 0.3000000001
                   for action in actions):
                raise x1.InputIntegrityError(f"issued slew changed: {row['rollout_id']}")
            for issue in range(65):
                if (actions[issue]["expected_card15_fields"]
                        != reference["actions"][issue]["expected_card15_fields"]):
                    raise x1.InputIntegrityError(
                        f"prefix action changed: {row['rollout_id']}:{issue}")
            start = int(row["hold_start_issue"])
            for issue in range(start, stage["horizon_steps"]):
                if (actions[issue]["expected_card15_fields"]
                        != actions[start - 1]["expected_card15_fields"]
                        or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
                    raise x1.InputIntegrityError(
                        f"terminal target is not held: {row['rollout_id']}:{issue}")
            for target in row["targets"]:
                minimum_headroom = min(minimum_headroom, *(min(
                    float(value) - float(low), float(high) - float(value))
                    for value, low, high in zip(target.current_a_tsc,
                                                cfg.min_current_a_tsc,
                                                cfg.max_current_a_tsc)))
            action_rows.append({key: value for key, value in row.items()
                                if key != "targets"})
        if minimum_headroom < 95.0:
            raise x1.InputIntegrityError("absolute-current headroom below 95 A")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": x1.sha256(path),
        "passed": not failures, "failures": failures, "action_streams": action_rows,
        "minimum_absolute_current_headroom_a": (
            minimum_headroom if math.isfinite(minimum_headroom) else None),
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def branch_metric(row: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    metric = x1.branch_metric(row, stage)
    metric["mixed_candidate"] = True
    return metric


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    branches = [branch_metric(row, stage) for row in rows]
    passing = [row["rollout_id"] for row in branches if row["passed"]]
    required = int(stage["measurement_gates"]["minimum_passing_branches"])
    return {"branch_metrics": branches, "passing_branch_ids": passing,
            "passing_branch_count": len(passing),
            "minimum_passing_branches": required, "passed": len(passing) >= required}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefixes: Sequence[dict[str, Any]], metrics: dict[str, Any] | None) -> str:
    return x1.route_for(stage, execution, raw_ok, prefixes, metrics)


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = x1.inside_root(output, "ID2Y1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, reference = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    x1.write_new(output / "offline_preflight.json", preflight)
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
        x1.write_new(output / "result.json", result)
        return result
    streams = campaign_streams(stage, cfg, targets)
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    rows: list[dict[str, Any]] = []
    for stream in streams:
        row = x1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        x1.write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"] and not safe_stop(row, stage):
            break
    inventory = x1.raw_inventory(output, rows, stage)
    execution = len(rows) == 4 and all(
        row["passed"] or safe_stop(row, stage) for row in rows)
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
        **inventory, "finite_nominal_hold_candidate_pending_independent": passed,
        "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Finite source-local late mixed braking branches only; PASS requires fresh "
            "repeatability and bounded-perturbation qualification and is not recovery, "
            "controller, waypoint, path, crossing or reachability evidence."),
    }
    x1.write_new(output / "result.json", result)
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
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2y1_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
