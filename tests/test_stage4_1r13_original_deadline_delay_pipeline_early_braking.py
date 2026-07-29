from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r13_original_deadline_delay_pipeline_early_braking as r13


class Stage41R13ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = Path(r13.__file__).resolve().parents[2]
        cls.config_path = cls.project / "configs" / "stage4_1r13_original_deadline_delay_pipeline_early_braking_370ms.json"
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_immutable_contract_and_early_bank(self) -> None:
        r13.validate_config(self.cfg)
        timing = self.cfg["formal_timing_contract"]
        self.assertEqual((timing["normal_slew"]["arrival_deadline_step"], timing["normal_slew"]["horizon_steps"]), (25, 35))
        self.assertEqual((timing["weak_slew"]["arrival_deadline_step"], timing["weak_slew"]["horizon_steps"]), (27, 37))
        affected = [row["first_affected_state_step"] for row in self.cfg["early_braking_closure"]["candidate_bank"]]
        self.assertEqual(affected, [20, 21, 22, 23, 24, 25, 26])
        self.assertFalse(self.cfg["early_braking_closure"]["arrival_deadline_expansion_allowed"])
        self.assertTrue(self.cfg["stage4_2r1_was_not_run_or_reused"])

    def test_candidate_after_latest_feasible_state_is_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["early_braking_closure"]["candidate_bank"][-1]["first_affected_state_step"] = 27
        bad["early_braking_closure"]["candidate_first_affected_state_steps"][-1] = 27
        with self.assertRaisesRegex(ValueError, "states 20--26"):
            r13.validate_config(bad)

    def test_deadline_expansion_is_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"].append(28)
        with self.assertRaisesRegex(ValueError, "270 ms"):
            r13.validate_config(bad)

    def test_issue_effect_alignment_for_both_delays(self) -> None:
        for first in range(20, 27):
            for delay in (1, 2):
                issue = r13._transition_issue_step(first, delay)
                self.assertEqual(issue + delay + 1, first)
                self.assertLess(issue, first)

    def test_self_test_budget_and_scope(self) -> None:
        payload = r13.self_test(self.project)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["development_rollout_count"], 28)
        self.assertEqual(payload["calibrated_rollout_count_if_development_passes"], 4)
        self.assertEqual(payload["maximum_true_tsc_rollouts"], 32)
        self.assertTrue(payload["selection_uses_both_required_targets"])
        self.assertFalse(payload["unseen_target_holdout_claimed"])


