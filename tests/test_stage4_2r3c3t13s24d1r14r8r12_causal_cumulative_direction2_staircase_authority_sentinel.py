from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r12_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel as sentinel,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel_370ms.json"
)


class CausalCumulativeDirection2StaircaseAuthoritySentinelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_contract(self) -> None:
        sentinel.validate_config(self.cfg, project_root=ROOT)
        self.assertEqual(self.cfg["schedule_contract"]["decision_task_steps"], [10, 14, 18, 22])
        self.assertEqual(self.cfg["schedule_contract"]["total_spec_count"], 16)
        self.assertEqual(self.cfg["scientific_gate"]["minimum_repaired_failed_baseline_count"], 1)
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])

    def test_contract_rejects_timing_safety_and_learning_mutation(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["formal_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["maximum_incremental_normalized_action_linf"] = 0.26
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["scientific_scope"]["expert_data_allowed"] = True
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)

    def test_design_document_and_matrix_hashes_are_frozen(self) -> None:
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(hashlib.sha256(design.read_bytes()).hexdigest(), self.cfg["design_document_sha256"])
        matrix = np.asarray(self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype="<f8")
        self.assertEqual(hashlib.sha256(matrix.tobytes(order="C")).hexdigest(), self.cfg["schedule_contract"]["canonical_matrix_float64_le_c_sha256"])

    def test_build_specs_freezes_one_direction2_positive_staircase_per_context(self) -> None:
        sources = []
        for pair in self.cfg["context_contract"]["ordered_pairs"]:
            for history in self.cfg["context_contract"]["histories"]:
                sources.append(
                    {
                        "experiment_id": f"baseline_{len(sources):02d}",
                        "pair_id": pair,
                        "history_member": history,
                        "horizon_steps": 35,
                    }
                )
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(sources, {})):
            specs = sentinel.build_specs(context)
        self.assertEqual(len(specs), 16)
        self.assertEqual(sum(row["partition"] == "safety" for row in specs), 4)
        self.assertTrue(all(row["r8r12_direction_index"] == 2 for row in specs))
        self.assertTrue(all(row["r8r12_sign"] == 1 for row in specs))
        self.assertTrue(all(row["r8r12_allowed_in_expert_dataset"] is False for row in specs))

    def test_controller_freezes_four_decisions_and_never_schedules_cancel(self) -> None:
        spec = {
            "r8r12_decision_task_steps": [10, 14, 18, 22],
            "r8r12_requested_coordinate": np.asarray(
                self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float
            )[:, 2].tolist(),
        }
        with mock.patch.object(r6.MixedBasisSignedExcitationController, "__init__", return_value=None) as parent:
            controller = sentinel.CausalCumulativeDirection2StaircaseController(
                object(), {}, {}, {}, {}, {}, {}, {}, self.cfg["controller_contract"], spec=spec
            )
        self.assertEqual(controller.r8r12_decisions, (10, 14, 18, 22))
        self.assertEqual(parent.call_args.kwargs["issue_step"], 10)
        self.assertEqual(parent.call_args.kwargs["cancel_step"], 11)
        self.assertEqual(parent.call_args.kwargs["zero_after_step"], 12)
        source = Path(sentinel.__file__).read_text(encoding="utf-8")
        self.assertNotIn("staircase_cancel", source)
        self.assertIn("staircase_refresh", source)

    def test_routes_separate_preflight_execution_and_authority_failure(self) -> None:
        routes = self.cfg["routes"]
        self.assertEqual(len(set(routes.values())), 4)
        self.assertIn("NO_TSC", routes["source_fail"])
        self.assertIn("SAFETY_FAIL_STOP", routes["execution_fail"])
        self.assertIn("AUTHORITY_INSUFFICIENT", routes["authority_fail"])
        self.assertIn("AUTHORITY_PRESENT", routes["pass"])

    def test_source_wrapper_metadata_is_not_executable_prefix_semantics(self) -> None:
        source = {
            "action_norm_tsc": [0.0] * 14,
            "r3c3t13s24d1r14r4_controller_revision": "source-wrapper",
            "r3c3t13s24d1r14r8r7_event": "none",
        }
        current = {"action_norm_tsc": [0.0] * 14}
        self.assertTrue(sentinel._source_trace_semantic_projection(source, current))
        self.assertTrue(independent._source_trace_projection(source, current))
        current["action_norm_tsc"][0] = 1.0
        self.assertFalse(sentinel._source_trace_semantic_projection(source, current))
        self.assertFalse(independent._source_trace_projection(source, current))

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel as",
            source,
        )
        self.assertIn("default=math.inf", source)

    def test_launcher_uses_existing_server_venv_and_direct_file_workflow(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r12_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("--r8r11-run", source)
        self.assertIn("authorize-safety", source)
        self.assertIn("authorize-qualification", source)
        self.assertIn("final-independent", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
