from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rgeo_zgeo_1ms_id2z22_discrete_vertex_moving_nominal_preflight as z22


class ID2Z22PreflightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage = json.loads(z22.CONFIG.read_text(encoding="utf-8"))
        cls.result = z22.execute(z22.CONFIG, "TEST_REVISION")

    def test_frozen_identity_and_zero_execution(self) -> None:
        self.assertEqual(self.stage["stage"], "ID-2Z22")
        self.assertEqual(self.stage["maximum_tsc_calls"], 0)
        self.assertEqual(self.stage["maximum_plant_advances"], 0)
        self.assertEqual(self.result["tsc_calls"], 0)
        self.assertEqual(self.result["plant_advances"], 0)
        self.assertEqual(self.result["models_fit_or_updated"], 0)

    def test_frozen_vertex_and_phase_matrix(self) -> None:
        self.assertEqual(self.stage["selected_vertex_ids"],
                         ["p00_minus4", "p05_minus4", "p05_plus4", "p06_plus4"])
        self.assertEqual(self.stage["prospective_phase_issue_steps"], [24, 32])
        self.assertEqual(len(self.stage["prospective_rollout_ids"]), 10)
        self.assertEqual(self.stage["maximum_prospective_advance_attempts"], 650)

    def test_authenticated_held_geometry_passes(self) -> None:
        self.assertTrue(self.result["passed"], self.result.get("failures"))
        self.assertEqual(self.result["unique_exact_vertex_count"], 4)
        for row in self.result["arm_metrics"]:
            self.assertTrue(row["passed"], row)
            self.assertGreaterEqual(row["state52_state56_cosine"], .95)
        for row in self.result["held_geometry"]:
            self.assertTrue(row["passed"], row)
            self.assertLessEqual(row["maximum_angular_gap_deg"], 120.0)
            self.assertGreaterEqual(row["weakest_best_projection_m"], .00006)

    def test_static_streams_are_exact_and_inside_limits(self) -> None:
        self.assertEqual(len(self.result["prospective_static_streams"]), 9)
        for row in self.result["prospective_static_streams"]:
            self.assertTrue(row["passed"], row)
            self.assertLessEqual(row["maximum_issued_delta_a"], .3000000001)
            self.assertGreaterEqual(row["minimum_absolute_current_headroom_a"], 0.0)

    def test_phase_collapse_is_retained_as_warning(self) -> None:
        warning = self.result["w1_phase_warning"]
        self.assertTrue(warning["passed"])
        self.assertTrue(warning["state25"]["passed"])
        self.assertFalse(warning["state26"]["passed"])

    def test_no_continuous_inversion_or_clipping(self) -> None:
        semantics = self.stage["action_semantics"]
        self.assertFalse(semantics["continuous_basis_inversion"])
        self.assertFalse(semantics["add_then_clip"])
        self.assertFalse(semantics["legacy_runner_clipping_may_be_relied_on"])



if __name__ == "__main__":
    unittest.main()
