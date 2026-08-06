"""Causal same-trajectory online innovation adapter for D1R14R8R2."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import action_conditioned_history_response_model as base_model
from tsc_rzip_rllib.control import causal_response_model as metrics


Array = np.ndarray


def fixed_candidate(cfg: Mapping[str, Any]) -> base_model.Candidate:
    value = cfg["fixed_candidate"]
    return base_model.Candidate(
        int(value["pca_rank"]),
        float(value["bandwidth_multiplier"]),
        float(value["ridge"]),
    )


def model_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = dict(cfg["gates"])
    gates["required_response_pass_count"] = int(gates["required_response_count"])
    return {
        "bank_contract": {
            "direction_count": int(cfg["bank_contract"]["direction_count"]),
            "response_scales": list(cfg["bank_contract"]["response_scales"]),
            "dt_s": float(cfg["bank_contract"]["dt_s"]),
        },
        "model_contract": dict(cfg["model_contract"]),
        "gates": gates,
    }


def probe_descriptor(
    visible: Sequence[Sequence[float]],
    issue_task_step: int,
    target_offsets: Sequence[float],
    cfg: Mapping[str, Any],
) -> Array:
    values = np.asarray(visible, dtype=float)
    issue = int(issue_task_step)
    bank = cfg["bank_contract"]
    offsets = tuple(map(int, bank["history_offsets"]))
    if (
        values.ndim != 2
        or values.shape[1] != 5
        or issue < 0
        or issue >= len(values)
        or len(target_offsets) != 3
        or not np.all(np.isfinite(values[: issue + 1]))
    ):
        raise ValueError("R8R2 causal descriptor input invalid")
    history = values[[max(0, issue - offset) for offset in offsets]].reshape(-1)
    availability = np.asarray([float(offset <= issue) for offset in offsets])
    target = np.asarray(target_offsets, dtype=float) / np.asarray(
        bank["target_scales"], dtype=float
    )
    descriptor = np.concatenate((history, availability, target, [(issue - 10.0) / 12.0]))
    if descriptor.shape != (int(bank["descriptor_dimension"]),):
        raise ValueError("R8R2 causal descriptor dimension changed")
    return descriptor


def no_action_forecast(
    visible: Sequence[Sequence[float]], issue_task_step: int, cfg: Mapping[str, Any]
) -> Array:
    values = np.asarray(visible, dtype=float)
    issue = int(issue_task_step)
    contract = cfg["innovation_contract"]
    offsets = np.asarray(contract["baseline_trend_offsets"], dtype=int)
    count = int(contract["baseline_forecast_relative_lags"])
    if (
        values.ndim != 2
        or values.shape[1] != 5
        or tuple(offsets.tolist()) != (-3, -2, -1, 0)
        or issue < 3
        or issue >= len(values)
        or count != 12
    ):
        raise ValueError("R8R2 no-action forecast input invalid")
    samples = values[issue + offsets, 2:5]
    if samples.shape != (4, 3) or not np.all(np.isfinite(samples)):
        raise ValueError("R8R2 no-action trend samples invalid")
    design = np.column_stack((offsets.astype(float), np.ones(4)))
    coefficient = np.linalg.lstsq(design, samples, rcond=None)[0]
    future = np.arange(1, count + 1, dtype=float)
    forecast = np.zeros((count, 5), dtype=float)
    forecast[:, 2:5] = np.column_stack((future, np.ones(count))) @ coefficient
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    forecast[:, 0] = values[issue, 0] + np.cumsum(forecast[:, 2]) * dt * scales[2] / scales[0]
    forecast[:, 1] = values[issue, 1] + np.cumsum(forecast[:, 3]) * dt * scales[3] / scales[1]
    if not np.all(np.isfinite(forecast)):
        raise ValueError("R8R2 no-action forecast non-finite")
    return forecast


def _weights(update_lag: int, recency: float) -> Array:
    if recency == 0.0:
        output = np.zeros(update_lag, dtype=float)
        output[-1] = 1.0
        return output
    output = recency ** np.arange(update_lag - 1, -1, -1, dtype=float)
    return output / np.sum(output)


def adapted_prediction(
    item: Mapping[str, Any],
    cold_prediction: Sequence[Sequence[float]],
    update_lag: int,
    recency: float,
    cfg: Mapping[str, Any],
) -> Array:
    contract = cfg["innovation_contract"]
    update = int(update_lag)
    horizon = int(contract["future_horizon_relative_lags"])
    if update not in tuple(map(int, contract["update_relative_lags"])):
        raise ValueError("R8R2 update lag is not frozen")
    if recency not in tuple(map(float, contract["recency_factors"])):
        raise ValueError("R8R2 recency factor is not frozen")
    base = np.asarray(cold_prediction, dtype=float)
    probe = np.asarray(item["probe_visible"], dtype=float)
    issue = int(item["issue_task_step"])
    forecast = no_action_forecast(probe, issue, cfg)
    required = update + horizon
    if (
        base.ndim != 2
        or base.shape[1] != 5
        or len(base) < required
        or probe.ndim != 2
        or probe.shape[1] != 5
        or len(probe) <= issue + update
        or len(forecast) < required
    ):
        raise ValueError("R8R2 adapted prediction coverage invalid")
    observed = probe[issue + 1 : issue + update + 1] - forecast[:update]
    innovation = observed[:, 2:5] - base[:update, 2:5]
    correction = _weights(update, recency) @ innovation
    output = np.asarray(base[update:required], dtype=float).copy()
    output[:, 2:5] += correction
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = observed[-1, 0] + np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = observed[-1, 1] + np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    if output.shape != (horizon, 5) or not np.all(np.isfinite(output)):
        raise ValueError("R8R2 adapted prediction invalid")
    return output


def prediction_row(
    item: Mapping[str, Any], prediction: Array, update_lag: int, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    update = int(update_lag)
    horizon = int(cfg["innovation_contract"]["future_horizon_relative_lags"])
    target = np.asarray(item["response"], dtype=float)[update : update + horizon]
    scored = dict(item)
    scored["response"] = target
    row = metrics.prediction_row(scored, np.asarray(prediction, dtype=float), cfg)
    row.update(
        {
            "source_stage": str(item["source_stage"]),
            "action_scale": float(item["action_scale"]),
            "geometry_roles": list(item["geometry_roles"]),
            "update_relative_lag": update,
            "actual_response": target.tolist(),
        }
    )
    return row


def cold_row(
    item: Mapping[str, Any], cold_prediction: Array, update_lag: int, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    update = int(update_lag)
    horizon = int(cfg["innovation_contract"]["future_horizon_relative_lags"])
    return prediction_row(item, cold_prediction[update : update + horizon], update, cfg)


def hard_row_pass(row: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    gates = cfg["gates"]
    actual_peak = float(row["actual_peak"])
    predicted_peak = float(row["predicted_peak"])
    return bool(
        (row.get("criteria") or {}).get("finite")
        and float(row["maximum_absolute_scaled_point_error"])
        <= float(gates["maximum_absolute_scaled_point_error"]) + 1e-15
        and float(row["response_cosine"])
        >= float(gates["hard_minimum_response_cosine"]) - 1e-15
        and float(gates["hard_minimum_peak_ratio"]) - 1e-15
        <= float(row["peak_ratio"])
        <= float(gates["hard_maximum_peak_ratio"]) + 1e-15
        and actual_peak >= float(gates["minimum_actual_peak"]) - 1e-15
        and predicted_peak >= float(gates["minimum_predicted_peak"]) - 1e-15
    )


def _geometry_family(
    rows: Sequence[Mapping[str, Any]], role: str, field: str, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    gates = cfg["gates"]
    grouped: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        if role in row["geometry_roles"]:
            key = (str(row["context_id"]), int(row["issue_task_step"]), int(row["sign"]))
            grouped.setdefault(key, []).append(row)
    branches = []
    for key, members in sorted(grouped.items()):
        members = sorted(members, key=lambda value: int(value["direction_index"]))
        if [int(value["direction_index"]) for value in members] != [0, 1, 2, 3]:
            raise ValueError("R8R2 geometry coverage changed")
        columns, peaks = [], []
        for member in members:
            value = np.asarray(member[field], dtype=float).reshape(-1)
            peak = float(np.max(np.abs(value)))
            norm = float(np.linalg.norm(value))
            peaks.append(peak)
            columns.append(value / max(norm, 1e-300))
        singular = np.linalg.svd(np.column_stack(columns), compute_uv=False)
        rank = int(np.sum(singular > singular[0] * float(gates["rank_relative_tolerance"])))
        condition = (
            float(singular[0] / singular[-1])
            if rank == int(gates["required_rank"]) and singular[-1] > 0.0
            else float("inf")
        )
        passed = bool(
            all(peak >= float(gates["minimum_predicted_peak"]) - 1e-15 for peak in peaks)
            and rank == int(gates["required_rank"])
            and condition <= float(gates["maximum_condition_number"]) + 1e-12
        )
        branches.append(
            {
                "context_id": key[0],
                "issue_task_step": key[1],
                "sign": key[2],
                "rank": rank,
                "condition_number": condition,
                "minimum_peak": min(peaks),
                "passed": passed,
            }
        )
    required = int(
        gates[
            "required_canonical_branch_count"
            if role == "canonical"
            else "required_operational_branch_count"
        ]
    )
    return {
        "role": role,
        "field": field,
        "branch_count": len(branches),
        "rank_pass_count": sum(row["rank"] == int(gates["required_rank"]) for row in branches),
        "condition_pass_count": sum(
            row["condition_number"] <= float(gates["maximum_condition_number"]) + 1e-12
            for row in branches
        ),
        "maximum_condition_number": max(row["condition_number"] for row in branches),
        "minimum_peak": min(row["minimum_peak"] for row in branches),
        "failed_branch_count": sum(not row["passed"] for row in branches),
        "rows": branches,
        "passed": bool(len(branches) == required and all(row["passed"] for row in branches)),
    }


def geometry(rows: Sequence[Mapping[str, Any]], field: str, cfg: Mapping[str, Any]) -> dict[str, Any]:
    canonical = _geometry_family(rows, "canonical", field, cfg)
    operational = _geometry_family(rows, "operational", field, cfg)
    return {
        "field": field,
        "canonical": canonical,
        "operational": operational,
        "passed": bool(canonical["passed"] and operational["passed"]),
    }


def selection_score(
    rows: Sequence[Mapping[str, Any]], recency: float, cfg: Mapping[str, Any]
) -> tuple[Any, ...]:
    aggregate = metrics.aggregate(rows, cfg)
    predicted = geometry(rows, "predicted_response", cfg)
    actual = geometry(rows, "actual_response", cfg)
    hard_failures = (
        sum(not hard_row_pass(row, cfg) for row in rows)
        + int(not aggregate["tube_cap_pass"])
        + predicted["canonical"]["failed_branch_count"]
        + predicted["operational"]["failed_branch_count"]
        + actual["canonical"]["failed_branch_count"]
        + actual["operational"]["failed_branch_count"]
    )
    relative = np.asarray([float(row["relative_l2_error"]) for row in rows])
    return (
        hard_failures,
        sum(not bool(row["passed"]) for row in rows),
        max(float(row["maximum_absolute_scaled_point_error"]) for row in rows),
        float(np.quantile(relative, 0.95, method="linear")),
        float(recency),
    )


def nested_outer_predictions(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[dict[int, list[dict[str, Any]]], dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    updates = tuple(map(int, cfg["innovation_contract"]["update_relative_lags"]))
    recencies = tuple(map(float, cfg["innovation_contract"]["recency_factors"]))
    mcfg = model_config(cfg)
    candidate = fixed_candidate(cfg)
    adapted: dict[int, list[dict[str, Any]]] = {value: [] for value in updates}
    cold: dict[int, list[dict[str, Any]]] = {value: [] for value in updates}
    folds = []
    pairs = sorted({str(item["pair_id"]) for item in items})
    for outer_pair in pairs:
        outer_train = [item for item in items if str(item["pair_id"]) != outer_pair]
        outer_held = [item for item in items if str(item["pair_id"]) == outer_pair]
        inner_predictions: dict[str, Array] = {}
        for inner_pair in sorted({str(item["pair_id"]) for item in outer_train}):
            inner_train = [item for item in outer_train if str(item["pair_id"]) != inner_pair]
            inner_held = [item for item in outer_train if str(item["pair_id"]) == inner_pair]
            fitted = base_model.fit_model(inner_train, candidate, mcfg)
            for item in inner_held:
                inner_predictions[str(item["response_id"])] = base_model.predict_item(fitted, item, mcfg)
        selected: dict[int, float] = {}
        scores: dict[int, list[dict[str, Any]]] = {}
        for update in updates:
            candidates = []
            for recency in recencies:
                rows = [
                    prediction_row(
                        item,
                        adapted_prediction(
                            item, inner_predictions[str(item["response_id"])], update, recency, cfg
                        ),
                        update,
                        cfg,
                    )
                    for item in outer_train
                ]
                score = selection_score(rows, recency, cfg)
                candidates.append((recency, score))
            selected[update] = min(candidates, key=lambda value: value[1])[0]
            scores[update] = [
                {"recency_factor": value, "selection_score": list(score)}
                for value, score in candidates
            ]
        fitted = base_model.fit_model(outer_train, candidate, mcfg)
        for item in outer_held:
            base = base_model.predict_item(fitted, item, mcfg)
            for update in updates:
                adapted[update].append(
                    prediction_row(
                        item,
                        adapted_prediction(item, base, update, selected[update], cfg),
                        update,
                        cfg,
                    )
                )
                cold[update].append(cold_row(item, base, update, cfg))
        folds.append(
            {
                "held_pair_id": outer_pair,
                "training_pair_count": len(pairs) - 1,
                "held_response_count": len(outer_held),
                "fixed_candidate": candidate.as_dict(),
                "selected_recency_by_update": {str(key): value for key, value in selected.items()},
                "inner_scores_by_update": {str(key): value for key, value in scores.items()},
            }
        )
    for table in (adapted, cold):
        for update in updates:
            table[update].sort(key=lambda row: str(row["response_id"]))
    return adapted, cold, folds


def evaluate_update(
    adapted_rows: Sequence[Mapping[str, Any]],
    cold_rows: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    gates = cfg["gates"]
    if len(adapted_rows) != int(gates["required_response_count"]) or len(cold_rows) != len(adapted_rows):
        raise ValueError("R8R2 update response coverage changed")
    aggregate = metrics.aggregate(adapted_rows, cfg)
    cold_aggregate = metrics.aggregate(cold_rows, cfg)
    predicted = geometry(adapted_rows, "predicted_response", cfg)
    actual = geometry(adapted_rows, "actual_response", cfg)
    pair_counts = {
        pair: sum(bool(row["passed"]) for row in adapted_rows if str(row["pair_id"]) == pair)
        for pair in sorted({str(row["pair_id"]) for row in adapted_rows})
    }
    cold_pair_counts = {
        pair: sum(bool(row["passed"]) for row in cold_rows if str(row["pair_id"]) == pair)
        for pair in pair_counts
    }
    context_counts = {
        context: sum(bool(row["passed"]) for row in adapted_rows if str(row["context_id"]) == context)
        for context in sorted({str(row["context_id"]) for row in adapted_rows})
    }
    hard_pass = bool(
        all(hard_row_pass(row, cfg) for row in adapted_rows)
        and aggregate["tube_cap_pass"]
        and predicted["passed"]
        and actual["passed"]
    )
    improvement = int(aggregate["response_pass_count"] - cold_aggregate["response_pass_count"])
    useful_pass = bool(
        int(aggregate["response_pass_count"])
        >= int(gates["useful_required_response_pass_count"])
        and all(value >= int(gates["useful_required_pair_pass_count"]) for value in pair_counts.values())
        and all(
            value >= int(gates["useful_required_context_pass_count"])
            for value in context_counts.values()
        )
        and improvement >= int(gates["useful_required_improvement_count"])
        and all(pair_counts[key] >= cold_pair_counts[key] for key in pair_counts)
    )
    return {
        "update_relative_lag": int(adapted_rows[0]["update_relative_lag"]),
        "elapsed_warmup_ms": 10 * int(adapted_rows[0]["update_relative_lag"]),
        "future_horizon_ms": 10 * int(cfg["innovation_contract"]["future_horizon_relative_lags"]),
        "aggregate": aggregate,
        "cold_comparator_aggregate": cold_aggregate,
        "response_pass_improvement": improvement,
        "pair_pass_counts": pair_counts,
        "cold_pair_pass_counts": cold_pair_counts,
        "context_pass_counts": context_counts,
        "hard_row_pass_count": sum(hard_row_pass(row, cfg) for row in adapted_rows),
        "predicted_geometry": predicted,
        "actual_geometry": actual,
        "hard_envelope_passed": hard_pass,
        "useful_performance_passed": useful_pass,
        "passed": bool(hard_pass and useful_pass),
        "rows": list(adapted_rows),
        "cold_rows": list(cold_rows),
    }


def baseline_forecast_audit(
    windows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    caps = np.asarray(cfg["gates"]["baseline_component_caps_physical"], dtype=float)
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    rows = []
    for window in windows:
        issue = int(window["issue_task_step"])
        visible = np.asarray(window["baseline_visible"], dtype=float)
        forecast = no_action_forecast(visible, issue, cfg)
        actual = visible[issue + 1 : issue + 1 + len(forecast)]
        error = np.max(np.abs(forecast - actual), axis=0) * scales
        passed = bool(actual.shape == forecast.shape and np.all(np.isfinite(actual)) and np.all(error <= caps + 1e-15))
        rows.append(
            {
                "context_id": str(window["context_id"]),
                "pair_id": str(window["pair_id"]),
                "history_member": str(window["history_member"]),
                "issue_task_step": issue,
                "componentwise_maximum_absolute_error_physical": error.tolist(),
                "maximum_scaled_point_error": float(np.max(error / caps)),
                "passed": passed,
            }
        )
    required = int(cfg["bank_contract"]["baseline_window_count"])
    return {
        "window_count": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "componentwise_maximum_absolute_error_physical": np.max(
            np.asarray([row["componentwise_maximum_absolute_error_physical"] for row in rows]), axis=0
        ).tolist(),
        "maximum_scaled_point_error": max(row["maximum_scaled_point_error"] for row in rows),
        "rows": rows,
        "passed": bool(len(rows) == required and all(row["passed"] for row in rows)),
    }


def select_update(results: Mapping[int, Mapping[str, Any]], cfg: Mapping[str, Any]) -> int | None:
    for update in map(int, cfg["innovation_contract"]["selection_order"]):
        if bool(results[update]["passed"]):
            return update
    return None
