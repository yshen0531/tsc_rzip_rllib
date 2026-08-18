from __future__ import annotations

import copy
import unittest

from scripts import rgeo_zgeo_1ms_id2s1_measured_sequence_discriminator as s1


class ID2S1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (cls.stage, cls.cfg, cls.targets, cls.source,
         cls.baseline, cls.s0_result) = s1.load()
        cls.streams = s1.campaign_streams(
            cls.stage, cls.cfg, cls.targets, cls.source, cls.s0_result)

    def _synthetic_additive_rows(self):
        predicted = {row["sequence_id"]: row["predicted_rz_response_m"]
                     for row in self.s0_result["predicted_candidates"]}
        rows = []
        for stream in self.streams:
            row = copy.deepcopy(self.baseline)
            row.update({key: copy.deepcopy(value) for key, value in stream.items()
                        if key not in ("targets", "actions")})
            row["actions"] = copy.deepcopy(stream["actions"])
            for offset, value in enumerate(predicted[stream["sequence_id"]]):
                state = row["states"][25 + offset]
                base = self.baseline["states"][25 + offset]
                state["r_geo_m"] = base["r_geo_m"] + value[0]
                state["z_geo_m"] = base["z_geo_m"] + value[1]
            row["passed"] = True
            rows.append(row)
        return rows

    def test_frozen_identity_and_budget(self):
        self.assertEqual([row["sequence_id"] for row in self.streams],
                         self.stage["selected_sequence_ids"])
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

    def test_streams_match_hash_bound_s0_actions(self):
        recorded = {row["sequence_id"]: row for row in self.s0_result["candidate_streams"]}
        for stream in self.streams:
            self.assertTrue(recorded[stream["sequence_id"]]["selected"])
            self.assertEqual(stream["actions"], recorded[stream["sequence_id"]]["actions"])
            self.assertEqual(len(stream["actions"]), 34)
            self.assertLessEqual(max(float(row["maximum_issued_delta_a"])
                                     for row in stream["actions"]), 0.3)
            self.assertEqual(stream["non_nominal_issue_steps"], [24, 27])

    def test_offline_preflight_is_zero_plant(self):
        result = s1.offline(s1.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual((result["reset_calls"], result["advance_attempts"],
                          result["plant_advance_gotsc_calls"],
                          result["verified_plant_advances"]), (0, 0, 0, 0))
        self.assertEqual(result["models_fit_or_updated"], 0)

    def test_exact_baseline_prefix_passes_and_change_fails(self):
        rows = self._synthetic_additive_rows()
        checks = s1.matched_prefix_checks(rows, self.baseline)
        self.assertEqual(len(checks), 4)
        self.assertTrue(all(row["passed"] for row in checks))
        rows[0]["states"][24]["r_geo_m"] += 2e-12
        self.assertFalse(s1.matched_prefix_checks(rows, self.baseline)[0]["passed"])

    def test_additive_synthetic_geometry_reproduces_selector_pass(self):
        metrics = s1.measured_metrics(
            self._synthetic_additive_rows(), self.baseline, self.s0_result, self.stage)
        self.assertTrue(metrics["passed"])
        self.assertEqual((metrics["sequence_count"], metrics["sample_count"]), (4, 40))
        self.assertAlmostEqual(metrics["minimum_direction_progress_m"],
                               self.s0_result["selection"]["minimum_direction_progress_m"])
        self.assertAlmostEqual(metrics["maximum_angular_gap_deg"],
                               self.s0_result["selection"]["maximum_angular_gap_deg"])
        for row in metrics["sequence_metrics"]:
            self.assertLessEqual(row["maximum_absolute_interaction_r_m"], 1e-15)
            self.assertLessEqual(row["maximum_absolute_interaction_z_m"], 1e-15)

    def test_interaction_is_reported_but_not_thresholded(self):
        gates = self.stage["measured_gates"]
        self.assertTrue(gates["additive_interaction_is_descriptive_not_gated"])
        self.assertNotIn("maximum_additive_error", gates)

    def test_data_use_stays_zero_weight(self):
        self.assertEqual(self.stage["data_use"],
                         "development_sequence_geometry_only_zero_fit_weight")
        self.assertEqual(self.stage["fit_calibration_holdout_controller_expert_or_rl_use"],
                         "forbidden")
        self.assertTrue(all(row["development_only_zero_fit_weight"] for row in self.streams))

    def test_storage_reserve_is_frozen(self):
        gate = self.stage["storage_gate"]
        self.assertEqual((gate["minimum_free_bytes_before_run"],
                          gate["maximum_estimated_raw_bytes"],
                          gate["minimum_free_bytes_after_estimate"]),
                         (20_000_000_000, 10_000_000_000, 10_000_000_000))
        self.assertEqual(gate["raw_compression"], "forbidden")

    def test_launcher_has_no_retry_or_resume_path(self):
        text = (s1.ROOT / "run_rgeo_zgeo_1ms_id2s1_measured_sequence_discriminator.sh").read_text(
            encoding="utf-8")
        self.assertIn("{offline|run|independent}", text)
        self.assertNotIn("resume", text.lower())
        self.assertNotIn("retry", text.lower())


if __name__ == "__main__":
    unittest.main()
