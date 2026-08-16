#!/usr/bin/env python3
"""Run the bounded ID-2C1 active-nominal and residual-vector search."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError,
    inside_root,
    one_rollout,
    raw_inventory,
    sha256,
    write_new,
)
from scripts.rgeo_zgeo_1ms_id2a_duration_history_development import (  # noqa: E402
    _targets as id2a_targets,
    load as load_id2a,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from scripts.rgeo_zgeo_1ms_nr2r2c2aa1_authority import target_from_fields  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target,
    assert_exact_slew,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.core.inputa import format_number  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2c1-active-nominal-vector-search-result-v1"
CONFIG_SHA256 = "955c5e69664f955b315bac6cbad559e55eb04bf0abea59295ef60041e5982547"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.json"


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2c1-active-nominal-vector-search-v1",
        "stage_id": "rgeo_zgeo_1ms_id2c1_active_nominal_vector_search_v1",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 32,
        "maximum_rollouts": 11,
        "maximum_reset_calls": 11,
        "maximum_advance_attempts": 352,
        "maximum_gotsc_calls": 352,
        "maximum_verified_plant_advances": 352,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_prospective_empirical_development_search",
        "model_fit_use": "forbidden_until_separate_postcampaign_design",
        "calibration_use": "forbidden",
        "holdout_use": "forbidden",
        "expert_oracle_fixture_bc_dagger_rl_use": "forbidden",
        "controller_safety_or_recourse_qualification_use": "forbidden",
        "holdout_records_read": 0,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    phase_a = stage.get("phase_a", {})
    expected_issues = [
        [],
        [1, 5, 9, 13, 17, 21, 25, 29],
        list(range(1, 32, 2)),
        list(range(1, 32)),
    ]
    if [row.get("p03_minus_increment_issues") for row in phase_a.get("candidates_in_order", [])] != expected_issues:
        raise InputIntegrityError("phase-A candidate matrix mismatch")
    if phase_a.get("minimum_terminal_rz_norm_reduction_fraction_vs_fresh_q0") != 0.20:
        raise InputIntegrityError("phase-A selection gate mismatch")
    phase_b = stage.get("phase_b", {})
    if phase_b.get("probe_issue_step") != 16 or phase_b.get("probe_duration_issues") != 1:
        raise InputIntegrityError("phase-B issue contract mismatch")
    if phase_b.get("directions") != ["p04", "p07", "p09_half_exact_center"] or phase_b.get("signs") != ["plus", "minus"]:
        raise InputIntegrityError("phase-B vector family mismatch")
    if phase_b.get("baseline") != "selected_nominal_prefix_through_issue15_then_held_level":
        raise InputIntegrityError("phase-B baseline mismatch")
    action = stage.get("action_semantics", {})
    if action.get("maximum_single_turn_adjacent_delta_a") != 0.3 or action.get("full_0p3_a_may_be_used") is not True:
        raise InputIntegrityError("action slew contract mismatch")
    if action.get("effect_state_index") != "issue_step_plus_one" or action.get("runner_clipping_must_not_be_triggered_or_relied_on") is not True:
        raise InputIntegrityError("action/effect contract mismatch")
    exploration = stage.get("empirical_exploration", {})
    if exploration.get("pre_action_transition_tube_claimed") is not False or exploration.get("post_action_abort_is_not_a_pre_action_bound") is not True:
        raise InputIntegrityError("empirical exploration claim changed")
    if exploration.get("post_successor_step_caps") != {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0}:
        raise InputIntegrityError("empirical step cap changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 150000000000,
        "maximum_estimated_raw_bytes": 30000000000,
        "minimum_free_bytes_after_estimate": 100000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate mismatch")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any], dict[str, Card15Target]]:
    stage_path = inside_root(stage_path, "ID2C1 config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2C1 config hash mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    compact_row = stage["evidence"]["id2c0_compact"]
    compact_path = inside_root(ROOT / compact_row["path"], "ID2C0 compact")
    if sha256(compact_path) != compact_row["sha256"]:
        raise InputIntegrityError("ID2C0 compact hash mismatch")
    compact = json.loads(compact_path.read_text(encoding="utf-8"))
    if compact.get("passed") is not True or compact.get("independent_audit_passed") is not True:
        raise InputIntegrityError("ID2C0 did not pass")
    id2a_row = stage["evidence"]["id2a_config"]
    id2a_path = inside_root(ROOT / id2a_row["path"], "ID2A config")
    if sha256(id2a_path) != id2a_row["sha256"]:
        raise InputIntegrityError("ID2A config hash mismatch")
    id2a_stage, id2a_cfg, _ = load_id2a(id2a_path)
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms, slew_a_per_ms=cfg.current_slew_a_per_ms)
    if tuple(cfg.turns_tsc) != tuple(id2a_cfg.turns_tsc):
        raise InputIntegrityError("ID2A/base coil geometry mismatch")
    source = _source(cfg)
    targets = id2a_targets(id2a_stage, cfg, source)
    return stage, cfg, source, targets


def _offset_target(q0: Card15Target, direction: Card15Target, multiplier: int, cfg: TSCConfig, name: str) -> Card15Target:
    if multiplier < 0:
        raise InputIntegrityError("negative target multiplier")
    fields = []
    for q0_field, direction_field in zip(q0.card15_fields, direction.card15_fields):
        q0_value = Decimal(q0_field.strip())
        delta = Decimal(direction_field.strip()) - q0_value
        fields.append(format_number(float(q0_value + Decimal(multiplier) * delta)))
    return target_from_fields(fields, cfg, name)


def _translated_target(base: Card15Target, q0: Card15Target, residual: Card15Target, cfg: TSCConfig, name: str) -> Card15Target:
    fields = []
    for base_field, q0_field, residual_field in zip(base.card15_fields, q0.card15_fields, residual.card15_fields):
        value = Decimal(base_field.strip()) + Decimal(residual_field.strip()) - Decimal(q0_field.strip())
        fields.append(format_number(float(value)))
    return target_from_fields(fields, cfg, name)


def _actions(sequence: Sequence[Card15Target], cfg: TSCConfig, rollout_id: str, virtual: Sequence[Sequence[float]]) -> list[dict[str, Any]]:
    previous = card15_target_decimal_a(sequence[0], cfg.turns_tsc, name=f"{rollout_id}.target0")
    actions = []
    for issue, target in enumerate(sequence):
        exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"{rollout_id}.{issue}")
        maximum = assert_exact_slew(previous, exact, name=f"{rollout_id}.{issue}") if issue else 0.0
        if any(value < Decimal(str(low)) or value > Decimal(str(high)) for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
            raise InputIntegrityError(f"absolute current limit: {rollout_id}:{issue}")
        actions.append({
            "issue_step": issue,
            "issue_time_ms": 1100 + issue,
            "effect_state_index": issue + 1,
            "effect_time_ms": 1101 + issue,
            "expected_card15_fields": list(target.card15_fields),
            "target_current_a_tsc": list(target.current_a_tsc),
            "maximum_issued_delta_a": maximum,
            "probe_virtual_action": list(virtual[issue]),
        })
        previous = exact
    return actions


def phase_a_streams(stage: dict[str, Any], cfg: TSCConfig, targets: dict[str, Card15Target]) -> list[dict[str, Any]]:
    q0 = targets["q0"]
    p03 = targets["p03:minus"]
    rows = []
    for spec in stage["phase_a"]["candidates_in_order"]:
        level = 0
        sequence = []
        virtual = []
        increments = set(spec["p03_minus_increment_issues"])
        for issue in range(stage["horizon_steps"]):
            if issue in increments:
                level += 1
            sequence.append(_offset_target(q0, p03, level, cfg, f"{spec['candidate_id']}.level{level}"))
            virtual.append([float(level), 0.0, 0.0, 0.0])
        rows.append({
            "rollout_id": spec["candidate_id"],
            "phase": "A",
            "candidate_id": spec["candidate_id"],
            "pulse_issue_step": 1,
            "p03_minus_increment_issues": list(spec["p03_minus_increment_issues"]),
            "targets": sequence,
            "actions": _actions(sequence, cfg, spec["candidate_id"], virtual),
        })
    return rows


def phase_b_streams(
    stage: dict[str, Any], cfg: TSCConfig, targets: dict[str, Card15Target], selected: dict[str, Any]
) -> list[dict[str, Any]]:
    phase_a_targets = selected["targets"]
    held = phase_a_targets[15]
    base_sequence = list(phase_a_targets[:16]) + [held] * 16
    specs: list[tuple[str, str | None, str | None]] = [("selected_nominal_probe_baseline", None, None)]
    specs.extend((f"selected_nominal_{direction}_{sign}", direction, sign) for direction in stage["phase_b"]["directions"] for sign in stage["phase_b"]["signs"])
    rows = []
    for rollout_id, direction, sign in specs:
        sequence = list(base_sequence)
        virtual = [[0.0, 0.0, 0.0, 0.0] for _ in sequence]
        if direction is not None and sign is not None:
            residual = targets[f"{direction}:{sign}"]
            sequence[16] = _translated_target(held, targets["q0"], residual, cfg, f"{rollout_id}.probe")
            virtual[16][{"p04": 1, "p07": 2, "p09_half_exact_center": 3}[direction]] = 1.0 if sign == "plus" else -1.0
        rows.append({
            "rollout_id": rollout_id,
            "phase": "B",
            "candidate_id": selected["candidate_id"],
            "direction_id": direction,
            "sign": sign,
            "pulse_issue_step": 16,
            "targets": sequence,
            "actions": _actions(sequence, cfg, rollout_id, virtual),
        })
    return rows


def _phase_a_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    if not rows or rows[0]["candidate_id"] != "fresh_q0_baseline" or not rows[0]["passed"]:
        return [], None
    source = rows[0]["states"][0]
    baseline_terminal = rows[0]["states"][-1]
    baseline_norm = math.hypot(
        baseline_terminal["r_geo_m"] - source["r_geo_m"], baseline_terminal["z_geo_m"] - source["z_geo_m"]
    )
    metrics = []
    for row in rows:
        if not row["passed"]:
            metrics.append({"candidate_id": row["candidate_id"], "complete": False, "reasons": row["reasons"]})
            continue
        terminal = row["states"][-1]
        norm = math.hypot(terminal["r_geo_m"] - source["r_geo_m"], terminal["z_geo_m"] - source["z_geo_m"])
        metrics.append({
            "candidate_id": row["candidate_id"],
            "complete": True,
            "terminal_source_rz_norm_m": norm,
            "terminal_rz_norm_reduction_fraction_vs_q0": 1.0 - norm / baseline_norm,
            "maximum_absolute_ip_from_source_a": max(abs(state["ip_a"] - source["ip_a"]) for state in row["states"]),
        })
    eligible = [
        value for value in metrics
        if value["candidate_id"] != "fresh_q0_baseline" and value["complete"]
        and value["terminal_rz_norm_reduction_fraction_vs_q0"] >= stage["phase_a"]["minimum_terminal_rz_norm_reduction_fraction_vs_fresh_q0"]
        and value["maximum_absolute_ip_from_source_a"] <= stage["phase_a"]["maximum_absolute_ip_from_source_a_for_selection"]
    ]
    selected = min(eligible, key=lambda value: value["terminal_source_rz_norm_m"])["candidate_id"] if eligible else None
    return metrics, selected


def _phase_b_metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    if len(rows) != 7 or not all(row["passed"] for row in rows):
        return None
    baseline = rows[0]
    base = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in baseline["states"]], dtype=float)
    arms = []
    vectors = []
    for row in rows[1:]:
        values = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in row["states"]], dtype=float)
        response = values - base
        window = response[17:]
        norms = np.linalg.norm(window[:, :2], axis=1)
        peak = int(np.argmax(norms))
        vectors.append(window[peak, :2])
        arms.append({
            "direction_id": row["direction_id"],
            "sign": row["sign"],
            "peak_state_index": 17 + peak,
            "peak_rz_response_norm_m": float(norms[peak]),
            "peak_rz_response_m": window[peak, :2].tolist(),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rzi_response": response[-1].tolist(),
        })
    matrix = np.asarray(vectors, dtype=float).T
    conditions = []
    for left in range(matrix.shape[1]):
        for right in range(left + 1, matrix.shape[1]):
            pair = matrix[:, [left, right]]
            if np.linalg.matrix_rank(pair) == 2:
                conditions.append(float(np.linalg.cond(pair)))
    return {
        "arm_metrics": arms,
        "descriptive_peak_rz_rank": int(np.linalg.matrix_rank(matrix)),
        "best_descriptive_pair_condition": min(conditions) if conditions else math.inf,
        "positive_span_or_superposition_claimed": False,
        "p09_pooled_as_smooth_gain": False,
    }


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    streams = []
    try:
        stage, cfg, _, targets = load(stage_path)
        streams = phase_a_streams(stage, cfg, targets)
        # Build a representative phase-B family from stride4 to validate translated Card15 actions.
        phase_b = phase_b_streams(stage, cfg, targets, streams[1])
        if len(streams) != 4 or len(phase_b) != 7:
            raise InputIntegrityError("stream budget mismatch")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures,
        "failures": failures,
        "phase_a_action_streams": [{k: v for k, v in row.items() if k != "targets"} for row in streams],
        "reset_calls": 0,
        "advance_attempts": 0,
        "plant_advance_gotsc_calls": 0,
        "verified_plant_advances": 0,
    }


def _storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(output.parent)
    gate = stage["storage_gate"]
    return {
        "free_bytes_before_run": usage.free,
        "estimated_raw_bytes": gate["maximum_estimated_raw_bytes"],
        "estimated_free_bytes_after_run": usage.free - gate["maximum_estimated_raw_bytes"],
        "passed": usage.free >= gate["minimum_free_bytes_before_run"] and usage.free - gate["maximum_estimated_raw_bytes"] >= gate["minimum_free_bytes_after_estimate"],
    }


def _interface_failure(row: dict[str, Any]) -> bool:
    empirical = ("EMPIRICAL_STEP_R", "EMPIRICAL_STEP_Z", "EMPIRICAL_STEP_IP", "OUTER_R", "OUTER_Z", "OUTER_IP")
    return any(not reason.startswith(empirical) for reason in row["reasons"])


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2C1 output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    stage, cfg, _, targets = load(stage_path)
    storage = _storage(stage, output)
    output.mkdir(parents=True)
    gate = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    if not storage["passed"] or not gate["passed"]:
        route = stage["routes"]["storage_fail"] if not storage["passed"] else stage["routes"]["offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route, "reasons": gate["failures"], "storage_gate": storage, "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime_stage = dict(stage)
    runtime_stage["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime_stage["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    rows = []
    phase_a_defs = phase_a_streams(stage, cfg, targets)
    for stream in phase_a_defs:
        row = one_rollout(cfg, runtime_stage, stream)
        row["schema_version"] = SCHEMA
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    phase_a_metrics, selected_id = _phase_a_metrics(rows, stage)
    selected_stream = next((row for row in phase_a_defs if row["candidate_id"] == selected_id), None)
    phase_b_rows = []
    if selected_stream is not None and all(row["passed"] for row in rows):
        for stream in phase_b_streams(stage, cfg, targets, selected_stream):
            row = one_rollout(cfg, runtime_stage, stream)
            row["schema_version"] = SCHEMA
            row["source_revision"] = source_revision
            phase_b_rows.append(row)
            rows.append(row)
            write_new(output / f"{row['rollout_id']}.json", row)
            if not row["passed"]:
                break
    inventory = raw_inventory(output, rows, stage)
    raw_ok = not inventory["missing_required_artifacts"]
    phase_b_metrics = _phase_b_metrics(phase_b_rows)
    if any(_interface_failure(row) for row in rows if not row["passed"]):
        route = stage["routes"]["execution_or_interface_fail"]
    elif not raw_ok:
        route = stage["routes"]["raw_integrity_fail"]
    elif selected_id is None:
        route = stage["routes"]["phase_a_authority_insufficient"]
    elif phase_b_metrics is None:
        route = stage["routes"]["phase_b_vector_incomplete"]
    else:
        route = stage["routes"]["pass"]
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage,
        "phase_a_metrics": phase_a_metrics,
        "selected_nominal_candidate_id": selected_id,
        "phase_b_metrics": phase_b_metrics,
        "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "model_fit_data_eligible": False,
        "postcampaign_design_analysis_eligible": raw_ok and not any(_interface_failure(row) for row in rows if not row["passed"]),
        "holdout_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    write_new(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("offline", "run"))
    parser.add_argument("--stage-config", type=Path, default=DEFAULT_CONFIG)
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
