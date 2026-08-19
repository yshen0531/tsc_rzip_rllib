from __future__ import annotations

import copy
import json
import unittest

from scripts import rgeo_zgeo_1ms_id2z14_early_remaining_basis_capture as m
from scripts import rgeo_zgeo_1ms_id2z14_early_remaining_basis_capture_independent as mi


class ID2Z14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.reference = m.load()

    def test_identity_budget_and_data_role(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_rollouts"], 10)
        self.assertEqual(self.stage["maximum_advance_attempts"], 650)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 3300)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(
            self.stage["fit_calibration_holdout_controller_expert_bc_dagger_rl_fixture_use"],
            "forbidden")

    def test_state33_prefix_and_closing_evidence_are_bound(self) -> None:
        self.assertGreaterEqual(len(self.parent["actions"]), 33)
        self.assertEqual(len(self.reference["states"]), 78)
        self.assertTrue(m.z6.prefix_check(
            self.reference, self.reference, 34, 33,
            self.stage["semantic_artifacts"])["passed"])

    def test_matrix_contains_p01_and_exact_return_p09(self) -> None:
        rows = m.build_matrix(self.stage, self.cfg, self.targets, self.parent)
        self.assertEqual([row["arm_id"] for row in rows], list(m.ARM_IDS))
        by_id = {row["arm_id"]: row for row in rows}
        self.assertEqual(by_id["i4h4"]["tokens"], "IIIIHHHH")
        self.assertEqual(by_id["j4h4"]["tokens"], "JJJJHHHH")
        self.assertEqual(by_id["k4r3"]["tokens"], "KHHHLHHH")
        self.assertEqual(by_id["l4r3"]["tokens"], "LHHHKHHH")
        decision = self.stage["decision_state_index"]
        for arm in ("k4r3", "l4r3"):
            self.assertEqual(
                by_id[arm]["actions"][decision + 4]["expected_card15_fields"],
                by_id[arm]["actions"][decision - 1]["expected_card15_fields"])
        self.assertEqual(
            by_id["i4h4"]["actions"][decision]["probe_virtual_action"][3]
            - by_id["h8"]["actions"][decision]["probe_virtual_action"][3], 1.0)
        self.assertEqual(
            by_id["j4h4"]["actions"][decision]["probe_virtual_action"][3]
            - by_id["h8"]["actions"][decision]["probe_virtual_action"][3], -1.0)

    def test_all_streams_are_statically_admissible(self) -> None:
        for row in m.build_matrix(self.stage, self.cfg, self.targets, self.parent):
            checked = m.validate_stream(row, self.stage, self.cfg)
            self.assertTrue(checked["passed"], checked["failures"])
            self.assertEqual(len(row["actions"]), 65)
            self.assertLessEqual(max(action["maximum_issued_delta_a"]
                                     for action in row["actions"]), 0.3)

    def test_offline_matrix_is_exact_and_zero_tsc(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_sequence_count"], 9)
        self.assertEqual(value["static_sequences_passed"], 9)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _states(distance: float, speed: float = 0.0) -> list[dict]:
        values = []
        for index in range(66):
            position = distance + (index - 60) * speed * 0.001 if index >= 60 else distance
            values.append({"r_geo_m": 0.0 if index == 0 else position,
                           "z_geo_m": 0.0, "ip_a": 1000.0})
        return values

    def _row(self, arm: str, distance: float, speed: float = 0.0) -> dict:
        spec = next(row for row in self.stage["candidate_specs"]
                    if row["arm_id"] == arm)
        return {"rollout_id": arm, "arm_id": arm, "tokens": spec["tokens"],
                "passed": True, "states": self._states(distance, speed),
                "actions": [{"expected_card15_fields": ["0"] * 14}
                            for _ in range(65)]}

    def test_relative_improvement_is_not_capture(self) -> None:
        rows = [self._row("h8", 0.030)]
        rows.extend(self._row(arm, 0.026 + index * 0.0001)
                    for index, arm in enumerate(m.ARM_IDS[1:]))
        value = m._metrics(rows, self.stage)
        self.assertTrue(value["passed"])
        self.assertTrue(value["baseline_complete"])
        self.assertTrue(all(row["execution_status"] == "complete"
                            for row in value["branch_metrics"]))
        self.assertFalse(value["selected_capture_passed"])
        self.assertEqual(m.route_for(self.stage, True, True, True, value,
                                     True, False), self.stage["routes"]["no_capture"])

    def test_route_requires_eligible_arm_replay_and_capture(self) -> None:
        good = {"passed": True}
        self.assertEqual(m.route_for(self.stage, True, True, True, good, True, True),
                         self.stage["routes"]["pass"])
        self.assertEqual(m.route_for(self.stage, True, True, True, good, False, True),
                         self.stage["routes"]["replay_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, True,
                                     {"passed": False}, True, False),
                         self.stage["routes"]["no_eligible_arm"])

    def test_independent_reconstructs_ten_streams(self) -> None:
        result = {"scientific_metrics": {"selected_arm_id": "k4r3"}}
        streams = mi.expected_streams(
            self.stage, self.cfg, self.targets, self.parent, result)
        self.assertEqual(len(streams), 10)
        self.assertEqual(streams[-1]["rollout_id"], "critical_replay")
        self.assertIn("branch__k4r3", [row["rollout_id"] for row in streams])

    def test_config_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        for mutate in (
                lambda value: value.update(maximum_rollouts=11),
                lambda value: value["candidate_specs"].append(
                    {"arm_id": "extra", "tokens": "HHHHHHHH"}),
                lambda value: value["measurement_gates"].update(
                    maximum_capture_source_rz_distance_m=0.026)):
            value = copy.deepcopy(original)
            mutate(value)
            with self.assertRaises(Exception):
                m._require(value)

    def test_launcher_has_independent_audit_and_no_resume(self) -> None:
        launcher = (m.ROOT / "run_rgeo_zgeo_1ms_id2z14_early_remaining_basis_capture.sh").read_text(
            encoding="utf-8")
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertNotIn("--resume", launcher)
        self.assertNotIn("retry", launcher.lower())


if __name__ == "__main__":
    unittest.main()
