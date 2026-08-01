from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT
    / "docs/codex/audit_tools/"
    "stage4_2r3c3t13s2r1_readback_residual_forensics.py"
)


def _load_tool():
    spec = importlib.util.spec_from_file_location("t13s2r1", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _env() -> dict:
    return {
        "turns_display_order": [100.0] * 14,
        "min_current_a_display_order": [-100.0] * 14,
        "max_current_a_display_order": [100.0] * 14,
        "current_slew_a_per_ms": 0.1,
        "dt_ms": 10,
    }


def _result(tool, experiment_id: str, sign: int, units: np.ndarray) -> dict:
    env = _env()
    currents = [np.zeros(14)]
    trace = []
    for step in range(50):
        action = np.zeros(14)
        action[0] = 0.1 if sign else 0.0
        reconstructed = tool.BASE.card15_quantized_next_current(
            currents[-1], action, env
        )
        target = np.asarray(reconstructed["predicted_current_a_tsc"])
        observed = target - units * tool.OUTPUT_GRID_KAT * 1000.0 / 100.0
        currents.append(observed)
        trace.append({"action_norm_tsc": action.tolist()})
    return {
        "experiment_id": experiment_id,
        "spec": {"r3c3_probe_sign": sign},
        "trajectory": [
            {
                "R": 0.72,
                "Z": 0.0,
                "Ip": 30000.0,
                "currents_a_tsc": row.tolist(),
            }
            for row in currents
        ],
        "controller_trace": trace,
    }


def test_fixed_baseline_bias_predicts_probe_holdout():
    tool = _load_tool()
    units = np.asarray([2, 1] + [0] * 12)
    results = [
        _result(tool, f"baseline-{index}", 0, units) for index in range(4)
    ] + [_result(tool, f"probe-{index}", 1, units) for index in range(48)]
    envs = {str(row["experiment_id"]): _env() for row in results}
    report = tool.analyze_readback_residual(results, envs)
    assert report["baseline_calibration"]["per_coil_constant"]
    assert report["baseline_calibration"]["calibrated_units_tsc_order"] == units.tolist()
    assert report["signed_probe_holdout"]["passed"]
    assert report["route"] == "FIXED_DEVELOPMENT_READBACK_BIAS_IDENTIFIED"


def test_probe_bias_change_fails_retrospective_holdout():
    tool = _load_tool()
    baseline_units = np.asarray([1] + [0] * 13)
    probe_units = np.asarray([2] + [0] * 13)
    results = [
        _result(tool, f"baseline-{index}", 0, baseline_units)
        for index in range(4)
    ] + [
        _result(tool, f"probe-{index}", 1, probe_units) for index in range(48)
    ]
    envs = {str(row["experiment_id"]): _env() for row in results}
    report = tool.analyze_readback_residual(results, envs)
    assert not report["signed_probe_holdout"]["passed"]
    assert (
        report["route"]
        == "UNRESOLVED_STATE_OR_VALUE_DEPENDENT_ACTUATOR_READBACK"
    )


def test_nonconstant_baseline_bias_cannot_be_calibrated():
    tool = _load_tool()
    units = np.asarray([1] + [0] * 13)
    results = [
        _result(tool, f"baseline-{index}", 0, units) for index in range(4)
    ] + [_result(tool, f"probe-{index}", 1, units) for index in range(48)]
    changed = copy.deepcopy(results[0])
    changed["trajectory"][1]["currents_a_tsc"][0] -= 1e-5
    results[0] = changed
    envs = {str(row["experiment_id"]): _env() for row in results}
    report = tool.analyze_readback_residual(results, envs)
    assert not report["baseline_calibration"]["per_coil_constant"]
    assert not report["signed_probe_holdout"]["passed"]
