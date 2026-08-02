import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s17_causal_multi_drift_belief_preflight as s17,
)


class Stage42R3c3T13S17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = Path(__file__).resolve().parents[1] / "configs" / "stage4_2r3c3t13s17_causal_multi_drift_belief_preflight.json"
        cls.cfg = s17._load_config(cls.config_path)

    def test_identity_and_execution_prohibitions(self):
        self.assertEqual(self.cfg["stage"], s17.STAGE)
        self.assertTrue(all(not value for value in self.cfg["execution"].values()))
        self.assertFalse(self.cfg["formal_timing_contract"]["arrival_deadline_expansion_allowed"])

    def test_designs_are_exact_full_rank_and_conditioned(self):
        designs = s17._designs(self.cfg)
        self.assertEqual([row["degree"] for row in designs], [1, 2, 3])
        self.assertEqual([row["rank"] for row in designs], [6, 7, 8])
        self.assertLessEqual(max(row["condition"] for row in designs), 4.0)

    def test_settling_rows_have_zero_input_code(self):
        codes = np.asarray(self.cfg["causal_history"]["fixed_input_codes"])
        np.testing.assert_array_equal(codes[8:], np.zeros((2, 4)))

    def test_visible_prefix_ignores_state_eleven_and_later(self):
        trajectory = []
        for index in range(13):
            trajectory.append({"R": 1.0 + 0.01 * index, "Z": 2.0 - 0.02 * index, "Ip": 30000.0 + index})
        result = {"trajectory": trajectory}
        first = s17._visible_outputs_prefix(result)
        changed = copy.deepcopy(result)
        changed["trajectory"][11] = {"R": 999.0, "Z": -999.0, "Ip": -1e9}
        changed["trajectory"][12] = {"R": -999.0, "Z": 999.0, "Ip": 1e9}
        second = s17._visible_outputs_prefix(changed)
        np.testing.assert_array_equal(first, second)

    def test_causal_prefix_has_expected_backward_velocity(self):
        trajectory = [
            {"R": 0.1 * index, "Z": -0.2 * index, "Ip": 100.0 + index}
            for index in range(12)
        ]
        output = s17._visible_outputs_prefix({"trajectory": trajectory})
        np.testing.assert_allclose(output[:, 2], 10.0)
        np.testing.assert_allclose(output[:, 3], -20.0)

    def test_hypothesis_query_leverage_is_finite(self):
        for item in s17._designs(self.cfg):
            for direction in range(4):
                query = np.concatenate((np.zeros(item["degree"] + 1), np.eye(4)[direction]))
                weights = query @ np.linalg.pinv(item["design"])
                self.assertTrue(np.all(np.isfinite(weights)))
                self.assertGreater(np.sum(np.abs(weights)), 0.0)

    def test_baseline_join_does_not_open_pair_or_history_labels(self):
        result = {"spec": {
            "state_generation_experiment_id": "opaque-state",
            "target_id": "nominal", "action_delay_steps": 2, "slew_scale": 0.9,
            "pair_id": "forbidden-a", "history_member": "forbidden-b",
        }}
        changed = copy.deepcopy(result)
        changed["spec"]["pair_id"] = "different"
        changed["spec"]["history_member"] = "different"
        self.assertEqual(s17._source_join_key(result), s17._source_join_key(changed))

    def test_config_rejects_gate_weakening(self):
        changed = copy.deepcopy(self.cfg)
        changed["hypotheses"]["maximum_design_condition"] = 5.0
        with self.assertRaises(ValueError):
            s17._validate_config(changed)

    def test_config_rejects_future_state(self):
        changed = copy.deepcopy(self.cfg)
        changed["causal_history"]["state_indices"].append(11)
        with self.assertRaises(ValueError):
            s17._validate_config(changed)

    def test_write_json_is_strict_and_atomic(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            path = Path(temp) / "value.json"
            s17._write_json(path, {"a": 1.0})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1.0})
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_self_test(self):
        result = s17.self_test(self.config_path)
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertEqual(result["new_tsc_or_plant_step_count"], 0)


if __name__ == "__main__":
    unittest.main()
