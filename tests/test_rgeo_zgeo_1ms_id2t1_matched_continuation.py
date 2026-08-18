from __future__ import annotations

import copy
import unittest

from scripts import rgeo_zgeo_1ms_id2t1_matched_continuation as t1


class ID2T1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.stage, cls.cfg, cls.targets, cls.source,
         cls.references, cls.base) = t1.load()
        cls.streams = t1.campaign_streams(cls.stage, cls.cfg, cls.references, cls.base)

    def test_budget_and_identity(self):
        self.assertEqual(len(self.streams), 4)
        self.assertEqual((self.stage["maximum_reset_calls"],
                          self.stage["maximum_advance_attempts"],
                          self.stage["maximum_gotsc_calls"]), (4, 136, 136))
        self.assertEqual(self.stage["continuation_arm"], "p04_plus")

    def test_prefix_is_exact_and_only_common_continuation_is_new(self):
        for stream in self.streams:
            reference = self.references[stream["sequence_id"]]
            self.assertEqual(stream["actions"][:30], reference["actions"][:30])
            self.assertEqual(stream["actions"][30]["probe_virtual_action"], [1.0, 0.0])
            self.assertEqual(stream["actions"][31]["probe_virtual_action"], [1.0, 0.0])
            self.assertEqual(stream["actions"][32]["probe_virtual_action"], [0.0, 0.0])
            self.assertEqual(stream["actions"][33]["probe_virtual_action"], [0.0, 0.0])
            self.assertLessEqual(max(float(row["maximum_issued_delta_a"])
                                     for row in stream["actions"]), 0.3)

    def test_offline_is_zero_plant(self):
        result = t1.offline(t1.CONFIG, "test-revision")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual((result["reset_calls"], result["advance_attempts"],
                          result["plant_advance_gotsc_calls"],
                          result["verified_plant_advances"]), (0, 0, 0, 0))

    def test_prefix_comparison_is_fail_closed(self):
        ref = self.references[self.stage["sequence_ids"][0]]
        self.assertEqual(t1._prefix_reasons(ref["states"][30], ref["states"][30],
                                            self.stage, 30), [])
        without_side = copy.deepcopy(ref["states"][30])
        without_side.pop("side")
        self.assertEqual(t1._prefix_reasons(without_side, ref["states"][30],
                                            self.stage, 30), [])
        changed = copy.deepcopy(ref["states"][30])
        changed["r_geo_m"] += 2e-12
        self.assertTrue(t1._prefix_reasons(changed, ref["states"][30], self.stage, 30))

    def test_metrics_measure_absolute_source_progress(self):
        rows = []
        for stream in self.streams:
            ref = self.references[stream["sequence_id"]]
            row = copy.deepcopy(ref)
            row.update({key: copy.deepcopy(value) for key, value in stream.items()
                        if key not in ("targets", "actions")})
            row["actions"] = copy.deepcopy(stream["actions"])
            source = row["states"][0]
            for index in self.stage["measured_gates"]["response_state_indices"]:
                base = ref["states"][index]
                direction_r = source["r_geo_m"] - base["r_geo_m"]
                direction_z = source["z_geo_m"] - base["z_geo_m"]
                norm = (direction_r ** 2 + direction_z ** 2) ** 0.5
                row["states"][index]["r_geo_m"] += 0.0001 * direction_r / norm
                row["states"][index]["z_geo_m"] += 0.0001 * direction_z / norm
            rows.append(row)
        metrics = t1.measured_metrics(rows, self.references, self.stage)
        self.assertTrue(metrics["passed"])
        self.assertEqual(metrics["passed_histories"], 4)

    def test_zero_weight_and_launcher_no_retry(self):
        self.assertEqual(self.stage["data_use"], "route_decision_only_zero_fit_weight")
        text = (t1.ROOT / "run_rgeo_zgeo_1ms_id2t1_matched_continuation.sh").read_text(
            encoding="utf-8")
        self.assertNotIn("retry", text.lower())
        self.assertNotIn("resume", text.lower())


if __name__ == "__main__":
    unittest.main()
