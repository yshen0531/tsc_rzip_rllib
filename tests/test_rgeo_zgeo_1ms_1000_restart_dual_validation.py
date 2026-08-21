from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_restart_dual_validation as stage


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_restart_dual_validation.json"
CONFIG_R1 = ROOT / "configs/rgeo_zgeo_1ms_1000_restart_dual_validation_r1.json"


class Fixed1000DualRestartValidationTest(unittest.TestCase):
    def test_identity_budget_and_distinct_restart_pair(self):
        row = stage.load_contract(CONFIG)
        self.assertEqual(row["route_prefix"], "ONE_MS_NR1000S0R3")
        self.assertEqual(row["replays_per_root"], 2)
        self.assertEqual(row["maximum_tsc_invocations"], 4)
        self.assertEqual(len(row["source_config_sha256"]), 64)
        left = row["reconstructed_roots"]["r0"]["files"]["sprsoua"]
        right = row["reconstructed_roots"]["r1"]["files"]["sprsoua"]
        self.assertEqual(left["bytes"], right["bytes"])
        self.assertNotEqual(left["sha256"], right["sha256"])

    def test_prior_failure_is_hash_and_route_bound(self):
        row = stage.load_contract(CONFIG)["r2r2_result"]
        self.assertEqual(len(row["sha256"]), 64)
        self.assertEqual(row["route"], "ONE_MS_NR1000S0R2R2_INITIAL_RECONSTRUCTION_FAIL")
        self.assertEqual(row["tsc_invocations"], 2)

    def test_r1_separates_issued_and_actual_current_coordinates(self):
        row = stage.load_contract(CONFIG_R1)
        self.assertEqual(row["route_prefix"], "ONE_MS_NR1000S0R3R1")
        self.assertEqual(
            row["issued_slew_coordinate"],
            "active_card15_command_to_issued_target",
        )
        self.assertEqual(
            row["source_to_successor_actual_delta_role"],
            "descriptive_not_issued_slew",
        )
        self.assertEqual(row["r3_result"]["tsc_invocations"], 1)
        self.assertEqual(len(row["r3_result"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
