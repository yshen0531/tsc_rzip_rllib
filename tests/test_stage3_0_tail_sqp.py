from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tsc_rzip_rllib.diagnostics import stage3_0_tail_sqp as s3


class Stage30Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = s3._synthetic_context()

    def _with_temp_paths(self, root: Path) -> s3.Stage30Context:
        ctx = copy.deepcopy(self.ctx)
        ctx.paths = s3.Stage30Paths.from_run_dir(root)
        for path in (ctx.paths.run_dir, ctx.paths.phases, ctx.paths.evaluations):
            path.mkdir(parents=True, exist_ok=True)
        return ctx

    def _result_with_errors(self, errors: list[tuple[float, float]], ip_error: float = 500.0) -> dict:
        self.assertEqual(len(errors), 16)
        rows = []
        for step, (r_error, z_error) in enumerate(errors):
            rows.append(
                {
                    "step_index": step,
                    "time_ms": 1100 + 10 * step,
                    "R": self.ctx.cfg["target"]["R"] + r_error,
                    "Z": self.ctx.cfg["target"]["Z"] + z_error,
                    "Ip": self.ctx.cfg["target"]["Ip"] + ip_error,
                    "currents_a_tsc": [0.0] * 14,
                    "currents_a_display": [0.0] * 14,
                    "action_norm_tsc": [0.0] * 14,
                    "action_norm_display": [0.0] * 14,
                    "abnormal": False,
                }
            )
        return {"experiment_id": "custom", "success": True, "failure_reason": "", "trajectory": rows}

    def test_synthetic_self_test(self) -> None:
        result = s3.synthetic_stage30_test()
        self.assertEqual(result["screen_templates"], 12)
        self.assertTrue(result["extended_horizon_gate_pass"])

    def test_config_validation_accepts_fixed_design(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "configs/stage3_0_svd3_tail_sqp_150ms.json"
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        s3.validate_stage30_config(cfg)
        broken = copy.deepcopy(cfg)
        broken["trajectory"]["horizon_steps"] = 14
        with self.assertRaises(ValueError):
            s3.validate_stage30_config(broken)

    def test_start_time_parser(self) -> None:
        self.assertEqual(s3.start_time_ms({"start_folder": "1100ms"}), 1100)
        self.assertEqual(s3.start_time_ms({"start_folder": "1120"}), 1120)
        with self.assertRaises(ValueError):
            s3.start_time_ms({"start_folder": "not-a-time"})

    def test_templates_are_unique_and_freeze_first_nine_actions(self) -> None:
        nominal = self.ctx.nominals[0]
        templates = s3.screen_tail_templates(self.ctx, nominal)
        self.assertEqual(len(templates), 12)
        self.assertEqual(
            len({s3._vector_key(nominal["nominal_id"], tail) for _, tail in templates}),
            12,
        )
        source = np.asarray(nominal["mode_coefficients_100ms"], dtype=float)
        reference_action = None
        for _, tail in templates:
            decoded = s3.decode_tail_sequence(self.ctx, nominal, tail)
            np.testing.assert_allclose(decoded["mode_coefficients"][:9], source[:9])
            # The initial screen is a pure time-margin diagnostic: all twelve
            # templates preserve the original 90-100 ms source control too.
            np.testing.assert_allclose(decoded["mode_coefficients"][9], source[9])
            action = np.asarray(decoded["action_norm_tsc"])
            self.assertEqual(action.shape, (15, 14))
            if reference_action is None:
                reference_action = action[:9].copy()
            else:
                np.testing.assert_allclose(action[:9], reference_action)

    def test_precise_gate_passes_at_150ms(self) -> None:
        nominal = self.ctx.nominals[0]
        decoded = s3.decode_tail_sequence(self.ctx, nominal, s3.screen_tail_templates(self.ctx, nominal)[0][1])
        metrics = s3.stage30_metrics(self.ctx, s3._synthetic_result(self.ctx), decoded)
        self.assertTrue(metrics["strict_gate_pass"])
        self.assertEqual(metrics["stage3_0_earliest_strict_arrival_ms"], 150)
        self.assertEqual(metrics["stage3_0_gate_endpoint_ms"], 150)

    def test_arrival_at_120ms_is_allowed_and_must_persist(self) -> None:
        # Inside the precise tube before state 10 and stationary afterwards.
        errors = [(-0.02, 0.02)] * 16
        metrics = s3.stage30_metrics(self.ctx, self._result_with_errors(errors), None)
        self.assertTrue(metrics["strict_gate_pass"])
        self.assertEqual(metrics["stage3_0_earliest_strict_arrival_ms"], 120)
        self.assertEqual(metrics["stage3_0_gate_endpoint_ms"], 120)

        # Leave the tube after an otherwise valid 120 ms arrival: must fail.
        errors[14] = (-0.045, 0.045)
        errors[15] = (-0.045, 0.045)
        rejected = s3.stage30_metrics(self.ctx, self._result_with_errors(errors), None)
        self.assertFalse(rejected["strict_gate_pass"])

    def test_relaxed_gate_reports_actual_gate_endpoint(self) -> None:
        errors = [(-0.035, 0.035)] * 16
        metrics = s3.stage30_metrics(self.ctx, self._result_with_errors(errors), None)
        self.assertFalse(metrics["strict_gate_pass"])
        self.assertTrue(metrics["relaxed_gate_pass"])
        self.assertEqual(metrics["stage3_0_gate_endpoint_ms"], 120)
        self.assertLessEqual(metrics["stage3_0_gate_sustained_box_max_error_m"], 0.04)

    def test_separate_late_rms_limit_is_enforced(self) -> None:
        ctx = copy.deepcopy(self.ctx)
        ctx.cfg["gate"]["terminal_velocity_max_m_per_s"] = 0.20
        ctx.cfg["gate"]["late_velocity_rms_max_m_per_s"] = 0.05
        # One 1 mm transition produces 0.1 m/s speed: terminal limit passes,
        # but the stricter RMS limit must reject the candidate.
        errors = [(-0.02, 0.02)] * 16
        errors[12] = (-0.021, 0.02)
        metrics = s3.stage30_metrics(ctx, self._result_with_errors(errors), None)
        self.assertFalse(metrics["strict_gate_pass"])
        self.assertGreater(metrics["stage3_0_endpoint_late_speed_violation"], 0.0)

    def test_feature_vector_has_documented_layout(self) -> None:
        feature = s3.trajectory_feature_vector(self.ctx, s3._synthetic_result(self.ctx))
        self.assertEqual(feature.shape, (30,))
        unpacked = s3.unpack_feature_vector(feature)
        self.assertEqual(set(unpacked), {"R", "Z", "vR", "vZ", "Ip"})
        self.assertTrue(all(value.shape == (6,) for value in unpacked.values()))

    def test_probe_manifest_has_72_unique_probes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._with_temp_paths(Path(tmp))
            nominal = ctx.nominals[0]
            base_tail = s3.screen_tail_templates(ctx, nominal)[0][1]
            centers = [
                {
                    "candidate_id": "center_a",
                    "nominal_id": nominal["nominal_id"],
                    "tail_vector": base_tail.tolist(),
                    "result_relpath": "dummy_a.json.gz",
                },
                {
                    "candidate_id": "center_b",
                    "nominal_id": nominal["nominal_id"],
                    "tail_vector": (base_tail + np.tile([0.04, -0.03, 0.01], 6)).tolist(),
                    "result_relpath": "dummy_b.json.gz",
                },
            ]
            manifest = s3.build_probe_manifest(ctx, round_index=0, centers=centers)
            self.assertEqual(manifest["population_size"], 72)
            keys = {
                s3._vector_key(row["nominal_id"], row["tail_vector"])
                for row in manifest["candidates"]
            }
            self.assertEqual(len(keys), 72)
            self.assertEqual(
                {int(row["probe_variable_index"]) for row in manifest["candidates"]},
                set(range(18)),
            )

    def test_probe_manifest_handles_center_at_global_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._with_temp_paths(Path(tmp))
            nominal = ctx.nominals[0]
            tail = np.asarray(ctx.coefficient_upper, dtype=float).copy()
            centers = [
                {
                    "candidate_id": "upper_bound_center",
                    "nominal_id": nominal["nominal_id"],
                    "tail_vector": tail.tolist(),
                    "result_relpath": "dummy.json.gz",
                }
            ]
            manifest = s3.build_probe_manifest(ctx, round_index=7, centers=centers)
            self.assertEqual(manifest["population_size"], 36)
            schemes = {row["probe_scheme"] for row in manifest["candidates"]}
            self.assertEqual(schemes, {"upper_bound_inward_secant"})
            for variable in range(18):
                pair = [row for row in manifest["candidates"] if row["probe_variable_index"] == variable]
                self.assertEqual(len(pair), 2)
                values = sorted(s3._tail_vector(row["tail_vector"])[variable] for row in pair)
                self.assertLess(values[0], values[1])
                self.assertLess(values[1], tail[variable] + 1e-12)

    def test_partial_jacobian_columns_use_json_null_not_nan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._with_temp_paths(Path(tmp))
            nominal = ctx.nominals[0]
            tail = s3.screen_tail_templates(ctx, nominal)[0][1]
            center_result_path = ctx.paths.run_dir / "center.json.gz"
            s3.atomic_write_json_gz(center_result_path, s3._synthetic_result(ctx))
            center = {
                "candidate_id": "center_partial",
                "nominal_id": nominal["nominal_id"],
                "tail_vector": tail.tolist(),
                "result_relpath": "center.json.gz",
            }
            manifest = s3.build_probe_manifest(ctx, round_index=8, centers=[center])
            probe_rows = []
            raw_dir = ctx.paths.run_dir / "probe_results"
            raw_dir.mkdir()
            for spec in manifest["candidates"]:
                variable = int(spec["probe_variable_index"])
                success = variable < 12
                rel = Path("probe_results") / f"{spec['candidate_id']}.json.gz"
                if success:
                    s3.atomic_write_json_gz(ctx.paths.run_dir / rel, s3._synthetic_result(ctx))
                probe_rows.append(
                    {
                        "candidate_id": spec["candidate_id"],
                        "success": success,
                        "tail_vector": spec["tail_vector"],
                        "result_relpath": str(rel),
                    }
                )
            summary = s3.build_real_tsc_jacobian(
                ctx,
                center=center,
                probe_manifest=manifest,
                probe_rows=probe_rows,
                output_dir=ctx.paths.run_dir / "jacobian",
            )
            self.assertEqual(summary["reliable_columns"], 12)
            unavailable = [row for row in summary["columns"] if row["method"] == "unavailable"]
            self.assertEqual(len(unavailable), 6)
            self.assertTrue(all(row["denominator"] is None for row in unavailable))
            # Strict readback proves the summary contains no NaN token.
            saved = s3.read_json(ctx.paths.run_dir / "jacobian/jacobian_center_partial.json")
            s3.jsonio.assert_json_finite(saved, context="partial Stage3.0 Jacobian")

    def test_linearized_solver_returns_twelve_bounded_proposals(self) -> None:
        nominal = self.ctx.nominals[0]
        tail = s3.screen_tail_templates(self.ctx, nominal)[2][1]
        center_feature = s3.trajectory_feature_vector(self.ctx, s3._synthetic_result(self.ctx))
        # Deterministic, full-column-rank local model with modest sensitivity.
        rng = np.random.default_rng(123)
        jacobian = rng.normal(0.0, 0.01, size=(30, 18))
        jacobian[24:, :] *= 1000.0
        center = {
            "candidate_id": "center",
            "nominal_id": nominal["nominal_id"],
            "tail_vector": tail.tolist(),
        }
        summary = {"center_feature": center_feature.tolist(), "jacobian": jacobian.tolist()}
        rows = s3.solve_linearized_tail_proposals(
            self.ctx,
            center=center,
            jacobian_summary=summary,
            trust_scale=1.0,
            round_index=0,
        )
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({s3._vector_key(row["nominal_id"], row["tail_vector"]) for row in rows}), 12)
        radius = np.asarray(self.ctx.cfg["sqp"]["trust_radius_by_step_mode"]).reshape(-1)
        for row in rows:
            delta = s3._tail_vector(row["tail_vector"]) - tail
            self.assertTrue(np.all(delta <= radius + 1e-12))
            self.assertTrue(np.all(delta >= -radius - 1e-12))


    def test_linearized_solver_freezes_unavailable_jacobian_variables(self) -> None:
        nominal = self.ctx.nominals[0]
        tail = s3.screen_tail_templates(self.ctx, nominal)[2][1]
        center_feature = s3.trajectory_feature_vector(self.ctx, s3._synthetic_result(self.ctx))
        rng = np.random.default_rng(321)
        jacobian = rng.normal(0.0, 0.01, size=(30, 18))
        jacobian[24:, :] *= 1000.0
        columns = [
            {"method": "central" if index < 12 else "unavailable"}
            for index in range(18)
        ]
        center = {
            "candidate_id": "center_partial_solver",
            "nominal_id": nominal["nominal_id"],
            "tail_vector": tail.tolist(),
        }
        summary = {
            "center_feature": center_feature.tolist(),
            "jacobian": jacobian.tolist(),
            "columns": columns,
        }
        rows = s3.solve_linearized_tail_proposals(
            self.ctx,
            center=center,
            jacobian_summary=summary,
            trust_scale=1.0,
            round_index=3,
        )
        self.assertEqual(len(rows), 12)
        for row in rows:
            delta = s3._tail_vector(row["tail_vector"]) - tail
            np.testing.assert_allclose(delta[12:], 0.0, atol=1e-12)
            self.assertEqual(row["unavailable_jacobian_variables_frozen"], list(range(12, 18)))

    def test_nominal_catalog_enforces_category_quotas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analysis = root / "stage2_2_analysis"
            analysis.mkdir()

            def row(index: int, category: str) -> dict:
                vector = np.linspace(-0.5, 0.5, 15) + index * 0.2
                return {
                    "success": True,
                    "candidate_id": f"{category}_{index}",
                    "parameter_vector": vector.tolist(),
                    "generation": index,
                    "source_type": category,
                    "stage2_2_max_violation": 0.03 + index * 0.001,
                    "stage2_2_final3_box_max_error_m": 0.03 + index * 0.0001,
                    "late_velocity_rms_m_per_s": 0.09 + index * 0.0001,
                    "selection_score": float(index),
                }

            corner = [row(i, "corner") for i in range(10)]
            speed = [row(i + 20, "speed") for i in range(10)]
            gate = [row(i + 40, "gate") for i in range(10)]
            position = [row(i + 60, "position") for i in range(10)]
            all_rows = corner + speed + gate + position
            for name, payload in (
                ("all_generation_results.json", all_rows),
                ("corner_hall_of_fame.json", corner),
                ("speed_safe_hall_of_fame.json", speed),
                ("gate_hall_of_fame.json", gate),
            ):
                (analysis / name).write_text(json.dumps(payload), encoding="utf-8")
            cfg = {
                "nominals": {
                    "count": 8,
                    "corner_candidates": 3,
                    "speed_safe_candidates": 2,
                    "gate_candidates": 2,
                    "position_front_candidates": 1,
                    "minimum_vector_distance": 0.01,
                }
            }
            interpolation = np.zeros((10, 5))
            interpolation[:, 0] = 1.0
            catalog = s3.build_nominal_catalog(cfg, root, interpolation)
            counts = {category: sum(item["category"] == category for item in catalog) for category in {
                "corner", "speed_safe", "gate", "position_front"
            }}
            self.assertEqual(counts, {"corner": 3, "speed_safe": 2, "gate": 2, "position_front": 1})

    def test_json_writer_rejects_nonfinite_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            with self.assertRaises(ValueError):
                s3.atomic_write_json(path, {"bad": float("nan")})
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
