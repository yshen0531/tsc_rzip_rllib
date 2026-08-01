from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs/codex/audit_tools/stage4_2r3c3t13_time_resolved_model_compatibility.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t13_time_resolved_model_compatibility", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T13 model compatibility audit")
T13 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = T13
SPEC.loader.exec_module(T13)


class Stage42R3C3T13ModelCompatibilityTests(unittest.TestCase):
    def test_frozen_matrix_and_counts(self) -> None:
        self.assertTrue(T13.IDENTITY.endswith("_v4"))
        self.assertEqual(T13.GATES["command_modal_residual_max_A"], 1e-6)
        self.assertEqual(sum(row["count"] for row in T13.RUNS.values()), 1408)
        self.assertEqual(sum(row["bytes"] for row in T13.RUNS.values()), 62444406)
        self.assertEqual(
            sum(row["signed_pairs"] for row in T13.RUNS.values()), 576
        )
        self.assertEqual(sum(row["nodes"] for row in T13.RUNS.values()), 896)
        self.assertEqual(T13.OUTPUT_SCALES.shape, (175,))

    def test_design_hash_matches_preregistered_document(self) -> None:
        design = (
            ROOT
            / "docs/codex/reports/STAGE4_2R3C3T13_TIME_RESOLVED_MODEL_COMPATIBILITY_DESIGN_V4.md"
        )
        self.assertEqual(T13._sha256(design), T13.DESIGN_SHA256)

    def test_actuator_conditioned_raw_horizons(self) -> None:
        contract = T13.RUNS["R3c3"]
        self.assertEqual(
            T13._expected_raw_lengths(
                "R3c3",
                {"action_delay_steps": 0, "slew_scale": 1.0},
                contract,
            ),
            (36, 35),
        )
        self.assertEqual(
            T13._expected_raw_lengths(
                "R3c3",
                {"action_delay_steps": 2, "slew_scale": 0.9},
                contract,
            ),
            (38, 37),
        )
        with self.assertRaisesRegex(ValueError, "unexpected actuator case"):
            T13._expected_raw_lengths(
                "R3c3",
                {"action_delay_steps": 1, "slew_scale": 1.0},
                contract,
            )

    def test_exact_prediction_passes_all_gates(self) -> None:
        rng = np.random.default_rng(17)
        actual = rng.normal(size=175) * T13.OUTPUT_SCALES * 0.1
        delta_u = np.zeros((35, 3))
        delta_u[0, 0] = 0.01
        metrics = T13._prediction_metrics(
            actual,
            actual.copy(),
            delta_u,
            expected_first_effect_state=1,
        )
        self.assertTrue(metrics["prediction_gate_pass"])
        self.assertTrue(metrics["causality_gate_pass"])
        self.assertTrue(metrics["all_gates_pass"])

    def test_pre_effect_leakage_is_separate_from_prediction_shape(self) -> None:
        actual = np.zeros(175)
        actual[0] = 2e-9
        predicted = actual.copy()
        delta_u = np.zeros((35, 3))
        delta_u[2, 0] = 0.01
        metrics = T13._prediction_metrics(
            actual,
            predicted,
            delta_u,
            expected_first_effect_state=3,
        )
        self.assertTrue(metrics["prediction_gate_pass"])
        self.assertFalse(metrics["causality_gate_pass"])
        self.assertFalse(metrics["all_gates_pass"])

    def test_relative_gate_rejects_wrong_small_response(self) -> None:
        actual = np.zeros(175)
        actual[0] = 1e-6
        predicted = np.zeros(175)
        delta_u = np.zeros((35, 3))
        delta_u[0, 0] = 0.01
        metrics = T13._prediction_metrics(
            actual,
            predicted,
            delta_u,
            expected_first_effect_state=1,
        )
        self.assertLess(metrics["position_rmse_m"], T13.GATES["position_rmse_m"])
        self.assertGreater(metrics["relative_response_l2"], 0.99)
        self.assertFalse(metrics["prediction_gate_pass"])

    def test_mode_projection_reconstructs_orthonormal_subspace(self) -> None:
        rng = np.random.default_rng(4)
        q, _ = np.linalg.qr(rng.normal(size=(14, 3)))
        u = rng.normal(size=(35, 3))
        delta_i = T13.NOMINAL_MAX_DELTA_A * (u @ q.T)
        recovered = (delta_i / T13.NOMINAL_MAX_DELTA_A) @ q
        reconstructed = T13.NOMINAL_MAX_DELTA_A * (recovered @ q.T)
        self.assertTrue(np.allclose(recovered, u, atol=1e-12))
        self.assertTrue(np.allclose(reconstructed, delta_i, atol=1e-12))

    def test_trace_command_is_primary_and_observed_current_is_diagnostic(self) -> None:
        rng = np.random.default_rng(8)
        q, _ = np.linalg.qr(rng.normal(size=(14, 3)))
        commanded_u = rng.normal(size=(35, 3)) * 0.01
        slew = 0.9
        actions = (commanded_u @ q.T) / slew
        command_delta = actions * T13.NOMINAL_MAX_DELTA_A * slew
        observed_delta = command_delta.copy()
        observed_delta[:, 13] += 0.02
        currents = np.vstack([np.zeros(14), np.cumsum(observed_delta, axis=0)])
        trajectory = [{"currents_a_tsc": row.tolist()} for row in currents]
        trace = [{"action_norm_tsc": row.tolist()} for row in actions]
        recovered, command_modal, observed_modal, observed_difference = (
            T13._input_sequence(
                trajectory,
                trace,
                slew_scale=slew,
                modes=q,
            )
        )
        self.assertTrue(np.allclose(recovered, commanded_u, atol=1e-12))
        self.assertLess(command_modal, 1e-12)
        self.assertGreater(observed_modal, 0.0)
        self.assertAlmostEqual(float(np.max(observed_difference)), 0.02)


if __name__ == "__main__":
    unittest.main()
