import unittest
from pathlib import Path

import numpy as np

from scripts import rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout as stage


ROOT = Path(__file__).resolve().parents[1]


class ID2N1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.cfg, cls.targets, cls.source, cls.data, cls.model = stage.load()
        cls.streams = stage.campaign_streams(cls.config, cls.cfg, cls.targets, cls.source)

    def test_identity_and_budget(self):
        self.assertEqual(stage.sha256(stage.CONFIG), stage.CONFIG_SHA256)
        self.assertEqual(len(self.streams), 28)
        self.assertEqual(len({row["cell_id"] for row in self.streams}), 24)
        self.assertEqual(sum(len(row["actions"]) for row in self.streams), 952)

    def test_split_is_whole_family_and_ordered(self):
        roles = [row["role"] for row in self.streams]
        self.assertEqual(roles[:14], ["calibration"] * 14)
        self.assertEqual(roles[14:], ["holdout"] * 14)
        for group in {row["group_id"] for row in self.streams}:
            self.assertEqual(len({row["role"] for row in self.streams if row["group_id"] == group}), 1)

    def test_each_family_has_baseline_two_probes(self):
        for family in self.config["families"]:
            primary = [row for row in self.streams if row["group_id"] == family["group_id"]
                       and row["replay_index"] == 0]
            self.assertEqual(len(primary), 3)
            self.assertEqual(sum(row["cell_kind"] == "baseline" for row in primary), 1)
            self.assertEqual({row["direction_id"] for row in primary if row["cell_kind"] == "probe"}, {"p04", "p07"})

    def test_four_replays_are_exactly_declared(self):
        replayed = {row["cell_id"] for row in self.streams if row["replay_index"] == 1}
        self.assertEqual(replayed, set(self.config["critical_replay_cells"]))

    def test_all_actions_respect_slew_and_horizon(self):
        for row in self.streams:
            self.assertEqual(len(row["actions"]), 34)
            self.assertLessEqual(max(float(action["maximum_issued_delta_a"]) for action in row["actions"]), 0.3)

    def test_offline_has_zero_plant_and_no_model_update(self):
        value = stage.offline(stage.CONFIG, "test-revision")
        self.assertTrue(value["passed"])
        self.assertEqual((value["reset_calls"], value["plant_advance_gotsc_calls"], value["models_fit_or_updated"]), (0, 0, 0))

    def test_selected_model_is_frozen_event_memory(self):
        self.assertEqual(self.model.kind, "separated_event_memory")
        self.assertEqual(self.model.coefficients.shape, (78, 3))
        self.assertTrue(np.all(np.isfinite(self.model.coefficients)))

    def test_tube_formula_and_caps_are_frozen(self):
        cal = self.config["calibration"]
        peak = np.asarray([0.0001, 0.00001, 2.0])
        tube = np.maximum(np.asarray(cal["tube_floor"]), cal["tube_multiplier"] * peak)
        self.assertTrue(np.allclose(tube, [0.000125, 0.00005, 5.0]))
        self.assertEqual(cal["prediction_horizons_ms"], list(range(1, 9)))

    def test_holdout_cannot_update_model_or_tube(self):
        self.assertTrue(self.config["holdout_execution_requires_written_calibration_pass"])
        self.assertTrue(self.config["model_update_forbidden"])
        self.assertTrue(self.config["development_refit_forbidden"])
        self.assertTrue(self.config["holdout"]["all_endpoint_rows_must_be_contained"])

    def test_launcher_has_explicit_offline_run_and_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2n1_fresh_calibration_blind_holdout.sh").read_text(encoding="utf-8")
        for token in ("offline)", "run)", "independent)"):
            self.assertIn(token, text)
        self.assertNotIn("cleanup", text.lower())


if __name__ == "__main__":
    unittest.main()
