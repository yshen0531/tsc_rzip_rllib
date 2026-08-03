from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys
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
    stage4_2r3c3t13s24d1r5_independent_forensics as independent,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r5_recursive_split_return_preflight as audit,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r5_recursive_split_return_preflight_v1.json"
)


class _Actuator:
    def __init__(self, fields):
        self.fields = fields

    def apply(self, _currents, _action):
        return SimpleNamespace(
            card15_fields=self.fields,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )


class Stage42R3C3T13S24D1R5Tests(unittest.TestCase):
    def test_frozen_config_and_zero_tsc_contract(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        audit._validate_config(cfg, CONFIG)
        self.assertFalse(cfg["execution_contract"]["tsc_allowed"])
        self.assertFalse(cfg["execution_contract"]["plant_advance_allowed"])
        self.assertFalse(cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_recursive_continuation_is_exact_0175_and_keeps_pending(self):
        controller = object.__new__(audit.CausalRecursiveSplitReturnPreflightController)
        stored = ["-1.000E+00"] * 14
        target = ["-2.000E+00"] * 14
        previous = ["-1.500E+00"] * 14
        continuation = ["-1.250E+00"] * 14
        controller._split_pending = {
            "slot": 3,
            "start_task_step": 18,
            "stored_center_card15_fields": stored,
            "issue_target_card15_fields": target,
            "intermediate_card15_fields": previous,
        }
        controller.step = 19
        controller.recursive_cfg = {
            "direct_finish_threshold": 0.24,
            "continuation_target_increment": 0.175,
            "maximum_continuation_increment": 0.18,
            "maximum_original_increment": 0.25,
            "maximum_total_normalized_action_abs": 1.0,
            "maximum_current_utilization": 0.55,
            "continuation_task_step": 19,
            "split_slot": 3,
        }
        controller.turns_tsc = np.full(14, 1000.0)
        controller.base = SimpleNamespace(
            max_delta_a=1.0,
            min_current=np.full(14, -100.0),
            max_current=np.full(14, 100.0),
        )
        controller.lattice_cfg = {}
        controller.actuator = _Actuator(continuation)
        controller._last_recursive_event = None
        direct = {
            "action_norm_tsc": [0.3] * 14,
            "incremental_normalized_action_linf": 0.3,
            "total_normalized_action_abs": 0.3,
            "predicted_maximum_current_utilization": 0.1,
            "target_fields": stored,
            "current_bounds_pass": True,
            "exact_stored_issue_center": True,
            "passed": False,
        }
        with mock.patch.object(
            audit.d1r2.s24.s21.s16.s9,
            "exact_stored_center_action",
            return_value=direct,
        ):
            action, event = controller._finish(np.zeros(14), np.zeros(14))
        self.assertTrue(event["passed"])
        self.assertAlmostEqual(
            event["continuation_incremental_normalized_action_linf"], 0.175
        )
        self.assertTrue(np.allclose(action, np.full(14, 0.175), rtol=0.0, atol=1e-15))
        self.assertEqual(
            controller._split_pending["intermediate_card15_fields"], continuation
        )
        self.assertEqual(controller._split_pending["continuation_count"], 1)

    def test_primary_and_independent_candidate_identity_match(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        specs = [
            {
                "experiment_id": "source",
                "pair_id": "pair",
                "history_member": "plus_first",
                "s24_sequence_index": 6,
            }
        ]
        rows = [
            {
                "source_experiment_id": "source",
                "source_raw_sha256": "1" * 64,
                "pair_id": "pair",
                "history_member": "plus_first",
                "sequence_index": 6,
            }
        ]
        primary_specs = audit._candidate_specs(rows, specs, cfg)
        independent_specs = independent._candidate_specs(rows, specs, cfg)
        self.assertEqual(primary_specs, independent_specs)
        self.assertEqual(len(primary_specs), 1)
        self.assertTrue(primary_specs[0]["experiment_id"].startswith("s42r3c3t13s24d1r6_"))
        self.assertFalse(primary_specs[0]["source_result_available_to_controller"])

    def test_launcher_uses_only_server_virtualenv_and_offline_audits(self):
        text = (ROOT / "run_stage4_2r3c3t13s24d1r5_offline.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python",
            text,
        )
        self.assertIn("stage4_2r3c3t13s24d1r5_recursive_split_return_preflight.py", text)
        self.assertIn("stage4_2r3c3t13s24d1r5_independent_forensics.py", text)
        self.assertNotIn("--command rollout", text)
        self.assertNotIn("--backend ray", text)
        self.assertNotIn("nohup ", text)


if __name__ == "__main__":
    unittest.main()
