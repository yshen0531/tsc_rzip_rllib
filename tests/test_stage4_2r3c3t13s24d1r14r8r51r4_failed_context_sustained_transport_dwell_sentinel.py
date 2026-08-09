from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r4_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel
    as r4,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / (
    "stage4_2r3c3t13s24d1r14r8r51r4_"
    "failed_context_sustained_transport_dwell_sentinel_370ms.json"
)


class R8R51R4SustainedDwellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_design_hash(self) -> None:
        r4.validate_config(self.cfg, project_root=ROOT)
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(
            hashlib.sha256(design.read_bytes()).hexdigest(),
            self.cfg["design_document_sha256"],
        )
        self.assertEqual(tuple(self.cfg["matrix_contract"]["candidate_ids"]), r4.SELECTED_CANDIDATE_IDS)
        self.assertEqual(tuple(self.cfg["matrix_contract"]["return_task_steps"]), r4.RETURN_STEPS)
        self.assertEqual(self.cfg["matrix_contract"]["trajectory_count"], 100)
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])

    def test_mutations_fail_closed(self) -> None:
        for section, key, value in (
            ("matrix_contract", "trajectory_count", 99),
            ("schedule_contract", "stored_center_return_task_steps", [16, 19]),
            ("controller_contract", "maximum_incremental_normalized_action_linf", 0.26),
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("known_aggregate_contract", "baseline_formal_pass_count", 7),
            ("scientific_gate", "minimum_repaired_failed_baseline_count", 0),
            ("scientific_scope", "model_fit_allowed", True),
        ):
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design changed"):
                r4.validate_config(changed, project_root=ROOT)

    def test_build_specs_is_exact_failed_context_candidate_dwell_product(self) -> None:
        baseline_ids = self.cfg["matrix_contract"]["failed_source_baseline_ids"]
        baselines = [
            {
                "experiment_id": baseline_id,
                "pair_id": f"pair_{index // 2}",
                "history_member": "minus_first" if index % 2 == 0 else "plus_first",
                "horizon_steps": 35 if index < 8 else 37,
                "formal_horizon_steps": 35 if index < 8 else 37,
            }
            for index, baseline_id in enumerate(baseline_ids)
        ]
        source_specs = []
        candidate_index = {"d0m": 1, "d1p": 3, "d2m": 4, "d3p": 6, "u1p50": 11}
        for baseline in baselines:
            for candidate_id in r4.SELECTED_CANDIDATE_IDS:
                source_specs.append(
                    {
                        "experiment_id": f"old_{baseline['experiment_id']}_{candidate_id}",
                        "source_r8r7_baseline_experiment_id": baseline["experiment_id"],
                        "r8r51r1_candidate_index": candidate_index[candidate_id],
                        "r8r51r1_candidate_id": candidate_id,
                        "r8r51r1_candidate_q": [1.0, 0.0, 0.0, 0.0],
                        "r8r51r1_requested_coordinate": [1.0, 2.0, 3.0, 4.0],
                    }
                )
        ctx = SimpleNamespace(
            cfg=self.cfg, base_ctx=object(), r51r1_stage=Path("source")
        )
        with mock.patch.object(r4.r51, "_source_baselines", return_value=(baselines, {})), mock.patch.object(
            r4, "_read", return_value=source_specs
        ):
            specs = r4.build_specs(ctx)
        self.assertEqual(len(specs), 100)
        self.assertEqual({row["r8r51r4_candidate_id"] for row in specs}, set(r4.SELECTED_CANDIDATE_IDS))
        self.assertEqual({row["r8r51r4_return_task_step"] for row in specs}, set(r4.RETURN_STEPS))
        self.assertEqual({row["source_r8r7_baseline_experiment_id"] for row in specs}, set(baseline_ids))
        self.assertTrue(all(row["r8r51r4_allowed_in_expert_dataset"] is False for row in specs))
        self.assertTrue(all(row["formal_timing_unchanged"] is True for row in specs))

    def test_controller_freezes_return_step_and_reuses_exact_primitives(self) -> None:
        spec = {
            "r8r51r1_candidate_id": "d0m",
            "r8r51r1_requested_coordinate": [1.0, 0.0, 0.0, 0.0],
            "r8r51r4_return_task_step": 18,
        }
        contract = copy.deepcopy(self.cfg["controller_contract"])
        contract["requested_coordinate_matrix_columns"] = np.eye(4).tolist()
        with mock.patch.object(
            r6.d1r11.SequentialAmplitudeCodedProbeController, "__init__", return_value=None
        ), mock.patch.object(r6, "_controller_source_spec", return_value={}):
            controller = r4.SustainedDwellController(
                object(), {}, {}, {}, {}, {}, {}, {}, contract, spec=spec
            )
        self.assertEqual(controller.r8r51r4_return_step, 18)
        source = inspect.getsource(r4.SustainedDwellController)
        self.assertIn("_issue_candidate", source)
        self.assertIn("_return", source)
        self.assertIn("_center_refresh", source)
        self.assertIn("candidate_current_dwell_hold", source)

    def test_controller_dwell_is_zero_increment_and_does_not_repeat_issue(self) -> None:
        controller = object.__new__(r4.SustainedDwellController)
        controller.step = 15
        controller.r8r51r4_return_step = 18
        controller.r8r51r1_issue_event = {"target_card15_fields": [" 0.000E+00"] * 14}
        controller.r8r51r1_contract = self.cfg["controller_contract"]
        controller.actuator = object()
        controller._issue_candidate = mock.Mock(side_effect=AssertionError("issue repeated"))
        state = {"step_index": 15, "currents_a_tsc": [0.0] * 14}
        event = {
            "event": "candidate_current_dwell_hold", "passed": True,
            "criteria": {"zero_action": True}, "action_norm_tsc": [0.0] * 14,
        }
        with mock.patch.object(r4.r51, "_observe_event", return_value=event) as observe, mock.patch.object(
            r6, "_trace_template", return_value={}
        ):
            action, trace = controller.action(state)
        self.assertTrue(np.array_equal(action, np.zeros(14)))
        self.assertEqual(observe.call_count, 1)
        self.assertEqual(trace["r3c3t13s24d1r14r8r51r4_event"], "candidate_dwell_hold")
        controller._issue_candidate.assert_not_called()

    def test_each_return_step_has_exact_dwell_count(self) -> None:
        self.assertEqual({step: step - 13 for step in r4.RETURN_STEPS}, {16: 3, 18: 5})
        source = inspect.getsource(r4.construct_event_stream)
        self.assertIn("range(ISSUE_STEP + 1, return_step)", source)
        self.assertIn("_return_event", source)
        self.assertIn("range(return_step + 1", source)

    def test_raw_and_formal_results_are_separated(self) -> None:
        run_source = inspect.getsource(r4.run_real)
        finalize_source = inspect.getsource(r4.finalize_primary)
        self.assertIn("audit_raw_integrity", run_source)
        self.assertNotIn("_formal_authority", run_source)
        self.assertIn("response_outcomes_opened=False", run_source)
        self.assertIn("_formal_authority", finalize_source)
        self.assertIn("raw_integrity_independent", finalize_source)

    def test_routes_distinguish_all_failure_layers_and_successor(self) -> None:
        routes = self.cfg["routes"]
        self.assertEqual(len(set(routes.values())), 5)
        self.assertIn("BLOCKED_BY_SOURCE", routes["source_blocked"])
        self.assertIn("NO_REAL_TSC", routes["offline_fail"])
        self.assertIn("EXECUTION_FAIL_STOP", routes["execution_fail"])
        self.assertIn("AUTHORITY_INSUFFICIENT", routes["authority_insufficient"])
        self.assertIn("R51R5_MODEL_PREFLIGHT_REQUIRED", routes["pass"])

    def test_independent_paths_are_separate_and_scalar(self) -> None:
        self.assertIsNot(independent.offline, r4.prepare_offline)
        self.assertIsNot(independent.raw, r4.audit_raw_integrity)
        self.assertIsNot(independent.formal, r4._formal_authority)
        offline_source = inspect.getsource(independent._independent_event_stream)
        formal_source = inspect.getsource(independent.formal)
        self.assertNotIn("construct_event_stream", offline_source)
        self.assertIn("scalar_formal_metric", formal_source)

    def test_scientific_and_learning_boundaries_remain_closed(self) -> None:
        self.assertEqual(self.cfg["known_aggregate_contract"]["baseline_formal_pass_count"], 6)
        self.assertEqual(self.cfg["scientific_gate"]["minimum_measured_oracle_formal_pass_count"], 7)
        self.assertFalse(self.cfg["formal_contract"]["arrival_deadline_expansion_allowed"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_runner_carries_both_new_source_runs_and_all_phases(self) -> None:
        runner = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r51r4_common.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--r51r1-run", runner)
        self.assertIn("--r51r3-run", runner)
        self.assertIn("independent-offline", runner)
        self.assertIn("independent-raw", runner)
        self.assertIn("independent-formal", runner)
        self.assertIn("--resume", runner)
        self.assertIn(
            "stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel",
            runner,
        )


if __name__ == "__main__":
    unittest.main()
