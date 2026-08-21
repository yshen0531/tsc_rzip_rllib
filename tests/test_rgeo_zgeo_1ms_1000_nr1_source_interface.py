import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_nr1_independent as independent
from scripts import rgeo_zgeo_1ms_nr1_qualification as primary
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr1 import validate_one_ms_config
from tsc_rzip_rllib.control.rgeo_zgeo_contract import ContractError


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_nr1_source_interface.json"


class Fixed1000SourceInterfaceTest(unittest.TestCase):
    def test_identity_is_separate_and_exact(self):
        row = primary._profile(CONFIG)
        self.assertEqual(row["takeover_time_ms"], 1000)
        self.assertEqual(row["campaign_id"], "rgeo_zgeo_1ms_1000_nr1_source_interface_v1")
        self.assertEqual(row["route_prefix"], "ONE_MS_NR1000S1")
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

    def test_explicit_takeover_override_preserves_legacy_default(self):
        validate_one_ms_config(start_folder="1000ms", dt_ms=1,
                               slew_a_per_ms=.3,
                               expected_start_folder="1000ms")
        with self.assertRaises(ContractError):
            validate_one_ms_config(start_folder="1000ms", dt_ms=1,
                                   slew_a_per_ms=.3)


if __name__ == "__main__":
    unittest.main()
