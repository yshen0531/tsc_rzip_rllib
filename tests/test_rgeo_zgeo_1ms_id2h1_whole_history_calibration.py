from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2h1_whole_history_calibration as h1


class ID2H1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.config = json.loads((cls.root / "configs/rgeo_zgeo_1ms_id2h1_whole_history_calibration.json").read_text(encoding="utf-8"))

    def test_budget_data_roles_and_group_order_are_frozen(self) -> None:
        stage = self.config
        self.assertEqual((stage["whole_history_groups"], stage["cells_per_group"], stage["replays_per_cell"]), (10, 2, 2))
        self.assertEqual((stage["maximum_rollouts"], stage["maximum_advance_attempts"], stage["maximum_retained_states"]), (40, 1360, 1400))
        self.assertEqual([row["group_id"] for row in stage["groups"]], [f"c{i:02d}" for i in range(10)])
        self.assertEqual(stage["model_fit_retrain_tune_or_select_use"], "forbidden")
        self.assertEqual(stage["blind_holdout_use"], "forbidden")
        self.assertEqual(stage["id2c2_records_read"], 0)

    def test_probe_matrix_is_balanced_and_contexts_are_distinct(self) -> None:
        probes = [row["probe"] for row in self.config["groups"]]
        self.assertEqual(sum(row["direction"] == "p04" for row in probes), 5)
        self.assertEqual(sum(row["direction"] == "p07" for row in probes), 5)
        self.assertEqual(sum(row["sign"] == "plus" for row in probes), 5)
        self.assertEqual(sum(row["sign"] == "minus" for row in probes), 5)
        self.assertEqual(sorted(row["duration_issues"] for row in probes), [1, 1, 2, 2, 2, 2, 4, 4, 4, 4])
        signatures = {json.dumps(row["conditioners"], sort_keys=True) for row in self.config["groups"]}
        self.assertEqual(len(signatures), 10)

    def test_calibration_is_group_max_not_step_quantile(self) -> None:
        calibration = self.config["calibration"]
        self.assertEqual(calibration["statistical_unit"], "whole_conditioner_group")
        self.assertEqual(calibration["finite_sample_order_index_one_based"], 10)
        self.assertEqual(calibration["absolute_error_state_range_inclusive"], [17, 34])
        self.assertEqual(calibration["paired_response_state_range_inclusive"], [23, 34])
        self.assertEqual(calibration["model_or_feature_update"], "forbidden")

    def test_calibration_metric_uses_tenth_order_statistic(self) -> None:
        class FakeCell:
            def __init__(self, cell_id: str, context_id: str, kind: str, offset: float):
                self.cell_id = cell_id
                self.context_id = context_id
                self.cell_kind = kind
                self.states = np.zeros((35, 3), dtype=float)
                self.states[17:, 0] = offset

        class FakeMember:
            def recursive(self, cell, data, origin=16):
                return np.zeros((18, 3), dtype=float)

        cells = []
        for index in range(10):
            cells.append(FakeCell(f"c{index:02d}__baseline", f"c{index:02d}", "baseline", (index + 1) * 1e-5))
            cells.append(FakeCell(f"c{index:02d}__probe", f"c{index:02d}", "probe", (index + 1) * 1e-5 + 1e-6))
        data = type("Data", (), {"response_scale": np.asarray([1e-4, 1e-4, 25.0])})()
        metrics = h1.calibration_metrics(self.config, cells, data, [FakeMember()] * 3)
        self.assertAlmostEqual(metrics["simultaneous_absolute_recursive_half_width"][0], 1.01e-4)
        self.assertEqual(metrics["finite_sample_order_index_one_based"], 10)

    def test_routes_do_not_authorize_control(self) -> None:
        self.assertTrue(self.config["routes"]["pass"].endswith("BLIND_HOLDOUT_DESIGN_ONLY"))
        self.assertIn("not a blind holdout", self.config["claim_boundary"])
        self.assertIn("controller", self.config["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
