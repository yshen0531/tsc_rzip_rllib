from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from tsc_rzip_rllib.diagnostics import stage2_1_trajectory_optimization as s21


class Stage21Tests(unittest.TestCase):
    def _cfg(self):
        return {
            "target": {"R": 0.75, "Z": 0.0, "Ip": 29779.724},
            "gate": {
                "precise_tolerance_m": 0.03,
                "relaxed_tolerance_m": 0.04,
                "required_terminal_streak_steps": 3,
                "terminal_velocity_max_m_per_s": 0.1,
                "late_velocity_rms_max_m_per_s": 0.1,
                "late_window_steps": 4,
                "ip_tolerance_a": 10000.0,
            },
            "objective": {
                "tier_spacing": 1e6,
                "tube_window_steps": 5,
                "weights": {
                    "tube_excess_mean": 90.0,
                    "tube_excess_max": 120.0,
                    "tube_excess_terminal": 60.0,
                    "velocity_excess": 80.0,
                    "streak_deficit": 4.0,
                    "late_position_core": 1.5,
                    "terminal_position_core": 1.0,
                    "velocity_core": 2.5,
                    "terminal_ip": 0.1,
                    "action_rms": 0.02,
                    "delta_action_rms": 0.04,
                    "repair": 2.0,
                },
            },
            "archives": {
                "damped_capacity": 8,
                "precise_capacity": 8,
                "minimum_vector_distance": 0.0,
                "damped_box_limit_m": 0.045,
                "precise_box_limit_m": 0.03,
                "speed_margin_factor": 1.05,
            },
            "search": {
                "bridge_noise_by_mode": [0.0, 0.0, 0.0],
                "tail_node_indices": [2, 3, 4],
            },
        }

    def test_self_test(self):
        result = s21.synthetic_self_test()
        self.assertTrue(result["tube_excess_monotonic"])
        self.assertTrue(result["bridge_front_tail_semantics"])

    def test_dual_archive_keeps_both_families(self):
        cfg = self._cfg()
        damped = {
            "candidate_id": "damped",
            "vector": np.zeros(15).tolist(),
            "terminal_RZ_box_max_error_m": 0.032,
            "terminal_RZ_euclidean_error_m": 0.041,
            "late_RZ_euclidean_rms_m": 0.042,
            "terminal_R_error_m": -0.025,
            "terminal_Z_error_m": 0.032,
            "terminal_Ip_error_A": 500.0,
            "terminal_velocity_m_per_s": 0.03,
            "late_velocity_rms_m_per_s": 0.09,
            "trailing_streak_within_30mm_steps": 0,
            "trailing_streak_within_40mm_steps": 10,
        }
        precise = {
            "candidate_id": "precise",
            "vector": (np.ones(15) * 0.2).tolist(),
            "terminal_RZ_box_max_error_m": 0.029,
            "terminal_RZ_euclidean_error_m": 0.035,
            "late_RZ_euclidean_rms_m": 0.034,
            "terminal_R_error_m": -0.029,
            "terminal_Z_error_m": 0.020,
            "terminal_Ip_error_A": 500.0,
            "terminal_velocity_m_per_s": 0.38,
            "late_velocity_rms_m_per_s": 0.33,
            "trailing_streak_within_30mm_steps": 3,
            "trailing_streak_within_40mm_steps": 3,
        }
        archives = s21.rebuild_archives(cfg, {"damped": [], "precise": []}, [damped, precise])
        self.assertEqual(archives["damped"][0]["candidate_id"], "damped")
        self.assertEqual(archives["precise"][0]["candidate_id"], "precise")

    def test_smooth_objective_prefers_31mm_to_32mm(self):
        cfg = self._cfg()
        ctx = SimpleNamespace(cfg=cfg)
        base_metrics = {
            "success": True,
            "gate_tier": 1,
            "gate_label": "PASS_DAMPED_HOLD_40MM",
            "strict_gate_pass": False,
            "relaxed_gate_pass": True,
            "terminal_velocity_m_per_s": 0.03,
            "late_velocity_rms_m_per_s": 0.08,
            "terminal_Ip_error_A": 0.0,
            "trailing_streak_within_30mm_steps": 0,
        }

        def result(z_error):
            trajectory = []
            for step in range(11):
                trajectory.append(
                    {
                        "R": 0.75 - 0.025,
                        "Z": z_error,
                        "Ip": 29779.724,
                    }
                )
            return {"success": True, "trajectory": trajectory}

        with patch.object(s21.s2, "stage2_metrics", return_value=base_metrics):
            score31 = s21.stage21_metrics(ctx, result(0.031), None)["continuous_objective"]
            score32 = s21.stage21_metrics(ctx, result(0.032), None)["continuous_objective"]
        self.assertLess(score31, score32)


if __name__ == "__main__":
    unittest.main()
