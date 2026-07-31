import importlib.util
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs"
    / "codex"
    / "audit_tools"
    / "stage4_2r3c3t6_new_direction_preflight.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t6_new_direction_preflight", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class Stage42R3C3T6NewDirectionPreflightTests(unittest.TestCase):
    def test_projection_and_orthonormalization(self) -> None:
        matrix = np.asarray(
            [
                [1.0, 0.0],
                [0.0, 1.0],
                [0.0, 0.0],
                [0.0, 0.0],
            ]
        )
        first = preflight._orthonormalize(
            np.asarray([2.0, -3.0, 4.0, 0.0]), matrix, []
        )
        second = preflight._orthonormalize(
            np.asarray([5.0, 1.0, 2.0, 3.0]), matrix, [first]
        )
        self.assertAlmostEqual(float(np.linalg.norm(first)), 1.0)
        self.assertAlmostEqual(float(np.linalg.norm(second)), 1.0)
        self.assertLess(float(np.max(np.abs(matrix.T @ first))), 1.0e-14)
        self.assertLess(float(np.max(np.abs(matrix.T @ second))), 1.0e-14)
        self.assertLess(abs(float(first @ second)), 1.0e-14)

    def test_delay_aware_zero_net_schedule(self) -> None:
        for delay, formal_hold in ((0, 35), (2, 37)):
            effective = formal_hold - delay
            formal = np.zeros((formal_hold, 3))
            formal[:effective, 0] = 0.001
            formal[:effective, 1] = -0.0005
            schedule = preflight._zero_net_schedule(
                formal, delay_steps=delay
            )
            self.assertEqual(
                schedule["last_formal_effect_state"], formal_hold
            )
            self.assertEqual(
                schedule["first_cancellation_effect_state"], 39
            )
            self.assertEqual(
                schedule["last_cancellation_effect_state"], 44
            )
            rows = schedule["positive_schedule_by_task_issue_step"]
            total = np.sum(
                np.asarray([row[1] for row in rows], dtype=float), axis=0
            )
            self.assertLess(float(np.max(np.abs(total))), 1.0e-14)
            for issue, _ in schedule["cancellation_issue_schedule"]:
                effect = issue + delay + 1
                self.assertIn(
                    effect, preflight.CANCELLATION_EFFECT_STATES
                )

    def test_noncausal_formal_rows_are_rejected(self) -> None:
        formal = np.zeros((37, 3))
        formal[35, 0] = 0.001
        with self.assertRaisesRegex(ValueError, "noncausal-to-formal"):
            preflight._zero_net_schedule(formal, delay_steps=2)

    def test_amplitude_rule_respects_both_limits(self) -> None:
        direction = np.zeros(35 * 3)
        direction[0] = 0.8
        direction[1] = 0.6
        formal, scale = preflight._scaled_formal_schedule(
            direction, formal_hold_step=35
        )
        self.assertAlmostEqual(scale, 0.0075 / 0.8)
        self.assertLessEqual(
            float(np.max(np.abs(formal))),
            preflight.COMPONENT_ABS_LIMIT,
        )
        self.assertLessEqual(
            float(np.linalg.norm(formal)), preflight.FORMAL_L2_LIMIT
        )


if __name__ == "__main__":
    unittest.main()
