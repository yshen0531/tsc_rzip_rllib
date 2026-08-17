import copy
import json
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2l1_structured_history_model as stage


ROOT = Path(__file__).resolve().parents[1]


class ID2L1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(stage.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_zero_plant_contract(self):
        self.assertEqual(stage.sha256(stage.CONFIG), stage.CONFIG_SHA256)
        self.assertEqual(self.config["new_tsc_calls"], 0)
        self.assertEqual(self.config["reset_calls"], 0)
        self.assertEqual(self.config["plant_advances"], 0)

    def test_whole_history_pair_folds(self):
        held = [item for fold in self.config["folds"] for item in fold["held_histories"]]
        self.assertEqual(sorted(held), [f"h{i:02d}" for i in range(8)])
        self.assertEqual(len(set(held)), 8)
        self.assertTrue(all(len(fold["held_histories"]) == 2 for fold in self.config["folds"]))

    def test_candidate_order_and_nonselectable_blind(self):
        self.assertFalse(self.config["candidates"]["action_blind"]["selectable"])
        self.assertEqual(self.config["eligibility"]["simplicity_order"], [
            "stable_signed", "stable_signed_even", "stable_contextual", "structured_gru_residual"
        ])
        self.assertEqual(self.config["candidates"]["structured_gru_residual"]["base_candidate"],
                         "stable_signed_even")

    def test_future_and_label_leakage_is_forbidden(self):
        forbidden = set(self.config["data_contract"]["forbidden_model_inputs"])
        for name in ("future_r_geo_z_geo_ip", "future_actual_or_readback_current", "future_matched_baseline",
                     "group_id", "direction_id", "sign", "conditioner_label", "holdout"):
            self.assertIn(name, forbidden)

    def test_stable_memory_has_no_fitted_state_matrix(self):
        self.assertFalse(self.config["backbone"]["fitted_autoregressive_state_matrix"])
        self.assertEqual(self.config["backbone"]["fixed_poles"], [0.0, 0.5, 0.8, 0.95])
        self.assertTrue(all(0.0 <= pole < 1.0 for pole in self.config["backbone"]["fixed_poles"]))

    def test_memory_shapes_and_effect_timing(self):
        data = stage.extract_dataset(stage.load_stage())
        cell = data.cells[0]
        values = stage.memory_matrix(cell, data, self.config["backbone"]["fixed_poles"])
        self.assertEqual(values["level"].shape, (34, 4, 3))
        self.assertEqual(self.config["data_contract"]["issue_to_effect_state_offset"], 1)
        self.assertEqual(data.action_rank, 3)

    def test_contextual_features_are_larger_but_finite(self):
        data = stage.extract_dataset(stage.load_stage())
        cell = data.cells[0]
        signed = stage.feature_matrix(cell, data, self.config, "stable_signed")
        even = stage.feature_matrix(cell, data, self.config, "stable_signed_even")
        contextual = stage.feature_matrix(cell, data, self.config, "stable_contextual")
        self.assertEqual(signed.shape[0], 34)
        self.assertLess(signed.shape[1], even.shape[1])
        self.assertLess(even.shape[1], contextual.shape[1])
        self.assertTrue(np.all(np.isfinite(contextual)))

    def test_integrity_mutation_is_rejected(self):
        mutated = copy.deepcopy(self.config)
        mutated["plant_advances"] = 1
        self.assertNotEqual(mutated, self.config)
        self.assertEqual(self.config["plant_advances"], 0)

    def test_gate_requires_action_response_not_only_absolute_drift(self):
        gate = self.config["eligibility"]
        self.assertLess(gate["each_fold_response_nrmse_strict_max"], 1.0)
        self.assertGreater(gate["minimum_action_blind_improvement_fraction"], 0.0)
        self.assertGreaterEqual(gate["minimum_positive_peak_cosine_per_fold"], 7)


if __name__ == "__main__":
    unittest.main()
