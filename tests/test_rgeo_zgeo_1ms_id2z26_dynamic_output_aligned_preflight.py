import json
from pathlib import Path
import shutil
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight as primary
from scripts import rgeo_zgeo_1ms_id2z26_dynamic_output_aligned_preflight_independent as independent


class ID2Z26PreflightTests(unittest.TestCase):
    def test_frozen_budget_and_roles(self):
        stage = primary._read(primary.CONFIG)
        self.assertEqual(stage["maximum_prospective_rollouts"], 11)
        self.assertEqual(stage["maximum_prospective_advance_attempts"], 803)
        self.assertEqual(stage["maximum_tsc_calls"], 0)
        self.assertEqual(stage["maximum_plant_advances"], 0)
        self.assertEqual(stage["phase_issue_steps"], [32, 40])
        self.assertEqual(stage["prospective_data_contract"]["id2z25_fit_weight"], 0)

    def test_output_aligned_seed_is_rank_two(self):
        stage = primary._read(primary.CONFIG)
        evidence = primary._evidence(stage)
        nominal, axes = primary._axis_seeds(evidence)
        self.assertEqual(len(nominal), 14)
        matrix = np.column_stack([[float(value) for value in axes["q_r"]],
                                  [float(value) for value in axes["q_z"]]])
        self.assertEqual(np.linalg.matrix_rank(matrix), 2)
        self.assertLess(np.linalg.cond(matrix), 1.2)

    def test_primary_static_preflight_passes(self):
        result = primary.execute(source_revision="TEST_REVISION")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["route"],
                         "ONE_MS_ID2Z26R1_DYNAMIC_OUTPUT_ALIGNED_PREFLIGHT_PASS_CAMPAIGN_DESIGN_ONLY")
        self.assertEqual(result["tsc_calls"], 0)
        self.assertEqual(result["plant_advances"], 0)
        self.assertEqual(len(result["prospective_static_streams"]), 11)
        self.assertTrue(all(len(row["card15_targets"]) == 73
                            for row in result["prospective_static_streams"]))
        self.assertTrue(all(row["maximum_issued_delta_a"] <= 0.3000000001
                            for row in result["prospective_static_streams"]))

    def test_all_branches_close_and_preserve_prefix(self):
        result = primary.execute(source_revision="TEST_REVISION")
        branches = [row for row in result["prospective_static_streams"]
                    if row["rollout_id"].startswith("issue")]
        self.assertEqual(len(branches), 8)
        self.assertTrue(all(row["prefix_exact"] for row in branches))
        self.assertTrue(all(row["closure_exact"] for row in branches))

    def test_independent_recomputes_primary(self):
        result = primary.execute(source_revision="TEST_REVISION")
        root = primary.ROOT / ".codex_tmp" / "id2z26_test"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        try:
            path = root / "primary.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            audit = independent.execute(path, "TEST_REVISION")
            self.assertTrue(audit["audit_passed"], audit["failures"])
            self.assertEqual(len(audit["stream_checks"]), 11)
        finally:
            shutil.rmtree(root)

    def test_mutated_frozen_field_is_rejected(self):
        stage = primary._read(primary.CONFIG)
        stage["phase_issue_steps"] = [31, 40]
        with self.assertRaisesRegex(ValueError, "phase_issue_steps"):
            primary._require(stage)


if __name__ == "__main__":
    unittest.main()
