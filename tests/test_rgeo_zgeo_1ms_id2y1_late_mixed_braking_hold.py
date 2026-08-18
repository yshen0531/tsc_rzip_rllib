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
    "id2y1", ROOT / "scripts/rgeo_zgeo_1ms_id2y1_late_mixed_braking_hold.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ID2Y1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets, cls.reference = MODULE.load()
        cls.streams = MODULE.campaign_streams(cls.stage, cls.cfg, cls.targets)

    def test_config_identity_and_budget(self):
        self.assertIsInstance(json.loads(MODULE.CONFIG.read_text(encoding="utf-8")), dict)
        self.assertEqual(self.stage["rollout_ids"], list(MODULE.ROLLOUT_IDS))
        self.assertEqual(self.stage["horizon_steps"], 104)
        self.assertEqual(self.stage["maximum_advance_attempts"], 416)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 2100)

    def test_offline_is_zero_plant_and_exact(self):
        result = MODULE.offline(MODULE.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertGreaterEqual(result["minimum_absolute_current_headroom_a"], 95.0)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_level64_prefix_ramps_and_holds(self):
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

    def test_only_clearance_stop_is_continuable(self):
        self.assertTrue(MODULE.safe_stop({"reasons": ["PULSE_CLEARANCE_R"]}, self.stage))
        self.assertTrue(MODULE.safe_stop(
            {"reasons": ["PULSE_CLEARANCE_Z", "PULSE_CLEARANCE_IP"]}, self.stage))
        self.assertFalse(MODULE.safe_stop({"reasons": []}, self.stage))
        self.assertFalse(MODULE.safe_stop({"reasons": ["STEP_CAP_R"]}, self.stage))

    @staticmethod
    def _complete_row(rollout_id: str, hold_start: int) -> dict:
        states = []
        for index in range(105):
            states.append({"r_geo_m": 0.7 + (0.00008 if index >= 97 else 0.0),
                           "z_geo_m": 0.03 + (0.00008 if index >= 97 else 0.0),
                           "ip_a": 30000.0 + (80.0 if index >= 97 else 0.0)})
        return {"rollout_id": rollout_id, "mixed_candidate": True,
                "hold_start_issue": hold_start, "passed": True,
                "reasons": [], "states": states}

    def test_one_complete_branch_can_nominate_only_candidate(self):
        row = self._complete_row(MODULE.ROLLOUT_IDS[0], 71)
        metrics = MODULE.scientific_metrics([row], self.stage)
        self.assertTrue(metrics["passed"], metrics)
        self.assertEqual(metrics["passing_branch_ids"], [MODULE.ROLLOUT_IDS[0]])

    def test_route_precedence(self):
        routes = self.stage["routes"]
        prefixes = [{"passed": True}] * 4
        self.assertEqual(MODULE.route_for(self.stage, False, False, [], None),
                         routes["execution_or_interface_fail"])
        self.assertEqual(MODULE.route_for(
            self.stage, True, False, prefixes, {"passed": True}),
            routes["raw_integrity_fail"])
        bad = [{"passed": True}] * 3 + [{"passed": False}]
        self.assertEqual(MODULE.route_for(
            self.stage, True, True, bad, {"passed": True}), routes["prefix_mismatch"])
        self.assertEqual(MODULE.route_for(
            self.stage, True, True, prefixes, {"passed": False}), routes["hold_fail"])
        self.assertEqual(MODULE.route_for(
            self.stage, True, True, prefixes, {"passed": True}), routes["pass"])

    def test_launcher_preserves_scientific_fail_for_raw_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2y1_late_mixed_braking_hold.sh").read_text(
            encoding="utf-8")
        self.assertIn("set +e", text)
        self.assertIn("primary_rc=$?", text)
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn('exit "$primary_rc"', text)


if __name__ == "__main__":
    unittest.main()
