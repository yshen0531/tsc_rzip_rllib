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
    stage4_2r3_authentic_hidden_history_initial_state as r3,
)


def _synthetic_state(order: str) -> dict:
    wire = (
        [10000.0] * r3.N_WIRES
        if order == "plus_first"
        else [9000.0] * 24 + [11000.0] * 24
    )
    return {
        "experiment_id": order,
        "pair_id": "q0_a0p100_settle8",
        "history_order": order,
        "nullspace_direction_index": 0,
        "amplitude_fraction": 0.1,
        "settle_steps": 8,
        "horizon_steps": 10,
        "success": True,
        "R": 1.0,
        "Z": 0.0,
        "Ip": 1.0e6,
        "vR_m_per_s": 0.0,
        "vZ_m_per_s": 0.0,
        "coil_currents_a": [0.0] * r3.N_COILS,
        "action_norm_tsc": [0.0] * r3.N_COILS,
        "wire_currents_a": wire,
        "wire_rms_a": r3._rms(np.asarray(wire)),
        "snapshot_dir": f"/synthetic/{order}",
        "snapshot_manifest_digest": order,
        "snapshot_time_ms": 1200,
    }


class Stage42R3DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(r3.__file__).resolve().parents[2]
        cls.config = json.loads(
            (
                cls.root
                / "configs"
                / "stage4_2r3_authentic_hidden_history_initial_state_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_config_keeps_preregistered_grid_and_formal_timing(self) -> None:
        r3.validate_config(self.config)
        self.assertEqual(self.config["state_generation"]["expected_pairs"], 27)
        self.assertEqual(
            self.config["state_generation"]["expected_rollouts"], 54
        )
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

    def test_nullspace_grid_is_complete_zero_net_and_bounded(self) -> None:
        modes = np.zeros((r3.N_COILS, r3.N_MODES), dtype=float)
        modes[:3, :] = np.eye(3)
        directions = r3._nullspace_directions(modes)
        self.assertLessEqual(float(np.max(np.abs(directions @ modes))), 1e-12)
        specs = r3._state_spec_grid(directions, self.config)
        self.assertEqual(len(specs), 54)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 54)
        for spec in specs:
            actions = np.asarray(spec["source_actions"], dtype=float)
            self.assertLessEqual(float(np.max(np.abs(actions))), 0.2)
            np.testing.assert_allclose(np.sum(actions, axis=0), 0.0, atol=0.0)

    def test_pair_gate_requires_visible_match_and_hidden_separation(self) -> None:
        pair = r3._pair_metrics(
            _synthetic_state("plus_first"),
            _synthetic_state("minus_first"),
            self.config["pair_gate"],
        )
        self.assertTrue(pair["visible_match_pass"])
        self.assertTrue(pair["hidden_separation_pass"])
        self.assertTrue(pair["accepted"])

        changed = _synthetic_state("minus_first")
        changed["R"] += 0.001
        rejected = r3._pair_metrics(
            _synthetic_state("plus_first"),
            changed,
            self.config["pair_gate"],
        )
        self.assertFalse(rejected["visible_match_pass"])
        self.assertFalse(rejected["accepted"])

    def test_recursive_future_payload_detection(self) -> None:
        self.assertEqual(
            r3._forbidden_future_paths(
                {"outer": [{"source_suffix_actions": [[0.0] * r3.N_COILS]}]}
            ),
            ["outer[0].source_suffix_actions"],
        )
        self.assertEqual(r3._forbidden_future_paths({"policy": "causal"}), [])

    def test_partial_state_grid_cannot_pass_pair_selection(self) -> None:
        rows = []
        for index in range(54):
            pair_index = index // 2
            rows.append(
                {
                    "experiment_id": f"state-{index}",
                    "pair_id": f"pair-{pair_index:02d}",
                    "history_order": (
                        "plus_first" if index % 2 == 0 else "minus_first"
                    ),
                    "nullspace_direction_index": pair_index // 9,
                    "amplitude_fraction": 0.1,
                    "settle_steps": 8,
                    "success": index != 0,
                    "failure_class": (
                        "runtime_or_environment_error" if index == 0 else ""
                    ),
                }
            )

        def pair_metrics(left, right, _gate):
            accepted = bool(left["success"] and right["success"])
            return {
                "pair_id": left["pair_id"],
                "nullspace_direction_index": left[
                    "nullspace_direction_index"
                ],
                "amplitude_fraction": 0.1,
                "settle_steps": 8,
                "wire_relative_rms_difference": 0.2,
                "visible_max_normalized_ratio": 0.1,
                "visible_match_pass": accepted,
                "hidden_separation_pass": accepted,
                "accepted": accepted,
                "plus_first_state": left,
                "minus_first_state": right,
            }

        with tempfile.TemporaryDirectory() as tmp:
            paths = r3.Stage42R3Paths.from_run_dir(Path(tmp))
            r3._prepare_dirs(paths)
            ctx = SimpleNamespace(paths=paths, cfg=copy.deepcopy(self.config))
            with mock.patch.object(
                r3, "_state_row", side_effect=rows
            ), mock.patch.object(
                r3, "_pair_metrics", side_effect=pair_metrics
            ), mock.patch.object(
                r3,
                "_frozen_initial_state",
                return_value={
                    "R": 0.0,
                    "Z": 0.0,
                    "Ip": 0.0,
                    "coil_currents_a": [0.0] * r3.N_COILS,
                },
            ), mock.patch.object(
                r3,
                "_different_initial_metrics",
                return_value={"different_initial_state_pass": True},
            ):
                summary = r3.analyze_state_generation(
                    ctx, [{"index": index} for index in range(54)]
                )
        self.assertFalse(summary["passed"])
        self.assertFalse(summary["complete_state_grid"])
        self.assertEqual(summary["runtime_or_environment_error_count"], 1)
        self.assertEqual(
            summary["stop_reason"],
            "state_generation_runtime_or_environment_error",
        )


class Stage42R3FreshControllerTests(unittest.TestCase):
    def test_offline_command_cannot_start_state_generation(self) -> None:
        ctx = SimpleNamespace(
            paths=SimpleNamespace(state=Path("/synthetic/state.json"))
        )
        state = {
            "finished": False,
            "primary_pass": False,
            "phase_status": "prepared",
            "stop_reason": "",
        }
        writes = {}

        def write(_path, value):
            writes.update(copy.deepcopy(value))

        with mock.patch.object(r3, "prepare"), mock.patch.object(
            r3,
            "run_offline_frozen_controller_audit",
            return_value={"passed": True, "real_tsc_executed": False},
        ), mock.patch.object(
            r3, "read_json", return_value=state
        ), mock.patch.object(
            r3, "atomic_write_json", side_effect=write
        ), mock.patch.object(
            r3, "_generation_base_payload"
        ) as generation:
            result = r3.execute(
                ctx,
                command="offline",
                backend="ray",
                resume=False,
            )

        generation.assert_not_called()
        self.assertFalse(result["real_tsc_executed"])
        self.assertEqual(writes["phase_status"], "offline_gate_complete")
        self.assertFalse(writes["finished"])

    def test_fresh_controller_starts_only_from_current_visible_state(self) -> None:
        class Base:
            stub = SimpleNamespace()
            library = {}
            cfg = {
                "target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0},
                "identification": {
                    "output_scales": {
                        "R_m": 0.03,
                        "Z_m": 0.03,
                        "vR_m_per_s": 0.1,
                        "vZ_m_per_s": 0.1,
                        "Ip_A": 30000.0,
                    }
                },
            }
            env_cfg = {"dt_ms": 10}
            robust_cfg = {
                "controller_upgrade": {
                    "delay_aware": {
                        "maximum_modeled_action_delay_steps": 2,
                        "prime_action_queue_with_nominal": True,
                    }
                }
            }

            @staticmethod
            def _flag(_spec, _section, _key):
                return True

            @staticmethod
            def _nominal_command_plan(
                nominal, _currents, _gain, _slew, enabled
            ):
                assert enabled
                return np.asarray(nominal, dtype=float), {}

        interpolation = {
            "full_control_vector": np.arange(105, dtype=float) / 1000.0,
            "nominal_trajectory_RZI": np.zeros((35, 3), dtype=float),
            "nominal_velocity_RZ": np.zeros((35, 2), dtype=float),
        }
        spec = {
            "trusted_calibration_model": True,
            "calibration_token": "trusted",
            "action_delay_steps": 2,
            "controller_action_delay_steps": 2,
            "slew_scale": 0.9,
            "controller_slew_scale_estimate": 0.9,
            "controller_gain_estimate_by_mode": [1.0] * 3,
            "actuator_gain_by_mode": [1.0] * 3,
            "actuator_bias_by_mode": [0.0] * 3,
        }
        initial = {
            "step_index": 0,
            "R": 0.71,
            "Z": -0.02,
            "Ip": 28000.0,
            "currents_a_tsc": [100.0] * r3.N_COILS,
            "wire_currents_a": [999999.0] * r3.N_WIRES,
        }
        with mock.patch.object(
            r3.r2.r3, "_sensor_path_is_clean", return_value=True
        ), mock.patch.object(
            r3.r2.r3.s34,
            "interpolation_for_target",
            return_value=interpolation,
        ), mock.patch.object(
            r3.r2.r3.s34,
            "_nominal_feature",
            return_value=np.zeros(35 * 5, dtype=float),
        ):
            controller = r3.FreshTaskController(
                Base(), {}, spec, initial
            )

        self.assertEqual(controller.step, 0)
        self.assertEqual(controller.history, [
            {"step_index": 0, "R": 0.71, "Z": -0.02, "Ip": 28000.0}
        ])
        self.assertNotIn("wire_currents_a", controller.history[0])
        np.testing.assert_array_equal(controller.integral, np.zeros(5))
        np.testing.assert_array_equal(controller.previous, np.zeros(3))
        self.assertEqual(len(controller.queue), 2)
        self.assertEqual(
            [row["origin_index"] for row in controller.queue], [-2, -1]
        )
        np.testing.assert_array_equal(
            controller.queue[0]["command"],
            np.asarray(interpolation["full_control_vector"]).reshape(35, 3)[0],
        )

    def test_runtime_error_is_not_reported_as_control_failure(self) -> None:
        result = {
            "experiment_id": "failed",
            "spec": {
                "pair_id": "pair",
                "history_member": "plus_first",
                "state_generation_experiment_id": "state",
                "target_id": "nominal",
                "action_delay_steps": 0,
                "slew_scale": 1.0,
                "horizon_steps": 35,
            },
            "success": False,
            "failure_reason": "TSC timeout",
        }
        row = r3._control_row(
            None, result, {}  # type: ignore[arg-type]
        )
        self.assertEqual(row["failure_class"], "runtime_or_environment_error")
        self.assertFalse(row["formal_contract_pass"])

    def test_self_test_covers_hidden_pair_and_future_rejection(self) -> None:
        result = r3.self_test()
        self.assertTrue(result["passed"])
        self.assertTrue(result["synthetic_pair_accepted"])
        self.assertTrue(result["future_action_payload_rejected"])


if __name__ == "__main__":
    unittest.main()
