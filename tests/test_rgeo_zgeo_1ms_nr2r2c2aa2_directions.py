from __future__ import annotations

from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "c2aa2_directions", ROOT / "scripts/rgeo_zgeo_1ms_nr2r2c2aa2_directions.py")
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C2AA2 = load_module()


def states(opposition_m: float, *, ip_difference_a: float = 0.0):
    q0 = []
    candidate = []
    for _ in range(33):
        q0.append({"r_geo_m": 0.7, "z_geo_m": 0.03, "ip_a": 31000.0})
        candidate.append({"r_geo_m": 0.7 + opposition_m / 2,
                          "z_geo_m": 0.03 - opposition_m / 2,
                          "ip_a": 31000.0 + ip_difference_a})
    return candidate, q0


class C2AA2DirectionTests(unittest.TestCase):
    def setUp(self):
        self.stage = json.loads((
            ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa2_supported_cube_directions.json"
        ).read_text())

    def test_frozen_budget_candidates_and_schedule(self):
        self.assertEqual(self.stage["maximum_plant_advances"], 96)
        self.assertEqual(self.stage["rollouts"], 3)
        self.assertEqual([item["candidate_id"] for item in self.stage["candidates"]],
                         ["p03_minus", "p04_minus", "p07_minus"])
        covered = [step for row in self.stage["schedule"]
                   for step in range(row["first_step"], row["last_step"] + 1)]
        self.assertEqual(covered, list(range(32)))

    def test_selection_hash_and_partition_are_frozen(self):
        item = self.stage["selection_audit"]
        path = ROOT / item["path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
        selection = json.loads(path.read_text())
        self.assertEqual(selection["source_partition"], "development")
        self.assertEqual(selection["holdout_records_read"], 0)
        self.assertTrue(all(row["positive_states"] == 4 for row in selection["candidates"]))

    def test_target_schedule_uses_common_full_window(self):
        q0, entry, full = object(), object(), object()
        targets = C2AA2.targets_for(self.stage, q0, entry, full)
        self.assertIs(targets[0], q0)
        self.assertIs(targets[1], entry)
        self.assertTrue(all(target is full for target in targets[2:16]))
        self.assertIs(targets[16], entry)
        self.assertTrue(all(target is q0 for target in targets[17:]))

    def test_all_fields_have_exact_card15_width(self):
        for spec in self.stage["candidates"]:
            keys = ["full_card15_fields"]
            if spec["entry_level"] == "level1":
                keys.append("level1_card15_fields")
            for key in keys:
                self.assertEqual(len(spec[key]), 14)
                self.assertTrue(all(len(field) == 10 for field in spec[key]))

    def test_level1_candidates_have_exact_doubled_card15_offset(self):
        q0_record = json.loads((ROOT / self.stage["q0_comparator"]["path"]).read_text())
        q0 = q0_record["actions"][0]["expected_card15_fields"]
        for spec in self.stage["candidates"]:
            if spec["entry_level"] != "level1":
                continue
            for base, entry, full in zip(q0, spec["level1_card15_fields"],
                                         spec["full_card15_fields"]):
                self.assertEqual(Decimal(full.strip()) - Decimal(base.strip()),
                                 2 * (Decimal(entry.strip()) - Decimal(base.strip())))

    def test_authority_metrics_retain_c2aa1_gates(self):
        good, q0 = states(0.0016, ip_difference_a=99.0)
        weak, _ = states(0.0002)
        high_ip, _ = states(0.0016, ip_difference_a=101.0)
        self.assertTrue(C2AA2.authority_metrics(good, q0, self.stage)["passed"])
        self.assertFalse(C2AA2.authority_metrics(weak, q0, self.stage)["passed"])
        self.assertFalse(C2AA2.authority_metrics(high_ip, q0, self.stage)["passed"])


if __name__ == "__main__":
    unittest.main()
