from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight as s23,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight_v1.json"
)
DESIGN = (
    ROOT
    / "docs/codex/reports/"
    "STAGE4_2R3C3T13S23_SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_DESIGN.md"
)


class Stage42R3C3T13S23Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_validates(self) -> None:
        s23._validate_design(self.cfg)

    def test_design_change_is_rejected(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["dynamic_exact_search_radius"] = 128
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            s23._validate_design(changed)

    def test_unpermuted_sylvester_matrix_is_exact(self) -> None:
        matrix = s23._sylvester_hadamard()
        self.assertEqual(matrix.shape, (16, 16))
        np.testing.assert_array_equal(matrix @ matrix.T, 16 * np.eye(16, dtype=int))
        np.testing.assert_array_equal(matrix[0], np.ones(16, dtype=int))

    def test_sequence_matrix_has_frozen_rank_and_sign_sentinels(self) -> None:
        matrix = s23._sequence_matrix()
        self.assertEqual(matrix.shape, (24, 16))
        self.assertEqual(np.linalg.matrix_rank(matrix), 16)
        np.testing.assert_array_equal(matrix[16:], -matrix[:8])

    def test_ideal_actual_coordinate_matrix_passes_geometry(self) -> None:
        actual = 0.25 * s23._sequence_matrix().astype(float)
        metrics = s23._matrix_metrics(actual, self.cfg)
        self.assertTrue(metrics["global_pass"])
        self.assertEqual(metrics["global_rank"], 16)
        self.assertEqual(metrics["slot_pass_count"], 4)
        self.assertTrue(metrics["late_novelty_pass"])

    def test_route_requires_every_frozen_gate(self) -> None:
        gate = self.cfg["primary_gate"]
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
        passed, route = s23._route(360, reproduction, primary, self.cfg)
        self.assertTrue(passed)
        self.assertEqual(route, self.cfg["routes"]["pass"])
        failed = dict(primary)
        failed["late_novelty_contexts"] = gate["late_novelty_contexts_required"] - 1
        passed, route = s23._route(360, reproduction, failed, self.cfg)
        self.assertFalse(passed)
        self.assertEqual(route, self.cfg["routes"]["fail"])

    def test_design_document_preserves_claim_boundary(self) -> None:
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("zero-new-TSC", text)
        self.assertIn("3,840 issue constructions", text)
        self.assertIn("global matrix rank", text)
        self.assertIn("S23 does not authorize a", text)
        self.assertIn("residual RL", text)

    def test_launchers_are_stage_specific_and_zero_plant(self) -> None:
        common = (ROOT / "run_stage4_2r3c3t13s23_common.sh").read_text(
            encoding="utf-8"
        )
        offline = (ROOT / "run_stage4_2r3c3t13s23_offline.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight.py", common)
        self.assertIn("source-s22-output", common)
        self.assertNotIn("gotsc", offline.lower())
        self.assertNotIn("ray", offline.lower())


if __name__ == "__main__":
    unittest.main()
