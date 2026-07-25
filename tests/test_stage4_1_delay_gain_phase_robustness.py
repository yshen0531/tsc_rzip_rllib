from __future__ import annotations

import json
import math
import os
import resource
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1_delay_gain_phase_robustness as s41


class Stage41Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.root = root
        cls.cfg = json.loads((root / "configs/stage4_1_delay_gain_phase_robustness_350ms.json").read_text())
        cls.stage34_cfg = json.loads((root / "configs/stage3_4_late_arrival_continuation_mpc_350ms.json").read_text())

    def test_default_workers_are_128(self) -> None:
        self.assertEqual(self.cfg["parallel"]["n_workers"], 128)

    def test_runtime_preflight_allows_128_with_144_visible_cpus(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        with mock.patch("os.cpu_count", return_value=144), mock.patch.object(
            s41, "_available_memory_gb", return_value=200.0
        ), mock.patch("resource.getrlimit", return_value=(65536, 65536)), mock.patch.dict(
            os.environ, {"STAGE4_1_WORKERS": "128"}, clear=False
        ):
            payload = s41.runtime_preflight(ctx)
        self.assertEqual(payload["requested_workers"], 128)
        self.assertEqual(payload["safe_worker_ceiling"], 128)

    def test_runtime_preflight_rejects_oversubscription(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        with mock.patch("os.cpu_count", return_value=144), mock.patch.object(
            s41, "_available_memory_gb", return_value=200.0
        ), mock.patch("resource.getrlimit", return_value=(65536, 65536)), mock.patch.dict(
            os.environ, {"STAGE4_1_WORKERS": "129"}, clear=False
        ):
            with self.assertRaises(RuntimeError):
                s41.runtime_preflight(ctx)

    def test_wilson_lower_bound_is_sensible(self) -> None:
        self.assertLess(s41.wilson_lower_bound(9, 10), 0.9)
        self.assertGreater(s41.wilson_lower_bound(32, 32), 0.85)
        self.assertEqual(s41.wilson_lower_bound(0, 0), 0.0)

    def test_alpha_beta_observer_filters_and_predicts(self) -> None:
        observer = s41.AlphaBetaObserver(0.7, 0.15, 0.4, 2.0)
        dt = 0.01
        observer.update(np.array([0.0, 0.0, 100.0]), 0, dt)
        observer.update(np.array([0.001, -0.002, 102.0]), 1, dt)
        pos, vel, ip = observer.predict_to(2, dt)
        self.assertTrue(np.all(np.isfinite(pos)))
        self.assertTrue(np.all(np.isfinite(vel)))
        self.assertTrue(math.isfinite(ip))
        self.assertGreater(pos[0], 0.0)
        self.assertLess(pos[1], 0.0)

    def test_observer_ignores_duplicate_delayed_measurement(self) -> None:
        observer = s41.AlphaBetaObserver(0.7, 0.15, 0.4, 2.0)
        observer.update(np.array([0.0, 0.0, 100.0]), 0, 0.01)
        before = observer.position.copy()
        observer.update(np.array([10.0, 10.0, 999.0]), 0, 0.01)
        np.testing.assert_allclose(observer.position, before)

    def test_disturbance_headroom_respects_all_pulse_steps(self) -> None:
        nominal = np.zeros((35, 3))
        nominal[5, 0] = 0.8
        lower = np.array([-1.0, -1.0, -1.0])
        upper = np.array([1.0, 1.0, 1.0])
        positive = s41._disturbance_headroom(nominal, 4, 3, 0, 1, lower, upper)
        negative = s41._disturbance_headroom(nominal, 4, 3, 0, -1, lower, upper)
        self.assertAlmostEqual(positive, 0.2)
        self.assertAlmostEqual(negative, 1.0)

    def test_adaptive_recovery_has_36_families(self) -> None:
        cfg = self.cfg["adaptive_failure_recovery"]
        count = len(cfg["targets"]) * len(cfg["steps"]) * len(cfg["modes"]) * len(cfg["signs"])
        self.assertEqual(count, 36)
        self.assertEqual(len(cfg["severity_ladder"]), 7)

    def test_noise_campaign_has_requested_seed_counts(self) -> None:
        levels = {row["name"]: row["n_seeds"] for row in self.cfg["noise_statistics"]["levels"]}
        self.assertEqual(levels, {"low": 12, "medium": 16, "high": 32})

    def test_structured_required_categories_exclude_diagnostics(self) -> None:
        required = set(self.cfg["structured_uncertainty"]["required_categories"])
        self.assertIn("matched_action_delay", required)
        self.assertIn("scheduled_slew", required)
        self.assertNotIn("diagnostic_unmodeled_delay", required)
        self.assertNotIn("diagnostic_unmodeled_slew", required)

    def test_phase_preludes_are_compensated(self) -> None:
        for row in self.cfg["phase_aligned_history"]["preludes"]:
            delta = np.asarray(row["mode_deltas"], dtype=float)
            np.testing.assert_allclose(np.sum(delta, axis=0), np.zeros(3), atol=1e-12)

    def test_specs_change_with_controller_delay_model(self) -> None:
        target = {"target_id": "n", "R_offset_m": 0.0, "Z_offset_m": 0.0, "Ip_offset_A": 0.0}
        a = s41._make_spec(phase="x", scenario="s", category="c", target=target, controller_scale=0.5,
                           extra={"action_delay_steps": 1, "controller_action_delay_steps": 1})
        b = s41._make_spec(phase="x", scenario="s", category="c", target=target, controller_scale=0.5,
                           extra={"action_delay_steps": 1, "controller_action_delay_steps": 0})
        self.assertNotEqual(a["experiment_id"], b["experiment_id"])

    def test_delay_aware_solver_shifts_effect_step(self) -> None:
        cfg = json.loads(json.dumps(self.stage34_cfg))
        stub = SimpleNamespace(cfg=cfg, env_cfg={"dt_ms": 10})
        bundle = {
            "jacobian_normalized": np.zeros((175, 105)).tolist(),
            "output_scales": np.ones(175).tolist(),
        }
        nominal = np.zeros((35, 3))
        feature = np.zeros(175)
        result = s41.solve_delay_gain_aware_correction(
            stub, bundle,
            current_step=4,
            modeled_action_delay_steps=1,
            modeled_pending_commands=[np.zeros(3)],
            nominal_physical_coefficients=nominal,
            nominal_command_coefficients=nominal,
            nominal_feature=feature,
            measurement_normalized=np.zeros(5),
            integral_normalized=np.zeros(5),
            previous_correction=np.zeros(3),
            controller_scale=0.5,
            estimated_effective_gain_by_mode=np.ones(3),
            controller_model_scale=1.0,
        )
        self.assertEqual(result["effect_step"], 5)
        self.assertEqual(result["fixed_pending_steps"], 1)
        self.assertEqual(np.asarray(result["first_correction"]).shape, (3,))

    def test_delay_solver_accounts_for_fixed_pending_command(self) -> None:
        cfg = json.loads(json.dumps(self.stage34_cfg))
        stub = SimpleNamespace(cfg=cfg, env_cfg={"dt_ms": 10})
        jac = np.zeros((175, 105))
        jac[:, 0] = 1.0
        bundle = {"jacobian_normalized": jac.tolist(), "output_scales": np.ones(175).tolist()}
        nominal = np.zeros((35, 3))
        result = s41.solve_delay_gain_aware_correction(
            stub, bundle, current_step=0, modeled_action_delay_steps=1,
            modeled_pending_commands=[np.array([0.1, 0.0, 0.0])],
            nominal_physical_coefficients=nominal, nominal_command_coefficients=nominal,
            nominal_feature=np.zeros(175), measurement_normalized=np.zeros(5), integral_normalized=np.zeros(5),
            previous_correction=np.zeros(3), controller_scale=0.5,
            estimated_effective_gain_by_mode=np.ones(3), controller_model_scale=1.0,
        )
        self.assertTrue(math.isfinite(result["predicted_normalized_residual_rms"]))

    def test_final_verdict_never_claims_deployment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = s41.Stage41Paths.from_run_dir(Path(tmp))
            paths.analysis.mkdir(parents=True)
            state = {
                "regression_summary": {"passed": True},
                "recovery_summary": {"passed": True},
                "structured_summary": {"passed": True},
                "noise_summary": {"passed": True},
                "history_summary": {"passed": True},
                "restart_summary": {"true_restart_validation_available": False, "passed": False},
                "confirmation_summary": {"passed": True},
            }
            s41.atomic_write_json(paths.state, state)
            ctx = SimpleNamespace(paths=paths, source_stage40_run=Path("/s40"), source_stage34_run=Path("/s34"), source_scale=0.5)
            verdict = s41.final_verdict(ctx)
            self.assertTrue(verdict["finite_test_envelope_validated"])
            self.assertFalse(verdict["deployment_robustness_validated"])
            self.assertIn("TRUE_RESTART_NOT_AVAILABLE", verdict["verdict"])


    def test_worker_phase_alignment_and_delay_queue_keep_36_states(self) -> None:
        class Runner:
            def cleanup_episode_workspace(self, **kwargs):
                return None

        class FakeEnv:
            def __init__(self):
                self.runner = Runner()
                self.last_state = None
                self.steps = 0
                self.reset()

            def reset(self):
                self.steps = 0
                self.last_state = {
                    "time_ms": 1100, "R": 0.75, "Z": 0.0, "Ip": 29779.724,
                    "vessel_current_total_a": 0.0, "vessel_current_abs_sum_a": 0.0,
                    "vessel_current_rms_a": 0.0, "vessel_current_max_abs_a": 0.0,
                    "currents_a_tsc": np.zeros(14), "currents_a_display": np.zeros(14),
                    "abnormal": False, "runner_timing": {},
                }
                return np.zeros(1), {}

            def step(self, action):
                self.steps += 1
                currents = np.asarray(self.last_state["currents_a_tsc"], dtype=float) + np.asarray(action, dtype=float)
                self.last_state = {
                    **self.last_state, "time_ms": 1100 + 10 * self.steps,
                    "currents_a_tsc": currents, "currents_a_display": currents.copy(),
                    "runner_timing": {},
                }
                return np.zeros(1), 0.0, False, self.steps >= 35, {}

            def close(self):
                return None

        cfg = json.loads(json.dumps(self.stage34_cfg))
        payload = {
            "cfg": cfg, "stage4_1_cfg": self.cfg, "train_cfg": {},
            "env_cfg": {"dt_ms": 10}, "modes_tsc": np.eye(14, 3).tolist(),
            "max_delta_a": 3.0, "min_current_tsc": (-1e6*np.ones(14)).tolist(),
            "max_current_tsc": (1e6*np.ones(14)).tolist(), "variant_id": "base", "slew_scale": 1.0,
        }
        entry = {
            "candidate_id": "fake", "stage3_4_target_tracking_pass": True,
            "task": {"task_id": "nominal", "R_offset_m": 0.0, "Z_offset_m": 0.0, "Ip_offset_A": 0.0},
            "full_control_vector": np.zeros(105).tolist(),
            "nominal_trajectory_RZI": np.tile(np.array([[0.75, 0.0, 29779.724]]), (36, 1)).tolist(),
            "nominal_velocity_RZ": np.zeros((36, 2)).tolist(),
        }
        library = {"entries": [entry]}
        bundle = {"jacobian_normalized": np.zeros((175, 105)).tolist(), "output_scales": np.ones(175).tolist()}
        import sys, types, tsc_rzip_rllib.envs as envs_pkg
        fake_factory = types.ModuleType("tsc_rzip_rllib.envs.factory")
        fake_factory.make_tsc_rzip_env = lambda *args, **kwargs: FakeEnv()
        with mock.patch.dict(sys.modules, {"tsc_rzip_rllib.envs.factory": fake_factory}), mock.patch.object(envs_pkg, "factory", fake_factory, create=True):
            worker = s41.LocalStage41Worker(payload, library, bundle, "fake")
            result = worker.evaluate({
                "experiment_id": "fake", "scenario": "fake", "category": "test",
                "target_R_offset_m": 0.0, "target_Z_offset_m": 0.0, "target_Ip_offset_A": 0.0,
                "controller_scale": 0.5, "action_delay_steps": 1, "controller_action_delay_steps": 1,
                "prime_action_queue_with_nominal": True,
                "prelude_mode_deltas": [[0.05, 0.0, 0.0], [-0.05, 0.0, 0.0], [0.0, 0.0, 0.0]],
            })
        self.assertTrue(result["success"], result.get("failure_reason"))
        self.assertEqual(len(result["trajectory"]), 36)
        self.assertEqual(result["phase_start_diagnostics"]["phase_offset_steps"], 3)
        self.assertEqual(result["control_trace"][0]["step"], 3)
        self.assertEqual(result["control_trace"][0]["actual_action_delay_steps"], 1)

    def test_synthetic_stage41_test(self) -> None:
        payload = s41.synthetic_stage41_test()
        self.assertTrue(payload["synthetic_ok"])
        self.assertEqual(payload["workers"], 128)


if __name__ == "__main__":
    unittest.main()
