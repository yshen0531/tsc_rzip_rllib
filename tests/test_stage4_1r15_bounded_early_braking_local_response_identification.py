from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r15_bounded_early_braking_local_response_identification as r15


class Stage41R15ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = Path(r15.__file__).resolve().parents[2]
        cls.path = cls.project / "configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json"
        cls.cfg = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_immutable_contract_and_identification_only(self) -> None:
        r15.validate_config(self.cfg)
        self.assertEqual(self.cfg["formal_timing_contract"]["normal_slew"]["arrival_deadline_step"], 25)
        self.assertEqual(self.cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"], 27)
        self.assertFalse(self.cfg["formal_timing_contract_restored_by_this_stage"])
        self.assertTrue(self.cfg["stage4_2r1_was_not_run_or_reused"])

    def test_timing_expansion_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] = 28
        with self.assertRaises(ValueError):
            r15.validate_config(bad)

    def test_probe_count_and_basis_locked(self) -> None:
        probe = self.cfg["bounded_probe_validation"]
        self.assertEqual(probe["expected_rollouts"], 32)
        self.assertEqual([x["probe_id"] for x in probe["probe_basis"]], ["early_mode0", "early_mode1", "late_mode0", "late_mode1"])
        self.assertEqual(probe["probe_amplitude_by_mode"], [0.015, 0.015, 0.0])

    def test_probe_amplitude_change_rejected_for_mode2(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["bounded_probe_validation"]["probe_amplitude_by_mode"][2] = 0.001
        with self.assertRaisesRegex(ValueError, "mode 2"):
            r15.validate_config(bad)

    def test_self_test(self) -> None:
        payload = r15.self_test(self.project)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["expected_true_tsc_probe_rollouts"], 32)
        self.assertTrue(payload["all_probes_zero_net"])
        self.assertFalse(payload["formal_timing_contract_restored_by_this_stage"])


class Stage41R15SourceInventoryTests(unittest.TestCase):
    def _build_r14_tree(self, root: Path, raw_count: int = 2) -> Path:
        source = root / "stage4_1r14_run"
        fixed = [
            "stage4_1r14_manifest.json",
            "stage4_1r14_state.json",
            "stage4_1r14_config.resolved.json",
            "stage4_1r14_analysis/stage4_1r14_verdict.json",
            "stage4_1r14_analysis/stage4_1r14_summary.json",
            "stage4_1r14_source_audit/summary.json",
            "stage4_1r14_oracle_development/summary.json",
            "stage4_1r14_oracle_development/results.json",
            "stage4_1r14_oracle_development/results.csv",
        ]
        for idx, rel in enumerate(fixed):
            path = source / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"index": idx}), encoding="utf-8")
        raw_dir = source / "stage4_1r14_oracle_development/raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(raw_count):
            (raw_dir / f"case_{idx}.json.gz").write_bytes(f"raw-{idx}".encode())
        return source

    def test_direct_r14_inventory_does_not_require_r13_manifest_at_r14_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = self._build_r14_tree(Path(td))
            with mock.patch.object(
                r15.r14,
                "_source_inventory",
                side_effect=AssertionError("R14's R13 inventory helper must not be used"),
            ):
                payload = r15._source_inventory(source)
            self.assertEqual(payload["source_stage"], "Stage4.1R14")
            self.assertEqual(payload["inventory_contract"], r15.R14_SOURCE_INVENTORY_CONTRACT)
            self.assertEqual(payload["n_files"], 11)
            self.assertFalse((source / "stage4_1r13_manifest.json").exists())

    def test_r14_raw_files_are_part_of_resume_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = self._build_r14_tree(Path(td), raw_count=1)
            before = r15._source_inventory(source)
            raw = next((source / "stage4_1r14_oracle_development/raw").glob("*.json.gz"))
            raw.write_bytes(b"changed")
            after = r15._source_inventory(source)
            self.assertNotEqual(before["digest"], after["digest"])
            self.assertTrue(
                any(row["relative_path"].endswith(".json.gz") for row in after["files"])
            )

    def test_missing_r14_artifact_has_r14_specific_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source = self._build_r14_tree(Path(td))
            (source / "stage4_1r14_state.json").unlink()
            with self.assertRaisesRegex(FileNotFoundError, "Stage4.1R14"):
                r15._source_inventory(source)


