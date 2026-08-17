from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]

from scripts.rgeo_zgeo_1ms_id2g1_grouped_causal_model import (
    AllowedDataset,
    CausalTCNDelta,
    Cell,
    CONFIG,
    CONFIG_SHA256,
    FEATURE_NAMES,
    _eligible,
    fit_neural,
    fit_structured,
    frame,
    load_stage,
    sha256,
)
from scripts.rgeo_zgeo_1ms_id2g1_grouped_causal_model_independent import numeric_maximum


def synthetic_cell(cell_id: str = "none__baseline", context: str = "none", offset: float = 0.0) -> Cell:
    time = np.arange(35, dtype=float)
    states = np.column_stack([
        0.70 - 0.0004 * time + offset,
        0.03 + 0.0005 * time - offset,
        31000.0 - 8.0 * time,
    ])
    current = np.zeros((35, 3), dtype=float)
    current[:, 0] = np.minimum(time / 15.0, 1.0)
    issued = current[:-1].copy()
    return Cell(cell_id, context, "baseline", states, current, issued, None, None, 0)


def synthetic_dataset(cells: list[Cell]) -> AllowedDataset:
    return AllowedDataset(
        cells=cells,
        source_rzi=cells[0].states[0].copy(),
        state_scale=np.asarray([0.001, 0.001, 100.0]),
        response_scale=np.asarray([0.0001, 0.0001, 25.0]),
        basis=np.eye(14, 3), q0=np.zeros(14), maximum_projection_residual_a=0.0,
    )


