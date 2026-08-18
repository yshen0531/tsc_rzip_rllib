import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rgeo_zgeo_1ms_id2v0_control_utility_support_audit.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("id2v0_primary", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ID2V0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = MODULE.require_stage()
        cls.result = MODULE.execute(source_revision="test-revision")

    def test_zero_execution_contract(self):
        self.assertEqual(self.result["new_tsc_calls"], 0)
        self.assertEqual(self.result["reset_calls"], 0)
        self.assertEqual(self.result["plant_advances"], 0)
        self.assertEqual(self.result["models_fit_or_trained"], 0)
        self.assertEqual(self.result["calibration_records_read"], 0)
        self.assertEqual(self.result["blind_holdout_records_read"], 0)

    def test_source_counts_and_rank(self):
        self.assertEqual(self.result["independent_history_family_count"], 4)
        self.assertEqual(self.result["probe_cell_count"], 16)
        self.assertEqual(self.result["action_rank"], 3)
        self.assertEqual([row["family_id"] for row in self.result["family_utility"]], list(MODULE.FAMILIES))

    def test_u02_support_is_outside_and_memory_dominated(self):
        row = next(row for row in self.result["support_decomposition"] if row["held_family"] == "u02")
        self.assertFalse(row["supported"])
        self.assertGreater(row["distance"], 900.0)
        self.assertLess(row["support_threshold"], 20.0)
        names = [entry["block"] for entry in self.result["u02_dominant_support_blocks"][:4]]
        self.assertTrue(any(name.startswith("action_memory") for name in names))

    def test_supported_folds_stay_supported(self):
        support = {row["held_family"]: row for row in self.result["support_decomposition"]}
        self.assertTrue(support["u00"]["supported"])
        self.assertTrue(support["u04"]["supported"])
        self.assertTrue(support["u06"]["supported"])

    def test_weak_terminal_control_utility_routes_to_branch_design(self):
        self.assertFalse(self.result["all_families_program_criteria_passed"])
        self.assertEqual(self.result["decision"], "branch_design_required")
        self.assertEqual(
            self.result["route"],
            self.stage["routes"]["branch_design_required"],
        )
        for row in self.result["family_utility"]:
            self.assertLess(row["residual_to_baseline_motion_fraction_by_horizon"][7], 0.01)
            self.assertLess(row["maximum_state40_residual_rz_norm_m"], 0.00002)
            self.assertFalse(row["program_criteria_passed"])

    def test_exact_one_ms_observation_is_not_macro_commitment(self):
        for row in self.result["family_utility"]:
            observation = row["observation_replanning"]
            self.assertEqual(observation["truth_observation_period_ms"], 1)
            self.assertEqual(observation["earliest_new_truth_after_issue_ms"], 1)
            self.assertTrue(observation["macro_commitment_is_not_a_queue_or_observation_delay"])

    def test_unopened_roles_remain_names_only(self):
        source = Path(self.stage["source"]["directory"])
        self.assertFalse(any((ROOT / source).glob("u01*.json")))
        self.assertFalse(any((ROOT / source).glob("u03*.json")))
        self.assertFalse(any((ROOT / source).glob("u05*.json")))
        self.assertFalse(any((ROOT / source).glob("u07*.json")))

    def test_config_is_strict_json(self):
        loaded = json.loads(MODULE.CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(loaded["stage"], "ID-2V0")


if __name__ == "__main__":
    unittest.main()
