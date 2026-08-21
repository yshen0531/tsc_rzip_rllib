from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_value_d2 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_d2.json"


def state(index: int, r_mm: float = 0.0, z_mm: float = 0.0, ip_a: float = 0.0) -> dict:
    return {"time_ms": 1000 + index, "r_geo_m": 0.7 + r_mm / 1000.0,
            "z_geo_m": z_mm / 1000.0, "r_mid_m": 0.79, "ip_a": 30000.0 + ip_a}


class Fixed1000ValueD2Test(unittest.TestCase):
    def test_frozen_identity_budget_and_roles(self) -> None:
        stage, _, _, _ = primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(stage["rollouts"], 12)
        self.assertEqual(stage["maximum_advance_attempts"], 576)
        self.assertEqual(stage["data_roles"]["calibration_histories"], "unopened")
        self.assertEqual(stage["data_roles"]["blind_histories"], "unopened")
        self.assertEqual(stage["data_roles"]["fixed_1100_data"], "forbidden")

    def test_matrix_has_ten_primary_and_two_zero_weight_replays(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(stage)
        self.assertEqual(sum(row["repeat_index"] == 0 for row in rows), 10)
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 2)
        self.assertEqual({row["candidate"] for row in rows if row["repeat_index"] == 0}, set(stage["candidates"]))

    def test_sequence_composes_two_nonoverlapping_exact_macros(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        levels = {f"{axis}_{sign}_level{level}": f"{axis}_{sign}_{level}"
                  for axis in ("even", "odd") for sign in ("plus", "minus") for level in range(1, 5)}
        target_map = {"q0": "q0", **levels}
        spec = next(row for row in primary.rollout_specs(stage)
                    if row["conditioner"] == "even_plus" and row["candidate"] == "odd_minus")
        sequence = primary.sequence_for(spec, stage, target_map)
        self.assertEqual(sequence[8:20], [f"even_plus_{level}" if level else "q0" for level in primary.MACRO_LEVELS])
        self.assertEqual(sequence[24:36], [f"odd_minus_{level}" if level else "q0" for level in primary.MACRO_LEVELS])
        self.assertTrue(all(value == "q0" for value in sequence[20:24] + sequence[36:]))

    def test_matched_history_metrics_pass_clean_two_axis_values(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = []
        for spec in primary.rollout_specs(stage):
            if spec["repeat_index"]:
                continue
            states = [state(index) for index in range(49)]
            if spec["candidate"] != "baseline":
                axis, sign = spec["candidate"].split("_")
                polarity = 1.0 if sign == "plus" else -1.0
                for horizon, magnitude in ((4, 0.20), (8, 0.30), (12, 0.05), (16, 0.02)):
                    index = stage["candidate_issue_phase"] + horizon
                    states[index] = state(index, r_mm=magnitude * polarity if axis == "even" else 0.0,
                                          z_mm=magnitude * polarity if axis == "odd" else 0.0)
            rows.append({**spec, "states": states})
        metrics = primary.scientific_metrics(rows, stage)
        self.assertTrue(metrics["passed"])
        self.assertEqual(len(metrics["histories"]), 2)

    def test_metrics_reject_one_conditioner_collapsed_geometry(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = []
        for spec in primary.rollout_specs(stage):
            if spec["repeat_index"]:
                continue
            states = [state(index) for index in range(49)]
            if spec["candidate"] != "baseline":
                axis, sign = spec["candidate"].split("_")
                polarity = 1.0 if sign == "plus" else -1.0
                for horizon in (4, 8):
                    index = stage["candidate_issue_phase"] + horizon
                    if spec["conditioner"] == "odd_plus":
                        states[index] = state(index, r_mm=0.25 * polarity)
                    else:
                        states[index] = state(index, r_mm=0.25 * polarity if axis == "even" else 0.0,
                                              z_mm=0.25 * polarity if axis == "odd" else 0.0)
            rows.append({**spec, "states": states})
        self.assertFalse(primary.scientific_metrics(rows, stage)["history_geometry_pass"])

    def test_launcher_has_separate_offline_run_and_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_value_d2.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_D2_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
