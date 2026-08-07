from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as audit,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit.json"
)


class MeasuredMultipulseAuthorityAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_contract(self) -> None:
        audit.validate_config(self.cfg, project_root=ROOT)
        self.assertEqual(self.cfg["scientific_gate"]["minimum_repaired_failed_baseline_count"], 1)
        self.assertFalse(self.cfg["scientific_scope"]["measured_oracle_is_causal_selector"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_contract_rejects_gate_timing_and_learning_mutation(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["scientific_gate"]["minimum_repaired_failed_baseline_count"] = 0
        with self.assertRaisesRegex(ValueError, "frozen design"):
            audit.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["formal_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaisesRegex(ValueError, "frozen design"):
            audit.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["scientific_scope"]["expert_data_allowed"] = True
        with self.assertRaisesRegex(ValueError, "frozen design"):
            audit.validate_config(changed, project_root=ROOT)

    @staticmethod
    def _row(
        *,
        context: int,
        partition: str,
        schedule: int,
        passed: bool,
        minimum: float,
        mean: float,
    ) -> dict[str, object]:
        return {
            "experiment_id": f"row_{context}_{partition}_{schedule}",
            "partition": partition,
            "pair_id": f"pair_{context}",
            "history_member": "a",
            "schedule_index": schedule,
            "formal_contract_pass": passed,
            "formal_minimum_signed_margin": minimum,
            "formal_mean_signed_margin": mean,
            "formal_best_arrival_ms": 250,
        }

    def test_authority_counts_repairs_oracle_and_margin_improvement(self) -> None:
        rows = [
            self._row(context=0, partition="baseline", schedule=-1, passed=False, minimum=-0.2, mean=-0.1),
            self._row(context=0, partition="multipulse", schedule=0, passed=True, minimum=0.1, mean=0.2),
            self._row(context=0, partition="multipulse", schedule=1, passed=False, minimum=-0.1, mean=0.1),
            self._row(context=1, partition="baseline", schedule=-1, passed=True, minimum=0.2, mean=0.3),
            self._row(context=1, partition="multipulse", schedule=0, passed=False, minimum=-0.2, mean=-0.1),
            self._row(context=1, partition="multipulse", schedule=1, passed=True, minimum=0.1, mean=0.2),
        ]
        result = audit._authority(rows)
        self.assertEqual(result["context_count"], 2)
        self.assertEqual(result["baseline_formal_pass_count"], 1)
        self.assertEqual(result["multipulse_formal_pass_count"], 2)
        self.assertEqual(result["failed_baseline_count"], 1)
        self.assertEqual(result["repaired_failed_baseline_count"], 1)
        self.assertEqual(result["failed_baseline_strict_margin_improvement_count"], 1)
        self.assertEqual(result["measured_oracle_formal_pass_count"], 2)
        self.assertEqual(result["context_rows"][1]["oracle_partition"], "baseline")

    def test_ratio_summary_keeps_frozen_threshold_exact(self) -> None:
        result = audit._ratio_summary([0.994, 0.995, 0.9950000001, 1.0, 1.1])
        self.assertEqual(result["strictly_better_than_zero_count"], 3)
        self.assertEqual(result["meets_frozen_0_995_ratio_count"], 2)
        self.assertEqual(result["median"], 0.9950000001)

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r9_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as",
            source,
        )

    def test_launcher_uses_server_venv_and_no_archives(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r9_common.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
