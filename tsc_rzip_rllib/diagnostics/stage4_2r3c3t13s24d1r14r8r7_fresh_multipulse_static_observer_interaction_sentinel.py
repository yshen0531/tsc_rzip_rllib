"""Frozen contract for the R8R7 fresh multipulse interaction sentinel."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R8R7"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel"
IDENTITY = "fresh_multipulse_static_observer_interaction_sentinel_v1"
CONTROLLER_REVISION = "exact_card15_fixed_canonical_multipulse_v42r3c3t13s24d1r14r8r7_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r7_fresh_multipulse_interaction_v1"
DESIGN_SHA256 = "a2d2abda8189ff475455ae945391948ede937ba49ab559d79f1c48c74e80067f"
ISSUE_STEPS = (10, 14, 18, 22)
SCHEDULES = (
    ((0, 1, 2, 3), (1, -1, 1, -1)),
    ((3, 2, 1, 0), (1, -1, 1, -1)),
)
FRESH_PAIRS = (
    "p5_q1_a0p900_gap3_settle4",
    "p5_q2_a0p750_gap3_settle4",
    "p9_q1_a0p900_gap3_settle4",
    "p9_q2_a0p750_gap3_settle4",
    "p5_q1_a0p750_gap4_settle4",
    "p5_q2_a0p900_gap4_settle4",
    "p9_q1_a0p750_gap4_settle4",
    "p9_q2_a0p900_gap4_settle4",
)
MATRIX_DIGEST = "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _matrix_digest(value: Any) -> str:
    matrix = np.asarray(value, dtype="<f8", order="C")
    return hashlib.sha256(matrix.tobytes(order="C")).hexdigest()


def validate_config(cfg: Mapping[str, Any], *, project_root: Path | None = None) -> None:
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("design_document_sha256") != DESIGN_SHA256
    ):
        raise ValueError("R8R7 frozen identity changed")
    if project_root is not None:
        design = project_root / str(cfg["design_document"])
        if not design.is_file() or _sha(design) != DESIGN_SHA256:
            raise ValueError("R8R7 design document changed")
        for key in ("source_r8", "source_r8r1", "source_r8r6"):
            path = project_root / str(cfg[f"{key}_config"])
            if not path.is_file() or _sha(path) != str(cfg[f"{key}_config_sha256"]):
                raise ValueError(f"R8R7 {key} config changed")

    rollout = cfg.get("rollout_contract") or {}
    if (
        tuple(map(int, rollout.get("issue_task_steps") or ())) != ISSUE_STEPS
        or int(rollout.get("pair_count", -1)) != 8
        or int(rollout.get("histories_per_pair", -1)) != 2
        or int(rollout.get("context_count", -1)) != 16
        or int(rollout.get("baseline_rollouts", -1)) != 16
        or int(rollout.get("multipulse_schedules_per_context", -1)) != 2
        or int(rollout.get("multipulse_rollouts", -1)) != 32
        or int(rollout.get("maximum_new_rollouts", -1)) != 48
        or int(rollout.get("cancel_step_offset", -1)) != 1
        or int(rollout.get("zero_after_cancel_step_offset", -1)) != 2
        or int(rollout.get("issue_windows", -1)) != 128
        or int(rollout.get("forecast_horizon_steps", -1)) != 4
        or int(rollout.get("delegated_last_task_step", -1)) != 9
    ):
        raise ValueError("R8R7 rollout contract changed")
    if tuple(map(str, cfg.get("fresh_pairs") or ())) != FRESH_PAIRS:
        raise ValueError("R8R7 fresh pair partition changed")

    schedule = cfg.get("schedule_contract") or {}
    actual_schedules = tuple(
        (
            tuple(map(int, (schedule.get(name) or {}).get("directions") or ())),
            tuple(map(int, (schedule.get(name) or {}).get("signs") or ())),
        )
        for name in ("schedule_a", "schedule_b")
    )
    if (
        actual_schedules != SCHEDULES
        or schedule.get("canonical_matrix_digest") != MATRIX_DIGEST
        or _matrix_digest(schedule.get("canonical_matrix_columns")) != MATRIX_DIGEST
        or float(schedule.get("canonical_scale", -1.0)) != 1.0
        or float(schedule.get("coordinate_absolute_tolerance", -1.0)) != 1e-15
    ):
        raise ValueError("R8R7 schedule or canonical matrix changed")

    controller = cfg.get("controller_contract") or {}
    expected_controller = {
        "maximum_incremental_normalized_action_linf": 0.25,
        "maximum_online_cancel_incremental_linf": 0.24,
        "maximum_total_normalized_action_abs": 1.0,
        "maximum_current_utilization": 0.55,
        "minimum_desired_applied_current_cosine": 0.98,
        "maximum_relative_off_basis_residual": 0.1,
    }
    if any(float(controller.get(key, -1.0)) != value for key, value in expected_controller.items()):
        raise ValueError("R8R7 action safety bounds changed")
    required = (
        "require_exact_stored_center_cancellation",
        "require_exact_zero_target_jump_net",
        "require_exact_source_prefix",
        "require_fresh_controller",
        "require_fresh_tsc_process",
        "forbid_future_r17_controller_execution",
    )
    if not all(controller.get(key) is True for key in required):
        raise ValueError("R8R7 fail-closed controller requirement changed")

    static = cfg.get("static_model_contract") or {}
    response = cfg.get("response_model_contract") or {}
    if (
        static != {
            "family": "linear",
            "pca_rank": 32,
            "ridge": 1e-6,
            "adaptation_enabled": False,
            "candidate_selection_allowed": False,
        }
        or int(response.get("pca_rank", -1)) != 4
        or float(response.get("bandwidth_multiplier", -1.0)) != 2.0
        or float(response.get("ridge", -1.0)) != 0.1
        or int(response.get("relative_lag_horizon", -1)) != 4
        or int(response.get("training_response_count", -1)) != 912
        or int(response.get("training_pair_count", -1)) != 12
        or response.get("candidate_selection_allowed") is not False
        or response.get("full_data_fit_validation_claim") is not False
    ):
        raise ValueError("R8R7 frozen predictor changed")

    tube = cfg.get("tube_contract") or {}
    if (
        tube.get("response_method")
        != "physical_floor_plus_two_times_lag_component_oof_max"
        or float(tube.get("response_multiplier", -1.0)) != 2.0
        or tuple(map(float, tube.get("response_floor_physical") or ()))
        != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or tube.get("combined_method") != "componentwise_static_plus_response"
        or tuple(map(float, tube.get("combined_caps_physical") or ()))
        != (0.01, 0.01, 0.05, 0.05, 3000.0)
        or tube.get("raw_dependent_widening_allowed") is not False
    ):
        raise ValueError("R8R7 tube contract changed")

    gates = cfg.get("gates") or {}
    exact_counts = {
        "baseline_required_point_pass_count": 61,
        "baseline_required_tube_pass_count": 61,
        "baseline_per_context_point_pass_count": 3,
        "baseline_per_context_tube_pass_count": 3,
        "multipulse_required_point_pass_count": 116,
        "multipulse_required_tube_pass_count": 116,
        "multipulse_per_context_point_pass_count": 7,
        "multipulse_per_context_tube_pass_count": 7,
        "multipulse_per_direction_point_pass_count": 28,
        "multipulse_per_direction_tube_pass_count": 28,
        "multipulse_per_sign_point_pass_count": 56,
        "multipulse_per_sign_tube_pass_count": 56,
    }
    if (
        tuple(map(float, gates.get("component_caps_physical") or ()))
        != (0.003, 0.003, 0.02, 0.02, 1000.0)
        or tuple(map(float, gates.get("finite_exclusion_caps_physical") or ()))
        != (0.01, 0.01, 0.05, 0.05, 3000.0)
        or any(int(gates.get(key, -1)) != value for key, value in exact_counts.items())
    ):
        raise ValueError("R8R7 qualification gates changed")
    formal = cfg.get("formal_timing_contract") or {}
    if (
        int(formal.get("normal_arrival_deadline_step", -1)) != 25
        or int(formal.get("normal_hold_through_step", -1)) != 35
        or int(formal.get("weak_arrival_deadline_step", -1)) != 27
        or int(formal.get("weak_hold_through_step", -1)) != 37
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or formal.get("formal_tracking_diagnostic_only") is not True
    ):
        raise ValueError("R8R7 formal timing changed")
    if (
        cfg.get("all_stage_trajectories_allowed_in_expert_dataset") is not False
        or cfg.get("mpc_validated") is not False
        or cfg.get("gate_a_qualified") is not False
        or cfg.get("bc_dagger_or_rl_allowed") is not False
    ):
        raise ValueError("R8R7 scientific scope changed")


def self_test(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(cfg, project_root=config_path.resolve().parents[1])
    directions = [direction for values, _ in SCHEDULES for direction in values]
    signs_by_direction = {
        direction: sorted(
            sign
            for values, signs in SCHEDULES
            for current, sign in zip(values, signs)
            if current == direction
        )
        for direction in range(4)
    }
    if directions.count(0) != 2 or any(values != [-1, 1] for values in signs_by_direction.values()):
        raise AssertionError("R8R7 signed direction coverage changed")
    return {
        "stage": STAGE,
        "context_count": 16,
        "baseline_rollouts": 16,
        "multipulse_rollouts": 32,
        "issue_windows": 128,
        "signed_direction_coverage": signs_by_direction,
        "passed": True,
    }
