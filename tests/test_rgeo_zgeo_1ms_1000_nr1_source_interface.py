import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_nr1_independent as independent
from scripts import rgeo_zgeo_1ms_nr1_qualification as primary
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import validate_one_ms_config
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_nr1_source_interface.json"
CONFIG_R4 = ROOT / "configs/rgeo_zgeo_1ms_1000_nr1_interface_r4.json"
CONFIG_R4R1 = ROOT / "configs/rgeo_zgeo_1ms_1000_nr1_interface_r4r1.json"


class Fixed1000SourceInterfaceTest(unittest.TestCase):
    def test_identity_is_separate_and_exact(self):
        row = primary._profile(CONFIG)
        self.assertEqual(row["takeover_time_ms"], 1000)
        self.assertEqual(row["campaign_id"], "rgeo_zgeo_1ms_1000_nr1_source_interface_v2")
        self.assertEqual(row["intended_use"], "interface_validation")
        self.assertEqual(row["route_prefix"], "ONE_MS_NR1000S1R1")
        self.assertEqual(independent._profile(CONFIG)["takeover_time_ms"], 1000)

    def test_source_identity_is_complete(self):
        row = json.loads(CONFIG.read_text(encoding="utf-8"))
        files = row["source_identity"]["files"]
        self.assertEqual(set(files), {
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv",
            "sprsina", "outputa",
        })
        self.assertTrue(all(len(value["sha256"]) == 64 and value["bytes"] > 0
                            for value in files.values()))
        state = row["source_identity"]["expected_state"]
        self.assertEqual(state["time_ms"], 1000)
        self.assertEqual(state["point_count"], 278)
        self.assertEqual(state["wire_count"], 48)
        self.assertEqual(row["start_folder"], "1000ms")

    def test_command_center_is_not_replaced_by_actual_current(self):
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(payload["source_command_contract"], {
            "command_center": "active_source_card15",
            "effect_evaluation": "matched_hold_state1_differential",
            "return_evaluation": "exact_card15_command_center",
        })

    def test_matched_hold_differential_checks_all_components(self):
        state = lambda values: {
            "actual_current_decimal_a_tsc": [str(value) for value in values]
        }
        hold = [state([0] * 14), state([1] * 14)] + [state([1] * 14)] * 3
        probe = [state([0] * 14), state([2] * 14)] + [state([1] * 14)] * 3

        class Target:
            card15_fields = tuple(" 1.000E-01" for _ in range(14))

        result = primary._matched_hold_effect(
            probe, hold, Target(), tuple(0 for _ in range(14)),
            tuple(1000 for _ in range(14)),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["component_checks"], 14)

    def test_explicit_takeover_override_preserves_legacy_default(self):
        validate_one_ms_config(start_folder="1000ms", dt_ms=1,
                               slew_a_per_ms=.3,
                               expected_start_folder="1000ms")
        with self.assertRaises(ContractError):
            validate_one_ms_config(start_folder="1000ms", dt_ms=1,
                                   slew_a_per_ms=.3)

    def test_r4_binds_qualified_reconstruction_and_matched_hold(self):
        row = json.loads(CONFIG_R4.read_text(encoding="utf-8"))
        profile = primary._profile(CONFIG_R4)
        self.assertEqual(profile["route_prefix"], "ONE_MS_NR1000S1R4")
        self.assertTrue(profile["matched_hold_effect"])
        self.assertEqual(
            row["source_identity"]["files"]["sprsina"]["sha256"],
            "de986e49cd2466e67a89567214c3ed988f3808b36924243accd2d82709d79145",
        )
        self.assertEqual(
            row["prerequisite"]["authorization"],
            "FRESH_1000MS_NR1_INTERFACE_DESIGN_ONLY",
        )

    def test_r4r1_reserves_readback_margin_without_weakening_hard_slew(self):
        row = json.loads(CONFIG_R4R1.read_text(encoding="utf-8"))
        self.assertEqual(row["qualification_command_slew_a"], 0.299)
        self.assertEqual(row["current_slew_a_per_ms"], 0.3)
        self.assertEqual(primary._profile(CONFIG_R4R1)["route_prefix"], "ONE_MS_NR1000S1R4R1")
        self.assertEqual(row["prior_failed_campaign"]["plant_advances"], 10)


if __name__ == "__main__":
    unittest.main()
