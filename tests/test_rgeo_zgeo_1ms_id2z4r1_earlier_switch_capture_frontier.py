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
    "id2z4r1",
    "scripts/rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier.py")
independent = _module(
    "id2z4r1_independent",
    "scripts/rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier_independent.py")


class ID2Z4R1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(primary.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_budget_and_routes(self) -> None:
        primary._require(self.stage)
        self.assertIsNotNone(primary.CountingRunner)
        for name in (
                "_record", "_validate_record", "RGeoZGeoSignal",
                "OneMsNR1SafetyEnvelope", "_outer_reasons",
                "_pulse_clearance", "card15_target_decimal_a",
                "assert_exact_slew", "_action", "_step_cap_reasons"):
            self.assertTrue(hasattr(primary.id0, name), name)
        self.assertEqual(primary.CONFIG_SHA256, primary.sha256(primary.CONFIG))
        self.assertEqual(self.stage["maximum_rollouts"], 12)
        self.assertEqual(self.stage["maximum_advance_attempts"], 12 * 117)
        self.assertEqual(self.stage["maximum_retained_states"], 12 * 118)
        self.assertEqual(
            self.stage["required_artifact_files_if_all_complete"], 12 * 118 * 5)
        self.assertEqual(self.stage["terminal_state_indices"], list(range(112, 118)))
        self.assertTrue(
            self.stage["measurement_gates"]["negative_control_may_be_incomplete"])

    def test_contract_mutations_fail_closed(self) -> None:
        for path, value in (
            (("maximum_gotsc_calls",), 1405),
            (("decision_state_index",), 89),
            (("action_semantics", "maximum_per_coil_issue_delta_a"), 0.31),
            (("measurement_gates", "negative_control_may_be_incomplete"), False),
            (("measurement_gates", "capture_terminal_state_indices"), [109]),
            (("storage_gate", "minimum_free_bytes_after_estimate"), 0),
        ):
            mutated = copy.deepcopy(self.stage)
            cursor = mutated
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(
                    primary.z3.z1.y1r1.y1.x1.InputIntegrityError):
                primary._require(mutated)

    def test_exact_state93_prefix_and_candidate_frontier(self) -> None:
        stage, cfg, targets, reference, selected = primary.load()
        self.assertGreaterEqual(reference["required_state_count"], 94)
        self.assertGreaterEqual(reference["required_action_count"], 93)
        rows = primary.candidate_streams(stage, cfg, targets, selected)
        self.assertEqual(len(rows), 12)
        self.assertEqual([row["candidate_id"] for row in rows], [
            spec["candidate_id"] for spec in stage["candidate_specs"]])
        for row in rows:
            self.assertEqual(len(row["actions"]), 117)
            self.assertEqual(len(row["targets"]), 117)
            self.assertTrue(primary.validate_stream(row, stage, cfg)["passed"])
            for issue in range(93):
                self.assertEqual(
                    row["actions"][issue]["expected_card15_fields"],
                    selected["actions"][issue]["expected_card15_fields"])
            for issue in range(105, 117):
                self.assertEqual(
                    row["actions"][issue]["expected_card15_fields"],
                    row["actions"][104]["expected_card15_fields"])
                self.assertEqual(
                    float(row["actions"][issue]["maximum_issued_delta_a"]), 0.0)

    def test_offline_requires_admissible_mixed_branch_and_is_zero_plant(self) -> None:
        result = primary.offline(primary.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        admitted = set(result["admissible_candidate_ids"])
        mixed = {spec["candidate_id"] for spec in self.stage["candidate_specs"]
                 if "B" in spec["tokens"] and "U" in spec["tokens"]}
        self.assertIn("hold12", admitted)
        self.assertTrue(admitted & mixed)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _states(count: int, *, distance_m: float = 0.024,
                speed_m_per_s: float = 0.0, ip_offset_a: float = 0.0):
        source_r = 0.7
        states = []
        for index in range(count):
            r = source_r if index == 0 else (
                source_r + distance_m + max(0, index - 107) *
                speed_m_per_s * 0.001)
            states.append({
                "r_geo_m": r,
                "z_geo_m": 0.03,
                "ip_a": 30000.0 + (0.0 if index == 0 else ip_offset_a),
            })
        return states

    def _row(self, candidate_id: str, states, passed: bool = True):
        spec = next(value for value in self.stage["candidate_specs"]
                    if value["candidate_id"] == candidate_id)
        return {**spec, "rollout_id": candidate_id, "passed": passed,
                "reasons": [], "states": states, "actions": []}

    def test_incomplete_negative_control_does_not_block_capture_science(self) -> None:
        incomplete_hold = self._row(
            "hold12", self._states(100), passed=False)
        candidate = self._row("b4_u4_h4", self._states(118))
        result = primary.metrics([incomplete_hold, candidate], self.stage)
        self.assertFalse(result["negative_control_complete"])
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_candidate_id"], "b4_u4_h4")
        metric = next(value for value in result["candidate_metrics"]
                      if value["candidate_id"] == "b4_u4_h4")
        self.assertEqual(metric["paired_response_state_indices"], list(range(94, 100)))

    def test_terminal_speed_and_ip_remain_hard_capture_gates(self) -> None:
        good = self._row("b4_u4_h4", self._states(118))
        fast = self._row(
            "b6_u4_h2", self._states(118, speed_m_per_s=0.100001))
        high_ip = self._row(
            "b8_u4", self._states(118, ip_offset_a=1500.001))
        result = primary.metrics([good, fast, high_ip], self.stage)
        by_id = {row["candidate_id"]: row
                 for row in result["candidate_metrics"]}
        self.assertTrue(by_id["b4_u4_h4"]["capture_passed"])
        self.assertFalse(by_id["b6_u4_h2"]["capture_passed"])
        self.assertFalse(by_id["b8_u4"]["capture_passed"])

    def test_live_checkpoint_gate_is_exact(self) -> None:
        stage, _, _, reference, _ = primary.load()
        state93 = next(value for value in reference["state_checkpoints"]
                       if value["state_index"] == 93)
        self.assertEqual(primary.checkpoint_reasons(
            copy.deepcopy(state93), 93, reference, stage), [])
        changed = copy.deepcopy(state93)
        changed["r_geo_m"] += 1e-12
        self.assertIn("LIVE_PREFIX:93:r_geo_m", primary.checkpoint_reasons(
            changed, 93, reference, stage))

    def test_route_precedence_and_identity(self) -> None:
        good_prefix = [{"passed": True}]
        scientific_pass = {"passed": True}
        scientific_fail = {"passed": False}
        self.assertEqual(primary.route_for(
            self.stage, False, True, good_prefix, scientific_pass),
            self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, False, good_prefix, scientific_pass),
            self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, [{"passed": False}], scientific_pass),
            self.stage["routes"]["prefix_mismatch"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good_prefix, scientific_pass),
            self.stage["routes"]["capture_candidate"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, good_prefix, scientific_fail),
            self.stage["routes"]["no_capture_candidate"])

    def test_independent_identity_and_launcher(self) -> None:
        self.assertEqual(
            independent.SCHEMA,
            "rgeo-zgeo-1ms-id2z4r1-earlier-switch-capture-frontier-"
            "independent-raw-reporting-r1")
        self.assertEqual(independent._side_from_geometry({
            "r_geo_m": 0.70, "r_mid_m": 0.80}), "HFS")
        self.assertEqual(independent._side_from_geometry({
            "r_geo_m": 0.80, "r_mid_m": 0.80}), "LFS")
        self.assertEqual(independent._side_from_geometry({
            "r_geo_m": 0.81, "r_mid_m": 0.80}), "LFS")
        launcher = (ROOT /
                    "run_rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier.sh").read_text(
                        encoding="utf-8")
        self.assertIn("ID2Z4R1_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z4R1_OUTPUT", launcher)
        self.assertIn("earlier_switch_capture_frontier_independent.py", launcher)
        self.assertIn('exit "$primary_rc"', launcher)


if __name__ == "__main__":
    unittest.main()
