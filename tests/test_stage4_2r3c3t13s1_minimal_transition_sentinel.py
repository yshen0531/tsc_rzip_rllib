import copy
import json
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np


runpy.run_path(str(Path(__file__).resolve().parent / "conftest.py"))

from scripts import stage4_2r3c3t13s1_server_postprocess as postprocess  # noqa: E402
from tsc_rzip_rllib.diagnostics import (  # noqa: E402
    stage4_2r3c3t13s1_minimal_transition_sentinel as t13s1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t13s1_minimal_transition_sentinel_500ms.json"
)


class Stage42R3C3T13S1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_self_test_and_frozen_config(self) -> None:
        t13s1._validate_config(self.cfg)
        result = t13s1.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["expected_rollouts"], 52)
        self.assertFalse(result["real_tsc_executed"])
        self.assertFalse(result["bc_dagger_or_rl_allowed"])

    def test_signed_schedules_are_adjacent_delay_aware_and_exact_zero_net(self) -> None:
        expected = {
            (0, "transport"): ([2, 3], [3, 4]),
            (0, "braking"): ([16, 17], [17, 18]),
            (2, "transport"): ([0, 1], [3, 4]),
            (2, "braking"): ([14, 15], [17, 18]),
        }
        for delay in (0, 2):
            for window in t13s1.WINDOWS:
                for mode in t13s1.MODES:
                    positive = t13s1._signed_schedule(
                        self.cfg,
                        delay=delay,
                        window=window,
                        mode=mode,
                        sign=1,
                    )
                    negative = t13s1._signed_schedule(
                        self.cfg,
                        delay=delay,
                        window=window,
                        mode=mode,
                        sign=-1,
                    )
                    self.assertEqual(sorted(positive), expected[(delay, window)][0])
                    self.assertEqual(
                        [step + delay + 1 for step in sorted(positive)],
                        expected[(delay, window)][1],
                    )
                    for step in positive:
                        np.testing.assert_array_equal(
                            positive[step], -negative[step]
                        )
                    np.testing.assert_array_equal(
                        np.sum(np.stack(list(positive.values())), axis=0),
                        np.zeros(3),
                    )

    def test_build_specs_selects_only_four_frozen_bookends(self) -> None:
        source_specs = []
        for index, row in enumerate(self.cfg["bookend_contexts"]):
            source_specs.append(
                {
                    "pair_id": row["pair_id"],
                    "history_member": row["history_member"],
                    "target_id": row["target_id"],
                    "action_delay_steps": row["action_delay_steps"],
                    "slew_scale": row["slew_scale"],
                    "baseline_experiment_id": f"baseline-{index}",
                    "state_generation_experiment_id": f"state-{index}",
                    "restart_snapshot_dir": f"/snapshot/{index}",
                    "restart_snapshot_manifest_digest": f"{index}" * 64,
                    "r3c3_probe_id": t13s1.t11.BASELINE_PROBE_ID,
                }
            )
        for index in range(28):
            source_specs.append(
                {
                    "pair_id": f"unused-{index}",
                    "history_member": "minus_first",
                    "target_id": "nominal",
                    "action_delay_steps": 0,
                    "slew_scale": 1.0,
                    "baseline_experiment_id": f"unused-baseline-{index}",
                    "state_generation_experiment_id": f"unused-state-{index}",
                    "restart_snapshot_dir": f"/unused/{index}",
                    "restart_snapshot_manifest_digest": "a" * 64,
                    "r3c3_probe_id": t13s1.t11.BASELINE_PROBE_ID,
                }
            )
        self.assertEqual(len(source_specs), 32)
        ctx = t13s1.Stage42R3C3T13S1Context(
            cfg=copy.deepcopy(self.cfg),
            base_config_path=ROOT / self.cfg["base_stage_config"],
            base_ctx=SimpleNamespace(
                base_ctx=SimpleNamespace(
                    source_t1_fingerprint={"raw_inventory_digest": "digest"}
                )
            ),
            paths=t13s1._paths(ROOT / ".codex_tmp" / "unused_t13s1_specs"),
        )
        with mock.patch.object(
            t13s1.t11, "build_control_specs", return_value=source_specs
        ):
            specs = t13s1.build_control_specs(ctx, [])
        self.assertEqual(len(specs), 52)
        self.assertEqual(len({spec["experiment_id"] for spec in specs}), 52)
        self.assertEqual(
            sum(spec["r3c3_probe_id"] == t13s1.BASELINE_PROBE_ID for spec in specs),
            4,
        )
        self.assertEqual(
            sum(spec["r3c3_probe_expected_issue_count"] == 2 for spec in specs),
            48,
        )
        self.assertTrue(
            all(not spec["pair_or_history_label_available_to_controller"] for spec in specs)
        )

    def test_underlying_controller_never_receives_probe_schedule_or_identity(self) -> None:
        spec = {
            "action_delay_steps": 0,
            "campaign_identity": t13s1.CAMPAIGN_IDENTITY,
            "r3c3_probe_delta_by_task_issue_step": {
                "2": [0.0075, 0.0, 0.0],
                "3": [-0.0075, 0.0, 0.0],
            },
            "r3c3_probe_id": "single_step_transport_mode0",
            "r3c3_probe_window": "transport",
            "r3c3_probe_mode": 0,
            "r3c3_probe_sign": 1,
            "r3c3_probe_first_effect_state": 3,
            "r3c3_probe_cancel_effect_state": 4,
            "r3c3_requested_probe_net": [0.0, 0.0, 0.0],
            "r3c3_probe_amplitude": 0.0075,
            "r3c3_probe_expected_issue_count": 2,
            "r3c3t13s1_schedule_contract": "adjacent_inverse_issue_single_physical_step_v1",
            "command_mode_subspace_residual_max_A": 1e-6,
            "scheduler_increment_residual_max_A": 1e-6,
            "controller_scale": 1.0,
        }
        received = {}

        def capture(_self, _base, _bundle, baseline_spec, _initial):
            received.update(baseline_spec)

        with mock.patch.object(
            t13s1.t11.t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController,
            "__init__",
            new=capture,
        ):
            controller = t13s1.SingleStepTransitionProbeController(
                object(), {}, spec, {}
            )
        self.assertEqual(len(controller.probe_schedule), 2)
        self.assertTrue(
            t13s1.SingleStepTransitionProbeController._WRAPPER_KEYS.isdisjoint(
                received
            )
        )

    def test_signal_floor_and_command_subspace_residual(self) -> None:
        floor = t13s1._signal_floor(33)
        expected = np.sqrt(
            2 * 33 * (1e-9 / 0.03) ** 2
            + 2 * 33 * (1e-7 / 0.1) ** 2
            + 33 * (1e-4 / 2000.0) ** 2
        )
        self.assertAlmostEqual(floor, expected)
        modes = np.zeros((14, 3))
        modes[:3] = np.eye(3)
        trace = [
            {"action_norm_tsc": [0.1, -0.2, 0.3] + [0.0] * 11}
        ]
        result = {"spec": {"slew_scale": 0.9}, "controller_trace": trace}
        self.assertLessEqual(
            t13s1._command_modal_residual(result, modes, 100.0), 1e-12
        )
        trace[0]["action_norm_tsc"][3] = 0.01
        self.assertGreater(
            t13s1._command_modal_residual(result, modes, 100.0), 0.1
        )

    def test_resume_requires_exact_fingerprint_and_preserves_completed_raw(self) -> None:
        original = {
            "contract": "r42r3c3t13s1_deployed_package_source_v1",
            "digest": "exact",
            "files": [{"path": "source.py", "sha256": "same"}],
        }
        self.assertIsNone(
            t13s1._semantics_preserving_resume_compatibility(
                original, copy.deepcopy(original)
            )
        )
        changed = copy.deepcopy(original)
        changed["digest"] = "changed"
        with self.assertRaises(ValueError):
            t13s1._semantics_preserving_resume_compatibility(
                original, changed
            )
        spec = {"experiment_id": "raw-id"}
        result = {
            "completed": True,
            "stage": t13s1.STAGE,
            "campaign_identity": t13s1.CAMPAIGN_IDENTITY,
            "controller_revision": t13s1.CONTROLLER_REVISION,
            "experiment_id": "raw-id",
            "spec": spec,
            "success": True,
            "trajectory": [],
            "controller_trace": [],
        }
        with mock.patch.object(Path, "is_file", return_value=True), mock.patch.object(
            t13s1.t11.t1.r3c3, "read_json_gz", return_value=result
        ):
            self.assertTrue(t13s1._result_complete(Path("raw.json.gz"), spec))

    def test_snapshot_audit_requires_one_exact_identity_per_state(self) -> None:
        specs = [
            {
                "state_generation_experiment_id": "state-a",
                "restart_snapshot_dir": "/server/snapshot-a",
                "restart_snapshot_manifest_digest": "a" * 64,
            },
            {
                "state_generation_experiment_id": "state-a",
                "restart_snapshot_dir": "/server/snapshot-a",
                "restart_snapshot_manifest_digest": "a" * 64,
            },
        ]
        manifest = {"digest": "a" * 64, "n_files": 8, "total_bytes": 123}
        with mock.patch.object(
            postprocess.t13s1.t11.t1.r3c3, "read_json", return_value=manifest
        ), mock.patch.object(Path, "is_dir", return_value=True), mock.patch.object(
            Path, "is_file", return_value=True
        ), mock.patch.object(
            postprocess.t13s1.t11.t1.r1,
            "_validate_snapshot_inventory",
            return_value=True,
        ):
            audit = postprocess._snapshot_integrity(specs)
        self.assertTrue(audit["passed"])
        changed = copy.deepcopy(specs)
        changed[1]["restart_snapshot_manifest_digest"] = "b" * 64
        conflict = postprocess._snapshot_integrity(changed)
        self.assertFalse(conflict["passed"])


if __name__ == "__main__":
    unittest.main()
