#!/usr/bin/env python3
"""Run the prospectively frozen ID-2R1 exact f03 integrity replay."""

from __future__ import annotations

import argparse
import copy
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
    InputIntegrityError, compare_rows, inside_root, raw_inventory, sha256, write_new,
)
from scripts import rgeo_zgeo_1ms_id2p1_matched_factorial_development as p1  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2r1_f03_exact_replay.json"
CONFIG_SHA256 = "730d4e23441f97749e3d712485698944ea6397ba87c40643bef441fcfb6ecd15"
SCHEMA = "rgeo-zgeo-1ms-id2r1-f03-exact-replay-result-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2r1-f03-exact-replay-v1",
        "identity": "rgeo-zgeo-1ms-id2r1-f03-exact-replay-v1",
        "stage": "ID-2R1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "family_id": "f03", "probe_issue_step": 24,
        "probe_duration_issues": 2, "maximum_rollouts": 5,
        "maximum_reset_calls": 5, "maximum_advance_attempts": 170,
        "maximum_gotsc_calls": 170, "maximum_verified_plant_advances": 170,
        "maximum_retained_states": 175, "required_artifact_files_if_complete": 875,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_exact_f03_integrity_replay",
        "data_use": "integrity_and_route_decision_only_zero_fit_weight",
        "fit_calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "new_action_or_schedule_cells": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    expected_ids = [
        "f03__baseline__fresh_r1",
        "f03__p04_minus_i24_d2__fresh_r1",
        "f03__p04_plus_i24_d2__fresh_r1",
        "f03__p07_minus_i24_d2__fresh_r1",
        "f03__p07_plus_i24_d2__fresh_r1",
    ]
    if stage.get("rollout_ids") != expected_ids:
        raise InputIntegrityError("rollout identity changed")
    if stage.get("action_semantics") != {
        "absolute_card15_targets": True, "maximum_per_coil_issue_delta_a": 0.3,
        "issue_to_effect_state_offset": 1, "software_queue_added": False,
        "legacy_runner_clipping_may_be_relied_on": False,
        "future_actual_current": "forbidden",
    }:
        raise InputIntegrityError("action semantics changed")
    if stage.get("observability") != {
        "current_same_step_paired_boundary_rgeo_zgeo_and_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_history": "available",
        "future_successor": "unknown_before_issue", "invalid_boundary": "fail_closed",
    }:
        raise InputIntegrityError("observability contract changed")
    exploration = stage.get("empirical_exploration", {})
    if exploration.get("novel_successors") != 0 or exploration.get("post_successor_step_caps") != {
        "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0,
    } or exploration.get("inner_probe_issue_clearance") != {
        "r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05,
    } or exploration.get("outer_hard_envelope") != {
        "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10,
    }:
        raise InputIntegrityError("exploration envelope changed")
    if stage.get("repeatability") != {
        "geometry_m": 1e-12, "ip_a": 1e-9, "coil_a": 1e-9, "wire_a": 1e-9,
        "sprsina_byte_identity_required": False,
    }:
        raise InputIntegrityError("repeatability contract changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 24000000000,
        "maximum_estimated_raw_bytes": 12000000000,
        "minimum_free_bytes_after_estimate": 12000000000,
        "output_must_not_exist": True, "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage contract changed")
    if stage.get("semantic_artifacts") != [
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv",
    ] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("artifact contract changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    path = inside_root(path, "ID2R1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2R1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    evidence = stage["evidence"]
    for name in ("design", "id2p1_config", "id2p1_result", "id2p1_independent",
                 "id2r0_result", "id2r0_independent"):
        item = evidence[name]
        source = inside_root(ROOT / item["path"], name)
        if sha256(source) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    p1_result = _json(ROOT / evidence["id2p1_result"]["path"])
    p1_audit = _json(ROOT / evidence["id2p1_independent"]["path"])
    if p1_result.get("route") != evidence["id2p1_result"]["required_route"] or not p1_audit.get("audit_passed"):
        raise InputIntegrityError("ID2P1 evidence route changed")
    r0_result = _json(ROOT / evidence["id2r0_result"]["path"])
    r0_audit = _json(ROOT / evidence["id2r0_independent"]["path"])
    if r0_result.get("route") != evidence["id2r0_result"]["required_route"] or not r0_audit.get("audit_passed"):
        raise InputIntegrityError("ID2R0 evidence route changed")
    originals: dict[str, dict[str, Any]] = {}
    for item in evidence["original_compacts"]:
        source = inside_root(ROOT / item["path"], item["cell_id"])
        if sha256(source) != item["sha256"]:
            raise InputIntegrityError(f"original compact mismatch: {item['cell_id']}")
        row = _json(source)
        if row.get("cell_id") != item["cell_id"] or row.get("group_id") != "f03" or row.get("replay_index") != 0:
            raise InputIntegrityError(f"original compact identity: {item['cell_id']}")
        originals[item["cell_id"]] = row
    if len(originals) != 5:
        raise InputIntegrityError("five original compact rows required")
    pstage, cfg, targets, source = p1.load(ROOT / evidence["id2p1_config"]["path"])
    return stage, cfg, targets, source, originals


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any], source: dict[str, Any],
                     originals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pstage = _json(ROOT / stage["evidence"]["id2p1_config"]["path"])
    old = [row for row in p1.campaign_streams(pstage, cfg, targets, source)
           if row["group_id"] == "f03" and int(row["replay_index"]) == 0]
    old.sort(key=lambda row: (row["cell_kind"] != "baseline", row["cell_id"]))
    streams = []
    for fresh_id, item in zip(stage["rollout_ids"], old):
        row = copy.deepcopy(item)
        original_actions = originals[row["cell_id"]]["actions"]
        if len(row["actions"]) != len(original_actions):
            raise InputIntegrityError(f"original action count changed: {row['cell_id']}")
        for issue, (generated, recorded) in enumerate(zip(row["actions"], original_actions)):
            generated_semantics = {key: value for key, value in generated.items()
                                   if key != "maximum_issued_delta_a"}
            recorded_semantics = {key: value for key, value in recorded.items()
                                  if key != "maximum_issued_delta_a"}
            if generated_semantics != recorded_semantics:
                raise InputIntegrityError(f"original action semantics changed: {row['cell_id']}:{issue}")
        row["actions"] = copy.deepcopy(original_actions)
        row.update({"rollout_id": fresh_id, "replay_index": 1,
                    "integrity_only_zero_fit_weight": True,
                    "original_rollout_id": f"{row['cell_id']}__r0"})
        streams.append(row)
    if len(streams) != 5 or [row["rollout_id"] for row in streams] != stage["rollout_ids"]:
        raise InputIntegrityError("fresh campaign identity changed")
    return streams


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    streams: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, source, originals = load(path)
        streams = campaign_streams(stage, cfg, targets, source, originals)
        for stream in streams:
            original = originals[stream["cell_id"]]
            if len(stream["actions"]) != 34 or stream["actions"] != original["actions"]:
                raise InputIntegrityError(f"action stream differs: {stream['cell_id']}")
            if any(float(action["maximum_issued_delta_a"]) > 0.3 for action in stream["actions"]):
                raise InputIntegrityError(f"slew differs: {stream['cell_id']}")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures,
        "rollout_ids": [row["rollout_id"] for row in streams],
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
    }


