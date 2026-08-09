import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r35_independent_forensics as independent35,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r35_causal_last_innovation_local_constant_schedule_generalizing_preflight
    as r8r35,
)


class R8R35CausalLastInnovationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r35_causal_last_innovation_local_constant_schedule_generalizing_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    @staticmethod
    def _trajectories(count=80):
        random = np.random.RandomState(3501)
        output = []
        for index in range(count):
            intervals = []
            previous = random.uniform(-1.0, 1.0, size=4)
            q = random.uniform(-1.0, 1.0, size=4)
            drift = random.normal(scale=0.01, size=5)
            for interval, target_count in enumerate((2, 2, 2, 2, 4, 15)):
                feature = random.normal(size=44)
                expanded = r8r31.expanded_feature238(feature, q, previous)
                coordinate = np.concatenate((feature, expanded[44:62]))
                base = coordinate[:5] * np.asarray([0.1, -0.05, 0.02, 0.03, -0.04])
                targets = np.asarray(
                    [
                        base + drift + 0.001 * offset + index * 1e-7
                        for offset in range(target_count)
                    ]
                )
                intervals.append(
                    {
                        "interval": interval,
                        "feature": feature,
                        "q": q,
                        "previous_q": previous,
                        "expanded": expanded,
                        "targets": targets,
                    }
                )
                previous = q
                q = random.uniform(-1.0, 1.0, size=4)
            output.append(
                {
                    "trajectory_id": f"trajectory_{index:03d}",
                    "pair_id": f"pair_{index % 8}",
                    "schedule_id": f"schedule_{index % 35}",
                    "intervals": intervals,
                }
            )
        return output

    def test_frozen_config_validates_and_blocks_search(self):
        r8r35.validate_config(self.cfg, project_root=self.root)
        self.assertEqual(self.cfg["model_contract"]["neighbor_count"], 64)
        self.assertEqual(self.cfg["model_contract"]["slope_dimension"], 0)
        self.assertEqual(self.cfg["model_contract"]["innovation_memory_intervals"], 1)
        for field in (
            "neighbor_search_allowed",
            "gain_search_allowed",
            "lag_search_allowed",
            "memory_search_allowed",
            "feature_search_allowed",
            "response_weighting_allowed",
            "outlier_deletion_allowed",
            "clipping_allowed",
        ):
            self.assertFalse(self.cfg["model_contract"][field])
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["innovation_gain"] = 0.99
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r35.validate_config(changed, project_root=self.root)

    def test_source_contract_binds_final_r8r34_numeric_failure(self):
        source = self.cfg["source_r8r34"]
        self.assertEqual(
            source["required_primary_route"],
            "CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC",
        )
        self.assertEqual(
            source["required_final_route"],
            "CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP",
        )
        for key, value in source.items():
            if key.endswith("_sha256"):
                self.assertEqual(len(value), 64)

    def test_local_constant_uses_fixed_k64_mean_and_exact_neighbor_order(self):
        trajectories = self._trajectories()
        model = r8r35.fit_model(trajectories, lambda _row: True, self.cfg)
        row = trajectories[0]["intervals"][5]
        group = model["intervals"][5]["groups"][0]
        prediction, keys = r8r35.predict_group(
            group, r8r35.r8r34.coordinate62(row), self.cfg
        )
        training = np.asarray(group["standardized_coordinates"])
        mean = np.asarray(group["coordinate_mean"])
        scale = np.asarray(group["coordinate_scale"])
        query = (r8r35.r8r34.coordinate62(row) - mean) / scale
        chosen = np.argsort(np.linalg.norm(training - query, axis=1), kind="mergesort")[:64]
        np.testing.assert_array_equal(prediction, np.mean(np.asarray(group["targets"])[chosen], axis=0))
        self.assertEqual(keys, [group["training_keys"][int(index)] for index in chosen])
        self.assertEqual(model["model_kind"], "causal_local_constant_k64_last_innovation")

    def test_primary_and_independent_predictions_and_neighbors_meet_gate(self):
        trajectories = self._trajectories()
        primary_model = r8r35.fit_model(trajectories, lambda _row: True, self.cfg)
        independent_model = independent35._fit_model(
            trajectories, lambda _row: True, self.cfg
        )
        row = trajectories[3]["intervals"][5]
        primary, primary_keys = r8r35.predict_base(primary_model, row, self.cfg)
        independent, independent_keys = independent35._predict_base(
            independent_model, row, self.cfg
        )
        self.assertEqual(primary_keys, independent_keys)
        scales = np.asarray(
            self.cfg["model_contract"]["primary_independent_component_scales"]
        )
        maximum = float(
            np.max(np.abs(primary - independent) * r8r35.FACTORS / scales)
        )
        self.assertLessEqual(maximum, 1e-9)

    def test_last_innovation_is_strictly_causal_and_has_one_interval_memory(self):
        training = self._trajectories()
        model = r8r35.fit_model(training, lambda _row: True, self.cfg)
        left = copy.deepcopy(training[0])
        right = copy.deepcopy(left)
        left["trajectory_id"] = "held_left"
        right["trajectory_id"] = "held_right"
        right["intervals"][1]["targets"] = (
            np.asarray(right["intervals"][1]["targets"]) + 5.0
        )
        _, _, left_predictions = r8r35._trajectory_residuals(
            model, [left], self.cfg, predict_group_fn=r8r35.predict_group
        )
        _, _, right_predictions = r8r35._trajectory_residuals(
            model, [right], self.cfg, predict_group_fn=r8r35.predict_group
        )
        left_rows = left_predictions[0]["adapted_predictions"]
        right_rows = right_predictions[0]["adapted_predictions"]
        np.testing.assert_array_equal(left_rows[0], right_rows[0])
        np.testing.assert_array_equal(left_rows[1], right_rows[1])
        np.testing.assert_allclose(
            np.asarray(right_rows[2]) - np.asarray(left_rows[2]), 5.0
        )
        np.testing.assert_array_equal(left_rows[3], right_rows[3])

    def test_usefulness_requires_five_percent_total_and_every_fold_no_regression(self):
        rows = [
            {
                "held_out": "a",
                "cold_post_initial_normalized_l1": 100.0,
                "adapted_post_initial_normalized_l1": 80.0,
                "adapted_to_cold_l1_ratio": 0.8,
                "post_initial_time_row_count": 6720,
            },
            {
                "held_out": "b",
                "cold_post_initial_normalized_l1": 100.0,
                "adapted_post_initial_normalized_l1": 101.0,
                "adapted_to_cold_l1_ratio": 1.01,
                "post_initial_time_row_count": 6720,
            },
        ]
        result = r8r35._usefulness("synthetic", rows, self.cfg)
        self.assertLessEqual(result["adapted_to_cold_total_l1_ratio"], 0.95)
        self.assertFalse(result["passed"])
        rows[1]["adapted_post_initial_normalized_l1"] = 90.0
        rows[1]["adapted_to_cold_l1_ratio"] = 0.9
        self.assertTrue(r8r35._usefulness("synthetic", rows, self.cfg)["passed"])

    def test_zero_cold_error_does_not_create_vacuous_usefulness_pass(self):
        rows = [
            {
                "held_out": "a",
                "cold_post_initial_normalized_l1": 0.0,
                "adapted_post_initial_normalized_l1": 0.0,
                "adapted_to_cold_l1_ratio": 1.0,
                "post_initial_time_row_count": 13440,
            }
        ]
        result = r8r35._usefulness("synthetic", rows, self.cfg)
        self.assertEqual(result["adapted_to_cold_total_l1_ratio"], 1.0)
        self.assertFalse(result["passed"])

    def test_independent_owns_predictor_adapter_and_metric_aggregator(self):
        self.assertIsNot(independent35._predict_group, r8r35.predict_group)
        self.assertIsNot(independent35._trajectory_residuals, r8r35._trajectory_residuals)
        self.assertIsNot(independent35._outer, r8r35.outer_model_evaluation)
        self.assertIsNot(independent35._schedule, r8r35.schedule_jackknife)
        self.assertIsNot(independent35._compute, r8r35.compute_from_bank)

    def test_summary_blocks_controller_and_learning(self):
        detailed = {
            "bank_evidence": {
                "trajectory_count": 560,
                "schedule_count": 35,
                "interval_record_count": 3360,
                "bank_digest": "bank",
                "feature_digest": "feature",
                "target_digest": "target",
            },
            "local_cardinality_audit": {
                "head_count": 1161,
                "failed_head_count": 0,
                "minimum_training_row_count": 210,
            },
            "outer_model_evaluation": {
                "passed": False,
                "maximum_absolute_physical_error": [0.0] * 5,
                "maximum_reserved_physical_tube_half_width": [0.0] * 5,
                "adaptation_usefulness": {
                    "adapted_to_cold_total_l1_ratio": 0.8
                },
            },
            "schedule_jackknife": {
                "passed": False,
                "maximum_absolute_physical_error": [0.0] * 5,
                "maximum_reserved_physical_tube_half_width": [0.0] * 5,
                "adaptation_usefulness": {
                    "adapted_to_cold_total_l1_ratio": 0.8
                },
            },
            "combined_tube_cap_passed": False,
            "model_gate_passed": False,
            "adaptation_usefulness_gate_passed": True,
            "scientific_gate_passed": False,
            "route": self.cfg["routes"]["model_fail"],
        }
        summary = r8r35._summary(detailed, "model")
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["gate_a_qualified"])
        self.assertFalse(summary["expert_data_allowed"])

    def test_success_finalizer_requires_exact_independent_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / r8r35.RUN_NAME
            paths = r8r35.Paths(
                stage=stage,
                analysis=stage / "analysis",
                model=stage / "model",
                state=stage / "stage_state.json",
                manifest=stage / "stage_manifest.json",
            )
            summary = {
                "route": self.cfg["routes"]["not_useful"],
                "scientific_gate_passed": False,
            }
            detailed = {
                "local_cardinality_audit": {"passed": True},
                "outer_model_evaluation": {"passed": True},
                "schedule_jackknife": {"passed": True},
                "combined_tube_maximum_physical_half_width": [0.0] * 5,
                "combined_tube_cap_passed": True,
                "adaptation_usefulness_gate_passed": False,
            }
            r8r35._write(paths.analysis / "primary_summary.json", summary)
            r8r35._write(paths.analysis / "primary_detailed.json", detailed)
            r8r35._write(paths.model / "preflight_model.json", {"model": "primary"})
            r8r35._write(paths.manifest, {"stage": r8r35.STAGE})
            r8r35._write(paths.state, {"primary_completed": True})
            independent = {
                "passed": True,
                "primary_bank_agreement": True,
                "primary_neighbor_agreement": True,
                "primary_prediction_agreement": True,
                "primary_tube_agreement": True,
                "primary_metric_agreement": True,
                "primary_route_agreement": True,
                "primary_outcome_agreement": True,
                "maximum_scaled_prediction_difference": 0.0,
                "maximum_scaled_tube_difference": 0.0,
                "maximum_scaled_metric_difference": 0.0,
                "route": summary["route"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
            }
            independent["primary_summary_sha256"] = r8r35._sha(
                paths.analysis / "primary_summary.json"
            )
            independent["primary_detailed_sha256"] = r8r35._sha(
                paths.analysis / "primary_detailed.json"
            )
            independent["primary_model_sha256"] = r8r35._sha(
                paths.model / "preflight_model.json"
            )
            r8r35._write(paths.analysis / "independent.json", independent)
            ctx = r8r35.Context(
                cfg=self.cfg,
                config_path=self.config_path,
                paths=paths,
                r8r34_ctx=None,
                r8r34_stage=stage,
                source_ctx=None,
            )
            final = r8r35.run_finalize(ctx)
            self.assertTrue(final["passed"])
            self.assertEqual(final["route"], summary["route"])
            self.assertFalse(final["controller_execution_authorized"])

    def test_failure_finalizer_preserves_numeric_gate_and_seals_execution_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / r8r35.RUN_NAME
            paths = r8r35.Paths(
                stage=stage,
                analysis=stage / "analysis",
                model=stage / "model",
                state=stage / "stage_state.json",
                manifest=stage / "stage_manifest.json",
            )
            summary = {
                "route": self.cfg["routes"]["model_fail"],
                "scientific_gate_passed": False,
            }
            detailed = {
                "local_cardinality_audit": {"passed": True},
                "outer_model_evaluation": {"passed": False},
                "schedule_jackknife": {"passed": False},
                "combined_tube_maximum_physical_half_width": [0.0] * 5,
                "combined_tube_cap_passed": False,
                "adaptation_usefulness_gate_passed": False,
            }
            r8r35._write(paths.analysis / "primary_summary.json", summary)
            r8r35._write(paths.analysis / "primary_detailed.json", detailed)
            r8r35._write(paths.model / "preflight_model.json", {"model": "primary"})
            r8r35._write(paths.manifest, {"stage": r8r35.STAGE})
            r8r35._write(paths.state, {"primary_completed": True})
            failure = {
                "passed": False,
                "primary_bank_agreement": True,
                "primary_neighbor_agreement": True,
                "primary_prediction_agreement": False,
                "primary_tube_agreement": True,
                "primary_metric_agreement": False,
                "primary_route_agreement": True,
                "primary_outcome_agreement": True,
                "maximum_scaled_prediction_difference": 2e-8,
                "maximum_scaled_tube_difference": 0.0,
                "maximum_scaled_metric_difference": 3e-8,
                "route": summary["route"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "primary_summary_sha256": r8r35._sha(
                    paths.analysis / "primary_summary.json"
                ),
                "primary_detailed_sha256": r8r35._sha(
                    paths.analysis / "primary_detailed.json"
                ),
                "primary_model_sha256": r8r35._sha(
                    paths.model / "preflight_model.json"
                ),
            }
            r8r35._write(paths.analysis / "independent_failure.json", failure)
            ctx = r8r35.Context(
                cfg=self.cfg,
                config_path=self.config_path,
                paths=paths,
                r8r34_ctx=None,
                r8r34_stage=stage,
                source_ctx=None,
            )
            final = r8r35.run_finalize(ctx)
            self.assertFalse(final["passed"])
            self.assertFalse(final["integrity_gate_passed"])
            self.assertEqual(final["primary_route"], summary["route"])
            self.assertEqual(final["route"], self.cfg["routes"]["execution_fail"])
            state = r8r35._read(paths.state)
            self.assertFalse(state["independent_validation_passed"])
            self.assertEqual(
                state["phase_status"],
                "offline_preflight_independent_validation_failed",
            )


if __name__ == "__main__":
    unittest.main()
