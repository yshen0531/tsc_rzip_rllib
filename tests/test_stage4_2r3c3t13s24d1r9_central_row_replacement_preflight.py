from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight as d1r7,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r9_central_row_replacement_preflight as stage,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json"
BASE = ROOT / "configs/stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1.json"


class CentralRowReplacementPreflightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.base = json.loads(BASE.read_text(encoding="utf-8"))

    def test_config_design_and_zero_tsc_scope_are_frozen(self):
        stage._validate_config(copy.deepcopy(self.cfg), CONFIG)
        scope = self.cfg["scientific_scope"]
        self.assertTrue(scope["offline_preflight_only"])
        self.assertTrue(scope["pass_authorizes_d1r10_design_only"])
        self.assertFalse(scope["pass_authorizes_d1r10_execution"])
        self.assertFalse(scope["pass_authorizes_mpc"])
        self.assertFalse(scope["bc_dagger_or_rl_allowed"])

    def _frozen_evidence(self):
        matrix = d1r7.requested_matrix(self.base)
        primary = matrix[:16]
        evidence = {}
        for index in self.cfg["evidence_contract"]["primary_exact_safe_indices"]:
            evidence[stage._digest(primary[index].tolist())] = {
                "success_count": 1,
                "failure_count": 0,
                "campaign_counts": {"synthetic": {"success": 1}},
            }
        for index in self.cfg["evidence_contract"]["negative_exact_safe_indices"]:
            evidence[stage._digest((-primary[index]).tolist())] = {
                "success_count": 1,
                "failure_count": 0,
                "campaign_counts": {"synthetic": {"success": 1}},
            }
        for index in self.cfg["evidence_contract"]["negative_contradicted_indices"]:
            evidence[stage._digest((-primary[index]).tolist())] = {
                "success_count": 1,
                "failure_count": 1,
                "campaign_counts": {"synthetic": {"success": 1, "failure": 1}},
            }
        return evidence

    def test_exhaustive_selection_is_unique_and_changes_only_row22(self):
        selected = stage._selection(self.cfg, self.base, self._frozen_evidence())
        self.assertEqual(selected["combination_count"], 12870)
        self.assertEqual(selected["eligible_combination_count"], 495)
        self.assertEqual(
            selected["selected_ordered_central_primary_indices"],
            [0, 4, 1, 5, 3, 7, 9, 8],
        )
        self.assertEqual(selected["changed_matrix_row_indices"], [22])
        self.assertEqual(
            selected["requested_matrix_digest"],
            "106dfed384febb16019e4d39ce1da03762ad9dbb5e8e69120a4a9d9acdebc30b",
        )
        self.assertEqual(
            selected["unknown_matrix_row_indices"], [3, 7, 11, 15, 20, 21, 22]
        )
        self.assertEqual(selected["contradicted_matrix_row_indices"], [])
        matrix = np.asarray(selected["requested_matrix"])
        source = d1r7.requested_matrix(self.base)
        for index in range(24):
            if index != 22:
                np.testing.assert_array_equal(matrix[index], source[index])

    def test_candidate_builder_freezes_126_new_identity_specs(self):
        selected = stage._selection(self.cfg, self.base, self._frozen_evidence())
        contexts = {}
        for index in range(18):
            pair = f"pair_{index // 2:02d}"
            history = "minus_first" if index % 2 == 0 else "plus_first"
            contexts[(pair, history)] = {
                "stage": "Stage4.2R3c3T13S24D1R2",
                "experiment_id": f"source_{index:02d}",
                "environment_variant": f"source_env_{index:02d}",
                "pair_id": pair,
                "history_member": history,
                "horizon_steps": 35 if index < 8 else 37,
                "formal_horizon_steps": 35 if index < 8 else 37,
                "restart_snapshot_dir": f"snapshot_{index:02d}",
            }
        candidate = stage._candidate_specs(
            self.cfg, self.base, contexts, selected
        )
        self.assertEqual(candidate["selected_spec_count"], 126)
        self.assertEqual(
            {row["stage"] for row in candidate["spec_rows"]},
            {"Stage4.2R3c3T13S24D1R10"},
        )
        self.assertEqual(
            {row["s24_sequence_index"] for row in candidate["spec_rows"]},
            {3, 7, 11, 15, 20, 21, 22},
        )
        self.assertTrue(
            all(not row["probe_trajectory_allowed_in_expert_dataset"] for row in candidate["spec_rows"])
        )

    def test_independent_implementation_does_not_import_primary(self):
        text = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r9_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r9_central_row_replacement_preflight as",
            text,
        )
        self.assertIn("itertools.combinations", text)
        self.assertIn("_authenticate_d1r1_and_static_replay", text)

    def test_launcher_uses_server_venv_and_contains_no_tsc_backend(self):
        launcher = (ROOT / "run_stage4_2r3c3t13s24d1r9.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python",
            launcher,
        )
        self.assertNotIn("--backend", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()

