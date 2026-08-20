import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/rgeo_zgeo_1ms_id2z19r1_zero_fit_attribution.py"


def load_module():
    spec = importlib.util.spec_from_file_location("id2z19r1_attribution_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


attribution = load_module()


class ID2Z19R1AttributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = attribution.compute()

    def test_frozen_classification(self):
        self.assertTrue(self.value["passed"])
        self.assertEqual(self.value["route"], attribution.ROUTE)
        self.assertEqual(self.value["oof_prediction_row_count"], 9408)
        self.assertEqual(self.value["models_fit_or_updated"], 0)
        self.assertEqual(self.value["new_tsc_calls"], 0)

    def test_terminal_failure_is_not_only_support(self):
        self.assertEqual(len(self.value["candidate_attribution"]), 2)
        for row in self.value["candidate_attribution"]:
            self.assertEqual(row["failure_counts"]["TERMINAL_VELOCITY"], 8)
            self.assertEqual(row["failure_counts"]["TERMINAL_INCREMENT_P95"], 8)
            self.assertGreaterEqual(row["support_pass_fold_count"], 7)
            self.assertGreater(row["terminal_r_above_cap_row_count"], 0)

    def test_tcn_relative_gate_remains_failed(self):
        selection = self.value["selection_diagnostics"]
        self.assertFalse(selection["tcn_relative_selection_gate_passed"])
        self.assertLess(selection["tcn_worst_pair_response_improvement_fraction"], 0.0)
        self.assertGreater(selection["tcn_maximum_componentwise_critical_metric_regression_fraction"], 0.1)

    def test_no_fit_or_future_data_code_path(self):
        text = SCRIPT.read_text(encoding="utf-8").lower()
        self.assertNotIn("torch", text)
        self.assertNotIn("def fit", text)
        self.assertNotIn(".fit(", text)
        self.assertNotIn("gotsc", text)
        self.assertNotIn("c00", text)
        self.assertNotIn("v00", text)


if __name__ == "__main__":
    unittest.main()
