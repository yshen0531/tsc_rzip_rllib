import copy
import json
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np


runpy.run_path(str(Path(__file__).resolve().parent / "conftest.py"))

from tsc_rzip_rllib.diagnostics import (  # noqa: E402
    stage4_2r3c3t11_persistent_step_response_identification as t11,
)
from scripts import stage4_2r3c3t11_server_postprocess as postprocess  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t11_persistent_step_response_identification_500ms.json"
)


class Stage42R3C3T11Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_self_test_and_frozen_config(self) -> None:
        t11._validate_config(self.cfg)
        result = t11.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["expected_rollouts"], 416)
        self.assertFalse(result["real_tsc_executed"])

    def test_signed_schedules_are_bounded_delay_aware_and_zero_net(self) -> None:
        _, preflight = t11._authenticate_preflight(self.cfg)
        for case in preflight["actuator_cases"]:
            delay = int(case["delay_steps"])
            for probe in case["probe_schedules"]:
                positive = t11._signed_schedule(probe, sign=1)
                negative = t11._signed_schedule(probe, sign=-1)
                self.assertEqual(len(positive), 7)
                self.assertEqual(set(positive), set(negative))
                for step in positive:
                    np.testing.assert_array_equal(
                        positive[step], -negative[step]
                    )
                net = np.sum(np.stack(list(positive.values())), axis=0)
                self.assertLess(float(np.max(np.abs(net))), 1.0e-12)
                effects = sorted(step + delay + 1 for step in positive)
                self.assertEqual(
                    effects[0], int(probe["first_effect_state"])
                )
                self.assertEqual(effects[1:], [39, 40, 41, 42, 43, 44])
                self.assertLessEqual(
                    max(float(np.max(np.abs(x))) for x in positive.values()),
                    0.0075,
                )

    def test_build_specs_has_exact_416_unique_identities(self) -> None:
        templates = []
        for pair in range(4):
            for history in ("plus_first", "minus_first"):
                for target in ("nominal", "RZ_p10_m10"):
                    for delay, slew in ((0, 1.0), (2, 0.9)):
                        templates.append(
                            {
                                "pair_id": f"pair_{pair}",
                                "history_member": history,
                                "target_id": target,
                                "action_delay_steps": delay,
                                "slew_scale": slew,
                                "baseline_experiment_id": (
                                    f"base_{pair}_{history}_{target}_{delay}"
                                ),
                            }
                        )
        self.assertEqual(len(templates), 32)
        preflight_path, preflight = t11._authenticate_preflight(self.cfg)
        ctx = t11.Stage42R3C3T11Context(
            cfg=copy.deepcopy(self.cfg),
            base_config_path=ROOT
            / self.cfg["base_stage_config"],
            base_ctx=SimpleNamespace(
                source_ctx=object(),
                source_t1_fingerprint={"raw_inventory_digest": "digest"},
            ),
            preflight_path=preflight_path,
            preflight=preflight,
            t3_controller_bank_path=Path("bank.json"),
            paths=t11._paths(ROOT / ".codex_tmp" / "unused_t11_test"),
        )
        with mock.patch.object(
            t11.t1, "build_control_specs", return_value=templates
        ):
            specs = t11.build_control_specs(ctx, [])
        self.assertEqual(len(specs), 416)
        self.assertEqual(len({item["experiment_id"] for item in specs}), 416)
        self.assertEqual(
            sum(item["r3c3_probe_id"] == t11.BASELINE_PROBE_ID for item in specs),
            32,
        )
        self.assertEqual(
            sum(item["r3c3_probe_expected_issue_count"] == 7 for item in specs),
            384,
        )
        self.assertTrue(
            all(not item["source_action_available_to_controller"] for item in specs)
        )
        self.assertTrue(
            all(
                not item["pair_or_history_label_available_to_controller"]
                for item in specs
            )
        )

    def test_condition_gate_distinguishes_rank_and_condition(self) -> None:
        arrays = []
        for index in range(6):
            array = np.zeros((10, 3), dtype=float)
            array[3 + index // 2, index % 2] = 1.0
            arrays.append(array)
        rank, condition, passed = t11._condition_row(
            arrays, expected_rank=6, maximum=25.0
        )
        self.assertEqual(rank, 6)
        self.assertTrue(np.isfinite(condition))
        self.assertTrue(passed)
        rank, _, passed = t11._condition_row(
            [arrays[0]] * 6,
            expected_rank=6,
            maximum=25.0,
        )
        self.assertEqual(rank, 1)
        self.assertFalse(passed)

    def test_controller_contract_accepts_only_frozen_seven_issue_shapes(self) -> None:
        _, preflight = t11._authenticate_preflight(self.cfg)
        case = next(
            item
            for item in preflight["actuator_cases"]
            if int(item["delay_steps"]) == 0
        )
        base_init = (
            t11.t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController
            .__init__
        )
        with mock.patch.object(
            t11.t1.r3c1.AuthenticatedVisibleManifoldPhaseTaskController,
            "__init__",
            return_value=None,
        ):
            for probe in case["probe_schedules"]:
                schedule = t11._signed_schedule(probe, sign=1)
                spec = {
                    "action_delay_steps": 0,
                    "r3c3_probe_delta_by_task_issue_step": {
                        str(step): value.tolist()
                        for step, value in schedule.items()
                    },
                    "r3c3_probe_id": probe["probe_id"],
                    "r3c3_probe_mode": int(probe["mode_index"]),
                    "r3c3_probe_sign": 1,
                    "r3c3_probe_first_effect_state": int(
                        probe["first_effect_state"]
                    ),
                    "r3c3_probe_amplitude": 0.0075,
                }
                controller = t11.PersistentStepResponseProbeController(
                    object(), {}, spec, {}
                )
                self.assertEqual(len(controller.probe_schedule), 7)
            invalid = copy.deepcopy(spec)
            invalid["r3c3_probe_delta_by_task_issue_step"].pop(
                next(iter(invalid["r3c3_probe_delta_by_task_issue_step"]))
            )
            with self.assertRaises(ValueError):
                t11.PersistentStepResponseProbeController(
                    object(), {}, invalid, {}
                )
        self.assertIsNotNone(base_init)

    def test_resume_requires_exact_package_fingerprint(self) -> None:
        original = {
            "contract": "r42r3c3t11_deployed_package_source_v1",
            "digest": "exact-package",
            "files": [{"path": "source.py", "sha256": "same"}],
        }
        self.assertIsNone(
            t11._semantics_preserving_resume_compatibility(
                original, copy.deepcopy(original)
            )
        )
        changed = copy.deepcopy(original)
        changed["digest"] = "changed-package"
        with self.assertRaises(ValueError):
            t11._semantics_preserving_resume_compatibility(
                original, changed
            )
        self.assertEqual(
            postprocess._runtime_package_fingerprint(
                {"deployed_package_fingerprint": original}
            ),
            original,
        )

    def test_control_payload_uses_frozen_base_runtime_config(self) -> None:
        _, preflight = t11._authenticate_preflight(self.cfg)
        paths = t11._paths(ROOT / ".codex_tmp" / "unused_t11_payload_test")
        base_cfg = {
            "runtime": {"tsc_timeout_s": 321.0},
            "storage": {"placeholder": True},
        }
        ctx = t11.Stage42R3C3T11Context(
            cfg=copy.deepcopy(self.cfg),
            base_config_path=Path("base.json"),
            base_ctx=SimpleNamespace(
                cfg=base_cfg,
                source_ctx=SimpleNamespace(source_ctx=object()),
            ),
            preflight_path=Path("preflight.json"),
            preflight=preflight,
            t3_controller_bank_path=Path("bank.json"),
            paths=paths,
        )
        spec = {
            "experiment_id": "payload-test",
            "restart_snapshot_dir": "/server/snapshot",
            "restart_snapshot_manifest_digest": "a" * 64,
        }

        def frozen_payload(proxy, *, spec):
            self.assertIs(proxy.cfg, base_cfg)
            self.assertEqual(proxy.cfg["runtime"]["tsc_timeout_s"], 321.0)
            self.assertIs(proxy.source_ctx, ctx.base_ctx.source_ctx.source_ctx)
            return {
                "train_cfg": {
                    "episode": {"max_episode_steps": 37}
                }
            }

        with mock.patch.object(
            t11.t1.r3c3,
            "_control_payload",
            side_effect=frozen_payload,
        ), mock.patch.object(t11.t1.r3c3, "atomic_write_json"):
            payload = t11._control_payload(ctx, spec=spec)
        self.assertEqual(
            payload["train_cfg"]["episode"]["max_episode_steps"], 50
        )
        self.assertEqual(payload["stage4_1r4_horizon_steps"], 50)
        self.assertEqual(
            payload["stage4_2r3c3t11_restart_snapshot_dir"],
            spec["restart_snapshot_dir"],
        )

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
        manifest = {
            "digest": "a" * 64,
            "n_files": 4,
            "total_bytes": 123,
        }
        with mock.patch.object(
            postprocess.t11.t1.r3c3,
            "read_json",
            return_value=manifest,
        ), mock.patch.object(Path, "is_dir", return_value=True), mock.patch.object(
            Path, "is_file", return_value=True
        ), mock.patch.object(
            postprocess.t11.t1.r1,
            "_validate_snapshot_inventory",
            return_value=True,
        ):
            audit = postprocess._snapshot_integrity(specs)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["passed_count"], 1)

        changed = copy.deepcopy(specs)
        changed[1]["restart_snapshot_manifest_digest"] = "b" * 64
        conflict = postprocess._snapshot_integrity(changed)
        self.assertFalse(conflict["passed"])
        self.assertEqual(conflict["failed_count"], 1)


if __name__ == "__main__":
    unittest.main()
