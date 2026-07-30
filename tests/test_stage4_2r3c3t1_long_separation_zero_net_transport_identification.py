from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from scripts import stage4_2r3c3t1_server_postprocess as postprocess
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t1_long_separation_zero_net_transport_identification as t1,
)


class Stage42R3C3T1DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(t1.__file__).resolve().parents[2]
        cls.config = json.loads(
            (
                cls.root
                / "configs"
                / "stage4_2r3c3t1_long_separation_zero_net_transport_identification_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_identity_timing_scope_and_source_are_frozen(self) -> None:
        t1.validate_config(self.config)
        self.assertEqual(t1.STAGE, "Stage4.2R3c3T1")
        self.assertEqual(
            t1.CONTROLLER_REVISION,
            "long_separation_zero_net_transport_probe_v42r3c3t1",
        )
        self.assertEqual(
            t1.PACKAGE_REVISION,
            "r42r3c3t1_long_separation_transport_identification_v1",
        )
        timing = self.config["formal_timing_contract"]
        self.assertEqual(timing["normal"]["arrival_deadline_step"], 25)
        self.assertEqual(timing["normal"]["hold_through_step"], 35)
        self.assertEqual(timing["weak"]["arrival_deadline_step"], 27)
        self.assertEqual(timing["weak"]["hold_through_step"], 37)
        self.assertFalse(timing["arrival_deadline_expansion_allowed"])
        probe = self.config["identification_probe"]
        self.assertEqual(
            probe["physical_mode_amplitude"], [0.0075, 0.0075, 0.0]
        )
        self.assertEqual(len(probe["basis"]), 2)
        self.assertEqual(probe["required_nonzero_issue_count"], 12)
        self.assertEqual(probe["probe_signs"], [-1, 1])
        self.assertFalse(probe["formal_tracking_pass_required"])
        self.assertFalse(
            probe["probe_trajectories_allowed_in_expert_dataset"]
        )
        matrix = self.config["control_matrix"]
        self.assertEqual(matrix["expected_rollouts"], 128)
        self.assertEqual(matrix["expected_baseline_contexts"], 32)
        self.assertTrue(self.config["development_set_only"])
        self.assertFalse(self.config["bc_dagger_or_rl_allowed"])
        source = self.config["source_requirements"]
        self.assertEqual(
            source["required_stage4_2r3c3_raw_inventory_digest"],
            "88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563",
        )
        self.assertEqual(
            source["required_stage4_2r3c3_bank_provenance_digest"],
            "5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6",
        )

    def test_long_separation_schedule_is_exact_and_zero_net(self) -> None:
        for basis in self.config["identification_probe"]["basis"]:
            for delay, expected in (
                (
                    0,
                    [
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                    ],
                ),
                (
                    2,
                    [
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                    ],
                ),
            ):
                for sign in (-1, 1):
                    schedule = t1._probe_schedule(
                        basis=basis,
                        actual_delay=delay,
                        sign=sign,
                        amplitude_by_mode=[0.0075, 0.0075, 0.0],
                    )
                    self.assertEqual(sorted(schedule), expected)
                    values = np.stack(list(schedule.values()))
                    self.assertEqual(values.shape, (12, t1.N_MODES))
                    np.testing.assert_array_equal(
                        values.sum(axis=0),
                        np.zeros(t1.N_MODES),
                    )
                    self.assertEqual(
                        np.count_nonzero(values[:, int(basis["mode"])]),
                        12,
                    )
                    self.assertAlmostEqual(
                        np.max(np.abs(values)), 0.0075
                    )

    def test_controller_spec_strips_forbidden_inputs(self) -> None:
        spec = {
            "experiment_id": "x",
            "r3c3_probe_delta_by_task_issue_step": {
                0: [0.0075, 0.0, 0.0]
            },
        }
        for key in t1.r3c3._FORBIDDEN_CONTROLLER_SPEC_KEYS:
            spec[key] = "forbidden"
        sanitized = t1._controller_spec(spec)
        self.assertNotIn("experiment_id", sanitized)
        self.assertEqual(
            sanitized["r3c3_probe_delta_by_task_issue_step"],
            {0: [0.0075, 0.0, 0.0]},
        )
        self.assertFalse(
            t1.r3c3._FORBIDDEN_CONTROLLER_SPEC_KEYS.intersection(
                sanitized
            )
        )

    def test_control_specs_expand_32_contexts_to_128_exact_probes(
        self,
    ) -> None:
        templates = []
        for index in range(32):
            delay = 0 if index % 2 == 0 else 2
            templates.append(
                {
                    "experiment_id": f"source-{index}",
                    "pair_id": f"pair-{index // 8}",
                    "history_member": (
                        "plus_first"
                        if (index // 4) % 2 == 0
                        else "minus_first"
                    ),
                    "target_id": (
                        "nominal"
                        if (index // 2) % 2 == 0
                        else "RZ_p10_m10"
                    ),
                    "state_generation_experiment_id": f"state-{index}",
                    "restart_snapshot_manifest_digest": f"digest-{index}",
                    "restart_snapshot_dir": f"/snapshot/{index}",
                    "action_delay_steps": delay,
                    "slew_scale": 1.0 if delay == 0 else 0.9,
                    "r3c3_probe_id": "early_mode0",
                    "r3c3_probe_sign": 1,
                    "baseline_experiment_id": f"baseline-{index}",
                }
            )
        ctx = SimpleNamespace(
            cfg=copy.deepcopy(self.config),
            base_ctx=object(),
            source_bank_fingerprint={
                "bank_provenance_digest": "provenance"
            },
        )
        with mock.patch.object(
            t1.r3c3, "build_control_specs", return_value=templates
        ):
            specs = t1.build_control_specs(ctx, [])
        self.assertEqual(len(specs), 128)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 128)
        self.assertEqual(
            {row["r3c3_probe_id"] for row in specs},
            {"transport_mode0", "transport_mode1"},
        )
        self.assertEqual(
            {row["r3c3_probe_sign"] for row in specs}, {-1, 1}
        )
        for spec in specs:
            schedule = spec["r3c3_probe_delta_by_task_issue_step"]
            self.assertEqual(len(schedule), 12)
            np.testing.assert_array_equal(
                np.asarray(list(schedule.values())).sum(axis=0),
                np.zeros(t1.N_MODES),
            )

    def test_phase_validator_authenticates_all_twelve_issues(self) -> None:
        basis = self.config["identification_probe"]["basis"][0]
        schedule = t1._probe_schedule(
            basis=basis,
            actual_delay=2,
            sign=1,
            amplitude_by_mode=[0.0075, 0.0075, 0.0],
        )
        zeros = np.zeros(t1.N_MODES).tolist()
        trace = []
        for step in range(37):
            expected = schedule.get(step, zeros)
            trace.append(
                {
                    "task_step": step,
                    "r3c3_probe_requested_delta": copy.deepcopy(
                        expected
                    ),
                    "r3c3_probe_applied_desired_delta": copy.deepcopy(
                        expected
                    ),
                    "r3c3_probe_issued": step in schedule,
                    "baseline_controller_revision": (
                        t1.r3c1.CONTROLLER_REVISION
                    ),
                    "r3c3_identification_only": True,
                    "r3c3_probe_id": "transport_mode0",
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
                "r3c3_probe_id": "transport_mode0",
                "r3c3_probe_mode": 0,
                "r3c3_probe_sign": 1,
                "r3c3_probe_first_effect_state": 3,
                "r3c3_probe_delta_by_task_issue_step": schedule,
            },
            "controller_trace": trace,
        }
        base = {
            "passed": True,
            "hidden_wire_trace_count": 0,
            "source_action_trace_count": 0,
            "source_coil_current_trace_count": 0,
            "source_wire_current_trace_count": 0,
            "current_run_future_trace_count": 0,
        }
        with mock.patch.object(
            t1.r3c1, "_phase_trace_valid", return_value=base
        ):
            phase = t1._phase_trace_valid(result)
            self.assertTrue(phase["passed"])
            self.assertEqual(phase["probe_issued_count"], 12)
            broken = copy.deepcopy(result)
            broken["controller_trace"][0][
                "r3c3_probe_issued"
            ] = False
            self.assertFalse(t1._phase_trace_valid(broken)["passed"])

    def test_summary_reuse_does_not_patch_frozen_r3c3(self) -> None:
        original_validator = t1.r3c3._phase_trace_valid
        namespace: dict = {}
        exec(
            "def fake(ctx, results, selected_pairs):\n"
            "    return {'stage': STAGE, "
            "'validator': _phase_trace_valid(results[0])}\n",
            namespace,
        )
        marker = {"passed": True, "probe_issued_count": 12}
        with mock.patch.object(
            t1.r3c3, "summarize_control", namespace["fake"]
        ), mock.patch.object(
            t1, "_phase_trace_valid", return_value=marker
        ):
            summary = t1._summarize_transport_responses(
                object(), [{}], []
            )
        self.assertEqual(summary["stage"], t1.STAGE)
        self.assertEqual(summary["validator"], marker)
        self.assertIs(t1.r3c3._phase_trace_valid, original_validator)

    def test_resume_result_identity_is_exact(self) -> None:
        spec = {"experiment_id": "x"}
        result = {
            "completed": True,
            "stage": t1.STAGE,
            "controller_revision": t1.CONTROLLER_REVISION,
            "experiment_id": "x",
            "spec": spec,
            "success": True,
            "trajectory": [],
            "controller_trace": [],
        }
        with mock.patch.object(
            t1.r3c3, "read_json_gz", return_value=result
        ):
            self.assertTrue(
                t1._result_complete(
                    self.root / "PACKAGE_MANIFEST.json", spec
                )
            )
            self.assertFalse(
                t1._result_complete(
                    self.root / "PACKAGE_MANIFEST.json",
                    {"experiment_id": "changed"},
                )
            )

    def test_postprocess_requires_exact_package(self) -> None:
        runtime = {
            "digest": "same",
            "files": [{"path": "x", "sha256": "a"}],
        }
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
                runtime, copy.deepcopy(runtime)
            )["passed"]
        )
        changed = postprocess._audit_package_compatibility(
            runtime,
            {"digest": "changed", "files": []},
        )
        self.assertFalse(changed["passed"])
        self.assertEqual(changed["changed_paths"], ["x"])

    def test_self_test_and_launchers(self) -> None:
        self.assertTrue(t1.self_test()["passed"])
        self.assertIsNot(t1.r3c3._phase_trace_valid, t1._phase_trace_valid)
        for relative in (
            "run_stage4_2r3c3t1_long_separation_zero_net_transport_identification_native.sh",
            "run_stop_stage4_2r3c3t1_now.sh",
        ):
            text = (self.root / relative).read_text(encoding="utf-8")
            self.assertNotIn("ray stop --force", text)
            self.assertNotIn("pkill", text)


if __name__ == "__main__":
    unittest.main()
