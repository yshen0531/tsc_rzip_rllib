from __future__ import annotations

import copy
import inspect
import json
import math
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock

from scripts import rgeo_zgeo_1ms_id2z23_moving_nominal_discrete_vertex_campaign as m
from scripts import rgeo_zgeo_1ms_id2z23_moving_nominal_discrete_vertex_campaign_independent as mi


ROOT = Path(__file__).resolve().parents[1]


class ID2Z23Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.baseline = m.load()
        cls.streams = m.build_streams(cls.stage, cls.cfg, cls.targets, cls.parent)

    def test_identity_budget_roles_and_hashes(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(len(self.streams), 10)
        self.assertEqual(self.stage["maximum_reset_calls"], 10)
        self.assertEqual(self.stage["maximum_advance_attempts"], 650)
        self.assertEqual(self.stage["maximum_gotsc_calls"], 650)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 3300)
        self.assertEqual(sum(row["fit_weight"] for row in self.streams), 9)
        self.assertEqual(sum(row["data_role"] == "replay" for row in self.streams), 1)

    def test_stream_matrix_prefix_replacement_resume_and_tail(self) -> None:
        baseline = self.streams[0]
        self.assertEqual(baseline["rollout_id"], "baseline_full_f")
        for stream in self.streams:
            check = m.validate_stream(stream, self.stage, self.cfg)
            self.assertTrue(check["passed"], check)
            self.assertEqual(len(stream["actions"]), 65)
            self.assertEqual(len(stream["targets"]), 65)
            self.assertLessEqual(max(float(row["maximum_issued_delta_a"])
                                     for row in stream["actions"]), .3000000001)
            decision = stream["phase_issue"]
            if decision is not None:
                self.assertEqual(
                    [row["expected_card15_fields"] for row in stream["actions"][:decision]],
                    [row["expected_card15_fields"] for row in baseline["actions"][:decision]])
                self.assertEqual(stream["non_nominal_issue_steps"],
                                 list(range(decision, decision + 4)))
            for issue in range(48, 65):
                self.assertEqual(stream["actions"][issue]["expected_card15_fields"],
                                 stream["actions"][47]["expected_card15_fields"])

    def test_replay_stream_is_exact_and_zero_weight(self) -> None:
        source = next(row for row in self.streams
                      if row["rollout_id"] == "issue24__p05_plus4")
        replay = self.streams[-1]
        self.assertEqual(replay["source_family_id"], source["family_id"])
        self.assertEqual(replay["fit_weight"], 0)
        self.assertEqual(replay["targets"], source["targets"])
        self.assertEqual(replay["actions"], source["actions"])

    def test_offline_is_zero_plant_and_all_streams_pass(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value)
        self.assertEqual(len(value["stream_checks"]), 10)
        self.assertTrue(all(row["passed"] for row in value["stream_checks"]))
        self.assertEqual(value["reset_calls"], 0)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)
        self.assertEqual(value["models_fit_or_updated"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        mutations = (
            lambda value: value.update(maximum_rollouts=11),
            lambda value: value["development_specs"][1].update(phase_issue=25),
            lambda value: value["replay_specs"][0].update(fit_weight=1),
            lambda value: value["action_semantics"].update(add_then_clip=True),
            lambda value: value.update(models_fit_or_updated=1),
        )
        for mutate in mutations:
            changed = copy.deepcopy(original); mutate(changed)
            with self.assertRaises(Exception):
                m._require(changed)

    @staticmethod
    def _state(r: float, z: float, ip: float = 1000.0) -> dict:
        return {"r_geo_m": r, "z_geo_m": z, "ip_a": ip}

    def _synthetic_rows(self) -> list[dict]:
        rows = []
        baseline_states = [self._state(index * 1e-4, 0.0) for index in range(66)]
        baseline = {"family_id": "baseline_full_f", "passed": True,
                    "states": baseline_states, "actions": []}
        rows.append(baseline)
        directions = ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))
        for phase in (24, 32):
            for vertex, direction in zip(self.stage["selected_vertex_ids"], directions):
                states = copy.deepcopy(baseline_states)
                for horizon in range(1, 66 - phase):
                    scale = 0.00003 * horizon
                    states[phase + horizon] = self._state(
                        baseline_states[phase + horizon]["r_geo_m"] + direction[0] * scale,
                        direction[1] * scale)
                rows.append({"family_id": f"issue{phase}__{vertex}", "passed": True,
                             "states": states, "actions": []})
        replay = copy.deepcopy(next(row for row in rows
                                    if row["family_id"] == "issue24__p05_plus4"))
        replay["family_id"] = "replay_issue24__p05_plus4"
        rows.append(replay)
        return rows

    def test_scientific_metrics_require_both_phases_and_exact_replay(self) -> None:
        rows = self._synthetic_rows()
        value = m.scientific_metrics(rows, self.stage)
        self.assertTrue(value["passed"], value)
        self.assertEqual([row["phase_issue"] for row in value["phase_metrics"]], [24, 32])
        self.assertTrue(all(row["passed"] for row in value["phase_metrics"]))
        bad = copy.deepcopy(rows)
        bad[-1]["states"][10]["r_geo_m"] += 1e-6
        self.assertFalse(m.scientific_metrics(bad, self.stage)["passed"])

    def test_fail_fast_and_counter_budget(self) -> None:
        output = ROOT / ".codex_tmp" / f"id2z23_failfast_{uuid.uuid4().hex}"
        output.mkdir(parents=True)
        calls = []
        try:
            def fake_execute(*args, **kwargs):
                stream = args[3]; calls.append(stream["rollout_id"])
                return {"rollout_id": stream["rollout_id"],
                        "family_id": stream["family_id"], "fit_weight": stream["fit_weight"],
                        "passed": False, "states": [], "actions": [],
                        "reset_calls": 1, "advance_attempts": 1,
                        "plant_advance_gotsc_calls": 1, "verified_plant_advances": 0,
                        "reasons": ["FAKE_STOP"]}
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": "empty",
                         "missing_required_artifacts": []}
            with (mock.patch.object(m.z7, "configure_run_root", return_value={"passed": True}),
                  mock.patch.object(m, "_execute_row", fake_execute),
                  mock.patch.object(m.z6, "prefix_check", return_value={"passed": True}),
                  mock.patch.object(m.io, "raw_inventory", return_value=inventory),
                  mock.patch.object(m.io, "write_new")):
                value = m.execute(self.stage, self.runtime, self.cfg, self.targets,
                                  self.parent, self.baseline, "test", output,
                                  {"passed": True})
            self.assertEqual(calls, ["baseline_full_f"])
            self.assertEqual(value["rollouts_started"], 1)
            self.assertEqual(value["route"], self.stage["routes"][
                "execution_or_interface_fail"])
        finally:
            shutil.rmtree(output)

    def test_failure_finalizer_preserves_partial_counters(self) -> None:
        output = ROOT / ".codex_tmp" / f"id2z23_finalizer_{uuid.uuid4().hex}"
        output.mkdir(parents=True)
        try:
            row = {"rollout_id": "baseline_full_f", "passed": False,
                   "states": [], "reset_calls": 1, "advance_attempts": 3,
                   "plant_advance_gotsc_calls": 3, "verified_plant_advances": 2}
            (output / "baseline_full_f.json").write_text(json.dumps(row), encoding="utf-8")
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": "empty",
                         "missing_required_artifacts": []}
            with mock.patch.object(m.io, "raw_inventory", return_value=inventory):
                value = m._failure_result(self.stage, "test", output,
                                          {"passed": True}, RuntimeError("boom"))
            self.assertEqual(value["advance_attempts"], 3)
            self.assertEqual(value["verified_plant_advances"], 2)
            self.assertEqual(value["rollouts_started"], 1)
            self.assertIn("RuntimeError:boom", value["failure"])
        finally:
            shutil.rmtree(output)

    def test_independent_and_launcher_contract(self) -> None:
        self.assertEqual(mi.SCHEMA, "rgeo-zgeo-1ms-id2z23-independent-raw-v1")
        source = inspect.getsource(mi.audit)
        self.assertIn("z9i._raw_rows", source)
        self.assertIn("scientific_metrics(raw_rows", source)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z23_moving_nominal_discrete_vertex_campaign.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z23_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z23_OUTPUT", launcher)
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
