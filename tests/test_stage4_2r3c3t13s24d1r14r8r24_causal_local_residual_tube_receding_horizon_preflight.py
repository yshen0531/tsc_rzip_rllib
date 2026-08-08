from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import numpy as np
from scipy.spatial import cKDTree

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r24_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r24_causal_local_residual_tube_receding_horizon_preflight
    as primary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r24_causal_local_residual_tube_receding_horizon_preflight.json"
)
LAUNCHER = ROOT / "run_stage4_2r3c3t13s24d1r14r8r24_common.sh"


def _cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _record(residual: np.ndarray | None = None) -> dict:
    features = np.zeros((34, 133), dtype=float)
    values = np.tile(
        np.asarray(
            residual if residual is not None else [2.0, 0.1, 0.4, 0.2, 0.3],
            dtype=float,
        ),
        (34, 1),
    )
    return {"features": features, "residuals": values, "tree": cKDTree(features)}


class R8R24ContractTests(unittest.TestCase):
    def test_primary_and_independent_validate_the_frozen_contract(self) -> None:
        cfg = _cfg()
        primary.validate_config(cfg, project_root=ROOT)
        independent._validate_config(cfg)
        self.assertEqual(cfg["local_tube_contract"]["neighbor_count"], 32)
        self.assertEqual(
            cfg["local_tube_contract"]["physical_point_error_floors"],
            [0.015, 0.015, 3000.0, 0.05, 0.05],
        )
        self.assertFalse(cfg["local_tube_contract"]["tube_clipping_allowed"])
        self.assertFalse(cfg["model_contract"]["innovation_enabled"])
        self.assertFalse(cfg["expert_data_allowed"])
        self.assertFalse(cfg["gate_a_qualified"])

    def test_contract_mutations_fail_closed_in_both_implementations(self) -> None:
        for path, value in (
            (("local_tube_contract", "neighbor_count"), 31),
            (("model_contract", "innovation_enabled"), True),
            (("formal_contract", "normal_arrival_deadline_step"), 26),
            (("planning_gate", "minimum_predicted_oracle_count"), 6),
            (("routes", "pass"), "changed"),
        ):
            cfg = copy.deepcopy(_cfg())
            cfg[path[0]][path[1]] = value
            with self.assertRaises(ValueError):
                primary.validate_config(cfg, project_root=ROOT)
            with self.assertRaises(ValueError):
                independent._validate_config(cfg)

    def test_neighbor_rule_includes_all_kth_distance_ties(self) -> None:
        record = _record()
        query = np.zeros(133, dtype=float)
        primary_indices = primary._neighbor_indices(record, query, 32)
        independent_indices = independent._neighbors(record, query, 32)
        np.testing.assert_array_equal(primary_indices, np.arange(34))
        np.testing.assert_array_equal(independent_indices, np.arange(34))

    def test_local_tube_matches_independent_and_is_not_clipped(self) -> None:
        calibration = [[_record()] for _ in range(4)]
        row = {
            "interval": 0,
            "expanded": np.zeros(133, dtype=float),
            "targets": np.zeros((1, 5), dtype=float),
        }
        left, left_counts = primary._query_tube(calibration, row, _cfg())
        right, right_counts = independent._tube_query(calibration, row, _cfg())
        np.testing.assert_allclose(left, right, rtol=0.0, atol=0.0)
        self.assertEqual(left_counts, [34])
        self.assertEqual(right_counts, [34])
        physical = left[0] * primary.FACTORS
        np.testing.assert_allclose(
            physical,
            [0.075, 0.015, 5000.0, 0.25, 0.375],
            rtol=0.0,
            atol=1e-12,
        )
        self.assertGreater(physical[0], _cfg()["model_gates"]["maximum_reserved_R_tube_half_width_m"])
        self.assertGreater(physical[3], _cfg()["model_gates"]["maximum_reserved_vR_tube_half_width_m_per_s"])

    def test_model_gate_reports_containment_support_and_cap_separately(self) -> None:
        cfg = _cfg()
        trajectory = {
            "trajectory_id": "held|h0",
            "intervals": [
                {
                    "targets": np.zeros((1, 5), dtype=float),
                }
            ],
        }
        floor = (
            np.asarray(cfg["local_tube_contract"]["physical_point_error_floors"])
            / primary.FACTORS
        ).reshape(1, 5)
        fold = {
            "held_pair": "held",
            "held_trajectories": [trajectory],
            "cold_predictions": {"held|h0": [np.zeros((1, 5))]},
            "local_tubes": {"held|h0": [floor]},
            "support": {"pass_counts": [1], "row_counts": [1]},
            "local_tube_evidence": {},
        }
        result = primary._evaluate_model([fold], cfg)
        self.assertTrue(result["reserved_tube_containment_gate_passed"])
        self.assertTrue(result["support_gate_passed"])
        self.assertTrue(result["tube_cap_gate_passed"])
        self.assertTrue(result["passed"])
        fold["local_tubes"]["held|h0"][0][0, 3] = 0.081
        result = primary._evaluate_model([fold], cfg)
        self.assertFalse(result["tube_cap_gate_passed"])
        self.assertFalse(result["passed"])

    def test_primary_and_independent_robust_formal_are_exact(self) -> None:
        cfg = _cfg()
        states = np.zeros((36, 5), dtype=float)
        tubes = np.zeros_like(states)
        left = primary.r8r23._robust_formal(
            states, tubes, deadline=25, endpoint=35, cfg=cfg
        )
        right = independent._formal(states, tubes, 25, 35, cfg)
        self.assertEqual(left, right)
        tubes[:, 0] = 2.0
        left = primary.r8r23._robust_formal(
            states, tubes, deadline=25, endpoint=35, cfg=cfg
        )
        right = independent._formal(states, tubes, 25, 35, cfg)
        self.assertEqual(left, right)
        self.assertFalse(left[0])

    def test_independent_does_not_import_either_primary_implementation(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight",
            source,
        )
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r24_causal_local_residual_tube_receding_horizon_preflight as",
            source,
        )

    def test_launcher_is_zero_tsc_and_uses_the_existing_server_venv(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("zero Ray/gotsc/TSC/controller/plant/raw", source)
        self.assertNotIn("ray start", source)
        self.assertNotIn("gotsc", source.split("printf '[R8R24]")[0])


if __name__ == "__main__":
    unittest.main()