def matched_prefix_checks(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = next((row for row in rows if row.get("cell_kind") == "baseline"), None)
    checks = []
    for probe in [row for row in rows if row.get("cell_kind") == "probe"]:
        failures: list[str] = []
        if baseline is None:
            failures.append("BASELINE_MISSING")
        else:
            for index in range(int(stage["probe_issue_step"]) + 1):
                for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                            "actual_current_decimal_a_tsc", "wire_current_a"):
                    if baseline["states"][index][key] != probe["states"][index][key]:
                        failures.append(f"STATE:{index}:{key}")
            for issue in range(int(stage["probe_issue_step"])):
                if baseline["actions"][issue]["expected_card15_fields"] != probe["actions"][issue]["expected_card15_fields"]:
                    failures.append(f"ACTION:{issue}")
        checks.append({"cell_id": probe.get("cell_id"), "passed": not failures,
                       "failures": list(dict.fromkeys(failures))})
    return checks


def replay_checks(rows: Sequence[dict[str, Any]], originals: dict[str, dict[str, Any]],
                  stage: dict[str, Any]) -> list[dict[str, Any]]:
    shim = {"repeatability": stage["repeatability"], "semantic_artifacts": stage["semantic_artifacts"]}
    checks = []
    for row in rows:
        check = compare_rows(originals[row["cell_id"]], row, shim)
        checks.append({"cell_id": row["cell_id"], "original_rollout_id": row["original_rollout_id"], **check})
    return checks


