from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r7_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as campaign,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel as contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_370ms.json"
)


class FreshMultipulseStaticObserverInteractionSentinelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_contract_and_self_test(self) -> None:
        contract.validate_config(self.cfg, project_root=ROOT)
        result = contract.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["context_count"], 16)
        self.assertEqual(result["baseline_rollouts"], 16)
        self.assertEqual(result["multipulse_rollouts"], 32)
        self.assertEqual(result["issue_windows"], 128)
        self.assertEqual(
            result["signed_direction_coverage"],
            {0: [-1, 1], 1: [-1, 1], 2: [-1, 1], 3: [-1, 1]},
        )

    def test_frozen_scope_schedule_and_model(self) -> None:
        rollout = self.cfg["rollout_contract"]
        self.assertEqual(rollout["issue_task_steps"], [10, 14, 18, 22])
        self.assertEqual(rollout["maximum_new_rollouts"], 48)
        schedule = self.cfg["schedule_contract"]
        self.assertEqual(schedule["schedule_a"]["directions"], [0, 1, 2, 3])
        self.assertEqual(schedule["schedule_b"]["directions"], [3, 2, 1, 0])
        self.assertEqual(schedule["schedule_a"]["signs"], [1, -1, 1, -1])
        self.assertEqual(schedule["schedule_b"]["signs"], [1, -1, 1, -1])
        self.assertFalse(self.cfg["static_model_contract"]["adaptation_enabled"])
        self.assertFalse(self.cfg["all_stage_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["mpc_validated"])
        self.assertFalse(self.cfg["gate_a_qualified"])
        self.assertFalse(self.cfg["bc_dagger_or_rl_allowed"])

    def test_contract_rejects_schedule_gate_and_adaptation_mutation(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["schedule_a"]["signs"][0] = -1
        with self.assertRaisesRegex(ValueError, "schedule"):
            contract.validate_config(changed)
        changed = copy.deepcopy(self.cfg)
        changed["gates"]["multipulse_required_point_pass_count"] = 115
        with self.assertRaisesRegex(ValueError, "qualification"):
            contract.validate_config(changed)
        changed = copy.deepcopy(self.cfg)
        changed["static_model_contract"]["adaptation_enabled"] = True
        with self.assertRaisesRegex(ValueError, "predictor"):
            contract.validate_config(changed)

    @staticmethod
    def _row(
        context: str,
        *,
        direction: int | None = None,
        sign: int | None = None,
        passed: bool = True,
    ) -> dict[str, object]:
        return {
            "context_id": context,
            "direction_index": direction,
            "sign": sign,
            "point_passed": passed,
            "tube_contained": passed,
            "finite_exclusion_violation_count": 0,
            "absolute_residual_physical": np.zeros((4, 5)).tolist(),
            "maximum_absolute_scaled_point_error": 0.0,
        }

    def test_baseline_gate_is_context_stratified(self) -> None:
        rows = [self._row(f"c{context}") for context in range(16) for _ in range(4)]
        result = campaign._evaluate_prediction_rows(rows, "baseline", self.cfg)
        self.assertTrue(result["passed"])
        rows[0]["point_passed"] = False
        rows[0]["tube_contained"] = False
        rows[1]["point_passed"] = False
        rows[1]["tube_contained"] = False
        result = campaign._evaluate_prediction_rows(rows, "baseline", self.cfg)
        self.assertEqual(result["point_pass_count"], 62)
        self.assertFalse(result["context_counts"]["c0"]["passed"])
        self.assertFalse(result["passed"])

    def test_multipulse_gate_is_context_direction_and_sign_stratified(self) -> None:
        signed_directions = (
            (0, 1),
            (1, -1),
            (2, 1),
            (3, -1),
            (3, 1),
            (2, -1),
            (1, 1),
            (0, -1),
        )
        rows = [
            self._row(f"c{context}", direction=direction, sign=sign)
            for context in range(16)
            for direction, sign in signed_directions
        ]
        result = campaign._evaluate_prediction_rows(rows, "multipulse", self.cfg)
        self.assertTrue(result["passed"])
        rows[0]["point_passed"] = False
        rows[0]["tube_contained"] = False
        rows[1]["point_passed"] = False
        rows[1]["tube_contained"] = False
        result = campaign._evaluate_prediction_rows(rows, "multipulse", self.cfg)
        self.assertEqual(result["point_pass_count"], 126)
        self.assertFalse(result["context_counts"]["c0"]["passed"])
        self.assertFalse(result["passed"])

    def test_response_descriptor_is_causal(self) -> None:
        visible = np.arange(40 * 5, dtype=float).reshape(40, 5) / 100.0
        spec = {
            "target_R_offset_m": 0.01,
            "target_Z_offset_m": -0.02,
            "target_Ip_offset_A": 5000.0,
        }
        original = campaign._response_descriptor(visible, spec, 22, self.cfg)
        future_changed = visible.copy()
        future_changed[23:] += 1e6
        np.testing.assert_array_equal(
            original,
            campaign._response_descriptor(future_changed, spec, 22, self.cfg),
        )
        present_changed = visible.copy()
        present_changed[22, 0] += 1.0
        self.assertFalse(
            np.array_equal(
                original,
                campaign._response_descriptor(present_changed, spec, 22, self.cfg),
            )
        )

    def test_parsers_are_fail_closed(self) -> None:
        primary_choices = next(
            action.choices
            for action in campaign._parser()._actions
            if action.dest == "command"
        )
        self.assertEqual(
            tuple(primary_choices),
            (
                "offline",
                "authorize-baseline",
                "baseline",
                "evaluate-baseline",
                "authorize-multipulse",
                "multipulse",
                "finalize",
                "postprocess",
            ),
        )
        independent_choices = next(
            action.choices
            for action in independent._parser()._actions
            if action.dest == "audit_kind"
        )
        self.assertEqual(
            tuple(independent_choices),
            (
                "offline",
                "baseline_raw",
                "baseline_model",
                "multipulse_raw",
                "multipulse_model",
            ),
        )

    def test_independent_does_not_import_primary_campaign(self) -> None:
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r7_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("interaction_campaign as campaign", source)
        self.assertNotIn("campaign._prediction_rows", source)
        self.assertNotIn("campaign._evaluate_prediction_rows", source)

    def test_launcher_pins_existing_server_virtual_environment(self) -> None:
        source = (
            ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r7_shell_common.sh"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source
        )
        self.assertNotIn("python3", source)
        launchers = "\n".join(
            (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "run_stage4_2r3c3t13s24d1r14r8r7_common.sh",
                "run_stage4_2r3c3t13s24d1r14r8r7_native.sh",
                "run_stage4_2r3c3t13s24d1r14r8r7_nohup.sh",
            )
        )
        self.assertNotIn("python3", launchers)
        self.assertNotIn("tar ", launchers)
        self.assertNotIn("unzip", launchers)


if __name__ == "__main__":
    unittest.main()
