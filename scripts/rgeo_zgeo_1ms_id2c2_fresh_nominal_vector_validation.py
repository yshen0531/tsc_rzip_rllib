#!/usr/bin/env python3
"""Run the fixed fresh ID-2C2 nominal/vector validation campaign."""

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
    load as load_id2c1,
    phase_a_streams,
    phase_b_streams,
)


SCHEMA = "rgeo-zgeo-1ms-id2c2-fresh-nominal-vector-validation-result-v1"
CONFIG_SHA256 = "cf68e47b430782fee27241bdd6b79b16d71bb3988c18046b0d341053bc5f6f2e"
DEFAULT_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation.json"
ID2C1_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.json"


def _exact_stage(stage: dict[str, Any]) -> None:
    exact = {
        "schema_version": "rgeo-zgeo-1ms-id2c2-fresh-nominal-vector-validation-v1",
        "stage_id": "rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation_v1",
        "takeover_time_ms": 1100,
        "control_period_ms": 1,
        "horizon_steps": 32,
        "replays_per_cell": 2,
        "maximum_rollouts": 18,
        "maximum_reset_calls": 18,
        "maximum_advance_attempts": 576,
        "maximum_gotsc_calls": 576,
        "maximum_verified_plant_advances": 576,
        "retry_after_any_advance_attempt": "forbidden",
        "experiment_contract": "tsc_only_prospective_fresh_empirical_validation",
        "intended_use": "fresh_repeatability_nominal_authority_and_local_vector_validation",
        "model_fit_use": "forbidden",
        "calibration_use": "forbidden",
        "blind_holdout_use": "forbidden",
        "fixture_expert_oracle_bc_dagger_rl_use": "forbidden",
        "controller_safety_or_recourse_qualification_use": "forbidden",
        "holdout_records_read": 0,
    }
    for key, value in exact.items():
        if stage.get(key) != value:
            raise InputIntegrityError(f"frozen field mismatch: {key}")
    expected_cells = [
        ("fresh_q0_baseline", "q0", None, None),
        ("p03_minus_stride1_nominal", "full_nominal", None, None),
        ("selected_nominal_probe_baseline", "held_prefix_baseline", None, None),
        ("selected_nominal_p04_plus", "residual", "p04", "plus"),
        ("selected_nominal_p04_minus", "residual", "p04", "minus"),
        ("selected_nominal_p07_plus", "residual", "p07", "plus"),
        ("selected_nominal_p07_minus", "residual", "p07", "minus"),
        ("selected_nominal_p09_half_exact_center_plus", "residual", "p09_half_exact_center", "plus"),
        ("selected_nominal_p09_half_exact_center_minus", "residual", "p09_half_exact_center", "minus"),
    ]
    observed = [(row.get("cell_id"), row.get("kind"), row.get("direction_id"), row.get("sign")) for row in stage.get("cells_in_order", [])]
    if observed != expected_cells:
        raise InputIntegrityError("fixed cell matrix mismatch")
    nominal = stage.get("frozen_nominal", {})
    if nominal.get("candidate_id") != "p03_minus_stride1" or nominal.get("p03_minus_increment_issues") != list(range(1, 32)):
        raise InputIntegrityError("frozen nominal mismatch")
    if nominal.get("selection_or_adaptation_during_id2c2") != "forbidden":
        raise InputIntegrityError("selection/adaptation contract changed")
    phase_b = stage.get("phase_b", {})
    if (phase_b.get("probe_issue_step"), phase_b.get("exact_return_issue_step")) != (16, 17):
        raise InputIntegrityError("phase-B issue/return mismatch")
    if phase_b.get("response_state_start") != 17 or phase_b.get("response_state_end") != 32:
        raise InputIntegrityError("phase-B response window mismatch")
    if phase_b.get("probe_duration_issues") != 1 or phase_b.get("directions") != ["p04", "p07", "p09_half_exact_center"] or phase_b.get("signs") != ["plus", "minus"]:
        raise InputIntegrityError("phase-B family mismatch")
    if phase_b.get("matched_baseline_by_replay_index") is not True or phase_b.get("actual_fourteen_dimensional_card15_vectors_required") is not True or phase_b.get("p09_pooled_as_smooth_gain") is not False:
        raise InputIntegrityError("phase-B role mismatch")
    action = stage.get("action_semantics", {})
    if action.get("maximum_single_turn_adjacent_delta_a") != 0.3 or action.get("full_0p3_a_may_be_used") is not True:
        raise InputIntegrityError("action slew mismatch")
    if action.get("effect_state_index") != "issue_step_plus_one" or action.get("runner_clipping_must_not_be_triggered_or_relied_on") is not True:
        raise InputIntegrityError("action/effect contract mismatch")
    if action.get("starting_issue_is_exact_q0") is not True or action.get("nominal_is_exact_card15_p03_minus_stride1") is not True:
        raise InputIntegrityError("action origin/nominal contract mismatch")
    if action.get("future_actual_current_before_issue") != "forbidden" or action.get("no_return_or_cleanup_plant_action_after_horizon_or_stop") is not True:
        raise InputIntegrityError("future-current/terminal action contract mismatch")
    if stage.get("observability") != {
        "current_same_step_r_geo_z_geo_ip": "exact_noiseless_before_issue",
        "post_takeover_causal_observation_and_owned_action_history": "available",
        "future_successor_before_issue": "unknown",
        "pre_takeover_history": "not_claimed",
        "latent_belief_role": "unobserved_memory_future_response_and_model_mismatch_only",
    }:
        raise InputIntegrityError("observability contract mismatch")
    exploration = stage.get("empirical_exploration", {})
    if exploration.get("pre_action_transition_tube_claimed") is not False or exploration.get("post_action_abort_is_not_a_pre_action_bound") is not True:
        raise InputIntegrityError("empirical claim changed")
    if exploration.get("post_successor_step_caps") != {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 100.0}:
        raise InputIntegrityError("empirical step caps changed")
    if exploration.get("inner_probe_issue_clearance") != {"r_geo_m": 0.025, "z_geo_m": 0.025, "ip_fraction": 0.05}:
        raise InputIntegrityError("inner issue clearance changed")
    if exploration.get("outer_hard_envelope") != {"r_geo_m": 0.05, "z_geo_m": 0.05, "ip_fraction": 0.10}:
        raise InputIntegrityError("outer envelope changed")
    if exploration.get("stop_before_next_issue_after_any_failure") is not True:
        raise InputIntegrityError("stop contract changed")
    gates = stage.get("scientific_gates", {})
    expected_gates = {
        "minimum_terminal_rz_norm_reduction_fraction_vs_matched_q0": 0.30,
        "maximum_absolute_nominal_ip_from_source_a": 1000.0,
        "minimum_each_arm_peak_rz_response_m": 0.000025,
        "maximum_each_arm_absolute_ip_response_a": 50.0,
        "maximum_each_arm_terminal_to_peak_rz_ratio": 0.50,
        "maximum_plus_minus_peak_vector_cosine": -0.95,
        "minimum_plus_minus_peak_norm_ratio": 0.5,
        "maximum_plus_minus_peak_norm_ratio": 2.0,
        "required_peak_rz_rank": 2,
        "maximum_best_pair_condition": 5.0,
        "maximum_circular_angular_gap_deg": 150.0,
        "all_gates_must_pass_in_each_replay_set": True,
    }
    if gates != expected_gates:
        raise InputIntegrityError("scientific gates changed")
    if stage.get("storage_gate") != {
        "minimum_free_bytes_before_run": 150000000000,
        "maximum_estimated_raw_bytes": 45000000000,
        "minimum_free_bytes_after_estimate": 100000000000,
        "output_must_not_exist": True,
        "raw_compression": "forbidden",
    }:
        raise InputIntegrityError("storage gate mismatch")
    if stage.get("repeatability") != {
        "geometry_m": 1e-12,
        "ip_a": 1e-9,
        "coil_a": 1e-9,
        "wire_a": 1e-9,
        "complete_state_action_and_semantic_artifact_pairs_required": 9,
    }:
        raise InputIntegrityError("repeatability contract changed")
    if stage.get("semantic_artifacts") != ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"] or stage.get("diagnostic_artifacts") != ["sprsina"]:
        raise InputIntegrityError("artifact role changed")
    if stage.get("routes") != {
        "offline_or_input_fail": "ONE_MS_ID2C2_OFFLINE_OR_INPUT_FAIL_NO_TSC",
        "storage_fail": "ONE_MS_ID2C2_STORAGE_FAIL_NO_TSC",
        "execution_or_interface_fail": "ONE_MS_ID2C2_EXECUTION_OR_INTERFACE_FAIL_STOP",
        "raw_integrity_fail": "ONE_MS_ID2C2_RAW_INTEGRITY_FAIL_PRESERVE_RAW_STOP",
        "repeatability_fail": "ONE_MS_ID2C2_FRESH_REPEATABILITY_FAIL_ROUTE_REVIEW",
        "nominal_authority_fail": "ONE_MS_ID2C2_FRESH_NOMINAL_AUTHORITY_FAIL_ROUTE_REVIEW",
        "residual_signal_or_ip_fail": "ONE_MS_ID2C2_FRESH_RESIDUAL_SIGNAL_OR_IP_FAIL_ROUTE_REVIEW",
        "residual_tail_fail": "ONE_MS_ID2C2_FRESH_RESIDUAL_TAIL_FAIL_ROUTE_REVIEW",
        "two_sided_geometry_fail": "ONE_MS_ID2C2_FRESH_TWO_SIDED_VECTOR_GEOMETRY_FAIL_ROUTE_REVIEW",
        "pass": "ONE_MS_ID2C2_FRESH_NOMINAL_VECTOR_VALIDATION_PASS_STRUCTURED_MODEL_DESIGN_REQUIRED",
    }:
        raise InputIntegrityError("routes changed")
    if stage.get("claim_boundary") != "Finite fresh source-local empirical validation only; not fit, calibration, blind holdout, tube, recovery, controller, MPC or reachability qualification.":
        raise InputIntegrityError("claim boundary changed")


