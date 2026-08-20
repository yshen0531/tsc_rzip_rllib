import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/rgeo_zgeo_1ms_id2z19_two_candidate_model_comparison.py"
SPEC = importlib.util.spec_from_file_location("id2z19", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class ID2Z19Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = mod.load_stage()
        cls.data = mod.load_dataset(cls.stage)

    def test_frozen_identity_and_two_candidates(self):
        self.assertEqual(self.stage["stage"], "ID-2Z19")
        self.assertEqual(tuple(self.stage["candidate_order"]), mod.CANDIDATES)
        self.assertEqual(self.stage["fit_and_execution_counts"]["candidate_count"], 2)
        self.assertEqual(self.stage["fit_and_execution_counts"]["new_tsc_calls"], 0)

    def test_roles_and_whole_history_folds(self):
        self.assertEqual(len(self.data.families), 14)
        held = [name for fold in self.stage["whole_history_folds"] for name in fold["held_family_ids"]]
        self.assertEqual(sorted(held), sorted(self.data.families))
        self.assertEqual(len(set(held)), 14)
        self.assertEqual(len(self.stage["zero_weight_replay_ids"]), 2)
        self.assertEqual(self.stage["unexecuted_calibration_ids"], ["c00", "c01", "c02", "c03"])
        self.assertEqual(self.stage["unexecuted_blind_holdout_ids"], ["v00", "v01", "v02", "v03"])

    def test_data_clocks_widths_and_action_rank(self):
        self.assertEqual(np.linalg.matrix_rank(self.data.action_basis), 3)
        for cell in self.data.cells.values():
            self.assertEqual(cell.states.shape, (66, 3))
            self.assertEqual(cell.actual.shape, (66, 14))
            self.assertEqual(cell.active.shape, (66, 14))
            self.assertEqual(cell.targets.shape, (65, 14))
            for issue, action in enumerate(cell.actions):
                self.assertEqual(action["issue_step"], issue)
                self.assertEqual(action["effect_state_index"], issue + 1)

    def test_complete_window_count_and_horizons(self):
        x, y, keys = mod.training_rows(self.data.families, self.data, self.stage)
        expected_per_family = sum(1 for origin in range(16, 58) for h in mod.HORIZONS if origin + h < 66)
        self.assertEqual(len(keys), 14 * expected_per_family)
        self.assertEqual(x.shape[0], y.shape[0])
        self.assertEqual(y.shape[1], 3)
        self.assertEqual(sorted(set(h for _, _, h in keys)), list(mod.HORIZONS))

    def test_feature_is_causal_under_future_truth_mutation(self):
        cell = self.data.cells["d00_plus"]
        memory = mod.memories(cell, self.data, self.stage["stable_regularized_lpv"]["fixed_action_memory_poles"])
        before = mod.lpv_feature(cell, 24, 8, self.data, self.stage, memory)
        mutated_states = cell.states.copy()
        mutated_states[25:] += np.array([1.0, 2.0, 3.0])
        changed = mod.Cell(cell.family_id, cell.pair_id, cell.sign, mutated_states,
                           cell.actual, cell.active, cell.targets, cell.actions)
        after = mod.lpv_feature(changed, 24, 8, self.data, self.stage, memory)
        np.testing.assert_array_equal(before, after)

    def test_future_actual_current_is_not_used(self):
        cell = self.data.cells["d01_plus"]
        memory = mod.memories(cell, self.data, self.stage["stable_regularized_lpv"]["fixed_action_memory_poles"])
        before = mod.lpv_feature(cell, 20, 8, self.data, self.stage, memory)
        actual = cell.actual.copy()
        actual[21:] += 999.0
        changed = mod.Cell(cell.family_id, cell.pair_id, cell.sign, cell.states,
                           actual, cell.active, cell.targets, cell.actions)
        after = mod.lpv_feature(changed, 20, 8, self.data, self.stage, memory)
        np.testing.assert_array_equal(before, after)

    def test_pair_folds_keep_siblings_together(self):
        for fold in self.stage["whole_history_folds"]:
            if fold["kind"] == "signed_pair":
                self.assertEqual(len(fold["held_family_ids"]), 2)
                roots = {name.rsplit("_", 1)[0] for name in fold["held_family_ids"]}
                self.assertEqual(len(roots), 1)

    def test_endpoint_value_uses_only_origin_endpoint_and_source(self):
        cell = self.data.cells["d02_minus"]
        value = mod.endpoint_value(cell.states[28], cell.states[24], 4,
                                   self.data.source_state, self.stage)
        self.assertTrue(np.isfinite(value))
        self.assertGreaterEqual(value, 0.0)

    def test_ridge_fit_is_finite_and_bounded_dimension(self):
        train = tuple(name for name in self.data.families if not name.startswith("d00_"))
        model = mod.fit_ridge(train, self.data, self.stage)
        self.assertLessEqual(model.coefficients.shape[0], 40)
        self.assertTrue(np.all(np.isfinite(model.coefficients)))
        self.assertGreater(model.feature_rank, 0)

    def test_forbidden_inputs_are_frozen_false(self):
        forbidden = ("future_actual_current", "wire_current", "sprsina",
                     "family_pair_sign_role_or_token_labels", "future_rgeo_zgeo_ip")
        self.assertTrue(all(self.stage["allowed_inputs"][key] is False for key in forbidden))

    def test_launcher_is_zero_tsc_model_only(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2z19_two_candidate_model_comparison.sh").read_text()
        self.assertIn("ID2Z19_OUTPUT", text)
        self.assertIn("ID2Z19_SOURCE_REVISION", text)
        self.assertNotIn("gotsc", text)
        self.assertNotIn("step_current", text)


if __name__ == "__main__":
    unittest.main()
