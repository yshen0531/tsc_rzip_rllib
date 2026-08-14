from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "c2aa4_support", ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c2aa4_support.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C2AA4 = load_module()


class C2AA4SupportTests(unittest.TestCase):
    def setUp(self):
        self.config_path = ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa4_late_state_support_audit.json"
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))

    def test_frozen_rule_does_not_promote_margin_or_threshold_to_support(self):
        rule = self.config["support_rule"]
        self.assertFalse(rule["empirical_stop_threshold_is_qualified_tube"])
        self.assertFalse(rule["current_state_margin_alone_is_causal_successor_support"])
        self.assertFalse(rule["wrong_action_or_history_substitution_allowed"])

    def test_exact_current_observation_is_not_future_successor_knowledge(self):
        observation = self.config["decision_observation_contract"]
        self.assertTrue(observation["available_before_issue"])
        self.assertTrue(observation["r_geo_z_geo_ip_are_exact_noiseless_observables"])
        self.assertTrue(
            observation["complete_causal_observation_and_own_action_history_through_current_step_is_available"]
        )
        self.assertFalse(observation["future_successor_is_observed_before_issue"])

    def test_real_audit_stops_at_first_unseen_level2_age(self):
        result = C2AA4.audit(self.config_path, "unit-test")
        self.assertTrue(result["audit_completed"])
        self.assertFalse(result["support_passed"])
        self.assertEqual(
            result["route"], "ONE_MS_NR2R2C2AA4_LATE_STATE_CAUSAL_SUPPORT_FAIL_NO_TSC"
        )
        self.assertEqual(result["supported_transitions"], 16)
        self.assertEqual(result["required_transitions"], 32)
        self.assertEqual(result["directly_supported_issue_steps"], list(range(16)))
        self.assertEqual(result["unsupported_issue_steps"], list(range(16, 32)))
        first = result["first_unsupported"]
        self.assertEqual(first["issue_step"], 16)
        self.assertEqual(first["effect_state_index"], 17)
        self.assertEqual(first["level2_dwell_effect_age"], 15)
        self.assertTrue(first["same_prefix_preissue_state"])
        self.assertFalse(first["same_prefix_successor"])
        self.assertFalse(result["support_table"][17]["same_prefix_preissue_state"])
        self.assertEqual(result["support_table"][2]["level2_dwell_effect_age"], 1)
        self.assertEqual(result["support_table"][15]["level2_dwell_effect_age"], 14)
        self.assertEqual(result["support_table"][31]["level2_dwell_effect_age"], 30)

    def test_support_requires_complete_matching_prefix_not_only_same_target(self):
        a4 = C2AA4.load_hashed_json(self.config["a4_config"])
        rows = {row["role"]: C2AA4.load_hashed_json(row) for row in self.config["compact_trajectories"]}
        q0_fields = rows["q0_h32"]["actions"][0]["expected_card15_fields"]
        expected = C2AA4.expected_a4_fields(a4, q0_fields)
        levels = C2AA4.expected_a4_levels(a4)
        replay0 = copy.deepcopy(rows["a3_level2_replay_0"])
        replay1 = copy.deepcopy(rows["a3_level2_replay_1"])
        replay0["actions"][15]["expected_card15_fields"] = list(expected[0])
        replay1["actions"][15]["expected_card15_fields"] = list(expected[0])
        replay0["actions"][16]["expected_card15_fields"] = list(expected[16])
        replay1["actions"][16]["expected_card15_fields"] = list(expected[16])
        table = C2AA4.build_support_table(
            expected,
            levels,
            replay0,
            replay1,
            effect_state_offset=1,
        )
        self.assertTrue(table[16]["same_card15_target"])
        self.assertFalse(table[16]["complete_same_issue_prefix"])
        self.assertFalse(table[16]["supported_before_advance"])

    def test_no_boolean_tube_bypass_exists(self):
        parameters = C2AA4.build_support_table.__annotations__
        self.assertNotIn("qualified_tube_available", parameters)
        source = (ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c2aa4_support.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("qualified_tube_available=True", source)

    def test_audit_is_zero_server_zero_tsc_zero_holdout(self):
        result = C2AA4.audit(self.config_path, "unit-test")
        self.assertEqual(result["counters"], {
            "server_accesses": 0,
            "server_raw_reads": 0,
            "holdout_records_read": 0,
            "new_tsc_or_plant_advances": 0,
            "model_fits_or_training_runs": 0,
            "controller_or_optimizer_executions": 0,
            "compact_trajectory_records_read": 6,
            "raw_records_read": 0,
        })


if __name__ == "__main__":
    unittest.main()
