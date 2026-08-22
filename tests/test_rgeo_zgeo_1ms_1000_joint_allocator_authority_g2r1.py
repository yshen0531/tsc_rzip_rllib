from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1 as primary
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1.json"


class Fixed1000JointAllocatorAuthorityG2R1Test(unittest.TestCase):
    def test_frozen_amendment_and_parent_failure(self) -> None:
        amendment = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(amendment["lattice_correction"]["vertical_single_turn_increment_a"], 0.06)
        self.assertEqual(amendment["lattice_correction"]["maximum_exact_issued_slew_a"], 0.21)
        self.assertEqual(amendment["lattice_correction"]["minimum_nominal_readback_reserve_a"], 0.09)
        failed = json.loads((ROOT / amendment["failed_parent_offline_path"]).read_text(encoding="utf-8"))
        self.assertFalse(failed["passed"])
        self.assertEqual(failed["route"], amendment["failed_parent_route"])

    def test_parent_semantics_except_lattice_and_identity_are_unchanged(self) -> None:
        stage, _, _ = primary.load(CONFIG)
        parent = json.loads((ROOT / "configs/rgeo_zgeo_1ms_1000_joint_allocator_authority_g2.json").read_text(encoding="utf-8"))
        for key in ("radial_policy", "vertical_policy", "scientific_gates", "rollout_ids", "data_roles"):
            self.assertEqual(stage[key], parent[key])
        self.assertEqual(stage["rollouts"], 5)
        self.assertEqual(stage["maximum_advance_attempts"], 320)

    def test_exact_lattice_and_all_branch_streams_pass(self) -> None:
        stage, cfg, _ = primary.load(CONFIG)
        source = _source(cfg)
        geometry = primary.targets(stage, cfg, source)["action_geometry"]
        self.assertEqual(geometry["rank"], 2)
        self.assertAlmostEqual(geometry["maximum_exact_adjacent_slew_a"], 0.20833333333333334, places=15)
        self.assertLessEqual(geometry["maximum_exact_adjacent_slew_a"], 0.21)
        self.assertGreaterEqual(geometry["minimum_nominal_readback_reserve_a"], 0.09)
        preflight = primary.offline(CONFIG, "test-revision")
        self.assertTrue(preflight["passed"], preflight["failures"])
        self.assertEqual(preflight["route"], "ONE_MS_NR1000G2R1_OFFLINE_PASS_RUN_ONLY")
        self.assertEqual(len(preflight["enumerated_branch_streams"]), 25)
        self.assertTrue(all(len(row["actions"]) == 64 for row in preflight["enumerated_branch_streams"]))

    def test_profiles_and_rollout_matrix_are_unchanged(self) -> None:
        stage, _, _ = primary.load(CONFIG)
        self.assertEqual([row["rollout_id"] for row in primary.rollout_specs(stage)], stage["rollout_ids"])
        self.assertEqual(primary.radial_levels_for_switch(stage, 4)[:4], [-1, -2, -3, -4])
        self.assertEqual(primary.radial_levels_for_switch(stage, 8)[-1], 32)
        self.assertEqual(primary.vertical_levels(stage, (1, -1))[8:20], [1,2,3,4,4,4,4,4,3,2,1,0])

    def test_launcher_exposes_only_offline_run_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_joint_allocator_authority_g2r1.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_G2R1_SOURCE_REVISION", text)
        for mode in ("offline)", "run)", "audit)"):
            self.assertIn(mode, text)


if __name__ == "__main__":
    unittest.main()
