from __future__ import annotations

import copy
import json
import unittest

from scripts import rgeo_zgeo_1ms_id2z11_bounded_capture_teacher as m
from scripts import rgeo_zgeo_1ms_id2z11_bounded_capture_teacher_independent as mi


class ID2Z11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.reference = m.load()

    def test_identity_budget_and_routes(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_rollouts"], 17)
        self.assertEqual(self.stage["maximum_advance_attempts"], 1309)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 6630)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(self.stage["fit_calibration_holdout_controller_expert_bc_dagger_rl_fixture_use"],
                         "forbidden")

    def test_state49_parent_and_reference_are_exact(self) -> None:
        self.assertGreaterEqual(len(self.parent["actions"]), 49)
        value = m.z6.prefix_check(self.reference, self.reference, 50, 49,
                                  self.stage["semantic_artifacts"])
        self.assertTrue(value["passed"], value)

    def test_signed_token_pairs_and_horizon(self) -> None:
        rows = m.build_matrix(self.stage, self.cfg, self.targets,
                              self.parent, 49, 0, "root")
        self.assertEqual([row["arm_id"] for row in rows], list(m.ARM_IDS))
        self.assertTrue(all(len(row["actions"]) == 77 for row in rows))
        by_arm = {row["arm_id"]: row for row in rows}
        base = by_arm["h8"]["actions"][49]["probe_virtual_action"]
        f = by_arm["f8"]["actions"][49]["probe_virtual_action"]
        u = by_arm["u4h4"]["actions"][49]["probe_virtual_action"]
        b = by_arm["b8"]["actions"][49]["probe_virtual_action"]
        p = by_arm["p4h4"]["actions"][49]["probe_virtual_action"]
        self.assertAlmostEqual(f[0] - base[0], 1.0)
        self.assertAlmostEqual(u[0] - base[0], -1.0)
        self.assertAlmostEqual(b[2] - base[2], -1.0)
        self.assertAlmostEqual(p[2] - base[2], 1.0)
        for row in rows:
            self.assertTrue(m.validate_stream(row, self.stage, self.cfg)["passed"])

    def test_all_root_main_sequences_are_statically_admissible(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_root_main_sequence_count"], 49)
        self.assertEqual(value["static_root_main_sequences_passed"], 49)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    def test_alternate_history_rule_is_nonnested(self) -> None:
        self.assertEqual(m.alternate_parent_arm("BBBBFFFF"), "f8")
        self.assertEqual(m.alternate_parent_arm("FFFFFFFF"), "b8")
        self.assertEqual(m.alternate_parent_arm("UUUUHHHH"), "b8")

    @staticmethod
    def _states(distance: float) -> list[dict]:
        values = []
        for index in range(78):
            values.append({"r_geo_m": 0.0 if index == 0 else distance,
                           "z_geo_m": 0.0, "ip_a": 1000.0})
        return values

    def _row(self, arm: str, distance: float) -> dict:
        tokens = next(row["tokens"] for row in self.stage["candidate_specs"]
                      if row["arm_id"] == arm)
        return {"rollout_id": arm, "arm_id": arm, "tokens": tokens,
                "passed": True, "states": self._states(distance),
                "actions": [{"expected_card15_fields": ["0"] * 14}
                            for _ in range(77)]}

    def test_metrics_require_capture_not_only_improvement(self) -> None:
        rows = [self._row("h8", 0.030)]
        rows.extend(self._row(arm, 0.026 + index * 0.0001)
                    for index, arm in enumerate(m.ARM_IDS[1:]))
        value = m._metrics(rows, self.stage, m.ARM_IDS)
        self.assertTrue(value["passed"])
        self.assertFalse(value["selected_capture_passed"])
        route = m.route_for(self.stage, True, True, True, value, value,
                            True, True, False)
        self.assertEqual(route, self.stage["routes"]["no_capture"])

    def test_route_requires_nonnested_support_replay_and_capture(self) -> None:
        good = {"passed": True}
        self.assertEqual(m.route_for(self.stage, True, True, True, good, good,
                                     True, True, True),
                         self.stage["routes"]["pass"])
        self.assertEqual(m.route_for(self.stage, True, True, True, good, good,
                                     False, True, True),
                         self.stage["routes"]["alternate_support_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, True, good, good,
                                     True, False, True),
                         self.stage["routes"]["replay_fail"])

    def test_independent_reconstructs_seventeen_streams(self) -> None:
        result = {"scientific_metrics": {"selected_root_arm_id": "f8",
                                          "selected_main_arm_id": "b4f4"}}
        streams, _ = mi.expected_streams(
            self.stage, self.cfg, self.targets, self.parent, result)
        self.assertEqual(len(streams), 17)
        self.assertEqual(streams[-1]["rollout_id"], "critical_replay")
        self.assertIn("alternate__b4f4", [row["rollout_id"] for row in streams])

    def test_config_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        for mutate in (
                lambda value: value.update(maximum_rollouts=18),
                lambda value: value["candidate_specs"].append(
                    {"arm_id": "extra", "tokens": "HHHHHHHH"}),
                lambda value: value["alternate_history_rule"].update(
                    otherwise_alternate_committed_tokens="FFFF")):
            value = copy.deepcopy(original)
            mutate(value)
            with self.assertRaises(Exception):
                m._require(value)

    def test_launcher_has_independent_audit_and_no_resume(self) -> None:
        launcher = (m.ROOT / "run_rgeo_zgeo_1ms_id2z11_bounded_capture_teacher.sh").read_text(
            encoding="utf-8")
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertNotIn("--resume", launcher)
        self.assertNotIn("retry", launcher.lower())


if __name__ == "__main__":
    unittest.main()
