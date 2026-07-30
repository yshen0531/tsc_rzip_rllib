from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c1_authenticated_visible_manifold_phase_mpc as r3c,
)


def _source_spec(
    *,
    target_id: str,
    delay: int,
    slew: float,
) -> dict:
    return {
        "experiment_id": f"source-{target_id}-{delay}-{slew}",
        "target_id": target_id,
        "action_delay_steps": delay,
        "controller_action_delay_steps": delay,
        "slew_scale": slew,
        "controller_slew_scale_estimate": slew,
        "controller_gain_estimate_by_mode": [1.0] * r3c.N_MODES,
        "actuator_gain_by_mode": [1.0] * r3c.N_MODES,
        "actuator_bias_by_mode": [0.0] * r3c.N_MODES,
    }


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


class Stage42R3C1DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(r3c.__file__).resolve().parents[2]
        cls.config = json.loads(
            (
                cls.root
                / "configs"
                / "stage4_2r3c1_authenticated_visible_manifold_phase_mpc_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_config_preserves_formal_timing_and_development_scope(
        self,
    ) -> None:
        r3c.validate_config(self.config)
        self.assertEqual(
            self.config["formal_timing_contract"]["normal"][
                "arrival_deadline_step"
            ],
            25,
        )
        self.assertEqual(
            self.config["formal_timing_contract"]["weak"][
                "arrival_deadline_step"
            ],
            27,
        )
        self.assertFalse(
            self.config["formal_timing_contract"][
                "arrival_deadline_expansion_allowed"
            ]
        )
        self.assertTrue(self.config["development_set_only"])
        self.assertFalse(
            self.config["independent_hidden_history_confirmation"]
        )
        self.assertFalse(self.config["bc_dagger_or_rl_allowed"])
        phase = self.config["phase_alignment"]
        self.assertEqual(
            phase["reference_manifold"],
            "authenticated_r17_actual_closed_loop_visible_RZI",
        )
        self.assertFalse(phase["source_actions_allowed"])
        self.assertFalse(phase["source_coil_currents_allowed"])
        self.assertFalse(phase["source_wire_currents_allowed"])

    def test_phase_selection_uses_only_visible_rzi_and_earliest_tie(
        self,
    ) -> None:
        nominal = np.asarray(
            [[float(step), -float(step), 100.0 * step] for step in range(35)]
        )
        selected = r3c.select_visible_reference_phase(
            nominal,
            [12.1, -12.1, 1210.0],
            candidate_min_phase=0,
            candidate_max_phase=20,
            scales=[1.0, 1.0, 100.0],
        )
        self.assertEqual(selected["selected_phase"], 12)
        self.assertEqual(selected["visible_fields"], ["R", "Z", "Ip"])
        self.assertFalse(selected["hidden_wire_used"])
        self.assertFalse(selected["source_action_used"])
        self.assertFalse(selected["source_coil_current_used"])
        self.assertFalse(selected["source_wire_current_used"])
        self.assertFalse(selected["current_run_future_used"])

        tied = r3c.select_visible_reference_phase(
            np.zeros((35, 3)),
            [0.0, 0.0, 0.0],
            candidate_min_phase=0,
            candidate_max_phase=20,
            scales=[0.03, 0.03, 2000.0],
        )
        self.assertEqual(tied["selected_phase"], 0)

    def test_invalid_phase_selection_inputs_fail_closed(self) -> None:
        nominal = np.zeros((35, 3))
        with self.assertRaises(ValueError):
            r3c.select_visible_reference_phase(
                nominal,
                [0.0, 0.0, 0.0],
                candidate_min_phase=0,
                candidate_max_phase=35,
                scales=[0.03, 0.03, 2000.0],
            )
        with self.assertRaises(ValueError):
            r3c.select_visible_reference_phase(
                nominal,
                [0.0, 0.0, 0.0],
                candidate_min_phase=0,
                candidate_max_phase=20,
                scales=[0.03, 0.0, 2000.0],
            )

    def test_control_spec_grid_is_exactly_32_and_keeps_hidden_state_out(
        self,
    ) -> None:
        sources = {
            (target, delay, slew): {
                "experiment_id": f"source-{target}-{delay}-{slew}",
                "controller_revision": "frozen-r17",
                "spec": _source_spec(
                    target_id=target,
                    delay=delay,
                    slew=slew,
                ),
            }
            for target in ("nominal", "RZ_p10_m10")
            for delay, slew in ((0, 1.0), (2, 0.9))
        }
        selected = []
        manifolds = {
            key: _manifold(
                str(source["experiment_id"]),
                offset=0.001 * index,
            )
            for index, (key, source) in enumerate(sorted(sources.items()))
        }
        for pair_index, pair_id in enumerate(
            self.config["source_requirements"][
                "required_selected_pair_ids"
            ]
        ):
            selected.append(
                {
                    "pair_id": pair_id,
                    "plus_first_state": {
                        "experiment_id": f"state-{pair_index}-plus",
                        "snapshot_dir": f"/synthetic/{pair_index}/plus",
                        "snapshot_manifest_digest": f"digest-{pair_index}-plus",
                    },
                    "minus_first_state": {
                        "experiment_id": f"state-{pair_index}-minus",
                        "snapshot_dir": f"/synthetic/{pair_index}/minus",
                        "snapshot_manifest_digest": f"digest-{pair_index}-minus",
                    },
                }
            )
        ctx = SimpleNamespace(cfg=copy.deepcopy(self.config))
        with mock.patch.object(
            r3c, "_source_controller_cases", return_value=sources
        ), mock.patch.object(
            r3c,
            "_visible_reference_manifolds",
            return_value=manifolds,
        ), mock.patch.object(
            r3c.r3b, "_forbidden_future_paths", return_value=[]
        ):
            specs = r3c.build_control_specs(ctx, selected)
        self.assertEqual(len(specs), 32)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 32)
        self.assertTrue(
            all(
                row["controller_history_initialization"]
                == "current_visible_state_only_at_task_step_zero"
                and not row["hidden_wire_current_available_to_controller"]
                and row["future_action_count"] == 0
                and row["future_measurement_count"] == 0
                and row["task_clock_starts_at_zero"]
                and not row["source_action_available_to_controller"]
                and not row["source_coil_current_available_to_controller"]
                and not row["source_wire_current_available_to_controller"]
                and row["visible_reference_manifold"]["phase_count"] == 21
                for row in specs
            )
        )

    def test_selected_snapshot_uses_r3b_validated_success_contract(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "success": True,
                "snapshot_dir": tmp,
                "snapshot_manifest_digest": "authenticated-digest",
            }
            self.assertNotIn("snapshot_pass", state)
            self.assertTrue(
                r3c._selected_snapshot_state_is_valid(state)
            )
            self.assertFalse(
                r3c._selected_snapshot_state_is_valid(
                    {**state, "success": False}
                )
            )

    def test_trace_validator_separates_task_and_reference_clocks(
        self,
    ) -> None:
        digest = "visible-manifold-digest"
        trace = [
            {
                "task_step": step,
                "reference_phase": 12 + step,
                "model_phase": min(12 + step, 34),
                "reference_phase_start": 12,
                "controller_phase": "phase_aligned_main_control",
                "visible_reference_manifold_digest": digest,
                "source_action_used": False,
                "source_coil_current_used": False,
                "source_wire_current_used": False,
                "current_run_future_used": False,
                "hidden_wire_used": False,
            }
            for step in range(35)
        ]
        result = r3c._phase_trace_valid(
            {
                "controller_trace": trace,
                "spec": {
                    "terminal_model_phase_cap_step": 28,
                    "terminal_template_step": 28,
                    "visible_reference_manifold_digest": digest,
                },
            }
        )
        self.assertEqual(result["reference_phase_start"], 12)
        self.assertTrue(result["task_clock_starts_at_zero"])
        self.assertTrue(result["reference_phase_monotonic"])
        self.assertTrue(result["reference_phase_exact"])
        self.assertTrue(result["model_phase_exact"])
        self.assertTrue(result["visible_reference_manifold_exact"])
        self.assertEqual(result["source_action_trace_count"], 0)

    def test_resume_requires_exact_stage_revision_id_and_spec(self) -> None:
        expected = {"experiment_id": "r3c-case", "value": 7}
        valid = {
            "completed": True,
            "stage": r3c.STAGE,
            "controller_revision": r3c.CONTROLLER_REVISION,
            "experiment_id": "r3c-case",
            "spec": copy.deepcopy(expected),
            "success": False,
            "trajectory": [],
            "controller_trace": [],
        }
        with mock.patch.object(
            r3c, "read_json_gz", return_value=valid
        ), mock.patch.object(Path, "is_file", return_value=True):
            self.assertTrue(
                r3c._result_complete(
                    Path("/synthetic/raw.json.gz"), expected
                )
            )
            incompatible = copy.deepcopy(valid)
            incompatible["controller_revision"] = "stale-controller"
            with mock.patch.object(
                r3c, "read_json_gz", return_value=incompatible
            ):
                self.assertFalse(
                    r3c._result_complete(
                        Path("/synthetic/raw.json.gz"), expected
                    )
                )

    def test_pair_classification_does_not_overclaim_masked_failures(
        self,
    ) -> None:
        self.assertEqual(
            r3c.classify_pair_assessment(True, True),
            "both_pass_development_pair_success",
        )
        self.assertEqual(
            r3c.classify_pair_assessment(True, False),
            "history_sensitive_pass_fail_outcome",
        )
        self.assertEqual(
            r3c.classify_pair_assessment(False, False),
            "masked_by_common_mode_both_fail",
        )

    def test_offline_command_cannot_start_real_control(self) -> None:
        state_path = Path("/synthetic/stage4_2r3c1_state.json")
        ctx = SimpleNamespace(paths=SimpleNamespace(state=state_path))
        writes = {}

        def write(_path, value):
            writes.update(copy.deepcopy(value))

        with mock.patch.object(
            r3c, "prepare", return_value=(["pair"], ["spec"])
        ), mock.patch.object(
            r3c,
            "run_offline_phase_alignment_audit",
            return_value={"passed": True, "real_tsc_executed": False},
        ), mock.patch.object(
            r3c,
            "read_json",
            return_value={
                "finished": False,
                "primary_pass": False,
                "phase_status": "prepared",
                "stop_reason": "",
            },
        ), mock.patch.object(
            r3c, "atomic_write_json", side_effect=write
        ), mock.patch.object(
            r3c, "_evaluate_control"
        ) as evaluate:
            result = r3c.execute(
                ctx,
                command="offline",
                backend="ray",
                resume=False,
            )
        evaluate.assert_not_called()
        self.assertFalse(result["real_tsc_executed"])
        self.assertFalse(result["finished"])
        self.assertEqual(writes["phase_status"], "offline_gate_complete")

    def test_self_test_covers_scope_and_hidden_wire_exclusion(self) -> None:
        result = r3c.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_phase"], 12)
        self.assertEqual(result["earliest_tie_phase"], 0)
        self.assertFalse(result["hidden_wire_used"])
        self.assertTrue(result["development_set_only"])
        self.assertFalse(result["bc_dagger_or_rl_allowed"])


