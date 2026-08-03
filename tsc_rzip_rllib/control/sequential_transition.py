"""Deterministic causal recursive transition model used by Stage4.2R3c3T13S24."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Mapping, Sequence

import numpy as np


Array = np.ndarray
FormalEvaluator = Callable[[Mapping[str, Any], Array], bool]
PREDICTOR_ITEM_FIELDS = frozenset(
    {"states", "horizon", "target_offsets", "requested_action_by_step"}
)


def _predictor_payload(
    item: Mapping[str, Any], model_cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Copy the complete and exclusive item fields visible to the predictor."""

    forbidden = set(map(str, model_cfg["forbidden_predictor_fields"]))
    overlap = PREDICTOR_ITEM_FIELDS & forbidden
    if overlap:
        raise ValueError(f"S24 predictor whitelist overlaps frozen forbidden fields: {sorted(overlap)}")
    missing = PREDICTOR_ITEM_FIELDS - set(item)
    if missing:
        raise ValueError(f"S24 predictor payload is incomplete: {sorted(missing)}")
    return {key: item[key] for key in PREDICTOR_ITEM_FIELDS}


def amplitude_coded_hadamard(schedule: Mapping[str, Any]) -> Array:
    """Return the frozen 24 x 16 amplitude-coded Sylvester schedule."""

    h2 = np.asarray([[1, 1], [1, -1]], dtype=int)
    matrix = np.asarray([[1]], dtype=int)
    for _ in range(4):
        matrix = np.kron(matrix, h2)
    if matrix.shape != (int(schedule["hadamard_order"]),) * 2:
        raise ValueError("S24 Hadamard order changed")
    signs = np.vstack((matrix, -matrix[: int(schedule["central_sign_sentinel_rows"])]))
    amplitudes = {str(key): float(value) for key, value in schedule["canonical_pattern_amplitudes"].items()}
    output = np.zeros_like(signs, dtype=float)
    for row in range(signs.shape[0]):
        for slot in range(4):
            block = signs[row, 4 * slot : 4 * slot + 4]
            global_sign = int(block[0])
            canonical = block * global_sign
            key = "".join("+" if value > 0 else "-" for value in canonical)
            if key not in amplitudes:
                raise ValueError(f"S24 unregistered canonical pattern: {key}")
            output[row, 4 * slot : 4 * slot + 4] = block * amplitudes[key]
    expected_rows = int(schedule["total_sequence_rows"])
    if output.shape != (expected_rows, 16) or not np.all(np.isfinite(output)):
        raise ValueError("S24 requested matrix shape or finiteness changed")
    return output


def requested_action_by_step(
    row: Sequence[float] | Array, schedule: Mapping[str, Any]
) -> dict[int, Array]:
    """Expose only the requested coordinate at its causal issue/cancel step."""

    values = np.asarray(row, dtype=float)
    if values.shape != (16,) or not np.all(np.isfinite(values)):
        raise ValueError("S24 sequence row must contain 16 finite coordinates")
    issue = tuple(map(int, schedule["issue_task_steps"]))
    cancel = tuple(map(int, schedule["cancel_task_steps"]))
    if len(issue) != 4 or len(cancel) != 4:
        raise ValueError("S24 issue/cancel slot count changed")
    output: dict[int, Array] = {}
    for slot, (start, stop) in enumerate(zip(issue, cancel)):
        coordinate = values[4 * slot : 4 * slot + 4].copy()
        output[start] = coordinate
        output[stop] = -coordinate
    return output


def _legendre_clock(step: int, horizon: int, degree: int) -> Array:
    if horizon <= 0 or not 0 <= step <= horizon:
        raise ValueError("invalid S24 recursive task clock")
    x = 2.0 * float(step) / float(horizon) - 1.0
    values = [1.0, x]
    for order in range(2, degree + 1):
        values.append(
            ((2 * order - 1) * x * values[-1] - (order - 1) * values[-2]) / order
        )
    return np.asarray(values[1:], dtype=float)


