from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout as i1


class ID2I1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.config = json.loads((cls.root / "configs/rgeo_zgeo_1ms_id2i1_blind_whole_history_holdout.json").read_text(encoding="utf-8"))

    def test_budget_and_blind_data_role_are_frozen(self) -> None:
        stage = self.config
        self.assertEqual((stage["whole_history_groups"], stage["cells_per_group"], stage["replays_per_cell"]), (8, 2, 2))
        self.assertEqual((stage["maximum_rollouts"], stage["maximum_advance_attempts"], stage["maximum_retained_states"]), (32, 1088, 1120))
        self.assertEqual(stage["data_use"], "blind_evaluation_only")
        self.assertEqual(stage["model_fit_retrain_tune_select_or_recalibrate_use"], "forbidden")
        self.assertEqual(stage["id2c2_records_read"], 0)

    def test_group_matrix_is_new_balanced_and_nonoverlapping(self) -> None:
        groups = self.config["groups"]
        self.assertEqual([row["group_id"] for row in groups], [f"h{i:02d}" for i in range(8)])
        probes = [row["probe"] for row in groups]
        self.assertTrue(all(row["issue_step"] == 25 for row in probes))
        self.assertEqual(sum(row["direction"] == "p04" for row in probes), 4)
        self.assertEqual(sum(row["direction"] == "p07" for row in probes), 4)
        self.assertEqual(sum(row["sign"] == "plus" for row in probes), 4)
        self.assertEqual(sum(row["sign"] == "minus" for row in probes), 4)
        self.assertEqual(sorted(row["duration_issues"] for row in probes), [1, 1, 2, 2, 3, 3, 3, 3])
        for group in groups:
            occupied = set()
            for event in [*group["conditioners"], group["probe"]]:
                steps = set(range(event["issue_step"], event["issue_step"] + event["duration_issues"]))
                self.assertFalse(occupied & steps)
                occupied |= steps

    def test_calibrated_widths_are_exactly_frozen(self) -> None:
        holdout = self.config["holdout"]
        self.assertEqual(holdout["frozen_absolute_recursive_half_width"], [0.0005936422508353578, 0.00024051138515601006, 24.0476938080501])
        self.assertEqual(holdout["frozen_paired_response_half_width"], [0.0006950692585707685, 0.00023825926428221178, 7.717859491567651])
        self.assertEqual(holdout["minimum_joint_contained_groups"], 7)
        self.assertEqual(holdout["paired_response_state_range_inclusive"], [26, 34])
        self.assertEqual(holdout["model_width_or_feature_update"], "forbidden")

    def test_holdout_uses_atomic_group_coverage(self) -> None:
        class FakeCell:
            def __init__(self, cell_id: str, context_id: str, kind: str, offset: float):
                self.cell_id = cell_id
                self.context_id = context_id
                self.cell_kind = kind
                self.states = np.zeros((35, 3), dtype=float)
                self.prediction = np.zeros((18, 3), dtype=float)
                self.states[17:, 0] = offset
                if kind == "probe":
                    self.states[26:, 0] += 1e-4
                    self.prediction[9:, 0] += 1e-4

        class FakeMember:
            def recursive(self, cell, data, origin=16):
                return cell.prediction.copy()

        cells = []
        for index in range(8):
            offset = 0.0006 if index == 7 else 0.0
            cells.append(FakeCell(f"h{index:02d}__baseline", f"h{index:02d}", "baseline", offset))
            cells.append(FakeCell(f"h{index:02d}__probe", f"h{index:02d}", "probe", offset))
        data = type("Data", (), {"response_scale": np.asarray([1e-4, 1e-4, 25.0])})()
        metrics = i1.holdout_metrics(self.config, cells, data, [FakeMember()] * 3)
        self.assertEqual(metrics["joint_width_contained_groups"], 7)
        self.assertEqual(metrics["positive_peak_direction_groups"], 8)
        self.assertTrue(metrics["gate_passes"]["joint_calibrated_width_coverage"])
        self.assertTrue(metrics["passed"])

    def test_pass_authorizes_design_not_controller(self) -> None:
        self.assertTrue(self.config["routes"]["pass"].endswith("CONTROLLER_SAFETY_DESIGN_ONLY"))
        self.assertIn("not a transition tube", self.config["claim_boundary"])
        self.assertIn("controller", self.config["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
