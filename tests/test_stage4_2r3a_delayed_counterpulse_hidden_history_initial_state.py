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
    stage4_2r3a_delayed_counterpulse_hidden_history_initial_state as r3,
)


def _synthetic_state(order: str) -> dict:
    wire = (
        [10000.0] * r3.N_WIRES
        if order == "plus_first"
        else [9000.0] * 24 + [11000.0] * 24
    )
    return {
        "experiment_id": order,
        "pair_id": "p4_q1_a0p400_gap4_settle4",
        "history_order": order,
        "common_prefix_steps": 4,
        "common_prefix_source_experiment_id": "authenticated-source",
        "common_prefix_action_digest": "prefix-digest",
        "nullspace_direction_index": 1,
        "amplitude_fraction": 0.4,
        "gap_steps": 4,
        "settle_steps": 4,
        "horizon_steps": 14,
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


class Stage42R3ADesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(r3.__file__).resolve().parents[2]
        cls.config = json.loads(
            (
                cls.root
                / "configs"
                / "stage4_2r3a_delayed_counterpulse_hidden_history_initial_state_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_config_keeps_preregistered_grid_and_formal_timing(self) -> None:
        r3.validate_config(self.config)
        self.assertEqual(self.config["state_generation"]["expected_pairs"], 36)
        self.assertEqual(
            self.config["state_generation"]["expected_rollouts"], 72
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
        common_prefix = {
            "source_experiment_id": "authenticated-source",
            "source_initial_action": [0.0] * r3.N_COILS,
            "actions": [
                [0.01 * (step + 1)] * r3.N_COILS for step in range(8)
            ],
            "prefix_action_digests": {
                "4": "prefix-digest-4",
                "8": "prefix-digest-8",
            },
            "action_digest": "prefix-digest",
        }
        specs = r3._state_spec_grid(
            directions, self.config, common_prefix
        )
        self.assertEqual(len(specs), 72)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 72)
        self.assertEqual(len({row["pair_id"] for row in specs}), 36)
        for spec in specs:
            actions = np.asarray(spec["source_actions"], dtype=float)
            prefix_steps = int(spec["common_prefix_steps"])
            gap_steps = int(spec["gap_steps"])
            np.testing.assert_array_equal(
                actions[:prefix_steps],
                np.asarray(common_prefix["actions"][:prefix_steps]),
            )
            first_pulse = actions[prefix_steps]
            counterpulse = actions[prefix_steps + gap_steps + 1]
            np.testing.assert_allclose(
                first_pulse + counterpulse, 0.0, atol=0.0
            )
            np.testing.assert_array_equal(
                actions[prefix_steps + 1 : prefix_steps + gap_steps + 1],
                np.zeros((gap_steps, r3.N_COILS)),
            )
            self.assertLessEqual(float(np.max(np.abs(actions))), 1.0)
            self.assertEqual(
                spec["horizon_steps"],
                prefix_steps + gap_steps + 6,
            )

    def test_common_prefix_is_exactly_bound_to_authenticated_source(
        self,
    ) -> None:
        actions = [
            [0.01 * (step + 1)] * r3.N_COILS for step in range(8)
        ]
        initial = [0.001] * r3.N_COILS
        source = {"experiment_id": "r17-nominal-delay0-slew1"}
        ctx = SimpleNamespace(
            cfg=copy.deepcopy(self.config), r1_ctx=SimpleNamespace()
        )
        with mock.patch.object(
            r3.r1,
            "_selected_source_cases",
            return_value={("nominal", 0, 1.0): source},
        ), mock.patch.object(
            r3.r1, "_source_action_sequence", return_value=actions
        ), mock.patch.object(
            r3.r1, "_source_initial_action", return_value=initial
        ):
            result = r3._common_prefix_source(ctx)
        self.assertEqual(
            result["source_experiment_id"], "r17-nominal-delay0-slew1"
        )
        self.assertEqual(result["actions"], actions)
        self.assertEqual(result["source_initial_action"], initial)
        self.assertEqual(set(result["prefix_action_digests"]), {"4", "8"})
        self.assertNotEqual(
            result["prefix_action_digests"]["4"],
            result["prefix_action_digests"]["8"],
        )
        self.assertEqual(len(result["action_digest"]), 64)

    def test_resume_rejects_deployed_package_fingerprint_change(self) -> None:
        modes = np.zeros((r3.N_COILS, r3.N_MODES), dtype=float)
        modes[:3, :] = np.eye(3)
        common_prefix = {
            "source_experiment_id": "authenticated-source",
            "source_initial_action": [0.0] * r3.N_COILS,
            "actions": [
                [0.01 * (step + 1)] * r3.N_COILS for step in range(8)
            ],
            "prefix_action_digests": {
                "4": "prefix-digest-4",
                "8": "prefix-digest-8",
            },
            "action_digest": "prefix-digest",
        }
        with tempfile.TemporaryDirectory() as tmp:
            paths = r3.Stage42R3APaths.from_run_dir(Path(tmp) / "run")
            ctx = SimpleNamespace(
                cfg=copy.deepcopy(self.config),
                paths=paths,
                source_r2_run=Path("/source/r2"),
                source_r1_run=Path("/source/r1"),
                source_r17_run=Path("/source/r17"),
                source_fingerprint={"digest": "source"},
            )
            with mock.patch.object(
                r3,
                "_generation_base_payload",
                return_value={"modes_tsc": modes},
            ), mock.patch.object(
                r3, "_common_prefix_source", return_value=common_prefix
            ), mock.patch.object(
                r3,
                "_deployed_package_fingerprint",
                return_value={"digest": "package-a"},
            ):
                r3.prepare(ctx, resume=False)
            with mock.patch.object(
                r3,
                "_generation_base_payload",
                return_value={"modes_tsc": modes},
            ), mock.patch.object(
                r3, "_common_prefix_source", return_value=common_prefix
            ), mock.patch.object(
                r3,
                "_deployed_package_fingerprint",
                return_value={"digest": "package-b"},
            ):
                with self.assertRaisesRegex(
                    ValueError, "deployed_package_fingerprint"
                ):
                    r3.prepare(ctx, resume=True)

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
        for index in range(72):
            pair_index = index // 2
            prefix_steps = 4 if pair_index < 18 else 8
            stratum_index = pair_index % 18
            direction = 1 if stratum_index < 9 else 2
            rows.append(
                {
                    "experiment_id": f"state-{index}",
                    "pair_id": f"pair-{pair_index:02d}",
                    "history_order": (
                        "plus_first" if index % 2 == 0 else "minus_first"
                    ),
                    "common_prefix_steps": prefix_steps,
                    "nullspace_direction_index": direction,
                    "amplitude_fraction": 0.4,
                    "gap_steps": 4,
                    "settle_steps": 4,
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
                "common_prefix_steps": left["common_prefix_steps"],
                "nullspace_direction_index": left[
                    "nullspace_direction_index"
                ],
                "amplitude_fraction": 0.4,
                "gap_steps": 4,
                "settle_steps": 4,
                "wire_relative_rms_difference": 0.2,
                "wire_max_abs_difference_A": 2.0,
                "visible_max_normalized_ratio": 0.1,
                "visible_match_pass": accepted,
                "hidden_separation_pass": accepted,
                "accepted": accepted,
                "plus_first_state": left,
                "minus_first_state": right,
            }

        with tempfile.TemporaryDirectory() as tmp:
            paths = r3.Stage42R3APaths.from_run_dir(Path(tmp))
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
                return_value={
                    "centroid_R": 1.0,
                    "centroid_Z": 0.0,
                    "centroid_Ip": 1.0e6,
                    "centroid_coil_currents_a": [1000.0] * r3.N_COILS,
                    "different_initial_state_pass": True,
                },
            ), mock.patch.object(
                r3,
                "_prefix_group_separation",
                return_value={
                    "common_prefix_coverage_pass": True,
                    "mutual_prefix_group_separation_pass": True,
                },
            ):
                summary = r3.analyze_state_generation(
                    ctx, [{"index": index} for index in range(72)]
                )
        self.assertFalse(summary["passed"])
        self.assertFalse(summary["complete_state_grid"])
        self.assertEqual(summary["runtime_or_environment_error_count"], 1)
        self.assertEqual(
            summary["stop_reason"],
            "state_generation_runtime_or_environment_error",
        )

    def test_prefix_group_separation_requires_both_groups_and_real_delta(
        self,
    ) -> None:
        gate = self.config["different_initial_state_gate"]
        base = {
            "pair_id": "p4",
            "common_prefix_steps": 4,
            "centroid_R": 0.7,
            "centroid_Z": 0.0,
            "centroid_Ip": 30000.0,
            "centroid_coil_currents_a": [0.0] * r3.N_COILS,
        }
        other = copy.deepcopy(base)
        other.update(
            {
                "pair_id": "p8",
                "common_prefix_steps": 8,
                "centroid_R": 0.701,
            }
        )
        result = r3._prefix_group_separation([base, other], [4, 8], gate)
        self.assertTrue(result["common_prefix_coverage_pass"])
        self.assertTrue(result["mutual_prefix_group_separation_pass"])

        missing = r3._prefix_group_separation([base], [4, 8], gate)
        self.assertFalse(missing["common_prefix_coverage_pass"])
        self.assertFalse(missing["mutual_prefix_group_separation_pass"])


class Stage42R3AFreshControllerTests(unittest.TestCase):
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
