#!/usr/bin/env python3
"""Frozen 1 ms ID2A duration/history-conditioned development campaign."""

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
    compare_rows,
    inside_root,
    one_rollout,
    raw_inventory,
    sha256,
    write_new,
)
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot import (  # noqa: E402
    _target_map as id1a_target_map,
    load as load_id1a,
)
from scripts.rgeo_zgeo_1ms_id1c_persistent_basis_validation import (  # noqa: E402
    _targets as id1c_targets,
    load as load_id1c,
)
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source  # noqa: E402
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (  # noqa: E402
    Card15Target,
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    card15_target_decimal_a,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import RGeoZGeoSignal  # noqa: E402
from tsc_rzip_rllib.core.runner import TSCConfig  # noqa: E402


SCHEMA = "rgeo-zgeo-1ms-id2a-duration-history-development-v1"
CONFIG_SHA256 = "2e2d2fc284203438e57355262241e629f57113e3583557070284c53a8767f52f"
DEFAULT_STAGE = ROOT / "configs/rgeo_zgeo_1ms_id2a_duration_history_development.json"
OFFLINE_PASS = "ONE_MS_ID2A_OFFLINE_PASS_RUN_ONLY"


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": SCHEMA,
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 32,
        "rollouts": 42,
        "maximum_reset_calls": 42,
        "maximum_advance_attempts": 1344,
        "maximum_gotsc_calls": 1344,
        "maximum_verified_plant_advances": 1344,
        "completed_state_count": 1386,
        "completed_required_artifact_files": 6930,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_prospective_empirical_identification",
        "intended_use": "fresh_duration_history_conditioned_primitive_development",
        "development_model_fit_use_after_all_gates_pass": "allowed",
        "calibration_use": "forbidden",
        "holdout_use": "forbidden",
        "expert_oracle_fixture_bc_dagger_rl_use": "forbidden",
        "controller_safety_or_recourse_qualification_use": "forbidden",
        "holdout_records_read": 0,
        "server_tests_and_execution_required": True,
        "local_nontrivial_tests_forbidden": True,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if [(r.get("context_id"), r.get("prefix_id"), r.get("probe_issue_step"), r.get("baseline_repetitions")) for r in stage.get("contexts", [])] != [
        ("late_q0", "q0", 10, 1),
        ("history_p04_plus", "short_p04_plus", 10, 1),
        ("anchor_p03_minus", "cumulative_p03_minus", 10, 1),
    ]:
        raise InputIntegrityError("context matrix mismatch")
    if stage.get("directions") != ["p01", "p09_half_exact_center"]:
        raise InputIntegrityError("direction matrix mismatch")
    if stage.get("signs") != ["plus", "minus"] or stage.get("durations_issues") != [1, 2, 4]:
        raise InputIntegrityError("sign/duration matrix mismatch")
    if stage.get("arm_repetitions") != 1 or stage.get("critical_replays") != [{
        "direction_id": "p09_half_exact_center", "sign": "minus",
        "duration_issues": 4, "additional_repetitions_per_context": 1,
    }]:
        raise InputIntegrityError("repeat matrix mismatch")
    if stage.get("prefix_schedules") != {
        "q0": [],
        "short_p04_plus": [{"first_issue": 6, "last_issue": 6, "target": "p04:plus"}],
        "cumulative_p03_minus": [
            {"first_issue": 1, "last_issue": 1, "target": "p03_anchor_level1"},
            {"first_issue": 2, "last_issue": 6, "target": "p03_anchor_level2"},
            {"first_issue": 7, "last_issue": 7, "target": "p03_anchor_level1"},
        ],
    }:
        raise InputIntegrityError("prefix schedule mismatch")
    action = stage.get("action_semantics", {})
    if action != {
        "unspecified_issues_are_q0": True,
        "all_contexts_active_command_is_q0_before_probe": True,
        "probe_return_target": "exact_q0_on_first_issue_after_duration",
        "effect_state_index": "issue_step_plus_one",
        "maximum_single_turn_adjacent_delta_a": 0.3,
        "maximum_designed_probe_component_a": 0.15,
        "actual_card15_vectors_not_sign_labels": True,
        "signed_pairs_assumed_odd": False,
        "complete_effect_and_tail_states_retained": True,
    }:
        raise InputIntegrityError("action semantics mismatch")
    if stage.get("observability") != {
        "current_same_step_r_geo_z_geo_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_observation_and_owned_action_history": "available",
        "future_successor_before_issue": "unknown",
        "pre_takeover_history": "not_claimed",
        "latent_belief_role": "unobserved_memory_future_response_and_model_mismatch_only",
    }:
        raise InputIntegrityError("observability mismatch")
    exploration = stage.get("empirical_exploration", {})
    if exploration != {
        "novel_duration_context_successors_are_declared_tsc_only_exposures": True,
        "pre_action_transition_tube_claimed": False,
        "post_successor_step_caps": {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0},
        "inner_probe_issue_clearance": {"r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05},
        "outer_hard_envelope": {"r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10},
        "stop_before_next_issue_after_any_failure": True,
    }:
        raise InputIntegrityError("exploration envelope mismatch")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 150000000000,
        "maximum_estimated_raw_bytes": 90000000000,
        "minimum_free_bytes_after_estimate": 50000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate mismatch")
    if stage.get("identifiability_gates") != {
        "virtual_action_coordinates": ["p01", "p09_half_exact_center"],
        "lag_steps": 16,
        "required_lag_block_rank": 32,
        "maximum_lag_block_condition": 100.0,
        "minimum_peak_rz_response_norm_m_per_context_direction_sign": 0.00001,
        "minimum_duration_trajectory_separation_m": 0.000005,
        "maximum_absolute_ip_response_a": 150.0,
        "context_response_difference_is_reported_not_required": True,
        "tail_extinction_is_not_a_gate": True,
    }:
        raise InputIntegrityError("identifiability gate mismatch")
    if stage.get("data_grouping", {}).get("atomic_group") != "complete_prefix_context_family" or stage.get("data_grouping", {}).get("step_level_random_split") != "forbidden":
        raise InputIntegrityError("data grouping mismatch")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("artifact contract mismatch")


def load(stage_path: Path) -> tuple[dict[str, Any], TSCConfig, dict[str, Any]]:
    stage_path = inside_root(stage_path, "stage config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2A config SHA-256 mismatch")
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
    if evidence["id1c_result"].get("route") != "ONE_MS_ID1C_SIGNAL_SYMMETRY_OR_IP_FAIL_REDESIGN" or evidence["id1c_result"].get("model_fit_data_eligible") is not False:
        raise InputIntegrityError("ID1C evidence role mismatch")
    if not evidence["id1c_independent"].get("audit_passed"):
        raise InputIntegrityError("ID1C independent audit mismatch")
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    cfg = TSCConfig.from_json(base)
    validate_one_ms_config(start_folder=cfg.start_folder, dt_ms=cfg.dt_ms, slew_a_per_ms=cfg.current_slew_a_per_ms)
    return stage, cfg, evidence


def rollout_specs(stage: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for context in stage["contexts"]:
        common = {"context_id": context["context_id"], "prefix_id": context["prefix_id"], "pulse_issue_step": context["probe_issue_step"]}
        rows.append({**common, "rollout_id": f"{context['context_id']}_baseline_r0", "is_context_baseline": True, "direction_id": None, "sign": None, "duration_issues": 0, "repeat_index": 0})
        for direction in stage["directions"]:
            for sign in stage["signs"]:
                for duration in stage["durations_issues"]:
                    rows.append({**common, "rollout_id": f"{context['context_id']}_{direction}_{sign}_d{duration}_r0", "is_context_baseline": False, "direction_id": direction, "sign": sign, "duration_issues": duration, "repeat_index": 0})
        rows.append({**common, "rollout_id": f"{context['context_id']}_p09_half_exact_center_minus_d4_r1", "is_context_baseline": False, "direction_id": "p09_half_exact_center", "sign": "minus", "duration_issues": 4, "repeat_index": 1})
    if len(rows) != stage["rollouts"] or len({row["rollout_id"] for row in rows}) != len(rows):
        raise InputIntegrityError(f"rollout matrix mismatch: {len(rows)}")
    return rows


def _targets(stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]) -> dict[str, Card15Target]:
    id1a_stage, id1a_cfg, id1a_evidence = load_id1a(ROOT / stage["evidence"]["id1a_config"]["path"])
    id1c_stage, id1c_cfg, id1c_evidence = load_id1c(ROOT / stage["evidence"]["id1c_config"]["path"])
    if tuple(id1a_cfg.turns_tsc) != tuple(cfg.turns_tsc) or tuple(id1c_cfg.turns_tsc) != tuple(cfg.turns_tsc):
        raise InputIntegrityError("dependency coil geometry mismatch")
    targets = id1a_target_map(id1a_stage, id1a_cfg, id1a_evidence, source)
    selected = id1c_targets(id1c_stage, id1c_cfg, id1c_evidence, source)
    for direction in stage["directions"]:
        for sign in stage["signs"]:
            targets[f"{direction}:{sign}"] = selected[f"{direction}:{sign}"]
    return targets


def targets_and_streams(stage: dict[str, Any], cfg: TSCConfig, source: dict[str, Any]) -> list[dict[str, Any]]:
    targets = _targets(stage, cfg, source)
    streams: list[dict[str, Any]] = []
    for spec in rollout_specs(stage):
        sequence = [targets["q0"]] * stage["horizon_steps"]
        for row in stage["prefix_schedules"][spec["prefix_id"]]:
            for issue in range(row["first_issue"], row["last_issue"] + 1):
                sequence[issue] = targets[row["target"]]
        if not spec["is_context_baseline"]:
            target = targets[f"{spec['direction_id']}:{spec['sign']}"]
            for issue in range(spec["pulse_issue_step"], spec["pulse_issue_step"] + spec["duration_issues"]):
                sequence[issue] = target
        previous = tuple(source["active_command_decimal_a_tsc"])
        actions = []
        for issue, target in enumerate(sequence):
            exact = card15_target_decimal_a(target, cfg.turns_tsc, name=f"id2a.{spec['rollout_id']}.{issue}")
            maximum = assert_exact_slew(previous, exact, name=f"id2a.{spec['rollout_id']}.{issue}")
            if any(value < Decimal(str(low)) or value > Decimal(str(high)) for value, low, high in zip(exact, cfg.min_current_a_tsc, cfg.max_current_a_tsc)):
                raise InputIntegrityError("target leaves absolute current limits")
            active_probe = not spec["is_context_baseline"] and spec["pulse_issue_step"] <= issue < spec["pulse_issue_step"] + spec["duration_issues"]
            virtual = [0.0, 0.0]
            if active_probe:
                virtual[stage["directions"].index(spec["direction_id"])] = 1.0 if spec["sign"] == "plus" else -1.0
            actions.append({
                "issue_step": issue, "issue_time_ms": 1100 + issue,
                "effect_state_index": issue + 1, "effect_time_ms": 1101 + issue,
                "expected_card15_fields": list(target.card15_fields),
                "target_current_a_tsc": list(target.current_a_tsc),
                "maximum_issued_delta_a": maximum,
                "probe_virtual_action": virtual,
                "duration_effect_age": issue - spec["pulse_issue_step"] + 1 if active_probe else None,
            })
            previous = exact
        probe = spec["pulse_issue_step"]
        if sequence[probe - 1].card15_fields != targets["q0"].card15_fields:
            raise InputIntegrityError(f"context not at q0 command before probe: {spec['rollout_id']}")
        if not spec["is_context_baseline"]:
            return_issue = probe + spec["duration_issues"]
            if sequence[return_issue].card15_fields != targets["q0"].card15_fields:
                raise InputIntegrityError("probe return is not exact q0")
        streams.append({**spec, "targets": sequence, "actions": actions})
    return streams


def lag_support(streams: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    lag = stage["identifiability_gates"]["lag_steps"]
    rows = []
    for stream in streams:
        if stream["is_context_baseline"]:
            continue
        values = np.asarray([row["probe_virtual_action"] for row in stream["actions"]], dtype=float)
        for effect_state in range(stream["pulse_issue_step"] + 1, stage["horizon_steps"] + 1):
            feature = []
            for age in range(lag):
                issue = effect_state - 1 - age
                feature.extend(values[issue].tolist() if issue >= 0 else [0.0, 0.0])
            rows.append(feature)
    matrix = np.asarray(rows, dtype=float)
    rank = int(np.linalg.matrix_rank(matrix))
    condition = float(np.linalg.cond(matrix)) if rank == matrix.shape[1] else math.inf
    gates = stage["identifiability_gates"]
    return {"rows": int(matrix.shape[0]), "columns": int(matrix.shape[1]), "rank": rank, "condition": condition, "passed": rank >= gates["required_lag_block_rank"] and condition <= gates["maximum_lag_block_condition"]}


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    stage = source_signal = streams = support = None
    try:
        stage, cfg, _ = load(stage_path)
        source = _source(cfg)
        source_signal = RGeoZGeoSignal.from_tsc_state(source)
        envelope = OneMsNR1SafetyEnvelope.from_signal(source_signal)
        failures.extend(envelope.state_reasons(source_signal, source["currents_a_tsc"], cfg.min_current_a_tsc, cfg.max_current_a_tsc))
        raw = targets_and_streams(stage, cfg, source)
        support = lag_support(raw, stage)
        if not support["passed"]:
            failures.append("VIRTUAL_ACTION_LAG_SUPPORT")
        streams = [{key: value for key, value in row.items() if key != "targets"} for row in raw]
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    failures = list(dict.fromkeys(failures))
    return {
        "schema_version": SCHEMA, "kind": "offline_preflight", "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures, "route": OFFLINE_PASS if not failures else (stage["routes"]["offline_fail"] if stage else "ONE_MS_ID2A_OFFLINE_FAIL_NO_TSC"),
        "failures": failures, "source_signal": None if source_signal is None else source_signal.to_dict(),
        "virtual_action_lag_support": support, "rollout_action_streams": streams,
        "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0,
    }


def scientific_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    gates = stage["identifiability_gates"]
    per_arm = []
    responses: dict[str, np.ndarray] = {}
    for context in (row["context_id"] for row in stage["contexts"]):
        baseline_row = next(row for row in rows if row["context_id"] == context and row["is_context_baseline"])
        baseline = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in baseline_row["states"]], dtype=float)
        for row in rows:
            if row["context_id"] != context or row["is_context_baseline"]:
                continue
            response = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in row["states"]], dtype=float) - baseline
            responses[row["rollout_id"]] = response
            start = row["pulse_issue_step"] + 1
            tail = response[start:]
            per_arm.append({
                "rollout_id": row["rollout_id"], "context_id": context, "direction_id": row["direction_id"],
                "sign": row["sign"], "duration_issues": row["duration_issues"], "repeat_index": row["repeat_index"],
                "peak_rz_response_norm_m": float(np.max(np.linalg.norm(tail[:, :2], axis=1))),
                "maximum_absolute_ip_response_a": float(np.max(np.abs(tail[:, 2]))),
                "terminal_rzi_response": response[-1].tolist(),
            })
    families = []
    for context in (row["context_id"] for row in stage["contexts"]):
        for direction in stage["directions"]:
            for sign in stage["signs"]:
                selected = [row for row in per_arm if row["context_id"] == context and row["direction_id"] == direction and row["sign"] == sign and row["repeat_index"] == 0]
                selected.sort(key=lambda row: row["duration_issues"])
                separations = []
                for left, right in zip(selected, selected[1:]):
                    a = responses[left["rollout_id"]][11:, :2]
                    b = responses[right["rollout_id"]][11:, :2]
                    separations.append({"durations": [left["duration_issues"], right["duration_issues"]], "maximum_rz_trajectory_separation_m": float(np.max(np.linalg.norm(a - b, axis=1)))})
                families.append({
                    "context_id": context, "direction_id": direction, "sign": sign,
                    "peak_rz_response_norm_m": max(row["peak_rz_response_norm_m"] for row in selected),
                    "maximum_absolute_ip_response_a": max(row["maximum_absolute_ip_response_a"] for row in selected),
                    "duration_separations": separations,
                    "signal_passed": max(row["peak_rz_response_norm_m"] for row in selected) >= gates["minimum_peak_rz_response_norm_m_per_context_direction_sign"],
                    "duration_separation_passed": all(row["maximum_rz_trajectory_separation_m"] >= gates["minimum_duration_trajectory_separation_m"] for row in separations),
                    "ip_passed": max(row["maximum_absolute_ip_response_a"] for row in selected) <= gates["maximum_absolute_ip_response_a"],
                })
    return {
        "per_arm": per_arm, "family_metrics": families,
        "signal_passed": all(row["signal_passed"] for row in families),
        "duration_separation_passed": all(row["duration_separation_passed"] for row in families),
        "ip_passed": all(row["ip_passed"] for row in families),
        "context_differences_reported_only": True,
        "tail_extinction_is_not_a_gate": True,
    }


