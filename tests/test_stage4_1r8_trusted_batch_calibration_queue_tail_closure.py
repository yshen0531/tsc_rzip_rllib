from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8


class Stage41R8SelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = {
            "delay_candidates": [0, 1, 2],
            "slew_candidates": [0.9, 1.0, 1.1],
            "nominal_coil_count": 14,
            "minimum_full_delta_log_likelihood": 50.0,
            "minimum_split_delta_log_likelihood": 20.0,
            "minimum_clean_score_ratio": 10.0,
            "minimum_clean_absolute_score_gap": 1e-12,
            "require_full_first_second_odd_even_consensus": True,
            "require_leave_one_out_consensus": True,
            "selector_revision": "unit_test",
        }
        self.keys = [r8._candidate_key(d, s) for d in (0, 1, 2) for s in (0.9, 1.0, 1.1)]

    def test_strong_batch_evidence_is_trusted(self) -> None:
        rows = []
        for step in range(10):
            row = {key: 0.08 + step * 1e-3 for key in self.keys}
            row[r8._candidate_key(2, 1.1)] = 0.006 + step * 1e-4
            row[r8._candidate_key(2, 1.0)] = 0.030 + step * 1e-4
            rows.append(row)
        result = r8.trusted_batch_select_from_residuals(
            rows, noise_sigma_a=0.02, nominal_max_delta_a=3.0, selector_cfg=self.cfg
        )
        self.assertTrue(result["trusted"])
        self.assertEqual(result["selected_delay_steps"], 2)
        self.assertAlmostEqual(result["selected_slew_scale"], 1.1)
        self.assertEqual(result["rejection_reasons"], [])

    def test_ambiguous_batch_never_falls_back_to_default(self) -> None:
        rows = [{key: 0.01 for key in self.keys} for _ in range(10)]
        result = r8.trusted_batch_select_from_residuals(
            rows, noise_sigma_a=0.02, nominal_max_delta_a=3.0, selector_cfg=self.cfg
        )
        self.assertFalse(result["trusted"])
        self.assertIsNone(result["selected_delay_steps"])
        self.assertIsNone(result["selected_slew_scale"])
        self.assertIn("full_likelihood_gap_below_threshold", result["rejection_reasons"])

    def test_split_disagreement_is_rejected(self) -> None:
        rows = []
        for step in range(10):
            row = {key: 0.08 for key in self.keys}
            best = r8._candidate_key(0, 0.9) if step < 5 else r8._candidate_key(2, 1.1)
            row[best] = 0.001
            rows.append(row)
        result = r8.trusted_batch_select_from_residuals(
            rows, noise_sigma_a=0.02, nominal_max_delta_a=3.0, selector_cfg=self.cfg
        )
        self.assertFalse(result["trusted"])
        self.assertIn("split_best_disagreement", result["rejection_reasons"])

    def test_candidate_bank_mismatch_is_hard_error(self) -> None:
        with self.assertRaises(ValueError):
            r8.trusted_batch_select_from_residuals(
                [{"d0_s1.000": 0.0}] * 10,
                noise_sigma_a=0.02,
                nominal_max_delta_a=3.0,
                selector_cfg=self.cfg,
            )


class Stage41R8QueueTests(unittest.TestCase):
    def test_pending_queue_is_drained_in_issue_order_before_zero(self) -> None:
        issued = [np.asarray([float(step), -float(step), 0.1 * step]) for step in range(35)]
        trace = [{"issued_mode_coefficients": row.tolist()} for row in issued]
        plan = r8._tail_queue_plan(trace, actual_delay=2, tail_steps=4)
        self.assertEqual([row["source"] for row in plan], [
            "pending_issued_command",
            "pending_issued_command",
            "zero_current_increment_after_queue_empty",
            "zero_current_increment_after_queue_empty",
        ])
        self.assertEqual([row["source_control_step"] for row in plan[:2]], [33, 34])
        np.testing.assert_allclose(plan[0]["command_mode_coefficients"], issued[33])
        np.testing.assert_allclose(plan[1]["command_mode_coefficients"], issued[34])
        np.testing.assert_allclose(plan[2]["command_mode_coefficients"], np.zeros(3))
        self.assertEqual(plan[-1]["pending_count_after_pop"], 0)

    def test_delay_zero_has_no_synthetic_pending_command(self) -> None:
        issued = [np.ones(3) for _ in range(35)]
        trace = [{"issued_mode_coefficients": row.tolist()} for row in issued]
        plan = r8._tail_queue_plan(trace, actual_delay=0, tail_steps=2)
        self.assertTrue(all(row["source"] == "zero_current_increment_after_queue_empty" for row in plan))

    def test_tail_shorter_than_pending_queue_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            trace = [{"issued_mode_coefficients": np.ones(3).tolist()} for _ in range(35)]
            r8._tail_queue_plan(trace, actual_delay=2, tail_steps=1)


