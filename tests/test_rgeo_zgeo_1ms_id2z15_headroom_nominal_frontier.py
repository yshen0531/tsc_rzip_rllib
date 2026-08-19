from __future__ import annotations

import copy
import json
import unittest

from scripts import rgeo_zgeo_1ms_id2z15_headroom_nominal_frontier as m
from scripts import rgeo_zgeo_1ms_id2z15_headroom_nominal_frontier_independent as mi


class ID2Z15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.reference = m.load()
        cls.rows = m.build_matrix(cls.stage, cls.cfg, cls.targets)

    def test_identity_budget_and_data_role(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_rollouts"], 7)
        self.assertEqual(self.stage["maximum_advance_attempts"], 336)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 1715)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(
            self.stage["fit_calibration_holdout_controller_expert_bc_dagger_rl_fixture_use"],
            "forbidden")

    def test_fraction_and_duty_matrix(self) -> None:
        self.assertEqual([row["arm_id"] for row in self.rows], list(m.ARM_IDS))
        by_id = {row["arm_id"]: row for row in self.rows}
        self.assertEqual(by_id["f25"]["attained_f_level"], "7.75")
        self.assertEqual(by_id["f50"]["attained_f_level"], "15.5")
        self.assertEqual(by_id["f75"]["attained_f_level"], "23.25")
        self.assertEqual(by_id["f100"]["attained_f_level"], "31.0")
        self.assertEqual(by_id["duty50"]["attained_f_level"], "16")
        for row in self.rows:
            self.assertEqual(len(row["actions"]), 48)
            self.assertTrue(m.validate_stream(row, self.stage, self.cfg)["passed"])
        duty = by_id["duty50"]["actions"]
        self.assertTrue(all(float(duty[i]["maximum_issued_delta_a"]) > 0
                            for i in range(1, 32, 2)))
        self.assertTrue(all(float(duty[i]["maximum_issued_delta_a"]) == 0
                            for i in range(2, 32, 2)))

    def test_tail_hold_and_full_rate_slew(self) -> None:
        for row in self.rows:
            for issue in range(32, 48):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 row["actions"][31]["expected_card15_fields"])
                self.assertEqual(float(row["actions"][issue]["maximum_issued_delta_a"]), 0.0)
        f100 = next(row for row in self.rows if row["arm_id"] == "f100")
        self.assertAlmostEqual(max(float(a["maximum_issued_delta_a"])
                                   for a in f100["actions"]), .3, places=12)

    def test_offline_is_six_of_six_and_zero_tsc(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_sequence_count"], 6)
        self.assertEqual(value["static_sequences_passed"], 6)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _states(distance: float, speed: float = 0.0) -> list[dict]:
        states = []
        for index in range(49):
            position = distance + ((index - 43) * speed * .001 if index >= 43 else 0.0)
            states.append({"r_geo_m": 0.0 if index == 0 else position,
                           "z_geo_m": 0.0, "ip_a": 1000.0})
        return states

    def _row(self, arm: str, distance: float, speed: float = 0.0) -> dict:
        return {"rollout_id": f"branch__{arm}", "arm_id": arm, "passed": True,
                "states": self._states(distance, speed), "actions": []}

    def test_capture_has_priority(self) -> None:
        rows = [self._row(arm, .03) for arm in m.ARM_IDS]
        rows[4] = self._row("f100", .02)
        value = m._metrics(rows, self.stage)
        self.assertEqual(value["selected_arm_id"], "f100")
        self.assertTrue(value["selected_capture_passed"])
        self.assertEqual(m.route_for(self.stage, True, True, True, value, True),
                         self.stage["routes"]["capture_pass"])

    def test_headroom_requires_both_endpoint_improvements(self) -> None:
        rows = [self._row("q0", .035), self._row("f25", .03),
                self._row("f50", .028), self._row("f75", .032),
                self._row("f100", .034), self._row("duty50", .031)]
        value = m._metrics(rows, self.stage)
        self.assertEqual(value["selected_arm_id"], "f50")
        self.assertFalse(value["selected_capture_passed"])
        self.assertTrue(value["selected_headroom_development_passed"])
        self.assertEqual(m.route_for(self.stage, True, True, True, value, True),
                         self.stage["routes"]["headroom_pass"])

    def test_no_relative_route_for_full_f_or_small_improvement(self) -> None:
        rows = [self._row("q0", .035), self._row("f25", .0345),
                self._row("f50", .0344), self._row("f75", .0343),
                self._row("f100", .034), self._row("duty50", .0342)]
        value = m._metrics(rows, self.stage)
        self.assertEqual(value["selected_arm_id"], "f100")
        self.assertFalse(value["selected_headroom_development_passed"])
        self.assertEqual(m.route_for(self.stage, True, True, True, value, True),
                         self.stage["routes"]["no_useful_nominal"])

    def test_route_precedence_and_incomplete(self) -> None:
        good = {"frontier_complete": True, "selected_capture_passed": False,
                "selected_headroom_development_passed": False}
        self.assertEqual(m.route_for(self.stage, False, False, False, good, False),
                         self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(m.route_for(self.stage, True, False, True, good, True),
                         self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, False, good, True),
                         self.stage["routes"]["prefix_mismatch"])
        self.assertEqual(m.route_for(self.stage, True, True, True,
                                     {"frontier_complete": False}, False),
                         self.stage["routes"]["frontier_incomplete"])
        self.assertEqual(m.route_for(self.stage, True, True, True, good, False),
                         self.stage["routes"]["replay_fail"])

    def test_independent_reconstructs_seven_streams(self) -> None:
        result = {"scientific_metrics": {"selected_arm_id": "f50"}}
        streams = mi.expected_streams(self.stage, self.cfg, self.targets, result)
        self.assertEqual(len(streams), 7)
        self.assertEqual(streams[-1]["rollout_id"], "critical_replay")

    def test_config_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        for mutate in (
                lambda value: value.update(maximum_rollouts=8),
                lambda value: value["candidate_specs"].append(
                    {"arm_id": "extra", "mode": "constant_fraction", "alpha_f": .6}),
                lambda value: value["measurement_gates"].update(
                    maximum_capture_source_rz_distance_m=.026)):
            value = copy.deepcopy(original)
            mutate(value)
            with self.assertRaises(Exception):
                m._require(value)

    def test_launcher_audits_scientific_fail_without_retry(self) -> None:
        launcher = (m.ROOT / "run_rgeo_zgeo_1ms_id2z15_headroom_nominal_frontier.sh").read_text(
            encoding="utf-8")
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertNotIn("--resume", launcher)
        self.assertNotIn("retry", launcher.lower())


if __name__ == "__main__":
    unittest.main()
