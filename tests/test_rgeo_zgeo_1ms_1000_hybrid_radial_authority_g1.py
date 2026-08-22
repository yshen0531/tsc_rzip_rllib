from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_hybrid_radial_authority_g1 as primary

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_hybrid_radial_authority_g1.json"


class Fixed1000HybridRadialAuthorityG1Test(unittest.TestCase):
    def test_frozen_identity_and_budget(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(stage["initial_minus_depths"], [4, 8, 12, 16])
        self.assertEqual(stage["transition_level_increment_per_issue"], 2)
        self.assertEqual(stage["final_plus_level"], 32)
        self.assertEqual(stage["maximum_advance_attempts"], 384)
        self.assertEqual(stage["retry_after_any_advance_attempt"], "forbidden")

    def test_matrix_and_level_sequences(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(stage)
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["rollout_id"], "matched_q0")
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 1)
        m4 = next(row for row in rows if row["rollout_id"] == "m04_cross_p32")
        levels = primary.level_sequence(m4, stage)
        self.assertEqual(levels[:8], [-1, -2, -3, -4, -2, 0, 2, 4])
        self.assertEqual(levels[-1], 32)
        m16 = next(row for row in rows if row["rollout_id"] == "m16_cross_p32")
        levels16 = primary.level_sequence(m16, stage)
        self.assertEqual(levels16[:16], list(range(-1, -17, -1)))
        self.assertEqual(levels16[16:20], [-14, -12, -10, -8])
        self.assertEqual(levels16[-1], 32)

    def test_launcher_modes(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_hybrid_radial_authority_g1.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_G1_SOURCE_REVISION", text)
        self.assertIn("offline)", text); self.assertIn("run)", text); self.assertIn("audit)", text)


if __name__ == "__main__": unittest.main()
