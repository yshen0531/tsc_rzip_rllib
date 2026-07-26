from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage3_4_late_arrival_continuation_mpc as s34
from tsc_rzip_rllib.diagnostics import stage4_1r3_control_aware_robustness as s41r3


class Stage41R3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (cls.root / "configs/stage4_1r3_control_aware_residual_observer_350ms.json").read_text()
        )
        cls.stage34_cfg = json.loads(
            (cls.root / "configs/stage3_4_late_arrival_continuation_mpc_350ms.json").read_text()
        )

    def test_revision_and_workers_are_locked(self) -> None:
        self.assertEqual(
            self.cfg["controller_revision"],
            "control_aware_residual_observer_antiwindup_v3",
        )
        self.assertEqual(self.cfg["parallel"]["n_workers"], 128)
        self.assertEqual(
            self.cfg["restart_sweep"]["environment_variable"],
            "STAGE4_1R3_START_FOLDERS",
        )

    def test_runtime_preflight_accepts_128_and_rejects_oversubscription(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        with mock.patch("os.cpu_count", return_value=144), mock.patch.object(
            s41r3, "_available_memory_gb", return_value=200.0
        ), mock.patch("resource.getrlimit", return_value=(65536, 65536)), mock.patch.dict(
            os.environ, {"STAGE4_1R3_WORKERS": "128"}, clear=False
        ):
            payload = s41r3.runtime_preflight(ctx)
        self.assertEqual(payload["requested_workers"], 128)
        with mock.patch("os.cpu_count", return_value=144), mock.patch.object(
            s41r3, "_available_memory_gb", return_value=200.0
        ), mock.patch("resource.getrlimit", return_value=(65536, 65536)), mock.patch.dict(
            os.environ, {"STAGE4_1R3_WORKERS": "129"}, clear=False
        ):
            with self.assertRaises(RuntimeError):
                s41r3.runtime_preflight(ctx)

    def test_known_control_effect_is_causal_and_physically_scaled(self) -> None:
        jac = np.zeros((175, 105), dtype=float)
        # State 1 rows [R,Z,vR,vZ,Ip], action step 0 mode 0.
        jac[[0, 35, 70, 105, 140], 0] = [0.2, -0.1, 0.3, -0.2, 0.05]
        bundle = {"jacobian_normalized": jac.tolist()}
        delta = np.zeros((35, 3), dtype=float)
        delta[0, 0] = 0.5
        scales = np.array([0.03, 0.03, 0.10, 0.10, 1000.0])
        np.testing.assert_allclose(
            s41r3.known_control_effect_physical(
                bundle,
                state_index=0,
                known_physical_delta_by_step=delta,
                measurement_scales=scales,
            ),
            np.zeros(5),
        )
        effect = s41r3.known_control_effect_physical(
            bundle,
            state_index=1,
            known_physical_delta_by_step=delta,
            measurement_scales=scales,
        )
        np.testing.assert_allclose(effect, [0.003, -0.0015, 0.015, -0.01, 25.0])

    def test_control_aware_observer_exact_known_response_has_zero_residual(self) -> None:
        nominal = np.zeros((5, 3), dtype=float)
        known = np.array([0.001, -0.002, 0.03, -0.04, 12.0])
        observer = s41r3.ControlAwareResidualObserver(
            alpha=0.68,
            beta=0.28,
            direct_velocity_blend=0.2,
            alpha_ip=0.4,
            max_abs_residual_velocity=1.0,
        )
        measurement = np.array([known[0], known[1], known[4]])
        observer.update(measurement, 1, nominal, known, 0.01)
        pos, vel, ip, residual = observer.predict_total_error_to(1, known, 0.01)
        np.testing.assert_allclose(pos, known[:2], atol=1e-14)
        np.testing.assert_allclose(vel, known[2:4], atol=1e-14)
        self.assertAlmostEqual(ip, known[4], places=12)
        np.testing.assert_allclose(residual, np.zeros(5), atol=1e-14)

    def test_control_aware_observer_preserves_unexplained_residual(self) -> None:
        nominal = np.zeros((4, 3), dtype=float)
        known = np.array([0.001, 0.002, 0.01, -0.02, 5.0])
        residual_position = np.array([0.0004, -0.0007])
        residual_ip = 3.0
        observer = s41r3.ControlAwareResidualObserver(
            alpha=1.0,
            beta=0.0,
            direct_velocity_blend=1.0,
            alpha_ip=1.0,
            max_abs_residual_velocity=1.0,
        )
        observer.update(
            np.array([
                known[0] + residual_position[0],
                known[1] + residual_position[1],
                known[4] + residual_ip,
            ]),
            1,
            nominal,
            known,
            0.01,
        )
        pos, _, ip, residual = observer.predict_total_error_to(1, known, 0.01)
        np.testing.assert_allclose(pos, known[:2] + residual_position)
        self.assertAlmostEqual(ip, known[4] + residual_ip)
        np.testing.assert_allclose(residual[:2], residual_position)

    def test_clean_sensor_path_detection(self) -> None:
        self.assertTrue(s41r3._sensor_path_is_clean({}))
        self.assertTrue(s41r3._sensor_path_is_clean({"observation_delay_steps": 0}))
        self.assertFalse(s41r3._sensor_path_is_clean({"observation_delay_steps": 1}))
        self.assertFalse(
            s41r3._sensor_path_is_clean(
                {"observation_noise": {"R_sigma_m": 1e-6}}
            )
        )
        self.assertFalse(
            s41r3._sensor_path_is_clean({"observation_bias": {"Ip_A": 1.0}})
        )

    def test_legacy_measurement_matches_nominal_without_noise(self) -> None:
        nominal = np.array(
            [
                [0.750, 0.000, 30000.0],
                [0.751, 0.002, 30010.0],
                [0.753, 0.003, 30020.0],
            ]
        )
        nominal_velocity = np.array([[0.0, 0.0], [0.1, 0.2], [0.2, 0.1]])
        error = s41r3.legacy_measurement_error(
            [row.copy() for row in nominal],
            delayed_local_index=2,
            delayed_absolute_index=2,
            current_absolute_index=2,
            nominal_y=nominal,
            nominal_velocity=nominal_velocity,
            dt_s=0.01,
        )
        np.testing.assert_allclose(error, np.zeros(5), atol=1e-12)

    def test_anti_windup_limits_and_freezes_integral(self) -> None:
        worker = object.__new__(s41r3.LocalStage41Worker)
        worker.cfg = {"mpc": {"integral_decay": 0.92}}
        worker.robust_cfg = self.cfg
        previous = np.array([2.4, -2.4, 1.4, -1.4, 2.4])
        measurement = np.ones(5)
        candidate = worker._integral_candidate(
            previous, measurement, reference_step=20, anti_windup_enabled=True
        )
        limits = np.array(self.cfg["controller_upgrade"]["anti_windup"]["integral_abs_limit"])
        self.assertTrue(np.all(np.abs(candidate) <= limits + 1e-12))
        frozen = worker._anti_windup_finalize(
            previous, candidate, saturated=True, anti_windup_enabled=True
        )
        expected = (
            self.cfg["controller_upgrade"]["anti_windup"]["saturated_integral_decay"]
            * previous
        )
        np.testing.assert_allclose(frozen, np.clip(expected, -limits, limits))

    def test_physical_scheduler_identity_and_compensation(self) -> None:
        scheduler = s41r3.PhysicalCoilScheduler(
            modes_tsc=np.eye(14, 3),
            nominal_max_delta_a=3.0,
            command_max_delta_a=3.0,
            min_current=-1e6 * np.ones(14),
            max_current=1e6 * np.ones(14),
            lower_mode=np.array([-2.6, -2.6, -0.9]),
            upper_mode=np.array([2.6, 2.6, 0.9]),
        )
        desired = np.array([0.4, -0.2, 0.1])
        identity = scheduler.solve_command(
            desired, np.zeros(14), np.ones(3), 1.0, enabled=True
        )
        np.testing.assert_allclose(identity["command"], desired, atol=1e-14)
        self.assertLess(identity["mismatch_rms_a"], 1e-12)
        compensated = scheduler.solve_command(
            desired, np.zeros(14), np.array([0.9, 1.1, 1.0]), 0.9, enabled=True
        )
        self.assertTrue(compensated["solver_success"])
        self.assertLess(compensated["mismatch_rms_a"], 1e-4)

    def test_zero_delay_solver_matches_stage34(self) -> None:
        cfg = json.loads(json.dumps(self.stage34_cfg))
        stub = SimpleNamespace(cfg=cfg, env_cfg={"dt_ms": 10})
        rng = np.random.default_rng(7)
        jac = rng.normal(0.0, 0.01, size=(175, 105))
        bundle = {
            "jacobian_normalized": jac.tolist(),
            "output_scales": np.ones(175).tolist(),
        }
        nominal = rng.normal(0.0, 0.1, size=(35, 3))
        feature = rng.normal(0.0, 0.01, size=175)
        measurement = rng.normal(0.0, 0.02, size=5)
        integral = rng.normal(0.0, 0.01, size=5)
        previous = np.array([0.01, -0.02, 0.005])
        legacy = s34.solve_receding_horizon_correction(
            stub,
            bundle,
            current_step=4,
            nominal_coefficients=nominal,
            nominal_feature=feature,
            measurement_normalized=measurement,
            integral_normalized=integral,
            previous_correction=previous,
            controller_scale=0.5,
        )
        revised = s41r3.solve_delay_aware_physical_correction(
            stub,
            bundle,
            current_step=4,
            modeled_action_delay_steps=0,
            modeled_pending_physical_coefficients=[],
            nominal_physical_coefficients=nominal,
            nominal_feature=feature,
            measurement_normalized=measurement,
            integral_normalized=integral,
            previous_correction=previous,
            controller_scale=0.5,
            controller_model_scale=1.0,
        )
        np.testing.assert_allclose(
            revised["first_correction"], legacy["first_correction"], atol=1e-10
        )

    def test_ablation_has_64_rollouts_and_only_control_aware_is_selectable(self) -> None:
        cfg = self.cfg["observer_ablation"]
        self.assertEqual(
            len(cfg["targets"]) * len(cfg["conditions"]) * len(cfg["variants"]),
            64,
        )
        selectable = [row for row in cfg["variants"] if row["selectable"]]
        self.assertEqual(len(selectable), 2)
        self.assertTrue(
            all(row["observer_variant"] == "control_aware_residual" for row in selectable)
        )

    def test_selected_controller_settings_are_attached_to_downstream_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            state = run / s41r3.STATE_FILENAME
            s41r3.atomic_write_json(
                state,
                {
                    "selected_observer_variant": "control_aware_residual",
                    "selected_anti_windup_enabled": True,
                },
            )
            ctx = SimpleNamespace(paths=SimpleNamespace(state=state))
            original = {
                "experiment_id": "old",
                "phase": "structured_uncertainty",
                "controller_scale": 0.5,
            }
            cooked = s41r3._apply_selected_controller_settings(ctx, [original])[0]
            self.assertEqual(cooked["observer_variant"], "control_aware_residual")
            self.assertTrue(cooked["anti_windup_enabled"])
            self.assertNotEqual(cooked["experiment_id"], "old")

    def test_execute_stops_after_regression_failure(self) -> None:
        fake_ctx = SimpleNamespace()
        with mock.patch.object(s41r3, "load_stage41_config", return_value=fake_ctx), mock.patch.object(
            s41r3, "prepare_stage41", return_value={}
        ), mock.patch.object(
            s41r3, "run_regression", return_value={"passed": False}
        ), mock.patch.object(
            s41r3, "analyze_stage41", return_value={"stopped": "regression"}
        ) as analyze, mock.patch.object(s41r3, "_update_state") as update, mock.patch.object(
            s41r3, "run_observer_ablation"
        ) as ablation:
            result = s41r3.execute("unused.json", command="all")
        self.assertEqual(result, {"stopped": "regression"})
        analyze.assert_called_once()
        update.assert_called_once()
        ablation.assert_not_called()

    def test_execute_stops_after_ablation_failure(self) -> None:
        fake_ctx = SimpleNamespace()
        with mock.patch.object(s41r3, "load_stage41_config", return_value=fake_ctx), mock.patch.object(
            s41r3, "prepare_stage41", return_value={}
        ), mock.patch.object(
            s41r3, "run_regression", return_value={"passed": True}
        ), mock.patch.object(
            s41r3, "run_observer_ablation", return_value={"passed": False}
        ), mock.patch.object(
            s41r3, "analyze_stage41", return_value={"stopped": "ablation"}
        ), mock.patch.object(s41r3, "_update_state") as update, mock.patch.object(
            s41r3, "run_recovery"
        ) as recovery:
            result = s41r3.execute("unused.json", command="all")
        self.assertEqual(result, {"stopped": "ablation"})
        update.assert_called_once()
        recovery.assert_not_called()

    def test_validate_config_rejects_wrong_revision(self) -> None:
        bad = json.loads(json.dumps(self.cfg))
        bad["controller_revision"] = "wrong"
        source = {"gate": json.loads(json.dumps(self.cfg["gate"]))}
        with self.assertRaises(ValueError):
            s41r3.validate_stage41_config(bad, source)

    def test_synthetic_self_test(self) -> None:
        result = s41r3.synthetic_stage41_test()
        self.assertTrue(result["synthetic_ok"])
        self.assertEqual(result["workers"], 128)
        self.assertEqual(result["ablation_variants"], 4)


if __name__ == "__main__":
    unittest.main()
