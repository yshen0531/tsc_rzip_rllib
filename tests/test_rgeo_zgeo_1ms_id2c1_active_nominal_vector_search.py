import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_id2c1_active_nominal_vector_search as stage
from scripts import rgeo_zgeo_1ms_id2c1_active_nominal_vector_independent as independent


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c1_active_nominal_vector_search.json"


class Id2C1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.cfg, cls.source, cls.targets = stage.load(CONFIG)

    def test_frozen_identity_and_budget(self):
        self.assertEqual(stage.sha256(CONFIG), stage.CONFIG_SHA256)
        self.assertEqual(self.config["maximum_rollouts"], 11)
        self.assertEqual(self.config["maximum_advance_attempts"], 352)
        self.assertEqual(self.config["holdout_records_read"], 0)

    def test_phase_a_streams_and_slew(self):
        streams = stage.phase_a_streams(self.config, self.cfg, self.targets)
        self.assertEqual(len(streams), 4)
        self.assertEqual([len(row["targets"]) for row in streams], [32] * 4)
        self.assertEqual([max(a["maximum_issued_delta_a"] for a in row["actions"]) for row in streams], [0.0, 0.3, 0.3, 0.3])
        self.assertEqual(streams[-1]["actions"][-1]["probe_virtual_action"][0], 31.0)

    def test_phase_b_is_matched_and_returns(self):
        selected = stage.phase_a_streams(self.config, self.cfg, self.targets)[1]
        rows = stage.phase_b_streams(self.config, self.cfg, self.targets, selected)
        self.assertEqual(len(rows), 7)
        baseline = rows[0]
        for row in rows:
            self.assertEqual(row["targets"][:16], baseline["targets"][:16])
            self.assertEqual(row["targets"][17:], baseline["targets"][17:])
            self.assertLessEqual(max(a["maximum_issued_delta_a"] for a in row["actions"]), 0.3)
        self.assertEqual(baseline["targets"][15:], [baseline["targets"][15]] * 17)

    def test_phase_a_selection_requires_material_improvement(self):
        def row(candidate, terminal_r, passed=True):
            return {
                "candidate_id": candidate,
                "passed": passed,
                "reasons": [],
                "states": [
                    {"r_geo_m": 0.0, "z_geo_m": 0.0, "ip_a": 1000.0},
                    {"r_geo_m": terminal_r, "z_geo_m": 0.0, "ip_a": 1000.0},
                ],
            }
        metrics, selected = stage._phase_a_metrics(
            [row("fresh_q0_baseline", 1.0), row("weak", 0.81), row("material", 0.79)], self.config
        )
        self.assertEqual(selected, "material")
        self.assertEqual(len(metrics), 3)

    def test_offline_has_zero_plant_work(self):
        result = stage.offline(CONFIG, "test")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["reset_calls"], 0)
        self.assertEqual(result["advance_attempts"], 0)
        self.assertEqual(result["plant_advance_gotsc_calls"], 0)

    def test_independent_schema_is_distinct(self):
        self.assertNotEqual(independent.SCHEMA, stage.SCHEMA)
        order = independent._campaign_order(self.config)
        self.assertEqual(order["fresh_q0_baseline"], 0)
        self.assertEqual(order["p03_minus_stride1"], 3)
        self.assertEqual(order["selected_nominal_probe_baseline"], 4)
        self.assertEqual(order["selected_nominal_p09_half_exact_center_minus"], 10)


if __name__ == "__main__":
    unittest.main()
