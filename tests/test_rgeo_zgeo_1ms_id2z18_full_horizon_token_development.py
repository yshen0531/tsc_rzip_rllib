from __future__ import annotations

import copy
import inspect
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock

from scripts import rgeo_zgeo_1ms_id2z18_full_horizon_token_development as m
from scripts import rgeo_zgeo_1ms_id2z18_full_horizon_token_development_independent as mi


ROOT = Path(__file__).resolve().parents[1]


class ID2Z18Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.runtime, cls.cfg, cls.targets, cls.parent, cls.reference = m.load()
        cls.streams = m.build_execution_streams(
            cls.stage, cls.cfg, cls.targets, cls.parent)

    def test_identity_budget_hash_and_roles(self) -> None:
        self.assertEqual(m.io.sha256(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["maximum_rollouts"], 16)
        self.assertEqual(self.stage["maximum_advance_attempts"], 1040)
        self.assertEqual(self.stage["maximum_retained_states"], 1056)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 5280)
        self.assertTrue(self.stage["empirical_exploration"][
            "abort_campaign_after_any_rollout_failure"])
        self.assertEqual(sum(row["fit_weight"] for row in self.streams), 14)
        self.assertEqual(sum(row["data_role"] == "replay" for row in self.streams), 2)

    def test_all_roles_are_static_but_only_development_executes(self) -> None:
        all_rows = m.build_all_static_streams(
            self.stage, self.cfg, self.targets, self.parent)
        self.assertEqual(len(all_rows), 24)
        self.assertEqual(sum(row["data_role"] == "development" for row in all_rows), 14)
        self.assertEqual(sum(row["data_role"] == "replay" for row in all_rows), 2)
        self.assertEqual(sum(row["data_role"] == "future_calibration_unexecuted"
                             for row in all_rows), 4)
        self.assertEqual(sum(row["data_role"] == "future_blind_holdout_unexecuted"
                             for row in all_rows), 4)
        self.assertEqual({row["data_role"] for row in self.streams},
                         {"development", "replay"})

    def test_stream_clocks_prefix_tail_and_slew(self) -> None:
        prefix = [row["expected_card15_fields"] for row in self.reference["actions"][:16]]
        for row in m.build_all_static_streams(
                self.stage, self.cfg, self.targets, self.parent):
            check = m.validate_stream(row, self.stage, self.cfg, self.reference)
            self.assertTrue(check["passed"], check)
            self.assertEqual(len(row["tokens"]), 32)
            self.assertEqual(len(row["actions"]), 65)
            self.assertEqual([a["expected_card15_fields"] for a in row["actions"][:16]],
                             prefix)
            self.assertLessEqual(max(float(a["maximum_issued_delta_a"])
                                     for a in row["actions"]), .3000000001)
            for issue in range(48, 65):
                self.assertEqual(row["actions"][issue]["expected_card15_fields"],
                                 row["actions"][47]["expected_card15_fields"])

    def test_increment_geometry_is_rank_three(self) -> None:
        value = m.increment_geometry(self.stage, self.cfg, self.targets, self.parent)
        self.assertTrue(value["passed"], value)
        self.assertEqual(value["rank"], 3)
        self.assertLessEqual(value["condition"], 2.1)

    def test_offline_is_24_of_24_zero_plant(self) -> None:
        value = m.offline(m.CONFIG, "test-revision")
        self.assertTrue(value["passed"], value["failures"])
        self.assertEqual(value["static_stream_count"], 24)
        self.assertEqual(value["static_streams_passed"], 24)
        self.assertEqual(value["execution_rollouts_planned"], 16)
        self.assertEqual(value["future_calibration_rollouts_planned_but_unexecuted"], 4)
        self.assertEqual(value["future_blind_holdout_rollouts_planned_but_unexecuted"], 4)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        original = json.loads(m.CONFIG.read_text(encoding="utf-8"))
        mutations = (
            lambda value: value.update(maximum_rollouts=17),
            lambda value: value["development_unique_specs"][0].update(tokens="H" * 32),
            lambda value: value["replay_specs"][0].update(fit_weight=1),
            lambda value: value["empirical_exploration"].update(
                abort_campaign_after_any_rollout_failure=False),
            lambda value: value.update(models_fit_or_updated=1),
        )
        for mutate in mutations:
            changed = copy.deepcopy(original); mutate(changed)
            with self.assertRaises(Exception):
                m._require(changed)

    def test_route_precedence(self) -> None:
        routes = self.stage["routes"]
        self.assertEqual(m.route_for(self.stage, False, False, False, 0, False, False),
                         routes["execution_or_interface_fail"])
        self.assertEqual(m.route_for(self.stage, True, False, True, 16, True, True),
                         routes["raw_integrity_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, False, 16, True, True),
                         routes["prefix_mismatch"])
        self.assertEqual(m.route_for(self.stage, True, True, True, 15, True, True),
                         routes["campaign_incomplete"])
        self.assertEqual(m.route_for(self.stage, True, True, True, 16, False, True),
                         routes["replay_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, True, 16, True, False),
                         routes["signal_or_support_fail"])
        self.assertEqual(m.route_for(self.stage, True, True, True, 16, True, True),
                         routes["data_pass"])

    @staticmethod
    def _state(r: float, z: float) -> dict:
        return {"r_geo_m": r, "z_geo_m": z, "ip_a": 1000.0}

    def test_pair_signal_gate(self) -> None:
        rows = []
        for index in range(6):
            plus = [self._state(0.0, 0.0) for _ in range(66)]
            minus = [self._state(0.0, 0.0) for _ in range(66)]
            plus[17] = self._state(.000051, 0.0)
            rows.extend([
                {"family_id": f"d{index:02d}_plus", "passed": True, "states": plus},
                {"family_id": f"d{index:02d}_minus", "passed": True, "states": minus},
            ])
        values = m.pair_metrics(rows, self.stage)
        self.assertEqual(len(values), 6)
        self.assertTrue(all(row["passed"] for row in values))
        rows[0]["states"][17] = self._state(.000049, 0.0)
        self.assertFalse(m.pair_metrics(rows, self.stage)[0]["passed"])

    def test_fail_fast_after_first_rollout_failure(self) -> None:
        output = ROOT / ".codex_tmp" / f"id2z18_failfast_{uuid.uuid4().hex}"
        output.mkdir(parents=True)
        calls = []
        try:
            def fake_execute(*args, **kwargs):
                stream = args[2]; calls.append(stream["rollout_id"])
                return {"rollout_id": stream["rollout_id"],
                        "family_id": stream["family_id"], "fit_weight": stream["fit_weight"],
                        "passed": False, "states": [], "actions": [],
                        "reset_calls": 1, "advance_attempts": 1,
                        "plant_advance_gotsc_calls": 1, "verified_plant_advances": 0,
                        "reasons": ["FAKE_STOP"]}
            inventory = {"required_artifact_files": 0, "required_artifact_bytes": 0,
                         "required_artifact_inventory_sha256": "empty",
                         "missing_required_artifacts": []}
            with (mock.patch.object(m.z7, "configure_run_root",
                                    return_value={"passed": True}),
                  mock.patch.object(m, "execute_row", fake_execute),
                  mock.patch.object(m.z6, "prefix_check", return_value={"passed": True}),
                  mock.patch.object(m.io, "raw_inventory", return_value=inventory),
                  mock.patch.object(m.io, "write_new")):
                value = m.execute(self.stage, self.runtime, self.cfg, self.targets,
                                  self.parent, self.reference, "test", output,
                                  {"passed": True})
            self.assertEqual(calls, ["baseline_full_f"])
            self.assertEqual(value["rollouts_started"], 1)
            self.assertTrue(value["campaign_aborted_after_rollout_failure"])
            self.assertEqual(value["route"], self.stage["routes"][
                "execution_or_interface_fail"])
        finally:
            shutil.rmtree(output)

    def test_independent_and_launcher_contract(self) -> None:
        self.assertEqual(mi.SCHEMA, "rgeo-zgeo-1ms-id2z18-independent-raw-v1")
        source = inspect.getsource(mi.audit)
        self.assertIn("z9i._raw_rows", source)
        self.assertIn("calibration_or_holdout_records_read", source)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z18_full_horizon_token_development.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z18_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z18_OUTPUT", launcher)
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
