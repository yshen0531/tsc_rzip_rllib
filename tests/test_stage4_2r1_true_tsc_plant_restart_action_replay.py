from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from tsc_rzip_rllib.core.runner import TSCStepRunner
from tsc_rzip_rllib.diagnostics import (
    stage4_2r1_true_tsc_plant_restart_action_replay as r42,
)
from tsc_rzip_rllib.envs.rzip_env import TscRzipEnv


class Stage42R1ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(r42.__file__).resolve().parents[2]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_config_is_valid_and_keeps_original_timing(self) -> None:
        r42.validate_config(self.cfg)
        checkpoint = self.cfg["checkpoint"]
        self.assertEqual(checkpoint["checkpoint_step"], 20)
        self.assertEqual(checkpoint["normal_horizon_steps"], 35)
        self.assertEqual(checkpoint["weak_horizon_steps"], 37)
        contract = self.cfg["formal_timing_contract"]
        self.assertEqual(contract["normal_slew"]["arrival_deadline_step"], 25)
        self.assertEqual(contract["normal_slew"]["hold_through_step"], 35)
        self.assertEqual(contract["weak_slew"]["arrival_deadline_step"], 27)
        self.assertEqual(contract["weak_slew"]["hold_through_step"], 37)
        self.assertFalse(contract["arrival_deadline_expansion_allowed"])
        self.assertTrue(self.cfg["plant_restart_only"])
        self.assertFalse(checkpoint["controller_checkpoint_replay_in_this_stage"])

    def test_scientific_guard_weakening_is_rejected(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["checkpoint"]["checkpoint_step"] = 21
        with self.assertRaisesRegex(ValueError, "checkpoint step"):
            r42.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["checkpoint"]["require_full_wire_current_vector"] = False
        with self.assertRaisesRegex(ValueError, "scientific guard"):
            r42.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["checkpoint"]["controller_checkpoint_replay_in_this_stage"] = True
        with self.assertRaisesRegex(ValueError, "isolate plant restart"):
            r42.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] = 28
        with self.assertRaisesRegex(ValueError, "weak formal timing"):
            r42.validate_config(cfg)
        cfg = copy.deepcopy(self.cfg)
        cfg["true_filesystem_tsc_restart_executed"] = True
        with self.assertRaisesRegex(ValueError, "pre-claims"):
            r42.validate_config(cfg)


    def test_hotfix_revision_accepts_only_known_legacy_manifests(self) -> None:
        self.assertEqual(r42.PACKAGE_REVISION, "r42r1b_lazy_runner_capture_resume_v3")
        self.assertIn("r42r1_plant_restart_action_replay_v1", r42.LEGACY_PACKAGE_REVISIONS)
        self.assertIn(
            "r42r1a_capture_failure_finite_summary_v2",
            r42.LEGACY_PACKAGE_REVISIONS,
        )

    def test_self_test_passes_and_budget_is_fixed(self) -> None:
        payload = r42.self_test()
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["expected_capture_rollouts"], 18)
        self.assertEqual(payload["expected_restart_rollouts"], 18)
        self.assertEqual(payload["maximum_true_tsc_rollouts"], 36)
        self.assertTrue(payload["plant_restart_only"])
        self.assertFalse(payload["controller_checkpoint_replay_validated"])


