import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2c0_control_relevance_audit as primary
from scripts import rgeo_zgeo_1ms_id2c0_control_relevance_independent as independent


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c0_control_relevance_audit.json"


class Id2C0ContractTests(unittest.TestCase):
    def test_frozen_config_and_routes(self):
        config, bound = primary.load_stage(ROOT, CONFIG)
        self.assertEqual(primary.sha256_file(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(len(bound), 14)
        self.assertEqual(config["routes"]["pass"], primary.PASS)
        self.assertEqual(config["plant_advances"], 0)
        self.assertEqual(config["tsc_calls"], 0)
        self.assertEqual(config["models_fit_or_trained"], 0)
        self.assertEqual(config["calibration_records_read"], 0)
        self.assertEqual(config["holdout_records_read"], 0)

    def test_feature_cancellation_detects_context_invariant_response(self):
        config = json.loads((ROOT / "configs/rgeo_zgeo_1ms_id2b1_structured_model_development.json").read_text())
        rows = []
        # Synthetic feature test: the real server test exercises all 39 trajectories.
        for context, offset in (
            ("anchor_p03_minus", 0.0),
            ("history_p04_plus", 0.2),
            ("late_q0", -0.1),
        ):
            states = [
                {"r_geo_m": offset, "z_geo_m": 0.0, "ip_a": 0.0, "actual_current_a_tsc": [0.0] * 14}
                for _ in range(33)
            ]
            q0_actions = [
                {"target_current_a_tsc": [0.0] * 14, "probe_virtual_action": [0.0, 0.0]}
                for _ in range(32)
            ]
            baseline = {"context_id": context, "direction_id": "baseline", "sign": "none", "duration_issues": 0, "states": states, "actions": q0_actions}
            action_rows = json.loads(json.dumps(q0_actions))
            action_rows[10]["target_current_a_tsc"][0] = 0.3
            action_rows[10]["probe_virtual_action"][0] = 1.0
            action = {"context_id": context, "direction_id": "p", "sign": "plus", "duration_issues": 1, "states": states, "actions": action_rows}
            rows.extend([baseline, action])
        metrics = primary.feature_cancellation(rows, config)
        self.assertLessEqual(metrics["stable_exp_signed"]["maximum_cross_context_matched_baseline_feature_difference"], 1e-12)
        self.assertLessEqual(metrics["stable_exp_signed_even"]["maximum_cross_context_matched_baseline_feature_difference"], 1e-12)

    def test_write_new_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            path = Path(folder) / "result.json"
            primary.write_new(path, {"a": 1})
            with self.assertRaises(FileExistsError):
                primary.write_new(path, {"a": 2})

    def test_independent_schema_is_distinct(self):
        self.assertNotEqual(independent.SCHEMA, primary.SCHEMA)


if __name__ == "__main__":
    unittest.main()
