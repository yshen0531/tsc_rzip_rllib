#!/usr/bin/env python3
"""Prospectively frozen 1 ms ID-1A context/anchor development pilot."""

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


SCHEMA = "rgeo-zgeo-1ms-id1a-context-anchor-pilot-v1"
CONFIG_SHA256 = "883945f8a15ba1d9aabe037fde6e51ba420cb7a59ba792df1064611b3ba196bf"
DEFAULT_STAGE = ROOT / "configs/rgeo_zgeo_1ms_id1a_context_anchor_pilot.json"
OFFLINE_PASS = "ONE_MS_ID1A_OFFLINE_PASS_RUN_ONLY"


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": SCHEMA,
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 24,
        "rollouts": 32,
        "maximum_reset_calls": 32,
        "maximum_advance_attempts": 768,
        "maximum_gotsc_calls": 768,
        "maximum_verified_plant_advances": 768,
        "completed_state_count": 800,
        "completed_required_artifact_files": 4000,
        "retry_after_any_advance_attempt": "forbidden",
        "holdout_records_read": 0,
        "non_q0_context_baseline_repetitions": 1,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("development_use_after_all_gates_pass") != "allowed_for_structure_and_anchor_design_only":
        raise InputIntegrityError("development-use contract mismatch")
    for key in (
        "calibration_use",
        "holdout_use",
        "expert_oracle_fixture_bc_dagger_rl_use",
        "controller_safety_or_recourse_qualification_use",
    ):
        if stage.get(key) != "forbidden":
            raise InputIntegrityError(f"forbidden data-use mismatch: {key}")
    if stage.get("probe_directions") != ["p03", "p07"] or stage.get("probe_signs") != ["plus", "minus"]:
        raise InputIntegrityError("probe basis mismatch")
    if [row.get("context_id") for row in stage.get("contexts", [])] != [
        "early_q0",
        "late_q0",
        "history_p04_plus",
        "history_p04_minus",
        "anchor_p03_minus",
        "anchor_p07_plus",
    ]:
        raise InputIntegrityError("context matrix mismatch")
    if stage.get("semantic_artifacts") != [
        "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"
    ] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("artifact contract mismatch")
    action = stage.get("action_semantics", {})
    if action.get("effect_state_index") != "issue_step_plus_one":
        raise InputIntegrityError("effect clock mismatch")
    if action.get("maximum_single_turn_adjacent_delta_a") != 0.3 or not action.get("full_limit_allowed"):
        raise InputIntegrityError("slew contract mismatch")
    exploration = stage.get("empirical_exploration", {})
    if exploration.get("pre_action_transition_tube_claimed") is not False:
        raise InputIntegrityError("empirical stage may not claim a transition tube")
    if exploration.get("post_successor_step_caps") != {
        "r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0
    } or exploration.get("outer_hard_envelope") != {
        "r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10
    }:
        raise InputIntegrityError("exploration envelope mismatch")
    expected_routes = {
        "offline_fail": "ONE_MS_ID1A_OFFLINE_FAIL_NO_TSC",
        "package_or_deployment_fail": "ONE_MS_ID1A_PACKAGE_OR_DEPLOYMENT_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID1A_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID1A_RAW_INTEGRITY_FAIL_STOP",
        "repeatability_fail": "ONE_MS_ID1A_REPEATABILITY_FAIL_REDESIGN",
        "signal_or_vector_fail": "ONE_MS_ID1A_SIGNAL_OR_VECTOR_FAIL_REDESIGN",
        "history_contrast_fail": "ONE_MS_ID1A_HISTORY_CONTRAST_FAIL_REDESIGN",
        "anchor_contrast_fail": "ONE_MS_ID1A_ANCHOR_CONTRAST_FAIL_REDESIGN",
        "pass": "ONE_MS_ID1A_CONTEXT_ANCHOR_DEVELOPMENT_PASS_MODEL_DESIGN_ONLY",
    }
    if stage.get("routes") != expected_routes:
        raise InputIntegrityError("route contract mismatch")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    stage_path = inside_root(stage_path, "stage config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID1A config SHA-256 mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    evidence_documents: dict[str, Any] = {}
    for label, row in stage["evidence"].items():
        if label == "base_tsc_config_sha256":
            continue
        path = inside_root(ROOT / row["path"], label)
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"{label} hash mismatch")
        evidence_documents[label] = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else None
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(
        start_folder=cfg.start_folder,
        dt_ms=cfg.dt_ms,
        slew_a_per_ms=cfg.current_slew_a_per_ms,
    )
    return stage, cfg, evidence_documents


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "rollout_id": f"q0_baseline_r{repeat}",
            "context_id": "q0_baseline",
            "prefix_id": "q0",
            "is_context_baseline": True,
            "direction_id": None,
            "sign": None,
            "repeat_index": repeat,
            "pulse_issue_step": None,
        }
        for repeat in range(stage["baseline"]["repetitions"])
    ]
    non_q0 = [row for row in stage["contexts"] if row["prefix_id"] != "q0"]
    for context in non_q0:
        rows.append(
            {
                "rollout_id": f"{context['context_id']}_baseline_r0",
                "context_id": context["context_id"],
                "prefix_id": context["prefix_id"],
                "is_context_baseline": True,
                "direction_id": None,
                "sign": None,
                "repeat_index": 0,
                "pulse_issue_step": context["probe_issue_step"],
            }
        )
    for context in stage["contexts"]:
        for direction in stage["probe_directions"]:
            for sign in stage["probe_signs"]:
                key = f"{direction}:{sign}"
                for repeat in range(context["repetitions"][key]):
                    rows.append(
                        {
                            "rollout_id": f"{context['context_id']}_{direction}_{sign}_r{repeat}",
                            "context_id": context["context_id"],
                            "prefix_id": context["prefix_id"],
                            "is_context_baseline": False,
                            "direction_id": direction,
                            "sign": sign,
                            "repeat_index": repeat,
                            "pulse_issue_step": context["probe_issue_step"],
                        }
                    )
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError(f"rollout matrix mismatch: {len(rows)}")
    return rows


