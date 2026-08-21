from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_value_c0 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_c0.json"


def state(index: int, r_mm: float = 0.0, z_mm: float = 0.0, ip_a: float = 0.0) -> dict:
    return {"time_ms": 1000 + index, "r_geo_m": 0.7 + r_mm / 1000.0,
            "z_geo_m": z_mm / 1000.0, "r_mid_m": 0.79, "ip_a": 30000.0 + ip_a}


def synthetic_rows(stage: dict, artifact: dict, offset_mm: float = 0.0) -> list[dict]:
    rows = []
    for spec in primary.rollout_specs(stage):
        if spec["repeat_index"]:
            continue
        states = [state(index) for index in range(49)]
        if spec["candidate"] != "baseline":
            for horizon in (4, 8):
                center = artifact["model"]["candidates"][spec["candidate"]][str(horizon)]["center_rz_ip"]
                states[stage["candidate_issue_phase"] + horizon] = state(
                    stage["candidate_issue_phase"] + horizon,
                    center[0] + offset_mm, center[1], center[2])
        rows.append({**spec, "states": states})
    return rows


class Fixed1000ValueC0Test(unittest.TestCase):
    def test_frozen_identity_budget_and_evidence(self) -> None:
        stage, _, _, _, artifact = primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(stage["conditioners"], ["even_minus", "odd_minus"])
        self.assertEqual(stage["rollouts"], 12)
        self.assertEqual(stage["maximum_advance_attempts"], 576)
        self.assertEqual(stage["data_roles"]["v0_artifact"], "frozen_read_only_no_refit")
        self.assertEqual(artifact["qualification"],
                         "development_only_fresh_calibration_and_blind_history_required")

    def test_matrix_has_ten_zero_fit_calibration_rows_and_two_replays(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(stage)
        self.assertEqual(sum(row["repeat_index"] == 0 for row in rows), 10)
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 2)
        self.assertTrue(all("fit" not in row["data_role"] or "zero_fit" in row["data_role"]
                            for row in rows))

    def test_negative_conditioner_and_candidate_macros_do_not_overlap(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        levels = {f"{axis}_{sign}_level{level}": f"{axis}_{sign}_{level}"
                  for axis in ("even", "odd") for sign in ("plus", "minus")
                  for level in range(1, 5)}
        target_map = {"q0": "q0", **levels}
        spec = next(row for row in primary.rollout_specs(stage)
                    if row["conditioner"] == "even_minus" and row["candidate"] == "odd_plus")
        sequence = primary.d2.sequence_for(spec, stage, target_map)
        expected_conditioner = [f"even_minus_{level}" if level else "q0"
                                for level in primary.d2.MACRO_LEVELS]
        expected_candidate = [f"odd_plus_{level}" if level else "q0"
                              for level in primary.d2.MACRO_LEVELS]
        self.assertEqual(sequence[8:20], expected_conditioner)
        self.assertEqual(sequence[24:36], expected_candidate)
        self.assertTrue(all(value == "q0" for value in sequence[20:24] + sequence[36:]))

    def test_fixed_artifact_accepts_centered_fresh_histories(self) -> None:
        stage, _, _, _, artifact = primary.load(CONFIG)
        metrics = primary.calibration_metrics(synthetic_rows(stage, artifact), stage, artifact)
        self.assertTrue(metrics["passed"])
        self.assertEqual([row["contained_components"] for row in metrics["histories"]], [24, 24])

    def test_fixed_artifact_rejects_uncontained_component_without_refit(self) -> None:
        stage, _, _, _, artifact = primary.load(CONFIG)
        metrics = primary.calibration_metrics(synthetic_rows(stage, artifact, offset_mm=0.2), stage, artifact)
        self.assertFalse(metrics["passed"])
        self.assertFalse(metrics["containment_pass"])

    def test_launcher_has_separate_offline_run_and_independent_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_value_c0.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_C0_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
