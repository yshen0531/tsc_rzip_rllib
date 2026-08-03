import copy
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s23d1_bounded_schedule_redesign_search as d1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s23d1_bounded_schedule_redesign_search_v1.json"
DESIGN = ROOT / "docs" / "codex" / "reports" / "STAGE4_2R3C3T13S23D1_SCHEDULE_REDESIGN_SEARCH.md"


class Stage42R3C3T13S23D1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_validates(self):
        d1._validate_design(self.cfg)

    def test_design_change_is_rejected(self):
        changed = copy.deepcopy(self.cfg)
        changed["search_contract"]["maximum_relative_off_basis_residual"] = 0.11
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            d1._validate_design(changed)

    def test_template_catalog_is_exact(self):
        signed, canonical = d1._templates(self.cfg)
        self.assertEqual(len(signed), 320)
        self.assertEqual(len(canonical), 160)
        lookup = {row["template_id"]: row for row in signed}
        for row in signed:
            negative = lookup[row["negative_template_id"]]
            np.testing.assert_allclose(
                negative["coordinate"], -np.asarray(row["coordinate"], dtype=float)
            )
        self.assertTrue(all(next(v for v in row["integer_vector"] if v) == 1 for row in canonical))

    def test_candidate_knot_space_is_exact(self):
        knots = d1._candidate_knot_sets(range(10, 20), self.cfg)
        self.assertEqual(len(knots), 35)
        self.assertEqual(knots[0], (10, 12, 14, 16))
        self.assertEqual(knots[-1], (13, 15, 17, 19))
        self.assertTrue(all(len(row) == 4 for row in knots))
        self.assertTrue(all(all(b - a >= 2 for a, b in zip(row, row[1:])) for row in knots))

    def test_schedule_matrix_uses_exact_sign_sentinels(self):
        contexts = {"ctx": {"positive": [1.0, 0.0, 0.0, 0.0], "negative": [-1.0, 0.0, 0.0, 0.0]}}
        pair = {
            "pair_id": "pair",
            "positive_template_id": "plus",
            "negative_template_id": "minus",
            "positive_coordinate": [1.0, 0.0, 0.0, 0.0],
            "negative_coordinate": [-1.0, 0.0, 0.0, 0.0],
            "actual_by_context": contexts,
        }
        catalog = {step: [pair] for step in (10, 12, 14, 16)}
        selections = [[(0, 1)] * 4 for _ in range(16)]
        matrix = d1._schedule_matrix(selections, (10, 12, 14, 16), catalog, "ctx")
        self.assertEqual(matrix.shape, (24, 16))
        np.testing.assert_array_equal(matrix[16:], -matrix[:8])

    def test_design_document_preserves_claim_boundary(self):
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("development-only", text)
        self.assertIn("D1 itself cannot authorize S24", text)
        self.assertIn("executes no Ray", text)
        self.assertIn("bounded residual RL remain prohibited", text)

    def test_launchers_are_stage_specific_and_zero_plant(self):
        common = (ROOT / "run_stage4_2r3c3t13s23d1_common.sh").read_text(encoding="utf-8")
        offline = (ROOT / "run_stage4_2r3c3t13s23d1_offline.sh").read_text(encoding="utf-8")
        self.assertIn("stage4_2r3c3t13s23d1_bounded_schedule_redesign_search.py", common)
        self.assertIn("zero plant/controller", common)
        self.assertNotIn("ray start", common.lower())
        self.assertIn("run_stage4_2r3c3t13s23d1_common.sh", offline)


if __name__ == "__main__":
    unittest.main()
