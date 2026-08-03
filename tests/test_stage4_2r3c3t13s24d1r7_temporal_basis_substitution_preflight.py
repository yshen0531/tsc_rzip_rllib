from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r7_independent_forensics as independent,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight as stage,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1.json"


class TemporalBasisSubstitutionPreflightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_design(self) -> None:
        stage._validate_config(self.cfg, CONFIG)
        self.assertEqual(independent.STAGE, stage.STAGE)

    def test_matrix_digest_rank_condition_and_novelty(self) -> None:
        matrix = stage.requested_matrix(self.cfg)
        self.assertEqual(matrix.shape, (24, 16))
        self.assertEqual(
            stage._digest(matrix.tolist()),
            "c4430a13b679ad8dcceb72c259051a5eebad03da47d86816d46c4385cd811d77",
        )
        metrics = stage.matrix_metrics(matrix, self.cfg)
        self.assertTrue(metrics["global_pass"])
        self.assertEqual(metrics["global_rank"], 16)
        self.assertEqual(metrics["slot_pass_count"], 4)
        self.assertTrue(metrics["late_novelty_pass"])
        self.assertAlmostEqual(metrics["global_normalized_condition"], 2.0364675298172568)

    def test_direction2_temporal_basis_excludes_observed_failures(self) -> None:
        matrix = stage.requested_matrix(self.cfg)
        expected = ["++++", "+--+", "-+-+", "--++"]
        actual = []
        for row_index in (2, 6, 10, 14):
            row = matrix[row_index]
            temporal = [int(np.sign(row[4 * slot])) for slot in range(4)]
            actual.append("".join("+" if value > 0 else "-" for value in temporal))
        self.assertEqual(actual, expected)
        self.assertTrue(set(actual).isdisjoint({"+-+-", "++--", "----"}))

    def test_central_sign_rows_are_exact(self) -> None:
        matrix = stage.requested_matrix(self.cfg)
        pairs = self.cfg["matrix_contract"]["central_sign_primary_indices"]
        for sentinel, primary in enumerate(pairs, start=16):
            np.testing.assert_array_equal(matrix[sentinel], -matrix[primary])

    def test_candidate_spec_builder_is_deterministic(self) -> None:
        matrix = stage.requested_matrix(self.cfg)
        contexts = {}
        for index in range(18):
            pair = f"pair_{index // 2:02d}"
            history = "minus_first" if index % 2 == 0 else "plus_first"
            horizon = 35 if index < 8 else 37
            contexts[(pair, history)] = {
                "experiment_id": f"source_{index:02d}",
                "environment_variant": f"source_env_{index:02d}",
                "pair_id": pair,
                "history_member": history,
                "horizon_steps": horizon,
                "formal_horizon_steps": horizon,
                "restart_snapshot_dir": f"snapshot_{index:02d}",
                "partition": "safety_sentinel",
            }
        first = stage._candidate_specs(contexts, matrix, self.cfg)
        second = stage._candidate_specs(contexts, matrix, self.cfg)
        independent_value = independent._candidate(contexts, matrix, self.cfg)
        self.assertEqual(first, second)
        self.assertEqual(first["selected_spec_count"], 108)
        self.assertEqual(first["ordered_spec_digest"], independent_value["digest"])
        self.assertEqual(first["spec_rows"], independent_value["specs"])
        self.assertEqual(
            {row["horizon_steps"] for row in first["spec_rows"]}, {35, 37}
        )
        self.assertTrue(
            all(not row["source_result_available_to_controller"] for row in first["spec_rows"])
        )

    def test_raw_inventory_digest_is_name_size_hash_bound(self) -> None:
        self.assertNotEqual(
            stage._digest([{"name": "a", "size": 1, "sha": "x"}]),
            stage._digest([{"name": "b", "size": 1, "sha": "x"}]),
        )


if __name__ == "__main__":
    unittest.main()
