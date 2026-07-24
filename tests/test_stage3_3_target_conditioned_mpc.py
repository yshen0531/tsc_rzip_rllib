from __future__ import annotations

import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tsc_rzip_rllib.diagnostics import stage3_3_target_conditioned_mpc as s33


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage3_3_target_conditioned_receding_horizon_mpc_250ms.json"


def load_cfg():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def fake_library():
    trajectory = np.zeros((26, 3), dtype=float)
    velocity = np.zeros((26, 2), dtype=float)
    entries = []
    for index, offset in enumerate((-0.01, 0.0, 0.01)):
        entries.append(
            {
                "candidate_id": f"entry{index}",
                "task": {
                    "task_id": f"task{index}",
                    "R_offset_m": offset,
                    "Z_offset_m": 0.0,
                    "Ip_offset_A": 0.0,
                    "mandatory": index == 1,
                },
                "stage3_3_target_tracking_pass": True,
                "full_control_vector": (np.full(75, offset)).tolist(),
                "nominal_trajectory_RZI": (trajectory + np.asarray([offset, 0.0, 0.0])[None, :]).tolist(),
                "nominal_velocity_RZ": velocity.tolist(),
            }
        )
    return {"entries": entries}


def solver_context():
    cfg = load_cfg()
    bundle = {
        "jacobian_normalized": np.eye(125, 75).tolist(),
        "jacobian_physical_units": np.eye(125, 75).tolist(),
        "center_feature_physical_units": np.zeros(125).tolist(),
        "output_scales": np.ones(125).tolist(),
        "output_weights": np.ones(125).tolist(),
        "control_radius": np.ones(75).tolist(),
    }
    return SimpleNamespace(cfg=cfg, source_bundle=bundle, env_cfg={"dt_ms": 10})


