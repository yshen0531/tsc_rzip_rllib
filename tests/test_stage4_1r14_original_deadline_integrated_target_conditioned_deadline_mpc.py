from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc as r14


class Stage41R14ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = Path(r14.__file__).resolve().parents[2]
        cls.config_path = (
            cls.project
            / "configs"
            / "stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_370ms.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_immutable_contract_fixed_onset_and_candidate_bank(self) -> None:
        r14.validate_config(self.cfg)
        timing = self.cfg["formal_timing_contract"]
        self.assertEqual(
            (
                timing["normal_slew"]["arrival_deadline_step"],
                timing["normal_slew"]["horizon_steps"],
            ),
            (25, 35),
        )
        self.assertEqual(
            (
                timing["weak_slew"]["arrival_deadline_step"],
                timing["weak_slew"]["horizon_steps"],
            ),
            (27, 37),
        )
        design = self.cfg["integrated_deadline_mpc"]
        self.assertEqual(design["fixed_first_affected_state_step"], 23)
        self.assertEqual(design["deadline_velocity_states"], [24, 25, 26, 27])
        self.assertEqual(len(design["candidate_bank"]), 6)
        self.assertTrue(design["require_no_onset_rescan"])
        self.assertTrue(self.cfg["stage4_2r1_was_not_run_or_reused"])

    def test_onset_rescan_is_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["integrated_deadline_mpc"]["fixed_first_affected_state_step"] = 22
        with self.assertRaisesRegex(ValueError, "state 23"):
            r14.validate_config(bad)

    def test_deadline_expansion_is_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"].append(28)
        with self.assertRaisesRegex(ValueError, "arrival list"):
            r14.validate_config(bad)

    def test_target_conditioned_nominal_cannot_be_disabled(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["integrated_deadline_mpc"]["target_conditioned_nominal_physical_required"] = False
        with self.assertRaisesRegex(ValueError, "target-conditioned nominal feedforward"):
            r14.validate_config(bad)

    def test_checkpoint_integral_cannot_be_reset(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["integrated_deadline_mpc"]["checkpoint_integral_preservation_required"] = False
        with self.assertRaisesRegex(ValueError, "checkpoint integral"):
            r14.validate_config(bad)

    def test_candidate_bank_change_is_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["integrated_deadline_mpc"]["candidate_bank"][0][
            "deadline_velocity_weight_multiplier"
        ] = 2.0
        with self.assertRaisesRegex(ValueError, "candidate bank"):
            r14.validate_config(bad)

    def test_issue_effect_alignment_for_both_delays(self) -> None:
        for delay in (1, 2):
            issue = r14._transition_issue_step(23, delay)
            self.assertEqual(issue + delay + 1, 23)

    def test_self_test_budget_and_scope(self) -> None:
        payload = r14.self_test(self.project)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["development_rollout_count"], 24)
        self.assertEqual(payload["calibrated_rollout_count_if_development_passes"], 4)
        self.assertEqual(payload["maximum_true_tsc_rollouts"], 28)
        self.assertTrue(payload["target_conditioned_nominal_required"])
        self.assertTrue(payload["checkpoint_integral_preservation_required"])
        self.assertFalse(payload["unseen_target_holdout_claimed"])


class Stage41R14SpecAndSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project = Path(r14.__file__).resolve().parents[2]
        cls.cfg = json.loads(
            (
                project
                / "configs"
                / "stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_370ms.json"
            ).read_text(encoding="utf-8")
        )

    @staticmethod
    def _nested_r13_ctx() -> SimpleNamespace:
        leaf = object()
        r8ctx = SimpleNamespace(cfg={"batch_selector": {}})
        r9ctx = SimpleNamespace(r8_ctx=r8ctx)
        r10ctx = SimpleNamespace(r9_ctx=r9ctx)
        r11ctx = SimpleNamespace(r10_ctx=r10ctx)
        r12ctx = SimpleNamespace(r11_ctx=r11ctx)
        return SimpleNamespace(r12_ctx=r12ctx, _leaf=leaf)

    def test_development_specs_cover_6_by_2_by_2(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg, r13_ctx=self._nested_r13_ctx())

        def fake_main_extra(
            _ctx,
            *,
            actual_delay,
            actual_slew,
            modeled_delay,
            modeled_slew,
            **_kwargs,
        ):
            return {
                "action_delay_steps": int(actual_delay),
                "controller_action_delay_steps": int(modeled_delay),
                "slew_scale": float(actual_slew),
                "controller_slew_scale_estimate": float(modeled_slew),
                "trusted_calibration_model": True,
            }

        with mock.patch.object(r14, "materialize_variant", return_value=("v", {})), mock.patch.object(
            r14.r8, "_main_extra", side_effect=fake_main_extra
        ), mock.patch.object(r14, "_source_scale", return_value=1.0):
            specs = r14.build_development_specs(ctx)
        self.assertEqual(len(specs), 24)
        self.assertEqual(len({spec["experiment_id"] for spec in specs}), 24)
        self.assertEqual({spec["target_id"] for spec in specs}, {"nominal", "RZ_p10_m10"})
        self.assertEqual({spec["action_delay_steps"] for spec in specs}, {1, 2})
        self.assertEqual(
            {spec["anticipatory_first_affected_state_step"] for spec in specs},
            {23},
        )
        self.assertTrue(all(spec["target_conditioned_nominal_physical_required"] for spec in specs))
        self.assertTrue(all(spec["checkpoint_integral_preservation_required"] for spec in specs))

    @staticmethod
    def _row(target: str, delay: int, *, passed: bool = True, margin: float = 0.1) -> dict:
        return {
            "policy_id": "itc_vw3_c0p50",
            "target_id": target,
            "actual_delay_steps": delay,
            "r14_composite_pass": passed,
            "formal_contract_minimum_signed_margin": margin,
            "terminal_speed_m_per_s": 0.04,
            "action_rms": 0.2,
            "any_mode_bound_fraction": 0.2,
            "physics_prefix_exact": True,
            "issued_prefix_exact": True,
            "applied_prefix_exact": True,
            "no_future_measurement": True,
            "streaming_queue_consistent": True,
            "target_conditioned_nominal_retained": True,
            "checkpoint_integral_preserved": True,
        }

    def test_candidate_summary_requires_both_targets_and_preserved_state(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        policy = self.cfg["integrated_deadline_mpc"]["candidate_bank"][1]
        rows = [self._row("nominal", 1), self._row("RZ_p10_m10", 1)]
        summary = r14._candidate_summary(ctx, rows, policy=policy, delay=1)
        self.assertTrue(summary["passed"])
        one = r14._candidate_summary(ctx, rows[:1], policy=policy, delay=1)
        self.assertFalse(one["passed"])
        broken = copy.deepcopy(rows)
        broken[1]["checkpoint_integral_preserved"] = False
        self.assertFalse(
            r14._candidate_summary(ctx, broken, policy=policy, delay=1)["passed"]
        )

    def test_candidate_summary_rejects_one_failed_target(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        policy = self.cfg["integrated_deadline_mpc"]["candidate_bank"][1]
        rows = [
            self._row("nominal", 2),
            self._row("RZ_p10_m10", 2, passed=False, margin=-0.02),
        ]
        summary = r14._candidate_summary(ctx, rows, policy=policy, delay=2)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["target_pass_fraction"], 0.5)


class Stage41R14SolverTests(unittest.TestCase):
    @staticmethod
    def _stub() -> SimpleNamespace:
        return SimpleNamespace(
            env_cfg={"dt_ms": 10.0},
            cfg={
                "identification": {
                    "output_scales": {
                        "R_m": 1.0,
                        "Z_m": 1.0,
                        "vR_m_per_s": 1.0,
                        "vZ_m_per_s": 1.0,
                        "Ip_A": 1.0,
                    }
                },
                "trajectory": {
                    "coefficient_lower": [-1.0, -1.0, -1.0],
                    "coefficient_upper": [1.0, 1.0, 1.0],
                },
                "mpc": {
                    "integral_measurement_gain": [0.0] * 5,
                    "output_weights": {"R": 1.0, "Z": 1.0, "vR": 1.0, "vZ": 1.0, "Ip": 1.0},
                    "future_discount": 1.0,
                    "hold_weight_start_state": 14,
                    "hold_weight_multiplier": 1.0,
                    "per_step_feedback_limit_by_mode": [0.2, 0.2, 0.07],
                    "per_step_correction_rate_limit_by_mode": [0.2, 0.2, 0.07],
                    "ridge_lambda": 0.0,
                    "future_correction_smoothness": 0.0,
                    "first_action_rate_weight": 0.0,
                    "solver_tolerance": 1e-8,
                    "solver_max_iterations": 50,
                },
            },
        )

    def test_deadline_velocity_rows_are_explicitly_weighted(self) -> None:
        stub = self._stub()
        bundle = {"jacobian_normalized": np.zeros((175, 105)), "output_scales": np.ones(175)}
        captured: list[tuple[np.ndarray, np.ndarray]] = []

        def fake_lsq(a, b, **_kwargs):
            captured.append((np.asarray(a, dtype=float), np.asarray(b, dtype=float)))
            return SimpleNamespace(
                x=np.zeros(a.shape[1]),
                success=True,
                status=1,
                cost=0.0,
                optimality=0.0,
            )

        kwargs = dict(
            current_step=20,
            modeled_action_delay_steps=1,
            modeled_pending_physical_coefficients=[np.zeros(3)],
            nominal_physical_coefficients=np.zeros((35, 3)),
            nominal_feature=np.ones(175) * 0.01,
            measurement_normalized=np.zeros(5),
            integral_normalized=np.zeros(5),
            previous_correction=np.zeros(3),
            controller_scale=0.5,
            controller_model_scale=1.0,
            deadline_velocity_states=[24, 25, 26, 27],
        )
        with mock.patch("scipy.optimize.lsq_linear", side_effect=fake_lsq):
            low = r14.solve_deadline_weighted_physical_correction(
                stub, bundle, deadline_velocity_weight_multiplier=1.0, **kwargs
            )
            high = r14.solve_deadline_weighted_physical_correction(
                stub, bundle, deadline_velocity_weight_multiplier=10.0, **kwargs
            )
        self.assertEqual(low["deadline_velocity_row_count"], 8)
        self.assertEqual(high["deadline_velocity_row_count"], 8)
        self.assertEqual(low["deadline_velocity_weight_multiplier"], 1.0)
        self.assertEqual(high["deadline_velocity_weight_multiplier"], 10.0)
        self.assertEqual(len(captured), 2)
        # Jacobian is zero, but the solver contract still receives the same
        # shape while the weighted right-hand side is changed internally.
        self.assertEqual(captured[0][0].shape, captured[1][0].shape)
        self.assertGreater(np.linalg.norm(captured[1][1]), np.linalg.norm(captured[0][1]))

    def test_solver_returns_zero_after_identified_main_horizon(self) -> None:
        stub = self._stub()
        bundle = {"jacobian_normalized": np.zeros((175, 105)), "output_scales": np.ones(175)}
        result = r14.solve_deadline_weighted_physical_correction(
            stub,
            bundle,
            current_step=34,
            modeled_action_delay_steps=1,
            modeled_pending_physical_coefficients=[np.zeros(3)],
            nominal_physical_coefficients=np.zeros((35, 3)),
            nominal_feature=np.zeros(175),
            measurement_normalized=np.zeros(5),
            integral_normalized=np.zeros(5),
            previous_correction=np.zeros(3),
            controller_scale=0.5,
            controller_model_scale=1.0,
            deadline_velocity_states=[24, 25, 26, 27],
            deadline_velocity_weight_multiplier=3.0,
        )
        self.assertTrue(result["solver_success"])
        np.testing.assert_array_equal(result["first_correction"], np.zeros(3))


class Stage41R14SafetyTests(unittest.TestCase):
    def test_untrusted_model_cannot_start_worker(self) -> None:
        worker = object.__new__(r14.LocalStage41R14Worker)
        worker.base_worker = SimpleNamespace(env=SimpleNamespace(runner=None))
        result = worker.evaluate(
            {
                "experiment_id": "bad",
                "slew_scale": 0.9,
                "controller_slew_scale_estimate": 0.9,
                "action_delay_steps": 1,
                "controller_action_delay_steps": 1,
                "trusted_calibration_model": False,
            }
        )
        self.assertFalse(result["success"])
        self.assertIn("untrusted", result["failure_reason"])

    def test_finalize_distinguishes_development_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths = r14.Stage41R14Paths.from_run_dir(Path(td))
            paths.analysis.mkdir(parents=True, exist_ok=True)
            state = {
                "source_audit_summary": {"passed": True},
                "oracle_development_summary": {"passed": False},
                "calibrated_confirmation_summary": {},
                "formal_grid_confirmation_summary": {},
                "restart_audit_summary": {"true_restart_validation_available": False},
            }
            r14.atomic_write_json(paths.state, state)
            ctx = SimpleNamespace(
                paths=paths,
                cfg={"final_task": "robust causal control"},
                source_stage41r13_run=Path("/source/r13"),
                source_stage41r12_run=Path("/source/r12"),
            )
            summary = r14.finalize(ctx)
            final_state = r14.read_json(paths.state)
            self.assertFalse(summary["primary_pass"])
            self.assertEqual(
                final_state["stop_reason"],
                "formal_original_deadline_integrated_deadline_mpc_failed",
            )
            self.assertFalse(summary["arrival_deadline_expanded"])


class Stage41R14SyntheticWorkerTests(unittest.TestCase):
    def test_delay_two_full_worker_preserves_nominal_integral_and_streaming_queue(self) -> None:
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
                        "queue": [
                            {
                                "command": [0.0, 0.0, 0.0],
                                "desired_physical": [0.0, 0.0, 0.0],
                            }
                            for _ in range(delay)
                        ],
                        "previous_correction_physical": [0.01, -0.01, 0.0],
                        "integral_normalized": [0.1, -0.2, 0.3, -0.4, 0.5],
                        "future_measurement_used": False,
                    },
                }

            @staticmethod
            def _integral_candidate(previous, measurement, *, reference_step, anti_windup_enabled):
                return np.asarray(previous, dtype=float)

            @staticmethod
            def _mode_action(effective, currents):
                return np.zeros(14, dtype=float)

        worker = object.__new__(r14.LocalStage41R14Worker)
        worker.r9_worker = SimpleNamespace(close=lambda: None)
        worker.base_worker = FakeBase()
        worker.bundle = {}
        worker.library = {}
        worker.horizon_steps = 37
        spec = {
            "experiment_id": "synthetic-r14",
            "target_id": "RZ_p10_m10",
            "target_R_offset_m": 0.01,
            "target_Z_offset_m": -0.01,
            "target_Ip_offset_A": 0.0,
            "slew_scale": 0.9,
            "controller_slew_scale_estimate": 0.9,
            "action_delay_steps": 2,
            "controller_action_delay_steps": 2,
            "trusted_calibration_model": True,
            "horizon_steps": 37,
            "anticipatory_policy_id": "itc_vw3_c0p50",
            "anticipatory_first_affected_state_step": 23,
            "anticipatory_transition_issue_step": 20,
            "integrated_controller_scale": 0.5,
            "integrated_controller_model_scale": 1.0,
            "deadline_velocity_weight_multiplier": 3.0,
            "deadline_velocity_states": [24, 25, 26, 27],
            "tail_controller_scale": 0.5,
            "tail_velocity_measurement_gain": 1.5,
            "tail_position_measurement_gain": 1.25,
            "tail_ip_measurement_gain": 1.0,
            "tail_model_phase_cap_step": 28,
            "actuator_gain_by_mode": [1.0, 1.0, 1.0],
            "controller_gain_estimate_by_mode": [1.0, 1.0, 1.0],
            "actuator_bias_by_mode": [0.0, 0.0, 0.0],
        }
        interpolation = {
            "task_ids": ["RZ_p10_m10mm"],
            "full_control_vector": (np.ones((35, 3)) * 0.02).reshape(-1).tolist(),
            "nominal_trajectory_RZI": np.tile([1.01, -1.01, 1000.0], (36, 1)).tolist(),
            "nominal_velocity_RZ": np.zeros((36, 2)).tolist(),
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
        main_solve = {
            "first_correction": np.zeros(3),
            "solver_success": True,
            "solver_status": 0,
            "solver_cost": 0.0,
            "effect_step": 22,
            "fixed_pending_steps": 2,
            "deadline_velocity_row_count": 8,
            "active_lower": 0,
            "active_upper": 0,
            "predicted_normalized_residual_rms": 0.0,
        }
        tail_solve = dict(main_solve, effect_step=30, deadline_velocity_row_count=0)
        with mock.patch.object(r14.s34, "interpolation_for_target", return_value=interpolation), mock.patch.object(
            r14, "solve_deadline_weighted_physical_correction", return_value=main_solve
        ), mock.patch.object(
            r14.r3, "solve_delay_aware_physical_correction", return_value=tail_solve
        ), mock.patch.object(
            r14.r3.base, "_state_record", side_effect=fake_state
        ):
            result = worker.evaluate(spec)
        self.assertTrue(result["success"], result.get("failure_reason"))
        summary = result["integrated_deadline_mpc_summary"]
        self.assertEqual(summary["transition_issue_start_step"], 20)
        self.assertEqual(summary["observed_first_affected_state_step"], 23)
        self.assertTrue(summary["target_conditioned_nominal_retained"])
        self.assertTrue(summary["checkpoint_integral_preserved"])
        self.assertGreater(summary["checkpoint_integral_l2"], 0.0)
        self.assertTrue(summary["streaming_queue_consistent"])
        self.assertFalse(summary["future_measurement_used"])
        self.assertEqual(len(result["trajectory"]), 38)
        self.assertEqual(len(result["control_trace"]), 37)
        first = result["integrated_deadline_mpc_trace"][0]
        self.assertEqual(first["feedforward_physical_mode_coefficients"], [0.02, 0.02, 0.02])
        self.assertNotEqual(first["integral_normalized"], [0.0] * 5)


if __name__ == "__main__":
    unittest.main()
