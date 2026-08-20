from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import rgeo_zgeo_1ms_id2z29_moving_reference_waypoint_preflight as m
from scripts import rgeo_zgeo_1ms_id2z29_moving_reference_waypoint_preflight_independent as mi


ROOT = Path(__file__).resolve().parents[1]


class ID2Z29Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.evidence = m.load()

    def test_frozen_identity_and_zero_work(self) -> None:
        self.assertEqual(m._sha(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["waypoint_radius_m"], .0001)
        self.assertEqual(self.stage["direction_count"], 8)
        self.assertEqual(self.stage["candidate_count_per_direction"], 390625)
        self.assertEqual(self.stage["models_fit_or_updated"], 0)
        self.assertEqual(self.stage["tsc_calls"], 0)

    def test_all_eight_directions_pass_frozen_waypoint_gates(self) -> None:
        rows = m.waypoint_rows(self.stage, self.evidence["id2z28_result"]["model"])
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["passed"] for row in rows), rows)
        self.assertLessEqual(max(row["maximum_predicted_path_error_m"] for row in rows), .000025)
        self.assertGreaterEqual(min(row["predicted_directional_progress_m"] for row in rows), .00008)

    def test_exact_streams_and_cardinal_contract(self) -> None:
        result = m.execute(source_revision="test-revision")
        self.assertTrue(result["passed"], result)
        self.assertEqual(len(result["exact_action_streams"]), 16)
        self.assertTrue(all(row["passed"] for row in result["exact_action_streams"]))
        self.assertEqual(set(result["cardinal_feedback_sequences"]),
                         {"r_plus", "z_plus", "r_minus", "z_minus"})
        self.assertEqual(result["source_capture_status"], "ID2Z28_FAIL_UNCHANGED")

    def test_independent_recomputes_primary(self) -> None:
        primary = m.execute(source_revision="test-revision")
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as directory:
            path = Path(directory) / "primary.json"
            path.write_text(json.dumps(primary), encoding="utf-8")
            result = mi.audit(mi.CONFIG, path, "test-revision")
        self.assertTrue(result["audit_passed"], result)
        self.assertEqual(result["recomputed_route"], self.stage["routes"]["pass"])

    def test_future_campaign_is_sequential_and_not_controller_authorization(self) -> None:
        contract = self.stage["future_campaign_contract"]
        self.assertEqual(contract["calibration_phase_issue"], 36)
        self.assertEqual(contract["blind_phase_issue"], 44)
        self.assertFalse(contract["model_refit_after_calibration"])
        self.assertFalse(contract["controller_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
