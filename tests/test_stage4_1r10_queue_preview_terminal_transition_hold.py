from __future__ import annotations

import copy
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_1r10_queue_preview_terminal_transition_hold as r10,
)


class Stage41R10QueuePreviewTests(unittest.TestCase):
    @staticmethod
    def _trace(delay: int = 2) -> list[dict]:
        trace = []
        for index in range(r10.MAIN_CONTROL_STEPS):
            issued = np.asarray(
                [0.01 * index, -0.005 * index, 0.002 * index], dtype=float
            )
            applied_index = index - delay
            applied = (
                np.asarray(
                    [
                        0.01 * applied_index,
                        -0.005 * applied_index,
                        0.002 * applied_index,
                    ],
                    dtype=float,
                )
                if applied_index >= 0
                else np.zeros(3)
            )
            trace.append(
                {
                    "issued_mode_coefficients": issued.tolist(),
                    "issued_desired_physical_mode_coefficients": issued.tolist(),
                    "desired_physical_mode_coefficients": issued.tolist(),
                    "applied_command_mode_coefficients": applied.tolist(),
                    "mode_correction_physical": issued.tolist(),
                }
            )
        return trace

    def test_delay_two_reconstructs_queue_before_preview_issue_slots(self) -> None:
        queue, indices = r10._initial_preview_queue(self._trace(2), 2)
        self.assertEqual(indices, [33, 34])
        self.assertEqual(
            [(item["origin"], item["origin_index"]) for item in queue],
            [("main_control", 31), ("main_control", 32)],
        )

    def test_delay_one_reconstructs_only_issue_34_preview(self) -> None:
        queue, indices = r10._initial_preview_queue(self._trace(1), 1)
        self.assertEqual(indices, [34])
        self.assertEqual(
            [(item["origin"], item["origin_index"]) for item in queue],
            [("main_control", 33)],
        )

    def test_delay_zero_has_no_preview_replacement(self) -> None:
        queue, indices = r10._initial_preview_queue(self._trace(0), 0)
        self.assertEqual(queue, [])
        self.assertEqual(indices, [])

    def test_preview_stream_preserves_old_applied_command_then_replaces_queue(self) -> None:
        queue, _ = r10._initial_preview_queue(self._trace(2), 2)
        preview33 = {
            "origin": "terminal_preview",
            "origin_index": 33,
            "command": np.asarray([1.0, 0.0, 0.0]),
            "desired_physical": np.asarray([0.1, 0.0, 0.0]),
        }
        applied33, queue = r10._stream_queue_apply(queue, preview33, 2)
        preview34 = {
            "origin": "terminal_preview",
            "origin_index": 34,
            "command": np.asarray([2.0, 0.0, 0.0]),
            "desired_physical": np.asarray([0.2, 0.0, 0.0]),
        }
        applied34, queue = r10._stream_queue_apply(queue, preview34, 2)
        self.assertEqual(
            (applied33["origin"], applied33["origin_index"]),
            ("main_control", 31),
        )
        self.assertEqual(
            (applied34["origin"], applied34["origin_index"]),
            ("main_control", 32),
        )
        self.assertEqual(
            [(item["origin"], item["origin_index"]) for item in queue],
            [("terminal_preview", 33), ("terminal_preview", 34)],
        )

    def test_issue_time_measurement_cannot_see_future_state(self) -> None:
        trajectory = [
            {"R": 1.0, "Z": -1.0, "Ip": 100.0},
            {"R": 1.001, "Z": -1.002, "Ip": 102.0},
            {"R": 1.002, "Z": -1.003, "Ip": 103.0},
            {"R": 99.0, "Z": 99.0, "Ip": 99.0},
        ]
        measurement = r10._terminal_measurement_at_issue(
            trajectory,
            issue_step=2,
            target=np.asarray([1.0, -1.0, 100.0]),
            dt_s=0.01,
        )
        np.testing.assert_allclose(
            measurement, [0.002, -0.003, 0.1, -0.1, 3.0]
        )


