from __future__ import annotations

import copy
import unittest

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r4_current_equivalence_reporting_hotfix as primary,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r4_current_equivalence_reporting_hotfix_independent
    as independent,
)


N = 14
ULP = 2.842170943040401e-14


def _detail(event: str, action: list[float], nominal: float) -> dict:
    return {
        "event": event,
        "action_norm_tsc": list(action),
        "nominal_readback_current_a_tsc": [nominal] * N,
        "passed": True,
        "criteria": {"fixture_gate": True},
    }


def _fixture():
    horizon = 17
    return_step = 16
    spec = {
        "experiment_id": "fixture",
        "horizon_steps": horizon,
        "pair_id": "pair",
        "history_member": "plus_first",
        "r8r51r4_candidate_index": 1,
        "r8r51r4_candidate_id": "d0m",
        "r8r51r4_return_task_step": return_step,
    }
    trajectory = [
        {
            "action_norm_tsc": [0.0] * N,
            "currents_a_tsc": [100.0] * N,
        }
        for _ in range(horizon + 1)
    ]
    trace = [{"action_norm_tsc": [0.0] * N} for _ in range(horizon)]
    key = "r3c3t13s24d1r14r8r51r4_event"
    detail_key = key + "_detail"
    q0_action = [0.0] * N
    q0_action[0] = 3.3333333296544274e-06
    candidate_action = [0.0] * N
    candidate_action[1] = 0.1
    return_action = [0.0] * N
    return_action[1] = -0.1

    q0 = _detail("q0_exact_current_target_issue", q0_action, 100.0 + ULP)
    observe = _detail("q0_observe_hold", [0.0] * N, 100.0 + ULP)
    issue = _detail("coordinate_issue", candidate_action, 110.0 + ULP)
    issue.pop("nominal_readback_current_a_tsc")
    issue["nominal_issue_readback_current_a_tsc"] = [110.0 + ULP] * N
    issue.update(
        {
            "target_card15_fields": ["candidate"] * N,
            "center_card15_fields": ["center"] * N,
        }
    )
    dwell = _detail("candidate_current_dwell_hold", [0.0] * N, 110.0 + ULP)
    dwell["stored_target_card15_fields"] = ["candidate"] * N
    returned = _detail("stored_pretransport_center_return", return_action, 100.0 + ULP)
    returned.update(
        {
            "stored_center_card15_fields": ["center"] * N,
            "issue_target_card15_fields": ["candidate"] * N,
        }
    )
    events = {
        10: ("q0_exact_issue", q0, q0_action, 100.0),
        11: ("q0_observe_hold", observe, [0.0] * N, 100.0),
        12: ("candidate_issue", issue, candidate_action, 110.0),
        13: ("candidate_dwell_hold", copy.deepcopy(dwell), [0.0] * N, 110.0),
        14: ("candidate_dwell_hold", copy.deepcopy(dwell), [0.0] * N, 110.0),
        15: ("candidate_dwell_hold", copy.deepcopy(dwell), [0.0] * N, 110.0),
        16: ("stored_center_return", returned, return_action, 100.0),
    }
    for step, (name, detail, action, next_current) in events.items():
        trace[step] = {
            "action_norm_tsc": list(action),
            key: name,
            detail_key: detail,
        }
        trajectory[step + 1] = {
            "action_norm_tsc": list(action),
            "currents_a_tsc": [next_current] * N,
        }
    details = [events[step][1] for step in range(10, horizon)]
    old = {
        "q0_first_effect_at_issue_plus_one": False,
        "dwell_exact": False,
        "event_stream_digest": primary._digest(details),
        "event_sequence_exact": True,
        "event_gates_passed": True,
        "forbidden_trace_count": 0,
    }
    result = {
        "completed": True,
        "success": True,
        "spec": spec,
        "trajectory": trajectory,
        "controller_trace": trace,
    }
    return result, spec, old


class Stage42R3C3T13S24D1R14R8R51R4ReportingHotfixTests(unittest.TestCase):
    def test_binary64_nominal_differences_pass_both_implementations(self):
        result, spec, old = _fixture()
        first = primary._measure(result, spec, old)
        second = independent._measure(result, spec, old)
        self.assertTrue(first["passed"])
        self.assertTrue(second["passed"])
        self.assertEqual(first, second)
        self.assertFalse(first["q0_nominal_current_binary_exact"])
        self.assertFalse(first["dwell_nominal_current_binary_exact"])
        self.assertTrue(first["dwell_physical_current_unchanged_exact"])

    def test_nominal_difference_above_frozen_tolerance_fails_closed(self):
        result, spec, old = _fixture()
        detail = result["controller_trace"][10][
            "r3c3t13s24d1r14r8r51r4_event_detail"
        ]
        detail["nominal_readback_current_a_tsc"][0] += 1.1e-12
        old["event_stream_digest"] = primary._digest(
            [
                result["controller_trace"][step][
                    "r3c3t13s24d1r14r8r51r4_event_detail"
                ]
                for step in range(10, 17)
            ]
        )
        self.assertFalse(primary._measure(result, spec, old)["passed"])
        self.assertFalse(independent._measure(result, spec, old)["passed"])

    def test_nonzero_dwell_increment_fails_closed(self):
        result, spec, old = _fixture()
        result["controller_trace"][13]["action_norm_tsc"][0] = 1e-6
        result["controller_trace"][13][
            "r3c3t13s24d1r14r8r51r4_event_detail"
        ]["action_norm_tsc"][0] = 1e-6
        result["trajectory"][14]["action_norm_tsc"][0] = 1e-6
        old["event_stream_digest"] = primary._digest(
            [
                result["controller_trace"][step][
                    "r3c3t13s24d1r14r8r51r4_event_detail"
                ]
                for step in range(10, 17)
            ]
        )
        self.assertFalse(primary._measure(result, spec, old)["passed"])
        self.assertFalse(independent._measure(result, spec, old)["passed"])

    def test_physical_dwell_drift_fails_closed(self):
        result, spec, old = _fixture()
        result["trajectory"][14]["currents_a_tsc"][0] += 5e-13
        self.assertFalse(primary._measure(result, spec, old)["passed"])
        self.assertFalse(independent._measure(result, spec, old)["passed"])

    def test_return_to_wrong_physical_center_fails_closed(self):
        result, spec, old = _fixture()
        result["trajectory"][17]["currents_a_tsc"][0] += 5e-13
        self.assertFalse(primary._measure(result, spec, old)["passed"])
        self.assertFalse(independent._measure(result, spec, old)["passed"])

    def test_action_effect_mismatch_fails_closed(self):
        result, spec, old = _fixture()
        result["trajectory"][13]["action_norm_tsc"][0] += 1e-6
        self.assertFalse(primary._measure(result, spec, old)["passed"])
        self.assertFalse(independent._measure(result, spec, old)["passed"])

    def test_contract_is_reporting_only_and_learning_forbidden(self):
        self.assertEqual(primary.ATOL_A, 1e-12)
        self.assertEqual(independent.ATOL_A, 1e-12)
        self.assertEqual(primary.RAW_COUNT, 100)
        self.assertEqual(primary.ORIGINAL_Q0_BINARY_COUNT, 20)
        self.assertEqual(primary.ORIGINAL_DWELL_BINARY_COUNT, 4)
        self.assertIn("FORMAL_REQUIRED", primary.RAW_HOTFIX_ROUTE)


if __name__ == "__main__":
    unittest.main()
