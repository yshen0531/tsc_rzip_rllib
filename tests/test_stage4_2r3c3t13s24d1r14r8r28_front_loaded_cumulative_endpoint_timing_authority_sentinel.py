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
    stage4_2r3c3t13s24d1r14r8r28_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification as r14,
    stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel as sentinel,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel_370ms.json"


class FrontLoadedCumulativeEndpointTimingAuthoritySentinelTests(unittest.TestCase):
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
                        "horizon_steps": 37 if "a0p900" not in pair else 35,
                    }
                )
        return rows

    def test_frozen_design_contract(self) -> None:
        sentinel.validate_config(self.cfg, project_root=ROOT)
        schedule = self.cfg["schedule_contract"]
        self.assertEqual(
            [(row["grid_id"], row["decision_task_steps"]) for row in schedule["timing_grids"]],
            [("g3", [10, 13, 16, 19]), ("g2", [10, 12, 14, 16])],
        )
        self.assertEqual(
            [(row["sequence_id"], row["direction_index"], row["sign"]) for row in schedule["endpoint_sequences"]],
            [("UUUU", 2, 1), ("VVVV", 1, -1)],
        )
        self.assertEqual(
            (schedule["safety_spec_count"], schedule["qualification_spec_count"], schedule["total_spec_count"], schedule["issue_count"], schedule["refresh_count"]),
            (16, 48, 64, 256, 1408),
        )
        self.assertTrue(self.cfg["scientific_scope"]["real_timing_authority_sentinel_only"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])

    def test_contract_rejects_context_timing_safety_and_learning_mutation(self) -> None:
        mutations = (
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("controller_contract", "maximum_incremental_normalized_action_linf", 0.26),
            ("scientific_scope", "expert_data_allowed", True),
            ("scientific_scope", "real_timing_authority_sentinel_only", False),
        )
        for section, key, value in mutations:
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design"):
                sentinel.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["timing_grids"][0]["decision_task_steps"][-1] = 20
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["context_contract"]["ordered_pairs"][0] = "unknown"
        with self.assertRaisesRegex(ValueError, "frozen design"):
            sentinel.validate_config(changed, project_root=ROOT)

    def test_design_document_and_matrix_hashes_are_frozen(self) -> None:
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(hashlib.sha256(design.read_bytes()).hexdigest(), self.cfg["design_document_sha256"])
        matrix = np.asarray(self.cfg["schedule_contract"]["canonical_matrix_columns"], dtype="<f8")
        self.assertEqual(hashlib.sha256(matrix.tobytes(order="C")).hexdigest(), self.cfg["schedule_contract"]["canonical_matrix_float64_le_c_sha256"])

    def test_build_specs_freezes_four_schedules_per_context(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            specs = sentinel.build_specs(context)
        self.assertEqual(len(specs), 64)
        self.assertEqual(sum(row["partition"] == "safety" for row in specs), 16)
        self.assertEqual(sum(row["partition"] == "qualification" for row in specs), 48)
        expected = {
            ("g3", "UUUU", (10, 13, 16, 19), 2, 1),
            ("g3", "VVVV", (10, 13, 16, 19), 1, -1),
            ("g2", "UUUU", (10, 12, 14, 16), 2, 1),
            ("g2", "VVVV", (10, 12, 14, 16), 1, -1),
        }
        for index in range(16):
            group = specs[index * 4 : (index + 1) * 4]
            self.assertEqual(
                {
                    (
                        row["r8r28_grid_id"], row["r8r28_sequence_id"],
                        tuple(row["r8r28_decision_task_steps"]),
                        row["r8r28_direction_index"], row["r8r28_sign"],
                    )
                    for row in group
                },
                expected,
            )
            self.assertTrue(all(row["r8r28_allowed_in_expert_dataset"] is False for row in group))

    def test_primary_and_independent_specs_are_identical(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            primary = sentinel.build_specs(context)
        with mock.patch.object(independent, "_source_baselines", return_value=(self._sources(), {})):
            audited = independent._expected_specs(SimpleNamespace(), self.cfg, SimpleNamespace())
        self.assertEqual(primary, audited)

    def test_specs_preserve_exact_r8r14_low_level_contract_without_labels(self) -> None:
        context = SimpleNamespace(cfg=self.cfg)
        with mock.patch.object(sentinel, "_source_baselines", return_value=(self._sources(), {})):
            specs = sentinel.build_specs(context)
        for row in specs:
            self.assertEqual(row["r8r28_direction_index"], row["r8r14_direction_index"])
            self.assertEqual(row["r8r28_sign"], row["r8r14_sign"])
            self.assertEqual(row["r8r28_requested_coordinate"], row["r8r14_requested_coordinate"])
            self.assertEqual(row["r8r28_decision_task_steps"], row["r8r14_decision_task_steps"])
            self.assertFalse(row["pair_or_history_label_available_to_controller"])
            self.assertFalse(row["source_result_available_to_controller"])
            self.assertEqual(row["future_measurement_count"], 0)
            self.assertEqual(row["future_action_count"], 0)

    def test_activation_is_scoped_and_restores_r8r14_module(self) -> None:
        names = ("STAGE", "IDENTITY", "RUN_NAME", "CONTROLLER_REVISION", "_payload", "_phase_specs", "audit_raw_phase", "LocalWorker", "_ray_actor_class")
        before = {name: getattr(r14, name) for name in names}
        with sentinel._activated():
            self.assertEqual(r14.STAGE, sentinel.STAGE)
            self.assertIs(r14._payload, sentinel._payload)
            self.assertIs(r14.LocalWorker, sentinel._Worker)
        self.assertEqual({name: getattr(r14, name) for name in names}, before)

    def test_formal_primary_and_independent_recompute_same_80_rows(self) -> None:
        primary = inspect.getsource(sentinel.compute_formal_authority)
        audited = inspect.getsource(independent._formal_recompute)
        for source in (primary, audited):
            self.assertIn('"source": "R8R7"', source)
            self.assertIn('"source": "R8R28"', source)
            self.assertIn("len(candidates) != 4", source)
            self.assertIn("held_oracle", source)
            self.assertIn("expected_members", source)
        self.assertIn('"row_count": len(rows)', primary)
        self.assertIn('"row_count": len(rows)', audited)

    def test_independent_implementation_does_not_import_r8r28_primary(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel as",
            source,
        )
        self.assertIn("def _expected_specs", source)
        self.assertIn("def raw_audit", source)
        self.assertIn("def _formal_recompute", source)

    def test_launcher_uses_existing_server_venv_and_direct_copy_workflow(self) -> None:
        source = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r28_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("--r8r14-run", source)
        self.assertIn("--r8r27-run", source)
        self.assertIn("authorize-safety", source)
        self.assertIn("authorize-qualification", source)
        self.assertIn("final-independent", source)
        self.assertIn("maximum 64 fresh", source)
        self.assertNotIn("python3", source)
        self.assertNotIn("tar ", source)
        self.assertNotIn("unzip", source)
        self.assertNotIn("zip ", source)


if __name__ == "__main__":
    unittest.main()
