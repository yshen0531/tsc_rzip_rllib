import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/rgeo_zgeo_1ms_id2z21_moving_nominal_temporal_contract.py"
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z21_moving_nominal_temporal_contract.json"
LAUNCHER = ROOT / "run_rgeo_zgeo_1ms_id2z21_moving_nominal_temporal_contract.sh"

SPEC = importlib.util.spec_from_file_location("id2z21", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def state(r: float, z: float, ip: float = 100.0) -> dict:
    return {"r_geo_m": r, "z_geo_m": z, "ip_a": ip}


class ID2Z21Tests(unittest.TestCase):
    def test_frozen_zero_tsc_config(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        MODULE.validate_config(config)
        self.assertEqual(config["models_fit_or_updated"], 0)
        self.assertEqual(config["tsc_calls_or_plant_advances"], 0)
        self.assertEqual(config["calibration_and_blind_holdout_reads"], 0)
        self.assertTrue(config["stationary_capture_gate"]["must_not_be_weakened"])
        self.assertEqual(config["sustained_response_gates"]["horizons_ms"], [2, 4, 8])

    def test_no_runtime_or_training_import(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "TSCStepRunner", "step_current_a", "gotsc", "torch", "sklearn",
            "fit_ridge", "GRU", "TCN",
        ):
            self.assertNotIn(forbidden, text)

    def test_launcher_is_server_read_only_entrypoint(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("ID2Z21_SOURCE_REVISION", text)
        self.assertIn("--server-run-root", text)
        self.assertNotIn("rm -", text)
        self.assertNotIn("gotsc", text)

    def test_first_divergence(self) -> None:
        self.assertEqual(MODULE.first_divergence("FFAE", "FFae", 16), 18)
        with self.assertRaises(MODULE.AuditInputError):
            MODULE.first_divergence("FFFF", "FFFF", 16)

    def test_causal_velocity_and_source_metrics(self) -> None:
        states = [state(0.0, 0.0), state(0.001, -0.002, 102.0)]
        velocity = MODULE.causal_velocity(states, 1, 0.001)
        np.testing.assert_allclose(velocity, [1.0, -2.0])
        metrics = MODULE.source_metrics(states, 1, 0.001)
        self.assertAlmostEqual(metrics["distance_m"], math.sqrt(5e-6))
        self.assertAlmostEqual(metrics["speed_m_per_s"], math.sqrt(5.0))
        self.assertAlmostEqual(metrics["ip_fraction"], 0.02)

    def test_rank_condition(self) -> None:
        rank, condition, singular = MODULE.numerical_rank_condition(np.eye(4), 1e-10)
        self.assertEqual(rank, 4)
        self.assertAlmostEqual(condition, 1.0)
        self.assertEqual(len(singular), 4)

    def test_useful_horizon_is_shortest_qualified(self) -> None:
        gates = {
            "minimum_four_ms_rz_separation_m": 1e-4,
            "minimum_eight_ms_rz_separation_m": 2e-4,
            "minimum_terminal_velocity_separation_m_per_s": 0.05,
            "minimum_three_state_median_rz_separation_m": 5e-5,
            "maximum_peak_to_three_state_median_ratio": 5.0,
        }
        segment = {
            "horizons": [
                {"horizon_ms": 2, "rz_separation_m": 1.0, "terminal_velocity_separation_m_per_s": 1.0, "three_state_median_rz_separation_m": 1.0, "peak_to_three_state_median_ratio": 1.0},
                {"horizon_ms": 4, "rz_separation_m": 1e-4, "terminal_velocity_separation_m_per_s": 0.05, "three_state_median_rz_separation_m": 5e-5, "peak_to_three_state_median_ratio": 5.0},
                {"horizon_ms": 8, "rz_separation_m": 3e-4, "terminal_velocity_separation_m_per_s": 0.06, "three_state_median_rz_separation_m": 2e-4, "peak_to_three_state_median_ratio": 1.0},
            ]
        }
        self.assertEqual(MODULE.useful_horizon(segment, gates)["horizon_ms"], 4)

    def test_two_vector_geometry(self) -> None:
        rows = [
            {"pair_id": "d00", "horizon_ms": 4, "rz_vector_m": [1.0, 0.0]},
            {"pair_id": "d01", "horizon_ms": 4, "rz_vector_m": [0.0, 1.0]},
        ]
        result = MODULE.best_two_vector_geometry(rows)
        self.assertEqual(result["pair_ids"], ["d00", "d01"])
        self.assertAlmostEqual(result["condition"], 1.0)
        self.assertAlmostEqual(result["acute_line_angle_deg"], 90.0)

    def test_nonoverwrite_result(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as temp:
            path = Path(temp) / "result.json"
            MODULE.write_new(path, {"x": 1})
            with self.assertRaises(FileExistsError):
                MODULE.write_new(path, {"x": 2})


if __name__ == "__main__":
    unittest.main()
