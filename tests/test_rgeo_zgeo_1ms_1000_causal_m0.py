from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_1000_causal_m0 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_causal_m0.json"


class Fixed1000CausalM0Test(unittest.TestCase):
    def test_frozen_identity_roles_and_manifest(self) -> None:
        stage, _, rows = primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(len(rows), 25)
        self.assertEqual(stage["executed_action_rank"], 6)
        self.assertEqual(stage["data_roles"]["fixed_1100_data"], "forbidden")
        self.assertEqual(stage["data_roles"]["calibration"], "unopened")
        self.assertEqual(stage["data_roles"]["holdout"], "unopened")

    def test_feature_rows_are_causal_and_use_rank_six_exact_action_span(self) -> None:
        stage, cfg, rows = primary.load(CONFIG)
        samples, basis, singular, names, blind_width = primary.feature_rows(
            rows, cfg, stage["fixed_memory_poles"], stage["executed_action_rank"]
        )
        self.assertEqual(len(samples), 1184)
        self.assertEqual(basis.shape, (14, 6))
        self.assertEqual(len(singular), 6)
        self.assertEqual(blind_width, 11)
        self.assertEqual(len(names), 56)

        mutated = copy.deepcopy(rows)
        mutated[1][2]["states"][10]["r_geo_m"] += 1.0
        changed, *_ = primary.feature_rows(
            mutated, cfg, stage["fixed_memory_poles"], stage["executed_action_rank"]
        )
        left = [sample["x"] for sample in samples if sample["family"] == samples[64]["family"]][:9]
        right = [sample["x"] for sample in changed if sample["family"] == changed[64]["family"]][:9]
        np.testing.assert_allclose(left, right, atol=0.0, rtol=0.0)

    def test_ridge_fit_and_prediction_are_deterministic(self) -> None:
        samples = []
        for value in range(20):
            x = np.asarray([float(value), float(value % 3)])
            y = np.asarray([2.0 * value, -float(value), 0.5 * value])
            samples.append({"x": x, "y": y})
        scales = np.ones(3)
        model = primary.fit_ridge(samples, 2, 1e-9, scales)
        first = primary.predict(model, samples, scales)
        second = primary.predict(model, samples, scales)
        np.testing.assert_allclose(first, second, atol=0.0, rtol=0.0)
        self.assertLess(float(np.max(np.abs(first - np.asarray([sample["y"] for sample in samples])))), 1e-5)

    def test_whole_family_folds_are_nonempty_and_disjoint_from_training_selector(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        families = [
            "d0:p10_even_plus", "d0:p24_odd_minus", "d1:p08_even_plus",
            "d1:p24_odd_plus", "n0:depth04", "n0:depth08", "n0:depth12", "n0:depth16",
        ]
        for fold in stage["whole_family_folds"]:
            held = [family for family in families if primary._selectors(stage, fold, family)]
            self.assertTrue(held, fold["name"])

    def test_launcher_is_zero_tsc_model_only(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_causal_m0.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_M0_SOURCE_REVISION", text)
        self.assertNotIn("gotsc", text)
        self.assertNotIn("step_current", text)


if __name__ == "__main__":
    unittest.main()