class Stage41R10WorkerFlowTests(unittest.TestCase):
    def test_full_synthetic_delay_two_preview_and_stream(self) -> None:
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
            def solve_command(self, desired, currents, gain, slew, *, enabled):
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

            @staticmethod
            def _issued(index: int) -> np.ndarray:
                return np.asarray(
                    [0.01 * index, -0.005 * index, 0.002 * index], dtype=float
                )

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
                control = []
                delay = 2
                for index in range(35):
                    issued = self._issued(index)
                    applied = (
                        self._issued(index - delay)
                        if index >= delay
                        else np.zeros(3)
                    )
                    control.append(
                        {
                            "issued_mode_coefficients": issued.tolist(),
                            "issued_desired_physical_mode_coefficients": issued.tolist(),
                            "desired_physical_mode_coefficients": issued.tolist(),
                            "applied_command_mode_coefficients": applied.tolist(),
                            "mode_correction_physical": issued.tolist(),
                        }
                    )
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

        worker = object.__new__(r10.LocalStage41R10Worker)
        worker.base_worker = FakeBase()
        worker.bundle = {}
        worker.horizon_steps = 75
        worker.r9_worker = SimpleNamespace(close=lambda: None)
        spec = {
            "experiment_id": "synthetic-r10",
            "horizon_steps": 75,
            "tail_feedback_steps": 40,
            "action_delay_steps": 2,
            "controller_action_delay_steps": 2,
            "slew_scale": 1.0,
            "controller_slew_scale_estimate": 1.0,
            "trusted_calibration_model": True,
            "terminal_template_step": 24,
            "terminal_controller_scale": 0.5,
            "terminal_controller_model_scale": 1.0,
            "terminal_velocity_measurement_gain": 1.5,
            "terminal_position_measurement_gain": 1.0,
            "terminal_ip_measurement_gain": 1.0,
            "terminal_policy_id": "synthetic-preview",
            "target_R_offset_m": 0.0,
            "target_Z_offset_m": 0.0,
            "target_Ip_offset_A": 0.0,
            "actuator_gain_by_mode": [1.0, 1.0, 1.0],
            "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
            "actuator_bias_by_mode": [0.0, 0.0, 0.0],
        }
        solve_calls = []

        def solve(*args, **kwargs):
            solve_calls.append(copy.deepcopy(kwargs))
            return {
                "first_correction": np.asarray([0.05, -0.02, 0.01]),
                "solver_success": True,
                "solver_status": 1,
                "solver_cost": 0.0,
                "solver_optimality": 0.0,
                "effect_step": int(kwargs["current_step"])
                + int(kwargs["modeled_action_delay_steps"]),
                "fixed_pending_steps": int(
                    kwargs["modeled_action_delay_steps"]
                ),
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
            r10.r3,
            "solve_delay_aware_physical_correction",
            side_effect=solve,
        ), mock.patch.object(r10.r3.base, "_state_record", side_effect=record):
            result = worker.evaluate(spec)

        self.assertTrue(result["success"], result.get("failure_reason"))
        self.assertEqual(len(result["trajectory"]), 76)
        self.assertEqual(len(result["transition_preview_trace"]), 2)
        self.assertEqual(len(result["terminal_feedback_trace"]), 40)
        self.assertEqual(
            [row["issue_step"] for row in result["transition_preview_trace"]],
            [33, 34],
        )
        self.assertTrue(
            all(
                not row["future_measurement_used"]
                for row in result["transition_preview_trace"]
            )
        )
        original = result["original_main_control_trace"]
        updated = result["control_trace"]
        for index in range(33):
            self.assertEqual(updated[index], original[index])
        for index in (33, 34):
            self.assertEqual(
                updated[index]["applied_command_mode_coefficients"],
                original[index]["applied_command_mode_coefficients"],
            )
            self.assertTrue(
                updated[index]["transition_preview_replaced_unapplied_issue"]
            )
        first_tail = result["terminal_feedback_trace"][0]
        self.assertEqual(
            first_tail["applied_origin"],
            {"origin": "terminal_preview", "origin_index": 33},
        )
        self.assertEqual(len(solve_calls), 42)
        self.assertEqual(
            result["terminal_feedback_summary"]["final_pending_count"], 2
        )
        self.assertTrue(
            result["transition_preview_summary"][
                "all_original_applied_commands_preserved"
            ]
        )