class Stage42R3C1ControllerInitializationTests(unittest.TestCase):
    def _controller(
        self,
        *,
        visible_phase: int,
        transition_step: int | None,
        wire_value: float,
    ) -> tuple[r3c.AuthenticatedVisibleManifoldPhaseTaskController, list[np.ndarray]]:
        calls: list[np.ndarray] = []
        nominal_y = np.asarray(
            [
                [0.70 + 0.001 * step, -0.01, 30000.0 + 10.0 * step]
                for step in range(35)
            ],
            dtype=float,
        )
        nominal_physical = np.asarray(
            [
                [0.01 * step, 0.02 * step, -0.01 * step]
                for step in range(35)
            ],
            dtype=float,
        )
        base = SimpleNamespace(
            robust_cfg={
                "controller_upgrade": {
                    "delay_aware": {
                        "prime_action_queue_with_nominal": True
                    }
                }
            }
        )

        def nominal_plan(
            nominal: np.ndarray,
            _currents: np.ndarray,
            _gain: np.ndarray,
            _slew: float,
            _enabled: bool,
        ) -> tuple[np.ndarray, dict]:
            calls.append(np.asarray(nominal, dtype=float).copy())
            return np.asarray(nominal, dtype=float).copy(), {}

        base._nominal_command_plan = nominal_plan
        initial = {
            "step_index": 0,
            "R": float(nominal_y[visible_phase, 0]),
            "Z": float(nominal_y[visible_phase, 1]),
            "Ip": float(nominal_y[visible_phase, 2]),
            "currents_a_tsc": [0.0] * r3c.N_COILS,
            "wire_currents_a": [wire_value] * r3c.N_WIRES,
        }
        phase_cfg = {
            "candidate_min_phase": 0,
            "candidate_max_phase": 20,
            "R_scale_m": 0.03,
            "Z_scale_m": 0.03,
            "Ip_scale_A": 2000.0,
        }

        def fake_parent_init(
            controller,
            base_worker,
            bundle,
            source_spec,
            initial_state,
        ):
            controller.base = base_worker
            controller.bundle = bundle
            controller.spec = copy.deepcopy(source_spec)
            # Deliberately move the controller's ideal nominal R away from
            # the authenticated visible table.  Phase selection must use the
            # table in the spec, not this ideal nominal trajectory.
            controller.nominal_y = nominal_y.copy()
            controller.nominal_y[:, 0] += 0.5
            controller.nominal_physical = nominal_physical.copy()
            controller.nominal_velocity = np.zeros((35, 2))
            controller.nominal_feature = np.zeros(35 * 5)
            controller.step = 0
            controller.delay = 2
            controller.actual_delay = 2
            controller.slew = 0.9
            controller.controller_gain = np.ones(r3c.N_MODES)
            controller.actual_gain = np.ones(r3c.N_MODES)
            controller.actuator_bias = np.zeros(r3c.N_MODES)
            controller.phase = "main_control"
            controller.transition_step = transition_step
            controller.integral = np.zeros(5)
            controller.previous = np.zeros(r3c.N_MODES)
            controller.damping_integral = np.zeros(5)
            controller.terminal_integral = np.zeros(5)
            controller.history = [
                {
                    "step_index": 0,
                    "R": float(initial_state["R"]),
                    "Z": float(initial_state["Z"]),
                    "Ip": float(initial_state["Ip"]),
                }
            ]

        spec = {
            "phase_alignment": phase_cfg,
            "prime_action_queue_with_nominal": True,
            "visible_reference_manifold": _manifold(
                "synthetic-r17-source"
            ),
        }
        with mock.patch.object(
            r3c.r3b.FreshTaskController,
            "__init__",
            new=fake_parent_init,
        ):
            controller = r3c.AuthenticatedVisibleManifoldPhaseTaskController(
                base, {}, spec, initial
            )
        return controller, calls

    def test_nonzero_phase_aligns_nominal_queue_and_transitions(self) -> None:
        controller, calls = self._controller(
            visible_phase=12,
            transition_step=20,
            wire_value=1.0,
        )
        self.assertEqual(controller.reference_phase_start, 12)
        self.assertEqual(controller.transition_step, 8)
        self.assertEqual(controller.terminal_transition_step, 23)
        self.assertEqual(
            [row["reference_phase"] for row in controller.queue],
            [12, 13],
        )
        np.testing.assert_array_equal(
            controller.queue[0]["desired_physical"],
            controller.nominal_physical[12],
        )
        np.testing.assert_array_equal(
            calls[0][0], controller.nominal_physical[12]
        )

    def test_hidden_wire_change_cannot_change_phase_or_prime_queue(self) -> None:
        left, _ = self._controller(
            visible_phase=9,
            transition_step=None,
            wire_value=-1.0e9,
        )
        right, _ = self._controller(
            visible_phase=9,
            transition_step=None,
            wire_value=1.0e9,
        )
        self.assertEqual(left.reference_phase_start, 9)
        self.assertEqual(right.reference_phase_start, 9)
        for left_row, right_row in zip(left.queue, right.queue):
            np.testing.assert_array_equal(
                left_row["command"], right_row["command"]
            )
            np.testing.assert_array_equal(
                left_row["desired_physical"],
                right_row["desired_physical"],
            )

    def test_phase_zero_preserves_original_queue_and_transition(self) -> None:
        controller, calls = self._controller(
            visible_phase=0,
            transition_step=20,
            wire_value=0.0,
        )
        self.assertEqual(controller.reference_phase_start, 0)
        self.assertEqual(controller.transition_step, 20)
        self.assertEqual(controller.terminal_transition_step, 35)
        np.testing.assert_array_equal(
            calls[0], controller.nominal_physical
        )
        self.assertEqual(
            [row["reference_phase"] for row in controller.queue],
            [0, 1],
        )


if __name__ == "__main__":
    unittest.main()
