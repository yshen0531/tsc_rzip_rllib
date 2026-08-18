from __future__ import annotations

import copy
import unittest

from scripts import rgeo_zgeo_1ms_id2s2_sequence_exact_replay as s2
from scripts import rgeo_zgeo_1ms_id2s2_sequence_exact_replay_independent as s2a


class ID2S2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (cls.stage, cls.cfg, cls.targets, cls.source, cls.baseline,
         cls.frozen_s0, cls.originals) = s2.load()
        cls.streams = s2.campaign_streams(
            cls.stage, cls.cfg, cls.targets, cls.source, cls.frozen_s0, cls.originals)

    def _synthetic_exact_rows(self):
        rows = []
        for stream in self.streams:
            row = copy.deepcopy(self.originals[stream["sequence_id"]])
            row.update({key: copy.deepcopy(value) for key, value in stream.items()
                        if key not in ("targets", "actions")})
            row["actions"] = copy.deepcopy(stream["actions"])
            row["passed"] = True
            rows.append(row)
        return rows

    def test_frozen_identity_and_budget(self):
        self.assertEqual([row["sequence_id"] for row in self.streams],
                         self.stage["sequence_ids"])
        self.assertEqual([row["rollout_id"] for row in self.streams],
                         self.stage["rollout_ids"])
        self.assertEqual((self.stage["maximum_rollouts"], self.stage["maximum_reset_calls"]),
                         (4, 4))
        self.assertEqual((self.stage["maximum_advance_attempts"],
                          self.stage["maximum_gotsc_calls"],
                          self.stage["maximum_verified_plant_advances"]),
                         (136, 136, 136))
        self.assertEqual((self.stage["maximum_retained_states"],
                          self.stage["required_artifact_files_if_complete"]), (140, 700))

    def test_no_new_action_timing_history_or_sequence_cell(self):
        self.assertEqual(self.stage["new_action_timing_history_or_sequence_cells"], 0)
        for stream in self.streams:
            original = self.originals[stream["sequence_id"]]
            self.assertEqual(stream["actions"], original["actions"])
            self.assertEqual(len(stream["actions"]), 34)
            self.assertLessEqual(max(float(row["maximum_issued_delta_a"])
                                     for row in stream["actions"]), 0.3)

    def test_issue_zero_preserves_authentic_source_to_q0_slew(self):
        for stream in self.streams:
            self.assertEqual(stream["actions"][0]["maximum_issued_delta_a"], 1e-5)

    def test_offline_preflight_is_zero_plant(self):
        result = s2.offline(s2.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual((result["reset_calls"], result["advance_attempts"],
                          result["plant_advance_gotsc_calls"],
                          result["verified_plant_advances"]), (0, 0, 0, 0))
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_rows_pass_prefix_replay_response_and_metrics(self):
        rows = self._synthetic_exact_rows()
        prefixes = s2.s1.matched_prefix_checks(rows, self.baseline)
        replays = s2.replay_checks(rows, self.originals, self.stage)
        responses = s2.response_checks(rows, self.originals, self.baseline, self.stage)
        self.assertTrue(all(row["passed"] for row in prefixes + replays + responses))
        s1_stage = s2._json(s2.ROOT / self.stage["evidence"]["id2s1_config"]["path"])
        metrics = s2.s1.measured_metrics(rows, self.baseline, self.frozen_s0, s1_stage)
        original = s2._json(s2.ROOT / self.stage["evidence"]["id2s1_result"]["path"])
        self.assertEqual(metrics, original["measured_sequence_metrics"])

    def test_replay_change_fails(self):
        rows = self._synthetic_exact_rows()
        rows[0]["states"][29]["r_geo_m"] += 2e-12
        self.assertFalse(s2.replay_checks(rows, self.originals, self.stage)[0]["passed"])
        self.assertFalse(s2.response_checks(
            rows, self.originals, self.baseline, self.stage)[0]["passed"])

    def test_raw_audit_excludes_outgoing_inputa_from_state_hash_comparison(self):
        rows = self._synthetic_exact_rows()
        for row in rows:
            for state in row["states"][:-1]:
                state["artifact_sha256"]["inputa"] = "outgoing-inputa-rewrite"
        self.assertTrue(all(check["passed"] for check in
                            s2a.raw_replay_checks(rows, self.originals, self.stage)))
        rows[0]["states"][0]["artifact_sha256"]["geqdsk"] = "changed"
        self.assertFalse(s2a.raw_replay_checks(rows, self.originals, self.stage)[0]["passed"])

    def test_data_use_and_claim_boundary(self):
        self.assertEqual(self.stage["data_use"],
                         "repeatability_and_route_decision_only_zero_fit_weight")
        self.assertEqual(self.stage["fit_calibration_holdout_controller_expert_or_rl_use"],
                         "forbidden")
        self.assertIn("no probabilistic tube", self.stage["claim_boundary"])

    def test_storage_reserve_is_frozen(self):
        gate = self.stage["storage_gate"]
        self.assertEqual((gate["minimum_free_bytes_before_run"],
                          gate["maximum_estimated_raw_bytes"],
                          gate["minimum_free_bytes_after_estimate"]),
                         (20_000_000_000, 10_000_000_000, 10_000_000_000))
        self.assertEqual(gate["raw_compression"], "forbidden")

    def test_launcher_has_no_retry_or_resume_path(self):
        text = (s2.ROOT / "run_rgeo_zgeo_1ms_id2s2_sequence_exact_replay.sh").read_text(
            encoding="utf-8")
        self.assertIn("{offline|run|independent}", text)
        self.assertNotIn("resume", text.lower())
        self.assertNotIn("retry", text.lower())


if __name__ == "__main__":
    unittest.main()
