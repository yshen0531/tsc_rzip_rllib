from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_signed_basis_g3 as primary
from scripts.rgeo_zgeo_1ms_nr1_qualification import _source


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_signed_basis_g3.json"


def state(index: int, r_mm: float = 0.0, z_mm: float = 0.0, ip_a: float = 0.0) -> dict:
    return {
        "time_ms": 1000 + index, "r_geo_m": 0.7 + r_mm / 1000.0,
        "z_geo_m": z_mm / 1000.0, "r_mid_m": 0.79, "ip_a": 30000.0 + ip_a,
    }


class Fixed1000SignedBasisG3Test(unittest.TestCase):
    def test_frozen_identity_budget_roles_and_basis(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(stage["axes"], ["even", "odd", "block2", "block4"])
        self.assertEqual(stage["issue_phases"], [8, 24])
        self.assertEqual(stage["rollouts"], 18)
        self.assertEqual(stage["maximum_advance_attempts"], 720)
        self.assertEqual(stage["retry_after_any_advance_attempt"], "forbidden")
        self.assertEqual(stage["data_roles"]["critical_replays"], "integrity_only_zero_fit_weight")

    def test_rollout_matrix_and_sequences(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        specs = primary.rollout_specs(stage)
        self.assertEqual(len(specs), 18)
        self.assertEqual(sum(row["repeat_index"] == 0 for row in specs), 16)
        self.assertEqual(sum(row["repeat_index"] == 1 for row in specs), 2)
        sequence = primary.sequence_for(specs[0], stage, {"q0": "q0", "even_plus": "pulse"})
        self.assertEqual([i for i, value in enumerate(sequence) if value == "pulse"], [8, 9, 10, 11])

    def test_server_exact_input_basis_and_offline_streams(self) -> None:
        stage, cfg, _ = primary.load(CONFIG)
        source = _source(cfg)
        geometry = primary.targets(stage, cfg, source)["action_geometry"]
        self.assertEqual(geometry["rank"], 4)
        self.assertLessEqual(geometry["condition"], 1.45)
        self.assertLessEqual(geometry["maximum_absolute_delta_a"], 0.146)
        preflight = primary.offline(CONFIG, "test-revision")
        self.assertTrue(preflight["passed"], preflight["failures"])
        self.assertEqual(len(preflight["rollout_action_streams"]), 18)
        self.assertTrue(all(len(row["actions"]) == 40 for row in preflight["rollout_action_streams"]))

    def test_science_passes_persistent_four_axis_positive_cone(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        baseline = [state(i) for i in range(41)]
        vectors = {"even": (0.10, 0.00), "odd": (0.00, 0.10),
                   "block2": (-0.10, 0.00), "block4": (0.00, -0.10)}
        rows = []
        for spec in primary.rollout_specs(stage):
            if spec["repeat_index"]:
                continue
            states = [state(i) for i in range(41)]
            polarity = 1.0 if spec["sign"] == "plus" else -1.0
            r, z = vectors[spec["axis"]]
            for horizon in (4, 8):
                i = spec["issue_phase"] + horizon
                states[i] = state(i, polarity * r, polarity * z)
            rows.append({**spec, "states": states})
        metrics = primary.scientific_metrics(rows, baseline, stage)
        self.assertTrue(metrics["passed"])
        self.assertTrue(all(phase["passed"] for phase in metrics["phases"]))

    def test_science_rejects_one_dimensional_outputs(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        baseline = [state(i) for i in range(41)]
        rows = []
        for spec in primary.rollout_specs(stage):
            if spec["repeat_index"]:
                continue
            states = [state(i) for i in range(41)]
            polarity = 1.0 if spec["sign"] == "plus" else -1.0
            for horizon in (4, 8):
                i = spec["issue_phase"] + horizon
                states[i] = state(i, 0.10 * polarity, 0.0)
            rows.append({**spec, "states": states})
        self.assertFalse(primary.scientific_metrics(rows, baseline, stage)["phase_geometry_pass"])

    def test_launcher_exposes_only_offline_run_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_signed_basis_g3.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_G3_SOURCE_REVISION", text)
        for mode in ("offline)", "run)", "audit)"):
            self.assertIn(mode, text)


if __name__ == "__main__":
    unittest.main()
