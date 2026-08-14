import json
import math
import unittest
from pathlib import Path

import numpy as np

from scripts.rgeo_zgeo_1ms_id1c0_direction_screen_audit import audit, ray_geometry


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id1c0_direction_screen_audit.json"


class ID1C0DirectionScreenAuditTest(unittest.TestCase):
    def test_geometry_distinguishes_rank_from_positive_span(self):
        failed = ray_geometry([np.array([1.0, 0.0]), np.array([1.0, 1.0])], 360)
        self.assertEqual(failed["rank"], 2)
        self.assertGreater(failed["maximum_angular_gap_deg"], 175.0)
        passed = ray_geometry(
            [np.array([1.0, 0.0]), np.array([-1.0, 0.0]), np.array([0.0, 1.0]), np.array([0.0, -1.0])],
            360,
        )
        self.assertEqual(passed["rank"], 2)
        self.assertLessEqual(passed["maximum_angular_gap_deg"], 90.0)
        self.assertGreater(passed["minimum_directional_support_m"], 0.7)

    def test_server_evidence_selects_a_finite_candidate(self):
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        result = audit(ROOT, stage, "server-test")
        self.assertTrue(result["passed"])
        self.assertEqual(result["route"], stage["routes"]["candidate"])
        self.assertEqual(result["selected_candidate"]["directions"], ["p01", "p09"])
        geometry = result["selected_candidate"]["geometry"]
        self.assertLess(geometry["maximum_angular_gap_deg"], 100.0)
        self.assertGreater(geometry["minimum_directional_support_m"], 0.00002)
        self.assertEqual(result["holdout_records_read"], 0)
        self.assertEqual(result["new_tsc_or_plant_advances"], 0)
        self.assertEqual(result["new_model_fit_or_training"], 0)


if __name__ == "__main__":
    unittest.main()
