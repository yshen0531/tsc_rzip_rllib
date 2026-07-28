from __future__ import annotations

import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r9_terminal_template_mpc_feedback_hold as r9


class Stage41R9QueueTests(unittest.TestCase):
    @staticmethod
    def _trace() -> list[dict]:
        return [
            {
                "issued_mode_coefficients": [float(i), -float(i), 0.1 * i],
                "issued_desired_physical_mode_coefficients": [
                    0.01 * i,
                    -0.01 * i,
                    0.001 * i,
                ],
            }
            for i in range(35)
        ]

    def test_initial_queue_contains_last_delayed_commands_in_issue_order(self) -> None:
        queue = r9._initial_stream_queue(self._trace(), 2)
        self.assertEqual(len(queue), 2)
        self.assertEqual([row["origin_index"] for row in queue], [33, 34])
        np.testing.assert_allclose(queue[0]["command"], [33.0, -33.0, 3.3])
        np.testing.assert_allclose(
            queue[1]["desired_physical"], [0.34, -0.34, 0.034]
        )

    def test_streaming_queue_applies_oldest_then_keeps_fixed_delay(self) -> None:
        queue = r9._initial_stream_queue(self._trace(), 2)
        issued0 = {
            "origin": "terminal_feedback",
            "origin_index": 0,
            "command": np.asarray([100.0, 0.0, 0.0]),
            "desired_physical": np.asarray([1.0, 0.0, 0.0]),
        }
        applied0, queue = r9._stream_queue_apply(queue, issued0, 2)
        self.assertEqual((applied0["origin"], applied0["origin_index"]), ("main_control", 33))
        self.assertEqual(len(queue), 2)
        self.assertEqual((queue[0]["origin"], queue[0]["origin_index"]), ("main_control", 34))
        self.assertEqual((queue[1]["origin"], queue[1]["origin_index"]), ("terminal_feedback", 0))

        issued1 = {
            "origin": "terminal_feedback",
            "origin_index": 1,
            "command": np.asarray([200.0, 0.0, 0.0]),
            "desired_physical": np.asarray([2.0, 0.0, 0.0]),
        }
        applied1, queue = r9._stream_queue_apply(queue, issued1, 2)
        self.assertEqual((applied1["origin"], applied1["origin_index"]), ("main_control", 34))
        self.assertEqual(len(queue), 2)
        self.assertEqual([row["origin_index"] for row in queue], [0, 1])

    def test_delay_zero_applies_current_issue_immediately(self) -> None:
        issued = {
            "origin": "terminal_feedback",
            "origin_index": 3,
            "command": np.asarray([1.0, 2.0, 3.0]),
            "desired_physical": np.asarray([0.1, 0.2, 0.3]),
        }
        applied, queue = r9._stream_queue_apply([], issued, 0)
        self.assertEqual(applied["origin_index"], 3)
        self.assertEqual(queue, [])

    def test_queue_length_mismatch_is_hard_error(self) -> None:
        issued = {
            "origin": "terminal_feedback",
            "origin_index": 0,
            "command": np.zeros(3),
            "desired_physical": np.zeros(3),
        }
        with self.assertRaises(ValueError):
            r9._stream_queue_apply([], issued, 2)


class Stage41R9MeasurementTests(unittest.TestCase):
    def test_terminal_measurement_uses_current_target_error_and_finite_difference_velocity(self) -> None:
        trajectory = [
            {"R": 1.0, "Z": -1.0, "Ip": 100.0},
            {"R": 1.001, "Z": -1.002, "Ip": 102.0},
        ]
        measurement = r9._terminal_measurement(
            trajectory, np.asarray([1.0, -1.0, 100.0]), 0.01
        )
        np.testing.assert_allclose(measurement, [0.001, -0.002, 0.1, -0.2, 2.0])

    def test_terminal_measurement_rejects_missing_velocity_history(self) -> None:
        with self.assertRaises(ValueError):
            r9._terminal_measurement(
                [{"R": 1.0, "Z": 0.0, "Ip": 1.0}], np.zeros(3), 0.01
            )


