#!/usr/bin/env python3
"""Run the frozen ID-2W3R1 level-64 hold completion."""

from __future__ import annotations

import argparse
import json
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
from scripts import rgeo_zgeo_1ms_id2w3_p03_braking_hold as w3  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2w3r1_level64_hold.json"
CONFIG_SHA256 = "249b4a816927340949584b7e6818f9784623b604509dd3f43268ef103de35100"
SCHEMA = "rgeo-zgeo-1ms-id2w3r1-level64-hold-result-v1"
ROLLOUT_ID = "p03_level64_hold"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2w3r1-level64-hold-completion-v1",
        "identity": "rgeo-zgeo-1ms-id2w3r1-level64-hold-completion-v1",
        "stage": "ID-2W3R1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 96, "rollout_id": ROLLOUT_ID, "hold_level": 64,
        "maximum_rollouts": 1, "maximum_reset_calls": 1,
        "maximum_advance_attempts": 96, "maximum_gotsc_calls": 96,
        "maximum_verified_plant_advances": 96, "maximum_retained_states": 97,
        "required_artifact_files_if_complete": 485,
        "retry_after_any_advance_attempt": "forbidden",
        "terminal_state_indices": list(range(88, 97)),
        "experiment_contract": "tsc_only_unstarted_preregistered_p03_level64_hold_completion",
        "data_use": "route_and_nominal_hold_design_only",
        "calibration_holdout_controller_expert_bc_dagger_rl_fixture_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True, "maximum_per_coil_issue_delta_a": 0.3,
        "full_0p3_a_allowed": True, "issue_to_effect_state_offset": 1,
        "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": "p03_stride1_to_level64_then_constant_hold",
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
    if (exp.get("novel_hold_issue_steps") != list(range(65, 96))
            or exp.get("post_successor_step_caps") != {
                "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 150.0}
            or exp.get("inner_novel_issue_clearance") != {
                "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05}
            or exp.get("outer_hard_envelope") != {
                "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.1}
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
        "minimum_passing_branches": 1,
        "pass_is_finite_nominal_hold_candidate_only": True,
    }:
        raise InputIntegrityError("measurement gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 35000000000,
        "maximum_estimated_raw_bytes": 8000000000,
        "minimum_free_bytes_after_estimate": 25000000000,
        "output_must_not_exist": True, "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any]]:
    path = inside_root(path, "ID2W3R1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2W3R1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside_root(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / stage["evidence"]["id2w3_result"]["path"])
    audit = _json(ROOT / stage["evidence"]["id2w3_independent"]["path"])
    compact = _json(ROOT / stage["evidence"]["id2w3_level52_compact"]["path"])
    if (result.get("route") != stage["evidence"]["id2w3_result"]["required_route"]
            or result.get("passed") is not False or result.get("execution_passed") is not False
            or result.get("rollouts_completed") != 1 or audit.get("audit_passed") is not True
            or audit.get("recomputed_route") != result.get("route")
            or compact.get("rollout_id") != "p03_level52_hold"
            or compact.get("reasons") != ["PULSE_CLEARANCE_R"]
            or len(compact.get("states", [])) != 80
            or len(compact.get("actions", [])) != 79):
        raise InputIntegrityError("ID2W3 evidence is not eligible")
    w3_stage, cfg, targets, reference = w3.load(
        ROOT / stage["evidence"]["id2w3_config"]["path"])
    if w3_stage["rollout_ids"][1] != ROLLOUT_ID:
        raise InputIntegrityError("unstarted branch identity changed")
    return stage, cfg, targets, reference


def action_stream(stage: dict[str, Any], cfg: Any,
                  targets: dict[str, Card15Target]) -> dict[str, Any]:
    w3_stage = _json(ROOT / stage["evidence"]["id2w3_config"]["path"])
    stream = w3.action_streams(w3_stage, cfg, targets)[1]
    if (stream["rollout_id"] != ROLLOUT_ID or stream["hold_level"] != 64
            or stream["non_nominal_issue_steps"] != list(range(65, 96))):
        raise InputIntegrityError("level64 stream changed")
    return stream


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    action = None
    try:
        stage, cfg, targets, reference = load(path)
        stream = action_stream(stage, cfg, targets)
        action = {key: value for key, value in stream.items() if key != "targets"}
        if any(float(row["maximum_issued_delta_a"]) > 0.3000000001
               for row in stream["actions"]):
            raise InputIntegrityError("issued slew changed")
        for issue in range(65):
            if (stream["actions"][issue]["expected_card15_fields"]
                    != reference["actions"][issue]["expected_card15_fields"]):
                raise InputIntegrityError(f"known action prefix changed: {issue}")
        for issue in range(65, 96):
            if (stream["actions"][issue]["expected_card15_fields"]
                    != stream["actions"][64]["expected_card15_fields"]
                    or float(stream["actions"][issue]["maximum_issued_delta_a"]) != 0.0):
                raise InputIntegrityError(f"hold action changed: {issue}")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures, "action_stream": action,
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    estimate = int(stage["storage_gate"]["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(stage["storage_gate"]["minimum_free_bytes_before_run"])
            and free - estimate >= int(stage["storage_gate"]["minimum_free_bytes_after_estimate"])}


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool,
              prefix: dict[str, Any] | None, metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not prefix or not prefix["passed"]:
        return stage["routes"]["prefix_mismatch"]
    if metrics is None or not metrics["passed"]:
        return stage["routes"]["hold_fail"]
    return stage["routes"]["pass"]


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2W3R1 output")
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
    execution = bool(row["passed"] and row["verified_plant_advances"] == 96
                     and len(row["states"]) == 97 and len(row["actions"]) == 96)
    raw_ok = bool(execution and not inventory["missing_required_artifacts"]
                  and inventory["required_artifact_files"] == 485)
    prefix = w3.prefix_check(row, reference, stage["semantic_artifacts"]) if execution else None
    metrics = w3.scientific_metrics(rows, stage) if execution else None
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
        "verified_plant_advances": row["verified_plant_advances"], **inventory,
        "finite_nominal_hold_candidate_pending_independent": passed,
        "models_fit_or_updated": 0, "calibration_or_holdout_records_read": 0,
        "claim_boundary": (
            "Finite source-local level64 p03 hold completion only; PASS requires fresh "
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
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2w3r1_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
