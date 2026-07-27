from __future__ import annotations

import inspect
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r3_control_aware_robustness as r3
from tsc_rzip_rllib.diagnostics import stage4_1r7_precontrol_calibration_queue_startup as r7


class Stage41R7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (cls.root / "configs/stage4_1r7_precontrol_calibration_queue_startup_370ms.json").read_text()
        )

    def _ctx(self, root: Path) -> SimpleNamespace:
        r3ctx = SimpleNamespace(source_scale=0.5, source_library={}, source_bundle={})
        r4ctx = SimpleNamespace(r3_ctx=r3ctx, variants={})
        r5ctx = SimpleNamespace(r4_ctx=r4ctx)
        r6ctx = SimpleNamespace(
            r5_ctx=r5ctx,
            source_r5_cfg={
                "static_handover": {
                    "estimator": {
                        "delay_candidates": [0, 1, 2],
                        "slew_candidates": [0.9, 1.0, 1.1],
                        "score_decay": 0.92,
                        "minimum_observations": 3,
                        "switch_hysteresis_fraction": 0.05,
                    }
                }
            },
        )
        paths = r7.Stage41R7Paths.from_run_dir(root)
        for value in vars(paths).values():
            if isinstance(value, Path):
                value.mkdir(parents=True, exist_ok=True) if value.suffix == "" else None
        return SimpleNamespace(cfg=self.cfg, paths=paths, r6_ctx=r6ctx)

    def test_revision_workers_and_calibration_architecture_are_locked(self) -> None:
        self.assertEqual(
            self.cfg["controller_revision"],
            "precontrol_calibration_queue_consistent_startup_v7",
        )
        self.assertEqual(self.cfg["parallel"]["n_workers"], 128)
        self.assertTrue(
            self.cfg["precontrol_calibration"]["calibration_is_separate_reset_episode"]
        )
        self.assertTrue(
            self.cfg["queue_consistent_startup"][
                "queue_primed_from_calibrated_model_before_first_main_action"
            ]
        )
        self.assertFalse(self.cfg["deployment_robustness_validated"])

    def test_calibration_plan_is_bounded_zero_net_and_has_flush_steps(self) -> None:
        plan = np.asarray(self.cfg["precontrol_calibration"]["mode_command_plan"], dtype=float)
        self.assertEqual(plan.shape, (10, 3))
        self.assertTrue(np.all(np.abs(plan[:, 0]) <= 0.72 + 1e-12))
        self.assertTrue(np.all(np.abs(plan[:, 1]) <= 0.60 + 1e-12))
        self.assertTrue(np.all(np.abs(plan[:, 2]) <= 0.24 + 1e-12))
        self.assertEqual(
            self.cfg["precontrol_calibration"]["calibration_plan_revision"],
            "bounded_zero_net_snr_20mA_v2",
        )
        self.assertLessEqual(
            self.cfg["precontrol_calibration"]["maximum_physical_coil_delta_fraction_of_nominal_slew"],
            0.34,
        )
        self.assertTrue(np.allclose(np.sum(plan, axis=0), 0.0, atol=1e-12))
        self.assertTrue(np.allclose(plan[-2:], 0.0))

    def test_self_test_identifies_all_clean_and_noisy_pairs(self) -> None:
        result = r7.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["pairs_tested"], 18)
        self.assertEqual(result["pairs_correct"], 18)

    def test_calibration_specs_cover_nine_pairs_and_two_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ctx = self._ctx(Path(temp))
            with mock.patch.object(r7, "materialize_variant", return_value=("variant", {})):
                specs = r7.build_calibration_specs(ctx)
        self.assertEqual(len(specs), 18)
        self.assertEqual(
            {(s["action_delay_steps"], s["slew_scale"]) for s in specs},
            {(d, s) for d in (0, 1, 2) for s in (0.9, 1.0, 1.1)},
        )
        self.assertEqual({s["calibration_profile"] for s in specs}, {"clean", "noisy_20mA"})
        self.assertTrue(all(s["phase"] == "precontrol_calibration" for s in specs))

    def test_calibration_summary_requires_all_profiles_and_pairs(self) -> None:
        rows = []
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                for profile in ("clean", "noisy_20mA"):
                    rows.append({
                        "success": True,
                        "final_identification_correct": True,
                        "incorrect_confident_lock_count": 0,
                        "first_confident_lock_step": 3 if delay == 2 else 2,
                        "confidence_ratio": 20.0,
                        "actual_delay_steps": delay,
                        "actual_slew_scale": slew,
                        "calibration_profile": profile,
                    })
        ctx = SimpleNamespace(cfg=self.cfg)
        summary = r7.summarize_calibration(ctx, rows)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["distinct_pairs_calibrated"], 9)
        rows[-1]["final_identification_correct"] = False
        self.assertFalse(r7.summarize_calibration(ctx, rows)["passed"])

    def _write_calibration_rows(self, root: Path) -> None:
        rows = []
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                for profile in ("clean", "noisy_20mA"):
                    rows.append({
                        "experiment_id": f"cal_{delay}_{slew}_{profile}",
                        "actual_delay_steps": delay,
                        "actual_slew_scale": slew,
                        "calibration_profile": profile,
                        "estimated_delay_steps": delay,
                        "estimated_slew_scale": slew,
                    })
        (root / "stage4_1r7_precontrol_calibration").mkdir(parents=True, exist_ok=True)
        (root / "stage4_1r7_precontrol_calibration/results.json").write_text(
            json.dumps(rows), encoding="utf-8"
        )

    def test_startup_specs_cover_six_variants_and_108_rollouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ctx = self._ctx(root)
            self._write_calibration_rows(root)
            with mock.patch.object(r7, "materialize_variant", return_value=("variant", {})):
                specs = r7.build_startup_specs(ctx)
        self.assertEqual(len(specs), 108)
        self.assertEqual(
            {s["controller_variant"] for s in specs},
            set(self.cfg["queue_consistent_startup"]["controller_variants"]),
        )

    def test_precalibrated_specs_disable_online_handover_and_prime_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ctx = self._ctx(root)
            self._write_calibration_rows(root)
            with mock.patch.object(r7, "materialize_variant", return_value=("variant", {})):
                specs = r7.build_startup_specs(ctx)
        primary = next(
            spec for spec in specs
            if spec["controller_variant"] == "r7_precalibrated_clean_monitor"
            and spec["action_delay_steps"] == 2
            and math.isclose(spec["slew_scale"], 1.1)
        )
        self.assertEqual(primary["controller_action_delay_steps"], 2)
        self.assertAlmostEqual(primary["controller_slew_scale_estimate"], 1.1)
        self.assertTrue(primary["prime_action_queue_with_nominal"])
        self.assertFalse(primary["adaptive_handover"]["enabled"])
        self.assertTrue(primary["adaptive_delay_slew_estimator"]["enabled"])

    def test_weak_slew_uses_370ms_extended_closure_and_validated_no_aw(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ctx = self._ctx(root)
            self._write_calibration_rows(root)
            with mock.patch.object(r7, "materialize_variant", return_value=("variant", {})):
                specs = r7.build_startup_specs(ctx)
        spec = next(
            item for item in specs
            if item["controller_variant"] == "r7_precalibrated_clean_no_monitor"
            and math.isclose(item["slew_scale"], 0.9)
        )
        self.assertEqual(spec["horizon_steps"], 37)
        self.assertTrue(spec["extended_horizon"])
        self.assertEqual(spec["tail_hold_steps"], 2)
        self.assertFalse(spec["anti_windup_enabled"])
        self.assertEqual(spec["anti_windup_mode"], "off")

    def test_startup_summary_requires_preservation_and_trace_equivalence(self) -> None:
        rows = []
        variants = self.cfg["queue_consistent_startup"]["controller_variants"]
        for target in ("nominal", "RZ_p10_m10"):
            for delay in (0, 1, 2):
                for slew in (0.9, 1.0, 1.1):
                    signature = f"sig_{target}_{delay}_{slew}"
                    for variant in variants:
                        row = {
                            "target_id": target,
                            "actual_action_delay_steps": delay,
                            "actual_slew_scale": slew,
                            "controller_variant": variant,
                            "stage3_4_target_tracking_pass": True,
                            "stage3_4_tracking_minimum_signed_margin": 0.2,
                            "trajectory_signature": signature if variant.startswith("r7_precalibrated") or variant == "oracle" else f"{variant}_{signature}",
                            "issued_command_signature": signature if variant.startswith("r7_precalibrated") or variant == "oracle" else f"{variant}_{signature}",
                            "monitor_estimated_delay_steps": delay,
                            "monitor_estimated_slew_scale": slew,
                            "monitor_transition_count": 0,
                        }
                        rows.append(row)
        ctx = SimpleNamespace(cfg=self.cfg)
        summary = r7.summarize_startup(ctx, rows)
        self.assertTrue(summary["passed"])
        bad = [dict(row) for row in rows]
        for row in bad:
            if row["controller_variant"] == "r7_precalibrated_noisy_monitor":
                row["trajectory_signature"] = "different"
                break
        self.assertFalse(r7.summarize_startup(ctx, bad)["passed"])

    def test_confirmation_specs_cover_eighteen_groups_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ctx = self._ctx(root)
            r7.atomic_write_json(
                ctx.paths.state,
                {"startup_summary": {"precalibrated_startup_passed": True}},
            )
            with mock.patch.object(r7, "materialize_variant", return_value=("variant", {})):
                specs = r7.build_confirmation_specs(ctx)
        self.assertEqual(len(specs), 36)
        self.assertEqual(len({s["confirmation_group"] for s in specs}), 18)
        self.assertTrue(all(s["phase"] == "paired_confirmation" for s in specs))
        self.assertTrue(all("paired_calibration_spec" in s for s in specs))
        self.assertTrue(all("paired_main_spec_template" in s for s in specs))

    def test_confirmation_summary_requires_calibration_and_tracking(self) -> None:
        rows = []
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                for target in ("nominal", "RZ_p10_m10"):
                    group = f"d{delay}_s{slew}_{target}"
                    for repeat in range(2):
                        rows.append({
                            "confirmation_group": group,
                            "success": True,
                            "paired_calibration_success": True,
                            "paired_calibration_estimated_delay_steps": delay,
                            "paired_calibration_estimated_slew_scale": slew,
                            "actual_action_delay_steps": delay,
                            "actual_slew_scale": slew,
                            "stage3_4_target_tracking_pass": True,
                            "stage3_4_tracking_minimum_signed_margin": 0.1,
                        })
        ctx = SimpleNamespace(cfg=self.cfg)
        summary = r7.summarize_confirmation(ctx, rows)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["n_tsc_episodes"], 72)
        rows[-1]["paired_calibration_estimated_delay_steps"] = -1
        self.assertFalse(r7.summarize_confirmation(ctx, rows)["passed"])

    def test_source_validation_accepts_expected_r6_partial_startup_result(self) -> None:
        manifest = {
            "stage": "Stage4.1R6",
            "controller_revision": "confidence_gated_persistent_prior_physical_handover_v6",
        }
        state = {
            "finished": True,
            "source_audit_summary": {"passed": True},
            "estimator_confirmation_summary": {"passed": True},
            "startup_summary": {
                "persistent_exact_preservation_fraction": 1.0,
                "persistent_exact_trace_equivalence_fraction": 1.0,
                "precalibrated_startup_passed": False,
            },
        }
        r7.validate_source(manifest, state)

    def test_queue_history_records_actual_issued_physical_target(self) -> None:
        source = inspect.getsource(r3.LocalStage41Worker.evaluate)
        self.assertIn('"desired_physical": np.asarray(', source)
        self.assertIn("issued_desired_physical", source)
        self.assertIn("issued_desired_physical_mode_coefficients", source)

    def test_analysis_preserves_scientific_early_stop_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ctx = self._ctx(root)
            ctx.source_stage41r6_run = root / "source"
            r7.atomic_write_json(
                ctx.paths.state,
                {
                    "stop_reason": "precontrol_calibration_failed",
                    "source_audit_summary": {"passed": True},
                    "calibration_summary": {"passed": False},
                },
            )
            summary = r7.analyze(ctx)
            state = r7.read_json(ctx.paths.state)
        self.assertIn("INCOMPLETE", summary["verdict"])
        self.assertEqual(state["stop_reason"], "precontrol_calibration_failed")


if __name__ == "__main__":
    unittest.main()
