from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


primary = _module(
    "id2z7", "scripts/rgeo_zgeo_1ms_id2z7_branch_continuation.py")
independent = _module(
    "id2z7_independent",
    "scripts/rgeo_zgeo_1ms_id2z7_branch_continuation_independent.py")


class ID2Z7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(primary.CONFIG.read_text(encoding="utf-8"))

    def test_identity_budget_hash_and_data_roles(self) -> None:
        primary._require(self.stage)
        self.assertEqual(
            primary.CONFIG_SHA256, primary.z6.z5.base.sha256(primary.CONFIG))
        self.assertEqual(self.stage["maximum_rollouts"], 11)
        self.assertEqual(self.stage["maximum_advance_attempts"], 11 * 69)
        self.assertEqual(self.stage["maximum_retained_states"], 11 * 70)
        self.assertEqual(
            self.stage["required_artifact_files_if_all_complete"], 11 * 70 * 5)
        self.assertEqual(
            self.stage["interrupted_id2z6_round1_fit_and_selection_weight"], 0)
        self.assertEqual(self.stage["critical_replay_fit_weight"], 0)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        mutations = (
            (("candidate_specs", 3, "tokens"), "BFFF"),
            (("action_semantics", "maximum_per_coil_issue_delta_a"), 0.31),
            (("empirical_exploration", "outer_hard_envelope", "r_geo_m"), 0.06),
            (("measurement_gates", "terminal_state_indices"), list(range(63, 69))),
            (("prefix_gates", "sprsina_hash_is_diagnostic_only"), False),
            (("storage_gate", "minimum_free_bytes_after_estimate"), 0),
            (("routes", "pass"), "WEAKENED"),
        )
        for path, value in mutations:
            changed = copy.deepcopy(self.stage)
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(
                    primary.z6.z5.z3.z1.y1r1.y1.x1.InputIntegrityError):
                primary._require(changed)

    def test_external_round0_is_fixed_and_interrupted_round1_is_not_read(self) -> None:
        (stage, z6_stage, cfg, targets, _, external, parent,
         parent_compact, z6_result) = primary.load()
        self.assertEqual([row["arm_id"] for row in external], list(primary.ARM_IDS))
        self.assertTrue(all(row["passed"] for row in external))
        self.assertEqual(sum(row["fit_weight"] for row in external), 5)
        self.assertEqual(parent["arm_id"], "f4")
        self.assertEqual(parent_compact["arm_id"], "f4")
        self.assertEqual(z6_result["selected_three_macro_sequence"], ["f4"])
        self.assertNotIn("id2z6_round1", set(stage["evidence"]))
        streams = primary.fresh_round_streams(z6_stage, cfg, targets, parent, 1)
        self.assertEqual([row["arm_id"] for row in streams], list(primary.ARM_IDS))
        self.assertTrue(all(
            primary.z6.validate_stream(row, z6_stage, cfg, targets)["passed"]
            for row in streams))

    def test_all_twenty_five_fresh_two_round_sequences_are_static_admissible(self) -> None:
        _, z6_stage, cfg, targets, _, _, parent, _, _ = primary.load()
        checks = primary._static_matrix(z6_stage, cfg, targets, parent)
        self.assertEqual(len(checks), 25)
        self.assertTrue(all(row["passed"] for row in checks), checks)

    def test_offline_is_zero_plant_and_zero_model(self) -> None:
        result = primary.offline(primary.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["static_two_round_sequence_count"], 25)
        self.assertEqual(result["static_two_round_sequences_passed"], 25)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_run_root_is_set_before_rollout_and_isolated(self) -> None:
        _, z6_stage, cfg, targets, _, _, parent, parent_compact, _ = primary.load()
        output = ROOT / ".codex_tmp" / f"id2z7_test_{uuid.uuid4().hex}"
        output.mkdir(parents=True)
        try:
            isolation = primary.configure_run_root(cfg, output)
            expected_root = (output / "rollouts").resolve()
            streams = primary.fresh_round_streams(
                z6_stage, cfg, targets, parent, 1)

            def fake_one_rollout(fake_cfg, _stage, stream, _reference,
                                 runner_cls=None):
                self.assertEqual(Path(fake_cfg.run_root).resolve(), expected_root)
                marker = expected_root / stream["rollout_id"] / "constructed.marker"
                marker.parent.mkdir(parents=True)
                marker.write_text("server fake runner", encoding="utf-8")
                return {
                    "rollout_id": stream["rollout_id"],
                    "candidate_id": stream["candidate_id"],
                    "arm_id": stream["arm_id"],
                    "round_index": stream["round_index"],
                    "fit_weight": stream["fit_weight"],
                    "passed": False,
                    "reasons": ["FAKE_STOP"],
                    "states": [],
                    "actions": [],
                    "reset_calls": 0,
                    "advance_attempts": 0,
                    "plant_advance_gotsc_calls": 0,
                    "verified_plant_advances": 0,
                }

            with mock.patch.object(primary.z6, "one_rollout", fake_one_rollout):
                row = primary.execute_row(
                    cfg, z6_stage, streams[0], parent_compact,
                    "test-revision", output)
            self.assertEqual(row["schema_version"], primary.SCHEMA)
            self.assertTrue((expected_root / streams[0]["rollout_id"] /
                             "constructed.marker").is_file())
            self.assertEqual(isolation["required_run_root"], str(expected_root))
        finally:
            shutil.rmtree(output)

    def test_run_root_rejects_output_outside_repository(self) -> None:
        _, _, cfg, _, _, _, _, _, _ = primary.load()
        with self.assertRaises(
                primary.z6.z5.z3.z1.y1r1.y1.x1.InputIntegrityError):
            primary.configure_run_root(cfg, ROOT.parent / "forbidden_id2z7_output")

    def test_route_precedence_and_data_gate(self) -> None:
        rounds = [{"passed": True}, {"passed": True}]
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
        no_data = copy.deepcopy(science)
        no_data["development_data_ready"] = False
        self.assertEqual(primary.route_for(
            self.stage, True, True, True, rounds, no_data),
            self.stage["routes"]["teacher_progress_data_insufficient"])
        self.assertEqual(primary.route_for(
            self.stage, True, True, True, rounds, science),
            self.stage["routes"]["pass"])

    def test_independent_audit_and_launcher_bind_fresh_continuation(self) -> None:
        self.assertEqual(
            independent.SCHEMA, "rgeo-zgeo-1ms-id2z7-independent-raw-v1")
        source = inspect.getsource(independent.audit)
        self.assertIn("z6i._raw_rows", source)
        self.assertIn("parent_prefix", source)
        self.assertIn("RUN_ROOT_ISOLATION", source)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z7_branch_continuation.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z7_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z7_OUTPUT", launcher)
        self.assertIn("branch_continuation_independent.py", launcher)
        self.assertIn("test ! -e", launcher)


if __name__ == "__main__":
    unittest.main()
