from __future__ import annotations

import json
import unittest

import numpy as np

from tsc_rzip_rllib.control import (
    AdditiveResponseTube,
    AffineTransitionHypothesis,
    CausalRestartObserverState,
    DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC,
    QuantizedActuatorModel,
    SetValuedTransitionModel,
    T13S2R1_REPORT_SHA256,
)


class QuantizedActuatorTests(unittest.TestCase):
    def make_model(self, **updates):
        values = dict(
            minimum_current_a_tsc=(-10.0,) * 14,
            maximum_current_a_tsc=(10.0,) * 14,
            max_slew_step_a=1.0,
            turns_tsc=(100.0,) * 14,
        )
        values.update(updates)
        return QuantizedActuatorModel(**values)

    def test_exact_positive_negative_zero_card15_serialization(self):
        result = self.make_model(bias_grid_units_tsc=(0.0,) * 14).apply(
            (0.0,) * 14, (1.0, -1.0, 0.0) + (0.0,) * 11
        )
        self.assertEqual(result.card15_fields[:3], ("1.000E-01 ", "-1.000E-01", "0.000E+00 "))
        self.assertEqual(result.card15_target_current_a_tsc[:3], (1.0, -1.0, 0.0))
        self.assertTrue(all(len(value) == 10 for value in result.card15_fields))

    def test_action_and_current_clipping(self):
        result = self.make_model().apply((9.8,) * 14, (2.0,) * 14)
        self.assertTrue(all(result.action_saturated))
        self.assertTrue(all(result.current_limit_clipped))
        self.assertEqual(result.desired_current_a_tsc, (10.0,) * 14)

    def test_active_command_can_collapse_to_grid(self):
        result = self.make_model(
            max_slew_step_a=1e-7, bias_grid_units_tsc=(0.0,) * 14
        ).apply((1.0,) * 14, (1.0,) * 14)
        self.assertTrue(all(result.active_command_collapsed_to_grid))

    def test_development_bias_and_nonzero_interval(self):
        result = self.make_model().apply((0.0,) * 14, (0.0,) * 14)
        expected = tuple(-value * 1e-5 for value in DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC)
        np.testing.assert_allclose(result.nominal_readback_current_a_tsc, expected, atol=0.0)
        self.assertTrue(all(lo < hi for lo, hi in zip(result.readback_lower_a_tsc, result.readback_upper_a_tsc)))
        self.assertEqual(dict(result.provenance)["bias_source_report_sha256"], T13S2R1_REPORT_SHA256)

    def test_interval_contains_all_bias_radius_edges(self):
        result = self.make_model(uncertainty_radius_grid_units_tsc=(2.0,) * 14).apply(
            (0.0,) * 14, (0.0,) * 14
        )
        for target, nominal, lower, upper in zip(
            result.card15_target_current_a_tsc,
            result.nominal_readback_current_a_tsc,
            result.readback_lower_a_tsc,
            result.readback_upper_a_tsc,
        ):
            self.assertLessEqual(lower, nominal)
            self.assertLessEqual(nominal, upper)
            self.assertLessEqual(lower, target)
            self.assertLessEqual(target, upper)

    def test_uncertainty_cannot_collapse(self):
        with self.assertRaisesRegex(ValueError, "at least one grid unit"):
            self.make_model(uncertainty_radius_grid_units_tsc=(0.0,) * 14)


class CausalObserverTests(unittest.TestCase):
    def restart_payload(self):
        return {
            "formal_task_step": 20,
            "target_rzip": [1.8, 0.0, -900000.0],
            "restart_measurement_rzip": [1.7, -0.1, -880000.0],
            "measured_coil_current_a_tsc": [0.0] * 14,
            "authenticated_delay_queue_norm_tsc": [[0.0] * 14],
            "previous_correction": [0.0] * 3,
            "integral_state": [0.0] * 3,
            "actuator_hypothesis_ids": ["quantized_bias_plus_tube"],
            "plant_response_tube_lower": [-0.01] * 5,
            "plant_response_tube_upper": [0.01] * 5,
            "provenance_hashes": {"snapshot": "abc", "source": "def"},
            "unknown_velocity_bound_mps": 1.0,
        }

    def test_restart_velocity_is_explicitly_unknown(self):
        state = CausalRestartObserverState.from_restart_mapping(self.restart_payload())
        self.assertEqual(state.velocity.status, "unknown_interval")
        self.assertEqual(state.velocity.lower_mps, (-1.0, -1.0))
        self.assertEqual(state.issued_commands_norm_tsc, ())

    def test_causal_update_and_queue_immutability(self):
        state = CausalRestartObserverState.from_restart_mapping(self.restart_payload())
        old_queue = state.authenticated_delay_queue_norm_tsc
        advanced = state.advance_from_mapping(
            {
                "next_measurement_rzip": [1.702, -0.099, -881000.0],
                "measured_coil_current_a_tsc": [1.0] * 14,
                "issued_command_norm_tsc": [0.1] * 14,
                "authenticated_delay_queue_norm_tsc": [[0.1] * 14],
                "dt_seconds": 0.01,
                "finite_difference_uncertainty_mps": 0.02,
            }
        )
        self.assertEqual(advanced.formal_task_step, 21)
        self.assertEqual(advanced.velocity.status, "finite_difference")
        np.testing.assert_allclose(advanced.velocity.value_mps, [0.2, 0.1])
        self.assertEqual(state.authenticated_delay_queue_norm_tsc, old_queue)
        self.assertNotEqual(advanced.authenticated_delay_queue_norm_tsc, old_queue)

    def test_forbidden_and_unknown_fields_fail_closed(self):
        for field in ("history_label", "wire_current", "future_schedule", "mystery"):
            payload = self.restart_payload()
            payload[field] = 1
            with self.assertRaises(ValueError):
                CausalRestartObserverState.from_restart_mapping(payload)

    def test_deterministic_json_serialization(self):
        state = CausalRestartObserverState.from_restart_mapping(self.restart_payload())
        first = json.dumps(state.to_dict(), sort_keys=True, allow_nan=False)
        second = json.dumps(state.to_dict(), sort_keys=True, allow_nan=False)
        self.assertEqual(first, second)
        self.assertEqual(
            CausalRestartObserverState.from_dict(json.loads(first)), state
        )


