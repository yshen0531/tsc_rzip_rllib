"""Action-conditioned full-history kernel response model for D1R14R7R2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_response_model as metrics


@dataclass(frozen=True)
class Candidate:
    pca_rank: int
    bandwidth_multiplier: float
    ridge: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "pca_rank": self.pca_rank,
            "bandwidth_multiplier": self.bandwidth_multiplier,
            "ridge": self.ridge,
        }


def candidates(cfg: Mapping[str, Any]) -> list[Candidate]:
    contract = cfg["model_contract"]
    return [
        Candidate(int(rank), float(multiplier), float(ridge))
        for rank in contract["pca_ranks"]
        for multiplier in contract["rbf_median_distance_multipliers"]
        for ridge in contract["kernel_ridges"]
    ]


def _preprocessor(
    items: Sequence[Mapping[str, Any]], rank: int, floor: float
) -> dict[str, np.ndarray]:
    values = np.asarray([item["descriptor"] for item in items], dtype=float)
    if values.ndim != 2 or len(values) == 0 or not np.all(np.isfinite(values)):
        raise ValueError("R7R2 descriptor matrix invalid")
    mean = values.mean(axis=0)
    scale = np.maximum(values.std(axis=0), floor)
    _, _, vt = np.linalg.svd((values - mean) / scale, full_matrices=False)
    if rank <= 0 or rank > len(vt):
        raise ValueError("R7R2 PCA rank unavailable")
    return {"mean": mean, "scale": scale, "components": vt[:rank]}


def _context(preprocessor: Mapping[str, np.ndarray], descriptor: Sequence[float]) -> np.ndarray:
    value = np.asarray(descriptor, dtype=float)
    return ((value - preprocessor["mean"]) / preprocessor["scale"]) @ preprocessor[
        "components"
    ].T


def _median_distance(values: np.ndarray, floor: float) -> float:
    if len(values) < 2:
        return floor
    delta = values[:, None, :] - values[None, :, :]
    distance = np.sqrt(np.sum(delta * delta, axis=2))
    upper = distance[np.triu_indices(len(values), 1)]
    positive = upper[upper > floor]
    return max(float(np.median(positive)) if len(positive) else floor, floor)


def _kernel(left: np.ndarray, right: np.ndarray, bandwidth: float) -> np.ndarray:
    delta = left[:, None, :] - right[None, :, :]
    return np.exp(-0.5 * np.sum(delta * delta, axis=2) / (bandwidth * bandwidth))


def fit_model(
    items: Sequence[Mapping[str, Any]], candidate: Candidate, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    contract = cfg["model_contract"]
    floor = float(contract["standard_deviation_floor"])
    preprocessor = _preprocessor(items, candidate.pca_rank, floor)
    contexts = {
        str(item["response_id"]): _context(preprocessor, item["descriptor"])
        for item in items
    }
    heads: dict[str, dict[str, Any]] = {}
    for sign in (-1, 1):
        for direction in range(int(cfg["bank_contract"]["direction_count"])):
            members = [
                item
                for item in items
                if int(item["sign"]) == sign
                and int(item["direction_index"]) == direction
            ]
            if not members:
                raise ValueError("R7R2 response head has no training members")
            amplitudes = np.asarray([item["action_scale"] for item in members], dtype=float)
            amplitude_mean = float(amplitudes.mean())
            amplitude_scale = max(float(amplitudes.std()), floor)
            features = {
                str(item["response_id"]): np.concatenate(
                    (
                        contexts[str(item["response_id"])],
                        [(float(item["action_scale"]) - amplitude_mean) / amplitude_scale],
                    )
                )
                for item in members
            }
            lag_heads = []
            maximum = max(len(item["response"]) for item in members)
            for lag in range(1, maximum + 1):
                available = [item for item in members if len(item["response"]) >= lag]
                x = np.asarray([features[str(item["response_id"])] for item in available])
                y = np.asarray(
                    [np.asarray(item["response"], dtype=float)[lag - 1, 2:5] for item in available]
                )
                median = _median_distance(x, float(contract["bandwidth_floor"]))
                bandwidth = max(
                    candidate.bandwidth_multiplier * median,
                    float(contract["bandwidth_floor"]),
                )
                gram = _kernel(x, x, bandwidth)
                y_mean = y.mean(axis=0)
                alpha = np.linalg.lstsq(
                    gram + candidate.ridge * np.eye(len(gram)), y - y_mean, rcond=None
                )[0]
                lag_heads.append(
                    {
                        "lag": lag,
                        "x": x,
                        "bandwidth": bandwidth,
                        "y_mean": y_mean,
                        "alpha": alpha,
                    }
                )
            heads[f"{sign}:{direction}"] = {
                "amplitude_mean": amplitude_mean,
                "amplitude_scale": amplitude_scale,
                "lags": lag_heads,
            }
    return {"candidate": candidate, "preprocessor": preprocessor, "heads": heads}


def _tail(values: np.ndarray, observed: int, count: int, cfg: Mapping[str, Any]) -> None:
    if count <= observed:
        return
    contract = cfg["model_contract"]
    points = int(contract["tail_fit_point_count"])
    degree = int(contract["tail_polynomial_degree"])
    if observed < points or degree >= points:
        raise ValueError("R7R2 tail fit coverage invalid")
    start = observed - points
    x = np.arange(start + 1, observed + 1, dtype=float)
    future = np.arange(observed + 1, count + 1, dtype=float)
    for component in (2, 3, 4):
        coefficient = np.polyfit(x, values[start:observed, component], degree)
        values[observed:count, component] = np.polyval(coefficient, future)


def predict_item(
    model: Mapping[str, Any], item: Mapping[str, Any], cfg: Mapping[str, Any]
) -> np.ndarray:
    head = model["heads"][f"{int(item['sign'])}:{int(item['direction_index'])}"]
    context = _context(model["preprocessor"], item["descriptor"])
    feature = np.concatenate(
        (
            context,
            [
                (float(item["action_scale"]) - float(head["amplitude_mean"]))
                / float(head["amplitude_scale"])
            ],
        )
    )[None, :]
    count = len(item["response"])
    observed = min(count, len(head["lags"]))
    output = np.zeros((count, 5), dtype=float)
    for index, lag_head in enumerate(head["lags"][:observed]):
        kernel = _kernel(feature, lag_head["x"], float(lag_head["bandwidth"]))
        output[index, 2:5] = lag_head["y_mean"] + kernel[0] @ lag_head["alpha"]
    _tail(output, observed, count, cfg)
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    if not np.all(np.isfinite(output)):
        raise ValueError("R7R2 prediction non-finite")
    return output


def prediction_row(
    item: Mapping[str, Any], predicted: np.ndarray, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    row = metrics.prediction_row(item, predicted, cfg)
    row.update(
        {
            "source_stage": str(item["source_stage"]),
            "action_scale": float(item["action_scale"]),
            "geometry_roles": list(item["geometry_roles"]),
        }
    )
    return row


def _score(rows: Sequence[Mapping[str, Any]], candidate: Candidate) -> tuple[Any, ...]:
    relative = np.asarray([float(row["relative_l2_error"]) for row in rows])
    return (
        sum(not bool(row["passed"]) for row in rows),
        max(float(row["maximum_absolute_scaled_point_error"]) for row in rows),
        float(np.quantile(relative, 0.95, method="linear")),
        float(np.mean([row["mean_squared_scaled_error"] for row in rows])),
        candidate.pca_rank,
        candidate.bandwidth_multiplier,
        candidate.ridge,
    )


def cross_validated_rows(
    items: Sequence[Mapping[str, Any]], candidate: Candidate, cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rows = []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        train = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        fitted = fit_model(train, candidate, cfg)
        rows.extend(prediction_row(item, predict_item(fitted, item, cfg), cfg) for item in held)
    return sorted(rows, key=lambda row: row["response_id"])


def select_candidate(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[Candidate, list[dict[str, Any]]]:
    scored = []
    for candidate in candidates(cfg):
        rows = cross_validated_rows(items, candidate, cfg)
        scored.append((candidate, _score(rows, candidate)))
    selected = min(scored, key=lambda row: row[1])[0]
    report = [
        {"candidate": candidate.as_dict(), "selection_score": list(score[:4])}
        for candidate, score in scored
    ]
    return selected, report


def nested_outer_rows(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, folds = [], []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        train = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        selected, scores = select_candidate(train, cfg)
        fitted = fit_model(train, selected, cfg)
        rows.extend(prediction_row(item, predict_item(fitted, item, cfg), cfg) for item in held)
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 3,
                "held_response_count": len(held),
                "selected_candidate": selected.as_dict(),
                "inner_candidate_scores": scores,
            }
        )
    return sorted(rows, key=lambda row: row["response_id"]), folds


def _geometry_family(
    rows: Sequence[Mapping[str, Any]], role: str, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    gates = cfg["gates"]
    grouped: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        if role in row["geometry_roles"]:
            key = (str(row["context_id"]), int(row["issue_task_step"]), int(row["sign"]))
            grouped.setdefault(key, []).append(row)
    branches = []
    for key, members in sorted(grouped.items()):
        members = sorted(members, key=lambda row: int(row["direction_index"]))
        if [int(row["direction_index"]) for row in members] != [0, 1, 2, 3]:
            raise ValueError("R7R2 geometry family coverage changed")
        columns = []
        for row in members:
            value = np.asarray(row["predicted_response"], dtype=float).reshape(-1)
            norm = float(np.linalg.norm(value))
            columns.append(value / max(norm, 1e-300))
        singular = np.linalg.svd(np.column_stack(columns), compute_uv=False)
        rank = int(np.sum(singular > singular[0] * float(gates["rank_relative_tolerance"])))
        condition = (
            float(singular[0] / singular[-1])
            if rank == int(gates["required_rank"]) and singular[-1] > 0.0
            else float("inf")
        )
        passed = bool(
            rank == int(gates["required_rank"])
            and condition <= float(gates["maximum_condition_number"]) + 1e-12
        )
        branches.append(
            {
                "context_id": key[0],
                "issue_task_step": key[1],
                "sign": key[2],
                "rank": rank,
                "condition_number": condition,
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
        "branch_count": len(branches),
        "rank_pass_count": sum(row["rank"] == int(gates["required_rank"]) for row in branches),
        "condition_pass_count": sum(
            row["condition_number"] <= float(gates["maximum_condition_number"]) + 1e-12
            for row in branches
        ),
        "maximum_condition_number": max(row["condition_number"] for row in branches),
        "rows": branches,
        "passed": bool(len(branches) == required and all(row["passed"] for row in branches)),
    }


def geometry(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = cfg["gates"]
    peaks = [
        float(np.max(np.abs(np.asarray(row["predicted_response"], dtype=float)))) for row in rows
    ]
    signal_pass = sum(peak >= float(gates["minimum_predicted_peak"]) - 1e-15 for peak in peaks)
    canonical = _geometry_family(rows, "canonical", cfg)
    operational = _geometry_family(rows, "operational", cfg)
    return {
        "response_count": len(rows),
        "signal_pass_count": signal_pass,
        "minimum_predicted_peak": min(peaks),
        "canonical": canonical,
        "operational": operational,
        "passed": bool(
            len(rows) == int(gates["required_signal_pass_count"])
            and signal_pass == int(gates["required_signal_pass_count"])
            and canonical["passed"]
            and operational["passed"]
        ),
    }


def serializable_model(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate": model["candidate"].as_dict(),
        "preprocessor": {
            key: np.asarray(value).tolist() for key, value in model["preprocessor"].items()
        },
        "heads": {
            key: {
                "amplitude_mean": float(head["amplitude_mean"]),
                "amplitude_scale": float(head["amplitude_scale"]),
                "lags": [
                    {
                        "lag": int(row["lag"]),
                        "x": np.asarray(row["x"]).tolist(),
                        "bandwidth": float(row["bandwidth"]),
                        "y_mean": np.asarray(row["y_mean"]).tolist(),
                        "alpha": np.asarray(row["alpha"]).tolist(),
                    }
                    for row in head["lags"]
                ],
            }
            for key, head in model["heads"].items()
        },
    }
