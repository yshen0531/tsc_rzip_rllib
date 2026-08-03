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

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r3_causal_split_return_preflight as stage,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r3_causal_split_return_preflight_v1.json"


class Stage42R3C3T13S24D1R3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_zero_tsc_scope(self):
        stage._validate_config(copy.deepcopy(self.cfg), CONFIG)
        self.assertFalse(self.cfg["execution_contract"]["tsc_allowed"])
        self.assertFalse(self.cfg["execution_contract"]["plant_advance_allowed"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_split_constants_and_timing_mutations_fail_closed(self):
        for key, value in (
            ("split_construction_target_increment", 0.174),
            ("maximum_split_start_increment", 0.181),
            ("direct_cancel_threshold", 0.25),
            ("split_finish_task_step", 20),
        ):
            changed = copy.deepcopy(self.cfg)
            changed["split_contract"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                stage._validate_config(changed, CONFIG)

    def test_failed_direct_cancel_constructs_bounded_exact_split_start(self):
        controller = object.__new__(stage.CausalSplitReturnPreflightController)
        controller._active_issue = {
            "slot": 3,
            "center_card15_fields": ["0.000E+00 "] * 14,
            "target_card15_fields": ["3.000E-02 "] * 14,
        }
        controller.turns_tsc = np.full(14, 1000.0)
        controller.base = SimpleNamespace(
            max_delta_a=1000.0,
            min_current=np.full(14, -1000.0),
            max_current=np.full(14, 1000.0),
        )
        controller.lattice_cfg = {}
        controller.split_cfg = copy.deepcopy(self.cfg["split_contract"])
        controller.step = 18
        controller._last_split_start_event = None
        controller._last_failed_event = None
        applied = SimpleNamespace(
            card15_fields=["1.500E-02 "] * 14,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )
        controller.actuator = SimpleNamespace(apply=mock.Mock(return_value=applied))
        baseline = np.full(14, 0.20)
        direct_action = np.full(14, -0.07)
        chosen = {
            "target_fields": ["0.000E+00 "] * 14,
            "action_norm_tsc": direct_action.tolist(),
            "incremental_normalized_action_linf": 0.27,
            "total_normalized_action_abs": 0.07,
            "current_bounds_pass": True,
            "predicted_maximum_current_utilization": 0.4,
            "exact_stored_issue_center": True,
            "passed": False,
        }
        with mock.patch.object(
            stage.d1r2.s24.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ):
            action, event = controller._cancel(3, np.zeros(14), baseline)
        self.assertTrue(event["passed"])
        self.assertEqual(event["event"], "sequential_cancel_split_start")
        self.assertAlmostEqual(
            event["split_start_incremental_normalized_action_linf"], 0.175
        )
        self.assertLessEqual(
            event["split_start_incremental_normalized_action_linf"], 0.18
        )
        self.assertTrue(event["criteria"]["exact_decimal_telescoping_net"])
        self.assertIsNotNone(controller._active_issue)
        np.testing.assert_allclose(action, baseline + (0.175 / 0.27) * (direct_action - baseline))

    def test_launcher_uses_virtualenv_and_contains_no_tsc_command(self):
        text = (ROOT / "run_stage4_2r3c3t13s24d1r3_offline.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", text
        )
        self.assertIn("zero-new-TSC causal replay", text)
        self.assertNotRegex(text, r"(?m)^\s*(?:exec\s+)?nohup\b")
        self.assertNotIn("--backend ray", text)


if __name__ == "__main__":
    unittest.main()
