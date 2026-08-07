from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r11_independent_forensics as independent,
    stage4_2r3c3t13s24d1r14r8r11_source_prefix_reporting_hotfix as reporting_hotfix,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel as sentinel,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel_370ms.json"


class SustainedExactTargetRefreshAuthoritySentinelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_contract(self) -> None:
        sentinel.validate_config(self.cfg, project_root=ROOT)
        self.assertEqual(self.cfg["schedule_contract"]["total_spec_count"], 96)
        self.assertEqual(self.cfg["schedule_contract"]["safety_spec_count"], 24)
        self.assertEqual(self.cfg["schedule_contract"]["qualification_spec_count"], 72)
        self.assertEqual(self.cfg["scientific_gate"]["minimum_repaired_failed_baseline_count"], 1)
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])

    def test_contract_rejects_timing_safety_and_learning_mutation(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["formal_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["maximum_online_cancel_incremental_linf"] = 0.25
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["scientific_scope"]["expert_data_allowed"] = True
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)

    def test_design_document_hash_is_frozen(self) -> None:
        path = ROOT / self.cfg["design_document"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(actual, self.cfg["design_document_sha256"])

    def test_controller_freezes_issue_refresh_cancel_offsets(self) -> None:
        spec = {
            "r8r11_issue_task_step": 18,
            "r8r11_refresh_task_step": 19,
            "r8r11_cancel_task_step": 20,
            "r8r11_sign": -1,
            "r8r11_requested_coordinate": np.asarray(
                self.cfg["schedule_contract"]["replacement_matrix_columns"], dtype=float
            )[:, 0].__neg__().tolist(),
        }
        with mock.patch.object(r6.MixedBasisSignedExcitationController, "__init__", return_value=None) as parent:
            controller = sentinel.SustainedRefreshController(
                object(), {}, {}, {}, {}, {}, {}, {}, self.cfg["controller_contract"], spec=spec
            )
        self.assertEqual(controller.r8r11_issue_step, 18)
        self.assertEqual(controller.r8r11_refresh_step, 19)
        self.assertEqual(controller.r8r11_cancel_step, 20)
        self.assertEqual(controller.r8r11_contract, self.cfg["controller_contract"])
        self.assertEqual(parent.call_args.kwargs["cancel_step"], 19)
        self.assertEqual(parent.call_args.kwargs["zero_after_step"], 20)

    def test_routes_separate_source_execution_and_authority_failure(self) -> None:
        routes = self.cfg["routes"]
        self.assertEqual(len(set(routes.values())), 4)
        self.assertIn("NO_TSC", routes["source_fail"])
        self.assertIn("SAFETY_FAIL_STOP", routes["execution_fail"])
        self.assertIn("AUTHORITY_INSUFFICIENT", routes["authority_fail"])
        self.assertIn("AUTHORITY_PRESENT", routes["pass"])

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r11_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel as",
            source,
        )

    def test_source_wrapper_metadata_is_not_executable_prefix_semantics(self) -> None:
        source = {
            "action_norm_tsc": [0.0] * 14,
            "r3c3t13s24d1r14r4_controller_revision": "old-wrapper",
            "r3c3t13s24d1r14r8r7_event": "none",
        }
        current = {"action_norm_tsc": [0.0] * 14}
        self.assertTrue(independent._source_trace_semantic_projection(source, current))
        self.assertTrue(reporting_hotfix._semantic_projection(source, current))
        current["action_norm_tsc"][0] = 1.0
        self.assertFalse(independent._source_trace_semantic_projection(source, current))
        self.assertFalse(reporting_hotfix._semantic_projection(source, current))

    def test_reporting_hotfix_freezes_primary_controller_module_hash(self) -> None:
        path = ROOT / reporting_hotfix.PRIMARY_MODULE
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            reporting_hotfix.ORIGINAL_PRIMARY_MODULE_SHA256,
        )

    def test_launcher_uses_server_venv_direct_files_and_phase_commands(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r11_common.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("authorize-safety", source)
        self.assertIn("authorize-qualification", source)
        self.assertIn("final-independent", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
