from __future__ import annotations

from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_1000_value_v0 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_v0.json"


class Fixed1000ValueV0Test(unittest.TestCase):
    def test_frozen_dataset_and_roles(self) -> None:
        stage, contexts = primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(set(contexts), {"q0", "even_plus", "odd_plus"})
        self.assertEqual(sum(len(value) for value in contexts.values()), 12)
        self.assertEqual(stage["data_roles"]["calibration_histories"], "unopened")
        self.assertEqual(stage["data_roles"]["blind_histories"], "unopened")
        self.assertEqual(stage["data_roles"]["fixed_1100_data"], "forbidden")

    def test_fit_set_adds_fixed_floor(self) -> None:
        contexts = {
            "a": {"x": {4: np.asarray([1.0, 2.0, 3.0])}},
            "b": {"x": {4: np.asarray([1.2, 2.4, 7.0])}},
        }
        model = primary.fit_set(contexts, ["x"], [4], np.asarray([0.03, 0.03, 10.0]))
        np.testing.assert_allclose(model["center"]["x"][4], [1.1, 2.2, 5.0])
        np.testing.assert_allclose(model["halfwidth"]["x"][4], [0.13, 0.23, 12.0])

    def test_directional_regret_detects_wrong_candidate(self) -> None:
        candidates = ["east", "west", "north", "south"]
        truth = {
            "east": {8: np.asarray([1.0, 0.0, 0.0])},
            "west": {8: np.asarray([-1.0, 0.0, 0.0])},
            "north": {8: np.asarray([0.0, 1.0, 0.0])},
            "south": {8: np.asarray([0.0, -1.0, 0.0])},
        }
        correct = {"center": {key: {8: value[8].copy()} for key, value in truth.items()},
                   "halfwidth": {key: {8: np.ones(3)} for key in candidates}}
        metrics = primary.evaluate_fold(correct, truth, candidates, [8], 64)
        self.assertAlmostEqual(metrics["maximum_directional_ranking_regret_mm"], 0.0)
        wrong = {"center": {key: {8: -value[8].copy()} for key, value in truth.items()},
                 "halfwidth": correct["halfwidth"]}
        self.assertGreater(primary.evaluate_fold(wrong, truth, candidates, [8], 64)[
            "maximum_directional_ranking_regret_mm"
        ], 1.0)

    def test_launcher_is_zero_tsc_model_only(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_value_v0.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_V0_SOURCE_REVISION", text)
        self.assertNotIn("gotsc", text)
        self.assertNotIn("step_current", text)


if __name__ == "__main__":
    unittest.main()
