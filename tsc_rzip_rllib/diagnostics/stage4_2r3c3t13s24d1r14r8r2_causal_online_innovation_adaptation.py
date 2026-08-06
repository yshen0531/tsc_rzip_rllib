"""Frozen contract for the D1R14R8R2 causal innovation discriminator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from tsc_rzip_rllib.control import causal_online_innovation_adapter as adapter


STAGE = "Stage4.2R3c3T13S24D1R14R8R2"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation"
IDENTITY = "causal_same_trajectory_innovation_adaptation_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r2_causal_online_innovation_v1"


def validate_config(cfg: Mapping[str, Any]) -> None:
    bank = cfg["bank_contract"]
    fixed = cfg["fixed_candidate"]
    model = cfg["model_contract"]
    innovation = cfg["innovation_contract"]
    gates = cfg["gates"]
    timing = cfg["formal_timing_contract"]
    source = cfg["source_r8r1_contract"]
    invalid = (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != IDENTITY
        or cfg.get("package_revision") != PACKAGE_REVISION
        or cfg.get("design_document_sha256")
        != "2613cd42b7b3a2e9c985c7ac1a9fd055fc20aa596e16add5a2e4c54cc8514dfe"
        or cfg.get("source_r8r1_config_sha256")
        != "d11cf5e806a478c516376a2c90444e2599175289f4ee1fc76e68915852844565"
        or tuple(
            (int(source[f"{key}_bytes"]), str(source[f"{key}_sha256"]))
            for key in ("primary_detailed", "primary_summary", "independent", "stage_state")
        )
        != (
            (1035205, "bd0041c3e16b56fce28abb80526bb5f1628ee74f6f5b52a70aaa07019e86a1ee"),
            (19743, "5d6c2eb4282dba1ba29e25624b147af8b760c8cfbe5fd085374cf54110de6204"),
            (13742, "3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c"),
            (504, "3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f"),
        )
        or source.get("required_route")
        != "FIXED_CANDIDATE_SHORT_HORIZON_FAIL_CAUSAL_INNOVATION_REQUIRED"
        or int(source.get("required_new_raw_count", -1)) != 0
        or bool(source.get("required_heldout_outcomes_opened"))
        or str(source.get("required_model_sha256") or "")
        or tuple(
            int(bank[key])
            for key in (
                "response_count", "pair_count", "context_count",
                "responses_per_pair", "responses_per_context",
                "baseline_window_count", "descriptor_dimension",
                "direction_count", "minimum_response_length",
            )
        )
        != (912, 12, 24, 76, 38, 96, 142, 4, 12)
        or tuple(map(float, bank["response_scales"]))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or tuple(map(int, bank["history_offsets"])) != tuple(range(23))
        or tuple(map(int, bank["issue_task_steps"])) != (10, 14, 18, 22)
        or float(bank["dt_s"]) != 0.01
        or (
            int(fixed["pca_rank"]),
            float(fixed["bandwidth_multiplier"]),
            float(fixed["ridge"]),
        )
        != (4, 2.0, 0.1)
        or tuple(
            float(model[key]) for key in ("standard_deviation_floor", "bandwidth_floor")
        )
        != (1e-12, 1e-12)
        or tuple(int(model[key]) for key in ("tail_polynomial_degree", "tail_fit_point_count"))
        != (2, 8)
        or tuple(map(int, innovation["baseline_trend_offsets"])) != (-3, -2, -1, 0)
        or int(innovation["baseline_forecast_relative_lags"]) != 12
        or tuple(map(int, innovation["update_relative_lags"])) != (2, 4)
        or tuple(map(int, innovation["selection_order"])) != (2, 4)
        or int(innovation["future_horizon_relative_lags"]) != 8
        or tuple(map(float, innovation["recency_factors"])) != (0.0, 0.5, 0.8)
        or tuple(map(int, innovation["correction_components"])) != (2, 3, 4)
        or not bool(innovation["constant_future_correction"])
        or not bool(innovation["causal_current_position_anchor"])
        or bool(innovation["matched_baseline_predictor_input_allowed"])
        or bool(innovation["origin_shift_allowed"])
        or tuple(
            float(gates[key])
            for key in (
                "maximum_relative_l2_error", "minimum_response_cosine",
                "minimum_peak_ratio", "maximum_peak_ratio",
                "maximum_absolute_scaled_point_error", "tube_multiplier",
                "minimum_predicted_peak", "minimum_actual_peak",
                "maximum_condition_number", "hard_minimum_response_cosine",
                "hard_minimum_peak_ratio", "hard_maximum_peak_ratio",
            )
        )
        != (0.75, 0.8, 0.5, 1.5, 0.1, 2.0, 0.0025, 0.0025, 20.0, 0.0, 0.25, 2.0)
        or tuple(map(float, gates["response_floor_physical"]))
        != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or tuple(map(float, gates["tube_caps_physical"]))
        != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or tuple(map(float, gates["baseline_component_caps_physical"]))
        != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or tuple(
            float(gates[key])
            for key in ("independent_relative_tolerance", "independent_absolute_tolerance")
        )
        != (1e-10, 1e-12)
        or float(gates["rank_relative_tolerance"]) != 1e-10
        or tuple(
            int(gates[key])
            for key in (
                "required_rank", "required_response_count",
                "required_response_pass_count", "required_signal_pass_count",
                "required_canonical_branch_count",
                "required_operational_branch_count", "useful_required_response_pass_count",
                "useful_required_pair_pass_count", "useful_required_context_pass_count",
                "useful_required_improvement_count",
            )
        )
        != (4, 912, 912, 912, 192, 192, 867, 69, 34, 46)
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
            "target_id", "regime_id", "delay_label", "slew_label",
            "source_result", "source_action", "source_coil_current",
            "source_wire_current", "current_coil_current", "current_wire_current",
            "hidden_wire_current", "matched_baseline_future", "future_measurement",
            "future_probe_state", "future_executed_action",
        )
        or int(cfg["new_tsc_rollouts"]) != 0
        or not bool(cfg["identification_development_only"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["mpc_validated"])
        or bool(cfg["gate_a_qualified"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
        or cfg["routes"]
        != {
            "audit_fail": "CAUSAL_ONLINE_INNOVATION_AUDIT_FAIL_STOP",
            "baseline_fail": "CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED",
            "adaptation_fail": "CAUSAL_ONLINE_INNOVATION_ADAPTATION_FAIL_NEW_IDENTIFICATION_REQUIRED",
            "pass": "CAUSAL_ONLINE_INNOVATION_ADAPTATION_PASS_FRESH_INTERACTION_SENTINEL_REQUIRED",
        }
    )
    if invalid:
        raise ValueError("R8R2 frozen contract changed")


def route_for(
    baseline_passed: bool, selected_update_lag: int | None, cfg: Mapping[str, Any]
) -> str:
    if not baseline_passed:
        return str(cfg["routes"]["baseline_fail"])
    if selected_update_lag is not None and selected_update_lag not in tuple(
        map(int, cfg["innovation_contract"]["selection_order"])
    ):
        raise ValueError("R8R2 selected update is not frozen")
    return str(cfg["routes"]["pass" if selected_update_lag is not None else "adaptation_fail"])


def self_test(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(cfg)
    visible = np.zeros((40, 5), dtype=float)
    visible[:, 2] = 0.2 + 0.01 * np.arange(40)
    visible[:, 3] = -0.1 + 0.005 * np.arange(40)
    visible[:, 4] = 0.3 - 0.002 * np.arange(40)
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    visible[0, :2] = (1.0, -1.0)
    visible[1:, 0] = visible[0, 0] + np.cumsum(visible[1:, 2]) * dt * scales[2] / scales[0]
    visible[1:, 1] = visible[0, 1] + np.cumsum(visible[1:, 3]) * dt * scales[3] / scales[1]
    forecast = adapter.no_action_forecast(visible, 10, cfg)
    descriptor = adapter.probe_descriptor(visible, 10, (0.0, 0.0, 0.0), cfg)
    return {
        "stage": STAGE,
        "forecast_shape": list(forecast.shape),
        "descriptor_shape": list(descriptor.shape),
        "fixed_candidate": adapter.fixed_candidate(cfg).as_dict(),
        "passed": bool(
            forecast.shape == (12, 5)
            and descriptor.shape == (142,)
            and np.all(np.isfinite(forecast))
        ),
    }
