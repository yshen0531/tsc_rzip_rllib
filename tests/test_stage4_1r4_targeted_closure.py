from __future__ import annotations

import json
import math
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tsc_rzip_rllib.diagnostics import stage3_4_late_arrival_continuation_mpc as s34
from tsc_rzip_rllib.diagnostics import stage4_1r3_control_aware_robustness as r3
from tsc_rzip_rllib.diagnostics import stage4_1r4_targeted_closure as r4


class Stage41R4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (cls.root / "configs/stage4_1r4_targeted_closure_370ms.json").read_text()
        )
        cls.stage34_cfg = json.loads(
            (cls.root / "configs/stage3_4_late_arrival_continuation_mpc_350ms.json").read_text()
        )

    def test_revision_workers_and_weak_slew_horizon_are_locked(self) -> None:
        self.assertEqual(
            self.cfg["controller_revision"],
            "targeted_weak_slew_and_online_delay_slew_estimator_v4",
        )
        self.assertEqual(self.cfg["parallel"]["n_workers"], 128)
        weak = self.cfg["weak_slew_closure"]
        self.assertEqual(weak["horizon_steps"], 37)
        self.assertEqual(weak["hold_through_step"], 37)
        self.assertEqual(max(weak["allowed_arrival_steps"]), 27)
        self.assertGreaterEqual(
            weak["hold_through_step"] - max(weak["allowed_arrival_steps"]),
            weak["minimum_post_arrival_hold_steps"],
        )

    def test_corrected_category_summary_handles_zero_baseline_passes(self) -> None:
        pairs = [
            {
                "category": "gain_estimation_error",
                "baseline_pass": False,
                "feedback_pass": True,
                "preserved": False,
                "recovered": True,
                "lost": False,
            },
            {
                "category": "gain_estimation_error",
                "baseline_pass": False,
                "feedback_pass": True,
                "preserved": False,
                "recovered": True,
                "lost": False,
            },
        ]
        required = {
            "gain_estimation_error": {
                "minimum_mpc_pass_fraction": 0.75,
                "minimum_preserved_fraction": 0.75,
                "minimum_recovery_fraction_when_no_baseline_pass": 0.75,
            }
        }
        summary = r4.corrected_category_summary(pairs, required)[0]
        self.assertFalse(summary["preservation_applicable"])
        self.assertIsNone(summary["preserved_open_loop_pass_fraction"])
        self.assertEqual(summary["failure_recovery_fraction"], 1.0)
        self.assertTrue(summary["passed"])

    def test_corrected_category_summary_still_rejects_lost_passes(self) -> None:
        pairs = [
            {
                "category": "scheduled_slew",
                "baseline_pass": True,
                "feedback_pass": False,
                "preserved": False,
                "recovered": False,
                "lost": True,
            }
        ]
        required = {
            "scheduled_slew": {
                "minimum_mpc_pass_fraction": 1.0,
                "minimum_preserved_fraction": 1.0,
                "minimum_recovery_fraction_when_no_baseline_pass": 1.0,
            }
        }
        summary = r4.corrected_category_summary(pairs, required)[0]
        self.assertTrue(summary["preservation_applicable"])
        self.assertFalse(summary["passed"])

    def test_delay_slew_hypothesis_bank_recovers_synthetic_pair(self) -> None:
        scheduler = r3.PhysicalCoilScheduler(
            modes_tsc=np.eye(14, 3),
            nominal_max_delta_a=3.0,
            command_max_delta_a=3.0,
            min_current=-1e6 * np.ones(14),
            max_current=1e6 * np.ones(14),
            lower_mode=np.array([-2.6, -2.6, -0.9]),
            upper_mode=np.array([2.6, 2.6, 0.9]),
        )
        bank = r3.DelaySlewHypothesisBank(
            scheduler=scheduler,
            delay_candidates=(0, 1, 2),
            slew_candidates=(0.9, 1.0, 1.1),
            minimum_observations=2,
            switch_hysteresis_fraction=0.0,
        )
        nominal = np.asarray(
            [[0.15 + 0.04 * k, -0.12 + 0.03 * k, 0.02 * (-1) ** k] for k in range(10)],
            dtype=float,
        )
        actual_delay = 2
        actual_slew = 1.1
        issued: list[np.ndarray] = []
        currents = np.zeros(14)
        for step in range(10):
            issued.append(nominal[step].copy())
            command = nominal[step] if step < actual_delay else issued[step - actual_delay]
            observed = scheduler.predicted_delta_a(
                command, currents, np.ones(3), actual_slew
            )
            bank.update(
                step=step,
                observed_delta_a=observed,
                currents_before_a=currents,
                issued_commands=issued,
                nominal_commands=nominal,
            )
            currents += observed
        self.assertEqual(bank.selected_delay_steps, actual_delay)
        self.assertAlmostEqual(bank.selected_slew_scale, actual_slew)


    def test_delay_slew_hypothesis_bank_recovers_all_grid_pairs(self) -> None:
        scheduler = r3.PhysicalCoilScheduler(
            modes_tsc=np.eye(14, 3),
            nominal_max_delta_a=3.0,
            command_max_delta_a=3.0,
            min_current=-1e6 * np.ones(14),
            max_current=1e6 * np.ones(14),
            lower_mode=np.array([-2.6, -2.6, -0.9]),
            upper_mode=np.array([2.6, 2.6, 0.9]),
        )
        nominal = np.asarray(
            [
                [
                    0.12 + 0.035 * k,
                    -0.11 + 0.027 * k + 0.01 * (-1) ** k,
                    0.018 * (-1) ** k,
                ]
                for k in range(14)
            ],
            dtype=float,
        )
        for actual_delay in (0, 1, 2):
            for actual_slew in (0.9, 1.0, 1.1):
                bank = r3.DelaySlewHypothesisBank(
                    scheduler=scheduler,
                    delay_candidates=(0, 1, 2),
                    slew_candidates=(0.9, 1.0, 1.1),
                    minimum_observations=3,
                    switch_hysteresis_fraction=0.0,
                )
                issued: list[np.ndarray] = []
                currents = np.zeros(14)
                for step in range(len(nominal)):
                    issued.append(nominal[step].copy())
                    command = (
                        nominal[step]
                        if step < actual_delay
                        else issued[step - actual_delay]
                    )
                    observed = scheduler.predicted_delta_a(
                        command, currents, np.ones(3), actual_slew
                    )
                    bank.update(
                        step=step,
                        observed_delta_a=observed,
                        currents_before_a=currents,
                        issued_commands=issued,
                        nominal_commands=nominal,
                    )
                    currents += observed
                self.assertEqual(bank.selected_delay_steps, actual_delay)
                self.assertAlmostEqual(bank.selected_slew_scale, actual_slew)

    def test_adaptive_controller_does_not_read_private_actual_slew_for_aw(self) -> None:
        ctx = SimpleNamespace(
            cfg=self.cfg,
            r3_ctx=SimpleNamespace(source_scale=0.5),
            variants={},
        )
        with mock.patch.object(
            r4, "materialize_variant", return_value=("variant", {})
        ):
            specs = r4.build_estimator_specs(ctx)
        adaptive = [
            spec for spec in specs if spec["controller_variant"] == "adaptive"
        ]
        oracle = [spec for spec in specs if spec["controller_variant"] == "oracle"]
        naive = [spec for spec in specs if spec["controller_variant"] == "naive"]
        self.assertTrue(adaptive and oracle and naive)
        self.assertTrue(all(spec["anti_windup_enabled"] for spec in adaptive))
        self.assertTrue(all(spec["anti_windup_enabled"] for spec in oracle))
        self.assertTrue(all(not spec["anti_windup_enabled"] for spec in naive))
        self.assertTrue(
            all(
                spec["conditional_anti_windup_use_actual_actuator_state"] is False
                for spec in adaptive + oracle + naive
            )
        )
        self.assertTrue(
            all(
                spec["known_control_effect_from_measured_current_increment"] is True
                for spec in adaptive + oracle + naive
            )
        )

    def test_delay_slew_bank_pending_queue_is_causal(self) -> None:
        scheduler = r3.PhysicalCoilScheduler(
            modes_tsc=np.eye(14, 3),
            nominal_max_delta_a=3.0,
            command_max_delta_a=3.0,
            min_current=-1e6 * np.ones(14),
            max_current=1e6 * np.ones(14),
            lower_mode=np.array([-2.6, -2.6, -0.9]),
            upper_mode=np.array([2.6, 2.6, 0.9]),
        )
        bank = r3.DelaySlewHypothesisBank(
            scheduler=scheduler,
            delay_candidates=(0, 1, 2),
            slew_candidates=(1.0,),
            initial_delay_steps=2,
        )
        nominal = np.arange(18, dtype=float).reshape(6, 3)
        issued = [
            {"desired_physical": np.array([100.0, 101.0, 102.0])},
            {"desired_physical": np.array([200.0, 201.0, 202.0])},
            {"desired_physical": np.array([300.0, 301.0, 302.0])},
        ]
        pending = bank.pending_desired_physical(
            current_step=3,
            issued_items=issued,
            nominal_physical=nominal,
        )
        np.testing.assert_allclose(pending[0], issued[1]["desired_physical"])
        np.testing.assert_allclose(pending[1], issued[2]["desired_physical"])

    def test_stage34_metrics_accept_370ms_horizon(self) -> None:
        cfg = json.loads(json.dumps(self.stage34_cfg))
        cfg["gate"]["allowed_arrival_steps"] = list(range(12, 28))
        cfg["gate"]["hold_through_step"] = 37
        cfg["gate"]["minimum_post_arrival_hold_steps"] = 10
        ctx = SimpleNamespace(
            cfg=cfg,
            env_cfg={
                "dt_ms": 10,
                "min_current_a_display_order": [-1e6] * 14,
                "max_current_a_display_order": [1e6] * 14,
            },
        )
        target = np.array([cfg["target"]["R"], cfg["target"]["Z"], cfg["target"]["Ip"]])
        trajectory = []
        for step in range(38):
            trajectory.append(
                {
                    "R": float(target[0]),
                    "Z": float(target[1]),
                    "Ip": float(target[2]),
                    "currents_a_display": [0.0] * 14,
                }
            )
        result = {"success": True, "trajectory": trajectory, "wall_time_s": 1.0}
        task = {
            "task_id": "nominal",
            "R_offset_m": 0.0,
            "Z_offset_m": 0.0,
            "Ip_offset_A": 0.0,
        }
        metrics = s34.target_metrics(ctx, task, result, None)
        self.assertTrue(metrics["stage3_4_target_tracking_pass"])
        self.assertEqual(metrics["stage3_4_horizon_steps"], 37)
        self.assertEqual(
            metrics["gate_label"],
            "PASS_PRECISE_HOLD_30MM_BY_270MS_THROUGH_370MS",
        )

    def test_estimator_grid_and_rollout_count(self) -> None:
        cfg = self.cfg["adaptive_estimator"]
        expected = (
            len(cfg["actual_delay_steps"])
            * len(cfg["actual_slew_scales"])
            * len(cfg["targets"])
            * len(cfg["controller_variants"])
        )
        self.assertEqual(expected, 54)

    def test_self_test_passes(self) -> None:
        payload = r4.self_test()
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["selected_delay_steps"], 1)
        self.assertAlmostEqual(payload["selected_slew_scale"], 0.9)


if __name__ == "__main__":
    unittest.main()