class Stage33Tests(unittest.TestCase):
    def test_config_validates(self):
        cfg = load_cfg()
        s33.validate_stage33_config(cfg)
        self.assertEqual(len(s33.build_target_tasks(cfg)), 20)
        self.assertEqual(
            cfg["refinement"]["model_revision"],
            s33.REFINEMENT_MODEL_REVISION,
        )
        self.assertEqual(
            cfg["gate"]["ip_tracking"],
            {
                "terminal_abs_tolerance_A": 2000.0,
                "hold_rms_tolerance_A": 2400.0,
                "sustained_max_tolerance_A": 4000.0,
                "revision": "2x_for_tsc_additional_heating",
            },
        )

    def test_old_ip_tracking_thresholds_are_rejected(self):
        cfg = load_cfg()
        cfg["gate"]["ip_tracking"].update(
            {
                "terminal_abs_tolerance_A": 1000.0,
                "hold_rms_tolerance_A": 1200.0,
                "sustained_max_tolerance_A": 2000.0,
            }
        )
        with self.assertRaises(ValueError):
            s33.validate_stage33_config(cfg)

    def test_target_library_has_one_nominal(self):
        tasks = s33.build_target_tasks(load_cfg())
        nominal = [t for t in tasks if t["R_offset_m"] == 0 and t["Z_offset_m"] == 0 and t["Ip_offset_A"] == 0]
        self.assertEqual(len(nominal), 1)
        self.assertTrue(nominal[0]["mandatory"])

    def test_calibration_holdout_are_disjoint(self):
        cfg = load_cfg()
        calibration = {row["scenario"] for row in cfg["mpc"]["calibration_scenarios"]}
        holdout = {row["scenario"] for row in cfg["mpc"]["holdout_scenarios"]}
        self.assertFalse(calibration & holdout)

    def test_json_safe_rejects_nan(self):
        with self.assertRaises(ValueError):
            s33._json_safe({"x": float("nan")})

    def test_vector_digest_is_deterministic(self):
        vector = np.arange(75, dtype=float)
        self.assertEqual(s33.vector_digest(vector), s33.vector_digest(vector.copy()))

    def test_target_feature_shift_blocks(self):
        task = {"R_offset_m": 0.01, "Z_offset_m": -0.002, "Ip_offset_A": 500.0}
        shift = s33._target_feature_shift(task)
        self.assertTrue(np.allclose(shift[:25], -0.01))
        self.assertTrue(np.allclose(shift[25:50], 0.002))
        self.assertTrue(np.allclose(shift[50:100], 0.0))
        self.assertTrue(np.allclose(shift[100:], -500.0))

    def test_difference_matrix_shape(self):
        matrix = s33._difference_matrix(25)
        self.assertEqual(matrix.shape, (72, 75))
        self.assertTrue(np.allclose(matrix.sum(axis=1), 0.0))

    def test_interpolation_exact_target(self):
        ctx = SimpleNamespace(cfg=load_cfg())
        result = s33.interpolation_for_target(ctx, fake_library(), np.zeros(3))
        self.assertEqual(result["task_ids"], ["task1"])
        self.assertEqual(result["weights"], [1.0])
        self.assertTrue(np.allclose(result["full_control_vector"], 0.0))

    def test_interpolation_midpoint_is_convex(self):
        ctx = SimpleNamespace(cfg=load_cfg())
        result = s33.interpolation_for_target(ctx, fake_library(), np.asarray([0.005, 0.0, 0.0]))
        weights = np.asarray(result["weights"])
        self.assertAlmostEqual(float(weights.sum()), 1.0)
        self.assertTrue(np.all(weights >= 0.0))
        represented = np.asarray(result["represented_target_offset"])
        self.assertGreater(represented[0], 0.0)

    def test_future_rows_and_columns_are_causal(self):
        rows = s33._future_feature_rows(8)
        columns = s33._future_control_columns(8)
        self.assertTrue(all((row % 25 + 1) >= 9 for row in rows))
        self.assertTrue(all((column // 3) >= 8 for column in columns))
        self.assertEqual(len(columns), 51)

    def test_receding_solver_respects_first_rate_limit(self):
        ctx = solver_context()
        result = s33.solve_receding_horizon_correction(
            ctx,
            current_step=0,
            nominal_coefficients=np.zeros((25, 3)),
            nominal_feature=np.zeros(125),
            measurement_normalized=np.asarray([1.0, -1.0, 0.0, 0.0, 0.0]),
            integral_normalized=np.zeros(5),
            previous_correction=np.zeros(3),
            controller_scale=1.0,
        )
        first = np.asarray(result["first_correction"])
        rate = np.asarray(ctx.cfg["mpc"]["per_step_correction_rate_limit_by_mode"])
        self.assertTrue(np.all(np.abs(first) <= rate + 1e-10))

    def test_receding_solver_future_only_at_last_step(self):
        ctx = solver_context()
        result = s33.solve_receding_horizon_correction(
            ctx,
            current_step=24,
            nominal_coefficients=np.zeros((25, 3)),
            nominal_feature=np.zeros(125),
            measurement_normalized=np.zeros(5),
            integral_normalized=np.zeros(5),
            previous_correction=np.zeros(3),
            controller_scale=1.0,
        )
        self.assertEqual(np.asarray(result["sequence_correction"]).shape, (1, 3))

    def test_library_sort_prefers_tracking_pass(self):
        good = {"stage3_3_target_tracking_pass": True, "stage3_3_tracking_minimum_signed_margin": 0.01, "stage3_3_tracking_objective": 5.0, "candidate_id": "g"}
        bad = {"stage3_3_target_tracking_pass": False, "stage3_3_tracking_minimum_signed_margin": 0.5, "stage3_3_tracking_objective": 0.0, "candidate_id": "b"}
        self.assertLess(s33.library_sort_key(good), s33.library_sort_key(bad))

    def test_mpc_specs_are_unique(self):
        cfg = load_cfg()
        ctx = SimpleNamespace(cfg=cfg)
        scenarios = cfg["mpc"]["calibration_scenarios"][:3]
        specs = s33.build_mpc_specs(ctx, scenarios=scenarios, controller_scales=[0.0, 1.0], split="calibration")
        ids = [row["experiment_id"] for row in specs]
        self.assertEqual(len(ids), len(set(ids)))

    def test_scale_summary_does_not_require_recovery_when_no_baseline_failure(self):
        cfg = load_cfg()
        ctx = SimpleNamespace(cfg=cfg)
        rows = []
        for scenario in ("a", "b"):
            for scale in (0.0, 1.0):
                rows.append({
                    "scenario": scenario,
                    "controller_scale": scale,
                    "success": True,
                    "stage3_3_target_tracking_pass": True,
                    "stage3_3_tracking_minimum_signed_margin": 0.01 + 0.001 * scale,
                })
        summaries, selected = s33.mpc_scale_summaries(ctx, rows)
        self.assertEqual(summaries[0]["n_baseline_failures"], 0)
        self.assertTrue(summaries[0]["recovery_requirement_met"])
        self.assertIsNotNone(selected)

    def test_holdout_no_baseline_failures_has_full_recovery_fraction(self):
        cfg = load_cfg()
        ctx = SimpleNamespace(cfg=cfg)
        rows = []
        for scenario in ("a", "b"):
            for scale in (0.0, 1.0):
                rows.append({
                    "scenario": scenario,
                    "controller_scale": scale,
                    "success": True,
                    "stage3_3_target_tracking_pass": True,
                    "stage3_3_tracking_minimum_signed_margin": 0.02,
                })
        summary = s33.holdout_summary(ctx, rows, selected_scale=1.0)
        self.assertEqual(summary["recovery_fraction"], 1.0)


    def test_target_metrics_selects_combined_ip_tracking_endpoint(self):
        cfg = load_cfg()
        ctx = SimpleNamespace(
            cfg=cfg,
            base32=SimpleNamespace(cfg={"target": copy.deepcopy(cfg["target"])}),
        )
        trajectory = []
        for state in range(26):
            # Large Ip error before state13 makes the early arrival endpoint
            # fail the doubled sustained-max gate, while the later endpoint passes.
            ip_error = 5000.0 if 10 <= state <= 12 else 100.0
            trajectory.append(
                {
                    "R": cfg["target"]["R"],
                    "Z": cfg["target"]["Z"],
                    "Ip": cfg["target"]["Ip"] + ip_error,
                }
            )
        fake_metrics = {
            "success": True,
            "terminal_RZ_euclidean_error_m": 0.0,
            "action_rms": 0.0,
            "delta_action_rms": 0.0,
            "repair_excess_rms": 0.0,
            "strict_gate_pass": True,
            "stage3_2_endpoint_evaluations": [
                {
                    "endpoint_step": 12,
                    "arrival_time_ms": 120,
                    "window_start_step": 10,
                    "sustained_box_max_error_m": 0.02,
                    "endpoint_velocity_m_per_s": 0.01,
                    "endpoint_late_velocity_rms_m_per_s": 0.01,
                    "post_arrival_velocity_rms_m_per_s": 0.01,
                    "final_velocity_m_per_s": 0.01,
                    "sustained_Ip_max_error_A": 5000.0,
                    "minimum_signed_margin": 0.20,
                    "mean_signed_margin": 0.30,
                    "pass": True,
                },
                {
                    "endpoint_step": 15,
                    "arrival_time_ms": 150,
                    "window_start_step": 13,
                    "sustained_box_max_error_m": 0.021,
                    "endpoint_velocity_m_per_s": 0.01,
                    "endpoint_late_velocity_rms_m_per_s": 0.01,
                    "post_arrival_velocity_rms_m_per_s": 0.01,
                    "final_velocity_m_per_s": 0.01,
                    "sustained_Ip_max_error_A": 100.0,
                    "minimum_signed_margin": 0.10,
                    "mean_signed_margin": 0.20,
                    "pass": True,
                },
            ],
        }
        task = {
            "task_id": "nominal",
            "R_offset_m": 0.0,
            "Z_offset_m": 0.0,
            "Ip_offset_A": 0.0,
        }
        with patch.object(s33.s32, "stage32_metrics", return_value=fake_metrics):
            metrics = s33.target_metrics(ctx, task, {"success": True, "trajectory": trajectory}, None)
        self.assertTrue(metrics["stage3_3_target_tracking_pass"])
        self.assertEqual(metrics["stage3_3_best_endpoint_step"], 15)
        early = metrics["stage3_3_endpoint_evaluations"][0]
        late = metrics["stage3_3_endpoint_evaluations"][1]
        self.assertFalse(early["stage3_3_ip_tracking_pass"])
        self.assertTrue(late["stage3_3_ip_tracking_pass"])

    def test_synthetic_smoke(self):
        result = s33.synthetic_stage33_test()
        self.assertEqual(result["synthetic_test"], "passed")

    def test_atomic_writer_cleans_failed_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            with self.assertRaises(ValueError):
                s33.atomic_write_json(path, {"bad": float("inf")})
            self.assertFalse(path.exists())
            self.assertFalse(list(Path(tmp).glob("*.tmp.*")))

    def test_probe_design_stays_collinear_at_control_bound(self):
        cfg = load_cfg()
        ctx = SimpleNamespace(cfg=cfg)
        lower = np.tile(np.asarray(cfg["trajectory"]["coefficient_lower"]), 25)
        upper = np.tile(np.asarray(cfg["trajectory"]["coefficient_upper"]), 25)
        center = np.zeros(75, dtype=float)
        center[0] = upper[0]
        direction = np.zeros(75, dtype=float)
        direction[0] = 1.0
        coordinates, scheme = s33._probe_coordinates_for_direction(
            ctx, center, direction
        )
        self.assertTrue(scheme.startswith("one_sided"))
        self.assertTrue(all(value < 0.0 for value in coordinates))
        for coordinate in coordinates:
            vector = center + coordinate * direction
            self.assertTrue(np.all(vector >= lower - 1e-12))
            self.assertTrue(np.all(vector <= upper + 1e-12))
            actual = vector - center
            projected = float(np.dot(actual, direction) / np.dot(direction, direction))
            self.assertLess(np.linalg.norm(actual - projected * direction), 1e-12)

    def test_reduced_jacobian_uses_dimensionless_curvature_aware_fit(self):
        cfg = load_cfg()
        cfg = copy.deepcopy(cfg)
        cfg["refinement"]["minimum_measured_directions"] = 1
        cfg["refinement"]["minimum_usable_directions"] = 2
        cfg["refinement"]["minimum_normalized_model_rank"] = 2
        basis = np.zeros((75, 3), dtype=float)
        basis[0, 0] = 1.0
        basis[1, 1] = 1.0
        basis[2, 2] = 1.0
        source_jacobian = np.zeros((125, 75), dtype=float)
        slopes = []
        for direction in range(3):
            slope = np.zeros(125, dtype=float)
            slope[8 + direction] = 0.02
            slope[25 + 8 + direction] = 0.015
            slope[50 + 8 + direction] = 0.04
            source_jacobian[:, direction] = slope
            slopes.append(slope)
        scales = np.concatenate(
            [
                np.full(25, 0.03),
                np.full(25, 0.03),
                np.full(25, 0.10),
                np.full(25, 0.10),
                np.full(25, 1000.0),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            ctx = SimpleNamespace(
                cfg=cfg,
                source_bundle={
                    "jacobian_physical_units": source_jacobian.tolist(),
                    "output_scales": scales.tolist(),
                },
                paths=SimpleNamespace(refinement=Path(tmp)),
            )
            center = {
                "candidate_id": "center",
                "full_control_vector": np.zeros(75).tolist(),
                "_feature": np.zeros(125),
            }
            task = {"task_id": "Z_m2mm"}
            probe_rows = []
            coordinate = 0.24
            for direction, slope in enumerate(slopes):
                # A large even Ip curvature makes the legacy raw-unit
                # through-origin residual close to one, while the central
                # derivative remains perfectly well defined.
                curvature = np.zeros(125, dtype=float)
                curvature[100 + direction] = 2000.0
                for sign in (-1.0, 1.0):
                    x = sign * coordinate
                    feature = x * slope + x * x * curvature
                    probe_rows.append(
                        {
                            "candidate_id": f"p{direction}_{sign:+.0f}",
                            "task": task,
                            "probe_direction": direction,
                            "probe_actual_coordinate": x,
                            "success": True,
                            "_feature": feature,
                        }
                    )
            basis_payload = {
                "basis": basis.tolist(),
                "selected_feature_indices": [
                    block * 25 + (state - 1)
                    for block in range(5)
                    for state in cfg["refinement"]["tracking_states"]
                ],
            }
            with patch.object(s33, "reduced_control_basis", return_value=basis_payload), patch.object(
                s33, "load_result_for_candidate", side_effect=lambda _ctx, row: row
            ), patch.object(
                s33,
                "_feature_for_task",
                side_effect=lambda _ctx, _task, result: np.asarray(result["_feature"], dtype=float),
            ):
                model = s33.build_reduced_jacobian(
                    ctx,
                    task=task,
                    center=center,
                    probe_rows=probe_rows,
                )
        self.assertEqual(model["n_measured_directions"], 3)
        self.assertEqual(model["n_usable_directions"], 3)
        self.assertGreaterEqual(model["normalized_model_rank"], 2)
        self.assertLess(model["legacy_raw_unit_reliable_directions"], 3)
        fitted = np.asarray(model["jacobian"])
        for direction, slope in enumerate(slopes):
            self.assertTrue(np.allclose(fitted[:, direction], slope, atol=1e-10))

    def test_reduced_jacobian_falls_back_to_source_prior_for_missing_probe(self):
        cfg = copy.deepcopy(load_cfg())
        cfg["refinement"]["minimum_measured_directions"] = 1
        cfg["refinement"]["minimum_usable_directions"] = 2
        cfg["refinement"]["minimum_normalized_model_rank"] = 1
        basis = np.zeros((75, 2), dtype=float)
        basis[0, 0] = 1.0
        basis[1, 1] = 1.0
        source_jacobian = np.zeros((125, 75), dtype=float)
        source_jacobian[8, 0] = 0.02
        source_jacobian[9, 1] = 0.03
        scales = np.ones(125, dtype=float)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = SimpleNamespace(
                cfg=cfg,
                source_bundle={
                    "jacobian_physical_units": source_jacobian.tolist(),
                    "output_scales": scales.tolist(),
                },
                paths=SimpleNamespace(refinement=Path(tmp)),
            )
            center = {
                "candidate_id": "center",
                "full_control_vector": np.zeros(75).tolist(),
                "_feature": np.zeros(125),
            }
            task = {"task_id": "task"}
            probe_rows = []
            for sign in (-1.0, 1.0):
                x = sign * 0.2
                feature = np.zeros(125)
                feature[8] = x * 0.02
                probe_rows.append(
                    {
                        "candidate_id": f"p{sign:+.0f}",
                        "task": task,
                        "probe_direction": 0,
                        "probe_actual_coordinate": x,
                        "success": True,
                        "_feature": feature,
                    }
                )
            basis_payload = {
                "basis": basis.tolist(),
                "selected_feature_indices": [
                    block * 25 + (state - 1)
                    for block in range(5)
                    for state in cfg["refinement"]["tracking_states"]
                ],
            }
            with patch.object(s33, "reduced_control_basis", return_value=basis_payload), patch.object(
                s33, "load_result_for_candidate", side_effect=lambda _ctx, row: row
            ), patch.object(
                s33,
                "_feature_for_task",
                side_effect=lambda _ctx, _task, result: np.asarray(result["_feature"], dtype=float),
            ):
                model = s33.build_reduced_jacobian(
                    ctx,
                    task=task,
                    center=center,
                    probe_rows=probe_rows,
                )
        self.assertEqual(model["n_measured_directions"], 1)
        self.assertEqual(model["n_usable_directions"], 2)
        self.assertTrue(model["columns"][1]["source_prior_used"])
        self.assertAlmostEqual(
            model["direction_coordinate_limits"][1],
            cfg["refinement"]["source_prior_direction_scale"],
        )

    def test_proposal_manifest_isolates_one_bad_target_model(self):
        cfg = copy.deepcopy(load_cfg())
        cfg["refinement"]["proposal_requests"] = [
            {"profile": "balanced", "step_scale": 0.5},
            {"profile": "balanced", "step_scale": 1.0},
            {"profile": "position", "step_scale": 1.0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            refinement = Path(tmp)
            ctx = SimpleNamespace(
                cfg=cfg,
                paths=SimpleNamespace(refinement=refinement),
            )
            good_task = {"task_id": "good"}
            bad_task = {"task_id": "bad"}
            center = {
                "candidate_id": "center",
                "full_control_vector": np.zeros(75).tolist(),
            }
            model = {
                "basis": np.eye(75, 2).tolist(),
                "n_measured_directions": 2,
                "n_measured_reliable_directions": 2,
                "n_usable_directions": 2,
            }

            def fake_build(_ctx, *, task, center, probe_rows):
                if task["task_id"] == "bad":
                    raise RuntimeError("synthetic bad target")
                return copy.deepcopy(model)

            with patch.object(s33, "build_reduced_jacobian", side_effect=fake_build), patch.object(
                s33,
                "solve_reduced_proposal",
                return_value=np.zeros(2, dtype=float),
            ), patch.object(
                s33,
                "clip_control",
                side_effect=lambda _ctx, vector: np.asarray(vector, dtype=float),
            ):
                manifest = s33.build_refinement_proposal_manifest(
                    ctx,
                    round_index=0,
                    active=[(bad_task, center), (good_task, center)],
                    probe_rows=[],
                )
        self.assertEqual(manifest["n_models_built"], 1)
        self.assertEqual(manifest["n_models_skipped"], 1)
        self.assertIn("bad", manifest["skipped_models"])
        self.assertTrue(manifest["candidates"])
        self.assertTrue(all(row["task"]["task_id"] == "good" for row in manifest["candidates"]))


if __name__ == "__main__":
    unittest.main()
