#!/usr/bin/env python3
"""Run the frozen ID-2S1 four-branch measured sequence discriminator."""

from __future__ import annotations

import argparse
import copy
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
from scripts import rgeo_zgeo_1ms_id2p1_matched_factorial_development as p1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2s0_sequence_utility_selector as s0  # noqa: E402


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2s1_measured_sequence_discriminator.json"
CONFIG_SHA256 = "fbf685fd55d2825cb284d1d45ade697f9837bf36ebb3637921a0c93509a9d319"
SCHEMA = "rgeo-zgeo-1ms-id2s1-measured-sequence-discriminator-result-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2s1-measured-sequence-discriminator-v1",
        "identity": "rgeo-zgeo-1ms-id2s1-measured-sequence-discriminator-v1",
        "stage": "ID-2S1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "family_id": "f03",
        "first_arm_issue_steps": [24, 25], "first_return_issue_step": 26,
        "second_arm_issue_steps": [27, 28], "second_return_issue_step": 29,
        "response_state_indices": list(range(25, 35)),
        "maximum_rollouts": 4, "maximum_reset_calls": 4,
        "maximum_advance_attempts": 136, "maximum_gotsc_calls": 136,
        "maximum_verified_plant_advances": 136, "maximum_retained_states": 140,
        "required_artifact_files_if_complete": 700,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_measured_two_arm_sequence_development_discriminator",
        "data_use": "development_sequence_geometry_only_zero_fit_weight",
        "fit_calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "models_fit_or_updated": 0,
    }
    for key, expected in exact.items():
        if stage.get(key) != expected:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    selected = [
        "p04_plus__then__p07_minus",
        "p07_minus__then__p07_minus",
        "p07_minus__then__p07_plus",
        "p07_plus__then__p04_plus",
    ]
    if stage.get("selected_sequence_ids") != selected:
        raise InputIntegrityError("selected sequence identity changed")
    if stage.get("rollout_ids") != [f"f03__seq_{value}__fresh_s1" for value in selected]:
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
    if exploration != {
        "novel_sequence_branches": 4,
        "post_successor_step_caps": {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0},
        "inner_probe_issue_clearance": {"r_geo_m": 0.025, "z_geo_m": 0.025,
                                         "ip_fraction": 0.05},
        "outer_hard_envelope": {"r_geo_m": 0.05, "z_geo_m": 0.05,
                                  "ip_fraction": 0.10},
        "stop_before_next_issue_after_any_failure": True,
        "post_action_abort_is_not_a_pre_action_bound": True,
    }:
        raise InputIntegrityError("empirical exploration contract changed")
    if stage.get("repeatability") != {
        "geometry_m": 1e-12, "ip_a": 1e-9, "coil_a": 1e-9, "wire_a": 1e-9,
        "sprsina_byte_identity_required": False,
    }:
        raise InputIntegrityError("repeatability contract changed")
    if stage.get("measured_gates") != {
        "target_direction_count": 16, "minimum_sample_norm_m": 0.00002,
        "minimum_each_direction_progress_m": 0.00002,
        "maximum_angular_gap_deg": 180.0,
        "maximum_absolute_paired_ip_response_a": 100.0,
        "additive_interaction_is_descriptive_not_gated": True,
    }:
        raise InputIntegrityError("measured gates changed")
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
        "storage_fail": "ONE_MS_ID2S1_STORAGE_GATE_FAIL_NO_TSC",
        "offline_or_input_fail": "ONE_MS_ID2S1_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2S1_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2S1_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "prefix_mismatch": "ONE_MS_ID2S1_MATCHED_PREFIX_FAIL_DEEP_REVIEW",
        "measured_utility_fail": "ONE_MS_ID2S1_MEASURED_SEQUENCE_GEOMETRY_OR_IP_FAIL_ROUTE_REVIEW",
        "pass": "ONE_MS_ID2S1_MEASURED_SEQUENCE_PASS_FRESH_REPLAY_TUBE_DESIGN_ONLY",
    }:
        raise InputIntegrityError("route contract changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any],
                                       dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = inside_root(path, "ID2S1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2S1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    evidence = stage["evidence"]
    for name, item in evidence.items():
        source_path = inside_root(ROOT / item["path"], name)
        if sha256(source_path) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    s0_result = _json(ROOT / evidence["id2s0_result"]["path"])
    s0_audit = _json(ROOT / evidence["id2s0_independent"]["path"])
    if (s0_result.get("route") != evidence["id2s0_result"]["required_route"]
            or not s0_result.get("passed") or not s0_audit.get("audit_passed")):
        raise InputIntegrityError("ID2S0 evidence route changed")
    r1_result = _json(ROOT / evidence["id2r1_result"]["path"])
    r1_audit = _json(ROOT / evidence["id2r1_independent"]["path"])
    if (r1_result.get("route") != evidence["id2r1_result"]["required_route"]
            or not r1_result.get("passed") or not r1_audit.get("audit_passed")):
        raise InputIntegrityError("ID2R1 evidence route changed")
    baseline = _json(ROOT / evidence["matched_baseline"]["path"])
    if (baseline.get("cell_id") != "f03__baseline" or not baseline.get("passed")
            or len(baseline.get("states", [])) != 35 or len(baseline.get("actions", [])) != 34):
        raise InputIntegrityError("matched baseline identity changed")
    sstage, cfg, targets, source, _ = s0.load(ROOT / evidence["id2s0_config"]["path"])
    recomputed = s0.execute(ROOT / evidence["id2s0_config"]["path"], "id2s1-reproduction")
    for key in ("route", "passed", "action_stream_gate_passed", "utility_gate_passed",
                "selection", "candidate_streams", "predicted_candidates"):
        if recomputed.get(key) != s0_result.get(key):
            raise InputIntegrityError(f"ID2S0 reproduction mismatch: {key}")
    return stage, cfg, targets, source, baseline, s0_result


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any],
                     source: dict[str, Any], s0_result: dict[str, Any]) -> list[dict[str, Any]]:
    sstage = _json(ROOT / stage["evidence"]["id2s0_config"]["path"])
    generated = {row["sequence_id"]: row for row in
                 s0.candidate_streams(sstage, cfg, targets, source)}
    recorded = {row["sequence_id"]: row for row in s0_result["candidate_streams"]}
    if s0_result["selection"]["sequence_ids"] != stage["selected_sequence_ids"]:
        raise InputIntegrityError("selected sequence order changed")
    streams = []
    for sequence_id, rollout_id in zip(stage["selected_sequence_ids"], stage["rollout_ids"]):
        candidate = generated[sequence_id]
        saved = recorded[sequence_id]
        if not saved.get("selected") or saved.get("actions") != candidate["actions"]:
            raise InputIntegrityError(f"selected action stream changed: {sequence_id}")
        first, second = sequence_id.split("__then__")
        streams.append({
            "rollout_id": rollout_id,
            "cell_id": f"f03__sequence_{sequence_id}",
            "group_id": "f03", "context_id": "f03", "replay_index": 0,
            "cell_kind": "sequence", "direction_id": sequence_id, "sign": None,
            "conditioners": "f03_exact_admitted_prefix",
            "sequence_id": sequence_id, "first_arm": first, "second_arm": second,
            "probe_issue_step": 24, "probe_duration_issues": 2,
            "non_nominal_issue_steps": [24, 27],
            "targets": copy.deepcopy(candidate["targets"]),
            "actions": copy.deepcopy(candidate["actions"]),
            "development_only_zero_fit_weight": True,
        })
    if len(streams) != 4 or [row["rollout_id"] for row in streams] != stage["rollout_ids"]:
        raise InputIntegrityError("campaign cardinality changed")
    return streams


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        stage, cfg, targets, source, baseline, s0_result = load(path)
        rows = campaign_streams(stage, cfg, targets, source, s0_result)
        for row in rows:
            if len(row["actions"]) != 34:
                raise InputIntegrityError(f"action count changed: {row['sequence_id']}")
            if any(float(action["maximum_issued_delta_a"]) > 0.3 for action in row["actions"]):
                raise InputIntegrityError(f"slew changed: {row['sequence_id']}")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision, "stage_config_sha256": sha256(path),
        "passed": not failures, "failures": failures,
        "action_streams": [{key: value for key, value in row.items()
                            if key not in ("targets",)} for row in rows],
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0, "models_fit_or_updated": 0,
    }


