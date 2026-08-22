from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_absolute_radial_authority_g0 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_absolute_radial_authority_g0.json"


def trajectory(speed_m_per_s: float, ip_fraction: float = 0.0) -> list[dict]:
    return [{
        "time_ms": 1000 + index,
        "r_geo_m": 0.7316591665 - speed_m_per_s * index * 0.001,
        "z_geo_m": 0.0,
        "r_mid_m": 0.7919,
        "ip_a": 30000.0 * (1.0 + ip_fraction * index / 64.0),
    } for index in range(65)]


class Fixed1000AbsoluteRadialAuthorityG0Test(unittest.TestCase):
    def test_identity_budget_and_roles_are_frozen(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(stage["candidate_depths"], [4, 8, 12, 16, 24, 32])
        self.assertEqual(stage["rollouts"], 8)
        self.assertEqual(stage["maximum_advance_attempts"], 512)
        self.assertEqual(stage["retry_after_any_advance_attempt"], "forbidden")
        self.assertEqual(stage["data_roles"]["calibration"], "unopened")
        self.assertEqual(stage["data_roles"]["holdout"], "unopened")
        self.assertEqual(stage["data_roles"]["controller_or_recourse"], "forbidden")

    def test_rollout_matrix_has_matched_q0_six_candidates_and_one_replay(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(stage)
        self.assertEqual(rows[0]["rollout_id"], "matched_q0")
        self.assertEqual(sum(row["kind"] == "even_plus" and row["repeat_index"] == 0 for row in rows), 6)
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 1)
        target_map = {"q0": 0, **{f"level{level}": level for level in range(1, 33)}}
        self.assertEqual(primary.sequence_for(rows[0], stage, target_map), [0] * 64)
        depth8 = next(row for row in rows if row["rollout_id"] == "depth08")
        self.assertEqual(primary.sequence_for(depth8, stage, target_map)[:10], [1,2,3,4,5,6,7,8,8,8])
        self.assertEqual(primary.sequence_for(depth8, stage, target_map)[-1], 8)

    def test_terminal_science_requires_distance_speed_and_ip(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = [{
            "rollout_id": "matched_q0", "kind": "matched_q0", "depth": 0,
            "repeat_index": 0, "states": trajectory(0.30),
        }]
        for depth, speed in zip(stage["candidate_depths"], (0.29, 0.28, 0.27, 0.24, 0.20, 0.18)):
            rows.append({
                "rollout_id": f"depth{depth:02d}", "kind": "even_plus", "depth": depth,
                "repeat_index": 0, "states": trajectory(speed),
            })
        rows.append({**rows[4], "rollout_id": "depth16_replay", "repeat_index": 1})
        metrics = primary.scientific_metrics(rows, stage)
        self.assertTrue(metrics["passed"])
        self.assertEqual(metrics["selected_eligible_candidate"]["depth"], 32)

        for row in rows[1:]:
            row["states"] = trajectory(0.29)
        self.assertFalse(primary.scientific_metrics(rows, stage)["passed"])

        rows[-2]["states"] = trajectory(0.18, ip_fraction=0.051)
        metrics = primary.scientific_metrics(rows, stage)
        self.assertFalse(next(row for row in metrics["candidates"] if row["depth"] == 32)["utility_pass"])

    def test_launcher_exposes_only_offline_run_and_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_absolute_radial_authority_g0.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("NR1000_G0_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
