from __future__ import annotations

import copy
import unittest

from scripts import rgeo_zgeo_1ms_id2r1_f03_exact_replay as r1


class ID2R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.cfg, cls.targets, cls.source, cls.originals = r1.load()
        cls.streams = r1.campaign_streams(cls.stage, cls.cfg, cls.targets, cls.source)

    def _synthetic_exact_rows(self):
        rows = []
        for stream in self.streams:
            row = copy.deepcopy(self.originals[stream["cell_id"]])
            row.update({key: copy.deepcopy(value) for key, value in stream.items()
                        if key not in ("targets", "actions")})
            row["actions"] = copy.deepcopy(stream["actions"])
            rows.append(row)
        return rows

    def test_frozen_identity_and_budget(self):
        self.assertEqual(self.stage["rollout_ids"], [row["rollout_id"] for row in self.streams])
        self.assertEqual((self.stage["maximum_rollouts"], self.stage["maximum_reset_calls"]), (5, 5))
        self.assertEqual((self.stage["maximum_advance_attempts"], self.stage["maximum_gotsc_calls"],
                          self.stage["maximum_verified_plant_advances"]), (170, 170, 170))
        self.assertEqual(self.stage["maximum_retained_states"], 175)
        self.assertEqual(self.stage["required_artifact_files_if_complete"], 875)
        self.assertEqual(self.stage["retry_after_any_advance_attempt"], "forbidden")

    def test_no_new_action_or_schedule_cell(self):
        self.assertEqual(self.stage["new_action_or_schedule_cells"], 0)
        for stream in self.streams:
            original = self.originals[stream["cell_id"]]
            self.assertEqual(stream["actions"], original["actions"])
            self.assertEqual(len(stream["actions"]), 34)
            self.assertLessEqual(max(float(row["maximum_issued_delta_a"])
                                     for row in stream["actions"]), 0.3)

    def test_offline_preflight_is_zero_plant(self):
        result = r1.offline(r1.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual((result["reset_calls"], result["advance_attempts"],
                          result["plant_advance_gotsc_calls"], result["verified_plant_advances"]),
                         (0, 0, 0, 0))

    def test_exact_original_rows_pass_all_replay_checks(self):
        rows = self._synthetic_exact_rows()
        prefixes = r1.matched_prefix_checks(rows, self.stage)
        replays = r1.replay_checks(rows, self.originals, self.stage)
        responses = r1.response_checks(rows, self.originals, self.stage)
        self.assertEqual(len(prefixes), 4)
        self.assertEqual(len(replays), 5)
        self.assertEqual(len(responses), 4)
        self.assertTrue(all(row["passed"] for row in prefixes + replays + responses))

    def test_replay_check_rejects_one_state_change(self):
        rows = self._synthetic_exact_rows()
        rows[1]["states"][25]["r_geo_m"] += 2e-12
        checks = r1.replay_checks(rows, self.originals, self.stage)
        changed = next(row for row in checks if row["cell_id"] == rows[1]["cell_id"])
        self.assertFalse(changed["passed"])
        self.assertIn("GEOMETRY_M", changed["failures"])

    def test_response_check_rejects_changed_differential(self):
        rows = self._synthetic_exact_rows()
        rows[2]["states"][27]["z_geo_m"] += 2e-12
        checks = r1.response_checks(rows, self.originals, self.stage)
        changed = next(row for row in checks if row["cell_id"] == rows[2]["cell_id"])
        self.assertFalse(changed["passed"])

    def test_data_use_is_integrity_only(self):
        self.assertEqual(self.stage["data_use"], "integrity_and_route_decision_only_zero_fit_weight")
        self.assertEqual(self.stage["fit_calibration_holdout_controller_expert_or_rl_use"], "forbidden")
        self.assertTrue(all(row["integrity_only_zero_fit_weight"] for row in self.streams))

    def test_storage_reserve_is_frozen(self):
        gate = self.stage["storage_gate"]
        self.assertEqual(gate["minimum_free_bytes_before_run"], 24000000000)
        self.assertEqual(gate["maximum_estimated_raw_bytes"], 12000000000)
        self.assertEqual(gate["minimum_free_bytes_after_estimate"], 12000000000)
        self.assertEqual(gate["raw_compression"], "forbidden")

    def test_launcher_has_no_retry_or_resume_path(self):
        text = (r1.ROOT / "run_rgeo_zgeo_1ms_id2r1_f03_exact_replay.sh").read_text(encoding="utf-8")
        self.assertIn("{offline|run|independent}", text)
        self.assertNotIn("resume", text.lower())
        self.assertNotIn("retry", text.lower())


if __name__ == "__main__":
    unittest.main()

