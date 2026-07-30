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
    stage4_2r2_persistent_controller_checkpoint_replay as r2,
)


def checkpoint_fixture(delay: int = 2) -> dict:
    payload = {
        "schema_version": 1,
        "checkpoint_step": 20,
        "measurement_history": [
            {"state_index": step, "R": 0.75, "Z": 0.0, "Ip": 30000.0}
            for step in range(21)
        ],
        "modeled_delay_steps": delay,
        "actual_delay_steps": delay,
        "modeled_slew_scale": 0.9,
        "trusted_calibration_model": True,
        "calibration_token": "trusted-token",
        "integral_normalized": [0.0] * 5,
        "previous_correction_physical": [0.0] * 3,
        "checkpoint_action_norm_tsc": [0.0] * 14,
        "pending_delay_queue": [
            {
                "origin": "main_control",
                "origin_index": 20 - delay + index,
                "command": [0.0] * 3,
                "desired_physical": [0.0] * 3,
            }
            for index in range(delay)
        ],
        "controller_spec": {
            "policy_parameter": "allowed",
            "r15_probe_delta_by_issue_step": {"20": [-0.03, 0.0, 0.0]},
        },
        "future_measurement_count": 0,
        "future_action_count": 0,
        "online_action_recomputation_required": True,
    }
    payload["digest"] = r2._canonical_digest(payload)
    return payload


