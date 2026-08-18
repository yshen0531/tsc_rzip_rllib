from __future__ import annotations

import unittest

from scripts import rgeo_zgeo_1ms_id2s0_sequence_utility_selector as s0


class ID2S0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.cfg, cls.targets, cls.source, cls.rows = s0.load()
        cls.streams = s0.candidate_streams(cls.stage, cls.cfg, cls.targets, cls.source)

    def test_zero_plant_and_zero_model_identity(self):
        self.assertEqual((self.stage["new_tsc_calls"], self.stage["reset_calls"],
                          self.stage["plant_advances"], self.stage["models_fit_or_updated"]),
                         (0, 0, 0, 0))
        self.assertEqual(self.stage["data_use"], "no_fit_candidate_nomination_only")

    def test_exact_sixteen_ordered_action_streams(self):
        self.assertEqual(len(self.streams), 16)
        self.assertEqual(len({row["sequence_id"] for row in self.streams}), 16)
        for row in self.streams:
            self.assertEqual(len(row["actions"]), 34)
            self.assertLessEqual(max(float(action["maximum_issued_delta_a"])
                                     for action in row["actions"]), 0.3)
            self.assertEqual(row["actions"][26]["probe_virtual_action"], [0.0, 0.0])
            self.assertEqual(row["actions"][29]["probe_virtual_action"], [0.0, 0.0])

    def test_fixed_shift_three_prediction(self):
        responses = s0.measured_arm_responses(self.rows)
        predicted = s0.predicted_sequences(self.streams, responses)
        first = predicted[0]
        self.assertEqual(first["predicted_rz_response_m"][:3], responses[first["first_arm"]][:3].tolist())

    def test_selector_is_deterministic_and_four_way(self):
        responses = s0.measured_arm_responses(self.rows)
        predicted = s0.predicted_sequences(self.streams, responses)
        left = s0.select(self.stage, predicted)
        right = s0.select(self.stage, predicted)
        self.assertEqual(left, right)
        self.assertEqual(len(left["sequence_ids"]), 4)
        self.assertEqual(left["subsets_evaluated"], 1820)

    def test_full_execute_passes_without_tsc(self):
        result = s0.execute(s0.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result)
        self.assertEqual((result["new_tsc_calls"], result["reset_calls"], result["plant_advances"]),
                         (0, 0, 0))
        self.assertEqual(len(result["selection"]["sequence_ids"]), 4)

    def test_launcher_has_only_zero_plant_modes(self):
        text = (s0.ROOT / "run_rgeo_zgeo_1ms_id2s0_sequence_utility_selector.sh").read_text(encoding="utf-8")
        self.assertIn("{run|independent}", text)
        self.assertNotIn("gotsc", text.lower())
        self.assertNotIn("reset", text.lower())


if __name__ == "__main__":
    unittest.main()

