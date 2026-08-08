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
    stage4_2r3c3t13s24d1r14r8r15_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel as sentinel,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel_370ms.json"
)


class BinaryTemporalSwitchingStaircaseAuthoritySentinelTests(unittest.TestCase):
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
        self.assertEqual(
            schedule["symbols"],
            {
                "U": {"direction_index": 2, "sign": 1},
                "V": {"direction_index": 1, "sign": -1},
            },
        )
        self.assertEqual(schedule["reused_sequences"], ["UUUU", "VVVV"])
        self.assertEqual(
            schedule["new_sequences"],
            ["UVVV", "UUVV", "UUUV", "VUUU", "VVUU", "VVVU", "UVUV", "VUVU"],
        )
        self.assertEqual((schedule["safety_spec_count"], schedule["qualification_spec_count"], schedule["total_spec_count"], schedule["final_atlas_spec_count"]), (32, 96, 128, 176))
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
        changed["schedule_contract"]["new_sequences"][0] = "UUUU"
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)

    def test_design_document_and_matrix_hashes_are_frozen(self) -> None:
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(hashlib.sha256(design.read_bytes()).hexdigest(), self.cfg["design_document_sha256"])
        matrix = np.asarray(self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype="<f8")
        self.assertEqual(hashlib.sha256(matrix.tobytes(order="C")).hexdigest(), self.cfg["schedule_contract"]["canonical_matrix_float64_le_c_sha256"])

    def test_build_specs_freezes_eight_new_sequences_per_context(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            specs = sentinel.build_specs(context)
        self.assertEqual(len(specs), 128)
        self.assertEqual(sum(row["partition"] == "safety" for row in specs), 32)
        self.assertEqual(sum(row["partition"] == "qualification" for row in specs), 96)
        expected = set(self.cfg["schedule_contract"]["new_sequences"])
        for index in range(16):
            group = specs[index * 8 : (index + 1) * 8]
            self.assertEqual({row["r8r15_sequence_code"] for row in group}, expected)
            self.assertTrue(all(len(row["r8r15_sequence"]) == 4 for row in group))
        self.assertTrue(all(row["r8r15_allowed_in_expert_dataset"] is False for row in specs))

    def test_primary_and_independent_spec_construction_are_identical(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            primary = sentinel.build_specs(context)
        args = SimpleNamespace()
        with mock.patch.object(independent, "_source_baselines", return_value=(self._sources(), {})):
            audited = independent._expected_specs(args, self.cfg, SimpleNamespace())
        self.assertEqual(primary, audited)

    def test_controller_freezes_binary_code_and_four_decisions(self) -> None:
        matrix = np.asarray(
            self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float
        )
        code = "UVVV"
        sequence = []
        for symbol in code:
            definition = self.cfg["schedule_contract"]["symbols"][symbol]
            direction, sign = definition["direction_index"], definition["sign"]
            sequence.append(
                {
                    "symbol": symbol,
                    "direction_index": direction,
                    "sign": sign,
                    "requested_coordinate": (matrix[:, direction] * sign).tolist(),
                }
            )
        spec = {
            "r8r15_decision_task_steps": [10, 14, 18, 22],
            "r8r15_sequence_code": code,
            "r8r15_sequence": sequence,
        }
        contract = copy.deepcopy(self.cfg["controller_contract"])
        contract["requested_coordinate_matrix_columns"] = matrix.tolist()
        with mock.patch.object(r6.MixedBasisSignedExcitationController, "__init__", return_value=None) as parent:
            controller = sentinel.BinaryTemporalSwitchingStaircaseController(
                object(), {}, {}, {}, {}, {}, {}, {}, contract, spec=spec
            )
        self.assertEqual(controller.r8r15_decisions, (10, 14, 18, 22))
        self.assertEqual(controller.r8r15_sequence_code, code)
        self.assertEqual(parent.call_args.kwargs["direction_index"], 2)
        self.assertEqual(parent.call_args.kwargs["sign"], 1)
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

    def test_issue_symbol_switches_only_to_the_frozen_next_coordinate(self) -> None:
        matrix = np.asarray(
            self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float
        )
        sequence = [
            {
                "symbol": symbol,
                "direction_index": self.cfg["schedule_contract"]["symbols"][symbol]["direction_index"],
                "sign": self.cfg["schedule_contract"]["symbols"][symbol]["sign"],
                "requested_coordinate": (
                    matrix[:, self.cfg["schedule_contract"]["symbols"][symbol]["direction_index"]]
                    * self.cfg["schedule_contract"]["symbols"][symbol]["sign"]
                ).tolist(),
            }
            for symbol in "UVVV"
        ]
        contract = copy.deepcopy(self.cfg["controller_contract"])
        contract["requested_coordinate_matrix_columns"] = matrix.tolist()
        with mock.patch.object(r6.MixedBasisSignedExcitationController, "__init__", return_value=None):
            controller = sentinel.BinaryTemporalSwitchingStaircaseController(
                object(), {}, {}, {}, {}, {}, {}, {}, contract,
                spec={
                    "r8r15_decision_task_steps": [10, 14, 18, 22],
                    "r8r15_sequence_code": "UVVV",
                    "r8r15_sequence": sequence,
                },
            )
        with mock.patch.object(
            r6.MixedBasisSignedExcitationController,
            "_issue",
            return_value=(np.zeros(14), {"passed": True, "target_card15_fields": ["0.000E+00"] * 14}),
        ) as issue:
            _, event = controller._issue_symbol(1, np.zeros(14))
        self.assertEqual(issue.call_args.args[0], 1)
        self.assertEqual(controller.d1r14r6_sign, -1)
        self.assertTrue(np.array_equal(controller.d1r14r6_requested_coordinate, -matrix[:, 1]))
        self.assertEqual((event["sequence_code"], event["sequence_level"], event["symbol"]), ("UVVV", 2, "V"))

    def test_formal_audit_uses_two_reused_and_eight_new_sequences(self) -> None:
        primary = inspect.getsource(sentinel.compute_formal_authority)
        audited = inspect.getsource(independent.final_audit)
        for source in (primary, audited):
            self.assertIn('"source": "R8R12"', source)
            self.assertIn('"source": "R8R14"', source)
            self.assertIn('"source": "R8R15"', source)
            self.assertIn("len(candidates) != 10", source)
            self.assertIn("held_oracle", source)
        self.assertIn("row_count", primary)
        self.assertIn("len(rows) == 176", audited)

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r15_binary_temporal_switching_staircase_authority_sentinel as",
            source,
        )
        self.assertIn("_source_r8r12_candidates", source)
        self.assertIn("_source_r8r14_candidates", source)

    def test_launcher_uses_existing_server_venv_and_direct_file_workflow(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r15_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("--r8r12-run", source)
        self.assertIn("--r8r14-run", source)
        self.assertIn("authorize-safety", source)
        self.assertIn("authorize-qualification", source)
        self.assertIn("final-independent", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
