#!/usr/bin/env python3
"""Prospectively frozen 1 ms ID-1B persistent-dwell geometry discriminator."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError,
    compare_rows,
    inside_root,
    one_rollout,
    raw_inventory,
    sha256,
    target_from_fields,
    write_new,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target,
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id1b-persistent-dwell-geometry-v1"
CONFIG_SHA256 = "3ceef849a801a5a027cc39144a4e3210a325a2e2d45e611fadd2f20369c3d1ae"
DEFAULT_STAGE = ROOT / "configs/rgeo_zgeo_1ms_id1b_persistent_dwell_geometry.json"
OFFLINE_PASS = "ONE_MS_ID1B_OFFLINE_PASS_RUN_ONLY"


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": SCHEMA,
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 24,
        "rollouts": 14,
        "maximum_reset_calls": 14,
        "maximum_advance_attempts": 336,
        "maximum_gotsc_calls": 336,
        "maximum_verified_plant_advances": 336,
        "completed_state_count": 350,
        "completed_required_artifact_files": 1750,
        "retry_after_any_advance_attempt": "forbidden",
        "holdout_records_read": 0,
        "baseline_repetitions": 2,
        "arm_repetitions": 2,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("directions") != ["p03", "p04", "p07"] or stage.get("signs") != ["plus", "minus"]:
        raise InputIntegrityError("signed direction matrix mismatch")
    if stage.get("development_use_after_all_gates_pass") != "allowed_for_temporal_action_basis_selection_only":
        raise InputIntegrityError("basis-selection use mismatch")
    for key in (
        "model_fit_use", "calibration_use", "holdout_use",
        "expert_oracle_fixture_bc_dagger_rl_use",
        "controller_safety_or_recourse_qualification_use",
    ):
        if stage.get(key) != "forbidden":
            raise InputIntegrityError(f"forbidden data-use mismatch: {key}")
    if stage.get("dwell") != {
        "first_issue": 10, "last_issue": 13, "return_issue": 14,
        "pure_effect_state_indices": [11, 12, 13, 14],
        "return_effect_state_index": 15, "tail_state_indices": [15, 24],
    }:
        raise InputIntegrityError("persistent dwell timing mismatch")
    action = stage.get("action_semantics", {})
    if (
        action.get("effect_state_index") != "issue_step_plus_one"
        or action.get("maximum_single_turn_adjacent_delta_a") != 0.3
        or action.get("same_target_held_through_measurement_window") is not True
        or action.get("signed_pairs_assumed_odd") is not False
    ):
        raise InputIntegrityError("action semantics mismatch")
    exploration = stage.get("empirical_exploration", {})
    if exploration.get("pre_action_transition_tube_claimed") is not False:
        raise InputIntegrityError("ID1B may not claim a transition tube")
    if exploration.get("post_successor_step_caps") != {
        "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0
    } or exploration.get("outer_hard_envelope") != {
        "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10
    }:
        raise InputIntegrityError("exploration envelope mismatch")
    gates = stage.get("scientific_gates", {})
    if gates != {
        "response_state_indices": [11, 12, 13, 14],
        "minimum_peak_rz_response_norm_m_per_signed_arm": 0.00001,
        "maximum_absolute_ip_response_a": 150.0,
        "minimum_rz_response_rank": 2,
        "maximum_best_pair_condition": 20.0,
        "maximum_angular_gap_deg": 175.0,
        "directional_support_angle_samples": 360,
        "minimum_directional_support_m": 0.000005,
        "tail_extinction_is_not_a_gate": True,
    }:
        raise InputIntegrityError("scientific gate mismatch")
    expected_routes = {
        "offline_fail": "ONE_MS_ID1B_OFFLINE_FAIL_NO_TSC",
        "package_or_deployment_fail": "ONE_MS_ID1B_PACKAGE_OR_DEPLOYMENT_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID1B_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID1B_RAW_INTEGRITY_FAIL_STOP",
        "repeatability_fail": "ONE_MS_ID1B_REPEATABILITY_FAIL_REDESIGN",
        "signal_or_ip_fail": "ONE_MS_ID1B_SIGNAL_OR_IP_FAIL_REDESIGN",
        "positive_span_fail": "ONE_MS_ID1B_PERSISTENT_POSITIVE_SPAN_FAIL_DIRECTION_REDESIGN",
        "pass": "ONE_MS_ID1B_PERSISTENT_TEMPORAL_ACTION_BASIS_PASS_CONTEXT_DATA_REQUIRED",
    }
    if stage.get("routes") != expected_routes:
        raise InputIntegrityError("route contract mismatch")
    if stage.get("semantic_artifacts") != [
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"
    ] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("artifact contract mismatch")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    stage_path = inside_root(stage_path, "stage config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID1B config SHA-256 mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    evidence: dict[str, Any] = {}
    for label, row in stage["evidence"].items():
        if label == "base_tsc_config_sha256":
            continue
        path = inside_root(ROOT / row["path"], label)
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"{label} hash mismatch")
        evidence[label] = json.loads(path.read_text(encoding="utf-8"))
    if evidence["id1a_primary"].get("route") != "ONE_MS_ID1A_HISTORY_CONTRAST_FAIL_REDESIGN":
        raise InputIntegrityError("ID1A route mismatch")
    if evidence["id1a_primary"].get("development_data_eligible") is not False:
        raise InputIntegrityError("ID1A data-use mismatch")
    if evidence["id1a_independent"].get("audit_passed") is not True:
        raise InputIntegrityError("ID1A independent audit mismatch")
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder, dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms,
    )
    return stage, cfg, evidence


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "rollout_id": f"q0_baseline_r{repeat}", "context_id": "baseline",
            "direction_id": None, "sign": None, "repeat_index": repeat,
            "pulse_issue_step": None,
        }
        for repeat in range(stage["baseline_repetitions"])
    ]
    for direction in stage["directions"]:
        for sign in stage["signs"]:
            for repeat in range(stage["arm_repetitions"]):
                rows.append({
                    "rollout_id": f"late_{direction}_{sign}_r{repeat}",
                    "context_id": "late", "direction_id": direction,
                    "sign": sign, "repeat_index": repeat,
                    "pulse_issue_step": stage["dwell"]["first_issue"],
                })
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError("rollout matrix mismatch")
    return rows


def _targets(stage: dict[str, Any], cfg: TSCConfig, evidence: dict[str, Any], source: dict[str, Any]) -> dict[str, Card15Target]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"], turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc, max_current_a_tsc=cfg.max_current_a_tsc,
    )
    result: dict[str, Card15Target] = {"q0": frozen.q0}
    selected = {row["direction_id"]: row for row in evidence["id0_direction_config"]["directions"]}
    if list(selected) != stage["directions"]:
        raise InputIntegrityError("ID0 direction evidence mismatch")
    for direction in stage["directions"]:
        for sign in stage["signs"]:
            result[f"{direction}:{sign}"] = target_from_fields(
                selected[direction][f"{sign}_card15_fields"], cfg,
                f"id1b.{direction}.{sign}",
            )
    return result


def targets_and_streams(stage: dict[str, Any], cfg: TSCConfig, evidence: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    targets = _targets(stage, cfg, evidence, source)
    streams = []
    for spec in rollout_specs(stage):
        sequence = [targets["q0"]] * stage["horizon_steps"]
        if spec["direction_id"] is not None:
            target = targets[f"{spec['direction_id']}:{spec['sign']}"]
            for issue in range(stage["dwell"]["first_issue"], stage["dwell"]["last_issue"] + 1):
                sequence[issue] = target
        previous = tuple(source["active_command_decimal_a_tsc"])
        actions = []
        for issue, target in enumerate(sequence):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"id1b.{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(previous, exact, name=f"id1b.{spec['rollout_id']}.{issue}")
            if any(
                value < Decimal(str(low)) or value > Decimal(str(high))
                for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)
            ):
                raise InputIntegrityError("target leaves absolute current limits")
            actions.append({
                "issue_step": issue, "issue_time_ms": 1100 + issue,
                "effect_state_index": issue + 1, "effect_time_ms": 1101 + issue,
                "expected_card15_fields": list(target.card15_fields),
                "target_current_a_tsc": list(target.current_a_tsc),
                "maximum_issued_delta_a": maximum,
                "persistent_dwell_effect_age": (
                    issue - stage["dwell"]["first_issue"] + 1
                    if stage["dwell"]["first_issue"] <= issue <= stage["dwell"]["last_issue"]
                    else None
                ),
            })
            previous = exact
        if spec["direction_id"] is not None:
            fields = [actions[index]["expected_card15_fields"] for index in range(10, 14)]
            if any(value != fields[0] for value in fields[1:]):
                raise InputIntegrityError("measurement window changes target")
            if actions[14]["expected_card15_fields"] != list(targets["q0"].card15_fields):
                raise InputIntegrityError("return issue is not exact q0")
        streams.append({**spec, "targets": sequence, "actions": actions})
    return streams


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = source_signal = streams = None
    try:
        stage, cfg, evidence = load(stage_path)
        source = _source(cfg)
        source_signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        failures.extend(envelope.state_reasons(
            source_signal, source["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc
        ))
        raw = targets_and_streams(stage, cfg, evidence, source)
        streams = [{key: value for key, value in row.items() if key != "targets"} for row in raw]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures,
        "route": OFFLINE_PASS if not failures else (
            stage["routes"]["offline_fail"] if stage else "ONE_MS_ID1B_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures,
        "source_signal": None if source_signal is None else source_signal.to_dict(),
        "rollout_action_streams": streams,
        "reset_calls": 0, "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
    }


def _baseline(rows: Sequence[dict[str, Any]]) -> np.ndarray:
    selected = [row for row in rows if row["context_id"] == "baseline"]
    if len(selected) != 2:
        raise ValueError("two matched q0 baselines required")
    return np.asarray([
        [
            np.mean([row["states"][index]["r_geo_m"] for row in selected]),
            np.mean([row["states"][index]["z_geo_m"] for row in selected]),
            np.mean([row["states"][index]["ip_a"] for row in selected]),
        ]
        for index in range(len(selected[0]["states"]))
    ], dtype=float)


def _angular_gap(vectors: np.ndarray) -> float:
    angles = sorted(math.degrees(math.atan2(float(row[1]), float(row[0]))) % 360.0 for row in vectors)
    return max(right - left for left, right in zip(angles, angles[1:] + [angles[0] + 360.0]))


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    baseline = _baseline(rows)
    arm_metrics = []
    for row in rows:
        if row["context_id"] == "baseline":
            continue
        response = np.asarray([
            [state["r_geo_m"], state["z_geo_m"], state["ip_a"]]
            for state in row["states"]
        ], dtype=float) - baseline
        indices = stage["scientific_gates"]["response_state_indices"]
        mean = np.mean(response[indices], axis=0)
        tail = response[stage["dwell"]["return_effect_state_index"]:]
        arm_metrics.append({
            "rollout_id": row["rollout_id"], "direction_id": row["direction_id"],
            "sign": row["sign"], "repeat_index": row["repeat_index"],
            "response_state_indices": indices,
            "mean_persistent_effect_1_4": mean.tolist(),
            "peak_persistent_rz_norm_m": float(np.max(np.linalg.norm(response[indices, :2], axis=1))),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(response[indices, 2]))),
            "tail_peak_rz_norm_m_reported_only": float(np.max(np.linalg.norm(tail[:, :2], axis=1))),
            "terminal_rz_norm_m_reported_only": float(np.linalg.norm(response[-1, :2])),
            "terminal_absolute_ip_response_a_reported_only": float(abs(response[-1, 2])),
        })

    keys = []
    vectors = []
    for direction in stage["directions"]:
        for sign in stage["signs"]:
            selected = [
                row["mean_persistent_effect_1_4"] for row in arm_metrics
                if row["direction_id"] == direction and row["sign"] == sign
            ]
            keys.append(f"{direction}:{sign}")
            vectors.append(np.mean(selected, axis=0)[:2])
    matrix = np.asarray(vectors, dtype=float).T
    rank = int(np.linalg.matrix_rank(matrix))
    conditions = []
    for left in range(len(keys)):
        for right in range(left + 1, len(keys)):
            pair = matrix[:, [left, right]]
            condition = float(np.linalg.cond(pair)) if np.linalg.matrix_rank(pair) == 2 else math.inf
            conditions.append({"columns": [keys[left], keys[right]], "condition": condition})
    best = min(conditions, key=lambda row: row["condition"])
    vectors_array = np.asarray(vectors, dtype=float)
    gap = _angular_gap(vectors_array)
    samples = stage["scientific_gates"]["directional_support_angle_samples"]
    unit = np.asarray([
        [math.cos(2.0 * math.pi * index / samples), math.sin(2.0 * math.pi * index / samples)]
        for index in range(samples)
    ])
    directional = np.max(unit @ vectors_array.T, axis=1)
    support = float(np.min(directional))
    gates = stage["scientific_gates"]
    signal = all(
        row["peak_persistent_rz_norm_m"] >= gates["minimum_peak_rz_response_norm_m_per_signed_arm"]
        for row in arm_metrics
    )
    ip_ok = all(
        row["maximum_absolute_ip_response_a"] <= gates["maximum_absolute_ip_response_a"]
        for row in arm_metrics
    )
    positive = (
        rank >= gates["minimum_rz_response_rank"]
        and best["condition"] <= gates["maximum_best_pair_condition"]
        and gap <= gates["maximum_angular_gap_deg"]
        and support >= gates["minimum_directional_support_m"]
    )
    return {
        "arm_metrics": arm_metrics,
        "vector_keys": keys,
        "mean_persistent_rz_response_matrix_m": matrix.tolist(),
        "rz_response_rank": rank,
        "pair_conditions": conditions,
        "best_pair": best,
        "maximum_angular_gap_deg": gap,
        "minimum_directional_support_m": support,
        "directional_support_samples": samples,
        "signal_passed": signal,
        "ip_passed": ip_ok,
        "positive_span_passed": positive,
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool, repeatable: bool, metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not repeatable:
        return stage["routes"]["repeatability_fail"]
    assert metrics is not None
    if not (metrics["signal_passed"] and metrics["ip_passed"]):
        return stage["routes"]["signal_or_ip_fail"]
    if not metrics["positive_span_passed"]:
        return stage["routes"]["positive_span_fail"]
    return stage["routes"]["pass"]


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "run output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    gate = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    if not gate["passed"]:
        result = {
            "schema_version": SCHEMA, "source_revision": source_revision,
            "passed": False, "route": gate["route"], "reasons": gate["failures"],
            "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
        }
        write_new(output / "result.json", result)
        return result
    stage, cfg, evidence = load(stage_path)
    if gate["stage_config_sha256"] != sha256(inside_root(stage_path, "stage config")):
        raise InputIntegrityError("stage changed after offline preflight")
    cfg.run_root = output / "rollouts"
    source = _source(cfg)
    streams = targets_and_streams(stage, cfg, evidence, source)
    runtime_stage = dict(stage)
    runtime_stage["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime_stage["empirical_exploration"]["inner_pulse_issue_clearance"] = stage[
        "empirical_exploration"
    ]["inner_probe_issue_clearance"]
    rows = []
    for stream in streams:
        row = one_rollout(cfg, runtime_stage, stream)
        row["schema_version"] = SCHEMA
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    execution = len(rows) == stage["rollouts"] and all(row["passed"] for row in rows)
    inventory = raw_inventory(output, rows, stage)
    raw_ok = (
        execution and not inventory["missing_required_artifacts"]
        and inventory["required_artifact_files"] == stage["completed_required_artifact_files"]
    )
    comparisons = []
    if execution:
        selected = [row for row in rows if row["context_id"] == "baseline"]
        comparisons.append({"pair_id": "q0_baseline", **compare_rows(selected[0], selected[1], stage)})
        for direction in stage["directions"]:
            for sign in stage["signs"]:
                selected = [
                    row for row in rows
                    if row["direction_id"] == direction and row["sign"] == sign
                ]
                comparisons.append({
                    "pair_id": f"late_{direction}_{sign}",
                    **compare_rows(selected[0], selected[1], stage),
                })
    repeatable = execution and all(row["passed"] for row in comparisons)
    metrics = scientific_metrics(rows, stage) if repeatable else None
    route = route_for(stage, execution, raw_ok, repeatable, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": passed, "route": route,
        "execution_passed": execution, "raw_integrity_passed": raw_ok,
        "repeatability_passed": repeatable, "scientific_metrics": metrics,
        "repeatability_comparisons": comparisons, "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "basis_selection_data_eligible": passed,
        "model_fit_data_eligible": False,
        "claim_boundary": "late_q0_persistent_temporal_action_basis_only_not_model_or_control",
    }
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "offline":
        result = offline(args.stage_config.resolve(), args.source_revision)
        write_new(args.output.resolve(), result)
    else:
        result = run(args.stage_config.resolve(), args.source_revision, args.output.resolve())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
