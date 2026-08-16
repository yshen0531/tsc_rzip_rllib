#!/usr/bin/env python3
"""Run ID-2D1R1 active-nominal duration/time development TSC campaign."""

from __future__ import annotations

import argparse
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
from scripts.rgeo_zgeo_1ms_id2c1_active_nominal_vector_search import (  # noqa: E402
    _actions,
    _translated_target,
    load as load_id2c1,
    phase_a_streams,
)


SCHEMA = "rgeo-zgeo-1ms-id2d1r1-active-nominal-duration-time-development-result-v1"
CONFIG_SHA256 = "856b2f3c5baeff4526a918e617db3cf62d7773442cd5f8d2965fa4344eef8ed7"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2d1r1_active_nominal_duration_time_development.json"
ID2C1_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.json"
DESIGN = ROOT / "docs/codex/reports/RGEO_ZGEO_1MS_ID2D1R1_ACTIVE_NOMINAL_DURATION_TIME_DEVELOPMENT_DESIGN.md"


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2d1r1-active-nominal-duration-time-development-v1",
        "stage_id": "rgeo_zgeo_1ms_id2d1r1_active_nominal_duration_time_development_v1",
        "base_tsc_config": "configs/rgeo_zgeo_1ms_nr1_safety_effect.json",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 32,
        "maximum_rollouts": 24,
        "maximum_reset_calls": 24,
        "maximum_advance_attempts": 768,
        "maximum_gotsc_calls": 768,
        "maximum_verified_plant_advances": 768,
        "maximum_retained_states": 792,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_prospective_fit_eligible_empirical_development",
        "intended_use": "source_local_active_nominal_duration_time_and_response_memory_development",
        "model_fit_use_after_all_gates_pass": "id2d1r1_development_only",
        "calibration_use": "forbidden",
        "blind_holdout_use": "forbidden",
        "fixture_expert_oracle_bc_dagger_rl_use": "forbidden",
        "controller_safety_or_recourse_qualification_use": "forbidden",
        "holdout_records_read": 0,
        "baseline_replays": 2,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    if stage.get("frozen_nominal") != {
        "candidate_id": "p03_minus_stride1",
        "p03_minus_increment_issues": list(range(1, 16)),
        "held_from_issue_step": 15,
        "selection_or_adaptation_during_id2d1r1": "forbidden",
    }:
        raise InputIntegrityError("frozen nominal mismatch")
    expected_schedules = [
        {"probe_issue_step": 16, "probe_duration_issues": 2},
        {"probe_issue_step": 16, "probe_duration_issues": 4},
        {"probe_issue_step": 22, "probe_duration_issues": 1},
        {"probe_issue_step": 22, "probe_duration_issues": 2},
        {"probe_issue_step": 22, "probe_duration_issues": 4},
    ]
    if stage.get("smooth_residual_schedule_cells") != expected_schedules:
        raise InputIntegrityError("smooth schedule cells changed")
    if stage.get("smooth_residual_directions") != ["p04", "p07"] or stage.get("signs") != ["plus", "minus"]:
        raise InputIntegrityError("smooth direction/sign family changed")
    if stage.get("event_residual_schedule_cells") != [{"probe_issue_step": 22, "probe_duration_issues": 1}]:
        raise InputIntegrityError("event schedule changed")
    if stage.get("event_residual_directions") != ["p09_half_exact_center"]:
        raise InputIntegrityError("event direction changed")
    if stage.get("excluded_evaluator_cells") != [{
        "probe_issue_step": 16,
        "probe_duration_issues": 1,
        "directions": ["p04", "p07", "p09_half_exact_center"],
    }]:
        raise InputIntegrityError("evaluator exclusion changed")
    if stage.get("observability") != {
        "current_same_step_r_geo_z_geo_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_observation_and_owned_action_history": "available",
        "future_successor_before_issue": "unknown",
        "pre_takeover_history": "not_claimed",
        "latent_belief_role": "unobserved_memory_future_response_and_model_mismatch_only",
    }:
        raise InputIntegrityError("observability contract changed")
    action = stage.get("action_semantics", {})
    if action != {
        "starting_issue_is_exact_q0": True,
        "nominal_is_exact_card15_p03_minus_stride1": True,
        "residual_is_translated_actual_fourteen_dimensional_card15_target": True,
        "maximum_single_turn_adjacent_delta_a": 0.3,
        "full_0p3_a_may_be_used": True,
        "runner_clipping_must_not_be_triggered_or_relied_on": True,
        "effect_state_index": "issue_step_plus_one",
        "future_actual_current_before_issue": "forbidden",
        "no_return_or_cleanup_plant_action_after_horizon_or_stop": True,
    }:
        raise InputIntegrityError("action contract changed")
    exploration = stage.get("empirical_exploration", {})
    if exploration != {
        "novel_successors_are_declared_tsc_only_exposures": True,
        "pre_action_transition_tube_claimed": False,
        "post_successor_step_caps": {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0},
        "inner_probe_issue_clearance": {"r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05},
        "outer_hard_envelope": {"r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10},
        "stop_before_next_issue_after_any_failure": True,
        "post_action_abort_is_not_a_pre_action_bound": True,
    }:
        raise InputIntegrityError("empirical exploration contract changed")
    if stage.get("baseline_repeatability") != {
        "geometry_m": 1e-12,
        "ip_a": 1e-9,
        "coil_a": 1e-9,
        "wire_a": 1e-9,
        "complete_state_action_and_semantic_artifact_pairs_required": 1,
    }:
        raise InputIntegrityError("baseline repeatability changed")
    if stage.get("fit_eligibility_gates") != {
        "smooth_virtual_residual_coordinates": ["p04", "p07"],
        "smooth_lag_steps": 16,
        "required_smooth_lag_block_rank": 32,
        "event_virtual_residual_coordinates": ["p09_half_exact_center"],
        "event_lag_steps": 10,
        "required_event_lag_block_rank": 10,
        "minimum_each_smooth_arm_peak_rz_response_m": 0.000025,
        "maximum_each_smooth_arm_absolute_ip_response_a": 150.0,
        "minimum_each_event_arm_peak_rz_response_m": 0.000025,
        "maximum_each_event_arm_absolute_ip_response_a": 50.0,
        "all_states_and_available_tails_through_state_32_required": True,
        "duration_or_issue_time_difference_is_not_a_forced_gate": True,
    }:
        raise InputIntegrityError("fit eligibility gates changed")
    if stage.get("later_model_contract") != {
        "id2d1r1_role": "development_fit_only_after_pass",
        "id2c2_role": "immutable_evaluator_only",
        "id2c2_issue16_one_issue_cells_are_excluded_from_id2d1r1": True,
        "action_blind_nominal_baseline_required": True,
        "stable_low_order_or_fixed_pole_candidate_required_first": True,
        "p09_is_separate_hybrid_event_channel": True,
        "future_readback_or_actual_current_input": "forbidden",
        "neural_residual": "blocked_until_structured_candidate_evaluated",
    }:
        raise InputIntegrityError("later model contract changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 180000000000,
        "maximum_estimated_raw_bytes": 60000000000,
        "minimum_free_bytes_after_estimate": 120000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]:
        raise InputIntegrityError("semantic artifacts changed")
    if stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("diagnostic artifacts changed")
    expected_routes = {
        "offline_or_input_fail": "ONE_MS_ID2D1R1_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "storage_fail": "ONE_MS_ID2D1R1_STORAGE_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2D1R1_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2D1R1_RAW_INTEGRITY_FAIL_PRESERVE_RAW_STOP",
        "baseline_repeatability_fail": "ONE_MS_ID2D1R1_BASELINE_REPEATABILITY_FAIL_ROUTE_REVIEW",
        "lag_support_fail": "ONE_MS_ID2D1R1_MODEL_ALIGNED_LAG_SUPPORT_FAIL_ROUTE_REVIEW",
        "signal_or_ip_fail": "ONE_MS_ID2D1R1_RESPONSE_SIGNAL_OR_IP_FAIL_ROUTE_REVIEW",
        "pass": "ONE_MS_ID2D1R1_ACTIVE_NOMINAL_DURATION_TIME_DEVELOPMENT_PASS_STRUCTURED_MODEL_ONLY",
    }
    if stage.get("routes") != expected_routes:
        raise InputIntegrityError("routes changed")
    if stage.get("claim_boundary") != "Finite source-local fit-eligible empirical development only after every gate passes; not calibration, blind holdout, tube, recovery, controller, MPC or reachability qualification.":
        raise InputIntegrityError("claim boundary changed")


def load(stage_path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    stage_path = inside_root(stage_path, "ID2D1R1 config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2D1R1 config hash mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    if sha256(inside_root(DESIGN, "ID2D1R1 design")) != stage["evidence"]["design_sha256"]:
        raise InputIntegrityError("ID2D1R1 design hash mismatch")
    base = inside_root(ROOT / stage["base_tsc_config"], "base config")
    if sha256(base) != stage["evidence"]["base_tsc_config_sha256"]:
        raise InputIntegrityError("base config hash mismatch")
    for key in ("id2c1_config", "id2c1_compact", "id2c2_config", "id2c2_compact", "id2d1_v1_config", "id2d1_v1_design"):
        row = stage["evidence"][key]
        path = inside_root(ROOT / row["path"], key)
        if sha256(path) != row["sha256"]:
            raise InputIntegrityError(f"{key} hash mismatch")
    id2c1_compact = json.loads((ROOT / stage["evidence"]["id2c1_compact"]["path"]).read_text(encoding="utf-8"))
    if id2c1_compact.get("primary_result_sha256") != stage["evidence"]["id2c1_primary_result_sha256"]:
        raise InputIntegrityError("ID2C1 primary identity mismatch")
    if id2c1_compact.get("independent_audit_v2_sha256") != stage["evidence"]["id2c1_independent_audit_v2_sha256"]:
        raise InputIntegrityError("ID2C1 independent identity mismatch")
    id2c2_compact = json.loads((ROOT / stage["evidence"]["id2c2_compact"]["path"]).read_text(encoding="utf-8"))
    if id2c2_compact.get("primary_result_sha256") != stage["evidence"]["id2c2_primary_result_sha256"]:
        raise InputIntegrityError("ID2C2 primary identity mismatch")
    if id2c2_compact.get("independent_audit_sha256") != stage["evidence"]["id2c2_independent_audit_sha256"]:
        raise InputIntegrityError("ID2C2 independent identity mismatch")
    if id2c2_compact.get("primary_passed") is not True or id2c2_compact.get("independent_audit_passed") is not True:
        raise InputIntegrityError("ID2C2 evidence did not pass")
    id2c1_stage, cfg, _, targets = load_id2c1(ID2C1_CONFIG)
    return stage, cfg, targets, id2c1_stage


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any], id2c1_stage: dict[str, Any]) -> list[dict[str, Any]]:
    phase_a = phase_a_streams(id2c1_stage, cfg, targets)
    selected = next(row for row in phase_a if row["candidate_id"] == "p03_minus_stride1")
    held = selected["targets"][15]
    base_sequence = list(selected["targets"][:16]) + [held] * 16
    rows: list[dict[str, Any]] = []

    def add(rollout_id: str, direction: str | None, sign: str | None, issue: int | None, duration: int | None, kind: str) -> None:
        sequence = list(base_sequence)
        virtual = [[0.0, 0.0, 0.0] for _ in sequence]
        if direction is not None and sign is not None and issue is not None and duration is not None:
            residual = targets[f"{direction}:{sign}"]
            translated = _translated_target(held, targets["q0"], residual, cfg, f"{rollout_id}.probe")
            coordinate = {"p04": 0, "p07": 1, "p09_half_exact_center": 2}[direction]
            signed = 1.0 if sign == "plus" else -1.0
            for step in range(issue, issue + duration):
                sequence[step] = translated
                virtual[step][coordinate] = signed
        rows.append({
            "rollout_id": rollout_id,
            "cell_id": rollout_id,
            "cell_kind": kind,
            "direction_id": direction,
            "sign": sign,
            "probe_issue_step": issue,
            "probe_duration_issues": duration,
            "pulse_issue_step": issue if issue is not None else 32,
            "exact_return_issue_step": issue + duration if issue is not None and duration is not None else None,
            "targets": sequence,
            "actions": _actions(sequence, cfg, rollout_id, virtual),
        })

    for replay in range(stage["baseline_replays"]):
        add(f"held_nominal_baseline_r{replay}", None, None, None, None, "baseline")
    for direction in stage["smooth_residual_directions"]:
        for sign in stage["signs"]:
            for cell in stage["smooth_residual_schedule_cells"]:
                issue = int(cell["probe_issue_step"])
                duration = int(cell["probe_duration_issues"])
                add(f"{direction}_{sign}_i{issue}_d{duration}", direction, sign, issue, duration, "smooth_residual")
    for direction in stage["event_residual_directions"]:
        for sign in stage["signs"]:
            for cell in stage["event_residual_schedule_cells"]:
                issue = int(cell["probe_issue_step"])
                duration = int(cell["probe_duration_issues"])
                add(f"{direction}_{sign}_i{issue}_d{duration}", direction, sign, issue, duration, "event_residual")
    if len(rows) != stage["maximum_rollouts"]:
        raise InputIntegrityError("campaign rollout budget mismatch")
    excluded = {(16, 1, direction) for direction in ("p04", "p07", "p09_half_exact_center")}
    if any((row["probe_issue_step"], row["probe_duration_issues"], row["direction_id"]) in excluded for row in rows):
        raise InputIntegrityError("ID2C2 evaluator cell leaked into ID2D1")
    return rows


def lag_support(streams: Sequence[dict[str, Any]], coordinates: Sequence[int], lag_steps: int) -> dict[str, Any]:
    matrix_rows = []
    for stream in streams:
        u = np.asarray([action["probe_virtual_action"] for action in stream["actions"]], dtype=float)[:, list(coordinates)]
        for issue in range(len(u)):
            feature = []
            for lag in range(lag_steps):
                feature.extend(u[issue - lag].tolist() if issue >= lag else [0.0] * len(coordinates))
            matrix_rows.append(feature)
    matrix = np.asarray(matrix_rows, dtype=float)
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.linalg.matrix_rank(matrix))
    return {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "rank": rank,
        "condition": float(singular[0] / singular[-1]) if singular.size and singular[-1] > 0 else math.inf,
        "minimum_singular_value": float(singular[-1]) if singular.size else 0.0,
    }


def development_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any] | None:
    if len(rows) != stage["maximum_rollouts"] or not all(row["passed"] for row in rows):
        return None
    baselines = [row for row in rows if row["cell_kind"] == "baseline"]
    shim = {"repeatability": stage["baseline_repeatability"], "semantic_artifacts": stage["semantic_artifacts"]}
    repeatability = compare_rows(baselines[0], baselines[1], shim)
    base = np.mean(np.asarray([[[state[k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for state in row["states"]] for row in baselines], dtype=float), axis=0)
    arms = []
    for row in rows:
        if row["cell_kind"] == "baseline":
            continue
        values = np.asarray([[state[k] for k in ("r_geo_m", "z_geo_m", "ip_a")] for state in row["states"]], dtype=float)
        response = values - base
        effect = int(row["probe_issue_step"]) + 1
        window = response[effect:33]
        norms = np.linalg.norm(window[:, :2], axis=1)
        peak = int(np.argmax(norms))
        arms.append({
            "cell_id": row["cell_id"],
            "cell_kind": row["cell_kind"],
            "direction_id": row["direction_id"],
            "sign": row["sign"],
            "probe_issue_step": row["probe_issue_step"],
            "probe_duration_issues": row["probe_duration_issues"],
            "effect_state_index": effect,
            "peak_state_index": effect + peak,
            "peak_rz_response_m": window[peak, :2].tolist(),
            "peak_rz_response_norm_m": float(norms[peak]),
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rzi_response": response[-1].tolist(),
            "terminal_to_peak_rz_ratio": float(norms[-1] / norms[peak]) if norms[peak] else math.inf,
            "complete_response": response[effect:33].tolist(),
        })
    streams = campaign_streams(stage, load_id2c1(ID2C1_CONFIG)[1], load_id2c1(ID2C1_CONFIG)[3], load_id2c1(ID2C1_CONFIG)[0])
    smooth_support = lag_support(streams, [0, 1], stage["fit_eligibility_gates"]["smooth_lag_steps"])
    event_support = lag_support(streams, [2], stage["fit_eligibility_gates"]["event_lag_steps"])
    gates = stage["fit_eligibility_gates"]
    smooth = [row for row in arms if row["cell_kind"] == "smooth_residual"]
    event = [row for row in arms if row["cell_kind"] == "event_residual"]
    gate_passes = {
        "baseline_repeatability": repeatability["passed"],
        "model_aligned_lag_support": (
            smooth_support["rank"] == gates["required_smooth_lag_block_rank"]
            and event_support["rank"] == gates["required_event_lag_block_rank"]
        ),
        "response_signal_and_ip": all(
            row["peak_rz_response_norm_m"] >= gates["minimum_each_smooth_arm_peak_rz_response_m"]
            and row["maximum_absolute_ip_response_a"] <= gates["maximum_each_smooth_arm_absolute_ip_response_a"]
            for row in smooth
        ) and all(
            row["peak_rz_response_norm_m"] >= gates["minimum_each_event_arm_peak_rz_response_m"]
            and row["maximum_absolute_ip_response_a"] <= gates["maximum_each_event_arm_absolute_ip_response_a"]
            for row in event
        ),
    }
    return {"baseline_repeatability": repeatability, "smooth_lag_support": smooth_support, "event_lag_support": event_support, "arm_metrics": arms, "gate_passes": gate_passes}


def _route(stage: dict[str, Any], rows: Sequence[dict[str, Any]], raw_ok: bool, metrics: dict[str, Any] | None) -> str:
    empirical = ("EMPIRICAL_STEP_R", "EMPIRICAL_STEP_Z", "EMPIRICAL_STEP_IP", "OUTER_R", "OUTER_Z", "OUTER_IP")
    if any(any(not reason.startswith(empirical) for reason in row["reasons"]) for row in rows if not row["passed"]):
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if metrics is None:
        return stage["routes"]["execution_or_interface_fail"]
    gates = metrics["gate_passes"]
    if not gates["baseline_repeatability"]:
        return stage["routes"]["baseline_repeatability_fail"]
    if not gates["model_aligned_lag_support"]:
        return stage["routes"]["lag_support_fail"]
    if not gates["response_signal_and_ip"]:
        return stage["routes"]["signal_or_ip_fail"]
    return stage["routes"]["pass"]


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures = []
    streams: list[dict[str, Any]] = []
    support = None
    try:
        stage, cfg, targets, id2c1_stage = load(stage_path)
        streams = campaign_streams(stage, cfg, targets, id2c1_stage)
        support = {
            "smooth": lag_support(streams, [0, 1], stage["fit_eligibility_gates"]["smooth_lag_steps"]),
            "event": lag_support(streams, [2], stage["fit_eligibility_gates"]["event_lag_steps"]),
        }
        if support["smooth"]["rank"] != stage["fit_eligibility_gates"]["required_smooth_lag_block_rank"]:
            raise InputIntegrityError(f"smooth lag support rank {support['smooth']['rank']}")
        if support["event"]["rank"] != stage["fit_eligibility_gates"]["required_event_lag_block_rank"]:
            raise InputIntegrityError(f"event lag support rank {support['event']['rank']}")
        if any(len(row["targets"]) != 32 or len(row["actions"]) != 32 for row in streams):
            raise InputIntegrityError("stream dimensions changed")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures,
        "failures": failures,
        "lag_support": support,
        "action_streams": [{key: value for key, value in row.items() if key != "targets"} for row in streams],
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


def run(stage_path: Path, source_revision: str, output: Path) -> dict[str, Any]:
    output = inside_root(output, "ID2D1R1 output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    stage, cfg, targets, id2c1_stage = load(stage_path)
    storage = _storage(stage, output)
    output.mkdir(parents=True)
    gate = offline(stage_path, source_revision)
    write_new(output / "offline_preflight.json", gate)
    if not storage["passed"] or not gate["passed"]:
        route = stage["routes"]["storage_fail"] if not storage["passed"] else stage["routes"]["offline_or_input_fail"]
        result = {"schema_version": SCHEMA, "source_revision": source_revision, "stage_config_sha256": CONFIG_SHA256, "passed": False, "route": route, "reasons": gate["failures"], "storage_gate": storage, "rollouts_completed": 0, "reset_calls": 0, "advance_attempts": 0, "plant_advance_gotsc_calls": 0, "verified_plant_advances": 0, "model_fit_data_eligible": False}
        write_new(output / "result.json", result)
        return result
    cfg.run_root = output / "rollouts"
    runtime_stage = dict(stage)
    runtime_stage["empirical_exploration"] = dict(stage["empirical_exploration"])
    runtime_stage["empirical_exploration"]["inner_pulse_issue_clearance"] = stage["empirical_exploration"]["inner_probe_issue_clearance"]
    rows = []
    for stream in campaign_streams(stage, cfg, targets, id2c1_stage):
        row = one_rollout(cfg, runtime_stage, stream)
        row["schema_version"] = SCHEMA
        row["source_revision"] = source_revision
        rows.append(row)
        write_new(output / f"{row['rollout_id']}.json", row)
        if not row["passed"]:
            break
    inventory = raw_inventory(output, rows, stage)
    raw_ok = not inventory["missing_required_artifacts"]
    metrics = development_metrics(rows, stage)
    route = _route(stage, rows, raw_ok, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage,
        "development_metrics": metrics,
        "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "model_fit_data_eligible": passed,
        "calibration_data_eligible": False,
        "blind_holdout_data_eligible": False,
        "id2c2_immutable_evaluator_not_read_as_fit_data": True,
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
