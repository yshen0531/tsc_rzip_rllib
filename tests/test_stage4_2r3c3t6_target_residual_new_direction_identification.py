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
    stage4_2r3c3t6_target_residual_new_direction_identification as t6,
)
from scripts import stage4_2r3c3t6_server_postprocess as postprocess  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t6_target_residual_new_direction_identification_500ms.json"
)


class Stage42R3C3T6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_self_test_and_frozen_config(self) -> None:
        t6._validate_config(self.cfg)
        result = t6.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["expected_rollouts"], 224)
        self.assertFalse(result["real_tsc_executed"])

    def test_signed_schedules_are_bounded_delay_aware_and_zero_net(self) -> None:
        _, preflight = t6._authenticate_preflight(self.cfg)
        for case in preflight["actuator_cases"]:
            delay = int(case["delay_steps"])
            hold = int(case["formal_hold_step"])
            for probe in case["probe_schedules"]:
                positive = t6._signed_schedule(probe, sign=1)
                negative = t6._signed_schedule(probe, sign=-1)
                self.assertEqual(len(positive), 41)
                self.assertEqual(set(positive), set(negative))
                for step in positive:
                    np.testing.assert_array_equal(
                        positive[step], -negative[step]
                    )
                net = np.sum(np.stack(list(positive.values())), axis=0)
                self.assertLess(float(np.max(np.abs(net))), 1.0e-12)
                effects = sorted(step + delay + 1 for step in positive)
                self.assertEqual(
                    effects[:35], list(range(delay + 1, hold + 1))
                )
                self.assertEqual(effects[35:], [39, 40, 41, 42, 43, 44])
                self.assertLessEqual(
                    max(float(np.max(np.abs(x))) for x in positive.values()),
                    0.0075,
                )

    def test_build_specs_has_exact_224_unique_identities(self) -> None:
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
        preflight_path, preflight = t6._authenticate_preflight(self.cfg)
        ctx = t6.Stage42R3C3T6Context(
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
            paths=t6._paths(ROOT / ".codex_tmp" / "unused_t6_test"),
        )
        with mock.patch.object(
            t6.t1, "build_control_specs", return_value=templates
        ):
            specs = t6.build_control_specs(ctx, [])
        self.assertEqual(len(specs), 224)
        self.assertEqual(len({item["experiment_id"] for item in specs}), 224)
        self.assertEqual(
            sum(item["r3c3_probe_id"] == t6.BASELINE_PROBE_ID for item in specs),
            32,
        )
        self.assertEqual(
            sum(item["r3c3_probe_expected_issue_count"] == 41 for item in specs),
            192,
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
        grid = np.arange(20, dtype=float).reshape(10, 2)
        arrays = [
            np.column_stack([grid[:, 0] ** index, grid[:, 1] ** index])
            for index in (1, 2, 3)
        ]
        rank, condition, passed = t6._condition_row(
            arrays, expected_rank=3, maximum=1.0e9
        )
        self.assertEqual(rank, 3)
        self.assertTrue(np.isfinite(condition))
        self.assertTrue(passed)
        rank, _, passed = t6._condition_row(
            [arrays[0], arrays[0], arrays[0]],
            expected_rank=3,
            maximum=1.0e9,
        )
        self.assertEqual(rank, 1)
        self.assertFalse(passed)

    def test_t3_bank_key_uses_tsc_order_not_display_order(self) -> None:
        tsc_currents = [float(index) for index in range(t6.N_COILS)]
        display_currents = list(reversed(tsc_currents))
        sample = {
            "initial_R_m": 2.96,
            "initial_Z_m": 0.03,
            "initial_Ip_A": 1.1e6,
            "initial_coil_currents_A": tsc_currents,
            "target_R_offset_m": 0.01,
            "target_Z_offset_m": -0.01,
            "target_Ip_offset_A": 0.0,
            "actuator_delay_steps": 2,
            "actuator_slew_scale": 0.9,
        }
        result = {
            "trajectory": [
                {
                    "R": sample["initial_R_m"],
                    "Z": sample["initial_Z_m"],
                    "Ip": sample["initial_Ip_A"],
                    "currents_a_tsc": tsc_currents,
                    "currents_a_display": display_currents,
                }
            ],
            "spec": {
                "target_R_offset_m": sample["target_R_offset_m"],
                "target_Z_offset_m": sample["target_Z_offset_m"],
                "target_Ip_offset_A": sample["target_Ip_offset_A"],
                "action_delay_steps": sample["actuator_delay_steps"],
                "slew_scale": sample["actuator_slew_scale"],
            },
        }
        self.assertNotEqual(tsc_currents, display_currents)
        self.assertEqual(
            t6._result_sample_key(result), t6._t3_sample_key(sample)
        )

    def test_summary_hotfix_accepts_only_exact_bound_delta(self) -> None:
        runtime_path = (
            "tsc_rzip_rllib/diagnostics/"
            "stage4_2r3c3t6_target_residual_new_direction_identification.py"
        )
        postprocess_path = "scripts/stage4_2r3c3t6_server_postprocess.py"
        test_path = (
            "tests/"
            "test_stage4_2r3c3t6_target_residual_new_direction_identification.py"
        )
        contract_path = (
            t6.SEMANTICS_PRESERVING_SUMMARY_HOTFIX_RELATIVE_PATH
        )
        original_rows = [
            {"path": "PACKAGE_MANIFEST.json", "sha256": "old-manifest"},
            {"path": "SHA256SUMS", "sha256": "old-sums"},
            {
                "path": runtime_path,
                "sha256": t6.INITIAL_RUNTIME_SOURCE_SHA256,
            },
            {
                "path": postprocess_path,
                "sha256": t6.INITIAL_POSTPROCESS_SOURCE_SHA256,
            },
            {
                "path": test_path,
                "sha256": t6.INITIAL_TEST_SOURCE_SHA256,
            },
            {"path": "unchanged.py", "sha256": "same"},
        ]
        active_rows = copy.deepcopy(original_rows)
        replacements = {
            "PACKAGE_MANIFEST.json": "new-manifest",
            "SHA256SUMS": "new-sums",
            runtime_path: "new-runtime",
            postprocess_path: "new-postprocess",
            test_path: "new-test",
        }
        for row in active_rows:
            if row["path"] in replacements:
                row["sha256"] = replacements[row["path"]]
        active_rows.append(
            {"path": contract_path, "sha256": "contract"}
        )
        original = {
            "contract": "r42r3c3t6_deployed_package_source_v1",
            "digest": t6.INITIAL_DEPLOYED_PACKAGE_DIGEST,
            "files": original_rows,
        }
        active = {
            "contract": original["contract"],
            "digest": "new-package",
            "files": active_rows,
        }
        contract = {
            "schema_version": 1,
            "hotfix_id": t6.SEMANTICS_PRESERVING_SUMMARY_HOTFIX_ID,
            "stage": t6.STAGE,
            "controller_revision": t6.CONTROLLER_REVISION,
            "package_revision": t6.PACKAGE_REVISION,
            "from_deployed_package_digest": (
                t6.INITIAL_DEPLOYED_PACKAGE_DIGEST
            ),
            "from_runtime_source_sha256": (
                t6.INITIAL_RUNTIME_SOURCE_SHA256
            ),
            "to_runtime_source_sha256": "new-runtime",
            "from_postprocess_source_sha256": (
                t6.INITIAL_POSTPROCESS_SOURCE_SHA256
            ),
            "to_postprocess_source_sha256": "new-postprocess",
            "from_test_source_sha256": t6.INITIAL_TEST_SOURCE_SHA256,
            "to_test_source_sha256": "new-test",
            "controller_action_semantics_changed": False,
            "reporting_logic_only": True,
            "raw_results_unchanged": True,
            "task_matrix_unchanged": True,
            "formal_gate_unchanged": True,
            "experiment_ids_unchanged": True,
            "source_fingerprints_unchanged": True,
            "summary_bug": (
                "T3 bank currents were matched to display-order instead "
                "of TSC-order currents"
            ),
            "corrected_field": "trajectory[0].currents_a_tsc",
        }
        with mock.patch.object(Path, "is_file", return_value=True), mock.patch.object(
            t6.t1.r3c3, "read_json", return_value=contract
        ):
            self.assertEqual(
                t6._semantics_preserving_resume_compatibility(
                    original, active
                ),
                contract,
            )
            incompatible = copy.deepcopy(active)
            incompatible["files"][-1]["path"] = "unexpected.py"
            with self.assertRaises(ValueError):
                t6._semantics_preserving_resume_compatibility(
                    original, incompatible
                )

        manifest = {
            "deployed_package_fingerprint": original,
            "semantics_preserving_summary_hotfix": {
                "contract": contract,
                "original_deployed_package_digest": original["digest"],
                "active_deployed_package_digest": active["digest"],
                "active_deployed_package_fingerprint": active,
            },
        }
        self.assertEqual(
            postprocess._runtime_package_fingerprint(manifest), active
        )

    def test_control_payload_uses_frozen_base_runtime_config(self) -> None:
        _, preflight = t6._authenticate_preflight(self.cfg)
        paths = t6._paths(ROOT / ".codex_tmp" / "unused_t6_payload_test")
        base_cfg = {
            "runtime": {"tsc_timeout_s": 321.0},
            "storage": {"placeholder": True},
        }
        ctx = t6.Stage42R3C3T6Context(
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
            t6.t1.r3c3,
            "_control_payload",
            side_effect=frozen_payload,
        ), mock.patch.object(t6.t1.r3c3, "atomic_write_json"):
            payload = t6._control_payload(ctx, spec=spec)
        self.assertEqual(
            payload["train_cfg"]["episode"]["max_episode_steps"], 50
        )
        self.assertEqual(payload["stage4_1r4_horizon_steps"], 50)
        self.assertEqual(
            payload["stage4_2r3c3t6_restart_snapshot_dir"],
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
            postprocess.t6.t1.r3c3,
            "read_json",
            return_value=manifest,
        ), mock.patch.object(Path, "is_dir", return_value=True), mock.patch.object(
            Path, "is_file", return_value=True
        ), mock.patch.object(
            postprocess.t6.t1.r1,
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