def _target_map(
    stage: dict[str, Any], cfg: TSCConfig, evidence: dict[str, Any], source: dict[str, Any]
) -> dict[str, Card15Target]:
    frozen = build_frozen_one_ms_prefixes(
        source_current_a_tsc=source["currents_a_tsc"],
        turns_tsc=cfg.turns_tsc,
        min_current_a_tsc=cfg.min_current_a_tsc,
        max_current_a_tsc=cfg.max_current_a_tsc,
    )
    targets: dict[str, Card15Target] = {"q0": frozen.q0}
    id0 = evidence["id0_direction_config"]
    for row in id0["directions"]:
        for sign in ("plus", "minus"):
            targets[f"{row['direction_id']}:{sign}"] = target_from_fields(
                row[f"{sign}_card15_fields"], cfg, f"id1a.{row['direction_id']}.{sign}"
            )
    p03 = evidence["p03_anchor_config"]
    p07 = evidence["p07_anchor_config"]
    targets["p03_anchor_level1"] = target_from_fields(p03["level1_card15_fields"], cfg, "id1a.p03.level1")
    targets["p03_anchor_level2"] = target_from_fields(p03["level2_card15_fields"], cfg, "id1a.p03.level2")
    targets["p07_anchor_level1"] = target_from_fields(p07["level1_card15_fields"], cfg, "id1a.p07.level1")
    targets["p07_anchor_level2"] = target_from_fields(p07["level2_card15_fields"], cfg, "id1a.p07.level2")
    return targets


