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
    "id2y1r1", ROOT / "scripts/rgeo_zgeo_1ms_id2y1r1_late_mixed_braking_hold.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ID2Y1R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets, cls.reference = MODULE.load()
        cls.streams = MODULE.campaign_streams(cls.stage, cls.cfg, cls.targets)

    def test_identity_and_budget(self):
        self.assertIsInstance(json.loads(MODULE.CONFIG.read_text(encoding="utf-8")), dict)
        self.assertEqual(self.stage["rollout_ids"], list(MODULE.ROLLOUT_IDS))
        self.assertEqual(self.stage["maximum_advance_attempts"], 416)
        self.assertEqual(self.stage["terminal_state_indices"], list(range(96, 105)))

    def test_repaired_offline_passes_without_plant(self):
        result = MODULE.offline(MODULE.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertGreaterEqual(result["minimum_absolute_current_headroom_a"], 95.0)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_prefix_slew_headroom_and_hold(self):
        self.assertEqual([row["rollout_id"] for row in self.streams],
                         list(MODULE.ROLLOUT_IDS))
        for stream, branch in zip(self.streams, self.stage["branch_specs"]):
            actions = stream["actions"]
            self.assertEqual(len(actions), 104)
            self.assertLessEqual(max(float(row["maximum_issued_delta_a"])
                                     for row in actions), 0.3000000001)
            for issue in range(65):
                self.assertEqual(actions[issue]["expected_card15_fields"],
                                 self.reference["actions"][issue]["expected_card15_fields"])
            start = branch["hold_start_issue"]
            for issue in range(start, 104):
                self.assertEqual(actions[issue]["expected_card15_fields"],
                                 actions[start - 1]["expected_card15_fields"])
                self.assertEqual(float(actions[issue]["maximum_issued_delta_a"]), 0.0)

    def test_only_clearance_can_continue(self):
        self.assertTrue(MODULE.safe_stop({"reasons": ["PULSE_CLEARANCE_R"]}, self.stage))
        self.assertFalse(MODULE.safe_stop({"reasons": ["STEP_CAP_R"]}, self.stage))
        self.assertFalse(MODULE.safe_stop({"reasons": []}, self.stage))

    def test_route_precedence(self):
        routes = self.stage["routes"]
        prefixes = [{"passed": True}] * 4
        self.assertEqual(MODULE.route_for(self.stage, False, False, [], None),
                         routes["execution_or_interface_fail"])
        self.assertEqual(MODULE.route_for(
            self.stage, True, False, prefixes, {"passed": True}),
            routes["raw_integrity_fail"])
        self.assertEqual(MODULE.route_for(
            self.stage, True, True, prefixes, {"passed": False}), routes["hold_fail"])
        self.assertEqual(MODULE.route_for(
            self.stage, True, True, prefixes, {"passed": True}), routes["pass"])

    def test_launcher_keeps_primary_and_independent_routes_separate(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2y1r1_late_mixed_braking_hold.sh").read_text(
            encoding="utf-8")
        self.assertIn("primary_rc=$?", text)
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn('exit "$primary_rc"', text)


if __name__ == "__main__":
    unittest.main()
