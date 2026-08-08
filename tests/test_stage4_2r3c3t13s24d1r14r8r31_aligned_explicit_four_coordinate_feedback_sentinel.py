import copy
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r31_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)


class R8R31AlignedExplicitFourCoordinateFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel_370ms.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_config_is_valid(self):
        r8r31.validate_config(self.cfg, project_root=self.root)

    def test_frozen_config_rejects_g3_or_dimension_change(self):
        changed = copy.deepcopy(self.cfg)
        changed["bank_contract"]["r8r28_g3_trajectory_count"] = 32
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r31.validate_config(changed, project_root=self.root)

        changed = copy.deepcopy(self.cfg)
        changed["bank_contract"]["expanded_feature_dimension"] = 150
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r31.validate_config(changed, project_root=self.root)

    def test_q2_to_q4_has_frozen_coordinate_order(self):
        np.testing.assert_array_equal(
            r8r31.q2_to_q4([1.25, -0.75]),
            np.asarray([0.0, 0.75, 1.25, 0.0]),
        )
        with self.assertRaises(ValueError):
            r8r31.q2_to_q4([np.nan, 0.0])

    def test_causal_feature44_has_frozen_block_order(self):
        states = np.arange(100, dtype=float).reshape(20, 5)
        trajectory = [
            {"currents_a_tsc": (np.arange(14, dtype=float) + step).tolist()}
            for step in range(20)
        ]
        limits = np.arange(1, 15, dtype=float) * 10.0
        previous_q = np.asarray([-1.5, -0.75, 0.75, 1.5])
        feature = r8r31.causal_feature44(
            states,
            trajectory,
            decision=10,
            previous_decision=8,
            previous_q=previous_q,
            coil_limits=limits,
        )

        self.assertEqual(feature.shape, (44,))
        np.testing.assert_array_equal(feature[:12], states[7:11, :3].reshape(-1))
        np.testing.assert_allclose(
            feature[12:26], np.asarray(trajectory[10]["currents_a_tsc"]) / limits
        )
        np.testing.assert_allclose(feature[26:40], np.full(14, 2.0) / limits)
        np.testing.assert_allclose(feature[40:44], previous_q / 1.5)

    def test_expanded_feature238_has_frozen_action_and_interaction_order(self):
        feature = np.linspace(-1.0, 1.0, 44)
        q = np.asarray([2.0, 3.0, 5.0, 7.0])
        previous_q = np.asarray([1.0, 1.0, 2.0, 3.0])
        expanded = r8r31.expanded_feature238(feature, q, previous_q)
        expected_action = np.asarray(
            [
                2.0,
                3.0,
                5.0,
                7.0,
                4.0,
                6.0,
                10.0,
                14.0,
                9.0,
                15.0,
                21.0,
                25.0,
                35.0,
                49.0,
                1.0,
                2.0,
                3.0,
                4.0,
            ]
        )

        self.assertEqual(expanded.shape, (238,))
        np.testing.assert_array_equal(expanded[:44], feature)
        np.testing.assert_array_equal(expanded[44:62], expected_action)
        for coordinate in range(4):
            start = 62 + 44 * coordinate
            np.testing.assert_array_equal(
                expanded[start : start + 44], feature * q[coordinate]
            )
        np.testing.assert_array_equal(
            independent._expand(feature, q, previous_q), expanded
        )

    def test_predict_uses_requested_interval_and_target_count(self):
        model = {"intervals": []}
        for interval in range(6):
            offsets = []
            for offset in range(r8r31.MAX_COUNTS[interval]):
                coefficients = np.zeros((238, 5), dtype=float)
                coefficients[0, :] = interval + 1.0
                offsets.append(
                    {
                        "intercept": np.full(5, offset, dtype=float),
                        "coefficients": coefficients,
                    }
                )
            model["intervals"].append({"interval": interval, "offsets": offsets})
        row = {
            "interval": 4,
            "expanded": np.concatenate(([2.0], np.zeros(237))),
            "targets": np.zeros((3, 5)),
        }
        prediction = r8r31.predict(model, row)
        np.testing.assert_array_equal(
            prediction,
            np.asarray([[10.0] * 5, [11.0] * 5, [12.0] * 5]),
        )

    def test_transition_support_uses_full_eight_dimensional_pair(self):
        vectors = [np.zeros(8)] + [np.eye(8)[index] for index in range(8)]
        trajectories = []
        for index, vector in enumerate(vectors):
            trajectories.append(
                {
                    "trajectory_id": f"t{index}",
                    "intervals": [
                        {"previous_q": vector[:4], "q": vector[4:]}
                        for _ in range(6)
                    ],
                }
            )
        hulls = r8r31.transition_hulls(trajectories, self.cfg)

        self.assertEqual([row["affine_rank"] for row in hulls], [8] * 6)
        self.assertTrue(
            r8r31.transition_supported(
                hulls[0], np.full(4, 0.0625 * 1.5), np.full(4, 0.0625 * 1.5), self.cfg
            )
        )
        self.assertFalse(
            r8r31.transition_supported(
                hulls[0], np.full(4, 2.0), np.full(4, 2.0), self.cfg
            )
        )

    def test_fault_injections_all_fail_closed_to_hold(self):
        result = r8r31.fault_injections()
        self.assertTrue(result["passed"])
        self.assertEqual(result["pass_count"], 6)
        self.assertEqual(
            {row["selected_mode"] for row in result["rows"]},
            {"exact_target_hold_fallback"},
        )

    def test_independent_q_mapping_and_numeric_comparison(self):
        np.testing.assert_array_equal(
            independent._q4([1.25, -0.75]),
            r8r31.q2_to_q4([1.25, -0.75]),
        )
        self.assertAlmostEqual(
            independent._maximum_difference(
                {"a": [1.0, {"b": True}]}, {"a": [1.0 + 5e-13, {"b": True}]}
            ),
            5e-13,
            places=16,
        )
        self.assertTrue(
            np.isinf(
                independent._maximum_difference(
                    {"a": [1.0, {"b": True}]}, {"a": [1.0, {"b": False}]}
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
