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
    stage4_2r3c3t13s24d1r14r8r14_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification as sentinel,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification_370ms.json"
)


class CumulativeMultidirectionStaircaseAuthorityIdentificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def _sources(self) -> list[dict[str, object]]:
        rows = []
        for pair in self.cfg["context_contract"]["ordered_pairs"]:
            for history in self.cfg["context_contract"]["histories"]:
                rows.append(
                    {
                        "experiment_id": f"baseline_{len(rows):02d}",
                        "pair_id": pair,
                        "history_member": history,
                        "horizon_steps": 35,
                    }
                )
        return rows

    def test_frozen_design_contract(self) -> None:
        sentinel.validate_config(self.cfg, project_root=ROOT)
        schedule = self.cfg["schedule_contract"]
        self.assertEqual(schedule["decision_task_steps"], [10, 14, 18, 22])
        self.assertEqual(schedule["new_candidates"], [[0, -1], [0, 1], [1, -1], [1, 1], [2, -1], [3, -1], [3, 1]])
        self.assertEqual(schedule["reused_candidate"], {"direction_index": 2, "sign": 1})
        self.assertEqual((schedule["safety_spec_count"], schedule["qualification_spec_count"], schedule["total_spec_count"], schedule["final_atlas_spec_count"]), (28, 84, 112, 128))
        self.assertFalse(self.cfg["scientific_scope"]["held_oracle_is_causal_selector"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])

    def test_contract_rejects_timing_safety_candidate_and_learning_mutation(self) -> None:
        mutations = (
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("controller_contract", "maximum_incremental_normalized_action_linf", 0.26),
            ("scientific_scope", "expert_data_allowed", True),
        )
        for section, key, value in mutations:
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design"):
                sentinel.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["new_candidates"][0] = [2, 1]
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)

    def test_design_document_and_matrix_hashes_are_frozen(self) -> None:
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(hashlib.sha256(design.read_bytes()).hexdigest(), self.cfg["design_document_sha256"])
        matrix = np.asarray(self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype="<f8")
        self.assertEqual(hashlib.sha256(matrix.tobytes(order="C")).hexdigest(), self.cfg["schedule_contract"]["canonical_matrix_float64_le_c_sha256"])

    def test_build_specs_freezes_seven_new_candidates_per_context(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            specs = sentinel.build_specs(context)
        self.assertEqual(len(specs), 112)
        self.assertEqual(sum(row["partition"] == "safety" for row in specs), 28)
        self.assertEqual(sum(row["partition"] == "qualification" for row in specs), 84)
        expected = {tuple(row) for row in self.cfg["schedule_contract"]["new_candidates"]}
        for index in range(16):
            group = specs[index * 7 : (index + 1) * 7]
            self.assertEqual({(row["r8r14_direction_index"], row["r8r14_sign"]) for row in group}, expected)
        self.assertTrue(all(row["r8r14_allowed_in_expert_dataset"] is False for row in specs))

    def test_primary_and_independent_spec_construction_are_identical(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            primary = sentinel.build_specs(context)
        args = SimpleNamespace()
        with mock.patch.object(independent, "_source_baselines", return_value=(self._sources(), {})):
            audited = independent._expected_specs(args, self.cfg, SimpleNamespace())
        self.assertEqual(primary, audited)

    def test_controller_freezes_candidate_direction_sign_and_four_decisions(self) -> None:
        requested = -np.asarray(
            self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float
        )[:, 3]
        spec = {
            "r8r14_decision_task_steps": [10, 14, 18, 22],
            "r8r14_direction_index": 3,
            "r8r14_sign": -1,
            "r8r14_requested_coordinate": requested.tolist(),
        }
        with mock.patch.object(r6.MixedBasisSignedExcitationController, "__init__", return_value=None) as parent:
            controller = sentinel.CumulativeMultidirectionStaircaseController(
                object(), {}, {}, {}, {}, {}, {}, {}, self.cfg["controller_contract"], spec=spec
            )
        self.assertEqual(controller.r8r14_decisions, (10, 14, 18, 22))
        self.assertEqual(controller.r8r14_direction, 3)
        self.assertEqual(parent.call_args.kwargs["direction_index"], 3)
        self.assertEqual(parent.call_args.kwargs["sign"], -1)
        self.assertEqual(parent.call_args.kwargs["issue_step"], 14)
        source = Path(sentinel.__file__).read_text(encoding="utf-8")
        self.assertNotIn("staircase_cancel", source)
        self.assertIn("staircase_refresh", source)

    def test_routes_separate_preflight_execution_authority_and_selector_design(self) -> None:
        routes = self.cfg["routes"]
        self.assertEqual(len(set(routes.values())), 4)
        self.assertIn("NO_TSC", routes["source_fail"])
        self.assertIn("SAFETY_FAIL_STOP", routes["execution_fail"])
        self.assertIn("AUTHORITY_INSUFFICIENT", routes["authority_fail"])
        self.assertIn("CAUSAL_SELECTOR_DESIGN_REQUIRED", routes["pass"])

    def test_formal_audit_uses_baseline_reused_and_seven_new_candidates(self) -> None:
        primary = inspect.getsource(sentinel.compute_formal_authority)
        audited = inspect.getsource(independent.final_audit)
        for source in (primary, audited):
            self.assertIn('"source": "R8R12"', source)
            self.assertIn('"source": "R8R14"', source)
            self.assertIn("len(candidates) != 8", source)
            self.assertIn("held_oracle", source)
        self.assertIn("row_count", primary)
        self.assertIn("len(rows) == 144", audited)

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification as",
            source,
        )
        self.assertIn("_source_r8r12_candidates", source)

    def test_launcher_uses_existing_server_venv_and_direct_file_workflow(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r14_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("--r8r12-run", source)
        self.assertIn("--r8r13-run", source)
        self.assertIn("authorize-safety", source)
        self.assertIn("authorize-qualification", source)
        self.assertIn("final-independent", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
