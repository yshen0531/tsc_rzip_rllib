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
    / "stage4_2r3c3t9_pc3_mixed_interaction_preflight.py"
)
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t9_pc3_mixed_interaction_preflight_v1.json"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t9_pc3_mixed_interaction_preflight", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T9 preflight")
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class Stage42R3C3T9PreflightTests(unittest.TestCase):
    def test_frozen_design_is_exact_and_non_authorizing(self) -> None:
        design = json.loads(CONFIG.read_text(encoding="utf-8"))
        PREFLIGHT._validate_design(design)
        self.assertEqual(
            design["prospective_real_identification_contract"][
                "total_task_count"
            ],
            224,
        )
        self.assertFalse(
            design["scientific_scope"][
                "controller_implementation_authorized_by_preflight"
            ]
        )
        self.assertEqual(
            design["stress_composite_contract"]["factorial_signs"],
            [[1, 1], [1, -1], [-1, 1], [-1, -1]],
        )

    def test_factorial_common_amplitude_bounds_every_schedule(self) -> None:
        formal_hold = 35
        stress = np.zeros(formal_hold * 3)
        pc3 = np.zeros(formal_hold * 3)
        stress[0] = 1.0
        pc3[1] = 1.0
        amplitude, combinations = PREFLIGHT._factorial_common_amplitude(
            stress,
            pc3,
            formal_hold_step=formal_hold,
            delay_steps=0,
        )
        self.assertAlmostEqual(
            amplitude,
            min(
                PREFLIGHT.T6.FORMAL_L2_LIMIT / np.sqrt(2.0),
                PREFLIGHT.T6.COMPONENT_ABS_LIMIT,
            ),
        )
        for signs, combination in zip(
            PREFLIGHT.FACTORIAL_SIGNS, combinations
        ):
            payload = PREFLIGHT._factorial_probe_payload(
                stress_sign=signs[0],
                pc3_sign=signs[1],
                combination_unit_sum=combination,
                common_amplitude=amplitude,
                formal_hold_step=formal_hold,
                delay_steps=0,
            )
            self.assertLessEqual(
                payload["formal_l2_norm"],
                PREFLIGHT.T6.FORMAL_L2_LIMIT + 1.0e-15,
            )
            self.assertLessEqual(
                payload["formal_max_abs_component"],
                PREFLIGHT.T6.COMPONENT_ABS_LIMIT + 1.0e-15,
            )
            self.assertEqual(
                payload["first_cancellation_effect_state"], 39
            )
            self.assertLessEqual(
                max(abs(value) for value in payload["requested_full_net"]),
                PREFLIGHT.ZERO_NET_TOLERANCE,
            )

    def test_failure_stress_mean_is_recomputed_not_copied(self) -> None:
        design = json.loads(CONFIG.read_text(encoding="utf-8"))
        expected = np.asarray(
            design["stress_composite_contract"]["delay0_slew1p0"][
                "mean_coefficients"
            ],
            dtype=float,
        )
        rows = []
        for index in range(4):
            coefficients = expected.copy()
            coefficients[0] += -0.5 if index < 2 else 0.5
            rows.append(
                {
                    "actual_delay_steps": 0,
                    "actual_slew_scale": 1.0,
                    "scale_rows": [
                        {
                            "target_direction_scale": 1.0,
                            "passed": False,
                            "best_coefficients": coefficients.tolist(),
                        }
                    ],
                }
            )
        mean, count = PREFLIGHT._stress_coefficients(
            {"context_rows": rows},
            design,
            delay_steps=0,
            slew_scale=1.0,
        )
        np.testing.assert_allclose(mean, expected, atol=1.0e-15, rtol=0.0)
        self.assertEqual(count, 4)

    def test_factorial_walsh_signs_are_complete(self) -> None:
        signs = set(PREFLIGHT.FACTORIAL_SIGNS)
        self.assertEqual(
            signs, {(1, 1), (1, -1), (-1, 1), (-1, -1)}
        )
        self.assertEqual(
            sum(stress * pc3 for stress, pc3 in signs), 0
        )


if __name__ == "__main__":
    unittest.main()
