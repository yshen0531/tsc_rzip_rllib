from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_joint_allocator_authority_g2 as primary
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2.json"


class Fixed1000JointAllocatorAuthorityG2Test(unittest.TestCase):
    def test_frozen_identity_roles_and_budget(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(stage["rollouts"], 5)
        self.assertEqual(stage["maximum_advance_attempts"], 320)
        self.assertEqual(stage["retry_after_any_advance_attempt"], "forbidden")
        self.assertEqual(stage["lattice"]["maximum_exact_issued_slew_a"], 0.25)
        self.assertEqual(stage["lattice"]["maximum_hard_observed_slew_a"], 0.3)
        self.assertEqual(stage["data_roles"]["primary_active_paths"],
                         "authority_qualification_only_zero_fit_weight")

    def test_rollout_matrix_has_reference_three_active_and_replay(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(stage)
        self.assertEqual([row["rollout_id"] for row in rows], stage["rollout_ids"])
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 1)
        self.assertEqual(sum(row["kind"] == "active" and row["repeat_index"] == 0 for row in rows), 3)

    def test_static_radial_and_vertical_profiles_close(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        for switch in range(4, 9):
            radial = primary.radial_levels_for_switch(stage, switch)
            self.assertEqual(radial[:4], [-1, -2, -3, -4])
            self.assertEqual(radial[-1], 32)
            self.assertLessEqual(max(abs(right - left) for left, right in zip([0] + radial[:-1], radial)), 1)
        vertical = primary.vertical_levels(stage, (1, -1))
        self.assertEqual(vertical[8:20], [1, 2, 3, 4, 4, 4, 4, 4, 3, 2, 1, 0])
        self.assertEqual(vertical[28:40], [-1, -2, -3, -4, -4, -4, -4, -4, -3, -2, -1, 0])
        self.assertEqual(vertical[-1], 0)

    def test_radial_switch_reads_current_state(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        level, phase, switched, inward = primary._next_radial_level(
            stage, 4, -4, "initial_minus", 0.7301, 0.7310
        )
        self.assertEqual((level, phase, switched), (-4, "await_switch", False))
        self.assertAlmostEqual(inward, 0.9)
        level, phase, switched, inward = primary._next_radial_level(
            stage, 5, -4, phase, 0.7299, 0.7310
        )
        self.assertEqual((level, phase, switched), (-3, "brake", True))
        self.assertAlmostEqual(inward, 1.1)

    def test_server_exact_lattice_and_all_branch_streams(self) -> None:
        stage, cfg, _ = primary.load(CONFIG)
        source = _source(cfg)
        target_map = primary.targets(stage, cfg, source)
        geometry = target_map["action_geometry"]
        self.assertEqual(geometry["rank"], 2)
        self.assertLessEqual(geometry["maximum_exact_adjacent_slew_a"], 0.25)
        self.assertGreaterEqual(geometry["minimum_nominal_readback_reserve_a"], 0.05)
        preflight = primary.offline(CONFIG, "test-revision")
        self.assertTrue(preflight["passed"], preflight["failures"])
        self.assertEqual(len(preflight["enumerated_branch_streams"]), 25)
        self.assertTrue(all(len(row["actions"]) == 64 for row in preflight["enumerated_branch_streams"]))

    def test_launcher_exposes_only_three_modes(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_joint_allocator_authority_g2.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_G2_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
