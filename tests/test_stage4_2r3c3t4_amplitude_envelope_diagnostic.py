from __future__ import annotations

import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t4_amplitude_envelope_diagnostic as diagnostic,
)


class _SyntheticEvaluator:
    horizon = 1
    policy = {"allowed_arrival_steps": [1]}

    @staticmethod
    def endpoint_margin(
        values: np.ndarray, endpoint: int
    ) -> tuple[float, dict[str, object]]:
        margin = float(values[-1, 0] - 1.1)
        return margin, {
            "endpoint_step": endpoint,
            "minimum_signed_margin": margin,
            "active_constraint": "position",
        }

    def best(
        self, values: np.ndarray
    ) -> tuple[float, dict[str, object]]:
        return self.endpoint_margin(values, 1)


class Stage42R3C3T4AmplitudeEnvelopeDiagnosticTests(
    unittest.TestCase
):
    def test_transport_only_bounds_preserve_local_four(self) -> None:
        self.assertEqual(
            diagnostic._bounds_for_profile("transport_only", 1.5),
            (1.0, 1.0, 1.0, 1.0, 1.5, 1.5, 1.5, 1.5),
        )

    def test_uniform_bounds_expand_all_eight(self) -> None:
        self.assertEqual(
            diagnostic._bounds_for_profile("uniform_all", 1.25),
            (1.25,) * 8,
        )

    def test_unknown_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown amplitude profile"):
            diagnostic._bounds_for_profile("unknown", 1.5)

    def test_optimizer_uses_expanded_bound(self) -> None:
        baseline = np.zeros((2, 3), dtype=float)
        columns = [np.zeros_like(baseline) for _ in range(8)]
        columns[4][-1, 0] = 1.0
        result = diagnostic._optimize_context_bounds(
            _SyntheticEvaluator(),
            baseline,
            columns,
            bounds=(1.0, 1.0, 1.0, 1.0, 1.25, 1.25, 1.25, 1.25),
            t3_seed=(0.0,) * 8,
        )
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["best_minimum_signed_margin"], 0.0)
        self.assertAlmostEqual(result["best_coefficients"][4], 1.25)


if __name__ == "__main__":
    unittest.main()
