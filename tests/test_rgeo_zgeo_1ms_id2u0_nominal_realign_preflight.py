import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


u0 = load("id2u0_primary", SCRIPTS / "rgeo_zgeo_1ms_id2u0_nominal_realign_preflight.py")
independent = load(
    "id2u0_independent",
    SCRIPTS / "rgeo_zgeo_1ms_id2u0_nominal_realign_preflight_independent.py",
)


class ID2U0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.source, cls.targets = u0.load_stage()
        cls.result = u0.execute()

    def test_frozen_zero_plant_zero_fit_identity(self):
        self.assertEqual(u0.sha256(u0.CONFIG), u0.CONFIG_SHA256)
        self.assertEqual(
            (self.stage["new_tsc_calls"], self.stage["reset_calls"],
             self.stage["plant_advances"], self.stage["models_fit_or_trained"],
             self.stage["holdout_records_read"]),
            (0, 0, 0, 0, 0),
        )
        self.assertTrue(all(self.stage["forbidden"].values()))

    def test_selected_nominal_remains_stride_one_not_held(self):
        lineage = self.result["nominal_lineage"]
        self.assertEqual(lineage["selected_candidate_id"], "p03_minus_stride1")
        self.assertEqual(lineage["moving_increment_issues"], list(range(1, 32)))
        self.assertEqual(lineage["issue24_level_difference"], 9)
        self.assertEqual(lineage["issue30_level_difference"], 15)
        self.assertFalse(lineage["held_corridor_is_selected_nominal"])

    def test_state27_event_and_return_edge_contrast_reproduce(self):
        event = self.result["event_map"]
        self.assertEqual(event["primary_probe_cells"], 32)
        self.assertEqual(event["large_response_count"], 16)
        self.assertEqual(event["large_response_state_indices"], [27])
        alignment = self.result["early_late_alignment"]
        self.assertLess(alignment["absolute_r_difference_mm"][1], 0.012)
        self.assertGreater(alignment["absolute_r_difference_mm"][2], 0.73)
        self.assertFalse(alignment["smooth_gain_sign_reversal_claimed"])

    def test_prospective_matrix_and_atomic_roles_are_fixed(self):
        self.assertEqual(self.result["family_count"], 8)
        self.assertEqual(self.result["stream_count"], 40)
        self.assertEqual(
            self.result["role_counts"],
            {"development": 4, "calibration": 2, "blind_holdout": 2},
        )
        grouped = {}
        for stream in self.result["prospective_campaign_streams"]:
            grouped.setdefault(stream["family_id"], []).append(stream)
        self.assertEqual(sorted(len(rows) for rows in grouped.values()), [5] * 8)

    def test_pause_probe_return_resume_is_exact_and_never_clipped(self):
        for stream in self.result["prospective_campaign_streams"]:
            actions = stream["actions"]
            issue = int(stream["probe_issue"])
            self.assertEqual(len(actions), 40)
            self.assertLessEqual(stream["maximum_adjacent_coil_delta_a"], 0.3)
            self.assertEqual(actions[issue]["issue_step"], issue)
            self.assertEqual(actions[issue + 1]["issue_step"], issue + 1)
            self.assertEqual(actions[issue + 2]["issue_step"], issue + 2)
            self.assertEqual(actions[issue + 3]["issue_step"], issue + 3)
            if stream["direction"] is not None:
                self.assertEqual(actions[issue]["expected_card15_fields"],
                                 actions[issue + 1]["expected_card15_fields"])
                self.assertNotEqual(actions[issue + 1]["expected_card15_fields"],
                                    actions[issue + 2]["expected_card15_fields"])
                self.assertNotEqual(actions[issue + 2]["expected_card15_fields"],
                                    actions[issue + 3]["expected_card15_fields"])

    def test_mutated_arrival_schedule_fails_before_any_plant_semantics(self):
        group = self.stage["prospective_campaign"]["groups"][0]
        saved = list(group["increment_issues"])
        try:
            group["increment_issues"] = saved[:-1]
            with self.assertRaises(u0.IntegrityError):
                u0.build_campaign(self.stage, self.cfg, self.source, self.targets)
        finally:
            group["increment_issues"] = saved

    def test_launcher_has_no_runner_or_tsc_entrypoint(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2u0_nominal_realign_preflight.sh").read_text(
            encoding="utf-8")
        lowered = text.lower()
        self.assertNotIn("gotsc", lowered)
        self.assertNotIn("reset(", lowered)
        self.assertNotIn("step_current", lowered)
        self.assertIn("independent", lowered)


if __name__ == "__main__":
    unittest.main()