def targets_and_streams(
    stage: dict[str, Any], cfg: TSCConfig, evidence: dict[str, Any], source: dict[str, Any]
) -> list[dict[str, Any]]:
    targets = _target_map(stage, cfg, evidence, source)
    streams: list[dict[str, Any]] = []
    for spec in rollout_specs(stage):
        sequence = [targets["q0"]] * stage["horizon_steps"]
        for row in stage["prefix_schedules"][spec["prefix_id"]]:
            for issue in range(row["first_issue"], row["last_issue"] + 1):
                sequence[issue] = targets[row["target"]]
        if not spec["is_context_baseline"] and spec["direction_id"] is not None:
            sequence[spec["pulse_issue_step"]] = targets[f"{spec['direction_id']}:{spec['sign']}"]
        previous = tuple(source["active_command_decimal_a_tsc"])
        actions = []
        for issue, target in enumerate(sequence):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"id1a.{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(previous, exact, name=f"id1a.{spec['rollout_id']}.{issue}")
            if any(
                value < Decimal(str(low)) or value > Decimal(str(high))
                for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)
            ):
                raise InputIntegrityError("target leaves absolute current limits")
            actions.append(
                {
                    "issue_step": issue,
                    "issue_time_ms": 1100 + issue,
                    "effect_state_index": issue + 1,
                    "effect_time_ms": 1101 + issue,
                    "expected_card15_fields": list(target.card15_fields),
                    "target_current_a_tsc": list(target.current_a_tsc),
                    "maximum_issued_delta_a": maximum,
                }
            )
            previous = exact
        if spec["prefix_id"] != "q0":
            probe = int(spec["pulse_issue_step"])
            if sequence[probe - 1].card15_fields != targets["q0"].card15_fields:
                raise InputIntegrityError(f"context does not return to q0 before probe: {spec['rollout_id']}")
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
        failures.extend(
            envelope.state_reasons(
                source_signal,
                source["currents_a_tsc"],
                cfg.min_current_a_tsc,
                cfg.max_current_a_tsc,
            )
        )
        raw = targets_and_streams(stage, cfg, evidence, source)
        streams = [{key: value for key, value in row.items() if key != "targets"} for row in raw]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures,
        "route": OFFLINE_PASS if not failures else (
            stage["routes"]["offline_fail"] if stage else "ONE_MS_ID1A_OFFLINE_FAIL_NO_TSC"
        ),
        "failures": failures,
        "source_signal": None if source_signal is None else source_signal.to_dict(),
        "rollout_action_streams": streams,
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0,
    }


