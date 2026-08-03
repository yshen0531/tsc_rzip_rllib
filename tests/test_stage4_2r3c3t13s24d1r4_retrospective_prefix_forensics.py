from __future__ import annotations

import sys
import types
import unittest

if sys.platform == "win32":
    try:
        import resource  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.RLIMIT_CORE = 4
        resource.getrlimit = lambda _which: (65536, 65536)
        resource.setrlimit = lambda _which, _limits: None
        sys.modules["resource"] = resource

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r4_retrospective_prefix_forensics as audit,
)


class Stage42R3C3T13S24D1R4RetrospectiveTests(unittest.TestCase):
    def test_structured_finish_requires_exact_failure_criteria(self):
        result = {
            "success": False,
            "completed": True,
            "failure_class": "structured_action_schedule_gate",
            "action_failure_event": {
                "event": "sequential_cancel_split_finish",
                "task_step": 19,
                "split_start_task_step": 18,
                "slot": 3,
                "passed": False,
                "incremental_normalized_action_linf": 0.271,
                "criteria": {
                    "actuator_gate": False,
                    "finish_increment": False,
                    "original_increment": False,
                    "exact_fields": True,
                },
            },
        }
        self.assertTrue(audit._structured_finish_failure(result))
        result["action_failure_event"]["criteria"]["exact_fields"] = False
        self.assertFalse(audit._structured_finish_failure(result))

    def test_aggregate_counts_all_executed_prefixes_and_finish_attempts(self):
        rows = []
        for index in range(9):
            rows.append(
                {
                    "pair_id": "p5" if index < 3 else "p9",
                    "history_member": "plus_first" if index % 2 else "minus_first",
                    "sequence_index": (6, 10, 18)[index % 3],
                    "structured_split_finish_safe_stop": True,
                    "common_prefix_forensic_pass": True,
                    "identity_pass": True,
                    "restart_exact": True,
                    "causality_pass": True,
                    "calibration_pass": True,
                    "source_prefix_action_exact": True,
                    "source_prefix_trace_exact": True,
                    "d1r3_split_start_exact": True,
                    "issue_event_count": 4,
                    "direct_cancel_event_count": 3,
                    "split_start_event_count": 1,
                    "failed_split_finish_attempt_count": 1,
                    "failure_action_not_applied": True,
                    "failed_finish_margin_pass": False,
                    "failed_finish_original_cap_pass": False,
                    "failed_finish_incremental_normalized_action_linf": 0.271 + index / 100,
                    "unapplied_finish_from_previous_command_linf_diagnostic": 0.06,
                    "maximum_executed_current_utilization": 0.384,
                    "failed_finish_predicted_current_utilization": 0.383,
                    "forbidden_trace_count": 0,
                    "formal_tracking_evaluable": False,
                }
            )
        result = audit._aggregate(rows)
        self.assertEqual(result["raw_count"], 9)
        self.assertEqual(result["common_prefix_forensic_pass_count"], 9)
        self.assertEqual(result["issue_event_count"], 36)
        self.assertEqual(result["direct_cancel_event_count"], 27)
        self.assertEqual(result["split_start_event_count"], 9)
        self.assertEqual(result["failed_split_finish_attempt_count"], 9)
        self.assertEqual(result["finish_margin_failure_count"], 9)
        self.assertEqual(result["formal_tracking_evaluable_count"], 0)


if __name__ == "__main__":
    unittest.main()
