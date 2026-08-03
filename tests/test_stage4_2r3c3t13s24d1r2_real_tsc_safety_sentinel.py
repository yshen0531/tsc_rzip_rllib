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
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as stage,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_forensics as forensics,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_370ms.json"
)
DESIGN = (
    ROOT
    / "docs"
    / "codex"
    / "reports"
    / "STAGE4_2R3C3T13S24D1R2_REAL_TSC_SAFETY_SENTINEL_DESIGN.md"
)


class Stage42R3C3T13S24D1R2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_design_and_self_test(self):
        stage._validate_config(copy.deepcopy(self.cfg), CONFIG)
        self.assertEqual(stage._sha256(DESIGN), self.cfg["design_document_sha256"])
        result = stage.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertTrue(result["identity_roundtrip_exact"])
        self.assertEqual(result["expected_real_tsc_rollouts"], 54)
        self.assertEqual(
            result["maximum_online_cancel_incremental_normalized_action_linf"],
            0.24,
        )

    def test_normalization_changes_only_five_frozen_paths(self):
        source = {
            "experiment_id": "s42r3c3t13s24d2_abc123",
            "environment_variant": (
                "stage4_2r3c3t13s24d2_s42r3c3t13s24d2_abc123"
            ),
            "kind": self.cfg["identity_normalization"]["old_kind"],
            "phase": self.cfg["identity_normalization"]["old_phase"],
            "s24d2_online_cancel_margin_gate": 0.24,
            "snapshot": "unchanged",
            "actions": [0.29, -0.29, 0.36, -0.36],
        }
        normalized = stage._normalise_spec(source, self.cfg)
        self.assertEqual(
            normalized["experiment_id"], "s42r3c3t13s24d1r2_abc123"
        )
        self.assertEqual(stage._reverse_normalisation(normalized, self.cfg), source)
        changed = copy.deepcopy(source)
        changed["environment_variant"] += "_changed"
        with self.assertRaisesRegex(ValueError, "environment identity"):
            stage._normalise_spec(changed, self.cfg)

    def test_gate_timing_capacity_and_rl_changes_fail_closed(self):
        mutations = []
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"][
            "maximum_online_cancel_incremental_normalized_action_linf"
        ] = 0.25
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["formal_timing_contract"]["weak"]["arrival_deadline_step"] = 28
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["parallel"]["n_workers"] = 53
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["scientific_scope"]["bc_dagger_or_rl_allowed"] = True
        mutations.append(changed)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    stage._validate_config(value, CONFIG)

    def _cancel_controller(self, increment: float):
        controller = object.__new__(stage.GeometryRestoredSafetySentinelController)
        controller._last_failed_event = None
        controller._active_issue = {
            "slot": 0,
            "center_card15_fields": [
                stage.s24.s21.s16.s9.format_number(0.0) for _ in range(14)
            ],
            "target_card15_fields": [
                stage.s24.s21.s16.s9.format_number(0.25 if coil < 4 else 0.0)
                for coil in range(14)
            ],
        }
        controller.step = 11
        controller.cancel_steps = (11, 14, 16, 18)
        controller.requested_by_step = {11: np.full(4, -0.29)}
        controller.schedule_cfg = copy.deepcopy(self.cfg["schedule_contract"])
        controller.lattice_cfg = {}
        controller.turns_tsc = np.ones(14)
        controller.base = SimpleNamespace(
            max_delta_a=1e6,
            min_current=np.full(14, -1e6),
            max_current=np.full(14, 1e6),
        )
        cancelled = SimpleNamespace(
            card15_fields=controller._active_issue["center_card15_fields"],
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )
        controller.actuator = SimpleNamespace(apply=mock.Mock(return_value=cancelled))
        chosen = {
            "action_norm_tsc": [0.0] * 14,
            "incremental_normalized_action_linf": increment,
            "total_normalized_action_abs": 0.3,
            "predicted_maximum_current_utilization": 0.4,
            "passed": True,
        }
        return controller, chosen

    def test_added_margin_fails_before_return_while_original_cap_still_passes(self):
        controller, chosen = self._cancel_controller(0.241)
        with mock.patch.object(
            stage.s24.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ):
            with self.assertRaisesRegex(ValueError, "D1R2 sequential cancel"):
                controller._cancel(0, np.zeros(14), np.zeros(14))
        event = controller._last_failed_event
        self.assertIsNotNone(event)
        self.assertTrue(event["criteria"]["incremental_action"])
        self.assertFalse(event["criteria"]["online_cancel_margin"])
        self.assertIsNotNone(controller._active_issue)

    def test_cancel_under_margin_passes_both_caps_and_exact_zero(self):
        controller, chosen = self._cancel_controller(0.239)
        with mock.patch.object(
            stage.s24.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ):
            _, event = controller._cancel(0, np.zeros(14), np.zeros(14))
        self.assertTrue(event["passed"])
        self.assertTrue(event["criteria"]["incremental_action"])
        self.assertTrue(event["criteria"]["online_cancel_margin"])
        self.assertTrue(forensics._cancel_gate(event, self.cfg))
        self.assertIsNone(controller._active_issue)

    def test_complete_failure_raw_is_covered_and_never_rescheduled_by_resume(self):
        spec = {"experiment_id": "example", "horizon_steps": 35}
        result = {
            "completed": True,
            "success": False,
            "stage": stage.STAGE,
            "campaign_identity": stage.CAMPAIGN_IDENTITY,
            "controller_revision": stage.CONTROLLER_REVISION,
            "probe_primitive_revision": stage.CONTROLLER_REVISION,
            "experiment_id": "example",
            "spec": copy.deepcopy(spec),
            "failure_class": "structured_action_schedule_gate",
            "trajectory": [{} for _ in range(12)],
            "controller_trace": [{} for _ in range(11)],
        }
        path = mock.Mock()
        path.is_file.return_value = True
        with mock.patch.object(stage, "_read_raw", return_value=result):
            self.assertTrue(stage._result_covered(path, spec))
            self.assertFalse(stage._result_success(path, spec))

    def test_launchers_use_server_virtualenv_fixed_capacity_and_independent_raw_code(self):
        shell = (ROOT / "scripts/stage4_2r3c3t13s24d1r2_shell_common.sh").read_text(
            encoding="utf-8"
        )
        common = (ROOT / "run_stage4_2r3c3t13s24d1r2_common.sh").read_text(
            encoding="utf-8"
        )
        independent = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python",
            shell,
        )
        self.assertIn("WORKERS:-54", shell)
        self.assertIn("exact 54-case real-TSC sentinel", common)
        self.assertNotIn("stage._execution_audit", independent)
        self.assertIn("_issue_gate", independent)
        self.assertIn("_cancel_gate", independent)


if __name__ == "__main__":
    unittest.main()
