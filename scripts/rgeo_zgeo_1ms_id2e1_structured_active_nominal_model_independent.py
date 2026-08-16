#!/usr/bin/env python3
"""Independent coefficient/prediction recomputation for ID-2E1."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id2e1_structured_active_nominal_model import (  # noqa: E402
    CONFIG_SHA256,
    DEVELOPMENT_FAIL_ROUTE,
    EVALUATOR_FAIL_ROUTE,
    INPUT_ROUTE,
    PASS_ROUTE,
    inside,
    load_config,
    load_development,
    load_evaluator,
    read_json,
    response,
    sha256_file,
    virtual_actions,
)


SCHEMA = "rgeo-zgeo-1ms-id2e1-structured-active-nominal-model-independent-v1"


def _features(row: dict[str, Any], source: str, model_id: str, config: dict[str, Any], event: bool = False) -> np.ndarray:
    actions = virtual_actions(row, source)
    if event:
        actions = actions[:, 2:3]
        include_even, include_time = True, False
        poles = np.asarray(config["event_channel"]["fixed_poles"], dtype=float)
    elif model_id == "fir16_signed_even":
        actions = actions[:, :2]
        lag_count = int(config["smooth_channel"]["fir_lag_steps"])
        rows = []
        for state in range(33):
            signed, even = [], []
            for lag in range(1, lag_count + 1):
                issue = state - lag
                value = actions[issue] if 0 <= issue < 32 else np.zeros(2)
                signed.extend(value.tolist())
                even.extend(np.abs(value).tolist())
            rows.append(signed + even)
        return np.asarray(rows, dtype=float)
    else:
        actions = actions[:, :2]
        include_even = model_id != "fixed_pole_odd"
        include_time = model_id == "fixed_pole_signed_even_time"
        poles = np.asarray(config["smooth_channel"]["fixed_poles"], dtype=float)
    signed_state = np.zeros((len(poles), actions.shape[1]))
    even_state = np.zeros_like(signed_state)
    width = signed_state.size * (2 if include_even else 1) * (2 if include_time else 1)
    rows = [np.zeros(width)]
    for issue in range(32):
        signed_state = poles[:, None] * signed_state + actions[issue][None, :]
        parts = [signed_state.ravel()]
        if include_even:
            even_state = poles[:, None] * even_state + np.abs(actions[issue])[None, :]
            parts.append(even_state.ravel())
        base = np.concatenate(parts)
        if include_time:
            base = np.concatenate([base, ((issue + 1 - 16.0) / 16.0) * base])
        rows.append(base)
    return np.asarray(rows)


def _indices(row: dict[str, Any]) -> np.ndarray:
    issue = int(row.get("probe_issue_step", row.get("pulse_issue_step", -1)))
    if issue not in (16, 22):
        raise ValueError("independent unsupported issue")
    return np.arange(issue + 1, 33)


def _refit(rows: Sequence[dict[str, Any]], nominal: np.ndarray, source: str, model_id: str, config: dict[str, Any], event: bool = False) -> dict[str, Any]:
    x, y = [], []
    for row in rows:
        idx = _indices(row)
        x.append(_features(row, source, model_id, config, event)[idx])
        y.append(response(row, nominal)[idx])
    xmat, ymat = np.concatenate(x), np.concatenate(y)
    scale = np.sqrt(np.mean(xmat ** 2, axis=0))
    scale[scale <= 1e-12] = 1.0
    xn = xmat / scale
    ridge = float(config["event_channel" if event else "smooth_channel"]["ridge"])
    coef = np.linalg.solve(xn.T @ xn + ridge * np.eye(xn.shape[1]), xn.T @ ymat)
    singular = np.linalg.svd(xn, compute_uv=False)
    cutoff = max(xn.shape) * np.finfo(float).eps * singular[0]
    nonzero = singular[singular > cutoff]
    return {
        "feature_rms": scale.tolist(), "coefficients": coef.tolist(), "ridge": ridge,
        "training_rows": int(xmat.shape[0]), "feature_count": int(xmat.shape[1]),
        "feature_rank": int(np.linalg.matrix_rank(xn)),
        "feature_condition_nonzero": float(singular[0] / nonzero[-1]),
        "zero_input_zero_output": True,
    }


def _predict(model: dict[str, Any], features: np.ndarray) -> np.ndarray:
    return (features / np.asarray(model["feature_rms"])) @ np.asarray(model["coefficients"])


def _arm(row: dict[str, Any], nominal: np.ndarray, predicted: np.ndarray, config: dict[str, Any]) -> dict[str, Any]:
    idx = _indices(row)
    actual = response(row, nominal)[idx]
    estimate = predicted[idx]
    error = estimate - actual
    floor = float(config["response_metrics"]["r_z_rms_floor_mm"])
    actual_energy = float(np.sum(actual[:, :2] ** 2))
    normalization = max(actual_energy, len(idx) * floor ** 2)
    peak_local = int(np.argmax(np.linalg.norm(actual[:, :2], axis=1)))
    a = actual[peak_local, :2]
    p = estimate[peak_local, :2]
    denom = float(np.linalg.norm(a) * np.linalg.norm(p))
    return {
        "rollout_id": row["rollout_id"], "direction_id": row.get("direction_id"), "sign": row.get("sign"),
        "probe_issue_step": int(row.get("probe_issue_step", row.get("pulse_issue_step"))),
        "probe_duration_issues": int(row.get("probe_duration_issues", 1)), "scored_states": idx.tolist(),
        "response_nrmse": float(math.sqrt(np.sum(error[:, :2] ** 2) / normalization)),
        "zero_response_nrmse": float(math.sqrt(actual_energy / normalization)),
        "peak_state_index": int(idx[peak_local]),
        "peak_response_r_z_mm": float(np.linalg.norm(a)),
        "predicted_at_true_peak_r_z_mm": float(np.linalg.norm(p)),
        "peak_direction_cosine": float(np.dot(a, p) / denom) if denom > 0 else -1.0,
        "r_z_error_norms_mm": np.linalg.norm(error[:, :2], axis=1).tolist(),
        "ip_absolute_errors_a": np.abs(error[:, 2]).tolist(),
        "response_energy_r_z_mm2": actual_energy,
        "error_energy_r_z_mm2": float(np.sum(error[:, :2] ** 2)),
        "normalization_energy_r_z_mm2": normalization,
    }


def _aggregate(arms: Sequence[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    ee = sum(row["error_energy_r_z_mm2"] for row in arms)
    te = sum(row["response_energy_r_z_mm2"] for row in arms)
    ne = sum(row["normalization_energy_r_z_mm2"] for row in arms)
    nrmse, blind = math.sqrt(ee / ne), math.sqrt(te / ne)
    rz = [value for row in arms for value in row["r_z_error_norms_mm"]]
    ip = [value for row in arms for value in row["ip_absolute_errors_a"]]
    threshold = float(config["response_metrics"]["peak_vector_direction_cosine_threshold"])
    passed = sum(row["peak_direction_cosine"] >= threshold for row in arms)
    return {
        "arms": len(arms), "response_nrmse": float(nrmse), "zero_response_nrmse": float(blind),
        "response_improvement_vs_zero": float(1.0 - nrmse / blind),
        "arm_response_nrmse_p90": float(np.percentile([row["response_nrmse"] for row in arms], 90)),
        "arm_response_nrmse_max": float(max(row["response_nrmse"] for row in arms)),
        "peak_direction_pass_arms": int(passed), "peak_direction_pass_fraction": float(passed / len(arms)),
        "r_z_response_error_p95_mm": float(np.percentile(rz, 95)), "r_z_response_error_max_mm": float(max(rz)),
        "ip_response_error_p95_a": float(np.percentile(ip, 95)), "ip_response_error_max_a": float(max(ip)),
        "arm_metrics": list(arms),
    }


def _numeric_difference(left: Any, right: Any) -> float:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return math.inf
        return max((_numeric_difference(left[key], right[key]) for key in left), default=0.0)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return math.inf
        return max((_numeric_difference(a, b) for a, b in zip(left, right)), default=0.0)
    if isinstance(left, (str, bool)) or isinstance(right, (str, bool)) or left is None or right is None:
        return 0.0 if left == right else math.inf
    return abs(float(left) - float(right))


def audit(repo_root: Path, config_path: Path, development_run: Path, evaluator_run: Path, model_dir: Path, output_path: Path) -> dict[str, Any]:
    config = load_config(repo_root, config_path)
    result_path, artifact_path = model_dir / "result.json", model_dir / "model_artifact.json"
    result = read_json(result_path)
    failures: list[str] = []
    if result.get("route") not in (DEVELOPMENT_FAIL_ROUTE, EVALUATOR_FAIL_ROUTE, PASS_ROUTE):
        failures.append("PRIMARY_ROUTE_NOT_A_SCIENTIFIC_RESULT")
    if result.get("route") == DEVELOPMENT_FAIL_ROUTE:
        audit_value = {
            "schema_version": SCHEMA, "audit_passed": not failures, "failures": failures,
            "primary_route": result.get("route"), "primary_result_sha256": sha256_file(result_path),
            "selection_recomputed": False, "reason": "no artifact/evaluator by frozen development-fail route",
            "counters": {"plant_advances": 0, "tsc_calls": 0},
        }
    else:
        artifact = read_json(artifact_path)
        nominal, smooth_rows, event_rows, _ = load_development(repo_root, config, development_run)
        selected = artifact["selected_smooth_model_id"]
        smooth = _refit(smooth_rows, nominal, "development", selected, config, False)
        event = _refit(event_rows, nominal, "development", "fixed_pole_signed_even", config, True)
        coefficient_difference = max(_numeric_difference(smooth, artifact["smooth_model"]), _numeric_difference(event, artifact["event_model"]))
        if coefficient_difference > 1e-12:
            failures.append("MODEL_REFIT_DIFFERENCE")
        evaluator_nominal, rows, _ = load_evaluator(repo_root, config, evaluator_run)
        arms = []
        absolute_rz, absolute_ip = [], []
        for row in rows:
            is_event = row.get("direction_id") == "p09_half_exact_center"
            model = event if is_event else smooth
            features = _features(row, "evaluator", "fixed_pole_signed_even" if is_event else selected, config, is_event)
            prediction = _predict(model, features)
            arms.append(_arm(row, evaluator_nominal, prediction, config))
            idx = _indices(row)
            error = nominal[idx] + prediction[idx] - np.asarray([
                [1000 * state["r_geo_m"], 1000 * state["z_geo_m"], state["ip_a"]] for state in row["states"]
            ], dtype=float)[idx]
            absolute_rz.extend(np.linalg.norm(error[:, :2], axis=1).tolist())
            absolute_ip.extend(np.abs(error[:, 2]).tolist())
        metrics = _aggregate(arms, config)
        metrics["absolute_r_z_error_p95_mm"] = float(np.percentile(absolute_rz, 95))
        metrics["absolute_ip_error_p95_a"] = float(np.percentile(absolute_ip, 95))
        metrics["p09_event_metrics"] = _aggregate([row for row in arms if row["direction_id"] == "p09_half_exact_center"], config)
        # Verdict fields are primary routing outputs, so compare only the independently recomputed numeric metric body.
        primary_metrics = dict(result["evaluator"])
        primary_metrics.pop("passed", None)
        primary_metrics.pop("failure_reasons", None)
        metric_difference = _numeric_difference(metrics, primary_metrics)
        if metric_difference > 1e-12:
            failures.append("EVALUATOR_METRIC_DIFFERENCE")
        if sha256_file(artifact_path) != result.get("model_artifact_sha256_before_evaluator_open"):
            failures.append("ARTIFACT_HASH_MISMATCH")
        audit_value = {
            "schema_version": SCHEMA, "audit_passed": not failures, "failures": failures,
            "primary_route": result.get("route"), "primary_passed": result.get("passed"),
            "primary_result_sha256": sha256_file(result_path), "model_artifact_sha256": sha256_file(artifact_path),
            "selected_model_id": selected, "maximum_model_refit_difference": coefficient_difference,
            "maximum_evaluator_metric_difference": metric_difference,
            "independent_evaluator_metrics": metrics,
            "independence_boundary": "source authentication loaders shared; feature construction, refit and evaluator metric recomputation are separate",
            "counters": {"plant_advances": 0, "tsc_calls": 0, "calibration_records_read": 0, "blind_holdout_records_read": 0},
        }
    if output_path.exists():
        raise FileExistsError(f"refusing overwrite: {output_path}")
    output_path.write_text(json.dumps(audit_value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return audit_value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("configs/rgeo_zgeo_1ms_id2e1_structured_active_nominal_model.json"))
    parser.add_argument("--development-run-dir", type=Path, required=True)
    parser.add_argument("--evaluator-run-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    resolve = lambda value: value if value.is_absolute() else root / value
    try:
        result = audit(root, resolve(args.config), resolve(args.development_run_dir), resolve(args.evaluator_run_dir), resolve(args.model_dir), resolve(args.output))
    except Exception as exc:
        result = {"schema_version": SCHEMA, "audit_passed": False, "failures": [f"{type(exc).__name__}:{exc}"], "counters": {"plant_advances": 0, "tsc_calls": 0}}
        output = resolve(args.output)
        if not output.exists():
            output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result.get("audit_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
