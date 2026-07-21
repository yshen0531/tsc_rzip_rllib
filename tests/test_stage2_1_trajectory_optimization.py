from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as jsonio
from tsc_rzip_rllib.diagnostics import stage2_1_trajectory_optimization as s21
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2


class Stage21Tests(unittest.TestCase):
    def _cfg(self) -> dict:
        return {
            "target": {"R": 0.75, "Z": 0.0, "Ip": 29779.724},
            "trajectory": {
                "n_modes": 3,
                "node_count": 5,
                "node_steps": [0, 2, 4, 6, 9],
            },
            "gate": {
                "precise_tolerance_m": 0.03,
                "relaxed_tolerance_m": 0.04,
                "required_terminal_streak_steps": 3,
                "terminal_velocity_max_m_per_s": 0.1,
                "late_velocity_rms_max_m_per_s": 0.1,
                "late_window_steps": 4,
                "ip_tolerance_a": 10000.0,
            },
            "objective": {
                "tier_spacing": 1e6,
                "tube_window_steps": 5,
                "weights": {
                    "tube_excess_mean": 90.0,
                    "tube_excess_max": 120.0,
                    "tube_excess_terminal": 60.0,
                    "velocity_excess": 80.0,
                    "streak_deficit": 4.0,
                    "late_position_core": 1.5,
                    "terminal_position_core": 1.0,
                    "velocity_core": 2.5,
                    "terminal_ip": 0.1,
                    "action_rms": 0.02,
                    "delta_action_rms": 0.04,
                    "repair": 2.0,
                },
            },
            "archives": {
                "damped_capacity": 8,
                "precise_capacity": 8,
                "minimum_vector_distance": 0.0,
                "damped_box_limit_m": 0.045,
                "precise_box_limit_m": 0.03,
                "speed_margin_factor": 1.0,
                "precise_score_weights": {
                    "terminal_box": 8.0,
                    "late_position": 3.0,
                    "terminal_velocity": 0.5,
                    "late_velocity": 1.5,
                },
            },
            "confirmation": {
                "top_k_candidates": 5,
                "repeats_per_candidate": 3,
            },
            "search": {
                "population_size": 192,
                "family_quotas": {
                    "anchors": 12,
                    "sensitivity": 18,
                    "damped_tail": 36,
                    "precise_tail": 24,
                    "bridge": 48,
                    "global": 18,
                    "random_tail": 36,
                },
                "bridge_noise_by_mode": [0.0, 0.0, 0.0],
                "tail_node_indices": [2, 3, 4],
                "early_node_indices": [0, 1],
                "early_node_std_by_mode": [0.035, 0.035, 0.015],
                "tail_std_by_mode": [0.15, 0.15, 0.065],
                "tail_node_std_multiplier": [0.8, 1.0, 1.25],
                "random_tail_radius_by_mode": [0.42, 0.42, 0.16],
                "sensitivity_delta_by_mode": [0.08, 0.08, 0.035],
            },
        }

    @staticmethod
    def _record(
        candidate_id: str,
        *,
        box: float,
        terminal_velocity: float,
        late_velocity: float,
        late_position: float | None = None,
        vector_offset: float = 0.0,
        streak30: int = 0,
        streak40: int = 3,
    ) -> dict:
        return {
            "candidate_id": candidate_id,
            "vector": (np.arange(15, dtype=float) * 0.001 + vector_offset).tolist(),
            "terminal_RZ_box_max_error_m": box,
            "terminal_RZ_euclidean_error_m": box * 1.25,
            "late_RZ_euclidean_rms_m": late_position if late_position is not None else box * 1.3,
            "terminal_R_error_m": -min(box, 0.025),
            "terminal_Z_error_m": box,
            "terminal_Ip_error_A": 500.0,
            "terminal_velocity_m_per_s": terminal_velocity,
            "late_velocity_rms_m_per_s": late_velocity,
            "trailing_streak_within_30mm_steps": streak30,
            "trailing_streak_within_40mm_steps": streak40,
        }

    def test_self_test(self) -> None:
        result = s21.synthetic_self_test()
        self.assertTrue(result["tube_excess_monotonic"])
        self.assertTrue(result["bridge_front_tail_semantics"])

    def test_validate_fixed_search_design(self) -> None:
        cfg = self._cfg()
        ctx = SimpleNamespace(
            cfg=cfg,
            coefficient_lower=np.full(15, -1.0),
            coefficient_upper=np.full(15, 1.0),
        )
        s21.validate_stage21_config(ctx)
        cfg["search"]["family_quotas"]["bridge"] -= 1
        with self.assertRaises(ValueError):
            s21.validate_stage21_config(ctx)

    def test_dual_archive_keeps_both_families(self) -> None:
        cfg = self._cfg()
        damped = self._record(
            "damped",
            box=0.032,
            terminal_velocity=0.03,
            late_velocity=0.09,
            vector_offset=0.0,
            streak30=0,
            streak40=10,
        )
        precise = self._record(
            "precise",
            box=0.029,
            terminal_velocity=0.38,
            late_velocity=0.33,
            vector_offset=0.2,
            streak30=3,
            streak40=3,
        )
        archives = s21.rebuild_archives(cfg, {"damped": [], "precise": []}, [damped, precise])
        self.assertEqual(archives["damped"][0]["candidate_id"], "damped")
        self.assertEqual(archives["precise"][0]["candidate_id"], "precise")

    def test_damped_archive_uses_exact_hard_speed_limits(self) -> None:
        cfg = self._cfg()
        safe = self._record(
            "safe",
            box=0.032,
            terminal_velocity=0.1,
            late_velocity=0.1,
            vector_offset=0.0,
        )
        unsafe = self._record(
            "unsafe",
            box=0.031,
            terminal_velocity=0.099,
            late_velocity=0.100001,
            vector_offset=0.2,
        )
        archives = s21.rebuild_archives(cfg, {"damped": [], "precise": []}, [safe, unsafe])
        ids = {row["candidate_id"] for row in archives["damped"]}
        self.assertIn("safe", ids)
        self.assertNotIn("unsafe", ids)

    def test_sensitivity_center_is_speed_safe_and_near_strict_boundary(self) -> None:
        cfg = self._cfg()
        unsafe_closer = self._record(
            "unsafe_closer",
            box=0.0302,
            terminal_velocity=0.03,
            late_velocity=0.101,
            vector_offset=0.0,
        )
        safe_farther = self._record(
            "safe_farther",
            box=0.0311,
            terminal_velocity=0.043,
            late_velocity=0.0997,
            vector_offset=0.2,
        )
        safe_far = self._record(
            "safe_far",
            box=0.035,
            terminal_velocity=0.01,
            late_velocity=0.07,
            vector_offset=0.4,
        )
        center = s21._sensitivity_center_record(
            [unsafe_closer, safe_far, safe_farther], cfg
        )
        self.assertEqual(center["candidate_id"], "safe_farther")

    def test_precise_archive_prefers_near_damped_candidate(self) -> None:
        cfg = self._cfg()
        near_damped = self._record(
            "near_damped",
            box=0.0299,
            terminal_velocity=0.04,
            late_velocity=0.112,
            late_position=0.038,
            vector_offset=0.0,
            streak30=1,
        )
        underdamped = self._record(
            "underdamped",
            box=0.0295,
            terminal_velocity=0.19,
            late_velocity=0.17,
            late_position=0.038,
            vector_offset=0.2,
            streak30=1,
        )
        self.assertLess(
            s21._precise_archive_score(near_damped, cfg),
            s21._precise_archive_score(underdamped, cfg),
        )

    def test_smooth_objective_prefers_31mm_to_32mm(self) -> None:
        cfg = self._cfg()
        ctx = SimpleNamespace(cfg=cfg)
        base_metrics = {
            "success": True,
            "gate_tier": 1,
            "gate_label": "PASS_DAMPED_HOLD_40MM",
            "strict_gate_pass": False,
            "relaxed_gate_pass": True,
            "terminal_velocity_m_per_s": 0.03,
            "late_velocity_rms_m_per_s": 0.08,
            "terminal_Ip_error_A": 0.0,
            "trailing_streak_within_30mm_steps": 0,
        }

        def result(z_error: float) -> dict:
            trajectory = []
            for _ in range(11):
                trajectory.append(
                    {
                        "R": 0.75 - 0.025,
                        "Z": z_error,
                        "Ip": 29779.724,
                    }
                )
            return {"success": True, "trajectory": trajectory}

        with patch.object(s21.s2, "stage2_metrics", return_value=base_metrics):
            score31 = s21.stage21_metrics(ctx, result(0.031), None)["continuous_objective"]
            score32 = s21.stage21_metrics(ctx, result(0.032), None)["continuous_objective"]
        self.assertLess(score31, score32)

    def test_strict_json_writer_reports_nonfinite_path_and_leaves_no_temp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            with self.assertRaisesRegex(ValueError, r"\$\.spec\.prediction"):
                jsonio.atomic_write_json(
                    path,
                    {"spec": {"prediction": float("nan")}},
                )
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(tmpdir).glob("*.tmp.*")), [])

    def test_legacy_nan_json_is_normalized_to_null_on_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "legacy.json"
            path.write_text('{"optional": NaN}', encoding="utf-8")
            self.assertIsNone(jsonio.read_json(path)["optional"])

    def test_candidate_specs_are_json_safe_when_surrogate_is_disabled(self) -> None:
        ctx = SimpleNamespace(cfg={"trajectory": {"horizon_steps": 10}})
        manifest = {
            "generation": 0,
            "candidates": [
                {
                    "candidate_id": "candidate",
                    "population_index": 0,
                    "source_name": "unit",
                    "source_type": "unit",
                    "vector": np.zeros(15).tolist(),
                    "linear_prefilter_score": 1.0,
                    "predicted_terminal_R_error_m": -0.02,
                    "predicted_terminal_Z_error_m": 0.03,
                    "predicted_terminal_Ip_error_A": 100.0,
                    "predicted_terminal_velocity_m_per_s": None,
                    "predicted_late_velocity_rms_m_per_s": None,
                }
            ],
        }
        decoded = {
            "nodes": np.zeros((5, 3)),
            "mode_coefficients": np.zeros((10, 3)),
            "action_norm_tsc": np.zeros((10, 14)),
            "action_norm_display": np.zeros((10, 14)),
        }
        with patch.object(s21.s2, "decode_vector", return_value=decoded):
            specs = s21.candidate_specs_from_manifest(ctx, manifest)
        self.assertIsNone(specs[0]["predicted_terminal_velocity_m_per_s"])
        self.assertIsNone(specs[0]["predicted_late_velocity_rms_m_per_s"])
        jsonio.assert_json_finite(specs, context="unit generation specs")

    def test_confirmation_missing_historical_predictions_is_recomputed_and_json_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paths = s21.Stage21Paths(
                run_dir=root,
                state=root / "stage2_1_state.json",
                manifest=root / "stage2_1_manifest.json",
                generations=root / "stage2_1_generations",
                evaluations=root / "stage2_1_evaluations",
                confirmations=root / "stage2_1_confirmations",
                analysis=root / "stage2_1_analysis",
                best=root / "stage2_1_best",
                source_reference=root / "source_stage2_reference",
            )
            generation_dir = paths.generations / "gen_000"
            generation_dir.mkdir(parents=True)
            # Deliberately omit predicted_terminal_R/Z/Ip: this is the exact
            # historical-row shape that caused the real confirmation crash.
            row = {
                "stage": "Stage2.1",
                "generation": 0,
                "candidate_id": "candidate",
                "population_index": 0,
                "parameter_vector": np.zeros(15).tolist(),
                "success": True,
                "selection_score": 1000001.0,
                "linear_prefilter_score": 5.0,
            }
            jsonio.atomic_write_json(generation_dir / "generation_results.json", [row])
            ctx = SimpleNamespace(
                cfg={
                    "confirmation": {"top_k_candidates": 1, "repeats_per_candidate": 1},
                    "trajectory": {"horizon_steps": 10},
                }
            )
            decoded = {
                "nodes": np.zeros((5, 3)),
                "mode_coefficients": np.zeros((10, 3)),
                "action_norm_tsc": np.zeros((10, 14)),
                "action_norm_display": np.zeros((10, 14)),
            }
            linear = {
                "linear_prefilter_score": 2.0,
                "predicted_terminal_R_error_m": -0.021,
                "predicted_terminal_Z_error_m": 0.029,
                "predicted_terminal_Ip_error_A": 321.0,
            }
            captured: dict[str, object] = {}

            def fake_evaluate(_ctx, specs, *, output_dir, backend, resume):
                captured["specs"] = specs
                return [
                    {
                        "experiment_id": specs[0]["experiment_id"],
                        "success": True,
                        "trajectory": [],
                    }
                ]

            metrics = {
                "success": True,
                "gate_tier": 1,
                "gate_label": "PASS_DAMPED_HOLD_40MM",
                "strict_gate_pass": False,
                "relaxed_gate_pass": True,
                "terminal_RZ_euclidean_error_m": 0.041,
                "terminal_velocity_m_per_s": 0.02,
                "late_velocity_rms_m_per_s": 0.08,
                "selection_score": 1000001.0,
                "continuous_objective": 1.0,
            }
            with (
                patch.object(s21.s2, "decode_vector", return_value=decoded),
                patch.object(s21.s2, "linear_prefilter_metrics", return_value=linear),
                patch.object(s21.s2, "evaluate_specs", side_effect=fake_evaluate),
                patch.object(s21, "stage21_metrics", return_value=metrics),
            ):
                verdict = s21.run_confirmation(
                    ctx,
                    paths,
                    backend="serial",
                    resume=True,
                )
            specs = captured["specs"]
            assert isinstance(specs, list)
            self.assertEqual(specs[0]["predicted_terminal_Z_error_m"], 0.029)
            jsonio.assert_json_finite(specs, context="regression confirmation specs")
            self.assertEqual(verdict["verdict"], "PASS_DAMPED_HOLD_40MM_CONFIRMED_ONLY")
            for output in (
                paths.confirmations / "confirmation_results.json",
                paths.confirmations / "confirmation_summary.json",
                paths.confirmations / "stage2_1_verdict.json",
            ):
                text = output.read_text(encoding="utf-8")
                self.assertNotIn("NaN", text)
                self.assertNotIn("Infinity", text)
                json.loads(text, parse_constant=lambda token: self.fail(f"invalid constant {token}"))

    def test_result_persistence_turns_nonfinite_runtime_payload_into_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "candidate.json.gz"
            spec = {"experiment_id": "candidate", "parameter": 1.0}
            result = {
                "experiment_id": "candidate",
                "spec": spec,
                "success": True,
                "trajectory": [{"R": float("nan")}],
            }
            stored = s2._persist_evaluation_result(path, spec=spec, result=result)
            self.assertFalse(stored["success"])
            self.assertIn("serialization rejected", stored["failure_reason"])
            reloaded = jsonio.read_json_gz(path)
            self.assertFalse(reloaded["success"])
            self.assertEqual(list(Path(tmpdir).glob("*.tmp.*")), [])

    def test_confirmation_summary_uses_null_when_all_repeats_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            paths = s21.Stage21Paths(
                run_dir=root,
                state=root / "state.json",
                manifest=root / "manifest.json",
                generations=root / "stage2_1_generations",
                evaluations=root / "evaluations",
                confirmations=root / "confirmations",
                analysis=root / "analysis",
                best=root / "best",
                source_reference=root / "source",
            )
            generation_dir = paths.generations / "gen_000"
            generation_dir.mkdir(parents=True)
            jsonio.atomic_write_json(
                generation_dir / "generation_results.json",
                [
                    {
                        "generation": 0,
                        "candidate_id": "candidate",
                        "population_index": 0,
                        "parameter_vector": np.zeros(15).tolist(),
                        "success": True,
                        "selection_score": 1.0,
                    }
                ],
            )
            ctx = SimpleNamespace(
                cfg={
                    "confirmation": {"top_k_candidates": 1, "repeats_per_candidate": 1},
                    "trajectory": {"horizon_steps": 10},
                }
            )
            decoded = {
                "nodes": np.zeros((5, 3)),
                "mode_coefficients": np.zeros((10, 3)),
                "action_norm_tsc": np.zeros((10, 14)),
                "action_norm_display": np.zeros((10, 14)),
            }
            linear = {
                "linear_prefilter_score": 2.0,
                "predicted_terminal_R_error_m": -0.02,
                "predicted_terminal_Z_error_m": 0.03,
                "predicted_terminal_Ip_error_A": 0.0,
            }

            def fake_evaluate(_ctx, specs, *, output_dir, backend, resume):
                return [{"experiment_id": specs[0]["experiment_id"], "success": False}]

            failed_metrics = {
                "success": False,
                "failure_reason": "synthetic failure",
                "gate_tier": 99,
                "gate_label": "TSC_FAILURE",
                "strict_gate_pass": False,
                "relaxed_gate_pass": False,
                "continuous_objective": 1e12,
                "selection_score": 99e6 + 1e12,
            }
            with (
                patch.object(s21.s2, "decode_vector", return_value=decoded),
                patch.object(s21.s2, "linear_prefilter_metrics", return_value=linear),
                patch.object(s21.s2, "evaluate_specs", side_effect=fake_evaluate),
                patch.object(s21, "stage21_metrics", return_value=failed_metrics),
            ):
                verdict = s21.run_confirmation(ctx, paths, backend="serial", resume=True)
            self.assertEqual(verdict["verdict"], "NO_CONFIRMED_HOLD")
            summary = jsonio.read_json_any(paths.confirmations / "confirmation_summary.json")
            self.assertIsNone(summary[0]["mean_terminal_RZ_error_m"])
            self.assertIsNone(summary[0]["max_terminal_velocity_m_per_s"])
            self.assertIsNone(summary[0]["max_late_velocity_rms_m_per_s"])

    def test_state_record_rejects_nonfinite_environment_state(self) -> None:
        env = SimpleNamespace(
            last_state={
                "time_ms": 1100,
                "R": float("nan"),
                "Z": 0.0,
                "Ip": 30000.0,
                "currents_a_tsc": np.zeros(14),
                "currents_a_display": np.zeros(14),
            }
        )
        with self.assertRaisesRegex(ValueError, "non-finite scalar"):
            jsonio._state_record(env, 0, np.zeros(14))


if __name__ == "__main__":
    unittest.main()
