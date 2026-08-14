from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "c2aa1_authority", ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c2aa1_authority.py"
    )
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C2AA1 = load_module()


def states(opposition_m: float, *, ip_difference_a: float = 0.0):
    q0 = []
    candidate = []
    for index in range(33):
        q0.append({"r_geo_m": 0.7, "z_geo_m": 0.03, "ip_a": 31000.0})
        candidate.append({
            "r_geo_m": 0.7 + opposition_m / 2,
            "z_geo_m": 0.03 - opposition_m / 2,
            "ip_a": 31000.0 + ip_difference_a,
        })
    return candidate, q0


class C2AA1AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.stage = json.loads(
            (ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa1_level2_authority.json").read_text()
        )

    def test_frozen_budget_schedule_and_card15_shape(self):
        self.assertEqual(self.stage["maximum_plant_advances"], 64)
        self.assertEqual(self.stage["rollouts"], 2)
        covered = [step for row in self.stage["schedule"]
                   for step in range(row["first_step"], row["last_step"] + 1)]
        self.assertEqual(covered, list(range(32)))
        for key in ("level1_card15_fields", "level2_card15_fields"):
            self.assertEqual(len(self.stage[key]), 14)
            self.assertTrue(all(len(field) == 10 for field in self.stage[key]))

    def test_target_schedule_has_exact_frozen_levels(self):
        q0, level1, level2 = object(), object(), object()
        targets = C2AA1.targets_for(self.stage, q0, level1, level2)
        self.assertEqual(len(targets), 32)
        self.assertIs(targets[0], q0)
        self.assertIs(targets[1], level1)
        self.assertTrue(all(target is level2 for target in targets[2:16]))
        self.assertIs(targets[16], level1)
        self.assertTrue(all(target is q0 for target in targets[17:]))

    def test_level2_is_exactly_twice_level1_in_card15_field_coordinate(self):
        q0_record = json.loads((ROOT / self.stage["q0_comparator"]["path"]).read_text())
        target = type("Target", (), {})
        q0 = target()
        q0.card15_fields = tuple(q0_record["actions"][0]["expected_card15_fields"])
        level1 = target()
        level1.card15_fields = tuple(self.stage["level1_card15_fields"])
        level2 = target()
        level2.card15_fields = tuple(self.stage["level2_card15_fields"])
        C2AA1.assert_exact_doubled_card15_offset(q0, level1, level2)

    def test_authority_metrics_apply_all_frozen_gates(self):
        good, q0 = states(0.0016, ip_difference_a=99.0)
        weak, _ = states(0.0002)
        high_ip, _ = states(0.0016, ip_difference_a=101.0)
        self.assertTrue(C2AA1.authority_metrics(good, q0, self.stage)["passed"])
        self.assertFalse(C2AA1.authority_metrics(weak, q0, self.stage)["passed"])
        self.assertFalse(C2AA1.authority_metrics(high_ip, q0, self.stage)["passed"])

    def test_authority_window_is_states_three_through_sixteen(self):
        candidate, q0 = states(0.0016)
        metrics = C2AA1.authority_metrics(candidate, q0, self.stage)
        self.assertEqual(metrics["window_states"], list(range(3, 17)))
        self.assertEqual(len(metrics["opposition_m"]), 14)


if __name__ == "__main__":
    unittest.main()
