from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r4d3_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight
    as d3,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4D3_CENTER_BRIDGED_TWO_PULSE_SCHEDULE_PREFLIGHT_DESIGN.md"
LAUNCHER = ROOT / "run_stage4_2r3c3t13s24d1r14r8r51r4d3_common.sh"


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _context() -> d3.Context:
    cfg = _config()
    return d3.Context(
        cfg=cfg,
        config_path=CONFIG,
        paths=d3._paths(ROOT / ".codex_tmp" / "unused_r51r4d3_test_run"),
        d1_ctx=None,
        d1_stage=ROOT / ".codex_tmp" / "unused_r51r4d1_source",
    )


def _source_specs() -> list[dict]:
    rows = []
    for context_index in range(10):
        for first_candidate_id in d3.CANDIDATE_IDS:
            for second_candidate_id in d3.CANDIDATE_IDS:
                rows.append(
                    {
                        "experiment_id": (
                            f"r8r51r4d1_c{context_index:02d}_"
                            f"{first_candidate_id}_then_{second_candidate_id}"
                        ),
                        "context_index": context_index,
                        "pair_id": f"pair_{context_index // 2:02d}",
                        "history_member": "a" if context_index % 2 == 0 else "b",
                        "first_candidate_id": first_candidate_id,
                        "second_candidate_id": second_candidate_id,
                        "source_result_available_to_construction": False,
                        "allowed_in_expert_dataset": False,
                    }
                )
    return rows


def _coverage_rows() -> list[dict]:
    return [
        {
            "context_index": context_index,
            "pair_id": f"pair_{context_index // 2:02d}",
            "history_member": "a" if context_index % 2 == 0 else "b",
            "first_candidate_id": first_candidate_id,
            "second_candidate_id": second_candidate_id,
            "eligible": True,
        }
        for context_index in range(10)
        for first_candidate_id in d3.CANDIDATE_IDS
        for second_candidate_id in d3.CANDIDATE_IDS
    ]


class TestR51R4D3CenterBridgedTwoPulseSchedulePreflight(unittest.TestCase):
    def test_frozen_config_and_design_authenticate(self) -> None:
        cfg = _config()
        d3.validate_config(cfg, project_root=ROOT)
        self.assertEqual(d3._sha(DESIGN), cfg["design_document_sha256"])
        self.assertEqual(cfg["matrix_contract"]["specification_count"], 250)
        self.assertEqual(cfg["coverage_gate"]["required_eligible_specification_count"], 250)
        self.assertTrue(cfg["scientific_scope"]["zero_new_tsc"])
        self.assertFalse(cfg["scientific_scope"]["response_values_used"])
        self.assertFalse(cfg["scientific_scope"]["gate_a_qualified"])

    def test_complete_ordered_matrix_is_preserved_without_results(self) -> None:
        with mock.patch.object(d3.d1, "build_specs", return_value=_source_specs()):
            specs = d3.build_specs(_context())
        self.assertEqual(len(specs), 250)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 250)
        self.assertTrue(all(row["stage"] == d3.STAGE for row in specs))
        self.assertTrue(all(row["decision_task_steps"] == [12, 16, 18, 22] for row in specs))
        self.assertTrue(all(row["source_d1_result_available_to_construction"] is False for row in specs))
        self.assertTrue(all(row["allowed_in_expert_dataset"] is False for row in specs))

    def test_coverage_requires_every_ordered_pair_in_every_context(self) -> None:
        rows = _coverage_rows()
        primary = d3.evaluate_coverage(rows, _config())
        scalar = independent._coverage(rows)
        self.assertTrue(primary["passed"])
        self.assertEqual(primary, scalar)
        self.assertEqual(primary["eligible_specification_count"], 250)
        self.assertEqual(primary["context_pass_count"], 10)
        self.assertEqual(primary["history_pair_pass_count"], 5)

        rows[25]["eligible"] = False
        primary = d3.evaluate_coverage(rows, _config())
        scalar = independent._coverage(rows)
        self.assertFalse(primary["passed"])
        self.assertEqual(primary, scalar)
        self.assertFalse(primary["gates"]["all_specs_eligible"])
        self.assertFalse(primary["gates"]["history_pair_sets_equal"])

    def test_center_bridge_and_second_pulse_clock_are_frozen(self) -> None:
        cfg = _config()
        schedule = cfg["schedule_contract"]
        self.assertEqual(schedule["first_issue_task_step"], 12)
        self.assertEqual(schedule["first_return_task_step"], 16)
        self.assertEqual(schedule["center_bridge_hold_task_step"], 17)
        self.assertEqual(schedule["second_issue_task_step"], 18)
        self.assertEqual(schedule["second_return_task_step"], 22)
        for function in (d3.construct_schedule, independent._construct_row):
            source = Path(function.__code__.co_filename).read_text(encoding="utf-8")
            self.assertIn('event="exact_q0_center_bridge_hold"', source)
            self.assertIn('"center_bridge_zero_increment"', source)
            self.assertIn('"second_return_exact"', source)
            self.assertIn('"fixed_task_clock"', source)

    def test_independent_does_not_delegate_core_reconstruction(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("d3.construct_schedule", source)
        self.assertNotIn("d3.evaluate_coverage", source)
        self.assertIn("def _construct_row(", source)
        self.assertIn("def _coverage(", source)

    def test_source_authentication_is_exactly_frozen(self) -> None:
        cfg = _config()
        source = cfg["source_r51r4d1"]
        self.assertEqual(source["eligible_specification_count"], 68)
        self.assertEqual(source["context_pass_count"], 0)
        self.assertEqual(
            source["required_route"],
            "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D1_TWO_TRANSPORT_SCHEDULE_GEOMETRY_INSUFFICIENT_NO_REAL_TSC",
        )
        self.assertEqual(
            source["action_stream_digest"],
            "d1607012ca5e39cca3b3113c269c569c754603c49704cef419b239d810ea7ccb",
        )

    def test_launcher_is_zero_tsc_dual_offline_only(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('r51r4d3_runs}', source)
        self.assertIn('--r51r4d1-run "${R51R4D1_RUN}"', source)
        self.assertIn("center_bridged_two_pulse_schedule_preflight", source)
        self.assertIn("r51r4d3_independent_forensics.py", source)
        self.assertIn("offline|independent", source)
        self.assertNotIn("--backend", source)
        self.assertNotIn("--resume", source)
        self.assertNotIn("gotsc", source)

    def test_routes_do_not_claim_control_or_gate_a(self) -> None:
        cfg = _config()
        self.assertEqual(set(cfg["routes"]), {"source_blocked", "geometry_fail", "pass"})
        self.assertTrue(cfg["routes"]["geometry_fail"].endswith("NO_REAL_TSC"))
        self.assertTrue(cfg["routes"]["pass"].endswith("R51R4D4_DESIGN_REQUIRED"))
        self.assertFalse(cfg["scientific_scope"]["controller_executed"])
        self.assertFalse(cfg["scientific_scope"]["expert_data_allowed"])
        self.assertFalse(cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
