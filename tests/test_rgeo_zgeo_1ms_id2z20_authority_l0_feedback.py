from __future__ import annotations

import copy
import inspect
import json
import math
import unittest
from pathlib import Path

from scripts import rgeo_zgeo_1ms_id2z20_authority_l0_feedback as m
from scripts import rgeo_zgeo_1ms_id2z20_authority_l0_feedback_independent as mi
from scripts import rgeo_zgeo_1ms_id2z20_reporting_recovery as recovery


ROOT = Path(__file__).resolve().parents[1]


class ID2Z20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.evidence, cls.dev, cls.validation = m.load()
        cls.dev_center = m.root_targets(cls.dev, cls.cfg, "test")[-1]

    def test_identity_hash_budget_and_data_roles(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_rollouts"], 23)
        self.assertEqual(self.stage["maximum_advance_attempts"], 1495)
        self.assertEqual(self.stage["maximum_retained_states"], 1518)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 7590)
        self.assertEqual(self.stage["phase_a"]["development_rollout_count"], 17)
        self.assertEqual(self.stage["phase_b"]["maximum_policy_rollouts"], 2)
        self.assertEqual(self.stage["phase_c"]["maximum_rollouts"], 4)
        self.assertEqual(self.stage["phase_c"]["fit_weight"], 0)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)

    def test_rank_four_exact_card15_basis(self) -> None:
        value = m.basis_geometry(self.stage, self.dev_center, self.cfg)
        self.assertTrue(value["passed"], value)
        self.assertEqual(value["rank"], 4)
        self.assertLessEqual(value["condition"], 5.0)
        self.assertAlmostEqual(value["maximum_absolute_component_a"], 0.3, places=12)
        self.assertEqual(value["coordinate_order"], ["b0", "b1", "b2", "b3"])

    def test_phase_a_population_pulse_return_and_tail(self) -> None:
        rows = m.phase_a_specs(self.stage, self.dev, self.cfg)
        self.assertEqual(len(rows), 17)
        self.assertEqual(len({row["rollout_id"] for row in rows}), 17)
        center = rows[0]["targets"][31].card15_fields
        self.assertTrue(all(target.card15_fields == center for target in rows[0]["targets"][32:]))
        for row in rows[1:]:
            issue = row["phase_issue"]
            self.assertNotEqual(row["targets"][issue].card15_fields, center)
            self.assertEqual(row["targets"][issue + 1].card15_fields, center)
            self.assertTrue(all(target.card15_fields == center
                                for target in row["targets"][issue + 1:]))

    def test_compact_boundary_removes_non_json_card15_targets(self) -> None:
        spec = m.phase_a_specs(self.stage, self.dev, self.cfg)[0]
        compact = m.compact_spec(spec)
        self.assertNotIn("targets", compact)
        json.dumps(compact, allow_nan=False)

    def test_reporting_recovery_freezes_exact_completed_hold(self) -> None:
        metadata, actions = recovery.frozen_actions(
            self.stage, self.cfg, self.dev)
        self.assertEqual(metadata["rollout_id"], "dev_hold")
        self.assertNotIn("targets", metadata)
        self.assertEqual(len(actions), 65)
        self.assertEqual([row["issue_step"] for row in actions], list(range(65)))
        self.assertTrue(all(row["maximum_issued_delta_a"] <= .3000000001
                            for row in actions))
        source = inspect.getsource(m.resume_completed_dev_hold)
        self.assertIn("initial_reporting_failure_result.json", source)
        self.assertIn("recovered_completed_rollouts", source)
        self.assertNotIn("runner.reset", source)

    def test_offline_is_zero_plant_and_all_arms_admissible(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value)
        self.assertTrue(value["basis_geometry"]["passed"])
        self.assertEqual(len(value["static_arm_checks"]), 18)
        self.assertTrue(all(row["passed"] for row in value["static_arm_checks"]))
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        mutations = (
            lambda value: value.update(maximum_rollouts=24),
            lambda value: value["basis_coordinates"].pop(),
            lambda value: value["phase_b"].update(arm_order=list(reversed(m.ARM_IDS))),
            lambda value: value["action_semantics"].update(odd_symmetry_assumed=True),
            lambda value: value["data_contract"].update(phase_c_fit_weight=1),
            lambda value: value.update(models_fit_or_updated=1),
        )
        for mutate in mutations:
            changed = copy.deepcopy(original); mutate(changed)
            with self.assertRaises(Exception):
                m._require(changed)

    @staticmethod
    def _state(r: float, z: float, ip: float = 1000.0) -> dict:
        return {"r_geo_m": r, "z_geo_m": z, "ip_a": ip}

    def test_selector_uses_current_truth_and_frozen_response_only(self) -> None:
        arms = m.basis_targets(self.stage, self.dev_center, self.cfg, "selector")
        empty = {arm: {"response_displacement": [0.0, 0.0, 0.0],
                       "response_velocity_m_per_s": [0.0, 0.0]}
                 for arm in m.ARM_IDS}
        empty["b0_plus"] = {"response_displacement": [0.001, 0.0, 0.0],
                            "response_velocity_m_per_s": [-0.2, 0.0]}
        cell = {"baseline_displacement": [0.0, 0.0, 0.0],
                "baseline_velocity_change_m_per_s": [0.0, 0.0], "arms": empty}
        library = {"phases": {"32": {"4": cell, "8": cell},
                              "40": {"4": cell, "8": cell}}}
        source = self._state(0.0, 0.0)
        previous = self._state(-.021, 0.0)
        current = self._state(-.020, 0.0)
        arm, decision = m.select_arm(self.stage, library, current, previous, source,
                                     32, 4, arms, self.dev_center)
        self.assertEqual(arm, "b0_plus")
        self.assertEqual(decision["response_phase_issue"], 32)
        # No future state or family/role label is accepted by the selector API.
        self.assertNotIn("future", inspect.signature(m.select_arm).parameters)
        self.assertNotIn("family", inspect.signature(m.select_arm).parameters)

    def _trajectory(self, distance: float, speed: float, ip_fraction: float) -> dict:
        source = self._state(0.0, 0.0, 1000.0)
        states = [dict(source) for _ in range(66)]
        for index in range(59, 66):
            states[index] = self._state(distance + (index - 65) * speed * .001, 0.0,
                                        1000.0 * (1.0 + ip_fraction))
        actions = [{"arm_id": "hold", "expected_card15_fields": ["x"]} for _ in range(65)]
        return {"passed": True, "states": states, "actions": actions}

    def test_capture_and_utility_gates_are_distinct(self) -> None:
        hold = self._trajectory(.030, .20, .01)
        candidate = self._trajectory(.029, .14, .01)
        candidate["actions"][32]["arm_id"] = "b0_plus"
        utility = m.utility_metrics(candidate, hold, self.stage)
        self.assertTrue(utility["passed"], utility)
        self.assertFalse(utility["candidate"]["capture_passed"])
        captured = self._trajectory(.024, .09, .01)
        self.assertTrue(m.terminal_metrics(captured, self.stage)["capture_passed"])

    def test_route_precedence_and_claim_levels(self) -> None:
        routes = self.stage["routes"]
        self.assertEqual(m._route(self.stage, False, False, False, False, False, False, False),
                         routes["execution_or_interface_fail"])
        self.assertEqual(m._route(self.stage, True, False, True, True, True, True, True),
                         routes["raw_integrity_fail"])
        self.assertEqual(m._route(self.stage, True, True, False, True, True, True, True),
                         routes["phase_a_signal_or_geometry_fail"])
        self.assertEqual(m._route(self.stage, True, True, True, False, True, True, True),
                         routes["phase_b_no_utility"])
        self.assertEqual(m._route(self.stage, True, True, True, True, False, True, True),
                         routes["replay_fail"])
        self.assertEqual(m._route(self.stage, True, True, True, True, True, False, True),
                         routes["validation_or_finite_return_fail"])
        self.assertEqual(m._route(self.stage, True, True, True, True, True, True, False),
                         routes["authority_pass_no_capture"])
        self.assertEqual(m._route(self.stage, True, True, True, True, True, True, True),
                         routes["authority_and_capture_pass"])

    def test_finite_return_is_not_recovery(self) -> None:
        hold = self._trajectory(.02, .08, .01)
        returned = copy.deepcopy(hold)
        returned["actions"][-1]["expected_card15_fields"] = ["center"]
        hold["actions"][-1]["expected_card15_fields"] = ["center"]
        value = m.finite_return_metrics(returned, hold, self.stage)
        self.assertTrue(value["passed"], value)
        self.assertTrue(value["final_active_target_returned_to_center"])
        self.assertIn("not", self.stage["claim_boundary"].lower())
        self.assertIn("Recourse-L1", self.stage["claim_boundary"])

    def test_independent_and_launcher_contract(self) -> None:
        self.assertIn("independent-raw", mi.SCHEMA)
        source = inspect.getsource(mi.audit)
        self.assertIn("z9i._raw_rows", source)
        self.assertIn("action_checks", source)
        self.assertIn("models_fit_or_updated", source)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z20_authority_l0_feedback.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z20_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z20_OUTPUT", launcher)
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
