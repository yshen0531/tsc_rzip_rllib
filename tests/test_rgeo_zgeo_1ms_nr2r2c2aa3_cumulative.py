from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "c2aa3_cumulative", ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c2aa3_cumulative.py")
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C2AA3 = load_module()


def paths(total: float, level1: float):
    q0, candidate, comparator = [], [], []
    for _ in range(33):
        q0.append({"r_geo_m": 0.7, "z_geo_m": 0.03, "ip_a": 31000.0})
        candidate.append({"r_geo_m": 0.7 + total / 2,
                          "z_geo_m": 0.03 - total / 2, "ip_a": 31000.0})
        comparator.append({"r_geo_m": 0.7 + level1 / 2,
                           "z_geo_m": 0.03 - level1 / 2, "ip_a": 31000.0})
    return candidate, q0, comparator


class C2AA3CumulativeTests(unittest.TestCase):
    def setUp(self):
        self.stage = json.loads((
            ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa3_p03_cumulative_level2.json"
        ).read_text())

    def test_frozen_budget_and_schedule(self):
        self.assertEqual(self.stage["maximum_plant_advances"], 64)
        self.assertEqual(self.stage["rollouts"], 2)
        covered = [step for row in self.stage["schedule"]
                   for step in range(row["first_step"], row["last_step"] + 1)]
        self.assertEqual(covered, list(range(32)))

    def test_level2_exactly_doubles_p03_card15_offset(self):
        q0_record = json.loads((ROOT / self.stage["q0_comparator"]["path"]).read_text())
        q0 = q0_record["actions"][0]["expected_card15_fields"]
        for base, level1, level2 in zip(q0, self.stage["level1_card15_fields"],
                                        self.stage["level2_card15_fields"]):
            self.assertEqual(Decimal(level2.strip()) - Decimal(base.strip()),
                             2 * (Decimal(level1.strip()) - Decimal(base.strip())))

    def test_incremental_metrics_apply_frozen_gates(self):
        good, q0, level1 = paths(0.0008, 0.0005)
        weak, _, _ = paths(0.0006, 0.0005)
        self.assertTrue(C2AA3.incremental_metrics(good, q0, level1, self.stage)["passed"])
        self.assertFalse(C2AA3.incremental_metrics(weak, q0, level1, self.stage)["passed"])

    def test_incremental_window_is_states_three_through_sixteen(self):
        candidate, q0, level1 = paths(0.0008, 0.0005)
        metrics = C2AA3.incremental_metrics(candidate, q0, level1, self.stage)
        self.assertEqual(metrics["window_states"], list(range(3, 17)))
        self.assertEqual(len(metrics["incremental_opposition_m"]), 14)

    def test_independent_auditor_populates_artifact_hashes_for_pair_compare(self):
        source = (ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c2aa3_independent.py").read_text()
        self.assertIn('state["artifact_sha256"] = {}', source)
        self.assertIn('state["artifact_sha256"][name] = digest', source)


if __name__ == "__main__":
    unittest.main()