def matched_prefix_checks(rows: Sequence[dict[str, Any]], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for row in rows:
        failures = []
        for index in range(25):
            for key in ("r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
                        "actual_current_decimal_a_tsc", "wire_current_a"):
                if row["states"][index][key] != baseline["states"][index][key]:
                    failures.append(f"STATE:{index}:{key}")
        for issue in range(24):
            if (row["actions"][issue]["expected_card15_fields"]
                    != baseline["actions"][issue]["expected_card15_fields"]):
                failures.append(f"ACTION:{issue}")
        checks.append({"sequence_id": row["sequence_id"], "passed": not failures,
                       "failures": list(dict.fromkeys(failures))})
    return checks


def measured_metrics(rows: Sequence[dict[str, Any]], baseline: dict[str, Any],
                     s0_result: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    predicted = {row["sequence_id"]: np.asarray(row["predicted_rz_response_m"], dtype=float)
                 for row in s0_result["predicted_candidates"]}
    base = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                       for state in baseline["states"]], dtype=float)
    sequence_metrics = []
    all_samples = []
    maximum_ip = 0.0
    for row in rows:
        truth = np.asarray([[state[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                            for state in row["states"]], dtype=float)
        response = truth[25:35] - base[25:35]
        expected = predicted[row["sequence_id"]]
        interaction = response[:, :2] - expected
        norms = np.linalg.norm(response[:, :2], axis=1)
        peak = int(np.argmax(norms))
        max_ip = float(np.max(np.abs(response[:, 2])))
        maximum_ip = max(maximum_ip, max_ip)
        all_samples.append(response[:, :2])
        sequence_metrics.append({
            "sequence_id": row["sequence_id"], "first_arm": row["first_arm"],
            "second_arm": row["second_arm"], "response_state_indices": list(range(25, 35)),
            "measured_rzi_response": response.tolist(),
            "id2s0_additive_rz_response_m": expected.tolist(),
            "actual_minus_additive_rz_interaction_m": interaction.tolist(),
            "maximum_absolute_interaction_r_m": float(np.max(np.abs(interaction[:, 0]))),
            "maximum_absolute_interaction_z_m": float(np.max(np.abs(interaction[:, 1]))),
            "peak_state_index": 25 + peak,
            "peak_rz_response_m": response[peak, :2].tolist(),
            "peak_rz_response_norm_m": float(norms[peak]),
            "maximum_absolute_paired_ip_response_a": max_ip,
        })
    samples = np.concatenate(all_samples) if all_samples else np.empty((0, 2))
    gates = stage["measured_gates"]
    units = np.asarray([[math.cos(2 * math.pi * i / gates["target_direction_count"]),
                         math.sin(2 * math.pi * i / gates["target_direction_count"])]
                        for i in range(gates["target_direction_count"])], dtype=float)
    progress = (np.max(samples @ units.T, axis=0) if len(samples)
                else np.full(gates["target_direction_count"], -math.inf))
    gap = s0.angular_gap(samples, float(gates["minimum_sample_norm_m"]))
    progress_ok = bool(np.min(progress) >= gates["minimum_each_direction_progress_m"])
    gap_ok = bool(gap < gates["maximum_angular_gap_deg"])
    ip_ok = bool(maximum_ip <= gates["maximum_absolute_paired_ip_response_a"])
    return {
        "sequence_count": len(sequence_metrics), "sample_count": int(len(samples)),
        "sequence_metrics": sequence_metrics,
        "direction_progress_m": progress.tolist(),
        "minimum_direction_progress_m": float(np.min(progress)),
        "mean_direction_progress_m": float(np.mean(progress)),
        "maximum_angular_gap_deg": float(gap),
        "maximum_absolute_paired_ip_response_a": maximum_ip,
        "direction_progress_gate_passed": progress_ok,
        "angular_gap_gate_passed": gap_ok, "ip_gate_passed": ip_ok,
        "additive_interaction_was_descriptive_only": True,
        "passed": len(sequence_metrics) == 4 and len(samples) == 40
                  and progress_ok and gap_ok and ip_ok,
    }


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    gate = stage["storage_gate"]
    estimate = int(gate["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= int(gate["minimum_free_bytes_before_run"])
            and free - estimate >= int(gate["minimum_free_bytes_after_estimate"])}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2S1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, source, baseline, s0_result = load(path)
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
    for stream in campaign_streams(stage, cfg, targets, source, s0_result):
        row = p1.one_rollout(cfg, runtime, stream)
        row.update({"schema_version": SCHEMA, "source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 4 and all(row["passed"] for row in rows)
    prefixes = matched_prefix_checks(rows, baseline) if execution else []
    metrics = measured_metrics(rows, baseline, s0_result, stage) if execution else {"passed": False}
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif (inventory["missing_required_artifacts"]
          or inventory["required_artifact_files"] != stage["required_artifact_files_if_complete"]):
        route = stage["routes"]["raw_integrity_fail"]
    elif not (len(prefixes) == 4 and all(row["passed"] for row in prefixes)):
        route = stage["routes"]["prefix_mismatch"]
    elif not metrics["passed"]:
        route = stage["routes"]["measured_utility_fail"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "storage_gate": storage_gate, "matched_prefix_checks": prefixes,
        "measured_sequence_metrics": metrics,
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
        args.output or ROOT / f"rgeo_zgeo_1ms_id2s1_{args.source_revision[:8]}")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