class Stage42R2CheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(r2.__file__).resolve().parents[2]
        cls.config = json.loads(
            (
                cls.root
                / "configs"
                / "stage4_2r2_persistent_controller_checkpoint_replay_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_config_keeps_immutable_formal_timing(self) -> None:
        r2.validate_config(self.config)
        self.assertEqual(self.config["checkpoint"]["step"], 20)
        self.assertEqual(
            self.config["formal_timing_contract"]["normal"]["arrival_deadline_step"],
            25,
        )
        self.assertEqual(
            self.config["formal_timing_contract"]["weak"]["arrival_deadline_step"],
            27,
        )
        self.assertFalse(
            self.config["formal_timing_contract"][
                "arrival_deadline_expansion_allowed"
            ]
        )

    def test_config_rejects_weakened_causal_gate(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["controller_checkpoint_requirements"][
            "forbid_future_actions"
        ] = False
        with self.assertRaisesRegex(ValueError, "requirement weakened"):
            r2.validate_config(changed)

    def test_checkpoint_accepts_policy_schedule_but_no_recorded_suffix(self) -> None:
        checkpoint = checkpoint_fixture()
        checked = r2._strict_checkpoint_payload(checkpoint)
        self.assertEqual(checked["digest"], checkpoint["digest"])
        self.assertIn(
            "r15_probe_delta_by_issue_step", checked["controller_spec"]
        )

        bad = copy.deepcopy(checkpoint)
        bad.pop("digest")
        bad["nested"] = {"source_suffix_actions": [[0.0] * 14]}
        bad["digest"] = r2._canonical_digest(bad)
        with self.assertRaisesRegex(ValueError, "forbidden future data"):
            r2._strict_checkpoint_payload(bad)

    def test_checkpoint_rejects_future_measurement_and_wrong_queue(self) -> None:
        future = checkpoint_fixture()
        future.pop("digest")
        future["measurement_history"].append(
            {"state_index": 21, "R": 0.75, "Z": 0.0, "Ip": 30000.0}
        )
        future["digest"] = r2._canonical_digest(future)
        with self.assertRaisesRegex(ValueError, "causal/contiguous"):
            r2._strict_checkpoint_payload(future)

        queue = checkpoint_fixture()
        queue.pop("digest")
        queue["pending_delay_queue"].pop()
        queue["digest"] = r2._canonical_digest(queue)
        with self.assertRaisesRegex(ValueError, "queue length"):
            r2._strict_checkpoint_payload(queue)

    def test_checkpoint_digest_detects_tamper(self) -> None:
        checkpoint = checkpoint_fixture()
        checkpoint["integral_normalized"][0] = 1.0
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            r2._strict_checkpoint_payload(checkpoint)


class Stage42R2ControllerTests(unittest.TestCase):
    def test_r17_braking_schedule_is_recomputed_inside_damping_policy(self) -> None:
        controller = object.__new__(r2.PersistentController)
        controller.step = 20
        controller.history = []
        controller.target = np.zeros(3)
        controller.dt_s = 0.01
        controller.measurement_scales = np.ones(5)
        controller.queue = []
        controller.delay = 0
        controller.actual_delay = 0
        controller.bundle = {}
        controller.previous = np.zeros(3)
        controller.damping_integral = np.zeros(5)
        controller.controller_gain = np.ones(3)
        controller.actual_gain = np.ones(3)
        controller.actuator_bias = np.zeros(3)
        controller.slew = 0.9
        controller.spec = {
            "terminal_position_measurement_gain": 1.0,
            "terminal_velocity_measurement_gain": 1.0,
            "terminal_ip_measurement_gain": 1.0,
            "terminal_model_phase_cap_step": 23,
            "terminal_controller_scale": 1.0,
            "terminal_controller_model_scale": 1.0,
            "r15_probe_delta_by_issue_step": {"20": [-0.03, 0.0, 0.0]},
        }

        class Scheduler:
            @staticmethod
            def solve_command(desired, _currents, _gain, _slew, enabled):
                assert enabled
                return {"command": np.asarray(desired, dtype=float)}

        controller.base = SimpleNamespace(
            stub=SimpleNamespace(),
            lower_mode=np.asarray([-1.0] * 3),
            upper_mode=np.asarray([1.0] * 3),
            scheduler=Scheduler(),
            _mode_action=lambda effective, _currents: np.pad(
                np.asarray(effective, dtype=float), (0, 11)
            ),
        )
        solve = {
            "first_correction": np.asarray([0.1, 0.0, 0.0]),
            "solver_success": True,
        }
        with mock.patch.object(
            r2.r9, "_terminal_measurement", return_value=np.zeros(5)
        ), mock.patch.object(
            r2.r12,
            "_measurement_for_solver",
            return_value=(np.zeros(5), np.zeros(5)),
        ), mock.patch.object(
            r2.r3, "solve_delay_aware_physical_correction", return_value=solve
        ):
            action, trace = controller._damping_action(np.zeros(14))

        self.assertAlmostEqual(action[0], 0.07)
        self.assertEqual(trace["r15_probe_requested_delta"], [-0.03, 0.0, 0.0])
        self.assertAlmostEqual(trace["mode_correction_physical"][0], 0.07)
        self.assertTrue(trace["r15_identification_probe"])

    def test_recombined_trajectory_has_one_checkpoint_state(self) -> None:
        capture = {"trajectory": [{"step_index": index} for index in range(38)]}
        replay = {
            "restart_trajectory": [
                {"step_index": index} for index in range(20, 38)
            ]
        }
        result = r2._recombined(capture, replay, 37)
        self.assertEqual(len(result["trajectory"]), 38)
        self.assertEqual(
            [row["step_index"] for row in result["trajectory"]], list(range(38))
        )

    def test_self_test_rejects_future_action_payload(self) -> None:
        result = r2.self_test()
        self.assertTrue(result["passed"])
        self.assertTrue(result["future_action_checkpoint_rejected"])

    def test_runtime_failure_is_not_converted_to_reporting_failure(self) -> None:
        result = {
            "experiment_id": "failed",
            "spec": {
                "target_id": "nominal",
                "action_delay_steps": 1,
                "slew_scale": 0.9,
            },
            "success": False,
            "failure_reason": "TSC timeout",
            "traceback": "trace",
            "controller_trace": [],
        }
        row = r2._result_row(None, result)  # type: ignore[arg-type]
        self.assertEqual(row["failure_class"], "runtime_or_environment_error")
        self.assertNotIn("summary_exception", row)

    def test_offline_only_analysis_remains_resumable_not_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = r2.Stage42R2Paths.from_run_dir(Path(tmp))
            paths.analysis.mkdir(parents=True)
            r2.atomic_write_json(
                paths.state,
                {
                    "finished": False,
                    "primary_pass": False,
                    "stop_reason": "",
                },
            )
            ctx = SimpleNamespace(
                paths=paths,
                source_r1_run=Path("/source/r1"),
            )
            checkpoint = {"passed": True}
            offline = {"passed": True}
            summary = r2.analyze(ctx, checkpoint, offline)
            state = r2.read_json(paths.state)
            self.assertFalse(state["finished"])
            self.assertEqual(state["stop_reason"], "")
            self.assertEqual(state["phase_status"], "offline_gate_complete")
            self.assertTrue(summary["online_action_recomputation_validated"])
            self.assertEqual(
                summary["controller_restart_replay_status"], "not_run"
            )


if __name__ == "__main__":
    unittest.main()
