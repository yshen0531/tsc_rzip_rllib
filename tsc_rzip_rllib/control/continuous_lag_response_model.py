"""Continuous-lag tensor response model for D1R14R7R1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_response_model as metrics


@dataclass(frozen=True)
class Candidate:
    pca_rank: int
    temporal_degree: int
    ridge: float

    def as_dict(self) -> dict[str, Any]:
        return {"pca_rank": self.pca_rank, "temporal_degree": self.temporal_degree, "ridge": self.ridge}


def candidates(cfg: Mapping[str, Any]) -> list[Candidate]:
    model = cfg["model_contract"]
    return [Candidate(int(rank), int(degree), float(ridge)) for rank in model["pca_ranks"] for degree in model["temporal_legendre_degrees"] for ridge in model["ridges"]]


def _preprocessor(items: Sequence[Mapping[str, Any]], rank: int, floor: float) -> dict[str, np.ndarray]:
    x = np.asarray([item["descriptor"] for item in items], dtype=float)
    if x.ndim != 2 or len(x) == 0 or not np.all(np.isfinite(x)):
        raise ValueError("R7R1 descriptor matrix invalid")
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), floor)
    _, _, vt = np.linalg.svd((x - mean) / scale, full_matrices=False)
    if rank > len(vt):
        raise ValueError("R7R1 PCA rank unavailable")
    return {"mean": mean, "scale": scale, "components": vt[:rank]}


def _context(pre: Mapping[str, np.ndarray], descriptor: Sequence[float]) -> np.ndarray:
    value = np.asarray(descriptor, dtype=float)
    return ((value - pre["mean"]) / pre["scale"]) @ pre["components"].T


def _legendre(lag: int, degree: int, maximum_lag: int) -> np.ndarray:
    x = 2.0 * float(lag) / float(maximum_lag) - 1.0
    values = [1.0, x]
    for order in range(2, degree + 1):
        values.append(((2 * order - 1) * x * values[-1] - (order - 1) * values[-2]) / order)
    return np.asarray(values[: degree + 1], dtype=float)


def _feature(context: np.ndarray, lag: int, degree: int, maximum_lag: int) -> np.ndarray:
    return np.kron(_legendre(lag, degree, maximum_lag), np.concatenate(([1.0], context)))


def fit_model(items: Sequence[Mapping[str, Any]], candidate: Candidate, cfg: Mapping[str, Any]) -> dict[str, Any]:
    floor = float(cfg["model_contract"]["standard_deviation_floor"])
    maximum_lag = int(cfg["bank_contract"]["maximum_relative_lag"])
    pre = _preprocessor(items, candidate.pca_rank, floor)
    heads = {}
    for sign in (-1, 1):
        for direction in range(4):
            members = [item for item in items if int(item["sign"]) == sign and int(item["direction_index"]) == direction]
            if not members:
                raise ValueError("R7R1 response head has no training members")
            x_rows, y_rows = [], []
            for item in members:
                context = _context(pre, item["descriptor"])
                response = np.asarray(item["response"], dtype=float)
                for lag in range(1, len(response) + 1):
                    x_rows.append(_feature(context, lag, candidate.temporal_degree, maximum_lag))
                    y_rows.append(response[lag - 1, 2:5])
            x = np.asarray(x_rows)
            y = np.asarray(y_rows)
            x_mean = x.mean(axis=0)
            x_scale = np.maximum(x.std(axis=0), floor)
            z = (x - x_mean) / x_scale
            y_mean = y.mean(axis=0)
            coefficient = np.linalg.lstsq(z.T @ z + candidate.ridge * np.eye(z.shape[1]), z.T @ (y - y_mean), rcond=None)[0]
            heads[f"{sign}:{direction}"] = {"x_mean": x_mean, "x_scale": x_scale, "y_mean": y_mean, "coefficient": coefficient}
    return {"candidate": candidate, "preprocessor": pre, "heads": heads}


def predict_item(model: Mapping[str, Any], item: Mapping[str, Any], cfg: Mapping[str, Any]) -> np.ndarray:
    candidate = model["candidate"]
    maximum_lag = int(cfg["bank_contract"]["maximum_relative_lag"])
    context = _context(model["preprocessor"], item["descriptor"])
    head = model["heads"][f"{int(item['sign'])}:{int(item['direction_index'])}"]
    output = np.zeros((len(item["response"]), 5), dtype=float)
    for lag in range(1, len(output) + 1):
        feature = _feature(context, lag, candidate.temporal_degree, maximum_lag)
        output[lag - 1, 2:5] = head["y_mean"] + ((feature - head["x_mean"]) / head["x_scale"]) @ head["coefficient"]
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    if not np.all(np.isfinite(output)):
        raise ValueError("R7R1 prediction non-finite")
    return output


def _score(rows: Sequence[Mapping[str, Any]], candidate: Candidate) -> tuple[Any, ...]:
    relative = np.asarray([float(row["relative_l2_error"]) for row in rows])
    return (sum(not bool(row["passed"]) for row in rows), max(float(row["maximum_absolute_scaled_point_error"]) for row in rows), float(np.quantile(relative, 0.95, method="linear")), float(np.mean([row["mean_squared_scaled_error"] for row in rows])), candidate.pca_rank, candidate.temporal_degree, candidate.ridge)


def cross_validated_rows(items: Sequence[Mapping[str, Any]], candidate: Candidate, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        train = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        model = fit_model(train, candidate, cfg)
        rows.extend(metrics.prediction_row(item, predict_item(model, item, cfg), cfg) for item in held)
    return sorted(rows, key=lambda row: row["response_id"])


def select_candidate(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[Candidate, list[dict[str, Any]]]:
    scored = []
    for candidate in candidates(cfg):
        rows = cross_validated_rows(items, candidate, cfg)
        scored.append((candidate, _score(rows, candidate)))
    selected = min(scored, key=lambda row: row[1])[0]
    return selected, [{"candidate": candidate.as_dict(), "selection_score": list(score[:4])} for candidate, score in scored]


def nested_outer_rows(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, folds = [], []
    for pair in sorted({str(item["pair_id"]) for item in items}):
        train = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        selected, scores = select_candidate(train, cfg)
        model = fit_model(train, selected, cfg)
        rows.extend(metrics.prediction_row(item, predict_item(model, item, cfg), cfg) for item in held)
        folds.append({"held_pair_id": pair, "training_pair_count": 3, "held_response_count": len(held), "selected_candidate": selected.as_dict(), "inner_candidate_scores": scores})
    return sorted(rows, key=lambda row: row["response_id"]), folds


def serializable_model(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate": model["candidate"].as_dict(),
        "preprocessor": {key: np.asarray(value).tolist() for key, value in model["preprocessor"].items()},
        "heads": {key: {field: np.asarray(value).tolist() for field, value in head.items()} for key, head in model["heads"].items()},
    }
