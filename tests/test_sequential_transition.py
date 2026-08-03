from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import numpy as np

from tsc_rzip_rllib.control import sequential_transition as st


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24_sequential_transition_identification_370ms.json"


class SequentialTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_amplitude_coded_matrix_geometry(self):
        matrix = st.amplitude_coded_hadamard(self.cfg["schedule_contract"])
        self.assertEqual(matrix.shape, (24, 16))
        normalized = matrix / np.linalg.norm(matrix, axis=0, keepdims=True)
        self.assertEqual(np.linalg.matrix_rank(matrix), 16)
        self.assertAlmostEqual(np.linalg.cond(normalized), 2.82842712474619, places=12)
        for slot in range(4):
            block = matrix[:, 4 * slot : 4 * slot + 4]
            block /= np.linalg.norm(block, axis=0, keepdims=True)
            self.assertEqual(np.linalg.matrix_rank(block), 4)
            self.assertAlmostEqual(np.linalg.cond(block), 2.0, places=12)
        self.assertTrue(np.array_equal(matrix[16:], -matrix[:8]))

    def test_requested_actions_are_revealed_only_at_frozen_steps(self):
        matrix = st.amplitude_coded_hadamard(self.cfg["schedule_contract"])
        actions = st.requested_action_by_step(matrix[0], self.cfg["schedule_contract"])
        self.assertEqual(sorted(actions), [10, 11, 13, 14, 15, 16, 17, 18])
        for issue, cancel in zip([10, 13, 15, 17], [11, 14, 16, 18]):
            self.assertTrue(np.array_equal(actions[cancel], -actions[issue]))

    def test_predictor_item_whitelist_excludes_every_frozen_forbidden_field(self):
        forbidden = set(self.cfg["transition_model"]["forbidden_predictor_fields"])
        self.assertFalse(st.PREDICTOR_ITEM_FIELDS & forbidden)
        item = {
            "states": np.zeros((36, 5)),
            "horizon": 35,
            "target_offsets": np.zeros(3),
            "requested_action_by_step": {},
            "pair_id": "must_not_reach_predictor",
            "hidden_wire_current": [123.0],
            "future_measurement": [456.0],
        }
        payload = st._predictor_payload(item, self.cfg["transition_model"])
        self.assertEqual(set(payload), set(st.PREDICTOR_ITEM_FIELDS))

    def test_feature_cannot_see_a_future_requested_action(self):
        model = self.cfg["transition_model"]
        history = np.arange(50, dtype=float).reshape(10, 5) / 100.0
        requested = {10: np.ones(4), 17: np.full(4, 999.0)}
        changed = {10: np.ones(4), 17: np.full(4, -999.0)}
        first = st.feature_vector(
            history,
            requested,
            [0.0, 0.0, 0.0],
            step=10,
            horizon=35,
            candidate="Q",
            model_cfg=model,
        )
        second = st.feature_vector(
            history,
            changed,
            [0.0, 0.0, 0.0],
            step=10,
            horizon=35,
            candidate="Q",
            model_cfg=model,
        )
        self.assertTrue(np.array_equal(first, second))

    def _synthetic_items(self):
        items = []
        for pair_index in range(12):
            for item_index in range(50):
                rng = np.random.default_rng(1000 + 50 * pair_index + item_index)
                states = rng.normal(scale=0.01, size=(12, 5))
                action = np.asarray(
                    [
                        (item_index % 5 - 2) / 4,
                        ((item_index // 5) % 5 - 2) / 4,
                        (pair_index % 3 - 1) / 4,
                        ((pair_index + item_index) % 3 - 1) / 4,
                    ],
                    dtype=float,
                )
                states[11] = 0.65 * states[10] + 0.04 * np.pad(action, (0, 1))
                items.append(
                    {
                        "experiment_id": f"p{pair_index:02d}_{item_index:02d}",
                        "pair_id": f"pair_{pair_index:02d}",
                        "history_member": "plus" if item_index % 2 else "minus",
                        "partition": "training",
                        "states": states,
                        "horizon": 11,
                        "target_offsets": np.zeros(3),
                        "requested_action_by_step": {10: action},
                    }
                )
        return items

    def test_whole_pair_selection_and_recursive_evaluation(self):
        model_cfg = copy.deepcopy(self.cfg["transition_model"])
        model_cfg["feature_candidates"] = ["L"]
        model_cfg["ridge_grid"] = [0.0]
        model_cfg["maximum_absolute_recursive_scaled_error"] = 1e-7
        items = self._synthetic_items()
        formal = lambda _item, _states: True
        artifact = st.select_training_model(items, model_cfg, formal)
        self.assertTrue(artifact["passed"])
        self.assertEqual(artifact["training_pair_count"], 12)
        self.assertEqual(len(artifact["training_oof_rows"]), 600)
        self.assertLess(
            artifact["selected"]["maximum_absolute_recursive_scaled_error"], 1e-8
        )
        residual = artifact["training_componentwise_maximum_scaled_residual"]
        rows, summary = st.evaluate_recursive_set(
            artifact["model"], items[:50], model_cfg, formal, residual
        )
        self.assertEqual(len(rows), 50)
        self.assertEqual(summary["formal_verdict_reproduction_count"], 50)
        self.assertTrue(summary["passed"])

    def test_ridge_rejects_an_underdetermined_fit(self):
        with self.assertRaises(ValueError):
            st.fit_ridge(
                np.ones((3, 5)),
                np.ones((3, 5)),
                candidate="L",
                ridge=0.0,
                standard_deviation_floor=1e-12,
            )


if __name__ == "__main__":
    unittest.main()
