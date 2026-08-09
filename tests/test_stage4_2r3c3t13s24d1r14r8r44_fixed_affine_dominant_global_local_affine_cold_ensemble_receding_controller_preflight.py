import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r44_independent_forensics as independent44,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight
    as source_r8r43,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r44_fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight
    as r8r44,
)


class R8R44AffineDominantControllerPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r44_fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def _ctx(self, paths=None):
        if paths is None:
            stage = self.root / ".codex_tmp" / "r8r44_test_unused"
            paths = r8r44.Paths(
                stage=stage,
                analysis=stage / "analysis",
                model=stage / "model",
                state=stage / "stage_state.json",
                manifest=stage / "stage_manifest.json",
            )
        return r8r44.Context(
            cfg=self.cfg,
            config_path=self.config_path,
            paths=paths,
            r8r43_ctx=None,
            r8r43_stage=paths.stage,
            source_ctx=None,
        )

    @staticmethod
    def _base_detailed():
        return {
            "integrity_gate_passed": True,
            "scientific_gate_passed": True,
            "model_gate_passed": True,
            "route": "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED",
            "local_cardinality_audit": {"passed": True},
            "outer_model_evaluation": {"passed": True},
            "schedule_jackknife": {"passed": True},
            "combined_tube_maximum_physical_half_width": [0.015, 0.018, 3000.0, 0.05, 0.059],
            "combined_tube_cap_passed": True,
        }

    @staticmethod
    def _planning(authority=True, safety=True):
        return {
            "safe_search_context_count": 16,
            "predicted_repaired_failed_baseline_count": 1,
            "predicted_regressed_baseline_pass_count": 0,
            "predicted_fallback_plus_plan_oracle_count": 7,
            "nonzero_first_action_count": 1,
            "safety_passed": safety,
            "authority_passed": authority,
            "plans": [],
        }

    def test_frozen_config_and_exact_source_pass_contract(self):
        r8r44.validate_config(self.cfg, project_root=self.root)
        self.assertEqual(self.cfg["model_contract"]["global_weight"], 0.25)
        self.assertEqual(self.cfg["model_contract"]["local_weight"], 0.75)
        self.assertEqual(self.cfg["planner_contract"]["candidate_count"], 17)
        self.assertEqual(self.cfg["planner_contract"]["beam_width"], 512)
        self.assertEqual(self.cfg["planner_contract"]["dynamic_exact_search_radius"], 16)
        self.assertEqual(
            self.cfg["source_r8r43"]["required_route"],
            "FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED",
        )

    def test_config_mutation_fails_closed(self):
        changed = copy.deepcopy(self.cfg)
        changed["planner_contract"]["beam_width"] = 513
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r44.validate_config(changed, project_root=self.root)
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["local_weight"] = 0.74
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r44.validate_config(changed, project_root=self.root)

    def test_planner_callback_is_explicit_and_first_action_contract_is_frozen(self):
        signature = inspect.signature(r8r44.evaluate_planning)
        self.assertIn("fit_model_fn", signature.parameters)
        self.assertIn("predict_ensemble_fn", signature.parameters)
        self.assertTrue(self.cfg["planner_contract"]["measurement_recentered"])
        self.assertTrue(self.cfg["planner_contract"]["execute_first_action_only"])
        self.assertFalse(self.cfg["planner_contract"]["failed_plan_deployment_allowed"])

    def test_source_planner_retains_exact_card15_and_safety_limits(self):
        action = self.cfg["action_contract"]
        self.assertTrue(action["require_exact_card15_issue"])
        self.assertTrue(action["require_exact_card15_refresh"])
        self.assertTrue(action["safe_stop_before_failed_advance"])
        self.assertEqual(action["maximum_incremental_normalized_action_linf"], 0.25)
        self.assertEqual(action["maximum_total_normalized_action_abs"], 1.0)
        self.assertEqual(action["maximum_current_utilization"], 0.55)
        self.assertEqual(action["minimum_desired_applied_current_cosine"], 0.98)
        self.assertEqual(action["maximum_relative_off_basis_residual"], 0.10)

    def test_fault_injections_are_six_fail_closed_holds(self):
        faults = r8r31.fault_injections()
        self.assertTrue(faults["passed"])
        self.assertEqual(faults["pass_count"], 6)
        self.assertTrue(
            all(row["selected_mode"] == "exact_target_hold_fallback" for row in faults["rows"])
        )

    def test_assemble_pass_requires_model_safety_and_authority(self):
        detailed = r8r44.assemble_result(
            self._ctx(),
            {"passed": True},
            {"trajectory_count": 560},
            self._base_detailed(),
            self._planning(),
            {"passed": True},
            {"passed": True},
        )
        self.assertTrue(detailed["scientific_gate_passed"])
        self.assertEqual(detailed["route"], self.cfg["routes"]["pass"])
        self.assertFalse(detailed["controller_execution_authorized"])
        self.assertFalse(detailed["gate_a_qualified"])

    def test_assemble_authority_failure_does_not_become_safety_failure(self):
        detailed = r8r44.assemble_result(
            self._ctx(),
            {"passed": True},
            {"trajectory_count": 560},
            self._base_detailed(),
            self._planning(authority=False),
            {"passed": True},
            {"passed": True},
        )
        self.assertTrue(detailed["safety_gate_passed"])
        self.assertFalse(detailed["authority_gate_passed"])
        self.assertEqual(detailed["route"], self.cfg["routes"]["authority_fail"])

    def test_assemble_model_or_fault_failure_is_safety_failure(self):
        detailed = r8r44.assemble_result(
            self._ctx(),
            {"passed": True},
            {"trajectory_count": 560},
            self._base_detailed(),
            self._planning(),
            {"passed": False},
            {"passed": True},
        )
        self.assertFalse(detailed["safety_gate_passed"])
        self.assertEqual(detailed["route"], self.cfg["routes"]["safety_fail"])

    def test_summary_never_authorizes_controller_gate_a_or_learning(self):
        detailed = r8r44.assemble_result(
            self._ctx(),
            {"passed": True},
            {
                "trajectory_count": 560,
                "schedule_count": 35,
                "interval_record_count": 3360,
                "bank_digest": "bank",
            },
            self._base_detailed(),
            self._planning(),
            {"passed": True, "pass_count": 6},
            {"passed": True},
        )
        summary = r8r44._summary(detailed, "model")
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["gate_a_qualified"])
        self.assertFalse(summary["expert_data_allowed"])
        self.assertFalse(summary["real_tsc_executed"])

    def test_independent_selection_comparison_binds_first_action_and_full_plan(self):
        row = {
            "pair_id": "p",
            "history_member": "q1",
            "beam_counts": [1, 1, 1, 1, 1, 1],
            "counters": {"safe": 6},
            "safe_search_complete": True,
            "selected_plan": {"candidate_indices": [2, 0, 0, 0, 0, 0]},
            "robust_formal_plan_found": True,
            "causal_mode": "first_action_plan",
            "selected_first_action_index": 2,
            "selected_first_action_mode": "safe_nonzero_first_action",
        }
        left = independent44._planning_selection({"plans": [row]})
        right = independent44._planning_selection({"plans": [copy.deepcopy(row)]})
        self.assertEqual(left, right)
        right[0]["selected_first_action_index"] = 0
        self.assertNotEqual(left, right)

    def test_independent_owns_model_path_and_uses_separate_ensemble_implementation(self):
        self.assertIsNot(independent44.ind43._fit_model, source_r8r43.fit_model)
        self.assertIsNot(independent44.ind43._predict, source_r8r43.predict)
        self.assertIsNot(independent44.audit, r8r44.compute_from_bank)

    def test_finalizer_requires_all_dual_agreements_and_seals_zero_tsc(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / r8r44.RUN_NAME
            paths = r8r44.Paths(
                stage=stage,
                analysis=stage / "analysis",
                model=stage / "model",
                state=stage / "stage_state.json",
                manifest=stage / "stage_manifest.json",
            )
            summary = {
                "route": self.cfg["routes"]["authority_fail"],
                "scientific_gate_passed": False,
            }
            detailed = {
                "source_model_binding": {"passed": True},
                "source_model_evaluation": {},
                "planning_evaluation": {"passed": False},
                "fault_injection": {"passed": True},
            }
            r8r44._write(paths.analysis / "primary_summary.json", summary)
            r8r44._write(paths.analysis / "primary_detailed.json", detailed)
            r8r44._write(paths.model / "preflight_model.json", {"model": "primary"})
            r8r44._write(paths.manifest, {"stage": r8r44.STAGE})
            r8r44._write(paths.state, {"primary_completed": True})
            independent = {
                "passed": True,
                **{field: True for field in r8r44.AGREEMENT_FIELDS},
                **{field: 0.0 for field in r8r44.DIFFERENCE_FIELDS},
                "route": summary["route"],
                "primary_summary_sha256": r8r44._sha(paths.analysis / "primary_summary.json"),
                "primary_detailed_sha256": r8r44._sha(paths.analysis / "primary_detailed.json"),
                "primary_model_sha256": r8r44._sha(paths.model / "preflight_model.json"),
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
            }
            r8r44._write(paths.analysis / "independent.json", independent)
            final = r8r44.run_finalize(self._ctx(paths))
            self.assertTrue(final["passed"])
            self.assertEqual(final["route"], summary["route"])
            self.assertFalse(final["real_tsc_executed"])
            self.assertFalse(final["controller_execution_authorized"])
            self.assertFalse(final["gate_a_qualified"])


if __name__ == "__main__":
    unittest.main()
