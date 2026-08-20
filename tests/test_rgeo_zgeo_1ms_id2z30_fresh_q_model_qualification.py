from __future__ import annotations

import copy
import inspect
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock

import numpy as np

from scripts import rgeo_zgeo_1ms_id2z30_fresh_q_model_qualification as m
from scripts import rgeo_zgeo_1ms_id2z30_fresh_q_model_qualification_independent as mi


ROOT = Path(__file__).resolve().parents[1]


class ID2Z30Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.base, cls.cfg, cls.preflight, cls.tracked, cls.model = m.load()
        cls.streams = m.build_streams(cls.stage, cls.cfg, cls.preflight, cls.tracked)

    def test_identity_budget_roles_and_hash(self) -> None:
        self.assertEqual(m._sha(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(len(self.streams), 10)
        self.assertEqual(self.stage["maximum_advance_attempts"], 730)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 3700)
        self.assertEqual(sum(row["data_role"] == "calibration" for row in self.streams), 4)
        self.assertEqual(sum(row["data_role"] == "blind" for row in self.streams), 4)
        self.assertEqual(sum(row["kind"] == "replay" for row in self.streams), 1)

    def test_all_streams_are_exact_and_blind_is_last(self) -> None:
        checks = [m.validate_stream(row, self.cfg) for row in self.streams]
        self.assertTrue(all(row["passed"] for row in checks), checks)
        self.assertEqual([row["phase_issue"] for row in self.streams[1:5]], [36] * 4)
        self.assertEqual([row["phase_issue"] for row in self.streams[6:]], [44] * 4)
        self.assertEqual(self.streams[5]["source_family_id"],
                         "cal_issue36__q_z__plus_then_return")

    def test_offline_is_zero_plant(self) -> None:
        value = m.offline(m.CONFIG, "test")
        self.assertTrue(value["passed"], value)
        self.assertEqual(value["reset_calls"], 0)
        self.assertEqual(value["plant_advance_gotsc_calls"], 0)

    @staticmethod
    def _baseline() -> dict:
        states = [{"time_ms": 1100 + i, "r_geo_m": i * 0.0001,
                   "z_geo_m": -i * 0.00005, "r_mid_m": i * 0.0001,
                   "ip_a": 30000.0, "actual_current_decimal_a_tsc": ["0"] * 14,
                   "wire_current_a": [0.0] * 48,
                   "active_command_card15_fields": ["0"] * 14,
                   "artifact_sha256": {name: "x" for name in
                       ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv")}}
                  for i in range(74)]
        return {"passed": True, "states": states, "actions": [],
                "reset_calls": 1, "advance_attempts": 73,
                "plant_advance_gotsc_calls": 73, "verified_plant_advances": 73}

    def _synthetic_row(self, stream: dict, bad: bool = False) -> dict:
        value = copy.deepcopy(self._baseline())
        value.update({"rollout_id": stream["rollout_id"], "family_id": stream["family_id"],
                      "kind": stream["kind"], "phase_issue": stream["phase_issue"],
                      "axis_id": stream["axis_id"], "initial_sign": stream["initial_sign"],
                      "data_role": stream["data_role"]})
        if stream["phase_issue"] is not None:
            prediction = np.asarray(self.model["model"]["odd_step_response"][stream["axis_id"]])
            if stream["initial_sign"] == "minus": prediction = -prediction
            if bad and stream["data_role"] == "calibration": prediction[:, 0] += .001
            phase = int(stream["phase_issue"])
            for h in range(1, 9):
                for index, key in enumerate(("r_geo_m", "z_geo_m", "ip_a")):
                    value["states"][phase + h][key] += float(prediction[h - 1, index])
        return value

    def test_phase_gate_stops_before_blind(self) -> None:
        output = ROOT / ".codex_tmp" / f"id2z30_{uuid.uuid4().hex}"
        output.mkdir(parents=True)
        calls = []
        try:
            def fake_execute(*args, **kwargs):
                stream = args[3]; calls.append(stream["rollout_id"])
                return self._synthetic_row(stream, bad=True)
            inventory = {"required_artifact_files": 5 * 74 * 6,
                         "required_artifact_bytes": 1,
                         "required_artifact_inventory_sha256": "x",
                         "missing_required_artifacts": []}
            with (mock.patch.object(m.z27.z7, "configure_run_root", return_value={"passed": True}),
                  mock.patch.object(m, "_execute_row", fake_execute),
                  mock.patch.object(m.z27.z6, "prefix_check", return_value={"passed": True}),
                  mock.patch.object(m.z27.z6, "replay_check", return_value={"passed": True}),
                  mock.patch.object(m.z27.io, "raw_inventory", return_value=inventory),
                  mock.patch.object(m.z27.io, "write_new")):
                value = m.execute(self.stage, self.base, self.cfg, self.preflight,
                                  self.tracked, self.model, "test", output, {"passed": True})
            self.assertEqual(len(calls), 6)
            self.assertFalse(value["blind_opened"])
            self.assertEqual(value["blind_records_read"], 0)
            self.assertEqual(value["route"], self.stage["routes"]["calibration_fail"])
        finally:
            shutil.rmtree(output)

    def test_tube_formula_and_containment(self) -> None:
        errors = np.ones((4, 8, 3))
        calibration = {"raw_errors": errors.tolist()}
        tube = m.calibrated_tube(calibration, self.stage["model_gates"])
        self.assertTrue(np.all(tube > 1.0))
        blind = {"raw_errors": (tube[None, :, :] * .9).repeat(4, axis=0).tolist()}
        self.assertTrue(m.blind_containment(blind, tube)["passed"])
        blind["raw_errors"][0][0][0] = float(tube[0, 0] * 1.1)
        self.assertFalse(m.blind_containment(blind, tube)["passed"])

    def test_independent_reads_raw_and_launcher_has_no_resume(self) -> None:
        source = inspect.getsource(mi.audit)
        self.assertIn("rawio._raw_rows", source)
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z30_fresh_q_model_qualification.sh").read_text(
            encoding="utf-8")
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
