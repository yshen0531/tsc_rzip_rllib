from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import sys
import tempfile
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
    stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel as d1r13,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_370ms.json"
)


class Stage42R3C3T13S24D1R13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_self_test(self):
        d1r13._validate_config(copy.deepcopy(self.cfg), CONFIG)
        result = d1r13.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_source_count"], 8)
        self.assertEqual(result["zero_start"], 10)
        self.assertEqual(result["expected_post_prefix_action_count"], 208)

    def test_contract_mutations_fail_closed(self):
        mutations = []
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["zero_increment_first_task_step"] = 11
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["formal_timing_contract"]["weak"]["arrival_deadline_step"] = 28
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["selected_source_baseline_experiment_ids"][0] = "wrong"
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["bc_dagger_or_rl_allowed"] = True
        mutations.append(changed)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    d1r13._validate_config(value, CONFIG)

    def test_zero_action_is_exact_and_boundary_is_fail_closed(self):
        with self.assertRaises(ValueError):
            d1r13.zero_increment_action(9)
        for step in (10, 34, 36):
            action = d1r13.zero_increment_action(step)
            self.assertEqual(action.shape, (14,))
            self.assertTrue(np.array_equal(action, np.zeros(14)))

    def test_controller_delegates_only_steps_zero_through_nine(self):
        controller = object.__new__(d1r13.ZeroIncrementController)
        controller.step = 9
        parent_action = np.linspace(-0.2, 0.2, 14)
        with mock.patch.object(
            d1r13.d1r11.SequentialAmplitudeCodedProbeController,
            "action",
            return_value=(parent_action, {"source_trace": "exact"}),
        ) as parent:
            action, trace = controller.action({"step_index": 9})
        parent.assert_called_once()
        self.assertTrue(np.array_equal(action, parent_action))
        self.assertEqual(trace["source_trace"], "exact")
        self.assertTrue(trace["r3c3t13s24d1r13_delegated_prefix"])

        controller.step = 10
        with mock.patch.object(
            d1r13.d1r11.SequentialAmplitudeCodedProbeController, "action"
        ) as parent:
            action, trace = controller.action({"step_index": 10})
        parent.assert_not_called()
        self.assertTrue(np.array_equal(action, np.zeros(14)))
        self.assertTrue(trace["r3c3t13s24d1r13_zero_increment"])
        self.assertFalse(trace["r3c3t13s24d1r13_future_r17_executed"])
        self.assertTrue(all(not bool(trace[key]) for key in d1r13.FORBIDDEN_TRACE_KEYS))

    def test_zero_branch_reads_only_step_index(self):
        class ReadAudit(dict):
            def __init__(self):
                super().__init__(step_index=10)
                self.reads = []

            def __getitem__(self, key):
                self.reads.append(key)
                return super().__getitem__(key)

        current = ReadAudit()
        controller = object.__new__(d1r13.ZeroIncrementController)
        controller.step = 10
        action, _ = controller.action(current)
        self.assertTrue(np.array_equal(action, np.zeros(14)))
        self.assertEqual(current.reads, ["step_index"])

    def test_semantic_state_excludes_only_runtime_timing(self):
        row = {
            "R": 0.7,
            "wire_currents_a": [1.0, 2.0],
            "gotsc_subprocess_s": 4.0,
            "step_total_s": 5.0,
        }
        self.assertEqual(
            d1r13._semantic_state(row),
            {"R": 0.7, "wire_currents_a": [1.0, 2.0]},
        )

    def test_source_trace_projection_requires_all_source_fields(self):
        source = {"a": 1, "nested": {"x": [2, 3]}}
        self.assertTrue(d1r13._source_trace_projection(source, {**source, "new": 4}))
        self.assertFalse(d1r13._source_trace_projection(source, {"a": 1}))

    def test_snapshot_audit_has_exact_eight_case_contract(self):
        with tempfile.TemporaryDirectory(prefix=".d1r13-snapshot-test-", dir=ROOT) as tmp:
            root = Path(tmp)
            table = []
            for index in range(8):
                directory = root / f"snapshot_{index}"
                directory.mkdir()
                (directory / "restart_snapshot_manifest.json").write_text(
                    json.dumps({"digest": f"digest_{index}"}), encoding="utf-8"
                )
                table.append(
                    {
                        "pair_id": f"pair_{index // 2}",
                        "history_member": "plus_first" if index % 2 == 0 else "minus_first",
                        "restart_snapshot_dir": str(directory),
                        "restart_snapshot_manifest_digest": f"digest_{index}",
                        "state_generation_experiment_id": f"state_{index}",
                    }
                )
            with mock.patch.object(
                d1r13.d1r11.s21.s16.s9.t11.t1.r1,
                "_validate_snapshot_inventory",
                return_value=True,
            ):
                result = d1r13._snapshot_audit(table)
        self.assertTrue(result["passed"])
        self.assertEqual(result["expected"], 8)
        self.assertEqual(result["actual"], 8)
        self.assertEqual(result["pass_count"], 8)

    def test_ray_execution_uses_validated_actor_capacity(self):
        source = inspect.getsource(d1r13.evaluate_specs)
        self.assertIn("range(0, len(pending), plan.actor_count)", source)
        self.assertIn("pending[batch_start : batch_start + plan.actor_count]", source)


if __name__ == "__main__":
    unittest.main()
