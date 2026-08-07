"""Frozen contract for the R8R8 causal discrete-pulse MPC core."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R8R8"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_receding_horizon_mpc_core"
IDENTITY = "causal_four_step_discrete_pulse_receding_horizon_mpc_core_v1"
CONTROLLER_REVISION = "causal_four_step_discrete_pulse_mpc_v42r3c3t13s24d1r14r8r8_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core_v1"
DESIGN_SHA256 = "0906ca9e58126cc2f414f167a685e766d95790ec4f3d28052debb4b5e6db0244"
MATRIX_DIGEST = "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
DECISION_STEPS = (10, 14, 18, 22)
CANDIDATES = (
    ("zero", -1, 0, 0.0),
    ("direction0_minus", 0, -1, 1.0),
    ("direction0_plus", 0, 1, 1.0),
    ("direction1_minus", 1, -1, 1.0),
    ("direction1_plus", 1, 1, 1.0),
    ("direction2_minus", 2, -1, 1.0),
    ("direction2_plus", 2, 1, 1.0),
    ("direction3_minus", 3, -1, 1.0),
    ("direction3_plus", 3, 1, 1.0),
)


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
        raise ValueError("R8R8 frozen identity changed")
    if project_root is not None:
        design = project_root / str(cfg["design_document"])
        source = project_root / str(cfg["source_r8r7_config"])
        if not design.is_file() or _sha(design) != DESIGN_SHA256:
            raise ValueError("R8R8 design document changed")
        if not source.is_file() or _sha(source) != str(cfg["source_r8r7_config_sha256"]):
            raise ValueError("R8R8 source R8R7 config changed")

    rollout = cfg.get("rollout_contract") or {}
    expected_rollout = {
        "context_count": 16,
        "new_rollout_count": 16,
        "decision_count": 64,
        "candidate_count_per_decision": 9,
        "candidate_forecast_count": 576,
        "nonzero_candidate_count_per_decision": 8,
        "pure_issue_construction_count": 512,
        "pure_cancel_construction_count": 512,
        "cancel_step_offset": 1,
        "zero_after_cancel_step_offset": 2,
        "delegated_last_task_step": 9,
        "forecast_horizon_steps": 4,
    }
    if (
        tuple(map(int, rollout.get("decision_task_steps") or ())) != DECISION_STEPS
        or any(int(rollout.get(key, -1)) != value for key, value in expected_rollout.items())
    ):
        raise ValueError("R8R8 rollout contract changed")

    candidate = cfg.get("candidate_contract") or {}
    actual_candidates = tuple(
        (
            str(row.get("name")),
            int(row.get("direction_index", -2)),
            int(row.get("sign", -2)),
            float(row.get("action_scale", -1.0)),
        )
        for row in candidate.get("ordered_candidates") or ()
    )
    if (
        actual_candidates != CANDIDATES
        or candidate.get("canonical_matrix_digest") != MATRIX_DIGEST
        or _matrix_digest(candidate.get("canonical_matrix_columns")) != MATRIX_DIGEST
        or float(candidate.get("canonical_scale", -1.0)) != 1.0
        or candidate.get("mixed_or_continuous_action_allowed") is not False
        or candidate.get("replacement_scale_allowed") is not False
    ):
        raise ValueError("R8R8 candidate alphabet changed")

    objective = cfg.get("objective_contract") or {}
    if (
        tuple(map(float, objective.get("base_target_physical") or ()))
        != (0.75, 0.0, 29779.724)
        or tuple(map(float, objective.get("physical_scales") or ()))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, objective.get("component_weights") or ()))
        != (4.0, 4.0, 1.0, 1.0, 0.25)
        or tuple(map(float, objective.get("lag_weights") or ()))
        != (1.0, 2.0, 4.0, 8.0)
        or float(objective.get("required_nonzero_score_ratio", -1.0)) != 0.995
        or objective.get("zero_wins_ties") is not True
        or objective.get("tail_extrapolation_allowed") is not False
        or objective.get("online_adaptation_allowed") is not False
    ):
        raise ValueError("R8R8 robust objective changed")

    controller = cfg.get("controller_contract") or {}
    expected_controller = {
        "maximum_incremental_normalized_action_linf": 0.25,
        "maximum_online_cancel_incremental_linf": 0.24,
        "maximum_total_normalized_action_abs": 1.0,
        "maximum_current_utilization": 0.55,
        "minimum_desired_applied_current_cosine": 0.98,
        "maximum_relative_off_basis_residual": 0.1,
    }
    required_controller = (
        "require_pure_candidate_construction",
        "require_exact_stored_center_cancellation",
        "require_exact_zero_target_jump_net",
        "require_exact_source_prefix",
        "require_fresh_controller",
        "require_fresh_tsc_process",
        "forbid_future_r17_controller_execution",
        "safe_zero_fallback",
    )
    if (
        any(float(controller.get(key, -1.0)) != value for key, value in expected_controller.items())
        or int(controller.get("dynamic_exact_search_radius", -1)) != 16
        or not all(controller.get(key) is True for key in required_controller)
    ):
        raise ValueError("R8R8 hard controller contract changed")

    models = cfg.get("source_model_contract") or {}
    if (
        int(models.get("forecast_horizon_steps", -1)) != 4
        or models.get("adaptation_enabled") is not False
        or models.get("response_model_sha256")
        != (cfg.get("source_r8r7_contract") or {}).get("response_model_sha256")
        or models.get("response_tube_sha256")
        != (cfg.get("source_r8r7_contract") or {}).get("response_tube_sha256")
        or models.get("combined_tube_sha256")
        != (cfg.get("source_r8r7_contract") or {}).get("combined_tube_sha256")
    ):
        raise ValueError("R8R8 model source contract changed")

    offline = cfg.get("offline_gates") or {}
    execution = cfg.get("execution_gates") or {}
    if (
        tuple(int(offline.get(key, -1)) for key in (
            "spec_count", "decision_origin_count", "candidate_forecast_count",
            "selection_agreement_count", "issue_construction_count",
            "cancel_construction_count", "minimum_nonzero_selection_count",
            "fault_injection_case_count",
        )) != (16, 64, 576, 64, 512, 512, 1, 4)
        or tuple(int(execution.get(key, -1)) for key in (
            "raw_count", "decision_record_count", "formal_pass_count",
            "minimum_nonzero_issue_count",
        )) != (16, 64, 16, 1)
        or float(execution.get("minimum_selected_nonzero_improvement_fraction", -1.0)) != 0.005
        or execution.get("zero_hard_safety_violation_required") is not True
        or execution.get("zero_forbidden_input_required") is not True
    ):
        raise ValueError("R8R8 qualification gates changed")

    formal = cfg.get("formal_timing_contract") or {}
    if (
        tuple(int(formal.get(key, -1)) for key in (
            "normal_arrival_deadline_step", "normal_hold_through_step",
            "weak_arrival_deadline_step", "weak_hold_through_step",
            "arrival_streak_steps",
        )) != (25, 35, 27, 37, 3)
        or tuple(float(formal.get(key, -1.0)) for key in (
            "position_tolerance_m", "speed_tolerance_m_per_s", "ip_tolerance_A",
        )) != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or formal.get("formal_tracking_is_hard_gate") is not True
    ):
        raise ValueError("R8R8 formal timing contract changed")

    if (
        cfg.get("all_stage_trajectories_allowed_in_expert_dataset") is not False
        or cfg.get("gate_a_qualified") is not False
        or cfg.get("bc_dagger_or_rl_allowed") is not False
    ):
        raise ValueError("R8R8 scientific boundary changed")


def self_test(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(cfg, project_root=config_path.resolve().parents[1])
    return {
        "stage": STAGE,
        "decision_count": len(DECISION_STEPS),
        "candidate_count": len(CANDIDATES),
        "nonzero_candidate_count": len(CANDIDATES) - 1,
        "passed": True,
    }
