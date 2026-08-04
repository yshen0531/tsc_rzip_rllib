from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import sys
import types
import unittest
from types import SimpleNamespace
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
    stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel as d1r14,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_370ms.json"
)


def _trajectory(horizon: int, direction: int | None = None, sign: int = 0):
    rows = []
    for state in range(horizon + 1):
        r = z = ip = 0.0
        if direction is not None and state >= 11:
            if direction == 0:
                r = sign * 0.0003
            elif direction == 1:
                z = sign * 0.0003
            elif direction == 2:
                ip = sign * 100.0
            elif direction == 3 and state >= 14:
                r = sign * 0.0003
        rows.append({"R": r, "Z": z, "Ip": ip})
    return rows


class Stage42R3C3T13S24D1R14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_self_test(self):
        d1r14._validate_config(copy.deepcopy(self.cfg), CONFIG)
        result = d1r14.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_context_count"], 8)
        self.assertEqual(result["expected_task_count"], 72)
        self.assertEqual(result["synthetic_rank"], 4)

    def test_contract_mutations_fail_closed(self):
        mutations = []
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["issue_task_step"] = 11
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["response_geometry"]["maximum_condition_number"] = 21.0
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["formal_timing_contract"]["weak"]["arrival_deadline_step"] = 28
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["parallel"]["n_workers"] = 8
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["bc_dagger_or_rl_allowed"] = True
        mutations.append(changed)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    d1r14._validate_config(value, CONFIG)

    def test_load_config_forwards_complete_d1r13_source_closure(self):
        names = (
            "source_s21_run",
            "source_s23r1_output",
            "source_s24_run",
            "source_d1r9_v1",
            "source_d1r9_v2",
            "source_d1r10_run",
            "source_d1r10_audit",
        )
        paths = {name: ROOT / f"mock_{name}" for name in names}
        source_d1r13_run = ROOT / "mock_d1r13_run"
        source_ctx = SimpleNamespace(
            paths=SimpleNamespace(run_dir=source_d1r13_run.resolve())
        )
        with mock.patch.object(d1r14.d1r13, "load_config", return_value=source_ctx) as load:
            ctx = d1r14.load_config(
                CONFIG,
                source_d1r13_run=source_d1r13_run,
                source_d1r13_audit=ROOT / "mock_d1r13_audit.json",
                source_d1r11_run=ROOT / "mock_d1r11_run",
                run_dir=ROOT / "mock_d1r14_run",
                **paths,
            )
        self.assertIs(ctx.source_ctx, source_ctx)
        kwargs = load.call_args.kwargs
        for name, path in paths.items():
            self.assertEqual(kwargs[name], path)
        self.assertEqual(kwargs["run_dir"], source_d1r13_run)

    def test_zero_action_boundary(self):
        with self.assertRaises(ValueError):
            d1r14.zero_action(9)
        for step in (10, 12, 36):
            action = d1r14.zero_action(step)
            self.assertEqual(action.shape, (14,))
            self.assertTrue(np.array_equal(action, np.zeros(14)))

    def test_prefix_delegates_and_baseline_zero_reads_only_step(self):
        controller = object.__new__(d1r14.ZeroBaselineSignedExcitationController)
        controller.step = 9
        controller.d1r14_role = "baseline"
        parent_action = np.linspace(-0.2, 0.2, 14)
        with mock.patch.object(
            d1r14.d1r11.SequentialAmplitudeCodedProbeController,
            "action",
            return_value=(parent_action, {"source_trace": "exact"}),
        ) as parent:
            action, trace = controller.action({"step_index": 9})
        parent.assert_called_once()
        self.assertTrue(np.array_equal(action, parent_action))
        self.assertEqual(trace["source_trace"], "exact")
        self.assertTrue(trace["r3c3t13s24d1r14_delegated_prefix"])

        class ReadAudit(dict):
            def __init__(self):
                super().__init__(step_index=10)
                self.reads = []

            def __getitem__(self, key):
                self.reads.append(key)
                return super().__getitem__(key)

        current = ReadAudit()
        controller.step = 10
        with mock.patch.object(
            d1r14.d1r11.SequentialAmplitudeCodedProbeController, "action"
        ) as parent:
            action, trace = controller.action(current)
        parent.assert_not_called()
        self.assertEqual(current.reads, ["step_index"])
        self.assertTrue(np.array_equal(action, np.zeros(14)))
        self.assertTrue(trace["r3c3t13s24d1r14_zero_increment"])

    def test_signed_issue_and_cancel_are_fixed_and_causal(self):
        controller = object.__new__(d1r14.ZeroBaselineSignedExcitationController)
        controller.d1r14_role = "signed_probe"
        controller.d1r14_direction_index = 2
        controller.d1r14_sign = -1
        controller.d1r14_requested_coordinate = np.asarray([0.0, 0.0, -0.25, 0.0])
        issued_action = np.linspace(-0.1, 0.1, 14)
        cancelled_action = -issued_action
        controller._issue = mock.Mock(
            return_value=(issued_action, {"event": "sequential_issue", "passed": True})
        )
        controller._cancel = mock.Mock(
            return_value=(
                cancelled_action,
                {"event": "sequential_cancel", "passed": True},
            )
        )
        current = {"step_index": 10, "currents_a_tsc": [1.0] * 14}
        controller.step = 10
        action, trace = controller.action(current)
        self.assertTrue(np.array_equal(action, issued_action))
        self.assertEqual(trace["r3c3t13s24d1r14_event"], "signed_issue")
        controller._issue.assert_called_once()
        self.assertEqual(controller._issue.call_args.args[0], 2)

        current["step_index"] = 11
        controller.step = 11
        action, trace = controller.action(current)
        self.assertTrue(np.array_equal(action, cancelled_action))
        self.assertEqual(trace["r3c3t13s24d1r14_event"], "stored_center_cancel")
        controller._cancel.assert_called_once()
        self.assertEqual(controller._cancel.call_args.args[0], 2)

        current = {"step_index": 12}
        controller.step = 12
        action, trace = controller.action(current)
        self.assertTrue(np.array_equal(action, np.zeros(14)))
        self.assertTrue(trace["r3c3t13s24d1r14_zero_increment"])

    def test_controller_source_spec_strips_labels_and_has_no_future_sequence(self):
        source = {
            "pair_id": "forbidden",
            "history_member": "forbidden",
            "partition": "forbidden",
            "d1r14_role": "signed_probe",
            "d1r14_direction_index": 1,
            "d1r14_direction_name": "mode0_coil8_component",
            "d1r14_sign": 1,
            "d1r14_requested_coordinate": [0.0, 0.25, 0.0, 0.0],
            "d1r14_issue_task_step": 10,
            "d1r14_cancel_task_step": 11,
            "d1r14_zero_after_task_step": 12,
            "d1r13_source_prefix_hash": "forbidden",
            "source_d1r13_audit_sha256": "forbidden",
            "safe": 1,
        }
        schedule = {
            "issue_task_steps": [10, 13, 15, 17],
            "cancel_task_steps": [11, 14, 16, 18],
        }
        with mock.patch.object(
            d1r14.d1r11.s21.s16.s9,
            "_controller_spec",
            return_value=copy.deepcopy(source),
        ):
            output = d1r14._controller_source_spec(source, schedule)
        self.assertEqual(output["safe"], 1)
        self.assertEqual(output["s24_sequence_index"], -1)
        self.assertEqual(output["s24_requested_matrix_row"], [0.0] * 16)
        self.assertTrue(
            all(
                value == [0.0] * 4
                for value in output["s24_requested_action_by_task_step"].values()
            )
        )
        self.assertNotIn("pair_id", output)
        self.assertNotIn("d1r14_direction_name", output)
        self.assertFalse(
            any(
                key.startswith(("d1r13_", "d1r14_", "source_d1r13_"))
                for key in output
            )
        )

    def test_visible_outputs_construct_backward_velocity_and_state10_origin(self):
        trajectory = _trajectory(35, direction=0, sign=1)
        scales = np.asarray([0.03, 0.03, 0.1, 0.1, 10000.0])
        values = d1r14._visible_outputs5(trajectory, scales)
        self.assertEqual(values.shape, (36, 5))
        self.assertTrue(np.array_equal(values[10], np.zeros(5)))
        self.assertGreater(values[11, 0], 0.0)
        self.assertGreater(values[11, 2], 0.0)

    def test_geometry_uses_fresh_baseline_signed_pairs_and_passes_rank_four(self):
        specs = []
        results = {}
        selected = self.cfg["selected_source_d1r13_experiment_ids"]
        for context_index, context_id in enumerate(selected):
            horizon = 35 if context_index < 4 else 37
            pair_id = f"pair_{context_index // 2}"
            baseline_id = f"{context_id}_baseline"
            baseline_spec = {
                "experiment_id": baseline_id,
                "source_d1r13_experiment_id": context_id,
                "d1r14_role": "baseline",
                "d1r14_direction_index": -1,
                "d1r14_sign": 0,
                "pair_id": pair_id,
                "history_member": "plus_first" if context_index % 2 == 0 else "minus_first",
                "horizon_steps": horizon,
            }
            specs.append(baseline_spec)
            results[baseline_id] = {
                "experiment_id": baseline_id,
                "trajectory": _trajectory(horizon),
            }
            for direction in range(4):
                for sign in (1, -1):
                    experiment_id = f"{context_id}_{direction}_{sign}"
                    spec = {
                        **baseline_spec,
                        "experiment_id": experiment_id,
                        "d1r14_role": "signed_probe",
                        "d1r14_direction_index": direction,
                        "d1r14_sign": sign,
                    }
                    specs.append(spec)
                    results[experiment_id] = {
                        "experiment_id": experiment_id,
                        "trajectory": _trajectory(horizon, direction, sign),
                    }
        ctx = types.SimpleNamespace(cfg=self.cfg)
        result = d1r14._response_geometry(ctx, specs, results)
        self.assertTrue(result["passed"])
        self.assertEqual(result["signed_pair_count"], 32)
        self.assertEqual(result["signal_pass_count"], 32)
        self.assertEqual(result["symmetry_pass_count"], 32)
        self.assertEqual(result["rank_pass_count"], 8)
        self.assertEqual(result["condition_pass_count"], 8)
        self.assertEqual(len(result["matched_hidden_history_rows_report_only"]), 16)

    def test_event_gate_requires_every_frozen_criterion(self):
        event = {
            "event": "sequential_issue",
            "slot": 2,
            "task_step": 10,
            "passed": True,
            "criteria": {"finite": True, "current_utilization": True},
        }
        self.assertTrue(
            d1r14._event_passes(
                event, expected_name="sequential_issue", slot=2, task_step=10
            )
        )
        event["criteria"]["current_utilization"] = False
        self.assertFalse(
            d1r14._event_passes(
                event, expected_name="sequential_issue", slot=2, task_step=10
            )
        )

    def test_forbidden_trace_keys_and_ray_batching_are_fail_closed(self):
        trace = d1r14._trace_template(12, np.zeros(14))
        self.assertTrue(all(not bool(trace.get(key)) for key in d1r14.FORBIDDEN_TRACE_KEYS))
        source = inspect.getsource(d1r14.evaluate_specs)
        self.assertIn("range(0, len(pending), plan.actor_count)", source)
        self.assertIn("pending[batch_start : batch_start + plan.actor_count]", source)


if __name__ == "__main__":
    unittest.main()
