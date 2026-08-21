from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_value_b1 as primary


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_value_b1.json"


class Fixed1000ValueB1Test(unittest.TestCase):
    def test_frozen_identity_budget_and_zero_fit_roles(self) -> None:
        stage, _, _, _, artifact = primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(stage["conditioner_phases"], [0, 12])
        self.assertEqual(stage["candidate_issue_phase"], 24)
        self.assertEqual(stage["rollouts"], 12)
        self.assertEqual(stage["maximum_advance_attempts"], 576)
        self.assertIn("no_refit", stage["data_roles"]["v0_artifact"])
        self.assertEqual(artifact["model"]["train_contexts"], ["even_plus", "odd_plus", "q0"])

    def test_matrix_has_ten_blind_rows_and_two_replays(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(stage)
        self.assertEqual(sum(row["repeat_index"] == 0 for row in rows), 10)
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 2)
        self.assertEqual({row["history"] for row in rows}, set(stage["histories"]))
        self.assertTrue(all("zero_fit" in row["data_role"] for row in rows))

    def test_two_conditioners_and_candidate_are_contiguous_and_nonoverlapping(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        levels = {f"{axis}_{sign}_level{level}": f"{axis}_{sign}_{level}"
                  for axis in ("even", "odd") for sign in ("plus", "minus")
                  for level in range(1, 5)}
        target_map = {"q0": "q0", **levels}
        spec = next(row for row in primary.rollout_specs(stage)
                    if row["history"] == "even_plus_then_odd_minus"
                    and row["candidate"] == "even_minus")
        sequence = primary.sequence_for(spec, stage, target_map)
        expected = lambda label: [f"{label}_{level}" if level else "q0"
                                  for level in primary.c0.d2.MACRO_LEVELS]
        self.assertEqual(sequence[0:12], expected("even_plus"))
        self.assertEqual(sequence[12:24], expected("odd_minus"))
        self.assertEqual(sequence[24:36], expected("even_minus"))
        self.assertTrue(all(value == "q0" for value in sequence[36:]))

    def test_evaluation_stage_maps_histories_without_changing_gates(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        evaluated = primary.evaluation_stage(stage)
        self.assertEqual(evaluated["conditioners"], list(stage["histories"]))
        self.assertEqual(evaluated["model_calibration_gates"], stage["model_blind_gates"])
        self.assertNotIn("conditioners", stage)

    def test_launcher_has_offline_run_and_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_value_b1.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_B1_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
