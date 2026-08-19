from __future__ import annotations

import copy
import json
import unittest

from scripts import rgeo_zgeo_1ms_id2z16_full_f_prefix_beam_reachability as m
from scripts import rgeo_zgeo_1ms_id2z16_full_f_prefix_beam_reachability_independent as mi


class ID2Z16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.reference = m.load()
        cls.roots = m.build_round(cls.stage, cls.cfg, cls.targets, cls.parent,
                                  32, 0, "round0")

    def test_identity_budget_and_role(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_static_sequences"], 30)
        self.assertEqual(self.stage["maximum_rollouts"], 16)
        self.assertEqual(self.stage["maximum_advance_attempts"], 1040)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 5280)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)

    def test_full_f_prefix_is_exact_and_bound(self) -> None:
        self.assertEqual(len(self.reference["states"]), 49)
        self.assertEqual(len(self.parent["actions"]), 48)
        self.assertEqual(
            [row["expected_card15_fields"] for row in self.parent["actions"][:32]],
            [row["expected_card15_fields"] for row in self.reference["actions"][:32]])
        for row in self.roots:
            self.assertEqual(
                [a["expected_card15_fields"] for a in row["actions"][:32]],
                [a["expected_card15_fields"] for a in self.parent["actions"][:32]])

    def test_static_tree_has_thirty_admissible_schedules(self) -> None:
        count = 0
        for root in self.roots:
            self.assertTrue(m.validate_stream(root, self.stage, self.cfg)["passed"])
            count += 1
            for child in m.build_round(self.stage, self.cfg, self.targets, root,
                                       40, 1, f"static__{root['arm_id']}"):
                self.assertTrue(m.validate_stream(child, self.stage, self.cfg)["passed"])
                count += 1
        self.assertEqual(count, 30)

    def test_clocks_hold_and_slew(self) -> None:
        for row in self.roots:
            self.assertEqual(len(row["actions"]), 65)
            self.assertLessEqual(max(float(a["maximum_issued_delta_a"])
                                     for a in row["actions"]), .3000000001)
            for issue in range(40, 65):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 row["actions"][39]["expected_card15_fields"])

    def test_offline_is_thirty_of_thirty_zero_tsc(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_sequence_count"], 30)
        self.assertEqual(value["static_sequences_passed"], 30)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _states(distance: float, speed: float = 0.0) -> list[dict]:
        states = []
        for index in range(66):
            position = distance + ((index - 60) * speed * .001 if index >= 60 else 0.0)
            states.append({"r_geo_m": 0.0 if index == 0 else position,
                           "z_geo_m": 0.0, "ip_a": 1000.0})
        return states

    def _row(self, path: str, distance: float, speed: float = 0.0) -> dict:
        return {"rollout_id": path, "path_id": path,
                "arm_id": path.rsplit("__", 1)[-1], "passed": True,
                "states": self._states(distance, speed)}

    def test_metrics_capture_first_then_score(self) -> None:
        rows = [self._row(f"full_f__{arm}", .03 + index * .001)
                for index, arm in enumerate(m.ARM_IDS)]
        rows[3] = self._row("full_f__b4f4", .02)
        value = m._metrics(rows, self.stage)
        self.assertTrue(value["complete"])
        self.assertEqual(value["selected_path_id"], "full_f__b4f4")
        self.assertTrue(value["selected_capture_passed"])

    def test_beam_is_exactly_top_two(self) -> None:
        rows = [self._row(f"full_f__{arm}", .03 + index * .001)
                for index, arm in enumerate(m.ARM_IDS)]
        value = m._metrics(rows, self.stage)
        self.assertEqual(value["ranked_path_ids"][:2], ["full_f__h8", "full_f__b8"])

    def test_route_precedence_and_fail(self) -> None:
        complete = {"complete": True, "selected_capture_passed": False}
        self.assertEqual(m.route_for(self.stage, False, False, False,
                                     complete, complete, False),
                         self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(m.route_for(self.stage, True, False, True,
                                     complete, complete, True),
                         self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, False,
                                     complete, complete, True),
                         self.stage["routes"]["prefix_mismatch"])
        self.assertEqual(m.route_for(self.stage, True, True, True,
                                     {"complete": False}, complete, False),
                         self.stage["routes"]["beam_incomplete"])
        self.assertEqual(m.route_for(self.stage, True, True, True,
                                     complete, complete, False),
                         self.stage["routes"]["replay_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, True,
                                     complete, complete, True),
                         self.stage["routes"]["no_capture"])

    def test_independent_reconstructs_sixteen_streams(self) -> None:
        beam = [self.roots[0]["path_id"], self.roots[1]["path_id"]]
        child = m.build_round(self.stage, self.cfg, self.targets,
                              self.roots[0], 40, 1, "round1__h8")[0]
        result = {"scientific_metrics": {
            "round0_selected_parent_path_ids": beam,
            "selected_path_id": child["path_id"]}}
        streams = mi.expected_streams(
            self.stage, self.cfg, self.targets, self.parent, result)
        self.assertEqual(len(streams), 16)
        self.assertEqual(streams[-1]["rollout_id"], "critical_replay")

    def test_independent_excludes_replay_from_round1_search(self) -> None:
        self.assertTrue(mi.is_round1_search_row(
            {"round_index": 1, "rollout_id": "round1__f8__f8"}))
        self.assertFalse(mi.is_round1_search_row(
            {"round_index": 1, "rollout_id": "critical_replay"}))
        self.assertFalse(mi.is_round1_search_row(
            {"round_index": 0, "rollout_id": "round0__f8"}))

    def test_config_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        for mutate in (
                lambda value: value.update(beam_width=3),
                lambda value: value["candidate_specs"].append(
                    {"arm_id": "extra", "tokens": "BFBFBFBF"}),
                lambda value: value["measurement_gates"].update(
                    maximum_capture_source_rz_distance_m=.026)):
            value = copy.deepcopy(original); mutate(value)
            with self.assertRaises(Exception):
                m._require(value)

    def test_launcher_preserves_fail_for_audit(self) -> None:
        text = (m.ROOT / "run_rgeo_zgeo_1ms_id2z16_full_f_prefix_beam_reachability.sh").read_text(
            encoding="utf-8")
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn("primary_rc=$?", text)
        self.assertNotIn("--resume", text)
        self.assertNotIn("retry", text.lower())


if __name__ == "__main__":
    unittest.main()