class Stage41R9WorkerFlowTests(unittest.TestCase):
    def test_terminal_feedback_worker_executes_full_synthetic_stream(self) -> None:
        class FakeEnv:
            def __init__(self) -> None:
                self.runner = None
                self.last_state = {
                    "R": 1.7,
                    "Z": -1.0,
                    "Ip": 2.5e6,
                    "currents_a_tsc": np.zeros(14),
                }

            def step(self, action):
                return None, 0.0, False, False, {}

        class FakeScheduler:
            def solve_command(
                self, desired, currents, gain, slew, *, enabled
            ):
                return {
                    "command": np.asarray(desired, dtype=float),
                    "mismatch_rms_a": 0.0,
                    "mismatch_max_abs_a": 0.0,
                }

        class FakeBase:
            def __init__(self) -> None:
                self.env = FakeEnv()
                self.cfg = {
                    "target": {"R": 1.7, "Z": -1.0, "Ip": 2.5e6},
                    "identification": {
                        "output_scales": {
                            "R_m": 0.03,
                            "Z_m": 0.03,
                            "vR_m_per_s": 0.1,
                            "vZ_m_per_s": 0.1,
                            "Ip_A": 10000.0,
                        }
                    },
                }
                self.env_cfg = {"dt_ms": 10}
                self.stub = SimpleNamespace(cfg={}, env_cfg=self.env_cfg)
                self.lower_mode = np.full(3, -2.0)
                self.upper_mode = np.full(3, 2.0)
                self.scheduler = FakeScheduler()

            def evaluate(self, spec):
                trajectory = [
                    {
                        "R": 1.7,
                        "Z": -1.0,
                        "Ip": 2.5e6,
                        "currents_a_tsc": [0.0] * 14,
                        "currents_a_display": [0.0] * 14,
                        "action_norm_tsc": [0.0] * 14,
                        "abnormal": False,
                    }
                    for _ in range(36)
                ]
                control = [
                    {
                        "issued_mode_coefficients": [0.0, 0.0, 0.0],
                        "issued_desired_physical_mode_coefficients": [
                            0.0,
                            0.0,
                            0.0,
                        ],
                    }
                    for _ in range(35)
                ]
                return {
                    "experiment_id": spec["experiment_id"],
                    "success": True,
                    "failure_reason": "",
                    "trajectory": trajectory,
                    "control_trace": control,
                }

            @staticmethod
            def _mode_action(effective, currents):
                return np.zeros(14, dtype=float)

        worker = object.__new__(r9.LocalStage41R9Worker)
        worker.base_worker = FakeBase()
        worker.bundle = {}
        worker.horizon_steps = 55
        worker.r8_worker = SimpleNamespace(close=lambda: None)
        spec = {
            "experiment_id": "synthetic-worker-flow",
            "horizon_steps": 55,
            "tail_feedback_steps": 20,
            "action_delay_steps": 2,
            "controller_action_delay_steps": 2,
            "slew_scale": 1.0,
            "controller_slew_scale_estimate": 1.0,
            "trusted_calibration_model": True,
            "terminal_template_step": 30,
            "terminal_controller_scale": 0.35,
            "terminal_controller_model_scale": 1.0,
            "terminal_velocity_measurement_gain": 1.0,
            "terminal_position_measurement_gain": 1.0,
            "terminal_ip_measurement_gain": 1.0,
            "terminal_initial_previous_correction": (
                "last_issued_desired_physical"
            ),
            "terminal_policy_id": "synthetic",
            "target_R_offset_m": 0.0,
            "target_Z_offset_m": 0.0,
            "target_Ip_offset_A": 0.0,
            "actuator_gain_by_mode": [1.0, 1.0, 1.0],
            "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
            "actuator_bias_by_mode": [0.0, 0.0, 0.0],
        }
        solve = {
            "first_correction": np.zeros(3),
            "solver_success": True,
            "solver_status": 1,
            "solver_cost": 0.0,
            "solver_optimality": 0.0,
            "effect_step": 32,
            "fixed_pending_steps": 2,
            "predicted_normalized_residual_rms": 0.0,
        }

        def record(env, index, action):
            return {
                "R": float(env.last_state["R"]),
                "Z": float(env.last_state["Z"]),
                "Ip": float(env.last_state["Ip"]),
                "currents_a_tsc": np.asarray(
                    env.last_state["currents_a_tsc"], dtype=float
                ).tolist(),
                "currents_a_display": np.asarray(
                    env.last_state["currents_a_tsc"], dtype=float
                ).tolist(),
                "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                "abnormal": False,
            }

        with mock.patch.object(
            r9.r3,
            "solve_delay_aware_physical_correction",
            return_value=solve,
        ), mock.patch.object(r9.r3.base, "_state_record", side_effect=record):
            result = worker.evaluate(spec)
        self.assertTrue(result["success"], result.get("failure_reason"))
        self.assertEqual(len(result["trajectory"]), 56)
        self.assertEqual(len(result["terminal_feedback_trace"]), 20)
        self.assertEqual(
            result["terminal_feedback_summary"]["final_pending_count"], 2
        )
        self.assertTrue(
            result["terminal_feedback_summary"][
                "streaming_queue_consistent"
            ]
        )

    def test_untrusted_source_token_is_hard_rejected_before_main_control(self) -> None:
        cfg_path = (
            Path(__file__).resolve().parents[1]
            / "configs"
            / "stage4_1r9_terminal_template_mpc_feedback_hold_550ms.json"
        )
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        # Rebuild the exact access chain:
        # r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
        r3_ctx = SimpleNamespace(source_scale=0.5)
        r4_ctx = SimpleNamespace(r3_ctx=r3_ctx)
        r5_ctx = SimpleNamespace(r4_ctx=r4_ctx)
        r6_ctx = SimpleNamespace(r5_ctx=r5_ctx)
        r7_ctx = SimpleNamespace(r6_ctx=r6_ctx)
        policy = cfg["terminal_feedback"]["candidate_bank"][0]
        bad_token = {
            "experiment_id": "bad-token",
            "success": True,
            "batch_trusted": False,
            "batch_trusted_correct": False,
            "batch_wrong_accept": False,
            "batch_selected_delay_steps": None,
            "batch_selected_slew_scale": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            holdout = Path(tmp) / "oracle_holdout"
            holdout.mkdir(parents=True)
            (holdout / "summary.json").write_text(
                json.dumps({"passed": True}), encoding="utf-8"
            )
            ctx = SimpleNamespace(
                cfg=cfg,
                r8_ctx=SimpleNamespace(r7_ctx=r7_ctx),
                paths=SimpleNamespace(oracle_holdout=holdout),
            )
            with mock.patch.object(
                r9, "_selected_policy", return_value=policy
            ), mock.patch.object(
                r9,
                "source_calibration_tokens",
                return_value={(0, 0.9): bad_token},
            ), mock.patch.object(
                r9, "materialize_variant", return_value=("variant", {})
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "untrusted.*cannot start"
                ):
                    r9.build_calibrated_confirmation_specs(ctx)



class Stage41R9TraceTests(unittest.TestCase):
    @staticmethod
    def _result(offset: float = 0.0) -> dict:
        trajectory = []
        for step in range(4):
            trajectory.append(
                {
                    "R": 1.7 + offset + 1e-3 * step,
                    "Z": -1.0 + 2e-3 * step,
                    "Ip": 2.5e6 + step,
                    "currents_a_tsc": [float(i + step) for i in range(14)],
                    "action_norm_tsc": [0.01 * (i + step) for i in range(14)],
                }
            )
        return {
            "trajectory": trajectory,
            "control_trace": [
                {"issued_mode_coefficients": [1.0, 2.0, 3.0]},
                {"issued_mode_coefficients": [0.5, -0.5, 0.0]},
            ],
            "terminal_feedback_trace": [
                {
                    "issued_mode_coefficients": [0.2, 0.1, 0.0],
                    "applied_mode_coefficients": [0.5, -0.5, 0.0],
                },
                {
                    "issued_mode_coefficients": [0.0, 0.0, 0.0],
                    "applied_mode_coefficients": [0.2, 0.1, 0.0],
                },
            ],
        }

    def test_exact_and_numeric_trace_comparison_are_distinct(self) -> None:
        exact = r9._compare_results(
            self._result(), self._result(), atol=1e-12, prefix_only=False
        )
        self.assertTrue(exact["exact_equal"])
        self.assertTrue(exact["numeric_equal"])
        close = r9._compare_results(
            self._result(offset=5e-13),
            self._result(),
            atol=1e-12,
            prefix_only=False,
        )
        self.assertFalse(close["exact_equal"])
        self.assertTrue(close["numeric_equal"])
        self.assertGreater(close["max_abs_difference"], 0.0)


class Stage41R9ResultRowTests(unittest.TestCase):
    def test_feedback_result_row_passes_r8_policy_mapping(self) -> None:
        cfg = {
            "terminal_feedback": {
                "horizon_steps": 55,
                "allowed_arrival_steps": [26, 40],
                "prefix_numeric_atol": 1e-12,
            }
        }
        ctx = SimpleNamespace(cfg=cfg, r8_ctx=object())
        result = {
            "experiment_id": "row-test",
            "success": True,
            "failure_reason": "",
            "spec": {
                "scenario": "row-test",
                "target_id": "nominal",
                "terminal_policy_id": "tm-test",
                "controller_variant": "oracle_terminal_feedback",
                "action_delay_steps": 1,
                "controller_action_delay_steps": 1,
                "slew_scale": 1.0,
                "controller_slew_scale_estimate": 1.0,
                "trusted_calibration_model": True,
            },
            "trajectory": [
                {
                    "R": 1.0,
                    "Z": 0.0,
                    "Ip": 1.0,
                    "currents_a_tsc": [0.0] * 14,
                    "action_norm_tsc": [0.0] * 14,
                }
                for _ in range(56)
            ],
            "control_trace": [],
            "terminal_feedback_trace": [],
            "terminal_feedback_summary": {},
        }
        metrics = {
            "stage3_4_target_tracking_pass": True,
            "stage3_4_tracking_minimum_signed_margin": 0.1,
        }
        prefix = {
            "source_available": True,
            "exact_equal": True,
            "numeric_equal": True,
            "max_abs_difference": 0.0,
        }
        empty_arrays = (
            np.zeros((0, 17)),
            np.zeros((0, 3)),
            np.zeros((0, 3)),
            np.zeros((0, 3)),
        )
        with mock.patch.object(r9.r8, "tracking_metrics", return_value=metrics) as tracking, mock.patch.object(
            r9, "_source_prefix_comparison", return_value=prefix
        ), mock.patch.object(r9, "_trace_arrays", return_value=empty_arrays):
            row = r9.feedback_result_row(ctx, result, phase="development")
        tracking.assert_called_once()
        args = tracking.call_args.args
        self.assertIs(args[0], ctx.r8_ctx)
        self.assertIs(args[1], result)
        self.assertEqual(
            args[2],
            {"horizon_steps": 55, "allowed_arrival_steps": [26, 40]},
        )
        self.assertTrue(row["stage3_4_target_tracking_pass"])



class Stage41R9SummaryTests(unittest.TestCase):
    @staticmethod
    def _config() -> dict:
        path = (
            Path(__file__).resolve().parents[1]
            / "configs"
            / "stage4_1r9_terminal_template_mpc_feedback_hold_550ms.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def _ctx(self) -> SimpleNamespace:
        return SimpleNamespace(cfg=self._config())

    @staticmethod
    def _row(policy: str, target: str, delay: int, slew: float, margin: float = 0.05) -> dict:
        return {
            "policy_id": policy,
            "target_id": target,
            "actual_action_delay_steps": delay,
            "actual_slew_scale": slew,
            "success": True,
            "stage3_4_target_tracking_pass": True,
            "stage3_4_tracking_minimum_signed_margin": margin,
            "first_350ms_prefix_exact": True,
            "continuous_streaming_queue": True,
            "streaming_queue_consistent": True,
            "pending_queue_bypassed": False,
            "maximum_final_pending_desired_physical_norm": 0.1,
            "last5_issued_desired_rms": 0.1,
            "terminal_action_rms": 0.05,
        }

    def test_development_selection_requires_complete_nine_case_campaign_per_policy(self) -> None:
        ctx = self._ctx()
        one = self._row("tm28_c0p35_v1p00", "nominal", 0, 0.9)
        summary = r9.summarize_oracle_development(ctx, [one])
        self.assertFalse(summary["coverage_complete"])
        self.assertFalse(summary["passed"])
        self.assertIsNone(summary["selected_policy_id"])

    def test_development_selects_largest_minimum_margin_without_holdout_rows(self) -> None:
        ctx = self._ctx()
        rows = []
        policies = ctx.cfg["terminal_feedback"]["candidate_bank"]
        for policy_index, policy in enumerate(policies):
            margin = 0.03 + 0.01 * policy_index
            for delay in (0, 1, 2):
                for slew in (0.9, 1.0, 1.1):
                    rows.append(
                        self._row(
                            policy["policy_id"], "nominal", delay, slew, margin
                        )
                    )
        summary = r9.summarize_oracle_development(ctx, rows)
        self.assertTrue(summary["coverage_complete"])
        self.assertTrue(summary["passed"])
        self.assertEqual(
            summary["selected_policy_id"], policies[-1]["policy_id"]
        )
        self.assertFalse(summary["candidate_selection_uses_holdout"])

    def test_policy_fails_if_streaming_queue_is_bypassed(self) -> None:
        ctx = self._ctx()
        policy = ctx.cfg["terminal_feedback"]["candidate_bank"][0]["policy_id"]
        rows = [
            self._row(policy, "nominal", delay, slew)
            for delay in (0, 1, 2)
            for slew in (0.9, 1.0, 1.1)
        ]
        rows[0]["pending_queue_bypassed"] = True
        expected = r9._expected_case_keys(
            [ctx.cfg["terminal_feedback"]["development_target"]]
        )
        summary = r9._policy_summary(ctx, policy, rows, expected)
        self.assertFalse(summary["passed"])

    def test_policy_fails_with_large_terminal_backlog(self) -> None:
        ctx = self._ctx()
        policy = ctx.cfg["terminal_feedback"]["candidate_bank"][0]["policy_id"]
        rows = [
            self._row(policy, "nominal", delay, slew)
            for delay in (0, 1, 2)
            for slew in (0.9, 1.0, 1.1)
        ]
        rows[-1]["maximum_final_pending_desired_physical_norm"] = 0.5
        expected = r9._expected_case_keys(
            [ctx.cfg["terminal_feedback"]["development_target"]]
        )
        summary = r9._policy_summary(ctx, policy, rows, expected)
        self.assertFalse(summary["passed"])


class Stage41R9GuardrailTests(unittest.TestCase):
    def test_packaged_config_preserves_hard_gates_and_disjoint_holdout(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "configs"
            / "stage4_1r9_terminal_template_mpc_feedback_hold_550ms.json"
        )
        cfg = json.loads(path.read_text(encoding="utf-8"))
        r9.validate_config(cfg)
        self.assertAlmostEqual(cfg["gate"]["precise_tolerance_m"], 0.03)
        self.assertAlmostEqual(
            cfg["gate"]["terminal_velocity_max_m_per_s"], 0.1
        )
        self.assertEqual(cfg["terminal_feedback"]["main_control_steps"], 35)
        self.assertEqual(cfg["terminal_feedback"]["horizon_steps"], 55)
        self.assertEqual(cfg["terminal_feedback"]["tail_feedback_steps"], 20)
        self.assertNotEqual(
            cfg["terminal_feedback"]["development_target"]["target_id"],
            cfg["terminal_feedback"]["holdout_target"]["target_id"],
        )
        self.assertFalse(
            cfg["calibrated_confirmation"]["online_handover_enabled"]
        )
        for policy in cfg["terminal_feedback"]["candidate_bank"]:
            self.assertLessEqual(policy["template_step"] + 2, 34)

    def test_self_test_passes(self) -> None:
        payload = r9.self_test()
        self.assertTrue(payload["passed"])


if __name__ == "__main__":
    unittest.main()
