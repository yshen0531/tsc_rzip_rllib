import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_restart_reconstruction as stage


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_restart_reconstruction.json"
CONFIG_R2 = ROOT / "configs/rgeo_zgeo_1ms_1000_restart_reconstruction_r2.json"
CONFIG_R2R1 = ROOT / "configs/rgeo_zgeo_1ms_1000_restart_reconstruction_r2r1.json"


class Fixed1000RestartReconstructionTest(unittest.TestCase):
    def test_frozen_identity_and_budget(self):
        row = stage.load_contract(CONFIG)
        self.assertEqual(row["contract_version"], "rgeo-zgeo-1ms-1000-restart-reconstruction-v1")
        self.assertEqual(row["initial_reconstruction_runs"], 2)
        self.assertEqual(row["restart_validation_runs"], 2)
        self.assertEqual(row["restart_validation_steps"], 1)
        self.assertEqual(row["maximum_tsc_invocations"], 4)

    def test_invocation_budget_is_counted_before_call(self):
        counters = {"tsc_invocation_attempts": 0, "tsc_invocations": 0}
        for _ in range(4):
            stage._note_tsc_invocation(counters, 4)
        self.assertEqual(counters, {"tsc_invocation_attempts": 4, "tsc_invocations": 4})
        with self.assertRaises(Exception):
            stage._note_tsc_invocation(counters, 4)
        self.assertEqual(counters, {"tsc_invocation_attempts": 4, "tsc_invocations": 4})

    def test_path_escape_is_rejected(self):
        with self.assertRaises(Exception):
            stage._require_inside_repo(ROOT.parent / "not_the_repo", label="test")

    def test_contaminated_restart_identity_is_explicit(self):
        row = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(row["source_sprsina_sha256"], row["source_1100_sprsina_sha256"])
        self.assertEqual(len(row["source_sprsina_sha256"]), 64)

    def test_r2_binds_full_nonrestart_input(self):
        row = stage.load_contract(CONFIG_R2)
        self.assertEqual(row["route_prefix"], "ONE_MS_NR1000S0R2")
        self.assertEqual(row["initial_source_files"]["inputa"]["bytes"], 13800)
        self.assertEqual(len(row["initial_source_files"]["inputa"]["sha256"]), 64)

    def test_r2r1_changes_only_the_initial_runtime_budget(self):
        r2 = stage.load_contract(CONFIG_R2)
        r2r1 = stage.load_contract(CONFIG_R2R1)
        self.assertEqual(r2r1["route_prefix"], "ONE_MS_NR1000S0R2R1")
        self.assertEqual(r2r1["initial_tsc_timeout_s"], 2700.0)
        for key in set(r2) - {"contract_version", "campaign_id", "route_prefix", "description"}:
            self.assertEqual(r2[key], r2r1[key])

    def test_card00_parser_distinguishes_restart(self):
        self.assertEqual(stage.card00_irst1_text("00  0.0000E+00\n"), 0)
        self.assertEqual(stage.card00_irst1_text("00  1.0000E+00\n"), 1)

    def test_output_time_parser(self):
        text = "special R. Taylor output: cycle= 1 time = 1.0000E+00(s)\n"
        self.assertEqual(stage.output_times_s(text), (1.0,))

    def test_semantic_comparison_detects_change(self):
        left = {"r_geo_m": 1.0, "z_geo_m": 0.0, "r_mid_m": 0.8, "ip_a": 3.0,
                "coil_a": [0.0] * 14, "wire_a": [0.0] * 48}
        right = dict(left)
        right["r_geo_m"] = 1.01
        self.assertIn("R_GEO", stage.semantic_failures(left, right))


if __name__ == "__main__":
    unittest.main()
