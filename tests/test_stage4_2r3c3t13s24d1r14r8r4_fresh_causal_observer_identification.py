from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import numpy as np

from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_campaign as campaign,
    stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification as contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification_370ms.json"
)


class FreshCausalObserverIdentificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_contract_and_self_test(self) -> None:
        contract.validate_config(self.cfg, project_root=ROOT)
        result = contract.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["prospective_rollout_count"], 16)
        self.assertEqual(result["candidate_count"], 48)

    def test_pair_partitions_are_disjoint_and_exact(self) -> None:
        self.assertEqual(
            tuple(self.cfg["pair_partitions"]["development"]),
            contract.DEVELOPMENT_PAIRS,
        )
        self.assertEqual(
            tuple(self.cfg["pair_partitions"]["holdout"]), contract.HOLDOUT_PAIRS
        )
        self.assertFalse(set(contract.DEVELOPMENT_PAIRS) & set(contract.HOLDOUT_PAIRS))

    def test_candidate_family_expands_rank_without_posthoc_options(self) -> None:
        values = observer.candidates(self.cfg)
        self.assertEqual(len(values), 48)
        self.assertEqual({value.pca_rank for value in values}, {32, 48, 64, 96})
        self.assertEqual({value.family for value in values}, {"linear", "rbf"})

    def test_contract_rejects_gate_mutation(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["gates"]["aggregate_point_pass_rate"] = 0.90
        with self.assertRaisesRegex(ValueError, "qualification"):
            contract.validate_config(changed)

    def test_quantile_scaled_tube_uses_higher_method(self) -> None:
        rows = []
        for index in range(20):
            value = np.full((12, 5), float(index + 1) * 1e-4)
            rows.append({"absolute_residual_physical": value.tolist()})
        tube = observer.tube_from_rows(rows, self.cfg)
        floor = np.asarray(
            self.cfg["tube_contract"]["component_floor_physical"], dtype=float
        )
        base = np.full((12, 5), 20e-4) + floor[None, :]
        ratio = np.asarray(
            [np.max(np.full((12, 5), (index + 1) * 1e-4) / base) for index in range(20)]
        )
        scalar = max(1.0, float(np.quantile(ratio, 0.95, method="higher")))
        np.testing.assert_allclose(tube, base * scalar, rtol=0.0, atol=0.0)

    def test_practical_gate_allows_recorded_finite_misses_only_at_rate(self) -> None:
        rows = []
        for context in range(2):
            for origin in range(10, 30):
                passed = not (context == 0 and origin == 29)
                residual = np.zeros((12, 5))
                if not passed:
                    residual[-1, 2] = 0.021
                rows.append(
                    {
                        "row_id": f"p{context}|h|{origin}",
                        "pair_id": f"p{context}",
                        "history_member": "h",
                        "origin_task_step": origin,
                        "prescribed_issue": origin in {10, 14, 18, 22},
                        "absolute_residual_physical": residual.tolist(),
                        "maximum_absolute_scaled_point_error": float(
                            np.max(residual / np.asarray(self.cfg["bank_contract"]["visible_scales"]))
                        ),
                        "finite_exclusion_violation_count": 0,
                        "passed": passed,
                    }
                )
        tube = np.full((12, 5), 0.049)
        tube[:, :2] = 0.009
        tube[:, 4] = 2999.0
        result = observer.practical_evaluation(rows, tube, self.cfg)
        self.assertTrue(result["passed"])
        self.assertEqual(result["origin_point_pass_count"], 39)
        self.assertEqual(result["origin_point_required"], 38)

    def test_finite_exclusion_miss_is_never_aggregated_away(self) -> None:
        item = {
            "row_id": "row",
            "pair_id": "pair",
            "history_member": "history",
            "origin_task_step": 10,
            "prescribed_issue": True,
            "origin_visible": np.zeros(5),
            "future_visible": np.zeros((12, 5)),
        }
        prediction = np.zeros((12, 5))
        prediction[-1, 2] = 0.51
        row = observer.prediction_row(item, prediction, self.cfg)
        self.assertFalse(row["finite_exclusion_passed"])
        self.assertGreater(row["finite_exclusion_violation_count"], 0)

    def test_all_stage_data_remain_forbidden_from_learning(self) -> None:
        self.assertFalse(self.cfg["all_stage_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["probe_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["bc_dagger_or_rl_allowed"])
        design = (ROOT / self.cfg["design_document"]).read_text(encoding="utf-8")
        self.assertIn("forbidden from every expert", design)

    def test_independent_does_not_import_primary_campaign_or_observer(self) -> None:
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r4_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("fresh_causal_observer_campaign as", source)
        self.assertNotIn("from tsc_rzip_rllib.control import causal_history", source)

    def test_launchers_pin_server_virtual_environment_and_eight_workers(self) -> None:
        common = (
            ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r4_shell_common.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", common)
        self.assertIn('R8R4_WORKERS:-8', common)
        self.assertNotIn("python3", common)

    def test_phase_parser_exposes_only_frozen_workflow(self) -> None:
        choices = next(
            action.choices
            for action in campaign._parser()._actions
            if action.dest == "command"
        )
        self.assertEqual(
            tuple(choices),
            (
                "offline",
                "development",
                "fit-development",
                "authorize-holdout",
                "holdout",
                "finalize",
                "postprocess",
            ),
        )


if __name__ == "__main__":
    unittest.main()
