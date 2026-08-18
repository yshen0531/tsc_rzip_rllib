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
    "id2w3", SCRIPTS / "rgeo_zgeo_1ms_id2w3_p03_braking_hold.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ID2W3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets, cls.reference = MODULE.load()
        cls.streams = MODULE.action_streams(cls.stage, cls.cfg, cls.targets)

    def test_config_is_strict_and_budgeted(self):
        self.assertIsInstance(json.loads(MODULE.CONFIG.read_text(encoding="utf-8")), dict)
        self.assertEqual(self.stage["rollout_ids"], list(MODULE.ROLLOUT_IDS))
        self.assertEqual(self.stage["hold_levels"], [52, 64])
        self.assertEqual(self.stage["maximum_advance_attempts"], 192)
        self.assertEqual(self.stage["maximum_retained_states"], 194)
        self.assertEqual(self.stage["required_artifact_files_if_complete"], 970)
        self.assertEqual(self.stage["terminal_state_indices"], list(range(88, 97)))
        self.assertEqual(
            self.stage["empirical_exploration"]["novel_hold_issue_steps_by_rollout"],
            {MODULE.ROLLOUT_IDS[0]: list(range(53, 96)),
             MODULE.ROLLOUT_IDS[1]: list(range(65, 96))})

    def test_offline_is_zero_plant_and_zero_fit(self):
        result = MODULE.offline(MODULE.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertTrue(all(row["passed"] for row in result["known_prefix_action_checks"]))
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)
        self.assertEqual(result["verified_plant_advances"], 0)
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_ramp_hold_schedule_and_prefix(self):
        self.assertEqual(len(self.streams), 2)
        for stream, level in zip(self.streams, (52, 64)):
            actions = stream["actions"]
            self.assertEqual(len(actions), 96)
            self.assertEqual([row["probe_virtual_action"][0] for row in actions],
                             [float(min(issue, level)) for issue in range(96)])
            self.assertLessEqual(
                max(float(row["maximum_issued_delta_a"]) for row in actions),
                0.3000000001)
            for issue in range(level + 1):
                self.assertEqual(actions[issue]["expected_card15_fields"],
                                 self.reference["actions"][issue]["expected_card15_fields"])
            for issue in range(level + 1, 96):
                self.assertEqual(actions[issue]["expected_card15_fields"],
                                 actions[level]["expected_card15_fields"])
                self.assertEqual(float(actions[issue]["maximum_issued_delta_a"]), 0.0)

    @staticmethod
    def _row(*, step_r: float = 0.00009, step_z: float = 0.00009,
             net_ip: float = 80.0, source_r: float = 0.0,
             source_z: float = 0.0) -> dict:
        states = []
        for index in range(97):
            if index < 88:
                r, z, ip = source_r, source_z, 3000.0
            else:
                fraction = (index - 88) / 8.0
                r = source_r + min(index - 88, 1) * step_r
                z = source_z + min(index - 88, 1) * step_z
                ip = 3000.0 + net_ip * fraction
            states.append({"r_geo_m": r, "z_geo_m": z, "ip_a": ip})
        return {"rollout_id": "synthetic", "hold_level": 52, "states": states}

    def test_terminal_hold_metrics_and_boundaries(self):
        good = MODULE.branch_metrics(self._row(), self.stage)
        self.assertTrue(good["passed"], good)
        bad_step = MODULE.branch_metrics(self._row(step_r=0.0001001), self.stage)
        self.assertFalse(bad_step["gate_passes"]["terminal_step_r"])
        bad_ip = MODULE.branch_metrics(self._row(net_ip=100.0001), self.stage)
        self.assertFalse(bad_ip["gate_passes"]["terminal_net_ip"])
        boundary = MODULE.branch_metrics(self._row(step_r=0.0001, step_z=0.0001,
                                                   net_ip=100.0), self.stage)
        self.assertTrue(boundary["passed"], boundary)

    def test_route_precedence(self):
        routes = self.stage["routes"]
        good_prefix, bad_prefix = [{"passed": True}], [{"passed": False}]
        good_metrics, bad_metrics = {"passed": True}, {"passed": False}
        self.assertEqual(MODULE.route_for(self.stage, False, False, [], None),
                         routes["execution_or_interface_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, False, good_prefix, good_metrics),
                         routes["raw_integrity_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, bad_prefix, good_metrics),
                         routes["prefix_mismatch"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, good_prefix, bad_metrics),
                         routes["hold_fail"])
        self.assertEqual(MODULE.route_for(self.stage, True, True, good_prefix, good_metrics),
                         routes["pass"])

    def test_launcher_preserves_scientific_fail_for_independent_audit(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2w3_p03_braking_hold.sh").read_text(
            encoding="utf-8")
        self.assertIn("set +e", text)
        self.assertIn("primary_rc=$?", text)
        self.assertIn("independent_raw_audit.json", text)
        self.assertIn('exit "$primary_rc"', text)


if __name__ == "__main__":
    unittest.main()
