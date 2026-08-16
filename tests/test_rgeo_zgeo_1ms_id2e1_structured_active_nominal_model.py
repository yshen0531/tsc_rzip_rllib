import json
from pathlib import Path
import unittest

import numpy as np

from scripts.rgeo_zgeo_1ms_id2e1_structured_active_nominal_model import (
    CONFIG_SHA256,
    fir_features,
    fit_no_intercept,
    fixed_pole_features,
    load_config,
    predict,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2e1_structured_active_nominal_model.json"


class Id2E1StructuredActiveNominalModelTest(unittest.TestCase):
    def test_frozen_config_and_zero_tsc_contract(self):
        self.assertEqual(sha256_file(CONFIG), CONFIG_SHA256)
        config = load_config(ROOT, CONFIG)
        self.assertEqual(config["plant_advances"], 0)
        self.assertEqual(config["tsc_calls"], 0)
        self.assertEqual(config["calibration_records_read"], 0)
        self.assertEqual(config["blind_holdout_records_read"], 0)
        self.assertEqual(config["selection_after_evaluator_open"], "forbidden")

    def test_fixed_poles_are_stable_and_zero_input_is_zero_output(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        poles = config["smooth_channel"]["fixed_poles"]
        self.assertTrue(all(abs(value) < 1.0 for value in poles))
        features = fixed_pole_features(np.zeros((32, 2)), poles, True, True)
        np.testing.assert_array_equal(features, np.zeros_like(features))

    def test_issue_to_effect_delay_is_one_state(self):
        actions = np.zeros((32, 2))
        actions[16, 0] = 1.0
        features = fixed_pole_features(actions, [0.0], False, False)
        self.assertEqual(features[16, 0], 0.0)
        self.assertEqual(features[17, 0], 1.0)
        self.assertEqual(features[18, 0], 0.0)
        fir = fir_features(actions, 16, True)
        self.assertEqual(fir[16, 0], 0.0)
        self.assertEqual(fir[17, 0], 1.0)

    def test_signed_even_features_distinguish_sign_without_label(self):
        plus = np.zeros((32, 1))
        minus = np.zeros((32, 1))
        plus[4, 0], minus[4, 0] = 1.0, -1.0
        p = fixed_pole_features(plus, [0.5], True, False)
        m = fixed_pole_features(minus, [0.5], True, False)
        self.assertEqual(p[5, 0], -m[5, 0])
        self.assertEqual(p[5, 1], m[5, 1])

    def test_no_intercept_fit_preserves_zero_action_response(self):
        x = np.asarray([[1.0], [2.0], [3.0], [4.0]])
        y = np.column_stack([2.0 * x[:, 0], -x[:, 0], 3.0 * x[:, 0]])
        model = fit_no_intercept(x, y, 1e-6)
        np.testing.assert_allclose(predict(model, np.zeros((1, 1))), np.zeros((1, 3)), atol=0.0)
        self.assertLess(float(np.max(np.abs(predict(model, x) - y))), 1e-5)

    def test_launcher_is_zero_tsc_and_runs_independent_after_primary(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2e1_structured_active_nominal_model.sh").read_text(encoding="utf-8")
        self.assertNotIn("gotsc", text.lower())
        self.assertNotIn("TSCStepRunner", text)
        self.assertIn("id2e1_structured_active_nominal_model.py", text)
        self.assertIn("id2e1_structured_active_nominal_model_independent.py", text)

    def test_evaluator_is_single_open_and_no_neural_candidate(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["selection_after_evaluator_open"], "forbidden")
        self.assertEqual(config["neural_residual"], "blocked_pending_id2e1_result")
        self.assertEqual(config["evaluator_source"]["data_role"], "single_open_immutable_evaluator_only")
        self.assertNotIn("gru", " ".join(config["smooth_channel"]["candidate_order"]).lower())


if __name__ == "__main__":
    unittest.main()