class FrozenContractTests(unittest.TestCase):
    def test_config_hash_and_evidence_contract(self) -> None:
        self.assertEqual(sha256(CONFIG), CONFIG_SHA256)
        stage = load_stage(CONFIG)
        self.assertEqual(stage["new_tsc_calls"], 0)
        self.assertEqual(stage["data_contract"]["id2c2_records_allowed"], 0)
        self.assertEqual(stage["data_contract"]["calibration_records_allowed"], 0)
        self.assertEqual(stage["data_contract"]["holdout_records_allowed"], 0)
        self.assertEqual([row["held_context"] for row in stage["folds"]],
                         ["none", "p04_plus_i18_d1", "p07_plus_i18_d1"])
        self.assertEqual(stage["eligibility"]["simplicity_order"],
                         ["stable_lpv", "small_gru", "causal_tcn", "probabilistic_ensemble"])

    def test_forbidden_inputs_are_explicit(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        forbidden = set(stage["data_contract"]["forbidden_model_inputs"])
        self.assertTrue({"future_r_geo_z_geo_ip", "future_actual_or_readback_current",
                         "wire_current", "context_id", "id2c2", "calibration", "holdout"} <= forbidden)
        self.assertNotIn("context_id", FEATURE_NAMES)
        self.assertNotIn("wire_current", FEATURE_NAMES)

    def test_launcher_is_zero_plant_and_server_venv(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_id2g1_grouped_causal_model_comparison.sh").read_text(encoding="utf-8")
        self.assertIn("tsc_all/tsc_simulation/venv_simu", text)
        self.assertNotIn("gotsc", text.lower())
        self.assertNotIn("step_current", text)
        self.assertNotIn("runner", text.lower())


class CausalFeatureTests(unittest.TestCase):
    def test_frame_has_only_frozen_dimensions_and_blind_action(self) -> None:
        cell = synthetic_cell()
        cell.issued[22] = [1.0, 2.0, -3.0]
        data = synthetic_dataset([cell])
        actual = frame(cell, 22, data)
        blind = frame(cell, 22, data, action_blind=True)
        self.assertEqual(actual.shape, (len(FEATURE_NAMES),))
        np.testing.assert_allclose(actual[9:12], [1.0, 2.0, -3.0])
        np.testing.assert_allclose(blind[9:12], [1.0, 0.0, 0.0])

    def test_structured_recursive_does_not_read_future_actual_state_or_current(self) -> None:
        cell = synthetic_cell()
        data = synthetic_dataset([cell])
        model = fit_structured([cell], data, {"poles": [0.2, 0.5, 0.8, 0.95], "ridge": 0.001})
        expected = model.recursive(cell, data)
        changed = synthetic_cell()
        changed.states[17:] += np.asarray([100.0, -100.0, 1e6])
        changed.currents[17:] += 999.0
        actual = model.recursive(changed, synthetic_dataset([changed]))
        # Keep the same source normalization while altering only unavailable future rows.
        actual = model.recursive(changed, data)
        np.testing.assert_allclose(actual, expected, atol=1e-12, rtol=0.0)

    def test_tcn_is_causal_and_shape_preserving(self) -> None:
        model = CausalTCNDelta(12, [1, 2, 4, 8], 2).eval()
        prefix = torch.randn(1, 16, len(FEATURE_NAMES))
        extended = torch.cat([prefix, torch.randn(1, 4, len(FEATURE_NAMES))], dim=1)
        with torch.no_grad():
            left = model(prefix)
            right = model(extended)
        self.assertEqual(tuple(right.shape), (1, 20, 3))
        torch.testing.assert_close(left, right[:, :16], atol=0.0, rtol=0.0)

    def test_neural_training_is_small_and_deterministic(self) -> None:
        cells = [synthetic_cell("none__baseline", "none"),
                 synthetic_cell("p04__baseline", "p04", 1e-6)]
        data = synthetic_dataset(cells)
        cfg = {"hidden_width": 4, "layers": 1, "seeds": [11], "epochs": 2,
               "learning_rate": 0.003, "weight_decay": 0.0001, "gradient_clip": 1.0}
        left = fit_neural("small_gru", cells, data, cfg, 11).teacher(cells[0], data)
        right = fit_neural("small_gru", cells, data, cfg, 11).teacher(cells[0], data)
        np.testing.assert_array_equal(left, right)


class GateAndAuditTests(unittest.TestCase):
    def test_eligibility_requires_every_fold(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        row = {"one_step_p95_abs": [1e-4, 1e-4, 10.0],
               "recursive_p95_abs": [5e-4, 5e-4, 20.0],
               "response_nrmse": 0.5, "positive_peak_cosine_count": 10}
        folds = [{"fold_id": name, **row} for name in ("a", "b", "c")]
        passed, failures = _eligible("stable_lpv", folds, 1.0, stage)
        self.assertTrue(passed, failures)
        folds[1] = {**folds[1], "response_nrmse": 0.96}
        passed, failures = _eligible("stable_lpv", folds, 1.0, stage)
        self.assertFalse(passed)
        self.assertIn("RESPONSE:b", failures)

    def test_probabilistic_gate_requires_coverage_and_width(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        row = {"one_step_p95_abs": [1e-4, 1e-4, 10.0],
               "recursive_p95_abs": [5e-4, 5e-4, 20.0],
               "response_nrmse": 0.5, "positive_peak_cosine_count": 10,
               "marginal_coverage": [0.9, 0.9, 0.9],
               "p95_half_width": [5e-4, 5e-4, 20.0]}
        folds = [{"fold_id": name, **row} for name in ("a", "b", "c")]
        self.assertTrue(_eligible("probabilistic_ensemble", folds, 1.0, stage)[0])
        folds[0] = {**folds[0], "marginal_coverage": [0.79, 0.9, 0.9]}
        self.assertFalse(_eligible("probabilistic_ensemble", folds, 1.0, stage)[0])

    def test_independent_numeric_comparison_is_strict(self) -> None:
        self.assertEqual(numeric_maximum({"a": [1.0, True]}, {"a": [1.0, True]}), 0.0)
        self.assertAlmostEqual(numeric_maximum({"a": 1.0}, {"a": 1.25}), 0.25)
        self.assertEqual(numeric_maximum({"a": 1}, {"b": 1}), float("inf"))


if __name__ == "__main__":
    unittest.main()
