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
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_370ms.json"


def _trajectory(horizon: int, direction: int | None = None, sign: int = 0, issue: int = 10):
    rows = []
    for state in range(horizon + 1):
        r_value = z_value = ip_value = 0.0
        if direction is not None and state >= issue + 1:
            if direction == 0:
                r_value = sign * 0.0003
            elif direction == 1:
                z_value = sign * 0.0003
            elif direction == 2:
                ip_value = sign * 100.0
            elif direction == 3 and state >= issue + 4:
                r_value = sign * 0.0003
        rows.append({"R": r_value, "Z": z_value, "Ip": ip_value})
    return rows


class Stage42R3C3T13S24D1R14R6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_self_test(self):
        r6._validate_config(copy.deepcopy(self.cfg), CONFIG)
        result = r6.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["expected_task_count"], 48)
        self.assertEqual(result["issue_steps"], [14, 18, 22])
        self.assertEqual(result["requested_matrix_digest"], r6._matrix_digest(
            np.asarray(self.cfg["controller_contract"]["requested_coordinate_matrix_columns"], dtype=float)
        ))
        self.assertEqual(result["requested_matrix_digest"], "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8")

    def test_contract_mutations_fail_closed(self):
        mutations = []
        for path, value in (
            (("controller_contract", "expected_task_count"), 49),
            (("controller_contract", "executed_direction_index"), 1),
            (("response_geometry", "maximum_condition_number"), 21.0),
            (("formal_timing_contract", "weak", "arrival_deadline_step"), 28),
            (("source_r4_contract", "raw_count"), 199),
            (("source_r5_contract", "required_construction_pass_count"), 47),
        ):
            changed = copy.deepcopy(self.cfg)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["bc_dagger_or_rl_allowed"] = True
        mutations.append(changed)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(ValueError):
                r6._validate_config(value, CONFIG)

    def test_load_config_forwards_sources_and_resolves_r4_r5(self):
        names = (
            "source_s21_run", "source_s23r1_output", "source_s24_run",
            "source_d1r9_v1", "source_d1r9_v2", "source_d1r10_run", "source_d1r10_audit",
        )
        closure = {name: ROOT / f"mock_{name}" for name in names}
        source_run = ROOT / "mock_d1r13_run"
        source_ctx = SimpleNamespace(paths=SimpleNamespace(run_dir=source_run.resolve()))
        with mock.patch.object(r6.d1r13, "load_config", return_value=source_ctx) as load:
            ctx = r6.load_config(
                CONFIG, source_d1r13_run=source_run,
                source_d1r13_audit=ROOT / "mock_d1r13_audit.json",
                source_r1a_output=ROOT / "mock_r1a", source_r2_run=ROOT / "mock_r2",
                source_r3_initial_output=ROOT / "mock_r3_initial",
                source_r3_corrected_output=ROOT / "mock_r3_corrected",
                source_r4_run=ROOT / "mock_r4", source_r5_output=ROOT / "mock_r5",
                source_d1r11_run=ROOT / "mock_d1r11", run_dir=ROOT / "mock_r6", **closure,
            )
        self.assertEqual(ctx.source_r4_run, (ROOT / "mock_r4").resolve())
        self.assertEqual(ctx.source_r5_output, (ROOT / "mock_r5").resolve())
        self.assertEqual(load.call_args.kwargs["run_dir"], source_run)

    def test_spec_matrix_is_48_direction0_only_probes(self):
        sources = []
        for index, context in enumerate(self.cfg["selected_source_d1r13_experiment_ids"]):
            sources.append({
                "experiment_id": context,
                "spec": {
                    "experiment_id": context,
                    "source_d1r11_experiment_id": f"d1r11_{index}",
                    "restart_snapshot_manifest_digest": f"snapshot_{index}",
                    "horizon_steps": 35 if index < 4 else 37,
                },
            })
        ctx = SimpleNamespace(cfg=self.cfg, source_ctx=SimpleNamespace(paths=SimpleNamespace(raw=ROOT / "mock_raw")))
        with mock.patch.object(r6, "_sha256", return_value="source_sha"), mock.patch.object(
            Path, "stat", return_value=SimpleNamespace(st_size=123)
        ):
            specs = r6.build_specs(ctx, sources)
        self.assertEqual(len(specs), 48)
        self.assertTrue(all(row["d1r14r6_role"] == "signed_probe" for row in specs))
        self.assertEqual({row["d1r14r6_direction_index"] for row in specs}, {0})
        self.assertEqual({row["d1r14r6_issue_task_step"] for row in specs}, {14, 18, 22})
        self.assertEqual(sum(row["d1r14r6_issue_task_step"] - 10 for row in specs), 384)
        self.assertEqual(sum(int(row["horizon_steps"]) - int(row["d1r14r6_zero_after_task_step"]) for row in specs), 768)

    def test_controller_is_causal_and_only_executes_direction0(self):
        controller = object.__new__(r6.MixedBasisSignedExcitationController)
        controller.d1r14r6_role = "signed_probe"
        controller.d1r14r6_direction_index = 0
        controller.d1r14r6_sign = 1
        controller.d1r14r6_requested_coordinate = np.asarray(
            self.cfg["controller_contract"]["requested_coordinate_matrix_columns"], dtype=float
        )[:, 0]
        controller.d1r14r6_issue_step = 14
        controller.d1r14r6_cancel_step = 15
        controller.d1r14r6_zero_after_step = 16
        controller._issue = mock.Mock(return_value=(np.ones(14) * 0.01, {"event": "sequential_issue", "passed": True}))
        controller._cancel = mock.Mock(return_value=(np.ones(14) * -0.01, {"event": "sequential_cancel", "passed": True}))
        controller.step = 14
        action, trace = controller.action({"step_index": 14, "currents_a_tsc": [0.0] * 14})
        controller._issue.assert_called_once()
        self.assertEqual(controller._issue.call_args.args[0], 0)
        self.assertEqual(trace["r3c3t13s24d1r14r6_event"], "signed_issue")
        self.assertTrue(np.array_equal(action, np.ones(14) * 0.01))
        controller.step = 15
        action, trace = controller.action({"step_index": 15, "currents_a_tsc": [0.0] * 14})
        self.assertEqual(trace["r3c3t13s24d1r14r6_event"], "stored_center_cancel")
        self.assertTrue(np.array_equal(action, np.ones(14) * -0.01))

    def test_controller_source_strips_all_experiment_labels(self):
        source = {
            "pair_id": "forbidden", "history_member": "forbidden", "partition": "forbidden",
            "d1r14r6_role": "signed_probe", "d1r14r6_direction_index": 0,
            "d1r14r6_direction_name": "pooled_mixed_0", "d1r14r6_sign": 1,
            "d1r14r6_requested_coordinate": [0.1] * 4, "d1r14r6_issue_task_step": 14,
            "d1r14r6_cancel_task_step": 15, "d1r14r6_zero_after_task_step": 16,
            "source_d1r13_experiment_id": "forbidden", "safe": 1,
        }
        schedule = {"issue_task_steps": [10, 13, 15, 17], "cancel_task_steps": [11, 14, 16, 18]}
        with mock.patch.object(r6.d1r11.s21.s16.s9, "_controller_spec", return_value=copy.deepcopy(source)):
            output = r6._controller_source_spec(source, schedule)
        self.assertEqual(output["safe"], 1)
        self.assertFalse(any(key.startswith(("d1r13_", "d1r14r6_", "source_d1r13_")) for key in output))
        self.assertNotIn("pair_id", output)

    def test_combined_geometry_replaces_only_r4_direction0(self):
        r4_specs, r4_results, r6_specs, r6_results, r2_specs, r2_results = [], {}, [], {}, [], {}
        for context_index, context in enumerate(self.cfg["selected_source_d1r13_experiment_ids"]):
            horizon = 35 if context_index < 4 else 37
            meta = {"source_d1r13_experiment_id": context, "pair_id": f"pair_{context_index // 2}", "history_member": "plus_first" if context_index % 2 == 0 else "minus_first", "horizon_steps": horizon}
            r4_baseline_id = f"{context}_r4_baseline"
            r4_specs.append({**meta, "experiment_id": r4_baseline_id, "d1r14r4_role": "baseline", "d1r14r4_direction_index": -1, "d1r14r4_sign": 0})
            r4_results[r4_baseline_id] = {"experiment_id": r4_baseline_id, "trajectory": _trajectory(horizon), "controller_trace": [{} for _ in range(horizon)]}
            r2_baseline_id = f"{context}_r2_baseline"
            r2_specs.append({**meta, "experiment_id": r2_baseline_id, "d1r14r2_role": "baseline", "d1r14r2_direction_index": -1, "d1r14r2_sign": 0})
            r2_results[r2_baseline_id] = {"experiment_id": r2_baseline_id, "trajectory": _trajectory(horizon), "controller_trace": [{} for _ in range(horizon)]}
            for issue in (10, 14, 18, 22):
                for direction in range(4):
                    for sign in (1, -1):
                        experiment_id = f"{context}_{issue}_{direction}_{sign}"
                        event = {"requested_coordinate": (np.eye(4)[:, direction] * sign).tolist(), "actual_signed_delta_field_kAt_tsc": (np.eye(14)[:, direction] * sign).tolist()}
                        trace = [{} for _ in range(horizon)]
                        if issue == 10:
                            trace[issue]["r3c3t13s24d1r14r2_event_detail"] = event
                            r2_specs.append({**meta, "experiment_id": experiment_id, "d1r14r2_role": "signed_probe", "d1r14r2_direction_index": direction, "d1r14r2_sign": sign, "d1r14r2_issue_task_step": issue})
                            r2_results[experiment_id] = {"experiment_id": experiment_id, "trajectory": _trajectory(horizon, direction, sign, issue), "controller_trace": trace}
                        elif direction == 0:
                            trace[issue]["r3c3t13s24d1r14r6_event_detail"] = event
                            r6_specs.append({**meta, "experiment_id": experiment_id, "d1r14r6_role": "signed_probe", "d1r14r6_direction_index": direction, "d1r14r6_direction_name": "pooled_mixed_0", "d1r14r6_sign": sign, "d1r14r6_requested_coordinate": event["requested_coordinate"], "d1r14r6_requested_matrix_digest": "x", "d1r14r6_issue_task_step": issue, "d1r14r6_cancel_task_step": issue + 1, "d1r14r6_zero_after_task_step": issue + 2})
                            r6_results[experiment_id] = {"experiment_id": experiment_id, "trajectory": _trajectory(horizon, direction, sign, issue), "controller_trace": trace}
                        else:
                            trace[issue]["r3c3t13s24d1r14r4_event_detail"] = event
                            r4_specs.append({**meta, "experiment_id": experiment_id, "d1r14r4_role": "signed_probe", "d1r14r4_direction_index": direction, "d1r14r4_direction_name": r6.DIRECTIONS[direction], "d1r14r4_sign": sign, "d1r14r4_requested_coordinate": event["requested_coordinate"], "d1r14r4_requested_matrix_digest": "old", "d1r14r4_issue_task_step": issue, "d1r14r4_cancel_task_step": issue + 1, "d1r14r4_zero_after_task_step": issue + 2})
                            r4_results[experiment_id] = {"experiment_id": experiment_id, "trajectory": _trajectory(horizon, direction, sign, issue), "controller_trace": trace}
        ctx = SimpleNamespace(cfg=self.cfg, source_r2_run=ROOT / "unused")
        with mock.patch.object(r6, "_authenticate_r4_r5", return_value={"r4_specs": r4_specs, "r4_results": r4_results}):
            result = r6._combined_response_geometry(ctx, r6_specs, r6_results, source_r2_specs=r2_specs, source_r2_results=r2_results)
        self.assertTrue(result["passed"])
        self.assertEqual(result["signal_pass_count"], 256)
        self.assertEqual(result["rank_pass_count"], 64)
        self.assertEqual(result["condition_pass_count"], 64)
        self.assertEqual(result["r6_direction0_antipodal_pair_pass_count"], 24)
        self.assertEqual(result["bank_composition"]["combined_signed_probe_count"], 256)

    def test_resume_authenticates_r4_r5_package_and_specs(self):
        source = inspect.getsource(r6._assert_run_identity)
        for token in ("_authenticate_source(ctx)", "source_r4_inventory_digest", "source_r4_spec_digest", "source_r5_hashes", "source_r5_compact_sha256", "package_digest"):
            self.assertIn(token, source)
        self.assertIn("_assert_run_identity(ctx)", inspect.getsource(r6.run_real))
        self.assertIn("_assert_run_identity(ctx)", inspect.getsource(r6.postprocess))

    def test_independent_forensic_and_launchers_are_fail_closed(self):
        independent = (ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r6_independent_forensics.py").read_text(encoding="utf-8")
        self.assertNotIn("from tsc_rzip_rllib.diagnostics", independent)
        self.assertIn("def _adapt_combined_bank", independent)
        self.assertIn("r4_baseline_issue_state_exact", independent)
        self.assertIn("--source-r4-run", independent)
        self.assertIn("--source-r5-output", independent)
        common = (ROOT / "run_stage4_2r3c3t13s24d1r14r6_common.sh").read_text(encoding="utf-8")
        shell_common = (ROOT / "scripts/stage4_2r3c3t13s24d1r14r6_shell_common.sh").read_text(encoding="utf-8")
        stop = (ROOT / "run_stop_stage4_2r3c3t13s24d1r14r6_now.sh").read_text(encoding="utf-8")
        self.assertIn("/tsc_simulation/venv_simu/bin/python", shell_common)
        self.assertIn("WORKERS:-96", shell_common)
        self.assertIn("48 fresh TSC", common)
        self.assertIn("--source-r4-run", common)
        self.assertIn("--source-r5-output", common)
        self.assertIn('kill -TERM "${PID}"', stop)
        self.assertNotIn("pkill", stop)
        self.assertNotIn("ray stop --force", stop)


if __name__ == "__main__":
    unittest.main()
