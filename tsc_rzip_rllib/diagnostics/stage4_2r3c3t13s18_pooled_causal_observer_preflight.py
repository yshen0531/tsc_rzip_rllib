"""Stage4.2R3c3T13S18 pooled causal observer development preflight.

This module consumes immutable S16/S17 development evidence.  It never calls
TSC and never creates plant trajectories.  Pair labels are used only for
whole-pair fold assignment and are not predictor features.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s17_causal_multi_drift_belief_preflight as s17,
)


STAGE = "Stage4.2R3c3T13S18"
SCHEMA_VERSION = 1
PASS_ROUTE = "POOLED_CAUSAL_OBSERVER_PREFLIGHT_PASS_FRESH_CAMPAIGN_REQUIRED"
FAIL_ROUTE = "POOLED_CAUSAL_OBSERVER_PREFLIGHT_FAIL_EXCITATION_OR_OBSERVER_REDESIGN"
BASELINE_PROBE_ID = "lattice_baseline"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _load_config(path: Path) -> dict[str, Any]:
    cfg = _read_json(path)
    _validate_config(cfg)
    return cfg


def _validate_config(cfg: Mapping[str, Any]) -> None:
    features = cfg["causal_features"]
    model = cfg["pooled_model"]
    gates = cfg["gates"]
    execution = cfg["execution"]
    expected_codes = np.asarray([
        [1, 0, 0, 0], [-1, 0, 0, 0],
        [0, 1, 0, 0], [0, -1, 0, 0],
        [0, 0, 1, 0], [0, 0, -1, 0],
        [0, 0, 0, 1], [0, 0, 0, -1],
        [0, 0, 0, 0], [0, 0, 0, 0],
    ], dtype=float)
    if (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("audit_identity") != "pooled_causal_observer_preflight_v1"
        or cfg.get("package_revision")
        != "r42r3c3t13s18_pooled_causal_observer_preflight_v1"
    ):
        raise ValueError("T13S18 identity changed")
    if (
        tuple(map(int, features["visible_state_indices"])) != tuple(range(1, 11))
        or tuple(map(int, features["input_steps"])) != tuple(range(10))
        or not np.array_equal(np.asarray(features["fixed_input_codes"], dtype=float), expected_codes)
        or int(features["legendre_degree"]) != 3
        or int(features["feature_count"]) != 9
        or int(features["response_issue_step"]) != 10
        or int(features["response_first_effect_state"]) != 11
        or tuple(map(float, features["response_floor"])) != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or tuple(map(float, features["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 2000.0)
        or tuple(map(float, features["belief_halfwidth_caps"])) != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(features["feature_equivalence_tolerance"]) != 1e-12
        or float(features["containment_tolerance"]) != 1e-12
    ):
        raise ValueError("T13S18 causal feature contract changed")
    if (
        model["outer_fold_key"] != "pair_id"
        or int(model["expected_outer_folds"]) != 8
        or int(model["expected_rows_per_outer_fold"]) != 16
        or tuple(map(float, model["ridge_grid"]))
        != (0.0, 1e-8, 1e-6, 1e-4, 1e-2, 1.0, 100.0)
        or float(model["standard_deviation_floor"]) != 1e-12
        or float(model["tube_multiplier"]) != 4.0
        or tuple(model["selection_order"]) != (
            "maximum_absolute_scaled_oof_error",
            "mean_squared_scaled_oof_error",
            "ridge_value",
        )
    ):
        raise ValueError("T13S18 pooled model contract changed")
    if (
        int(gates["expected_source_raw"]) != 144
        or int(gates["expected_response_rows"]) != 128
        or int(gates["expected_outer_folds"]) != 8
        or int(gates["expected_held_rows_per_fold"]) != 16
        or not bool(gates["require_artifact_before_held_outcome"])
        or not bool(gates["require_all_response_contained"])
        or not bool(gates["require_all_belief_caps"])
        or int(gates["maximum_forbidden_predictor_input_count"]) != 0
        or int(gates["maximum_new_tsc_or_plant_steps"]) != 0
    ):
        raise ValueError("T13S18 gate contract changed")
    if any(bool(execution[key]) for key in (
        "new_tsc_allowed", "ray_allowed", "gotsc_allowed", "controller_allowed",
        "optimizer_allowed", "probe_trajectories_allowed_in_expert_dataset",
        "bc_dagger_or_rl_allowed",
    )):
        raise ValueError("T13S18 execution prohibition changed")


def _authenticate_s17(cfg: Mapping[str, Any], s17_run: Path) -> dict[str, Any]:
    prior = cfg["prior_s17"]
    paths = {
        "belief": s17_run / "causal_belief_artifact.json",
        "final": s17_run / "final_result.json",
        "state": s17_run / "stage4_2r3c3t13s17_state.json",
    }
    actual = {key: _sha256(path) if path.is_file() else "" for key, path in paths.items()}
    expected = {
        "belief": prior["causal_belief_sha256"],
        "final": prior["final_result_sha256"],
        "state": prior["state_sha256"],
    }
    if actual != expected:
        raise ValueError("T13S18 prior S17 hash mismatch")
    belief = _read_json(paths["belief"])
    final = _read_json(paths["final"])
    state = _read_json(paths["state"])
    if (
        belief.get("audit_identity") != prior["audit_identity"]
        or belief.get("response_row_count") != 128
        or belief.get("outcome_value_access_count") != 0
        or final.get("route") != prior["expected_route"]
        or final.get("containment_pass_count") != 128
        or final.get("belief_cap_pass_count") != 0
        or state.get("verdict", {}).get("route") != prior["expected_route"]
        or not bool(state.get("finished"))
    ):
        raise ValueError("T13S18 prior S17 semantic mismatch")
    return {
        "s17_run": str(s17_run.resolve()),
        "hashes": actual,
        "response_row_count": 128,
        "passed": True,
    }


def _degree3_design(cfg: Mapping[str, Any]) -> np.ndarray:
    inputs = np.asarray(cfg["causal_features"]["fixed_input_codes"], dtype=float)
    polynomial = np.polynomial.legendre.legvander(np.linspace(-1.0, 1.0, 10), 3)
    design = np.column_stack((polynomial, inputs))
    if design.shape != (10, 8) or np.linalg.matrix_rank(design) != 8:
        raise ValueError("T13S18 degree-three causal design lost rank")
    return design


def _basis_and_coordinate(
    result: Mapping[str, Any], payload: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    trace = result["controller_trace"]
    recorded = [row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc") or [] for row in trace[:11]]
    if (
        len(recorded) != 11 or any(row != recorded[0] for row in recorded)
        or np.asarray(recorded[0], dtype=float).shape != (4, 14)
    ):
        raise ValueError("T13S18 fixed basis is not constant and causal")
    turns = s17._turns_tsc(payload)
    basis = np.asarray(recorded[0], dtype=float).T * 1000.0 / turns[:, None]
    signed_field = np.asarray(
        trace[10].get("r3c3t13s9_signed_issue_delta_kAt_tsc"), dtype=float
    )
    if signed_field.shape != (14,) or not np.all(np.isfinite(signed_field)):
        raise ValueError("T13S18 same-trajectory signed action is missing")
    requested_current = signed_field * 1000.0 / turns
    coordinate, _, _, _ = np.linalg.lstsq(basis, requested_current, rcond=None)
    reconstructed = basis @ coordinate
    request_norm = float(np.linalg.norm(requested_current))
    cosine = float(
        np.dot(requested_current, reconstructed)
        / max(request_norm * float(np.linalg.norm(reconstructed)), 1e-300)
    )
    off_basis = float(np.linalg.norm(requested_current - reconstructed) / max(request_norm, 1e-300))
    prediction = s17._prediction(trace[10])
    uncertainty_units = np.asarray(prediction["uncertainty_radius_grid_units_tsc"], dtype=float)
    bias_units = np.asarray(prediction["bias_grid_units_tsc"], dtype=float)
    output_grid = float(prediction["output_grid_kAt"])
    if (
        uncertainty_units.shape != (14,) or bias_units.shape != (14,)
        or np.any(uncertainty_units < 1.0)
        or output_grid != 1e-6
    ):
        raise ValueError("T13S18 current-run quantized uncertainty changed")
    grid_a = output_grid * 1000.0 / turns
    center_fields = trace[10].get("r3c3t13s16_center_card15_fields") or []
    if len(center_fields) != 14:
        raise ValueError("T13S18 same-trajectory Card15 center fields are missing")
    center_target = np.asarray([
        float(str(field).strip()) * 1000.0 / turn
        for field, turn in zip(center_fields, turns)
    ])
    center_nominal = center_target - bias_units * grid_a
    center_lower = center_nominal - uncertainty_units * grid_a
    center_upper = center_nominal + uncertainty_units * grid_a
    center_radius = 0.5 * (center_upper - center_lower)
    probe_lower = np.asarray(prediction["readback_lower_a_tsc"], dtype=float)
    probe_upper = np.asarray(prediction["readback_upper_a_tsc"], dtype=float)
    if probe_lower.shape != (14,) or probe_upper.shape != (14,):
        raise ValueError("T13S18 current-run probe readback interval is missing")
    probe_radius = 0.5 * (probe_upper - probe_lower)
    coordinate_radius = np.abs(np.linalg.pinv(basis)) @ (center_radius + probe_radius)
    return basis, coordinate, coordinate_radius, cosine, off_basis


def _causal_row(
    result: Mapping[str, Any], payload: Mapping[str, Any], cfg: Mapping[str, Any],
    s17_row: Mapping[str, Any], design: np.ndarray,
) -> dict[str, Any]:
    trace = result["controller_trace"]
    forbidden_trace = sum(bool(trace[10].get(key, False)) for key in (
        "pair_or_history_label_used", "source_action_used", "source_result_used",
        "source_wire_current_used", "source_coil_current_used", "hidden_wire_used",
        "future_measurement_used", "current_run_future_used",
    ))
    if forbidden_trace:
        raise ValueError("T13S18 source trace used forbidden information")
    outputs = s17._visible_outputs_prefix(result)
    coefficients = np.linalg.pinv(design) @ outputs
    _, coordinate, coordinate_radius, cosine, off_basis = _basis_and_coordinate(result, payload)
    query = np.concatenate((np.zeros(4), coordinate))
    prediction = query @ coefficients
    input_coefficients = coefficients[-4:]
    prediction_radius = np.abs(input_coefficients).T @ coordinate_radius
    feature = np.concatenate((prediction, coordinate))
    feature_radius = np.concatenate((prediction_radius, coordinate_radius))
    saved_h3 = next(item for item in s17_row["hypotheses"] if int(item["degree"]) == 3)
    tolerance = float(cfg["causal_features"]["feature_equivalence_tolerance"])
    equivalence = bool(
        np.allclose(prediction, saved_h3["prediction"], rtol=0.0, atol=tolerance)
        and np.allclose(coordinate, s17_row["response_basis_coordinates"], rtol=0.0, atol=tolerance)
        and np.allclose(coordinate_radius, s17_row["response_basis_coordinate_radius"], rtol=0.0, atol=tolerance)
        and np.allclose(prediction_radius, saved_h3["input_radius"], rtol=0.0, atol=tolerance)
    )
    if (
        feature.shape != (9,) or feature_radius.shape != (9,)
        or not np.all(np.isfinite(feature)) or not np.all(np.isfinite(feature_radius))
        or np.any(feature_radius < 0.0) or cosine < 0.98 or off_basis > 0.15
        or not equivalence
    ):
        raise ValueError("T13S18 causal feature reconstruction failed")
    spec = result["spec"]
    return {
        "experiment_id": str(result["experiment_id"]),
        "baseline_experiment_id": str(s17_row["baseline_experiment_id"]),
        "fold_key": str(spec["pair_id"]),
        "feature": feature.tolist(),
        "feature_radius": feature_radius.tolist(),
        "same_trajectory_coordinate": True,
        "s17_feature_equivalence": True,
        "basis_cosine": cosine,
        "basis_relative_residual": off_basis,
        "forbidden_predictor_input_count": 0,
    }


def _build_causal_rows(
    cfg: Mapping[str, Any], source_run: Path, s17_run: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Mapping[str, Any]]]:
    source_audit, results = s17._authenticate_source(cfg, source_run)
    s17_audit = _authenticate_s17(cfg, s17_run)
    source_paths = s17._source_paths(source_run)
    belief = _read_json(s17_run / "causal_belief_artifact.json")
    saved = {str(row["experiment_id"]): row for row in belief["rows"]}
    by_id = {str(result["experiment_id"]): result for result in results}
    probes = sorted(
        (result for result in results if result["spec"].get("r3c3_probe_id") != BASELINE_PROBE_ID),
        key=lambda value: str(value["experiment_id"]),
    )
    if len(probes) != 128 or set(saved) != {str(result["experiment_id"]) for result in probes}:
        raise ValueError("T13S18 source/S17 response identity mismatch")
    design = _degree3_design(cfg)
    rows = []
    for result in probes:
        experiment_id = str(result["experiment_id"])
        payload = s17._payload(source_paths, experiment_id)
        row = _causal_row(result, payload, cfg, saved[experiment_id], design)
        if row["baseline_experiment_id"] not in by_id:
            raise ValueError("T13S18 matched response baseline is missing")
        rows.append(row)
    groups = sorted({row["fold_key"] for row in rows})
    counts = {group: sum(row["fold_key"] == group for row in rows) for group in groups}
    if len(groups) != 8 or set(counts.values()) != {16}:
        raise ValueError("T13S18 whole-pair fold coverage changed")
    return {
        "source": source_audit,
        "prior_s17": s17_audit,
        "response_row_count": len(rows),
        "outer_fold_count": len(groups),
        "passed": True,
    }, rows, by_id


def _actual_response(
    row: Mapping[str, Any], by_id: Mapping[str, Mapping[str, Any]]
) -> np.ndarray:
    return s17._actual_response(
        by_id[str(row["experiment_id"])],
        by_id[str(row["baseline_experiment_id"])],
    )


def _fit_model(
    x_train: np.ndarray, y_train_physical: np.ndarray, ridge: float,
    scales: np.ndarray, std_floor: float,
) -> dict[str, np.ndarray]:
    mean = np.mean(x_train, axis=0)
    std = np.std(x_train, axis=0)
    std = np.where(std > std_floor, std, 1.0)
    standardized = (x_train - mean) / std
    design = np.column_stack((np.ones(len(standardized)), standardized))
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    y_scaled = y_train_physical / scales
    coefficients = np.linalg.pinv(
        design.T @ design + float(ridge) * penalty
    ) @ design.T @ y_scaled
    sensitivity = (coefficients[1:].T / std[None, :]) * scales[:, None]
    return {
        "mean": mean,
        "std": std,
        "coefficients": coefficients,
        "sensitivity": sensitivity,
    }


def _predict(model: Mapping[str, np.ndarray], x: np.ndarray, scales: np.ndarray) -> np.ndarray:
    standardized = (x - model["mean"]) / model["std"]
    design = np.column_stack((np.ones(len(standardized)), standardized))
    return (design @ model["coefficients"]) * scales


def _oof(
    x: np.ndarray, y: np.ndarray, groups: np.ndarray, ridge: float,
    scales: np.ndarray, std_floor: float,
) -> np.ndarray:
    prediction = np.full_like(y, np.nan)
    for held in sorted(set(map(str, groups))):
        test = groups == held
        model = _fit_model(x[~test], y[~test], ridge, scales, std_floor)
        prediction[test] = _predict(model, x[test], scales)
    if not np.all(np.isfinite(prediction)):
        raise ValueError("T13S18 inner OOF prediction is non-finite")
    return prediction


def _serialize_model(model: Mapping[str, np.ndarray]) -> dict[str, Any]:
    return {key: np.asarray(value).tolist() for key, value in model.items()}


def _deserialize_model(model: Mapping[str, Any]) -> dict[str, np.ndarray]:
    return {key: np.asarray(value, dtype=float) for key, value in model.items()}


def _build_artifact(
    cfg: Mapping[str, Any], source_run: Path, s17_run: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    authentication, rows, by_id = _build_causal_rows(cfg, source_run, s17_run)
    groups = sorted({row["fold_key"] for row in rows})
    scales = np.asarray(cfg["causal_features"]["response_scales"], dtype=float)
    floor = np.asarray(cfg["causal_features"]["response_floor"], dtype=float)
    grid = tuple(map(float, cfg["pooled_model"]["ridge_grid"]))
    std_floor = float(cfg["pooled_model"]["standard_deviation_floor"])
    multiplier = float(cfg["pooled_model"]["tube_multiplier"])
    x_all = np.asarray([row["feature"] for row in rows], dtype=float)
    group_all = np.asarray([row["fold_key"] for row in rows])
    fold_artifacts = []
    training_outcome_access_count = 0
    held_outcome_access_before_hash_count = 0
    for outer in groups:
        train_mask = group_all != outer
        held_mask = ~train_mask
        train_rows = [row for row, keep in zip(rows, train_mask) if keep]
        held_rows = [row for row, keep in zip(rows, held_mask) if keep]
        y_train = np.asarray([_actual_response(row, by_id) for row in train_rows], dtype=float)
        training_outcome_access_count += len(train_rows)
        x_train = x_all[train_mask]
        train_groups = group_all[train_mask]
        candidates = []
        for ridge in grid:
            prediction = _oof(x_train, y_train, train_groups, ridge, scales, std_floor)
            scaled_error = np.abs(prediction - y_train) / scales
            candidates.append({
                "ridge": ridge,
                "maximum_absolute_scaled_oof_error": float(np.max(scaled_error)),
                "mean_squared_scaled_oof_error": float(np.mean(scaled_error ** 2)),
            })
        selected = min(
            candidates,
            key=lambda value: (
                value["maximum_absolute_scaled_oof_error"],
                value["mean_squared_scaled_oof_error"],
                value["ridge"],
            ),
        )
        ridge = float(selected["ridge"])
        inner_prediction = _oof(x_train, y_train, train_groups, ridge, scales, std_floor)
        residual = np.max(np.abs(inner_prediction - y_train), axis=0)
        model = _fit_model(x_train, y_train, ridge, scales, std_floor)
        held_x = x_all[held_mask]
        held_prediction = _predict(model, held_x, scales)
        held_radii = np.asarray([row["feature_radius"] for row in held_rows], dtype=float)
        propagation = held_radii @ np.abs(model["sensitivity"]).T
        halfwidth = floor + multiplier * residual + propagation
        inner_rows = []
        for row, prediction, actual in zip(train_rows, inner_prediction, y_train):
            inner_rows.append({
                "experiment_id": row["experiment_id"],
                "absolute_residual_physical": np.abs(prediction - actual).tolist(),
            })
        held_predictions = []
        for row, prediction, radius in zip(held_rows, held_prediction, halfwidth):
            held_predictions.append({
                "experiment_id": row["experiment_id"],
                "prediction": prediction.tolist(),
                "halfwidth": radius.tolist(),
            })
        fold = {
            "outer_fold": outer,
            "training_experiment_ids": sorted(row["experiment_id"] for row in train_rows),
            "held_experiment_ids": sorted(row["experiment_id"] for row in held_rows),
            "training_outcome_access_count": len(train_rows),
            "held_outcome_access_before_hash_count": 0,
            "candidate_scores": candidates,
            "selected_ridge": ridge,
            "calibration_residual_physical": residual.tolist(),
            "model": _serialize_model(model),
            "inner_oof_rows": inner_rows,
            "held_predictions": held_predictions,
        }
        fold["fold_sha256"] = _digest(fold)
        fold_artifacts.append(fold)
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "audit_identity": cfg["audit_identity"],
        "phase": "outer_fold_models_frozen_before_held_outcomes",
        "config_sha256": _sha256(_project_root() / "configs" / "stage4_2r3c3t13s18_pooled_causal_observer_preflight.json"),
        "source_raw_inventory_digest": authentication["source"]["raw_inventory_digest"],
        "prior_s17_belief_sha256": authentication["prior_s17"]["hashes"]["belief"],
        "response_row_count": len(rows),
        "outer_fold_count": len(fold_artifacts),
        "training_outcome_access_count": training_outcome_access_count,
        "held_outcome_access_before_hash_count": held_outcome_access_before_hash_count,
        "forbidden_predictor_input_count": sum(row["forbidden_predictor_input_count"] for row in rows),
        "new_tsc_or_plant_step_count": 0,
        "real_tsc_executed": False,
        "rows": rows,
        "folds": fold_artifacts,
        "passed": True,
    }
    return authentication, artifact


def prepare(
    cfg: Mapping[str, Any], source_run: Path, s17_run: Path, output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"T13S18 output identity already exists: {output_dir}")
    authentication, artifact = _build_artifact(cfg, source_run, s17_run)
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "source_authentication.json", authentication)
    artifact_path = output_dir / "pooled_observer_artifact.json"
    _write_json(artifact_path, artifact)
    artifact_sha = _sha256(artifact_path)
    state = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase_status": "fold_models_frozen",
        "finished": False,
        "source_raw_count": 144,
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "held_outcomes_opened": False,
        "pooled_observer_artifact_sha256": artifact_sha,
    }
    _write_json(output_dir / "stage4_2r3c3t13s18_state.json", state)
    return {
        "stage": STAGE,
        "phase": artifact["phase"],
        "response_row_count": artifact["response_row_count"],
        "outer_fold_count": artifact["outer_fold_count"],
        "held_outcome_access_before_hash_count": 0,
        "pooled_observer_artifact_sha256": artifact_sha,
        "real_tsc_executed": False,
        "passed": True,
    }


def _evaluate_artifact(
    cfg: Mapping[str, Any], source_run: Path, s17_run: Path,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    authentication, causal_rows, by_id = _build_causal_rows(cfg, source_run, s17_run)
    saved_rows = {row["experiment_id"]: row for row in artifact["rows"]}
    if _digest(causal_rows) != _digest(artifact["rows"]):
        raise ValueError("T13S18 causal feature artifact changed before evaluation")
    prior_final = _read_json(s17_run / "final_result.json")
    prior_actual = {
        str(row["experiment_id"]): np.asarray(row["actual_response"], dtype=float)
        for row in prior_final["rows"]
    }
    scales = np.asarray(cfg["causal_features"]["response_scales"], dtype=float)
    caps = np.asarray(cfg["causal_features"]["belief_halfwidth_caps"], dtype=float)
    tolerance = float(cfg["causal_features"]["containment_tolerance"])
    rows = []
    held_access_count = 0
    for fold in artifact["folds"]:
        expected_sha = fold["fold_sha256"]
        unhashed = {key: value for key, value in fold.items() if key != "fold_sha256"}
        if _digest(unhashed) != expected_sha or fold["held_outcome_access_before_hash_count"] != 0:
            raise ValueError("T13S18 fold artifact hash/access audit failed")
        model = _deserialize_model(fold["model"])
        held_saved = {row["experiment_id"]: row for row in fold["held_predictions"]}
        for experiment_id in fold["held_experiment_ids"]:
            causal = saved_rows[experiment_id]
            if causal["fold_key"] != fold["outer_fold"]:
                raise ValueError("T13S18 held fold identity mismatch")
            actual = _actual_response(causal, by_id)
            held_access_count += 1
            if not np.allclose(actual, prior_actual[experiment_id], rtol=0.0, atol=1e-15):
                raise ValueError("T13S18 actual response differs from S17 source recomputation")
            x = np.asarray([causal["feature"]], dtype=float)
            prediction = _predict(model, x, scales)[0]
            reported = held_saved[experiment_id]
            halfwidth = np.asarray(reported["halfwidth"], dtype=float)
            if not np.allclose(prediction, reported["prediction"], rtol=0.0, atol=1e-15):
                raise ValueError("T13S18 held prediction changed after fold hash")
            contained_components = np.abs(actual - prediction) <= halfwidth + tolerance
            cap_components = halfwidth <= caps + 1e-15
            rows.append({
                "experiment_id": experiment_id,
                "outer_fold": fold["outer_fold"],
                "selected_ridge": fold["selected_ridge"],
                "prediction": prediction.tolist(),
                "actual_response": actual.tolist(),
                "halfwidth": halfwidth.tolist(),
                "absolute_error": np.abs(actual - prediction).tolist(),
                "scaled_point_error": (np.abs(actual - prediction) / scales).tolist(),
                "contained_components": contained_components.tolist(),
                "cap_components": cap_components.tolist(),
                "containment_pass": bool(np.all(contained_components)),
                "cap_pass": bool(np.all(cap_components)),
                "passed": bool(np.all(contained_components) and np.all(cap_components)),
            })
    if len(rows) != 128 or len({row["experiment_id"] for row in rows}) != 128:
        raise ValueError("T13S18 evaluation response coverage mismatch")
    containment = sum(row["containment_pass"] for row in rows)
    cap_pass = sum(row["cap_pass"] for row in rows)
    joint = sum(row["passed"] for row in rows)
    maximum_halfwidth = np.max(np.asarray([row["halfwidth"] for row in rows]), axis=0)
    maximum_point_error = np.max(np.asarray([row["absolute_error"] for row in rows]), axis=0)
    maximum_scaled_point_error = max(max(row["scaled_point_error"]) for row in rows)
    passed = bool(
        authentication["passed"] and held_access_count == 128
        and artifact["held_outcome_access_before_hash_count"] == 0
        and artifact["forbidden_predictor_input_count"] == 0
        and containment == 128 and cap_pass == 128 and joint == 128
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "final_pooled_causal_observer_preflight",
        "route": PASS_ROUTE if passed else FAIL_ROUTE,
        "source_raw_count": 144,
        "response_row_count": len(rows),
        "outer_fold_count": 8,
        "held_outcome_access_count_after_artifact": held_access_count,
        "held_outcome_access_before_hash_count": artifact["held_outcome_access_before_hash_count"],
        "forbidden_predictor_input_count": artifact["forbidden_predictor_input_count"],
        "containment_pass_count": containment,
        "belief_cap_pass_count": cap_pass,
        "joint_pass_count": joint,
        "maximum_belief_halfwidth": maximum_halfwidth.tolist(),
        "maximum_point_absolute_error": maximum_point_error.tolist(),
        "maximum_scaled_point_error": float(maximum_scaled_point_error),
        "runtime_or_environment_error_count": 0,
        "source_raw_or_restart_error_count": 0,
        "statistics_or_reporting_error_count": 0,
        "new_tsc_or_plant_step_count": 0,
        "real_tsc_executed": False,
        "rows": rows,
        "passed": passed,
    }


def evaluate(
    cfg: Mapping[str, Any], source_run: Path, s17_run: Path, output_dir: Path,
) -> dict[str, Any]:
    artifact_path = output_dir / "pooled_observer_artifact.json"
    state_path = output_dir / "stage4_2r3c3t13s18_state.json"
    if not artifact_path.is_file() or not state_path.is_file():
        raise FileNotFoundError("T13S18 frozen artifact/state missing")
    state = _read_json(state_path)
    artifact_sha = _sha256(artifact_path)
    if (
        state.get("phase_status") != "fold_models_frozen"
        or bool(state.get("held_outcomes_opened"))
        or state.get("pooled_observer_artifact_sha256") != artifact_sha
    ):
        raise ValueError("T13S18 evaluate phase ordering failed")
    artifact = _read_json(artifact_path)
    result = _evaluate_artifact(cfg, source_run, s17_run, artifact)
    final_path = output_dir / "final_result.json"
    _write_json(final_path, result)
    state.update({
        "phase_status": "evaluation_complete",
        "finished": True,
        "primary_pass": result["passed"],
        "held_outcomes_opened": True,
        "final_result_sha256": _sha256(final_path),
        "verdict": {"route": result["route"], "passed": result["passed"]},
    })
    _write_json(state_path, state)
    return {key: result[key] for key in (
        "stage", "phase", "route", "response_row_count", "outer_fold_count",
        "containment_pass_count", "belief_cap_pass_count", "joint_pass_count",
        "maximum_belief_halfwidth", "maximum_point_absolute_error",
        "maximum_scaled_point_error", "real_tsc_executed", "passed",
    )}


def postprocess(
    cfg: Mapping[str, Any], source_run: Path, s17_run: Path, output_dir: Path,
) -> dict[str, Any]:
    artifact_path = output_dir / "pooled_observer_artifact.json"
    final_path = output_dir / "final_result.json"
    if not artifact_path.is_file() or not final_path.is_file():
        raise FileNotFoundError("T13S18 postprocess inputs missing")
    saved_artifact = _read_json(artifact_path)
    saved_final = _read_json(final_path)
    _, rebuilt_artifact = _build_artifact(cfg, source_run, s17_run)
    artifact_exact = _digest(rebuilt_artifact) == _digest(saved_artifact)
    recomputed = _evaluate_artifact(cfg, source_run, s17_run, rebuilt_artifact)
    summary_keys = (
        "route", "response_row_count", "outer_fold_count", "containment_pass_count",
        "belief_cap_pass_count", "joint_pass_count", "maximum_belief_halfwidth",
        "maximum_point_absolute_error", "maximum_scaled_point_error", "passed",
    )
    summary_exact = all(recomputed[key] == saved_final[key] for key in summary_keys)
    report = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "independent_server_side_raw_recomputation",
        "source_raw_count": 144,
        "source_raw_inventory_digest": cfg["source"]["raw_inventory_digest"],
        "response_row_count": recomputed["response_row_count"],
        "outer_fold_count": recomputed["outer_fold_count"],
        "artifact_exact_on_recomputation": artifact_exact,
        "reported_summary_exact_on_recomputation": summary_exact,
        "containment_pass_count": recomputed["containment_pass_count"],
        "belief_cap_pass_count": recomputed["belief_cap_pass_count"],
        "joint_pass_count": recomputed["joint_pass_count"],
        "model_passed": recomputed["passed"],
        "runtime_or_environment_error_count": 0,
        "source_raw_or_restart_error_count": 0,
        "statistics_or_reporting_error_count": 0 if summary_exact else 1,
        "new_tsc_or_plant_step_count": 0,
        "real_tsc_executed": False,
        "route": recomputed["route"],
        "passed": bool(artifact_exact and summary_exact),
    }
    _write_json(output_dir / "server_independent_postprocess.json", report)
    return report


def self_test(config_path: Path) -> dict[str, Any]:
    cfg = _load_config(config_path)
    groups = np.asarray([f"g{index}" for index in range(8) for _ in range(2)])
    x = np.asarray([
        [float(index), float(index % 3), 1.0, 0.5, -0.5, 1.0, 0.0, 0.0, 0.0]
        for index in range(16)
    ])
    scales = np.asarray(cfg["causal_features"]["response_scales"], dtype=float)
    weights = np.arange(45, dtype=float).reshape(9, 5) * 1e-6
    y = (x @ weights) * scales
    prediction = _oof(x, y, groups, 1e-2, scales, 1e-12)
    passed = bool(
        prediction.shape == (16, 5) and np.all(np.isfinite(prediction))
        and len(set(groups)) == 8 and float(cfg["pooled_model"]["tube_multiplier"]) == 4.0
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "self_test",
        "synthetic_rows": 16,
        "synthetic_groups": 8,
        "feature_count": 9,
        "tube_multiplier": 4.0,
        "new_tsc_or_plant_step_count": 0,
        "real_tsc_executed": False,
        "passed": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path,
        default=_project_root() / "configs" / "stage4_2r3c3t13s18_pooled_causal_observer_preflight.json",
    )
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--s17-run", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--command", choices=("prepare", "evaluate", "postprocess"), default="prepare"
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    cfg = _load_config(args.config)
    if args.self_test:
        result = self_test(args.config)
    else:
        if args.source_run is None or args.s17_run is None or args.output_dir is None:
            parser.error("--source-run, --s17-run, and --output-dir are required")
        if args.command == "prepare":
            result = prepare(cfg, args.source_run, args.s17_run, args.output_dir)
        elif args.command == "evaluate":
            result = evaluate(cfg, args.source_run, args.s17_run, args.output_dir)
        else:
            result = postprocess(cfg, args.source_run, args.s17_run, args.output_dir)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
