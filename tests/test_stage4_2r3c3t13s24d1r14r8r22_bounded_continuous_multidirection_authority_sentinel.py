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
    stage4_2r3c3t13s24d1r14r8r22_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r22_bounded_continuous_multidirection_authority_sentinel as sentinel,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r22_bounded_continuous_multidirection_authority_sentinel_370ms.json"
)


class BoundedContinuousMultidirectionAuthoritySentinelTests(unittest.TestCase):
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
        self.assertEqual(schedule["endpoint_u"], {"direction_index": 2, "sign": 1})
        self.assertEqual(schedule["endpoint_v"], {"direction_index": 1, "sign": -1})
        self.assertEqual(
            schedule["mixing_weight_tokens"],
            ["0.00", "0.25", "0.50", "0.75", "1.00"],
        )
        self.assertEqual(schedule["amplitude_tokens"], ["1.25", "1.50"])
        self.assertEqual(
            (
                schedule["safety_spec_count"],
                schedule["qualification_spec_count"],
                schedule["total_spec_count"],
                schedule["source_formal_spec_count"],
                schedule["final_formal_row_count"],
            ),
            (40, 120, 160, 256, 432),
        )
        self.assertFalse(self.cfg["scientific_scope"]["held_oracle_is_causal_selector"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])

    def test_contract_rejects_timing_safety_candidate_and_learning_mutation(self) -> None:
        mutations = (
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("controller_contract", "maximum_incremental_normalized_action_linf", 0.26),
            ("scientific_scope", "expert_data_allowed", True),
            ("schedule_contract", "mixing_weight_tokens", ["0.00", "0.50", "1.00"]),
        )
        for section, key, value in mutations:
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design"):
                sentinel.validate_config(changed, project_root=ROOT)

    def test_design_document_and_matrix_hashes_are_frozen(self) -> None:
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(
            hashlib.sha256(design.read_bytes()).hexdigest(),
            self.cfg["design_document_sha256"],
        )
        matrix = np.asarray(
            self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype="<f8"
        )
        self.assertEqual(
            hashlib.sha256(matrix.tobytes(order="C")).hexdigest(),
            self.cfg["schedule_contract"]["canonical_matrix_float64_le_c_sha256"],
        )

    def test_candidate_grid_is_amplitude_major_and_uses_exact_endpoints(self) -> None:
        rows = sentinel._candidate_definitions(self.cfg["schedule_contract"])
        audited = independent._candidate_definitions(self.cfg)
        self.assertEqual(rows, audited)
        self.assertEqual(
            [row["candidate_id"] for row in rows],
            [
                "a1p25_w0p00", "a1p25_w0p25", "a1p25_w0p50",
                "a1p25_w0p75", "a1p25_w1p00", "a1p50_w0p00",
                "a1p50_w0p25", "a1p50_w0p50", "a1p50_w0p75",
                "a1p50_w1p00",
            ],
        )
        matrix = np.asarray(
            self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype=float
        )
        self.assertTrue(np.array_equal(rows[0]["requested_coordinate"], -1.25 * matrix[:, 1]))
        self.assertTrue(np.array_equal(rows[-1]["requested_coordinate"], 1.50 * matrix[:, 2]))

    def test_build_specs_freezes_ten_candidates_per_context(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            specs = sentinel.build_specs(context)
        self.assertEqual(len(specs), 160)
        self.assertEqual(sum(row["partition"] == "safety" for row in specs), 40)
        self.assertEqual(sum(row["partition"] == "qualification" for row in specs), 120)
        expected = {row["candidate_id"] for row in sentinel._candidate_definitions(self.cfg["schedule_contract"])}
        for index in range(16):
            group = specs[index * 10 : (index + 1) * 10]
            self.assertEqual({row["r8r22_candidate_id"] for row in group}, expected)
            self.assertTrue(all(len(row["r8r22_requested_coordinate"]) == 4 for row in group))
        self.assertTrue(all(row["r8r22_allowed_in_expert_dataset"] is False for row in specs))

    def test_primary_and_independent_spec_construction_are_identical(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            primary = sentinel.build_specs(context)
        with mock.patch.object(independent, "_source_baselines", return_value=(self._sources(), {})):
            audited = independent._expected_specs(SimpleNamespace(), self.cfg, SimpleNamespace())
        self.assertEqual(primary, audited)

    def test_controller_freezes_coordinate_and_four_decisions(self) -> None:
        candidate = sentinel._candidate_definitions(self.cfg["schedule_contract"])[3]
        spec = {
            "r8r22_decision_task_steps": [10, 14, 18, 22],
            "r8r22_candidate_id": candidate["candidate_id"],
            "r8r22_amplitude_token": candidate["amplitude_token"],
            "r8r22_mixing_weight_token": candidate["mixing_weight_token"],
            "r8r22_requested_coordinate": candidate["requested_coordinate"],
        }
        contract = copy.deepcopy(self.cfg["controller_contract"])
        matrix = self.cfg["schedule_contract"]["canonical_matrix_columns"]
        contract["requested_coordinate_matrix_columns"] = matrix
        with mock.patch.object(
            r6.MixedBasisSignedExcitationController, "__init__", return_value=None
        ) as parent:
            controller = sentinel.BoundedContinuousMultidirectionController(
                object(), {}, {}, {}, {}, {}, {}, {}, contract, spec=spec
            )
        self.assertEqual(controller.r8r22_decisions, (10, 14, 18, 22))
        self.assertEqual(controller.r8r22_candidate_id, candidate["candidate_id"])
        self.assertTrue(
            np.array_equal(
                controller.r8r22_requested_coordinate,
                np.asarray(candidate["requested_coordinate"], dtype=float),
            )
        )
        self.assertEqual(parent.call_args.kwargs["direction_index"], 2)
        self.assertEqual(parent.call_args.kwargs["sign"], 1)
        self.assertEqual(parent.call_args.kwargs["issue_step"], 14)

    def test_controller_uses_explicit_coordinate_issue_and_never_cancels(self) -> None:
        source = inspect.getsource(sentinel.BoundedContinuousMultidirectionController)
        self.assertIn("_construct_coordinate_issue", source)
        self.assertNotIn("super()._issue(", source)
        self.assertNotIn("staircase_cancel", source)
        self.assertIn("staircase_refresh", source)

    def test_routes_separate_preflight_execution_authority_and_feedback_design(self) -> None:
        routes = self.cfg["routes"]
        self.assertEqual(len(set(routes.values())), 4)
        self.assertIn("NO_TSC", routes["source_fail"])
        self.assertIn("SAFETY_FAIL_STOP", routes["execution_fail"])
        self.assertIn("AUTHORITY_INSUFFICIENT", routes["authority_fail"])
        self.assertIn("CAUSAL_RECEDING_HORIZON_CONTROLLER_DESIGN_REQUIRED", routes["pass"])

    def test_formal_audits_authenticate_sources_and_restrict_oracle_to_new_family(self) -> None:
        primary = inspect.getsource(sentinel.compute_formal_authority)
        audited = inspect.getsource(independent.final_audit)
        for source in (primary, audited):
            self.assertIn('"source": "R8R12"', source)
            self.assertIn('"source": "R8R14"', source)
            self.assertIn('"source": "R8R15"', source)
            self.assertIn('"source": "R8R20"', source)
            self.assertIn('"source": "R8R22"', source)
            self.assertIn("len(source_candidates) != 16", source)
            self.assertIn("len(new_candidates) != 10", source)
            self.assertIn("[base, *new_candidates]", source)
        self.assertIn("final_formal_row_count", inspect.getsource(sentinel.finalize_primary))
        self.assertIn("final_formal_row_count", audited)

    def test_primary_and_independent_load_all_96_r8r20_source_candidates(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        rows = []
        safety = set(cfg["context_contract"]["safety_pairs"])
        for pair in cfg["context_contract"]["ordered_pairs"]:
            for history in cfg["context_contract"]["histories"]:
                for code in cfg["schedule_contract"]["source_r8r20_sequences"]:
                    rows.append(
                        {
                            "experiment_id": f"r8r20_{len(rows):02d}",
                            "pair_id": pair,
                            "history_member": history,
                            "partition": "safety" if pair in safety else "qualification",
                            "r8r20_sequence_code": code,
                            "r8r20_sequence": [{"symbol": symbol} for symbol in code],
                            "r8r20_decision_task_steps": [10, 14, 18, 22],
                        }
                    )
        self.assertEqual(len(rows), 96)
        cfg["source_r8r20"]["spec_digest"] = sentinel._digest(rows)
        context = SimpleNamespace(cfg=cfg)
        with (
            mock.patch.object(sentinel, "_r8r20_stage", return_value=Path("source")),
            mock.patch.object(sentinel, "_read", return_value=copy.deepcopy(rows)),
            mock.patch.object(sentinel.r8r7.r8, "_read_gz", return_value={}),
        ):
            primary_specs, primary_results = sentinel._source_r8r20_candidates(context)
        with (
            mock.patch.object(independent, "_r8r20_stage", return_value=Path("source")),
            mock.patch.object(independent, "_read", return_value=copy.deepcopy(rows)),
            mock.patch.object(independent, "_gzip", return_value={}),
        ):
            audited_specs, audited_results = independent._source_r8r20_candidates(
                SimpleNamespace(), cfg
            )
        self.assertEqual(primary_specs, audited_specs)
        self.assertEqual(len(primary_specs), 96)
        self.assertEqual(len(primary_results), 96)
        self.assertEqual(primary_results, audited_results)

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r22_bounded_continuous_multidirection_authority_sentinel as",
            source,
        )
        self.assertIn("_coordinate_issue", source)
        self.assertIn("_source_r8r20_candidates", source)

    def test_launcher_uses_existing_server_venv_and_direct_file_workflow(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r22_common.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source
        )
        for argument in ("--r8r12-run", "--r8r14-run", "--r8r15-run", "--r8r19-run", "--r8r20-run"):
            self.assertIn(argument, source)
        self.assertIn("maximum 160 fresh", source)
        self.assertIn("authorize-safety", source)
        self.assertIn("authorize-qualification", source)
        self.assertIn("final-independent", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