class Stage42R1TraceTests(unittest.TestCase):
    @staticmethod
    def synthetic(horizon: int = 37, wire_count: int = 4) -> dict:
        trajectory = []
        for step in range(horizon + 1):
            action = [0.0] * 14 if step == 0 else [step / 1000.0] * 14
            trajectory.append(
                {
                    "step_index": step,
                    "time_ms": 1100 + 10 * step,
                    "R": 0.75 + step * 1e-6,
                    "Z": -step * 1e-6,
                    "Ip": 29779.724 + step,
                    "vessel_current_total_a": float(step),
                    "vessel_current_abs_sum_a": float(step + 1),
                    "vessel_current_rms_a": float(step + 2),
                    "vessel_current_max_abs_a": float(step + 3),
                    "currents_a_tsc": [float(step + index) for index in range(14)],
                    "currents_a_display": [float(step + index) for index in range(14)],
                    "action_norm_tsc": action,
                    "action_norm_display": action,
                    "wire_currents_a": [float(step + index) for index in range(wire_count)],
                    "wire_current_count": wire_count,
                    "abnormal": False,
                }
            )
        return {"trajectory": trajectory}

    def test_source_action_sequence_maps_transitions(self) -> None:
        source = self.synthetic()
        actions = r42._source_action_sequence(source, horizon=37)
        self.assertEqual(len(actions), 37)
        self.assertEqual(actions[0], source["trajectory"][1]["action_norm_tsc"])
        self.assertEqual(actions[-1], source["trajectory"][37]["action_norm_tsc"])
        self.assertEqual(r42._source_initial_action(source), source["trajectory"][0]["action_norm_tsc"])

    def test_visible_and_full_wire_arrays_preserve_shapes(self) -> None:
        source = self.synthetic()
        self.assertEqual(r42._visible_array(source).shape, (38, 35))
        self.assertEqual(r42._wire_array(source).shape, (38, 4))

    def test_full_wire_array_rejects_inconsistent_width(self) -> None:
        source = self.synthetic()
        source["trajectory"][4]["wire_currents_a"] = [1.0, 2.0]
        with self.assertRaisesRegex(ValueError, "shape changed"):
            r42._wire_array(source)

    def test_recombine_uses_capture_prefix_and_restart_suffix_once(self) -> None:
        source = self.synthetic()
        capture = self.synthetic()
        restart = {
            "restart_trajectory": copy.deepcopy(source["trajectory"][20:]),
        }
        original = {
            "trajectory": source["trajectory"],
            "spec": {"target_id": "nominal", "action_delay_steps": 0, "slew_scale": 0.9},
        }
        combined = r42._recombined_result(original, capture, restart, horizon=37)
        self.assertEqual(len(combined["trajectory"]), 38)
        self.assertEqual(combined["trajectory"], source["trajectory"])

    def test_compare_arrays_distinguishes_exact_and_numeric(self) -> None:
        left = np.asarray([[1.0, 2.0]])
        tiny = np.asarray([[1.0, 2.0 + 1e-13]])
        exact = r42._compare_arrays(left, left, atol=1e-12)
        self.assertTrue(exact["exact"])
        numeric = r42._compare_arrays(left, tiny, atol=1e-12)
        self.assertFalse(numeric["exact"])
        self.assertTrue(numeric["numeric"])



    def test_shape_mismatch_is_structured_finite_json(self) -> None:
        left = np.empty((0, 0), dtype=float)
        right = np.ones((3, 2), dtype=float)
        result = r42._compare_arrays(left, right, atol=0.0)
        self.assertFalse(result["comparable"])
        self.assertEqual(result["mismatch_reason"], "shape_mismatch")
        self.assertIsNone(result["maximum_abs_difference"])
        json.dumps(result, allow_nan=False)

    def test_finite_metric_max_rejects_missing_comparisons(self) -> None:
        self.assertEqual(r42._finite_metric_max([{"x": 0.0}, {"x": 1.0}], "x"), 1.0)
        self.assertIsNone(r42._finite_metric_max([{"x": 0.0}, {"x": None}], "x"))

