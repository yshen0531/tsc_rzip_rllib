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
    stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel as stage,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_350ms.json"
)


class Stage42R3C3T13S24D1R4Tests(unittest.TestCase):
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
        self.assertTrue(
            self.cfg["formal_timing_contract"]["formal_tracking_is_diagnostic_only"]
        )
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_gate_identity_timing_and_capacity_changes_fail_closed(self):
        changes = (
            ("split_contract", "maximum_finish_increment", 0.25),
            ("split_contract", "split_finish_task_step", 20),
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

    def test_three_snapshot_subset_fails_if_one_inventory_fails(self):
        contexts = [{"index": index} for index in range(3)]
        inherited = {
            "expected": 40,
            "actual": 3,
            "pass_count": 2,
            "passed": False,
            "rows": [{"passed": True}, {"passed": False}, {"passed": True}],
        }
        with mock.patch.object(
            stage.d1r2.s24.s21, "_snapshot_audit", return_value=inherited
        ):
            audit = stage._selected_snapshot_audit(contexts)
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["pass_count"], 2)

    def _finish_controller(self, increment: float = 0.20):
        controller = object.__new__(stage.CausalSplitReturnSafetySentinelController)
        controller.split_cfg = copy.deepcopy(self.cfg["split_contract"])
        controller._split_pending = {
            "slot": 3,
            "start_task_step": 18,
            "stored_center_card15_fields": ["0.000E+00 "] * 14,
            "issue_target_card15_fields": ["3.000E-02 "] * 14,
            "intermediate_card15_fields": ["1.500E-02 "] * 14,
            "split_start_event": {},
        }
        controller._active_issue = {"slot": 3}
        controller.step = 19
        controller.turns_tsc = np.full(14, 1000.0)
        controller.base = SimpleNamespace(
            max_delta_a=1000.0,
            min_current=np.full(14, -1000.0),
            max_current=np.full(14, 1000.0),
        )
        controller.lattice_cfg = {}
        controller._last_failed_event = None
        controller._split_finish_count = 0
        finished = SimpleNamespace(
            card15_fields=["0.000E+00 "] * 14,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )
        controller.actuator = SimpleNamespace(apply=mock.Mock(return_value=finished))
        chosen = {
            "target_fields": ["0.000E+00 "] * 14,
            "action_norm_tsc": [0.0] * 14,
            "incremental_normalized_action_linf": increment,
            "total_normalized_action_abs": 0.0,
            "current_bounds_pass": True,
            "predicted_maximum_current_utilization": 0.4,
            "exact_stored_issue_center": True,
            "passed": increment <= 0.25,
        }
        return controller, chosen

    def test_finish_is_exact_bounded_and_clears_pending_only_after_pass(self):
        controller, chosen = self._finish_controller()
        with mock.patch.object(
            stage.d1r2.s24.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ):
            action, event = controller._finish(np.zeros(14), np.zeros(14))
        self.assertTrue(event["passed"])
        self.assertEqual(event["event"], "sequential_cancel_split_finish")
        self.assertTrue(event["criteria"]["exact_decimal_telescoping_net"])
        self.assertTrue(event["criteria"]["one_plant_advance"])
        self.assertIsNone(controller._active_issue)
        self.assertIsNone(controller._split_pending)
        self.assertEqual(controller._split_finish_count, 1)
        np.testing.assert_array_equal(action, np.zeros(14))

    def test_finish_over_prospective_margin_fails_before_state_clear(self):
        controller, chosen = self._finish_controller(increment=0.245)
        with mock.patch.object(
            stage.d1r2.s24.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ), self.assertRaises(ValueError):
            controller._finish(np.zeros(14), np.zeros(14))
        self.assertIsNotNone(controller._active_issue)
        self.assertIsNotNone(controller._split_pending)
        self.assertFalse(controller._last_failed_event["criteria"]["finish_increment"])

    def test_split_start_sets_one_shot_pending_state(self):
        controller = object.__new__(stage.CausalSplitReturnSafetySentinelController)
        controller._split_pending = None
        controller._split_start_count = 0
        controller._last_split_start_event = None
        controller.step = 18
        source_event = {
            "event": "sequential_cancel_split_start",
            "stored_center_card15_fields": ["0.000E+00 "] * 14,
            "issue_target_card15_fields": ["3.000E-02 "] * 14,
            "intermediate_card15_fields": ["1.500E-02 "] * 14,
            "passed": True,
        }
        with mock.patch.object(
            stage.d1r3.CausalSplitReturnPreflightController,
            "_cancel",
            return_value=(np.zeros(14), source_event),
        ):
            _, event = controller._cancel(3, np.zeros(14), np.zeros(14))
        self.assertEqual(event["stage"], stage.STAGE)
        self.assertEqual(controller._split_start_count, 1)
        self.assertEqual(controller._split_pending["start_task_step"], 18)

    def test_split_start_gate_failure_is_preserved_as_structured_failure(self):
        controller = object.__new__(stage.CausalSplitReturnSafetySentinelController)
        controller._last_split_start_event = None
        controller._last_failed_event = None
        failed_event = {
            "event": "sequential_cancel_split_start",
            "passed": False,
            "criteria": {"split_start_increment": False},
        }

        def fail(*_args, **_kwargs):
            controller._last_split_start_event = copy.deepcopy(failed_event)
            raise ValueError("frozen split-start gate")

        with mock.patch.object(
            stage.d1r3.CausalSplitReturnPreflightController,
            "_cancel",
            side_effect=fail,
        ), self.assertRaises(ValueError):
            controller._cancel(3, np.zeros(14), np.zeros(14))
        self.assertEqual(controller._last_failed_event, failed_event)

    def test_controller_spec_removes_d1r4_source_selection_fields(self):
        source = {
            "d1r4_source_d1r2_experiment_id": "forbidden-source",
            "d1r4_split_contract": {"future": "forbidden"},
            "candidate_preflight_sha256": "forbidden-hash",
            "kept": 1,
        }
        with mock.patch.object(
            stage.d1r2.s24.s21.s16.s9,
            "_controller_spec",
            side_effect=lambda value: value,
        ):
            output = stage._controller_spec(source)
        self.assertEqual(output, {"kept": 1})

    def test_launchers_use_virtualenv_fixed_capacity_and_exact_pid_stop(self):
        names = (
            "run_stage4_2r3c3t13s24d1r4_common.sh",
            "run_stage4_2r3c3t13s24d1r4_nohup.sh",
            "run_stage4_2r3c3t13s24d1r4_offline.sh",
            "run_stage4_2r3c3t13s24d1r4_postprocess.sh",
            "run_stage4_2r3c3t13s24d1r4_independent_forensics.sh",
            "run_stage4_2r3c3t13s24d1r4_verify_package.sh",
            "run_stop_stage4_2r3c3t13s24d1r4_now.sh",
            "scripts/stage4_2r3c3t13s24d1r4_shell_common.sh",
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
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r4_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("stage._execution_audit", forensic)
        self.assertIn("source_prefix_trace_exact", forensic)
        self.assertIn("raw_inventory_exact", forensic)
        self.assertIn("snapshot_audit_sha256", forensic)


if __name__ == "__main__":
    unittest.main()
