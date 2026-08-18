from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "id2w3r1", ROOT / "scripts/rgeo_zgeo_1ms_id2w3r1_level64_hold.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ID2W3R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets, cls.reference = MODULE.load()
        cls.stream = MODULE.action_stream(cls.stage, cls.cfg, cls.targets)

    def test_config_budget_and_identity(self):
        self.assertIsInstance(json.loads(MODULE.CONFIG.read_text(encoding="utf-8")), dict)
        self.assertEqual(self.stage["rollout_id"], MODULE.ROLLOUT_ID)
        self.assertEqual(self.stage["hold_level"], 64)
        self.assertEqual(self.stage["maximum_rollouts"], 1)
        self.assertEqual(self.stage["maximum_advance_attempts"], 96)
        self.assertEqual(self.stage["maximum_retained_states"], 97)
        self.assertEqual(self.stage["required_artifact_files_if_complete"], 485)
        self.assertEqual(self.stage["empirical_exploration"]["novel_hold_issue_steps"],
                         list(range(65, 96)))

    def test_offline_is_zero_plant_and_zero_fit(self):
        result = MODULE.offline(MODULE.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["verified_plant_advances"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_unstarted_level64_stream(self):
        actions = self.stream["actions"]
        self.assertEqual(len(actions), 96)
        self.assertEqual([row["probe_virtual_action"][0] for row in actions],
                         [float(min(issue, 64)) for issue in range(96)])
        self.assertLessEqual(max(float(row["maximum_issued_delta_a"]) for row in actions),
                             0.3000000001)
        for issue in range(65):
            self.assertEqual(actions[issue]["expected_card15_fields"],
                             self.reference["actions"][issue]["expected_card15_fields"])
        for issue in range(65, 96):
            self.assertEqual(actions[issue]["expected_card15_fields"],
                             actions[64]["expected_card15_fields"])
            self.assertEqual(float(actions[issue]["maximum_issued_delta_a"]), 0.0)

    def test_terminal_metric_reuses_frozen_gate(self):
        states = []
        for index in range(97):
            fraction = max(0, index - 88) / 8.0
            states.append({"r_geo_m": 0.7 + (0.00008 if index >= 89 else 0.0),
                           "z_geo_m": 0.03 + (0.00008 if index >= 89 else 0.0),
                           "ip_a": 30000.0 + 80.0 * fraction})
        row = {"rollout_id": MODULE.ROLLOUT_ID, "hold_level": 64, "states": states}
        metrics = MODULE.w3.scientific_metrics([row], self.stage)
        self.assertTrue(metrics["passed"], metrics)
        states[96]["ip_a"] = states[88]["ip_a"] + 100.0001
        self.assertFalse(MODULE.w3.scientific_metrics([row], self.stage)["passed"])

    def test_route_precedence(self):
        routes = self.stage["routes"]
        self.assertEqual(MODULE.route_for(self.stage, False, False, None, None),
                         routes["execution_or_interface_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, False, {"passed": True}, {"passed": True}),
                         routes["raw_integrity_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, {"passed": False}, {"passed": True}),
                         routes["prefix_mismatch"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, {"passed": True}, {"passed": False}),
                         routes["hold_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, {"passed": True}, {"passed": True}),
                         routes["pass"])

    def test_launcher_preserves_scientific_fail_for_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2w3r1_level64_hold.sh").read_text(
            encoding="utf-8")
        self.assertIn("set +e", text)
        self.assertIn("primary_rc=$?", text)
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn('exit "$primary_rc"', text)


if __name__ == "__main__":
    unittest.main()
