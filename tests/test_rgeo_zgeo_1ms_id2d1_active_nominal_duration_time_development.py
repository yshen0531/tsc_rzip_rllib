import copy
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2d1r1_active_nominal_duration_time_development.json"


class Id2D1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import rgeo_zgeo_1ms_id2d1_active_nominal_duration_time_development as primary
        cls.primary = primary
        cls.stage, cls.cfg, cls.targets, cls.id2c1_stage = primary.load(CONFIG)
        cls.streams = primary.campaign_streams(cls.stage, cls.cfg, cls.targets, cls.id2c1_stage)

    def test_frozen_identity_and_budget(self):
        self.assertEqual(self.primary.sha256(CONFIG), self.primary.CONFIG_SHA256)
        self.assertEqual(len(self.streams), 24)
        self.assertEqual(sum(len(row["actions"]) for row in self.streams), 768)
        self.assertEqual(sum(len(row["actions"]) + 1 for row in self.streams), 792)
        self.assertEqual(len([row for row in self.streams if row["cell_kind"] == "baseline"]), 2)

    def test_exact_id2c2_evaluator_cells_are_excluded(self):
        for row in self.streams:
            key = (row["probe_issue_step"], row["probe_duration_issues"], row["direction_id"])
            self.assertNotIn(key, {(16, 1, "p04"), (16, 1, "p07"), (16, 1, "p09_half_exact_center")})

    def test_schedule_matrix_and_return(self):
        smooth = [row for row in self.streams if row["cell_kind"] == "smooth_residual"]
        event = [row for row in self.streams if row["cell_kind"] == "event_residual"]
        self.assertEqual(len(smooth), 20)
        self.assertEqual(len(event), 2)
        self.assertEqual({(row["probe_issue_step"], row["probe_duration_issues"]) for row in smooth}, {(16, 2), (16, 4), (22, 1), (22, 2), (22, 4)})
        for row in smooth + event:
            active = [index for index, action in enumerate(row["actions"]) if any(action["probe_virtual_action"])]
            self.assertEqual(active, list(range(row["probe_issue_step"], row["probe_issue_step"] + row["probe_duration_issues"])))
            if row["exact_return_issue_step"] < 32:
                self.assertFalse(any(row["actions"][row["exact_return_issue_step"]]["probe_virtual_action"]))

    def test_exact_action_and_effect_semantics(self):
        for row in self.streams:
            self.assertEqual([action["issue_step"] for action in row["actions"]], list(range(32)))
            self.assertEqual([action["effect_state_index"] for action in row["actions"]], list(range(1, 33)))
            self.assertLessEqual(max(action["maximum_issued_delta_a"] for action in row["actions"]), 0.3)
            self.assertTrue(all(len(action["expected_card15_fields"]) == 14 for action in row["actions"]))

    def test_model_aligned_lag_support_is_full(self):
        smooth = self.primary.lag_support(self.streams, [0, 1], 16)
        event = self.primary.lag_support(self.streams, [2], 10)
        self.assertEqual((smooth["rows"], smooth["columns"], smooth["rank"]), (768, 32, 32))
        self.assertEqual((event["rows"], event["columns"], event["rank"]), (768, 10, 10))
        self.assertGreater(smooth["minimum_singular_value"], 0.0)
        self.assertGreater(event["minimum_singular_value"], 0.0)

    def test_frozen_config_mutation_fails_closed(self):
        for path, value in (
            (("maximum_rollouts",), 25),
            (("fit_eligibility_gates", "smooth_lag_steps"), 15),
            (("empirical_exploration", "post_successor_step_caps", "r_geo_m"), 0.003),
            (("later_model_contract", "id2c2_role"), "fit"),
        ):
            mutated = copy.deepcopy(self.stage)
            cursor = mutated
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(Exception):
                self.primary._exact_stage(mutated)

    def test_data_roles_are_separated(self):
        self.assertEqual(self.stage["model_fit_use_after_all_gates_pass"], "id2d1r1_development_only")
        self.assertEqual(self.stage["later_model_contract"]["id2c2_role"], "immutable_evaluator_only")
        self.assertEqual(self.stage["calibration_use"], "forbidden")
        self.assertEqual(self.stage["blind_holdout_use"], "forbidden")
        self.assertEqual(self.stage["holdout_records_read"], 0)


if __name__ == "__main__":
    unittest.main()