class Stage41R15ModelTests(unittest.TestCase):
    def test_probe_schedule_is_causal_and_zero_net(self) -> None:
        basis = {"mode": 0, "effect_offsets": [0, 1, 3, 4], "sign_pattern": [1, 1, -1, -1]}
        for delay in (1, 2):
            schedule = r15._probe_schedule(first_effect_state=23, actual_delay=delay, basis=basis, sign=1, amplitude_by_mode=[0.015, 0.015, 0.0])
            net = np.sum(np.stack(list(schedule.values())), axis=0)
            self.assertTrue(np.allclose(net, 0.0, atol=1e-12, rtol=0.0))
            for issue in schedule:
                self.assertGreaterEqual(issue, 0)
                self.assertIn(issue + delay + 1, {23, 24, 26, 27})

    def test_pca_ridge_reconstructs_low_rank_mapping(self) -> None:
        rng = np.random.default_rng(9)
        latent = rng.normal(size=(20, 3))
        loading = rng.normal(size=(3, 12))
        x = latent @ loading
        y = np.column_stack([latent[:, 0] - 0.3 * latent[:, 1], 0.5 * latent[:, 2], latent[:, 1] + latent[:, 2]])
        model = r15._fit_pca_ridge(x, y, rank=3, ridge_lambda=1e-8)
        pred = r15._predict_pca_ridge(model, x)
        self.assertLess(float(np.sqrt(np.mean((pred - y) ** 2))), 1e-5)

    def test_prediction_metric_layout(self) -> None:
        layout = {"state_start": 23, "state_end_inclusive": 37, "state_count": 15}
        actual = np.zeros(75)
        pred = np.zeros(75)
        pred[14] = 0.003
        pred[29] = 0.004
        metrics = r15._prediction_metrics(actual, pred, layout)
        self.assertAlmostEqual(metrics["final_speed_error_m_per_s"], 0.005)
        self.assertGreater(metrics["velocity_component_rmse_m_per_s"], 0.0)

    def test_output_vector_dimensions(self) -> None:
        trajectory = []
        for i in range(38):
            trajectory.append({"R": 1.0 + 1e-4 * i, "Z": -1e-4 * i, "Ip": 1e6 + i})
        vector = r15._output_vector({"trajectory": trajectory}, start_state=23, end_state_inclusive=37)
        self.assertEqual(vector.shape, (75,))

    def test_control_input_requires_complete_steps(self) -> None:
        result = {"control_trace": [{"step": i, "applied_desired_physical_mode_coefficients": [i, 0, 0]} for i in range(16, 37)]}
        vector = r15._control_input_vector(result, start_step=16, end_step_inclusive=36)
        self.assertEqual(vector.shape, (63,))
        bad = copy.deepcopy(result)
        bad["control_trace"].pop()
        with self.assertRaisesRegex(ValueError, "missing steps"):
            r15._control_input_vector(bad, start_step=16, end_step_inclusive=36)


class Stage41R15ProbeWorkerTests(unittest.TestCase):
    def test_worker_records_requested_and_applied_zero_net_probe(self) -> None:
        stub = SimpleNamespace(cfg={"trajectory": {"coefficient_lower": [-1, -1, -1], "coefficient_upper": [1, 1, 1]}})

        def baseline_solver(*_args, **_kwargs):
            return {"first_correction": np.zeros(3), "sequence_correction": np.zeros((2, 3))}

        class FakeInner:
            def __init__(self, *_args, **_kwargs):
                pass
            def close(self):
                pass
            def evaluate(self, spec):
                trace = []
                for step in sorted(int(k) for k in spec["r15_probe_delta_by_issue_step"]):
                    r15.r12.r3.solve_delay_aware_physical_correction(stub, {}, current_step=step)
                    trace.append({"step": step, "solver_success": True, "future_measurement_used": False})
                return {"success": True, "failure_reason": "", "spec": spec, "trajectory": [], "anticipatory_damping_trace": trace, "anticipatory_damping_summary": {"streaming_queue_consistent": True}}

        spec = {"experiment_id": "x", "r15_probe_id": "early_mode0", "r15_probe_sign": 1, "r15_probe_delta_by_issue_step": {"20": [0.015, 0, 0], "21": [0.015, 0, 0], "23": [-0.015, 0, 0], "24": [-0.015, 0, 0]}}
        with mock.patch.object(r15.r13, "LocalStage41R13Worker", FakeInner), mock.patch.object(r15.r12.r3, "solve_delay_aware_physical_correction", side_effect=baseline_solver):
            worker = r15.LocalStage41R15ProbeWorker({}, {}, {}, "w", {})
            result = worker.evaluate(spec)
        summary = result["r15_probe_summary"]
        self.assertTrue(summary["probe_zero_net"])
        self.assertTrue(summary["applied_probe_zero_net"])
        self.assertEqual(summary["probe_issue_count"], summary["probe_applied_issue_count"])
        self.assertLessEqual(summary["maximum_applied_component"], 0.015 + 1e-12)

    def test_probe_specs_cover_32_unique_causal_tasks(self) -> None:
        project = Path(r15.__file__).resolve().parents[2]
        cfg = json.loads((project / "configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json").read_text())
        ctx = SimpleNamespace(cfg=cfg, r14_ctx=SimpleNamespace(r13_ctx=object()))

        def fake_make_spec(**kwargs):
            target = kwargs["target"]
            return {
                "target_id": target["target_id"],
                "target_R_offset_m": target["R_offset_m"],
                "target_Z_offset_m": target["Z_offset_m"],
                "target_Ip_offset_A": target["Ip_offset_A"],
                "action_delay_steps": kwargs["actual_delay"],
                "slew_scale": 0.9,
            }

        with mock.patch.object(r15, "materialize_variant", return_value=("v", {})), mock.patch.object(r15.r13, "_make_spec", side_effect=fake_make_spec):
            specs = r15._probe_specs(ctx)
        self.assertEqual(len(specs), 32)
        self.assertEqual(len({x["experiment_id"] for x in specs}), 32)
        self.assertEqual({x["target_id"] for x in specs}, {"nominal", "RZ_p10_m10"})
        self.assertEqual({x["action_delay_steps"] for x in specs}, {1, 2})
        for spec in specs:
            schedule = {int(k): np.asarray(v) for k, v in spec["r15_probe_delta_by_issue_step"].items()}
            self.assertTrue(np.allclose(np.sum(np.stack(list(schedule.values())), axis=0), 0.0, atol=1e-12, rtol=0.0))

    def test_result_complete_rejects_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json.gz"
            r15.atomic_write_json_gz(p, {"success": False})
            self.assertFalse(r15._result_complete(p))
            r15.atomic_write_json_gz(p, {"success": True})
            self.assertTrue(r15._result_complete(p))


if __name__ == "__main__":
    unittest.main()
