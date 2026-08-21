import unittest

from scripts import rgeo_zgeo_1ms_id2z33_corrected_moving_center_d0 as stage
from scripts import rgeo_zgeo_1ms_id2z33_corrected_moving_center_d0_independent as independent


class ID2Z33CorrectedMovingCenterTest(unittest.TestCase):
    def test_offline_action_separation(self):
        value = stage.offline(stage.CONFIG, "f" * 40)
        self.assertTrue(value["passed"], value["failures"])
        self.assertTrue(value["action_stream_separation"]["passed"])
        self.assertEqual(len(value["action_stream_separation"]["rows"]), 8)
        issue56 = [row for row in value["action_stream_separation"]["rows"]
                   if row["family_id"].startswith("issue56")]
        self.assertEqual(len(issue56), 4)
        self.assertTrue(all(row["differing_issue_indices"] for row in issue56))
        self.assertTrue(all(row["first_branch_issue_nonzero"] for row in issue56))
        self.assertTrue(all(row["terminal_target_equals_center"] for row in issue56))

    def test_frozen_budget_and_no_model(self):
        config = stage.z32._read(stage.CONFIG)
        self.assertEqual(config["maximum_rollouts"], 10)
        self.assertEqual(config["maximum_gotsc_calls"], 730)
        self.assertEqual(config["models_fit_or_updated"], 0)
        self.assertEqual(config["data_contract"]["id2z32_rows_fit_weight"], 0)

    def test_independent_uses_patched_original_primary(self):
        stage.install()
        self.assertIs(independent.old.primary, stage.z32)
        self.assertIs(independent.old.primary.load, stage.load)
        self.assertIs(independent.old.primary.build_streams, stage.build_streams)


if __name__ == "__main__":
    unittest.main()
