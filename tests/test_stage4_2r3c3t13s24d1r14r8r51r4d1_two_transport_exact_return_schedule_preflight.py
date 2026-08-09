from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r4d1_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight
    as d1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4D1_TWO_TRANSPORT_EXACT_RETURN_SCHEDULE_PREFLIGHT_DESIGN.md"
LAUNCHER = ROOT / "run_stage4_2r3c3t13s24d1r14r8r51r4d1_common.sh"


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _context() -> d1.Context:
    cfg = _config()
    return d1.Context(
        cfg=cfg,
        config_path=CONFIG,
        paths=d1._paths(ROOT / ".codex_tmp" / "unused_r51r4d1_test_run"),
        r4_ctx=None,
        r4_stage=ROOT / ".codex_tmp" / "unused_r51r4_source",
    )


def _source_specs() -> list[dict]:
    cfg = _config()
    rows = []
    for context_index, baseline_id in enumerate(cfg["matrix_contract"]["failed_source_baseline_ids"]):
        pair_index = context_index // 2
        for candidate_index, candidate_id in enumerate(d1.CANDIDATE_IDS):
            coordinate = [0.0] * 5
            coordinate[candidate_index] = 0.1
            rows.append(
                {
                    "experiment_id": f"source_c{context_index:02d}_{candidate_id}_r16",
                    "source_r8r7_baseline_experiment_id": baseline_id,
                    "r8r51r4_candidate_id": candidate_id,
                    "r8r51r4_candidate_index": candidate_index,
                    "r8r51r4_candidate_q": coordinate,
                    "r8r51r4_requested_coordinate": coordinate[:4],
                    "r8r51r4_return_task_step": 16,
                    "pair_id": f"pair_{pair_index:02d}",
                    "history_member": "a" if context_index % 2 == 0 else "b",
                    "horizon_steps": 36 if context_index < 8 else 38,
                }
            )
    return rows


def _coverage_rows() -> list[dict]:
    rows = []
    for context_index in range(10):
        for first in d1.CANDIDATE_IDS:
            for second in d1.CANDIDATE_IDS:
                rows.append(
                    {
                        "context_index": context_index,
                        "pair_id": f"pair_{context_index // 2:02d}",
                        "history_member": "a" if context_index % 2 == 0 else "b",
                        "first_candidate_id": first,
                        "second_candidate_id": second,
                        "eligible": True,
                    }
                )
    return rows