class Stage41R10ConfigTests(unittest.TestCase):
    @staticmethod
    def _config() -> dict:
        path = (
            Path(__file__).resolve().parents[1]
            / "configs"
            / "stage4_1r10_queue_preview_terminal_transition_hold_750ms.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_packaged_config_preserves_scientific_guardrails(self) -> None:
        cfg = self._config()
        r10.validate_config(cfg)
        terminal = cfg["terminal_transition"]
        self.assertEqual(terminal["main_control_steps"], 35)
        self.assertEqual(terminal["horizon_steps"], 75)
        self.assertEqual(terminal["tail_feedback_steps"], 40)
        self.assertEqual(terminal["actual_delay_steps"], [0, 1, 2])
        self.assertEqual(terminal["actual_slew_scales"], [0.9, 1.0, 1.1])
        self.assertEqual(len(terminal["candidate_bank"]), 6)
        self.assertNotEqual(
            terminal["development_target"]["target_id"],
            terminal["holdout_target"]["target_id"],
        )
        self.assertFalse(
            cfg["calibrated_confirmation"]["online_handover_enabled"]
        )

    def test_config_rejects_future_information_preview(self) -> None:
        cfg = self._config()
        cfg["terminal_transition"][
            "preview_uses_only_original_issue_time_information"
        ] = False
        with self.assertRaisesRegex(ValueError, "remain causal"):
            r10.validate_config(cfg)

    def test_config_rejects_weakened_tracking_gate(self) -> None:
        cfg = self._config()
        cfg["gate"]["terminal_velocity_max_m_per_s"] = 0.11
        with self.assertRaisesRegex(ValueError, "0.1 m/s"):
            r10.validate_config(cfg)

    def test_config_rejects_wrong_transition_smoothing_anchor(self) -> None:
        cfg = self._config()
        cfg["terminal_transition"]["initial_previous_correction"] = (
            "last_issued_desired_physical"
        )
        with self.assertRaisesRegex(ValueError, "last main-MPC correction"):
            r10.validate_config(cfg)

    def test_candidate_bank_contains_exact_r9_structural_baseline_and_factored_axes(self) -> None:
        cfg = self._config()
        bank = cfg["terminal_transition"]["candidate_bank"]
        baseline = bank[0]
        self.assertEqual(baseline["template_step"], 28)
        self.assertAlmostEqual(baseline["controller_scale"], 0.5)
        self.assertAlmostEqual(baseline["velocity_measurement_gain"], 1.5)
        self.assertAlmostEqual(baseline["position_measurement_gain"], 1.0)
        axes = {row["ablation_axis"] for row in bank}
        self.assertTrue(
            {
                "earlier_template_only",
                "controller_scale_only",
                "velocity_gain_only",
                "position_gain_only",
                "combined_stronger_earlier",
            }.issubset(axes)
        )


class Stage41R10SummaryTests(unittest.TestCase):
    @staticmethod
    def _ctx() -> SimpleNamespace:
        path = (
            Path(__file__).resolve().parents[1]
            / "configs"
            / "stage4_1r10_queue_preview_terminal_transition_hold_750ms.json"
        )
        return SimpleNamespace(
            cfg=json.loads(path.read_text(encoding="utf-8"))
        )

    @staticmethod
    def _row(policy: str, target: str, delay: int, slew: float, margin: float) -> dict:
        return {
            "experiment_id": f"{policy}_{target}_{delay}_{slew}",
            "policy_id": policy,
            "target_id": target,
            "actual_action_delay_steps": delay,
            "actual_slew_scale": slew,
            "success": True,
            "r10_target_tracking_pass": True,
            "r10_combined_minimum_signed_margin": margin,
            "stage3_4_tracking_minimum_signed_margin": margin + 0.01,
            "prefix_guard_pass": True,
            "preview_guard_pass": True,
            "queue_guard_pass": True,
            "convergence_guard_pass": True,
            "maximum_preview_desired_physical_norm": 0.1,
            "maximum_final_pending_desired_physical_norm": 0.05,
            "last10_speed_rms_m_per_s": 0.03,
            "last10_box_max_error_m": 0.01,
            "terminal_action_rms": 0.05,
        }

    def test_development_requires_complete_54_rollout_bank(self) -> None:
        ctx = self._ctx()
        summary = r10.summarize_oracle_development(
            ctx,
            [
                self._row(
                    ctx.cfg["terminal_transition"]["candidate_bank"][0][
                        "policy_id"
                    ],
                    "nominal",
                    0,
                    0.9,
                    0.05,
                )
            ],
        )
        self.assertFalse(summary["coverage_complete"])
        self.assertFalse(summary["passed"])
        self.assertIsNone(summary["selected_policy_id"])

    def test_selection_uses_only_development_and_largest_worst_margin(self) -> None:
        ctx = self._ctx()
        rows = []
        bank = ctx.cfg["terminal_transition"]["candidate_bank"]
        for index, policy in enumerate(bank):
            margin = 0.03 + 0.01 * index
            for delay in (0, 1, 2):
                for slew in (0.9, 1.0, 1.1):
                    rows.append(
                        self._row(
                            policy["policy_id"], "nominal", delay, slew, margin
                        )
                    )
        summary = r10.summarize_oracle_development(ctx, rows)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["selected_policy_id"], bank[-1]["policy_id"])
        self.assertFalse(summary["candidate_selection_uses_holdout"])

    def test_policy_fails_when_preview_guard_fails(self) -> None:
        ctx = self._ctx()
        policy = ctx.cfg["terminal_transition"]["candidate_bank"][0]["policy_id"]
        rows = [
            self._row(policy, "nominal", delay, slew, 0.05)
            for delay in (0, 1, 2)
            for slew in (0.9, 1.0, 1.1)
        ]
        rows[-1]["preview_guard_pass"] = False
        summary = r10._policy_summary(
            ctx, rows, policy_id=policy, expected_target_id="nominal"
        )
        self.assertFalse(summary["passed"])

    def test_policy_fails_when_long_tail_does_not_converge(self) -> None:
        ctx = self._ctx()
        policy = ctx.cfg["terminal_transition"]["candidate_bank"][0]["policy_id"]
        rows = [
            self._row(policy, "nominal", delay, slew, 0.05)
            for delay in (0, 1, 2)
            for slew in (0.9, 1.0, 1.1)
        ]
        rows[0]["convergence_guard_pass"] = False
        summary = r10._policy_summary(
            ctx, rows, policy_id=policy, expected_target_id="nominal"
        )
        self.assertFalse(summary["passed"])


