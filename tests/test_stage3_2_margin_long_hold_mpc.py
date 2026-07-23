from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tsc_rzip_rllib.diagnostics import stage3_2_margin_long_hold_mpc as s32


class Stage32MarginLongHoldTests(unittest.TestCase):
    def setUp(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "configs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms.json"
        self.cfg = json.loads(config_path.read_text(encoding="utf-8"))

    def make_ctx(self, root: Path) -> s32.Stage32Context:
        return s32._synthetic_context(root)

    def test_config_validation(self) -> None:
        s32.validate_stage32_config(self.cfg)
        broken = copy.deepcopy(self.cfg)
        broken["trajectory"]["hold_variable_steps"] = list(range(16, 25))
        with self.assertRaises(ValueError):
            s32.validate_stage32_config(broken)

    def test_config_rejects_hard_gate_drift(self) -> None:
        for key, value in (
            ("precise_tolerance_m", 0.031),
            ("terminal_velocity_max_m_per_s", 0.11),
            ("ip_tolerance_a", 11000.0),
        ):
            broken = copy.deepcopy(self.cfg)
            broken["gate"][key] = value
            with self.assertRaises(ValueError, msg=key):
                s32.validate_stage32_config(broken)

    def test_config_rejects_feedback_design_drift(self) -> None:
        broken = copy.deepcopy(self.cfg)
        broken["mpc"]["controller_scales"] = [0.0, 1.0]
        with self.assertRaises(ValueError):
            s32.validate_stage32_config(broken)
        broken = copy.deepcopy(self.cfg)
        broken["full_controller_identification"]["variables"] = 72
        with self.assertRaises(ValueError):
            s32.validate_stage32_config(broken)

    def test_decoder_shape_and_current_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            full = np.linspace(-0.5, 0.5, 75)
            decoded = s32.decode_full_sequence(ctx, full)
            self.assertEqual(decoded["mode_coefficients"].shape, (25, 3))
            self.assertEqual(decoded["action_norm_tsc"].shape, (25, 14))
            self.assertEqual(decoded["currents_a_tsc"].shape, (26, 14))
            self.assertLessEqual(float(np.max(np.abs(decoded["action_norm_tsc"]))), 1.0 + 1e-12)
            self.assertTrue(np.all(decoded["currents_a_tsc"] >= ctx.min_current_tsc[None, :] - 1e-8))
            self.assertTrue(np.all(decoded["currents_a_tsc"] <= ctx.max_current_tsc[None, :] + 1e-8))

    def test_stage32_metrics_require_hold_through_250ms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            decoded = s32.decode_full_sequence(ctx, np.zeros(75))
            good = s32.stage32_metrics(ctx, s32._synthetic_result(ctx, horizon=25), decoded, horizon=25)
            drift = s32.stage32_metrics(
                ctx,
                s32._synthetic_result(ctx, horizon=25, drift_after_150=True),
                decoded,
                horizon=25,
            )
            self.assertTrue(good["strict_gate_pass"])
            self.assertFalse(drift["strict_gate_pass"])
            self.assertGreater(good["stage3_2_minimum_signed_margin"], 0.0)
            self.assertLess(drift["stage3_2_minimum_signed_margin"], 0.0)

    def test_source_150ms_metrics_remain_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            decoded = s32.decode_full_sequence(ctx, np.zeros(75))
            metrics = s32.stage32_metrics(ctx, s32._synthetic_result(ctx, horizon=15), decoded, horizon=15)
            self.assertTrue(metrics["strict_gate_pass"])
            self.assertEqual(metrics["stage3_2_horizon_steps"], 15)
            self.assertLessEqual(metrics["stage3_2_earliest_strict_arrival_step"], 15)

    def test_signed_margin_is_not_zero_clipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            decoded = s32.decode_full_sequence(ctx, np.zeros(75))
            good = s32.stage32_metrics(ctx, s32._synthetic_result(ctx, horizon=25), decoded, horizon=25)
            self.assertTrue(good["strict_gate_pass"])
            self.assertGreater(good["stage3_2_minimum_signed_margin"], 0.0)
            self.assertEqual(good["stage3_2_max_violation"], 0.0)

    def test_probe_populations_and_unique_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            source = copy.deepcopy(ctx.source_rows[0])
            source.update(s32.stage32_metrics(ctx, s32.load_result_for_row(ctx, source), None, horizon=15))
            second = copy.deepcopy(source)
            second["candidate_id"] = "second"
            vector = np.zeros(75)
            vector[24] = 0.03
            second["full_control_vector"] = vector.tolist()
            margin = s32.build_probe_manifest(
                ctx,
                phase="margin",
                round_index=0,
                centers=[source, second],
                variable_steps=ctx.margin_steps,
                delta_by_step_mode=np.asarray(ctx.cfg["margin_sqp"]["probe_delta_by_step_mode"]),
                horizon=15,
            )
            hold = s32.build_probe_manifest(
                ctx,
                phase="hold",
                round_index=0,
                centers=[source, second],
                variable_steps=ctx.hold_steps,
                delta_by_step_mode=np.asarray(ctx.cfg["hold_sqp"]["probe_delta_by_step_mode"]),
                horizon=25,
            )
            full = s32.build_probe_manifest(
                ctx,
                phase="controller",
                round_index=0,
                centers=[source],
                variable_steps=ctx.full_steps,
                delta_by_step_mode=s32.full_identification_delta_matrix(ctx.cfg),
                horizon=25,
            )
            self.assertEqual(margin["population_size"], 84)
            self.assertEqual(hold["population_size"], 120)
            self.assertEqual(full["population_size"], 150)
            self.assertEqual(len({row["candidate_id"] for row in margin["candidates"]}), 84)
            self.assertEqual(len({row["candidate_id"] for row in hold["candidates"]}), 120)
            self.assertEqual(len({row["candidate_id"] for row in full["candidates"]}), 150)

    def test_bound_secant_probes_are_nonzero(self) -> None:
        points, scheme = s32._probe_points(2.6, -2.6, 2.6, 0.1)
        self.assertEqual(scheme, "lower_bound_inward_secant")
        self.assertEqual(len(points), 2)
        self.assertTrue(all(point < 2.6 for point in points))
        self.assertNotAlmostEqual(points[0], points[1])

    def test_extension_templates_are_unique_and_twelve(self) -> None:
        templates = s32.extension_tail_templates(np.zeros((25, 3)))
        self.assertEqual(len(templates), 12)
        self.assertEqual(len({name for name, _ in templates}), 12)
        self.assertTrue(all(np.asarray(tail).shape == (10, 3) for _, tail in templates))

    def test_feature_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            feature15 = s32.trajectory_feature_vector(ctx, s32._synthetic_result(ctx, horizon=15), state_start=9, horizon=15)
            feature25 = s32.trajectory_feature_vector(ctx, s32._synthetic_result(ctx, horizon=25), state_start=1, horizon=25)
            self.assertEqual(feature15.shape, (35,))
            self.assertEqual(feature25.shape, (125,))
            self.assertEqual(set(s32.unpack_feature(feature15, 7)), {"R", "Z", "vR", "vZ", "Ip"})

    def test_predicted_endpoint_metrics_exposes_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            feature = s32.trajectory_feature_vector(ctx, s32._synthetic_result(ctx, horizon=15), state_start=9, horizon=15)
            metrics = s32.predicted_endpoint_metrics(
                ctx,
                feature,
                state_start=9,
                horizon=15,
                endpoint=14,
                tolerance=0.03,
                speed_limit=0.10,
            )
            self.assertEqual(metrics["endpoint_step"], 14)
            self.assertEqual(metrics["window_start_step"], 12)

    def test_dimensionless_gain_shape(self) -> None:
        rng = np.random.default_rng(32)
        j = rng.normal(size=(125, 75))
        weights = np.ones(125)
        radius = np.tile(np.asarray([0.1, 0.1, 0.035]), 25)
        gain = s32._regularized_gain(
            j,
            weights,
            radius,
            ridge_lambda=0.1,
            relative_cutoff=0.002,
            maximum_condition=5e5,
        )
        self.assertEqual(np.asarray(gain["gain_from_normalized_output_error"]).shape, (75, 125))
        self.assertGreater(gain["retained_rank"], 0)

    def test_feedback_scenario_count_and_rollouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            scenarios = s32.feedback_scenarios(ctx)
            self.assertEqual(len(scenarios), 33)
            bundle = {
                "causal_time_indexed_gains": [],
                "center_candidate_id": ctx.source_rows[0]["candidate_id"],
            }
            specs = s32.feedback_specs(ctx, bundle, ctx.source_rows[0])
            self.assertEqual(len(specs), 99)
            self.assertEqual(len({spec["experiment_id"] for spec in specs}), 99)

    def test_feedback_signed_margin_selection_credits_safe_improvement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            rows = []
            for scenario in ("nominal", "a", "b"):
                for scale, margin in ((0.0, 0.01), (0.5, 0.02), (1.0, 0.015)):
                    rows.append(
                        {
                            "scenario": scenario,
                            "scenario_category": "nominal" if scenario == "nominal" else "target",
                            "controller_scale": scale,
                            "success": True,
                            "strict_gate_pass": True,
                            "stage3_2_minimum_signed_margin": margin,
                        }
                    )
            summaries, selected = s32.feedback_scale_summaries(ctx, rows)
            self.assertIsNotNone(selected)
            self.assertEqual(selected["controller_scale"], 0.5)
            self.assertAlmostEqual(selected["median_signed_margin_gain"], 0.01)
            self.assertGreaterEqual(selected["worst_case_signed_margin_gain"], 0.0)

    def test_feedback_lost_pass_disqualifies_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            rows = []
            for scenario in ("nominal", "a", "b"):
                rows.append(
                    {
                        "scenario": scenario,
                        "scenario_category": "nominal" if scenario == "nominal" else "target",
                        "controller_scale": 0.0,
                        "success": True,
                        "strict_gate_pass": True,
                        "stage3_2_minimum_signed_margin": 0.01,
                    }
                )
                rows.append(
                    {
                        "scenario": scenario,
                        "scenario_category": "nominal" if scenario == "nominal" else "target",
                        "controller_scale": 0.5,
                        "success": True,
                        "strict_gate_pass": scenario != "a",
                        "stage3_2_minimum_signed_margin": -0.01 if scenario == "a" else 0.02,
                    }
                )
            summaries, selected = s32.feedback_scale_summaries(ctx, rows)
            self.assertIsNotNone(selected)
            self.assertFalse(summaries[0]["target_disturbance_feedback_validation_pass"])
            self.assertEqual(summaries[0]["n_lost"], 1)

    def test_confirmation_selection_prefers_strict_long_hold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            strict = {
                **ctx.source_rows[0],
                "candidate_id": "strict25",
                "stage3_2_horizon_steps": 25,
                "success": True,
                "strict_gate_pass": True,
                "relaxed_gate_pass": True,
                "stage3_2_minimum_signed_margin": 0.02,
                "stage3_2_margin_objective": -1.0,
            }
            near = copy.deepcopy(strict)
            near.update({"candidate_id": "near25", "strict_gate_pass": False, "stage3_2_minimum_signed_margin": -0.01})
            phase = ctx.paths.extension
            phase.mkdir(parents=True, exist_ok=True)
            s32.atomic_write_json(phase / "extension_results.json", [near, strict])
            candidates = s32.select_open_loop_confirmation_candidates(ctx)
            self.assertEqual(candidates[0]["candidate_id"], "strict25")


    def test_controller_identification_probe_catalog_is_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            ctx.paths.controller.mkdir(parents=True, exist_ok=True)
            probe = {"candidate_id": "id_probe", "success": True}
            s32.atomic_write_json(
                ctx.paths.controller / "full_identification_probe_results.json",
                [probe],
            )
            rows = s32.aggregate_new_rows(ctx)
            self.assertIn("id_probe", {row.get("candidate_id") for row in rows})

    def test_open_loop_confirmation_uses_any_reproducible_strict_candidate(self) -> None:
        summary = {
            "any_candidate_confirmed_strict": True,
            "all_selected_candidates_confirmed_strict": False,
            "all_candidates_confirmed_strict": False,
        }
        self.assertTrue(s32.open_loop_confirmation_passed(summary))
        self.assertFalse(
            s32.open_loop_confirmation_passed(
                {
                    "any_candidate_confirmed_strict": False,
                    "all_candidates_confirmed_strict": False,
                }
            )
        )
        # Backward compatibility for a partially completed older run.
        self.assertTrue(
            s32.open_loop_confirmation_passed(
                {"all_candidates_confirmed_strict": True}
            )
        )

    def test_json_safety_rejects_nan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                s32.atomic_write_json(Path(tmp) / "bad.json", {"x": math.nan})

    def test_self_test(self) -> None:
        result = s32.synthetic_stage32_test()
        self.assertEqual(result["margin_probe_population"], 84)
        self.assertEqual(result["hold_probe_population"], 120)
        self.assertEqual(result["full_identification_probe_population"], 150)
        self.assertTrue(result["post_150ms_drift_rejected"])
        self.assertTrue(result["final_task_boundary_present"])


if __name__ == "__main__":
    unittest.main()
