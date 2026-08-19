from __future__ import annotations

import copy
import json
import unittest

from scripts import rgeo_zgeo_1ms_id2z17_full_f_transient_remaining_basis_beam as m
from scripts import rgeo_zgeo_1ms_id2z17_full_f_transient_remaining_basis_beam_independent as mi


class ID2Z17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.reference = m.load()
        cls.specs = list(cls.stage["round0_candidate_specs"])
        cls.roots = m.build_round(cls.stage, cls.cfg, cls.targets, cls.parent,
                                  48, 0, "round0", cls.specs)

    def test_identity_budget_and_role(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_static_sequences"], 121)
        self.assertEqual(self.stage["maximum_rollouts"], 18)
        self.assertEqual(self.stage["maximum_advance_attempts"], 1170)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 5940)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(self.stage["fit_calibration_holdout_controller_expert_bc_dagger_rl_fixture_use"],
                         "forbidden")

    def test_state48_prefix_is_exact_and_bound(self) -> None:
        self.assertEqual(len(self.reference["states"]), 66)
        self.assertEqual(len(self.parent["actions"]), 65)
        self.assertEqual(
            [row["expected_card15_fields"] for row in self.parent["actions"]],
            [row["expected_card15_fields"] for row in self.reference["actions"]])
        for row in self.roots:
            self.assertEqual(
                [a["expected_card15_fields"] for a in row["actions"][:48]],
                [a["expected_card15_fields"] for a in self.parent["actions"][:48]])

    def test_direction_identity_and_translated_targets(self) -> None:
        self.assertEqual(tuple(row["arm_id"] for row in self.roots), m.ROUND0_ARM_IDS)
        frozen = self.stage["zero_tsc_action_audit"]["translated_first_target_card15_fields"]
        for row in self.roots:
            if row["arm_id"] == "h4":
                continue
            self.assertEqual(row["actions"][48]["expected_card15_fields"],
                             frozen[row["arm_id"]])
            self.assertLessEqual(row["actions"][48]["maximum_issued_delta_a"], .3000000001)

    def test_static_tree_has_121_admissible_schedules(self) -> None:
        count = 0
        for root in self.roots:
            self.assertTrue(m.validate_stream(root, self.stage, self.cfg)["passed"])
            count += 1
            if root["arm_id"] == "h4":
                continue
            for child in m.build_round(self.stage, self.cfg, self.targets, root,
                                       52, 1, f"static__{root['arm_id']}", self.specs):
                self.assertTrue(m.validate_stream(child, self.stage, self.cfg)["passed"])
                count += 1
        self.assertEqual(count, 121)

    def test_clocks_hold_and_slew(self) -> None:
        for row in self.roots:
            self.assertEqual(len(row["actions"]), 65)
            self.assertLessEqual(max(float(a["maximum_issued_delta_a"])
                                     for a in row["actions"]), .3000000001)
            for issue in range(52, 65):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 row["actions"][51]["expected_card15_fields"])

    def test_offline_is_121_of_121_zero_tsc(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_sequence_count"], 121)
        self.assertEqual(value["static_sequences_passed"], 121)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _states(distance: float, speed: float = 0.0) -> list[dict]:
        states = []
        for index in range(66):
            position = distance + ((index - 60) * speed * .001 if index >= 60 else 0.0)
            states.append({"r_geo_m": 0.0 if index == 0 else position,
                           "z_geo_m": 0.0, "ip_a": 1000.0})
        return states

    def _row(self, stream: dict, distance: float, speed: float = 0.0) -> dict:
        return {"rollout_id": stream["rollout_id"], "path_id": stream["path_id"],
                "arm_id": stream["arm_id"], "base_direction_id": stream["base_direction_id"],
                "passed": True, "states": self._states(distance, speed)}

    def test_distinct_parent_selection(self) -> None:
        rows = [self._row(row, .04 + index * .001) for index, row in enumerate(self.roots)]
        # Same-direction p00 signs rank first; selection must take only one of them.
        rows[1] = self._row(self.roots[1], .030)
        rows[2] = self._row(self.roots[2], .031)
        rows[3] = self._row(self.roots[3], .032)
        metrics = m._metrics(rows, self.stage)
        selected = m._distinct_parents(metrics, self.roots)
        self.assertEqual(selected, [self.roots[1]["path_id"], self.roots[3]["path_id"]])

    def test_route_precedence_early_and_two_layer(self) -> None:
        complete = {"complete": True, "selected_capture_passed": False}
        captured = {"complete": True, "selected_capture_passed": True}
        self.assertEqual(m.route_for(self.stage, False, False, False, complete,
                                     complete, False, 2, False),
                         self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, True, captured,
                                     {"complete": False}, True, 0, True),
                         self.stage["routes"]["capture_pass"])
        self.assertEqual(m.route_for(self.stage, True, True, True, complete,
                                     complete, False, 2, True),
                         self.stage["routes"]["no_capture"])
        self.assertEqual(m.route_for(self.stage, True, True, True, complete,
                                     complete, False, 1, True),
                         self.stage["routes"]["beam_incomplete"])

    def test_independent_reconstructs_18_streams(self) -> None:
        parents = [self.roots[1]["path_id"], self.roots[3]["path_id"]]
        selected_specs = [self.specs[0], self.specs[1], self.specs[3]]
        child = m.build_round(self.stage, self.cfg, self.targets, self.roots[1],
                              52, 1, "round1__p00_plus4", selected_specs)[0]
        result = {"scientific_metrics": {
            "round0_early_capture": False,
            "round0_selected_parent_path_ids": parents,
            "selected_path_id": child["path_id"]}}
        streams = mi.expected_streams(
            self.stage, self.cfg, self.targets, self.parent, result)
        self.assertEqual(len(streams), 18)
        self.assertEqual(streams[-1]["rollout_id"], "critical_replay")

    def test_independent_early_capture_reconstructs_12_streams(self) -> None:
        selected = self.roots[1]
        result = {"scientific_metrics": {
            "round0_early_capture": True,
            "round0_selected_parent_path_ids": [],
            "selected_path_id": selected["path_id"]}}
        streams = mi.expected_streams(
            self.stage, self.cfg, self.targets, self.parent, result)
        self.assertEqual(len(streams), 12)
        self.assertEqual(streams[-1]["rollout_id"], "critical_replay")

    def test_independent_excludes_replay_from_round1_search(self) -> None:
        self.assertTrue(mi.is_round1_search_row(
            {"round_index": 1, "rollout_id": "round1__p00_plus4__h4"}))
        self.assertFalse(mi.is_round1_search_row(
            {"round_index": 1, "rollout_id": "critical_replay"}))

    def test_config_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        for mutate in (
                lambda value: value.update(beam_width=3),
                lambda value: value["round0_candidate_specs"].append(
                    {"arm_id": "extra", "base_direction_id": "p01", "sign": "plus"}),
                lambda value: value.update(maximum_rollouts=19),
                lambda value: value.update(models_fit_or_updated=1)):
            value = copy.deepcopy(original); mutate(value)
            with self.assertRaises(Exception):
                m._require(value)

    def test_launcher_preserves_fail_for_audit(self) -> None:
        text = (m.ROOT / "run_rgeo_zgeo_1ms_id2z17_full_f_transient_remaining_basis_beam.sh").read_text(
            encoding="utf-8")
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn("primary_rc=$?", text)
        self.assertNotIn("--resume", text)
        self.assertNotIn("retry", text.lower())


if __name__ == "__main__":
    unittest.main()