def response_checks(rows: Sequence[dict[str, Any]], originals: dict[str, dict[str, Any]],
                    stage: dict[str, Any]) -> list[dict[str, Any]]:
    fresh_base = next(row for row in rows if row["cell_kind"] == "baseline")
    old_base = originals["f03__baseline"]
    checks = []
    origin = int(stage["probe_issue_step"])
    for fresh in [row for row in rows if row["cell_kind"] == "probe"]:
        old = originals[fresh["cell_id"]]
        fresh_response = np.asarray([[s[k] - b[k] for k in ("r_geo_m", "z_geo_m", "ip_a")]
                                     for s, b in zip(fresh["states"][origin + 1:], fresh_base["states"][origin + 1:])])
        old_response = np.asarray([[s[k] - b[k] for k in ("r_geo_m", "z_geo_m", "ip_a")]
                                   for s, b in zip(old["states"][origin + 1:], old_base["states"][origin + 1:])])
        difference = np.max(np.abs(fresh_response - old_response), axis=0)
        checks.append({
            "cell_id": fresh["cell_id"], "passed": bool(
                difference[0] <= stage["repeatability"]["geometry_m"]
                and difference[1] <= stage["repeatability"]["geometry_m"]
                and difference[2] <= stage["repeatability"]["ip_a"]),
            "maximum_absolute_response_difference_rzi": difference.tolist(),
        })
    return checks


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    gate = stage["storage_gate"]
    estimate = int(gate["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(gate["minimum_free_bytes_before_run"])
            and free - estimate >= int(gate["minimum_free_bytes_after_estimate"])}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2R1 output")
    if output.exists():
        raise FileExistsError(str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    stage, cfg, targets, source, originals = load(path)
    storage_gate = storage(stage, output)
    output.mkdir()
    gate = offline(path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    if not storage_gate["passed"] or not gate["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"] else "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage_gate, "reasons": gate["failures"],
                  "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "fresh_records_have_zero_fit_weight": True, "models_fit_or_updated": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    rows = []
    for stream in campaign_streams(stage, cfg, targets, source, originals):
        row = p1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 5 and all(row["passed"] for row in rows)
    prefixes = matched_prefix_checks(rows, stage) if execution else []
    replays = replay_checks(rows, originals, stage) if execution else []
    responses = response_checks(rows, originals, stage) if execution else []
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif inventory["missing_required_artifacts"] or inventory["required_artifact_files"] != 875:
        route = stage["routes"]["raw_integrity_fail"]
    elif not (len(prefixes) == 4 and all(x["passed"] for x in prefixes)
              and len(replays) == 5 and all(x["passed"] for x in replays)
              and len(responses) == 4 and all(x["passed"] for x in responses)):
        route = stage["routes"]["replay_mismatch"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage_gate, "matched_prefix_checks": prefixes,
        "original_to_fresh_replay_checks": replays, "paired_response_replay_checks": responses,
        "rollouts_completed": len(rows), "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory, "fresh_records_have_zero_fit_weight": True,
        "fit_calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "models_fit_or_updated": 0, "claim_boundary": stage["claim_boundary"],
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
    result = offline(args.stage_config, args.source_revision) if args.mode == "offline" else run(
        args.stage_config, args.source_revision,
        args.output or ROOT / f"rgeo_zgeo_1ms_id2r1_{args.source_revision[:8]}")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
