from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation as r15b


class Stage41R15BTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (cls.root / "configs/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json").read_text()
        )
        cls.source_cfg = json.loads(
            (cls.root / "configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json").read_text()
        )

    def test_config_and_self_test(self) -> None:
        r15b.validate_config(self.cfg)
        payload = r15b.self_test(self.root)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["expected_true_tsc_probe_rollouts"], 32)
        self.assertFalse(payload["formal_timing_contract_restored_by_this_stage"])

    def test_hadamard_is_orthogonal(self) -> None:
        h = np.asarray([x["coefficients"] for x in self.cfg["superposition_validation"]["hadamard_combinations"]], dtype=float)
        np.testing.assert_allclose(h @ h.T, 4.0 * np.eye(4), atol=0.0, rtol=0.0)

    def test_combined_schedules_are_zero_net_and_bounded(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg, source_cfg=self.source_cfg)
        maximum = 0.0
        for delay in (1, 2):
            for combo in self.cfg["superposition_validation"]["hadamard_combinations"]:
                for sign in (-1, 1):
                    coefficients = 0.5 * sign * np.asarray(combo["coefficients"], dtype=float)
                    schedule = r15b._combined_schedule(ctx, actual_delay=delay, coefficients=coefficients)
                    self.assertGreater(len(schedule), 0)
                    net = np.sum(np.stack(list(schedule.values())), axis=0)
                    np.testing.assert_allclose(net, np.zeros(3), atol=1e-12, rtol=0.0)
                    maximum = max(maximum, max(float(np.max(np.abs(x))) for x in schedule.values()))
        self.assertLessEqual(maximum, 0.015 + 1e-12)

    def test_superposition_prediction(self) -> None:
        baseline = np.arange(75, dtype=float) / 100.0
        basis = np.arange(300, dtype=float).reshape(4, 75) / 1000.0
        coefficients = np.asarray([0.5, -0.5, 0.5, -0.5])
        model = {"baseline_output": baseline.tolist(), "basis_odd_response": basis.tolist()}
        np.testing.assert_array_equal(
            r15b._predict_superposition(model, coefficients), baseline + coefficients @ basis
        )

    def test_hadamard_reconstruction_exact(self) -> None:
        rng = np.random.default_rng(7)
        basis = rng.normal(size=(4, 75))
        h = np.asarray([x["coefficients"] for x in self.cfg["superposition_validation"]["hadamard_combinations"]], dtype=float)
        scale = 0.5
        combo_odd = basis.T @ (scale * h.T)
        reconstructed = (combo_odd @ (h * scale)).T
        np.testing.assert_allclose(reconstructed, basis, atol=1e-12, rtol=0.0)

    def test_source_inventory_includes_every_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            for path in r15b._required_source_files(source):
                if "raw" not in path.parts:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
            raw_dir = source / "stage4_1r15_bounded_probe_validation/raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            for i in range(32):
                (raw_dir / f"probe_{i:02d}.json.gz").write_bytes(b"x")
            inv = r15b._source_inventory(source)
            self.assertEqual(inv["n_files"], 45)
            self.assertEqual(sum("/raw/" in x["relative_path"] for x in inv["files"]), 32)

    def test_validation_rejects_relaxed_timing(self) -> None:
        cfg = json.loads(json.dumps(self.cfg))
        cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] = 28
        with self.assertRaises(ValueError):
            r15b.validate_config(cfg)

    def test_validation_rejects_nonorthogonal_combinations(self) -> None:
        cfg = json.loads(json.dumps(self.cfg))
        cfg["superposition_validation"]["hadamard_combinations"][3]["coefficients"] = [1, 1, 1, 1]
        with self.assertRaises(ValueError):
            r15b.validate_config(cfg)


if __name__ == "__main__":
    unittest.main()
