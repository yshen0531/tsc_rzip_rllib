import copy
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

from scripts import rgeo_zgeo_1ms_id2u1_moving_nominal_development as stage


class ID2U1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec, cls.cfg, cls.streams = stage.load()

    def test_frozen_identity_and_budget(self):
        self.assertEqual(stage.sha256(stage.CONFIG), stage.CONFIG_SHA256)
        self.assertEqual(self.spec["maximum_rollouts"], 20)
        self.assertEqual(self.spec["maximum_reset_calls"], 20)
        self.assertEqual(self.spec["maximum_advance_attempts"], 800)
        self.assertEqual(self.spec["maximum_gotsc_calls"], 800)
        self.assertEqual(self.spec["maximum_verified_plant_advances"], 800)
        self.assertEqual(self.spec["maximum_retained_states"], 820)
        self.assertEqual(self.spec["retry_after_any_advance_attempt"], "forbidden")

    def test_only_development_families_are_executable(self):
        self.assertEqual(len(self.streams), 20)
        self.assertEqual({row["group_id"] for row in self.streams}, {"u00", "u02", "u04", "u06"})
        self.assertTrue(all(row["role"] == "development" for row in self.streams))
        self.assertTrue(all(row["arrival"] == "frontloaded" for row in self.streams))
        forbidden = set(self.spec["unopened_calibration_family_ids"] + self.spec["unopened_blind_holdout_family_ids"])
        self.assertFalse(any(row["group_id"] in forbidden for row in self.streams))

    def test_each_family_has_matched_five_arm_matrix(self):
        for group_id in self.spec["active_family_ids"]:
            rows = [row for row in self.streams if row["group_id"] == group_id]
            self.assertEqual(len(rows), 5)
            self.assertEqual(sum(row["cell_kind"] == "baseline" for row in rows), 1)
            self.assertEqual({(row["direction_id"], row["sign"]) for row in rows if row["cell_kind"] == "probe"},
                             {("p04", "plus"), ("p04", "minus"), ("p07", "plus"), ("p07", "minus")})

    def test_all_actions_are_exact_and_never_require_clipping(self):
        for row in self.streams:
            self.assertEqual(len(row["targets"]), 40)
            self.assertEqual(len(row["actions"]), 40)
            for target, action in zip(row["targets"], row["actions"]):
                self.assertEqual(list(target.card15_fields), action["expected_card15_fields"])
                self.assertEqual(list(target.current_a_tsc), action["target_current_a_tsc"])
                self.assertLessEqual(float(action["maximum_issued_delta_a"]), 0.3)

    def test_probe_return_resume_clock_is_frozen(self):
        for row in [item for item in self.streams if item["cell_kind"] == "probe"]:
            issue = int(row["probe_issue_step"])
            self.assertEqual(row["probe_duration_issues"], 2)
            self.assertEqual(row["non_nominal_issue_steps"], [issue])
            virtual = [action["probe_virtual_action"] for action in row["actions"]]
            self.assertEqual(virtual[issue][0], virtual[issue + 1][0])
            self.assertEqual(virtual[issue + 2][1:], [0.0, 0.0])
            self.assertGreaterEqual(virtual[issue + 3][0], virtual[issue + 2][0])

    def test_offline_is_zero_plant_and_zero_fit(self):
        result = stage.offline(stage.CONFIG, "test-revision")
        self.assertTrue(result["passed"])
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["verified_plant_advances"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)
        self.assertEqual(result["calibration_or_holdout_records_read"], 0)

    def test_mutated_role_or_budget_fails_closed(self):
        for key, value in (("active_role", "calibration"), ("maximum_rollouts", 21),
                           ("retry_after_any_advance_attempt", "allowed")):
            mutated = copy.deepcopy(self.spec)
            mutated[key] = value
            with self.assertRaises(stage.InputIntegrityError):
                stage._require(mutated)

    def test_launcher_has_explicit_revision_output_and_independent_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2u1_moving_nominal_development.sh").read_text(encoding="utf-8")
        self.assertIn("ID2U1_SOURCE_REVISION", text)
        self.assertIn("ID2U1_OUTPUT", text)
        self.assertIn("matched_nominal_development_independent.py".replace("matched_nominal", "moving_nominal"), text)
        self.assertIn("test ! -e", text)


if __name__ == "__main__":
    unittest.main()
