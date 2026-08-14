import copy
import hashlib
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import rgeo_zgeo_1ms_id1c_persistent_basis_validation as primary
from scripts import rgeo_zgeo_1ms_id1c_persistent_basis_validation_independent as independent
from tsc_rzip_rllib.core.runner import TSCConfig


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "configs/rgeo_zgeo_1ms_id1c_persistent_basis_validation.json"
SOURCE = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_id0_result_20260814_38b3a22e/baseline_q0_r0.json"


class TestId1cPersistentBasisValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(STAGE.read_text(encoding="utf-8"))

    def test_frozen_config_identity_and_data_role(self) -> None:
        self.assertEqual(hashlib.sha256(STAGE.read_bytes()).hexdigest(), primary.CONFIG_SHA256)
        primary._exact_stage(self.stage)
        self.assertEqual(self.stage["model_fit_use"], "forbidden")
        self.assertEqual(self.stage["holdout_records_read"], 0)
        self.assertFalse(self.stage["empirical_exploration"]["pre_action_transition_tube_claimed"])

    def test_rollout_budget_and_atomic_replay_pairs(self) -> None:
        rows = primary.rollout_specs(self.stage)
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(row["context_id"] == "baseline" for row in rows), 2)
        for direction in (row["direction_id"] for row in self.stage["directions"]):
            for sign in ("plus", "minus"):
                selected = [row for row in rows if row["direction_id"] == direction and row["sign"] == sign]
                self.assertEqual([row["repeat_index"] for row in selected], [0, 1])
        self.assertEqual(self.stage["rollouts"] * self.stage["horizon_steps"], 180)
        self.assertEqual(self.stage["rollouts"] * (self.stage["horizon_steps"] + 1), 190)

    def test_persistent_window_has_one_unchanged_target_and_later_return(self) -> None:
        with patch.object(TSCConfig, "validate", lambda self: None):
            stage, cfg, evidence = primary.load(STAGE)
        compact = json.loads(SOURCE.read_text(encoding="utf-8"))
        state = compact["states"][0]
        source = {
            "currents_a_tsc": state["actual_current_a_tsc"],
            "active_command_decimal_a_tsc": state["active_command_decimal_a_tsc"],
        }
        streams = primary.targets_and_streams(stage, cfg, evidence, source)
        q0 = next(row for row in streams if row["context_id"] == "baseline")
        for stream in streams:
            self.assertEqual(len(stream["targets"]), 18)
            self.assertEqual(len(stream["actions"]), 18)
            self.assertLessEqual(max(action["maximum_issued_delta_a"] for action in stream["actions"]), 0.15)
            if stream["context_id"] == "baseline":
                continue
            fields = [stream["actions"][issue]["expected_card15_fields"] for issue in range(10, 14)]
            self.assertTrue(all(value == fields[0] for value in fields[1:]))
            self.assertEqual(
                [stream["actions"][issue]["persistent_dwell_effect_age"] for issue in range(10, 14)],
                [1, 2, 3, 4],
            )
            self.assertEqual(stream["actions"][14]["expected_card15_fields"], q0["actions"][14]["expected_card15_fields"])
            self.assertNotEqual(fields[0], stream["actions"][14]["expected_card15_fields"])

    @staticmethod
    def _synthetic_rows(vectors: dict[tuple[str, str], tuple[float, float]]) -> list[dict]:
        def states(vector: tuple[float, float] | None) -> list[dict]:
            rows = [{"r_geo_m": 0.0, "z_geo_m": 0.0, "ip_a": 0.0} for _ in range(19)]
            if vector is not None:
                for index in range(11, 15):
                    rows[index] = {"r_geo_m": vector[0], "z_geo_m": vector[1], "ip_a": 0.0}
                for index in range(15, 19):
                    rows[index] = {"r_geo_m": 0.25 * vector[0], "z_geo_m": 0.25 * vector[1], "ip_a": 0.0}
            return rows
        result = [
            {"rollout_id": f"q0_baseline_r{repeat}", "context_id": "baseline", "states": states(None)}
            for repeat in range(2)
        ]
        for (direction, sign), vector in vectors.items():
            for repeat in range(2):
                result.append({
                    "rollout_id": f"late_{direction}_{sign}_r{repeat}",
                    "context_id": "late", "direction_id": direction,
                    "sign": sign, "repeat_index": repeat, "states": states(vector),
                })
        return result

    def test_positive_span_metric_passes_for_supported_cone(self) -> None:
        scale = 2.0e-5
        vectors = {
            ("p01", "plus"): (scale, 0.0), ("p01", "minus"): (-scale, 0.0),
            ("p09_half_exact_center", "plus"): (0.0, scale),
            ("p09_half_exact_center", "minus"): (0.0, -scale),
        }
        metrics = primary.scientific_metrics(self._synthetic_rows(vectors), self.stage)
        audited = independent._metrics(self._synthetic_rows(vectors), self.stage)
        self.assertTrue(metrics["positive_span_passed"])
        self.assertTrue(metrics["signal_passed"])
        self.assertTrue(metrics["symmetry_passed"])
        self.assertLessEqual(metrics["maximum_angular_gap_deg"], 90.0)
        self.assertGreaterEqual(metrics["minimum_directional_support_m"], 1.0e-5)
        self.assertLessEqual(independent._numeric_max_difference(metrics, audited), 1e-12)

    def test_rank_two_one_half_plane_fails_positive_span(self) -> None:
        scale = 2.0e-5
        vectors = {
            ("p01", "plus"): (scale, 0.1 * scale), ("p01", "minus"): (scale, -0.1 * scale),
            ("p09_half_exact_center", "plus"): (scale, 1.0 * scale),
            ("p09_half_exact_center", "minus"): (scale, -1.0 * scale),
        }
        metrics = primary.scientific_metrics(self._synthetic_rows(vectors), self.stage)
        self.assertEqual(metrics["rz_response_rank"], 2)
        self.assertFalse(metrics["positive_span_passed"])
        self.assertGreater(metrics["maximum_angular_gap_deg"], 175.0)
        self.assertLess(metrics["minimum_directional_support_m"], 0.0)

    def test_route_precedence(self) -> None:
        metrics = {
            "signal_passed": True, "symmetry_passed": True,
            "ip_passed": True, "positive_span_passed": True,
        }
        self.assertEqual(primary.route_for(self.stage, False, True, True, metrics), self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(self.stage, True, False, True, metrics), self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, False, metrics), self.stage["routes"]["repeatability_fail"])
        rejected = dict(metrics, positive_span_passed=False)
        self.assertEqual(primary.route_for(self.stage, True, True, True, rejected), self.stage["routes"]["positive_span_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, True, metrics), self.stage["routes"]["pass"])
        self.assertEqual(independent._route(self.stage, True, metrics), self.stage["routes"]["pass"])

    def test_exact_q0_centered_targets(self) -> None:
        with patch.object(TSCConfig, "validate", lambda self: None):
            stage, cfg, evidence = primary.load(STAGE)
        compact = json.loads(SOURCE.read_text(encoding="utf-8"))
        state = compact["states"][0]
        source = {
            "currents_a_tsc": state["actual_current_a_tsc"],
            "active_command_decimal_a_tsc": state["active_command_decimal_a_tsc"],
        }
        targets = primary._targets(stage, cfg, evidence, source)
        q0 = np.asarray(targets["q0"].current_a_tsc)
        for direction in (row["direction_id"] for row in stage["directions"]):
            plus = np.asarray(targets[f"{direction}:plus"].current_a_tsc)
            minus = np.asarray(targets[f"{direction}:minus"].current_a_tsc)
            np.testing.assert_allclose((plus + minus) / 2.0, q0, rtol=0.0, atol=1e-12)
            self.assertLessEqual(float(np.max(np.abs(plus - q0))), 0.15 + 1e-12)
            self.assertLessEqual(float(np.max(np.abs(minus - q0))), 0.15 + 1e-12)

    def test_raw_state0_outgoing_inputa_is_not_preissue_source_command(self) -> None:
        with patch.object(TSCConfig, "validate", lambda self: None):
            stage, cfg, evidence = primary.load(STAGE)
        compact = json.loads(SOURCE.read_text(encoding="utf-8"))
        state = compact["states"][0]
        source_command = state["active_command_decimal_a_tsc"]
        streams = primary.targets_and_streams(
            stage,
            cfg,
            evidence,
            {
                "currents_a_tsc": state["actual_current_a_tsc"],
                "active_command_decimal_a_tsc": source_command,
            },
        )
        issue0 = streams[0]["actions"][0]
        self.assertEqual(issue0["maximum_issued_delta_a"], 1.0e-5)
        self.assertNotEqual(
            source_command,
            [
                str(value)
                for value in primary.card15_target_decimal_a(
                    streams[0]["targets"][0], cfg.turns_tsc, name="id1c.test.issue0"
                )
            ],
        )

    def test_safety_or_data_role_mutation_fails_closed(self) -> None:
        for path, value in (
            (("model_fit_use",), "allowed"),
            (("dwell", "return_issue"), 13),
            (("scientific_gates", "maximum_angular_gap_deg"), 180.0),
            (("scientific_gates", "minimum_directional_support_m"), 0.0),
            (("empirical_exploration", "pre_action_transition_tube_claimed"), True),
        ):
            changed = copy.deepcopy(self.stage)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.assertRaises(primary.InputIntegrityError):
                primary._exact_stage(changed)


if __name__ == "__main__":
    unittest.main()