class Stage41R8TraceComparisonTests(unittest.TestCase):
    @staticmethod
    def _result(offset: float = 0.0) -> dict:
        trajectory = []
        for step in range(3):
            trajectory.append({
                "R": 1.7 + offset + 1e-3 * step,
                "Z": -1.0 + 2e-3 * step,
                "Ip": 2.5e6 + step,
                "currents_a_tsc": [float(index + step) for index in range(14)],
                "action_norm_tsc": [0.01 * (index + step) for index in range(14)],
            })
        return {
            "trajectory": trajectory,
            "control_trace": [
                {"issued_mode_coefficients": [1.0, 2.0, 3.0]},
                {"issued_mode_coefficients": [0.5, -0.5, 0.0]},
            ],
            "tail_queue_trace": [
                {"command_mode_coefficients": [0.5, -0.5, 0.0]},
                {"command_mode_coefficients": [0.0, 0.0, 0.0]},
            ],
        }

    def test_raw_trace_comparison_checks_exact_and_numeric_equality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calibrated = root / "calibrated"
            oracle = root / "oracle"
            (calibrated / "raw").mkdir(parents=True)
            (oracle / "raw").mkdir(parents=True)
            r8.atomic_write_json_gz(calibrated / "raw" / "cal.json.gz", self._result())
            r8.atomic_write_json_gz(oracle / "raw" / "oracle.json.gz", self._result())
            ctx = SimpleNamespace(paths=SimpleNamespace(
                calibrated_startup=calibrated, oracle_queue_tail=oracle
            ))
            comparison = r8._trace_comparison(
                ctx, {"experiment_id": "cal"}, {"experiment_id": "oracle"}, atol=1e-12
            )
            self.assertTrue(comparison["exact_equal"])
            self.assertTrue(comparison["numeric_equal"])
            modified = self._result(offset=5e-13)
            r8.atomic_write_json_gz(calibrated / "raw" / "cal.json.gz", modified)
            comparison = r8._trace_comparison(
                ctx, {"experiment_id": "cal"}, {"experiment_id": "oracle"}, atol=1e-12
            )
            self.assertFalse(comparison["exact_equal"])
            self.assertTrue(comparison["numeric_equal"])
            self.assertGreater(comparison["physics_max_abs_difference"], 0.0)



class Stage41R8SummaryTests(unittest.TestCase):
    def _ctx(self) -> SimpleNamespace:
        config_path = Path(__file__).resolve().parents[1] / "configs" / "stage4_1r8_trusted_batch_calibration_queue_tail_closure_410ms.json"
        return SimpleNamespace(cfg=json.loads(config_path.read_text(encoding="utf-8")))

    def _row(self, policy_id: str, target: str, delay: int, slew: float, margin: float = 0.1) -> dict:
        return {
            "policy_id": policy_id,
            "target_id": target,
            "actual_action_delay_steps": delay,
            "actual_slew_scale": slew,
            "success": True,
            "stage3_4_target_tracking_pass": True,
            "stage3_4_tracking_minimum_signed_margin": margin,
            "pending_queue_fully_drained": True,
            "zero_action_while_pending_count": 0,
        }

    def test_oracle_policy_selection_requires_complete_campaign(self) -> None:
        ctx = self._ctx()
        one = self._row("drain_pending_h37", "nominal", 0, 0.9)
        summary = r8.summarize_oracle_queue_tail(ctx, [one])
        self.assertFalse(summary["coverage_complete"])
        self.assertFalse(summary["passed"])
        self.assertIsNone(summary["selected_policy_id"])

    def test_shortest_complete_passing_policy_is_selected(self) -> None:
        ctx = self._ctx()
        rows = []
        for policy in ctx.cfg["oracle_queue_tail"]["policies"]:
            for target in ("nominal", "RZ_p10_m10"):
                for delay in (0, 1, 2):
                    for slew in (0.9, 1.0, 1.1):
                        rows.append(self._row(policy["policy_id"], target, delay, slew, margin=0.05))
        summary = r8.summarize_oracle_queue_tail(ctx, rows)
        self.assertTrue(summary["coverage_complete"])
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["selected_policy_id"], "drain_pending_h37")

    def test_source_config_encodes_no_gate_weakening(self) -> None:
        ctx = self._ctx()
        gate = ctx.cfg["gate"]
        self.assertAlmostEqual(gate["precise_tolerance_m"], 0.03)
        self.assertAlmostEqual(gate["terminal_velocity_max_m_per_s"], 0.1)
        self.assertAlmostEqual(gate["late_velocity_rms_max_m_per_s"], 0.1)
        self.assertTrue(ctx.cfg["source_requirement"]["allow_paired_confirmation_failure"])
        self.assertFalse(ctx.cfg["calibrated_startup"]["online_handover_enabled"])
        self.assertAlmostEqual(
            ctx.cfg["integrated_calibration"]["maximum_final_max_abs_coil_residual_A"], 0.01
        )
        self.assertAlmostEqual(
            ctx.cfg["calibrated_startup"]["numeric_trace_equivalence_atol"], 1e-12
        )


if __name__ == "__main__":
    unittest.main()
