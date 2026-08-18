from __future__ import annotations

import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "id2w1", SCRIPTS / "rgeo_zgeo_1ms_id2w1_sustained_branch_campaign.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ID2W1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets = MODULE.load()
        cls.streams = MODULE.campaign_streams(cls.stage, cls.cfg, cls.targets)

    def test_config_is_strict_json_and_budgeted(self):
        raw = MODULE.CONFIG.read_text(encoding="utf-8")
        self.assertIsInstance(json.loads(raw), dict)
        self.assertEqual(self.stage["maximum_rollouts"], 6)
        self.assertEqual(self.stage["maximum_advance_attempts"], 288)
        self.assertEqual(self.stage["required_artifact_files_if_complete"], 1470)

    def test_offline_is_zero_plant_and_zero_fit(self):
        result = MODULE.offline(MODULE.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["verified_plant_advances"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)
        self.assertEqual(result["calibration_or_holdout_records_read"], 0)

    def test_exact_six_stream_schedule(self):
        self.assertEqual([row["rollout_id"] for row in self.streams], list(MODULE.KINDS))
        self.assertTrue(all(len(row["actions"]) == 48 for row in self.streams))
        reference = self.streams[0]
        for row in self.streams[1:]:
            self.assertEqual(
                [a["expected_card15_fields"] for a in row["actions"][:19]],
                [a["expected_card15_fields"] for a in reference["actions"][:19]],
            )
        residual = self.streams[2]
        levels = [a["probe_virtual_action"][1] for a in residual["actions"]]
        self.assertEqual(levels[19:33], [1, 2, 3, 4, 5, 6, 6, 6, 5, 4, 3, 2, 1, 0])
        self.assertEqual([a["probe_virtual_action"][0] for a in residual["actions"][33:46]],
                         list(range(19, 32)))

    def test_exact_return_and_common_catchup(self):
        paused = self.streams[1]
        uninterrupted = self.streams[0]
        for branch in self.streams[2:]:
            self.assertEqual(branch["actions"][32]["expected_card15_fields"],
                             paused["actions"][32]["expected_card15_fields"])
            self.assertEqual([a["expected_card15_fields"] for a in branch["actions"][33:]],
                             [a["expected_card15_fields"] for a in paused["actions"][33:]])
        self.assertEqual(paused["actions"][45]["expected_card15_fields"],
                         uninterrupted["actions"][45]["expected_card15_fields"])
        self.assertEqual(paused["actions"][47]["expected_card15_fields"],
                         uninterrupted["actions"][47]["expected_card15_fields"])

    def test_slew_and_residual_offset(self):
        paused = self.streams[1]
        for row in self.streams:
            self.assertLessEqual(max(a["maximum_issued_delta_a"] for a in row["actions"]),
                                 0.3000000001)
        for branch in self.streams[2:]:
            base = np.asarray(paused["actions"][24]["target_current_a_tsc"])
            target = np.asarray(branch["actions"][24]["target_current_a_tsc"])
            maximum = float(np.max(np.abs(target - base)))
            self.assertGreater(maximum, 1.0)
            self.assertLessEqual(maximum, 1.800000001)

    def test_vector_geometry(self):
        vectors = np.asarray([[0.001, 0.0], [0.0, 0.001], [-0.001, 0.0], [0.0, -0.001]])
        result = MODULE._vector_geometry(vectors, 64)
        self.assertAlmostEqual(result["maximum_angular_gap_deg"], 90.0, places=10)
        self.assertGreater(result["minimum_all_direction_best_progress_m"], 0.0007)
        one_sided = MODULE._vector_geometry(np.asarray([[0.001, 0.0], [0.001, 0.0001]]), 64)
        self.assertGreater(one_sided["maximum_angular_gap_deg"], 180.0)

    @staticmethod
    def _row(name, kind, vector=None, hybrid_only=False):
        states = []
        for index in range(49):
            dr = dz = dip = 0.0
            if vector is not None and 20 <= index <= 32:
                if hybrid_only:
                    if index == 27:
                        dr, dz = vector
                else:
                    dr, dz = vector
            if index >= 46:
                dr = dz = dip = 0.0
            states.append({"r_geo_m": dr, "z_geo_m": dz, "ip_a": dip})
        direction, sign = (None, None)
        if kind == "residual_branch":
            direction = "p04" if "p04" in name else "p07"
            sign = "plus" if "plus" in name else "minus"
        return {"rollout_id": name, "cell_kind": kind,
                "direction_id": direction, "sign": sign, "states": states}

    def test_scientific_metrics_require_non_hybrid_common_state_utility(self):
        vectors = {
            "p04_plus_depth6": (0.0003, 0.0),
            "p04_minus_depth6": (-0.0003, 0.0),
            "p07_plus_depth6": (0.0, 0.0003),
            "p07_minus_depth6": (0.0, -0.0003),
        }
        rows = [self._row("uninterrupted_nominal", "uninterrupted_baseline"),
                self._row("pause_catchup_baseline", "paused_baseline")]
        rows.extend(self._row(name, "residual_branch", vector) for name, vector in vectors.items())
        metrics = MODULE.scientific_metrics(rows, self.stage)
        self.assertTrue(metrics["passed"])
        hybrid = [self._row("uninterrupted_nominal", "uninterrupted_baseline"),
                  self._row("pause_catchup_baseline", "paused_baseline")]
        hybrid.extend(self._row(name, "residual_branch", vector, True)
                      for name, vector in vectors.items())
        rejected = MODULE.scientific_metrics(hybrid, self.stage)
        self.assertFalse(rejected["passed"])
        self.assertFalse(rejected["gate_passes"]["signal_and_persistence"])

    def test_route_precedence(self):
        prefix = [{"passed": True}]
        good = {"passed": True}
        bad = {"passed": False}
        routes = self.stage["routes"]
        self.assertEqual(MODULE.route_for(self.stage, False, False, [], None),
                         routes["execution_or_interface_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, False, prefix, good),
                         routes["raw_integrity_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, [{"passed": False}], good),
                         routes["prefix_mismatch"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, prefix, bad),
                         routes["control_utility_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, prefix, good), routes["pass"])

    def test_launcher_preserves_scientific_fail_for_independent_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2w1_sustained_branch_campaign.sh").read_text(
            encoding="utf-8")
        self.assertIn("set +e", text)
        self.assertIn("primary_rc=$?", text)
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn('exit "$primary_rc"', text)


if __name__ == "__main__":
    unittest.main()

