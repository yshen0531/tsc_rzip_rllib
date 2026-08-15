import json
from pathlib import Path
import unittest

import numpy as np

from scripts.rgeo_zgeo_1ms_id2b1_structured_model_development import (
    CONFIG_SHA256,
    apply_gates,
    feature_vector,
    fit_ridge,
    load_config,
    predict_ridge,
    sample_pairs,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2b1_structured_model_development.json"


def synthetic_row() -> dict:
    states = []
    q0 = np.linspace(-80.0, -67.0, 14)
    for index in range(33):
        states.append({
            "r_geo_m": 0.7 - index * 0.0005,
            "z_geo_m": 0.03 + index * 0.0007,
            "ip_a": 31000.0 - index * 10.0,
            "actual_current_a_tsc": q0.tolist(),
        })
    actions = []
    for issue in range(32):
        offset = np.zeros(14)
        virtual = [0.0, 0.0]
        if 10 <= issue <= 13:
            offset[0] = 0.15
            virtual = [1.0, 0.0]
        actions.append({
            "target_current_a_tsc": (q0 + offset).tolist(),
            "probe_virtual_action": virtual,
        })
    return {
        "states": states,
        "actions": actions,
        "context_id": "late_q0",
        "rollout_id": "synthetic",
        "is_context_baseline": False,
    }


class Id2B1StructuredModelDevelopmentTest(unittest.TestCase):
    def test_frozen_config_and_zero_execution_contract(self):
        self.assertEqual(sha256_file(CONFIG), CONFIG_SHA256)
        config = load_config(ROOT, CONFIG)
        self.assertEqual(config["plant_advances"], 0)
        self.assertEqual(config["tsc_calls"], 0)
        self.assertEqual(config["holdout_records_read"], 0)
        self.assertTrue(all(abs(value) < 1.0 for value in config["stable_memory"]["poles"]))

    def test_dense_response_keeps_every_state10_future(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        pairs = sample_pairs(config, dense=True)
        self.assertEqual(pairs[0], (10, 1))
        self.assertEqual(pairs[-1], (10, 22))
        self.assertEqual(len(pairs), 22)

    def test_feature_is_independent_of_future_state_truth(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        row = synthetic_row()
        reference = feature_vector(row, 10, 8, "stable_exp_contextual", config)
        for state in row["states"][11:]:
            state["r_geo_m"] += 1.0
            state["z_geo_m"] -= 1.0
            state["ip_a"] += 1e6
            state["actual_current_a_tsc"] = [999.0] * 14
        changed = feature_vector(row, 10, 8, "stable_exp_contextual", config)
        np.testing.assert_array_equal(reference, changed)

    def test_action_conditioned_feature_changes_with_known_future_issue(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        row = synthetic_row()
        blind = feature_vector(row, 10, 8, "action_blind_history", config)
        signed = feature_vector(row, 10, 8, "stable_exp_signed", config)
        row["actions"][10]["target_current_a_tsc"][1] += 0.3
        changed_blind = feature_vector(row, 10, 8, "action_blind_history", config)
        changed_signed = feature_vector(row, 10, 8, "stable_exp_signed", config)
        np.testing.assert_array_equal(blind, changed_blind)
        self.assertGreater(float(np.max(np.abs(signed - changed_signed))), 0.0)

    def test_ridge_fit_is_deterministic_and_finite(self):
        x = np.asarray([[0.0], [1.0], [2.0], [3.0]])
        y = np.column_stack([2.0 * x[:, 0], -x[:, 0], x[:, 0] + 1.0])
        first = fit_ridge(x, y, 1e-6)
        second = fit_ridge(x, y, 1e-6)
        self.assertEqual(first, second)
        predicted = predict_ridge(first, x)
        self.assertTrue(np.all(np.isfinite(predicted)))
        self.assertLess(float(np.max(np.abs(predicted - y))), 1e-5)

    def test_gate_requires_action_improvement_in_every_fold(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        contexts = config["data_contract"]["contexts"]
        def fold(context, response):
            return {
                "test_context": context,
                "absolute_geometry_p95_mm": 0.1,
                "absolute_geometry_max_mm": 0.2,
                "absolute_ip_p95_a": 1.0,
                "absolute_ip_max_a": 2.0,
                "absolute_scaled_rmse": 0.1,
                "response_scaled_rmse": response,
                "response_arm_scaled_rmse_p90": response,
                "response_arm_scaled_rmse_max": response,
                "peak_vector_direction_pass_fraction": 1.0,
            }
        metrics = {
            "persistence": [fold(c, 1.0) for c in contexts],
            "last_velocity": [fold(c, 1.0) for c in contexts],
            "action_blind_history": [fold(c, 1.0) for c in contexts],
            "stable_exp_signed": [fold(c, 0.5) for c in contexts],
            "stable_exp_signed_even": [fold(c, 0.5) for c in contexts],
            "stable_exp_contextual": [fold(c, 0.5) for c in contexts],
        }
        verdict = apply_gates(metrics, config)
        self.assertTrue(verdict["eligible_candidates"])
        metrics["stable_exp_signed"][1]["response_scaled_rmse"] = 0.95
        metrics["stable_exp_signed_even"][1]["response_scaled_rmse"] = 0.95
        metrics["stable_exp_contextual"][1]["response_scaled_rmse"] = 0.95
        verdict = apply_gates(metrics, config)
        self.assertEqual(verdict["eligible_candidates"], [])

    def test_launcher_contains_no_tsc_or_runner_entrypoint(self):
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2b1_structured_model_development.sh").read_text(encoding="utf-8")
        self.assertNotIn("gotsc", launcher)
        self.assertNotIn("TSCStepRunner", launcher)
        self.assertIn("structured_model_independent.py", launcher)


if __name__ == "__main__":
    unittest.main()
