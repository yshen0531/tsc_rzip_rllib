import copy
from pathlib import Path
import unittest
import numpy as np
from scripts import rgeo_zgeo_1ms_1000_feedback_f1 as f1


class FeedbackF1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.baseline, cls.d1_stage, cls.artifact = f1.load(f1.DEFAULT_CONFIG)

    def test_identity_budget_and_no_refit(self):
        self.assertEqual(f1.f0.b0.sha256(f1.DEFAULT_CONFIG), f1.CONFIG_SHA256)
        self.assertEqual(len(f1.specs(self.stage)), 4)
        self.assertEqual(self.stage["maximum_advance_attempts"], 256)
        self.assertEqual(self.stage["data_roles"]["v0_artifact"],
                         "frozen_read_only_no_refit_or_widening")

    def test_deadband_selects_noop_and_outside_requires_progress(self):
        candidate, before, after = f1.select(
            self.stage, self.artifact, np.asarray([-.1483775, -1.049926]),
            np.asarray([-.3, -.75]))
        self.assertEqual(candidate, "q0_noop")
        self.assertEqual(before, after)
        candidate, before, after = f1.select(
            self.stage, self.artifact, np.zeros(2), np.asarray([.28, 0]))
        self.assertEqual(candidate, "even_minus")
        self.assertLess(after, before)

    def test_outside_deadband_without_improvement_refuses(self):
        candidate, before, after = f1.select(
            self.stage, self.artifact, np.zeros(2), np.asarray([0.0, .36]))
        self.assertIsNone(candidate)
        self.assertGreaterEqual(after, before)

    def test_synthetic_metrics_include_state64(self):
        q0 = copy.deepcopy(self.baseline)
        q0["decisions"] = []
        rows = {"q0_baseline": copy.deepcopy(q0)}
        for path in ("path_a", "path_b"):
            row = copy.deepcopy(q0)
            row["decisions"] = []
            for ordinal, issue in enumerate(self.stage["decision_issues"]):
                command = np.asarray(self.stage["paths_mm_relative_q0"][path][ordinal])
                candidate, before, after = f1.select(
                    self.stage, self.artifact, np.zeros(2), command)
                if candidate is None:
                    candidate, before, after = "q0_noop", .1, .1
                row["decisions"].append({"candidate": candidate,
                    "predicted_error_before_mm": before, "predicted_error_after_mm": after})
                endpoint = self.stage["endpoint_states"][ordinal]
                row["states"][endpoint]["r_geo_m"] += command[0] / 1000
                row["states"][endpoint]["z_geo_m"] += command[1] / 1000
            command = np.asarray(self.stage["paths_mm_relative_q0"][path][-1])
            row["states"][64]["r_geo_m"] += command[0] / 1000
            row["states"][64]["z_geo_m"] += command[1] / 1000
            rows[path] = row
        rows["path_a_replay"] = copy.deepcopy(rows["path_a"])
        self.assertTrue(f1.metrics(rows, self.stage, self.baseline, self.artifact)["passed"])
        rows["path_b"]["states"][64]["r_geo_m"] += .001
        self.assertFalse(f1.metrics(rows, self.stage, self.baseline, self.artifact)["passed"])

    def test_launcher_modes(self):
        launcher = (Path(__file__).resolve().parents[1] /
                    "run_rgeo_zgeo_1ms_1000_feedback_f1.sh").read_text(encoding="utf-8")
        self.assertIn("offline|run|audit", launcher)


if __name__ == "__main__":
    unittest.main()
