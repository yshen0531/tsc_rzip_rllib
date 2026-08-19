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
    "id2z6", "scripts/rgeo_zgeo_1ms_id2z6_early_root_branch_teacher.py")
independent = _module(
    "id2z6_independent",
    "scripts/rgeo_zgeo_1ms_id2z6_early_root_branch_teacher_independent.py")


class ID2Z6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(primary.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_budget_and_three_envelopes(self) -> None:
        primary._require(self.stage)
        self.assertEqual(primary.CONFIG_SHA256, primary.z5.base.sha256(primary.CONFIG))
        self.assertEqual(self.stage["maximum_rollouts"], 16)
        self.assertEqual(self.stage["maximum_advance_attempts"], 16 * 69)
        self.assertEqual(self.stage["maximum_retained_states"], 16 * 70)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 16 * 70 * 5)
        self.assertEqual(
            self.stage["empirical_exploration"][
                "simulator_development_preissue_clearance"]["r_geo_m"], 0.035)
        self.assertEqual(
            self.stage["empirical_exploration"]["outer_hard_envelope"]["r_geo_m"],
            0.05)
        self.assertEqual(
            self.stage["measurement_gates"]["maximum_capture_source_rz_distance_m"],
            0.025)

    def test_contract_mutations_fail_closed(self) -> None:
        for path, value in (
                (("rounds", 0, "decision_state_index"), 50),
                (("candidate_specs", 3, "tokens"), "BFFF"),
                (("action_semantics", "scalar_100a_headroom_is_not_a_gate"), False),
                (("empirical_exploration", "outer_hard_envelope", "r_geo_m"), 0.06),
                (("measurement_gates", "terminal_state_indices"), list(range(63, 69))),
                (("storage_gate", "minimum_free_bytes_after_estimate"), 0)):
            changed = copy.deepcopy(self.stage)
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(primary.z5.z3.z1.y1r1.y1.x1.InputIntegrityError):
                primary._require(changed)

    def test_state49_streams_and_full_static_matrix(self) -> None:
        stage, cfg, targets, compact, selected = primary.load()
        self.assertGreaterEqual(len(compact["states"]), 70)
        streams = primary.initial_round_streams(stage, cfg, targets, selected)
        self.assertEqual([row["arm_id"] for row in streams], list(primary.ARM_IDS))
        self.assertEqual(len(streams), 5)
        for stream in streams:
            check = primary.validate_stream(stream, stage, cfg, targets)
            self.assertTrue(check["passed"], check)
            self.assertEqual(len(stream["actions"]), 69)
            for issue in range(49):
                self.assertEqual(
                    stream["actions"][issue]["expected_card15_fields"],
                    selected["actions"][issue]["expected_card15_fields"])
            for issue in range(53, 69):
                self.assertEqual(float(stream["actions"][issue]["maximum_issued_delta_a"]),
                                 0.0)
        matrix = primary._enumerate_static_sequences(stage, cfg, targets, selected)
        self.assertEqual(len(matrix), 125)
        self.assertTrue(all(row["passed"] for row in matrix))

    def test_offline_is_zero_plant_and_does_not_fit(self) -> None:
        result = primary.offline(primary.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["static_three_round_sequence_count"], 125)
        self.assertEqual(result["static_three_round_sequences_passed"], 125)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    @staticmethod
    def _states(distance: float, count: int = 70) -> list[dict]:
        rows = []
        for index in range(count):
            r = 0.0 if index == 0 else distance
            rows.append({
                "time_ms": 1100 + index,
                "r_geo_m": r,
                "z_geo_m": 0.0,
                "r_mid_m": 0.8,
                "ip_a": 30000.0,
                "actual_current_decimal_a_tsc": ["0"] * 14,
                "wire_current_a": [0.0] * 48,
                "active_command_card15_fields": ["0"] * 14,
                "artifact_sha256": {name: "same" for name in (
                    "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv")},
            })
        return rows

    def _row(self, arm_id: str, distance: float, round_index: int = 0,
             fit_weight: int = 1) -> dict:
        return {
            "rollout_id": f"r{round_index}__{arm_id}",
            "candidate_id": f"r{round_index}__{arm_id}",
            "arm_id": arm_id,
            "tokens": dict(zip(primary.ARM_IDS, ("HHHH", "BBBB", "FFFF", "BBFF", "FFBB")))[arm_id],
            "round_index": round_index,
            "fit_weight": fit_weight,
            "passed": True,
            "reasons": [],
            "states": self._states(distance),
            "actions": [{"expected_card15_fields": ["0"] * 14} for _ in range(69)],
        }

    def test_round_selection_uses_joint_terminal_score_not_distance_label(self) -> None:
        rows = [self._row("hold4", 0.030)]
        rows.extend(self._row(arm, value) for arm, value in (
            ("b4", 0.024), ("f4", 0.028), ("b2f2", 0.026), ("f2b2", 0.027)))
        value = primary.round_metrics(rows, self.stage, 0)
        self.assertTrue(value["passed"])
        self.assertEqual(value["selected_arm_id"], "b4")
        self.assertGreater(value["baseline_terminal_worst_normalized_score"], 1.0)
        by_arm = {row["arm_id"]: row for row in value["branch_metrics"]}
        self.assertGreater(by_arm["b4"]["score_improvement_over_hold"], 0.02)

    def test_replay_and_final_data_readiness_are_separate(self) -> None:
        rows = []
        rounds = []
        selected = None
        for round_index in range(3):
            current = [self._row("hold4", 0.030, round_index)]
            current.extend(self._row(arm, 0.020 + 0.001 * index, round_index)
                           for index, arm in enumerate(primary.ARM_IDS[1:]))
            rows.extend(current)
            value = primary.round_metrics(current, self.stage, round_index)
            rounds.append(value)
            selected = next(row for row in current
                            if row["arm_id"] == value["selected_arm_id"])
        assert selected is not None
        replay = copy.deepcopy(selected)
        replay.update({"rollout_id": "critical_replay", "candidate_id": "critical_replay",
                       "fit_weight": 0})
        rows.append(replay)
        result = primary.final_metrics(rounds, rows, self.stage, selected, replay)
        self.assertTrue(result["critical_replay_check"]["passed"])
        self.assertEqual(result["complete_fit_weight_windows"], 15)
        self.assertTrue(result["development_data_ready"])
        rows[0]["passed"] = False
        result = primary.final_metrics(rounds, rows, self.stage, selected, replay)
        self.assertFalse(result["development_data_ready"])

    def test_route_precedence_and_launcher(self) -> None:
        rounds = [{"passed": True}] * 3
        science = {
            "critical_replay_check": {"passed": True},
            "teacher_utility_passed": True,
            "development_data_ready": True,
        }
        self.assertEqual(primary.route_for(
            self.stage, False, True, True, rounds, science),
            self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, False, True, rounds, science),
            self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, False, rounds, science),
            self.stage["routes"]["prefix_mismatch"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, True, rounds, science),
            self.stage["routes"]["pass"])
        self.assertIn("id2z6-independent-raw-v1", independent.SCHEMA)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z6_early_root_branch_teacher.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z6_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z6_OUTPUT", launcher)
        self.assertIn("early_root_branch_teacher_independent.py", launcher)


if __name__ == "__main__":
    unittest.main()
