from __future__ import annotations

import copy
import unittest

import numpy as np

from tsc_rzip_rllib.control.rgeo_zgeo_contract import (
    BoundaryBoxGeometry,
    LimiterMidplaneGeometry,
    RGeoZGeoSignal,
)
from tsc_rzip_rllib.control.rgeo_zgeo_nr1 import (
    NR1SafetyEnvelope,
    build_frozen_prefixes,
    compare_replay_records,
    quantize_card15_target,
)


class NR1ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.turns = np.asarray([480.0] * 8 + [200.0] * 2 + [100.0] * 4)
        self.initial = np.linspace(-100.0, 100.0, 14)
        boundary = BoundaryBoxGeometry.from_paired_points(
            time_ms=1100,
            r_boundary_m=[0.55, 0.85, 0.85, 0.55],
            z_boundary_m=[-0.1, -0.1, 0.1, 0.1],
        )
        limiter = LimiterMidplaneGeometry(midplane_z_m=0.0, r_inner_m=0.39, r_outer_m=1.19)
        self.signal = RGeoZGeoSignal(boundary=boundary, limiter=limiter, ip_a=31_000.0)
        self.envelope = NR1SafetyEnvelope.from_source_signal(self.signal)
        self.lower = np.full(14, -400.0)
        self.upper = np.full(14, 400.0)

    def test_card15_quantization_is_explicit_and_invertible(self) -> None:
        target = quantize_card15_target(self.initial, self.turns)
        self.assertEqual(len(target.serialized_card15_fields), 14)
        self.assertTrue(all(len(value) == 10 for value in target.serialized_card15_fields))
        expected = np.asarray([float(value.strip()) for value in target.serialized_card15_fields])
        expected = expected * 1000.0 / self.turns
        np.testing.assert_array_equal(target.quantized_current_a_tsc, expected)

    def test_frozen_prefixes_have_only_declared_actions(self) -> None:
        prefixes = build_frozen_prefixes(
            initial_current_a_tsc=self.initial,
            turns_tsc=self.turns,
            max_delta_current_a_per_step=3.0,
        )
        self.assertEqual(set(prefixes), {"hold", "pulse"})
        self.assertEqual(len(prefixes["hold"].targets), 8)
        self.assertEqual(len(prefixes["pulse"].targets), 8)
        self.assertEqual(prefixes["pulse"].targets[1:], prefixes["hold"].targets[1:])
        pulse = np.asarray(prefixes["pulse"].targets[0].quantized_current_a_tsc)
        center = np.asarray(prefixes["hold"].targets[0].quantized_current_a_tsc)
        self.assertLessEqual(float(np.max(np.abs(pulse - center))), 0.15 + 1e-9)
        self.assertGreater(float(np.max(np.abs(pulse - center))), 0.0)

    def test_safety_accepts_source_and_small_target(self) -> None:
        self.assertEqual(
            self.envelope.state_reasons(
                signal=self.signal,
                actual_current_a_tsc=self.initial,
                min_current_a_tsc=self.lower,
                max_current_a_tsc=self.upper,
            ),
            (),
        )
        self.assertEqual(
            self.envelope.target_reasons(
                actual_current_a_tsc=self.initial,
                target_current_a_tsc=self.initial + 0.1,
                min_current_a_tsc=self.lower,
                max_current_a_tsc=self.upper,
                max_delta_current_a_per_step=3.0,
            ),
            (),
        )

    def test_safety_fails_closed_on_each_campaign_axis(self) -> None:
        shifted_boundary = BoundaryBoxGeometry(
            time_ms=1110,
            point_count=4,
            r_boundary_min_m=0.61,
            r_boundary_max_m=0.91,
            z_boundary_min_m=-0.1,
            z_boundary_max_m=0.1,
        )
        shifted = RGeoZGeoSignal(
            boundary=shifted_boundary,
            limiter=self.signal.limiter,
            ip_a=27_000.0,
        )
        reasons = self.envelope.state_reasons(
            signal=shifted,
            actual_current_a_tsc=np.full(14, 401.0),
            min_current_a_tsc=self.lower,
            max_current_a_tsc=self.upper,
        )
        self.assertIn("R_GEO_CAMPAIGN_LIMIT", reasons)
        self.assertIn("IP_CAMPAIGN_LIMIT", reasons)
        self.assertIn("ACTUAL_CURRENT_LIMIT", reasons)
        target_reasons = self.envelope.target_reasons(
            actual_current_a_tsc=self.initial,
            target_current_a_tsc=self.initial + 3.1,
            min_current_a_tsc=self.lower,
            max_current_a_tsc=self.upper,
            max_delta_current_a_per_step=3.0,
        )
        self.assertIn("TARGET_SLEW_LIMIT", target_reasons)

    def test_replay_comparison_checks_parsed_state_and_targets(self) -> None:
        record = {
            "time_ms": 1100,
            "r_geo_m": 0.7,
            "z_geo_m": 0.0,
            "r_mid_m": 0.79,
            "ip_a": 31_000.0,
            "actual_current_a_tsc": [0.0] * 14,
            "wire_current_a": [1.0, -1.0],
            "target_card15_fields": ["0.000E+00 "] * 14,
        }
        self.assertTrue(compare_replay_records([record], [copy.deepcopy(record)])["passed"])
        mismatch = copy.deepcopy(record)
        mismatch["wire_current_a"][1] += 1e-6
        result = compare_replay_records([record], [mismatch])
        self.assertFalse(result["passed"])
        self.assertIn("WIRE_CURRENT_TOLERANCE", result["reasons"])


if __name__ == "__main__":
    unittest.main()
