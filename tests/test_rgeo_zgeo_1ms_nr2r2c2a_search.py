from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "c2a_search", ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c2a_search.py"
    )
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C2A = load_module()


def states(*, terminal_step: float = 0.00005, terminal_source: float = 0.001):
    result = []
    for index in range(33):
        if index < 24:
            value = terminal_source * index / 24
        else:
            value = terminal_source + terminal_step * (index - 24)
        result.append({"r_geo_m": 0.7 + value, "z_geo_m": 0.03 - value,
                       "ip_a": 31000.0 + index})
    return result


class C2ASearchTests(unittest.TestCase):
    def test_frozen_matrix_and_exact_targets(self):
        stage = json.loads((ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2a_search.json").read_text())
        self.assertEqual(stage["maximum_plant_advances"], 64)
        self.assertEqual(len(stage["candidates"]), 2)
        self.assertTrue(all(len(spec["card15_fields"]) == 14 for spec in stage["candidates"]))
        self.assertTrue(all(len(field) == 10 for spec in stage["candidates"] for field in spec["card15_fields"]))

    def test_action_stream_is_q0_then_constant_target(self):
        stage = json.loads((ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2a_search.json").read_text())
        q0, target = object(), object()
        stream = C2A.action_stream(stage, q0, target)
        self.assertEqual(len(stream), 32)
        self.assertIs(stream[0], q0)
        self.assertTrue(all(item is target for item in stream[1:]))

    def test_hold_metrics_apply_all_frozen_terminal_gates(self):
        stage = json.loads((ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2a_search.json").read_text())
        good = C2A.hold_metrics(states(), stage)
        bad = C2A.hold_metrics(states(terminal_step=0.00011), stage)
        self.assertTrue(good["eligible"])
        self.assertFalse(bad["eligible"])

    def test_selection_key_is_deterministic(self):
        left = {"candidate_id": "b", "hold_metrics": {
            "terminal_maximum_source_axis_displacement_m": 1.0,
            "terminal_maximum_absolute_axis_step_m": 2.0,
            "terminal_maximum_absolute_axis_net_drift_m": 3.0}}
        right = {"candidate_id": "a", "hold_metrics": dict(left["hold_metrics"])}
        self.assertEqual(min((left, right), key=C2A.selection_key)["candidate_id"], "a")


if __name__ == "__main__":
    unittest.main()
