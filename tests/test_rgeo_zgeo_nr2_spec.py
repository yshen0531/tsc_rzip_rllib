from __future__ import annotations

import unittest

import numpy as np

from tsc_rzip_rllib.control.rgeo_zgeo_nr2_spec import (
    NR2_SPLIT_PAIRS,
    build_nr2_specs,
    validate_nr2_specs,
)


class NR2SpecTests(unittest.TestCase):
    def test_counts_ranks_and_digest_are_deterministic(self) -> None:
        specs = build_nr2_specs()
        first = validate_nr2_specs(specs)
        second = validate_nr2_specs(build_nr2_specs())
        self.assertEqual(first, second)
        self.assertEqual(first["trajectory_count"], 60)
        self.assertEqual(first["plant_advances"], 480)
        self.assertEqual(first["splits"]["development"]["plant_advances"], 256)
        self.assertEqual(first["splits"]["calibration"]["plant_advances"], 96)
        self.assertEqual(first["splits"]["holdout"]["plant_advances"], 128)
        self.assertTrue(all(row["action_rank"] == 14 for row in first["splits"].values()))

    def test_every_pair_is_exact_negative_with_same_return_pattern(self) -> None:
        specs = build_nr2_specs()
        for split, pair_count in NR2_SPLIT_PAIRS.items():
            for pair_index in range(pair_count):
                plus = next(spec for spec in specs if spec.split == split and spec.pair_index == pair_index and spec.sign == 1)
                minus = next(spec for spec in specs if spec.split == split and spec.pair_index == pair_index and spec.sign == -1)
                np.testing.assert_array_equal(plus.normalized_actions_tsc, -np.asarray(minus.normalized_actions_tsc))
                self.assertEqual(plus.pulse_width, minus.pulse_width)
                self.assertEqual(plus.normalized_amplitude, minus.normalized_amplitude)
                self.assertTrue(any(not any(action) for action in plus.normalized_actions_tsc))


if __name__ == "__main__":
    unittest.main()