def feature_vector(
    history: Sequence[Sequence[float]] | Array,
    requested: Mapping[int, Sequence[float] | Array],
    target_offsets: Sequence[float] | Array,
    *,
    step: int,
    horizon: int,
    candidate: str,
    model_cfg: Mapping[str, Any],
) -> Array:
    """Build one predictor vector from causal visible/action history only."""

    history_length = int(model_cfg["history_length"])
    states = np.asarray(history, dtype=float)
    if states.ndim != 2 or states.shape[1] != 5 or len(states) < history_length:
        raise ValueError("S24 visible history is incomplete")
    states = states[-history_length:]
    target = np.asarray(target_offsets, dtype=float)
    target_scales = np.asarray(model_cfg["target_offset_scales"], dtype=float)
    if target.shape != (3,) or target_scales.shape != (3,) or np.any(target_scales <= 0):
        raise ValueError("S24 numerical target feature changed")
    action_rows = []
    for offset in range(int(model_cfg["action_history_length"])):
        value = np.asarray(requested.get(step - offset, np.zeros(4)), dtype=float)
        if value.shape != (4,):
            raise ValueError("S24 requested action coordinate shape changed")
        action_rows.append(value)
    actions = np.concatenate(action_rows)
    base = np.concatenate(
        (
            states.reshape(-1),
            target / target_scales,
            _legendre_clock(step, horizon, int(model_cfg["task_clock_legendre_degree"])),
            actions,
        )
    )
    if candidate == "L":
        output = base
    elif candidate in {"SA", "Q"}:
        latest = states[-1]
        pieces = [base, latest**2, np.outer(latest, actions).reshape(-1)]
        if candidate == "Q":
            upper = np.triu_indices(len(actions))
            pieces.append(np.outer(actions, actions)[upper])
        output = np.concatenate(pieces)
    else:
        raise ValueError(f"unsupported S24 feature candidate: {candidate}")
    if not np.all(np.isfinite(output)):
        raise ValueError("S24 feature contains a non-finite value")
    return output


def fit_ridge(
    x: Array,
    y: Array,
    *,
    candidate: str,
    ridge: float,
    standard_deviation_floor: float,
) -> dict[str, Any]:
    """Fit a deterministic standardized multi-output ridge model."""

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y) or y.shape[1] != 5:
        raise ValueError("S24 ridge matrix shape changed")
    if len(x) <= x.shape[1] or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("S24 ridge fit is non-finite or underdetermined")
    if ridge < 0.0 or standard_deviation_floor <= 0.0:
        raise ValueError("S24 ridge regularization changed")
    x_mean = np.mean(x, axis=0)
    x_scale = np.std(x, axis=0)
    x_scale = np.maximum(x_scale, float(standard_deviation_floor))
    y_mean = np.mean(y, axis=0)
    standardized = (x - x_mean) / x_scale
    gram = standardized.T @ standardized
    cross = standardized.T @ (y - y_mean)
    regularized = gram + float(ridge) * np.eye(gram.shape[0])
    coefficients = np.linalg.lstsq(regularized, cross, rcond=None)[0]
    if coefficients.shape != (x.shape[1], 5) or not np.all(np.isfinite(coefficients)):
        raise ValueError("S24 ridge coefficient fit failed")
    return {
        "candidate": candidate,
        "ridge": float(ridge),
        "x_mean": x_mean.tolist(),
        "x_scale": x_scale.tolist(),
        "y_mean": y_mean.tolist(),
        "coefficients": coefficients.tolist(),
    }


def predict(model: Mapping[str, Any], x: Sequence[float] | Array) -> Array:
    value = np.asarray(x, dtype=float)
    mean = np.asarray(model["x_mean"], dtype=float)
    scale = np.asarray(model["x_scale"], dtype=float)
    y_mean = np.asarray(model["y_mean"], dtype=float)
    coefficients = np.asarray(model["coefficients"], dtype=float)
    if value.shape != mean.shape or scale.shape != mean.shape:
        raise ValueError("S24 prediction feature shape changed")
    output = y_mean + ((value - mean) / scale) @ coefficients
    if output.shape != (5,) or not np.all(np.isfinite(output)):
        raise ValueError("S24 recursive prediction is non-finite")
    return output


