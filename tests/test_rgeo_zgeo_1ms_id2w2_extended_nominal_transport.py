from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "id2w2", SCRIPTS / "rgeo_zgeo_1ms_id2w2_extended_nominal_transport.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ID2W2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets, cls.reference = MODULE.load()
        cls.stream = MODULE.action_stream(cls.stage, cls.cfg, cls.targets)

    def test_config_is_strict_json_and_budgeted(self):
        self.assertIsInstance(json.loads(MODULE.CONFIG.read_text(encoding="utf-8")), dict)
        self.assertEqual(self.stage["maximum_rollouts"], 1)
        self.assertEqual(self.stage["maximum_advance_attempts"], 80)
        self.assertEqual(self.stage["required_artifact_files_if_complete"], 405)
        self.assertEqual(self.stage["empirical_exploration"]["novel_issue_steps"],
                         list(range(32, 80)))

    def test_offline_is_zero_plant_and_zero_fit(self):
        result = MODULE.offline(MODULE.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertTrue(result["known_prefix_action_match"])
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["verified_plant_advances"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_extended_stride_schedule_and_slew(self):
        actions = self.stream["actions"]
        self.assertEqual(len(actions), 80)
        self.assertEqual(
            [row["probe_virtual_action"][0] for row in actions],
            [float(index) for index in range(80)],
        )
        self.assertLessEqual(max(float(row["maximum_issued_delta_a"]) for row in actions),
                             0.3000000001)
        for issue in range(32):
            self.assertEqual(actions[issue]["expected_card15_fields"],
                             self.reference["actions"][issue]["expected_card15_fields"])
        self.assertNotEqual(actions[32]["expected_card15_fields"],
                            self.reference["actions"][32]["expected_card15_fields"])

    @staticmethod
    def _row(distances):
        states = []
        for index, distance in enumerate(distances):
            states.append({"r_geo_m": float(distance), "z_geo_m": 0.0,
                           "ip_a": 1000.0 + index})
        return {"states": states}

    def test_scientific_gate_requires_three_consecutive_corridor_states(self):
        distances = [0.0] + [0.02] * 80
        distances[32] = self.stage["measurement_gates"]["reference_source_rz_distance_m"]
        distances[40:43] = [0.0149, 0.0148, 0.0149]
        passed = MODULE.scientific_metrics(self._row(distances), self.stage)
        self.assertTrue(passed["passed"])
        self.assertEqual(passed["longest_consecutive_corridor_states"], 3)
        distances[42] = 0.0151
        failed = MODULE.scientific_metrics(self._row(distances), self.stage)
        self.assertFalse(failed["passed"])

    def test_route_precedence(self):
        routes = self.stage["routes"]
        good_prefix, bad_prefix = {"passed": True}, {"passed": False}
        good_metrics, bad_metrics = {"passed": True}, {"passed": False}
        self.assertEqual(MODULE.route_for(self.stage, False, False, None, None),
                         routes["execution_or_interface_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, False, good_prefix, good_metrics),
                         routes["raw_integrity_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, bad_prefix, good_metrics),
                         routes["prefix_mismatch"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, good_prefix, bad_metrics),
                         routes["transport_utility_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, good_prefix, good_metrics),
                         routes["pass"])

    def test_launcher_preserves_scientific_fail_for_independent_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2w2_extended_nominal_transport.sh").read_text(
            encoding="utf-8")
        self.assertIn("set +e", text)
        self.assertIn("primary_rc=$?", text)
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn('exit "$primary_rc"', text)


if __name__ == "__main__":
    unittest.main()