class Stage41R10SourceAuditTests(unittest.TestCase):
    def test_synthetic_r9_structure_is_recomputed_not_trusted_from_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source_r9"
            raw_dir = source / "stage4_1r9_oracle_development" / "raw"
            raw_dir.mkdir(parents=True)
            rows = []
            policies = [f"p{index}" for index in range(6)]
            experiment = 0
            for policy in policies:
                for delay in (0, 1, 2):
                    for slew in (0.9, 1.0, 1.1):
                        experiment += 1
                        experiment_id = f"synthetic_{experiment:03d}"
                        trajectory = []
                        for state_index in range(56):
                            # Identical across policies for each delay/slew.  The
                            # exact values are irrelevant to the audit structure.
                            trajectory.append(
                                {
                                    "R": 1.7 + 1e-5 * state_index,
                                    "Z": -1.0 - 2e-5 * state_index,
                                    "Ip": 2.5e6,
                                    "currents_a_tsc": [0.0] * 14,
                                    "action_norm_tsc": [0.0] * 14,
                                    "abnormal": False,
                                }
                            )
                        control = []
                        for index in range(35):
                            issued = [0.1, 0.0, 0.0]
                            control.append(
                                {
                                    "issued_mode_coefficients": issued,
                                    "issued_desired_physical_mode_coefficients": issued,
                                }
                            )
                        result = {
                            "experiment_id": experiment_id,
                            "success": True,
                            "failure_reason": "",
                            "spec": {
                                "target_id": "nominal",
                                "action_delay_steps": delay,
                                "slew_scale": slew,
                                "terminal_policy_id": policy,
                            },
                            "trajectory": trajectory,
                            "control_trace": control,
                            "terminal_feedback_trace": [
                                {
                                    "solver_success": True,
                                    "issued_desired_physical_mode_coefficients": [
                                        0.02,
                                        0.0,
                                        0.0,
                                    ],
                                }
                            ],
                            "terminal_feedback_summary": {
                                "streaming_queue_consistent": True,
                                "pending_queue_bypassed": False,
                            },
                        }
                        with gzip.open(
                            raw_dir / f"{experiment_id}.json.gz", "wt"
                        ) as handle:
                            json.dump(result, handle)
                        rows.append(
                            {
                                "experiment_id": experiment_id,
                                "actual_action_delay_steps": delay,
                                "actual_slew_scale": slew,
                                "stage3_4_target_tracking_pass": delay == 0,
                                "stage3_4_tracking_minimum_signed_margin": (
                                    0.05 if delay == 0 else -0.05
                                ),
                                "max_current_utilization": 0.4,
                            }
                        )
            (source / "stage4_1r9_oracle_development" / "results.json").write_text(
                json.dumps(rows), encoding="utf-8"
            )
            cfg_path = (
                Path(__file__).resolve().parents[1]
                / "configs"
                / "stage4_1r10_queue_preview_terminal_transition_hold_750ms.json"
            )
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            paths = r10.Stage41R10Paths.from_run_dir(root / "run")
            paths.source_audit.mkdir(parents=True)
            paths.run_dir.mkdir(parents=True, exist_ok=True)
            r10.atomic_write_json(paths.state, r10.initial_state())
            ctx = SimpleNamespace(
                cfg=cfg,
                source_stage41r9_run=source,
                source_state={"finished": True, "stop_reason": "oracle_development_failed"},
                source_cfg={"terminal_feedback": {"dt_s": 0.01}},
                paths=paths,
            )
            summary = r10.run_source_audit(ctx)
            self.assertTrue(summary["passed"])
            self.assertTrue(summary["all_delay0_cases_pass"])
            self.assertTrue(summary["all_delay1_delay2_cases_fail"])
            self.assertTrue(
                summary["all_policies_identical_before_first_terminal_effect"]
            )


