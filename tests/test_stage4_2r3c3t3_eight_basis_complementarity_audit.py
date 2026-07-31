from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs"
    / "codex"
    / "audit_tools"
    / "stage4_2r3c3t3_eight_basis_complementarity_audit.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t3_eight_basis_complementarity_audit", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T3 eight-basis complementarity audit")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class Stage42R3C3T3EightBasisAuditTests(unittest.TestCase):
    def test_exact_frozen_modules_load(self) -> None:
        six = (
            ROOT
            / "docs"
            / "codex"
            / "audit_tools"
            / "stage4_2r3c3t2_six_basis_feasibility_audit.py"
        )
        formal = (
            ROOT
            / "docs"
            / "codex"
            / "audit_tools"
            / "stage4_2r3c3t1_six_basis_feasibility_diagnostic.py"
        )
        self.assertTrue(
            callable(
                AUDIT._load_exact_module(
                    six,
                    expected_sha256=(
                        AUDIT.EXPECTED_SIX_BUILDER_SHA256
                    ),
                    name="test_six",
                )._inventory
            )
        )
        self.assertTrue(
            callable(
                AUDIT._load_exact_module(
                    formal,
                    expected_sha256=(
                        AUDIT.EXPECTED_FROZEN_FEASIBILITY_TOOL_SHA256
                    ),
                    name="test_formal",
                ).FormalEvaluator
            )
        )

    def test_generalized_optimizer_preserves_eight_bounds(self) -> None:
        class PassingEvaluator:
            horizon = 35
            policy = {"allowed_arrival_steps": [25]}

            @staticmethod
            def best(values):
                del values
                return 0.25, {
                    "endpoint_step": 25,
                    "active_constraint": "position",
                }

        result = AUDIT._optimize_context_n(
            PassingEvaluator(),
            np.zeros((36, 3)),
            [np.zeros((36, 3)) for _ in range(8)],
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["best_coefficients"], [0.0] * 8)
        self.assertEqual(result["method"], "exact_baseline_already_passes")

    def test_t1_response_is_odd_zero_net_and_formal_length(self) -> None:
        def result(sign: int) -> dict:
            schedule = {}
            effect_states = [
                3,
                4,
                5,
                6,
                7,
                8,
                15,
                16,
                17,
                18,
                19,
                20,
            ]
            polarities = [1] * 6 + [-1] * 6
            for state, polarity in zip(effect_states, polarities):
                schedule[str(state - 1)] = [
                    0.0075 * sign * polarity,
                    0.0,
                    0.0,
                ]
            return {
                "spec": {
                    "r3c3_probe_id": "transport_mode0",
                    "r3c3_probe_mode": 0,
                    "r3c3_probe_sign": sign,
                    "r3c3_probe_amplitude": 0.0075,
                    "r3c3_probe_first_effect_state": 3,
                    "r3c3_probe_delta_by_task_issue_step": schedule,
                }
            }

        plus_y = np.arange(108, dtype=float).reshape(36, 3)
        minus_y = -plus_y
        plus_v = np.arange(72, dtype=float).reshape(36, 2)
        minus_v = -plus_v
        with mock.patch.object(
            AUDIT.t2.t1.r3c3,
            "_trajectory_arrays",
            side_effect=[
                (plus_y, plus_v),
                (minus_y, minus_v),
            ],
        ):
            audit, controller, delta_y, delta_v = AUDIT._t1_response(
                plus=result(1),
                minus=result(-1),
                plus_path=SCRIPT,
                minus_path=SCRIPT,
                basis_index=4,
            )
        self.assertEqual(delta_y.shape, (36, 3))
        self.assertEqual(delta_v.shape, (36, 2))
        self.assertEqual(audit["basis_index"], 4)
        self.assertEqual(controller["basis_index"], 4)
        self.assertNotIn("plus_file", controller)
        self.assertEqual(controller["temporal_shape"], "t1_long_separation_zero_net")


if __name__ == "__main__":
    unittest.main()
