"""Frozen contract for the D1R14R8R3 causal no-action observer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from tsc_rzip_rllib.control import causal_history_no_action_observer as observer


STAGE = "Stage4.2R3c3T13S24D1R14R8R3"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer"
IDENTITY = "causal_history_action_current_no_action_observer_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r3_causal_history_observer_v1"
DESIGN_SHA256 = "c55130a41f6522259d6fe9073686f0c86226c7dc11be7e93607b63f0abd0dfcb"
SOURCE_CONFIG_SHA256 = "43e513942b66bdae94d8089b5885455f148c961b2a68be03a879444859149fe1"


def validate_config(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_r8r2_contract"]
    bank = cfg["bank_contract"]
    feature = cfg["feature_contract"]
    model = cfg["model_contract"]
    tube = cfg["tube_contract"]
    gates = cfg["gates"]
    timing = cfg["formal_timing_contract"]
    invalid = (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != IDENTITY
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("design_document_sha256") != DESIGN_SHA256
        or cfg.get("source_r8r2_config_sha256") != SOURCE_CONFIG_SHA256
        or tuple(
            (int(source[f"{key}_bytes"]), str(source[f"{key}_sha256"]))
            for key in ("primary_detailed", "primary_summary", "independent", "stage_state")
        )
        != (
            (53252, "ad04374987ce4de599d71f4673ac110fe763928831e4c9610cdb117efd7977cf"),
            (4907, "05d761ef64c9e7c2373a6754184ecf42cf0a250d26ee235293e768c0416c0bb2"),
            (1802, "2ca90fab851c4131f7242bd9a5331286bde15ccaf47d251348b7d80a4597066c"),
            (537, "ee06726c8a5170ffd03a9465432ceed6f42053e2db8f710442c80c7809f07670"),
        )
        or source.get("required_route")
        != "CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED"
        or bool(source.get("required_scientific_gate_passed"))
        or int(source.get("required_new_raw_count", -1)) != 0
        or bool(source.get("required_heldout_outcomes_opened"))
        or str(source.get("required_development_artifact_sha256") or "")
        or tuple(
            int(bank[key])
            for key in (
                "pair_count", "context_count", "origin_row_count",
                "prescribed_issue_row_count", "probe_feature_count",
                "history_state_count", "history_action_count", "future_state_count",
                "first_origin_task_step", "coil_count", "feature_dimension",
                "output_dimension",
            )
        )
        != (12, 24, 360, 96, 912, 11, 10, 12, 10, 14, 353, 36)
        or tuple(map(int, bank["baseline_visible_lengths"])) != (36, 38)
        or tuple(map(int, bank["prescribed_issue_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(float, bank["visible_scales"]))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or float(bank["dt_s"]) != 0.01
        or tuple(map(int, feature["visible_state_offsets"])) != tuple(range(-10, 1))
        or tuple(map(int, feature["issued_action_offsets"])) != tuple(range(-10, 0))
        or tuple(map(int, feature["applied_current_offsets"])) != tuple(range(-10, 1))
        or int(feature["relative_clock_origin"]) != 10
        or float(feature["relative_clock_scale"]) != 15.0
        or not bool(feature["future_incremental_action_is_zero"])
        or not bool(feature["future_applied_current_target_is_constant"])
        or bool(feature["matched_baseline_feature_copy_allowed"])
        or bool(feature["matched_baseline_future_predictor_input_allowed"])
        or tuple(map(int, model["pca_ranks"])) != (8, 16, 24, 32)
        or tuple(model["kernel_families"]) != ("linear", "rbf")
        or tuple(map(float, model["rbf_median_distance_multipliers"])) != (0.5, 1.0, 2.0)
        or tuple(map(float, model["kernel_ridges"])) != (1e-6, 1e-3, 1e-1)
        or tuple(float(model[key]) for key in ("standard_deviation_floor", "bandwidth_floor"))
        != (1e-12, 1e-12)
        or model.get("pca_sign_rule")
        != "largest_absolute_loading_positive_lowest_index_tie"
        or tuple(map(int, model["target_components"])) != (2, 3, 4)
        or model.get("target_mode") != "origin_relative_direct_12_step"
        or model.get("position_reconstruction")
        != "integrate_predicted_velocity_from_origin"
        or int(model["candidate_count"]) != 48
        or model.get("outer_group_key") != "pair_id"
        or float(tube["inner_residual_multiplier"]) != 1.25
        or tuple(map(float, tube["component_floor_physical"]))
        != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or bool(tube["clipping_allowed"])
        or tuple(map(float, gates["component_caps_physical"]))
        != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or tuple(
            int(gates[key])
            for key in (
                "required_outer_fold_count", "required_outer_origin_row_count",
                "required_prescribed_issue_row_count", "required_probe_feature_count",
                "required_origin_pass_count", "required_prescribed_issue_pass_count",
                "required_tube_cap_fold_count", "required_tube_contained_origin_count",
                "required_probe_feature_equal_count",
            )
        )
        != (12, 360, 96, 912, 360, 96, 12, 360, 912)
        or tuple(
            float(gates[key])
            for key in ("independent_relative_tolerance", "independent_absolute_tolerance")
        )
        != (1e-10, 1e-12)
        or tuple(
            int(timing[key])
            for key in (
                "normal_arrival_deadline_step", "normal_hold_through_step",
                "weak_arrival_deadline_step", "weak_hold_through_step",
                "arrival_streak_steps",
            )
        )
        != (25, 35, 27, 37, 3)
        or tuple(
            float(timing[key])
            for key in ("position_tolerance_m", "speed_tolerance_m_per_s", "ip_tolerance_A")
        )
        != (0.03, 0.1, 10000.0)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or bool(timing["formal_tracking_evaluated"])
        or tuple(cfg["forbidden_predictor_fields"])
        != (
            "pair_id", "history_member", "source_stage", "partition", "prefix",
            "target_id", "regime_id", "delay_label", "slew_label", "experiment_id",
            "source_outcome", "formal_outcome", "hidden_state", "wire_current",
            "matched_baseline_future", "future_measurement", "future_probe_state",
            "future_coil_current", "future_executed_action",
        )
        or cfg["routes"]
        != {
            "audit_fail": "CAUSAL_HISTORY_NO_ACTION_OBSERVER_AUDIT_FAIL_STOP",
            "fail": "CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED",
            "pass": "CAUSAL_HISTORY_NO_ACTION_OBSERVER_PASS_COMBINED_ADAPTATION_FREEZE_REQUIRED",
        }
        or int(cfg["new_tsc_rollouts"]) != 0
        or not bool(cfg["identification_development_only"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["mpc_validated"])
        or bool(cfg["gate_a_qualified"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    )
    if invalid or len(observer.candidates(cfg)) != 48:
        raise ValueError("R8R3 frozen contract changed")


def route_for(scientific_gate_passed: bool, cfg: Mapping[str, Any]) -> str:
    return str(cfg["routes"]["pass" if scientific_gate_passed else "fail"])


def self_test(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(cfg)
    visible = np.zeros((24, 5), dtype=float)
    visible[:, 0] = 1.0 + 0.01 * np.arange(24)
    visible[:, 1] = -0.5 + 0.005 * np.arange(24)
    visible[:, 2] = 0.2 + 0.001 * np.arange(24)
    visible[:, 3] = -0.1 + 0.002 * np.arange(24)
    visible[:, 4] = 0.3 - 0.003 * np.arange(24)
    actions = np.zeros((23, 14), dtype=float)
    currents = np.tile(np.arange(14, dtype=float), (24, 1))
    feature = observer.causal_feature(
        visible, actions, currents, (0.01, -0.02, 1000.0), 10, cfg
    )
    delta = observer.target_delta(visible, 10, cfg)
    item = {"origin_visible": visible[10]}
    forecast = observer.forecast_from_delta(item, delta, cfg)
    return {
        "stage": STAGE,
        "feature_shape": list(feature.shape),
        "delta_shape": list(delta.shape),
        "forecast_shape": list(forecast.shape),
        "candidate_count": len(observer.candidates(cfg)),
        "passed": bool(
            feature.shape == (353,)
            and delta.shape == (12, 3)
            and forecast.shape == (12, 5)
            and len(observer.candidates(cfg)) == 48
        ),
    }
