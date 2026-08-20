from __future__ import annotations

import copy
import inspect
import itertools
import json
import math
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock

from scripts import rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign as m
from scripts import rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign_independent as mi


ROOT = Path(__file__).resolve().parents[1]


class ID2Z27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.preflight, cls.baseline = m.load()
        cls.streams = m.build_streams(
            cls.stage, cls.cfg, cls.preflight, cls.baseline)

    def test_identity_budget_roles_and_hashes(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(len(self.streams), 11)
        self.assertEqual(self.stage["maximum_reset_calls"], 11)
        self.assertEqual(self.stage["maximum_advance_attempts"], 803)
        self.assertEqual(self.stage["maximum_gotsc_calls"], 803)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 4070)
        self.assertEqual(sum(row["fit_weight"] for row in self.streams), 9)
        self.assertEqual(sum(row["kind"] == "replay" for row in self.streams), 1)
        self.assertEqual(sum(row["kind"] == "full_f_diagnostic" for row in self.streams), 1)

    def test_exact_stream_matrix_bridge_and_tail(self) -> None:
        centered = self.streams[0]
        for stream in self.streams:
            check = m.validate_stream(stream, self.stage, self.cfg)
            self.assertTrue(check["passed"], check)
            self.assertEqual(len(stream["actions"]), 73)
            self.assertLessEqual(check["maximum_issued_delta_a"], .3000000001)
            if stream["kind"] in ("output_aligned_branch", "replay"):
                phase = int(stream["phase_issue"])
                self.assertEqual(
                    [row["expected_card15_fields"] for row in stream["actions"][:phase]],
                    [row["expected_card15_fields"] for row in centered["actions"][:phase]])
                self.assertEqual(stream["actions"][phase + 15]["expected_card15_fields"],
                                 centered["actions"][phase + 15]["expected_card15_fields"])
                self.assertEqual(stream["non_nominal_issue_steps"],
                                 list(range(phase, phase + 16)))

    def test_replay_is_exact_and_zero_weight(self) -> None:
        source = next(row for row in self.streams
                      if row["rollout_id"] == "issue32__q_z__plus_then_return")
        replay = self.streams[-1]
        self.assertEqual(replay["source_family_id"], source["family_id"])
        self.assertEqual(replay["fit_weight"], 0)
        self.assertEqual(replay["targets"], source["targets"])
        self.assertEqual(replay["actions"], source["actions"])

    def test_offline_is_zero_plant_and_all_streams_pass(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value)
        self.assertEqual(len(value["stream_checks"]), 11)
        self.assertTrue(all(row["passed"] for row in value["stream_checks"]))
        self.assertEqual(value["reset_calls"], 0)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)
        self.assertEqual(value["models_fit_or_updated"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        mutations = (
            lambda value: value.update(maximum_rollouts=12),
            lambda value: value["rollout_specs"][2].update(phase_issue=33),
            lambda value: value["rollout_specs"][-1].update(fit_weight=1),
            lambda value: value["data_contract"].update(id2z25_fit_weight=1),
            lambda value: value["data_contract"].update(d0_requires_capture=True),
        )
        for mutate in mutations:
            changed = copy.deepcopy(original)
            mutate(changed)
            with self.assertRaises(Exception):
                m._require(changed)

    @staticmethod
    def _state(r: float, z: float, ip: float = 1000.0) -> dict:
        return {"time_ms": 1100, "r_geo_m": r, "z_geo_m": z, "r_mid_m": r,
                "ip_a": ip, "actual_current_decimal_a_tsc": ["0"] * 14,
                "wire_current_a": [0.0] * 48,
                "active_command_card15_fields": ["0"] * 14,
                "artifact_sha256": {name: "same" for name in
                                    ("inputa", "geqdsk", "coil_currents.csv",
                                     "wire_currents.csv")}}

    def _synthetic_rows(self) -> list[dict]:
        baseline_states = [self._state(index * 1e-4, 0.0) for index in range(74)]
        rows = [{"family_id": "baseline_transition_center", "passed": True,
                 "states": baseline_states, "actions": []}]
        directions = [(1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)]
        for phase in (32, 40):
            for index, (axis, sign) in enumerate(itertools.product(
                    self.stage["output_aligned_axis_ids"], self.stage["initial_signs"])):
                states = copy.deepcopy(baseline_states)
                direction = directions[index]
                for horizon in range(1, 74 - phase):
                    scale = 0.00003 * horizon
                    states[phase + horizon] = self._state(
                        baseline_states[phase + horizon]["r_geo_m"] + direction[0] * scale,
                        direction[1] * scale)
                rows.append({"family_id": f"issue{phase}__{axis}__{sign}_then_return",
                             "passed": True, "states": states, "actions": []})
        replay = copy.deepcopy(next(row for row in rows
                                    if row["family_id"] == "issue32__q_z__plus_then_return"))
        replay["family_id"] = "replay_issue32__q_z__plus_then_return"
        rows.append(replay)
        rows.insert(1, {"family_id": "diagnostic_baseline_full_f", "passed": True,
                        "states": copy.deepcopy(baseline_states), "actions": []})
        return rows

    def test_scientific_gates_include_geometry_but_not_capture(self) -> None:
        rows = self._synthetic_rows()
        value = m.scientific_metrics(rows, self.stage)
        self.assertTrue(value["passed"], value)
        self.assertEqual(len(value["branch_metrics"]), 8)
        self.assertTrue(all(row["passed"] for row in value["positive_span_metrics"]))
        bad = copy.deepcopy(rows)
        target = next(row for row in bad if row["family_id"] ==
                      "issue32__q_r__plus_then_return")
        target["states"][36] = copy.deepcopy(bad[0]["states"][36])
        self.assertFalse(m.scientific_metrics(bad, self.stage)["passed"])

    def test_fail_fast_preserves_single_attempt(self) -> None:
        output = ROOT / ".codex_tmp" / f"id2z27_failfast_{uuid.uuid4().hex}"
        output.mkdir(parents=True)
        calls: list[str] = []
        try:
            def fake_execute(*args, **kwargs):
                stream = args[3]
                calls.append(stream["rollout_id"])
                return {"rollout_id": stream["rollout_id"],
                        "family_id": stream["family_id"], "passed": False,
                        "states": [], "actions": [], "reset_calls": 1,
                        "advance_attempts": 1, "plant_advance_gotsc_calls": 1,
                        "verified_plant_advances": 0}
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": "empty",
                         "missing_required_artifacts": []}
            with (mock.patch.object(m.z7, "configure_run_root", return_value={"passed": True}),
                  mock.patch.object(m, "_execute_row", fake_execute),
                  mock.patch.object(m.z6, "prefix_check", return_value={"passed": True}),
                  mock.patch.object(m.io, "raw_inventory", return_value=inventory),
                  mock.patch.object(m.io, "write_new")):
                value = m.execute(self.stage, self.runtime, self.cfg, self.preflight,
                                  self.baseline, "test", output, {"passed": True})
            self.assertEqual(calls, ["baseline_transition_center"])
            self.assertEqual(value["rollouts_started"], 1)
            self.assertEqual(value["route"],
                             self.stage["routes"]["execution_or_interface_fail"])
        finally:
            shutil.rmtree(output)

    def test_independent_and_launcher_contract(self) -> None:
        self.assertEqual(mi.SCHEMA, "rgeo-zgeo-1ms-id2z27-independent-raw-v1")
        source = inspect.getsource(mi.audit)
        self.assertIn("rawio._raw_rows", source)
        self.assertIn("scientific_metrics(raw_rows", source)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z27_dynamic_output_aligned_campaign.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z27_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z27_OUTPUT", launcher)
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertNotIn("--resume", launcher)

    def test_independent_raw_prefix_preserves_only_preissue_inputa(self) -> None:
        raw = {"states": [self._state(1.0, 2.0)], "actions": [{"x": 1}]}
        raw["states"][0]["artifact_sha256"]["inputa"] = "outgoing"
        raw["states"][0]["artifact_sha256"]["geqdsk"] = "raw-geqdsk"
        compact = copy.deepcopy(raw)
        compact["states"][0]["artifact_sha256"]["inputa"] = "preissue"
        compact["states"][0]["artifact_sha256"]["geqdsk"] = "compact-geqdsk"
        value = mi._preissue_semantic_row(raw, compact)
        self.assertEqual(value["states"][0]["artifact_sha256"]["inputa"], "preissue")
        self.assertEqual(value["states"][0]["artifact_sha256"]["geqdsk"], "raw-geqdsk")
        self.assertEqual(raw["states"][0]["artifact_sha256"]["inputa"], "outgoing")


if __name__ == "__main__":
    unittest.main()
