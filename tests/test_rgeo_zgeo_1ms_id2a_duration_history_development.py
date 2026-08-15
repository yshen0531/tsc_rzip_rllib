import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import rgeo_zgeo_1ms_id2a_duration_history_development as primary
from tsc_rzip_rllib.core.runner import TSCConfig


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "configs/rgeo_zgeo_1ms_id2a_duration_history_development.json"
SOURCE = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_id0_result_20260814_38b3a22e/baseline_q0_r0.json"


class TestId2aDurationHistoryDevelopment(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(STAGE.read_text(encoding="utf-8"))

    def test_frozen_identity_and_data_roles(self) -> None:
        self.assertEqual(hashlib.sha256(STAGE.read_bytes()).hexdigest(), primary.CONFIG_SHA256)
        primary._exact_stage(self.stage)
        self.assertEqual(self.stage["development_model_fit_use_after_all_gates_pass"], "allowed")
        self.assertEqual(self.stage["calibration_use"], "forbidden")
        self.assertEqual(self.stage["holdout_use"], "forbidden")
        self.assertEqual(self.stage["holdout_records_read"], 0)
        self.assertFalse(self.stage["empirical_exploration"]["pre_action_transition_tube_claimed"])

    def test_rollout_matrix_and_budgets(self) -> None:
        rows = primary.rollout_specs(self.stage)
        self.assertEqual(len(rows), 42)
        self.assertEqual(len({row["rollout_id"] for row in rows}), 42)
        for context in (row["context_id"] for row in self.stage["contexts"]):
            selected = [row for row in rows if row["context_id"] == context]
            self.assertEqual(len(selected), 14)
            self.assertEqual(sum(row["is_context_baseline"] for row in selected), 1)
            repeated = [row for row in selected if row["direction_id"] == "p09_half_exact_center" and row["sign"] == "minus" and row["duration_issues"] == 4]
            self.assertEqual([row["repeat_index"] for row in repeated], [0, 1])
        self.assertEqual(42 * 32, self.stage["maximum_advance_attempts"])
        self.assertEqual(42 * 33, self.stage["completed_state_count"])
        self.assertEqual(42 * 33 * 5, self.stage["completed_required_artifact_files"])

    def _streams(self):
        with patch.object(TSCConfig, "validate", lambda self: None):
            stage, cfg, _ = primary.load(STAGE)
        compact = json.loads(SOURCE.read_text(encoding="utf-8"))
        state = compact["states"][0]
        source = {"currents_a_tsc": state["actual_current_a_tsc"], "active_command_decimal_a_tsc": state["active_command_decimal_a_tsc"]}
        return stage, cfg, primary.targets_and_streams(stage, cfg, source)

    def test_duration_streams_return_exact_q0_and_keep_exact_card15(self) -> None:
        stage, _, streams = self._streams()
        for stream in streams:
            self.assertEqual(len(stream["actions"]), 32)
            self.assertLessEqual(max(row["maximum_issued_delta_a"] for row in stream["actions"]), 0.3)
            self.assertEqual(stream["actions"][9]["probe_virtual_action"], [0.0, 0.0])
            if stream["is_context_baseline"]:
                continue
            start = stream["pulse_issue_step"]
            stop = start + stream["duration_issues"]
            self.assertEqual([stream["actions"][index]["duration_effect_age"] for index in range(start, stop)], list(range(1, stream["duration_issues"] + 1)))
            self.assertTrue(all(stream["actions"][index]["expected_card15_fields"] == stream["actions"][start]["expected_card15_fields"] for index in range(start, stop)))
            self.assertEqual(stream["actions"][stop]["expected_card15_fields"], next(row for row in streams if row["context_id"] == stream["context_id"] and row["is_context_baseline"])["actions"][stop]["expected_card15_fields"])
            self.assertNotEqual(stream["actions"][start]["expected_card15_fields"], stream["actions"][stop]["expected_card15_fields"])
        self.assertEqual(stage["action_semantics"]["effect_state_index"], "issue_step_plus_one")

    def test_virtual_lag_support_is_full_rank_and_well_conditioned(self) -> None:
        stage, _, streams = self._streams()
        result = primary.lag_support(streams, stage)
        self.assertEqual(result["columns"], 32)
        self.assertEqual(result["rank"], 32)
        self.assertLessEqual(result["condition"], 100.0)
        self.assertTrue(result["passed"])

    def test_scientific_metrics_require_signal_duration_and_ip_per_family(self) -> None:
        rows = []
        vectors = {"p01": (1.0, 0.2), "p09_half_exact_center": (0.1, 1.0)}
        for spec in primary.rollout_specs(self.stage):
            states = [{"r_geo_m": 0.0, "z_geo_m": 0.0, "ip_a": 0.0} for _ in range(33)]
            if not spec["is_context_baseline"]:
                sign = 1.0 if spec["sign"] == "plus" else -1.0
                vector = vectors[spec["direction_id"]]
                scale = sign * spec["duration_issues"] * 1.0e-5
                for index in range(11, 33):
                    states[index] = {"r_geo_m": scale * vector[0], "z_geo_m": scale * vector[1], "ip_a": 10.0 * spec["duration_issues"]}
            rows.append({**spec, "states": states})
        result = primary.scientific_metrics(rows, self.stage)
        self.assertEqual(len(result["family_metrics"]), 12)
        self.assertTrue(result["signal_passed"])
        self.assertTrue(result["duration_separation_passed"])
        self.assertTrue(result["ip_passed"])
        self.assertTrue(result["tail_extinction_is_not_a_gate"])

    def test_route_precedence(self) -> None:
        metrics = {"signal_passed": True, "duration_separation_passed": True, "ip_passed": True}
        routes = self.stage["routes"]
        self.assertEqual(primary.route_for(self.stage, False, True, True, True, metrics), routes["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(self.stage, True, False, True, True, metrics), routes["raw_integrity_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, False, True, metrics), routes["repeatability_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, True, False, metrics), routes["input_support_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, True, True, dict(metrics, duration_separation_passed=False)), routes["response_support_or_ip_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, True, True, metrics), routes["pass"])

    def test_safety_and_data_role_mutations_fail_closed(self) -> None:
        for path, value in (
            (("development_model_fit_use_after_all_gates_pass",), "forbidden"),
            (("durations_issues",), [1, 4]),
            (("action_semantics", "maximum_single_turn_adjacent_delta_a"), 0.31),
            (("empirical_exploration", "pre_action_transition_tube_claimed"), True),
            (("storage_gate", "minimum_free_bytes_before_run"), 1),
            (("identifiability_gates", "required_lag_block_rank"), 31),
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
