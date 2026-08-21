from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_baseline_b0 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_baseline_b0.json"


def state(index: int) -> dict:
    return {
        "time_ms": 1000 + index,
        "r_geo_m": 0.7 + index * 1e-5,
        "z_geo_m": -index * 2e-5,
        "r_mid_m": 0.79,
        "ip_a": 30000.0 + index,
        "actual_current_a_tsc": [float(index)] * 14,
        "wire_current_a": [float(index)] * 48,
        "artifact_sha256": {
            "inputa": "a", "geqdsk": "b", "coil_currents.csv": "c",
            "wire_currents.csv": "d", "sprsina": str(index),
        },
    }


class Fixed1000BaselineB0Test(unittest.TestCase):
    def test_frozen_identity_and_budget(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(payload["takeover_time_ms"], 1000)
        self.assertEqual(payload["horizon_steps"], 64)
        self.assertEqual(payload["rollouts"], 2)
        self.assertEqual(payload["maximum_advance_attempts"], 128)
        self.assertEqual(payload["retry_after_any_advance_attempt"], "forbidden")

    def test_data_roles_prevent_replay_double_weighting(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["data_roles"]["baseline_primary"],
            "development_fit_eligible_baseline_weight_1",
        )
        self.assertEqual(
            payload["data_roles"]["baseline_replay"],
            "integrity_replay_zero_fit_weight",
        )
        self.assertEqual(payload["data_roles"]["calibration"], "unopened")
        self.assertEqual(payload["data_roles"]["holdout"], "unopened")

    def test_drift_metrics_use_exact_64ms_and_last_8ms_windows(self) -> None:
        metrics = primary.drift_metrics([state(index) for index in range(65)])
        self.assertEqual(metrics["terminal_state_index"], 64)
        self.assertEqual(metrics["terminal_time_ms"], 1064)
        self.assertAlmostEqual(metrics["terminal_source_delta"]["r_mm"], 0.64)
        self.assertAlmostEqual(metrics["terminal_source_delta"]["z_mm"], -1.28)
        self.assertAlmostEqual(metrics["last_8ms_net_delta"]["r_mm"], 0.08)
        self.assertAlmostEqual(metrics["last_8ms_net_delta"]["z_mm"], -0.16)

    def test_replay_comparison_ignores_sprsina_but_not_semantic_artifacts(self) -> None:
        left = {"states": [state(index) for index in range(65)]}
        right = {"states": [state(index) for index in range(65)]}
        for row in right["states"]:
            row["artifact_sha256"]["sprsina"] = "different"
        self.assertTrue(primary.compare_replay(left, right)["passed"])
        right["states"][10]["artifact_sha256"]["geqdsk"] = "changed"
        self.assertFalse(primary.compare_replay(left, right)["passed"])

    def test_launcher_exposes_only_offline_run_and_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_baseline_b0.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_B0_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