def load(stage_path: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    stage_path = inside_root(stage_path, "ID2C2 config")
    if sha256(stage_path) != CONFIG_SHA256:
        raise InputIntegrityError("ID2C2 config hash mismatch")
    stage = json.loads(stage_path.read_text(encoding="utf-8"))
    _exact_stage(stage)
    design = inside_root(ROOT / "docs/codex/reports/RGEO_ZGEO_1MS_ID2C2_FRESH_NOMINAL_VECTOR_VALIDATION_DESIGN.md", "ID2C2 design")
    if sha256(design) != stage["evidence"]["design_sha256"]:
        raise InputIntegrityError("ID2C2 design hash mismatch")
    id2c1_design_row = stage["evidence"]["id2c1_design"]
    id2c1_design = inside_root(ROOT / id2c1_design_row["path"], "ID2C1 design")
    if sha256(id2c1_design) != id2c1_design_row["sha256"]:
        raise InputIntegrityError("ID2C1 design hash mismatch")
    compact_row = stage["evidence"]["id2c1_compact"]
    compact_path = inside_root(ROOT / compact_row["path"], "ID2C1 compact")
    if sha256(compact_path) != compact_row["sha256"]:
        raise InputIntegrityError("ID2C1 compact hash mismatch")
    compact = json.loads(compact_path.read_text(encoding="utf-8"))
    if compact.get("primary_passed") is not True or compact.get("independent_audit_passed") is not True:
        raise InputIntegrityError("ID2C1 evidence did not pass")
    if compact.get("primary_result_sha256") != stage["evidence"]["id2c1_primary_result_sha256"]:
        raise InputIntegrityError("ID2C1 primary result identity mismatch")
    if compact.get("independent_audit_v2_sha256") != stage["evidence"]["id2c1_independent_audit_v2_sha256"]:
        raise InputIntegrityError("ID2C1 independent identity mismatch")
    id2c1_row = stage["evidence"]["id2c1_config"]
    id2c1_path = inside_root(ROOT / id2c1_row["path"], "ID2C1 config")
    if id2c1_path != ID2C1_CONFIG.resolve() or sha256(id2c1_path) != id2c1_row["sha256"]:
        raise InputIntegrityError("ID2C1 config identity mismatch")
    id2c1_stage, cfg, source, targets = load_id2c1(id2c1_path)
    return stage, cfg, source, targets, id2c1_stage


def campaign_streams(stage: dict[str, Any], cfg: Any, targets: dict[str, Any], id2c1_stage: dict[str, Any]) -> list[dict[str, Any]]:
    phase_a = phase_a_streams(id2c1_stage, cfg, targets)
    selected = next(row for row in phase_a if row["candidate_id"] == stage["frozen_nominal"]["candidate_id"])
    phase_b = phase_b_streams(id2c1_stage, cfg, targets, selected)
    source = {
        "fresh_q0_baseline": next(row for row in phase_a if row["candidate_id"] == "fresh_q0_baseline"),
        "p03_minus_stride1_nominal": selected,
        **{row["rollout_id"]: row for row in phase_b},
    }
    rows: list[dict[str, Any]] = []
    for cell in stage["cells_in_order"]:
        base = source[cell["cell_id"]]
        for replay_index in range(stage["replays_per_cell"]):
            rollout_id = f"{cell['cell_id']}_r{replay_index}"
            rows.append({
                **{key: value for key, value in base.items() if key != "rollout_id"},
                "rollout_id": rollout_id,
                "pair_id": cell["cell_id"],
                "cell_id": cell["cell_id"],
                "cell_kind": cell["kind"],
                "replay_index": replay_index,
                "direction_id": cell.get("direction_id"),
                "sign": cell.get("sign"),
            })
    if len(rows) != stage["maximum_rollouts"]:
        raise InputIntegrityError("campaign rollout budget mismatch")
    return rows


def _angular_gap(vectors: Sequence[Sequence[float]]) -> float:
    angles = sorted(math.degrees(math.atan2(float(v[1]), float(v[0]))) % 360.0 for v in vectors)
    return max(b - a for a, b in zip(angles, angles[1:] + [angles[0] + 360.0]))


def _one_replay_metrics(rows: Sequence[dict[str, Any]], replay_index: int) -> dict[str, Any]:
    subset = {row["cell_id"]: row for row in rows if row["replay_index"] == replay_index}
    q0 = subset["fresh_q0_baseline"]
    nominal = subset["p03_minus_stride1_nominal"]
    source = q0["states"][0]
    q0_terminal = q0["states"][-1]
    nominal_terminal = nominal["states"][-1]
    q0_norm = math.hypot(q0_terminal["r_geo_m"] - source["r_geo_m"], q0_terminal["z_geo_m"] - source["z_geo_m"])
    nominal_norm = math.hypot(nominal_terminal["r_geo_m"] - source["r_geo_m"], nominal_terminal["z_geo_m"] - source["z_geo_m"])
    nominal_metrics = {
        "q0_terminal_source_rz_norm_m": q0_norm,
        "nominal_terminal_source_rz_norm_m": nominal_norm,
        "terminal_rz_norm_reduction_fraction_vs_matched_q0": 1.0 - nominal_norm / q0_norm,
        "maximum_absolute_nominal_ip_from_source_a": max(abs(state["ip_a"] - source["ip_a"]) for state in nominal["states"]),
    }
    baseline = subset["selected_nominal_probe_baseline"]
    base = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in baseline["states"]], dtype=float)
    arm_metrics: list[dict[str, Any]] = []
    vectors: list[np.ndarray] = []
    for cell in (
        "selected_nominal_p04_plus", "selected_nominal_p04_minus",
        "selected_nominal_p07_plus", "selected_nominal_p07_minus",
        "selected_nominal_p09_half_exact_center_plus", "selected_nominal_p09_half_exact_center_minus",
    ):
        row = subset[cell]
        values = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in row["states"]], dtype=float)
        response = values - base
        window = response[17:33]
        norms = np.linalg.norm(window[:, :2], axis=1)
        peak_offset = int(np.argmax(norms))
        peak = window[peak_offset, :2]
        peak_norm = float(norms[peak_offset])
        terminal_norm = float(norms[-1])
        vectors.append(peak)
        arm_metrics.append({
            "cell_id": cell,
            "direction_id": row["direction_id"],
            "sign": row["sign"],
            "peak_state_index": 17 + peak_offset,
            "peak_rz_response_m": peak.tolist(),
            "peak_rz_response_norm_m": peak_norm,
            "maximum_absolute_ip_response_a": float(np.max(np.abs(window[:, 2]))),
            "terminal_rz_response_norm_m": terminal_norm,
            "terminal_to_peak_rz_ratio": terminal_norm / peak_norm if peak_norm else math.inf,
            "terminal_rzi_response": response[-1].tolist(),
        })
    matrix = np.asarray(vectors, dtype=float).T
    conditions = []
    for left in range(matrix.shape[1]):
        for right in range(left + 1, matrix.shape[1]):
            pair = matrix[:, [left, right]]
            if np.linalg.matrix_rank(pair) == 2:
                conditions.append(float(np.linalg.cond(pair)))
    direction_pairs = []
    for direction in ("p04", "p07", "p09_half_exact_center"):
        plus = next(row for row in arm_metrics if row["direction_id"] == direction and row["sign"] == "plus")
        minus = next(row for row in arm_metrics if row["direction_id"] == direction and row["sign"] == "minus")
        p = np.asarray(plus["peak_rz_response_m"], dtype=float)
        m = np.asarray(minus["peak_rz_response_m"], dtype=float)
        pn = float(np.linalg.norm(p))
        mn = float(np.linalg.norm(m))
        direction_pairs.append({
            "direction_id": direction,
            "plus_minus_peak_vector_cosine": float(np.dot(p, m) / (pn * mn)),
            "plus_over_minus_peak_norm_ratio": pn / mn,
        })
    return {
        "replay_index": replay_index,
        "nominal_metrics": nominal_metrics,
        "arm_metrics": arm_metrics,
        "direction_pair_metrics": direction_pairs,
        "peak_rz_rank": int(np.linalg.matrix_rank(matrix)),
        "best_pair_condition": min(conditions) if conditions else math.inf,
        "circular_maximum_angular_gap_deg": _angular_gap(vectors),
        "positive_span_claim_scope": "finite_one_issue_return_peak_response_rays_only",
        "p09_pooled_as_smooth_gain": False,
    }


