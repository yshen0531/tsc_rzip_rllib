import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import rgeo_zgeo_1ms_id0_vector_tail as primary
from scripts import rgeo_zgeo_1ms_id0_vector_tail_independent as independent
from tsc_rzip_rllib.core.runner import TSCConfig


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id0_vector_tail.json"
Q0 = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_nr2r2c1a_result_20260814_778b454/q0_h32_r0.json"


class ID0VectorTailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        with patch.object(TSCConfig, "validate", lambda self: None):
            cls.cfg = TSCConfig.from_json(ROOT / cls.stage["base_tsc_config"])
        state = json.loads(Q0.read_text(encoding="utf-8"))["states"][0]
        cls.source = {
            "currents_a_tsc": state["actual_current_a_tsc"],
            "active_command_decimal_a_tsc": state["active_command_decimal_a_tsc"],
        }

    def test_config_hash_and_exact_contract(self):
        self.assertEqual(primary.sha256(CONFIG), primary.CONFIG_SHA256)
        primary._exact_stage(self.stage)
        self.assertEqual(len(primary.rollout_specs(self.stage)), 20)

    def test_rollout_order_and_counts(self):
        rows = primary.rollout_specs(self.stage)
        self.assertEqual([row["rollout_id"] for row in rows[:4]], [
            "baseline_q0_r0", "baseline_q0_r1", "early_p03_plus_r0", "early_p03_plus_r1"
        ])
        self.assertEqual(sum(row["context_id"] == "early" for row in rows), 12)
        self.assertEqual(sum(row["context_id"] == "late" for row in rows), 6)

    def test_actual_targets_reconstruct_and_exact_slew(self):
        targets, streams = primary.targets_and_stream(self.stage, self.cfg, self.source)
        self.assertEqual(set(targets), {"q0", "p03:plus", "p03:minus", "p04:plus", "p04:minus", "p07:plus", "p07:minus"})
        self.assertEqual(len(streams), 20)
        for row in streams:
            self.assertEqual(len(row["targets"]), 20)
            self.assertEqual(len(row["actions"]), 20)
            self.assertLessEqual(max(action["maximum_issued_delta_a"] for action in row["actions"]), 0.3)
            if row["pulse_issue_step"] is not None:
                self.assertAlmostEqual(row["actions"][row["pulse_issue_step"]]["maximum_issued_delta_a"], 0.3)
                self.assertAlmostEqual(row["actions"][row["return_issue_step"]]["maximum_issued_delta_a"], 0.3)

    def test_action_matrix_uses_actual_vectors(self):
        targets, _ = primary.targets_and_stream(self.stage, self.cfg, self.source)
        q0 = np.asarray(targets["q0"].current_a_tsc)
        matrix = np.asarray([targets[key].current_a_tsc for key in targets if key != "q0"]) - q0
        self.assertEqual(np.linalg.matrix_rank(matrix), 4)

    def test_config_mutation_is_fail_closed(self):
        for mutation in (
            lambda row: row.__setitem__("maximum_advance_attempts", 401),
            lambda row: row["scientific_gates"].__setitem__("maximum_best_pair_condition", 11.0),
            lambda row: row["empirical_exploration"].__setitem__("pre_action_transition_tube_claimed", True),
            lambda row: row["routes"].__setitem__("pass", "WEAKENED"),
        ):
            stage = copy.deepcopy(self.stage)
            mutation(stage)
            with self.assertRaises(primary.InputIntegrityError):
                primary._exact_stage(stage)

    def test_step_caps_are_axis_specific(self):
        before = {"r_geo_m": 0.0, "z_geo_m": 0.0, "ip_a": 0.0}
        self.assertEqual(primary._step_cap_reasons(self.stage, before, {"r_geo_m": .002, "z_geo_m": -.002, "ip_a": 100.0}), [])
        self.assertIn("EMPIRICAL_STEP_R", primary._step_cap_reasons(self.stage, before, {"r_geo_m": .0020001, "z_geo_m": 0.0, "ip_a": 0.0}))

    def test_route_precedence(self):
        metrics = {"signal_passed": True, "ip_passed": True, "vector_geometry_passed": True, "tail_passed": True}
        self.assertEqual(primary.route_for(self.stage, False, False, False, None), self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(self.stage, True, False, False, None), self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, False, None), self.stage["routes"]["repeatability_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, True, metrics), self.stage["routes"]["pass"])
        metrics["tail_passed"] = False
        self.assertEqual(primary.route_for(self.stage, True, True, True, metrics), self.stage["routes"]["tail_horizon_fail"])

    def test_vector_metrics_pass_synthetic_geometry(self):
        rows = self._synthetic_rows()
        metrics = primary.scientific_metrics(rows, self.stage)
        self.assertEqual(metrics["rz_response_rank"], 2)
        self.assertTrue(metrics["signal_passed"])
        self.assertTrue(metrics["ip_passed"])
        self.assertTrue(metrics["vector_geometry_passed"])
        self.assertTrue(metrics["tail_passed"])

    def test_primary_and_independent_metrics_agree(self):
        rows = self._synthetic_rows()
        self.assertEqual(
            json.dumps(primary.scientific_metrics(rows, self.stage), sort_keys=True),
            json.dumps(independent._metrics(rows, self.stage), sort_keys=True),
        )

    def test_launcher_is_stage_specific(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id0_vector_tail.sh").read_text(encoding="utf-8")
        self.assertIn("ID0_SOURCE_REVISION", text)
        self.assertIn("rgeo_zgeo_1ms_id0_vector_tail_independent.py", text)
        self.assertNotIn("aa4e1", text.lower())

    def _synthetic_rows(self):
        rows = []
        specs = primary.rollout_specs(self.stage)
        direction = {
            ("p03", "plus"): np.array([1.0, 0.0]), ("p03", "minus"): np.array([-1.0, 0.0]),
            ("p04", "plus"): np.array([0.0, 1.0]), ("p04", "minus"): np.array([0.0, -1.0]),
            ("p07", "plus"): np.array([1.0, 1.0]), ("p07", "minus"): np.array([-1.0, -1.0]),
        }
        for spec in specs:
            states = []
            effect = None if spec["pulse_issue_step"] is None else spec["pulse_issue_step"] + 1
            for index in range(21):
                response = np.zeros(2)
                if effect is not None and index >= effect:
                    age = index - effect
                    response = direction[(spec["direction_id"], spec["sign"])] * 0.0001 * max(0.0, 1.0 - age / 12.0)
                states.append({"r_geo_m": 0.7 + response[0], "z_geo_m": 0.03 + response[1], "ip_a": 31000.0,
                               "r_mid_m": .79, "actual_current_decimal_a_tsc": ["0"] * 14,
                               "wire_current_a": [0.0] * 48, "artifact_sha256": {name: "x" for name in primary.ARTIFACTS},
                               "time_ms": 1100 + index})
            rows.append({**spec, "states": states, "actions": []})
        return rows


if __name__ == "__main__":
    unittest.main()
