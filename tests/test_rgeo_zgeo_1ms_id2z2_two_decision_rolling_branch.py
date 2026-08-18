from __future__ import annotations

import copy
import importlib.util
import json
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
    "id2z2", "scripts/rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch.py")
independent = _module(
    "id2z2_independent",
    "scripts/rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch_independent.py")


class ID2Z2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(primary.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_budget_and_routes(self) -> None:
        primary._require(self.stage)
        self.assertEqual(primary.CONFIG_SHA256,
                         primary.z1.y1r1.y1.x1.sha256(primary.CONFIG))
        self.assertEqual(self.stage["maximum_rollouts"], 14)
        self.assertEqual(self.stage["maximum_advance_attempts"], 7 * 77 + 7 * 81)
        self.assertEqual(self.stage["maximum_retained_states"], 7 * 78 + 7 * 82)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"],
                         (7 * 78 + 7 * 82) * 5)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(
            self.stage["routes"]["pass"],
            "ONE_MS_ID2Z2_TWO_DECISION_ROLLING_BRANCH_PASS_HOLD_CONTROLLER_DESIGN_ONLY")

    def test_contract_mutation_fails_closed(self) -> None:
        for path, value in (
            (("maximum_gotsc_calls",), 1107),
            (("action_semantics", "maximum_per_coil_issue_delta_a"), 0.31),
            (("measurement_gates",
              "minimum_active_terminal_source_distance_improvement_m"), 0.0),
            (("storage_gate", "minimum_free_bytes_after_estimate"), 0),
            (("prefix_gates", "round_b_matches_selected_round_a"), False),
        ):
            mutated = copy.deepcopy(self.stage)
            cursor = mutated
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(primary.z1.y1r1.y1.x1.InputIntegrityError):
                primary._require(mutated)

    def test_round_a_and_all_49_round_b_combinations_are_exact(self) -> None:
        stage, cfg, targets, selected, selected_stream = primary.load()
        round_a = primary.initial_round_streams(stage, cfg, targets, selected_stream)
        self.assertEqual([row["arm_id"] for row in round_a], list(primary.ARM_IDS))
        self.assertEqual(len(round_a), 7)
        for row in round_a:
            self.assertEqual(len(row["actions"]), 77)
            self.assertEqual(len(row["targets"]), 77)
            for issue in range(69):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 selected["actions"][issue]["expected_card15_fields"])
            self.assertLessEqual(max(float(value["maximum_issued_delta_a"])
                                     for value in row["actions"]), 0.3)
            for issue in range(73, 77):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 row["actions"][72]["expected_card15_fields"])
                self.assertEqual(float(row["actions"][issue][
                    "maximum_issued_delta_a"]), 0.0)
        by_arm = {row["arm_id"]: row for row in round_a}
        self.assertEqual(by_arm["p03forward4"]["actions"][72][
            "probe_virtual_action"], [72.0, 0.0, 0.0, 1.0])
        self.assertEqual(by_arm["p03unwind4"]["actions"][72][
            "probe_virtual_action"], [64.0, 0.0, 0.0, 1.0])
        combinations = []
        for parent in round_a:
            children = primary.next_round_streams(stage, cfg, targets, parent)
            self.assertEqual([row["arm_id"] for row in children],
                             list(primary.ARM_IDS))
            for row in children:
                self.assertEqual(len(row["actions"]), 81)
                for issue in range(73):
                    self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                     parent["actions"][issue]["expected_card15_fields"])
                self.assertLessEqual(max(float(value["maximum_issued_delta_a"])
                                         for value in row["actions"]), 0.3)
                for issue in range(77, 81):
                    self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                     row["actions"][76]["expected_card15_fields"])
                combinations.append((parent["arm_id"], row["arm_id"]))
        self.assertEqual(len(combinations), 49)

    def test_offline_is_zero_plant_and_all_combinations_admissible(self) -> None:
        result = primary.offline(primary.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["round_b_combination_count"], 49)
        self.assertTrue(all(row["passed"] for row in result[
            "round_a_stream_checks"] + result["round_b_combination_checks"]))
        self.assertGreaterEqual(result["minimum_absolute_current_headroom_a"], 95.0)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["verified_plant_advances"], 0)

    @staticmethod
    def _states(*, count: int, decision: int, improvement_m: float = 0.0,
                active_only: bool = False, ip_response_a: float = 0.0):
        values = []
        for index in range(count):
            baseline_r = index * 0.0002
            adjustment = improvement_m if index > decision else 0.0
            if active_only and index > decision + 4:
                adjustment = 0.0
            values.append({
                "r_geo_m": baseline_r - adjustment,
                "z_geo_m": 0.0,
                "ip_a": 30000.0 + (ip_response_a if index > decision else 0.0),
            })
        return values

    def _row(self, round_index: int, arm_id: str, states, passed: bool = True):
        spec = next(value for value in self.stage["candidate_specs"]
                    if value["arm_id"] == arm_id)
        return {**spec, "rollout_id": f"r{round_index}__{arm_id}",
                "round_index": round_index, "passed": passed,
                "reasons": [], "states": states}

    def test_round_metrics_require_active_and_terminal_persistence(self) -> None:
        baseline = self._row(0, "hold", self._states(count=78, decision=69))
        useful = self._row(
            0, "p03forward4",
            self._states(count=78, decision=69, improvement_m=0.00025,
                         ip_response_a=10.0))
        result = primary.round_metrics([baseline, useful], self.stage, 0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_arm_id"], "p03forward4")
        transient = self._row(
            0, "p03forward4",
            self._states(count=78, decision=69, improvement_m=0.00025,
                         active_only=True))
        rejected = primary.round_metrics([baseline, transient], self.stage, 0)
        self.assertFalse(rejected["passed"])

    def test_round_metrics_reject_ip_and_select_absolute_geometry(self) -> None:
        baseline = self._row(1, "hold", self._states(count=82, decision=73))
        best = self._row(
            1, "p03forward4",
            self._states(count=82, decision=73, improvement_m=0.0003,
                         ip_response_a=100.0))
        lesser = self._row(
            1, "p07minus4",
            self._states(count=82, decision=73, improvement_m=0.0002,
                         ip_response_a=20.0))
        over_ip = self._row(
            1, "p04minus4",
            self._states(count=82, decision=73, improvement_m=0.001,
                         ip_response_a=151.0))
        result = primary.round_metrics(
            [baseline, lesser, over_ip, best], self.stage, 1)
        self.assertEqual(result["selected_arm_id"], "p03forward4")
        self.assertNotIn("p04minus4", result["nominated_arm_ids"])

    def test_route_precedence_and_both_rounds_required(self) -> None:
        good = [{"passed": True}] * 7
        bad = good[:-1] + [{"passed": False}]
        metrics = {"passed": True}
        self.assertEqual(primary.route_for(
            self.stage, False, True, good, metrics, good, metrics),
            self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, False, good, metrics, good, metrics),
            self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, bad, metrics, good, metrics),
            self.stage["routes"]["round_a_prefix_mismatch"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good, {"passed": False}, [], None),
            self.stage["routes"]["round_a_utility_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good, metrics, bad, metrics),
            self.stage["routes"]["round_b_prefix_mismatch"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good, metrics, good, {"passed": False}),
            self.stage["routes"]["round_b_utility_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good, metrics, good, metrics),
            self.stage["routes"]["pass"])

    def test_prefix_check_uses_complete_state_and_action_counts(self) -> None:
        state = {
            "r_geo_m": 1.0, "z_geo_m": 2.0, "r_mid_m": 3.0, "ip_a": 4.0,
            "actual_current_decimal_a_tsc": ["0"] * 14,
            "wire_current_a": [0.0] * 48,
            "active_command_card15_fields": ["0"] * 14,
            "artifact_sha256": {name: name for name in self.stage[
                "semantic_artifacts"]},
        }
        action = {"expected_card15_fields": ["0"] * 14}
        row = {"rollout_id": "x", "states": [copy.deepcopy(state)] * 2,
               "actions": [copy.deepcopy(action)]}
        reference = copy.deepcopy(row)
        self.assertTrue(primary._prefix_check(
            row, reference, 2, 1, self.stage["semantic_artifacts"])["passed"])
        row["states"][1] = {**row["states"][1], "wire_current_a": [1.0] * 48}
        self.assertFalse(primary._prefix_check(
            row, reference, 2, 1, self.stage["semantic_artifacts"])["passed"])

    def test_independent_identity_and_launcher(self) -> None:
        self.assertEqual(independent.SCHEMA,
                         "rgeo-zgeo-1ms-id2z2-independent-raw-v1")
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z2_two_decision_rolling_branch.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z2_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z2_OUTPUT", launcher)
        self.assertIn("two_decision_rolling_branch_independent.py", launcher)
        self.assertIn('exit "$primary_rc"', launcher)


if __name__ == "__main__":
    unittest.main()
