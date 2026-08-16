#!/usr/bin/env python3
"""Fit and evaluate the frozen zero-TSC ID-2E1 structured response model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "rgeo-zgeo-1ms-id2e1-structured-active-nominal-model-result-v1"
ARTIFACT_SCHEMA = "rgeo-zgeo-1ms-id2e1-structured-active-nominal-model-artifact-v1"
CONFIG_SHA256 = "d80f2bca63bf035cb38edd0be663b5cf470d45bddfe96523ee9cfbd1360417ce"
INPUT_ROUTE = "ONE_MS_ID2E1_INPUT_OR_SOURCE_INTEGRITY_FAIL_NO_MODEL_CLAIM"
DEVELOPMENT_FAIL_ROUTE = "ONE_MS_ID2E1_GROUPED_DEVELOPMENT_MODEL_FAIL_ROUTE_REVIEW"
EVALUATOR_FAIL_ROUTE = "ONE_MS_ID2E1_IMMUTABLE_EVALUATOR_MODEL_FAIL_ROUTE_REVIEW"
PASS_ROUTE = "ONE_MS_ID2E1_STRUCTURED_SOURCE_LOCAL_MODEL_PASS_FRESH_CALIBRATION_DESIGN_REQUIRED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} leaves repository root") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_config(repo_root: Path, path: Path) -> dict[str, Any]:
    path = inside(repo_root, path, "ID2E1 config")
    if sha256_file(path) != CONFIG_SHA256:
        raise ValueError("ID2E1 config hash mismatch")
    config = read_json(path)
    if config.get("schema_version") != "rgeo-zgeo-1ms-id2e1-structured-active-nominal-model-v1":
        raise ValueError("ID2E1 config schema mismatch")
    if any(config.get(key) != 0 for key in (
        "plant_advances", "tsc_calls", "calibration_records_read", "blind_holdout_records_read"
    )):
        raise ValueError("ID2E1 zero-execution/data counters changed")
    if config.get("routes") != {
        "input_or_source_fail": INPUT_ROUTE,
        "development_fail": DEVELOPMENT_FAIL_ROUTE,
        "evaluator_fail": EVALUATOR_FAIL_ROUTE,
        "pass": PASS_ROUTE,
    }:
        raise ValueError("ID2E1 routes changed")
    smooth = config["smooth_channel"]
    if smooth.get("candidate_order") != [
        "fixed_pole_odd", "fixed_pole_signed_even", "fixed_pole_signed_even_time", "fir16_signed_even"
    ]:
        raise ValueError("ID2E1 candidate order changed")
    poles = [float(value) for value in smooth["fixed_poles"]]
    if poles != [-0.5, 0.0, 0.5, 0.8, 0.95] or any(abs(value) >= 1.0 for value in poles):
        raise ValueError("ID2E1 fixed poles changed or are unstable")
    if float(smooth["ridge"]) != 1e-6 or smooth.get("intercept") is not False:
        raise ValueError("ID2E1 regression contract changed")
    if config.get("selection_after_evaluator_open") != "forbidden":
        raise ValueError("ID2E1 evaluator reselection must remain forbidden")
    if config.get("neural_residual") != "blocked_pending_id2e1_result":
        raise ValueError("ID2E1 neural residual gate changed")
    return config


def _verify_bound(repo_root: Path, relative: str, expected: str, label: str) -> Path:
    path = inside(repo_root, repo_root / relative, label)
    if not path.is_file() or sha256_file(path) != expected:
        raise ValueError(f"{label} hash mismatch")
    return path


def _states(row: dict[str, Any]) -> np.ndarray:
    values = np.asarray([
        [1000.0 * float(state["r_geo_m"]), 1000.0 * float(state["z_geo_m"]), float(state["ip_a"])]
        for state in row["states"]
    ], dtype=float)
    if values.shape != (33, 3) or not np.all(np.isfinite(values)):
        raise ValueError(f"invalid state array: {row.get('rollout_id')}")
    return values


def _semantic_state(state: dict[str, Any]) -> dict[str, Any]:
    artifacts = state.get("artifact_sha256", {})
    return {
        "time_ms": state.get("time_ms"),
        "r_geo_m": state.get("r_geo_m"),
        "z_geo_m": state.get("z_geo_m"),
        "r_mid_m": state.get("r_mid_m"),
        "ip_a": state.get("ip_a"),
        "actual_current_decimal_a_tsc": state.get("actual_current_decimal_a_tsc"),
        "wire_current_a": state.get("wire_current_a"),
        "artifacts": {name: artifacts.get(name) for name in (
            "inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv"
        )},
    }


def assert_exact_replay(left: dict[str, Any], right: dict[str, Any], label: str) -> None:
    if len(left.get("states", [])) != 33 or len(right.get("states", [])) != 33:
        raise ValueError(f"{label} state count mismatch")
    if len(left.get("actions", [])) != 32 or len(right.get("actions", [])) != 32:
        raise ValueError(f"{label} action count mismatch")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        if _semantic_state(a) != _semantic_state(b):
            raise ValueError(f"{label} state replay mismatch at {index}")
    for index, (a, b) in enumerate(zip(left["actions"], right["actions"])):
        if a != b:
            raise ValueError(f"{label} action replay mismatch at {index}")


def _validate_row(row: dict[str, Any], schema: str, revision: str, label: str) -> None:
    if row.get("schema_version") != schema or row.get("source_revision") != revision or row.get("passed") is not True:
        raise ValueError(f"{label} identity/pass mismatch")
    if len(row.get("states", [])) != 33 or len(row.get("actions", [])) != 32:
        raise ValueError(f"{label} trajectory length mismatch")
    for state_index, state in enumerate(row["states"]):
        if int(state.get("time_ms", -1)) != 1100 + state_index:
            raise ValueError(f"{label} state clock mismatch")
        if len(state.get("actual_current_decimal_a_tsc", [])) != 14 or len(state.get("wire_current_a", [])) != 48:
            raise ValueError(f"{label} current shape mismatch")
    for issue, action in enumerate(row["actions"]):
        if int(action.get("issue_step", -1)) != issue or int(action.get("effect_state_index", -1)) != issue + 1:
            raise ValueError(f"{label} action/effect clock mismatch")
        if len(action.get("target_current_a_tsc", [])) != 14:
            raise ValueError(f"{label} target-current shape mismatch")
    _states(row)


def _source_integrity(repo_root: Path, source: dict[str, Any], run_dir: Path, kind: str) -> dict[str, Any]:
    run_dir = inside(repo_root, run_dir, f"{kind} run directory")
    if run_dir.name != source["run_directory"]:
        raise ValueError(f"{kind} run-directory identity mismatch")
    _verify_bound(repo_root, source["tracked_compact_path"], source["tracked_compact_sha256"], f"{kind} tracked compact")
    primary = run_dir / "result.json"
    independent = run_dir / "independent_audit.json"
    if sha256_file(primary) != source["primary_result_sha256"]:
        raise ValueError(f"{kind} primary result hash mismatch")
    if sha256_file(independent) != source["independent_audit_sha256"]:
        raise ValueError(f"{kind} independent audit hash mismatch")
    p = read_json(primary)
    a = read_json(independent)
    if p.get("route") != source["required_route"] or p.get("passed") is not True:
        raise ValueError(f"{kind} primary route mismatch")
    if a.get("audit_passed") is not True:
        raise ValueError(f"{kind} independent audit did not pass")
    return {
        "run_directory": run_dir.name,
        "primary_sha256": sha256_file(primary),
        "independent_sha256": sha256_file(independent),
        "tracked_compact_sha256": source["tracked_compact_sha256"],
    }


def load_development(repo_root: Path, config: dict[str, Any], run_dir: Path) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source = config["development_source"]
    identity = _source_integrity(repo_root, source, run_dir, "ID2D1R1")
    run_dir = inside(repo_root, run_dir, "ID2D1R1 run directory")
    revision = source["source_revision"]
    schema = "rgeo-zgeo-1ms-id2d1r1-active-nominal-duration-time-development-result-v1"
    baselines = [read_json(run_dir / f"{name}.json") for name in source["held_nominal_replays"]]
    for index, row in enumerate(baselines):
        _validate_row(row, schema, revision, f"development baseline {index}")
    assert_exact_replay(baselines[0], baselines[1], "development baseline")
    smooth_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name in {"result.json", "independent_audit.json", "offline_preflight.json"}:
            continue
        if path.stem in source["held_nominal_replays"]:
            continue
        row = read_json(path)
        _validate_row(row, schema, revision, f"development {path.stem}")
        if row.get("cell_kind") == "smooth_residual":
            smooth_rows.append(row)
        elif row.get("cell_kind") == "event_residual":
            event_rows.append(row)
        else:
            raise ValueError(f"unknown development cell kind: {path.stem}")
    if len(smooth_rows) != source["smooth_action_cells"] or len(event_rows) != source["event_action_cells"]:
        raise ValueError("development action-cell count mismatch")
    identity.update({"smooth_cells": len(smooth_rows), "event_cells": len(event_rows)})
    return _states(baselines[0]), smooth_rows, event_rows, identity


def load_evaluator(repo_root: Path, config: dict[str, Any], run_dir: Path) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    source = config["evaluator_source"]
    identity = _source_integrity(repo_root, source, run_dir, "ID2C2")
    run_dir = inside(repo_root, run_dir, "ID2C2 run directory")
    revision = source["source_revision"]
    schema = "rgeo-zgeo-1ms-id2c2-fresh-nominal-vector-validation-result-v1"
    baseline_rows = [read_json(run_dir / f"selected_nominal_probe_baseline_r{index}.json") for index in range(2)]
    for index, row in enumerate(baseline_rows):
        _validate_row(row, schema, revision, f"evaluator baseline {index}")
    assert_exact_replay(baseline_rows[0], baseline_rows[1], "evaluator baseline")
    rows: list[dict[str, Any]] = []
    for pair_id in source["evaluator_pairs"]:
        pair = [read_json(run_dir / f"{pair_id}_r{index}.json") for index in range(2)]
        for index, row in enumerate(pair):
            _validate_row(row, schema, revision, f"evaluator {pair_id} replay {index}")
            if row.get("pair_id") != pair_id:
                raise ValueError(f"evaluator pair identity mismatch: {pair_id}")
        assert_exact_replay(pair[0], pair[1], f"evaluator {pair_id}")
        rows.append(pair[0])
    if len(rows) != 6:
        raise ValueError("evaluator unique arm count mismatch")
    identity.update({"unique_evaluator_arms": len(rows), "replays_verified": 2 * len(rows) + 2})
    return _states(baseline_rows[0]), rows, identity


def response(row: dict[str, Any], nominal: np.ndarray) -> np.ndarray:
    return _states(row) - nominal


def virtual_actions(row: dict[str, Any], source_kind: str) -> np.ndarray:
    values = np.asarray([action["probe_virtual_action"] for action in row["actions"]], dtype=float)
    if source_kind == "development":
        if values.shape != (32, 3):
            raise ValueError("development virtual-action shape mismatch")
        return values
    if source_kind == "evaluator":
        if values.shape != (32, 4):
            raise ValueError("evaluator virtual-action shape mismatch")
        return values[:, 1:]
    raise ValueError("unknown source kind")


def fixed_pole_features(actions: np.ndarray, poles: Sequence[float], include_even: bool, include_time: bool) -> np.ndarray:
    if actions.ndim != 2 or actions.shape[0] != 32:
        raise ValueError("fixed-pole action shape mismatch")
    signed_state = np.zeros((len(poles), actions.shape[1]), dtype=float)
    even_state = np.zeros_like(signed_state)
    rows = [np.zeros(len(poles) * actions.shape[1] * (2 if include_even else 1) * (2 if include_time else 1))]
    pole_array = np.asarray(poles, dtype=float)[:, None]
    for issue, value in enumerate(actions):
        signed_state = pole_array * signed_state + value[None, :]
        blocks = [signed_state.reshape(-1)]
        if include_even:
            even_state = pole_array * even_state + np.abs(value)[None, :]
            blocks.append(even_state.reshape(-1))
        base = np.concatenate(blocks)
        if include_time:
            tau = ((issue + 1) - 16.0) / 16.0
            base = np.concatenate([base, tau * base])
        rows.append(base)
    return np.stack(rows)


def fir_features(actions: np.ndarray, lag_steps: int, include_even: bool = True) -> np.ndarray:
    if actions.ndim != 2 or actions.shape[0] != 32:
        raise ValueError("FIR action shape mismatch")
    width = lag_steps * actions.shape[1] * (2 if include_even else 1)
    rows = []
    for state_index in range(33):
        signed: list[np.ndarray] = []
        even: list[np.ndarray] = []
        for lag in range(1, lag_steps + 1):
            issue = state_index - lag
            value = actions[issue] if 0 <= issue < 32 else np.zeros(actions.shape[1])
            signed.append(value)
            even.append(np.abs(value))
        feature = np.concatenate(signed + even if include_even else signed)
        if feature.size != width:
            raise AssertionError("FIR feature width mismatch")
        rows.append(feature)
    return np.stack(rows)


def feature_curve(row: dict[str, Any], source_kind: str, model_id: str, config: dict[str, Any], channel: str) -> np.ndarray:
    action = virtual_actions(row, source_kind)
    poles = config["smooth_channel"]["fixed_poles"]
    if channel == "smooth":
        action = action[:, :2]
        if model_id == "fixed_pole_odd":
            return fixed_pole_features(action, poles, False, False)
        if model_id == "fixed_pole_signed_even":
            return fixed_pole_features(action, poles, True, False)
        if model_id == "fixed_pole_signed_even_time":
            return fixed_pole_features(action, poles, True, True)
        if model_id == "fir16_signed_even":
            return fir_features(action, int(config["smooth_channel"]["fir_lag_steps"]), True)
        raise ValueError(f"unknown smooth model: {model_id}")
    if channel == "event":
        return fixed_pole_features(action[:, 2:3], config["event_channel"]["fixed_poles"], True, False)
    raise ValueError("unknown model channel")


def fit_no_intercept(features: np.ndarray, targets: np.ndarray, ridge: float) -> dict[str, Any]:
    if features.ndim != 2 or targets.ndim != 2 or features.shape[0] != targets.shape[0]:
        raise ValueError("fit shape mismatch")
    rms = np.sqrt(np.mean(features * features, axis=0))
    rms = np.where(rms > 1e-12, rms, 1.0)
    x = features / rms
    gram = x.T @ x + float(ridge) * np.eye(x.shape[1])
    coefficients = np.linalg.solve(gram, x.T @ targets)
    singular = np.linalg.svd(x, compute_uv=False)
    nonzero = singular[singular > max(x.shape) * np.finfo(float).eps * singular[0]] if singular.size else singular
    return {
        "feature_rms": rms.tolist(),
        "coefficients": coefficients.tolist(),
        "ridge": float(ridge),
        "training_rows": int(features.shape[0]),
        "feature_count": int(features.shape[1]),
        "feature_rank": int(np.linalg.matrix_rank(x)),
        "feature_condition_nonzero": float(singular[0] / nonzero[-1]) if nonzero.size else math.inf,
        "zero_input_zero_output": True,
    }


def predict(model: dict[str, Any], features: np.ndarray) -> np.ndarray:
    rms = np.asarray(model["feature_rms"], dtype=float)
    coefficients = np.asarray(model["coefficients"], dtype=float)
    return (features / rms) @ coefficients


def _post_effect_indices(row: dict[str, Any]) -> np.ndarray:
    issue = int(row.get("probe_issue_step", row.get("pulse_issue_step", -1)))
    if issue not in (16, 22):
        raise ValueError(f"unsupported probe issue: {row.get('rollout_id')}")
    return np.arange(issue + 1, 33, dtype=int)


def fit_channel(rows: Sequence[dict[str, Any]], nominal: np.ndarray, source_kind: str, model_id: str, config: dict[str, Any], channel: str) -> dict[str, Any]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for row in rows:
        indices = _post_effect_indices(row)
        features = feature_curve(row, source_kind, model_id, config, channel)
        truth = response(row, nominal)
        xs.append(features[indices])
        ys.append(truth[indices])
    ridge = float(config["smooth_channel" if channel == "smooth" else "event_channel"]["ridge"])
    return fit_no_intercept(np.concatenate(xs), np.concatenate(ys), ridge)


def arm_metrics(row: dict[str, Any], nominal_truth: np.ndarray, prediction: np.ndarray, config: dict[str, Any]) -> dict[str, Any]:
    truth = response(row, nominal_truth)
    indices = _post_effect_indices(row)
    actual = truth[indices]
    predicted = prediction[indices]
    errors = predicted - actual
    floor = float(config["response_metrics"]["r_z_rms_floor_mm"])
    actual_energy = float(np.sum(actual[:, :2] ** 2))
    denominator = max(actual_energy, len(indices) * floor * floor)
    nrmse = float(math.sqrt(float(np.sum(errors[:, :2] ** 2)) / denominator))
    blind_nrmse = float(math.sqrt(actual_energy / denominator))
    norms = np.linalg.norm(actual[:, :2], axis=1)
    peak_local = int(np.argmax(norms))
    actual_peak = actual[peak_local, :2]
    predicted_peak = predicted[peak_local, :2]
    cosine_denominator = float(np.linalg.norm(actual_peak) * np.linalg.norm(predicted_peak))
    cosine = float(np.dot(actual_peak, predicted_peak) / cosine_denominator) if cosine_denominator > 0.0 else -1.0
    return {
        "rollout_id": row["rollout_id"],
        "direction_id": row.get("direction_id"),
        "sign": row.get("sign"),
        "probe_issue_step": int(row.get("probe_issue_step", row.get("pulse_issue_step"))),
        "probe_duration_issues": int(row.get("probe_duration_issues", 1)),
        "scored_states": indices.tolist(),
        "response_nrmse": nrmse,
        "zero_response_nrmse": blind_nrmse,
        "peak_state_index": int(indices[peak_local]),
        "peak_response_r_z_mm": float(norms[peak_local]),
        "predicted_at_true_peak_r_z_mm": float(np.linalg.norm(predicted_peak)),
        "peak_direction_cosine": cosine,
        "r_z_error_norms_mm": np.linalg.norm(errors[:, :2], axis=1).tolist(),
        "ip_absolute_errors_a": np.abs(errors[:, 2]).tolist(),
        "response_energy_r_z_mm2": actual_energy,
        "error_energy_r_z_mm2": float(np.sum(errors[:, :2] ** 2)),
        "normalization_energy_r_z_mm2": denominator,
    }


def aggregate_metrics(arms: Sequence[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    if not arms:
        raise ValueError("cannot aggregate zero arms")
    error_energy = sum(float(row["error_energy_r_z_mm2"]) for row in arms)
    truth_energy = sum(float(row["response_energy_r_z_mm2"]) for row in arms)
    norm_energy = sum(float(row["normalization_energy_r_z_mm2"]) for row in arms)
    nrmse = math.sqrt(error_energy / norm_energy)
    blind = math.sqrt(truth_energy / norm_energy)
    r_z_errors = [value for row in arms for value in row["r_z_error_norms_mm"]]
    ip_errors = [value for row in arms for value in row["ip_absolute_errors_a"]]
    threshold = float(config["response_metrics"]["peak_vector_direction_cosine_threshold"])
    return {
        "arms": len(arms),
        "response_nrmse": float(nrmse),
        "zero_response_nrmse": float(blind),
        "response_improvement_vs_zero": float(1.0 - nrmse / blind) if blind > 0.0 else -math.inf,
        "arm_response_nrmse_p90": float(np.percentile([row["response_nrmse"] for row in arms], 90)),
        "arm_response_nrmse_max": float(max(row["response_nrmse"] for row in arms)),
        "peak_direction_pass_arms": int(sum(row["peak_direction_cosine"] >= threshold for row in arms)),
        "peak_direction_pass_fraction": float(sum(row["peak_direction_cosine"] >= threshold for row in arms) / len(arms)),
        "r_z_response_error_p95_mm": float(np.percentile(r_z_errors, 95)),
        "r_z_response_error_max_mm": float(max(r_z_errors)),
        "ip_response_error_p95_a": float(np.percentile(ip_errors, 95)),
        "ip_response_error_max_a": float(max(ip_errors)),
        "arm_metrics": list(arms),
    }


def schedule_key(row: dict[str, Any]) -> str:
    return f"i{int(row['probe_issue_step'])}_d{int(row['probe_duration_issues'])}"


def predict_response(row: dict[str, Any], source_kind: str, smooth_id: str, smooth_model: dict[str, Any], event_model: dict[str, Any], config: dict[str, Any]) -> np.ndarray:
    if row.get("direction_id") == "p09_half_exact_center":
        features = feature_curve(row, source_kind, "fixed_pole_signed_even", config, "event")
        return predict(event_model, features)
    features = feature_curve(row, source_kind, smooth_id, config, "smooth")
    return predict(smooth_model, features)


def development_selection(nominal: np.ndarray, smooth_rows: Sequence[dict[str, Any]], event_rows: Sequence[dict[str, Any]], config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    fold_keys = [f"i{row['probe_issue_step']}_d{row['probe_duration_issues']}" for row in config["smooth_channel"]["fold_schedule_cells"]]
    if sorted({schedule_key(row) for row in smooth_rows}) != sorted(fold_keys):
        raise ValueError("development fold cell set mismatch")
    candidate_results: dict[str, Any] = {}
    gates = config["development_gates"]
    selected_id: str | None = None
    selected_model: dict[str, Any] | None = None
    for model_id in config["smooth_channel"]["candidate_order"]:
        folds: list[dict[str, Any]] = []
        reasons: list[str] = []
        for held in fold_keys:
            training = [row for row in smooth_rows if schedule_key(row) != held]
            testing = [row for row in smooth_rows if schedule_key(row) == held]
            model = fit_channel(training, nominal, "development", model_id, config, "smooth")
            arms = [arm_metrics(row, nominal, predict(model, feature_curve(row, "development", model_id, config, "smooth")), config) for row in testing]
            metrics = aggregate_metrics(arms, config)
            metrics.update({"held_schedule_cell": held, "training_cells": len(training), "model_support": {
                "feature_count": model["feature_count"], "feature_rank": model["feature_rank"],
                "feature_condition_nonzero": model["feature_condition_nonzero"],
            }})
            fold_reasons = []
            if metrics["response_improvement_vs_zero"] < gates["minimum_response_rmse_improvement_vs_zero_each_fold"]:
                fold_reasons.append("RESPONSE_IMPROVEMENT")
            if metrics["response_nrmse"] > gates["maximum_response_nrmse_each_fold"]:
                fold_reasons.append("RESPONSE_NRMSE")
            if metrics["arm_response_nrmse_p90"] > gates["maximum_arm_response_nrmse_p90_each_fold"]:
                fold_reasons.append("ARM_P90")
            if metrics["peak_direction_pass_fraction"] < gates["minimum_peak_direction_pass_fraction_each_fold"]:
                fold_reasons.append("PEAK_DIRECTION")
            if metrics["r_z_response_error_p95_mm"] > gates["maximum_r_z_response_error_p95_mm_each_fold"]:
                fold_reasons.append("RZ_P95")
            if metrics["ip_response_error_p95_a"] > gates["maximum_ip_response_error_p95_a_each_fold"]:
                fold_reasons.append("IP_P95")
            metrics["passed"] = not fold_reasons
            metrics["failure_reasons"] = fold_reasons
            reasons.extend(f"{held}:{reason}" for reason in fold_reasons)
            folds.append(metrics)
        eligible = not reasons
        candidate_results[model_id] = {"eligible": eligible, "failure_reasons": reasons, "folds": folds}
        if selected_id is None and eligible:
            selected_id = model_id
            selected_model = fit_channel(smooth_rows, nominal, "development", model_id, config, "smooth")
    event_model = fit_channel(event_rows, nominal, "development", "fixed_pole_signed_even", config, "event")
    event_arms = [arm_metrics(row, nominal, predict(event_model, feature_curve(row, "development", "fixed_pole_signed_even", config, "event")), config) for row in event_rows]
    audit = {
        "candidate_order": config["smooth_channel"]["candidate_order"],
        "candidate_results": candidate_results,
        "selected_model_id": selected_id,
        "event_development_metrics": aggregate_metrics(event_arms, config),
        "evaluator_open_authorized": selected_id is not None,
    }
    if selected_model is None:
        return audit, None
    artifact = {
        "schema_version": ARTIFACT_SCHEMA,
        "config_sha256": CONFIG_SHA256,
        "selected_smooth_model_id": selected_id,
        "smooth_model": selected_model,
        "event_model_id": "fixed_pole_signed_even",
        "event_model": event_model,
        "fixed_poles": config["smooth_channel"]["fixed_poles"],
        "nominal_state_r_mm_z_mm_ip_a": nominal.tolist(),
        "output_units": ["mm", "mm", "A"],
        "evaluator_metrics_in_artifact": False,
    }
    return audit, artifact


def evaluator_metrics(nominal_model: np.ndarray, evaluator_nominal: np.ndarray, rows: Sequence[dict[str, Any]], artifact: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    smooth_id = artifact["selected_smooth_model_id"]
    smooth_model = artifact["smooth_model"]
    event_model = artifact["event_model"]
    arms: list[dict[str, Any]] = []
    absolute_r_z_errors: list[float] = []
    absolute_ip_errors: list[float] = []
    for row in rows:
        predicted_response = predict_response(row, "evaluator", smooth_id, smooth_model, event_model, config)
        arm = arm_metrics(row, evaluator_nominal, predicted_response, config)
        arms.append(arm)
        indices = _post_effect_indices(row)
        absolute_prediction = nominal_model + predicted_response
        absolute_error = absolute_prediction[indices] - _states(row)[indices]
        absolute_r_z_errors.extend(np.linalg.norm(absolute_error[:, :2], axis=1).tolist())
        absolute_ip_errors.extend(np.abs(absolute_error[:, 2]).tolist())
    aggregate = aggregate_metrics(arms, config)
    aggregate["absolute_r_z_error_p95_mm"] = float(np.percentile(absolute_r_z_errors, 95))
    aggregate["absolute_ip_error_p95_a"] = float(np.percentile(absolute_ip_errors, 95))
    p09 = aggregate_metrics([row for row in arms if row["direction_id"] == "p09_half_exact_center"], config)
    aggregate["p09_event_metrics"] = p09
    gates = config["evaluator_gates"]
    reasons: list[str] = []
    if aggregate["response_improvement_vs_zero"] < gates["minimum_aggregate_response_rmse_improvement_vs_zero"]:
        reasons.append("AGGREGATE_RESPONSE_IMPROVEMENT")
    if aggregate["response_nrmse"] > gates["maximum_aggregate_response_nrmse"]:
        reasons.append("AGGREGATE_RESPONSE_NRMSE")
    if aggregate["arm_response_nrmse_max"] > gates["maximum_each_arm_response_nrmse"]:
        reasons.append("ARM_RESPONSE_NRMSE")
    if aggregate["peak_direction_pass_arms"] < gates["minimum_peak_direction_pass_arms"]:
        reasons.append("PEAK_DIRECTION")
    if aggregate["r_z_response_error_p95_mm"] > gates["maximum_r_z_response_error_p95_mm"]:
        reasons.append("RZ_RESPONSE_P95")
    if aggregate["ip_response_error_p95_a"] > gates["maximum_ip_response_error_p95_a"]:
        reasons.append("IP_RESPONSE_P95")
    if p09["response_nrmse"] > gates["maximum_p09_response_nrmse"]:
        reasons.append("P09_RESPONSE_NRMSE")
    if p09["peak_direction_pass_arms"] < gates["required_p09_peak_direction_pass_arms"]:
        reasons.append("P09_PEAK_DIRECTION")
    if aggregate["absolute_r_z_error_p95_mm"] > gates["maximum_absolute_r_z_error_p95_mm"]:
        reasons.append("ABSOLUTE_RZ_P95")
    if aggregate["absolute_ip_error_p95_a"] > gates["maximum_absolute_ip_error_p95_a"]:
        reasons.append("ABSOLUTE_IP_P95")
    aggregate["passed"] = not reasons
    aggregate["failure_reasons"] = reasons
    return aggregate


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing overwrite: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def execute(repo_root: Path, config_path: Path, development_run: Path, evaluator_run: Path, output_dir: Path, source_revision: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("source revision must be a full lowercase Git hash")
    output_dir = inside(repo_root, output_dir, "ID2E1 output directory")
    if output_dir.exists():
        raise FileExistsError(f"refusing overwrite: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        config = load_config(repo_root, config_path)
        nominal, smooth_rows, event_rows, development_identity = load_development(repo_root, config, development_run)
        development, artifact = development_selection(nominal, smooth_rows, event_rows, config)
        if artifact is None:
            result = {
                "schema_version": SCHEMA, "source_revision": source_revision,
                "config_sha256": CONFIG_SHA256, "passed": False, "route": DEVELOPMENT_FAIL_ROUTE,
                "failure_reasons": ["NO_CANDIDATE_PASSED_ALL_GROUPED_DEVELOPMENT_FOLDS"],
                "development_source_identity": development_identity,
                "development": development, "evaluator_opened": False,
                "counters": {"models_fit": 20 + 1, "plant_advances": 0, "tsc_calls": 0,
                             "calibration_records_read": 0, "blind_holdout_records_read": 0,
                             "evaluator_unique_arms_read": 0},
            }
        else:
            artifact.update({"source_revision": source_revision, "development_source_identity": development_identity})
            artifact_path = output_dir / "model_artifact.json"
            write_json_new(artifact_path, artifact)
            artifact_sha = sha256_file(artifact_path)
            evaluator_nominal, evaluator_rows, evaluator_identity = load_evaluator(repo_root, config, evaluator_run)
            evaluation = evaluator_metrics(nominal, evaluator_nominal, evaluator_rows, artifact, config)
            passed = bool(evaluation["passed"])
            result = {
                "schema_version": SCHEMA, "source_revision": source_revision,
                "config_sha256": CONFIG_SHA256, "passed": passed,
                "route": PASS_ROUTE if passed else EVALUATOR_FAIL_ROUTE,
                "failure_reasons": evaluation["failure_reasons"],
                "development_source_identity": development_identity,
                "evaluator_source_identity": evaluator_identity,
                "development": development, "model_artifact_sha256_before_evaluator_open": artifact_sha,
                "evaluator_opened": True, "evaluator": evaluation,
                "counters": {"models_fit": 20 + 2, "plant_advances": 0, "tsc_calls": 0,
                             "calibration_records_read": 0, "blind_holdout_records_read": 0,
                             "evaluator_unique_arms_read": len(evaluator_rows)},
            }
        result["claim_boundary"] = {
            "source_local_structured_model_passed": bool(result["passed"]),
            "calibrated_uncertainty": False, "blind_context_history_holdout_opened": False,
            "controller_or_recourse_qualified": False, "transport_or_crossing_qualified": False,
            "neural_residual_fit": False,
        }
    except Exception as exc:
        result = {
            "schema_version": SCHEMA, "source_revision": source_revision,
            "config_sha256": CONFIG_SHA256, "passed": False, "route": INPUT_ROUTE,
            "failure_reasons": [f"{type(exc).__name__}:{exc}"],
            "evaluator_opened": False,
            "counters": {"models_fit": 0, "plant_advances": 0, "tsc_calls": 0,
                         "calibration_records_read": 0, "blind_holdout_records_read": 0,
                         "evaluator_unique_arms_read": 0},
        }
    write_json_new(output_dir / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("configs/rgeo_zgeo_1ms_id2e1_structured_active_nominal_model.json"))
    parser.add_argument("--development-run-dir", type=Path, required=True)
    parser.add_argument("--evaluator-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    resolve = lambda value: value if value.is_absolute() else root / value
    result = execute(root, resolve(args.config), resolve(args.development_run_dir), resolve(args.evaluator_run_dir), resolve(args.output_dir), args.source_revision)
    print(json.dumps({
        "schema_version": result["schema_version"], "route": result["route"],
        "passed": result["passed"], "failure_reasons": result["failure_reasons"],
        "selected_model_id": result.get("development", {}).get("selected_model_id"),
        "evaluator_opened": result.get("evaluator_opened", False), "counters": result["counters"],
    }, indent=2, sort_keys=True, allow_nan=False))
    return 2 if result["route"] == INPUT_ROUTE else 0


if __name__ == "__main__":
    raise SystemExit(main())
