from __future__ import annotations

import json
import math
import sys
import types
import unittest
from unittest import mock

import numpy as np

if sys.platform == "win32":
    try:
        import resource as _resource  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.RLIMIT_CORE = 4
        resource.getrlimit = lambda _which: (65536, 65536)
        resource.setrlimit = lambda _which, _limits: None
        sys.modules["resource"] = resource

from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.core.inputa import format_number
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s4_lattice_transition_holdout as s4,
)


def _cfg():
    return s4.t11.t1.r3c3.read_json(
        s4._project_root()
        / "configs/stage4_2r3c3t13s4_lattice_transition_holdout_370ms.json"
    )


def _plan(center: float = 0.0):
    cfg = _cfg()["lattice_probe"]
    mode = np.ones(14) / math.sqrt(14)
    current = [center * 1000.0 / 100.0] * 14
    model = QuantizedActuatorModel(
        minimum_current_a_tsc=(-20000.0,) * 14,
        maximum_current_a_tsc=(20000.0,) * 14,
        max_slew_step_a=1000.0,
        turns_tsc=(100.0,) * 14,
    )
    center_result = model.apply(current, [0.0] * 14)
    plan = s4.choose_lattice_displacement(
        center_fields=center_result.card15_fields,
        measured_current_a_tsc=current,
        baseline_action_norm_tsc=[0.0] * 14,
        mode_vector_tsc=mode,
        turns_tsc=[100.0] * 14,
        max_slew_step_a=1000.0,
        minimum_current_a_tsc=[-20000.0] * 14,
        maximum_current_a_tsc=[20000.0] * 14,
        cfg=cfg,
    )
    return cfg, model, current, plan


