from __future__ import annotations

import unittest

import numpy as np

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (
    NR1_1MS_HORIZON_STEPS,
    OneMsNR1SafetyEnvelope,
    assert_exact_slew,
    build_frozen_one_ms_prefixes,
    validate_one_ms_config,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError, RGeoZGeoSignal


class OneMsNR1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.turns = np.asarray([480.0] * 8 + [200.0] * 2 + [100.0] * 4)
        self.source = np.asarray([-72.9166708333, -93.7500041667, -93.7500041667, -72.9166708333,
                                  -93.7500041667, -93.7500041667, -66.6666708333, -66.6666708333,
                                  0.0, 0.0, -75.0, -135.00001, -82.0, -82.0])
        self.lower = np.full(14, -1000.0)
        self.upper = np.full(14, 1000.0)

    def test_config_is_exact_and_not_ten_ms(self) -> None:
        validate_one_ms_config(start_folder="1100ms", dt_ms=1, slew_a_per_ms=0.3)
        for kwargs in (
            {"start_folder": "1110ms", "dt_ms": 1, "slew_a_per_ms": 0.3},
            {"start_folder": "1100ms", "dt_ms": 10, "slew_a_per_ms": 0.3},
            {"start_folder": "1100ms", "dt_ms": 1, "slew_a_per_ms": 0.03},
        ):
            with self.assertRaises(ContractError):
                validate_one_ms_config(**kwargs)

    def test_all_coils_have_both_signed_nonzero_lattice_targets(self) -> None:
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=self.source,
            turns_tsc=self.turns,
            min_current_a_tsc=self.lower,
            max_current_a_tsc=self.upper,
        )
        self.assertEqual(set(frozen.prefixes), {"hold", "pattern_a", "pattern_b"})
        self.assertTrue(all(len(value) == NR1_1MS_HORIZON_STEPS for value in frozen.prefixes.values()))
        q0 = np.asarray(frozen.q0.current_a_tsc)
        a = np.asarray(frozen.prefixes["pattern_a"][0].current_a_tsc) - q0
        b = np.asarray(frozen.prefixes["pattern_b"][0].current_a_tsc) - q0
        self.assertTrue(np.all(a != 0.0))
        self.assertTrue(np.all(b != 0.0))
        self.assertTrue(np.all(np.sign(a) == -np.sign(b)))
        self.assertLessEqual(
            assert_exact_slew(q0, frozen.prefixes["pattern_a"][0].current_a_tsc, name="a"),
            0.3,
        )
        self.assertLessEqual(
            assert_exact_slew(q0, frozen.prefixes["pattern_b"][0].current_a_tsc, name="b"),
            0.3,
        )
        self.assertEqual(frozen.prefixes["pattern_a"][1:], (frozen.q0,) * 3)

    def test_source_readback_bias_cannot_be_hidden_by_q0_center(self) -> None:
        source = self.source.copy()
        source[11] = -135.00000999999997
        frozen = build_frozen_one_ms_prefixes(
            source_current_a_tsc=source,
            turns_tsc=self.turns,
            min_current_a_tsc=self.lower,
            max_current_a_tsc=self.upper,
        )
        for prefix in ("pattern_a", "pattern_b"):
            assert_exact_slew(
                source,
                frozen.prefixes[prefix][0].current_a_tsc,
                name=f"source_to_{prefix}",
            )

    def test_exact_point_three_is_allowed_and_any_excess_rejected(self) -> None:
        self.assertEqual(assert_exact_slew([0.0] * 14, [0.3] * 14, name="edge"), 0.3)
        with self.assertRaisesRegex(ContractError, "exceeds"):
            assert_exact_slew([0.0] * 14, [0.30000000000000004] * 14, name="over")

    def test_safety_uses_boundary_geometry_and_ip(self) -> None:
        state = {
            "time_ms": 1100,
            "Ip": 31000.0,
            "abnormal": False,
            "gfile": {
                "boundary_R": [0.55, 0.85, 0.85, 0.55],
                "boundary_Z": [-0.1, -0.1, 0.1, 0.1],
                "limiter_R": [0.4, 1.1, 1.1, 0.4],
                "limiter_Z": [-0.5, -0.5, 0.5, 0.5],
                "ip": 31000.0,
            },
        }
        signal = RGeoZGeoSignal.from_tsc_state(state)
        envelope = OneMsNR1SafetyEnvelope.from_signal(signal)
        self.assertEqual(envelope.state_reasons(signal, [0.0] * 14, self.lower, self.upper), ())


if __name__ == "__main__":
    unittest.main()
