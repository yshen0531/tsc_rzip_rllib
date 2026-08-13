from __future__ import annotations

from decimal import Decimal
import unittest

import numpy as np

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import (
    assert_exact_slew,
    card15_target_decimal_a,
)
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_spec import (
    NR2_1MS_HORIZON_STEPS,
    NR2_1MS_SPLIT_PAIRS,
    build_one_ms_nr2_specs,
    build_one_ms_nr2_targets,
    validate_one_ms_nr2_specs,
)


class OneMsNR2SpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.turns = np.asarray([480.0] * 8 + [200.0] * 2 + [100.0] * 4)
        self.source = np.asarray(
            [-72.9166708333, -93.7500041667, -93.7500041667, -72.9166708333,
             -93.7500041667, -93.7500041667, -66.6666708333, -66.6666708333,
             0.0, 0.0, -75.0, -135.00001, -82.0, -82.0]
        )

    def test_count_schedules_pairs_rank_and_digest(self) -> None:
        specs = build_one_ms_nr2_specs()
        self.assertEqual(len(specs), 36)
        self.assertTrue(all(len(value.schedule) == NR2_1MS_HORIZON_STEPS for value in specs))
        self.assertEqual(
            {name: sum(value.split == name for value in specs) for name in NR2_1MS_SPLIT_PAIRS},
            {"development": 20, "calibration": 8, "holdout": 8},
        )
        gate = validate_one_ms_nr2_specs(
            specs, source_current_a_tsc=self.source, turns_tsc=self.turns
        )
        self.assertEqual(gate["plant_advances"], 576)
        self.assertEqual(
            gate["action_stream_sha256"],
            "5fb7533a2c656f824f34f168285412a16a75b1fa5aec19dec142ed51830c0ada",
        )
        self.assertEqual(
            {name: row["quantized_action_rank"] for name, row in gate["splits"].items()},
            {"development": 14, "calibration": 14, "holdout": 14},
        )

    def test_every_command_transition_is_exactly_bounded(self) -> None:
        for spec in build_one_ms_nr2_specs():
            targets = build_one_ms_nr2_targets(
                spec, source_current_a_tsc=self.source, turns_tsc=self.turns
            )
            previous = card15_target_decimal_a(targets[0], self.turns, name="q0")
            self.assertTrue(all(value == Decimal("0") for value in (
                current - center for current, center in zip(previous, previous)
            )))
            for target in targets[1:]:
                current = card15_target_decimal_a(target, self.turns, name="target")
                self.assertLessEqual(assert_exact_slew(previous, current, name="command"), 0.3)
                previous = current

    def test_schedule_types_have_frozen_nonzero_counts(self) -> None:
        one_each = {}
        for spec in build_one_ms_nr2_specs():
            one_each.setdefault(spec.schedule_type, spec)
        expected = {"impulse": 4, "dwell": 8, "switch": 12}
        for kind, spec in one_each.items():
            self.assertEqual(sum(amplitude != "zero" for amplitude, _ in spec.schedule), expected[kind])


if __name__ == "__main__":
    unittest.main()