def validation_metrics(rows: Sequence[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any] | None:
    if len(rows) != stage["maximum_rollouts"] or not all(row["passed"] for row in rows):
        return None
    replay_metrics = [_one_replay_metrics(rows, replay) for replay in range(stage["replays_per_cell"])]
    repeatability = []
    for cell in stage["cells_in_order"]:
        pair = sorted((row for row in rows if row["cell_id"] == cell["cell_id"]), key=lambda row: row["replay_index"])
        result = compare_rows(pair[0], pair[1], stage)
        repeatability.append({"cell_id": cell["cell_id"], **result})
    gates = stage["scientific_gates"]
    repeatability_passed = len(repeatability) == 9 and all(row["passed"] for row in repeatability)
    nominal_passed = all(
        row["nominal_metrics"]["terminal_rz_norm_reduction_fraction_vs_matched_q0"] >= gates["minimum_terminal_rz_norm_reduction_fraction_vs_matched_q0"]
        and row["nominal_metrics"]["maximum_absolute_nominal_ip_from_source_a"] <= gates["maximum_absolute_nominal_ip_from_source_a"]
        for row in replay_metrics
    )
    signal_ip_passed = all(
        arm["peak_rz_response_norm_m"] >= gates["minimum_each_arm_peak_rz_response_m"]
        and arm["maximum_absolute_ip_response_a"] <= gates["maximum_each_arm_absolute_ip_response_a"]
        for row in replay_metrics for arm in row["arm_metrics"]
    )
    tail_passed = all(
        arm["terminal_to_peak_rz_ratio"] <= gates["maximum_each_arm_terminal_to_peak_rz_ratio"]
        for row in replay_metrics for arm in row["arm_metrics"]
    )
    geometry_passed = all(
        row["peak_rz_rank"] == gates["required_peak_rz_rank"]
        and row["best_pair_condition"] <= gates["maximum_best_pair_condition"]
        and row["circular_maximum_angular_gap_deg"] <= gates["maximum_circular_angular_gap_deg"]
        and all(
            pair["plus_minus_peak_vector_cosine"] <= gates["maximum_plus_minus_peak_vector_cosine"]
            and gates["minimum_plus_minus_peak_norm_ratio"] <= pair["plus_over_minus_peak_norm_ratio"] <= gates["maximum_plus_minus_peak_norm_ratio"]
            for pair in row["direction_pair_metrics"]
        )
        for row in replay_metrics
    )
    return {
        "replay_metrics": replay_metrics,
        "repeatability": repeatability,
        "gate_passes": {
            "repeatability": repeatability_passed,
            "nominal_authority": nominal_passed,
            "residual_signal_and_ip": signal_ip_passed,
            "residual_tail": tail_passed,
            "two_sided_vector_geometry": geometry_passed,
        },
    }


def _route(stage: dict[str, Any], rows: Sequence[dict[str, Any]], raw_ok: bool, metrics: dict[str, Any] | None) -> str:
    interface_prefixes = ("EMPIRICAL_STEP_R", "EMPIRICAL_STEP_Z", "EMPIRICAL_STEP_IP", "OUTER_R", "OUTER_Z", "OUTER_IP")
    if any(any(not reason.startswith(interface_prefixes) for reason in row["reasons"]) for row in rows if not row["passed"]):
        return stage["routes"]["execution_or_interface_fail"]
    if not raw_ok:
        return stage["routes"]["raw_integrity_fail"]
    if metrics is None:
        return stage["routes"]["execution_or_interface_fail"]
    passed = metrics["gate_passes"]
    if not passed["repeatability"]:
        return stage["routes"]["repeatability_fail"]
    if not passed["nominal_authority"]:
        return stage["routes"]["nominal_authority_fail"]
    if not passed["residual_signal_and_ip"]:
        return stage["routes"]["residual_signal_or_ip_fail"]
    if not passed["residual_tail"]:
        return stage["routes"]["residual_tail_fail"]
    if not passed["two_sided_vector_geometry"]:
        return stage["routes"]["two_sided_geometry_fail"]
    return stage["routes"]["pass"]


def offline(stage_path: Path, source_revision: str) -> dict[str, Any]:
    failures: list[str] = []
    definitions: list[dict[str, Any]] = []
    try:
        stage, cfg, _, targets, id2c1_stage = load(stage_path)
        definitions = campaign_streams(stage, cfg, targets, id2c1_stage)
        if len(definitions) != 18 or any(len(row["targets"]) != 32 or len(row["actions"]) != 32 for row in definitions):
            raise InputIntegrityError("campaign stream dimensions mismatch")
    except Exception as exc:
        failures.append(f"{type(exc).__name__}:{exc}")
    return {
        "schema_version": SCHEMA,
        "kind": "offline_preflight",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(inside_root(stage_path, "stage config")),
        "passed": not failures,
        "failures": failures,
        "action_streams": [{key: value for key, value in row.items() if key != "targets"} for row in definitions],
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
    output = inside_root(output, "ID2C2 output")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    stage, cfg, _, targets, id2c1_stage = load(stage_path)
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
    rows: list[dict[str, Any]] = []
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
    metrics = validation_metrics(rows, stage)
    route = _route(stage, rows, raw_ok, metrics)
    passed = route == stage["routes"]["pass"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": passed,
        "route": route,
        "storage_gate": storage,
        "validation_metrics": metrics,
        "rollouts_completed": len(rows),
        "reset_calls": sum(row["reset_calls"] for row in rows),
        "advance_attempts": sum(row["advance_attempts"] for row in rows),
        "plant_advance_gotsc_calls": sum(row["plant_advance_gotsc_calls"] for row in rows),
        "verified_plant_advances": sum(row["verified_plant_advances"] for row in rows),
        **inventory,
        "model_fit_data_eligible": False,
        "immutable_evaluation_data_eligible": passed,
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
