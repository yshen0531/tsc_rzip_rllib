from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_1r11_frozen_terminal_long_horizon_hold as r11,
)


class Stage41R11ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = (
            Path(r11.__file__).resolve().parents[2]
            / "configs"
            / "stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_config_is_valid_and_policy_is_frozen(self) -> None:
        r11.validate_config(self.cfg)
        hold = self.cfg["long_hold"]
        self.assertEqual(hold["horizon_steps"], 200)
        self.assertEqual(hold["tail_feedback_steps"], 165)
        self.assertEqual(hold["uniform_hold_start_step"], 65)
        self.assertEqual(hold["require_exact_source_prefix_through_step"], 75)
        self.assertTrue(hold["no_policy_retuning_allowed"])
        self.assertTrue(hold["no_new_arrival_search_allowed"])
        self.assertEqual(
            hold["selected_policy"]["policy_id"],
            "qp28_c0p50_v1p50_p1p25_position",
        )

    def test_gate_weakening_is_rejected(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["gate"]["position_box_max_m"] = 0.031
        with self.assertRaisesRegex(ValueError, "30 mm"):
            r11.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["gate"]["velocity_max_m_per_s"] = 0.11
        with self.assertRaisesRegex(ValueError, "0.1 m/s"):
            r11.validate_config(cfg)

    def test_policy_retuning_or_endpoint_search_is_rejected(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["long_hold"]["selected_policy"]["position_measurement_gain"] = 1.3
        with self.assertRaisesRegex(ValueError, "frozen policy"):
            r11.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["long_hold"]["no_new_arrival_search_allowed"] = False
        with self.assertRaisesRegex(ValueError, "endpoint search"):
            r11.validate_config(cfg)

    def test_scenario_digest_is_stable_and_revision_scoped(self) -> None:
        payload = {"b": [2, 3], "a": 1}
        first = r11._scenario_digest(payload)
        second = r11._scenario_digest({"a": 1, "b": [2, 3]})
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("s41r11_"))
        self.assertEqual(len(first), len("s41r11_") + 20)

    def test_self_test_passes(self) -> None:
        payload = r11.self_test()
        self.assertTrue(payload["passed"])
        self.assertTrue(payload["r10_preview_queue_semantics_retained"])
        self.assertTrue(payload["long_hold_metric_arithmetic_passed"])


class Stage41R11PrefixTests(unittest.TestCase):
    @staticmethod
    def _result(horizon: int) -> dict:
        trajectory = []
        for index in range(horizon + 1):
            trajectory.append(
                {
                    "R": 1.0 + index * 1e-6,
                    "Z": -1.0 - index * 2e-6,
                    "Ip": 1000.0 + index,
                    "vessel_current_total_a": float(index),
                    "vessel_current_abs_sum_a": float(index + 1),
                    "vessel_current_rms_a": float(index + 2),
                    "vessel_current_max_abs_a": float(index + 3),
                    "currents_a_tsc": [float(index + j) for j in range(14)],
                }
            )
        control = [
            {
                "issued_mode_coefficients": [index, index + 1, index + 2],
                "applied_command_mode_coefficients": [index - 1, index, index + 1],
            }
            for index in range(35)
        ]
        original = copy.deepcopy(control)
        preview = [
            {
                "issued_mode_coefficients": [index, 0.0, 0.0],
                "applied_mode_coefficients": [index - 1, 0.0, 0.0],
            }
            for index in range(2)
        ]
        terminal = [
            {
                "issued_mode_coefficients": [index * 0.01, 0.0, 0.0],
                "applied_mode_coefficients": [(index - 2) * 0.01, 0.0, 0.0],
            }
            for index in range(max(horizon - 35, 0))
        ]
        return {
            "spec": {"target_id": "nominal", "action_delay_steps": 2, "slew_scale": 1.0},
            "trajectory": trajectory,
            "control_trace": control,
            "original_main_control_trace": original,
            "transition_preview_trace": preview,
            "terminal_feedback_trace": terminal,
        }

    def test_prefix_comparison_uses_exact_first_750ms_only(self) -> None:
        source = self._result(75)
        extended = self._result(200)
        ctx = SimpleNamespace()
        with mock.patch.object(
            r11,
            "_source_selected_oracle_raw",
            return_value={("nominal", 2, 1.0): source},
        ):
            exact = r11._source_prefix_comparison(ctx, extended, atol=1e-12)
            self.assertTrue(exact["exact"])
            extended["trajectory"][76]["R"] += 99.0
            after_prefix = r11._source_prefix_comparison(ctx, extended, atol=1e-12)
            self.assertTrue(after_prefix["exact"])
            extended["trajectory"][75]["R"] += 1e-5
            changed_prefix = r11._source_prefix_comparison(ctx, extended, atol=1e-12)
            self.assertFalse(changed_prefix["exact"])
            self.assertFalse(changed_prefix["numeric"])


class Stage41R11MetricTests(unittest.TestCase):
    @classmethod
    def _ctx(cls) -> SimpleNamespace:
        cfg_path = (
            Path(r11.__file__).resolve().parents[2]
            / "configs"
            / "stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json"
        )
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        base34 = SimpleNamespace(
            cfg={"target": {"R": 1.0, "Z": -1.0, "Ip": 1000.0}},
            env_cfg={
                "min_current_a_display_order": [-100.0] * 14,
                "max_current_a_display_order": [100.0] * 14,
            },
        )
        r3_ctx = SimpleNamespace(base34=base34)
        r4_ctx = SimpleNamespace(r3_ctx=r3_ctx)
        r5_ctx = SimpleNamespace(r4_ctx=r4_ctx)
        r6_ctx = SimpleNamespace(r5_ctx=r5_ctx)
        r7_ctx = SimpleNamespace(r6_ctx=r6_ctx)
        r8_ctx = SimpleNamespace(r7_ctx=r7_ctx)
        r9_ctx = SimpleNamespace(r8_ctx=r8_ctx)
        r10_ctx = SimpleNamespace(r9_ctx=r9_ctx)
        return SimpleNamespace(cfg=cfg, r10_ctx=r10_ctx)

    @staticmethod
    def _passing_result() -> dict:
        horizon = 200
        target = np.asarray([1.0, -1.0, 1000.0])
        trajectory = []
        for index in range(horizon + 1):
            decay = math.exp(-index / 25.0)
            state = target + np.asarray([0.01 * decay, -0.01 * decay, 100.0 * decay])
            trajectory.append(
                {
                    "R": float(state[0]),
                    "Z": float(state[1]),
                    "Ip": float(state[2]),
                    "currents_a_tsc": [0.0] * 14,
                    "currents_a_display": [0.0] * 14,
                    "action_norm_tsc": [0.0] * 14,
                    "vessel_current_total_a": 0.0,
                    "vessel_current_abs_sum_a": 0.0,
                    "vessel_current_rms_a": 0.0,
                    "vessel_current_max_abs_a": 0.0,
                    "abnormal": False,
                }
            )
        terminal = []
        for index in range(165):
            terminal.append(
                {
                    "issued_desired_physical_mode_coefficients": [0.0, 0.0, 0.0],
                    "issued_mode_coefficients": [0.0, 0.0, 0.0],
                    "applied_mode_coefficients": [0.0, 0.0, 0.0],
                    "currents_after_A": [0.0] * 14,
                    "solver_success": True,
                }
            )
        return {
            "experiment_id": "synthetic-pass",
            "spec": {
                "scenario": "synthetic",
                "target_id": "nominal",
                "terminal_policy_id": "qp28_c0p50_v1p50_p1p25_position",
                "action_delay_steps": 0,
                "controller_action_delay_steps": 0,
                "slew_scale": 1.0,
                "controller_slew_scale_estimate": 1.0,
                "calibration_token": None,
                "trusted_calibration_model": True,
                "target_R_offset_m": 0.0,
                "target_Z_offset_m": 0.0,
                "target_Ip_offset_A": 0.0,
            },
            "success": True,
            "failure_reason": "",
            "trajectory": trajectory,
            "terminal_feedback_trace": terminal,
            "terminal_feedback_summary": {
                "continuous_streaming_queue": True,
                "streaming_queue_consistent": True,
                "pending_queue_bypassed": False,
                "maximum_final_pending_desired_physical_norm": 0.0,
            },
            "control_trace": [],
            "original_main_control_trace": [],
            "transition_preview_trace": [],
        }

    def test_fixed_hold_metrics_pass_for_stationary_synthetic_case(self) -> None:
        ctx = self._ctx()
        result = self._passing_result()
        with mock.patch.object(
            r11,
            "_source_prefix_comparison",
            return_value={"exact": True, "numeric": True, "maximum_abs_difference": 0.0, "component_max_abs_difference": {}},
        ):
            row = r11.long_hold_result_row(ctx, result, phase="oracle_long_hold")
        self.assertTrue(row["long_hold_pass"])
        self.assertEqual(row["uniform_hold_start_step"], 65)
        self.assertGreaterEqual(row["long_hold_combined_minimum_signed_margin"], 0.02)

    def test_drift_after_650ms_fails_even_if_terminal_state_returns(self) -> None:
        ctx = self._ctx()
        result = self._passing_result()
        # A temporary 40 mm excursion in the fixed hold window must fail; no
        # later endpoint can hide it.
        result["trajectory"][100]["R"] += 0.04
        with mock.patch.object(
            r11,
            "_source_prefix_comparison",
            return_value={"exact": True, "numeric": True, "maximum_abs_difference": 0.0, "component_max_abs_difference": {}},
        ):
            row = r11.long_hold_result_row(ctx, result, phase="oracle_long_hold")
        self.assertFalse(row["long_hold_pass"])
        self.assertGreater(row["hold_box_max_error_m"], 0.03)

    def test_summary_reports_long_hold_fraction_not_legacy_tracking_fraction(self) -> None:
        ctx = self._ctx()
        rows = []
        for target in ("nominal", "RZ_p10_m10"):
            for delay in (0, 1, 2):
                for slew in (0.9, 1.0, 1.1):
                    rows.append(
                        {
                            "target_id": target,
                            "actual_action_delay_steps": delay,
                            "actual_slew_scale": slew,
                            "success": True,
                            "long_hold_pass": True,
                            "long_hold_combined_minimum_signed_margin": 0.2,
                            "source_prefix_exact": True,
                            "source_prefix_max_abs_difference": 0.0,
                            "streaming_queue_consistent": True,
                            "pending_queue_bypassed": False,
                            "hold_box_max_error_m": 0.01,
                            "hold_speed_max_m_per_s": 0.02,
                            "final_window_speed_rms_m_per_s": 0.01,
                            "max_current_utilization": 0.2,
                            "final_window_current_net_change_max_A": 1.0,
                            "final_window_issued_desired_mean_norm": 0.01,
                            "maximum_final_pending_desired_physical_norm": 0.01,
                        }
                    )
        summary = r11.summarize_long_hold(ctx, rows, phase="oracle_long_hold")
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["long_hold_pass_fraction"], 1.0)
        self.assertNotIn("tracking_fraction", summary)


class Stage41R11WorkerAndSpecTests(unittest.TestCase):
    def test_worker_preserves_r11_spec_and_revision(self) -> None:
        class FakeR10Worker:
            def __init__(self, *args, **kwargs):
                pass

            def evaluate(self, spec):
                self.seen = copy.deepcopy(spec)
                return {"success": True, "spec": spec, "controller_revision": "old"}

            def close(self):
                return None

        with mock.patch.object(r11.r10, "LocalStage41R10Worker", FakeR10Worker):
            worker = r11.LocalStage41R11Worker({}, {}, {}, "w", {})
            original = {
                "experiment_id": "x",
                "controller_revision": r11.CONTROLLER_REVISION,
                "horizon_steps": 200,
            }
            result = worker.evaluate(original)
        self.assertEqual(result["spec"], original)
        self.assertEqual(result["controller_revision"], r11.CONTROLLER_REVISION)
        self.assertEqual(result["frozen_source_controller_revision"], r11.r10.CONTROLLER_REVISION)

    def test_expected_case_bank_is_exactly_18(self) -> None:
        cfg_path = (
            Path(r11.__file__).resolve().parents[2]
            / "configs"
            / "stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json"
        )
        ctx = SimpleNamespace(cfg=json.loads(cfg_path.read_text(encoding="utf-8")))
        keys = r11._expected_case_keys(ctx)
        self.assertEqual(len(keys), 18)
        self.assertIn(("RZ_p10_m10", 2, 0.9), keys)

    def test_untrusted_calibration_token_is_rejected(self) -> None:
        tokens = {}
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                tokens[(delay, slew)] = {
                    "success": True,
                    "batch_trusted": True,
                    "batch_trusted_correct": True,
                    "batch_wrong_accept": False,
                    "batch_selected_delay_steps": delay,
                    "batch_selected_slew_scale": slew,
                    "experiment_id": f"d{delay}s{slew}",
                }
        tokens[(2, 1.1)]["batch_trusted"] = False
        ctx = SimpleNamespace(r10_ctx=SimpleNamespace(r9_ctx=object()))
        with mock.patch.object(r11.r9, "source_calibration_tokens", return_value=tokens):
            with self.assertRaisesRegex(ValueError, "not trusted"):
                r11._trusted_tokens(ctx)


if __name__ == "__main__":
    unittest.main()
