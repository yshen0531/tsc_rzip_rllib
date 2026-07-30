from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from scripts import stage4_2r3c3_server_postprocess as postprocess
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3_restart_task_clock_local_response_identification as r3c,
)


def _source_spec(*, target_id: str, delay: int, slew: float) -> dict:
    spec = {
        "experiment_id": f"source-{target_id}-{delay}-{slew}",
        "target_id": target_id,
        "action_delay_steps": delay,
        "controller_action_delay_steps": delay,
        "slew_scale": slew,
        "controller_slew_scale_estimate": slew,
        "controller_gain_estimate_by_mode": [1.0] * r3c.N_MODES,
        "actuator_gain_by_mode": [1.0] * r3c.N_MODES,
        "actuator_bias_by_mode": [0.0] * r3c.N_MODES,
        "terminal_controller_scale": 0.5,
        "terminal_position_measurement_gain": 1.25,
        "terminal_velocity_measurement_gain": 1.5,
        "terminal_ip_measurement_gain": 1.0,
        "terminal_controller_model_scale": 1.0,
    }
    if delay:
        spec["terminal_model_phase_cap_step"] = 28
        spec["r15_probe_delta_by_issue_step"] = {}
    else:
        spec["terminal_template_step"] = 28
    return spec


def _manifold(experiment_id: str, offset: float = 0.0) -> dict:
    values = [
        [
            0.70 + offset + 0.001 * step,
            -0.01 + offset,
            30000.0 + 10.0 * step,
        ]
        for step in range(21)
    ]
    return {
        "schema_version": 1,
        "contract": "authenticated_r17_actual_closed_loop_visible_RZI_v1",
        "source_experiment_id": experiment_id,
        "source_raw_sha256": r3c._canonical_digest(
            {"experiment_id": experiment_id}
        ),
        "source_raw_size_bytes": 1234,
        "visible_fields": ["R", "Z", "Ip"],
        "phase_min": 0,
        "phase_max": 20,
        "phase_count": 21,
        "values": values,
        "values_digest": r3c._canonical_digest(values),
        "source_actions_included": False,
        "source_coil_currents_included": False,
        "source_wire_currents_included": False,
        "current_run_future_included": False,
    }