def _teacher_rows(
    items: Sequence[Mapping[str, Any]], candidate: str, model_cfg: Mapping[str, Any]
) -> tuple[Array, Array]:
    x_rows, y_rows = [], []
    start = int(model_cfg["recursive_start_state"])
    for item in items:
        payload = _predictor_payload(item, model_cfg)
        states = np.asarray(payload["states"], dtype=float)
        horizon = int(payload["horizon"])
        if states.shape != (horizon + 1, 5):
            raise ValueError("S24 teacher trajectory shape changed")
        for step in range(start, horizon):
            x_rows.append(
                feature_vector(
                    states[: step + 1],
                    payload["requested_action_by_step"],
                    payload["target_offsets"],
                    step=step,
                    horizon=horizon,
                    candidate=candidate,
                    model_cfg=model_cfg,
                )
            )
            y_rows.append(states[step + 1])
    return np.asarray(x_rows, dtype=float), np.asarray(y_rows, dtype=float)


def recursive_prediction(
    model: Mapping[str, Any], item: Mapping[str, Any], model_cfg: Mapping[str, Any]
) -> Array:
    """Roll from authentic state 10 without reopening any future measurement."""

    payload = _predictor_payload(item, model_cfg)
    actual = np.asarray(payload["states"], dtype=float)
    horizon = int(payload["horizon"])
    start = int(model_cfg["recursive_start_state"])
    if actual.shape != (horizon + 1, 5) or start != 10:
        raise ValueError("S24 recursive source trajectory changed")
    predicted = np.full_like(actual, np.nan, dtype=float)
    predicted[: start + 1] = actual[: start + 1]
    candidate = str(model["candidate"])
    for step in range(start, horizon):
        vector = feature_vector(
            predicted[: step + 1],
            payload["requested_action_by_step"],
            payload["target_offsets"],
            step=step,
            horizon=horizon,
            candidate=candidate,
            model_cfg=model_cfg,
        )
        predicted[step + 1] = predict(model, vector)
    if not np.all(np.isfinite(predicted)):
        raise ValueError("S24 recursive rollout is non-finite")
    return predicted


def _prediction_rows(
    model: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    model_cfg: Mapping[str, Any],
    formal_evaluator: FormalEvaluator,
) -> tuple[list[dict[str, Any]], Array, float, int]:
    start = int(model_cfg["recursive_start_state"])
    rows: list[dict[str, Any]] = []
    component_residual = np.zeros(5, dtype=float)
    squared_sum = 0.0
    scalar_count = 0
    mismatch = 0
    for item in items:
        actual = np.asarray(item["states"], dtype=float)
        predicted = recursive_prediction(model, item, model_cfg)
        error = np.abs(predicted[start + 1 :] - actual[start + 1 :])
        component = np.max(error, axis=0)
        component_residual = np.maximum(component_residual, component)
        squared_sum += float(np.sum(error**2))
        scalar_count += int(error.size)
        actual_formal = bool(formal_evaluator(item, actual))
        predicted_formal = bool(formal_evaluator(item, predicted))
        mismatch += int(actual_formal != predicted_formal)
        rows.append(
            {
                "experiment_id": str(item["experiment_id"]),
                "pair_id": str(item["pair_id"]),
                "history_member": str(item["history_member"]),
                "partition": str(item["partition"]),
                "maximum_absolute_scaled_error": float(np.max(error)),
                "componentwise_maximum_absolute_scaled_error": component.tolist(),
                "actual_formal_pass": actual_formal,
                "predicted_formal_pass": predicted_formal,
                "formal_verdict_reproduced": actual_formal == predicted_formal,
                "recursive_state_count": int(len(error)),
            }
        )
    mse = squared_sum / max(scalar_count, 1)
    return rows, component_residual, mse, mismatch


