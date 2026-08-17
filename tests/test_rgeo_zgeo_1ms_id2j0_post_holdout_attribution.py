import json
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2j0_post_holdout_attribution as stage


ROOT = Path(__file__).resolve().parents[1]


class ID2J0ContractTests(unittest.TestCase):
    def test_frozen_config_and_evidence_load(self):
        payload, cfg, targets, source = stage.load()
        self.assertEqual(payload["maximum_rollouts"], 16)
        self.assertEqual(payload["maximum_advance_attempts"], 544)
        self.assertEqual(payload["analysis"]["truth_recenter_periods_ms"], [1, 2, 4])
        self.assertEqual(payload["data_use"], "post_holdout_attribution_and_future_design_only")
        self.assertEqual(payload["id2c2_records_read"], 0)

    def test_single_replay_campaign_has_exact_old_history_matrix(self):
        payload, cfg, targets, source = stage.load()
        rows = stage.streams(payload, cfg, targets, source)
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({row["cell_id"] for row in rows}), 16)
        self.assertEqual({row["replay_index"] for row in rows}, {0})
        self.assertTrue(all(len(row["actions"]) == 34 for row in rows))
        self.assertTrue(all(max(action["maximum_issued_delta_a"] for action in row["actions"]) <= .3
                            for row in rows))

    def test_probe_issue_and_effect_are_not_shifted(self):
        payload = json.loads(stage.CONFIG.read_text(encoding="utf-8"))
        self.assertEqual({row["probe"]["issue_step"] for row in payload["groups"]}, {25})
        self.assertEqual(payload["analysis"]["probe_first_effect_state"], 26)
        self.assertEqual(payload["action_semantics"]["effect_state_index"], "issue_step_plus_one")

    def test_storage_budget_matches_single_replay_identity(self):
        payload = json.loads(stage.CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(payload["maximum_retained_states"], 16 * 35)
        self.assertEqual(payload["maximum_verified_plant_advances"], 16 * 34)
        self.assertEqual(payload["storage_gate"]["maximum_estimated_raw_bytes"], 40_000_000_000)

    def test_support_masks_cover_only_causal_frame(self):
        payload = json.loads(stage.CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(payload["analysis"]["causal_support_window_steps"], 16)
        self.assertEqual(payload["analysis"]["support_embeddings"],
                         ["full_tcn_features", "without_absolute_time", "action_history_only"])

    def test_route_tokens_keep_attribution_separate_from_pass(self):
        routes = json.loads(stage.CONFIG.read_text(encoding="utf-8"))["routes"]
        self.assertIn("MIXED_DATA_AND_STRUCTURED_MODEL_REQUIRED", routes["mixed"])
        self.assertNotIn("PASS", routes["mixed"])
        self.assertIn("ATTRIBUTE_ONLY", routes["data_pass"])

    def test_matched_prefix_detects_state_difference(self):
        common_state = {"r_geo_m": 1.0, "z_geo_m": 2.0, "r_mid_m": 3.0, "ip_a": 4.0,
                        "actual_current_decimal_a_tsc": ["0"] * 14, "wire_current_a": [0.0] * 48,
                        "artifact_sha256": {x: "x" for x in ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv")}}
        action = {"expected_card15_fields": ["0"] * 14}
        rows = []
        for kind in ("baseline", "probe"):
            rows.append({"group_id": "h00", "cell_kind": kind,
                         "states": [dict(common_state) for _ in range(26)],
                         "actions": [dict(action) for _ in range(25)]})
        self.assertTrue(stage._matched_prefix(rows)[0]["passed"])
        rows[1]["states"][25] = dict(common_state, ip_a=5.0)
        self.assertFalse(stage._matched_prefix(rows)[0]["passed"])


if __name__ == "__main__":
    unittest.main()
