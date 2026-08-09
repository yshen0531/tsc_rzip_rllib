import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r37_independent_forensics as independent37,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r37_training_only_diagonal_innovation_gain_schedule_generalizing_preflight
    as r8r37,
)


class R8R37TrainingOnlyDiagonalGainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r37_training_only_diagonal_innovation_gain_schedule_generalizing_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))
        cls.trajectories = cls._make_trajectories()
        cls.primary_model = r8r37.fit_model(
            cls.trajectories, lambda _row: True, cls.cfg
        )
        cls.independent_model = independent37._fit_model(
            cls.trajectories, lambda _row: True, cls.cfg
        )

    @staticmethod
    def _make_trajectories(count=80):
        random = np.random.RandomState(3701)
        output = []
        for index in range(count):
            intervals = []
            previous = random.uniform(-1.0, 1.0, size=4)
            q = random.uniform(-1.0, 1.0, size=4)
            innovation = random.normal(scale=0.008, size=5)
            for interval, target_count in enumerate((2, 2, 2, 2, 4, 15)):
                feature = random.normal(size=44)
                expanded = r8r31.expanded_feature238(feature, q, previous)
                coordinate = np.concatenate((feature, expanded[44:62]))
                base = coordinate[:5] * np.asarray(
                    [0.06, -0.04, 0.02, 0.03, -0.05]
                )
                targets = np.asarray(
                    [
                        base
                        + (0.7 ** interval) * innovation
                        + 0.0005 * offset
                        + index * 1e-7
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

    def test_frozen_config_and_source_contract(self):
        r8r37.validate_config(self.cfg, project_root=self.root)
        model = self.cfg["model_contract"]
        self.assertEqual(model["gain_parameter_count"], 25)
        self.assertEqual(model["innovation_memory_intervals"], 1)
        for field in (
            "neighbor_search_allowed",
            "gain_search_allowed",
            "lag_search_allowed",
            "memory_search_allowed",
            "feature_search_allowed",
            "response_weighting_allowed",
            "outlier_deletion_allowed",
            "innovation_clipping_allowed",
        ):
            self.assertFalse(model[field])
        self.assertEqual(
            self.cfg["source_r8r35"]["required_route"],
            "CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_MODEL_FAIL_NO_TSC",
        )
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["maximum_gain"] = 1.01
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r37.validate_config(changed, project_root=self.root)

    def test_gain_fit_has_exact_shape_counts_bounds_and_evidence(self):
        model = self.primary_model
        gains = np.asarray(model["diagonal_gains"])
        counts = np.asarray(model["gain_sample_counts"])
        self.assertEqual(gains.shape, (6, 5))
        np.testing.assert_array_equal(gains[0], 0.0)
        self.assertTrue(np.all((gains[1:] >= 0.0) & (gains[1:] <= 1.0)))
        self.assertTrue(np.all(counts[1:] > 0))
        evidence = r8r37.gain_evidence(model)
        self.assertEqual(evidence["gain_parameter_count"], 25)
        self.assertEqual(sum(evidence["gain_projection_counts"].values()), 25)
        self.assertEqual(len(evidence["gain_digest"]), 64)

    def test_primary_and_independent_gain_statistics_agree(self):
        primary = r8r37.gain_evidence(self.primary_model)
        independent = independent37._gain_evidence(self.independent_model)
        for field in (
            "diagonal_gains",
            "gain_numerators",
            "gain_denominators",
        ):
            left = np.asarray(primary[field])
            right = np.asarray(independent[field])
            denominator = np.maximum(1.0, np.maximum(np.abs(left), np.abs(right)))
            self.assertLessEqual(float(np.max(np.abs(left - right) / denominator)), 1e-9)
        self.assertEqual(primary["gain_sample_counts"], independent["gain_sample_counts"])
        self.assertEqual(
            primary["gain_projection_states"], independent["gain_projection_states"]
        )

    def test_fixed_k64_base_predictor_and_neighbor_order(self):
        row = self.trajectories[0]["intervals"][5]
        primary, primary_keys = r8r37.predict_base(
            self.primary_model, row, self.cfg
        )
        independent, independent_keys = independent37._predict_base(
            self.independent_model, row, self.cfg
        )
        self.assertEqual(primary_keys, independent_keys)
        scales = np.asarray(
            self.cfg["model_contract"]["primary_independent_component_scales"]
        )
        self.assertLessEqual(
            float(np.max(np.abs(primary - independent) * r8r37.FACTORS / scales)),
            1e-9,
        )

    def test_adapter_is_strictly_causal_and_uses_one_completed_interval(self):
        left = copy.deepcopy(self.trajectories[0])
        right = copy.deepcopy(left)
        right["trajectory_id"] = "held_mutated"
        right["intervals"][1]["targets"] = (
            np.asarray(right["intervals"][1]["targets"]) + 5.0
        )
        _, _, left_rows = r8r37._trajectory_residuals(
            self.primary_model, [left], self.cfg, predict_group_fn=r8r37.predict_group
        )
        _, _, right_rows = r8r37._trajectory_residuals(
            self.primary_model, [right], self.cfg, predict_group_fn=r8r37.predict_group
        )
        left_predictions = left_rows[0]["adapted_predictions"]
        right_predictions = right_rows[0]["adapted_predictions"]
        np.testing.assert_array_equal(left_predictions[0], right_predictions[0])
        np.testing.assert_array_equal(left_predictions[1], right_predictions[1])
        expected = 5.0 * np.asarray(self.primary_model["diagonal_gains"])[2]
        np.testing.assert_allclose(
            np.asarray(right_predictions[2]) - np.asarray(left_predictions[2]),
            np.broadcast_to(expected, np.asarray(right_predictions[2]).shape),
        )
        np.testing.assert_array_equal(left_predictions[3], right_predictions[3])

    def test_held_targets_cannot_influence_training_gain(self):
        changed = copy.deepcopy(self.trajectories)
        changed[0]["intervals"][4]["targets"] = (
            np.asarray(changed[0]["intervals"][4]["targets"]) + 100.0
        )
        selected = lambda row: row["trajectory_id"] != "trajectory_000"
        left = r8r37.fit_model(self.trajectories, selected, self.cfg)
        right = r8r37.fit_model(changed, selected, self.cfg)
        self.assertEqual(
            r8r37.gain_evidence(left),
            r8r37.gain_evidence(right),
        )

    def test_usefulness_requires_total_improvement_and_no_regressing_fold(self):
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
        self.assertFalse(r8r37._usefulness("synthetic", rows, self.cfg)["passed"])
        rows[1]["adapted_post_initial_normalized_l1"] = 90.0
        rows[1]["adapted_to_cold_l1_ratio"] = 0.9
        self.assertTrue(r8r37._usefulness("synthetic", rows, self.cfg)["passed"])

    def test_independent_gain_comparison_checks_numbers_and_projection_state(self):
        evidence = r8r37.gain_evidence(self.primary_model)
        primary = {
            "outer_model_evidence": [{"held_pair": "p", "gain_evidence": evidence}],
            "schedule_model_evidence": [
                {"held_schedule": "s", "gain_evidence": evidence}
            ],
        }
        independent = copy.deepcopy(primary)
        self.assertEqual(independent37._scaled_gain_difference(primary, independent), 0.0)
        independent["outer_model_evidence"][0]["gain_evidence"][
            "gain_projection_states"
        ][1][0] = "projected_upper"
        self.assertEqual(
            independent37._scaled_gain_difference(primary, independent), np.inf
        )

    def test_independent_owns_gain_predictor_adapter_and_aggregators(self):
        self.assertIsNot(independent37._fit_model, r8r37.fit_model)
        self.assertIsNot(independent37._predict_group, r8r37.predict_group)
        self.assertIsNot(independent37._trajectory_residuals, r8r37._trajectory_residuals)
        self.assertIsNot(independent37._outer, r8r37.outer_model_evaluation)
        self.assertIsNot(independent37._schedule, r8r37.schedule_jackknife)
        self.assertIsNot(independent37._compute, r8r37.compute_from_bank)

    def test_summary_blocks_controller_gate_a_and_learning(self):
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
                "adaptation_usefulness": {"adapted_to_cold_total_l1_ratio": 0.8},
            },
            "schedule_jackknife": {
                "passed": False,
                "maximum_absolute_physical_error": [0.0] * 5,
                "maximum_reserved_physical_tube_half_width": [0.0] * 5,
                "adaptation_usefulness": {"adapted_to_cold_total_l1_ratio": 0.8},
            },
            "combined_tube_cap_passed": False,
            "model_gate_passed": False,
            "adaptation_usefulness_gate_passed": True,
            "scientific_gate_passed": False,
            "route": self.cfg["routes"]["model_fail"],
        }
        summary = r8r37._summary(detailed, "model")
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["gate_a_qualified"])
        self.assertFalse(summary["expert_data_allowed"])

    def test_finalizer_requires_gain_agreement_and_seals_zero_tsc(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / r8r37.RUN_NAME
            paths = r8r37.Paths(
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
            r8r37._write(paths.analysis / "primary_summary.json", summary)
            r8r37._write(paths.analysis / "primary_detailed.json", detailed)
            r8r37._write(paths.model / "preflight_model.json", {"model": "primary"})
            r8r37._write(paths.manifest, {"stage": r8r37.STAGE})
            r8r37._write(paths.state, {"primary_completed": True})
            independent = {
                "passed": True,
                "primary_bank_agreement": True,
                "primary_neighbor_agreement": True,
                "primary_gain_agreement": True,
                "primary_prediction_agreement": True,
                "primary_tube_agreement": True,
                "primary_metric_agreement": True,
                "primary_route_agreement": True,
                "primary_outcome_agreement": True,
                "maximum_scaled_gain_difference": 0.0,
                "maximum_scaled_prediction_difference": 0.0,
                "maximum_scaled_tube_difference": 0.0,
                "maximum_scaled_metric_difference": 0.0,
                "route": summary["route"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "primary_summary_sha256": r8r37._sha(
                    paths.analysis / "primary_summary.json"
                ),
                "primary_detailed_sha256": r8r37._sha(
                    paths.analysis / "primary_detailed.json"
                ),
                "primary_model_sha256": r8r37._sha(
                    paths.model / "preflight_model.json"
                ),
            }
            r8r37._write(paths.analysis / "independent.json", independent)
            ctx = r8r37.Context(
                cfg=self.cfg,
                config_path=self.config_path,
                paths=paths,
                r8r35_ctx=None,
                r8r35_stage=stage,
                source_ctx=None,
            )
            final = r8r37.run_finalize(ctx)
            self.assertTrue(final["passed"])
            self.assertFalse(final["controller_execution_authorized"])
            self.assertFalse(final["gate_a_qualified"])
            self.assertEqual(final["real_tsc_executed"], False)


if __name__ == "__main__":
    unittest.main()