def select_training_model(
    items: Sequence[Mapping[str, Any]],
    model_cfg: Mapping[str, Any],
    formal_evaluator: FormalEvaluator,
) -> dict[str, Any]:
    """Select a model only by twelve leave-one-whole-pair-out recursive folds."""

    pairs = sorted({str(item["pair_id"]) for item in items})
    if len(pairs) != 12 or Counter(str(item["pair_id"]) for item in items) != Counter(
        {pair: 50 for pair in pairs}
    ):
        raise ValueError("S24 training whole-pair coverage changed")
    candidates = tuple(map(str, model_cfg["feature_candidates"]))
    ridge_grid = tuple(map(float, model_cfg["ridge_grid"]))
    scores: list[dict[str, Any]] = []
    predictions: dict[tuple[str, float], list[dict[str, Any]]] = {}
    residuals: dict[tuple[str, float], Array] = {}
    for candidate in candidates:
        for ridge in ridge_grid:
            all_rows: list[dict[str, Any]] = []
            component = np.zeros(5, dtype=float)
            squared_sum = 0.0
            scalar_count = 0
            mismatch = 0
            for pair in pairs:
                train = [item for item in items if str(item["pair_id"]) != pair]
                held = [item for item in items if str(item["pair_id"]) == pair]
                x, y = _teacher_rows(train, candidate, model_cfg)
                model = fit_ridge(
                    x,
                    y,
                    candidate=candidate,
                    ridge=ridge,
                    standard_deviation_floor=float(
                        model_cfg["feature_standard_deviation_floor"]
                    ),
                )
                rows, fold_residual, fold_mse, fold_mismatch = _prediction_rows(
                    model, held, model_cfg, formal_evaluator
                )
                all_rows.extend(rows)
                component = np.maximum(component, fold_residual)
                held_scalars = sum(int(row["recursive_state_count"]) * 5 for row in rows)
                squared_sum += fold_mse * held_scalars
                scalar_count += held_scalars
                mismatch += fold_mismatch
            key = (candidate, ridge)
            predictions[key] = all_rows
            residuals[key] = component
            scores.append(
                {
                    "feature_candidate": candidate,
                    "ridge": ridge,
                    "recursive_formal_verdict_mismatch_count": mismatch,
                    "maximum_absolute_recursive_scaled_error": float(
                        max(row["maximum_absolute_scaled_error"] for row in all_rows)
                    ),
                    "mean_squared_recursive_scaled_error": squared_sum
                    / max(scalar_count, 1),
                }
            )
    order = {name: index for index, name in enumerate(candidates)}
    selected = min(
        scores,
        key=lambda row: (
            int(row["recursive_formal_verdict_mismatch_count"]),
            float(row["maximum_absolute_recursive_scaled_error"]),
            float(row["mean_squared_recursive_scaled_error"]),
            order[str(row["feature_candidate"])],
            float(row["ridge"]),
        ),
    )
    selected_key = (str(selected["feature_candidate"]), float(selected["ridge"]))
    x, y = _teacher_rows(items, selected_key[0], model_cfg)
    model = fit_ridge(
        x,
        y,
        candidate=selected_key[0],
        ridge=selected_key[1],
        standard_deviation_floor=float(model_cfg["feature_standard_deviation_floor"]),
    )
    threshold = float(model_cfg["maximum_absolute_recursive_scaled_error"])
    scales = np.asarray(model_cfg["visible_state_scales"], dtype=float)
    floor = np.asarray(model_cfg["response_floor"], dtype=float) / scales
    caps = np.asarray(model_cfg["belief_halfwidth_caps"], dtype=float) / scales
    precursor_halfwidth = (
        floor
        + float(model_cfg["tube_multiplier"]) * residuals[selected_key]
    )
    passed = bool(
        int(selected["recursive_formal_verdict_mismatch_count"]) == 0
        and float(selected["maximum_absolute_recursive_scaled_error"]) <= threshold
        and np.all(precursor_halfwidth <= caps + 1e-15)
    )
    return {
        "candidate_scores": scores,
        "selected": selected,
        "model": model,
        "training_oof_rows": predictions[selected_key],
        "training_componentwise_maximum_scaled_residual": residuals[selected_key].tolist(),
        "training_tube_precursor_halfwidth_scaled": precursor_halfwidth.tolist(),
        "training_tube_precursor_halfwidth_physical": (
            precursor_halfwidth * scales
        ).tolist(),
        "training_tube_precursor_cap_pass": bool(
            np.all(precursor_halfwidth <= caps + 1e-15)
        ),
        "training_item_count": len(items),
        "training_pair_count": len(pairs),
        "teacher_row_count": len(x),
        "forbidden_predictor_input_count": 0,
        "calibration_outcome_access_count_before_model_hash": 0,
        "holdout_outcome_access_count_before_model_hash": 0,
        "passed": passed,
    }


