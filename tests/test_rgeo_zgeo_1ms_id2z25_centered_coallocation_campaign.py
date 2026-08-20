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

from scripts import rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign as m
from scripts import rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign_independent as mi

ROOT = Path(__file__).resolve().parents[1]


class ID2Z25Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.parent, cls.baseline = m.load()
        cls.streams = m.build_streams(cls.stage, cls.cfg, cls.baseline)

    def test_identity_budget_roles_and_hashes(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(len(self.streams), 15)
        self.assertEqual(self.stage["maximum_reset_calls"], 15)
        self.assertEqual(self.stage["maximum_advance_attempts"], 975)
        self.assertEqual(self.stage["maximum_gotsc_calls"], 975)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 4950)
        self.assertEqual(sum(row["fit_weight"] for row in self.streams), 13)
        self.assertEqual(sum(row["data_role"] == "zero_fit_replay" for row in self.streams), 1)
        self.assertEqual(sum(row["kind"] == "full_f_diagnostic" for row in self.streams), 1)

    def test_stream_matrix_exact_prefix_bridge_and_tail(self) -> None:
        center = self.streams[0]
        self.assertEqual(center["rollout_id"], "baseline_center")
        for stream in self.streams:
            check = m.validate_stream(stream, self.stage, self.cfg)
            self.assertTrue(check["passed"], check)
            self.assertEqual(len(stream["actions"]), 65)
            self.assertLessEqual(check["maximum_issued_delta_a"], .3000000001)
            if stream["kind"] in ("centered_branch", "replay"):
                phase = int(stream["phase_issue"])
                self.assertEqual(
                    [row["expected_card15_fields"] for row in stream["actions"][:phase]],
                    [row["expected_card15_fields"] for row in center["actions"][:phase]])
                self.assertEqual(stream["actions"][phase + 15]["expected_card15_fields"],
                                 center["actions"][phase + 15]["expected_card15_fields"])
                self.assertEqual(stream["non_nominal_issue_steps"],
                                 list(range(phase, phase + 16)))

    def test_replay_is_exact_and_zero_weight(self) -> None:
        source = next(row for row in self.streams
                      if row["rollout_id"] == "issue24__p05_plus__plus_then_minus")
        replay = self.streams[-1]
        self.assertEqual(replay["source_family_id"], source["family_id"])
        self.assertEqual(replay["fit_weight"], 0)
        self.assertEqual(replay["targets"], source["targets"])
        self.assertEqual(replay["actions"], source["actions"])

    def test_offline_is_zero_plant_and_all_streams_pass(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value)
        self.assertEqual(len(value["stream_checks"]), 15)
        self.assertTrue(all(row["passed"] for row in value["stream_checks"]))
        self.assertEqual(value["reset_calls"], 0)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)
        self.assertEqual(value["models_fit_or_updated"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        mutations = (
            lambda value: value.update(maximum_rollouts=16),
            lambda value: value["rollout_specs"][2].update(phase_issue=25),
            lambda value: value["rollout_specs"][-1].update(fit_weight=1),
            lambda value: value["action_semantics"].update(legacy_runner_clipping_may_be_relied_on=True),
            lambda value: value["data_contract"].update(d0_requires_positive_span_or_capture=True),
        )
        for mutate in mutations:
            changed = copy.deepcopy(original); mutate(changed)
            with self.assertRaises(Exception):
                m._require(changed)

    @staticmethod
    def _state(r: float, z: float, ip: float = 1000.0) -> dict:
        return {"r_geo_m": r, "z_geo_m": z, "r_mid_m": r, "ip_a": ip,
                "actual_current_decimal_a_tsc": ["0"] * 14,
                "wire_current_a": [0.0] * 48,
                "active_command_card15_fields": ["0"] * 14,
                "artifact_sha256": {name: "same" for name in
                                    ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv")}}

    def _synthetic_rows(self) -> list[dict]:
        baseline_states = [self._state(index * 1e-4, 0.0) for index in range(66)]
        rows = [{"family_id": "baseline_center", "passed": True,
                 "states": baseline_states, "actions": []}]
        directions = [(math.cos(math.pi * k / 3), math.sin(math.pi * k / 3))
                      for k in range(6)]
        for phase in (24, 32):
            for index, (axis, order) in enumerate(
                    (x for x in __import__("itertools").product(
                        self.stage["residual_axis_ids"], self.stage["starting_sign_orders"]))):
                states = copy.deepcopy(baseline_states)
                direction = directions[index]
                for horizon in range(1, 66 - phase):
                    scale = 0.00003 * horizon
                    states[phase + horizon] = self._state(
                        baseline_states[phase + horizon]["r_geo_m"] + direction[0] * scale,
                        direction[1] * scale)
                rows.append({"family_id": f"issue{phase}__{axis}__{order}",
                             "passed": True, "states": states, "actions": []})
        replay = copy.deepcopy(next(row for row in rows
                                    if row["family_id"] == "issue24__p05_plus__plus_then_minus"))
        replay["family_id"] = "replay_issue24__p05_plus__plus_then_minus"
        rows.append(replay)
        rows.insert(1, {"family_id": "diagnostic_baseline_full_f", "passed": True,
                        "states": copy.deepcopy(baseline_states), "actions": []})
        return rows

    def test_scientific_gate_does_not_require_positive_span_or_capture(self) -> None:
        rows = self._synthetic_rows()
        value = m.scientific_metrics(rows, self.stage)
        self.assertTrue(value["passed"], value)
        self.assertEqual(len(value["branch_metrics"]), 12)
        self.assertTrue(all(row["passed"] for row in value["branch_metrics"]))
        bad = copy.deepcopy(rows)
        target = next(row for row in bad if row["family_id"] ==
                      "issue24__p00_minus__plus_then_minus")
        target["states"][28] = copy.deepcopy(bad[0]["states"][28])
        self.assertFalse(m.scientific_metrics(bad, self.stage)["passed"])

    def test_fail_fast_preserves_single_attempt(self) -> None:
        output = ROOT / ".codex_tmp" / f"id2z25_failfast_{uuid.uuid4().hex}"
        output.mkdir(parents=True); calls = []
        try:
            def fake_execute(*args, **kwargs):
                stream = args[3]; calls.append(stream["rollout_id"])
                return {"rollout_id": stream["rollout_id"], "family_id": stream["family_id"],
                        "passed": False, "states": [], "actions": [], "reset_calls": 1,
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
                value = m.execute(self.stage, self.runtime, self.cfg, self.baseline,
                                  "test", output, {"passed": True})
            self.assertEqual(calls, ["baseline_center"])
            self.assertEqual(value["rollouts_started"], 1)
            self.assertEqual(value["route"], self.stage["routes"]["execution_or_interface_fail"])
        finally:
            shutil.rmtree(output)

    def test_independent_and_launcher_contract(self) -> None:
        self.assertEqual(mi.SCHEMA, "rgeo-zgeo-1ms-id2z25-independent-raw-v1")
        source = inspect.getsource(mi.audit)
        self.assertIn("rawio._raw_rows", source)
        self.assertIn("scientific_metrics(raw_rows", source)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z25_centered_coallocation_campaign.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z25_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z25_OUTPUT", launcher)
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
