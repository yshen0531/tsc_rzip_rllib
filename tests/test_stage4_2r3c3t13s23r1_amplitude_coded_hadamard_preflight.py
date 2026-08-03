import copy
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight as r1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight_v1.json"
DESIGN = ROOT / "docs" / "codex" / "reports" / "STAGE4_2R3C3T13S23R1_AMPLITUDE_CODED_HADAMARD_PREFLIGHT_DESIGN.md"


class Stage42R3C3T13S23R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_validates(self):
        r1._validate_design(self.cfg)

    def test_design_change_is_rejected(self):
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["canonical_pattern_amplitudes"]["++--"] = 0.49
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            r1._validate_design(changed)

    def test_coded_patterns_are_exact(self):
        cases = {
            (1, 1, 1, 1): [0.25, 0.25, 0.25, 0.25],
            (1, -1, 1, -1): [0.25, -0.25, 0.25, -0.25],
            (1, 1, -1, -1): [0.5, 0.5, -0.5, -0.5],
            (1, -1, -1, 1): [0.5, -0.5, -0.5, 0.5],
            (-1, 1, 1, -1): [-0.5, 0.5, 0.5, -0.5],
        }
        for signs, expected in cases.items():
            np.testing.assert_array_equal(r1._coded_coordinate(signs, self.cfg), expected)

    def test_requested_matrix_has_frozen_geometry(self):
        matrix = r1._requested_matrix(self.cfg)
        self.assertEqual(matrix.shape, (24, 16))
        np.testing.assert_array_equal(matrix[16:], -matrix[:8])
        metrics = r1.s23._matrix_metrics(matrix, self.cfg)
        self.assertEqual(metrics["global_rank"], 16)
        self.assertAlmostEqual(metrics["global_normalized_condition"], 2.8284271247461916)
        self.assertEqual(metrics["slot_pass_count"], 4)
        self.assertTrue(metrics["late_novelty_pass"])

    def test_route_requires_every_frozen_gate(self):
        reproduction = {
            "baseline_formal_reproduction_count": 40,
            "measured_probe_formal_reproduction_count": 320,
        }
        primary = {
            "fixed_basis_contexts": 40,
            "finite_constructions": 7680,
            "issue_gate_pass": 3840,
            "cancellation_gate_pass": 3840,
            "central_sign_gate_pass": 1280,
            "global_rank_condition_contexts": 40,
            "slot_rank_condition_blocks": 160,
            "late_novelty_contexts": 40,
        }
        passed, route = r1._route(360, reproduction, primary, self.cfg)
        self.assertTrue(passed)
        self.assertEqual(route, self.cfg["routes"]["pass"])
        primary["issue_gate_pass"] -= 1
        passed, route = r1._route(360, reproduction, primary, self.cfg)
        self.assertFalse(passed)
        self.assertEqual(route, self.cfg["routes"]["fail"])

    def test_design_document_preserves_claim_boundary(self):
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("zero-new-TSC", text)
        self.assertIn("does not validate a sequential plant response", text)
        self.assertIn("bounded residual RL remain prohibited", text)

    def test_launchers_are_stage_specific_and_zero_plant(self):
        common = (ROOT / "run_stage4_2r3c3t13s23r1_common.sh").read_text(encoding="utf-8")
        offline = (ROOT / "run_stage4_2r3c3t13s23r1_offline.sh").read_text(encoding="utf-8")
        self.assertIn("stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight.py", common)
        self.assertIn("zero plant/controller/TSC", common)
        self.assertNotIn("ray start", common.lower())
        self.assertIn("run_stage4_2r3c3t13s23r1_common.sh", offline)


if __name__ == "__main__":
    unittest.main()
