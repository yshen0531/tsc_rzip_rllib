from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r25_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r25_training_cardinality_matched_outer_jackknife_tube_preflight
    as primary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r25_training_cardinality_matched_outer_jackknife_tube_preflight.json"
LAUNCHER = ROOT / "run_stage4_2r3c3t13s24d1r14r8r25_common.sh"


def _cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _synthetic_bank() -> list[dict]:
    rng = np.random.default_rng(20260809)
    output = []
    for pair_index in range(8):
        pair = f"pair_{pair_index}"
        for trajectory_index in range(3):
            intervals = []
            previous_q = np.zeros(2)
            for interval, count in enumerate((4, 4, 4, 15)):
                feature = rng.normal(size=42) + pair_index * 0.01
                q = np.asarray(
                    [0.25 * (trajectory_index % 2), 0.25 * ((trajectory_index + interval) % 2)]
                )
                row = {
                    "row_id": f"{pair}|t{trajectory_index}|i{interval}",
                    "interval": interval,
                    "feature": feature,
                    "q": q,
                    "previous_q": previous_q.copy(),
                }
                row["expanded"] = primary.r8r23._expanded_row(row)
                base = np.asarray(
                    [
                        0.001 * row["expanded"][0],
                        -0.002 * row["expanded"][1],
                        0.003 * row["expanded"][2],
                        0.004 * row["expanded"][3],
                        -0.005 * row["expanded"][4],
                    ]
                )
                row["targets"] = np.asarray(
                    [base + offset * np.asarray([1, 2, 3, 4, 5]) * 1e-5 for offset in range(count)]
                )
                intervals.append(row)
                previous_q = q
            output.append(
                {
                    "trajectory_id": f"{pair}|t{trajectory_index}",
                    "pair_id": pair,
                    "history_member": f"h{trajectory_index % 2}",
                    "intervals": intervals,
                }
            )
    return output


def _constant_folds() -> list[dict]:
    folds = []
    for pair_index in range(8):
        groups = []
        for count in (4, 4, 4, 15):
            groups.append(
                [np.full((2, 5), float(pair_index + 1)) for _ in range(count)]
            )
        folds.append({"held_pair": f"pair_{pair_index}", "residual_groups": groups})
    return folds


class R8R25ContractTests(unittest.TestCase):
    def test_primary_and_independent_validate_frozen_contract(self) -> None:
        cfg = _cfg()
        primary.validate_config(cfg, project_root=ROOT)
        independent._validate_config(cfg)
        self.assertTrue(cfg["outer_jackknife_tube_contract"]["evaluated_pair_residual_excluded"])
        self.assertEqual(cfg["outer_jackknife_tube_contract"]["reserve_multiplier"], 1.25)
        self.assertFalse(cfg["outer_jackknife_tube_contract"]["tube_clipping_allowed"])
        self.assertFalse(cfg["expert_data_allowed"])
        self.assertFalse(cfg["gate_a_qualified"])

    def test_contract_mutations_fail_closed(self) -> None:
        for group, key, value in (
            ("outer_jackknife_tube_contract", "evaluated_pair_residual_excluded", False),
            ("outer_jackknife_tube_contract", "reserve_multiplier", 1.0),
            ("planning_support_contract", "threshold_multiplier", 1.4),
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("routes", "pass", "changed"),
        ):
            cfg = copy.deepcopy(_cfg())
            cfg[group][key] = value
            with self.assertRaises(ValueError):
                primary.validate_config(cfg, project_root=ROOT)
            with self.assertRaises(ValueError):
                independent._validate_config(cfg)

    def test_cross_outer_tube_excludes_evaluated_pair(self) -> None:
        folds = _constant_folds()
        calibration = [f"pair_{index}" for index in range(7)]
        left, left_evidence = primary._tube_template(folds, calibration, _cfg())
        right, right_evidence = independent._tube_template(folds, calibration, _cfg())
        self.assertEqual(left_evidence, right_evidence)
        self.assertNotIn("pair_7", left_evidence["calibration_pair_ids"])
        self.assertEqual(left_evidence["calibration_pair_count"], 7)
        for left_value, right_value in zip(left, right):
            np.testing.assert_allclose(left_value, right_value, rtol=0.0, atol=0.0)
            np.testing.assert_allclose(left_value[0], np.full(5, 8.75), rtol=0.0, atol=0.0)

    def test_cross_outer_tube_never_clips_to_caps(self) -> None:
        folds = _constant_folds()
        tube, _ = primary._tube_template(folds, [f"pair_{index}" for index in range(8)], _cfg())
        physical = tube[0][0] * primary.FACTORS
        self.assertGreater(physical[0], _cfg()["model_gates"]["maximum_reserved_R_tube_half_width_m"])
        self.assertGreater(physical[3], _cfg()["model_gates"]["maximum_reserved_vR_tube_half_width_m_per_s"])

    def test_primary_and_independent_outer_folds_are_exact(self) -> None:
        bank = _synthetic_bank()
        left = primary._outer_folds(bank, _cfg())
        right = independent._outer(bank, _cfg())
        primary._attach_outer_tubes(left, _cfg())
        independent._attach(right, _cfg())
        for left_fold, right_fold in zip(left, right):
            self.assertEqual(left_fold["held_pair"], right_fold["held_pair"])
            self.assertEqual(
                left_fold["outer_residual_group_digest"],
                right_fold["outer_residual_group_digest"],
            )
            self.assertEqual(left_fold["local_tube_evidence"], right_fold["local_tube_evidence"])
            difference = independent.ind23._maximum_difference(
                primary.r8r23._model_serializable(left_fold["model"]),
                independent.ind23._serial(right_fold["model"]),
            )
            self.assertLessEqual(difference, 1e-12)

    def test_all_pair_planning_support_matches_independent(self) -> None:
        bank = _synthetic_bank()
        left = primary._planning_support(bank, _cfg())
        right = independent._planning_support(bank, _cfg())
        for key in (
            "training_nearest_neighbor_maxima",
            "thresholds",
            "training_origin_count_by_interval",
        ):
            np.testing.assert_allclose(left[key], right[key], rtol=0.0, atol=1e-12)
        feature = np.asarray(bank[0]["intervals"][0]["feature"])
        self.assertTrue(primary._planning_supported(left, feature, 0))
        self.assertTrue(independent._supported(right, feature, 0))
        far = feature + 1e6
        self.assertFalse(primary._planning_supported(left, far, 0))
        self.assertFalse(independent._supported(right, far, 0))

    def test_primary_and_independent_formal_are_exact(self) -> None:
        states = np.zeros((36, 5))
        tubes = np.zeros_like(states)
        left = primary.r8r23._robust_formal(states, tubes, deadline=25, endpoint=35, cfg=_cfg())
        right = independent.ind24._formal(states, tubes, 25, 35, _cfg())
        self.assertEqual(left, right)

    def test_independent_does_not_import_any_primary_implementation(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        for name in (
            "stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight",
            "stage4_2r3c3t13s24d1r14r8r24_causal_local_residual_tube_receding_horizon_preflight",
            "stage4_2r3c3t13s24d1r14r8r25_training_cardinality_matched_outer_jackknife_tube_preflight as",
        ):
            self.assertNotIn(name, source)

    def test_launcher_is_zero_tsc_and_uses_existing_server_venv(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("zero Ray/gotsc/TSC/controller/plant/raw", source)
        self.assertNotIn("ray start", source)


if __name__ == "__main__":
    unittest.main()
