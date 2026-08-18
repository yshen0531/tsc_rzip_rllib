#!/usr/bin/env python3
"""Run the frozen ID-2T1 matched p04+ continuation discriminator."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import json
import math
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id0_vector_tail as id0  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2p1_matched_factorial_development as p1  # noqa: E402
from scripts import rgeo_zgeo_1ms_id2s2_sequence_exact_replay as s2  # noqa: E402
from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, inside_root, raw_inventory, sha256, write_new,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    OneMsNR1SafetyEnvelope, assert_exact_slew, card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal  # noqa: E402

CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2t1_matched_continuation.json"
CONFIG_SHA256 = "49f736edb1a38bed1d2f6b41a44ebba041a4e7c836c93b5b09b9a77949f9b5d9"
SCHEMA = "rgeo-zgeo-1ms-id2t1-matched-continuation-result-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(inside_root(path, "JSON evidence").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError("JSON object required")
    return value


def _require(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2t1-matched-continuation-v1",
        "identity": "rgeo-zgeo-1ms-id2t1-matched-continuation-v1",
        "stage": "ID-2T1", "takeover_time_ms": 1100, "control_period_ms": 1,
        "horizon_steps": 34, "family_id": "f03", "continuation_arm": "p04_plus",
        "prefix_state_last_index": 30, "prefix_action_last_issue": 29,
        "continuation_issue_steps": [30, 31], "return_issue_step": 32,
        "terminal_q0_issue_step": 33, "maximum_rollouts": 4,
        "maximum_reset_calls": 4, "maximum_advance_attempts": 136,
        "maximum_gotsc_calls": 136, "maximum_verified_plant_advances": 136,
        "maximum_retained_states": 140, "required_artifact_files_if_complete": 700,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_matched_continuation_control_utility",
        "data_use": "route_decision_only_zero_fit_weight",
        "fit_calibration_holdout_controller_expert_or_rl_use": "forbidden",
        "models_fit_or_updated": 0,
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
        "post_takeover_causal_history": "available", "future_successor": "unknown_before_issue",
        "invalid_boundary": "fail_closed",
    }:
        raise InputIntegrityError("observability changed")
    if stage.get("empirical_exploration") != {
        "novel_history_conditioned_continuation_cells": 4,
        "post_successor_step_caps": {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0},
        "inner_probe_issue_clearance": {"r_geo_m": 0.025, "z_geo_m": 0.025,
                                          "ip_fraction": 0.05},
        "outer_hard_envelope": {"r_geo_m": 0.05, "z_geo_m": 0.05,
                                  "ip_fraction": 0.10},
        "stop_before_next_issue_after_any_failure": True,
        "post_action_abort_is_not_a_pre_action_bound": True,
    }:
        raise InputIntegrityError("empirical exploration changed")
    if stage.get("prefix_tolerance") != {
        "geometry_m": 1e-12, "ip_a": 1e-9, "coil_a": 1e-9, "wire_a": 1e-9,
        "sprsina_byte_identity_required": False,
    }:
        raise InputIntegrityError("prefix tolerance changed")
    if stage.get("measured_gates") != {
        "response_state_indices": [31, 32, 33, 34],
        "minimum_peak_paired_rz_norm_m": 0.00005,
        "minimum_peak_source_correction_projection_m": 0.000025,
        "minimum_best_absolute_source_distance_improvement_m": 0.000025,
        "maximum_absolute_paired_ip_response_a": 100.0,
    }:
        raise InputIntegrityError("measured gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 20000000000,
        "maximum_estimated_raw_bytes": 10000000000,
        "minimum_free_bytes_after_estimate": 10000000000,
        "output_must_not_exist": True, "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")
    if stage.get("semantic_artifacts") != [
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")
    if stage.get("routes") != {
        "storage_fail": "ONE_MS_ID2T1_STORAGE_GATE_FAIL_NO_TSC",
        "offline_or_input_fail": "ONE_MS_ID2T1_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2T1_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2T1_RAW_INTEGRITY_FAIL_PRESERVE_RAW",
        "prefix_mismatch": "ONE_MS_ID2T1_MATCHED_PREFIX_FAIL_STOP",
        "control_utility_fail": "ONE_MS_ID2T1_MATCHED_CONTINUATION_CONTROL_UTILITY_FAIL_REVIEW",
        "pass": "ONE_MS_ID2T1_MATCHED_CONTINUATION_PASS_ROUTE_DECISION_ONLY",
    }:
        raise InputIntegrityError("routes changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any],
                                       dict[str, dict[str, Any]], list[dict[str, Any]]]:
    path = inside_root(path, "ID2T1 config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2T1 config hash mismatch")
    stage = _json(path)
    _require(stage)
    evidence = stage["evidence"]
    for name in ("design", "id2s2_config", "id2s2_result", "id2s2_independent"):
        item = evidence[name]
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    result = _json(ROOT / evidence["id2s2_result"]["path"])
    audit = _json(ROOT / evidence["id2s2_independent"]["path"])
    if (not result.get("passed") or result.get("route") != evidence["id2s2_result"]["required_route"]
            or not audit.get("audit_passed")):
        raise InputIntegrityError("ID2S2 route changed")
    references: dict[str, dict[str, Any]] = {}
    for item in evidence["matched_compacts"]:
        source_path = inside_root(ROOT / item["path"], item["sequence_id"])
        if sha256(source_path) != item["sha256"]:
            raise InputIntegrityError(f"compact mismatch: {item['sequence_id']}")
        row = _json(source_path)
        if row.get("sequence_id") != item["sequence_id"] or not row.get("passed"):
            raise InputIntegrityError(f"compact identity: {item['sequence_id']}")
        references[item["sequence_id"]] = row
    sstage, cfg, targets, source, baseline, frozen_s0, originals = s2.load(
        ROOT / evidence["id2s2_config"]["path"])
    base_streams = s2.campaign_streams(sstage, cfg, targets, source, frozen_s0, originals)
    if list(references) != stage["sequence_ids"]:
        raise InputIntegrityError("reference order changed")
    return stage, cfg, targets, source, references, base_streams


def campaign_streams(stage: dict[str, Any], cfg: Any,
                     references: dict[str, dict[str, Any]],
                     base_streams: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sequence = {row["sequence_id"]: row for row in base_streams}
    p04_target = by_sequence["p04_plus__then__p07_minus"]["targets"][24]
    rows = []
    for sequence_id, rollout_id in zip(stage["sequence_ids"], stage["rollout_ids"]):
        base = by_sequence[sequence_id]
        reference = references[sequence_id]
        targets = copy.deepcopy(base["targets"])
        virtual = [copy.deepcopy(action["probe_virtual_action"]) for action in reference["actions"]]
        for issue in stage["continuation_issue_steps"]:
            targets[issue] = p04_target
            virtual[issue] = [1.0, 0.0]
        generated = p1._actions(targets, cfg, f"id2t1.{sequence_id}", virtual)
        generated[:30] = copy.deepcopy(reference["actions"][:30])
        rows.append({
            "rollout_id": rollout_id, "cell_id": f"f03__{sequence_id}__p04_plus_cont",
            "group_id": "f03", "sequence_id": sequence_id,
            "reference_rollout_id": reference["rollout_id"], "replay_index": 0,
            "cell_kind": "matched_continuation", "direction_id": "p04", "sign": "plus",
            "pulse_issue_step": 30, "probe_duration_issues": 2,
            "non_nominal_issue_steps": list(base["non_nominal_issue_steps"]) + [30],
            "targets": targets, "actions": generated,
            "development_only_zero_fit_weight": True,
        })
    return rows


def _prefix_reasons(actual: dict[str, Any], expected: dict[str, Any], stage: dict[str, Any],
                    index: int) -> list[str]:
    shim = {"repeatability": stage["prefix_tolerance"],
            "semantic_artifacts": stage["semantic_artifacts"]}
    check = id0.compare_rows({"states": [actual], "actions": []},
                             {"states": [expected], "actions": []}, shim)
    failures = [f"PREFIX_STATE:{index}:{value}" for value in check["failures"]]
    if actual.get("side") != expected.get("side"):
        failures.append(f"PREFIX_SIDE:{index}")
    return failures


def one_rollout(cfg: Any, stage: dict[str, Any], stream: dict[str, Any],
                reference: dict[str, Any], runner_cls: type = id0.CountingRunner) -> dict[str, Any]:
    runner = None
    states: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    attempted: list[dict[str, Any]] = []
    reasons: list[str] = []
    reset_calls = attempts = successes = 0
    started = time.perf_counter()
    try:
        runner = runner_cls(cfg, worker_id=f"id2t1_{stream['rollout_id']}", keep_workspace=False)
        reset_calls += 1
        state = runner.reset(episode_name=stream["rollout_id"])
        states.append(id0._record(cfg, state))
        id0._validate_record(states[-1], f"{stream['rollout_id']}.state0")
        source_signal = RGeoZGeoSignal.from_tsc_state(state)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        for issue, (target, frozen_action) in enumerate(zip(stream["targets"], stream["actions"])):
            if reasons:
                break
            signal = RGeoZGeoSignal.from_tsc_state(state)
            reasons.extend(envelope.state_reasons(
                signal, state["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(id0._outer_reasons(stage, source_signal, signal))
            if issue <= stage["prefix_state_last_index"]:
                reasons.extend(_prefix_reasons(states[-1], reference["states"][issue], stage, issue))
            if issue <= stage["prefix_action_last_issue"]:
                if frozen_action != reference["actions"][issue]:
                    reasons.append(f"PREFIX_ACTION:{issue}")
            if issue == stream["pulse_issue_step"]:
                reasons.extend(id0._pulse_clearance(stage, source_signal, signal))
            target_exact = card15_target_decimal_a(
                target, cfg.turns_tsc, name=f"id2t1.run.{stream['rollout_id']}.{issue}")
            try:
                maximum = assert_exact_slew(
                    states[-1]["active_command_decimal_a_tsc"], target_exact,
                    name=f"id2t1.issue.{stream['rollout_id']}.{issue}")
                if any(value < Decimal(str(low)) or value > Decimal(str(high))
                       for value, low, high in zip(target_exact, cfg.min_current_a_tsc,
                                                   cfg.max_current_a_tsc)):
                    raise ContractError("target leaves absolute current limits")
            except Exception as exc:
                reasons.append(f"ISSUED_ACTION:{issue}:{type(exc).__name__}:{exc}")
                break
            if reasons:
                break
            action = id0._action(frozen_action)
            action["maximum_issued_delta_a"] = maximum
            attempted.append(action)
            attempts += 1
            try:
                successor = runner.step_current_a(np.asarray(target.current_a_tsc, dtype=float))
            except Exception as exc:
                reasons.append(f"STEP_EXECUTION:{issue}:{type(exc).__name__}:{exc}")
                break
            try:
                record = id0._record(cfg, successor)
                id0._validate_record(record, f"{stream['rollout_id']}.state{issue + 1}")
            except Exception as exc:
                reasons.append(f"SUCCESSOR_RECORD:{issue}:{type(exc).__name__}:{exc}")
                break
            if record["time_ms"] != 1101 + issue:
                reasons.append(f"TIME:{issue}:{record['time_ms']}")
                break
            states.append(record)
            if int(successor.get("returncode", 0)) != 0 or bool(successor.get("abnormal", False)):
                reasons.append(f"TSC_STATUS:{issue}:{successor.get('returncode', 0)}")
                break
            actions.append(action)
            successes += 1
            if tuple(record["active_command_card15_fields"]) != target.card15_fields:
                reasons.append(f"CARD15:{issue}")
            try:
                record["maximum_observed_delta_a"] = assert_exact_slew(
                    states[-2]["actual_current_decimal_a_tsc"], record["actual_current_decimal_a_tsc"],
                    name=f"id2t1.observed.{stream['rollout_id']}.{issue}")
            except Exception as exc:
                reasons.append(f"OBSERVED_SLEW:{issue}:{type(exc).__name__}:{exc}")
            reasons.extend(envelope.state_reasons(
                RGeoZGeoSignal.from_tsc_state(successor), successor["currents_a_tsc"],
                cfg.min_current_a_tsc, cfg.max_current_a_tsc))
            reasons.extend(id0._outer_reasons(
                stage, source_signal, RGeoZGeoSignal.from_tsc_state(successor)))
            reasons.extend(id0._step_cap_reasons(stage, states[-2], states[-1]))
            state = successor
    except Exception as exc:
        reasons.append(f"ROLLOUT_EXECUTION:{type(exc).__name__}:{exc}")
    finally:
        if runner is not None:
            try:
                runner.cleanup_runtime_workspace()
            except Exception as exc:
                reasons.append(f"CLEANUP:{type(exc).__name__}:{exc}")
    reasons = list(dict.fromkeys(reasons))
    gotsc = 0 if runner is None else int(getattr(runner, "plant_advance_gotsc_calls", attempts))
    complete = (not reasons and reset_calls == 1 and attempts == successes == 34
                and len(states) == 35 and len(actions) == 34)
    return {**{key: value for key, value in stream.items() if key not in ("targets", "actions")},
            "schema_version": SCHEMA, "passed": complete, "reasons": reasons,
            "reset_calls": reset_calls, "advance_attempts": attempts,
            "plant_advance_gotsc_calls": gotsc, "verified_plant_advances": successes,
            "states": states, "actions": actions, "attempted_actions": attempted,
            "retry_attempted": False, "wall_time_s": time.perf_counter() - started}


def measured_metrics(rows: Sequence[dict[str, Any]], references: dict[str, dict[str, Any]],
                     stage: dict[str, Any]) -> dict[str, Any]:
    indices = stage["measured_gates"]["response_state_indices"]
    values = []
    all_responses = []
    for row in rows:
        ref = references[row["sequence_id"]]
        source = np.asarray([ref["states"][0]["r_geo_m"], ref["states"][0]["z_geo_m"]])
        response = []
        projection = []
        improvement = []
        ip = []
        for index in indices:
            base = np.asarray([ref["states"][index]["r_geo_m"], ref["states"][index]["z_geo_m"]])
            actual = np.asarray([row["states"][index]["r_geo_m"], row["states"][index]["z_geo_m"]])
            delta = actual - base
            correction = source - base
            unit = correction / np.linalg.norm(correction)
            response.append(delta.tolist())
            projection.append(float(delta @ unit))
            improvement.append(float(np.linalg.norm(base - source) - np.linalg.norm(actual - source)))
            ip.append(float(row["states"][index]["ip_a"] - ref["states"][index]["ip_a"]))
        response_array = np.asarray(response)
        norms = np.linalg.norm(response_array, axis=1)
        item = {"sequence_id": row["sequence_id"], "state_indices": indices,
                "paired_rz_response_m": response, "paired_ip_response_a": ip,
                "source_correction_projection_m": projection,
                "absolute_source_distance_improvement_m": improvement,
                "peak_paired_rz_norm_m": float(np.max(norms)),
                "peak_source_correction_projection_m": float(np.max(projection)),
                "best_absolute_source_distance_improvement_m": float(np.max(improvement)),
                "maximum_absolute_paired_ip_response_a": float(np.max(np.abs(ip)))}
        gates = stage["measured_gates"]
        item["passed"] = bool(
            item["peak_paired_rz_norm_m"] >= gates["minimum_peak_paired_rz_norm_m"]
            and item["peak_source_correction_projection_m"] >= gates[
                "minimum_peak_source_correction_projection_m"]
            and item["best_absolute_source_distance_improvement_m"] >= gates[
                "minimum_best_absolute_source_distance_improvement_m"]
            and item["maximum_absolute_paired_ip_response_a"] <= gates[
                "maximum_absolute_paired_ip_response_a"])
        values.append(item)
        all_responses.append(response_array)
    spread = 0.0
    for index in range(len(indices)):
        for left in range(len(all_responses)):
            for right in range(left + 1, len(all_responses)):
                spread = max(spread, float(np.linalg.norm(
                    all_responses[left][index] - all_responses[right][index])))
    return {"history_metrics": values, "maximum_cross_history_rz_response_spread_m": spread,
            "passed_histories": sum(item["passed"] for item in values),
            "passed": len(values) == 4 and all(item["passed"] for item in values)}


def storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    free = shutil.disk_usage(output.parent).free
    estimate = int(stage["storage_gate"]["maximum_estimated_raw_bytes"])
    return {"free_bytes_before_run": free, "estimated_raw_bytes": estimate,
            "estimated_free_bytes_after_run": free - estimate,
            "passed": free >= stage["storage_gate"]["minimum_free_bytes_before_run"]
            and free - estimate >= stage["storage_gate"]["minimum_free_bytes_after_estimate"]}


def offline(path: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    streams = []
    try:
        stage, cfg, targets, source, references, base = load(path)
        streams = campaign_streams(stage, cfg, references, base)
        for stream in streams:
            if len(stream["actions"]) != 34 or max(
                    float(action["maximum_issued_delta_a"]) for action in stream["actions"]) > 0.3:
                raise InputIntegrityError(f"action contract: {stream['sequence_id']}")
            if stream["actions"][:30] != references[stream["sequence_id"]]["actions"][:30]:
                raise InputIntegrityError(f"prefix action contract: {stream['sequence_id']}")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {"schema_version": SCHEMA, "kind": "offline_preflight",
            "source_revision": source_revision, "stage_config_sha256": sha256(path),
            "passed": not failures, "failures": failures,
            "action_streams": [{key: value for key, value in row.items() if key != "targets"}
                               for row in streams], "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
            "models_fit_or_updated": 0}


def run(path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2T1 output")
    if output.exists():
        raise FileExistsError(str(output))
    stage, cfg, targets, source, references, base = load(path)
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
                  "models_fit_or_updated": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime = copy.deepcopy(stage)
    runtime["empirical_exploration"]["inner_pulse_issue_clearance"] = (
        stage["empirical_exploration"]["inner_probe_issue_clearance"])
    rows = []
    for stream in campaign_streams(stage, cfg, references, base):
        row = one_rollout(cfg, runtime, stream, references[stream["sequence_id"]])
        row.update({"source_revision": source_revision})
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    execution = len(rows) == 4 and all(row["passed"] for row in rows)
    prefix_ok = execution and all(not _prefix_reasons(
        row["states"][index], references[row["sequence_id"]]["states"][index], stage, index)
        for row in rows for index in range(31))
    metrics = measured_metrics(rows, references, stage) if execution else {"passed": False}
    if not execution:
        route = stage["routes"]["execution_or_interface_fail"]
    elif inventory["missing_required_artifacts"] or inventory["required_artifact_files"] != 700:
        route = stage["routes"]["raw_integrity_fail"]
    elif not prefix_ok:
        route = stage["routes"]["prefix_mismatch"]
    elif not metrics["passed"]:
        route = stage["routes"]["control_utility_fail"]
    else:
        route = stage["routes"]["pass"]
    result = {"schema_version": SCHEMA, "source_revision": source_revision,
              "stage_config_sha256": CONFIG_SHA256, "passed": route == stage["routes"]["pass"],
              "route": route, "storage_gate": storage_gate, "prefix_checks_passed": prefix_ok,
              "matched_continuation_metrics": metrics, "rollouts_completed": len(rows),
              "reset_calls": sum(row["reset_calls"] for row in rows),
              "advance_attempts": sum(row["advance_attempts"] for row in rows),
              "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
              "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
              **inventory, "records_have_zero_fit_weight": True,
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
        args.output or ROOT / f"rgeo_zgeo_1ms_id2t1_{args.source_revision[:8]}")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
