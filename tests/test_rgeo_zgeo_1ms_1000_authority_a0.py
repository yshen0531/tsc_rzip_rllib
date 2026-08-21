import copy
import json
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_1000_authority_a0 as a0


ROOT = Path(__file__).resolve().parents[1]


class AuthorityA0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.baseline, cls.d1_stage, cls.artifact = a0.load(a0.DEFAULT_CONFIG)

    def test_identity_budget_and_matrix(self):
        self.assertEqual(a0.b0.sha256(a0.DEFAULT_CONFIG), a0.CONFIG_SHA256)
        self.assertEqual(len(a0.rollout_specs(self.stage)), 6)
        self.assertEqual(self.stage["maximum_reset_calls"], 6)
        self.assertEqual(self.stage["maximum_advance_attempts"], 360)
        self.assertEqual(self.stage["decision_issues"], [24, 36])

    def test_frozen_initial_nominations_are_control_aligned(self):
        self.assertEqual(a0.select_candidate(
            self.stage, self.artifact, np.asarray(self.stage["waypoints_mm"]["positive"])),
            "even_minus")
        self.assertEqual(a0.select_candidate(
            self.stage, self.artifact, np.asarray(self.stage["waypoints_mm"]["negative"])),
            "odd_minus")

    def test_selector_uses_remaining_error(self):
        self.assertEqual(a0.select_candidate(self.stage, self.artifact, np.asarray([1.0, 0.0])),
                         "even_minus")
        self.assertEqual(a0.select_candidate(self.stage, self.artifact, np.asarray([0.0, 1.0])),
                         "odd_plus")
        self.assertEqual(a0.select_candidate(self.stage, self.artifact, np.asarray([-1.0, 0.0])),
                         "even_plus")
        self.assertEqual(a0.select_candidate(self.stage, self.artifact, np.asarray([0.0, -1.0])),
                         "odd_minus")

    def test_metrics_require_containment_and_progress(self):
        rows = {}
        blank = {"r_geo_m": 0.0, "z_geo_m": 0.0, "ip_a": 0.0}
        for spec in a0.rollout_specs(self.stage):
            states = [dict(blank) for _ in range(61)]
            decisions = []
            for ordinal in range(spec["decision_count"]):
                candidate = "even_minus" if spec["path"] == "positive" and ordinal == 0 else \
                    "odd_plus" if spec["path"] == "positive" else \
                    "odd_minus" if ordinal == 0 else "even_plus"
                direction = [1.0, 0.0] if candidate == "even_minus" else [0.0, 1.0] if candidate == "odd_plus" \
                    else [0.0, -1.0] if candidate == "odd_minus" else [-1.0, 0.0]
                decisions.append({"candidate": candidate, "remaining_direction_rz": direction})
            rows[spec["rollout_id"]] = {"states": states,
                                        "actions": [{"issue_step": i} for i in range(60)],
                                        "decisions": decisions}
        for full_id, base_id, origin, ordinal in (
            ("positive_first_only", "q0_baseline", 24, 0),
            ("positive_full", "positive_first_only", 36, 1),
            ("negative_first_only", "q0_baseline", 24, 0),
            ("negative_full", "negative_first_only", 36, 1),
        ):
            candidate = rows[full_id]["decisions"][ordinal]["candidate"]
            for horizon in (4, 8):
                center = self.artifact["model"]["candidates"][candidate][str(horizon)]["center_rz_ip"]
                rows[full_id]["states"][origin + horizon] = {
                    "r_geo_m": center[0] / 1000, "z_geo_m": center[1] / 1000, "ip_a": center[2]}
        for path in ("positive", "negative"):
            first = rows[f"{path}_first_only"]
            full = rows[f"{path}_full"]
            for index in range(37):
                if index not in (40, 44):
                    full["states"][index] = copy.deepcopy(first["states"][index])
        metrics = a0.scientific_metrics(rows, self.stage, self.artifact)
        self.assertTrue(metrics["passed"])
        broken = copy.deepcopy(rows)
        broken["positive_full"]["states"][44]["r_geo_m"] += 0.01
        self.assertFalse(a0.scientific_metrics(broken, self.stage, self.artifact)["passed"])

    def test_launcher_and_data_roles(self):
        launcher = (ROOT / "run_rgeo_zgeo_1ms_1000_authority_a0.sh").read_text(encoding="utf-8")
        self.assertIn("offline|run|audit", launcher)
        self.assertIn("authority_a0_independent.py", launcher)
        self.assertEqual(self.stage["data_roles"]["all_primary_rows"],
                         "authority_qualification_only_zero_fit_weight")
        self.assertEqual(self.stage["data_roles"]["controller_expert_bc_dagger_rl"], "forbidden")

    def test_independent_prefix_excludes_only_outgoing_inputa(self):
        source = (ROOT / "scripts/rgeo_zgeo_1ms_1000_authority_a0_independent.py").read_text(
            encoding="utf-8")
        self.assertIn("final_state_inputa_is_outgoing", source)
        self.assertIn('index == count - 1 and name == "inputa"', source)


if __name__ == "__main__":
    unittest.main()
