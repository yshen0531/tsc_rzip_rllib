from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r5_independent_forensics as independent,
)
from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_campaign as campaign,
    stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout as contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout_370ms.json"
)


class ContextRobustObserverHoldoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_contract_and_self_test(self) -> None:
        contract.validate_config(self.cfg, project_root=ROOT)
        result = contract.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["development_new_rollout_count"], 0)
        self.assertEqual(result["holdout_rollout_count"], 8)

    def test_source_r8r4_is_final_and_holdout_unopened(self) -> None:
        source = self.cfg["source_r8r4_contract"]
        self.assertEqual(
            source["required_route"],
            "FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT",
        )
        self.assertEqual(source["development_raw_count"], 8)
        self.assertEqual(source["holdout_raw_count"], 0)
        self.assertEqual(source["model_file_count"], 0)

    def test_fixed_candidate_has_no_selection_bank(self) -> None:
        fixed = self.cfg["fixed_model_contract"]
        self.assertEqual(
            (fixed["family"], fixed["pca_rank"], fixed["bandwidth_multiplier"], fixed["ridge"]),
            ("linear", 32, 0.0, 1e-6),
        )
        self.assertFalse(fixed["candidate_selection_allowed"])
        self.assertEqual(len(observer.candidates(self.cfg)), 1)

    def test_context_robust_tube_matches_independent(self) -> None:
        rows = []
        for context in range(4):
            for index in range(10):
                value = np.full((12, 5), (1 + context + index) * 1e-4)
                rows.append(
                    {
                        "pair_id": f"pair{context // 2}",
                        "history_member": f"history{context % 2}",
                        "absolute_residual_physical": value.tolist(),
                    }
                )
        primary_tube, primary_detail = campaign.context_robust_tube(rows, self.cfg)
        independent_tube, independent_detail = independent._context_tube(rows, self.cfg)
        np.testing.assert_allclose(primary_tube, independent_tube, rtol=0.0, atol=0.0)
        self.assertEqual(primary_detail, independent_detail)
        self.assertEqual(primary_detail["reserve_multiplier"], 1.25)
        self.assertEqual(len(primary_detail["per_context_q90_row_ratios"]), 4)

    def test_context_scalar_uses_worst_context_not_mean(self) -> None:
        rows = []
        for context, high in (("ordinary", 1.0), ("tail", 8.0)):
            for index in range(10):
                value = np.full((12, 5), 1e-4)
                if context == "tail" and index == 9:
                    value[-1, -1] *= high
                rows.append(
                    {
                        "pair_id": context,
                        "history_member": "h",
                        "absolute_residual_physical": value.tolist(),
                    }
                )
        _, detail = campaign.context_robust_tube(rows, self.cfg)
        self.assertEqual(
            detail["calibration_ratio"],
            max(detail["per_context_q90_row_ratios"].values()),
        )
        self.assertEqual(detail["scalar"], 1.25 * detail["calibration_ratio"])

    def test_contract_rejects_posthoc_tube_expansion(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["tube_contract"]["blind_holdout_reserve_multiplier"] = 1.5
        with self.assertRaisesRegex(ValueError, "context-robust"):
            contract.validate_config(changed)

    def test_only_blind_holdout_can_create_new_raw(self) -> None:
        rollout = self.cfg["rollout_contract"]
        self.assertEqual(rollout["development_new_rollouts"], 0)
        self.assertEqual(rollout["maximum_new_rollouts"], 8)
        self.assertEqual(tuple(self.cfg["holdout_pairs"]), contract.HOLDOUT_PAIRS)

    def test_phase_parser_exposes_fail_closed_order(self) -> None:
        choices = next(
            action.choices
            for action in campaign._parser()._actions
            if action.dest == "command"
        )
        self.assertEqual(
            tuple(choices),
            (
                "offline",
                "fit-development",
                "authorize-holdout",
                "holdout",
                "finalize",
                "postprocess",
            ),
        )

    def test_independent_does_not_import_primary_or_observer(self) -> None:
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r5_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("context_robust_observer_campaign as", source)
        self.assertNotIn("from tsc_rzip_rllib.control", source)

    def test_launcher_pins_existing_server_virtual_environment(self) -> None:
        source = (
            ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r5_shell_common.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("R8R5_WORKERS:-8", source)
        self.assertNotIn("python3", source)

    def test_all_stage_data_remain_forbidden_from_learning(self) -> None:
        self.assertFalse(self.cfg["all_stage_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["probe_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["bc_dagger_or_rl_allowed"])
        design = (ROOT / self.cfg["design_document"]).read_text(encoding="utf-8")
        self.assertIn("forbidden from expert", design)


if __name__ == "__main__":
    unittest.main()
