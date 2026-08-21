import copy
from pathlib import Path
import unittest
import numpy as np
from scripts import rgeo_zgeo_1ms_1000_feedback_f0 as f0


class FeedbackF0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.baseline, cls.d1_stage, cls.artifact = f0.load(f0.DEFAULT_CONFIG)

    def test_identity_budget(self):
        self.assertEqual(f0.b0.sha256(f0.DEFAULT_CONFIG), f0.CONFIG_SHA256)
        self.assertEqual(len(f0.specs(self.stage)), 4)
        self.assertEqual(self.stage["maximum_advance_attempts"], 256)
        self.assertEqual(self.stage["decision_issues"], [24, 36, 48])

    def test_selector_minimizes_checkpoint_error(self):
        candidate, before, after = f0.select(self.stage, self.artifact, np.zeros(2), np.asarray([.28, 0]))
        self.assertEqual(candidate, "even_minus")
        self.assertLess(after, before)
        candidate, before, after = f0.select(self.stage, self.artifact, np.zeros(2), np.asarray([0, -.90]))
        self.assertEqual(candidate, "odd_minus")
        self.assertLess(after, before)

    def test_synthetic_exact_checkpoint_metrics(self):
        q0 = copy.deepcopy(self.baseline)
        q0["decisions"] = []
        rows = {"q0_baseline": copy.deepcopy(q0)}
        for path in ("path_a", "path_b"):
            row = copy.deepcopy(q0)
            row["decisions"] = []
            for ordinal, issue in enumerate(self.stage["decision_issues"]):
                command = np.asarray(self.stage["paths_mm_relative_q0"][path][ordinal])
                candidate, before, after = f0.select(self.stage, self.artifact, np.zeros(2), command)
                row["decisions"].append({"candidate": candidate,
                    "predicted_error_before_mm": before, "predicted_error_after_mm": after})
                endpoint = self.stage["endpoint_states"][ordinal]
                row["states"][endpoint]["r_geo_m"] += command[0] / 1000
                row["states"][endpoint]["z_geo_m"] += command[1] / 1000
            rows[path] = row
        rows["path_a_replay"] = copy.deepcopy(rows["path_a"])
        self.assertTrue(f0.metrics(rows, self.stage, self.baseline, self.artifact)["passed"])
        rows["path_b"]["states"][56]["r_geo_m"] += .001
        self.assertFalse(f0.metrics(rows, self.stage, self.baseline, self.artifact)["passed"])

    def test_zero_fit_and_launcher(self):
        self.assertEqual(self.stage["data_roles"]["path_rows"],
                         "finite_feedback_qualification_only_zero_fit_weight")
        launcher = (Path(__file__).resolve().parents[1] /
                    "run_rgeo_zgeo_1ms_1000_feedback_f0.sh").read_text(encoding="utf-8")
        self.assertIn("offline|run|audit", launcher)

if __name__ == "__main__":
    unittest.main()
