from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r3_control_aware_robustness as r3
from tsc_rzip_rllib.diagnostics import stage4_1r5_adaptive_handover_closure as r5


class Stage41R5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (cls.root / "configs/stage4_1r5_adaptive_handover_closure_350ms.json").read_text()
        )

    def _ctx(self) -> SimpleNamespace:
        return SimpleNamespace(
            cfg=self.cfg,
            r4_ctx=SimpleNamespace(
                r3_ctx=SimpleNamespace(source_scale=0.5),
                variants={},
            ),
        )

    def test_revision_workers_and_finite_bank_are_locked(self) -> None:
        self.assertEqual(
            self.cfg["controller_revision"],
            "confidence_gated_bumpless_delay_slew_handover_v5",
        )
        self.assertEqual(self.cfg["parallel"]["n_workers"], 128)
        self.assertEqual(self.cfg["estimator_only_confirmation"]["minimum_observations"], 2)
        self.assertEqual(self.cfg["static_handover"]["estimator"]["minimum_observations"], 2)
        self.assertEqual(self.cfg["estimator_only_confirmation"]["delay_candidates"], [0, 1, 2])
        self.assertEqual(self.cfg["estimator_only_confirmation"]["slew_candidates"], [0.9, 1.0, 1.1])
        self.assertFalse(self.cfg["deployment_robustness_validated"])

    def test_bumpless_ramp_starts_safe_and_ends_full(self) -> None:
        ramp = self.cfg["static_handover"]["handover"]["ramp_scale_fractions"]
        self.assertEqual(ramp[0], 0.0)
        self.assertEqual(ramp[-1], 1.0)
        self.assertTrue(all(b >= a for a, b in zip(ramp, ramp[1:])))
        self.assertTrue(self.cfg["static_handover"]["handover"]["reset_previous_correction_on_switch"])
        self.assertEqual(self.cfg["static_handover"]["handover"]["integral_decay_on_switch"], 0.0)

    def test_estimator_only_specs_cover_eighteen_independent_cases(self) -> None:
        ctx = self._ctx()
        with mock.patch.object(r5, "materialize_variant", return_value=("variant", {})):
            specs = r5.build_estimator_only_specs(ctx)
        self.assertEqual(len(specs), 18)
        keys = {
            (spec["target_id"], spec["action_delay_steps"], spec["slew_scale"])
            for spec in specs
        }
        self.assertEqual(len(keys), 18)
        self.assertTrue(all(spec["controller_scale"] == 0.0 for spec in specs))
        self.assertTrue(all(spec["adaptive_handover"]["enabled"] is False for spec in specs))

    def test_estimator_confirmation_specs_cover_all_nine_pairs_twice(self) -> None:
        ctx = self._ctx()
        with mock.patch.object(r5, "materialize_variant", return_value=("variant", {})):
            specs = r5.build_estimator_only_specs(ctx, repeats=True)
        self.assertEqual(len(specs), 18)
        groups = {spec["confirmation_group"] for spec in specs}
        self.assertEqual(len(groups), 9)
        self.assertTrue(all(sum(1 for spec in specs if spec["confirmation_group"] == group) == 2 for group in groups))

    def test_static_handover_specs_cover_five_variants_and_ninety_rollouts(self) -> None:
        ctx = self._ctx()
        with mock.patch.object(r5, "materialize_variant", return_value=("variant", {})):
            specs = r5.build_static_handover_specs(ctx)
        self.assertEqual(len(specs), 90)
        variants = {spec["controller_variant"] for spec in specs}
        self.assertEqual(variants, set(self.cfg["static_handover"]["controller_variants"]))

    def test_unknown_bumpless_and_persistent_specs_have_correct_startup_semantics(self) -> None:
        ctx = self._ctx()
        target = self.cfg["static_handover"]["targets"][0]
        unknown = r5._static_variant_spec(
            ctx,
            variant="r5_bumpless_unknown",
            target=target,
            actual_delay=2,
            actual_slew=1.1,
            environment_variant="variant",
        )
        persistent = r5._static_variant_spec(
            ctx,
            variant="r5_persistent_exact",
            target=target,
            actual_delay=2,
            actual_slew=1.1,
            environment_variant="variant",
        )
        self.assertEqual(unknown["controller_action_delay_steps"], 0)
        self.assertEqual(unknown["controller_slew_scale_estimate"], 1.0)
        self.assertFalse(unknown["adaptive_handover"]["initial_model_trusted"])
        self.assertTrue(unknown["adaptive_handover"]["safe_start_until_lock"])
        self.assertEqual(persistent["controller_action_delay_steps"], 2)
        self.assertEqual(persistent["controller_slew_scale_estimate"], 1.1)
        self.assertTrue(persistent["adaptive_handover"]["initial_model_trusted"])
        self.assertFalse(persistent["adaptive_handover"]["safe_start_until_lock"])

    def test_delay_slew_bank_locks_by_second_observation(self) -> None:
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
            [[0.15 + 0.04 * k, -0.10 + 0.03 * k, 0.02 * (-1) ** k] for k in range(10)],
            dtype=float,
        )
        actual_delay, actual_slew = 2, 1.1
        issued: list[np.ndarray] = []
        currents = np.zeros(14)
        for step in range(len(nominal)):
            issued.append(nominal[step].copy())
            command = nominal[step] if step < actual_delay else issued[step - actual_delay]
            observed = scheduler.predicted_delta_a(command, currents, np.ones(3), actual_slew)
            bank.update(
                step=step,
                observed_delta_a=observed,
                currents_before_a=currents,
                issued_commands=issued,
                nominal_commands=nominal,
            )
            currents += observed
        summary = bank.summary()
        self.assertEqual(summary["selected_delay_steps"], 2)
        self.assertAlmostEqual(summary["selected_slew_scale"], 1.1)
        self.assertIsNotNone(summary["first_lock_step"])
        self.assertLessEqual(summary["first_lock_step"], 2)
        self.assertGreater(summary["confidence_ratio"], 1.0)

    def test_piecewise_schedule_is_causal(self) -> None:
        schedule = [
            {"start_step": 0, "delay_steps": 0},
            {"start_step": 8, "delay_steps": 2},
        ]
        self.assertEqual(r3._piecewise_schedule_value(schedule, step=7, default=1, value_key="delay_steps"), 0)
        self.assertEqual(r3._piecewise_schedule_value(schedule, step=8, default=1, value_key="delay_steps"), 2)
        self.assertEqual(r3._piecewise_schedule_value(schedule, step=20, default=1, value_key="delay_steps"), 2)

    def test_change_point_specs_are_finite_and_complete(self) -> None:
        ctx = self._ctx()
        with mock.patch.object(r5, "materialize_variant", return_value=("variant", {})):
            specs = r5.build_change_point_specs(ctx)
        expected = (
            len(self.cfg["change_point_diagnostics"]["scenarios"])
            * len(self.cfg["change_point_diagnostics"]["targets"])
            * len(self.cfg["change_point_diagnostics"]["controller_variants"])
        )
        self.assertEqual(len(specs), expected)
        self.assertEqual(expected, 36)
        adaptive = [s for s in specs if s["controller_variant"] == "adaptive_bumpless"]
        self.assertTrue(all(s["adaptive_handover"]["enabled"] for s in adaptive))
        self.assertTrue(all(s["actual_action_delay_schedule"] for s in adaptive))
        self.assertTrue(all(s["actual_slew_scale_schedule"] for s in adaptive))

    def test_estimator_only_summary_passes_complete_correct_rows(self) -> None:
        ctx = self._ctx()
        rows = []
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                rows.append({
                    "success": True,
                    "actual_action_delay_steps": delay,
                    "actual_slew_scale": slew,
                    "adaptive_estimated_delay_steps": delay,
                    "adaptive_estimated_slew_scale": slew,
                    "adaptive_estimator_first_lock_step": 1,
                    "adaptive_estimator_confidence_ratio": 5.0,
                })
        summary = r5.summarize_estimator_only(ctx, rows)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["identification_fraction"], 1.0)

    def test_static_summary_rewards_bumpless_handover_and_persistent_initialization(self) -> None:
        ctx = self._ctx()
        rows = []
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                for target in ("nominal", "RZ_p10_m10"):
                    oracle_pass = not (slew == 0.9 and target == "RZ_p10_m10")
                    for variant in self.cfg["static_handover"]["controller_variants"]:
                        tracking = oracle_pass
                        if variant == "r4_abrupt_unknown" and delay == 2 and oracle_pass:
                            tracking = False
                        row = {
                            "success": True,
                            "target_id": target,
                            "actual_action_delay_steps": delay,
                            "actual_slew_scale": slew,
                            "controller_variant": variant,
                            "stage3_4_target_tracking_pass": tracking,
                            "stage3_4_tracking_minimum_signed_margin": 0.2 if tracking else -0.2,
                            "adaptive_estimated_delay_steps": delay,
                            "adaptive_estimated_slew_scale": slew,
                            "handover_events": [],
                        }
                        rows.append(row)
        summary = r5.summarize_static_handover(ctx, rows)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["adaptive_identification_fraction"], 1.0)
        self.assertGreater(summary["unknown_bumpless_recoveries"], 0)

    def test_change_point_summary_detects_correct_low_latency_recovery(self) -> None:
        ctx = self._ctx()
        rows = []
        for scenario in self.cfg["change_point_diagnostics"]["scenarios"]:
            for target in ("nominal", "RZ_p10_m10"):
                prefix = scenario["scenario_id"]
                for variant in ("oracle_schedule", "fixed_initial", "adaptive_bumpless"):
                    tracking = variant != "fixed_initial"
                    transitions = []
                    if variant == "adaptive_bumpless":
                        transitions = [{
                            "step": scenario["change_step"] + 2,
                            "new_delay_steps": scenario["final_delay"],
                            "new_slew_scale": scenario["final_slew"],
                        }]
                    rows.append({
                        "success": True,
                        "scenario": f"{prefix}__{target}__{variant}",
                        "target_id": target,
                        "controller_variant": variant,
                        "stage3_4_target_tracking_pass": tracking,
                        "stage3_4_tracking_minimum_signed_margin": 0.2 if tracking else -0.2,
                        "adaptive_estimated_delay_steps": scenario["final_delay"],
                        "adaptive_estimated_slew_scale": scenario["final_slew"],
                        "adaptive_estimator_transitions": transitions,
                    })
        summary = r5.summarize_change_point(ctx, rows)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["final_identification_fraction"], 1.0)
        self.assertLessEqual(summary["maximum_detection_latency_steps"], 2)

    def test_source_validation_allows_r4_adaptive_control_failure(self) -> None:
        manifest = {
            "stage": "Stage4.1R4",
            "controller_revision": "targeted_weak_slew_and_online_delay_slew_estimator_v4",
        }
        state = {
            "finished": True,
            "reclassification_summary": {
                "gain_estimation_error_reclassified_without_new_tsc": True,
                "all_non_slew_required_categories_passed": True,
            },
            "weak_slew_summary": {"passed": True},
            "estimator_summary": {
                "estimator_accuracy_passed": True,
                "adaptive_control_passed": False,
            },
        }
        r5.validate_source(self.cfg, manifest, state)


    def test_execute_stops_after_estimator_only_failure(self) -> None:
        fake_ctx = SimpleNamespace(
            paths=SimpleNamespace(
                state=Path("/tmp/nonexistent-stage41r5-state.json"),
            )
        )
        with (
            mock.patch.object(r5, "load_stage41r5_config", return_value=fake_ctx),
            mock.patch.object(r5, "initialize_run"),
            mock.patch.object(r5, "run_source_audit"),
            mock.patch.object(r5, "run_estimator_only", return_value={"passed": False}),
            mock.patch.object(r5, "run_static_handover") as static_run,
            mock.patch.object(r5, "_update_state"),
            mock.patch.object(r5, "analyze", return_value={"verdict": "incomplete"}),
        ):
            result = r5.execute(
                config_path="dummy.json",
                source_stage41r4_run="dummy",
                run_dir="dummy-run",
                command="all",
                backend="serial",
                resume=False,
            )
        self.assertEqual(result["verdict"], "incomplete")
        static_run.assert_not_called()

    def test_execute_stops_after_static_handover_failure(self) -> None:
        fake_ctx = SimpleNamespace(
            paths=SimpleNamespace(
                state=Path("/tmp/nonexistent-stage41r5-state-2.json"),
            )
        )
        with (
            mock.patch.object(r5, "load_stage41r5_config", return_value=fake_ctx),
            mock.patch.object(r5, "initialize_run"),
            mock.patch.object(r5, "run_source_audit"),
            mock.patch.object(r5, "run_estimator_only", return_value={"passed": True}),
            mock.patch.object(r5, "run_static_handover", return_value={"passed": False}),
            mock.patch.object(r5, "run_change_point") as change_run,
            mock.patch.object(r5, "_update_state"),
            mock.patch.object(r5, "analyze", return_value={"verdict": "incomplete"}),
        ):
            result = r5.execute(
                config_path="dummy.json",
                source_stage41r4_run="dummy",
                run_dir="dummy-run",
                command="all",
                backend="serial",
                resume=False,
            )
        self.assertEqual(result["verdict"], "incomplete")
        change_run.assert_not_called()

    def test_self_test_passes(self) -> None:
        result = r5.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_delay_steps"], 2)
        self.assertAlmostEqual(result["selected_slew_scale"], 1.1)

    def test_strict_json_writer_rejects_nonfinite_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"
            with self.assertRaises(ValueError):
                r5.atomic_write_json(path, {"bad": math.nan})
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
