#!/usr/bin/env python3
"""Read-only S21 replay of the frozen S23 four-knot Hadamard lattice design.

This audit executes no controller, Ray task, gotsc, TSC, plant step, or
snapshot operation.  It reconstructs exact Card15 actions only from immutable
S21 baseline states and contemporaneous recorded baseline actions.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s22_full_horizon_affine_authority as s22,
)


STAGE = "Stage4.2R3c3T13S23"
IDENTITY = "sequential_four_knot_hadamard_card15_lattice_preflight_v1"
BASELINE_PROBE_ID = "lattice_baseline"
DIRECTIONS = (
    "mode0_without_coil8",
    "mode0_coil8_component",
    "mode1",
    "mode2",
)
ISSUE_STEPS = (10, 13, 16, 19)
CANCEL_STEPS = (11, 14, 17, 20)
N_COILS = 14


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value, indent=2, sort_keys=True, ensure_ascii=False,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    schedule = cfg["schedule_contract"]
    formal = cfg["formal_contract"]
    matrix = cfg["prospective_campaign_matrix"]
    gate = cfg["primary_gate"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s23_sequential_hadamard_lattice_preflight_v1"
        or str(source["s21_package_commit"]) != "98dc353"
        or int(source["s21_raw_count"]) != 360
        or int(source["s21_raw_total_bytes"]) != 21083271
        or int(source["expected_baseline_formal_pass_count"]) != 16
        or int(source["expected_probe_formal_pass_count"]) != 99
        or source["required_s22_route"]
        != "AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED"
        or int(source["required_s22_optimistic_affine_feasible"]) != 16
        or tuple(schedule["context_key_fields"]) != ("pair_id", "history_member")
        or int(schedule["expected_context_count"]) != 40
        or int(schedule["expected_baseline_count"]) != 40
        or int(schedule["expected_signed_probe_count"]) != 320
        or schedule["baseline_probe_id"] != BASELINE_PROBE_ID
        or tuple(schedule["ordered_directions"]) != DIRECTIONS
        or tuple(map(int, schedule["issue_task_steps"])) != ISSUE_STEPS
        or tuple(map(int, schedule["cancel_task_steps"])) != CANCEL_STEPS
        or tuple(map(int, schedule["issue_effect_states"])) != (11, 14, 17, 20)
        or tuple(map(int, schedule["cancel_effect_states"])) != (12, 15, 18, 21)
        or int(schedule["hadamard_order"]) != 16
        or schedule["hadamard_construction"]
        != "unpermuted_sylvester_h2_kronecker_power_4"
        or schedule["column_assignment"] != "4_times_slot_plus_direction"
        or int(schedule["primary_sequence_rows"]) != 16
        or int(schedule["central_sign_primary_rows"]) != 8
        or int(schedule["central_sign_sentinel_rows"]) != 8
        or int(schedule["total_sequence_rows"]) != 24
        or float(schedule["coordinate_amplitude"]) != 0.25
        or int(schedule["dynamic_exact_search_radius"]) != 16
        or schedule["cancellation_policy"]
        != "exact_return_to_stored_preissue_card15_center_only"
        or float(schedule["minimum_absolute_applied_coordinate"]) != 0.18
        or float(schedule["maximum_absolute_applied_coordinate"]) != 0.32
        or float(schedule["maximum_absolute_coordinate_error"]) != 0.07
        or float(schedule["minimum_desired_applied_current_cosine"]) != 0.98
        or float(schedule["maximum_relative_off_basis_residual"]) != 0.10
        or float(schedule["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(schedule["maximum_total_normalized_action_abs"]) != 1.0
        or float(schedule["maximum_current_utilization"]) != 0.55
        or int(schedule["required_global_rank"]) != 16
        or float(schedule["maximum_global_normalized_condition"]) != 3.0
        or int(schedule["required_slot_rank"]) != 4
        or float(schedule["maximum_slot_normalized_condition"]) != 3.0
        or float(schedule["minimum_late_column_residual_outside_slot0_span"]) != 0.5
        or not bool(schedule["require_decimal_exact_central_target_symmetry"])
        or not bool(schedule["require_exact_stored_center_cancellation"])
        or not bool(schedule["require_exact_zero_target_jump_net"])
        or int(formal["normal_arrival_deadline_step"]) != 25
        or int(formal["normal_hold_through_step"]) != 35
        or int(formal["weak_arrival_deadline_step"]) != 27
        or int(formal["weak_hold_through_step"]) != 37
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or int(formal["arrival_streak_steps"]) != 3
        or bool(formal["arrival_deadline_expansion_allowed"])
        or tuple(
            int(matrix[key]) for key in (
                "training_contexts", "calibration_contexts", "holdout_contexts",
                "rollouts_per_context", "training_rollouts",
                "calibration_rollouts", "holdout_rollouts", "total_real_rollouts",
            )
        ) != (24, 8, 8, 25, 600, 200, 200, 1000)
        or bool(matrix["authorized_by_s23"])
        or tuple(
            int(gate[key]) for key in (
                "source_raw_authentication_required",
                "baseline_authentication_required",
                "probe_authentication_required",
                "fixed_basis_contexts_required",
                "finite_constructions_required",
                "issue_gate_pass_required",
                "cancellation_gate_pass_required",
                "central_sign_gate_pass_required",
                "global_rank_condition_contexts_required",
                "slot_rank_condition_blocks_required",
                "late_novelty_contexts_required",
            )
        ) != (360, 40, 320, 40, 7680, 3840, 3840, 1280, 40, 160, 40)
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["read_raw_in_place"])
        or int(execution["new_raw_count"]) != 0
        or bool(execution["ray_executed"])
        or bool(execution["gotsc_executed"])
        or bool(execution["tsc_executed"])
        or int(execution["plant_steps_executed"]) != 0
        or bool(execution["controller_executed"])
        or bool(execution["snapshot_creation_allowed"])
        or bool(scope["s21_or_s22_result_changed"])
        or bool(scope["plant_response_simulated"])
        or bool(scope["real_mpc_executed"])
        or bool(scope["global_plant_reachability_claimed"])
        or bool(scope["hidden_history_robustness_claimed"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S23 frozen design changed")


def _sylvester_hadamard(order: int = 16) -> np.ndarray:
    if order != 16:
        raise ValueError("S23 Hadamard order changed")
    output = np.ones((1, 1), dtype=int)
    seed = np.asarray([[1, 1], [1, -1]], dtype=int)
    for _ in range(4):
        output = np.kron(output, seed)
    if (
        output.shape != (16, 16)
        or not np.array_equal(output @ output.T, 16 * np.eye(16, dtype=int))
        or set(np.unique(output)) != {-1, 1}
    ):
        raise ValueError("S23 Sylvester matrix construction failed")
    return output


def _sequence_matrix() -> np.ndarray:
    primary = _sylvester_hadamard()
    output = np.vstack((primary, -primary[:8]))
    if (
        output.shape != (24, 16)
        or int(np.linalg.matrix_rank(output)) != 16
        or not np.array_equal(output[16:], -output[:8])
    ):
        raise ValueError("S23 sequence matrix changed")
    return output


def _normalized_condition(matrix: np.ndarray) -> float:
    values = np.asarray(matrix, dtype=float)
    norms = np.linalg.norm(values, axis=0)
    if (
        values.ndim != 2 or not np.all(np.isfinite(values))
        or not np.all(np.isfinite(norms)) or np.any(norms <= 0.0)
    ):
        return math.inf
    return float(np.linalg.cond(values / norms))


def _matrix_metrics(actual: np.ndarray, cfg: Mapping[str, Any]) -> dict[str, Any]:
    schedule = cfg["schedule_contract"]
    matrix = np.asarray(actual, dtype=float)
    if matrix.shape != (24, 16) or not np.all(np.isfinite(matrix)):
        return {
            "global_rank": 0,
            "global_raw_condition": math.inf,
            "global_normalized_condition": math.inf,
            "slot_rows": [],
            "late_column_residuals": [],
            "global_pass": False,
            "slot_pass_count": 0,
            "late_novelty_pass": False,
        }
    rank = int(np.linalg.matrix_rank(matrix))
    raw_condition = float(np.linalg.cond(matrix))
    condition = _normalized_condition(matrix)
    slot_rows = []
    for slot in range(4):
        block = matrix[:, 4 * slot:4 * slot + 4]
        slot_rank = int(np.linalg.matrix_rank(block))
        slot_condition = _normalized_condition(block)
        slot_rows.append({
            "slot": slot,
            "rank": slot_rank,
            "raw_condition": float(np.linalg.cond(block)),
            "normalized_condition": slot_condition,
            "passed": bool(
                slot_rank == int(schedule["required_slot_rank"])
                and slot_condition
                <= float(schedule["maximum_slot_normalized_condition"]) + 1e-12
            ),
        })
    slot0 = matrix[:, :4]
    projector = slot0 @ np.linalg.pinv(slot0)
    late_residuals = []
    for column in range(4, 16):
        value = matrix[:, column]
        residual = float(
            np.linalg.norm(value - projector @ value)
            / max(float(np.linalg.norm(value)), 1e-300)
        )
        late_residuals.append(residual)
    global_pass = bool(
        rank == int(schedule["required_global_rank"])
        and math.isfinite(condition)
        and condition
        <= float(schedule["maximum_global_normalized_condition"]) + 1e-12
    )
    late_pass = bool(
        len(late_residuals) == 12
        and min(late_residuals)
        >= float(schedule["minimum_late_column_residual_outside_slot0_span"])
        - 1e-12
    )
    return {
        "global_rank": rank,
        "global_raw_condition": raw_condition,
        "global_normalized_condition": condition,
        "slot_rows": slot_rows,
        "late_column_residuals": late_residuals,
        "global_pass": global_pass,
        "slot_pass_count": sum(bool(row["passed"]) for row in slot_rows),
        "late_novelty_pass": late_pass,
    }


def _authenticate_s22(output: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_contract"]
    if output.name != str(source["s22_output_name"]):
        raise ValueError("immutable S22 output name mismatch")
    paths = {
        "detailed": output / "stage4_2r3c3t13s22_affine_authority_v1.json",
        "summary": output / "stage4_2r3c3t13s22_summary_v1.json",
        "manifest": output / "stage4_2r3c3t13s22_manifest_v1.json",
        "independent_postprocess": output / "server_independent_postprocess.json",
    }
    expected = {
        "detailed": source["s22_detailed_sha256"],
        "summary": source["s22_summary_sha256"],
        "manifest": source["s22_manifest_sha256"],
        "independent_postprocess": source["s22_independent_postprocess_sha256"],
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if any(hashes[name] != str(value) for name, value in expected.items()):
        raise ValueError("immutable S22 artifact SHA-256 mismatch")
    detailed = _read_json(paths["detailed"])
    summary = _read_json(paths["summary"])
    post = _read_json(paths["independent_postprocess"])
    if (
        detailed.get("route") != source["required_s22_route"]
        or summary.get("route") != source["required_s22_route"]
        or post.get("route") != source["required_s22_route"]
        or bool(detailed.get("primary_pass"))
        or bool(summary.get("primary_pass"))
        or bool(post.get("primary_pass"))
        or int(summary.get("optimistic_affine_formal_feasibility", -1))
        != int(source["required_s22_optimistic_affine_feasible"])
        or int(post.get("primary_gate_counts", {}).get(
            "optimistic_affine_formal_feasibility", -1
        )) != int(source["required_s22_optimistic_affine_feasible"])
        or not bool(post.get("passed"))
        or int(post.get("new_tsc_ray_plant_controller_or_snapshot_count", -1)) != 0
    ):
        raise ValueError("S22 scientific route changed")
    return {"paths": {key: str(value) for key, value in paths.items()}, "hashes": hashes}


def _payload_for_baseline(ctx: Any, baseline: Mapping[str, Any]) -> tuple[dict[str, Any], Path]:
    experiment_id = str(baseline["experiment_id"])
    path = ctx.paths.variants / f"payload_{experiment_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"S21 baseline payload missing: {experiment_id}")
    return _read_json(path), path


def _basis_and_actuator(
    ctx: Any, baseline: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, Any, dict[str, Any]]:
    s21 = s22.s21
    trace = baseline["controller_trace"]
    recorded = [
        row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc") or []
        for row in trace[:21]
    ]
    field_rows = np.asarray(recorded[0], dtype=float) if recorded else np.empty((0, 0))
    constant = bool(
        len(recorded) == 21
        and field_rows.shape == (4, N_COILS)
        and all(row == recorded[0] for row in recorded)
    )
    if not constant:
        raise ValueError("S21 fixed field basis is not constant through S23 knots")
    if tuple(ctx.base_ctx.cfg["active_calibration"]["pulse_directions"]) != DIRECTIONS:
        raise ValueError("S21 active-calibration QR direction order changed")
    field_basis = field_rows.T
    field_norms = np.linalg.norm(field_basis, axis=0)
    field_rank = int(np.linalg.matrix_rank(field_basis))
    field_condition = float(np.linalg.cond(field_basis / field_norms))
    payload, payload_path = _payload_for_baseline(ctx, baseline)
    turns = s21.s16.s13._turns_tsc(payload)
    minimum, maximum = s21.s16.s13._current_limits_tsc(payload)
    max_delta = float(payload["max_delta_a"])
    lattice_cfg = ctx.base_ctx.cfg["lattice_probe"]
    actuator = s21.s16.s9.QuantizedActuatorModel(
        minimum_current_a_tsc=tuple(map(float, minimum)),
        maximum_current_a_tsc=tuple(map(float, maximum)),
        max_slew_step_a=max_delta,
        turns_tsc=tuple(map(float, turns)),
        bias_grid_units_tsc=tuple(map(float, lattice_cfg["readback_bias_grid_units_tsc"])),
        uncertainty_radius_grid_units_tsc=tuple(
            map(float, lattice_cfg["readback_radius_grid_units_tsc"])
        ),
    )
    return (
        field_basis,
        turns,
        minimum,
        maximum,
        max_delta,
        actuator,
        {
            "fixed_basis_rank": field_rank,
            "fixed_basis_normalized_condition": field_condition,
            "fixed_basis_constant_through_state20": constant,
            "payload_path": str(payload_path),
            "payload_sha256": _sha256(payload_path),
        },
    )


def _decimal_vector(values: Sequence[float]) -> tuple[Decimal, ...]:
    return tuple(Decimal(str(float(value))) for value in values)


def _construct_event(
    *, ctx: Any, baseline: Mapping[str, Any], sequence: int, slot: int,
    signs: np.ndarray, field_basis: np.ndarray, turns: np.ndarray,
    minimum: np.ndarray, maximum: np.ndarray, max_delta: float,
    actuator: Any, cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], np.ndarray]:
    s21 = s22.s21
    schedule = cfg["schedule_contract"]
    lattice_cfg = ctx.base_ctx.cfg["lattice_probe"]
    issue_step = ISSUE_STEPS[slot]
    cancel_step = CANCEL_STEPS[slot]
    trajectory = baseline["trajectory"]
    trace = baseline["controller_trace"]
    issue_current = np.asarray(trajectory[issue_step]["currents_a_tsc"], dtype=float)
    issue_baseline_action = np.asarray(
        trace[issue_step]["r3c3t13s9_baseline_action_norm_tsc"], dtype=float
    )
    issue_center_fields = tuple(
        map(str, trace[issue_step]["r3c3t13s9_center_card15_fields"])
    )
    replay_center = actuator.apply(issue_current, issue_baseline_action)
    center_reproduction = list(replay_center.card15_fields) == list(issue_center_fields)
    desired_coordinate = (
        float(schedule["coordinate_amplitude"])
        * np.asarray(signs[4 * slot:4 * slot + 4], dtype=float)
    )
    desired_field = field_basis @ desired_coordinate
    target_fields, actual_decimal, integer_counts = s21._dynamic_exact_target(
        issue_center_fields,
        _decimal_vector(desired_field),
        search_radius=int(schedule["dynamic_exact_search_radius"]),
    )
    issue_action = s21.s16.s9.exact_stored_center_action(
        stored_fields=target_fields,
        measured_current_a_tsc=issue_current,
        baseline_action_norm_tsc=issue_baseline_action,
        turns_tsc=turns,
        max_slew_step_a=max_delta,
        minimum_current_a_tsc=minimum,
        maximum_current_a_tsc=maximum,
        cfg=lattice_cfg,
    )
    issued = actuator.apply(issue_current, issue_action["action_norm_tsc"])
    target_reproduction = list(issued.card15_fields) == list(target_fields)
    actual_field = np.asarray([float(value) for value in actual_decimal], dtype=float)
    current_basis = field_basis * 1000.0 / turns[:, None]
    actual_current = actual_field * 1000.0 / turns
    desired_current = current_basis @ desired_coordinate
    coordinate, _, _, _ = np.linalg.lstsq(current_basis, actual_current, rcond=None)
    reconstructed = current_basis @ coordinate
    actual_norm = float(np.linalg.norm(actual_current))
    desired_norm = float(np.linalg.norm(desired_current))
    cosine = float(
        np.dot(desired_current, actual_current)
        / max(desired_norm * actual_norm, 1e-300)
    )
    off_basis = float(
        np.linalg.norm(actual_current - reconstructed) / max(actual_norm, 1e-300)
    )
    coordinate_error = np.abs(coordinate - desired_coordinate)
    coordinate_pass = bool(
        np.all(np.sign(coordinate) == np.sign(desired_coordinate))
        and np.all(
            np.abs(coordinate)
            >= float(schedule["minimum_absolute_applied_coordinate"]) - 1e-12
        )
        and np.all(
            np.abs(coordinate)
            <= float(schedule["maximum_absolute_applied_coordinate"]) + 1e-12
        )
        and float(np.max(coordinate_error))
        <= float(schedule["maximum_absolute_coordinate_error"]) + 1e-12
        and cosine
        >= float(schedule["minimum_desired_applied_current_cosine"]) - 1e-12
        and off_basis
        <= float(schedule["maximum_relative_off_basis_residual"]) + 1e-12
    )
    action_pass = bool(
        issue_action["passed"]
        and center_reproduction
        and target_reproduction
        and not any(issued.action_saturated)
        and not any(issued.current_limit_clipped)
        and len(target_fields) == N_COILS
        and all(len(field) == 10 for field in target_fields)
        and float(issue_action["incremental_normalized_action_linf"])
        <= float(schedule["maximum_incremental_normalized_action_linf"]) + 1e-12
        and float(issue_action["total_normalized_action_abs"])
        <= float(schedule["maximum_total_normalized_action_abs"]) + 1e-12
        and float(issue_action["predicted_maximum_current_utilization"])
        <= float(schedule["maximum_current_utilization"]) + 1e-12
        and coordinate_pass
    )

    cancel_current = np.asarray(trajectory[cancel_step]["currents_a_tsc"], dtype=float)
    cancel_baseline_action = np.asarray(
        trace[cancel_step]["r3c3t13s9_baseline_action_norm_tsc"], dtype=float
    )
    cancel_action = s21.s16.s9.exact_stored_center_action(
        stored_fields=issue_center_fields,
        measured_current_a_tsc=cancel_current,
        baseline_action_norm_tsc=cancel_baseline_action,
        turns_tsc=turns,
        max_slew_step_a=max_delta,
        minimum_current_a_tsc=minimum,
        maximum_current_a_tsc=maximum,
        cfg=lattice_cfg,
    )
    cancelled = actuator.apply(cancel_current, cancel_action["action_norm_tsc"])
    cancellation_target_exact = list(cancelled.card15_fields) == list(issue_center_fields)
    center_decimal = tuple(s21.s16.s9._decimal_field(value) for value in issue_center_fields)
    target_decimal = tuple(s21.s16.s9._decimal_field(value) for value in target_fields)
    cancel_decimal = tuple(s21.s16.s9._decimal_field(value) for value in cancelled.card15_fields)
    zero_net = all(
        (target - center) + (cancel - target) == 0
        for center, target, cancel in zip(center_decimal, target_decimal, cancel_decimal)
    )
    cancellation_pass = bool(
        cancel_action["passed"]
        and cancellation_target_exact
        and zero_net
        and not any(cancelled.action_saturated)
        and not any(cancelled.current_limit_clipped)
        and float(cancel_action["incremental_normalized_action_linf"])
        <= float(schedule["maximum_incremental_normalized_action_linf"]) + 1e-12
        and float(cancel_action["total_normalized_action_abs"])
        <= float(schedule["maximum_total_normalized_action_abs"]) + 1e-12
        and float(cancel_action["predicted_maximum_current_utilization"])
        <= float(schedule["maximum_current_utilization"]) + 1e-12
    )
    finite = bool(
        np.all(np.isfinite(desired_coordinate))
        and np.all(np.isfinite(coordinate))
        and np.all(np.isfinite(actual_field))
        and math.isfinite(cosine)
        and math.isfinite(off_basis)
    )
    row = {
        "sequence_index": sequence,
        "slot": slot,
        "issue_task_step": issue_step,
        "cancel_task_step": cancel_step,
        "schedule_signs": list(map(int, signs[4 * slot:4 * slot + 4])),
        "desired_coordinate": desired_coordinate.tolist(),
        "actual_coordinate": coordinate.tolist(),
        "maximum_absolute_coordinate_error": float(np.max(coordinate_error)),
        "desired_applied_current_cosine": cosine,
        "relative_off_basis_residual": off_basis,
        "issue_center_fields": list(issue_center_fields),
        "issue_target_fields": list(target_fields),
        "issue_integer_grid_counts": list(integer_counts),
        "issue_incremental_normalized_action_linf": float(
            issue_action["incremental_normalized_action_linf"]
        ),
        "issue_total_normalized_action_abs": float(
            issue_action["total_normalized_action_abs"]
        ),
        "issue_predicted_current_utilization": float(
            issue_action["predicted_maximum_current_utilization"]
        ),
        "center_reproduction": center_reproduction,
        "target_reproduction": target_reproduction,
        "coordinate_geometry_pass": coordinate_pass,
        "issue_gate_pass": action_pass,
        "cancel_target_fields": list(cancelled.card15_fields),
        "cancel_incremental_normalized_action_linf": float(
            cancel_action["incremental_normalized_action_linf"]
        ),
        "cancel_total_normalized_action_abs": float(
            cancel_action["total_normalized_action_abs"]
        ),
        "cancel_predicted_current_utilization": float(
            cancel_action["predicted_maximum_current_utilization"]
        ),
        "cancellation_target_exact": cancellation_target_exact,
        "exact_zero_target_jump_net": zero_net,
        "cancellation_gate_pass": cancellation_pass,
        "finite_issue_and_cancellation": finite,
    }
    return row, coordinate


def _context_replay(
    ctx: Any, baseline: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sequence_matrix = _sequence_matrix()
    (
        field_basis, turns, minimum, maximum, max_delta, actuator, basis_audit,
    ) = _basis_and_actuator(ctx, baseline)
    actual = np.zeros((24, 16), dtype=float)
    rows = []
    by_sequence_slot: dict[tuple[int, int], dict[str, Any]] = {}
    for sequence in range(24):
        for slot in range(4):
            row, coordinate = _construct_event(
                ctx=ctx, baseline=baseline, sequence=sequence, slot=slot,
                signs=sequence_matrix[sequence], field_basis=field_basis,
                turns=turns, minimum=minimum, maximum=maximum,
                max_delta=max_delta, actuator=actuator, cfg=cfg,
            )
            rows.append(row)
            by_sequence_slot[(sequence, slot)] = row
            actual[sequence, 4 * slot:4 * slot + 4] = coordinate
    matrix = _matrix_metrics(actual, cfg)
    central_rows = []
    s21 = s22.s21
    for primary in range(8):
        sentinel = 16 + primary
        for slot in range(4):
            plus = by_sequence_slot[(primary, slot)]
            minus = by_sequence_slot[(sentinel, slot)]
            center = tuple(
                s21.s16.s9._decimal_field(value)
                for value in plus["issue_center_fields"]
            )
            plus_target = tuple(
                s21.s16.s9._decimal_field(value)
                for value in plus["issue_target_fields"]
            )
            minus_target = tuple(
                s21.s16.s9._decimal_field(value)
                for value in minus["issue_target_fields"]
            )
            passed = bool(
                plus["issue_center_fields"] == minus["issue_center_fields"]
                and all(
                    positive + negative == 2 * middle
                    for positive, negative, middle in zip(
                        plus_target, minus_target, center
                    )
                )
            )
            central_rows.append({
                "primary_sequence": primary,
                "sentinel_sequence": sentinel,
                "slot": slot,
                "decimal_exact_target_symmetry": passed,
            })
    spec = baseline["spec"]
    basis_pass = bool(
        basis_audit["fixed_basis_rank"] == 4
        and basis_audit["fixed_basis_constant_through_state20"]
        and basis_audit["fixed_basis_normalized_condition"]
        <= float(ctx.base_ctx.cfg["lattice_probe"][
            "maximum_fixed_field_basis_condition"
        ]) + 1e-12
    )
    context = {
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "partition": str(spec["partition"]),
        "baseline_experiment_id": str(baseline["experiment_id"]),
        "baseline_raw_sha256": str(baseline["_s22_raw_sha256"]),
        "basis_audit": basis_audit,
        "basis_pass": basis_pass,
        "finite_construction_count": 2 * sum(
            bool(row["finite_issue_and_cancellation"]) for row in rows
        ),
        "issue_gate_pass_count": sum(bool(row["issue_gate_pass"]) for row in rows),
        "cancellation_gate_pass_count": sum(
            bool(row["cancellation_gate_pass"]) for row in rows
        ),
        "central_sign_gate_pass_count": sum(
            bool(row["decimal_exact_target_symmetry"]) for row in central_rows
        ),
        "central_sign_rows": central_rows,
        "matrix_metrics": matrix,
        "maximum_issue_incremental_normalized_action_linf": max(
            float(row["issue_incremental_normalized_action_linf"]) for row in rows
        ),
        "maximum_cancel_incremental_normalized_action_linf": max(
            float(row["cancel_incremental_normalized_action_linf"]) for row in rows
        ),
        "maximum_total_normalized_action_abs": max(
            max(
                float(row["issue_total_normalized_action_abs"]),
                float(row["cancel_total_normalized_action_abs"]),
            ) for row in rows
        ),
        "maximum_predicted_current_utilization": max(
            max(
                float(row["issue_predicted_current_utilization"]),
                float(row["cancel_predicted_current_utilization"]),
            ) for row in rows
        ),
        "maximum_absolute_coordinate_error": max(
            float(row["maximum_absolute_coordinate_error"]) for row in rows
        ),
        "minimum_desired_applied_current_cosine": min(
            float(row["desired_applied_current_cosine"]) for row in rows
        ),
        "maximum_relative_off_basis_residual": max(
            float(row["relative_off_basis_residual"]) for row in rows
        ),
    }
    for row in rows:
        row.update({
            "pair_id": context["pair_id"],
            "history_member": context["history_member"],
            "baseline_experiment_id": context["baseline_experiment_id"],
        })
    return context, rows


def _primary_counts(contexts: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "fixed_basis_contexts": sum(bool(row["basis_pass"]) for row in contexts),
        "finite_constructions": sum(int(row["finite_construction_count"]) for row in contexts),
        "issue_gate_pass": sum(int(row["issue_gate_pass_count"]) for row in contexts),
        "cancellation_gate_pass": sum(
            int(row["cancellation_gate_pass_count"]) for row in contexts
        ),
        "central_sign_gate_pass": sum(
            int(row["central_sign_gate_pass_count"]) for row in contexts
        ),
        "global_rank_condition_contexts": sum(
            bool(row["matrix_metrics"]["global_pass"]) for row in contexts
        ),
        "slot_rank_condition_blocks": sum(
            int(row["matrix_metrics"]["slot_pass_count"]) for row in contexts
        ),
        "late_novelty_contexts": sum(
            bool(row["matrix_metrics"]["late_novelty_pass"]) for row in contexts
        ),
    }


def _route(
    source_count: int, reproduction: Mapping[str, int], primary: Mapping[str, int],
    cfg: Mapping[str, Any],
) -> tuple[bool, str]:
    gate = cfg["primary_gate"]
    passed = bool(
        source_count == int(gate["source_raw_authentication_required"])
        and reproduction["baseline_formal_reproduction_count"]
        == int(gate["baseline_authentication_required"])
        and reproduction["measured_probe_formal_reproduction_count"]
        == int(gate["probe_authentication_required"])
        and primary["fixed_basis_contexts"]
        == int(gate["fixed_basis_contexts_required"])
        and primary["finite_constructions"]
        == int(gate["finite_constructions_required"])
        and primary["issue_gate_pass"]
        == int(gate["issue_gate_pass_required"])
        and primary["cancellation_gate_pass"]
        == int(gate["cancellation_gate_pass_required"])
        and primary["central_sign_gate_pass"]
        == int(gate["central_sign_gate_pass_required"])
        and primary["global_rank_condition_contexts"]
        == int(gate["global_rank_condition_contexts_required"])
        and primary["slot_rank_condition_blocks"]
        == int(gate["slot_rank_condition_blocks_required"])
        and primary["late_novelty_contexts"]
        == int(gate["late_novelty_contexts_required"])
    )
    return passed, str(cfg["routes"]["pass" if passed else "fail"])


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    s22._load_s21_module()
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    source_run = args.source_s21_run.expanduser().resolve()
    source_s22 = args.source_s22_output.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("T13S23 output directory must be new")
    if (
        output == source_run or source_run in output.parents
        or output == source_s22 or source_s22 in output.parents
    ):
        raise ValueError("T13S23 output must remain outside immutable source evidence")
    s21 = s22.s21
    ctx = s21.load_config(
        args.source_s21_config.expanduser().resolve(),
        source_stage42r3b_run=args.source_stage42r3b_run,
        source_stage42r3c3_run=args.source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=args.source_stage42r3c3t3_controller_bank,
        q1_run=args.q1_run,
        q2_run=args.q2_run,
        q1_audit=args.q1_audit,
        q2_audit=args.q2_audit,
        r3b_server_audit=args.r3b_server_audit,
        r3b_snapshot_checks=args.r3b_snapshot_checks,
        run_dir=source_run,
    )
    authenticated = s22._authenticate_source(ctx, config_path, cfg)
    contexts, reproduction = s22._load_and_authenticate_raw(
        ctx, authenticated["phase_formal_map"]
    )
    source = cfg["source_contract"]
    if (
        reproduction["baseline_formal_pass_count"]
        != int(source["expected_baseline_formal_pass_count"])
        or reproduction["measured_probe_formal_pass_count"]
        != int(source["expected_probe_formal_pass_count"])
    ):
        raise ValueError("S21 frozen formal pass counts changed")
    s22_auth = _authenticate_s22(source_s22, cfg)

    context_rows = []
    event_rows = []
    for key in sorted(contexts):
        context, events = _context_replay(ctx, contexts[key]["baseline"], cfg)
        context_rows.append(context)
        event_rows.extend(events)
    primary = _primary_counts(context_rows)
    source_count = int(authenticated["raw_inventory"]["count"])
    primary_pass, route = _route(source_count, reproduction, primary, cfg)
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(config_path),
        "source_s21_run": str(source_run),
        "source_s22_output": str(source_s22),
        "source_s21_file_hashes": authenticated["source_file_hashes"],
        "source_s22_hashes": s22_auth["hashes"],
        "s21_raw_inventory_digest": authenticated["raw_inventory"]["digest"],
        "sequence_matrix_digest": _digest(_sequence_matrix().tolist()),
        "formal_timing_changed": False,
    }
    provenance_digest = _digest(provenance)
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "read_only_sequential_hadamard_card15_lattice_preflight",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "source_authentication": {
            "s21_raw_inventory": authenticated["raw_inventory"],
            "s21_raw_authentication_count": source_count,
            "s22": s22_auth,
            "passed": source_count == 360,
        },
        "formal_reproduction": reproduction,
        "sequence_matrix": _sequence_matrix().tolist(),
        "primary_gate_counts": primary,
        "context_rows": context_rows,
        "event_rows": event_rows,
        "primary_pass": primary_pass,
        "route": route,
        "scientific_guardrails": cfg["scientific_scope"],
        "execution": cfg["execution_contract"],
        "audit_complete": True,
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "source_raw_authentication_count": source_count,
        **reproduction,
        **primary,
        "context_count": len(context_rows),
        "event_row_count": len(event_rows),
        "maximum_global_normalized_condition": max(
            float(row["matrix_metrics"]["global_normalized_condition"])
            for row in context_rows
        ),
        "maximum_slot_normalized_condition": max(
            float(slot["normalized_condition"])
            for row in context_rows for slot in row["matrix_metrics"]["slot_rows"]
        ),
        "minimum_late_column_residual": min(
            min(map(float, row["matrix_metrics"]["late_column_residuals"]))
            for row in context_rows
        ),
        "maximum_incremental_normalized_action_linf": max(
            max(
                float(row["maximum_issue_incremental_normalized_action_linf"]),
                float(row["maximum_cancel_incremental_normalized_action_linf"]),
            ) for row in context_rows
        ),
        "maximum_total_normalized_action_abs": max(
            float(row["maximum_total_normalized_action_abs"]) for row in context_rows
        ),
        "maximum_predicted_current_utilization": max(
            float(row["maximum_predicted_current_utilization"]) for row in context_rows
        ),
        "maximum_absolute_coordinate_error": max(
            float(row["maximum_absolute_coordinate_error"]) for row in context_rows
        ),
        "minimum_desired_applied_current_cosine": min(
            float(row["minimum_desired_applied_current_cosine"]) for row in context_rows
        ),
        "maximum_relative_off_basis_residual": max(
            float(row["maximum_relative_off_basis_residual"]) for row in context_rows
        ),
        "primary_pass": primary_pass,
        "route": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "action_schedule_design_result": "pass" if primary_pass else "fail",
            "real_tsc_or_plant_executed": False,
            "real_controller_or_mpc_executed": False,
            "real_closed_loop_conclusion": "not_tested",
            "global_plant_reachability_conclusion": "not_tested",
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    detailed_path = output / "stage4_2r3c3t13s23_sequential_lattice_preflight_v1.json"
    summary_path = output / "stage4_2r3c3t13s23_summary_v1.json"
    _write_json(detailed_path, detailed)
    _write_json(summary_path, summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "output_files": [
            {
                "path": detailed_path.name,
                "size_bytes": detailed_path.stat().st_size,
                "sha256": _sha256(detailed_path),
            },
            {
                "path": summary_path.name,
                "size_bytes": summary_path.stat().st_size,
                "sha256": _sha256(summary_path),
            },
        ],
        "source_raw_files_copied_or_modified": 0,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
    }
    manifest_path = output / "stage4_2r3c3t13s23_manifest_v1.json"
    _write_json(manifest_path, manifest)
    return {
        "output": str(output),
        "detailed_sha256": _sha256(detailed_path),
        "summary_sha256": _sha256(summary_path),
        "manifest_sha256": _sha256(manifest_path),
        **summary,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-s21-config", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s22-output", type=Path, required=True)
    for name in (
        "source-stage42r3b-run",
        "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank",
        "q1-run",
        "q2-run",
        "q1-audit",
        "q2-audit",
        "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    result = run_audit(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
