from __future__ import annotations

import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s7_causal_multi_history_tube_audit as audit,
)


class Stage42R3C3T13S7CausalMultiHistoryTubeAuditTests(unittest.TestCase):
    def test_issue_cancel_reinterprets_both_campaigns_immediately(self) -> None:
        s1 = {
            "spec": {
                "r3c3_probe_delta_by_task_issue_step": {"0": [1.0], "1": [-1.0]}
            }
        }
        s5 = {"spec": {"r3c3_probe_issue_step": 14, "r3c3_probe_cancel_step": 15}}
        self.assertEqual(audit._issue_cancel("s1", s1), (0, 1))
        self.assertEqual(audit._issue_cancel("s5", s5), (14, 15))

    def test_causal_feature_contains_no_forbidden_label(self) -> None:
        baseline = {
            "spec": {
                "formal_horizon_steps": 35,
                "target_R_offset_m": 0.01,
                "target_Z_offset_m": -0.01,
                "target_Ip_offset_A": 0.0,
                "action_delay_steps": 0,
                "slew_scale": 1.0,
                "pair_id": "forbidden_if_used",
                "history_member": "forbidden_if_used",
            },
            "trajectory": [
                {"R": 0.7, "Z": 0.02, "Ip": 30000.0, "currents_a_tsc": [1.0] * 14},
                {"R": 0.701, "Z": 0.019, "Ip": 30001.0, "currents_a_tsc": [2.0] * 14},
            ],
        }
        values, names = audit.causal_feature(
            baseline, issue_step=1, current_scales=np.asarray([100.0] * 14), dt_s=0.01
        )
        self.assertEqual(values.shape, (41,))
        self.assertFalse(audit.FORBIDDEN_FEATURE_NAMES.intersection(names))
        self.assertEqual(values[names.index("velocity_known")], 1.0)
        self.assertEqual(values[names.index("coil_history_known")], 1.0)

    def test_restart_feature_marks_velocity_and_current_history_unknown(self) -> None:
        baseline = {
            "spec": {
                "formal_horizon_steps": 37,
                "target_R_offset_m": 0.01,
                "target_Z_offset_m": -0.01,
                "target_Ip_offset_A": 0.0,
                "action_delay_steps": 2,
                "slew_scale": 0.9,
            },
            "trajectory": [
                {"R": 0.7, "Z": 0.02, "Ip": 30000.0, "currents_a_tsc": [1.0] * 14}
            ],
        }
        values, names = audit.causal_feature(
            baseline, issue_step=0, current_scales=np.asarray([100.0] * 14), dt_s=0.01
        )
        self.assertEqual(values[names.index("vR")], 0.0)
        self.assertEqual(values[names.index("vZ")], 0.0)
        self.assertEqual(values[names.index("velocity_known")], 0.0)
        self.assertEqual(values[names.index("coil_history_known")], 0.0)

    def test_input_support_uses_training_row_space(self) -> None:
        model = {"row_basis": np.asarray([[1.0, 0.0], [0.0, 1.0]])}
        relative, supported = audit.input_support(model, np.asarray([3.0, 4.0]))
        self.assertAlmostEqual(relative, 0.0)
        self.assertTrue(supported)
        narrow = {"row_basis": np.asarray([[1.0, 0.0]])}
        relative, supported = audit.input_support(narrow, np.asarray([0.0, 1.0]))
        self.assertAlmostEqual(relative, 1.0)
        self.assertFalse(supported)

    def test_nearest_contexts_selects_two_and_exact_ties(self) -> None:
        def context(identifier: str, value: float) -> dict:
            return {
                "context_id": identifier,
                "feature_digest": identifier,
                "features": {"transport": {"values": np.asarray([value])}},
            }

        held = context("held", 0.0)
        selected = audit.nearest_contexts(
            held,
            [context("a", 1.0), context("b", 2.0), context("c", 2.0)],
            window="transport",
        )
        self.assertEqual([row[1]["context_id"] for row in selected], ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
