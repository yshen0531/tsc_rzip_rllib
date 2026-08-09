import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r39_independent_forensics as independent39,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r39_fixed_equal_global_ridge_local_constant_cold_ensemble_preflight
    as r8r39,
)


class R8R39FixedEqualColdEnsembleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r39_fixed_equal_global_ridge_local_constant_cold_ensemble_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))
        cls.trajectories = cls._make_trajectories()
        cls.primary_model = r8r39.fit_model(
            cls.trajectories, lambda _row: True, cls.cfg
        )
        cls.independent_model = independent39._fit_model(
            cls.trajectories, lambda _row: True, cls.cfg
        )

    @staticmethod
    def _make_trajectories(count=80):
        random = np.random.RandomState(3901)
        output = []
        for index in range(count):
            intervals = []
            previous = random.uniform(-1.0, 1.0, size=4)
            q = random.uniform(-1.0, 1.0, size=4)
            for interval, target_count in enumerate((2, 2, 2, 2, 4, 15)):
                feature = random.normal(size=44)
                expanded = r8r31.expanded_feature238(feature, q, previous)
                global_part = expanded[:5] * np.asarray(
                    [0.012, -0.008, 0.004, 0.006, -0.01]
                )
                local_part = np.tanh(feature[:5]) * np.asarray(
                    [0.018, 0.015, 0.006, 0.009, 0.012]
                )
                targets = np.asarray(
                    [
                        global_part
                        + local_part
                        + 0.0004 * offset
                        + 0.00001 * index
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
        r8r39.validate_config(self.cfg, project_root=self.root)
        model = self.cfg["model_contract"]
        self.assertEqual(model["global_expanded_dimension"], 238)
        self.assertEqual(model["local_coordinate_dimension"], 62)
        self.assertEqual(model["local_neighbor_count"], 64)
        self.assertEqual(model["global_weight"], 0.5)
        self.assertEqual(model["local_weight"], 0.5)
        self.assertFalse(model["innovation_enabled"])
        self.assertEqual(
            self.cfg["source_r8r31"]["required_route"],
            "ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_PREFLIGHT_FAIL_NO_TSC",
        )
        self.assertEqual(
            self.cfg["source_r8r37"]["required_route"],
            "TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_MODEL_FAIL_NO_TSC",
        )
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["global_weight"] = 0.51
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r39.validate_config(changed, project_root=self.root)

    def test_primary_and_independent_expert_predictions_agree(self):
        row = self.trajectories[0]["intervals"][5]
        primary = r8r39.predict(self.primary_model, row, self.cfg)
        independent = independent39._predict(
            self.independent_model, row, self.cfg
        )
        self.assertEqual(primary[3], independent[3])
        scales = np.asarray(
            self.cfg["model_contract"]["primary_independent_component_scales"]
        )
        for left, right in zip(primary[:3], independent[:3]):
            self.assertLessEqual(
                float(np.max(np.abs(left - right) * r8r39.FACTORS / scales)),
                1e-9,
            )

    def test_ensemble_is_exact_fixed_half_sum(self):
        row = self.trajectories[1]["intervals"][4]
        global_prediction, local_prediction, ensemble, _neighbors = r8r39.predict(
            self.primary_model, row, self.cfg
        )
        np.testing.assert_array_equal(
            ensemble, 0.5 * global_prediction + 0.5 * local_prediction
        )

    def test_local_expert_is_cold_and_target_response_blind(self):
        left = copy.deepcopy(self.trajectories[0])
        right = copy.deepcopy(left)
        right["trajectory_id"] = "mutated_held"
        right["intervals"][0]["targets"] = (
            np.asarray(right["intervals"][0]["targets"]) + 100.0
        )
        for interval in range(1, 6):
            right["intervals"][interval]["targets"] = (
                np.asarray(right["intervals"][interval]["targets"]) - 50.0
            )
        for left_row, right_row in zip(left["intervals"], right["intervals"]):
            left_prediction = r8r39.predict(
                self.primary_model, left_row, self.cfg
            )[2]
            right_prediction = r8r39.predict(
                self.primary_model, right_row, self.cfg
            )[2]
            np.testing.assert_array_equal(left_prediction, right_prediction)

    def test_held_targets_cannot_influence_either_expert_fit(self):
        changed = copy.deepcopy(self.trajectories)
        changed[0]["intervals"][4]["targets"] = (
            np.asarray(changed[0]["intervals"][4]["targets"]) + 100.0
        )
        selected = lambda row: row["trajectory_id"] != "trajectory_000"
        left = r8r39.fit_model(self.trajectories, selected, self.cfg)
        right = r8r39.fit_model(changed, selected, self.cfg)
        self.assertEqual(r8r39.model_evidence(left), r8r39.model_evidence(right))

    def test_cardinality_uses_both_frozen_exclusion_families(self):
        evidence = independent39._cardinality(self.trajectories, self.cfg)
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["family_count"], 2)
        self.assertEqual(evidence["failed_head_count"], 0)
        self.assertGreaterEqual(evidence["minimum_training_row_count"], 64)

    def test_primary_and_independent_model_parameters_agree(self):
        primary = {
            "outer_model_evidence": [
                {"held_pair": "p", **r8r39.model_evidence(self.primary_model)}
            ],
            "schedule_model_evidence": [
                {"held_schedule": "s", **r8r39.model_evidence(self.primary_model)}
            ],
        }
        independent = {
            "outer_model_evidence": [
                {
                    "held_pair": "p",
                    **independent39._model_evidence(self.independent_model),
                }
            ],
            "schedule_model_evidence": [
                {
                    "held_schedule": "s",
                    **independent39._model_evidence(self.independent_model),
                }
            ],
        }
        self.assertLessEqual(
            independent39._scaled_model_difference(primary, independent), 1e-9
        )
        independent["outer_model_evidence"][0]["local_model_evidence"][
            "intervals"
        ][0]["groups"][0]["training_row_count"] += 1
        self.assertEqual(
            independent39._scaled_model_difference(primary, independent), np.inf
        )

    def test_prediction_comparison_checks_both_experts_and_blend(self):
        primary_rows = [
            {
                "held_pair": "p",
                "trajectories": [
                    {
                        "trajectory_id": "t",
                        "global_predictions": [[[1.0] * 5]],
                        "local_predictions": [[[2.0] * 5]],
                        "ensemble_predictions": [[[1.5] * 5]],
                        "absolute_residuals": [[[0.1] * 5]],
                        "neighbor_key_digests": [["n"]],
                    }
                ],
            }
        ]
        primary = {
            "outer_predictions": primary_rows,
            "schedule_predictions": [
                {**copy.deepcopy(primary_rows[0]), "held_schedule": "s"}
            ],
        }
        primary["schedule_predictions"][0].pop("held_pair")
        independent = copy.deepcopy(primary)
        self.assertEqual(
            independent39._scaled_prediction_difference(
                primary, independent, self.cfg
            ),
            0.0,
        )
        independent["outer_predictions"][0]["trajectories"][0][
            "local_predictions"
        ][0][0][0] += 1.0
        self.assertGreater(
            independent39._scaled_prediction_difference(
                primary, independent, self.cfg
            ),
            0.0,
        )

    def test_independent_owns_local_fit_predict_ensemble_and_aggregators(self):
        self.assertIsNot(independent39._fit_model, r8r39.fit_model)
        self.assertIsNot(independent39._predict_local, r8r39.predict)
        self.assertIsNot(independent39._predict, r8r39.predict)
        self.assertIsNot(independent39._residuals, r8r39._residuals)
        self.assertIsNot(independent39._outer, r8r39.outer_model_evaluation)
        self.assertIsNot(independent39._schedule, r8r39.schedule_jackknife)
        self.assertIsNot(independent39._compute, r8r39.compute_from_bank)

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
                "contained_count": 1,
                "component_count": 1,
            },
            "schedule_jackknife": {
                "passed": False,
                "maximum_absolute_physical_error": [0.0] * 5,
                "maximum_reserved_physical_tube_half_width": [0.0] * 5,
                "contained_count": 1,
                "component_count": 1,
            },
            "combined_tube_cap_passed": False,
            "scientific_gate_passed": False,
            "route": self.cfg["routes"]["model_fail"],
        }
        summary = r8r39._summary(detailed, "model")
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["gate_a_qualified"])
        self.assertFalse(summary["expert_data_allowed"])

    def test_finalizer_requires_all_agreements_and_seals_zero_tsc(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / r8r39.RUN_NAME
            paths = r8r39.Paths(
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
                "combined_tube_cap_passed": True,
            }
            r8r39._write(paths.analysis / "primary_summary.json", summary)
            r8r39._write(paths.analysis / "primary_detailed.json", detailed)
            r8r39._write(paths.model / "preflight_model.json", {"model": "primary"})
            r8r39._write(paths.manifest, {"stage": r8r39.STAGE})
            r8r39._write(paths.state, {"primary_completed": True})
            independent = {
                "passed": True,
                **{field: True for field in r8r39.AGREEMENT_FIELDS},
                **{field: 0.0 for field in r8r39.DIFFERENCE_FIELDS},
                "route": summary["route"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "primary_summary_sha256": r8r39._sha(paths.analysis / "primary_summary.json"),
                "primary_detailed_sha256": r8r39._sha(paths.analysis / "primary_detailed.json"),
                "primary_model_sha256": r8r39._sha(paths.model / "preflight_model.json"),
            }
            r8r39._write(paths.analysis / "independent.json", independent)
            ctx = r8r39.Context(
                cfg=self.cfg,
                config_path=self.config_path,
                paths=paths,
                r8r37_ctx=None,
                r8r37_stage=stage,
                source_ctx=None,
            )
            final = r8r39.run_finalize(ctx)
            self.assertTrue(final["passed"])
            self.assertFalse(final["controller_execution_authorized"])
            self.assertFalse(final["gate_a_qualified"])
            self.assertEqual(final["real_tsc_executed"], False)


if __name__ == "__main__":
    unittest.main()
