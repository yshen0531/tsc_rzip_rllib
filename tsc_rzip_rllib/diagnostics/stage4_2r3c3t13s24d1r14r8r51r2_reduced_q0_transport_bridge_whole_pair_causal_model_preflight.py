#!/usr/bin/env python3
"""Frozen zero-TSC whole-pair causal model preflight for R8R51R2."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R8R51R2"
N_COILS = 14
ZERO_Q = np.zeros(4, dtype=float)
OLD_R51R1_ROUTE = "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_EXECUTION_FAIL_STOP"
PRIMARY_DETAIL = "primary_detailed.json"
PRIMARY_SUMMARY = "primary_summary.json"
INDEPENDENT = "independent.json"


def validate_config(cfg: Mapping[str, Any], project_root: Path) -> None:
    expected_feature = {
        "feature_dimension": 44,
        "expanded_dimension": 180,
        "completed_state_step": 12,
        "history_state_steps": [9, 10, 11, 12],
        "previous_current_state_step": 10,
        "candidate_first_effect_state_step": 13,
        "candidate_second_effect_state_step": 14,
        "q_scale": 1.5,
        "whitening_standard_deviation_floor": 1e-12,
        "forbid_pair_history_partition_labels": True,
        "forbid_wire_vessel_future_source_outcome_formal_inputs": True,
    }
    expected_model = {
        "physical_pair_count": 8,
        "context_count": 16,
        "candidate_count": 13,
        "row_count": 208,
        "outer_fold_count": 8,
        "outer_training_row_count": 182,
        "outer_holdout_row_count": 26,
        "nested_training_row_count": 156,
        "nested_holdout_row_count": 26,
        "ridge_penalty": 0.0001,
        "tube_reserve_multiplier": 1.25,
        "output_scales": [0.03, 0.03, 10000.0, 0.03, 0.03, 10000.0],
        "point_error_floors": [0.015, 0.015, 3000.0, 0.015, 0.015, 3000.0],
        "tube_half_width_caps": [0.025, 0.025, 5000.0, 0.025, 0.025, 5000.0],
        "comparison_absolute_tolerance": 1e-12,
        "intercept_allowed": False,
        "feature_only_term_allowed": False,
        "hyperparameter_selection_count": 0,
    }
    expected_routes = {
        "source_blocked": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_MODEL_PREFLIGHT_BLOCKED_BY_SOURCE",
        "execution_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_MODEL_PREFLIGHT_EXECUTION_FAIL_STOP",
        "model_insufficient": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_WHOLE_PAIR_CAUSAL_MODEL_INSUFFICIENT_NONLINEAR_REDESIGN_REQUIRED",
        "pass": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_WHOLE_PAIR_CAUSAL_MODEL_COMPLETE_CONTROLLER_PREFLIGHT_REQUIRED",
    }
    expected_scope = {
        "zero_new_tsc": True,
        "maximum_new_tsc_trajectories": 0,
        "new_raw_allowed": False,
        "snapshot_creation_allowed": False,
        "controller_execution_allowed": False,
        "model_selection_allowed": False,
        "real_mpc_executed": False,
        "gate_a_qualified": False,
        "all_source_trajectories_allowed_in_expert_dataset": False,
        "expert_data_allowed": False,
        "bc_dagger_or_rl_allowed": False,
    }
    design = project_root.resolve() / str(cfg.get("design_document", ""))
    source_hash_values = [
        value
        for section in ("source_r51r1", "source_r8r7")
        for key, value in cfg.get(section, {}).items()
        if key.endswith("sha256") or key.endswith("digest")
    ]
    if (
        cfg.get("stage") != STAGE
        or cfg.get("identity")
        != "reduced_q0_transport_bridge_whole_pair_causal_model_preflight_v1"
        or cfg.get("run_name")
        != "stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight"
        or cfg.get("feature_contract") != expected_feature
        or cfg.get("model_contract") != expected_model
        or cfg.get("routes") != expected_routes
        or cfg.get("scientific_scope") != expected_scope
        or tuple(cfg.get("source_r51r1", {}).get("candidate_ids", ()))
        != (
            "d0m",
            "d0p",
            "d1p",
            "d2m",
            "d3m",
            "d3p",
            "u1p00",
            "u1p25",
            "u1p50",
            "v0p75",
            "v1p00",
            "v1p25",
            "v1p50",
        )
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source_hash_values
        or any(not isinstance(value, str) or len(value) != 64 for value in source_hash_values)
    ):
        raise ValueError("R8R51R2 frozen design changed")


def _strict_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {value}")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_strict_constant)


def _read_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=_strict_constant)


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    rows = []
    combined = hashlib.sha256()
    for item in sorted(path.glob("*.json.gz"), key=lambda value: value.name):
        size = item.stat().st_size
        sha = _sha(item)
        combined.update(f"{item.name}\0{size}\0{sha}\n".encode("utf-8"))
        rows.append({"name": item.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": combined.hexdigest(),
        "rows": rows,
    }


def _stage(source_run: Path, contract: Mapping[str, Any]) -> Path:
    return source_run.expanduser().resolve() / str(contract["stage_directory"])


def _source_paths(r51_stage: Path, r7_stage: Path) -> dict[str, Path]:
    return {
        "r51_raw_primary": r51_stage / "analysis/raw_primary.json",
        "r51_raw_independent": r51_stage / "analysis/raw_independent.json",
        "r51_hotfix_primary": r51_stage
        / "analysis/q0_first_effect_reporting_hotfix_primary.json",
        "r51_hotfix_independent": r51_stage
        / "analysis/q0_first_effect_reporting_hotfix_independent.json",
        "r51_compact_audit": r51_stage
        / "analysis/q0_first_effect_reporting_hotfix_compact_audit.json",
        "r51_final_report": r51_stage
        / "analysis/q0_first_effect_reporting_hotfix_final_report.json",
        "r51_state": r51_stage / "stage_state.json",
        "r51_manifest": r51_stage / "stage_manifest.json",
        "r51_specs": r51_stage / "specs/all_specs.json",
        "r51_offline_construction": r51_stage / "analysis/offline_construction.json",
        "r7_all_specs": r7_stage / "specs/all_specs.json",
        "r7_baseline_specs": r7_stage / "specs/baseline_specs.json",
        "r7_final_report": r7_stage / "analysis/final_report.json",
        "r7_manifest": r7_stage / "stage_manifest.json",
        "r7_state": r7_stage / "stage_state.json",
    }


def authenticate_sources(
    cfg: Mapping[str, Any], r51_run: Path, r7_run: Path
) -> dict[str, Any]:
    c51 = cfg["source_r51r1"]
    c7 = cfg["source_r8r7"]
    r51_stage = _stage(r51_run, c51)
    r7_stage = _stage(r7_run, c7)
    project = Path(__file__).resolve().parents[2]
    r51_source_paths = {
        "config": project
        / "configs/stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel_370ms.json",
        "implementation": project
        / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel.py",
    }
    for name, expected in (
        ("config", c51["config_sha256"]),
        ("implementation", c51["implementation_sha256"]),
    ):
        if (
            not r51_source_paths[name].is_file()
            or _sha(r51_source_paths[name]) != expected
        ):
            raise ValueError(f"R8R51R2 R51R1 source code changed: {name}")
    if r51_stage.parent.name != c51["run_name"] or r7_stage.parent.name != c7["run_name"]:
        raise ValueError("R8R51R2 source run identity changed")
    paths = _source_paths(r51_stage, r7_stage)
    hashes = {
        "r51_raw_primary": c51["raw_primary_sha256"],
        "r51_raw_independent": c51["raw_independent_sha256"],
        "r51_hotfix_primary": c51["hotfix_primary_sha256"],
        "r51_hotfix_independent": c51["hotfix_independent_sha256"],
        "r51_compact_audit": c51["compact_audit_sha256"],
        "r51_final_report": c51["final_report_sha256"],
        "r51_state": c51["stage_state_sha256"],
        "r51_manifest": c51["stage_manifest_sha256"],
        "r51_specs": c51["all_specs_sha256"],
        "r51_offline_construction": c51["offline_construction_sha256"],
        "r7_all_specs": c7["all_specs_sha256"],
        "r7_baseline_specs": c7["baseline_specs_sha256"],
        "r7_final_report": c7["final_report_sha256"],
        "r7_manifest": c7["stage_manifest_sha256"],
        "r7_state": c7["stage_state_sha256"],
    }
    for name, expected in hashes.items():
        if not paths[name].is_file() or _sha(paths[name]) != expected:
            raise ValueError(f"R8R51R2 source artifact changed: {name}")
    raw_inventory = _inventory(r51_stage / "raw")
    baseline_inventory = _inventory(r7_stage / "raw/baseline")
    if (
        raw_inventory["count"] != int(c51["raw_count"])
        or raw_inventory["bytes"] != int(c51["raw_bytes"])
        or raw_inventory["digest"] != c51["raw_inventory_digest"]
        or baseline_inventory["count"] != int(c7["baseline_raw_count"])
        or baseline_inventory["bytes"] != int(c7["baseline_raw_bytes"])
        or baseline_inventory["digest"] != c7["baseline_raw_digest"]
    ):
        raise ValueError("R8R51R2 source raw inventory changed")
    raw_primary = _read(paths["r51_raw_primary"])
    raw_independent = _read(paths["r51_raw_independent"])
    hotfix_primary = _read(paths["r51_hotfix_primary"])
    hotfix_independent = _read(paths["r51_hotfix_independent"])
    final = _read(paths["r51_final_report"])
    state = _read(paths["r51_state"])
    manifest = _read(paths["r51_manifest"])
    r7_final = _read(paths["r7_final_report"])
    r7_state = _read(paths["r7_state"])
    required_counts = (
        "strict_parse_count",
        "runtime_success_count",
        "full_horizon_count",
        "authentic_restart_count",
        "source_prefix_state_exact_count",
        "source_prefix_trace_exact_count",
        "source_trace_difference_wrapper_only_count",
        "causal_forbidden_pass_count",
        "q0_exact_count",
        "q0_offline_parity_count",
        "within_context_q0_prefix_exact_count",
        "candidate_exact_count",
        "candidate_issue_gate_pass_count",
        "first_effect_at_issue_plus_one_count",
        "finite_response_count",
        "stored_center_return_exact_count",
    )
    if (
        raw_primary.get("route") != OLD_R51R1_ROUTE
        or any(int(raw_primary.get(key, -1)) != 208 for key in required_counts)
        or int(raw_primary.get("runtime_failure_count", -1)) != 0
        or int(raw_primary.get("safety_stop_count", -1)) != 0
        or raw_independent.get("primary_agreement") is not True
        or hotfix_primary.get("passed") is not True
        or hotfix_independent.get("passed") is not True
        or hotfix_independent.get("primary_agreement") is not True
        or final.get("passed") is not True
        or final.get("primary_independent_agreement") is not True
        or final.get("route") != c51["required_route"]
        or int(final.get("corrected_numerical_equivalence_count", -1)) != 208
        or final.get("raw_inventory") != raw_inventory
        or final.get("prefix_digest") != c51["prefix_digest"]
        or final.get("response_digest") != c51["response_digest"]
        or state.get("route") != OLD_R51R1_ROUTE
        or state.get("real_tsc_executed") is not True
        or int(state.get("new_raw_count", -1)) != 208
        or manifest.get("spec_digest") != c51["spec_digest"]
        or int(manifest.get("spec_count", -1)) != 208
        or r7_final.get("route") != c7["required_route"]
        or r7_final.get("passed") is not True
        or r7_state.get("finished") is not True
    ):
        raise ValueError("R8R51R2 final source route or integrity changed")
    specs = _read(paths["r51_specs"])
    if _digest(specs) != c51["spec_digest"]:
        raise ValueError("R8R51R2 R51R1 spec digest changed")
    return {
        "r51_stage": r51_stage,
        "r7_stage": r7_stage,
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": hashes,
        "r51_source_code_paths": {
            name: str(path) for name, path in r51_source_paths.items()
        },
        "raw_inventory": raw_inventory,
        "baseline_inventory": baseline_inventory,
        "specs": specs,
        "raw_primary": raw_primary,
        "passed": True,
    }


def causal_feature44(
    trajectory: Sequence[Mapping[str, Any]], current_scales: Sequence[float]
) -> np.ndarray:
    scales = np.asarray(current_scales, dtype=float).reshape(N_COILS)
    if np.any(scales <= 0.0) or not np.all(np.isfinite(scales)):
        raise ValueError("R8R51R2 source current scales invalid")
    visible = np.asarray(
        [
            [float(trajectory[step][key]) for key in ("R", "Z", "Ip")]
            for step in (9, 10, 11, 12)
        ],
        dtype=float,
    ).reshape(-1)
    current = np.asarray(trajectory[12]["currents_a_tsc"], dtype=float).reshape(N_COILS)
    previous = np.asarray(trajectory[10]["currents_a_tsc"], dtype=float).reshape(
        N_COILS
    )
    feature = np.concatenate(
        (visible, current / scales, (current - previous) / scales, ZERO_Q / 1.5)
    )
    if feature.shape != (44,) or not np.all(np.isfinite(feature)):
        raise ValueError("R8R51R2 causal feature is not finite 44D")
    return feature


def expanded_feature180(
    feature: Sequence[float], q: Sequence[float], mean: Sequence[float], scale: Sequence[float]
) -> np.ndarray:
    base = np.asarray(feature, dtype=float).reshape(44)
    q_scaled = np.asarray(q, dtype=float).reshape(4) / 1.5
    whitened = (base - np.asarray(mean, dtype=float).reshape(44)) / np.asarray(
        scale, dtype=float
    ).reshape(44)
    expanded = np.concatenate((q_scaled, np.outer(whitened, q_scaled).reshape(-1)))
    if expanded.shape != (180,) or not np.all(np.isfinite(expanded)):
        raise ValueError("R8R51R2 expanded feature is not finite 180D")
    return expanded


def _physical_prefix_equal(
    current: Sequence[Mapping[str, Any]], reference: Sequence[Mapping[str, Any]]
) -> bool:
    return all(
        all(current[step][key] == reference[step][key] for key in ("R", "Z", "Ip"))
        and current[step]["currents_a_tsc"] == reference[step]["currents_a_tsc"]
        for step in (9, 10, 11, 12)
    )


def build_bank(cfg: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    r51_stage = Path(source["r51_stage"])
    r7_stage = Path(source["r7_stage"])
    old_rows = {
        str(row["experiment_id"]): row for row in source["raw_primary"]["rows"]
    }
    baselines: dict[str, dict[str, Any]] = {}
    rows = []
    prefix_count = 0
    for spec in source["specs"]:
        experiment_id = str(spec["experiment_id"])
        raw_path = r51_stage / "raw" / f"{experiment_id}.json.gz"
        result = _read_gzip(raw_path)
        baseline_id = str(spec["source_r8r7_baseline_experiment_id"])
        if baseline_id not in baselines:
            baselines[baseline_id] = _read_gzip(
                r7_stage / "raw/baseline" / f"{baseline_id}.json.gz"
            )
        baseline = baselines[baseline_id]
        old = old_rows.get(experiment_id)
        trajectory = result.get("trajectory") or []
        reference = baseline.get("trajectory") or []
        horizon = int(spec["horizon_steps"])
        if (
            old is None
            or result.get("success") is not True
            or result.get("spec") != spec
            or len(trajectory) != horizon + 1
            or baseline.get("success") is not True
            or len(reference) != horizon + 1
            or str(baseline.get("experiment_id")) != baseline_id
            or not all(
                old.get(key) is True
                for key in (
                    "runtime_success",
                    "full_horizon",
                    "authentic_restart",
                    "source_prefix_state_exact",
                    "source_prefix_trace_exact",
                    "source_trace_difference_wrapper_only",
                    "calibration_exact",
                    "q0_exact",
                    "q0_offline_parity",
                    "within_context_q0_prefix_exact",
                    "candidate_exact",
                    "event_sequence_exact",
                    "event_gates_passed",
                    "first_effect_at_issue_plus_one",
                    "finite_response",
                    "return_exact",
                    "finite",
                )
            )
            or int(old.get("forbidden_trace_count", -1)) != 0
        ):
            raise ValueError(f"R8R51R2 strict source row changed: {experiment_id}")
        prefix = _physical_prefix_equal(trajectory, reference)
        prefix_count += int(prefix)
        if not prefix:
            raise ValueError(f"R8R51R2 q0 reference prefix changed: {experiment_id}")
        payload = _read(r51_stage / "variants" / f"payload_{experiment_id}.json")
        minimum = np.asarray(payload["min_current_tsc"], dtype=float).reshape(N_COILS)
        maximum = np.asarray(payload["max_current_tsc"], dtype=float).reshape(N_COILS)
        current_scales = np.maximum(np.abs(minimum), np.abs(maximum))
        feature = causal_feature44(trajectory, current_scales)
        q = np.asarray(spec["r8r51r1_candidate_q"], dtype=float).reshape(4)
        response = np.asarray(
            [
                float(trajectory[step][key]) - float(reference[step][key])
                for step in (13, 14)
                for key in ("R", "Z", "Ip")
            ],
            dtype=float,
        )
        if not np.all(np.isfinite(q)) or not np.all(np.isfinite(response)):
            raise ValueError(f"R8R51R2 non-finite bank row: {experiment_id}")
        rows.append(
            {
                "row_id": experiment_id,
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": int(spec["r8r51r1_candidate_index"]),
                "candidate_id": str(spec["r8r51r1_candidate_id"]),
                "feature": feature,
                "q": q,
                "response": response,
                "normalized_response": response
                / np.asarray(cfg["model_contract"]["output_scales"], dtype=float),
                "current_scales": current_scales,
                "source_baseline_id": baseline_id,
            }
        )
    rows.sort(key=lambda row: row["row_id"])
    pairs = sorted({row["pair_id"] for row in rows})
    contexts = {(row["pair_id"], row["history_member"]) for row in rows}
    candidate_ids = list(cfg["source_r51r1"]["candidate_ids"])
    coverage = {
        key: [
            row["candidate_id"]
            for row in rows
            if (row["pair_id"], row["history_member"]) == key
        ]
        for key in contexts
    }
    if (
        len(rows) != 208
        or len(pairs) != 8
        or len(contexts) != 16
        or len(baselines) != 16
        or prefix_count != 208
        or any(sorted(values) != sorted(candidate_ids) for values in coverage.values())
        or any(sum(row["pair_id"] == pair for row in rows) != 26 for pair in pairs)
    ):
        raise ValueError("R8R51R2 immutable bank coverage changed")
    serial = [
        {
            "row_id": row["row_id"],
            "pair_id": row["pair_id"],
            "history_member": row["history_member"],
            "candidate_index": row["candidate_index"],
            "candidate_id": row["candidate_id"],
            "feature": row["feature"].tolist(),
            "q": row["q"].tolist(),
            "response": row["response"].tolist(),
            "current_scales": row["current_scales"].tolist(),
            "source_baseline_id": row["source_baseline_id"],
        }
        for row in rows
    ]
    return {
        "rows": rows,
        "serial_rows": serial,
        "pairs": pairs,
        "row_count": len(rows),
        "context_count": len(contexts),
        "source_baseline_count": len(baselines),
        "physical_prefix_exact_count": prefix_count,
        "forbidden_model_input_count": 0,
        "source_or_row_exclusion_count": 0,
        "bank_digest": _digest(serial),
        "feature_digest": _digest([row["feature"] for row in serial]),
        "response_digest": _digest([row["response"] for row in serial]),
    }


def fit_model(
    rows: Sequence[Mapping[str, Any]], training_pairs: Iterable[str], ridge: float
) -> dict[str, Any]:
    allowed = set(map(str, training_pairs))
    selected = [row for row in rows if str(row["pair_id"]) in allowed]
    feature = np.asarray([row["feature"] for row in selected], dtype=float)
    mean = np.mean(feature, axis=0)
    raw_scale = np.std(feature, axis=0)
    scale = np.where(raw_scale < 1e-12, 1.0, raw_scale)
    x = np.asarray(
        [expanded_feature180(row["feature"], row["q"], mean, scale) for row in selected],
        dtype=float,
    )
    y = np.asarray([row["normalized_response"] for row in selected], dtype=float)
    coefficients = np.linalg.solve(
        x.T @ x + float(ridge) * np.eye(180, dtype=float), x.T @ y
    )
    if coefficients.shape != (180, 6) or not np.all(np.isfinite(coefficients)):
        raise ValueError("R8R51R2 ridge coefficients invalid")
    return {
        "training_pairs": sorted(allowed),
        "training_row_count": len(selected),
        "mean": mean,
        "scale": scale,
        "coefficients": coefficients,
    }


def predict_model(model: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    x = np.asarray(
        [
            expanded_feature180(
                row["feature"], row["q"], model["mean"], model["scale"]
            )
            for row in rows
        ],
        dtype=float,
    )
    result = x @ np.asarray(model["coefficients"], dtype=float)
    if result.shape != (len(rows), 6) or not np.all(np.isfinite(result)):
        raise ValueError("R8R51R2 prediction invalid")
    return result


def _model_serial(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "training_pairs": list(model["training_pairs"]),
        "training_row_count": int(model["training_row_count"]),
        "mean": np.asarray(model["mean"], dtype=float).tolist(),
        "scale": np.asarray(model["scale"], dtype=float).tolist(),
        "coefficients": np.asarray(model["coefficients"], dtype=float).tolist(),
    }


def evaluate_whole_pair(cfg: Mapping[str, Any], bank: Mapping[str, Any]) -> dict[str, Any]:
    rows = bank["rows"]
    pairs = list(bank["pairs"])
    contract = cfg["model_contract"]
    ridge = float(contract["ridge_penalty"])
    reserve = float(contract["tube_reserve_multiplier"])
    output_scales = np.asarray(contract["output_scales"], dtype=float)
    floors = np.asarray(contract["point_error_floors"], dtype=float)
    caps = np.asarray(contract["tube_half_width_caps"], dtype=float)
    tolerance = float(contract["comparison_absolute_tolerance"])
    folds = []
    point_count = containment_count = coverage_count = tube_fold_count = 0
    maximum_error = np.zeros(6, dtype=float)
    maximum_tube = np.zeros(6, dtype=float)
    for held_pair in pairs:
        training_pairs = [pair for pair in pairs if pair != held_pair]
        nested_maximum = np.zeros(6, dtype=float)
        nested_models = []
        for nested_held in training_pairs:
            nested_training = [pair for pair in training_pairs if pair != nested_held]
            nested_model = fit_model(rows, nested_training, ridge)
            nested_rows = [row for row in rows if row["pair_id"] == nested_held]
            nested_prediction = predict_model(nested_model, nested_rows)
            nested_actual = np.asarray(
                [row["normalized_response"] for row in nested_rows], dtype=float
            )
            residual = np.abs(nested_prediction - nested_actual) * output_scales
            nested_maximum = np.maximum(nested_maximum, np.max(residual, axis=0))
            serial_model = _model_serial(nested_model)
            nested_models.append(
                {
                    "held_pair": nested_held,
                    "model": serial_model,
                    "model_digest": _digest(serial_model),
                    "maximum_absolute_physical_residual": np.max(
                        residual, axis=0
                    ).tolist(),
                }
            )
        tube = np.maximum(floors, reserve * nested_maximum)
        tube_pass = bool(np.all(tube <= caps + tolerance))
        tube_fold_count += int(tube_pass)
        maximum_tube = np.maximum(maximum_tube, tube)
        model = fit_model(rows, training_pairs, ridge)
        held_rows = [row for row in rows if row["pair_id"] == held_pair]
        prediction = predict_model(model, held_rows)
        actual = np.asarray(
            [row["normalized_response"] for row in held_rows], dtype=float
        )
        error = np.abs(prediction - actual) * output_scales
        maximum_error = np.maximum(maximum_error, np.max(error, axis=0))
        point = np.all(error <= floors + tolerance, axis=1)
        contained = np.all(error <= tube + tolerance, axis=1)
        point_count += int(np.count_nonzero(point))
        containment_count += int(np.count_nonzero(contained))
        coverage_count += len(held_rows)
        serial_model = _model_serial(model)
        prediction_rows = [
            {
                "row_id": row["row_id"],
                "actual_response": row["response"].tolist(),
                "predicted_response": (prediction[index] * output_scales).tolist(),
                "absolute_physical_error": error[index].tolist(),
                "point_error_passed": bool(point[index]),
                "tube_contained": bool(contained[index]),
            }
            for index, row in enumerate(held_rows)
        ]
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": training_pairs,
                "outer_model": serial_model,
                "outer_model_digest": _digest(serial_model),
                "nested_models": nested_models,
                "nested_maximum_absolute_physical_residual": nested_maximum.tolist(),
                "tube_half_width": tube.tolist(),
                "tube_cap_passed": tube_pass,
                "point_error_pass_count": int(np.count_nonzero(point)),
                "containment_pass_count": int(np.count_nonzero(contained)),
                "prediction_rows": prediction_rows,
                "prediction_digest": _digest(prediction_rows),
            }
        )
    passed = bool(
        coverage_count == 208
        and point_count == 208
        and containment_count == 208
        and tube_fold_count == 8
        and bank["forbidden_model_input_count"] == 0
        and bank["source_or_row_exclusion_count"] == 0
    )
    route = cfg["routes"]["pass" if passed else "model_insufficient"]
    return {
        "folds": folds,
        "outer_fold_count": len(folds),
        "prediction_coverage_count": coverage_count,
        "point_error_pass_count": point_count,
        "containment_pass_count": containment_count,
        "tube_cap_fold_pass_count": tube_fold_count,
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_tube_half_width": maximum_tube.tolist(),
        "fold_digest": _digest(
            [
                {
                    "held_pair": fold["held_pair"],
                    "outer_model_digest": fold["outer_model_digest"],
                    "nested_model_digests": [
                        row["model_digest"] for row in fold["nested_models"]
                    ],
                    "tube_half_width": fold["tube_half_width"],
                    "prediction_digest": fold["prediction_digest"],
                }
                for fold in folds
            ]
        ),
        "route": route,
        "scientific_gate_passed": passed,
    }


def _paths(run_dir: Path, cfg: Mapping[str, Any]) -> dict[str, Path]:
    stage = run_dir.expanduser().resolve() / str(cfg["run_name"])
    return {
        "stage": stage,
        "analysis": stage / "analysis",
        "source": stage / "source_reference",
        "state": stage / "stage_state.json",
        "manifest": stage / "stage_manifest.json",
    }


def run_primary(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _read(args.config.expanduser().resolve())
    validate_config(cfg, Path(__file__).resolve().parents[2])
    paths = _paths(args.run_dir, cfg)
    if paths["stage"].exists():
        raise ValueError("R8R51R2 primary requires a fresh output identity")
    paths["analysis"].mkdir(parents=True)
    paths["source"].mkdir(parents=True)
    source = authenticate_sources(cfg, args.r51r1_run, args.r8r7_run)
    bank = build_bank(cfg, source)
    evaluation = evaluate_whole_pair(cfg, bank)
    source_serial = {
        key: value
        for key, value in source.items()
        if key not in {"specs", "raw_primary"}
    }
    source_serial["r51_stage"] = str(source["r51_stage"])
    source_serial["r7_stage"] = str(source["r7_stage"])
    bank_serial = {
        "schema_version": 1,
        "stage": STAGE,
        "rows": bank["serial_rows"],
        "row_count": bank["row_count"],
        "context_count": bank["context_count"],
        "source_baseline_count": bank["source_baseline_count"],
        "physical_prefix_exact_count": bank["physical_prefix_exact_count"],
        "forbidden_model_input_count": bank["forbidden_model_input_count"],
        "source_or_row_exclusion_count": bank["source_or_row_exclusion_count"],
        "bank_digest": bank["bank_digest"],
        "feature_digest": bank["feature_digest"],
        "response_digest": bank["response_digest"],
    }
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "primary",
        "bank_digest": bank["bank_digest"],
        "feature_digest": bank["feature_digest"],
        "response_digest": bank["response_digest"],
        **evaluation,
        "new_tsc_count": 0,
        "new_raw_count": 0,
        "snapshot_count": 0,
        "controller_execution_count": 0,
        "plant_step_count": 0,
        "model_selection_count": 0,
    }
    summary = {
        key: detailed[key]
        for key in (
            "schema_version",
            "stage",
            "phase",
            "bank_digest",
            "feature_digest",
            "response_digest",
            "outer_fold_count",
            "prediction_coverage_count",
            "point_error_pass_count",
            "containment_pass_count",
            "tube_cap_fold_pass_count",
            "maximum_absolute_physical_error",
            "maximum_tube_half_width",
            "fold_digest",
            "route",
            "scientific_gate_passed",
            "new_tsc_count",
            "new_raw_count",
            "snapshot_count",
            "controller_execution_count",
            "plant_step_count",
            "model_selection_count",
        )
    }
    summary.update(
        {
            "source_authentication_passed": True,
            "strict_source_row_count": bank["row_count"],
            "finite_causal_response_row_count": bank["row_count"],
            "physical_prefix_exact_count": bank["physical_prefix_exact_count"],
            "forbidden_model_input_count": bank["forbidden_model_input_count"],
            "source_or_row_exclusion_count": bank["source_or_row_exclusion_count"],
            "primary_integrity_passed": True,
        }
    )
    _write(paths["source"] / "source_authentication.json", source_serial)
    _write(paths["analysis"] / "bank_detailed.json", bank_serial)
    _write(paths["analysis"] / PRIMARY_DETAIL, detailed)
    _write(paths["analysis"] / PRIMARY_SUMMARY, summary)
    project = Path(__file__).resolve().parents[2]
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": cfg["identity"],
        "package_revision": cfg["package_revision"],
        "config_sha256": _sha(args.config.expanduser().resolve()),
        "design_document_sha256": cfg["design_document_sha256"],
        "package_manifest_sha256": _sha(project / "PACKAGE_MANIFEST.json"),
        "sha256sums_sha256": _sha(project / "SHA256SUMS"),
        "source_r51r1_run": str(args.r51r1_run.expanduser().resolve()),
        "source_r8r7_run": str(args.r8r7_run.expanduser().resolve()),
        "source_authentication_sha256": _sha(
            paths["source"] / "source_authentication.json"
        ),
        "bank_detailed_sha256": _sha(paths["analysis"] / "bank_detailed.json"),
        "primary_detailed_sha256": _sha(paths["analysis"] / PRIMARY_DETAIL),
        "primary_summary_sha256": _sha(paths["analysis"] / PRIMARY_SUMMARY),
        "new_tsc_count": 0,
        "new_raw_count": 0,
        "all_source_trajectories_allowed_in_expert_dataset": False,
    }
    _write(paths["manifest"], manifest)
    state = {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "primary_ready",
        "finished": False,
        "route": summary["route"],
        "scientific_gate_passed": summary["scientific_gate_passed"],
        "new_tsc_count": 0,
        "new_raw_count": 0,
        "snapshot_count": 0,
        "controller_execution_count": 0,
        "plant_step_count": 0,
        "model_selection_count": 0,
        "source_outcomes_opened": True,
        "all_source_trajectories_allowed_in_expert_dataset": False,
    }
    _write(paths["state"], state)
    return summary


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _read(args.config.expanduser().resolve())
    validate_config(cfg, Path(__file__).resolve().parents[2])
    paths = _paths(args.run_dir, cfg)
    primary = _read(paths["analysis"] / PRIMARY_SUMMARY)
    independent = _read(paths["analysis"] / INDEPENDENT)
    state = _read(paths["state"])
    if (
        state.get("phase_status") != "primary_ready"
        or independent.get("audit_passed") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("route") != primary.get("route")
        or independent.get("scientific_gate_passed")
        != primary.get("scientific_gate_passed")
    ):
        raise ValueError("R8R51R2 finalization integrity failed")
    compact = {
        **primary,
        "phase": "compact_audit",
        "primary_summary_sha256": _sha(paths["analysis"] / PRIMARY_SUMMARY),
        "primary_detailed_sha256": _sha(paths["analysis"] / PRIMARY_DETAIL),
        "independent_sha256": _sha(paths["analysis"] / INDEPENDENT),
        "primary_independent_numerical_agreement": independent[
            "primary_numerical_agreement"
        ],
        "primary_independent_discrete_agreement": independent[
            "primary_discrete_agreement"
        ],
        "maximum_primary_numerical_difference": independent[
            "maximum_primary_numerical_difference"
        ],
        "audit_passed": True,
    }
    _write(paths["analysis"] / "compact_audit.json", compact)
    final = {
        **compact,
        "phase": "final",
        "compact_audit_sha256": _sha(paths["analysis"] / "compact_audit.json"),
        "passed": bool(primary["scientific_gate_passed"]),
        "classification": {
            "runtime_or_environment_error": False,
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": False,
            "summary_or_reporting_error": False,
            "model_design_failure": not bool(primary["scientific_gate_passed"]),
            "real_controller_or_mpc_executed": False,
            "gate_a_qualified": False,
        },
        "all_source_trajectories_allowed_in_expert_dataset": False,
    }
    _write(paths["analysis"] / "final_report.json", final)
    state.update(
        {
            "phase_status": "complete",
            "finished": True,
            "route": final["route"],
            "scientific_gate_passed": final["scientific_gate_passed"],
            "final_report_sha256": _sha(paths["analysis"] / "final_report.json"),
        }
    )
    _write(paths["state"], state)
    manifest = _read(paths["manifest"])
    manifest.update(
        {
            "independent_sha256": _sha(paths["analysis"] / INDEPENDENT),
            "compact_audit_sha256": _sha(paths["analysis"] / "compact_audit.json"),
            "final_report_sha256": _sha(paths["analysis"] / "final_report.json"),
            "stage_state_sha256": _sha(paths["state"]),
            "finished": True,
        }
    )
    _write(paths["manifest"], manifest)
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", choices=("primary", "finalize"), required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r51r1-run", type=Path)
    parser.add_argument("--r8r7-run", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "primary":
        if args.r51r1_run is None or args.r8r7_run is None:
            raise ValueError("R8R51R2 primary requires both source run paths")
        result = run_primary(args)
    else:
        result = finalize(args)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