class Stage41R10ConfirmationTokenTests(unittest.TestCase):
    def test_untrusted_r8_token_is_rejected_before_control_specs_exist(self) -> None:
        cfg_path = (
            Path(__file__).resolve().parents[1]
            / "configs"
            / "stage4_1r10_queue_preview_terminal_transition_hold_750ms.json"
        )
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            paths = r10.Stage41R10Paths.from_run_dir(Path(tmp))
            paths.oracle_development.mkdir(parents=True)
            paths.oracle_holdout.mkdir(parents=True)
            selected = cfg["terminal_transition"]["candidate_bank"][0]
            r10.atomic_write_json(
                paths.oracle_development / "summary.json",
                {"passed": True, "selected_policy_id": selected["policy_id"]},
            )
            r10.atomic_write_json(
                paths.oracle_holdout / "summary.json", {"passed": True}
            )
            chain = SimpleNamespace(source_scale=1.0)
            r3ctx = SimpleNamespace(source_scale=1.0)
            r4ctx = SimpleNamespace(r3_ctx=r3ctx)
            r5ctx = SimpleNamespace(r4_ctx=r4ctx)
            r6ctx = SimpleNamespace(r5_ctx=r5ctx)
            r7ctx = SimpleNamespace(r6_ctx=r6ctx)
            r8ctx = SimpleNamespace(r7_ctx=r7ctx)
            r9ctx = SimpleNamespace(r8_ctx=r8ctx)
            ctx = SimpleNamespace(cfg=cfg, paths=paths, r9_ctx=r9ctx)
            tokens = {}
            for delay in (0, 1, 2):
                for slew in (0.9, 1.0, 1.1):
                    tokens[(delay, slew)] = {
                        "experiment_id": f"token_{delay}_{slew}",
                        "success": True,
                        "batch_trusted": True,
                        "batch_trusted_correct": True,
                        "batch_wrong_accept": False,
                        "batch_selected_delay_steps": delay,
                        "batch_selected_slew_scale": slew,
                    }
            tokens[(1, 1.0)]["batch_trusted"] = False
            with mock.patch.object(
                r10.r9, "source_calibration_tokens", return_value=tokens
            ), mock.patch.object(
                r10, "materialize_variant", return_value=("variant", {})
            ):
                with self.assertRaisesRegex(RuntimeError, "untrusted"):
                    r10.build_calibrated_confirmation_specs(ctx)


class Stage41R10SelfTest(unittest.TestCase):
    def test_self_test_passes(self) -> None:
        payload = r10.self_test()
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["package_revision"], r10.PACKAGE_REVISION)


if __name__ == "__main__":
    unittest.main()
