from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_radial_nominal_n0 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_radial_nominal_n0.json"


def state(index: int, r_mm: float, speed_mm_per_step: float, ip_fraction: float = 0.0) -> dict:
    return {
        "time_ms": 1000 + index,
        "r_geo_m": 0.7 + (r_mm + speed_mm_per_step * index) / 1000.0,
        "z_geo_m": 0.0,
        "r_mid_m": 0.79,
        "ip_a": 30000.0 * (1.0 + ip_fraction),
    }


def replay_state(index: int) -> dict:
    row = state(index, 0.0, -0.3)
    row.update({
        "actual_current_a_tsc": [0.0] * 14,
        "wire_current_a": [0.0] * 48,
        "artifact_sha256": {name: "same" for name in primary.SEMANTIC_ARTIFACTS},
    })
    return row


class Fixed1000RadialNominalN0Test(unittest.TestCase):
    def test_frozen_identity_budget_and_roles(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(payload["candidate_depths"], [4, 8, 12, 16])
        self.assertEqual(payload["maximum_advance_attempts"], 320)
        self.assertEqual(payload["retry_after_any_advance_attempt"], "forbidden")
        self.assertEqual(payload["data_roles"]["critical_replay"], "integrity_only_zero_fit_weight")
        self.assertEqual(payload["data_roles"]["calibration"], "unopened")
        self.assertEqual(payload["data_roles"]["holdout"], "unopened")

    def test_rollout_matrix_and_sequence(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(payload)
        self.assertEqual(len(rows), 5)
        self.assertEqual(sum(row["repeat_index"] == 0 for row in rows), 4)
        target_map = {f"level{level}": level for level in range(1, 17)}
        sequence = primary.sequence_for(rows[1], payload, target_map)
        self.assertEqual(sequence[:10], [1, 2, 3, 4, 5, 6, 7, 8, 8, 8])
        self.assertEqual(sequence[-1], 8)

    def test_scientific_metrics_require_distance_and_speed_utility(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        baseline = [state(index, 0.0, -0.30) for index in range(65)]
        rows = []
        speeds = {4: -0.29, 8: -0.27, 12: -0.24, 16: -0.20}
        for spec in primary.rollout_specs(payload):
            if spec["repeat_index"]:
                continue
            rows.append({**spec, "states": [state(index, 0.0, speeds[spec["depth"]]) for index in range(65)]})
        metrics = primary.scientific_metrics(rows, baseline, payload)
        self.assertTrue(metrics["passed"])
        self.assertEqual(metrics["best_candidate"]["depth"], 16)

        for row in rows:
            row["states"] = [state(index, 0.0, -0.29) for index in range(65)]
        self.assertFalse(primary.scientific_metrics(rows, baseline, payload)["passed"])

    def test_replay_comparison_uses_n0_cardinality(self) -> None:
        row = {"states": [replay_state(index) for index in range(65)], "actions": list(range(64))}
        self.assertTrue(primary.compare_rows(row, json.loads(json.dumps(row)))["passed"])
        short = {"states": row["states"][:-1], "actions": row["actions"][:-1]}
        self.assertEqual(
            set(primary.compare_rows(short, json.loads(json.dumps(short)))["failures"]),
            {"STATE_COUNT", "ACTION_COUNT"},
        )

    def test_launcher_exposes_only_offline_run_and_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_radial_nominal_n0.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_N0_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
