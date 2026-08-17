import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ID2F1FrozenContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "configs/rgeo_zgeo_1ms_id2f1r1_repeated_context_development.json"
        cls.stage = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_frozen_config_hash_and_budget(self):
        self.assertEqual(
            hashlib.sha256(self.path.read_bytes()).hexdigest(),
            "2c97be4f3adbc684bcb7ed7782d76822e8071c919f92882e3141b3bf934e1831",
        )
        self.assertEqual(self.stage["unique_whole_history_cells"], 39)
        self.assertEqual(self.stage["replays_per_cell"], 2)
        self.assertEqual(self.stage["maximum_rollouts"], 78)
        self.assertEqual(self.stage["maximum_advance_attempts"], 78 * 34)
        self.assertEqual(self.stage["maximum_retained_states"], 78 * 35)

    def test_observability_and_data_roles(self):
        observed = self.stage["observability"]
        self.assertEqual(observed["current_same_step_r_geo_z_geo_ip"], "exact_noiseless_before_issue")
        self.assertEqual(observed["future_successor_before_issue"], "unknown")
        self.assertEqual(self.stage["id2c2_records_read"], 0)
        self.assertEqual(self.stage["calibration_use"], "forbidden")
        self.assertEqual(self.stage["blind_holdout_use"], "forbidden")

    def test_context_and_probe_matrix(self):
        self.assertEqual([row["context_id"] for row in self.stage["contexts"]],
                         ["none", "p04_plus_i18_d1", "p07_plus_i18_d1"])
        self.assertEqual(self.stage["probe_directions"], ["p04", "p07"])
        self.assertEqual(self.stage["probe_signs"], ["plus", "minus"])
        self.assertEqual(self.stage["probe_duration_issues"], [1, 2, 4])
        self.assertEqual(self.stage["probe_issue_step"], 22)

    def test_design_hash(self):
        design = ROOT / "docs/codex/reports/RGEO_ZGEO_1MS_ID2F1R1_REPEATED_CONTEXT_DEVELOPMENT_DESIGN.md"
        self.assertEqual(hashlib.sha256(design.read_bytes()).hexdigest(),
                         self.stage["evidence"]["design_sha256"])


class ID2F1ExecutableContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import (
            campaign_streams, clearance_required, lag_support, load,
        )
        cls.campaign_streams = staticmethod(campaign_streams)
        cls.clearance_required = staticmethod(clearance_required)
        cls.lag_support = staticmethod(lag_support)
        cls.stage, cls.cfg, cls.targets, cls.id2c1 = load(
            ROOT / "configs/rgeo_zgeo_1ms_id2f1r1_repeated_context_development.json"
        )
        cls.streams = campaign_streams(cls.stage, cls.cfg, cls.targets, cls.id2c1)

    def test_exact_campaign_shape_and_atomic_pairs(self):
        self.assertEqual(len(self.streams), 78)
        cells = {}
        for row in self.streams:
            cells.setdefault(row["cell_id"], []).append(row)
            self.assertEqual(len(row["targets"]), 34)
            self.assertEqual(len(row["actions"]), 34)
        self.assertEqual(len(cells), 39)
        self.assertTrue(all(sorted(item["replay_index"] for item in members) == [0, 1]
                            for members in cells.values()))

    def test_conditioner_and_probe_clearance_are_both_required(self):
        row = next(item for item in self.streams
                   if item["context_id"] == "p04_plus_i18_d1"
                   and item["direction_id"] == "p07" and item["sign"] == "minus"
                   and item["probe_duration_issues"] == 4)
        self.assertEqual(row["non_nominal_issue_steps"], [18, 22])
        self.assertTrue(self.clearance_required(18, row))
        self.assertTrue(self.clearance_required(22, row))
        self.assertFalse(self.clearance_required(19, row))

    def test_baseline_has_conditioner_but_no_probe(self):
        row = next(item for item in self.streams
                   if item["context_id"] == "p07_plus_i18_d1"
                   and item["cell_kind"] == "baseline")
        self.assertEqual(row["non_nominal_issue_steps"], [18])
        self.assertIsNone(row["probe_issue_step"])
        virtual = [action["probe_virtual_action"] for action in row["actions"]]
        self.assertEqual(virtual[18], [0.0, 1.0])
        self.assertEqual(virtual[19], [0.0, 0.0])

    def test_evaluator_cells_absent(self):
        self.assertFalse(any(row["probe_issue_step"] == 16 and row["probe_duration_issues"] == 1
                             for row in self.streams))

    def test_exact_action_semantics(self):
        for row in self.streams:
            for issue, action in enumerate(row["actions"]):
                self.assertEqual(action["issue_step"], issue)
                self.assertEqual(action["effect_state_index"], issue + 1)
                self.assertLessEqual(action["maximum_issued_delta_a"], 0.3)

    def test_lag_support_gate(self):
        support = self.lag_support(self.streams, 16)
        self.assertEqual(support["columns"], 32)
        self.assertEqual(support["rank"], 32)
        self.assertLessEqual(support["condition"], 100.0)


if __name__ == "__main__":
    unittest.main()
