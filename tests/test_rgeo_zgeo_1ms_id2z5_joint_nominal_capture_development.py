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
    "id2z5", "scripts/rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development.py")
independent = _module(
    "id2z5_independent",
    "scripts/rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development_independent.py")


class ID2Z5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(primary.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_budget_and_hash(self) -> None:
        primary._require(self.stage)
        self.assertEqual(primary.CONFIG_SHA256, primary.base.sha256(primary.CONFIG))
        self.assertEqual(self.stage["maximum_rollouts"], 13)
        self.assertEqual(self.stage["maximum_advance_attempts"], 13 * 117)
        self.assertEqual(self.stage["maximum_retained_states"], 13 * 118)
        self.assertEqual(
            self.stage["required_artifact_files_if_all_complete"], 13 * 118 * 5)
        self.assertEqual(self.stage["terminal_state_indices"], list(range(112, 118)))

    def test_contract_mutations_fail_closed(self) -> None:
        for path, value in (
                (("decision_state_index",), 65),
                (("action_semantics", "minimum_absolute_current_headroom_a_on_new_targets"), 99.9),
                (("measurement_gates", "minimum_complete_non_replay_families"), 7),
                (("storage_gate", "minimum_free_bytes_after_estimate"), 0),
                (("candidate_specs", 4, "tokens"), "F" * 24)):
            changed = copy.deepcopy(self.stage)
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(primary.z3.z1.y1r1.y1.x1.InputIntegrityError):
                primary._require(changed)

    def test_state61_prefix_and_all_streams_are_statically_admissible(self) -> None:
        stage, cfg, targets, reference, selected = primary.load()
        self.assertEqual([row["state_index"] for row in reference["state_checkpoints"]],
                         [0, 32, 49, 53, 57, 61])
        streams = primary.candidate_streams(stage, cfg, targets, selected)
        self.assertEqual(len(streams), 13)
        for stream in streams:
            check = primary.validate_stream(stream, stage, cfg)
            self.assertTrue(check["passed"], check)
            self.assertGreaterEqual(check["minimum_absolute_current_headroom_a"], 100.0)
            self.assertGreaterEqual(check["minimum_prefix_b_minus_f_balance"], 0)
            self.assertEqual(len(stream["actions"]), 117)
            for issue in range(61):
                self.assertEqual(
                    stream["actions"][issue]["expected_card15_fields"],
                    selected["actions"][issue]["expected_card15_fields"])
            for issue in range(85, 117):
                self.assertEqual(float(stream["actions"][issue]["maximum_issued_delta_a"]), 0.0)

    def test_offline_is_zero_plant_and_replay_stream_is_identical(self) -> None:
        result = primary.offline(primary.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(len(result["admissible_candidate_ids"]), 13)

    @staticmethod
    def _states(count: int) -> list[dict]:
        values = []
        for index in range(count):
            values.append({
                "time_ms": 1100 + index,
                "r_geo_m": 0.7 if index == 0 else 0.724,
                "z_geo_m": 0.03,
                "r_mid_m": 0.8,
                "ip_a": 30000.0,
                "actual_current_decimal_a_tsc": ["0"] * 14,
                "wire_current_a": [0.0] * 48,
                "active_command_card15_fields": ["0"] * 14,
            })
        return values

    def _row(self, spec: dict, *, complete: bool = True) -> dict:
        states = self._states(118 if complete else 70)
        return {
            **spec,
            "rollout_id": spec["candidate_id"],
            "passed": complete,
            "reasons": [] if complete else ["PULSE_CLEARANCE_R"],
            "states": states,
            "actions": [{"expected_card15_fields": ["0"] * 14}
                        for _ in range(len(states) - 1)],
        }

    def test_data_readiness_is_separate_from_capture(self) -> None:
        rows = [self._row(spec) for spec in self.stage["candidate_specs"]]
        result = primary.metrics(rows, self.stage)
        self.assertTrue(result["passed"])
        self.assertTrue(result["critical_replay_check"]["passed"])
        self.assertEqual(result["complete_non_replay_families"], 12)
        self.assertTrue(result["capture_not_required_for_data_readiness"])
        rows[1] = self._row(self.stage["candidate_specs"][1], complete=False)
        rows[2] = self._row(self.stage["candidate_specs"][2], complete=False)
        rows[3] = self._row(self.stage["candidate_specs"][3], complete=False)
        rows[4] = self._row(self.stage["candidate_specs"][4], complete=False)
        rows[-1] = self._row(self.stage["candidate_specs"][-1], complete=False)
        self.assertFalse(primary.metrics(rows, self.stage)["passed"])

    def test_route_precedence_and_launcher(self) -> None:
        prefixes = [{"passed": True}]
        self.assertEqual(primary.route_for(
            self.stage, False, True, prefixes, {"passed": True}),
            self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, False, prefixes, {"passed": True}),
            self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, [{"passed": False}], {"passed": True}),
            self.stage["routes"]["prefix_mismatch"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, prefixes, {"passed": True}),
            self.stage["routes"]["capture_candidate"])
        self.assertIn("development-independent-raw-v1", independent.SCHEMA)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z5_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z5_OUTPUT", launcher)
        self.assertIn("joint_nominal_capture_development_independent.py", launcher)


if __name__ == "__main__":
    unittest.main()
