from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import types
import unittest
from unittest import mock

import numpy as np

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

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel as stage,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/"
    "stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel_350ms.json"
)


class Stage42R3C3T13S24D1R6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_identity_timing_capacity_and_scope(self):
        stage._validate_config(copy.deepcopy(self.cfg), CONFIG)
        self.assertEqual(self.cfg["parallel"]["n_workers"], 9)
        self.assertEqual(
            self.cfg["formal_timing_contract"]["normal"],
            {"arrival_deadline_step": 25, "hold_through_step": 35},
        )
        self.assertEqual(
            self.cfg["recursive_contract"]["latest_finish_task_step"], 22
        )
        self.assertTrue(
            self.cfg["formal_timing_contract"]["formal_tracking_is_diagnostic_only"]
        )
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_gate_identity_timing_and_capacity_changes_fail_closed(self):
        changes = (
            ("recursive_contract", "direct_finish_threshold", 0.25),
            ("recursive_contract", "latest_finish_task_step", 23),
            ("parallel", "n_workers", 10),
            ("formal_timing_contract", "arrival_deadline_expansion_allowed", True),
            ("scientific_scope", "bc_dagger_or_rl_allowed", True),
        )
        for section, key, value in changes:
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                stage._validate_config(changed, CONFIG)

    def test_three_snapshot_subset_reaggregates_inherited_rows(self):
        contexts = [{"index": index} for index in range(3)]
        inherited = {
            "expected": 40,
            "actual": 3,
            "pass_count": 3,
            "passed": False,
            "rows": [{"passed": True, "index": index} for index in range(3)],
        }
        with mock.patch.object(
            stage.d1r2.s24.s21, "_snapshot_audit", return_value=inherited
        ):
            audit = stage._selected_snapshot_audit(contexts)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["expected"], 3)
        self.assertEqual(audit["pass_count"], 3)
        self.assertEqual(audit["source_helper_expected"], 40)
        self.assertFalse(audit["source_helper_passed"])

    def _controller(self, *, step: int = 19, continuation_count: int = 0):
        controller = object.__new__(
            stage.CausalRecursiveSplitReturnSafetySentinelController
        )
        controller.recursive_cfg = copy.deepcopy(self.cfg["recursive_contract"])
        controller.split_cfg = {
            "split_start_task_step": 18,
            "split_finish_task_step": 19,
            "split_slot": 3,
        }
        middle = ["1.500E-02 "] * 14
        history = [middle]
        if continuation_count:
            history.extend([["1.000E-02 "] * 14] * continuation_count)
        controller._split_pending = {
            "slot": 3,
            "start_task_step": 18,
            "stored_center_card15_fields": ["0.000E+00 "] * 14,
            "issue_target_card15_fields": ["3.000E-02 "] * 14,
            "intermediate_card15_fields": history[-1],
            "intermediate_history": history,
            "continuation_count": continuation_count,
            "split_start_event": {},
        }
        controller._active_issue = {"slot": 3}
        controller.step = step
        controller.turns_tsc = np.full(14, 1000.0)
        controller.base = SimpleNamespace(
            max_delta_a=1000.0,
            min_current=np.full(14, -1000.0),
            max_current=np.full(14, 1000.0),
        )
        controller.lattice_cfg = {}
        controller._last_failed_event = None
        controller._last_recursive_event = None
        controller._split_finish_count = 0
        controller._recursive_finish_count = 0
        controller._recursive_continuation_count = continuation_count
        return controller

    @staticmethod
    def _applied(fields: list[str]):
        return SimpleNamespace(
            card15_fields=fields,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )

    def test_expanded_decimal_telescope_is_exact_for_multiple_intermediates(self):
        controller = self._controller(step=22, continuation_count=2)
        self.assertTrue(
            controller._telescope(
                ["0.000E+00 "] * 14,
                ["3.000E-02 "] * 14,
                [
                    ["1.500E-02 "] * 14,
                    ["1.000E-02 "] * 14,
                    ["5.000E-03 "] * 14,
                ],
            )
        )

    def test_first_continuation_is_exactly_point_one_seven_five(self):
        controller = self._controller(step=19)
        fields = ["1.000E-02 "] * 14
        controller.actuator = SimpleNamespace(
            apply=mock.Mock(return_value=self._applied(fields))
        )
        direct = np.zeros(14)
        direct[0] = 0.35
        direct_event = {
            "passed": False,
            "incremental_normalized_action_linf": 0.35,
        }
        action, event = controller._continuation(
            np.zeros(14), np.zeros(14), direct, direct_event
        )
        self.assertTrue(event["passed"])
        self.assertEqual(event["task_step"], 19)
        self.assertEqual(event["continuation_count"], 1)
        self.assertAlmostEqual(
            event["continuation_incremental_normalized_action_linf"], 0.175
        )
        self.assertAlmostEqual(action[0], 0.175)
        self.assertEqual(controller._split_pending["continuation_count"], 1)
        self.assertEqual(controller._recursive_continuation_count, 1)

    def test_direct_finish_after_continuation_clears_pending(self):
        controller = self._controller(step=20, continuation_count=1)
        controller.actuator = SimpleNamespace(
            apply=mock.Mock(return_value=self._applied(["0.000E+00 "] * 14))
        )
        chosen = {
            "target_fields": ["0.000E+00 "] * 14,
            "action_norm_tsc": [0.0] * 14,
            "incremental_normalized_action_linf": 0.20,
            "total_normalized_action_abs": 0.0,
            "current_bounds_pass": True,
            "predicted_maximum_current_utilization": 0.4,
            "exact_stored_issue_center": True,
            "passed": True,
        }
        with mock.patch.object(
            stage.d1r2.s24.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ):
            action, event = controller._finish(np.zeros(14), np.zeros(14))
        self.assertTrue(event["passed"])
        self.assertEqual(event["task_step"], 20)
        self.assertTrue(event["criteria"]["expanded_exact_decimal_telescope"])
        self.assertIsNone(controller._active_issue)
        self.assertIsNone(controller._split_pending)
        self.assertEqual(controller._split_finish_count, 1)
        self.assertEqual(controller._recursive_finish_count, 1)
        np.testing.assert_array_equal(action, np.zeros(14))

    def test_step_twenty_two_failed_finish_stops_before_plant_action(self):
        controller = self._controller(step=22, continuation_count=3)
        failed = {
            "event": "sequential_cancel_split_finish",
            "task_step": 22,
            "passed": False,
            "criteria": {"finish_increment": False},
            "incremental_normalized_action_linf": 0.26,
        }
        with mock.patch.object(
            controller, "_direct_event", return_value=(np.ones(14), failed)
        ), mock.patch.object(controller, "_continuation") as continuation:
            with self.assertRaises(ValueError):
                controller._finish(np.zeros(14), np.zeros(14))
        continuation.assert_not_called()
        self.assertEqual(
            controller._last_failed_event["event"],
            "sequential_cancel_recursive_deadline_stop",
        )
        self.assertFalse(controller._last_failed_event["failed_candidate_applied"])
        self.assertFalse(
            controller._last_failed_event["plant_advance_after_failure"]
        )
        self.assertIsNotNone(controller._split_pending)

    def test_controller_spec_removes_all_source_selection_fields(self):
        source = {
            "d1r4_source_d1r2_experiment_id": "forbidden-d1r2",
            "d1r4_split_contract": {"future": "forbidden"},
            "d1r6_source_d1r4_experiment_id": "forbidden-d1r4",
            "d1r6_recursive_contract": {"future": "forbidden"},
            "candidate_preflight_sha256": "forbidden-hash",
            "pair_id": "forbidden-pair",
            "history_member": "forbidden-history",
            "partition": "forbidden-partition",
            "kept": 1,
        }
        with mock.patch.object(
            stage.d1r2.s24.s21.s16.s9,
            "_controller_spec",
            side_effect=lambda value: value,
        ):
            output = stage._controller_spec(source)
        self.assertEqual(output, {"kept": 1})

    def test_forbidden_trace_flags_include_d1r6_namespace(self):
        trace = [
            {
                "r3c3t13s24d1r6_future_measurement_used": True,
                "r3c3t13s24d1r6_source_outcome_used": False,
            }
        ]
        with mock.patch.object(stage.d1r2, "_forbidden_trace_count", return_value=0):
            self.assertEqual(stage._forbidden_trace_count(trace), 1)

    def test_self_test_reports_recursive_boundary_without_tsc(self):
        result = stage.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertEqual(result["first_continuation_task_step"], 19)
        self.assertEqual(result["latest_finish_task_step"], 22)

    def test_launchers_use_virtualenv_fixed_capacity_and_exact_pid_stop(self):
        names = (
            "run_stage4_2r3c3t13s24d1r6_common.sh",
            "run_stage4_2r3c3t13s24d1r6_nohup.sh",
            "run_stage4_2r3c3t13s24d1r6_offline.sh",
            "run_stage4_2r3c3t13s24d1r6_postprocess.sh",
            "run_stage4_2r3c3t13s24d1r6_independent_forensics.sh",
            "run_stage4_2r3c3t13s24d1r6_verify_package.sh",
            "run_stop_stage4_2r3c3t13s24d1r6_now.sh",
            "scripts/stage4_2r3c3t13s24d1r6_shell_common.sh",
        )
        text = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in names)
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python",
            text,
        )
        self.assertIn("WORKERS:-9", text)
        self.assertIn("kill -TERM", text)
        self.assertNotIn("pkill", text)
        self.assertNotIn("killall", text)

    def test_independent_forensics_does_not_call_internal_execution_audit(self):
        forensic = (
            ROOT
            / "docs/codex/audit_tools/"
            "stage4_2r3c3t13s24d1r6_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("stage._execution_audit", forensic)
        self.assertIn("source_prefix_trace_exact", forensic)
        self.assertIn("raw_inventory_exact", forensic)
        self.assertIn("snapshot_audit_sha256", forensic)


if __name__ == "__main__":
    unittest.main()