class Stage41R13SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project = Path(r13.__file__).resolve().parents[2]
        cls.cfg = json.loads(
            (project / "configs" / "stage4_1r13_original_deadline_delay_pipeline_early_braking_370ms.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def _row(target: str, delay: int, *, passed: bool = True, margin: float = 0.1, first: int = 24) -> dict:
        return {
            "policy_id": "p",
            "target_id": target,
            "actual_delay_steps": delay,
            "r13_composite_pass": passed,
            "formal_contract_minimum_signed_margin": margin,
            "terminal_speed_m_per_s": 0.04,
            "action_rms": 0.2,
            "first_affected_state_step": first,
            "physics_prefix_exact": True,
            "issued_prefix_exact": True,
            "applied_prefix_exact": True,
            "no_future_measurement": True,
            "streaming_queue_consistent": True,
        }

    def test_candidate_summary_requires_both_targets_per_delay(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        rows = [self._row("nominal", 1), self._row("RZ_p10_m10", 1)]
        summary = r13._candidate_summary(ctx, rows, policy_id="p", delay=1)
        self.assertTrue(summary["passed"])
        self.assertTrue(summary["target_coverage_complete"])
        one = r13._candidate_summary(ctx, rows[:1], policy_id="p", delay=1)
        self.assertFalse(one["passed"])
        self.assertFalse(one["target_coverage_complete"])

    def test_candidate_summary_rejects_one_failed_required_target(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        rows = [self._row("nominal", 2), self._row("RZ_p10_m10", 2, passed=False, margin=-0.01)]
        summary = r13._candidate_summary(ctx, rows, policy_id="p", delay=2)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["target_pass_fraction"], 0.5)

    def test_development_specs_cover_7_by_2_by_2(self) -> None:
        nested_r8 = object()
        ctx = SimpleNamespace(
            cfg=self.cfg,
            r12_ctx=SimpleNamespace(
                r11_ctx=SimpleNamespace(
                    r10_ctx=SimpleNamespace(
                        r9_ctx=SimpleNamespace(r8_ctx=nested_r8)
                    )
                )
            ),
        )

        def fake_main_extra(_ctx, *, actual_delay, actual_slew, modeled_delay, modeled_slew, **_kwargs):
            return {
                "action_delay_steps": int(actual_delay),
                "controller_action_delay_steps": int(modeled_delay),
                "slew_scale": float(actual_slew),
                "controller_slew_scale_estimate": float(modeled_slew),
                "trusted_calibration_model": True,
            }

        with mock.patch.object(r13, "materialize_variant", return_value=("v", {})), mock.patch.object(
            r13.r8, "_main_extra", side_effect=fake_main_extra
        ), mock.patch.object(r13, "_source_scale", return_value=1.0):
            specs = r13.build_development_specs(ctx)
        self.assertEqual(len(specs), 28)
        self.assertEqual({spec["target_id"] for spec in specs}, {"nominal", "RZ_p10_m10"})
        self.assertEqual({spec["action_delay_steps"] for spec in specs}, {1, 2})
        self.assertEqual({spec["anticipatory_first_affected_state_step"] for spec in specs}, set(range(20, 27)))
        self.assertEqual(len({spec["experiment_id"] for spec in specs}), 28)


class Stage41R13CausalityTests(unittest.TestCase):
    @staticmethod
    def _trajectory(n: int = 38) -> list[dict]:
        return [
            {
                "R": 1.0 + 1e-4 * index,
                "Z": -1.0 - 2e-4 * index,
                "Ip": 1000.0 + index,
                "currents_a_tsc": [float(index)] * 14,
                "currents_a_display": [float(index)] * 14,
                "action_norm_tsc": [0.0] * 14,
            }
            for index in range(n)
        ]

    @staticmethod
    def _control(n: int = 37) -> list[dict]:
        return [
            {
                "issued_mode_coefficients": [float(index), 0.0, 0.0],
                "applied_command_mode_coefficients": [float(index), 0.0, 0.0],
            }
            for index in range(n)
        ]

    def test_early_effect_prefix_audit_allows_only_causal_boundary_change(self) -> None:
        first = 24
        delay = 2
        issue = r13._transition_issue_step(first, delay)
        source = {"trajectory": self._trajectory(), "control_trace": self._control()}
        result = copy.deepcopy(source)
        result["spec"] = {
            "anticipatory_first_affected_state_step": first,
            "action_delay_steps": delay,
        }
        result["anticipatory_damping_trace"] = [
            {
                "future_measurement_used": False,
                "measurement_max_state_index_used": issue,
                "state_index_before": issue,
            }
        ]
        result["anticipatory_damping_summary"] = {
            "streaming_queue_consistent": True,
            "damping_control_steps": 1,
            "observed_first_affected_state_step": first,
        }
        result["control_trace"][issue]["issued_mode_coefficients"][0] += 1.0
        result["trajectory"][first]["R"] += 0.01
        audit = r13._prefix_audit(source, result, atol=1e-12)
        self.assertTrue(audit["physics_prefix_exact"])
        self.assertTrue(audit["issued_prefix_exact"])
        self.assertTrue(audit["applied_prefix_exact"])
        self.assertTrue(audit["no_future_measurement"])
        self.assertTrue(audit["first_effect_alignment_exact"])
        result["trajectory"][first - 1]["R"] += 0.01
        self.assertFalse(r13._prefix_audit(source, result, atol=1e-12)["physics_prefix_exact"])

    def test_future_measurement_is_rejected(self) -> None:
        source = {"trajectory": self._trajectory(), "control_trace": self._control()}
        result = copy.deepcopy(source)
        result["spec"] = {"anticipatory_first_affected_state_step": 24, "action_delay_steps": 1}
        result["anticipatory_damping_trace"] = [
            {"future_measurement_used": True, "measurement_max_state_index_used": 24, "state_index_before": 22}
        ]
        result["anticipatory_damping_summary"] = {
            "streaming_queue_consistent": True,
            "damping_control_steps": 1,
            "observed_first_affected_state_step": 24,
        }
        audit = r13._prefix_audit(source, result, atol=1e-12)
        self.assertFalse(audit["no_future_measurement"])

    def test_worker_preserves_r13_revision_while_reusing_validated_r12_worker(self) -> None:
        fake = mock.Mock()
        fake.evaluate.return_value = {"success": True, "spec": {}, "trajectory": [], "control_trace": []}
        with mock.patch.object(r13.r12, "LocalStage41R12Worker", return_value=fake):
            worker = r13.LocalStage41R13Worker({}, {}, {}, "w", {})
            result = worker.evaluate({})
            worker.close()
        self.assertEqual(result["controller_revision"], r13.CONTROLLER_REVISION)
        self.assertTrue(result["stage4_1r13_uses_r12_validated_streaming_worker"])
        fake.close.assert_called_once()


class Stage41R13FeasibilityTests(unittest.TestCase):
    def test_state27_only_lower_bound_detects_structural_impossibility(self) -> None:
        # Four-point RMS includes states 24--27. If states 24--26 alone already
        # contribute more than 4*(0.1)^2, no action first affecting state 27 can pass.
        speed_24_26 = np.asarray([0.13, 0.12, 0.11])
        lower = float(np.sqrt(np.sum(speed_24_26**2) / 4.0))
        self.assertGreater(lower, 0.1)

    def test_source_and_post_damping_limiting_components_are_not_conflated(self) -> None:
        source_endpoint = {
            "position_signed_margin": 0.4,
            "endpoint_speed_signed_margin": 0.1,
            "endpoint_late_speed_signed_margin": -0.017,
            "post_speed_signed_margin": 0.2,
            "final_speed_signed_margin": -0.021,
            "ip_signed_margin": 0.9,
            "stage3_4_ip_terminal_signed_margin": 0.9,
            "stage3_4_ip_hold_rms_signed_margin": 0.9,
            "stage3_4_ip_sustained_signed_margin": 0.9,
        }
        post_damping = dict(source_endpoint)
        post_damping["final_speed_signed_margin"] = 0.7
        self.assertEqual(r13._limiting_component(source_endpoint)[0], "final_speed")
        self.assertEqual(r13._limiting_component(post_damping)[0], "endpoint_late_speed")

    def test_latest_candidate_is_state26_not_post_deadline(self) -> None:
        project = Path(r13.__file__).resolve().parents[2]
        cfg = json.loads(
            (project / "configs" / "stage4_1r13_original_deadline_delay_pipeline_early_braking_370ms.json").read_text(encoding="utf-8")
        )
        self.assertEqual(cfg["r12_design_audit"]["latest_globally_feasible_first_affected_state_step"], 26)
        self.assertLessEqual(max(cfg["early_braking_closure"]["candidate_first_affected_state_steps"]), 26)


if __name__ == "__main__":
    unittest.main()