def _mean_baseline(rows: Sequence[dict[str, Any]]) -> list[dict[str, float]]:
    if not rows:
        raise ValueError("missing matched baseline")
    return [
        {
            key: float(np.mean([row["states"][index][key] for row in rows]))
            for key in ("r_geo_m", "z_geo_m", "ip_a")
        }
        for index in range(len(rows[0]["states"]))
    ]


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    q0_baselines = [row for row in rows if row["context_id"] == "q0_baseline"]
    q0 = _mean_baseline(q0_baselines)
    context_baselines: dict[str, list[dict[str, float]]] = {}
    for context in stage["contexts"]:
        if context["prefix_id"] == "q0":
            context_baselines[context["context_id"]] = q0
        else:
            selected = [
                row for row in rows
                if row["context_id"] == context["context_id"] and row["is_context_baseline"]
            ]
            context_baselines[context["context_id"]] = _mean_baseline(selected)

    probes = [row for row in rows if not row["is_context_baseline"]]
    arm_metrics = []
    for row in probes:
        baseline = context_baselines[row["context_id"]]
        response = np.asarray(
            [
                [
                    state["r_geo_m"] - base["r_geo_m"],
                    state["z_geo_m"] - base["z_geo_m"],
                    state["ip_a"] - base["ip_a"],
                ]
                for state, base in zip(row["states"], baseline)
            ],
            dtype=float,
        )
        effect = int(row["pulse_issue_step"]) + 1
        mean = np.mean(response[effect : effect + 4], axis=0)
        tail = response[effect:]
        arm_metrics.append(
            {
                "rollout_id": row["rollout_id"],
                "context_id": row["context_id"],
                "direction_id": row["direction_id"],
                "sign": row["sign"],
                "repeat_index": row["repeat_index"],
                "effect_state_index": effect,
                "mean_effect_age_1_4": mean.tolist(),
                "peak_rz_norm_m": float(np.max(np.linalg.norm(tail[:, :2], axis=1))),
                "maximum_absolute_ip_response_a": float(np.max(np.abs(tail[:, 2]))),
            }
        )

    context_vectors: dict[str, Any] = {}
    vector_passed = True
    for context in stage["contexts"]:
        vectors = []
        keys = []
        for direction in stage["probe_directions"]:
            for sign in stage["probe_signs"]:
                selected = [
                    row["mean_effect_age_1_4"]
                    for row in arm_metrics
                    if row["context_id"] == context["context_id"]
                    and row["direction_id"] == direction
                    and row["sign"] == sign
                ]
                vectors.append(np.mean(selected, axis=0)[:2])
                keys.append(f"{direction}:{sign}")
        matrix = np.asarray(vectors, dtype=float).T
        rank = int(np.linalg.matrix_rank(matrix))
        pairs = []
        for left in range(4):
            for right in range(left + 1, 4):
                pair = matrix[:, [left, right]]
                condition = float(np.linalg.cond(pair)) if np.linalg.matrix_rank(pair) == 2 else math.inf
                pairs.append({"columns": [keys[left], keys[right]], "condition": condition})
        best = min(pairs, key=lambda item: item["condition"])
        passed = (
            rank >= stage["scientific_gates"]["minimum_rz_response_rank_per_context"]
            and best["condition"] <= stage["scientific_gates"]["maximum_best_pair_condition_per_context"]
        )
        vector_passed = vector_passed and passed
        context_vectors[context["context_id"]] = {
            "keys": keys,
            "mean_rz_response_matrix_m": matrix.tolist(),
            "rank": rank,
            "best_pair": best,
            "passed": passed,
        }

    def mean_arm(context_id: str, direction: str, sign: str) -> np.ndarray:
        selected = [
            row["mean_effect_age_1_4"]
            for row in arm_metrics
            if row["context_id"] == context_id
            and row["direction_id"] == direction
            and row["sign"] == sign
        ]
        return np.mean(selected, axis=0)

    context_contrasts = {}
    history_passed = True
    anchor_passed = True
    late_preprobe = np.asarray([q0[10]["r_geo_m"], q0[10]["z_geo_m"], q0[10]["ip_a"]])
    for context in stage["contexts"]:
        context_id = context["context_id"]
        if context_id in ("early_q0", "late_q0"):
            continue
        baseline = context_baselines[context_id]
        current = np.asarray([baseline[10]["r_geo_m"], baseline[10]["z_geo_m"], baseline[10]["ip_a"]])
        preprobe_rz = float(np.linalg.norm(current[:2] - late_preprobe[:2]))
        preprobe_ip = float(abs(current[2] - late_preprobe[2]))
        response_differences = {}
        for direction in stage["probe_directions"]:
            for sign in stage["probe_signs"]:
                delta = mean_arm(context_id, direction, sign) - mean_arm("late_q0", direction, sign)
                response_differences[f"{direction}:{sign}"] = {
                    "rz_norm_m": float(np.linalg.norm(delta[:2])),
                    "ip_a": float(delta[2]),
                }
        maximum = max(item["rz_norm_m"] for item in response_differences.values())
        if context_id.startswith("history_"):
            passed = (
                preprobe_rz <= stage["scientific_gates"]["history_preprobe_maximum_rz_distance_from_late_q0_m"]
                and preprobe_ip <= stage["scientific_gates"]["history_preprobe_maximum_ip_distance_from_late_q0_a"]
                and maximum >= stage["scientific_gates"]["minimum_history_conditioned_response_difference_m"]
            )
            history_passed = history_passed and passed
        else:
            passed = (
                preprobe_rz >= stage["scientific_gates"]["minimum_anchor_preprobe_rz_distance_from_late_q0_m"]
                and maximum >= stage["scientific_gates"]["minimum_anchor_conditioned_response_difference_m"]
            )
            anchor_passed = anchor_passed and passed
        context_contrasts[context_id] = {
            "preprobe_rz_distance_from_late_q0_m": preprobe_rz,
            "preprobe_ip_distance_from_late_q0_a": preprobe_ip,
            "response_differences_from_late_q0": response_differences,
            "maximum_rz_response_difference_m": maximum,
            "passed": passed,
        }

    time_contrasts = {}
    for direction in stage["probe_directions"]:
        for sign in stage["probe_signs"]:
            delta = mean_arm("late_q0", direction, sign) - mean_arm("early_q0", direction, sign)
            time_contrasts[f"{direction}:{sign}"] = {
                "rz_norm_m": float(np.linalg.norm(delta[:2])),
                "ip_a": float(delta[2]),
            }
    gates = stage["scientific_gates"]
    signal_passed = all(row["peak_rz_norm_m"] >= gates["minimum_peak_rz_response_norm_m_per_arm"] for row in arm_metrics)
    ip_passed = all(row["maximum_absolute_ip_response_a"] <= gates["maximum_absolute_ip_response_a"] for row in arm_metrics)
    return {
        "arm_metrics": arm_metrics,
        "context_vector_geometry": context_vectors,
        "context_contrasts": context_contrasts,
        "time_contrasts_reported_only": time_contrasts,
        "signal_passed": signal_passed,
        "ip_passed": ip_passed,
        "vector_geometry_passed": vector_passed,
        "history_contrast_passed": history_passed,
        "anchor_contrast_passed": anchor_passed,
    }


