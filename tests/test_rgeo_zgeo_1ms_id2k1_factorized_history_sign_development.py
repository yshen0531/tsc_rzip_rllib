from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_id2k1_factorized_history_sign_development as stage


ROOT = Path(__file__).resolve().parents[1]


class ID2K1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(stage.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_evidence_and_budget_load(self) -> None:
        payload, cfg, targets, source = stage.load()
        self.assertEqual(payload["maximum_rollouts"], 43)
        self.assertEqual(payload["maximum_advance_attempts"], 43 * 34)
        self.assertEqual(payload["maximum_retained_states"], 43 * 35)
        self.assertEqual(payload["data_use"], "development_fit_only_after_all_gates_pass")
        self.assertEqual(payload["id2c2_records_read"], 0)
        self.assertEqual(payload["id2i1_or_id2j0_records_used_for_fit"], 0)

    def test_complete_eight_by_four_factor_matrix_and_three_replays(self) -> None:
        payload, cfg, targets, source = stage.load()
        rows = stage.campaign_streams(payload, cfg, targets, source)
        self.assertEqual(len(rows), 43)
        self.assertEqual(len({row["cell_id"] for row in rows}), 40)
        primary = [row for row in rows if row["replay_index"] == 0]
        self.assertEqual(len(primary), 40)
        for group in [f"h{i:02d}" for i in range(8)]:
            members = [row for row in primary if row["group_id"] == group]
            self.assertEqual(len(members), 5)
            self.assertEqual(sum(row["cell_kind"] == "baseline" for row in members), 1)
            probes = {(row["direction_id"], row["sign"]) for row in members if row["cell_kind"] == "probe"}
            self.assertEqual(probes, {("p04", "plus"), ("p04", "minus"),
                                      ("p07", "plus"), ("p07", "minus")})
        replayed = {row["cell_id"] for row in rows if row["replay_index"] == 1}
        self.assertEqual(replayed, set(payload["critical_replay_cells"]))

    def test_action_timing_and_slew_are_exact(self) -> None:
        payload, cfg, targets, source = stage.load()
        rows = stage.campaign_streams(payload, cfg, targets, source)
        self.assertTrue(all(len(row["actions"]) == 34 for row in rows))
        self.assertTrue(all(max(action["maximum_issued_delta_a"] for action in row["actions"]) <= 0.3
                            for row in rows))
        for row in rows:
            if row["cell_kind"] == "probe":
                self.assertEqual(row["probe_issue_step"], 25)
                self.assertEqual(row["probe_duration_issues"], 3)
                self.assertNotEqual(row["actions"][25]["expected_card15_fields"],
                                    row["actions"][24]["expected_card15_fields"])
                self.assertEqual(row["actions"][25]["expected_card15_fields"],
                                 row["actions"][27]["expected_card15_fields"])
                self.assertNotEqual(row["actions"][27]["expected_card15_fields"],
                                    row["actions"][28]["expected_card15_fields"])

    def test_data_gates_do_not_require_odd_symmetry_or_rank(self) -> None:
        gates = self.payload["data_gates"]
        self.assertTrue(gates["rank_condition_and_sign_asymmetry_are_descriptive_only"])
        self.assertEqual(gates["minimum_peak_paired_rz_norm_m"], 2e-5)
        self.assertEqual(gates["maximum_peak_paired_abs_ip_a"], 100.0)

    def test_routes_keep_data_pass_separate_from_control(self) -> None:
        self.assertTrue(self.payload["routes"]["pass"].endswith("STRUCTURED_MODEL_ONLY"))
        self.assertIn("not calibration", self.payload["claim_boundary"])
        self.assertIn("controller", self.payload["claim_boundary"])

    def test_launcher_has_server_only_identity_and_independent_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_id2k1_factorized_history_sign_development.sh").read_text(encoding="utf-8")
        self.assertIn("ID2K1_SOURCE_REVISION", text)
        self.assertIn("ID2K1_OUTPUT_DIR", text)
        self.assertIn("factorized_history_sign_development_independent.py", text)
        self.assertNotIn("rm -", text)


if __name__ == "__main__":
    unittest.main()
