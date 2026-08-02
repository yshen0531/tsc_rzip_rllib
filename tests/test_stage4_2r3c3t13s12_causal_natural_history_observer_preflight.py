from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s12_causal_natural_history_observer_preflight as audit,
)


class Stage42R3C3T13S12NaturalHistoryObserverTests(unittest.TestCase):
    def test_design_hash_is_frozen(self) -> None:
        with mock.patch.object(audit.common, "_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "design SHA-256"):
                audit.s10.authenticate_exact_file(
                    Path("design.md"), audit.DESIGN_SHA256, "design"
                )

    def test_rms_whitening_is_training_only_and_unit_rms(self) -> None:
        values = np.asarray([[1.0, 2.0], [-1.0, 4.0], [1.0, -2.0]])
        whitened, rms, passed = audit._rms_whiten(values)
        self.assertTrue(passed)
        np.testing.assert_allclose(np.sqrt(np.mean(whitened**2, axis=0)), 1.0)
        np.testing.assert_allclose(rms, np.sqrt(np.mean(values**2, axis=0)))

    def test_zero_rms_fails_closed(self) -> None:
        whitened, rms, passed = audit._rms_whiten(np.zeros((3, 2)))
        self.assertFalse(passed)
        np.testing.assert_array_equal(whitened, np.zeros((3, 2)))
        np.testing.assert_array_equal(rms, np.zeros(2))

    def test_history_signature_uses_deployed_target_and_causal_differences(self) -> None:
        trajectory = []
        for index in range(15):
            trajectory.append(
                {
                    "R": 0.79 + (0.001 if index >= 1 else 0.0),
                    "Z": -0.01,
                    "Ip": 30000.0,
                    "currents_a_tsc": [float(index)] * 14,
                }
            )
        baseline = {
            "spec": {
                "action_delay_steps": 2,
                "slew_scale": 0.9,
                "target_R_offset_m": 0.01,
                "target_Z_offset_m": -0.01,
                "target_Ip_offset_A": 0.0,
            },
            "trajectory": trajectory,
        }
        payload = {
            "cfg": {"target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0}},
            "train_cfg": {"target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0}},
            "env_cfg": {
                "min_current_a_display_order": [-100.0] * 14,
                "max_current_a_display_order": [100.0] * 14,
            },
        }
        result = audit._history_signature(baseline, payload)
        self.assertTrue(result["passed"])
        self.assertEqual(result["history_vector_length"], 527)
        self.assertAlmostEqual(result["values"][0], 1.0)
        self.assertEqual(result["values"][5], 0.0)
        self.assertEqual(result["values"][34], 0.0)
        self.assertAlmostEqual(result["values"][35 + 3], 1.0)
        self.assertEqual(result["values"][35 + 5], 1.0)
        self.assertEqual(result["values"][35 + 34], 1.0)

    def test_history_signature_rejects_mismatched_payload_base_targets(self) -> None:
        trajectory = [
            {
                "R": 0.75,
                "Z": 0.0,
                "Ip": 30000.0,
                "currents_a_tsc": [0.0] * 14,
            }
            for _ in range(17)
        ]
        baseline = {
            "spec": {
                "action_delay_steps": 0,
                "slew_scale": 1.0,
                "target_R_offset_m": 0.0,
                "target_Z_offset_m": 0.0,
                "target_Ip_offset_A": 0.0,
            },
            "trajectory": trajectory,
        }
        payload = {
            "cfg": {"target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0}},
            "train_cfg": {"target": {"R": 0.76, "Z": 0.0, "Ip": 30000.0}},
            "env_cfg": {
                "min_current_a_display_order": [-100.0] * 14,
                "max_current_a_display_order": [100.0] * 14,
            },
        }
        with self.assertRaisesRegex(ValueError, "base target contract mismatch"):
            audit._history_signature(baseline, payload)

    def test_history_schema_has_only_visible_causal_fields(self) -> None:
        self.assertEqual(len(audit.STATE_FIELDS), 35)
        self.assertFalse(
            audit.s7.FORBIDDEN_FEATURE_NAMES.intersection(audit.STATE_FIELDS)
        )
        joined = " ".join(audit.STATE_FIELDS)
        self.assertNotIn("action", joined)
        self.assertNotIn("wire", joined)
        self.assertNotIn("vessel", joined)

    def test_routes_require_new_sequence_or_redesign(self) -> None:
        self.assertIn("Q3_SEQUENCE_TSC_REQUIRED", audit.PASS_ROUTE)
        self.assertIn("NONLINEAR_OBSERVER_REDESIGN", audit.FAIL_ROUTE)


if __name__ == "__main__":
    unittest.main()
