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
    "id2z3", "scripts/rgeo_zgeo_1ms_id2z3_bounded_braking_rolling_search.py")
independent = _module(
    "id2z3_independent",
    "scripts/rgeo_zgeo_1ms_id2z3_bounded_braking_rolling_search_independent.py")


class ID2Z3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(primary.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_budget_and_routes(self) -> None:
        primary._require(self.stage)
        self.assertEqual(primary.CONFIG_SHA256,
                         primary.z1.y1r1.y1.x1.sha256(primary.CONFIG))
        self.assertEqual(self.stage["maximum_rollouts"], 15)
        self.assertEqual(self.stage["maximum_advance_attempts"],
                         3 * sum((89, 93, 97, 101, 105)))
        self.assertEqual(self.stage["maximum_retained_states"],
                         3 * sum((90, 94, 98, 102, 106)))
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"],
                         self.stage["maximum_retained_states"] * 5)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)

    def test_contract_mutation_fails_closed(self) -> None:
        for path, value in (
            (("maximum_gotsc_calls",), 1456),
            (("action_semantics", "maximum_per_coil_issue_delta_a"), 0.31),
            (("measurement_gates",
              "minimum_terminal_max_speed_improvement_m_per_s"), 0.0),
            (("stabilization_gate", "maximum_rz_step_speed_m_per_s"), 0.2),
            (("storage_gate", "minimum_free_bytes_after_estimate"), 0),
        ):
            mutated = copy.deepcopy(self.stage)
            cursor = mutated
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(primary.z1.y1r1.y1.x1.InputIntegrityError):
                primary._require(mutated)

    def test_load_and_logical_state77_prefix(self) -> None:
        stage, cfg, targets, reference, selected = primary.load()
        self.assertEqual(len(reference["states"]), 82)
        self.assertEqual(len(reference["actions"]), 81)
        rows = primary.initial_round_streams(stage, cfg, targets, selected)
        self.assertEqual([row["arm_id"] for row in rows], list(primary.ARM_IDS))
        for row in rows:
            self.assertEqual(len(row["actions"]), 89)
            self.assertEqual(len(row["targets"]), 89)
            for issue in range(77):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 reference["actions"][issue]["expected_card15_fields"])
            for issue in range(81, 89):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 row["actions"][80]["expected_card15_fields"])
                self.assertEqual(float(row["actions"][issue][
                    "maximum_issued_delta_a"]), 0.0)

    def test_next_round_discards_lookahead_hold(self) -> None:
        stage, cfg, targets, _, selected = primary.load()
        first = next(row for row in primary.initial_round_streams(
            stage, cfg, targets, selected) if row["arm_id"] == "p07minus4")
        children = primary.next_round_streams(
            stage, cfg, targets, first, 1, ["p07minus4"])
        hold = next(row for row in children if row["arm_id"] == "hold")
        self.assertEqual(len(hold["actions"]), 93)
        for issue in range(81):
            self.assertEqual(hold["actions"][issue]["expected_card15_fields"],
                             first["actions"][issue]["expected_card15_fields"])
        self.assertEqual(hold["actions"][81]["expected_card15_fields"],
                         first["actions"][80]["expected_card15_fields"])
        self.assertEqual(float(hold["actions"][81]["maximum_issued_delta_a"]), 0.0)

    def test_offline_is_zero_plant_and_records_exclusions(self) -> None:
        result = primary.offline(primary.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertGreater(result["candidate_stream_check_count"], 0)
        self.assertLessEqual(result["candidate_stream_check_count"], 363)
        self.assertGreater(result["admissible_stream_count"], 0)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _states(count: int, speed_m_per_s: float,
                *, response_m: float = 0.0, ip_response_a: float = 0.0):
        states = []
        for index in range(count):
            states.append({
                "r_geo_m": speed_m_per_s * 0.001 * index - response_m,
                "z_geo_m": 0.0,
                "ip_a": 30000.0 + ip_response_a,
            })
        return states

    def _row(self, arm_id: str, states, round_index: int = 0):
        spec = next(value for value in self.stage["candidate_specs"]
                    if value["arm_id"] == arm_id)
        return {**spec, "rollout_id": f"r{round_index}__{arm_id}",
                "round_index": round_index, "passed": True, "reasons": [],
                "states": states}

    def test_metrics_select_speed_improvement_and_reject_distance_regression(self) -> None:
        # Decision 77, terminal 89.  Offset the candidate after decision so
        # paired response is nonzero without changing its terminal speed.
        baseline_states = self._states(90, 0.30)
        useful_states = copy.deepcopy(baseline_states)
        bad_states = copy.deepcopy(baseline_states)
        for index in range(78, 90):
            useful_states[index]["r_geo_m"] = (
                useful_states[77]["r_geo_m"] + 0.20 * 0.001 * (index - 77))
            bad_states[index]["r_geo_m"] = (
                bad_states[77]["r_geo_m"] + 0.20 * 0.001 * (index - 77)
                + 0.002)
        result = primary.round_metrics([
            self._row("hold", baseline_states),
            self._row("p07minus4", useful_states),
            self._row("p03forward4", bad_states),
        ], self.stage, 0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_arm_id"], "p07minus4")
        by_arm = {value["arm_id"]: value for value in result["branch_metrics"]}
        self.assertFalse(by_arm["p03forward4"]["eligible"])

    def test_stabilization_and_route_precedence(self) -> None:
        states = self._states(90, 0.05)
        row = self._row("hold", states)
        metric = primary.stabilization_metrics(row, self.stage)
        self.assertTrue(metric["passed"])
        good_prefix = [{"passed": True}]
        stable_round = {"passed": True, "stabilization_reached": True}
        continue_round = {"passed": True, "stabilization_reached": False}
        fail_round = {"passed": False, "stabilization_reached": False}
        self.assertEqual(primary.route_for(
            self.stage, False, True, good_prefix, [stable_round]),
            self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, False, good_prefix, [stable_round]),
            self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, [{"passed": False}], [stable_round]),
            self.stage["routes"]["prefix_mismatch"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good_prefix, [stable_round]),
            self.stage["routes"]["stabilization_candidate"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good_prefix, [fail_round]),
            self.stage["routes"]["no_braking_arm"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good_prefix, [continue_round]),
            self.stage["routes"]["budget_exhausted"])

    def test_independent_identity_and_launcher(self) -> None:
        self.assertEqual(independent.SCHEMA,
                         "rgeo-zgeo-1ms-id2z3-independent-raw-v1")
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z3_bounded_braking_rolling_search.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z3_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z3_OUTPUT", launcher)
        self.assertIn("bounded_braking_rolling_search_independent.py", launcher)
        self.assertIn('exit "$primary_rc"', launcher)


if __name__ == "__main__":
    unittest.main()
