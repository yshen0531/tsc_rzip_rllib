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
from tsc_rzip_rllib.diagnostics import stage4_1r6_startup_architecture_closure as r6


class Stage41R6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (cls.root / "configs/stage4_1r6_startup_architecture_closure_350ms.json").read_text()
        )

    def _ctx(self) -> SimpleNamespace:
        base34 = SimpleNamespace(
            cfg={
                "trajectory": {
                    "coefficient_lower": [-2.6, -2.6, -0.9],
                    "coefficient_upper": [2.6, 2.6, 0.9],
                }
            },
            modes_tsc=np.eye(14, 3),
            max_delta_a=3.0,
            min_current_tsc=-1e6 * np.ones(14),
            max_current_tsc=1e6 * np.ones(14),
        )
        r3ctx = SimpleNamespace(
            source_scale=0.5,
            base34=base34,
            cfg={
                "controller_upgrade": {
                    "gain_slew_scheduling": {"physical_inverse_regularization": 1e-4}
                }
            },
            source_library={},
            source_bundle={},
        )
        return SimpleNamespace(
            cfg=self.cfg,
            source_r5_cfg={
                "static_handover": {
                    "estimator": {
                        "delay_candidates": [0, 1, 2],
                        "slew_candidates": [0.9, 1.0, 1.1],
                        "score_decay": 0.92,
                        "minimum_observations": 2,
                        "switch_hysteresis_fraction": 0.03,
                    }
                }
            },
            r5_ctx=SimpleNamespace(
                r4_ctx=SimpleNamespace(r3_ctx=r3ctx, variants={})
            ),
        )

    def _scheduler(self) -> r3.PhysicalCoilScheduler:
        return r3.PhysicalCoilScheduler(
            modes_tsc=np.eye(14, 3),
            nominal_max_delta_a=3.0,
            command_max_delta_a=3.0,
            min_current=-1e6 * np.ones(14),
            max_current=1e6 * np.ones(14),
            lower_mode=np.array([-2.6, -2.6, -0.9]),
            upper_mode=np.array([2.6, 2.6, 0.9]),
        )

    def test_revision_workers_and_confidence_gate_are_locked(self) -> None:
        self.assertEqual(
            self.cfg["controller_revision"],
            "confidence_gated_persistent_prior_physical_handover_v6",
        )
        self.assertEqual(self.cfg["parallel"]["n_workers"], 128)
        confidence = self.cfg["confidence_gate"]
        self.assertGreater(confidence["minimum_confidence_ratio"], 1.0)
        self.assertGreaterEqual(confidence["consecutive_best_observations"], 2)
        self.assertTrue(confidence["require_unique_best"])
        self.assertFalse(self.cfg["deployment_robustness_validated"])

    def test_tied_hypotheses_do_not_lock(self) -> None:
        scheduler = self._scheduler()
        bank = r3.DelaySlewHypothesisBank(
            scheduler=scheduler,
            delay_candidates=(0, 1, 2),
            slew_candidates=(1.0,),
            minimum_observations=2,
            switch_hysteresis_fraction=0.0,
            minimum_confidence_ratio=5.0,
            minimum_absolute_score_gap=1e-10,
            consecutive_best_observations=2,
            require_unique_best=True,
            tie_relative_tolerance=1e-9,
            tie_absolute_tolerance=1e-12,
        )
        nominal = np.zeros((5, 3))
        currents = np.zeros(14)
        issued: list[np.ndarray] = []
        updates = []
        for step in range(3):
            issued.append(np.zeros(3))
            updates.append(bank.update(
                step=step,
                observed_delta_a=np.zeros(14),
                currents_before_a=currents,
                issued_commands=issued,
                nominal_commands=nominal,
            ))
        self.assertFalse(any(update["locked"] for update in updates))
        self.assertIsNone(bank.summary()["first_confident_lock_step"])

    def test_confidence_gated_bank_locks_correct_model_after_information_arrives(self) -> None:
        scheduler = self._scheduler()
        bank = r3.DelaySlewHypothesisBank(
            scheduler=scheduler,
            delay_candidates=(0, 1, 2),
            slew_candidates=(0.9, 1.0, 1.1),
            minimum_observations=2,
            switch_hysteresis_fraction=0.0,
            minimum_confidence_ratio=5.0,
            minimum_absolute_score_gap=1e-10,
            consecutive_best_observations=2,
            require_unique_best=True,
            tie_relative_tolerance=1e-9,
            tie_absolute_tolerance=1e-12,
        )
        nominal = np.asarray(
            [[0.15 + 0.04 * k, -0.10 + 0.03 * k, 0.02 * (-1) ** k] for k in range(12)],
            dtype=float,
        )
        actual_delay, actual_slew = 2, 1.1
        currents = np.zeros(14)
        issued: list[np.ndarray] = []
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
        self.assertEqual(summary["selected_delay_steps"], actual_delay)
        self.assertAlmostEqual(summary["selected_slew_scale"], actual_slew)
        self.assertIsNotNone(summary["first_confident_lock_step"])
        self.assertGreaterEqual(summary["first_confident_lock_step"], 2)
        self.assertTrue(all(event["confidence_ratio"] >= 5.0 for event in summary["lock_events"]))

    def test_physical_scheduler_solves_for_target_coil_increment(self) -> None:
        scheduler = self._scheduler()
        currents = np.zeros(14)
        target_command = np.array([0.3, -0.2, 0.1])
        target_delta = scheduler.predicted_delta_a(target_command, currents, np.ones(3), 0.9)
        solved = scheduler.solve_command_for_target_delta(
            target_delta_a=target_delta,
            currents=currents,
            gain_estimate=np.ones(3),
            slew_estimate=0.9,
            enabled=True,
            reference_command=np.zeros(3),
        )
        actual = scheduler.predicted_delta_a(solved["command"], currents, np.ones(3), 0.9)
        self.assertLess(float(np.sqrt(np.mean((actual - target_delta) ** 2))), 1e-4)

    def test_estimator_confirmation_specs_cover_nine_pairs_two_targets_twice(self) -> None:
        ctx = self._ctx()
        with mock.patch.object(r6, "materialize_variant", return_value=("variant", {})):
            specs = r6.build_estimator_confirmation_specs(ctx)
        self.assertEqual(len(specs), 36)
        pairs = {(s["action_delay_steps"], s["slew_scale"]) for s in specs}
        self.assertEqual(len(pairs), 9)
        self.assertTrue(all(s["controller_scale"] == 0.0 for s in specs))
        self.assertTrue(all(s["adaptive_handover"]["enabled"] is False for s in specs))

    def test_static_startup_specs_cover_six_variants_and_108_rollouts(self) -> None:
        ctx = self._ctx()
        with (
            mock.patch.object(r6, "materialize_variant", return_value=("variant", {})),
            mock.patch.object(r6, "common_prefix_plan", return_value=np.zeros((35, 3))),
        ):
            specs = r6.build_static_startup_specs(ctx)
        self.assertEqual(len(specs), 108)
        self.assertEqual(
            {s["controller_variant"] for s in specs},
            set(self.cfg["static_startup"]["controller_variants"]),
        )

    def test_persistent_exact_monitor_suppresses_noop_handover(self) -> None:
        ctx = self._ctx()
        target = self.cfg["static_startup"]["targets"][0]
        spec = r6._startup_spec(
            ctx,
            variant="r6_persistent_exact_monitor",
            target=target,
            actual_delay=2,
            actual_slew=1.1,
            environment_variant="variant",
        )
        self.assertEqual(spec["controller_action_delay_steps"], 2)
        self.assertEqual(spec["controller_slew_scale_estimate"], 1.1)
        self.assertTrue(spec["adaptive_handover"]["initial_model_trusted"])
        self.assertTrue(spec["adaptive_handover"]["suppress_noop_initial_lock_event"])

    def test_cold_start_uses_conservative_common_prefix_and_zero_feedback_prelock(self) -> None:
        ctx = self._ctx()
        target = self.cfg["static_startup"]["targets"][0]
        plan = np.full((35, 3), 0.123)
        with mock.patch.object(r6, "common_prefix_plan", return_value=plan):
            spec = r6._startup_spec(
                ctx,
                variant="r6_cold_common_prefix",
                target=target,
                actual_delay=2,
                actual_slew=1.1,
                environment_variant="variant",
            )
        self.assertEqual(spec["controller_action_delay_steps"], 0)
        self.assertEqual(spec["adaptive_handover"]["prelock_controller_scale_fraction"], 0.0)
        self.assertTrue(spec["adaptive_handover"]["safe_start_until_lock"])
        self.assertTrue(np.allclose(np.asarray(spec["prelock_common_prefix_physical"]), plan))

    def _synthetic_startup_rows(self, *, exact_noop_events: int = 0) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        variants = self.cfg["static_startup"]["controller_variants"]
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                for target in ("nominal", "RZ_p10_m10"):
                    oracle_pass = not (slew == 0.9 and target == "RZ_p10_m10")
                    for variant in variants:
                        tracking = oracle_pass
                        signature = f"oracle-{target}-{delay}-{slew}"
                        rows.append({
                            "success": True,
                            "target_id": target,
                            "actual_action_delay_steps": delay,
                            "actual_slew_scale": slew,
                            "controller_variant": variant,
                            "stage3_4_target_tracking_pass": tracking,
                            "stage3_4_tracking_minimum_signed_margin": 0.2 if tracking else -0.2,
                            "trajectory_signature": signature if variant in {"oracle", "r6_persistent_exact_monitor"} else f"{variant}-{signature}",
                            "issued_command_signature": signature if variant in {"oracle", "r6_persistent_exact_monitor"} else f"{variant}-{signature}",
                            "adaptive_estimator_enabled": variant.startswith("r6_"),
                            "adaptive_estimated_delay_steps": delay,
                            "adaptive_estimated_slew_scale": slew,
                            "adaptive_estimator_incorrect_lock_count": 0,
                            "handover_noop_event_count": exact_noop_events if variant == "r6_persistent_exact_monitor" else 0,
                            "handover_model_switch_count": 0,
                            "handover_max_event_delta_jump_rms_a": 0.0,
                        })
        return rows

    def test_static_summary_passes_precalibrated_paths_and_keeps_cold_diagnostic_separate(self) -> None:
        ctx = self._ctx()
        summary = r6.summarize_static_startup(ctx, self._synthetic_startup_rows())
        self.assertTrue(summary["precalibrated_startup_passed"])
        self.assertTrue(summary["cold_common_prefix_diagnostic_passed"])
        self.assertEqual(summary["persistent_exact_trace_equivalence_fraction"], 1.0)

    def test_static_summary_rejects_destructive_noop_handover(self) -> None:
        ctx = self._ctx()
        summary = r6.summarize_static_startup(ctx, self._synthetic_startup_rows(exact_noop_events=1))
        self.assertFalse(summary["precalibrated_startup_passed"])

    def test_source_validation_allows_r5_unknown_handover_failure(self) -> None:
        manifest = {
            "stage": "Stage4.1R5",
            "controller_revision": "confidence_gated_bumpless_delay_slew_handover_v5",
        }
        state = {
            "finished": True,
            "source_audit_summary": {"passed": True},
            "estimator_only_summary": {"passed": True},
            "static_handover_summary": {
                "persistent_exact_preservation_fraction": 1.0,
                "passed": False,
            },
        }
        r6.validate_source(self.cfg, manifest, state)

    def test_execute_stops_after_estimator_confirmation_failure(self) -> None:
        fake_ctx = SimpleNamespace(paths=SimpleNamespace(state=Path("/tmp/nonexistent-stage41r6-state.json")))
        with (
            mock.patch.object(r6, "load_stage41r6_config", return_value=fake_ctx),
            mock.patch.object(r6, "initialize_run"),
            mock.patch.object(r6, "run_source_audit", return_value={"passed": True}),
            mock.patch.object(r6, "run_estimator_confirmation", return_value={"passed": False}),
            mock.patch.object(r6, "run_static_startup") as startup,
            mock.patch.object(r6, "_update_state"),
            mock.patch.object(r6, "analyze", return_value={"verdict": "incomplete"}),
        ):
            result = r6.execute(
                config_path="dummy", source_stage41r5_run="dummy", run_dir="dummy",
                command="all", backend="serial", resume=False,
            )
        self.assertEqual(result["verdict"], "incomplete")
        startup.assert_not_called()

    def test_analysis_never_claims_deployment_robustness(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = SimpleNamespace(
                state=root / "state.json",
                analysis=root / "analysis",
            )
            paths.analysis.mkdir()
            r6.atomic_write_json(paths.state, {
                "source_audit_summary": {"passed": True},
                "estimator_confirmation_summary": {"passed": True},
                "startup_summary": {
                    "precalibrated_startup_passed": True,
                    "cold_common_prefix_diagnostic_passed": False,
                },
                "restart_audit_summary": {"true_restart_validation_available": False},
                "confirmation_summary": {"passed": True},
            })
            ctx = SimpleNamespace(
                paths=paths,
                source_stage41r5_run=Path("/tmp/source"),
                cfg={"final_task": self.cfg["final_task"]},
            )
            with mock.patch.object(r6, "_update_state"):
                summary = r6.analyze(ctx)
            self.assertTrue(summary["finite_precalibrated_startup_envelope_validated"])
            self.assertFalse(summary["cold_start_deployment_validated"])
            self.assertFalse(summary["deployment_robustness_validated"])

    def test_strict_json_writer_rejects_nonfinite_values(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                r6.atomic_write_json(Path(td) / "bad.json", {"x": math.nan})

    def test_self_test_passes(self) -> None:
        self.assertTrue(r6.self_test()["passed"])


if __name__ == "__main__":
    unittest.main()
