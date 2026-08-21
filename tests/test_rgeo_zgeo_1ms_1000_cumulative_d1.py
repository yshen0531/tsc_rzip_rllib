from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_cumulative_d1 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_cumulative_d1.json"


def state(index: int, r_mm: float = 0.0, z_mm: float = 0.0, ip_a: float = 0.0) -> dict:
    return {
        "time_ms": 1000 + index, "r_geo_m": 0.7 + r_mm / 1000.0,
        "z_geo_m": z_mm / 1000.0, "r_mid_m": 0.79, "ip_a": 30000.0 + ip_a,
    }


class Fixed1000CumulativeD1Test(unittest.TestCase):
    def test_frozen_identity_budget_and_roles(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(payload["issue_phases"], [8, 24])
        self.assertEqual(payload["rollouts"], 10)
        self.assertEqual(payload["maximum_advance_attempts"], 480)
        self.assertEqual(payload["retry_after_any_advance_attempt"], "forbidden")
        self.assertEqual(payload["data_roles"]["critical_replays"], "integrity_only_zero_fit_weight")
        self.assertEqual(payload["data_roles"]["calibration"], "unopened")
        self.assertEqual(payload["data_roles"]["holdout"], "unopened")

    def test_rollout_matrix_has_eight_primary_and_two_zero_weight_replays(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(payload)
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(row["repeat_index"] == 0 for row in rows), 8)
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 2)

    def test_sequence_is_ramp_plateau_exact_return_and_tail(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        spec = primary.rollout_specs(payload)[0]
        target_map = {"q0": 0, **{f"even_plus_level{level}": level for level in range(1, 5)}}
        sequence = primary.sequence_for(spec, payload, target_map)
        self.assertEqual(sequence[8:20], [1, 2, 3, 4, 4, 4, 4, 4, 3, 2, 1, 0])
        self.assertTrue(all(value == 0 for value in sequence[:8] + sequence[20:]))

    def test_scientific_metrics_pass_clean_sustained_two_axis_response(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        baseline = [state(index) for index in range(49)]
        rows = []
        for spec in primary.rollout_specs(payload):
            if spec["repeat_index"]:
                continue
            states = [state(index) for index in range(49)]
            sign = 1.0 if spec["sign"] == "plus" else -1.0
            for horizon, magnitude in ((4, 0.20), (8, 0.30), (12, 0.05), (16, 0.02)):
                index = spec["issue_phase"] + horizon
                if spec["axis"] == "even":
                    states[index] = state(index, r_mm=magnitude * sign)
                else:
                    states[index] = state(index, z_mm=magnitude * sign)
            rows.append({**spec, "states": states})
        metrics = primary.scientific_metrics(rows, baseline, payload)
        self.assertTrue(metrics["passed"])
        self.assertTrue(metrics["return_tail_pass"])

    def test_scientific_metrics_reject_unbounded_return_tail(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        baseline = [state(index) for index in range(49)]
        rows = []
        for spec in primary.rollout_specs(payload):
            if spec["repeat_index"]:
                continue
            states = [state(index) for index in range(49)]
            sign = 1.0 if spec["sign"] == "plus" else -1.0
            for horizon, magnitude in ((4, 0.20), (8, 0.30), (12, 4.0), (16, 4.0)):
                index = spec["issue_phase"] + horizon
                if spec["axis"] == "even":
                    states[index] = state(index, r_mm=magnitude * sign)
                else:
                    states[index] = state(index, z_mm=magnitude * sign)
            rows.append({**spec, "states": states})
        metrics = primary.scientific_metrics(rows, baseline, payload)
        self.assertFalse(metrics["return_tail_pass"])
        self.assertFalse(metrics["passed"])

    def test_launcher_exposes_only_offline_run_and_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_cumulative_d1.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_D1_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