class Stage42R3C3DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(r3c.__file__).resolve().parents[2]
        cls.config = json.loads(
            (
                cls.root
                / "configs"
                / "stage4_2r3c3_restart_task_clock_local_response_identification_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_identity_timing_and_identification_scope_are_frozen(
        self,
    ) -> None:
        r3c.validate_config(self.config)
        self.assertEqual(r3c.STAGE, "Stage4.2R3c3")
        self.assertEqual(
            r3c.CONTROLLER_REVISION,
            "restart_task_clock_local_response_probe_v42r3c3",
        )
        self.assertEqual(
            r3c.PACKAGE_REVISION,
            "r42r3c3_restart_task_clock_local_response_identification_v1",
        )
        timing = self.config["formal_timing_contract"]
        self.assertEqual(timing["normal"]["arrival_deadline_step"], 25)
        self.assertEqual(timing["normal"]["hold_through_step"], 35)
        self.assertEqual(timing["weak"]["arrival_deadline_step"], 27)
        self.assertEqual(timing["weak"]["hold_through_step"], 37)
        self.assertFalse(timing["arrival_deadline_expansion_allowed"])
        probe = self.config["identification_probe"]
        self.assertEqual(
            probe["baseline_controller"],
            r3c.r3c1.CONTROLLER_REVISION,
        )
        self.assertEqual(
            probe["physical_mode_amplitude"], [0.0075, 0.0075, 0.0]
        )
        self.assertEqual(len(probe["basis"]), 4)
        self.assertEqual(probe["probe_signs"], [-1, 1])
        self.assertFalse(probe["formal_tracking_pass_required"])
        self.assertFalse(
            probe["probe_trajectories_allowed_in_expert_dataset"]
        )
        self.assertEqual(
            self.config["control_matrix"]["expected_rollouts"], 256
        )
        self.assertTrue(self.config["development_set_only"])
        self.assertFalse(self.config["bc_dagger_or_rl_allowed"])

    def test_r3c1_and_r3c2_evidence_hashes_are_exact(self) -> None:
        source = self.config["source_requirements"]
        self.assertEqual(
            source["required_stage4_2r3c1_run_inventory_digest"],
            "5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f",
        )
        self.assertEqual(
            source["required_stage4_2r3c1_formal_pass_count"], 16
        )
        self.assertEqual(
            source["required_stage4_2r3c2_run_inventory_digest"],
            "2119d2edad615dbb9594ad4332b758a9cf7ffc2e62b988650c41297aace8cff2",
        )
        self.assertEqual(
            source["required_stage4_2r3c2_raw_forensics_sha256"],
            "644da85280e03015732bb63deb1205bf5fcafeabc53b0f8a9e606565a27efbb2",
        )
        self.assertEqual(
            source["required_stage4_2r3c2_formal_pass_count"], 12
        )
        self.assertEqual(
            source["required_stage4_2r3c2_formal_failure_count"], 20
        )

    def test_phase_selection_uses_only_visible_rzi_and_earliest_tie(
        self,
    ) -> None:
        reference = np.asarray(
            [[float(step), -float(step), 100.0 * step] for step in range(35)]
        )
        selected = r3c.select_visible_reference_phase(
            reference,
            [12.1, -12.1, 1210.0],
            candidate_min_phase=0,
            candidate_max_phase=20,
            scales=[1.0, 1.0, 100.0],
        )
        self.assertEqual(selected["selected_phase"], 12)
        self.assertFalse(selected["hidden_wire_used"])
        self.assertFalse(selected["source_action_used"])
        tied = r3c.select_visible_reference_phase(
            np.zeros((35, 3)),
            [0.0, 0.0, 0.0],
            candidate_min_phase=0,
            candidate_max_phase=20,
            scales=[0.03, 0.03, 2000.0],
        )
        self.assertEqual(tied["selected_phase"], 0)

    def test_step_zero_velocity_is_zero_then_uses_current_run_only(
        self,
    ) -> None:
        target = np.asarray([0.70, -0.01, 30000.0])
        first = [
            {"step_index": 0, "R": 0.705, "Z": -0.012, "Ip": 30125.0}
        ]
        np.testing.assert_allclose(
            r3c._fresh_task_terminal_measurement(first, target, 0.01),
            np.asarray([0.005, -0.002, 0.0, 0.0, 125.0]),
            rtol=0.0,
            atol=1.0e-15,
        )
        second = [
            *first,
            {"step_index": 1, "R": 0.706, "Z": -0.010, "Ip": 30050.0},
        ]
        np.testing.assert_array_equal(
            r3c._fresh_task_terminal_measurement(second, target, 0.01),
            r3c.r2.r9._terminal_measurement(second, target, 0.01),
        )

    def test_probe_schedule_is_task_clock_relative_and_zero_net(
        self,
    ) -> None:
        for basis in self.config["identification_probe"]["basis"]:
            for delay in (0, 2):
                for sign in (-1, 1):
                    schedule = r3c._probe_schedule(
                        first_effect_state=basis["first_effect_state"],
                        actual_delay=delay,
                        basis=basis,
                        sign=sign,
                        amplitude_by_mode=[0.0075, 0.0075, 0.0],
                    )
                    self.assertEqual(len(schedule), 4)
                    self.assertEqual(
                        min(schedule) + delay + 1,
                        basis["first_effect_state"],
                    )
                    np.testing.assert_array_equal(
                        np.sum(np.stack(list(schedule.values())), axis=0),
                        np.zeros(r3c.N_MODES),
                    )
                    for value in schedule.values():
                        self.assertEqual(np.count_nonzero(value), 1)
                        self.assertAlmostEqual(
                            abs(value[basis["mode"]]), 0.0075
                        )

    def test_controller_spec_removes_all_experiment_identity(self) -> None:
        spec = {
            "pair_id": "pair",
            "history_member": "plus_first",
            "state_generation_experiment_id": "state",
            "baseline_experiment_id": "baseline",
            "restart_snapshot_dir": "/snapshot",
            "restart_snapshot_manifest_digest": "digest",
            "experiment_id": "control",
            "environment_variant": "env",
            "kind": "kind",
            "phase": "phase",
            "category": "category",
            "target_id": "nominal",
            "action_delay_steps": 2,
        }
        sanitized = r3c._controller_spec(spec)
        self.assertFalse(
            r3c._FORBIDDEN_CONTROLLER_SPEC_KEYS.intersection(sanitized)
        )
        self.assertEqual(sanitized["target_id"], "nominal")

    def test_control_grid_is_exact_256_and_baseline_authenticated(
        self,
    ) -> None:
        sources = {}
        manifolds = {}
        baseline_ids = {}
        for target in ("nominal", "RZ_p10_m10"):
            for delay, slew in ((0, 1.0), (2, 0.9)):
                key = (target, delay, slew)
                experiment_id = f"source-{target}-{delay}-{slew}"
                sources[key] = {
                    "experiment_id": experiment_id,
                    "spec": _source_spec(
                        target_id=target, delay=delay, slew=slew
                    ),
                }
                manifolds[key] = _manifold(experiment_id)
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            snapshot = Path(temp)
            selected = []
            for pair_index in range(4):
                pair_id = f"pair-{pair_index}"
                pair = {"pair_id": pair_id}
                for member in ("plus_first", "minus_first"):
                    pair[f"{member}_state"] = {
                        "experiment_id": f"state-{pair_id}-{member}",
                        "snapshot_dir": str(snapshot),
                        "snapshot_manifest_digest": f"digest-{member}",
                    }
                    for target in ("nominal", "RZ_p10_m10"):
                        for delay, slew in ((0, 1.0), (2, 0.9)):
                            baseline_ids[
                                (pair_id, member, target, delay, slew)
                            ] = (
                                f"baseline-{pair_id}-{member}-"
                                f"{target}-{delay}-{slew}"
                            )
                selected.append(pair)
            ctx = SimpleNamespace(cfg=copy.deepcopy(self.config))
            with mock.patch.object(
                r3c, "_source_controller_cases", return_value=sources
            ), mock.patch.object(
                r3c,
                "_visible_reference_manifolds",
                return_value=manifolds,
            ), mock.patch.object(
                r3c,
                "_r3c1_baseline_result_ids",
                return_value=baseline_ids,
            ):
                specs = r3c.build_control_specs(ctx, selected)
        self.assertEqual(len(specs), 256)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 256)
        self.assertEqual(
            len({row["baseline_experiment_id"] for row in specs}), 32
        )
        self.assertTrue(all(row["identification_only"] for row in specs))
        self.assertTrue(
            all(
                not row["probe_trajectory_allowed_in_expert_dataset"]
                for row in specs
            )
        )
        self.assertEqual(
            {
                (
                    row["r3c3_probe_id"],
                    row["r3c3_probe_sign"],
                )
                for row in specs
            },
            {
                (basis["probe_id"], sign)
                for basis in self.config["identification_probe"]["basis"]
                for sign in (-1, 1)
            },
        )

    def test_probe_action_overlay_is_bounded_and_exact(self) -> None:
        controller = object.__new__(
            r3c.RestartTaskClockLocalResponseProbeController
        )
        controller.step = 2
        controller.probe_schedule = {
            2: np.asarray([0.0075, 0.0, 0.0])
        }
        controller.probe_id = "early_mode0"
        controller.probe_mode = 0
        controller.probe_sign = 1
        controller.probe_first_effect_state = 5
        controller.probe_amplitude = 0.0075
        controller.base = SimpleNamespace(
            stub=SimpleNamespace(
                cfg={
                    "trajectory": {
                        "coefficient_lower": [-1.0, -1.0, -1.0],
                        "coefficient_upper": [1.0, 1.0, 1.0],
                    }
                }
            )
        )

        def fake_solver(*args, **kwargs):
            return {
                "first_correction": np.asarray([0.1, 0.2, 0.3]),
                "sequence_correction": np.asarray([[0.1, 0.2, 0.3]]),
                "effect_step": 5,
                "solver_success": True,
            }

        def fake_parent(self, current_state):
            solved = r3c.r2.r3.solve_delay_aware_physical_correction(
                nominal_physical_coefficients=np.zeros((35, 3)),
                current_step=2,
            )
            return np.zeros(r3c.N_COILS), {
                "solver_success": solved["solver_success"],
                "measurement_max_state_index_used": 2,
                "future_measurement_used": False,
            }

        with mock.patch.object(
            r3c.r2.r3,
            "solve_delay_aware_physical_correction",
            side_effect=fake_solver,
        ), mock.patch.object(
            r3c.r3c1.AuthenticatedVisibleManifoldPhaseTaskController,
            "action",
            new=fake_parent,
        ):
            _, trace = controller.action({"step_index": 2})
        self.assertTrue(trace["r3c3_probe_issued"])
        np.testing.assert_allclose(
            trace["r3c3_probe_requested_delta"],
            [0.0075, 0.0, 0.0],
            rtol=0.0,
            atol=1.0e-15,
        )
        np.testing.assert_allclose(
            trace["r3c3_probe_applied_desired_delta"],
            [0.0075, 0.0, 0.0],
            rtol=0.0,
            atol=1.0e-15,
        )
        self.assertFalse(trace["hidden_wire_used"])
        self.assertFalse(trace["source_result_used"])

    def test_trace_gate_requires_exact_four_probe_zero_net(self) -> None:
        schedule = {
            2: [0.0075, 0.0, 0.0],
            3: [0.0075, 0.0, 0.0],
            5: [-0.0075, 0.0, 0.0],
            6: [-0.0075, 0.0, 0.0],
        }
        trace = []
        for step in range(8):
            requested = schedule.get(step, [0.0, 0.0, 0.0])
            trace.append(
                {
                    "task_step": step,
                    "r3c3_probe_requested_delta": requested,
                    "r3c3_probe_applied_desired_delta": requested,
                    "r3c3_probe_issued": step in schedule,
                    "baseline_controller_revision": (
                        r3c.r3c1.CONTROLLER_REVISION
                    ),
                    "r3c3_identification_only": True,
                    "r3c3_probe_id": "early_mode0",
                    "r3c3_probe_mode": 0,
                    "r3c3_probe_sign": 1,
                    "pair_or_history_label_used": False,
                    "source_result_used": False,
                    "solver_success": True,
                }
            )
        result = {
            "spec": {
                "action_delay_steps": 2,
                "r3c3_probe_first_effect_state": 5,
                "r3c3_probe_id": "early_mode0",
                "r3c3_probe_mode": 0,
                "r3c3_probe_sign": 1,
                "r3c3_probe_delta_by_task_issue_step": {
                    str(key): value for key, value in schedule.items()
                },
            },
            "controller_trace": trace,
        }
        with mock.patch.object(
            r3c.r3c1,
            "_phase_trace_valid",
            return_value={"passed": True},
        ):
            validated = r3c._phase_trace_valid(result)
        self.assertTrue(validated["passed"])
        self.assertTrue(validated["probe_zero_net"])
        self.assertTrue(validated["probe_applied_exact"])
        broken = copy.deepcopy(result)
        broken["controller_trace"][6][
            "r3c3_probe_applied_desired_delta"
        ] = [-0.006, 0.0, 0.0]
        with mock.patch.object(
            r3c.r3c1,
            "_phase_trace_valid",
            return_value={"passed": True},
        ):
            self.assertFalse(r3c._phase_trace_valid(broken)["passed"])

    def test_response_summary_gates_signed_and_hidden_pairs(self) -> None:
        horizon = 20

        def trajectory(response: np.ndarray) -> list[dict]:
            return [
                {
                    "R": float(0.7 + response[step, 0]),
                    "Z": float(-0.01 + response[step, 1]),
                    "Ip": float(30000.0 + response[step, 2]),
                    "currents_a_tsc": [0.0] * r3c.N_COILS,
                    "wire_currents_a": [0.0] * r3c.N_WIRES,
                }
                for step in range(horizon + 1)
            ]

        probe_shapes = {
            "early_mode0": (5, 0),
            "early_mode1": (6, 1),
            "deadline_mode0": (17, 0),
            "deadline_mode1": (18, 1),
        }
        results = []
        baselines = {}
        for history_member in ("plus_first", "minus_first"):
            baseline_id = f"baseline-{history_member}"
            baselines[baseline_id] = {
                "trajectory": trajectory(
                    np.zeros((horizon + 1, 3), dtype=float)
                )
            }
            for probe_id, (effect_step, axis) in probe_shapes.items():
                first_effect = 5 if probe_id.startswith("early") else 17
                response = np.zeros((horizon + 1, 3), dtype=float)
                response[effect_step:, axis] = 1.0e-4
                for sign in (-1, 1):
                    experiment_id = (
                        f"{history_member}-{probe_id}-{sign}"
                    )
                    results.append(
                        {
                            "experiment_id": experiment_id,
                            "success": True,
                            "trajectory": trajectory(sign * response),
                            "spec": {
                                "pair_id": "pair",
                                "history_member": history_member,
                                "state_generation_experiment_id": (
                                    f"state-{history_member}"
                                ),
                                "target_id": "nominal",
                                "action_delay_steps": 0,
                                "slew_scale": 1.0,
                                "horizon_steps": horizon,
                                "r3c3_probe_id": probe_id,
                                "r3c3_probe_mode": axis,
                                "r3c3_probe_sign": sign,
                                "r3c3_probe_first_effect_state": (
                                    first_effect
                                ),
                                "baseline_experiment_id": baseline_id,
                            },
                        }
                    )

        def control_row(_ctx, result, _state):
            spec = result["spec"]
            return {
                "experiment_id": result["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "target_id": spec["target_id"],
                "actual_delay_steps": spec["action_delay_steps"],
                "actual_slew_scale": spec["slew_scale"],
                "environment_success": True,
                "fresh_controller": True,
                "fresh_tsc_process": True,
                "initial_restart_exact": True,
                "controller_trace_causal": True,
                "formal_contract_pass": True,
                "formal_minimum_signed_margin": 1.0,
                "failure_class": "",
                "passed": True,
            }

        phase = {
            "passed": True,
            "probe_trace_exact": True,
            "probe_issued_count": 4,
            "probe_applied_exact": True,
            "probe_zero_net": True,
            "probe_first_effect_exact": True,
            "solver_failure_count": 0,
            "pair_or_history_label_trace_count": 0,
            "source_result_trace_count": 0,
            "hidden_wire_trace_count": 0,
            "source_action_trace_count": 0,
            "source_coil_current_trace_count": 0,
            "source_wire_current_trace_count": 0,
            "current_run_future_trace_count": 0,
        }
        cfg = copy.deepcopy(self.config)
        cfg["control_matrix"]["expected_rollouts"] = 16
        cfg["control_matrix"]["expected_baseline_contexts"] = 2
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            control_dir = Path(temp)
            ctx = SimpleNamespace(
                cfg=cfg,
                paths=SimpleNamespace(control=control_dir),
                source_r3c1_run=control_dir,
                source_ctx=SimpleNamespace(r1_ctx=object()),
            )
            r13 = SimpleNamespace(
                r12_ctx=SimpleNamespace(
                    r11_ctx=SimpleNamespace(
                        r10_ctx=SimpleNamespace(
                            r9_ctx=SimpleNamespace(
                                r8_ctx=SimpleNamespace(
                                    r7_ctx=SimpleNamespace(
                                        r6_ctx=SimpleNamespace(
                                            r5_ctx=SimpleNamespace(
                                                r4_ctx=SimpleNamespace(
                                                    r3_ctx=SimpleNamespace(
                                                        base34=SimpleNamespace(
                                                            env_cfg={
                                                                "dt_ms": 10
                                                            }
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
            with mock.patch.object(
                r3c.r1, "_r13_ctx", return_value=r13
            ), mock.patch.object(
                r3c.r3b,
                "_selected_state_map",
                return_value={
                    "state-plus_first": {},
                    "state-minus_first": {},
                },
            ), mock.patch.object(
                r3c.r3b, "_control_row", side_effect=control_row
            ), mock.patch.object(
                r3c, "_phase_trace_valid", return_value=phase
            ), mock.patch.object(
                r3c,
                "_formal_metrics",
                return_value={
                    "max_current_utilization": 0.2,
                    "stage3_4_target_tracking_pass": True,
                    "stage3_4_tracking_minimum_signed_margin": 1.0,
                },
            ), mock.patch.object(
                r3c,
                "read_json_gz",
                side_effect=lambda path: baselines[
                    path.name.removesuffix(".json.gz")
                ],
            ):
                summary = r3c.summarize_control(ctx, results, [{}])
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["execution_pass_count"], 16)
        self.assertEqual(summary["central_symmetry_pass_count"], 8)
        self.assertEqual(
            summary["matched_hidden_history_pass_count"], 4
        )
        self.assertEqual(summary["condition_number_pass_count"], 2)
        self.assertAlmostEqual(
            summary["maximum_selected_velocity_condition_number"], 1.0
        )

    def test_resume_requires_exact_spec_and_package(self) -> None:
        spec = {"experiment_id": "x"}
        result = {
            "completed": True,
            "stage": r3c.STAGE,
            "controller_revision": r3c.CONTROLLER_REVISION,
            "experiment_id": "x",
            "spec": spec,
            "success": True,
            "trajectory": [],
            "controller_trace": [],
        }
        path = self.root / "PACKAGE_MANIFEST.json"
        with mock.patch.object(r3c, "read_json_gz", return_value=result):
            self.assertTrue(r3c._result_complete(path, spec))
            self.assertFalse(
                r3c._result_complete(path, {"experiment_id": "changed"})
            )
        ctx = SimpleNamespace()
        fingerprint = {"digest": "same"}
        self.assertIsNone(
            r3c._semantics_preserving_resume_compatibility(
                ctx, fingerprint, copy.deepcopy(fingerprint)
            )
        )
        with self.assertRaises(ValueError):
            r3c._semantics_preserving_resume_compatibility(
                ctx, fingerprint, {"digest": "changed"}
            )

    def test_postprocess_requires_exact_runtime_package(self) -> None:
        runtime = {"digest": "runtime", "files": []}
        self.assertEqual(
            postprocess._runtime_package_fingerprint(
                {"deployed_package_fingerprint": runtime}
            ),
            runtime,
        )
        with self.assertRaises(ValueError):
            postprocess._runtime_package_fingerprint({})
        self.assertTrue(
            postprocess._audit_package_compatibility(
                self.root, runtime, copy.deepcopy(runtime)
            )["passed"]
        )
        self.assertFalse(
            postprocess._audit_package_compatibility(
                self.root, runtime, {"digest": "changed"}
            )["passed"]
        )

    def test_self_test_and_launchers(self) -> None:
        result = r3c.self_test()
        self.assertTrue(result["passed"])
        self.assertTrue(result["identification_only"])
        self.assertFalse(
            result["probe_trajectories_allowed_in_expert_dataset"]
        )
        for path in (
            self.root
            / "run_stage4_2r3c3_restart_task_clock_local_response_identification_native.sh",
            self.root / "run_stop_stage4_2r3c3_now.sh",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("ray stop --force", text)
            self.assertNotIn("pkill", text)


if __name__ == "__main__":
    unittest.main()
