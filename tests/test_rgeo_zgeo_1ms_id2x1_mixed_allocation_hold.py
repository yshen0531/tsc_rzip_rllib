from __future__ import annotations

import importlib.util
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "id2x1", ROOT / "scripts/rgeo_zgeo_1ms_id2x1_mixed_allocation_hold.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
AUDIT_SPEC = importlib.util.spec_from_file_location(
    "id2x1_independent",
    ROOT / "scripts/rgeo_zgeo_1ms_id2x1_mixed_allocation_hold_independent.py")
AUDIT = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT)


class ID2X1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets, cls.reference = MODULE.load()
        cls.streams = MODULE.campaign_streams(cls.stage, cls.cfg, cls.targets)

    def test_config_and_budget(self):
        self.assertIsInstance(json.loads(MODULE.CONFIG.read_text(encoding="utf-8")), dict)
        self.assertEqual(self.stage["rollout_ids"], list(MODULE.ROLLOUT_IDS))
        self.assertEqual(self.stage["maximum_rollouts"], 4)
        self.assertEqual(self.stage["maximum_advance_attempts"], 384)
        self.assertEqual(self.stage["required_artifact_files_if_all_complete"], 1940)

    def test_offline_is_zero_plant_and_has_headroom(self):
        result = MODULE.offline(MODULE.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertGreaterEqual(result["minimum_absolute_current_headroom_a"], 98.79)
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_streams_prefix_ramps_and_holds(self):
        self.assertEqual([row["rollout_id"] for row in self.streams], list(MODULE.ROLLOUT_IDS))
        for stream, spec in zip(self.streams, self.stage["branch_specs"]):
            actions = stream["actions"]
            self.assertEqual(len(actions), 96)
            self.assertLessEqual(max(float(row["maximum_issued_delta_a"]) for row in actions),
                                 0.3000000001)
            for issue in range(33):
                self.assertEqual(actions[issue]["expected_card15_fields"],
                                 self.reference["actions"][issue]["expected_card15_fields"])
            start = spec["hold_start_issue"]
            for issue in range(start, 96):
                self.assertEqual(actions[issue]["expected_card15_fields"],
                                 actions[start - 1]["expected_card15_fields"])
                self.assertEqual(float(actions[issue]["maximum_issued_delta_a"]), 0.0)

    def test_only_preissue_clearance_is_continuable(self):
        self.assertTrue(MODULE.safe_stop({"reasons": ["PULSE_CLEARANCE_R"]}, self.stage))
        self.assertTrue(MODULE.safe_stop({"reasons": ["PULSE_CLEARANCE_Z",
                                                       "PULSE_CLEARANCE_IP"]}, self.stage))
        self.assertFalse(MODULE.safe_stop({"reasons": []}, self.stage))
        self.assertFalse(MODULE.safe_stop({"reasons": ["STEP_CAP_R"]}, self.stage))
        self.assertFalse(MODULE.safe_stop({"reasons": ["PULSE_CLEARANCE_R", "CARD15:1"]},
                                          self.stage))

    @staticmethod
    def _complete_row(rollout_id: str, mixed: bool) -> dict:
        states = []
        for index in range(97):
            fraction = max(0, index - 88) / 8.0
            states.append({"r_geo_m": 0.7 + (0.00008 if index >= 89 else 0.0),
                           "z_geo_m": 0.03 + (0.00008 if index >= 89 else 0.0),
                           "ip_a": 30000.0 + 80.0 * fraction})
        return {"rollout_id": rollout_id, "mixed_candidate": mixed,
                "hold_start_issue": 51, "passed": True, "reasons": [], "states": states}

    def test_baseline_cannot_create_campaign_pass(self):
        baseline = self._complete_row(MODULE.ROLLOUT_IDS[0], False)
        metrics = MODULE.scientific_metrics([baseline], self.stage)
        self.assertFalse(metrics["passed"])
        mixed = self._complete_row(MODULE.ROLLOUT_IDS[1], True)
        metrics = MODULE.scientific_metrics([baseline, mixed], self.stage)
        self.assertTrue(metrics["passed"], metrics)

    def test_route_precedence(self):
        routes = self.stage["routes"]
        prefixes = [{"passed": True}] * 4
        self.assertEqual(MODULE.route_for(self.stage, False, False, [], None),
                         routes["execution_or_interface_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, False, prefixes, {"passed": True}),
                         routes["raw_integrity_fail"])
        bad = [{"passed": True}] * 3 + [{"passed": False}]
        self.assertEqual(MODULE.route_for(self.stage, True, True, bad, {"passed": True}),
                         routes["prefix_mismatch"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, prefixes, {"passed": False}),
                         routes["hold_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, prefixes, {"passed": True}),
                         routes["pass"])

    def test_launcher_preserves_scientific_fail_for_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2x1_mixed_allocation_hold.sh").read_text(
            encoding="utf-8")
        self.assertIn("set +e", text)
        self.assertIn("primary_rc=$?", text)
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn('exit "$primary_rc"', text)

    def test_independent_prefix_respects_inputa_lifecycle(self):
        row = {
            "rollout_id": "synthetic",
            "states": copy.deepcopy(self.reference["states"][:34]),
            "actions": copy.deepcopy(self.reference["actions"][:33]),
        }
        for state in row["states"]:
            state["artifact_sha256"]["inputa"] = "outgoing-inputa-is-different"
        result = AUDIT.independent_prefix_check(
            row, self.reference, self.stage["semantic_artifacts"])
        self.assertTrue(result["passed"], result)
        row["states"][7]["artifact_sha256"]["geqdsk"] = "corrupt"
        result = AUDIT.independent_prefix_check(
            row, self.reference, self.stage["semantic_artifacts"])
        self.assertFalse(result["passed"])
        self.assertIn("STATE:7:artifact:geqdsk", result["failures"])


if __name__ == "__main__":
    unittest.main()
