from __future__ import annotations

import copy
import importlib.util
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


primary = _module(
    "id2z1", "scripts/rgeo_zgeo_1ms_id2z1_late_action_macro_utility.py")
independent = _module(
    "id2z1_independent",
    "scripts/rgeo_zgeo_1ms_id2z1_late_action_macro_utility_independent.py")


class ID2Z1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(primary.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_budget_and_routes(self) -> None:
        primary._require(self.stage)
        self.assertEqual(primary.CONFIG_SHA256, primary.y1r1.y1.x1.sha256(primary.CONFIG))
        self.assertEqual(self.stage["maximum_rollouts"], 7)
        self.assertEqual(self.stage["maximum_advance_attempts"], 7 * 73)
        self.assertEqual(self.stage["maximum_retained_states"], 7 * 74)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 7 * 74 * 5)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(self.stage["routes"]["pass"],
                         "ONE_MS_ID2Z1_LATE_MACRO_UTILITY_PASS_ROLLING_SEQUENCE_DESIGN_ONLY")

    def test_contract_mutation_fails_closed(self) -> None:
        for path, value in (
            (("maximum_gotsc_calls",), 512),
            (("action_semantics", "maximum_per_coil_issue_delta_a"), 0.31),
            (("measurement_gates", "minimum_terminal_source_distance_improvement_m"),
             0.0),
            (("storage_gate", "minimum_free_bytes_after_estimate"), 0),
        ):
            mutated = copy.deepcopy(self.stage)
            cursor = mutated
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(primary.y1r1.y1.x1.InputIntegrityError):
                primary._require(mutated)

    def test_seven_exact_macro_streams(self) -> None:
        stage, cfg, targets, reference = primary.load()
        rows = primary.campaign_streams(stage, cfg, targets)
        self.assertEqual([row["rollout_id"] for row in rows], list(primary.ROLLOUT_IDS))
        self.assertEqual(len(rows), 7)
        for row in rows:
            self.assertEqual(len(row["targets"]), 73)
            self.assertEqual(len(row["actions"]), 73)
            self.assertEqual(row["non_nominal_issue_steps"], list(range(65, 73)))
            for issue in range(65):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 reference["actions"][issue]["expected_card15_fields"])
            self.assertLessEqual(max(float(action["maximum_issued_delta_a"])
                                     for action in row["actions"]), 0.3)
            for issue in range(69, 73):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 row["actions"][68]["expected_card15_fields"])
                self.assertEqual(row["actions"][issue]["maximum_issued_delta_a"], 0.0)
        by_id = {row["rollout_id"]: row for row in rows}
        self.assertEqual(by_id[primary.ROLLOUT_IDS[0]]["actions"][68][
            "probe_virtual_action"], [64.0, 0.0, 0.0, 1.0])
        self.assertEqual(by_id[primary.ROLLOUT_IDS[1]]["actions"][68][
            "probe_virtual_action"], [68.0, 0.0, 0.0, 1.0])
        self.assertEqual(by_id[primary.ROLLOUT_IDS[2]]["actions"][68][
            "probe_virtual_action"], [60.0, 0.0, 0.0, 1.0])
        self.assertEqual(by_id[primary.ROLLOUT_IDS[3]]["actions"][68][
            "probe_virtual_action"], [64.0, -4.0, 0.0, 1.0])
        self.assertEqual(by_id[primary.ROLLOUT_IDS[4]]["actions"][68][
            "probe_virtual_action"], [64.0, 4.0, 0.0, 1.0])
        self.assertEqual(by_id[primary.ROLLOUT_IDS[5]]["actions"][68][
            "probe_virtual_action"], [64.0, 0.0, -4.0, 1.0])
        self.assertEqual(by_id[primary.ROLLOUT_IDS[6]]["actions"][68][
            "probe_virtual_action"], [64.0, 0.0, 4.0, 1.0])

    def test_offline_is_zero_plant_and_exact_headroom(self) -> None:
        result = primary.offline(primary.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["verified_plant_advances"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)
        self.assertAlmostEqual(result["minimum_absolute_current_headroom_a"], 97.6)

    @staticmethod
    def _states(*, improvement_m: float = 0.0, transient_only: bool = False,
                ip_response_a: float = 0.0) -> list[dict[str, float]]:
        states = []
        for index in range(74):
            baseline_r = index * 0.0004
            adjustment = 0.0
            if index >= 66:
                adjustment = improvement_m
            if transient_only and index != 66:
                adjustment = 0.0
            states.append({
                "r_geo_m": baseline_r - adjustment,
                "z_geo_m": 0.0,
                "ip_a": 30000.0 + (ip_response_a if index >= 66 else 0.0),
            })
        return states

    def _row(self, rollout_id: str, states: list[dict[str, float]],
             *, passed: bool = True) -> dict[str, object]:
        coordinate = next(row["coordinate"] for row in self.stage["candidate_specs"]
                          if row["rollout_id"] == rollout_id)
        level = next(row["level_delta"] for row in self.stage["candidate_specs"]
                     if row["rollout_id"] == rollout_id)
        return {"rollout_id": rollout_id, "coordinate": coordinate,
                "level_delta": level, "passed": passed, "reasons": [],
                "states": states}

    def test_persistent_macro_is_nominated(self) -> None:
        baseline = self._row(primary.ROLLOUT_IDS[0], self._states())
        candidate = self._row(primary.ROLLOUT_IDS[1],
                              self._states(improvement_m=0.0002,
                                           ip_response_a=10.0))
        result = primary.scientific_metrics([baseline, candidate], self.stage)
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_arm_id"], primary.ROLLOUT_IDS[1])
        metric = next(row for row in result["branch_metrics"]
                      if row["rollout_id"] == primary.ROLLOUT_IDS[1])
        self.assertEqual(metric["persistent_improvement_count"], 4)
        self.assertGreaterEqual(metric["terminal_source_distance_improvement_m"],
                                0.0001)

    def test_transient_spike_is_not_nominated(self) -> None:
        baseline = self._row(primary.ROLLOUT_IDS[0], self._states())
        candidate = self._row(primary.ROLLOUT_IDS[1],
                              self._states(improvement_m=0.0008,
                                           transient_only=True))
        result = primary.scientific_metrics([baseline, candidate], self.stage)
        self.assertFalse(result["passed"])
        self.assertEqual(result["nominated_arm_ids"], [])

    def test_ip_gate_and_deterministic_ranking(self) -> None:
        baseline = self._row(primary.ROLLOUT_IDS[0], self._states())
        better = self._row(primary.ROLLOUT_IDS[1],
                           self._states(improvement_m=0.00025,
                                        ip_response_a=20.0))
        lesser = self._row(primary.ROLLOUT_IDS[2],
                           self._states(improvement_m=0.0002,
                                        ip_response_a=10.0))
        over_ip = self._row(primary.ROLLOUT_IDS[3],
                            self._states(improvement_m=0.001,
                                         ip_response_a=151.0))
        result = primary.scientific_metrics(
            [baseline, lesser, over_ip, better], self.stage)
        self.assertEqual(result["selected_arm_id"], primary.ROLLOUT_IDS[1])
        self.assertNotIn(primary.ROLLOUT_IDS[3], result["nominated_arm_ids"])

    def test_route_precedence_and_safe_stop(self) -> None:
        prefixes = [{"passed": True}] * 7
        metrics = {"passed": True}
        self.assertEqual(primary.route_for(self.stage, False, True, prefixes, metrics),
                         self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(self.stage, True, False, prefixes, metrics),
                         self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, prefixes[:-1] + [{"passed": False}], metrics),
            self.stage["routes"]["prefix_mismatch"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, prefixes, {"passed": False}),
            self.stage["routes"]["utility_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, prefixes, metrics),
                         self.stage["routes"]["pass"])
        self.assertTrue(primary.safe_stop(
            {"reasons": ["PULSE_CLEARANCE_R"]}, self.stage))
        self.assertFalse(primary.safe_stop(
            {"reasons": ["EMPIRICAL_STEP_R"]}, self.stage))

    def test_independent_identity_and_launcher(self) -> None:
        self.assertEqual(independent.SCHEMA,
                         "rgeo-zgeo-1ms-id2z1-independent-raw-v1")
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z1_late_action_macro_utility.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z1_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z1_OUTPUT", launcher)
        self.assertIn("late_action_macro_utility_independent.py", launcher)
        self.assertIn('exit "$primary_rc"', launcher)


if __name__ == "__main__":
    unittest.main()