class Stage42R3C3T13S4Tests(unittest.TestCase):
    def test_frozen_config_and_exact_component_count(self):
        cfg = _cfg()
        s4._validate_config(cfg)
        self.assertEqual(
            cfg["lattice_probe"]["expected_current_components"], 26208
        )
        self.assertEqual(26 * 37 * 14 + 26 * 35 * 14, 26208)

    def test_local_steps_are_positive_symmetric_and_round_trip(self):
        for value in (1.234, -1.234, 1000.0, -1000.0, 0.0):
            with self.subTest(value=value):
                field = format_number(value)
                center = s4._decimal_field(field)
                step = s4.local_symmetric_card15_step(field)
                plus = format_number(float(center + step))
                minus = format_number(float(center - step))
                self.assertGreater(step, 0)
                self.assertEqual(len(plus), 10)
                self.assertEqual(len(minus), 10)
                self.assertEqual(
                    s4._decimal_field(plus) - center,
                    center - s4._decimal_field(minus),
                )

    def test_dynamic_lattice_moves_four_steps_and_reproduces_fields(self):
        _, model, current, plan = _plan()
        self.assertTrue(plan["passed"])
        self.assertGreaterEqual(plan["minimum_significant_grid_steps_actual"], 4)
        self.assertTrue(plan["target_field_central_symmetry_exact"])
        self.assertGreaterEqual(plan["coil_space_cosine"], 0.98)
        self.assertLessEqual(plan["relative_off_mode_residual"], 0.15)
        positive = model.apply(current, plan["positive_action_norm_tsc"])
        negative = model.apply(current, plan["negative_action_norm_tsc"])
        self.assertEqual(
            list(positive.card15_fields), plan["positive_target_fields"]
        )
        self.assertEqual(
            list(negative.card15_fields), plan["negative_target_fields"]
        )

    def test_exact_cancellation_uses_negative_issued_field_displacement(self):
        cfg, model, current, plan = _plan(1.234)
        center = model.apply(current, [0.0] * 14)
        inverse = s4.exact_inverse_lattice_action(
            center_fields=center.card15_fields,
            signed_issue_delta_kAt_tsc=plan["delta_field_kAt_tsc"],
            measured_current_a_tsc=current,
            baseline_action_norm_tsc=[0.0] * 14,
            turns_tsc=[100.0] * 14,
            max_slew_step_a=1000.0,
            minimum_current_a_tsc=[-20000.0] * 14,
            maximum_current_a_tsc=[20000.0] * 14,
            cfg=cfg,
        )
        selected = model.apply(current, inverse["action_norm_tsc"])
        self.assertTrue(inverse["passed"])
        self.assertTrue(inverse["exact_negative_of_issued_displacement"])
        self.assertEqual(list(selected.card15_fields), inverse["target_fields"])

    def test_cancellation_fails_closed_at_current_boundary(self):
        inverse = s4.exact_inverse_lattice_action(
            center_fields=[format_number(1.0)] * 14,
            signed_issue_delta_kAt_tsc=[-10.0] * 14,
            measured_current_a_tsc=[10.0] * 14,
            baseline_action_norm_tsc=[0.0] * 14,
            turns_tsc=[100.0] * 14,
            max_slew_step_a=1.0,
            minimum_current_a_tsc=[-20.0] * 14,
            maximum_current_a_tsc=[20.0] * 14,
            cfg=_cfg()["lattice_probe"],
        )
        self.assertFalse(inverse["passed"])
        self.assertFalse(inverse["current_bounds_pass"])

    def test_blind_guard_requires_development_and_model_hash(self):
        guard = s4.BlindOpenOrderGuard(expected_development_count=2)
        guard.before_open("development")
        with self.assertRaisesRegex(ValueError, "before development model hash"):
            guard.before_open("blind_holdout")
        guard.before_open("development")
        guard.freeze("a" * 64)
        guard.before_open("blind_holdout")
        self.assertEqual(guard.development_open_count, 2)
        self.assertEqual(guard.holdout_open_count, 1)

    def test_blind_guard_rejects_late_development_and_bad_hash(self):
        guard = s4.BlindOpenOrderGuard(expected_development_count=1)
        guard.before_open("development")
        with self.assertRaisesRegex(ValueError, "64 hexadecimal"):
            guard.freeze("bad")
        guard.freeze("b" * 64)
        with self.assertRaisesRegex(ValueError, "after T13S4 model freeze"):
            guard.before_open("development")

    def test_controller_spec_strips_identity_and_history_labels(self):
        source = {
            "pair_id": "forbidden",
            "history_member": "forbidden",
            "common_prefix_steps": 5,
            "state_generation_experiment_id": "forbidden",
            "baseline_experiment_id": "forbidden",
            "restart_snapshot_dir": "forbidden",
            "restart_snapshot_manifest_digest": "forbidden",
            "experiment_id": "forbidden",
            "environment_variant": "forbidden",
            "kind": "forbidden",
            "phase": "forbidden",
            "category": "forbidden",
            "r3c3t13s4_offline_role": "development",
            "r3c3t13s4_stratum": "hard",
            "r3c3t13s4_source_r3c1_experiment_id": "forbidden",
            "target_id": "nominal",
        }
        self.assertEqual(s4._controller_spec(source), {"target_id": "nominal"})

    def test_self_test_is_json_safe_zero_tsc_and_passes(self):
        result = s4.self_test()
        json.dumps(result, sort_keys=True, allow_nan=False)
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertFalse(result["bc_dagger_or_rl_allowed"])

    def test_offline_design_failure_is_recorded_without_tsc(self):
        ctx = types.SimpleNamespace(
            paths=types.SimpleNamespace(state="state.json")
        )
        offline = {
            "passed": False,
            "route": "LATTICE_PREFLIGHT_FAIL_NO_REAL_TSC",
            "lattice_design_failure_count": 40,
            "raw_count": 0,
            "plant_advance_count": 0,
            "real_tsc_executed": False,
        }
        writes = []
        with (
            mock.patch.object(s4, "prepare", return_value=([], [])),
            mock.patch.object(
                s4, "run_offline_lattice_audit", return_value=offline
            ),
            mock.patch.object(
                s4.t11.t1.r3c3, "read_json", return_value={"prepared": True}
            ),
            mock.patch.object(
                s4.t11.t1.r3c3,
                "atomic_write_json",
                side_effect=lambda path, payload: writes.append((path, payload)),
            ),
        ):
            result = s4.execute(
                ctx, command="offline", backend="local", resume=False
            )
        self.assertTrue(result["finished"])
        self.assertFalse(result["primary_pass"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertEqual(len(writes), 1)
        state = writes[0][1]
        self.assertEqual(state["phase_status"], "offline_gate_failed")
        self.assertEqual(
            state["stop_reason"], "frozen_dynamic_lattice_infeasible"
        )
        self.assertFalse(state["real_tsc_executed"])


if __name__ == "__main__":
    unittest.main()
