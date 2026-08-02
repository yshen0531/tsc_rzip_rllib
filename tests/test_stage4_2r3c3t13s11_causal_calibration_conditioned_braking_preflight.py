from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s11_causal_calibration_conditioned_braking_preflight as audit,
)


class Stage42R3C3T13S11CausalCalibrationPreflightTests(unittest.TestCase):
    def test_design_hash_is_authenticated_before_analysis(self) -> None:
        with mock.patch.object(audit.common, "_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "design SHA-256"):
                audit.s10.authenticate_exact_file(
                    Path("design.md"), audit.DESIGN_SHA256, "design"
                )

    def test_projection_support_is_nonvacuous_in_original_space(self) -> None:
        basis = np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        self.assertEqual(audit._projection_residual(np.asarray([2.0, 3.0, 0.0]), basis), 0.0)
        self.assertAlmostEqual(
            audit._projection_residual(np.asarray([0.0, 0.0, 4.0]), basis), 1.0
        )

    def test_interaction_row_has_frozen_twelve_column_order(self) -> None:
        row = audit._interaction_row(
            np.asarray([1.0, 2.0, 3.0, 4.0]), np.asarray([5.0, 7.0])
        )
        np.testing.assert_array_equal(
            row,
            np.asarray(
                [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 15.0, 20.0, 7.0, 14.0, 21.0, 28.0]
            ),
        )

    def test_affine_rank_of_three_points_cannot_exceed_two(self) -> None:
        values = np.asarray(
            [
                [1.0e9, 1.0, 4.0, 0.0],
                [1.0e9 + 1.0e-4, 2.0, 4.0, 0.0],
                [1.0e9 - 2.0e-4, 1.0, 5.0, 0.0],
            ]
        )
        self.assertEqual(audit._affine_rank(values), 2)

    def test_signature_schema_contains_no_hidden_identity_or_future(self) -> None:
        self.assertFalse(audit.s7.FORBIDDEN_FEATURE_NAMES.intersection(audit.SIGNATURE_NAMES))
        self.assertNotIn("counterfactual", " ".join(audit.SIGNATURE_NAMES))

    def test_routes_never_authorize_controller_or_rl(self) -> None:
        self.assertIn("DUAL_WINDOW_TSC_REQUIRED", audit.PASS_ROUTE)
        self.assertIn("PERSISTENT_OBSERVER_REDESIGN", audit.FAIL_ROUTE)
        self.assertNotEqual(audit.PASS_ROUTE, audit.FAIL_ROUTE)


if __name__ == "__main__":
    unittest.main()
