#!/usr/bin/env python3
"""Run the frozen ID-2S2 exact replay of four measured sequences."""

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
from scripts import rgeo_zgeo_1ms_id2s1_measured_sequence_discriminator as s1  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2s2_sequence_exact_replay.json"
CONFIG_SHA256 = "43bbf436be27a5950a802cf99f10f63b40315f5e05e9d98c692af621d3c64afe"
SCHEMA = "rgeo-zgeo-1ms-id2s2-sequence-exact-replay-result-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    sequences = [
        "p04_plus__then__p07_minus", "p07_minus__then__p07_minus",
        "p07_minus__then__p07_plus", "p07_plus__then__p04_plus",
    ]
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2s2-sequence-exact-replay-v1",
        "identity": "rgeo-zgeo-1ms-id2s2-sequence-exact-replay-v1",
        "stage": "ID-2S2", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "family_id": "f03", "sequence_ids": sequences,
        "rollout_ids": [f"f03__seq_{value}__fresh_s2" for value in sequences],
        "maximum_rollouts": 4, "maximum_reset_calls": 4,
        "maximum_advance_attempts": 136, "maximum_gotsc_calls": 136,
        "maximum_verified_plant_advances": 136, "maximum_retained_states": 140,
        "required_artifact_files_if_complete": 700,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_exact_four_sequence_replay",
        "data_use": "repeatability_and_route_decision_only_zero_fit_weight",
        "fit_calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "new_action_timing_history_or_sequence_cells": 0, "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
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
    if stage.get("empirical_exploration") != {
        "novel_sequence_branches": 0,
        "post_successor_step_caps": {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0},
        "inner_probe_issue_clearance": {"r_geo_m": 0.025, "z_geo_m": 0.025,
                                         "ip_fraction": 0.05},
        "outer_hard_envelope": {"r_geo_m": 0.05, "z_geo_m": 0.05,
                                  "ip_fraction": 0.10},
        "stop_before_next_issue_after_any_failure": True,
        "post_action_abort_is_not_a_pre_action_bound": True,
    }:
        raise InputIntegrityError("exploration contract changed")
    if stage.get("repeatability") != {
        "geometry_m": 1e-12, "ip_a": 1e-9, "coil_a": 1e-9, "wire_a": 1e-9,
        "sprsina_byte_identity_required": False,
    }:
        raise InputIntegrityError("repeatability contract changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 20000000000,
        "maximum_estimated_raw_bytes": 10000000000,
        "minimum_free_bytes_after_estimate": 10000000000,
        "output_must_not_exist": True, "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage contract changed")
    if stage.get("semantic_artifacts") != [
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv",
    ] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("artifact contract changed")
    if stage.get("routes") != {
        "storage_fail": "ONE_MS_ID2S2_STORAGE_GATE_FAIL_NO_TSC",
        "offline_or_input_fail": "ONE_MS_ID2S2_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2S2_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2S2_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "replay_mismatch": "ONE_MS_ID2S2_SEQUENCE_REPLAY_MISMATCH_DEEP_REVIEW",
        "pass": "ONE_MS_ID2S2_SEQUENCE_EXACT_REPLAY_PASS_SHOOTING_DESIGN_ONLY",
    }:
        raise InputIntegrityError("route contract changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any],
                                       dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    path = inside_root(path, "ID2S2 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2S2 config hash mismatch")
    stage = _json(path)
    _require(stage)
    evidence = stage["evidence"]
    for name in ("design", "id2s1_config", "id2s1_result", "id2s1_independent"):
        item = evidence[name]
        source_path = inside_root(ROOT / item["path"], name)
        if sha256(source_path) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    s1_result = _json(ROOT / evidence["id2s1_result"]["path"])
    s1_audit = _json(ROOT / evidence["id2s1_independent"]["path"])
    if (s1_result.get("route") != evidence["id2s1_result"]["required_route"]
            or not s1_result.get("passed") or not s1_audit.get("audit_passed")):
        raise InputIntegrityError("ID2S1 evidence route changed")
    originals: dict[str, dict[str, Any]] = {}
    for item in evidence["original_compacts"]:
        source_path = inside_root(ROOT / item["path"], item["sequence_id"])
        if sha256(source_path) != item["sha256"]:
            raise InputIntegrityError(f"original compact mismatch: {item['sequence_id']}")
        row = _json(source_path)
        if row.get("sequence_id") != item["sequence_id"] or not row.get("passed"):
            raise InputIntegrityError(f"original compact identity: {item['sequence_id']}")
        originals[item["sequence_id"]] = row
    if list(originals) != stage["sequence_ids"]:
        raise InputIntegrityError("original compact order changed")
    sstage, cfg, targets, source, baseline, frozen_s0 = s1.load(
        ROOT / evidence["id2s1_config"]["path"])
    return stage, cfg, targets, source, baseline, frozen_s0, originals


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     source: dict[str, Any], frozen_s0: dict[str, Any],
                     originals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    sstage = _json(ROOT / stage["evidence"]["id2s1_config"]["path"])
    generated = {row["sequence_id"]: row for row in
                 s1.campaign_streams(sstage, cfg, targets, source, frozen_s0)}
    rows = []
    for sequence_id, rollout_id in zip(stage["sequence_ids"], stage["rollout_ids"]):
        stream = copy.deepcopy(generated[sequence_id])
        original = originals[sequence_id]
        # The generator records issue 0 relative to q0, whereas the authentic
        # rollout records its exact 1e-5 A source-to-q0 settling slew.  That
        # maximum is a measured/derived field, not part of the Card15 stream.
        # Every other action field must remain byte-for-byte identical.
        generated_contract = [
            {key: value for key, value in action.items()
             if key != "maximum_issued_delta_a"}
            for action in stream["actions"]
        ]
        recorded_contract = [
            {key: value for key, value in action.items()
             if key != "maximum_issued_delta_a"}
            for action in original["actions"]
        ]
        if generated_contract != recorded_contract:
            raise InputIntegrityError(f"original action stream changed: {sequence_id}")
        stream["actions"] = copy.deepcopy(original["actions"])
        stream.update({"rollout_id": rollout_id, "replay_index": 1,
                       "original_rollout_id": original["rollout_id"],
                       "development_only_zero_fit_weight": True})
        rows.append(stream)
    if len(rows) != 4 or [row["rollout_id"] for row in rows] != stage["rollout_ids"]:
        raise InputIntegrityError("campaign cardinality changed")
    return rows


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, source, baseline, frozen_s0, originals = load(path)
        rows = campaign_streams(stage, cfg, targets, source, frozen_s0, originals)
        for row in rows:
            if len(row["actions"]) != 34 or row["actions"] != originals[row["sequence_id"]]["actions"]:
                raise InputIntegrityError(f"action stream differs: {row['sequence_id']}")
            if any(float(action["maximum_issued_delta_a"]) > 0.3 for action in row["actions"]):
                raise InputIntegrityError(f"slew differs: {row['sequence_id']}")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "source_revision": source_revision, "stage_config_sha256": sha256(path),
            "passed": not failures, "failures": failures,
            "action_streams": [{key: value for key, value in row.items() if key != "targets"}
                               for row in rows],
            "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
            "verified_plant_advances": 0, "models_fit_or_updated": 0}


