from __future__ import annotations

import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s6_independent_raw_audit as audit,
)


class Stage42R3C3T13S6IndependentRawAuditTests(unittest.TestCase):
    def test_server_layout_uses_run_level_environment_variants(self) -> None:
        source = audit.Path(audit.__file__).read_text(encoding="utf-8")
        self.assertIn('run_dir / "stage4_2r3c3t13s5_environment_variants"', source)
        self.assertNotIn('"stage4_2r3c3t13s5_lattice_native_split_holdout" / "variants"', source)

    def test_feature_arrays_use_causal_backward_velocity(self) -> None:
        result = {
            "trajectory": [
                {"R": 1.0, "Z": 2.0, "Ip": 3.0},
                {"R": 1.1, "Z": 1.8, "Ip": 4.0},
                {"R": 1.4, "Z": 1.9, "Ip": 5.0},
            ]
        }
        actual = audit._feature_arrays(result, 0.1)
        expected = np.asarray(
            [
                [1.0, 2.0, 0.0, 0.0, 3.0],
                [1.1, 1.8, 1.0, -2.0, 4.0],
                [1.4, 1.9, 3.0, 1.0, 5.0],
            ]
        )
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-14)

    def test_target_symmetry_uses_exact_decimal_card_fields(self) -> None:
        def result(field: str) -> dict:
            return {
                "controller_trace": [
                    {
                        "r3c3t13s5_lattice_event": "issue",
                        "r3c3t13s5_actuator_prediction": {
                            "card15_fields": [field]
                        },
                        "r3c3t13s5_center_card15_fields": ["1.000E+00"],
                    }
                ]
            }

        self.assertTrue(audit._target_symmetry(result("1.001E+00"), result("9.990E-01")))
        self.assertFalse(audit._target_symmetry(result("1.002E+00"), result("9.990E-01")))

    def test_fit_and_validation_reproduce_exact_linear_cell(self) -> None:
        cfg = {
            "tube_caps_unscaled": [1.0] * 10,
            "tube_residual_multiplier": 1.5,
            "response_scales": [0.03, 0.03, 0.1, 0.1, 2000.0],
            "maximum_holdout_scaled_center_relative_error": 0.1,
        }
        matrix = np.zeros((28, 10))
        matrix[:4, :4] = np.eye(4)
        rows = []
        for index, direction in enumerate(audit.DIRECTIONS):
            x = np.zeros(28)
            x[index] = 1.0
            y = x @ matrix
            rows.append(
                {
                    "offline_role": "development",
                    "stratum": "easy",
                    "probe_window": "transport",
                    "probe_direction": direction,
                    "development_signal": True,
                    "odd_input": x,
                    "odd_output": y,
                    "signed_inputs": {-1: -x, 1: x},
                    "signed_outputs": {-1: -y, 1: y},
                    "pre_pass": True,
                }
            )
        duplicated = []
        for stratum in ("easy", "hard"):
            for window in audit.WINDOWS:
                for row in rows:
                    copied = dict(row)
                    copied["stratum"] = stratum
                    copied["probe_window"] = window
                    duplicated.append(copied)
        models = audit._fit_models(duplicated, cfg)
        self.assertEqual(len(models), 4)
        self.assertTrue(all(model["rank"] == 4 for model in models.values()))
        holdout = []
        for row in duplicated:
            copied = dict(row)
            copied["offline_role"] = "blind_holdout"
            holdout.append(copied)
        validation = audit._validation_rows(holdout, models, cfg)
        self.assertEqual(len(validation), 32)
        self.assertTrue(all(row["componentwise_contained"] for row in validation))
        self.assertTrue(all(row["scaled_center_relative_error_pass"] for row in validation))


if __name__ == "__main__":
    unittest.main()