def route_for(
    stage: dict[str, Any], execution: bool, raw_ok: bool, repeatable: bool, metrics: dict[str, Any] | None
) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not repeatable:
        return stage["routes"]["repeatability_fail"]
    assert metrics is not None
    if not (metrics["signal_passed"] and metrics["ip_passed"] and metrics["vector_geometry_passed"]):
        return stage["routes"]["signal_or_vector_fail"]
    if not metrics["history_contrast_passed"]:
        return stage["routes"]["history_contrast_fail"]
    if not metrics["anchor_contrast_passed"]:
        return stage["routes"]["anchor_contrast_fail"]
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
            "schema_version": SCHEMA,
            "source_revision": source_revision,
            "passed": False,
            "route": gate["route"],
            "reasons": gate["failures"],
            "rollouts_completed": 0,
            "reset_calls": 0,
            "advance_attempts": 0,
            "plant_advance_gotsc_calls": 0,
            "verified_plant_advances": 0,
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
        execution
        and not inventory["missing_required_artifacts"]
        and inventory["required_artifact_files"] == stage["completed_required_artifact_files"]
    )
    comparisons = []
    if execution:
        q0 = [row for row in rows if row["context_id"] == "q0_baseline"]
        comparisons.append({"pair_id": "q0_baseline", **compare_rows(q0[0], q0[1], stage)})
        for direction, sign in (("p03", "plus"), ("p07", "minus")):
            selected = [
                row for row in rows
                if row["context_id"] == "late_q0"
                and row["direction_id"] == direction
                and row["sign"] == sign
            ]
            comparisons.append(
                {"pair_id": f"late_q0_{direction}_{sign}", **compare_rows(selected[0], selected[1], stage)}
            )
    repeatable = execution and all(row["passed"] for row in comparisons)
    metrics = scientific_metrics(rows, stage) if repeatable else None
    route = route_for(stage, execution, raw_ok, repeatable, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "execution_passed": execution,
        "raw_integrity_passed": raw_ok,
        "repeatability_passed": repeatable,
        "scientific_metrics": metrics,
        "repeatability_comparisons": comparisons,
        "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "development_data_eligible": passed,
        "claim_boundary": "small_hfs_tsc_identification_development_only_not_calibration_holdout_or_control",
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
