from __future__ import annotations

import copy
import inspect
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_1r3_control_aware_robustness as r3,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_1r12_original_deadline_weak_slew_anticipatory_damping as r12,
)


class Stage41R12ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_dir = Path(r12.__file__).resolve().parents[2]
        cls.config_path = (
            cls.project_dir
            / "configs"
            / "stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_config_restores_exact_original_timing_contract(self) -> None:
        r12.validate_config(self.cfg)
        normal = self.cfg["formal_timing_contract"]["normal_slew"]
        weak = self.cfg["formal_timing_contract"]["weak_slew"]
        self.assertEqual((normal["arrival_deadline_step"], normal["horizon_steps"]), (25, 35))
        self.assertEqual((weak["arrival_deadline_step"], weak["horizon_steps"]), (27, 37))
        self.assertEqual(max(normal["allowed_arrival_steps"]), 25)
        self.assertEqual(max(weak["allowed_arrival_steps"]), 27)
        self.assertTrue(self.cfg["formal_timing_contract"]["arrival_deadline_may_not_expand"])

    def test_candidate_bank_is_causal_post_deadline_hold_ablation(self) -> None:
        bank = self.cfg["weak_slew_closure"]["candidate_bank"]
        effects = [int(row["first_affected_state_step"]) for row in bank]
        self.assertEqual(effects, [28, 30, 32, 33, 34, 35])
        self.assertGreater(min(effects), 27)
        for effect in effects:
            for delay in (1, 2):
                issue = r12._transition_issue_step(effect, delay)
                self.assertEqual(issue + delay + 1, effect)
                self.assertLess(issue, effect)

    def test_deadline_or_gate_weakening_is_rejected(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] = 28
        with self.assertRaisesRegex(ValueError, "270/370"):
            r12.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"].append(28)
        with self.assertRaisesRegex(ValueError, "270 ms"):
            r12.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["gate"]["precise_tolerance_m"] = 0.031
        with self.assertRaisesRegex(ValueError, "30 mm"):
            r12.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["gate"]["terminal_velocity_max_m_per_s"] = 0.101
        with self.assertRaisesRegex(ValueError, "0.1 m/s"):
            r12.validate_config(cfg)

    def test_at_or_before_deadline_candidate_bank_is_rejected(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["weak_slew_closure"]["candidate_bank"] = [
            {"policy_id": f"bad_{step}", "first_affected_state_step": step}
            for step in (27, 30, 32, 33, 34, 35)
        ]
        cfg["weak_slew_closure"]["candidate_first_affected_state_steps"] = [27, 30, 32, 33, 34, 35]
        with self.assertRaisesRegex(ValueError, "28,30,32,33,34,35"):
            r12.validate_config(cfg)

    def test_scope_expansion_to_other_delays_is_rejected(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["weak_slew_closure"]["actual_delay_steps"] = [0, 1, 2]
        with self.assertRaisesRegex(ValueError, "delay=1/2"):
            r12.validate_config(cfg)

    def test_self_test_encodes_eighteen_episode_budget(self) -> None:
        payload = r12.self_test(self.project_dir)
        self.assertTrue(payload["passed"])
        self.assertTrue(payload["no_arrival_deadline_expansion"])
        self.assertEqual(payload["development_rollout_count"], 12)
        self.assertEqual(payload["holdout_rollout_count"], 2)
        self.assertEqual(payload["calibrated_rollout_count"], 4)
        self.assertEqual(payload["maximum_true_tsc_rollouts"], 18)


class Stage41R12SourceAndPrefixTests(unittest.TestCase):
    @staticmethod
    def _trajectory(horizon: int = 37) -> list[dict]:
        rows = []
        for index in range(horizon + 1):
            rows.append(
                {
                    "R": 1.0 + 1e-4 * index,
                    "Z": -1.0 - 2e-4 * index,
                    "Ip": 1000.0 + index,
                    "vessel_current_total_a": float(index),
                    "vessel_current_abs_sum_a": float(index + 1),
                    "vessel_current_rms_a": float(index + 2),
                    "vessel_current_max_abs_a": float(index + 3),
                    "currents_a_tsc": [float(index + j) for j in range(14)],
                    "currents_a_display": [float(index + j) for j in range(14)],
                    "action_norm_tsc": [0.001 * index] * 14,
                    "abnormal": False,
                }
            )
        return rows

    @staticmethod
    def _control(horizon: int = 37) -> list[dict]:
        return [
            {
                "issued_mode_coefficients": [index, index + 1, index + 2],
                "applied_command_mode_coefficients": [index - 2, index - 1, index],
            }
            for index in range(horizon)
        ]

    def test_prefix_audit_allows_change_only_at_candidate_effect(self) -> None:
        first_effect = 28
        delay = 2
        issue = r12._transition_issue_step(first_effect, delay)
        source = {"trajectory": self._trajectory(), "control_trace": self._control()}
        result = copy.deepcopy(source)
        result["spec"] = {
            "anticipatory_first_affected_state_step": first_effect,
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
            "observed_first_affected_state_step": first_effect,
        }
        # Changes at the issue/effect boundary are permitted.
        result["control_trace"][issue]["issued_mode_coefficients"][0] += 10.0
        result["trajectory"][first_effect]["R"] += 0.01
        audit = r12._prefix_audit(source, result, atol=1e-12)
        self.assertTrue(audit["physics_prefix_exact"])
        self.assertTrue(audit["issued_prefix_exact"])
        self.assertTrue(audit["applied_prefix_exact"])
        self.assertTrue(audit["no_future_measurement"])
        self.assertTrue(audit["first_effect_alignment_exact"])
        # A one-step-earlier physical change must be rejected.
        result["trajectory"][first_effect - 1]["R"] += 0.01
        audit = r12._prefix_audit(source, result, atol=1e-12)
        self.assertFalse(audit["physics_prefix_exact"])

    def test_future_measurement_is_rejected_by_prefix_audit(self) -> None:
        source = {"trajectory": self._trajectory(), "control_trace": self._control()}
        result = copy.deepcopy(source)
        result["spec"] = {
            "anticipatory_first_affected_state_step": 28,
            "action_delay_steps": 1,
        }
        result["anticipatory_damping_trace"] = [
            {
                "future_measurement_used": True,
                "measurement_max_state_index_used": 28,
                "state_index_before": 25,
            }
        ]
        result["anticipatory_damping_summary"] = {
            "streaming_queue_consistent": True,
            "damping_control_steps": 1,
            "observed_first_affected_state_step": 28,
        }
        audit = r12._prefix_audit(source, result, atol=1e-12)
        self.assertFalse(audit["no_future_measurement"])

    def test_source_failure_set_is_exactly_four(self) -> None:
        cfg_path = (
            Path(r12.__file__).resolve().parents[2]
            / "configs"
            / "stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json"
        )
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        expected_fail = {
            ("nominal", 1, 0.9),
            ("nominal", 2, 0.9),
            ("RZ_p10_m10", 1, 0.9),
            ("RZ_p10_m10", 2, 0.9),
        }
        source = {}
        for target in ("nominal", "RZ_p10_m10"):
            for delay in (0, 1, 2):
                for slew in (0.9, 1.0, 1.1):
                    key = (target, delay, slew)
                    source[key] = {
                        "spec": {
                            "target_id": target,
                            "action_delay_steps": delay,
                            "slew_scale": slew,
                        },
                        "success": True,
                        "trajectory": [{}] * (38 if slew == 0.9 else 36),
                        "control_trace": [],
                    }
        def fake_metrics(_ctx, result, _policy):
            spec = result["spec"]
            key = (spec["target_id"], spec["action_delay_steps"], spec["slew_scale"])
            passed = key not in expected_fail
            return {
                "stage3_4_target_tracking_pass": passed,
                "stage3_4_best_endpoint_step": 25 if spec["slew_scale"] > 0.95 else 27,
                "stage3_4_tracking_minimum_signed_margin": 0.1 if passed else -0.1,
                "terminal_velocity_m_per_s": 0.05 if passed else 0.11,
                "stage3_4_sustained_box_max_error_m": 0.02,
            }
        with tempfile.TemporaryDirectory() as tmp:
            paths = r12.Stage41R12Paths.from_run_dir(Path(tmp))
            paths.source_audit.mkdir(parents=True)
            ctx = SimpleNamespace(
                cfg=cfg,
                paths=paths,
                source_stage41r11_run=Path(tmp),
                source_verdict={"primary_pass": True},
                r11_ctx=SimpleNamespace(r10_ctx=SimpleNamespace(r9_ctx=SimpleNamespace(r8_ctx=object()))),
            )
            with mock.patch.object(r12, "_source_oracle_map", return_value=source), mock.patch.object(
                r12.r8, "tracking_metrics", side_effect=fake_metrics
            ), mock.patch.object(
                r12, "read_json", return_value={"exact_trace_equivalence_fraction": 1.0}
            ), mock.patch.object(r12, "_update_state", return_value={}):
                summary = r12.run_source_audit(ctx)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["formal_contract_pass_count"], 14)
        observed = {
            (row["target_id"], row["actual_delay_steps"], row["actual_slew_scale"])
            for row in summary["formal_contract_failure_keys"]
        }
        self.assertEqual(observed, expected_fail)


class Stage41R12SelectionAndTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project = Path(r12.__file__).resolve().parents[2]
        cls.cfg = json.loads(
            (project / "configs" / "stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json").read_text(encoding="utf-8")
        )

    def test_policy_summary_requires_both_delays(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        rows = [
            {
                "policy_id": "p",
                "actual_delay_steps": delay,
                "r12_composite_pass": True,
                "formal_contract_minimum_signed_margin": 0.1 + delay * 0.01,
                "terminal_speed_m_per_s": 0.05,
                "action_rms": 0.02,
                "first_affected_state_step": 28,
                "physics_prefix_exact": True,
                "issued_prefix_exact": True,
                "applied_prefix_exact": True,
                "no_future_measurement": True,
                "streaming_queue_consistent": True,
            }
            for delay in (1, 2)
        ]
        summary = r12._policy_summary(ctx, rows, "p")
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["n_rollouts"], 2)
        self.assertEqual(summary["first_affected_state_step"], 28)
        one = r12._policy_summary(ctx, rows[:1], "p")
        self.assertFalse(one["passed"])
        self.assertFalse(one["coverage_complete"])

    def test_untrusted_calibration_token_is_rejected(self) -> None:
        bad_tokens = {
            (1, 0.9): {
                "success": True,
                "batch_trusted": False,
                "batch_trusted_correct": False,
                "batch_wrong_accept": False,
                "batch_selected_delay_steps": 1,
                "batch_selected_slew_scale": 0.9,
            },
            (2, 0.9): {
                "success": True,
                "batch_trusted": True,
                "batch_trusted_correct": True,
                "batch_wrong_accept": False,
                "batch_selected_delay_steps": 2,
                "batch_selected_slew_scale": 0.9,
            },
        }
        ctx = SimpleNamespace(r11_ctx=SimpleNamespace(r10_ctx=SimpleNamespace(r9_ctx=object())))
        with mock.patch.object(r12.r9, "source_calibration_tokens", return_value=bad_tokens):
            with self.assertRaisesRegex(ValueError, "trusted-correct"):
                r12._trusted_tokens(ctx)

    def test_r3_partial_checkpoint_hook_is_present_and_default_is_35(self) -> None:
        source = inspect.getsource(r3.LocalStage41Worker.evaluate)
        self.assertIn("_stage4_1r12_main_control_stop_step", source)
        self.assertIn("partial_main_control_checkpoint", source)
        self.assertIn("main_control_stop_step = 35 if partial_stop_step is None", source)
        self.assertIn("for env_step in range(env_phase_offset, main_control_stop_step)", source)


class Stage41R12SyntheticWorkerTests(unittest.TestCase):
    def test_delay_two_candidate_first_effect_is_causal_and_streaming(self) -> None:
        class FakeEnv:
            def __init__(self) -> None:
                self.runner = None
                self.last_state = {
                    "R": 1.0,
                    "Z": -1.0,
                    "Ip": 1000.0,
                    "currents_a_tsc": np.zeros(14),
                    "currents_a_display": np.zeros(14),
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
                    "target": {"R": 1.0, "Z": -1.0, "Ip": 1000.0},
                    "identification": {
                        "output_scales": {
                            "R_m": 0.03,
                            "Z_m": 0.03,
                            "vR_m_per_s": 0.1,
                            "vZ_m_per_s": 0.1,
                            "Ip_A": 2000.0,
                        }
                    },
                }
                self.env_cfg = {"dt_ms": 10}
                self.stub = SimpleNamespace(cfg={}, env_cfg=self.env_cfg)
                self.lower_mode = np.full(3, -1.0)
                self.upper_mode = np.full(3, 1.0)
                self.scheduler = FakeScheduler()

            def evaluate(self, spec):
                stop = int(spec["_stage4_1r12_main_control_stop_step"])
                delay = int(spec["action_delay_steps"])
                trajectory = [
                    {
                        "R": 1.0,
                        "Z": -1.0,
                        "Ip": 1000.0,
                        "currents_a_tsc": [0.0] * 14,
                        "currents_a_display": [0.0] * 14,
                        "action_norm_tsc": [0.0] * 14,
                        "vessel_current_total_a": 0.0,
                        "vessel_current_abs_sum_a": 0.0,
                        "vessel_current_rms_a": 0.0,
                        "vessel_current_max_abs_a": 0.0,
                        "abnormal": False,
                    }
                    for _ in range(stop + 1)
                ]
                control = [
                    {
                        "issued_mode_coefficients": [0.0, 0.0, 0.0],
                        "issued_desired_physical_mode_coefficients": [0.0, 0.0, 0.0],
                        "applied_command_mode_coefficients": [0.0, 0.0, 0.0],
                    }
                    for _ in range(stop)
                ]
                return {
                    "schema_version": 1,
                    "experiment_id": spec["experiment_id"],
                    "spec": spec,
                    "success": True,
                    "failure_reason": "",
                    "trajectory": trajectory,
                    "control_trace": control,
                    "partial_main_control_checkpoint": {
                        "state_index": stop,
                        "actual_delay_steps": delay,
                        "modeled_delay_steps": delay,
                        "actual_slew_scale": 0.9,
                        "modeled_slew_scale": 0.9,
                        "queue": [
                            {"command": [0.0, 0.0, 0.0], "desired_physical": [0.0, 0.0, 0.0]}
                            for _ in range(delay)
                        ],
                        "previous_correction_physical": [0.0, 0.0, 0.0],
                        "integral_normalized": [0.0] * 5,
                        "measurement_history_max_state_index": stop,
                        "future_measurement_used": False,
                        "issued_command_count": stop,
                    },
                }

            @staticmethod
            def _mode_action(effective, currents):
                return np.zeros(14, dtype=float)

        worker = object.__new__(r12.LocalStage41R12Worker)
        worker.r9_worker = SimpleNamespace(close=lambda: None)
        worker.base_worker = FakeBase()
        worker.bundle = {}
        worker.horizon_steps = 37
        spec = {
            "experiment_id": "synthetic-r12",
            "target_id": "nominal",
            "target_R_offset_m": 0.0,
            "target_Z_offset_m": 0.0,
            "target_Ip_offset_A": 0.0,
            "slew_scale": 0.9,
            "controller_slew_scale_estimate": 0.9,
            "action_delay_steps": 2,
            "controller_action_delay_steps": 2,
            "trusted_calibration_model": True,
            "horizon_steps": 37,
            "anticipatory_policy_id": "brake_effect_state28",
            "anticipatory_first_affected_state_step": 28,
            "terminal_controller_scale": 0.5,
            "terminal_controller_model_scale": 1.0,
            "terminal_velocity_measurement_gain": 1.5,
            "terminal_position_measurement_gain": 1.25,
            "terminal_ip_measurement_gain": 1.0,
            "terminal_model_phase_cap_step": 28,
            "actuator_gain_by_mode": [1.0, 1.0, 1.0],
            "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
            "actuator_bias_by_mode": [0.0, 0.0, 0.0],
        }
        fake_state = lambda env, index, action: {
            "R": 1.0,
            "Z": -1.0,
            "Ip": 1000.0,
            "currents_a_tsc": [0.0] * 14,
            "currents_a_display": [0.0] * 14,
            "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
            "vessel_current_total_a": 0.0,
            "vessel_current_abs_sum_a": 0.0,
            "vessel_current_rms_a": 0.0,
            "vessel_current_max_abs_a": 0.0,
            "abnormal": False,
        }
        solve = {
            "first_correction": np.zeros(3),
            "solver_success": True,
            "solver_status": 0,
            "solver_cost": 0.0,
            "effect_step": 0,
            "fixed_pending_steps": 2,
            "predicted_normalized_residual_rms": 0.0,
        }
        with mock.patch.object(r12.r3, "solve_delay_aware_physical_correction", return_value=solve), mock.patch.object(
            r12.r3.base, "_state_record", side_effect=fake_state
        ):
            result = worker.evaluate(spec)
        self.assertTrue(result["success"], result.get("failure_reason"))
        summary = result["anticipatory_damping_summary"]
        self.assertEqual(summary["transition_issue_start_step"], 25)
        self.assertEqual(summary["observed_first_affected_state_step"], 28)
        self.assertTrue(summary["streaming_queue_consistent"])
        self.assertFalse(summary["future_measurement_used"])
        self.assertEqual(len(result["trajectory"]), 38)
        self.assertEqual(len(result["control_trace"]), 37)


if __name__ == "__main__":
    unittest.main()
