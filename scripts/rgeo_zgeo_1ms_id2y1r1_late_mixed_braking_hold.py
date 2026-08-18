#!/usr/bin/env python3
"""Run the repaired ID-2Y1R1 late mixed-braking hold campaign."""

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

from scripts import rgeo_zgeo_1ms_id2y1_late_mixed_braking_hold as y1  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import Card15Target  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2y1r1_late_mixed_braking_hold.json"
CONFIG_SHA256 = "0904428058e9ca806e80f47e4b0a40442cf6fbf79218ed264d400e2d7b7679e8"
SCHEMA = "rgeo-zgeo-1ms-id2y1r1-late-mixed-braking-hold-result-v1"
ROLLOUT_IDS = (
    "p03l64_p04m6_hold", "p03l64_p04m12_hold",
    "p03l64_p04m6_p07p4_hold", "p03l64_p04m8_p07p4_hold",
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(y1.x1.inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise y1.x1.InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2y1r1-late-mixed-braking-hold-v1",
        "identity": "rgeo-zgeo-1ms-id2y1r1-late-mixed-braking-hold-v1",
        "stage": "ID-2Y1R1", "takeover_time_ms": 1100, "control_period_ms": 1,
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
            raise y1.x1.InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("branch_specs") != [
        {"rollout_id": ROLLOUT_IDS[0], "p04_minus_depth": 6,
         "p07_plus_depth": 0, "hold_start_issue": 71},
        {"rollout_id": ROLLOUT_IDS[1], "p04_minus_depth": 12,
         "p07_plus_depth": 0, "hold_start_issue": 77},
        {"rollout_id": ROLLOUT_IDS[2], "p04_minus_depth": 6,
         "p07_plus_depth": 4, "hold_start_issue": 75},
        {"rollout_id": ROLLOUT_IDS[3], "p04_minus_depth": 8,
         "p07_plus_depth": 4, "hold_start_issue": 77},
    ]:
        raise y1.x1.InputIntegrityError("branch specs changed")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True, "maximum_per_coil_issue_delta_a": 0.3,
        "minimum_absolute_current_headroom_a": 95.0, "full_0p3_a_allowed": True,
        "issue_to_effect_state_offset": 1, "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
        "grammar": (
            "p03_level64_transport_then_p04minus_and_optional_p07plus_late_braking"),
    }:
        raise y1.x1.InputIntegrityError("action semantics changed")
    for key in ("observability", "semantic_artifacts", "diagnostic_artifacts",
                "empirical_exploration", "measurement_gates", "storage_gate"):
        if stage.get(key) != _json(ROOT / stage["evidence"]["id2y1_config"]["path"]).get(key):
            raise y1.x1.InputIntegrityError(f"unchanged Y1 contract field changed: {key}")


def load(path: Path = CONFIG) -> tuple[
        dict[str, Any], Any, dict[str, Card15Target], dict[str, Any]]:
    path = y1.x1.inside_root(path, "ID2Y1R1 config")
    if y1.x1.sha256(path) != CONFIG_SHA256:
        raise y1.x1.InputIntegrityError("ID2Y1R1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    for name, spec in stage["evidence"].items():
        evidence = y1.x1.inside_root(ROOT / spec["path"], name)
        if y1.x1.sha256(evidence) != spec["sha256"]:
            raise y1.x1.InputIntegrityError(f"evidence mismatch: {name}")
    x1_result = _json(ROOT / stage["evidence"]["id2x1_result"]["path"])
    x1_audit = _json(ROOT / stage["evidence"]["id2x1_independent"]["path"])
    w3_result = _json(ROOT / stage["evidence"]["id2w3r1_result"]["path"])
    w3_audit = _json(ROOT / stage["evidence"]["id2w3r1_independent"]["path"])
    reference = _json(ROOT / stage["evidence"]["id2w3r1_compact"]["path"])
    if (x1_result.get("route") != stage["evidence"]["id2x1_result"]["required_route"]
            or x1_audit.get("audit_passed") is not True
            or w3_result.get("route") != stage["evidence"]["id2w3r1_result"]["required_route"]
            or w3_audit.get("audit_passed") is not True
            or len(reference.get("states", [])) != 87
            or len(reference.get("actions", [])) != 86):
        raise y1.x1.InputIntegrityError("route evidence is not eligible")
    _, cfg, targets, _ = y1.x1.load(ROOT / stage["evidence"]["id2x1_config"]["path"])
    return stage, cfg, targets, reference


def campaign_streams(stage: dict[str, Any], cfg: Any,
                     targets: dict[str, Card15Target]) -> list[dict[str, Any]]:
    return y1.campaign_streams(stage, cfg, targets, expected_ids=ROLLOUT_IDS)


common_prefix_check = y1.common_prefix_check
safe_stop = y1.safe_stop
branch_metric = y1.branch_metric
scientific_metrics = y1.scientific_metrics
route_for = y1.route_for


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
                raise y1.x1.InputIntegrityError(f"issued slew changed: {row['rollout_id']}")
            for issue in range(65):
                if (actions[issue]["expected_card15_fields"]
                        != reference["actions"][issue]["expected_card15_fields"]):
                    raise y1.x1.InputIntegrityError(
                        f"prefix action changed: {row['rollout_id']}:{issue}")
            start = int(row["hold_start_issue"])
            for issue in range(start, stage["horizon_steps"]):
                if (actions[issue]["expected_card15_fields"]
                        != actions[start - 1]["expected_card15_fields"]
                        or float(actions[issue]["maximum_issued_delta_a"]) != 0.0):
                    raise y1.x1.InputIntegrityError(
                        f"terminal target is not held: {row['rollout_id']}:{issue}")
            for target in row["targets"]:
                minimum_headroom = min(minimum_headroom, *(min(
                    float(value) - float(low), float(high) - float(value))
                    for value, low, high in zip(target.current_a_tsc,
                                                cfg.min_current_a_tsc,
                                                cfg.max_current_a_tsc)))
            action_rows.append({key: value for key, value in row.items()
                                if key != "targets"})
        if minimum_headroom < float(stage["action_semantics"][
                "minimum_absolute_current_headroom_a"]):
            raise y1.x1.InputIntegrityError("absolute-current headroom below 95 A")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": y1.x1.sha256(path),
        "passed": not failures, "failures": failures, "action_streams": action_rows,
        "minimum_absolute_current_headroom_a": (
            minimum_headroom if math.isfinite(minimum_headroom) else None),
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
        "calibration_or_holdout_records_read": 0,
    }


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = y1.x1.inside_root(output, "ID2Y1R1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, reference = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = y1.x1.storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    y1.x1.write_new(output / "offline_preflight.json", preflight)
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
        y1.x1.write_new(output / "result.json", result)
        return result
    streams = campaign_streams(stage, cfg, targets)
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_novel_issue_clearance"])
    rows: list[dict[str, Any]] = []
    for stream in streams:
        row = y1.x1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        y1.x1.write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"] and not safe_stop(row, stage):
            break
    inventory = y1.x1.raw_inventory(output, rows, stage)
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
            "Finite source-local repaired late mixed braking branches only; PASS "
            "requires fresh repeatability and bounded-perturbation qualification."),
    }
    y1.x1.write_new(output / "result.json", result)
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
                       args.output or ROOT / f"rgeo_zgeo_1ms_id2y1r1_{args.source_revision[:8]}"))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
