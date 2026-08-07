from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r6_independent_forensics as independent,
)
from tsc_rzip_rllib.control import causal_one_step_innovation_observer as innovation
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer as contract,
    stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer_audit as audit,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer.json"
)


class CausalOneStepInnovationObserverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_contract_and_self_test(self) -> None:
        contract.validate_config(self.cfg, project_root=ROOT)
        result = contract.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertTrue(result["zero_new_tsc"])
        self.assertEqual(result["origin_row_count"], 600)
        self.assertEqual(result["adapted_origin_row_count"], 560)

    def test_frozen_scope_and_fixed_candidate(self) -> None:
        fixed = self.cfg["fixed_model_contract"]
        self.assertEqual(
            (fixed["family"], fixed["pca_rank"], fixed["bandwidth_multiplier"], fixed["ridge"]),
            ("linear", 32, 0.0, 1e-6),
        )
        self.assertFalse(fixed["candidate_selection_allowed"])
        self.assertTrue(self.cfg["zero_new_tsc"])
        self.assertFalse(self.cfg["all_stage_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["probe_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["bc_dagger_or_rl_allowed"])

    def test_adaptation_matches_independent_and_reintegrates_position(self) -> None:
        origin = np.array([1.0, -2.0, 3.0, -4.0, 5.0])
        previous = np.zeros((12, 5))
        previous[0, 2:5] = np.array([2.9, -3.9, 4.95])
        cold = np.zeros((12, 5))
        primary, primary_detail = innovation.adapt_prediction(
            origin, previous, cold, self.cfg
        )
        other, other_detail = independent._adapt(
            {"origin_visible": origin.tolist()}, previous, cold, self.cfg
        )
        np.testing.assert_allclose(primary, other, rtol=0.0, atol=0.0)
        self.assertEqual(primary_detail, other_detail)
        np.testing.assert_allclose(
            primary_detail["innovation_physical"], [0.01, -0.01, 500.0]
        )
        self.assertFalse(primary_detail["clip_activated"])
        self.assertAlmostEqual(primary[0, 0], origin[0] + 0.1 * 0.01 * 0.1 / 0.03)
        self.assertAlmostEqual(primary[0, 1], origin[1] - 0.1 * 0.01 * 0.1 / 0.03)

    def test_adaptation_clips_only_frozen_dynamic_components(self) -> None:
        origin = np.array([0.5, -0.5, 2.0, -2.0, 1.0])
        previous = np.zeros((12, 5))
        cold = np.zeros((12, 5))
        result, detail = innovation.adapt_prediction(origin, previous, cold, self.cfg)
        self.assertTrue(detail["clip_activated"])
        np.testing.assert_allclose(
            detail["clipped_innovation_physical"], [0.02, -0.02, 1000.0]
        )
        np.testing.assert_allclose(result[0, 2:5], [0.2, -0.2, 0.1])
        np.testing.assert_allclose(result[1, 2:5], [0.16, -0.16, 0.08])

    def _tube_rows(self) -> list[dict[str, object]]:
        rows = []
        for pair in range(20):
            for history in ("minus_first", "plus_first"):
                for origin in range(11, 25):
                    scale = (1.0 + pair + (history == "plus_first") + origin / 100.0) * 1e-5
                    rows.append(
                        {
                            "row_id": f"p{pair}|{history}|{origin}",
                            "pair_id": f"p{pair}",
                            "history_member": history,
                            "absolute_residual_physical": np.full((12, 5), scale).tolist(),
                        }
                    )
        return rows

    def test_context_tube_matches_independent(self) -> None:
        rows = self._tube_rows()
        primary_tube, primary_detail = innovation.context_robust_tube(rows, self.cfg)
        other_tube, other_detail = independent._tube(rows, self.cfg)
        np.testing.assert_allclose(primary_tube, other_tube, rtol=0.0, atol=0.0)
        self.assertEqual(primary_detail, other_detail)
        self.assertEqual(len(primary_detail["per_context_q90_row_ratios"]), 40)
        self.assertEqual(
            primary_detail["scalar"], 2.0 * primary_detail["calibration_ratio"]
        )

    def test_usefulness_gate_pass_and_static_fallback(self) -> None:
        cold, adapted = [], []
        for pair in range(20):
            for history in ("minus_first", "plus_first"):
                for origin in range(11, 25):
                    common = {
                        "row_id": f"p{pair}|{history}|{origin}",
                        "pair_id": f"p{pair}",
                        "history_member": history,
                    }
                    cold.append({**common, "mean_squared_scaled_error": 1.0})
                    adapted.append({**common, "mean_squared_scaled_error": 0.9})
        primary = innovation.usefulness(cold, adapted, self.cfg)
        other = independent._usefulness(cold, adapted, self.cfg)
        self.assertEqual(primary, other)
        self.assertTrue(primary["passed"])
        self.assertEqual(primary["strictly_improved_context_count"], 40)
        unchanged = [{**row, "mean_squared_scaled_error": 1.0} for row in adapted]
        self.assertFalse(innovation.usefulness(cold, unchanged, self.cfg)["passed"])

    def test_contract_rejects_postresult_innovation_tuning(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["innovation_contract"]["persistence"] = 0.81
        with self.assertRaisesRegex(ValueError, "innovation"):
            contract.validate_config(changed)

    def test_parser_has_fail_closed_zero_tsc_phase_order(self) -> None:
        choices = next(
            action.choices for action in audit._parser()._actions if action.dest == "command"
        )
        self.assertEqual(tuple(choices), ("offline", "primary", "postprocess"))

    def test_independent_does_not_import_primary_or_control_implementation(self) -> None:
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r6_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("causal_one_step_innovation_observer_audit", source)
        self.assertNotIn("from tsc_rzip_rllib.control", source)

    def test_launcher_pins_existing_server_virtual_environment(self) -> None:
        source = (
            ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r6_shell_common.sh"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source
        )
        self.assertNotIn("python3", source)


if __name__ == "__main__":
    unittest.main()