class TransitionTubeTests(unittest.TestCase):
    def hypothesis(self, identifier, offset):
        return AffineTransitionHypothesis(
            hypothesis_id=identifier,
            state_matrix=((1.0, 0.0), (0.0, 1.0)),
            action_matrix=((1.0,), (0.0,)),
            offset=(offset, 0.0),
            interpolation_state_lower=(-1.0, -1.0),
            interpolation_state_upper=(1.0, 1.0),
            interpolation_action_lower=(-1.0,),
            interpolation_action_upper=(1.0,),
            extrapolation_state_lower=(-3.0, -3.0),
            extrapolation_state_upper=(3.0, 3.0),
            extrapolation_action_lower=(-2.0,),
            extrapolation_action_upper=(2.0,),
            measured_state_action_points=((0.0, 0.0, 0.0),),
            provenance=(("fit", identifier),),
        )

    def model(self):
        return SetValuedTransitionModel(
            hypotheses=(self.hypothesis("low", -0.1), self.hypothesis("high", 0.1)),
            additive_tube=AdditiveResponseTube(
                lower=(-0.01, -0.02),
                upper=(0.01, 0.02),
                provenance=(("tube", "prospective"),),
            ),
            actuator_provenance=(("actuator", "quantized"),),
        )

    def test_multiple_hypothesis_union_and_formal_clock(self):
        result = self.model().predict_from_mapping(
            {"formal_task_step": 20, "initial_state": [0.0, 0.0], "action_sequence": [[0.0]]}
        )
        self.assertEqual(result.formal_task_steps, (21,))
        self.assertAlmostEqual(result.lower[0][0], -0.11)
        self.assertAlmostEqual(result.upper[0][0], 0.11)
        self.assertFalse(result.point_model_certified)
        self.assertFalse(result.robust_controller_authorized)

    def test_measured_interpolation_and_extrapolation_classes(self):
        model = self.model()
        measured = model.predict_from_mapping(
            {"formal_task_step": 0, "initial_state": [0.0, 0.0], "action_sequence": [[0.0]]}
        )
        interpolation = model.predict_from_mapping(
            {"formal_task_step": 0, "initial_state": [0.2, 0.0], "action_sequence": [[0.0]]}
        )
        extrapolation = model.predict_from_mapping(
            {"formal_task_step": 0, "initial_state": [2.0, 0.0], "action_sequence": [[0.0]]}
        )
        self.assertEqual(measured.support_class, "measured")
        self.assertEqual(interpolation.support_class, "interpolation")
        self.assertEqual(extrapolation.support_class, "extrapolation")

    def test_empty_or_unsupported_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            SetValuedTransitionModel(
                hypotheses=(),
                additive_tube=AdditiveResponseTube(
                    lower=(-0.1,), upper=(0.1,), provenance=(("tube", "x"),)
                ),
                actuator_provenance=(("actuator", "x"),),
            )
        with self.assertRaisesRegex(ValueError, "unsupported"):
            self.model().predict_from_mapping(
                {"formal_task_step": 0, "initial_state": [4.0, 0.0], "action_sequence": [[0.0]]}
            )

    def test_transition_forbidden_label_and_unknown_field_rejection(self):
        with self.assertRaises(ValueError):
            self.model().predict_from_mapping(
                {
                    "formal_task_step": 0,
                    "initial_state": [0.0, 0.0],
                    "action_sequence": [[0.0]],
                    "pair_id": "forbidden",
                }
            )

    def test_prediction_serialization_is_deterministic(self):
        result = self.model().predict_from_mapping(
            {"formal_task_step": 5, "initial_state": [0.0, 0.0], "action_sequence": [[0.0]]}
        )
        first = json.dumps(result.to_dict(), sort_keys=True, allow_nan=False)
        second = json.dumps(result.to_dict(), sort_keys=True, allow_nan=False)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
