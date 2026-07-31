from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from scripts import stage4_2r3c2_server_postprocess as postprocess
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c2_restart_target_state_regulation_mpc as r3c,
)


def _source_spec(
    *,
    target_id: str,
    delay: int,
    slew: float,
) -> dict:
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


class Stage42R3C2DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(r3c.__file__).resolve().parents[2]
        cls.config = json.loads(
            (
                cls.root
                / "configs"
                / "stage4_2r3c2_restart_target_state_regulation_mpc_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_identity_timing_scope_and_regulation_are_frozen(self) -> None:
        r3c.validate_config(self.config)
        self.assertEqual(r3c.STAGE, "Stage4.2R3c2")
        self.assertEqual(
            r3c.CONTROLLER_REVISION,
            "restart_target_state_regulation_mpc_v42r3c2",
        )
        self.assertEqual(
            r3c.PACKAGE_REVISION,
            "r42r3c2_restart_target_state_regulation_mpc_v1",
        )
        timing = self.config["formal_timing_contract"]
        self.assertEqual(timing["normal"]["arrival_deadline_step"], 25)
        self.assertEqual(timing["normal"]["hold_through_step"], 35)
        self.assertEqual(timing["weak"]["arrival_deadline_step"], 27)
        self.assertEqual(timing["weak"]["hold_through_step"], 37)
        self.assertFalse(timing["arrival_deadline_expansion_allowed"])
        regulation = self.config["restart_regulation"]
        self.assertEqual(
            regulation["phase_zero_policy"], "preserve_r3c1_path"
        )
        self.assertEqual(
            regulation["nonzero_phase_policy"],
            "target_state_regulation_from_task_step_zero",
        )
        self.assertTrue(regulation["nonzero_phase_regulation_persistent"])
        self.assertFalse(
            regulation["pair_or_history_label_input_allowed"]
        )
        self.assertFalse(regulation["source_result_input_allowed"])
        self.assertTrue(self.config["development_set_only"])
        self.assertFalse(
            self.config["independent_hidden_history_confirmation"]
        )
        self.assertFalse(self.config["bc_dagger_or_rl_allowed"])

    def test_r3c1_evidence_hashes_are_exact(self) -> None:
        source = self.config["source_requirements"]
        self.assertEqual(
            source["required_stage4_2r3c1_run_inventory_digest"],
            "5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f",
        )
        self.assertEqual(
            source["required_stage4_2r3c1_raw_forensics_sha256"],
            "29e37da1d570179228a39700ac4f4c2c66067cf2a7295c2b744f2bfb40d50edd",
        )
        self.assertEqual(
            source[
                "required_stage4_2r3c1_restart_regulation_diagnostic_sha256"
            ],
            "9a278b5e97416ae2d98d05b4cff7ad2328ddd0a1ec8f3d14ded0421b184c124d",
        )
        self.assertEqual(
            source["required_stage4_2r3c1_formal_pass_count"], 16
        )
        self.assertEqual(
            source["required_stage4_2r3c1_formal_failure_count"], 16
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

    def test_invalid_phase_inputs_fail_closed(self) -> None:
        reference = np.zeros((35, 3))
        with self.assertRaises(ValueError):
            r3c.select_visible_reference_phase(
                reference,
                [0.0, 0.0, 0.0],
                candidate_min_phase=0,
                candidate_max_phase=35,
                scales=[0.03, 0.03, 2000.0],
            )
        with self.assertRaises(ValueError):
            r3c.select_visible_reference_phase(
                reference,
                [0.0, 0.0, 0.0],
                candidate_min_phase=0,
                candidate_max_phase=20,
                scales=[0.03, 0.0, 2000.0],
            )

    def test_step_zero_velocity_is_zero_then_current_run_difference(
        self,
    ) -> None:
        target = np.asarray([0.70, -0.01, 30000.0])
        first = [
            {
                "step_index": 0,
                "R": 0.705,
                "Z": -0.012,
                "Ip": 30125.0,
            }
        ]
        np.testing.assert_allclose(
            r3c._fresh_task_terminal_measurement(first, target, 0.01),
            np.asarray([0.005, -0.002, 0.0, 0.0, 125.0]),
            rtol=0.0,
            atol=1.0e-15,
        )
        second = [
            *first,
            {
                "step_index": 1,
                "R": 0.706,
                "Z": -0.010,
                "Ip": 30050.0,
            },
        ]
        np.testing.assert_array_equal(
            r3c._fresh_task_terminal_measurement(second, target, 0.01),
            r3c.r2.r9._terminal_measurement(second, target, 0.01),
        )
        with self.assertRaises(ValueError):
            r3c._fresh_task_terminal_measurement([], target, 0.01)

    def test_controller_spec_removes_experiment_and_history_identity(
        self,
    ) -> None:
        spec = {
            "pair_id": "pair",
            "history_member": "plus_first",
            "state_generation_experiment_id": "state",
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
        self.assertEqual(sanitized["action_delay_steps"], 2)

    def test_control_grid_is_exact_and_normalizes_model_cap(self) -> None:
        sources = {
            (target, delay, slew): {
                "experiment_id": f"source-{target}-{delay}-{slew}",
                "controller_revision": "frozen-r17",
                "spec": _source_spec(
                    target_id=target, delay=delay, slew=slew
                ),
            }
            for target in ("nominal", "RZ_p10_m10")
            for delay, slew in ((0, 1.0), (2, 0.9))
        }
        manifolds = {
            key: _manifold(
                str(source["experiment_id"]), 0.001 * index
            )
            for index, (key, source) in enumerate(sorted(sources.items()))
        }
        selected = []
        for index, pair_id in enumerate(
            self.config["source_requirements"][
                "required_selected_pair_ids"
            ]
        ):
            selected.append(
                {
                    "pair_id": pair_id,
                    "plus_first_state": {
                        "experiment_id": f"state-{index}-plus",
                        "snapshot_dir": f"/synthetic/{index}/plus",
                        "snapshot_manifest_digest": f"digest-{index}-plus",
                    },
                    "minus_first_state": {
                        "experiment_id": f"state-{index}-minus",
                        "snapshot_dir": f"/synthetic/{index}/minus",
                        "snapshot_manifest_digest": f"digest-{index}-minus",
                    },
                }
            )
        ctx = SimpleNamespace(cfg=copy.deepcopy(self.config))
        with mock.patch.object(
            r3c, "_source_controller_cases", return_value=sources
        ), mock.patch.object(
            r3c, "_visible_reference_manifolds", return_value=manifolds
        ), mock.patch.object(
            r3c.r3b, "_forbidden_future_paths", return_value=[]
        ):
            specs = r3c.build_control_specs(ctx, selected)
        self.assertEqual(len(specs), 32)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 32)
        self.assertTrue(
            all(
                row["terminal_model_phase_cap_step"] == 28
                and row["restart_regulation"]
                == self.config["restart_regulation"]
                and not row[
                    "pair_or_history_label_available_to_controller"
                ]
                and not row["source_result_available_to_controller"]
                and row["future_action_count"] == 0
                and row["future_measurement_count"] == 0
                and row["task_clock_starts_at_zero"]
                for row in specs
            )
        )

    def test_nonzero_phase_trace_requires_persistent_regulation(self) -> None:
        digest = "visible-manifold-digest"
        trace = [
            {
                "task_step": step,
                "reference_phase": 12 + step,
                "model_phase": min(12 + step, 28),
                "reference_phase_start": 12,
                "controller_phase": "restart_target_state_regulation",
                "visible_reference_manifold_digest": digest,
                "source_action_used": False,
                "source_coil_current_used": False,
                "source_wire_current_used": False,
                "current_run_future_used": False,
                "hidden_wire_used": False,
                "pair_or_history_label_used": False,
                "source_result_used": False,
            }
            for step in range(35)
        ]
        result = r3c._phase_trace_valid(
            {
                "controller_trace": trace,
                "spec": {
                    "terminal_model_phase_cap_step": 28,
                    "visible_reference_manifold_digest": digest,
                },
            }
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["restart_regulation_trace_count"], 35)
        stale = copy.deepcopy(trace)
        stale[3]["controller_phase"] = "phase_aligned_main_control"
        self.assertFalse(
            r3c._phase_trace_valid(
                {
                    "controller_trace": stale,
                    "spec": {
                        "terminal_model_phase_cap_step": 28,
                        "visible_reference_manifold_digest": digest,
                    },
                }
            )["passed"]
        )

    def test_action_branches_on_phase_without_using_labels(self) -> None:
        controller = (
            r3c.RestartTargetStateRegulationTaskController.__new__(
                r3c.RestartTargetStateRegulationTaskController
            )
        )
        controller.step = 0
        controller.restart_regulation_enabled = True
        controller.phase = "main_control"
        controller._damping_action = mock.Mock(
            return_value=(np.ones(r3c.N_COILS), {"phase": "regulation"})
        )
        controller._main_action = mock.Mock()
        action, _ = controller.action(
            {
                "step_index": 0,
                "currents_a_tsc": [0.0] * r3c.N_COILS,
            }
        )
        np.testing.assert_array_equal(action, np.ones(r3c.N_COILS))
        controller._damping_action.assert_called_once()
        controller._main_action.assert_not_called()

        phase_zero = (
            r3c.RestartTargetStateRegulationTaskController.__new__(
                r3c.RestartTargetStateRegulationTaskController
            )
        )
        phase_zero.step = 0
        phase_zero.restart_regulation_enabled = False
        phase_zero.phase = "main_control"
        phase_zero.transition_step = None
        phase_zero.terminal_transition_step = 35
        phase_zero._main_action = mock.Mock(
            return_value=(np.zeros(r3c.N_COILS), {"phase": "main"})
        )
        phase_zero._damping_action = mock.Mock()
        phase_zero.action(
            {
                "step_index": 0,
                "currents_a_tsc": [0.0] * r3c.N_COILS,
            }
        )
        phase_zero._main_action.assert_called_once()
        phase_zero._damping_action.assert_not_called()

    def test_snapshot_and_pair_assessment_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "success": True,
                "snapshot_dir": tmp,
                "snapshot_manifest_digest": "digest",
            }
            self.assertTrue(r3c._selected_snapshot_state_is_valid(state))
            self.assertFalse(
                r3c._selected_snapshot_state_is_valid(
                    {**state, "success": False}
                )
            )
        self.assertEqual(
            r3c.classify_pair_assessment(True, True),
            "both_pass_development_pair_success",
        )
        self.assertEqual(
            r3c.classify_pair_assessment(False, False),
            "masked_by_common_mode_both_fail",
        )
        self.assertEqual(
            r3c.classify_pair_assessment(True, False),
            "history_sensitive_pass_fail_outcome",
        )

    def test_resume_requires_exact_identity_and_spec(self) -> None:
        expected = {"experiment_id": "case", "value": 7}
        valid = {
            "completed": True,
            "stage": r3c.STAGE,
            "controller_revision": r3c.CONTROLLER_REVISION,
            "experiment_id": "case",
            "spec": copy.deepcopy(expected),
            "success": True,
            "trajectory": [{"step_index": 0}],
            "controller_trace": [{"task_step": 0}],
        }
        with mock.patch.object(
            r3c, "read_json_gz", return_value=valid
        ), mock.patch.object(Path, "is_file", return_value=True):
            self.assertTrue(
                r3c._result_complete(Path("/synthetic/raw.json.gz"), expected)
            )
            invalid = copy.deepcopy(valid)
            invalid["controller_revision"] = "stale"
            with mock.patch.object(
                r3c, "read_json_gz", return_value=invalid
            ):
                self.assertFalse(
                    r3c._result_complete(
                        Path("/synthetic/raw.json.gz"), expected
                    )
                )
            failed = copy.deepcopy(valid)
            failed.update(
                {
                    "success": False,
                    "failure_reason": "synthetic runtime failure",
                    "trajectory": [],
                    "controller_trace": [],
                }
            )
            with mock.patch.object(
                r3c, "read_json_gz", return_value=failed
            ):
                self.assertTrue(
                    r3c._result_complete(
                        Path("/synthetic/raw.json.gz"), expected
                    )
                )
        self.assertIsNone(
            r3c._semantics_preserving_resume_compatibility(
                mock.Mock(), {"digest": "same"}, {"digest": "same"}
            )
        )
        with self.assertRaises(ValueError):
            r3c._semantics_preserving_resume_compatibility(
                mock.Mock(),
                {"digest": "original"},
                {"digest": "changed"},
            )

    def test_postprocess_requires_exact_runtime_package(self) -> None:
        fingerprint = {"digest": "same", "files": []}
        self.assertEqual(
            postprocess._runtime_package_fingerprint(
                {"deployed_package_fingerprint": fingerprint}
            ),
            fingerprint,
        )
        with self.assertRaises(ValueError):
            postprocess._runtime_package_fingerprint(
                {
                    "deployed_package_fingerprint": fingerprint,
                    "semantics_preserving_resume_hotfix": {"unexpected": True},
                }
            )
        compatible = postprocess._audit_package_compatibility(
            Path("/project"), fingerprint, copy.deepcopy(fingerprint)
        )
        self.assertTrue(compatible["passed"])
        incompatible = postprocess._audit_package_compatibility(
            Path("/project"),
            fingerprint,
            {"digest": "different", "files": []},
        )
        self.assertFalse(incompatible["passed"])

    def test_self_test_and_launchers(self) -> None:
        self.assertTrue(r3c.self_test()["passed"])
        module = Path(r3c.__file__).read_text(encoding="utf-8")
        for token in (
            "run_offline_restart_regulation_audit",
            "restart_target_state_regulation",
            "_controller_spec",
            "_r3c1_evidence_fingerprint",
            "current_run_future_used",
            "real_closed_loop_formal_control_failure",
        ):
            self.assertIn(token, module)
        for relative in (
            "run_stage4_2r3c2_restart_target_state_regulation_mpc_native.sh",
            "run_stage4_2r3c2_restart_target_state_regulation_mpc_nohup.sh",
            "run_stop_stage4_2r3c2_now.sh",
        ):
            path = self.root / relative
            if not path.is_file():
                package = json.loads(
                    (self.root / "PACKAGE_MANIFEST.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertTrue(
                    any(
                        key.startswith("root_shell_scripts_are_")
                        and bool(value)
                        for key, value in package["package_rules"].items()
                    )
                )
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("ray stop --force", text)
            self.assertNotIn("pkill", text)


if __name__ == "__main__":
    unittest.main()