def replay_checks(rows: Sequence[dict[str, Any]], originals: dict[str, dict[str, Any]],
                  stage: dict[str, Any]) -> list[dict[str, Any]]:
    shim = {"repeatability": stage["repeatability"],
            "semantic_artifacts": stage["semantic_artifacts"]}
    checks = []
    for row in rows:
        check = compare_rows(originals[row["sequence_id"]], row, shim)
        checks.append({"sequence_id": row["sequence_id"],
                       "original_rollout_id": row["original_rollout_id"], **check})
    return checks


def response_checks(rows: Sequence[dict[str, Any]], originals: dict[str, dict[str, Any]],
                    baseline: dict[str, Any], stage: dict[str, Any]) -> list[dict[str, Any]]:
    base = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                       for state in baseline["states"]], dtype=float)
    checks = []
    for row in rows:
        old = originals[row["sequence_id"]]
        fresh_values = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                   for state in row["states"]], dtype=float)
        old_values = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                 for state in old["states"]], dtype=float)
        difference = np.max(np.abs((fresh_values[25:35] - base[25:35])
                                   - (old_values[25:35] - base[25:35])), axis=0)
        checks.append({
            "sequence_id": row["sequence_id"],
            "maximum_absolute_paired_response_difference_rzi": difference.tolist(),
            "passed": bool(difference[0] <= stage["repeatability"]["geometry_m"]
                           and difference[1] <= stage["repeatability"]["geometry_m"]
                           and difference[2] <= stage["repeatability"]["ip_a"]),
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
    output = inside_root(output, "ID2S2 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, source, baseline, frozen_s0, originals = load(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    storage_gate = storage(stage, output)
    output.mkdir()
    preflight = offline(path, source_revision)
    write_new(output / "offline_preflight.json", preflight)
    if not storage_gate["passed"] or not preflight["passed"]:
        route = stage["routes"]["storage_fail" if not storage_gate["passed"] else
                                  "offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route,
                  "storage_gate": storage_gate, "reasons": preflight["failures"],
                  "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
                  "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
                  "fresh_records_have_zero_fit_weight": True, "models_fit_or_updated": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = dict(stage)
    runtime["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_probe_issue_clearance"])
    rows = []
    for stream in campaign_streams(stage, cfg, targets, source, frozen_s0, originals):
        row = p1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 4 and all(row["passed"] for row in rows)
    prefixes = s1.matched_prefix_checks(rows, baseline) if execution else []
    replays = replay_checks(rows, originals, stage) if execution else []
    responses = response_checks(rows, originals, baseline, stage) if execution else []
    metrics = s1.measured_metrics(rows, baseline, frozen_s0, _json(
        ROOT / stage["evidence"]["id2s1_config"]["path"])) if execution else {"passed": False}
    original_metrics = _json(ROOT / stage["evidence"]["id2s1_result"]["path"])[
        "measured_sequence_metrics"]
    metrics_exact = metrics == original_metrics
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif (inventory["missing_required_artifacts"]
          or inventory["required_artifact_files"] != stage["required_artifact_files_if_complete"]):
        route = stage["routes"]["raw_integrity_fail"]
    elif not (len(prefixes) == len(replays) == len(responses) == 4
              and all(row["passed"] for row in prefixes + replays + responses)
              and metrics_exact):
        route = stage["routes"]["replay_mismatch"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
              "storage_gate": storage_gate, "matched_prefix_checks": prefixes,
              "original_to_fresh_replay_checks": replays,
              "paired_response_replay_checks": responses,
              "measured_sequence_metrics": metrics,
              "measured_metrics_exactly_reproduced": metrics_exact,
              "rollouts_completed": len(rows), "reset_calls": sum(row["reset_calls"] for row in rows),
              "advance_attempts": sum(row["advance_attempts"] for row in rows),
              "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
              "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
              **inventory, "fresh_records_have_zero_fit_weight": True,
              "two_repeats_do_not_define_a_probabilistic_tube": True,
              "fit_calibration_holdout_controller_expert_or_rl_use": "forbidden",
              "models_fit_or_updated": 0, "claim_boundary": stage["claim_boundary"]}
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
        args.output or ROOT / f"rgeo_zgeo_1ms_id2s2_{args.source_revision[:8]}")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
