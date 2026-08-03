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
    stage4_2r3c3t13s24d1r2_retrospective_prefix_forensics as audit,
)


class Stage42R3C3T13S24D1R2RetrospectiveTests(unittest.TestCase):
    def test_aggregate_counts_all_successful_and_failed_cancel_attempts(self):
        rows = []
        for index in range(45):
            rows.append(
                {
                    "pair_id": "success",
                    "history_member": "plus_first",
                    "sequence_index": index,
                    "result_success": True,
                    "structured_safe_stop": False,
                    "common_prefix_forensic_pass": True,
                    "restart_exact": True,
                    "causality_pass": True,
                    "calibration_pass": True,
                    "issue_event_count": 4,
                    "issue_gate_pass_count": 4,
                    "successful_cancel_event_count": 4,
                    "successful_cancel_gate_pass_count": 4,
                    "failed_cancel_attempt_count": 0,
                    "failed_cancel_original_cap_pass": None,
                    "successful_cancel_maximum_incremental_normalized_action_linf": 0.216,
                    "attempted_cancel_maximum_incremental_normalized_action_linf": 0.216,
                    "maximum_current_utilization": 0.392,
                    "forbidden_trace_count": 0,
                }
            )
        for index in range(9):
            original_pass = index < 4
            rows.append(
                {
                    "pair_id": "failure",
                    "history_member": "minus_first",
                    "sequence_index": (6, 10, 18)[index % 3],
                    "result_success": False,
                    "structured_safe_stop": True,
                    "common_prefix_forensic_pass": True,
                    "restart_exact": True,
                    "causality_pass": True,
                    "calibration_pass": True,
                    "issue_event_count": 4,
                    "issue_gate_pass_count": 4,
                    "successful_cancel_event_count": 3,
                    "successful_cancel_gate_pass_count": 3,
                    "failed_cancel_attempt_count": 1,
                    "failed_cancel_original_cap_pass": original_pass,
                    "successful_cancel_maximum_incremental_normalized_action_linf": 0.210,
                    "attempted_cancel_maximum_incremental_normalized_action_linf": 0.2787208,
                    "maximum_current_utilization": 0.383,
                    "forbidden_trace_count": 0,
                }
            )
        result = audit._aggregate(rows)
        self.assertEqual(result["raw_count"], 54)
        self.assertEqual(result["issue_event_count"], 216)
        self.assertEqual(result["successful_cancel_event_count"], 207)
        self.assertEqual(result["failed_cancel_attempt_count"], 9)
        self.assertEqual(result["total_cancel_attempt_count"], 216)
        self.assertEqual(result["original_cancel_cap_pass_count"], 211)
        self.assertEqual(result["original_cancel_cap_failure_count"], 5)
        self.assertEqual(result["common_prefix_forensic_pass_count"], 54)


if __name__ == "__main__":
    unittest.main()
