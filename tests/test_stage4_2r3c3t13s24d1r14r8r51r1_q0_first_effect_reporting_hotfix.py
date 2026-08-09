from __future__ import annotations

import copy
import unittest

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r1_q0_first_effect_reporting_hotfix as primary,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r1_q0_first_effect_reporting_hotfix_independent
    as independent,
)


def _fixture(difference: float = 2.842170943040401e-14):
    trajectory = [
        {"action_norm_tsc": [0.0] * 14, "currents_a_tsc": [100.0] * 14}
        for _ in range(12)
    ]
    trace = [{"action_norm_tsc": [0.0] * 14} for _ in range(11)]
    q0_action = [0.0] * 14
    q0_action[11] = 3.3333333296544274e-06
    trace[10] = {
        "action_norm_tsc": q0_action,
        "r3c3t13s24d1r14r8r51r1_event_detail": {
            "nominal_readback_current_a_tsc": [100.0 + difference] + [100.0] * 13
        },
    }
    trajectory[11]["action_norm_tsc"] = list(q0_action)
    return trajectory, trace


class Stage42R3C3T13S24D1R14R8R51R1ReportingHotfixTests(unittest.TestCase):
    def test_binary64_ulp_difference_passes_both_implementations(self):
        trajectory, trace = _fixture()
        first = primary._measure_q0_effect(trajectory, trace)
        second = independent._measure_q0_effect(trajectory, trace)
        self.assertTrue(first["passed"])
        self.assertTrue(second["passed"])
        self.assertFalse(first["state11_current_equals_q0_target_binary_exact"])
        self.assertFalse(second["state11_current_equals_q0_target_binary_exact"])
        self.assertEqual(first, second)

    def test_difference_above_frozen_tolerance_fails_closed(self):
        trajectory, trace = _fixture(1.1e-12)
        self.assertFalse(primary._measure_q0_effect(trajectory, trace)["passed"])
        self.assertFalse(independent._measure_q0_effect(trajectory, trace)["passed"])

    def test_state11_action_mismatch_fails_closed(self):
        trajectory, trace = _fixture()
        trajectory[11]["action_norm_tsc"][0] = 1e-6
        self.assertFalse(primary._measure_q0_effect(trajectory, trace)["passed"])
        self.assertFalse(independent._measure_q0_effect(trajectory, trace)["passed"])

    def test_previous_action_mismatch_fails_closed(self):
        trajectory, trace = _fixture()
        trajectory[10]["action_norm_tsc"][0] = 1e-6
        self.assertFalse(primary._measure_q0_effect(trajectory, trace)["passed"])
        self.assertFalse(independent._measure_q0_effect(trajectory, trace)["passed"])

    def test_nonfinite_current_fails_closed(self):
        trajectory, trace = _fixture()
        broken = copy.deepcopy(trajectory)
        broken[11]["currents_a_tsc"][0] = float("nan")
        self.assertFalse(primary._measure_q0_effect(broken, trace)["passed"])
        with self.assertRaises(ValueError):
            independent._measure_q0_effect(broken, trace)

    def test_contract_is_reporting_only_and_learning_forbidden(self):
        self.assertEqual(primary.CURRENT_ABSOLUTE_TOLERANCE_A, 1e-12)
        self.assertEqual(independent.ATOL_A, 1e-12)
        self.assertEqual(primary.EXPECTED_RAW_COUNT, 208)
        self.assertEqual(primary.EXPECTED_BINARY_EXACT_COUNT, 39)
        self.assertIn("R51R2_MODEL_PREFLIGHT_REQUIRED", primary.PASS_ROUTE)


if __name__ == "__main__":
    unittest.main()
