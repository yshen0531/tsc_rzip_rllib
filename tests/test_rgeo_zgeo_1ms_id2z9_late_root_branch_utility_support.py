from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts import rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support as m


class ID2Z9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.reference = m.load()

    def test_identity_budget_and_data_roles(self) -> None:
        self.assertEqual(m.z6.z5.z3.z1.y1r1.y1.x1.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_rollouts"], 11)
        self.assertEqual(self.stage["maximum_advance_attempts"], 847)
        self.assertEqual(self.stage["new_complete_fit_weight_windows_required"], 10)
        self.assertEqual(self.stage["critical_replay_fit_weight"], 0)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)

    def test_selected_parent_is_exact_id2z7_prefix(self) -> None:
        self.assertEqual(len(self.parent["actions"]), 69)
        self.assertEqual(len(self.reference["states"]), 70)
        self.assertEqual([row["expected_card15_fields"] for row in self.parent["actions"]],
                         [row["expected_card15_fields"] for row in self.reference["actions"]])

    def test_all_twenty_five_sequences_are_statically_admissible(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_two_round_sequence_count"], 25)
        self.assertEqual(value["static_two_round_sequences_passed"], 25)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    def test_round_streams_share_prefix_and_end_at_state77(self) -> None:
        first = m.build_round_streams(
            self.stage, self.runtime, self.cfg, self.targets, self.parent, 0)
        self.assertEqual([row["arm_id"] for row in first], list(m.ARM_IDS))
        self.assertTrue(all(len(row["actions"]) == 77 for row in first))
        for row in first:
            self.assertEqual(row["actions"][:61], self.parent["actions"][:61])
        second = m.build_round_streams(
            self.stage, self.runtime, self.cfg, self.targets, first[3], 1)
        for row in second:
            self.assertEqual(row["actions"][:65], first[3]["actions"][:65])

    def test_route_requires_both_rounds_utility_replay_and_data(self) -> None:
        rounds = [{"passed": True}, {"passed": True}]
        good = {"teacher_utility_passed": True,
                "five_context_development_ready": True,
                "critical_replay_check": {"passed": True}}
        self.assertEqual(m.route_for(self.stage, True, True, True, rounds, good),
                         self.stage["routes"]["pass"])
        for key in ("teacher_utility_passed", "five_context_development_ready"):
            bad = copy.deepcopy(good); bad[key] = False
            self.assertNotEqual(m.route_for(self.stage, True, True, True, rounds, bad),
                                self.stage["routes"]["pass"])

    def test_run_root_isolation_is_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=m.ROOT / ".codex_tmp") as name:
            output = Path(name) / "new-output"
            cfg = SimpleNamespace(run_root=Path("forbidden"))
            value = m.z7.configure_run_root(cfg, output)
            self.assertTrue(value["passed"])
            self.assertEqual(Path(cfg.run_root).resolve(), (output / "rollouts").resolve())

    def test_contract_mutation_fails_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        for mutate in (
                lambda value: value.update(maximum_rollouts=12),
                lambda value: value["measurement_gates"].update(
                    minimum_round_score_improvement_over_hold=0.0),
                lambda value: value["candidate_specs"][0].update(fit_weight=0)):
            value = copy.deepcopy(original); mutate(value)
            with tempfile.NamedTemporaryFile("w", suffix=".json", dir=m.ROOT / ".codex_tmp",
                                             delete=False, encoding="utf-8") as handle:
                json.dump(value, handle); path = Path(handle.name)
            try:
                with self.assertRaises(Exception):
                    m.load(path)
            finally:
                path.unlink(missing_ok=True)

    def test_launcher_has_no_resume_or_retry(self) -> None:
        value = (m.ROOT / "run_rgeo_zgeo_1ms_id2z9_late_root_branch_utility_support.sh").read_text()
        self.assertIn("independent_raw_audit.json", value)
        self.assertNotIn("--resume", value)
        self.assertNotIn("retry", value.lower())

    def test_execution_failure_finalizer_preserves_partial_inventory(self) -> None:
        with tempfile.TemporaryDirectory(dir=m.ROOT / ".codex_tmp") as name:
            output = Path(name)
            (output / "r00__hold4.json").write_text(json.dumps({
                "rollout_id": "r00__hold4", "passed": False,
                "reset_calls": 1, "advance_attempts": 7,
                "plant_advance_gotsc_calls": 7, "verified_plant_advances": 6,
            }), encoding="utf-8")
            inventory = {
                "required_artifact_files": 35,
                "required_artifact_bytes": 123,
                "required_artifact_inventory_sha256": "ab" * 32,
                "missing_required_artifacts": ["partial/state/file"],
            }
            with mock.patch.object(
                    m.z6.z5.z3.z1.y1r1.y1.x1, "raw_inventory",
                    return_value=inventory):
                value = m._failure_result(
                    self.stage, "test-revision", output, {"passed": True},
                    RuntimeError("boom"))
            self.assertEqual(value["fresh_rollouts_completed"], 1)
            self.assertEqual(value["advance_attempts"], 7)
            self.assertEqual(value["verified_plant_advances"], 6)
            self.assertEqual(value["missing_required_artifacts"],
                             ["partial/state/file"])
            self.assertEqual(value["route"],
                             self.stage["routes"]["execution_or_interface_fail"])


if __name__ == "__main__":
    unittest.main()
