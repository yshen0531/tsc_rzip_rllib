from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


PRIMARY = module("nr2r2b0_primary", "scripts/rgeo_zgeo_1ms_nr2r2b0_source_baseline.py")
INDEPENDENT = module("nr2r2b0_independent", "scripts/rgeo_zgeo_1ms_nr2r2b0_independent.py")


STAGE = {
    "inner_r_radius_m": .025, "inner_z_radius_m": .025, "inner_ip_fraction": .05,
    "terminal_window_start_state": 24, "terminal_window_end_state": 32,
    "terminal_max_axis_step_m": .0001, "terminal_max_axis_net_drift_m": .001,
    "repeatability": {"geometry_m": 1e-12, "ip_a": 1e-9, "coil_a": 1e-9, "wire_a": 1e-9},
}


def states(step_r: float = 0.0, step_z: float = 0.0):
    return [{"r_geo_m": .7 + i * step_r, "z_geo_m": .03 + i * step_z, "r_mid_m": .79,
             "ip_a": 31200.0, "actual_current_decimal_a_tsc": ["0"] * 14,
             "wire_current_a": [0.0] * 48, "active_command_card15_fields": ["0"] * 14,
             "artifact_sha256": {"x": "a"}} for i in range(33)]


class NR2R2B0Tests(unittest.TestCase):
    def test_static_q0_is_short_hold(self):
        self.assertTrue(PRIMARY.hold_metrics(states(), STAGE)["passed"])
        adapted = [{"r_geo_m": x["r_geo_m"], "z_geo_m": x["z_geo_m"], "ip_a": x["ip_a"]} for x in states()]
        self.assertTrue(INDEPENDENT.hold(adapted, STAGE)["passed"])

    def test_persistent_terminal_drift_is_not_hold(self):
        self.assertFalse(PRIMARY.hold_metrics(states(.0002, 0.0), STAGE)["passed"])

    def test_repeatability_checks_artifacts(self):
        reference = states()
        candidate = copy.deepcopy(reference)
        self.assertTrue(PRIMARY.compare(reference, candidate, STAGE)["passed"])
        candidate[5]["artifact_sha256"]["x"] = "b"
        self.assertFalse(PRIMARY.compare(reference, candidate, STAGE)["passed"])

    def test_repeatability_checks_geometry(self):
        reference = states()
        candidate = copy.deepcopy(reference)
        candidate[2]["r_geo_m"] += 2e-12
        self.assertFalse(PRIMARY.compare(reference, candidate, STAGE)["passed"])


if __name__ == "__main__":
    unittest.main()
