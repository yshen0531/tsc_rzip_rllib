from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tsc_rzip_rllib.diagnostics.stage1_controllability import (
    baseline_summary,
    build_scan_specs,
    compute_terminal_reachable_set,
    fit_response_tensor,
    solve_reachability_candidate,
    svd_diagnostics,
)


def fake_result(spec, base_y, base_currents, response, delta_a):
    horizon = len(base_y) - 1
    y = base_y.copy()
    currents = base_currents.copy()
    if spec["kind"] == "scan":
        k = spec["injection_step"]
        c = spec["coil_index_tsc"]
        x = spec["sign"] * spec["amplitude_fraction"] * delta_a
        y = y + response[:, :, k, c] * x
        currents[k + 1 :, c] += x
    traj = []
    for t in range(horizon + 1):
        traj.append(
            {
                "R": float(y[t, 0]),
                "Z": float(y[t, 1]),
                "Ip": float(y[t, 2]),
                "vessel_current_total_a": 0.0,
                "vessel_current_abs_sum_a": 0.0,
                "currents_a_tsc": currents[t].tolist(),
            }
        )
    out = {"success": True, "spec": spec, "trajectory": traj}
    if spec["kind"] == "scan":
        out["effective_injection_delta_a"] = float(spec["sign"] * spec["amplitude_fraction"] * delta_a)
    return out


def main():
    horizon = 4
    rng = np.random.default_rng(5)
    response = np.zeros((horizon + 1, 3, horizon, 14))
    for t in range(horizon + 1):
        for k in range(horizon):
            if t > k:
                response[t, :, k, :] = rng.normal(size=(3, 14)) * np.asarray([0.002, 0.002, 20.0])[:, None]
    base_y = np.column_stack(
        [np.linspace(0.55, 0.56, horizon + 1), np.linspace(-0.15, -0.14, horizon + 1), np.linspace(30000, 29800, horizon + 1)]
    )
    base_currents = np.zeros((horizon + 1, 14))
    cfg_scan = {
        "scan": {
            "horizon_steps": horizon,
            "baseline_repeats": 3,
            "injection_steps": list(range(horizon)),
            "amplitude_fractions": [0.5, 1.0],
        }
    }
    specs = build_scan_specs(cfg_scan)
    results = [fake_result(s, base_y, base_currents, response, 3.0) for s in specs]
    baseline, _ = baseline_summary(results, horizon)
    fitted, fit_meta = fit_response_tensor(results, baseline, horizon=horizon)
    assert np.allclose(fitted, response, atol=1e-11)
    assert max(x["relative_nonlinearity_residual"] for x in fit_meta["fit_rows"]) < 1e-10

    cfg = {
        "target": {"R": 0.75, "Z": 0.0, "Ip": 29779.724},
        "scan": {"horizon_steps": horizon, "dt_ms": 10},
        "analysis": {
            "r_scale_m": 0.08,
            "z_scale_m": 0.08,
            "ip_scale_a": 8000,
            "ip_weight": 0.15,
            "mode_energy_target": 0.99,
            "singular_ratio_floor": 0.001,
            "max_recommended_modes": 8,
            "reachable_set_directions": 24,
            "reachable_set_ip_tolerance_a": 8000,
        },
        "optimization": {
            "tracking_steps": [2, 3, 4],
            "tracking_step_weights": [0.5, 0.8, 1.0],
            "velocity_steps": [3, 4],
            "velocity_weight": 0.1,
            "action_increment_l2": 0.001,
            "current_deviation_l2": 0.00001,
            "max_iterations": 200,
            "ftol": 1e-9,
        },
        "_env_config": {
            "current_slew_a_per_ms": 0.3,
            "dt_ms": 10,
            "min_current_a_display_order": [-400.0] * 14,
            "max_current_a_display_order": [400.0] * 14,
        },
    }
    svd = svd_diagnostics(fitted, cfg)
    reachable = compute_terminal_reachable_set(fitted, baseline, cfg)
    assert len(reachable["points"]) == 24
    candidate = solve_reachability_candidate(
        fitted, baseline, svd["modes_tsc"][:, :4], cfg, target_fraction=0.5, label="test"
    )
    increments = np.asarray(candidate["action_increment_a_tsc"])
    assert increments.shape == (horizon, 14)
    assert np.max(np.abs(increments)) <= 3.0 + 1e-6
    print("stage1 synthetic tests: PASS")


if __name__ == "__main__":
    main()
