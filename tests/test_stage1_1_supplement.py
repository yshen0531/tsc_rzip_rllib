#!/usr/bin/env python3
from __future__ import annotations

from types import SimpleNamespace

from tsc_rzip_rllib.diagnostics.stage1_controllability import build_gate_a_verdict
from tsc_rzip_rllib.diagnostics.stage1_1_supplement import synthetic_stage1_1_test


def test_synthetic_metrics() -> None:
    result = synthetic_stage1_1_test()
    assert result["step0_exclusion_ok"]
    assert result["trailing_streak_ok"]


def test_precise_gate() -> None:
    resolved = SimpleNamespace(
        cfg={
            "scan": {"horizon_steps": 10},
            "validation": {
                "gate_mode": "stage1_1_precise_hold",
                "primary_tolerance_m": 0.03,
                "relaxed_tolerance_m": 0.04,
                "required_terminal_streak_steps": 3,
                "terminal_velocity_max_m_per_s": 0.10,
                "late_velocity_rms_max_m_per_s": 0.10,
                "promising_distance_reduction": 0.50,
                "gate_ip_tolerance_a": 10000.0,
            },
        },
        env_cfg={"dt_ms": 10},
    )
    rows = [
        {
            "candidate_label": "zero_action_baseline",
            "success": True,
            "terminal_RZ_euclidean_error_m": 0.09,
            "late_RZ_euclidean_rms_m": 0.08,
            "terminal_velocity_m_per_s": 0.70,
        },
        {
            "candidate_label": "svd03_target1p00",
            "success": True,
            "terminal_within_30mm": True,
            "trailing_streak_within_30mm_steps": 3,
            "terminal_within_40mm": True,
            "trailing_streak_within_40mm_steps": 4,
            "terminal_Ip_safe": True,
            "terminal_velocity_m_per_s": 0.08,
            "late_velocity_rms_m_per_s": 0.09,
            "terminal_RZ_euclidean_error_m": 0.028,
            "terminal_RZ_reduction_vs_zero_action_fraction": 0.69,
        },
    ]
    verdict = build_gate_a_verdict(resolved, rows)
    assert verdict["status"] == "PASS_PRECISE_HOLD_30MM"
    assert verdict["best_validation"]["candidate_label"] == "svd03_target1p00"


if __name__ == "__main__":
    test_synthetic_metrics()
    test_precise_gate()
    print("Stage1.1 supplement tests passed")
