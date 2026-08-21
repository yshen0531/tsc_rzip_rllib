from __future__ import annotations

import copy
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_1000_causal_m0 as m0
from scripts import rgeo_zgeo_1ms_1000_causal_m1 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_causal_m1.json"


class Fixed1000CausalM1Test(unittest.TestCase):
    def test_frozen_identity_and_predecessor(self) -> None:
        stage, samples, basis, singular, names = primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(len(samples), 1184)
        self.assertEqual(basis.shape, (14, 6))
        self.assertEqual(len(singular), 6)
        self.assertEqual(len(names), 176)
        self.assertEqual(stage["data_roles"]["fixed_1100_data"], "forbidden")
        self.assertEqual(stage["data_roles"]["calibration"], "unopened")

    def test_event_rows_are_causal_and_event_is_one_hot(self) -> None:
        m0_stage, cfg, rows = m0.load(ROOT / "configs/rgeo_zgeo_1ms_1000_causal_m0.json")
        raw, _, _, names, _ = m0.feature_rows(rows, cfg, m0_stage["fixed_memory_poles"], 6)
        samples, enhanced_names = primary.event_rows(raw, names, 63)
        self.assertEqual(len(enhanced_names), 176)
        for sample in samples[:70]:
            event = sample["x_event"][-64:]
            self.assertEqual(float(event.sum()), 1.0)
            self.assertEqual(float(event[sample["issue"]]), 1.0)

        mutated = copy.deepcopy(rows)
        mutated[1][2]["states"][10]["r_geo_m"] += 1.0
        changed_raw, *_ = m0.feature_rows(mutated, cfg, m0_stage["fixed_memory_poles"], 6)
        changed, _ = primary.event_rows(changed_raw, names, 63)
        family = samples[64]["family"]
        left = [sample["x_event"] for sample in samples if sample["family"] == family][:9]
        right = [sample["x_event"] for sample in changed if sample["family"] == family][:9]
        np.testing.assert_allclose(left, right, atol=0.0, rtol=0.0)

    def test_small_ensemble_is_deterministic(self) -> None:
        samples = []
        for value in range(24):
            x = np.asarray([float(value), float(value % 4), float(value % 2)])
            response = np.asarray([0.1 * value, -0.2 * value, 0.5 * value])
            samples.append({"x_event": x, "response": response})
        scales = np.ones(3)
        first = primary.fit_ensemble(samples, [8, 4], [7], 15, 0.01, 0.0, scales)
        second = primary.fit_ensemble(samples, [8, 4], [7], 15, 0.01, 0.0, scales)
        np.testing.assert_allclose(
            primary.predict_response(first, samples, scales),
            primary.predict_response(second, samples, scales), atol=0.0, rtol=0.0,
        )

    def test_whole_family_folds_are_frozen(self) -> None:
        stage, samples, *_ = primary.load(CONFIG)
        for fold in stage["whole_family_folds"]:
            test = [sample for sample in samples if primary._selectors(fold, sample["family"])]
            train = [sample for sample in samples if not primary._selectors(fold, sample["family"])]
            self.assertTrue(test)
            self.assertTrue(train)
            self.assertFalse(any(sample["group"] == "b0" for sample in test))

    def test_launcher_is_zero_tsc_and_no_model_search(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_causal_m1.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_M1_SOURCE_REVISION", text)
        self.assertNotIn("gotsc", text)
        self.assertNotIn("step_current", text)
        self.assertNotIn("grid", text.lower())


if __name__ == "__main__":
    unittest.main()
