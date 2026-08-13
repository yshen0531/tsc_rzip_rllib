from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("c1a", ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c1a_source_replay.py")
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C1A = load_module()
STAGE = {"repeatability": {"geometry_m": 1e-12, "ip_a": 1e-9, "coil_a": 1e-9, "wire_a": 1e-9},
         "semantic_artifacts": ["inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"]}


def row():
    state = {"time_ms": 1100, "r_geo_m": .7, "z_geo_m": .03, "r_mid_m": .79, "ip_a": 31200.0,
             "actual_current_decimal_a_tsc": ["0"] * 14, "wire_current_a": [0.0] * 48,
             "artifact_sha256": {"inputa": "a", "geqdsk": "b", "coil_currents.csv": "c",
                                     "wire_currents.csv": "d", "sprsina": "x"}}
    action = {"issue_step": 0, "issue_time_ms": 1100, "effect_state_index": 1, "effect_age_steps": 1}
    return {"pair_id": "q0_h04", "states": [state], "actions": [action]}


class C1ATests(unittest.TestCase):
    def test_frozen_matrix_budget(self):
        stage = json.loads((ROOT / "configs/rgeo_zgeo_1ms_nr2r2c1a_source_replay.json").read_text(encoding="utf-8"))
        specs = C1A.matrix(stage)
        self.assertEqual(len(specs), 12)
        self.assertEqual(sum(x["horizon_steps"] for x in specs), 136)

    def test_sprsina_is_diagnostic_only(self):
        left, right = row(), copy.deepcopy(row())
        right["states"][0]["artifact_sha256"]["sprsina"] = "y"
        result = C1A.compare_pair(left, right, STAGE)
        self.assertTrue(result["passed"])
        self.assertFalse(result["sprsina_hash_exact_all_states"])

    def test_semantic_artifact_mismatch_fails(self):
        left, right = row(), copy.deepcopy(row())
        right["states"][0]["artifact_sha256"]["geqdsk"] = "z"
        self.assertFalse(C1A.compare_pair(left, right, STAGE)["passed"])

    def test_action_history_mismatch_fails(self):
        left, right = row(), copy.deepcopy(row())
        right["actions"][0]["effect_age_steps"] = 2
        self.assertFalse(C1A.compare_pair(left, right, STAGE)["passed"])


if __name__ == "__main__":
    unittest.main()
