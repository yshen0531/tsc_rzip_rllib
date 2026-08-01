#!/usr/bin/env python3
"""Read-only T13S2R1 target-current versus TSC readback forensics."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S2R1"
AUDIT_IDENTITY = "card15_target_tsc_readback_residual_forensics_v1"
OUTPUT_GRID_KAT = 1e-6
NUMERICAL_GATE_A = 1e-9
EXPECTED_T13S2_REPORT_SHA256 = (
    "9ef183d20f3354d11bb70c2324bade6829879f00c05dd96b99c1312bcfd53d58"
)
EXPECTED_T13S2_MANIFEST_SHA256 = (
    "564569ec948399792d2db49c4d5742e70a2b20c9ad48efaad7eda34f95f096dd"
)


def _load_base_module():
    path = (
        Path(__file__).resolve().parent
        / "stage4_2r3c3t13s2_quantized_observability_audit.py"
    )
    spec = importlib.util.spec_from_file_location("t13s2_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load T13S2 base audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_base_module()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _residual_rows(
    results: Sequence[Mapping[str, Any]],
    env_by_experiment: Mapping[str, Mapping[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    units = []
    residual_a = []
    active = []
    target_a = []
    for result in results:
        experiment_id = str(result["experiment_id"])
        env = env_by_experiment[experiment_id]
        turns = np.asarray(BASE._env_arrays(env)["turns"], dtype=float)
        currents = BASE._trajectory_currents(result)
        actions = BASE._trace_actions(result)
        for step in range(50):
            reconstructed = BASE.card15_quantized_next_current(
                currents[step], actions[step], env
            )
            target = np.asarray(
                reconstructed["predicted_current_a_tsc"], dtype=float
            )
            observed = currents[step + 1]
            delta_a = target - observed
            units.append(delta_a * turns / 1000.0 / OUTPUT_GRID_KAT)
            residual_a.append(delta_a)
            active.append(np.abs(actions[step]) > 0.0)
            target_a.append(target)
    return (
        np.asarray(units, dtype=float),
        np.asarray(residual_a, dtype=float),
        np.asarray(active, dtype=bool),
        np.asarray(target_a, dtype=float),
    )


def analyze_readback_residual(
    results: Sequence[Mapping[str, Any]],
    env_by_experiment: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    baselines = [
        result
        for result in results
        if int(result["spec"]["r3c3_probe_sign"]) == 0
    ]
    probes = [
        result
        for result in results
        if int(result["spec"]["r3c3_probe_sign"]) != 0
    ]
    if len(results) == 52 and (len(baselines), len(probes)) != (4, 48):
        raise ValueError("T13S1 baseline/probe split changed")
    all_units, all_residual_a, all_active, all_target = _residual_rows(
        results, env_by_experiment
    )
    baseline_units, _, _, _ = _residual_rows(baselines, env_by_experiment)
    probe_units, _, probe_active, probe_target = _residual_rows(
        probes, env_by_experiment
    )
    rounded = np.rint(all_units).astype(int)
    integer_residual = all_units - rounded
    baseline_rounded = np.rint(baseline_units).astype(int)
    baseline_integer_residual = baseline_units - baseline_rounded
    baseline_constant = bool(
        baseline_units.size
        and np.max(np.abs(baseline_integer_residual)) <= 1e-7
        and all(len(np.unique(baseline_rounded[:, coil])) == 1 for coil in range(14))
    )
    calibrated_units = (
        baseline_rounded[0].astype(int)
        if baseline_constant
        else np.zeros(14, dtype=int)
    )
    first_env = env_by_experiment[str(results[0]["experiment_id"])]
    turns = np.asarray(BASE._env_arrays(first_env)["turns"], dtype=float)
    corrected_probe_prediction = (
        probe_target
        - calibrated_units.reshape(1, 14)
        * OUTPUT_GRID_KAT
        * 1000.0
        / turns.reshape(1, 14)
    )
    observed_probe = np.asarray(
        [
            BASE._trajectory_currents(result)[1:]
            for result in probes
        ],
        dtype=float,
    ).reshape(-1, 14)
    holdout_residual = corrected_probe_prediction - observed_probe
    holdout_count = int(holdout_residual.size)
    holdout_within = int(
        np.sum(np.abs(holdout_residual) <= NUMERICAL_GATE_A)
    )
    per_coil = []
    for coil in range(14):
        values = rounded[:, coil]
        active_values = rounded[:, coil][all_active[:, coil]]
        inactive_values = rounded[:, coil][~all_active[:, coil]]
        per_coil.append(
            {
                "coil_index_tsc": coil,
                "turns": float(turns[coil]),
                "signed_output_grid_units": sorted(
                    int(value) for value in np.unique(values)
                ),
                "unit_histogram": {
                    str(key): int(value)
                    for key, value in sorted(Counter(values.tolist()).items())
                },
                "constant_across_all_transitions": bool(
                    len(np.unique(values)) == 1
                ),
                "baseline_calibrated_unit": int(calibrated_units[coil]),
                "active_action_units": sorted(
                    int(value) for value in np.unique(active_values)
                ),
                "inactive_action_units": sorted(
                    int(value) for value in np.unique(inactive_values)
                ),
                "maximum_integer_grid_residual": float(
                    np.max(np.abs(integer_residual[:, coil]))
                ),
            }
        )
    holdout_passed = bool(
        baseline_constant
        and holdout_count == 48 * 50 * 14
        and holdout_within == holdout_count
    )
    return {
        "run_count": len(results),
        "baseline_run_count": len(baselines),
        "signed_probe_run_count": len(probes),
        "transition_count": int(all_units.shape[0] * all_units.shape[1]),
        "component_count": int(all_units.size),
        "output_grid_kAt": OUTPUT_GRID_KAT,
        "maximum_abs_uncorrected_residual_A": float(
            np.max(np.abs(all_residual_a))
        ),
        "maximum_abs_output_grid_units": float(np.max(np.abs(all_units))),
        "maximum_integer_grid_residual": float(
            np.max(np.abs(integer_residual))
        ),
        "signed_output_grid_unit_histogram": {
            str(key): int(value)
            for key, value in sorted(Counter(rounded.reshape(-1).tolist()).items())
        },
        "per_coil": per_coil,
        "baseline_calibration": {
            "component_count": int(baseline_units.size),
            "per_coil_constant": baseline_constant,
            "calibrated_units_tsc_order": calibrated_units.tolist(),
            "maximum_integer_grid_residual": float(
                np.max(np.abs(baseline_integer_residual))
            ),
        },
        "signed_probe_holdout": {
            "component_count": holdout_count,
            "within_1e_9_A_count": holdout_within,
            "exact_count": int(
                np.sum(np.equal(corrected_probe_prediction, observed_probe))
            ),
            "maximum_abs_residual_A": float(
                np.max(np.abs(holdout_residual))
            ),
            "rms_residual_A": float(
                np.sqrt(np.mean(holdout_residual**2))
            ),
            "retrospective_development_split_only": True,
            "passed": holdout_passed,
        },
        "target_value_range_A": [
            float(np.min(all_target)),
            float(np.max(all_target)),
        ],
        "active_action_component_count": int(np.sum(all_active)),
        "probe_active_action_component_count": int(np.sum(probe_active)),
        "route": (
            "FIXED_DEVELOPMENT_READBACK_BIAS_IDENTIFIED"
            if holdout_passed
            else "UNRESOLVED_STATE_OR_VALUE_DEPENDENT_ACTUATOR_READBACK"
        ),
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.expanduser().resolve()
    run_dir = args.run_dir.expanduser().resolve()
    audit_dir = args.audit_dir.expanduser().resolve()
    t13s2_dir = args.t13s2_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise ValueError("T13S2R1 output directory must be new")
    report_path = (
        t13s2_dir / "stage4_2r3c3t13s2_quantized_observability_audit.json"
    )
    manifest_path = (
        t13s2_dir / "stage4_2r3c3t13s2_quantized_observability_manifest.json"
    )
    if (
        _sha256(report_path) != EXPECTED_T13S2_REPORT_SHA256
        or _sha256(manifest_path) != EXPECTED_T13S2_MANIFEST_SHA256
    ):
        raise ValueError("T13S2 source audit identity mismatch")
    t13s2 = _read_json(report_path)
    if (
        t13s2["route"]["primary"] != "ACTUATOR_MAPPING_IMPLEMENTATION_GAP"
        or bool(t13s2["actuator_reconstruction"]["actuator_reconstruction_passed"])
    ):
        raise ValueError("T13S2 result was reinterpreted")
    results, env_by_id, raw_inventory, source = BASE._load_authenticated_inputs(
        project_root, run_dir, audit_dir
    )
    analysis = analyze_readback_residual(results, env_by_id)
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_identity": AUDIT_IDENTITY,
        "classification": "read_only_target_to_readback_residual_forensics",
        "source_run": str(run_dir),
        "source_t13s2_dir": str(t13s2_dir),
        "source_provenance": {
            **source,
            "t13s2_report_sha256": _sha256(report_path),
            "t13s2_manifest_sha256": _sha256(manifest_path),
        },
        "raw_inventory": raw_inventory,
        "official_results_unchanged": {
            "t13s1": "SENTINEL_FAIL_STOP_IDENTIFICATION",
            "t13s2": "ACTUATOR_MAPPING_IMPLEMENTATION_GAP",
            "thresholds_changed": False,
            "verdicts_reinterpreted": False,
        },
        "analysis": analysis,
        "route": {
            "primary": analysis["route"],
            "required_interface": "QUANTIZED_MULTI_HYPOTHESIS_TUBE",
            "fixed_bias_may_be_nominal_only": True,
            "nonzero_actuator_uncertainty_required": True,
            "real_mpc_authorized": False,
            "new_tsc_authorized": False,
        },
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "t13s2_audit_design_or_gate_bug": False,
            "fixed_development_readback_bias_identified": bool(
                analysis["route"]
                == "FIXED_DEVELOPMENT_READBACK_BIAS_IDENTIFIED"
            ),
            "independent_holdout": False,
            "observer_or_plant_model_validated": False,
            "real_mpc_tested": False,
            "real_tsc_executed": False,
            "probe_trajectories_allowed_in_expert_dataset": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    output_report = output_dir / "stage4_2r3c3t13s2r1_readback_residual_forensics.json"
    _write_json(output_report, report)
    output_manifest = output_dir / "stage4_2r3c3t13s2r1_readback_residual_manifest.json"
    _write_json(
        output_manifest,
        {
            "schema_version": 1,
            "stage": STAGE,
            "audit_identity": AUDIT_IDENTITY,
            "report": {
                "path": output_report.name,
                "size_bytes": int(output_report.stat().st_size),
                "sha256": _sha256(output_report),
            },
            "raw_files_copied_or_modified": 0,
            "controller_ray_gotsc_tsc_or_plant_steps_executed": 0,
        },
    )
    return {
        "output_dir": str(output_dir),
        "report_sha256": _sha256(output_report),
        "manifest_sha256": _sha256(output_manifest),
        "route": analysis["route"],
        "baseline_calibration": analysis["baseline_calibration"],
        "signed_probe_holdout": analysis["signed_probe_holdout"],
        "real_tsc_executed": False,
        "plant_steps_executed": 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--t13s2-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run_audit(_parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