class Stage42R1SnapshotTests(unittest.TestCase):
    REQUIRED = [
        "inputa",
        "sprsina",
        "geqdsk",
        "outputa",
        "coil_currents.csv",
        "wire_currents.csv",
    ]

    def test_snapshot_inventory_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in self.REQUIRED:
                (root / name).write_text(name + "\n", encoding="utf-8")
            cfg = {"required_snapshot_files": self.REQUIRED, "optional_snapshot_files": []}
            inventory = r42._snapshot_file_inventory(root, cfg)
            self.assertTrue(inventory["passed"])
            self.assertTrue(r42._validate_snapshot_inventory(root, inventory))
            forged = copy.deepcopy(inventory)
            forged["files"][0]["size_bytes"] += 1
            self.assertFalse(r42._validate_snapshot_inventory(root, forged))
            (root / "sprsina").write_text("tampered\n", encoding="utf-8")
            self.assertFalse(r42._validate_snapshot_inventory(root, inventory))

    def test_snapshot_wire_vector_uses_runner_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pd.DataFrame({"cwire(ka)": [1.25, -0.5]}).to_csv(
                root / "wire_currents.csv", index=False
            )
            actual = r42._snapshot_wire_vector_a(
                root, column_name="cwire(ka)", raw_to_a=1000.0
            )
            np.testing.assert_array_equal(actual, np.asarray([1250.0, -500.0]))
            with self.assertRaisesRegex(ValueError, "missing"):
                r42._snapshot_wire_vector_a(
                    root, column_name="wrong", raw_to_a=1000.0
                )

    def test_runner_snapshot_request_is_one_shot_and_clearable(self) -> None:
        runner = TSCStepRunner.__new__(TSCStepRunner)
        runner._restart_snapshot_requests = {}
        runner.request_restart_snapshot(local_step_index=20, destination=Path("/tmp/a"))
        self.assertEqual(runner._restart_snapshot_requests[20], Path("/tmp/a").resolve())
        with self.assertRaisesRegex(ValueError, "already targets"):
            runner.request_restart_snapshot(local_step_index=20, destination=Path("/tmp/b"))
        runner.clear_restart_snapshot_requests()
        self.assertEqual(runner._restart_snapshot_requests, {})

    def test_runner_export_snapshot_requires_complete_plant_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            destination = root / "snapshot"
            runtime.mkdir()
            for name in [
                "inputa",
                "sprsina",
                "geqdsk",
                "outputa",
                "coil_currents.csv",
                "wire_currents.csv",
            ]:
                (runtime / name).write_text(name, encoding="utf-8")
            runner = TSCStepRunner.__new__(TSCStepRunner)
            runner.cfg = SimpleNamespace(runtime_only_fast_mode=True)
            runner.runtime_tsc_dir = runtime
            runner.current_time_ms = 1300
            runner.current_folder = runtime
            runner.local_step_index = 20
            runner._copy_runtime_artifacts_to = lambda dst: [
                (Path(dst) / path.name).write_bytes(path.read_bytes())
                for path in runtime.iterdir()
            ]
            metadata = runner.export_restart_snapshot(destination)
            self.assertEqual(metadata["local_step_index"], 20)
            self.assertEqual(metadata["time_ms"], 1300)
            self.assertTrue((destination / "sprsina").is_file())

    def test_resume_keeps_only_complete_untampered_successful_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "snapshot"
            snapshot.mkdir()
            for name in self.REQUIRED:
                (snapshot / name).write_text(name + "\n", encoding="utf-8")
            checkpoint_cfg = {
                "required_snapshot_files": self.REQUIRED,
                "optional_snapshot_files": [],
            }
            inventory = r42._snapshot_file_inventory(snapshot, checkpoint_cfg)
            manifest_path = snapshot / "restart_snapshot_manifest.json"
            r42.atomic_write_json(manifest_path, inventory)
            raw_path = root / "capture.json.gz"
            result = {
                "success": True,
                "restart_snapshot": {
                    "snapshot_dir": str(snapshot),
                    "snapshot_manifest_path": str(manifest_path),
                    "snapshot_manifest_digest": inventory["digest"],
                    "snapshot_files_valid": True,
                    "snapshot_wire_vector_exact_to_capture_state": True,
                },
            }
            r42.atomic_write_json_gz(raw_path, result)
            self.assertTrue(r42._capture_snapshot_complete(raw_path))
            (snapshot / "sprsina").write_text("tampered\n", encoding="utf-8")
            self.assertFalse(r42._capture_snapshot_complete(raw_path))

    def test_runner_consumes_snapshot_request_in_fast_mode(self) -> None:
        runner = TSCStepRunner.__new__(TSCStepRunner)
        runner.cfg = SimpleNamespace(
            runtime_only_fast_mode=True,
            save_step_artifacts=False,
            save_artifacts_every_n_steps=0,
        )
        runner.local_step_index = 20
        runner._restart_snapshot_requests = {20: Path("/tmp/snapshot")}
        called = []
        runner.export_restart_snapshot = lambda path: called.append(path)
        runner._maybe_save_runtime_step_artifacts()
        self.assertEqual(called, [Path("/tmp/snapshot")])
        self.assertEqual(runner._restart_snapshot_requests, {})

    def test_base_worker_chain_is_explicit(self) -> None:
        base = object()
        container = SimpleNamespace(
            inner=SimpleNamespace(
                inner=SimpleNamespace(inner=SimpleNamespace(base_worker=base))
            )
        )
        self.assertIs(r42._base_worker_from_container(container), base)

    def test_capture_worker_uses_real_env_lazy_runner_interface(self) -> None:
        class NoFilesystemRunner:
            def __init__(self, cfg, worker_id=None, keep_workspace=None):
                self.cfg = cfg
                self.worker_id = worker_id
                self.keep_workspace = keep_workspace

        env = TscRzipEnv.__new__(TscRzipEnv)
        env.cfg = SimpleNamespace(start_folder="1100ms", dt_ms=10)
        env.worker_id = "stage42r1_lifecycle_test"
        env.keep_tsc_workspace = False
        env.runner = None
        worker = r42.LocalPlantReplayWorker.__new__(r42.LocalPlantReplayWorker)
        worker.base_worker = SimpleNamespace(env=env)
        self.assertIsNone(worker.runner)
        with mock.patch(
            "tsc_rzip_rllib.envs.rzip_env.TSCStepRunner",
            NoFilesystemRunner,
        ):
            runner = worker._ensure_runner()
        self.assertIs(runner, env.runner)
        self.assertEqual(runner.cfg.start_folder, "1100ms")
        self.assertIs(worker._ensure_runner(), runner)

    def test_inventory_paths_are_canonical_posix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "nested"
            nested.mkdir()
            evidence = nested / "evidence.json"
            evidence.write_text("{}\n", encoding="utf-8")
            inventory = r42._inventory(
                root,
                [evidence],
                contract="test",
                stage="test",
            )
        self.assertEqual(inventory["files"][0]["relative_path"], "nested/evidence.json")

    def test_resume_expert_inventory_ignores_only_absolute_locator_root(self) -> None:
        row = {
            "target_id": "nominal",
            "actual_delay_steps": 0,
            "actual_slew_scale": 1.0,
            "experiment_id": "source_case",
            "path": "/home/server/project/raw/source_case.json.gz",
            "size_bytes": 123,
            "sha256": "a" * 64,
        }
        recorded = {
            "schema_version": 1,
            "source_stage": "Stage4.1R17 formal expert map",
            "inventory_contract": "test",
            "n_files": 1,
            "total_bytes": 123,
            "digest": "server-path-dependent",
            "files": [row],
        }
        current = copy.deepcopy(recorded)
        current["digest"] = "windows-path-dependent"
        current["files"][0]["path"] = (
            "C:/workspace/project/raw/source_case.json.gz"
        )
        self.assertTrue(
            r42._selected_expert_inventory_compatible(recorded, current)
        )
        current["files"][0]["sha256"] = "b" * 64
        self.assertFalse(
            r42._selected_expert_inventory_compatible(recorded, current)
        )

    def test_analyze_preserves_not_run_restart_tristate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = SimpleNamespace(
                analysis=root / "analysis",
                source_audit=root / "source_audit",
                capture=root / "capture",
                restart=root / "restart",
                state=root / "state.json",
            )
            for directory in (
                paths.analysis,
                paths.source_audit,
                paths.capture,
                paths.restart,
            ):
                directory.mkdir()
            ctx = SimpleNamespace(
                paths=paths,
                source_stage41r17_run=Path("stage4_1r17_source"),
                cfg={"final_task": "reliable MPC expert"},
            )
            result = r42.analyze(
                ctx,
                source_audit={"passed": True},
                capture={"passed": False},
                restart={},
            )
        self.assertEqual(result["plant_restart_replay_status"], "not_run")
        self.assertIsNone(result["plant_restart_fidelity_passed"])
        self.assertIsNone(result["formal_contract_preserved"])
        self.assertEqual(result["formal_contract_preservation_status"], "not_run")

    def test_capture_summary_does_not_count_missing_snapshot_paths(self) -> None:
        keys = [
            (target, delay, slew)
            for target in ("nominal", "RZ_p10_m10")
            for delay in (0, 1, 2)
            for slew in (0.9, 1.0, 1.1)
        ]
        rows = []
        for target, delay, slew in keys:
            rows.append(
                {
                    "experiment_id": f"{target}_{delay}_{slew}",
                    "target_id": target,
                    "actual_delay_steps": delay,
                    "actual_slew_scale": slew,
                    "environment_success": False,
                    "failure_reason": "runner not initialized",
                    "capture_visible_exact_to_source": False,
                    "source_actions_exactly_replayed": False,
                    "capture_visible_maximum_abs_difference": None,
                    "source_action_maximum_abs_difference": None,
                    "capture_visible_comparable": False,
                    "source_action_comparable": False,
                    "capture_exception_stage": "prepare_replay",
                    "snapshot_files_valid": False,
                    "snapshot_wire_exact_to_capture_checkpoint": False,
                    "full_wire_current_vector_present": False,
                    "snapshot_dir": "",
                    "wire_current_count": 0,
                    "passed": False,
                }
            )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = SimpleNamespace(capture=root / "capture", state=root / "state.json")
            paths.capture.mkdir()
            ctx = SimpleNamespace(
                paths=paths,
                cfg={"matrix": {"expected_capture_rollouts": 18}},
            )
            with mock.patch.object(
                r42,
                "_safe_capture_result_row",
                side_effect=rows,
            ), mock.patch.object(
                r42,
                "_selected_source_cases",
                return_value={key: {} for key in keys},
            ):
                summary = r42._summarize_capture(ctx, [{} for _ in rows])
        self.assertEqual(summary["distinct_snapshot_paths"], 0)
        self.assertEqual(
            summary["capture_trace_comparison_status"],
            "not_comparable",
        )
        self.assertFalse(
            summary["plant_capture_instrumentation_changed_source_trace"]
        )


if __name__ == "__main__":
    unittest.main()
