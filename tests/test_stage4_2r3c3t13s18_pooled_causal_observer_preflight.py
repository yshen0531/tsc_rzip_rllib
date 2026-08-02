import copy
import json
from pathlib import Path
import unittest

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s18_pooled_causal_observer_preflight as s18,
)


class Stage4R3c3T13S18Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root / "configs" /
            "stage4_2r3c3t13s18_pooled_causal_observer_preflight.json"
        )
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_config_and_self_test(self):
        cfg = s18._load_config(self.config_path)
        result = s18.self_test(self.config_path)
        self.assertEqual(cfg["stage"], "Stage4.2R3c3T13S18")
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])

    def test_identity_mutation_fails_closed(self):
        cfg = copy.deepcopy(self.config)
        cfg["audit_identity"] = "changed"
        with self.assertRaises(ValueError):
            s18._validate_config(cfg)

    def test_feature_contract_mutation_fails_closed(self):
        cfg = copy.deepcopy(self.config)
        cfg["causal_features"]["legendre_degree"] = 2
        with self.assertRaises(ValueError):
            s18._validate_config(cfg)

    def test_tube_multiplier_mutation_fails_closed(self):
        cfg = copy.deepcopy(self.config)
        cfg["pooled_model"]["tube_multiplier"] = 4.1
        with self.assertRaises(ValueError):
            s18._validate_config(cfg)

    def test_execution_mutation_fails_closed(self):
        cfg = copy.deepcopy(self.config)
        cfg["execution"]["new_tsc_allowed"] = True
        with self.assertRaises(ValueError):
            s18._validate_config(cfg)

    def test_degree_three_design_is_fixed_full_rank(self):
        design = s18._degree3_design(self.config)
        self.assertEqual(design.shape, (10, 8))
        self.assertEqual(np.linalg.matrix_rank(design), 8)

    def test_same_trajectory_action_coordinate_needs_no_baseline(self):
        basis_fields = np.zeros((4, 14), dtype=float)
        basis_fields[:, :4] = np.eye(4) * 0.1
        coordinate = np.asarray([0.5, -0.25, 0.75, -0.5])
        signed = basis_fields.T @ coordinate
        turns = np.asarray([100.0] * 14)
        grid_a = 1e-6 * 1000.0 / turns
        center_fields = ["1.000E-01"] * 14
        center_target = np.asarray([float(field) * 1000.0 / 100.0 for field in center_fields])
        nominal = center_target - np.asarray([2.0] * 14) * grid_a
        radius_a = np.asarray([1.0] * 14) * grid_a
        prediction = {
            "uncertainty_radius_grid_units_tsc": [1.0] * 14,
            "bias_grid_units_tsc": [2.0] * 14,
            "output_grid_kAt": 1e-6,
            "readback_lower_a_tsc": (nominal - radius_a).tolist(),
            "readback_upper_a_tsc": (nominal + radius_a).tolist(),
        }
        trace = []
        for _ in range(11):
            trace.append({
                "r3c3t13s16_fixed_basis_delta_field_kAt_tsc": basis_fields.tolist(),
                "r3c3t13s9_signed_issue_delta_kAt_tsc": signed.tolist(),
                "r3c3t13s9_actuator_prediction": prediction,
                "r3c3t13s16_center_card15_fields": center_fields,
            })
        result = {"controller_trace": trace}
        payload = {"env_cfg": {"turns_display_order": [100.0] * 14}}
        _, recovered, radius, cosine, residual = s18._basis_and_coordinate(result, payload)
        np.testing.assert_allclose(recovered, coordinate, rtol=0.0, atol=1e-14)
        self.assertTrue(np.all(radius > 0.0))
        self.assertAlmostEqual(cosine, 1.0)
        self.assertLess(residual, 1e-14)

    def test_fit_predict_and_sensitivity_are_physical(self):
        rng = np.random.default_rng(7)
        x = rng.normal(size=(80, 9))
        scales = np.asarray([0.03, 0.03, 0.1, 0.1, 2000.0])
        weights = rng.normal(size=(9, 5)) * np.asarray([1e-4, 1e-4, 1e-3, 1e-3, 1.0])
        y = x @ weights
        model = s18._fit_model(x, y, 1e-8, scales, 1e-12)
        query = x[:1].copy()
        baseline = s18._predict(model, query, scales)[0]
        epsilon = 1e-6
        shifted = query.copy()
        shifted[0, 3] += epsilon
        finite_difference = (s18._predict(model, shifted, scales)[0] - baseline) / epsilon
        np.testing.assert_allclose(
            finite_difference, model["sensitivity"][:, 3], rtol=2e-6, atol=2e-8
        )

    def test_oof_holds_whole_groups(self):
        groups = np.asarray([f"g{i}" for i in range(8) for _ in range(3)])
        x = np.arange(24 * 9, dtype=float).reshape(24, 9)
        scales = np.asarray([0.03, 0.03, 0.1, 0.1, 2000.0])
        y = np.column_stack((x[:, :4], x[:, 4])) * scales
        prediction = s18._oof(x, y, groups, 1.0, scales, 1e-12)
        self.assertEqual(prediction.shape, y.shape)
        self.assertTrue(np.all(np.isfinite(prediction)))

    def test_model_serialization_roundtrip(self):
        rng = np.random.default_rng(11)
        x = rng.normal(size=(30, 9))
        y = rng.normal(size=(30, 5))
        scales = np.asarray([0.03, 0.03, 0.1, 0.1, 2000.0])
        model = s18._fit_model(x, y, 0.01, scales, 1e-12)
        restored = s18._deserialize_model(s18._serialize_model(model))
        np.testing.assert_allclose(
            s18._predict(model, x, scales), s18._predict(restored, x, scales),
            rtol=0.0, atol=0.0,
        )

    def test_digest_is_order_stable(self):
        self.assertEqual(s18._digest({"a": 1, "b": 2}), s18._digest({"b": 2, "a": 1}))

    def test_forbidden_predictor_contract_contains_labels_and_future(self):
        forbidden = set(self.config["causal_features"]["forbidden_predictor_fields"])
        self.assertTrue({
            "pair_id", "history_member", "target_id", "action_delay_steps",
            "slew_scale", "future_measurement", "matched_baseline_value",
        }.issubset(forbidden))


if __name__ == "__main__":
    unittest.main()
