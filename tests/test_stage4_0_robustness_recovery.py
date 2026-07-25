from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tsc_rzip_rllib.diagnostics import stage4_0_robustness_recovery as s40


class Stage40Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_path = Path(__file__).resolve().parents[1] / "configs/stage4_0_robustness_recovery_350ms.json"
        self.cfg = json.loads(self.config_path.read_text(encoding="utf-8"))

    def test_campaign_is_explicitly_192_workers(self) -> None:
        self.assertEqual(self.cfg["parallel"]["n_workers"], 192)
        self.assertGreaterEqual(self.cfg["parallel"]["reserve_logical_cpus"], 8)

    def test_heldout_targets_are_unique(self) -> None:
        points = {
            (row["R_offset_m"], row["Z_offset_m"], row["Ip_offset_A"])
            for row in self.cfg["heldout_targets"]["scenarios"]
        }
        self.assertEqual(len(points), len(self.cfg["heldout_targets"]["scenarios"]))
        self.assertGreaterEqual(len(points), 16)

    def test_failure_recovery_contains_escalation_ladders(self) -> None:
        amplitudes = self.cfg["failure_recovery"]["amplitudes_by_mode"]
        self.assertEqual(set(amplitudes), {"0", "1", "2"})
        self.assertTrue(all(len(values) >= 5 for values in amplitudes.values()))
        self.assertEqual(self.cfg["failure_recovery"]["signs"], [-1, 1])

    def test_pair_summary_detects_recovery_and_loss(self) -> None:
        rows = [
            {"scenario": "a", "category": "x", "controller_scale": 0.0, "experiment_id": "a0", "stage3_4_target_tracking_pass": False, "stage3_4_tracking_minimum_signed_margin": -0.2},
            {"scenario": "a", "category": "x", "controller_scale": 0.5, "experiment_id": "a1", "stage3_4_target_tracking_pass": True, "stage3_4_tracking_minimum_signed_margin": 0.1},
            {"scenario": "b", "category": "x", "controller_scale": 0.0, "experiment_id": "b0", "stage3_4_target_tracking_pass": True, "stage3_4_tracking_minimum_signed_margin": 0.1},
            {"scenario": "b", "category": "x", "controller_scale": 0.5, "experiment_id": "b1", "stage3_4_target_tracking_pass": False, "stage3_4_tracking_minimum_signed_margin": -0.1},
        ]
        pairs, summary = s40.summarize_pairs(rows, ("scenario", "category"))
        self.assertEqual(len(pairs), 2)
        self.assertEqual(summary["n_recovered"], 1)
        self.assertEqual(summary["n_lost"], 1)

    def test_runtime_preflight_accepts_192_on_208_cpu_host(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        with mock.patch("os.cpu_count", return_value=208), mock.patch.object(s40, "_available_memory_gb", return_value=200.0), mock.patch("resource.getrlimit", return_value=(65536, 65536)), mock.patch.dict(os.environ, {"STAGE4_WORKERS": "192"}, clear=False):
            plan = s40.runtime_preflight(ctx)
        self.assertEqual(plan["requested_workers"], 192)
        self.assertEqual(plan["safe_worker_ceiling"], 192)

    def test_runtime_preflight_refuses_silent_fallback(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        with mock.patch("os.cpu_count", return_value=128), mock.patch.object(s40, "_available_memory_gb", return_value=200.0), mock.patch("resource.getrlimit", return_value=(65536, 65536)), mock.patch.dict(os.environ, {"STAGE4_WORKERS": "192"}, clear=False):
            with self.assertRaises(RuntimeError):
                s40.runtime_preflight(ctx)

    def test_restart_discovery_uses_only_existing_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("1080ms", "1090ms", "1100ms", "1110ms"):
                (root / name).mkdir()
            ctx = SimpleNamespace(
                cfg=self.cfg,
                source_env_cfg={"simulation_root": str(root), "start_folder": "1100ms"},
            )
            with mock.patch.dict(os.environ, {"STAGE4_START_FOLDERS": "1080ms,missing,1110ms"}, clear=False):
                folders = s40.discover_restart_folders(ctx)
            self.assertIn("1080ms", folders)
            self.assertIn("1090ms", folders)
            self.assertIn("1110ms", folders)
            self.assertNotIn("1100ms", folders)
            self.assertNotIn("missing", folders)

    def test_spec_ids_change_with_noise_seed_and_variant(self) -> None:
        target = {"target_id": "n", "R_offset_m": 0.0, "Z_offset_m": 0.0, "Ip_offset_A": 0.0}
        a = s40._make_spec(phase="p", scenario="s", category="c", target=target, controller_scale=0.5, extra={"observation_noise": {"seed": 1}})
        b = s40._make_spec(phase="p", scenario="s", category="c", target=target, controller_scale=0.5, extra={"observation_noise": {"seed": 2}})
        c = s40._make_spec(phase="p", scenario="s", category="c", target=target, controller_scale=0.5, environment_variant="restart_1090ms", extra={"observation_noise": {"seed": 1}})
        self.assertEqual(len({a["experiment_id"], b["experiment_id"], c["experiment_id"]}), 3)


    def test_campaign_rollout_counts_match_design(self) -> None:
        heldout = self.cfg["heldout_targets"]
        recovery = self.cfg["failure_recovery"]
        uncertainty = self.cfg["uncertainty"]
        preconditioned = self.cfg["preconditioned_state"]

        heldout_rollouts = len(heldout["scenarios"]) * len(heldout["controller_scales"])
        recovery_families = (
            len(recovery["targets"])
            * len(recovery["amplitudes_by_mode"])
            * len(recovery["steps"])
            * len(recovery["signs"])
        )
        recovery_rollouts = (
            recovery_families
            * len(next(iter(recovery["amplitudes_by_mode"].values())))
            * len(recovery["controller_scales"])
        )
        uncertainty_rollouts = (
            len(uncertainty["targets"])
            * (len(uncertainty["scenarios"]) + len(uncertainty["slew_scale_variants"]))
            * len(uncertainty["controller_scales"])
        )
        preconditioned_rollouts = (
            len(preconditioned["targets"])
            * len(preconditioned["preludes"])
            * len(preconditioned["controller_scales"])
        )

        self.assertEqual(heldout_rollouts, 40)
        self.assertEqual(recovery_families, 36)
        self.assertEqual(recovery_rollouts, 360)
        self.assertEqual(uncertainty_rollouts, 104)
        self.assertEqual(preconditioned_rollouts, 32)

    def test_runtime_preflight_rejects_low_memory_and_file_limit(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        with mock.patch("os.cpu_count", return_value=208), mock.patch.object(
            s40, "_available_memory_gb", return_value=80.0
        ), mock.patch("resource.getrlimit", return_value=(65536, 65536)), mock.patch.dict(
            os.environ, {"STAGE4_WORKERS": "192"}, clear=False
        ):
            with self.assertRaises(RuntimeError):
                s40.runtime_preflight(ctx)
        with mock.patch("os.cpu_count", return_value=208), mock.patch.object(
            s40, "_available_memory_gb", return_value=200.0
        ), mock.patch("resource.getrlimit", return_value=(1024, 65536)), mock.patch.dict(
            os.environ, {"STAGE4_WORKERS": "192"}, clear=False
        ):
            with self.assertRaises(RuntimeError):
                s40.runtime_preflight(ctx)

    def test_config_rejects_heldout_target_that_is_in_library(self) -> None:
        source_cfg = {
            "gate": {
                **self.cfg["gate"],
                "ip_tracking": dict(self.cfg["gate"]["ip_tracking"]),
            }
        }
        scenario = self.cfg["heldout_targets"]["scenarios"][0]
        library = {
            "entries": [
                {
                    "task": {
                        "R_offset_m": scenario["R_offset_m"],
                        "Z_offset_m": scenario["Z_offset_m"],
                        "Ip_offset_A": scenario["Ip_offset_A"],
                    }
                }
            ]
        }
        with self.assertRaises(ValueError):
            s40.validate_stage40_config(self.cfg, source_cfg, library)

    def test_final_verdict_never_claims_deployment_qualification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = s40.Stage40Paths.from_run_dir(Path(tmp))
            paths.analysis.mkdir(parents=True, exist_ok=True)
            state = {
                "heldout_summary": {"passed": True},
                "recovery_summary": {"passed": True},
                "uncertainty_summary": {"passed": True},
                "preconditioned_summary": {"passed": True},
                "restart_summary": {
                    "true_restart_validation_available": False,
                    "passed": False,
                },
                "confirmation_summary": {"passed": True},
            }
            s40.atomic_write_json(paths.state, state)
            ctx = SimpleNamespace(paths=paths, source_run=Path("/source"), source_scale=0.5)
            verdict = s40.final_verdict(ctx)
            self.assertTrue(verdict["finite_test_envelope_validated"])
            self.assertFalse(verdict["deployment_robustness_validated"])
            self.assertFalse(verdict["plant_parameter_robustness_validated"])
            self.assertIn("TRUE_RESTART_NOT_AVAILABLE", verdict["verdict"])


    def test_variant_reconstruction_uses_spec_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = SimpleNamespace(
                variants={},
                source_env_cfg={"start_folder": "1100ms", "current_slew_a_per_ms": 0.3, "dt_ms": 10},
                source_train_cfg={"env_config": "unused", "episode": {"max_episode_steps": 38}},
                paths=SimpleNamespace(variants=root),
                base34=SimpleNamespace(),
                cfg=self.cfg,
            )
            payload = {"cfg": {}, "train_cfg": {}, "env_cfg": {}, "modes_tsc": [[0.0]], "max_delta_a": 3.0, "min_current_tsc": [0.0], "max_current_tsc": [1.0]}
            with mock.patch.object(s40.s34, "_context_payload", return_value=payload):
                s40._ensure_variant_for_spec(ctx, {"environment_variant": "slew_0p9", "slew_scale": 0.9, "experiment_id": "x"})
            self.assertIn("slew_0p9", ctx.variants)
            self.assertAlmostEqual(ctx.variants["slew_0p9"]["max_delta_a"], 0.9 * 0.3 * 10.0)



    def test_result_row_preserves_recovery_pairing_metadata(self) -> None:
        ctx = SimpleNamespace(base34=SimpleNamespace())
        result = {
            "experiment_id": "recovery",
            "spec": {
                "phase": "failure_recovery",
                "scenario": "family_amp",
                "category": "failure_recovery",
                "target_id": "nominal",
                "controller_scale": 0.5,
                "environment_variant": "base",
                "target_R_offset_m": 0.0,
                "target_Z_offset_m": 0.0,
                "target_Ip_offset_A": 0.0,
                "recovery_family": "nominal_m0_s04_p",
                "disturbance_amplitude_abs": 0.15,
                "slew_scale": 0.9,
                "controller_model_scale": 1.1,
            },
            "library_interpolation": {},
            "control_trace": [],
        }
        metrics = {
            "success": True,
            "stage3_4_target_tracking_pass": True,
            "stage3_4_tracking_minimum_signed_margin": 0.1,
        }
        with mock.patch.object(s40.s34, "target_metrics", return_value=metrics):
            row = s40.result_row(ctx, result)
        self.assertEqual(row["recovery_family"], "nominal_m0_s04_p")
        self.assertAlmostEqual(row["disturbance_amplitude_abs"], 0.15)
        self.assertAlmostEqual(row["slew_scale"], 0.9)
        self.assertAlmostEqual(row["controller_model_scale"], 1.1)

    def test_mixed_variant_actor_allocation_uses_full_capacity(self) -> None:
        allocation = s40._allocate_variant_actor_counts(
            {"base": 96, "slew_0p9": 4, "slew_1p1": 4},
            104,
        )
        self.assertEqual(allocation, {"base": 96, "slew_0p9": 4, "slew_1p1": 4})
        allocation = s40._allocate_variant_actor_counts(
            {"restart_1080ms": 4, "restart_1090ms": 4, "restart_1110ms": 4, "restart_1120ms": 4},
            16,
        )
        self.assertEqual(sum(allocation.values()), 16)
        self.assertTrue(all(value == 4 for value in allocation.values()))

    def test_mixed_variant_actor_allocation_handles_large_base_wave(self) -> None:
        allocation = s40._allocate_variant_actor_counts({"base": 360}, 192)
        self.assertEqual(allocation, {"base": 192})
        with self.assertRaises(ValueError):
            s40._allocate_variant_actor_counts({"a": 2, "b": 2}, 1)

    def test_synthetic_stage40_test(self) -> None:
        payload = s40.synthetic_stage40_test()
        self.assertTrue(payload["synthetic_ok"])
        self.assertEqual(payload["workers"], 192)


if __name__ == "__main__":
    unittest.main()
