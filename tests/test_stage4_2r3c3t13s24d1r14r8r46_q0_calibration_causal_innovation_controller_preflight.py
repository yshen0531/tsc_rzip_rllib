import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r43_independent_forensics as independent43,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r46_independent_forensics as independent46,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight
    as source_r8r43,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r46_q0_calibration_causal_innovation_controller_preflight
    as r8r46,
)


class R8R46Q0CalibrationInnovationPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r46_q0_calibration_causal_innovation_controller_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def _ctx(self, paths=None):
        if paths is None:
            stage = self.root / ".codex_tmp" / "r8r46_test_unused"
            paths = r8r46.Paths(
                stage=stage,
                analysis=stage / "analysis",
                model=stage / "model",
                state=stage / "stage_state.json",
                manifest=stage / "stage_manifest.json",
            )
        return r8r46.Context(
            cfg=self.cfg,
            config_path=self.config_path,
            paths=paths,
            r8r44_ctx=SimpleNamespace(),
            r8r44_stage=paths.stage,
        )

    @staticmethod
    def _model_evaluation(passed=True):
        return {
            "outer_model_evaluation": {
                "passed": passed,
                "adapted_to_cold_aggregate_ratio": 0.9,
            },
            "schedule_jackknife": {
                "passed": passed,
                "adapted_to_cold_aggregate_ratio": 0.9,
            },
            "combined_postcalibration_tube_maximum_physical_half_width": [
                0.015,
                0.015,
                3000.0,
                0.05,
                0.05,
            ],
            "combined_postcalibration_tube_cap_passed": passed,
            "model_gate_passed": passed,
        }

    @staticmethod
    def _planning(authority=True, safety=True):
        return {
            "ran": True,
            "calibration_context_pass_count": 16,
            "safe_search_context_count": 16,
            "predicted_repaired_failed_baseline_count": 1,
            "predicted_regressed_baseline_pass_count": 0,
            "predicted_fallback_plus_plan_oracle_count": 7,
            "nonzero_first_transport_action_count": 1,
            "plans": [],
            "safety_passed": safety,
            "authority_passed": authority,
            "passed": authority,
        }

    def test_frozen_config_and_source_failure_contract(self):
        r8r46.validate_config(self.cfg, project_root=self.root)
        self.assertEqual(
            self.cfg["source_r8r44"]["required_route"],
            "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC",
        )
        self.assertEqual(
            self.cfg["planner_contract"]["transport_decision_task_steps"],
            [12, 14, 16, 18, 22],
        )
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])

    def test_frozen_config_mutations_fail_closed(self):
        for path, value in (
            (("model_contract", "innovation_forecast_decay"), 0.49),
            (("calibration_contract", "candidate_id"), "hold"),
            (("planner_contract", "immediate_safety_tube"), "adapted_only"),
            (("action_contract", "maximum_current_utilization"), 0.56),
        ):
            changed = copy.deepcopy(self.cfg)
            changed[path[0]][path[1]] = value
            with self.assertRaisesRegex(ValueError, "frozen config changed"):
                r8r46.validate_config(changed, project_root=self.root)

    def test_fixed_ewma_teacher_forcing_reduces_synthetic_postcal_error(self):
        intervals = [
            {
                "targets": np.ones((1, 5), dtype=float),
            }
            for _ in range(6)
        ]
        held = [{"trajectory_id": "t", "intervals": intervals}]
        predictions = [
            {
                "trajectory_id": "t",
                "ensemble_predictions": [np.zeros((1, 5)).tolist() for _ in range(6)],
            }
        ]
        cold_tube = [np.full((count, 5), 12.5) for count in r8r46.r8r31.MAX_COUNTS]
        _groups, evidence, artifact = r8r46._adapt_held(
            held, predictions, cold_tube, self.cfg
        )
        self.assertAlmostEqual(evidence["adapted_to_cold_ratio"], 0.25)
        self.assertEqual(evidence["innovation_clipping_component_count"], 0)
        self.assertEqual(artifact[0]["updates"][0]["next_bias"], [0.5] * 5)

    def test_fixed_ewma_records_clipping_instead_of_hiding_it(self):
        intervals = [{"targets": np.ones((1, 5), dtype=float)} for _ in range(6)]
        held = [{"trajectory_id": "t", "intervals": intervals}]
        predictions = [
            {
                "trajectory_id": "t",
                "ensemble_predictions": [np.zeros((1, 5)).tolist() for _ in range(6)],
            }
        ]
        cold_tube = [np.full((count, 5), 0.125) for count in r8r46.r8r31.MAX_COUNTS]
        _groups, evidence, artifact = r8r46._adapt_held(
            held, predictions, cold_tube, self.cfg
        )
        self.assertGreater(evidence["innovation_clipping_component_count"], 0)
        self.assertEqual(artifact[0]["updates"][0]["next_bias"], [0.1] * 5)

    def test_execution_tube_preserves_cold_interval_zero_and_dual_first_interval(self):
        cold = [np.full((count, 5), 2.0) for count in r8r46.r8r31.MAX_COUNTS]
        adapted = [np.full((count, 5), 1.0) for count in r8r46.r8r31.MAX_COUNTS]
        adapted[2][:] = 3.0
        combined = r8r46.execution_tube(cold, adapted)
        self.assertTrue(np.array_equal(combined[0], cold[0]))
        self.assertTrue(np.array_equal(combined[1], cold[1]))
        self.assertTrue(np.array_equal(combined[2], adapted[2]))
        with self.assertRaisesRegex(ValueError, "coverage changed"):
            r8r46.execution_tube(cold[:5], adapted)

    def test_calibration_uses_q0_measured_step12_state_and_current(self):
        source_trajectory = [
            {"currents_a_tsc": np.full(14, float(index))}
            for index in range(13)
        ]
        measured_states = np.arange(65, dtype=float).reshape(13, 5)
        q0 = {
            "trajectory_id": "q0-row",
            "states": measured_states,
            "trajectory": source_trajectory,
            "intervals": [
                {
                    "feature": np.zeros(44),
                    "targets": np.zeros((2, 5)),
                    "q": np.zeros(4),
                    "previous_q": np.zeros(4),
                }
            ],
        }
        ctx = SimpleNamespace(
            cfg=self.cfg,
            source_ctx=SimpleNamespace(cfg={}),
            r8r43_ctx=SimpleNamespace(cfg={}),
        )
        support = {"features": [np.zeros((1, 44))], "thresholds": [1.0]}
        candidate = {"index": 0, "id": "q0", "q": np.zeros(4)}
        issue = {
            "passed": True,
            "nominal_issue_readback_current_a_tsc": np.full(14, 12.0),
        }
        cold_tube = [np.ones((count, 5)) for count in r8r46.r8r31.MAX_COUNTS]
        with mock.patch.object(r8r46.r8r31, "_candidate_rows", return_value=[candidate]), mock.patch.object(
            r8r46.r8r31, "transition_supported", return_value=True
        ), mock.patch.object(r8r46.r8r31, "_safe_issue", return_value=issue):
            row = r8r46._calibration_row(
                ctx,
                {"pair_id": "p", "history_member": "q1"},
                q0,
                {},
                cold_tube,
                support,
                [{}],
                predict_fn=lambda _model, value, _cfg: np.zeros_like(value["targets"]),
            )
        self.assertTrue(row["passed"])
        self.assertTrue(row["exact_target_hold"])
        self.assertEqual(row["measured_states_through_task_step_12"], measured_states.tolist())
        self.assertEqual(row["measured_current_a_tsc"], [12.0] * 14)
        self.assertEqual(row["previous_current_a_tsc"], [10.0] * 14)

    def test_postcalibration_fold_interface_allows_independent_cold_predictions(self):
        signature = inspect.signature(r8r46.postcalibration_from_cold_folds)
        for name in (
            "outer_folds",
            "outer_predictions",
            "schedule_folds",
            "schedule_predictions",
        ):
            self.assertIn(name, signature.parameters)
        self.assertIsNot(independent43._fit_model, source_r8r43.fit_model)
        self.assertIsNot(independent43._predict, source_r8r43.predict)
        self.assertIsNot(independent46.audit, r8r46.compute_from_bank)

    def test_model_failure_skips_planning_and_preserves_fault_holds(self):
        planning, faults, support, hulls = r8r46.skipped_planning()
        self.assertFalse(planning["ran"])
        self.assertEqual(planning["skip_reason"], "postcalibration_model_gate_failed")
        self.assertTrue(faults["passed"])
        self.assertEqual(faults["pass_count"], 6)
        self.assertEqual(support["features"], [])
        self.assertEqual(hulls, [])

    def test_assemble_routes_distinguish_model_safety_and_authority(self):
        common = (
            self._ctx(),
            {"passed": True},
            {"trajectory_count": 560},
            {"passed": True},
        )
        passed = r8r46.assemble_result(
            *common,
            self._model_evaluation(),
            self._planning(),
            {"passed": True},
        )
        self.assertEqual(passed["route"], self.cfg["routes"]["pass"])
        authority = r8r46.assemble_result(
            *common,
            self._model_evaluation(),
            self._planning(authority=False),
            {"passed": True},
        )
        self.assertEqual(authority["route"], self.cfg["routes"]["authority_fail"])
        model = r8r46.assemble_result(
            self._ctx(),
            {"passed": True},
            {"trajectory_count": 560},
            {"passed": False},
            self._model_evaluation(),
            self._planning(),
            {"passed": True},
        )
        self.assertEqual(model["route"], self.cfg["routes"]["model_fail"])

    def test_summary_never_authorizes_controller_gate_a_or_learning(self):
        detailed = r8r46.assemble_result(
            self._ctx(),
            {"passed": True},
            {
                "trajectory_count": 560,
                "schedule_count": 35,
                "interval_record_count": 3360,
                "bank_digest": "bank",
            },
            {"passed": True},
            self._model_evaluation(),
            self._planning(),
            {"passed": True, "pass_count": 6},
        )
        summary = r8r46._summary(detailed, "model")
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["gate_a_qualified"])
        self.assertFalse(summary["expert_data_allowed"])
        self.assertFalse(summary["real_tsc_executed"])

    def test_independent_selection_binds_calibrated_transport_action(self):
        row = {
            "pair_id": "p",
            "history_member": "q1",
            "beam_counts": [17, 100, 100, 100, 100],
            "counters": {"safe": 500},
            "safe_search_complete": True,
            "selected_plan": {"candidate_indices": [2, 0, 0, 0, 0]},
            "robust_formal_plan_found": True,
            "causal_mode": "calibrated_first_action_plan",
            "selected_first_transport_action_index": 2,
            "selected_first_transport_action_mode": "safe_nonzero_first_transport_action",
        }
        left = independent46._planning_selection({"plans": [row]})
        right = independent46._planning_selection({"plans": [copy.deepcopy(row)]})
        self.assertEqual(left, right)
        right[0]["selected_first_transport_action_index"] = 0
        self.assertNotEqual(left, right)

    def test_independent_model_artifact_converts_numpy_before_json_digest(self):
        artifact = independent46._serializable_model_artifact(
            {"combined_execution_tube": [np.zeros((2, 5), dtype=float)]}
        )
        self.assertIsInstance(artifact["combined_execution_tube"][0], list)
        json.dumps(artifact, sort_keys=True, allow_nan=False)

    def test_finalizer_requires_all_dual_agreements_and_seals_zero_tsc(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / r8r46.RUN_NAME
            paths = r8r46.Paths(
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
                "cold_source_binding": {"passed": True},
                "postcalibration_model_evaluation": self._model_evaluation(False),
                "planning_evaluation": r8r46.skipped_planning()[0],
                "fault_injection": {"passed": True},
            }
            r8r46._write(paths.analysis / "primary_summary.json", summary)
            r8r46._write(paths.analysis / "primary_detailed.json", detailed)
            r8r46._write(paths.model / "preflight_model.json", {"model": "primary"})
            r8r46._write(paths.manifest, {"stage": r8r46.STAGE})
            r8r46._write(paths.state, {"primary_completed": True})
            independent = {
                "passed": True,
                **{field: True for field in r8r46.AGREEMENT_FIELDS},
                **{field: 0.0 for field in r8r46.DIFFERENCE_FIELDS},
                "route": summary["route"],
                "primary_summary_sha256": r8r46._sha(
                    paths.analysis / "primary_summary.json"
                ),
                "primary_detailed_sha256": r8r46._sha(
                    paths.analysis / "primary_detailed.json"
                ),
                "primary_model_sha256": r8r46._sha(
                    paths.model / "preflight_model.json"
                ),
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
            }
            r8r46._write(paths.analysis / "independent.json", independent)
            final = r8r46.run_finalize(self._ctx(paths))
            self.assertTrue(final["passed"])
            self.assertEqual(final["route"], summary["route"])
            self.assertFalse(final["real_tsc_executed"])
            self.assertFalse(final["controller_execution_authorized"])
            self.assertFalse(final["gate_a_qualified"])


if __name__ == "__main__":
    unittest.main()
