"""Deterministic nested whole-pair kernel response model for D1R14R7."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np


Array = np.ndarray


@dataclass(frozen=True)
class Candidate:
    pca_rank: int
    bandwidth_multiplier: float
    ridge: float

    def key(self) -> tuple[int, float, float]:
        return (self.pca_rank, self.bandwidth_multiplier, self.ridge)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pca_rank": self.pca_rank,
            "bandwidth_multiplier": self.bandwidth_multiplier,
            "ridge": self.ridge,
        }


def candidates(cfg: Mapping[str, Any]) -> list[Candidate]:
    model = cfg["model_contract"]
    return [
        Candidate(int(rank), float(multiplier), float(ridge))
        for rank in model["pca_ranks"]
        for multiplier in model["rbf_median_distance_multipliers"]
        for ridge in model["kernel_ridges"]
    ]


def _preprocessor(items: Sequence[Mapping[str, Any]], rank: int, floor: float) -> dict[str, Array]:
    x = np.asarray([item["descriptor"] for item in items], dtype=float)
    if x.ndim != 2 or len(x) == 0 or not np.all(np.isfinite(x)):
        raise ValueError("R7 descriptor matrix is invalid")
    mean = np.mean(x, axis=0)
    scale = np.maximum(np.std(x, axis=0), floor)
    z = (x - mean) / scale
    _, _, vt = np.linalg.svd(z, full_matrices=False)
    if rank <= 0 or rank > len(vt):
        raise ValueError("R7 PCA rank is unavailable")
    return {"mean": mean, "scale": scale, "components": vt[:rank]}


def _transform(pre: Mapping[str, Array], descriptor: Sequence[float]) -> Array:
    x = np.asarray(descriptor, dtype=float)
    return ((x - pre["mean"]) / pre["scale"]) @ pre["components"].T


def _median_distance(x: Array, floor: float) -> float:
    if len(x) < 2:
        return floor
    delta = x[:, None, :] - x[None, :, :]
    distance = np.sqrt(np.sum(delta * delta, axis=2))
    values = distance[np.triu_indices(len(x), 1)]
    values = values[values > floor]
    return max(float(np.median(values)) if len(values) else floor, floor)


def _kernel(left: Array, right: Array, bandwidth: float) -> Array:
    delta = left[:, None, :] - right[None, :, :]
    squared = np.sum(delta * delta, axis=2)
    return np.exp(-0.5 * squared / (bandwidth * bandwidth))


def fit_model(
    items: Sequence[Mapping[str, Any]], candidate: Candidate, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    model_cfg = cfg["model_contract"]
    floor = float(model_cfg["standard_deviation_floor"])
    pre = _preprocessor(items, candidate.pca_rank, floor)
    projected = {str(item["response_id"]): _transform(pre, item["descriptor"]) for item in items}
    heads: dict[str, list[dict[str, Any]]] = {}
    for sign in (-1, 1):
        for direction in range(int(cfg["bank_contract"]["direction_count"])):
            members = [
                item for item in items
                if int(item["sign"]) == sign and int(item["direction_index"]) == direction
            ]
            if not members:
                raise ValueError("R7 response head has no training members")
            lag_models: list[dict[str, Any]] = []
            for lag in range(1, max(len(item["response"]) for item in members) + 1):
                available = [item for item in members if len(item["response"]) >= lag]
                x = np.asarray([projected[str(item["response_id"])] for item in available])
                y = np.asarray([np.asarray(item["response"])[lag - 1, 2:5] for item in available])
                median = _median_distance(x, float(model_cfg["bandwidth_floor"]))
                bandwidth = max(candidate.bandwidth_multiplier * median, float(model_cfg["bandwidth_floor"]))
                gram = _kernel(x, x, bandwidth)
                y_mean = np.mean(y, axis=0)
                alpha = np.linalg.lstsq(
                    gram + candidate.ridge * np.eye(len(gram)), y - y_mean, rcond=None
                )[0]
                lag_models.append({
                    "lag": lag,
                    "x": x,
                    "bandwidth": bandwidth,
                    "y_mean": y_mean,
                    "alpha": alpha,
                })
            heads[f"{sign}:{direction}"] = lag_models
    return {"candidate": candidate, "preprocessor": pre, "heads": heads}


def predict_item(model: Mapping[str, Any], item: Mapping[str, Any], cfg: Mapping[str, Any]) -> Array:
    descriptor = _transform(model["preprocessor"], item["descriptor"])[None, :]
    head = model["heads"][f"{int(item['sign'])}:{int(item['direction_index'])}"]
    count = len(item["response"])
    if count > len(head):
        raise ValueError("R7 prediction requests an untrained lag")
    output = np.zeros((count, 5), dtype=float)
    for index, lag_model in enumerate(head[:count]):
        k = _kernel(descriptor, lag_model["x"], float(lag_model["bandwidth"]))
        output[index, 2:5] = lag_model["y_mean"] + k[0] @ lag_model["alpha"]
    dt = float(cfg["bank_contract"]["dt_s"])
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    output[:, 0] = np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    if not np.all(np.isfinite(output)):
        raise ValueError("R7 prediction is non-finite")
    return output


def prediction_row(item: Mapping[str, Any], predicted: Array, cfg: Mapping[str, Any]) -> dict[str, Any]:
    actual = np.asarray(item["response"], dtype=float)
    error = predicted - actual
    actual_flat = actual.reshape(-1)
    predicted_flat = predicted.reshape(-1)
    actual_norm = float(np.linalg.norm(actual_flat))
    predicted_norm = float(np.linalg.norm(predicted_flat))
    relative = float(np.linalg.norm(error) / max(actual_norm, 1e-300))
    cosine = float(np.dot(actual_flat, predicted_flat) / max(actual_norm * predicted_norm, 1e-300))
    actual_peak = float(np.max(np.abs(actual)))
    predicted_peak = float(np.max(np.abs(predicted)))
    ratio = predicted_peak / max(actual_peak, 1e-300)
    gates = cfg["gates"]
    criteria = {
        "finite": bool(np.all(np.isfinite(predicted))),
        "relative_l2": relative <= float(gates["maximum_relative_l2_error"]) + 1e-15,
        "cosine": cosine >= float(gates["minimum_response_cosine"]) - 1e-15,
        "peak_ratio": float(gates["minimum_peak_ratio"]) - 1e-15 <= ratio <= float(gates["maximum_peak_ratio"]) + 1e-15,
        "point_error": float(np.max(np.abs(error))) <= float(gates["maximum_absolute_scaled_point_error"]) + 1e-15,
    }
    return {
        "response_id": str(item["response_id"]),
        "context_id": str(item["context_id"]),
        "pair_id": str(item["pair_id"]),
        "history_member": str(item["history_member"]),
        "issue_task_step": int(item["issue_task_step"]),
        "sign": int(item["sign"]),
        "direction_index": int(item["direction_index"]),
        "relative_l2_error": relative,
        "response_cosine": cosine,
        "actual_peak": actual_peak,
        "predicted_peak": predicted_peak,
        "peak_ratio": ratio,
        "maximum_absolute_scaled_point_error": float(np.max(np.abs(error))),
        "componentwise_maximum_absolute_scaled_error": np.max(np.abs(error), axis=0).tolist(),
        "mean_squared_scaled_error": float(np.mean(error * error)),
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "predicted_response": predicted.tolist(),
    }


def _candidate_score(rows: Sequence[Mapping[str, Any]], candidate: Candidate) -> tuple[Any, ...]:
    relative = np.asarray([float(row["relative_l2_error"]) for row in rows])
    return (
        sum(not bool(row["passed"]) for row in rows),
        max(float(row["maximum_absolute_scaled_point_error"]) for row in rows),
        float(np.quantile(relative, 0.95, method="linear")),
        float(np.mean([float(row["mean_squared_scaled_error"]) for row in rows])),
        candidate.pca_rank,
        candidate.bandwidth_multiplier,
        candidate.ridge,
    )


def cross_validated_rows(
    items: Sequence[Mapping[str, Any]], candidate: Candidate, cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pairs = sorted({str(item["pair_id"]) for item in items})
    for pair in pairs:
        train = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        model = fit_model(train, candidate, cfg)
        rows.extend(prediction_row(item, predict_item(model, item, cfg), cfg) for item in held)
    return sorted(rows, key=lambda row: str(row["response_id"]))


def select_candidate(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[Candidate, list[dict[str, Any]]]:
    scores = []
    for candidate in candidates(cfg):
        rows = cross_validated_rows(items, candidate, cfg)
        scores.append({"candidate": candidate, "score": _candidate_score(rows, candidate)})
    selected = min(scores, key=lambda row: row["score"])
    report = [
        {"candidate": row["candidate"].as_dict(), "selection_score": list(row["score"][:4])}
        for row in scores
    ]
    return selected["candidate"], report


def nested_outer_rows(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    folds = []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        train = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        selected, scores = select_candidate(train, cfg)
        model = fit_model(train, selected, cfg)
        held_rows = [prediction_row(item, predict_item(model, item, cfg), cfg) for item in held]
        rows.extend(held_rows)
        folds.append({
            "held_pair_id": pair,
            "training_pair_count": len({str(item["pair_id"]) for item in train}),
            "held_response_count": len(held),
            "selected_candidate": selected.as_dict(),
            "inner_candidate_scores": scores,
        })
    return sorted(rows, key=lambda row: str(row["response_id"])), folds


def geometry(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = cfg["gates"]
    grouped: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["context_id"]), int(row["issue_task_step"]), int(row["sign"])), []).append(row)
    branches = []
    direction_pass = 0
    rank_pass = 0
    condition_pass = 0
    for key, members in sorted(grouped.items()):
        members = sorted(members, key=lambda row: int(row["direction_index"]))
        if [int(row["direction_index"]) for row in members] != [0, 1, 2, 3]:
            raise ValueError("R7 predicted branch coverage changed")
        columns = []
        peaks = []
        for row in members:
            value = np.asarray(row["predicted_response"], dtype=float).reshape(-1)
            peak = float(np.max(np.abs(value)))
            norm = float(np.linalg.norm(value))
            passed = bool(np.all(np.isfinite(value)) and norm > 0.0 and peak >= float(gates["minimum_predicted_peak"]) - 1e-15)
            direction_pass += int(passed)
            peaks.append(peak)
            columns.append(value / max(norm, 1e-300))
        matrix = np.column_stack(columns)
        singular = np.linalg.svd(matrix, compute_uv=False)
        rank = int(np.sum(singular > singular[0] * float(gates["rank_relative_tolerance"])))
        condition = float(singular[0] / singular[-1]) if rank == 4 and singular[-1] > 0 else float("inf")
        rank_ok = rank == int(gates["required_rank"])
        condition_ok = condition <= float(gates["maximum_condition_number"]) + 1e-12
        rank_pass += int(rank_ok)
        condition_pass += int(condition_ok)
        branches.append({
            "context_id": key[0], "issue_task_step": key[1], "sign": key[2],
            "direction_peaks": peaks, "rank": rank, "condition_number": condition,
            "passed": bool(all(peak >= float(gates["minimum_predicted_peak"]) - 1e-15 for peak in peaks) and rank_ok and condition_ok),
        })
    return {
        "branch_count": len(branches),
        "direction_pass_count": direction_pass,
        "rank_pass_count": rank_pass,
        "condition_pass_count": condition_pass,
        "maximum_condition_number": max(row["condition_number"] for row in branches),
        "minimum_predicted_peak": min(min(row["direction_peaks"]) for row in branches),
        "rows": branches,
        "passed": bool(len(branches) == int(gates["required_branch_pass_count"]) and direction_pass == int(gates["required_response_pass_count"]) and rank_pass == len(branches) and condition_pass == len(branches)),
    }


def aggregate(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    component = np.max(np.asarray([row["componentwise_maximum_absolute_scaled_error"] for row in rows]), axis=0)
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    gates = cfg["gates"]
    precursor = np.asarray(gates["response_floor_physical"], dtype=float) / scales + float(gates["tube_multiplier"]) * component
    caps = np.asarray(gates["tube_caps_physical"], dtype=float) / scales
    return {
        "response_count": len(rows),
        "response_pass_count": sum(bool(row["passed"]) for row in rows),
        "maximum_relative_l2_error": max(float(row["relative_l2_error"]) for row in rows),
        "minimum_response_cosine": min(float(row["response_cosine"]) for row in rows),
        "minimum_peak_ratio": min(float(row["peak_ratio"]) for row in rows),
        "maximum_peak_ratio": max(float(row["peak_ratio"]) for row in rows),
        "maximum_absolute_scaled_point_error": max(float(row["maximum_absolute_scaled_point_error"]) for row in rows),
        "componentwise_maximum_absolute_scaled_error": component.tolist(),
        "tube_precursor_scaled": precursor.tolist(),
        "tube_precursor_physical": (precursor * scales).tolist(),
        "tube_cap_pass": bool(np.all(precursor <= caps + 1e-15)),
        "passed": bool(len(rows) == int(gates["required_response_pass_count"]) and all(bool(row["passed"]) for row in rows) and np.all(precursor <= caps + 1e-15)),
    }


def serializable_model(model: Mapping[str, Any]) -> dict[str, Any]:
    pre = model["preprocessor"]
    return {
        "candidate": model["candidate"].as_dict(),
        "preprocessor": {key: np.asarray(value).tolist() for key, value in pre.items()},
        "heads": {
            key: [
                {
                    "lag": int(row["lag"]), "x": np.asarray(row["x"]).tolist(),
                    "bandwidth": float(row["bandwidth"]), "y_mean": np.asarray(row["y_mean"]).tolist(),
                    "alpha": np.asarray(row["alpha"]).tolist(),
                }
                for row in values
            ]
            for key, values in model["heads"].items()
        },
    }


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()
