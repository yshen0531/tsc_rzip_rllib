from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r10_replacement_scale_formal_authority_audit as audit,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r10_replacement_scale_formal_authority_audit.json"


class ReplacementScaleFormalAuthorityAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_contract(self) -> None:
        audit.validate_config(self.cfg, project_root=ROOT)
        self.assertEqual(self.cfg["row_contract"]["selected_row_count"], 312)
        self.assertEqual(self.cfg["scientific_gate"]["minimum_replacement_only_repair_count"], 1)
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_contract_rejects_timing_gate_and_learning_mutation(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["formal_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaisesRegex(ValueError, "frozen design"):
            audit.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["scientific_gate"]["minimum_replacement_only_repair_count"] = 0
        with self.assertRaisesRegex(ValueError, "frozen design"):
            audit.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["scientific_scope"]["expert_data_allowed"] = True
        with self.assertRaisesRegex(ValueError, "frozen design"):
            audit.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["source_r8"]["training_raw_count"] = 623
        with self.assertRaisesRegex(ValueError, "frozen design"):
            audit.validate_config(changed, project_root=ROOT)

    @staticmethod
    def _row(
        context: int,
        role: str,
        issue: int,
        sign: int,
        *,
        passed: bool,
        margin: float,
    ) -> dict[str, object]:
        scale = {"baseline": 0.0, "canonical": 1.0, "replacement": 1.5}[role]
        return {
            "source_bank": "synthetic",
            "experiment_id": f"{context}_{role}_{issue}_{sign}",
            "pair_id": f"p{5 + 4 * context}_q1_case",
            "history_member": "plus_first",
            "role": role,
            "action_scale": scale,
            "issue_task_step": issue,
            "sign": sign,
            "formal_contract_pass": passed,
            "formal_minimum_signed_margin": margin,
            "formal_mean_signed_margin": margin + 0.1,
            "formal_best_arrival_ms": 250,
        }

    def test_authority_requires_replacement_only_repair(self) -> None:
        rows = []
        for context in range(2):
            baseline_pass = context == 1
            rows.append(self._row(context, "baseline", -1, 0, passed=baseline_pass, margin=0.2 if baseline_pass else -0.2))
            for issue in audit.ISSUE_STEPS:
                for sign in audit.SIGNS:
                    rows.append(self._row(context, "canonical", issue, sign, passed=baseline_pass, margin=0.1 if baseline_pass else -0.1))
                    replacement_pass = baseline_pass or (context == 0 and issue == 18 and sign == 1)
                    rows.append(self._row(context, "replacement", issue, sign, passed=replacement_pass, margin=0.3 if replacement_pass else -0.05))
        result = audit.authority(rows)
        self.assertEqual(result["pair_count"], 2)
        self.assertEqual(result["context_count"], 2)
        self.assertEqual(result["selected_row_count"], 26)
        self.assertEqual(result["baseline_formal_pass_count"], 1)
        self.assertEqual(result["failed_baseline_count"], 1)
        self.assertEqual(result["canonical_repaired_failed_baseline_count"], 0)
        self.assertEqual(result["replacement_repaired_failed_baseline_count"], 1)
        self.assertEqual(result["replacement_only_repaired_failed_baseline_count"], 1)
        self.assertEqual(result["canonical_oracle_formal_pass_count"], 1)
        self.assertEqual(result["replacement_oracle_formal_pass_count"], 2)
        self.assertEqual(result["combined_oracle_formal_pass_count"], 2)

    def test_normalized_source_roles_are_exact(self) -> None:
        baseline = audit._normalize_spec(
            "R4",
            {
                "experiment_id": "b", "pair_id": "p", "history_member": "h",
                "d1r14r4_role": "baseline", "d1r14r4_issue_task_step": -1,
                "d1r14r4_direction_index": -1, "d1r14r4_sign": 0,
            },
        )
        replacement = audit._normalize_spec(
            "R6",
            {
                "experiment_id": "r", "pair_id": "p", "history_member": "h",
                "d1r14r6_role": "signed_probe", "d1r14r6_issue_task_step": 18,
                "d1r14r6_direction_index": 0, "d1r14r6_sign": -1,
            },
        )
        self.assertEqual(baseline["role"], "baseline")
        self.assertEqual(replacement["role"], "replacement")
        self.assertEqual(replacement["action_scale"], 1.5)

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = (ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r10_independent_forensics.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r10_replacement_scale_formal_authority_audit as",
            source,
        )

    def test_launcher_uses_server_venv_and_no_archives(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r10_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
