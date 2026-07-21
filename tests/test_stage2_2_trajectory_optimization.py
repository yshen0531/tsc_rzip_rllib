from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as jsonio
from tsc_rzip_rllib.diagnostics import stage2_2_trajectory_optimization as s22


class Stage22Tests(unittest.TestCase):
    @staticmethod
    def _cfg() -> dict:
        root = Path(__file__).resolve().parents[1]
        return json.loads(
            (root / "configs/stage2_2_svd3_corner_feasibility_100ms.json").read_text(
                encoding="utf-8"
            )
        )

    @staticmethod
    def _record(
        candidate_id: str,
        *,
        final3: float,
        terminal_box: float | None = None,
        terminal_velocity: float,
        late_velocity: float,
        vector_offset: float = 0.0,
        strict: bool | None = None,
    ) -> dict:
        terminal_box = final3 if terminal_box is None else terminal_box
        vp = max(final3 / 0.03 - 1.0, 0.0)
        vt = max(terminal_velocity / 0.1 - 1.0, 0.0)
        vl = max(late_velocity / 0.1 - 1.0, 0.0)
        values = np.asarray([vp, vt, vl, 0.0])
        strict_value = bool(np.max(values) <= 1e-12) if strict is None else strict
        return {
            "candidate_id": candidate_id,
            "source_stage": "synthetic",
            "generation": 0,
            "source_type": "synthetic",
            "vector": (np.arange(15, dtype=float) * 0.001 + vector_offset).tolist(),
            "strict_gate_pass": strict_value,
            "relaxed_gate_pass": True,
            "gate_tier": 0 if strict_value else 1,
            "gate_label": "PASS_PRECISE_HOLD_30MM" if strict_value else "PASS_DAMPED_HOLD_40MM",
            "stage2_2_final3_box_max_error_m": final3,
            "stage2_2_final3_box_mean_error_m": final3 - 0.0002,
            "stage2_2_terminal_box_error_m": terminal_box,
            "terminal_RZ_box_max_error_m": terminal_box,
            "terminal_velocity_m_per_s": terminal_velocity,
            "late_velocity_rms_m_per_s": late_velocity,
            "terminal_Ip_error_A": 500.0,
            "stage2_2_position_violation": vp,
            "stage2_2_terminal_speed_violation": vt,
            "stage2_2_late_speed_violation": vl,
            "stage2_2_ip_violation": 0.0,
            "stage2_2_max_violation": float(np.max(values)),
            "stage2_2_sum_violation": float(np.sum(values)),
            "stage2_2_l2_violation": float(np.linalg.norm(values)),
            "stage2_2_quality": 1.0,
            "stage2_2_selection_score": (0.0 if strict_value else 1e6) + 1e5 * float(np.max(values)),
            "selection_score": (0.0 if strict_value else 1e6) + 1e5 * float(np.max(values)),
            "stage2_legacy_continuous_objective": 10.0,
            "stage2_legacy_selection_score": 1e6 + 10.0,
            "trailing_streak_within_30mm_steps": 3 if final3 <= 0.03 else 0,
            "trailing_streak_within_40mm_steps": 3,
            "success": True,
            "parameter_vector": (np.arange(15, dtype=float) * 0.001 + vector_offset).tolist(),
            "population_index": 0,
        }

    def test_synthetic_self_test(self) -> None:
        result = s22.synthetic_self_test()
        self.assertTrue(result["constraint_violation_math"])
        self.assertTrue(result["archive_separation"])

    def test_validate_fixed_design(self) -> None:
        cfg = self._cfg()
        ctx = SimpleNamespace(
            cfg=cfg,
            coefficient_lower=np.tile(np.asarray([-2.6, -2.6, -0.9]), 5),
            coefficient_upper=np.tile(np.asarray([2.6, 2.6, 0.9]), 5),
        )
        s22.validate_stage22_config(ctx)
        cfg["search"]["family_quotas"]["corner_local"] -= 1
        with self.assertRaises(ValueError):
            s22.validate_stage22_config(ctx)

    def test_constraint_violation_matches_expected(self) -> None:
        ctx = SimpleNamespace(cfg=self._cfg())
        violation = s22._constraint_violations(
            ctx,
            final3_box_max_error_m=0.031275,
            terminal_velocity_m_per_s=0.01,
            late_velocity_rms_m_per_s=0.1029,
            terminal_Ip_error_A=500.0,
        )
        self.assertAlmostEqual(violation["stage2_2_position_violation"], 0.0425)
        self.assertAlmostEqual(violation["stage2_2_late_speed_violation"], 0.029)
        self.assertAlmostEqual(violation["stage2_2_max_violation"], 0.0425)

    def test_stage22_metrics_preserves_hard_gate_and_prefers_lower_max_violation(self) -> None:
        cfg = self._cfg()
        ctx = SimpleNamespace(cfg=cfg)

        def result(final3: float, late_v: float) -> dict:
            trajectory = []
            for index in range(11):
                z = final3 if index >= 8 else 0.02
                trajectory.append({"R": 0.725, "Z": z, "Ip": 29779.724})
            return {"success": True, "trajectory": trajectory}

        def base_metrics(late_v: float, strict: bool) -> dict:
            return {
                "success": True,
                "gate_tier": 0 if strict else 1,
                "gate_label": "PASS_PRECISE_HOLD_30MM" if strict else "PASS_DAMPED_HOLD_40MM",
                "strict_gate_pass": strict,
                "relaxed_gate_pass": True,
                "terminal_velocity_m_per_s": 0.01,
                "late_velocity_rms_m_per_s": late_v,
                "terminal_Ip_error_A": 0.0,
                "selection_score": 1e6,
                "continuous_objective": 10.0,
                "action_rms": 0.2,
                "delta_action_rms": 0.1,
                "repair_excess_rms": 0.0,
            }

        with patch.object(s22.s2, "stage2_metrics", return_value=base_metrics(0.1029, False)):
            a = s22.stage22_metrics(ctx, result(0.031275, 0.1029), None)
        with patch.object(s22.s2, "stage2_metrics", return_value=base_metrics(0.099, False)):
            b = s22.stage22_metrics(ctx, result(0.03132, 0.099), None)
        self.assertLess(a["stage2_2_max_violation"], b["stage2_2_max_violation"])
        self.assertLess(a["selection_score"], b["selection_score"])

    def test_stage22_metrics_rejects_gate_drift(self) -> None:
        ctx = SimpleNamespace(cfg=self._cfg())
        trajectory = [
            {"R": 0.75, "Z": 0.0, "Ip": 29779.724}
            for _ in range(11)
        ]
        base_metrics = {
            "success": True,
            "gate_tier": 1,
            "gate_label": "wrong",
            "strict_gate_pass": False,
            "relaxed_gate_pass": True,
            "terminal_velocity_m_per_s": 0.0,
            "late_velocity_rms_m_per_s": 0.0,
            "terminal_Ip_error_A": 0.0,
            "selection_score": 1e6,
            "continuous_objective": 0.0,
        }
        with patch.object(s22.s2, "stage2_metrics", return_value=base_metrics):
            with self.assertRaises(RuntimeError):
                s22.stage22_metrics(ctx, {"success": True, "trajectory": trajectory}, None)

    def test_archives_use_exact_speed_and_corner_ranking(self) -> None:
        cfg = self._cfg()
        speed_safe = self._record(
            "speed_safe", final3=0.03131, terminal_velocity=0.02, late_velocity=0.099, vector_offset=0.0
        )
        slightly_unsafe = self._record(
            "unsafe", final3=0.0308, terminal_velocity=0.02, late_velocity=0.105, vector_offset=0.2
        )
        balanced = self._record(
            "balanced", final3=0.03127, terminal_velocity=0.01, late_velocity=0.1029, vector_offset=0.4
        )
        archives = s22.rebuild_archives(cfg, {}, [speed_safe, slightly_unsafe, balanced])
        damped_ids = {row["candidate_id"] for row in archives["damped"]}
        self.assertIn("speed_safe", damped_ids)
        self.assertNotIn("unsafe", damped_ids)
        self.assertEqual(archives["corner"][0]["candidate_id"], "balanced")

    def test_precise_archive_prefers_near_damped_transition(self) -> None:
        cfg = self._cfg()
        transition = self._record(
            "transition", final3=0.0312, terminal_box=0.0299, terminal_velocity=0.03, late_velocity=0.108, vector_offset=0.0
        )
        deep_fast = self._record(
            "deep_fast", final3=0.0297, terminal_box=0.028, terminal_velocity=0.12, late_velocity=0.18, vector_offset=0.2
        )
        archives = s22.rebuild_archives(cfg, {}, [transition, deep_fast])
        self.assertEqual(archives["precise"][0]["candidate_id"], "transition")

    def test_corner_covariance_does_not_move_node_zero(self) -> None:
        cfg = self._cfg()
        vectors = [np.arange(15, dtype=float) * 0.01 + index * 0.001 for index in range(8)]
        mean, covariance = s22.fit_corner_covariance(vectors, cfg=cfg, trust_scale=1.0)
        self.assertTrue(np.allclose(mean[:3], vectors[0][:3]))
        self.assertTrue(np.allclose(covariance[:3, 3:], 0.0))
        self.assertTrue(np.allclose(covariance[3:, :3], 0.0))
        self.assertTrue(np.all(np.linalg.eigvalsh(covariance) > 0.0))

    def test_probe_generation_is_24_unique_and_fixes_node_zero(self) -> None:
        cfg = self._cfg()
        ctx = SimpleNamespace(cfg=cfg)
        archives = {
            "corner": [self._record("corner", final3=0.0312, terminal_velocity=0.01, late_velocity=0.103, vector_offset=0.0)],
            "damped": [self._record("damped", final3=0.0313, terminal_velocity=0.02, late_velocity=0.099, vector_offset=0.2)],
            "precise": [self._record("precise", final3=0.0311, terminal_box=0.0299, terminal_velocity=0.03, late_velocity=0.108, vector_offset=0.4)],
        }

        def proposal(_ctx, vector, source_name, source_type):
            return {"vector": np.asarray(vector, dtype=float).tolist(), "source_name": source_name, "source_type": source_type}

        with patch.object(s22, "_proposal_row", side_effect=proposal):
            rows = s22._probe_rows(ctx, archives, generation=0, trust_scale=1.0)
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({s22._vector_key(row["vector"]) for row in rows}), 24)
        centers = s22.select_probe_centers(archives)
        center_node0 = {tuple(np.round(s22._record_vector(c)[:3], 12)) for c in centers}
        for row in rows:
            self.assertIn(tuple(np.round(np.asarray(row["vector"])[:3], 12)), center_node0)


    def test_local_search_preserves_a_validated_node_zero(self) -> None:
        cfg = self._cfg()
        corner = [
            self._record(
                f"corner_{index}",
                final3=0.0312 + index * 1e-5,
                terminal_velocity=0.01,
                late_velocity=0.102 + index * 1e-4,
                vector_offset=0.2 * index,
            )
            for index in range(4)
        ]
        mean = np.asarray(corner[0]["vector"], dtype=float)
        state = {
            "archives": {"corner": corner},
            "corner_mean": mean.tolist(),
            "corner_covariance": (np.eye(15) * 0.001).tolist(),
            "trust_scale": 1.0,
        }
        ctx = SimpleNamespace(cfg=cfg)

        def proposal(_ctx, vector, source_name, source_type):
            return {
                "vector": np.asarray(vector, dtype=float).tolist(),
                "source_name": source_name,
                "source_type": source_type,
            }

        validated_node0 = {
            tuple(np.round(np.asarray(record["vector"], dtype=float)[:3], 12))
            for record in corner
        }
        with patch.object(s22, "_proposal_row", side_effect=proposal):
            rng = np.random.default_rng(17)
            local_rows = s22._corner_local_pool(ctx, state, rng, 8)
            mix_rows = s22._trust_mix_pool(ctx, state, rng, 20)
        for row in [*local_rows, *mix_rows]:
            node0 = tuple(np.round(np.asarray(row["vector"], dtype=float)[:3], 12))
            self.assertIn(node0, validated_node0)

    def test_confirmation_selection_is_category_aware(self) -> None:
        cfg = self._cfg()
        rows = [
            self._record("corner", final3=0.03127, terminal_velocity=0.01, late_velocity=0.103, vector_offset=0.0),
            self._record("speed", final3=0.03131, terminal_velocity=0.02, late_velocity=0.099, vector_offset=0.2),
            self._record("position", final3=0.0299, terminal_velocity=0.11, late_velocity=0.17, vector_offset=0.4),
            self._record("gate", final3=0.032, terminal_velocity=0.01, late_velocity=0.08, vector_offset=0.6),
        ]
        selected = s22.select_confirmation_candidates(rows, cfg)
        reasons = {reason for row in selected for reason in row["confirmation_reasons"]}
        self.assertIn("corner", reasons)
        self.assertIn("speed_safe", reasons)
        self.assertIn("position_front", reasons)
        self.assertIn("gate_hall", reasons)

    def test_optional_predictions_are_null_not_nan(self) -> None:
        ctx = SimpleNamespace(
            cfg={"trajectory": {"horizon_steps": 10}},
        )
        manifest = {
            "generation": 0,
            "candidates": [
                {
                    "candidate_id": "c",
                    "population_index": 0,
                    "source_name": "x",
                    "source_type": "x",
                    "vector": np.zeros(15).tolist(),
                    "linear_prefilter_score": 1.0,
                    "predicted_terminal_R_error_m": 0.0,
                    "predicted_terminal_Z_error_m": 0.0,
                    "predicted_terminal_Ip_error_A": 0.0,
                    "predicted_final3_box_max_error_m": None,
                    "predicted_terminal_velocity_m_per_s": None,
                    "predicted_late_velocity_rms_m_per_s": None,
                    "predicted_corner_max_violation": None,
                    "predicted_corner_sum_violation": None,
                }
            ],
        }
        decoded = {
            "nodes": np.zeros((5, 3)),
            "mode_coefficients": np.zeros((10, 3)),
            "action_norm_tsc": np.zeros((10, 14)),
            "action_norm_display": np.zeros((10, 14)),
        }
        with patch.object(s22.s2, "decode_vector", return_value=decoded):
            specs = s22.candidate_specs_from_manifest(ctx, manifest)
        self.assertIsNone(specs[0]["predicted_final3_box_max_error_m"])
        jsonio.assert_json_finite(specs)

    def test_strict_json_writer_rejects_nonfinite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            with self.assertRaisesRegex(ValueError, r"\$\.prediction"):
                jsonio.atomic_write_json(path, {"prediction": float("nan")})
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
