from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition as audit,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition.json"


class MeasuredAdditiveCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_contract(self) -> None:
        audit.validate_config(self.cfg, project_root=ROOT)
        self.assertEqual(self.cfg["candidate_contract"]["total_source_raw_count"], 128)
        self.assertTrue(self.cfg["candidate_contract"]["global_candidate_only"])
        self.assertFalse(self.cfg["candidate_contract"]["per_context_oracle_allowed"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])

    def test_timing_gate_source_and_learning_mutations_are_rejected(self) -> None:
        for path, value in (
            (("formal_contract", "normal_arrival_deadline_step"), 26),
            (("scientific_gate", "minimum_selected_formal_pass_count"), 6),
            (("candidate_contract", "per_context_oracle_allowed"), True),
            (("source_r8r12", "qualification_raw_count"), 11),
            (("scientific_scope", "expert_data_allowed"), True),
        ):
            changed = copy.deepcopy(self.cfg)
            changed[path[0]][path[1]] = value
            with self.assertRaisesRegex(ValueError, "frozen design"):
                audit.validate_config(changed, project_root=ROOT)

    def test_additive_paths_agree_within_frozen_tolerance(self) -> None:
        base = np.asarray([[0.2, -0.1, 2.0e5], [0.3, -0.2, 2.1e5]])
        direction0 = np.asarray([[0.21, -0.08, 2.01e5], [0.28, -0.18, 2.08e5]])
        direction2 = np.asarray([[0.18, -0.11, 1.99e5], [0.31, -0.22, 2.12e5]])
        path_a = direction2 + (direction0 - base)
        path_b = base + (direction2 - base) + (direction0 - base)
        self.assertLessEqual(float(np.max(np.abs(path_a - path_b))), 1e-12)
        self.assertTrue(np.array_equal(direction2 + (base - base), direction2))

    def test_global_ranking_is_deterministic_and_has_no_context_oracle(self) -> None:
        rows = [
            {"candidate_index": 0, "formal_pass_count": 7, "repaired_failed_baseline_count": 1, "baseline_pass_regression_count": 0, "failed_baseline_minimum_margin_gain": {"minimum": 0.01}},
            {"candidate_index": 1, "formal_pass_count": 8, "repaired_failed_baseline_count": 1, "baseline_pass_regression_count": 1, "failed_baseline_minimum_margin_gain": {"minimum": 0.10}},
            {"candidate_index": 2, "formal_pass_count": 7, "repaired_failed_baseline_count": 2, "baseline_pass_regression_count": 0, "failed_baseline_minimum_margin_gain": {"minimum": -0.01}},
            {"candidate_index": 3, "formal_pass_count": 7, "repaired_failed_baseline_count": 2, "baseline_pass_regression_count": 0, "failed_baseline_minimum_margin_gain": {"minimum": 0.02}},
        ]
        self.assertEqual([row["candidate_index"] for row in audit._rank_candidates(rows)], [1, 3, 2, 0])
        self.assertTrue(self.cfg["candidate_contract"]["global_candidate_only"])

    def test_routes_and_execution_scope_are_zero_tsc(self) -> None:
        execution = self.cfg["execution_contract"]
        self.assertEqual(execution["new_raw_count"], 0)
        self.assertEqual(execution["plant_steps_executed"], 0)
        self.assertFalse(execution["ray_executed"])
        self.assertFalse(execution["gotsc_executed"])
        self.assertFalse(execution["tsc_executed"])
        self.assertIn("NO_TSC", self.cfg["routes"]["integrity_fail"])

    def test_independent_does_not_import_primary(self) -> None:
        source = (ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r13_independent_forensics.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r13_measured_additive_direction0_on_direction2_composition as",
            source,
        )

    def test_launcher_uses_existing_server_venv_and_no_archives(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r13_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("zero_new_tsc=true", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