def evaluate_recursive_set(
    model: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    model_cfg: Mapping[str, Any],
    formal_evaluator: FormalEvaluator,
    calibrated_scaled_residual: Sequence[float] | Array,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, component, mse, mismatch = _prediction_rows(
        model, items, model_cfg, formal_evaluator
    )
    residual = np.asarray(calibrated_scaled_residual, dtype=float)
    floor = np.asarray(model_cfg["response_floor"], dtype=float) / np.asarray(
        model_cfg["visible_state_scales"], dtype=float
    )
    caps = np.asarray(model_cfg["belief_halfwidth_caps"], dtype=float) / np.asarray(
        model_cfg["visible_state_scales"], dtype=float
    )
    halfwidth = floor + float(model_cfg["tube_multiplier"]) * residual
    threshold = float(model_cfg["maximum_absolute_recursive_scaled_error"])
    point_count = containment_count = 0
    recursive_states = 0
    for row, item in zip(rows, items):
        actual = np.asarray(item["states"], dtype=float)
        predicted = recursive_prediction(model, item, model_cfg)
        start = int(model_cfg["recursive_start_state"])
        errors = np.abs(predicted[start + 1 :] - actual[start + 1 :])
        state_point = np.max(errors, axis=1) <= threshold + 1e-15
        state_containment = np.all(errors <= halfwidth[None, :] + 1e-15, axis=1)
        point_count += int(np.sum(state_point))
        containment_count += int(np.sum(state_containment))
        recursive_states += len(errors)
        row.update(
            {
                "point_pass_count": int(np.sum(state_point)),
                "containment_pass_count": int(np.sum(state_containment)),
                "recursive_state_count": int(len(errors)),
                "point_pass": bool(np.all(state_point)),
                "containment_pass": bool(np.all(state_containment)),
                "tube_cap_pass": bool(np.all(halfwidth <= caps + 1e-15)),
                "passed": bool(
                    np.all(state_point)
                    and np.all(state_containment)
                    and np.all(halfwidth <= caps + 1e-15)
                    and row["formal_verdict_reproduced"]
                ),
            }
        )
    summary = {
        "trajectory_count": len(rows),
        "recursive_state_count": recursive_states,
        "point_pass_count": point_count,
        "containment_pass_count": containment_count,
        "tube_cap_pass": bool(np.all(halfwidth <= caps + 1e-15)),
        "formal_verdict_reproduction_count": len(rows) - mismatch,
        "maximum_absolute_recursive_scaled_error": float(np.max(component)),
        "mean_squared_recursive_scaled_error": mse,
        "componentwise_maximum_scaled_residual": component.tolist(),
        "tube_halfwidth_scaled": halfwidth.tolist(),
        "tube_halfwidth_physical": (
            halfwidth * np.asarray(model_cfg["visible_state_scales"], dtype=float)
        ).tolist(),
        "passed": bool(rows and all(row["passed"] for row in rows)),
    }
    return rows, summary


def calibration_artifact(
    training: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    model_cfg: Mapping[str, Any],
    formal_evaluator: FormalEvaluator,
) -> dict[str, Any]:
    model = training["model"]
    _, calibration_component, _, _ = _prediction_rows(
        model, items, model_cfg, formal_evaluator
    )
    training_component = np.asarray(
        training["training_componentwise_maximum_scaled_residual"], dtype=float
    )
    calibrated = np.maximum(training_component, calibration_component)
    rows, summary = evaluate_recursive_set(
        model, items, model_cfg, formal_evaluator, calibrated
    )
    return {
        "training_componentwise_maximum_scaled_residual": training_component.tolist(),
        "calibration_componentwise_maximum_scaled_residual": calibration_component.tolist(),
        "calibrated_componentwise_scaled_residual": calibrated.tolist(),
        "tube_multiplier": float(model_cfg["tube_multiplier"]),
        "calibration_rows": rows,
        "calibration_summary": summary,
        "holdout_outcome_access_count_before_tube_hash": 0,
        "passed": bool(summary["passed"]),
    }
