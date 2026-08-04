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
    stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel as d1r14r4,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_370ms.json"
)


def _trajectory(
    horizon: int,
    direction: int | None = None,
    sign: int = 0,
    issue_step: int = 10,
):
    rows = []
    for state in range(horizon + 1):
        r = z = ip = 0.0
        if direction is not None and state >= issue_step + 1:
            if direction == 0:
                r = sign * 0.0003
            elif direction == 1:
                z = sign * 0.0003
            elif direction == 2:
                ip = sign * 100.0
            elif direction == 3 and state >= issue_step + 4:
                r = sign * 0.0003
        rows.append({"R": r, "Z": z, "Ip": ip})
    return rows


class Stage42R3C3T13S24D1R14R4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_self_test(self):
        d1r14r4._validate_config(copy.deepcopy(self.cfg), CONFIG)
        result = d1r14r4.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_context_count"], 8)
        self.assertEqual(result["expected_task_count"], 200)
        self.assertEqual(result["issue_steps"], [14, 18, 22])
        self.assertEqual(result["synthetic_rank"], 4)
        self.assertEqual(
            result["requested_matrix_digest"],
            "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c",
        )
        requested = np.asarray(
            self.cfg["controller_contract"]["requested_coordinate_matrix_columns"],
            dtype=float,
        )
        self.assertEqual(requested.shape, (4, 4))
        self.assertTrue(np.all(np.count_nonzero(requested, axis=0) == 4))

    def test_contract_mutations_fail_closed(self):
        mutations = []
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["issue_task_steps"] = [14, 18, 23]
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
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["requested_coordinate_matrix_columns"][0][0] += 1e-9
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["source_r1a_contract"]["required_static_issue_pass_count"] = 63
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["routes"]["pass"] = "PASS"
        mutations.append(changed)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    d1r14r4._validate_config(value, CONFIG)

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
        with mock.patch.object(d1r14r4.d1r13, "load_config", return_value=source_ctx) as load:
            ctx = d1r14r4.load_config(
                CONFIG,
                source_d1r13_run=source_d1r13_run,
                source_d1r13_audit=ROOT / "mock_d1r13_audit.json",
                source_r1a_output=ROOT / "mock_r1a_output",
                source_r2_run=ROOT / "mock_r2_run",
                source_r3_initial_output=ROOT / "mock_r3_initial",
                source_r3_corrected_output=ROOT / "mock_r3_corrected",
                source_d1r11_run=ROOT / "mock_d1r11_run",
                run_dir=ROOT / "mock_d1r14r4_run",
                **paths,
            )
        self.assertIs(ctx.source_ctx, source_ctx)
        kwargs = load.call_args.kwargs
        for name, path in paths.items():
            self.assertEqual(kwargs[name], path)
        self.assertEqual(kwargs["run_dir"], source_d1r13_run)

    def test_zero_action_boundary(self):
        with self.assertRaises(ValueError):
            d1r14r4.zero_action(9)
        for step in (10, 12, 36):
            action = d1r14r4.zero_action(step)
            self.assertEqual(action.shape, (14,))
            self.assertTrue(np.array_equal(action, np.zeros(14)))

    def test_spec_matrix_has_three_times_and_exact_frozen_counts(self):
        source_results = []
        for index, context_id in enumerate(
            self.cfg["selected_source_d1r13_experiment_ids"]
        ):
            source_results.append(
                {
                    "experiment_id": context_id,
                    "spec": {
                        "experiment_id": context_id,
                        "source_d1r11_experiment_id": f"d1r11_{index}",
                        "restart_snapshot_manifest_digest": f"snapshot_{index}",
                        "horizon_steps": 35 if index < 4 else 37,
                    },
                }
            )
        ctx = SimpleNamespace(
            cfg=self.cfg,
            source_ctx=SimpleNamespace(paths=SimpleNamespace(raw=ROOT / "mock_raw")),
        )
        with mock.patch.object(d1r14r4, "_sha256", return_value="source_sha"), mock.patch.object(
            Path, "stat", return_value=SimpleNamespace(st_size=123)
        ):
            specs = d1r14r4.build_specs(ctx, source_results)
        self.assertEqual(len(specs), 200)
        self.assertEqual(sum(row["d1r14r4_role"] == "baseline" for row in specs), 8)
        probes = [row for row in specs if row["d1r14r4_role"] == "signed_probe"]
        self.assertEqual(len(probes), 192)
        self.assertEqual(
            {row["d1r14r4_issue_task_step"] for row in probes}, {14, 18, 22}
        )
        self.assertTrue(
            all(
                row["d1r14r4_cancel_task_step"]
                == row["d1r14r4_issue_task_step"] + 1
                and row["d1r14r4_zero_after_task_step"]
                == row["d1r14r4_issue_task_step"] + 2
                for row in probes
            )
        )
        self.assertEqual(
            sum(row["d1r14r4_issue_task_step"] - 10 for row in probes), 1536
        )
        self.assertEqual(
            sum(
                int(row["horizon_steps"])
                - int(row["d1r14r4_zero_after_task_step"])
                for row in probes
            ),
            3072,
        )

    def test_prefix_delegates_and_baseline_zero_reads_only_step(self):
        controller = object.__new__(d1r14r4.MixedBasisSignedExcitationController)
        controller.step = 9
        controller.d1r14r4_role = "baseline"
        parent_action = np.linspace(-0.2, 0.2, 14)
        with mock.patch.object(
            d1r14r4.d1r11.SequentialAmplitudeCodedProbeController,
            "action",
            return_value=(parent_action, {"source_trace": "exact"}),
        ) as parent:
            action, trace = controller.action({"step_index": 9})
        parent.assert_called_once()
        self.assertTrue(np.array_equal(action, parent_action))
        self.assertEqual(trace["source_trace"], "exact")
        self.assertTrue(trace["r3c3t13s24d1r14r4_delegated_prefix"])

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
            d1r14r4.d1r11.SequentialAmplitudeCodedProbeController, "action"
        ) as parent:
            action, trace = controller.action(current)
        parent.assert_not_called()
        self.assertEqual(current.reads, ["step_index"])
        self.assertTrue(np.array_equal(action, np.zeros(14)))
        self.assertTrue(trace["r3c3t13s24d1r14r4_zero_increment"])

    def test_signed_issue_and_cancel_are_fixed_and_causal(self):
        controller = object.__new__(d1r14r4.MixedBasisSignedExcitationController)
        controller.d1r14r4_role = "signed_probe"
        controller.d1r14r4_direction_index = 2
        controller.d1r14r4_sign = -1
        controller.d1r14r4_requested_coordinate = -np.asarray(
            self.cfg["controller_contract"]["requested_coordinate_matrix_columns"],
            dtype=float,
        )[:, 2]
        controller.d1r14r4_issue_step = 14
        controller.d1r14r4_cancel_step = 15
        controller.d1r14r4_zero_after_step = 16
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
        current = {"step_index": 14, "currents_a_tsc": [1.0] * 14}
        controller.step = 14
        action, trace = controller.action(current)
        self.assertTrue(np.array_equal(action, issued_action))
        self.assertEqual(trace["r3c3t13s24d1r14r4_event"], "signed_issue")
        controller._issue.assert_called_once()
        self.assertEqual(controller._issue.call_args.args[0], 2)

        current["step_index"] = 15
        controller.step = 15
        action, trace = controller.action(current)
        self.assertTrue(np.array_equal(action, cancelled_action))
        self.assertEqual(trace["r3c3t13s24d1r14r4_event"], "stored_center_cancel")
        controller._cancel.assert_called_once()
        self.assertEqual(controller._cancel.call_args.args[0], 2)

        current = {"step_index": 16}
        controller.step = 16
        action, trace = controller.action(current)
        self.assertTrue(np.array_equal(action, np.zeros(14)))
        self.assertTrue(trace["r3c3t13s24d1r14r4_zero_increment"])

    def test_mixed_issue_enforces_preregistered_action_and_projection_gates(self):
        controller = object.__new__(d1r14r4.MixedBasisSignedExcitationController)
        controller.step = 10
        controller.issue_steps = (10, 13, 15, 17)
        requested_matrix = np.asarray(
            self.cfg["controller_contract"]["requested_coordinate_matrix_columns"],
            dtype=float,
        )
        requested = -requested_matrix[:, 2]
        controller.d1r14r4_requested_coordinate = requested
        controller.requested_by_step = {15: requested}
        controller.schedule_cfg = {"dynamic_exact_search_radius": 6}
        controller.d1r14r4_controller_contract = copy.deepcopy(
            self.cfg["controller_contract"]
        )
        controller.d1r14r4_sign = -1
        controller.turns_tsc = np.full(14, 1000.0)
        controller.base = SimpleNamespace(
            max_delta_a=1.0,
            min_current=np.full(14, -1.0e6),
            max_current=np.full(14, 1.0e6),
        )
        controller.lattice_cfg = {}
        controller._freeze_fixed_basis = mock.Mock()
        basis = np.zeros((14, 4), dtype=float)
        basis[:4, :4] = np.eye(4)
        controller._basis_current = mock.Mock(return_value=(basis, basis))
        center_fields = ["0000000000"] * 14
        target_fields = ["1111111111"] * 14
        center = SimpleNamespace(
            card15_fields=center_fields,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )
        issued = SimpleNamespace(
            card15_fields=target_fields,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )
        controller.actuator = mock.Mock()
        controller.actuator.apply.side_effect = [center, issued]
        actual = requested.tolist() + [0.0] * 10
        chosen = {
            "action_norm_tsc": [0.01] * 14,
            "incremental_normalized_action_linf": 0.05,
            "total_normalized_action_abs": 0.05,
            "predicted_maximum_current_utilization": 0.38,
            "passed": True,
        }
        with mock.patch.object(
            d1r14r4.d1r11.s21,
            "_dynamic_exact_target",
            return_value=(
                target_fields,
                tuple(str(value) for value in actual),
                [1] * 14,
            ),
        ), mock.patch.object(
            d1r14r4.d1r11.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ):
            action, event = controller._issue(2, np.zeros(14), np.zeros(14))
        self.assertTrue(event["passed"])
        self.assertEqual(event["gate_revision"], "d1r14r4_fixed_mixed_action_safety_v1")
        self.assertTrue(all(event["criteria"].values()))
        self.assertTrue(event["criteria"]["requested_mixed_coordinate_exact"])
        self.assertTrue(event["criteria"]["cosine"])
        self.assertTrue(event["criteria"]["off_basis"])
        self.assertGreaterEqual(event["desired_applied_current_cosine"], 0.98)
        self.assertLessEqual(event["relative_off_basis_residual"], 0.10)
        self.assertTrue(np.array_equal(action, np.asarray(chosen["action_norm_tsc"])))

    def test_controller_source_spec_strips_labels_and_has_no_future_sequence(self):
        source = {
            "pair_id": "forbidden",
            "history_member": "forbidden",
            "partition": "forbidden",
            "d1r14r4_role": "signed_probe",
            "d1r14r4_direction_index": 1,
            "d1r14r4_direction_name": "pooled_mixed_1",
            "d1r14r4_sign": 1,
            "d1r14r4_requested_coordinate": np.asarray(
                self.cfg["controller_contract"]["requested_coordinate_matrix_columns"],
                dtype=float,
            )[:, 1].tolist(),
            "d1r14r4_issue_task_step": 14,
            "d1r14r4_cancel_task_step": 15,
            "d1r14r4_zero_after_task_step": 16,
            "d1r13_source_prefix_hash": "forbidden",
            "source_d1r13_audit_sha256": "forbidden",
            "safe": 1,
        }
        schedule = {
            "issue_task_steps": [10, 13, 15, 17],
            "cancel_task_steps": [11, 14, 16, 18],
        }
        with mock.patch.object(
            d1r14r4.d1r11.s21.s16.s9,
            "_controller_spec",
            return_value=copy.deepcopy(source),
        ):
            output = d1r14r4._controller_source_spec(source, schedule)
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
        self.assertNotIn("d1r14r4_direction_name", output)
        self.assertFalse(
            any(
                key.startswith(("d1r13_", "d1r14r4_", "source_d1r13_"))
                for key in output
            )
        )

    def test_visible_outputs_construct_backward_velocity_and_state10_origin(self):
        trajectory = _trajectory(35, direction=0, sign=1)
        scales = np.asarray([0.03, 0.03, 0.1, 0.1, 10000.0])
        values = d1r14r4._visible_outputs5(trajectory, scales)
        self.assertEqual(values.shape, (36, 5))
        self.assertTrue(np.array_equal(values[10], np.zeros(5)))
        self.assertGreater(values[11, 0], 0.0)
        self.assertGreater(values[11, 2], 0.0)

    def test_geometry_combines_r2_and_time_shifted_sign_split_branches(self):
        specs = []
        results = {}
        source_specs = []
        source_results = {}
        selected = self.cfg["selected_source_d1r13_experiment_ids"]
        for context_index, context_id in enumerate(selected):
            horizon = 35 if context_index < 4 else 37
            pair_id = f"pair_{context_index // 2}"
            baseline_id = f"{context_id}_baseline"
            baseline_spec = {
                "experiment_id": baseline_id,
                "source_d1r13_experiment_id": context_id,
                "d1r14r4_role": "baseline",
                "d1r14r4_direction_index": -1,
                "d1r14r4_sign": 0,
                "pair_id": pair_id,
                "history_member": "plus_first" if context_index % 2 == 0 else "minus_first",
                "horizon_steps": horizon,
            }
            specs.append(baseline_spec)
            results[baseline_id] = {
                "experiment_id": baseline_id,
                "trajectory": _trajectory(horizon),
                "controller_trace": [{} for _ in range(horizon)],
            }
            source_baseline_id = f"{context_id}_r2_baseline"
            source_baseline_spec = {
                "experiment_id": source_baseline_id,
                "source_d1r13_experiment_id": context_id,
                "d1r14r2_role": "baseline",
                "d1r14r2_direction_index": -1,
                "d1r14r2_sign": 0,
                "pair_id": pair_id,
                "history_member": baseline_spec["history_member"],
                "horizon_steps": horizon,
            }
            source_specs.append(source_baseline_spec)
            source_results[source_baseline_id] = {
                "experiment_id": source_baseline_id,
                "trajectory": _trajectory(horizon),
                "controller_trace": [{} for _ in range(horizon)],
            }
            for issue_step in (10, 14, 18, 22):
                for direction in range(4):
                    for sign in (1, -1):
                        experiment_id = f"{context_id}_{issue_step}_{direction}_{sign}"
                        event = {
                            "requested_coordinate": (
                                np.eye(4, dtype=float)[:, direction] * sign
                            ).tolist(),
                            "actual_signed_delta_field_kAt_tsc": (
                                np.eye(14, dtype=float)[:, direction] * sign
                            ).tolist(),
                        }
                        trace = [{} for _ in range(horizon)]
                        if issue_step == 10:
                            spec = {
                                **source_baseline_spec,
                                "experiment_id": experiment_id,
                                "d1r14r2_role": "signed_probe",
                                "d1r14r2_direction_index": direction,
                                "d1r14r2_sign": sign,
                                "d1r14r2_issue_task_step": 10,
                            }
                            trace[issue_step][
                                "r3c3t13s24d1r14r2_event_detail"
                            ] = event
                            source_specs.append(spec)
                            source_results[experiment_id] = {
                                "experiment_id": experiment_id,
                                "trajectory": _trajectory(
                                    horizon, direction, sign, issue_step
                                ),
                                "controller_trace": trace,
                            }
                        else:
                            spec = {
                                **baseline_spec,
                                "experiment_id": experiment_id,
                                "d1r14r4_role": "signed_probe",
                                "d1r14r4_direction_index": direction,
                                "d1r14r4_sign": sign,
                                "d1r14r4_issue_task_step": issue_step,
                            }
                            trace[issue_step][
                                "r3c3t13s24d1r14r4_event_detail"
                            ] = event
                            specs.append(spec)
                            results[experiment_id] = {
                                "experiment_id": experiment_id,
                                "trajectory": _trajectory(
                                    horizon, direction, sign, issue_step
                                ),
                                "controller_trace": trace,
                            }
        ctx = types.SimpleNamespace(cfg=self.cfg)
        result = d1r14r4._response_geometry(
            ctx,
            specs,
            results,
            source_r2_specs=source_specs,
            source_r2_results=source_results,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["branch_count"], 64)
        self.assertEqual(result["branch_direction_count"], 256)
        self.assertEqual(result["signal_pass_count"], 256)
        self.assertEqual(result["rank_pass_count"], 64)
        self.assertEqual(result["condition_pass_count"], 64)
        symmetry = result["issue_coordinate_and_field_symmetry"]
        self.assertEqual(symmetry["source_pair_count"], 32)
        self.assertEqual(symmetry["new_pair_count"], 96)
        self.assertEqual(symmetry["combined_pair_count"], 128)
        self.assertEqual(len(result["matched_hidden_history_rows_report_only"]), 128)
        self.assertEqual(len(result["cross_time_response_rows_report_only"]), 384)

    def test_event_gate_requires_every_frozen_criterion(self):
        event = {
            "event": "sequential_issue",
            "slot": 2,
            "task_step": 10,
            "passed": True,
            "criteria": {"finite": True, "current_utilization": True},
        }
        self.assertTrue(
            d1r14r4._event_passes(
                event, expected_name="sequential_issue", slot=2, task_step=10
            )
        )
        event["criteria"]["current_utilization"] = False
        self.assertFalse(
            d1r14r4._event_passes(
                event, expected_name="sequential_issue", slot=2, task_step=10
            )
        )

    def test_forbidden_trace_keys_and_ray_batching_are_fail_closed(self):
        trace = d1r14r4._trace_template(12, np.zeros(14))
        self.assertTrue(all(not bool(trace.get(key)) for key in d1r14r4.FORBIDDEN_TRACE_KEYS))
        source = inspect.getsource(d1r14r4.evaluate_specs)
        self.assertIn("range(0, len(pending), plan.actor_count)", source)
        self.assertIn("pending[batch_start : batch_start + plan.actor_count]", source)

    def test_resume_identity_reauthenticates_package_sources_and_specs(self):
        source = inspect.getsource(d1r14r4._assert_run_identity)
        for token in (
            "_authenticate_source(ctx)",
            "_package_fingerprint()",
            "source_d1r13_inventory_digest",
            "source_d1r11_inventory_digest",
            "source_r1a_hashes",
            "spec_digest",
            "package_digest",
        ):
            self.assertIn(token, source)
        self.assertIn("_assert_run_identity(ctx)", inspect.getsource(d1r14r4.run_real))
        self.assertIn("_assert_run_identity(ctx)", inspect.getsource(d1r14r4.postprocess))

    def test_independent_forensic_is_structurally_separate_and_r1a_authenticated(self):
        path = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r4_independent_forensics.py"
        )
        source = path.read_text(encoding="utf-8")
        self.assertNotIn(
            "from tsc_rzip_rllib.diagnostics import (\n"
            "    stage4_2r3c3t13s24d1r14r4",
            source,
        )
        self.assertIn("def _r1a_authentication", source)
        self.assertIn("--source-r1a-output", source)
        self.assertIn(
            "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_PASS_CAUSAL_MODEL_FIT_DESIGN_REQUIRED",
            source,
        )
        self.assertIn("def _r3_r2_authentication", source)
        self.assertIn("source_r2_identity_count == 72", source)
        self.assertIn("requested_mixed_coordinate_exact", inspect.getsource(d1r14r4.MixedBasisSignedExcitationController._issue))

    def test_launchers_pin_server_venv_capacity_and_exact_pid_stop(self):
        shell_common = (
            ROOT / "scripts/stage4_2r3c3t13s24d1r14r4_shell_common.sh"
        ).read_text(encoding="utf-8")
        common = (ROOT / "run_stage4_2r3c3t13s24d1r14r4_common.sh").read_text(
            encoding="utf-8"
        )
        stop = (ROOT / "run_stop_stage4_2r3c3t13s24d1r14r4_now.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("/tsc_simulation/venv_simu/bin/python", shell_common)
        self.assertIn('WORKERS:-96', shell_common)
        self.assertIn('WORKERS}" == 96', shell_common)
        self.assertIn("--source-r1a-output", common)
        self.assertIn("--source-r2-run", common)
        self.assertIn("--source-r3-initial-output", common)
        self.assertIn("--source-r3-corrected-output", common)
        self.assertIn("200 fresh TSC", common)
        self.assertIn('kill -TERM "${PID}"', stop)
        self.assertNotIn("pkill", stop)
        self.assertNotIn("ray stop --force", stop)


if __name__ == "__main__":
    unittest.main()