def route_for(stage: dict[str, Any], execution: bool, raw_ok: bool, repeatable: bool, input_support: bool, metrics: dict[str, Any] | None) -> str:
    if not execution:
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if not repeatable:
        return stage["routes"]["repeatability_fail"]
    if not input_support:
        return stage["routes"]["input_support_fail"]
    assert metrics is not None
    if not (metrics["signal_passed"] and metrics["duration_separation_passed"] and metrics["ip_passed"]):
        return stage["routes"]["response_support_or_ip_fail"]
    return stage["routes"]["pass"]


def _storage(stage: dict[str, Any], output: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(output.parent)
    gate = stage["storage_gate"]
    return {
        "free_bytes_before_run": usage.free,
        "estimated_raw_bytes": gate["maximum_estimated_raw_bytes"],
        "estimated_free_bytes_after_run": usage.free - gate["maximum_estimated_raw_bytes"],
        "passed": usage.free >= gate["minimum_free_bytes_before_run"] and usage.free - gate["maximum_estimated_raw_bytes"] >= gate["minimum_free_bytes_after_estimate"],
    }


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "run output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    stage, _, _ = load(stage_path)
    storage = _storage(stage, output)
    if not storage["passed"]:
        output.mkdir(parents=True)
        result = {"schema_version": SCHEMA, "source_revision": source_revision, "passed": False, "route": stage["routes"]["storage_fail"], "reasons": ["STORAGE_PREFLIGHT"], "storage_gate": storage, "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0}
        write_new(output / "result.json", result)
        return result
    output.mkdir(parents=True)
    gate = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    if not gate["passed"]:
        result = {"schema_version": SCHEMA, "source_revision": source_revision, "passed": False, "route": gate["route"], "reasons": gate["failures"], "storage_gate": storage, "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0}
        write_new(output / "result.json", result)
        return result
    stage, cfg, _ = load(stage_path)
    if gate["stage_config_sha256"] != CONFIG_SHA256:
        raise InputIntegrityError("stage changed after offline preflight")
    cfg.run_root = output / "rollouts"
    source = _source(cfg)
    streams = targets_and_streams(stage, cfg, source)
    runtime_stage = dict(stage)
    runtime_stage["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime_stage["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
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
    raw_ok = execution and not inventory["missing_required_artifacts"] and inventory["required_artifact_files"] == stage["completed_required_artifact_files"]
    comparisons = []
    if execution:
        for context in (row["context_id"] for row in stage["contexts"]):
            selected = [row for row in rows if row["context_id"] == context and row["direction_id"] == "p09_half_exact_center" and row["sign"] == "minus" and row["duration_issues"] == 4]
            comparisons.append({"pair_id": f"{context}:p09_minus:d4", **compare_rows(selected[0], selected[1], stage)})
    repeatable = execution and all(row["passed"] for row in comparisons)
    input_support = bool(gate["virtual_action_lag_support"]["passed"])
    metrics = scientific_metrics(rows, stage) if repeatable else None
    route = route_for(stage, execution, raw_ok, repeatable, input_support, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256,
        "passed": passed, "route": route, "execution_passed": execution, "raw_integrity_passed": raw_ok,
        "repeatability_passed": repeatable, "input_support_passed": input_support,
        "virtual_action_lag_support": gate["virtual_action_lag_support"], "scientific_metrics": metrics,
        "repeatability_comparisons": comparisons, "storage_gate": storage, "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows), "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory, "model_fit_data_eligible": passed, "claim_boundary": stage["claim_boundary"],
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
