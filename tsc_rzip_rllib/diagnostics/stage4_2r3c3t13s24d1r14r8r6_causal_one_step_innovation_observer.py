"""Frozen contract for Stage4.2R3c3T13S24D1R14R8R6."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


STAGE = "Stage4.2R3c3T13S24D1R14R8R6"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer"
IDENTITY = "causal_one_step_innovation_observer_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer_v1"
DESIGN_SHA256 = "6f8886f42321a2e99a97332ecf03c1827b5385ebfc50f6ee07fefefcafa182f1"


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_config(cfg: Mapping[str, Any], *, project_root: Path | None = None) -> None:
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != IDENTITY
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("design_document_sha256") != DESIGN_SHA256
    ):
        raise ValueError("R8R6 frozen identity changed")
    if project_root is not None:
        root = project_root.resolve()
        for key, expected in (
            ("design_document", DESIGN_SHA256),
            ("source_r8r5_config", str(cfg["source_r8r5_config_sha256"])),
        ):
            if _sha((root / str(cfg[key])).resolve()) != expected:
                raise ValueError(f"R8R6 {key} hash changed")
    bank = cfg.get("bank_contract") or {}
    if (
        tuple(map(float, bank.get("visible_scales") or ()))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or float(bank.get("dt_s", -1.0)) != 0.01
        or int(bank.get("future_state_count", -1)) != 12
        or int(bank.get("feature_dimension", -1)) != 353
        or int(bank.get("physical_pair_count", -1)) != 20
        or int(bank.get("history_context_count", -1)) != 40
        or int(bank.get("origin_row_count", -1)) != 600
        or int(bank.get("startup_fallback_row_count", -1)) != 40
        or int(bank.get("adapted_origin_row_count", -1)) != 560
        or int(bank.get("adapted_prescribed_issue_row_count", -1)) != 120
        or tuple(map(int, bank.get("adapted_prescribed_issue_task_steps") or ()))
        != (14, 18, 22)
    ):
        raise ValueError("R8R6 bank contract changed")
    model = cfg.get("fixed_model_contract") or {}
    implementation = cfg.get("model_contract") or {}
    if (
        model.get("family") != "linear"
        or int(model.get("pca_rank", -1)) != 32
        or float(model.get("ridge", -1.0)) != 1e-6
        or float(model.get("bandwidth_multiplier", -1.0)) != 0.0
        or bool(model.get("candidate_selection_allowed"))
        or tuple(map(int, implementation.get("pca_ranks") or ())) != (32,)
        or tuple(implementation.get("rbf_median_distance_multipliers") or ())
        or tuple(map(float, implementation.get("kernel_ridges") or ()))
        != (1e-6,)
        or int(implementation.get("candidate_count", -1)) != 1
    ):
        raise ValueError("R8R6 fixed model changed")
    innovation = cfg.get("innovation_contract") or {}
    if (
        tuple(map(str, innovation.get("dynamic_components") or ()))
        != ("vR", "vZ", "Ip")
        or int(innovation.get("first_adapted_origin_task_step", -1)) != 11
        or int(innovation.get("previous_prediction_future_lag", -1)) != 1
        or tuple(map(float, innovation.get("clip_physical") or ()))
        != (0.02, 0.02, 1000.0)
        or float(innovation.get("persistence", -1.0)) != 0.8
        or bool(innovation.get("fit_coefficients"))
        or bool(innovation.get("candidate_selection_allowed"))
        or innovation.get("reintegrate_position") is not True
    ):
        raise ValueError("R8R6 innovation contract changed")
    tube = cfg.get("tube_contract") or {}
    gates = cfg.get("gates") or {}
    if (
        tube.get("method")
        != "causal_adapted_context_robust_global_higher_quantile_scaled"
        or float(tube.get("base_absolute_residual_quantile", -1.0)) != 0.95
        or float(tube.get("aggregate_row_ratio_quantile", -1.0)) != 0.95
        or float(tube.get("per_context_row_ratio_quantile", -1.0)) != 0.90
        or float(tube.get("prospective_reserve_multiplier", -1.0)) != 2.0
        or tuple(map(float, tube.get("component_caps_physical") or ()))
        != (0.01, 0.01, 0.05, 0.05, 3000.0)
        or tuple(map(float, gates.get("component_caps_physical") or ()))
        != (0.003, 0.003, 0.02, 0.02, 1000.0)
        or int(gates.get("required_outer_fold_count", -1)) != 20
        or int(gates.get("required_startup_fallback_pass_count", -1)) != 40
        or float(gates.get("maximum_aggregate_mse_ratio", -1.0)) != 0.95
        or float(gates.get("maximum_context_mse_ratio", -1.0)) != 1.05
        or int(gates.get("minimum_strictly_improved_context_count", -1)) != 24
    ):
        raise ValueError("R8R6 gate contract changed")
    timing = cfg.get("formal_timing_contract") or {}
    if (
        int(timing.get("normal_arrival_deadline_step", -1)) != 25
        or int(timing.get("normal_hold_through_step", -1)) != 35
        or int(timing.get("weak_arrival_deadline_step", -1)) != 27
        or int(timing.get("weak_hold_through_step", -1)) != 37
        or float(timing.get("position_tolerance_m", -1.0)) != 0.03
        or float(timing.get("speed_tolerance_m_per_s", -1.0)) != 0.1
        or float(timing.get("ip_tolerance_A", -1.0)) != 10000.0
        or int(timing.get("arrival_streak_steps", -1)) != 3
        or bool(timing.get("arrival_deadline_expansion_allowed"))
    ):
        raise ValueError("R8R6 formal timing changed")
    if (
        cfg.get("zero_new_tsc") is not True
        or bool(cfg.get("all_stage_trajectories_allowed_in_expert_dataset"))
        or bool(cfg.get("probe_trajectories_allowed_in_expert_dataset"))
        or bool(cfg.get("mpc_validated"))
        or bool(cfg.get("gate_a_qualified"))
        or bool(cfg.get("bc_dagger_or_rl_allowed"))
    ):
        raise ValueError("R8R6 scope changed")


def self_test(config_path: Path) -> dict[str, Any]:
    path = config_path.expanduser().resolve()
    cfg = _read(path)
    validate_config(cfg, project_root=path.parents[1])
    return {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": IDENTITY,
        "zero_new_tsc": True,
        "physical_pair_count": 20,
        "origin_row_count": 600,
        "adapted_origin_row_count": 560,
        "persistence": 0.8,
        "design_sha256": DESIGN_SHA256,
        "passed": True,
    }
