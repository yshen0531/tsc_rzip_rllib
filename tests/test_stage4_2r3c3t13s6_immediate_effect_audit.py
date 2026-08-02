from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

import numpy as np

if sys.platform == "win32":
    try:
        import resource as _resource  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.RLIMIT_CORE = 4
        resource.getrlimit = lambda _which: (65536, 65536)
        resource.setrlimit = lambda _which, _limits: None
        sys.modules["resource"] = resource


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "docs/codex/audit_tools/stage4_2r3c3t13s6_immediate_effect_audit.py"
)
SPEC = importlib.util.spec_from_file_location("stage4_2r3c3t13s6_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
S6 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S6)


class Stage42R3C3T13S6Tests(unittest.TestCase):
    def test_corrected_effect_states_are_post_queue_and_delay_independent(self):
        spec = {
            "r3c3_probe_issue_step": 0,
            "r3c3_probe_cancel_step": 1,
            "action_delay_steps": 2,
        }
        self.assertEqual(S6.corrected_effect_states(spec), (1, 2))
        spec.update(
            r3c3_probe_issue_step=14,
            r3c3_probe_cancel_step=15,
            action_delay_steps=0,
        )
        self.assertEqual(S6.corrected_effect_states(spec), (15, 16))

    def test_rank_deficiency_is_strict_json_safe(self):
        result = S6.matrix_diagnostics(
            np.zeros((4, 28)), required_rank=4, maximum_condition=15.0
        )
        self.assertEqual(result["rank"], 0)
        self.assertIsNone(result["condition_number"])
        self.assertFalse(result["condition_number_finite"])
        self.assertFalse(result["rank_condition_pass"])
        json.dumps(result, allow_nan=False)

    def test_full_rank_cell_fit_preserves_frozen_tube_contract(self):
        rows = []
        for index, direction in enumerate(S6.s5.DIRECTIONS):
            x = np.zeros(4)
            x[index] = 1.0
            y = np.zeros(10)
            y[index] = 0.001
            rows.append(
                {
                    "probe_direction": direction,
                    "odd_input_measured_current_A": x.tolist(),
                    "odd_response_unscaled": y.tolist(),
                    "signed_inputs_measured_current_A": {
                        "-1": (-x).tolist(),
                        "1": x.tolist(),
                    },
                    "signed_responses_unscaled": {
                        "-1": (-y).tolist(),
                        "1": y.tolist(),
                    },
                    "development_signal_pass": True,
                }
            )
        cfg = {
            "required_development_rank": 4,
            "maximum_development_condition_number": 15.0,
            "tube_caps_unscaled": [
                0.003,
                0.003,
                0.01,
                0.01,
                1000.0,
                0.003,
                0.003,
                0.01,
                0.01,
                1000.0,
            ],
            "tube_residual_multiplier": 1.5,
        }
        result = S6.fit_cell(rows, cfg)
        self.assertEqual(result["rank"], 4)
        self.assertEqual(result["condition_number"], 1.0)
        self.assertTrue(result["rank_condition_pass"])
        self.assertTrue(result["tube_non_vacuous_pass"])
        self.assertTrue(result["passed"])

    def test_design_preserves_formal_contract_and_learning_veto(self):
        text = (
            ROOT
            / "docs/codex/reports/"
            "STAGE4_2R3C3T13S6_IMMEDIATE_EFFECT_REINTERPRETATION_DESIGN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("250/270 ms", text)
        self.assertIn("350/370 ms", text)
        self.assertIn("runs no controller, Ray, `gotsc`, TSC", text)
        self.assertIn("bounded\nresidual RL", text)


if __name__ == "__main__":
    unittest.main()
