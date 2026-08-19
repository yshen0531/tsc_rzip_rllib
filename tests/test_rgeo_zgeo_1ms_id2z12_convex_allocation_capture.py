from __future__ import annotations

import copy
from decimal import Decimal
import json
import unittest

from scripts import rgeo_zgeo_1ms_id2z12_convex_allocation_capture as m
from scripts import rgeo_zgeo_1ms_id2z12_convex_allocation_capture_independent as mi


class ID2Z12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.reference = m.load()

    def test_identity_budget_and_routes(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_rollouts"], 19)
        self.assertEqual(self.stage["maximum_advance_attempts"], 1463)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 7410)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(
            self.stage["fit_calibration_holdout_controller_expert_bc_dagger_rl_fixture_use"],
            "forbidden")

    def test_selected_parent_matches_bound_id2z11_replay(self) -> None:
        self.assertTrue(m._planned_matches_replay(self.parent, self.reference))
        self.assertEqual(len(self.parent["actions"]), 77)
        self.assertEqual(len(self.reference["states"]), 78)

    def test_allocation_matrix_is_exact_and_statically_admissible(self) -> None:
        rows = m.build_matrix(self.stage, self.cfg, self.targets,
                              self.parent, 61, 0, "root")
        self.assertEqual([row["arm_id"] for row in rows], list(m.ARM_IDS))
        for row in rows:
            self.assertLessEqual(abs(Decimal(row["alpha_b"]))
                                 + abs(Decimal(row["alpha_f"])), Decimal("1"))
            self.assertTrue(m.validate_stream(row, self.stage, self.cfg)["passed"])
            self.assertEqual(len(row["actions"]), 77)

    def test_half_allocation_is_card15_midpoint_and_virtual_state(self) -> None:
        rows = {row["arm_id"]: row for row in m.build_matrix(
            self.stage, self.cfg, self.targets, self.parent, 61, 0, "root")}
        base = rows["hold4"]["actions"][61]["probe_virtual_action"]
        bf = rows["bf4"]["actions"][61]["probe_virtual_action"]
        self.assertAlmostEqual(bf[0] - base[0], 0.5)
        self.assertAlmostEqual(bf[2] - base[2], -0.5)
        self.assertLessEqual(rows["bf4"]["actions"][61]["maximum_issued_delta_a"], 0.3)
        self.assertEqual(rows["bf4"]["actions"][65]["maximum_issued_delta_a"], 0.0)

    def test_full_root_main_matrix_is_statically_admissible(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_root_main_sequence_count"], 81)
        self.assertEqual(value["static_root_main_sequences_passed"], 81)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _states(distance: float, speed: float = 0.0) -> list[dict]:
        values = []
        for index in range(78):
            position = distance + (index - 72) * speed * 0.001 if index >= 72 else distance
            values.append({"r_geo_m": 0.0 if index == 0 else position,
                           "z_geo_m": 0.0, "ip_a": 1000.0})
        return values

    def _row(self, arm: str, distance: float, speed: float = 0.0) -> dict:
        spec = next(row for row in self.stage["candidate_specs"]
                    if row["arm_id"] == arm)
        return {"rollout_id": arm, "arm_id": arm,
                "alpha_b": spec["alpha_b"], "alpha_f": spec["alpha_f"],
                "passed": True, "states": self._states(distance, speed),
                "actions": [{"expected_card15_fields": ["0"] * 14}
                            for _ in range(77)]}

    def test_metrics_require_capture_not_only_improvement(self) -> None:
        rows = [self._row("hold4", 0.030)]
        rows.extend(self._row(arm, 0.026 + index * 0.0001)
                    for index, arm in enumerate(m.ARM_IDS[1:]))
        value = m._metrics(rows, self.stage)
        self.assertTrue(value["passed"])
        self.assertFalse(value["selected_capture_passed"])
        route = m.route_for(self.stage, True, True, True, value, value,
                            True, False)
        self.assertEqual(route, self.stage["routes"]["no_capture"])

    def test_route_requires_rounds_replay_and_capture(self) -> None:
        good = {"passed": True}
        self.assertEqual(m.route_for(self.stage, True, True, True, good, good,
                                     True, True), self.stage["routes"]["pass"])
        self.assertEqual(m.route_for(self.stage, True, True, True, good, good,
                                     False, True), self.stage["routes"]["replay_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, True, good,
                                     {"passed": False}, True, False),
                         self.stage["routes"]["round_no_eligible_arm"])

    def test_independent_reconstructs_nineteen_streams(self) -> None:
        result = {"scientific_metrics": {"selected_root_arm_id": "bf4",
                                          "selected_main_arm_id": "pf4"}}
        streams = mi.expected_streams(
            self.stage, self.cfg, self.targets, self.parent, result)
        self.assertEqual(len(streams), 19)
        self.assertEqual(streams[-1]["rollout_id"], "critical_replay")
        self.assertIn("main__pf4", [row["rollout_id"] for row in streams])

    def test_config_and_hull_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        for mutate in (
                lambda value: value.update(maximum_rollouts=20),
                lambda value: value["candidate_specs"].append(
                    {"arm_id": "extra", "alpha_b": "0", "alpha_f": "0"}),
                lambda value: value["measurement_gates"].update(
                    maximum_capture_source_rz_distance_m=0.026)):
            value = copy.deepcopy(original)
            mutate(value)
            with self.assertRaises(Exception):
                m._require(value)
        with self.assertRaises(Exception):
            m._allocation_delta(self.targets["q0"], self.targets, self.cfg,
                                Decimal("0.75"), Decimal("0.5"), "bad")

    def test_launcher_has_independent_audit_and_no_resume(self) -> None:
        launcher = (m.ROOT / "run_rgeo_zgeo_1ms_id2z12_convex_allocation_capture.sh").read_text(
            encoding="utf-8")
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertNotIn("--resume", launcher)
        self.assertNotIn("retry", launcher.lower())


if __name__ == "__main__":
    unittest.main()