class TestR51R4D1TwoTransportSchedulePreflight(unittest.TestCase):
    def test_frozen_config_and_design_authenticate(self) -> None:
        cfg = _config()
        d1.validate_config(cfg, project_root=ROOT)
        self.assertEqual(d1._sha(DESIGN), cfg["design_document_sha256"])
        self.assertEqual(cfg["matrix_contract"]["specification_count"], 250)
        self.assertTrue(cfg["scientific_scope"]["zero_new_tsc"])
        self.assertFalse(cfg["scientific_scope"]["response_values_used"])
        self.assertFalse(cfg["scientific_scope"]["gate_a_qualified"])

    def test_complete_ordered_specification_matrix_is_frozen(self) -> None:
        with mock.patch.object(d1, "_source_specs", return_value=_source_specs()):
            specs = d1.build_specs(_context())
        self.assertEqual(len(specs), 250)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 250)
        self.assertEqual(
            {(row["first_candidate_id"], row["second_candidate_id"]) for row in specs if row["context_index"] == 0},
            set((first, second) for first in d1.CANDIDATE_IDS for second in d1.CANDIDATE_IDS),
        )
        self.assertTrue(all(row["source_result_available_to_construction"] is False for row in specs))
        self.assertTrue(all(row["allowed_in_expert_dataset"] is False for row in specs))
        self.assertTrue(all(row["decision_task_steps"] == [12, 16, 20] for row in specs))

    def test_coverage_passes_only_complete_symmetric_support(self) -> None:
        cfg = _config()
        coverage = d1.evaluate_coverage(_coverage_rows(), cfg)
        self.assertTrue(coverage["passed"])
        self.assertEqual(coverage["eligible_specification_count"], 250)
        self.assertEqual(coverage["context_pass_count"], 10)
        self.assertEqual(coverage["history_pair_pass_count"], 5)

        mutated = _coverage_rows()
        for row in mutated:
            if row["context_index"] == 1 and row["first_candidate_id"] == "d0m" and row["second_candidate_id"] == "d1p":
                row["eligible"] = False
        failed = d1.evaluate_coverage(mutated, cfg)
        self.assertFalse(failed["passed"])
        self.assertFalse(failed["gates"]["history_pair_eligible_sets_equal"])

    def test_scalar_geometry_is_independent_and_matches_primary(self) -> None:
        field_basis = np.zeros((14, 4), dtype=float)
        field_basis[:4, :] = np.eye(4)
        field_basis[4:, :] = np.arange(40, dtype=float).reshape(10, 4) / 100.0
        turns = np.arange(1, 15, dtype=float)
        before = np.linspace(-5.0, 5.0, 14)
        coordinate = np.asarray([0.02, -0.01, 0.03, -0.015])
        current_basis = field_basis * 1000.0 / turns[:, None]
        after = before + current_basis @ coordinate
        desired_target = after.copy()
        expected = d1._transition_geometry(
            before=before,
            after=after,
            desired_target=desired_target,
            field_basis=field_basis,
            turns=turns,
        )
        actual = independent._geometry(
            before.tolist(), after.tolist(), desired_target.tolist(), field_basis.tolist(), turns.tolist()
        )
        self.assertAlmostEqual(actual[0], expected[0], places=12)
        self.assertAlmostEqual(actual[1], expected[1], places=12)

    def test_equal_pair_zero_geometry_is_exact(self) -> None:
        zeros = [0.0] * 14
        basis = np.zeros((14, 4), dtype=float)
        basis[:4, :] = np.eye(4)
        self.assertEqual(independent._geometry(zeros, zeros, zeros, basis.tolist(), [1.0] * 14), (1.0, 0.0))

    def test_independent_does_not_delegate_core_reconstruction(self) -> None:
        source = (ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r4d1_independent_forensics.py").read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("np.linalg", source)
        self.assertNotIn("d1.construct_schedule", source)
        self.assertNotIn("d1.evaluate_coverage", source)
        self.assertIn("def _solve(", source)
        self.assertIn("def _coverage(", source)

    def test_primary_and_independent_enforce_full_clock_and_exact_return(self) -> None:
        primary = (ROOT / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight.py").read_text(encoding="utf-8")
        independent_source = (ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r4d1_independent_forensics.py").read_text(encoding="utf-8")
        for source in (primary, independent_source):
            self.assertIn('"fixed_task_clock"', source)
            self.assertIn('"q0_integration_action"', source)
            self.assertIn('"stored_center_current_exact"', source)
            self.assertIn('"post_return_refresh_zero_increment"', source)
            self.assertIn('"current_utilization_limits"', source)

    def test_launcher_is_zero_tsc_dual_offline_only(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('--r51r4-run "${R51R4_RUN}"', source)
        self.assertIn("two_transport_exact_return_schedule_preflight", source)
        self.assertIn("r51r4d1_independent_forensics.py", source)
        self.assertIn("offline|independent", source)
        self.assertNotIn("--backend", source)
        self.assertNotIn("--resume", source)
        self.assertNotIn("gotsc", source)

    def test_routes_do_not_claim_control_or_gate_a(self) -> None:
        cfg = _config()
        self.assertEqual(set(cfg["routes"]), {"source_blocked", "geometry_fail", "pass"})
        self.assertTrue(cfg["routes"]["geometry_fail"].endswith("NO_REAL_TSC"))
        self.assertTrue(cfg["routes"]["pass"].endswith("R51R4D2_DESIGN_REQUIRED"))
        self.assertFalse(cfg["scientific_scope"]["controller_executed"])
        self.assertFalse(cfg["scientific_scope"]["expert_data_allowed"])
        self.assertFalse(cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
