from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tsc_rzip_rllib.diagnostics import stage3_0_tail_sqp as s30
from tsc_rzip_rllib.diagnostics import stage3_1_adaptive_sqp_mpc as s31


class Stage31Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.base30 = s30._synthetic_context()
        config_path = Path(__file__).resolve().parents[1] / "configs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms.json"
        self.cfg = json.loads(config_path.read_text(encoding="utf-8"))

    def make_ctx(self, root: Path) -> s31.Stage31Context:
        base = copy.deepcopy(self.base30)
        nominal = base.nominals[0]
        alternate = copy.deepcopy(nominal)
        alternate["nominal_id"] = "nominal_alt_synthetic"
        alternate["source_candidate_id"] = "alt_source"
        alternate["category"] = "position_front"
        base.nominals.append(alternate)
        tail = s30.screen_tail_templates(base, nominal)[0][1]
        decoded = s30.decode_tail_sequence(base, nominal, tail)
        control = np.asarray(decoded["mode_coefficients"])[8:15].reshape(-1)
        source_result = s30._synthetic_result(base)
        source_path = root / "source_result.json.gz"
        s31.atomic_write_json_gz(source_path, source_result)
        metrics = s30.stage30_metrics(base, source_result, decoded)
        row = {
            "stage": "Stage3.0-source",
            "phase": "source",
            "candidate_id": "source_best",
            "nominal_id": nominal["nominal_id"],
            "source_candidate_id": nominal["source_candidate_id"],
            "nominal_category": nominal["category"],
            "source_name": "synthetic",
            "source_type": "synthetic",
            "control_vector": control.tolist(),
            "source_result_path": str(source_path),
            "success": True,
            **metrics,
        }
        for key, value in list(metrics.items()):
            if key.startswith("stage3_0_"):
                row["stage3_1_" + key[len("stage3_0_"):]] = copy.deepcopy(value)
        paths = s31.Stage31Paths.from_run_dir(root)
        ctx = s31.Stage31Context(
            cfg=copy.deepcopy(self.cfg),
            train_cfg=copy.deepcopy(base.train_cfg),
            env_cfg=copy.deepcopy(base.env_cfg),
            paths=paths,
            source_stage30_run=root / "source30",
            source_stage22_run=root / "source22",
            base30=base,
            modes_tsc=np.asarray(base.modes_tsc),
            initial_currents_tsc=np.asarray(base.initial_currents_tsc),
            max_delta_a=float(base.max_delta_a),
            min_current_tsc=np.asarray(base.min_current_tsc),
            max_current_tsc=np.asarray(base.max_current_tsc),
            variable_steps=tuple(range(8, 15)),
            coefficient_lower=np.tile(np.asarray(self.cfg["trajectory"]["coefficient_lower"]), 7),
            coefficient_upper=np.tile(np.asarray(self.cfg["trajectory"]["coefficient_upper"]), 7),
            nominals=copy.deepcopy(base.nominals),
            source_rows=[row],
        )
        for path in (paths.run_dir, paths.phases, paths.evaluations, paths.analysis, paths.best, paths.controller, paths.feedback, paths.confirmations):
            path.mkdir(parents=True, exist_ok=True)
        return ctx

    def test_config_validation(self) -> None:
        s31.validate_stage31_config(self.cfg)
        broken = copy.deepcopy(self.cfg)
        broken["trajectory"]["variable_steps"] = [9, 10, 11, 12, 13, 14]
        with self.assertRaises(ValueError):
            s31.validate_stage31_config(broken)

    def test_config_rejects_feedback_design_drift(self) -> None:
        broken = copy.deepcopy(self.cfg)
        broken["mpc"]["controller_scales"] = [0.0, 1.0]
        with self.assertRaises(ValueError):
            s31.validate_stage31_config(broken)
        broken = copy.deepcopy(self.cfg)
        broken["sqp"]["trust_expand_factor"] = 0.9
        with self.assertRaises(ValueError):
            s31.validate_stage31_config(broken)

    def test_self_test(self) -> None:
        result = s31.synthetic_stage31_test()
        self.assertEqual(result["parameter_dimension"], 21)
        self.assertTrue(result["strict_constraint_math"])

    def test_decode_freezes_steps_zero_through_seven(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            row = ctx.source_rows[0]
            nominal = s31.nominal_by_id(ctx, row["nominal_id"])
            decoded = s31.decode_control_sequence(ctx, nominal, s31._vector(row["control_vector"]))
            source = np.asarray(nominal["mode_coefficients_100ms"])
            np.testing.assert_allclose(decoded["mode_coefficients"][:8], source[:8])
            np.testing.assert_allclose(decoded["mode_coefficients"][8:15].reshape(-1), row["control_vector"])
            self.assertEqual(decoded["action_norm_tsc"].shape, (15, 14))

    def test_mode_action_helper_matches_open_loop_decoder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            row = ctx.source_rows[0]
            nominal = s31.nominal_by_id(ctx, row["nominal_id"])
            decoded = s31.decode_control_sequence(ctx, nominal, s31._vector(row["control_vector"]))
            for step in range(15):
                action = s31._mode_action_from_current(
                    ctx,
                    np.asarray(decoded["mode_coefficients"])[step],
                    np.asarray(decoded["currents_a_tsc"])[step],
                )
                np.testing.assert_allclose(
                    action,
                    np.asarray(decoded["action_norm_tsc"])[step],
                    atol=5e-8,
                    rtol=0.0,
                )

    def test_feature_layout_is_35(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            feature = s31.trajectory_feature_vector(ctx, s31.load_result_for_row(ctx, ctx.source_rows[0]))
            self.assertEqual(feature.shape, (35,))
            unpacked = s31.unpack_feature(feature)
            self.assertEqual(set(unpacked), {"R", "Z", "vR", "vZ", "Ip"})
            self.assertTrue(all(value.shape == (7,) for value in unpacked.values()))

    def test_stage31_metrics_preserve_hard_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            row = ctx.source_rows[0]
            nominal = s31.nominal_by_id(ctx, row["nominal_id"])
            decoded = s31.decode_control_sequence(ctx, nominal, s31._vector(row["control_vector"]))
            metrics = s31.stage31_metrics(ctx, s31.load_result_for_row(ctx, row), decoded)
            self.assertTrue(metrics["strict_gate_pass"])
            self.assertEqual(metrics["stage3_1_earliest_strict_arrival_ms"], 150)

    def test_probe_manifest_has_84_unique_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = ctx.source_rows[0]
            second = copy.deepcopy(center)
            second["candidate_id"] = "second"
            second["control_vector"] = (s31._vector(center["control_vector"]) + 0.03).tolist()
            manifest = s31.build_probe_manifest(ctx, round_index=0, centers=[center, second])
            self.assertEqual(manifest["population_size"], 84)
            self.assertEqual(len({row["candidate_id"] for row in manifest["candidates"]}), 84)
            self.assertEqual({int(row["probe_variable_index"]) for row in manifest["candidates"]}, set(range(21)))

    def test_probe_manifest_at_upper_bounds_uses_inward_secants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = copy.deepcopy(ctx.source_rows[0])
            center["candidate_id"] = "upper"
            center["control_vector"] = ctx.coefficient_upper.tolist()
            manifest = s31.build_probe_manifest(ctx, round_index=7, centers=[center])
            self.assertEqual(manifest["population_size"], 42)
            self.assertEqual({row["probe_scheme"] for row in manifest["candidates"]}, {"upper_bound_inward_secant"})

    def test_partial_jacobian_uses_null_for_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = ctx.source_rows[0]
            manifest = s31.build_probe_manifest(ctx, round_index=8, centers=[center])
            probe_rows = []
            raw = ctx.paths.run_dir / "raw"
            raw.mkdir()
            source_result = s31.load_result_for_row(ctx, center)
            for spec in manifest["candidates"]:
                variable = int(spec["probe_variable_index"])
                success = variable < 15
                rel = Path("raw") / f"{spec['candidate_id']}.json.gz"
                if success:
                    s31.atomic_write_json_gz(ctx.paths.run_dir / rel, source_result)
                probe_rows.append(
                    {
                        "candidate_id": spec["candidate_id"],
                        "success": success,
                        "control_vector": spec["control_vector"],
                        "result_relpath": str(rel),
                    }
                )
            summary = s31.build_real_tsc_jacobian(ctx, center=center, probe_manifest=manifest, probe_rows=probe_rows, output_dir=ctx.paths.run_dir / "jac")
            self.assertEqual(summary["reliable_columns"], 15)
            unavailable = [row for row in summary["column_diagnostics"] if row["method"] == "unavailable"]
            self.assertEqual(len(unavailable), 6)
            self.assertTrue(all(row["denominator"] is None for row in unavailable))
            s31.read_json(ctx.paths.run_dir / f"jac/jacobian_{center['candidate_id']}.json")

    def test_solver_returns_fifteen_proposals_and_extrapolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = ctx.source_rows[0]
            center_feature = s31.trajectory_feature_vector(ctx, s31.load_result_for_row(ctx, center))
            rng = np.random.default_rng(123)
            jacobian = rng.normal(0.0, 0.01, size=(35, 21))
            jacobian[28:] *= 1000.0
            rows = s31.solve_linearized_proposals(
                ctx,
                center=center,
                jacobian_summary={"center_feature": center_feature.tolist(), "jacobian": jacobian.tolist(), "unavailable_variables": []},
                trust_scale=1.0,
                round_index=0,
            )
            self.assertEqual(len(rows), 15)
            self.assertEqual({float(row["sqp_step_scale"]) for row in rows}, {0.5, 1.0, 1.5})
            self.assertTrue(all(np.all(s31._vector(row["control_vector"]) <= ctx.coefficient_upper + 1e-12) for row in rows))

    def test_trust_expands_on_good_boundary_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = copy.deepcopy(ctx.source_rows[0])
            center["stage3_1_max_violation"] = 0.20
            center["stage3_1_endpoint_evaluations"] = [{"endpoint_step": 15, "max_violation": 0.20}]
            row = copy.deepcopy(center)
            row.update(
                {
                    "candidate_id": "step",
                    "sqp_center_candidate_id": center["candidate_id"],
                    "sqp_endpoint_step": 15,
                    "stage3_1_max_violation": 0.10,
                    "stage3_1_endpoint_evaluations": [{"endpoint_step": 15, "max_violation": 0.10}],
                    "predicted_max_violation": 0.10,
                    "trust_boundary_fraction": 1.0,
                    "success": True,
                }
            )
            diagnostic = s31._trust_update_for_center(ctx, center=center, step_rows=[row], current_scale=1.0)
            self.assertEqual(diagnostic["action"], "expand")
            self.assertAlmostEqual(diagnostic["rho"], 1.0)
            self.assertGreater(diagnostic["new_trust_scale"], 1.0)

    def test_trust_ratio_uses_same_requested_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = copy.deepcopy(ctx.source_rows[0])
            center["stage3_1_max_violation"] = 0.01  # best endpoint, deliberately misleading
            center["stage3_1_endpoint_evaluations"] = [
                {"endpoint_step": 12, "max_violation": 0.30},
                {"endpoint_step": 15, "max_violation": 0.01},
            ]
            row = copy.deepcopy(center)
            row.update(
                {
                    "candidate_id": "endpoint_step",
                    "sqp_center_candidate_id": center["candidate_id"],
                    "sqp_endpoint_step": 12,
                    "stage3_1_max_violation": 0.02,
                    "stage3_1_endpoint_evaluations": [
                        {"endpoint_step": 12, "max_violation": 0.20},
                        {"endpoint_step": 15, "max_violation": 0.02},
                    ],
                    "predicted_max_violation": 0.20,
                    "trust_boundary_fraction": 1.0,
                    "success": True,
                }
            )
            diagnostic = s31._trust_update_for_center(
                ctx, center=center, step_rows=[row], current_scale=1.0
            )
            self.assertEqual(diagnostic["comparison_endpoint_step"], 12)
            self.assertAlmostEqual(diagnostic["center_max_violation_at_endpoint"], 0.30)
            self.assertAlmostEqual(diagnostic["real_max_violation_at_endpoint"], 0.20)
            self.assertAlmostEqual(diagnostic["rho"], 1.0)
            self.assertEqual(diagnostic["action"], "expand")

    def test_trust_shrinks_rejected_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = copy.deepcopy(ctx.source_rows[0])
            center["stage3_1_max_violation"] = 0.20
            center["stage3_1_endpoint_evaluations"] = [{"endpoint_step": 15, "max_violation": 0.20}]
            row = copy.deepcopy(center)
            row.update(
                {
                    "candidate_id": "bad",
                    "sqp_center_candidate_id": center["candidate_id"],
                    "sqp_endpoint_step": 15,
                    "stage3_1_max_violation": 0.25,
                    "stage3_1_endpoint_evaluations": [{"endpoint_step": 15, "max_violation": 0.25}],
                    "predicted_max_violation": 0.10,
                    "trust_boundary_fraction": 1.0,
                    "strict_gate_pass": False,
                    "success": True,
                }
            )
            diagnostic = s31._trust_update_for_center(ctx, center=center, step_rows=[row], current_scale=1.0)
            self.assertEqual(diagnostic["action"], "shrink_rejected")
            self.assertLess(diagnostic["new_trust_scale"], 1.0)

    def test_first_round_forces_different_nominal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            primary = ctx.source_rows[0]
            alt = copy.deepcopy(primary)
            alt["candidate_id"] = "alt"
            alt["nominal_id"] = ctx.nominals[1]["nominal_id"]
            alt["nominal_category"] = "position_front"
            alt["control_vector"] = (s31._vector(primary["control_vector"]) + 0.1).tolist()
            alt["stage3_1_max_violation"] = 1.0
            centers = s31.select_sqp_centers(ctx, [primary, alt], round_index=0)
            self.assertNotEqual(centers[0]["nominal_id"], centers[1]["nominal_id"])

    def test_dimensionless_batch_and_causal_gain_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = ctx.source_rows[0]
            feature = s31.trajectory_feature_vector(ctx, s31.load_result_for_row(ctx, center))
            rng = np.random.default_rng(8)
            jacobian = rng.normal(0.0, 0.02, size=(35, 21))
            jacobian[28:] *= 1000.0
            bundle = s31.build_mpc_bundle(ctx, center=center, jacobian_summary={"center_feature": feature.tolist(), "jacobian": jacobian.tolist()})
            self.assertEqual(np.asarray(bundle["batch_gain"]).shape, (21, 35))
            self.assertEqual(len(bundle["causal_time_indexed_gains"]), 7)
            for row in bundle["causal_time_indexed_gains"]:
                self.assertEqual(np.asarray(row["first_action_gain"]).shape, (3, 5))
            self.assertFalse(bundle["online_feedback_validated"])

    def test_feedback_poc_selects_one_global_scale(self) -> None:
        rows = []
        scenarios = list(self.cfg["mpc"]["scenarios"])
        for scenario in scenarios:
            rows.append(
                {
                    "scenario": scenario,
                    "controller_scale": 0.0,
                    "success": True,
                    "stage3_1_max_violation": 1.0,
                }
            )
            rows.append(
                {
                    "scenario": scenario,
                    "controller_scale": 0.5,
                    "success": True,
                    "stage3_1_max_violation": 1.0 if scenario == "nominal" else 0.8,
                }
            )
            rows.append(
                {
                    "scenario": scenario,
                    "controller_scale": 1.0,
                    "success": True,
                    "stage3_1_max_violation": 0.9 if scenario == "nominal" else 1.2,
                }
            )
        summaries, selected = s31._feedback_scale_summaries(
            rows, meaningful_improvement=1e-4
        )
        self.assertEqual(len(summaries), 2)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["controller_scale"], 0.5)
        self.assertTrue(selected["limited_causal_feedback_poc_pass"])

    def test_feedback_specs_are_24(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            center = ctx.source_rows[0]
            specs = s31.feedback_specs(ctx, {"causal_time_indexed_gains": []}, center)
            self.assertEqual(len(specs), 24)
            self.assertEqual(len({spec["experiment_id"] for spec in specs}), 24)

    def test_json_safety_rejects_nan(self) -> None:
        with self.assertRaises(ValueError):
            s31._json_safe({"x": float("nan")})

    def test_predicted_constraints_use_sustained_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            feature = np.zeros(35)
            feature[0:7] = 0.029
            feature[7:14] = 0.029
            self.assertEqual(s31.predicted_constraints(ctx, feature, 15)["max_violation"], 0.0)
            # state13 is inside the endpoint-15 sustained window.
            feature[4] = 0.031
            self.assertGreater(s31.predicted_constraints(ctx, feature, 15)["position_box_m"], 0.03)

    def test_confirmation_selection_preserves_different_nominal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_ctx(Path(tmp))
            primary = ctx.source_rows[0]
            alt = copy.deepcopy(primary)
            alt["candidate_id"] = "alt"
            alt["nominal_id"] = ctx.nominals[1]["nominal_id"]
            alt["control_vector"] = (s31._vector(primary["control_vector"]) + 0.2).tolist()
            selected = s31.select_confirmation_candidates(ctx, [primary, alt])
            self.assertGreaterEqual(len({row["nominal_id"] for row, _ in selected}), 2)


if __name__ == "__main__":
    unittest.main()
