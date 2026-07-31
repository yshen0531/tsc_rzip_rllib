from __future__ import annotations

import importlib.util
import json
import runpy
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "tests" / "conftest.py"))
SCRIPT = (
    ROOT
    / "docs"
    / "codex"
    / "audit_tools"
    / "stage4_2r3c3t8_measured_current_headroom_diagnostic.py"
)
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t8_measured_current_headroom_diagnostic_v1.json"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t8_measured_current_headroom_diagnostic", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T8 diagnostic")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class _LinearEvaluator:
    horizon = 1
    policy = {"allowed_arrival_steps": [1]}

    def endpoint_margin(
        self, values: np.ndarray, endpoint: int
    ) -> tuple[float, dict[str, object]]:
        margin = float(values[-1, 0])
        return margin, {
            "endpoint_step": endpoint,
            "active_constraint": "position",
        }

    def best(
        self, values: np.ndarray
    ) -> tuple[float, dict[str, object]]:
        return self.endpoint_margin(values, 1)


class Stage42R3C3T8Tests(unittest.TestCase):
    def test_frozen_design_is_exact_and_non_authorizing(self) -> None:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        AUDIT._validate_design(cfg)
        self.assertEqual(
            cfg["diagnostic_contract"][
                "target_direction_common_scale_grid"
            ],
            [1.0, 1.25, 1.5, 2.0, 3.0, 4.0],
        )
        self.assertFalse(
            cfg["scientific_scope"]["controller_implementation_authorized"]
        )

    def test_current_odd_and_midpoint_decomposition(self) -> None:
        baseline = np.zeros((2, 14))
        delta = np.full((2, 14), 0.2)
        plus = baseline + delta
        minus = baseline - delta
        odd, midpoint_error = AUDIT._current_odd_component(
            plus, minus, baseline
        )
        np.testing.assert_array_equal(odd, delta)
        self.assertEqual(midpoint_error, 0.0)

    def test_scaled_optimizer_uses_only_new_envelope(self) -> None:
        baseline = np.zeros((2, 3))
        baseline[-1, 0] = -1.5
        columns = [np.zeros_like(baseline) for _ in range(8)]
        columns[5][-1, 0] = 1.0
        baseline_current = np.zeros((2, 14))
        current_columns = [np.zeros_like(baseline_current) for _ in range(8)]
        result = AUDIT._optimize_context(
            _LinearEvaluator(),
            baseline,
            columns,
            baseline_current,
            current_columns,
            np.full(14, -400.0),
            np.full(14, 400.0),
            target_scale=2.0,
            maximum_current_utilization=0.55,
            warm_starts=[],
        )
        self.assertTrue(result["passed"])
        self.assertLessEqual(abs(result["best_coefficients"][0]), 1.0)
        self.assertGreater(result["best_coefficients"][5], 1.0)


if __name__ == "__main__":
    unittest.main()
