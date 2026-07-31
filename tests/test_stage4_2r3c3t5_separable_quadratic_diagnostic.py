from __future__ import annotations

import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t5_separable_quadratic_diagnostic as diagnostic,
)


class _SyntheticEvaluator:
    horizon = 1
    policy = {"allowed_arrival_steps": [1]}

    @staticmethod
    def endpoint_margin(
        values: np.ndarray, endpoint: int
    ) -> tuple[float, dict[str, object]]:
        margin = float(values[-1, 0] - 0.4)
        return margin, {
            "endpoint_step": endpoint,
            "minimum_signed_margin": margin,
            "active_constraint": "position",
        }

    def best(
        self, values: np.ndarray
    ) -> tuple[float, dict[str, object]]:
        return self.endpoint_margin(values, 1)


class Stage42R3C3T5SeparableQuadraticDiagnosticTests(
    unittest.TestCase
):
    def test_signed_file_metadata_supports_embedded_dict(self) -> None:
        response = {
            "plus_file": {
                "path": "plus.json.gz",
                "sha256": "a" * 64,
                "size_bytes": 12,
            }
        }
        self.assertEqual(
            diagnostic._signed_file_metadata(response, "plus"),
            ("plus.json.gz", "a" * 64, 12),
        )

    def test_signed_file_metadata_supports_separate_hash(self) -> None:
        response = {
            "minus_file": "minus.json.gz",
            "minus_sha256": "b" * 64,
        }
        self.assertEqual(
            diagnostic._signed_file_metadata(response, "minus"),
            ("minus.json.gz", "b" * 64, None),
        )

    def test_prediction_is_exact_at_signed_endpoints(self) -> None:
        baseline = np.zeros((2, 3), dtype=float)
        odd = [np.zeros_like(baseline) for _ in range(8)]
        even = [np.zeros_like(baseline) for _ in range(8)]
        odd[0][-1, 0] = 0.3
        even[0][-1, 0] = 0.2
        plus = diagnostic._predict(
            baseline, odd, even, [1.0] + [0.0] * 7
        )
        minus = diagnostic._predict(
            baseline, odd, even, [-1.0] + [0.0] * 7
        )
        self.assertAlmostEqual(plus[-1, 0], 0.5)
        self.assertAlmostEqual(minus[-1, 0], -0.1)

    def test_high_precision_endpoint_auth_avoids_one_ip_ulp(self) -> None:
        baseline = np.asarray([[0.0, 0.0, 29_600.0]], dtype=float)
        plus = np.asarray([[0.0, 0.0, 29_618.8526]], dtype=float)
        minus = np.asarray([[0.0, 0.0, 29_648.7562]], dtype=float)
        odd = (plus - minus) / 2.0
        even = (plus + minus) / 2.0 - baseline
        float64_error = max(
            float(np.max(np.abs(baseline + odd + even - plus))),
            float(np.max(np.abs(baseline - odd + even - minus))),
        )
        self.assertGreater(float64_error, 1.0e-12)
        self.assertEqual(
            diagnostic._signed_endpoint_reproduction_error(
                baseline, plus, minus
            ),
            0.0,
        )

    def test_quadratic_optimizer_can_use_even_term(self) -> None:
        baseline = np.zeros((2, 3), dtype=float)
        odd = [np.zeros_like(baseline) for _ in range(8)]
        even = [np.zeros_like(baseline) for _ in range(8)]
        even[3][-1, 0] = 0.5
        result = diagnostic._optimize_context(
            _SyntheticEvaluator(),
            baseline,
            odd,
            even,
            t3_seed=(0.0,) * 8,
        )
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["best_minimum_signed_margin"], 0.0)
        self.assertAlmostEqual(abs(result["best_coefficients"][3]), 1.0)


if __name__ == "__main__":
    unittest.main()
