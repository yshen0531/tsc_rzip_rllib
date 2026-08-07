"""Causal history-conditioned no-action observer for D1R14R8R3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np


Array = np.ndarray


@dataclass(frozen=True)
class Candidate:
    family: str
    pca_rank: int
    bandwidth_multiplier: float
    ridge: float

    @property
    def key(self) -> str:
        return (
            f"{self.family}:r{self.pca_rank}:b{self.bandwidth_multiplier:.17g}:"
            f"k{self.ridge:.17g}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "pca_rank": self.pca_rank,
            "bandwidth_multiplier": self.bandwidth_multiplier,
            "ridge": self.ridge,
        }


def candidates(cfg: Mapping[str, Any]) -> list[Candidate]:
    contract = cfg["model_contract"]
    output: list[Candidate] = []
    for rank in map(int, contract["pca_ranks"]):
        for ridge in map(float, contract["kernel_ridges"]):
            output.append(Candidate("linear", rank, 0.0, ridge))
        for multiplier in map(float, contract["rbf_median_distance_multipliers"]):
            for ridge in map(float, contract["kernel_ridges"]):
                output.append(Candidate("rbf", rank, multiplier, ridge))
    if len(output) != int(contract["candidate_count"]):
        raise ValueError("R8R3 candidate coverage changed")
    return output


def causal_feature(
    visible: Sequence[Sequence[float]],
    actions: Sequence[Sequence[float]],
    currents_a_tsc: Sequence[Sequence[float]],
    target_offsets: Sequence[float],
    origin_task_step: int,
    cfg: Mapping[str, Any],
) -> Array:
    """Construct the frozen 353-value feature from causal values only."""

    bank = cfg["bank_contract"]
    contract = cfg["feature_contract"]
    origin = int(origin_task_step)
    state_offsets = np.asarray(contract["visible_state_offsets"], dtype=int)
    action_offsets = np.asarray(contract["issued_action_offsets"], dtype=int)
    current_offsets = np.asarray(contract["applied_current_offsets"], dtype=int)
    values = np.asarray(visible, dtype=float)
    issued = np.asarray(actions, dtype=float)
    currents = np.asarray(currents_a_tsc, dtype=float)
    target = np.asarray(target_offsets, dtype=float)
    if (
        tuple(state_offsets.tolist()) != tuple(range(-10, 1))
        or tuple(action_offsets.tolist()) != tuple(range(-10, 0))
        or tuple(current_offsets.tolist()) != tuple(range(-10, 1))
        or origin < int(bank["first_origin_task_step"])
        or values.ndim != 2
        or values.shape[1] != 5
        or origin >= len(values)
        or issued.ndim != 2
        or issued.shape[1] != int(bank["coil_count"])
        or origin > len(issued)
        or currents.ndim != 2
        or currents.shape[1] != int(bank["coil_count"])
        or origin >= len(currents)
        or target.shape != (3,)
    ):
        raise ValueError("R8R3 causal feature input invalid")
    target_scaled = target / np.asarray(bank["target_scales"], dtype=float)
    clock = (
        origin - int(contract["relative_clock_origin"])
    ) / float(contract["relative_clock_scale"])
    feature = np.concatenate(
        (
            values[origin + state_offsets].reshape(-1),
            issued[origin + action_offsets].reshape(-1),
            currents[origin + current_offsets].reshape(-1),
            target_scaled,
            [clock],
        )
    )
    if (
        feature.shape != (int(bank["feature_dimension"]),)
        or not np.all(np.isfinite(feature))
    ):
        raise ValueError("R8R3 causal feature changed")
    return feature


def target_delta(visible: Sequence[Sequence[float]], origin_task_step: int, cfg: Mapping[str, Any]) -> Array:
    values = np.asarray(visible, dtype=float)
    origin = int(origin_task_step)
    count = int(cfg["bank_contract"]["future_state_count"])
    if values.ndim != 2 or values.shape[1] != 5 or origin + count >= len(values):
        raise ValueError("R8R3 target coverage invalid")
    output = values[origin + 1 : origin + count + 1, 2:5] - values[origin, 2:5]
    if output.shape != (count, 3) or not np.all(np.isfinite(output)):
        raise ValueError("R8R3 target delta invalid")
    return output


def forecast_from_delta(item: Mapping[str, Any], delta: Sequence[Sequence[float]], cfg: Mapping[str, Any]) -> Array:
    count = int(cfg["bank_contract"]["future_state_count"])
    change = np.asarray(delta, dtype=float)
    origin = np.asarray(item["origin_visible"], dtype=float)
    if change.shape != (count, 3) or origin.shape != (5,):
        raise ValueError("R8R3 forecast reconstruction input invalid")
    output = np.zeros((count, 5), dtype=float)
    output[:, 2:5] = origin[2:5] + change
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = origin[0] + np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = origin[1] + np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    if not np.all(np.isfinite(output)):
        raise ValueError("R8R3 forecast is non-finite")
    return output


def _canonical_components(components: Array) -> Array:
    output = np.asarray(components, dtype=float).copy()
    for row in output:
        index = int(np.argmax(np.abs(row)))
        if row[index] < 0.0:
            row *= -1.0
    return output


def _preprocessor(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Array]:
    values = np.asarray([item["feature"] for item in items], dtype=float)
    floor = float(cfg["model_contract"]["standard_deviation_floor"])
    if values.ndim != 2 or len(values) == 0 or not np.all(np.isfinite(values)):
        raise ValueError("R8R3 feature matrix invalid")
    mean = values.mean(axis=0)
    scale = np.maximum(values.std(axis=0), floor)
    _, _, vt = np.linalg.svd((values - mean) / scale, full_matrices=False)
    components = _canonical_components(vt)
    maximum_rank = max(map(int, cfg["model_contract"]["pca_ranks"]))
    if len(components) < maximum_rank:
        raise ValueError("R8R3 PCA rank unavailable")
    return {"mean": mean, "scale": scale, "components": components}


def _project(preprocessor: Mapping[str, Array], items: Sequence[Mapping[str, Any]], rank: int) -> Array:
    values = np.asarray([item["feature"] for item in items], dtype=float)
    return ((values - preprocessor["mean"]) / preprocessor["scale"]) @ preprocessor[
        "components"
    ][:rank].T


def _targets(items: Sequence[Mapping[str, Any]]) -> Array:
    values = np.asarray([item["target_delta"] for item in items], dtype=float)
    if values.ndim != 3 or values.shape[1:] != (12, 3) or not np.all(np.isfinite(values)):
        raise ValueError("R8R3 training target matrix invalid")
    return values.reshape(len(values), -1)


def _median_distance(values: Array, floor: float) -> float:
    delta = values[:, None, :] - values[None, :, :]
    distance = np.sqrt(np.sum(delta * delta, axis=2))
    upper = distance[np.triu_indices(len(values), 1)]
    positive = upper[upper > floor]
    return max(float(np.median(positive)) if len(positive) else floor, floor)


def _rbf(left: Array, right: Array, bandwidth: float) -> Array:
    delta = left[:, None, :] - right[None, :, :]
    return np.exp(-0.5 * np.sum(delta * delta, axis=2) / (bandwidth * bandwidth))


def _eigen_alpha(gram: Array, centered_target: Array, ridge: float) -> Array:
    values, vectors = np.linalg.eigh(0.5 * (gram + gram.T))
    denominator = values + ridge
    if np.any(denominator <= 0.0):
        raise ValueError("R8R3 kernel system is not positive")
    return vectors @ ((vectors.T @ centered_target) / denominator[:, None])


def predict_candidate_set(
    training: Sequence[Mapping[str, Any]],
    held: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> dict[str, list[Array]]:
    """Fit all frozen candidates once per preprocessing/kernel group."""

    preprocessor = _preprocessor(training, cfg)
    target = _targets(training)
    target_mean = target.mean(axis=0)
    centered = target - target_mean
    output: dict[str, list[Array]] = {}
    contract = cfg["model_contract"]
    floor = float(contract["bandwidth_floor"])
    ridges = tuple(map(float, contract["kernel_ridges"]))
    for rank in map(int, contract["pca_ranks"]):
        train_x = _project(preprocessor, training, rank)
        held_x = _project(preprocessor, held, rank)
        linear_left = train_x.T @ train_x / rank
        linear_right = train_x.T @ centered / rank
        for ridge in ridges:
            beta = np.linalg.lstsq(
                linear_left + ridge * np.eye(rank), linear_right, rcond=None
            )[0]
            flat = target_mean + held_x @ beta
            candidate = Candidate("linear", rank, 0.0, ridge)
            output[candidate.key] = [
                forecast_from_delta(item, row.reshape(12, 3), cfg)
                for item, row in zip(held, flat)
            ]
        median = _median_distance(train_x, floor)
        for multiplier in map(float, contract["rbf_median_distance_multipliers"]):
            bandwidth = max(multiplier * median, floor)
            gram = _rbf(train_x, train_x, bandwidth)
            held_kernel = _rbf(held_x, train_x, bandwidth)
            values, vectors = np.linalg.eigh(0.5 * (gram + gram.T))
            projected_target = vectors.T @ centered
            for ridge in ridges:
                denominator = values + ridge
                if np.any(denominator <= 0.0):
                    raise ValueError("R8R3 kernel system is not positive")
                alpha = vectors @ (projected_target / denominator[:, None])
                flat = target_mean + held_kernel @ alpha
                candidate = Candidate("rbf", rank, multiplier, ridge)
                output[candidate.key] = [
                    forecast_from_delta(item, row.reshape(12, 3), cfg)
                    for item, row in zip(held, flat)
                ]
    expected = {candidate.key for candidate in candidates(cfg)}
    if set(output) != expected:
        raise ValueError("R8R3 candidate prediction coverage changed")
    return output


def fit_model(
    items: Sequence[Mapping[str, Any]], candidate: Candidate, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    preprocessor = _preprocessor(items, cfg)
    x = _project(preprocessor, items, candidate.pca_rank)
    target = _targets(items)
    target_mean = target.mean(axis=0)
    centered = target - target_mean
    model: dict[str, Any] = {
        "candidate": candidate,
        "preprocessor": preprocessor,
        "training_x": x,
        "target_mean": target_mean,
    }
    if candidate.family == "linear":
        left = x.T @ x / candidate.pca_rank
        right = x.T @ centered / candidate.pca_rank
        model["beta"] = np.linalg.lstsq(
            left + candidate.ridge * np.eye(candidate.pca_rank), right, rcond=None
        )[0]
        model["bandwidth"] = 0.0
    elif candidate.family == "rbf":
        bandwidth = max(
            candidate.bandwidth_multiplier
            * _median_distance(x, float(cfg["model_contract"]["bandwidth_floor"])),
            float(cfg["model_contract"]["bandwidth_floor"]),
        )
        gram = _rbf(x, x, bandwidth)
        model["alpha"] = _eigen_alpha(gram, centered, candidate.ridge)
        model["bandwidth"] = bandwidth
    else:
        raise ValueError("R8R3 kernel family changed")
    return model


def predict_model(model: Mapping[str, Any], items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[Array]:
    candidate: Candidate = model["candidate"]
    x = _project(model["preprocessor"], items, candidate.pca_rank)
    if candidate.family == "linear":
        flat = model["target_mean"] + x @ model["beta"]
    else:
        flat = model["target_mean"] + _rbf(
            x, model["training_x"], float(model["bandwidth"])
        ) @ model["alpha"]
    return [
        forecast_from_delta(item, row.reshape(12, 3), cfg)
        for item, row in zip(items, flat)
    ]


def prediction_row(item: Mapping[str, Any], prediction: Sequence[Sequence[float]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    predicted = np.asarray(prediction, dtype=float)
    target = np.asarray(item["future_visible"], dtype=float)
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    caps = np.asarray(cfg["gates"]["component_caps_physical"], dtype=float)
    if predicted.shape != (12, 5) or target.shape != (12, 5):
        raise ValueError("R8R3 prediction row shape changed")
    residual_scaled = predicted - target
    residual_physical = residual_scaled * scales
    absolute_physical = np.abs(residual_physical)
    violations = absolute_physical > caps[None, :] + 1e-15
    return {
        "row_id": str(item["row_id"]),
        "pair_id": str(item["pair_id"]),
        "history_member": str(item["history_member"]),
        "origin_task_step": int(item["origin_task_step"]),
        "prescribed_issue": bool(item["prescribed_issue"]),
        "predicted_visible": predicted.tolist(),
        "target_visible": target.tolist(),
        "absolute_residual_physical": absolute_physical.tolist(),
        "component_future_violation_count": int(np.sum(violations)),
        "component_violation_counts": np.sum(violations, axis=0).astype(int).tolist(),
        "maximum_absolute_scaled_point_error": float(np.max(np.abs(residual_scaled))),
        "mean_squared_scaled_error": float(np.mean(residual_scaled * residual_scaled)),
        "passed": bool(not np.any(violations) and np.all(np.isfinite(predicted))),
    }


def _family_order(candidate: Candidate) -> int:
    return 0 if candidate.family == "linear" else 1


def _score(rows: Sequence[Mapping[str, Any]], candidate: Candidate) -> tuple[Any, ...]:
    maxima = np.asarray([row["maximum_absolute_scaled_point_error"] for row in rows], dtype=float)
    return (
        sum(not bool(row["passed"]) for row in rows),
        sum(int(row["component_future_violation_count"]) for row in rows),
        float(np.max(maxima)),
        float(np.quantile(maxima, 0.95, method="linear")),
        float(np.mean([row["mean_squared_scaled_error"] for row in rows])),
        _family_order(candidate),
        candidate.pca_rank,
        candidate.bandwidth_multiplier,
        candidate.ridge,
    )


def select_candidate(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[Candidate, list[dict[str, Any]], list[dict[str, Any]]]:
    candidate_rows: dict[str, list[dict[str, Any]]] = {
        candidate.key: [] for candidate in candidates(cfg)
    }
    pairs = sorted({str(item["pair_id"]) for item in items})
    for pair in pairs:
        training = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        predictions = predict_candidate_set(training, held, cfg)
        for candidate in candidates(cfg):
            candidate_rows[candidate.key].extend(
                prediction_row(item, prediction, cfg)
                for item, prediction in zip(held, predictions[candidate.key])
            )
    scored = []
    for candidate in candidates(cfg):
        rows = sorted(candidate_rows[candidate.key], key=lambda row: row["row_id"])
        scored.append((candidate, _score(rows, candidate), rows))
    selected, _, selected_rows = min(scored, key=lambda item: item[1])
    report = [
        {"candidate": candidate.as_dict(), "selection_score": list(score[:5])}
        for candidate, score, _ in scored
    ]
    return selected, report, selected_rows


def tube_from_rows(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> Array:
    residual = np.asarray([row["absolute_residual_physical"] for row in rows], dtype=float)
    floor = np.asarray(cfg["tube_contract"]["component_floor_physical"], dtype=float)
    multiplier = float(cfg["tube_contract"]["inner_residual_multiplier"])
    if residual.ndim != 3 or residual.shape[1:] != (12, 5):
        raise ValueError("R8R3 tube residual shape changed")
    tube = multiplier * np.max(residual, axis=0) + floor[None, :]
    if not np.all(np.isfinite(tube)):
        raise ValueError("R8R3 tube is non-finite")
    return tube


def nested_outer_predictions(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    caps = np.asarray(cfg["gates"]["component_caps_physical"], dtype=float)
    pairs = sorted({str(item["pair_id"]) for item in items})
    for pair in pairs:
        training = [item for item in items if str(item["pair_id"]) != pair]
        held = [item for item in items if str(item["pair_id"]) == pair]
        selected, scores, inner_rows = select_candidate(training, cfg)
        tube = tube_from_rows(inner_rows, cfg)
        tube_cap_passed = bool(np.all(tube <= caps[None, :] + 1e-15))
        model = fit_model(training, selected, cfg)
        held_rows = [
            prediction_row(item, prediction, cfg)
            for item, prediction in zip(held, predict_model(model, held, cfg))
        ]
        contained = 0
        for row in held_rows:
            value = np.asarray(row["absolute_residual_physical"], dtype=float)
            row["tube_contained"] = bool(np.all(value <= tube + 1e-15))
            contained += int(row["tube_contained"])
        rows.extend(held_rows)
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": len(pairs) - 1,
                "training_origin_row_count": len(training),
                "held_origin_row_count": len(held),
                "selected_candidate": selected.as_dict(),
                "inner_candidate_scores": scores,
                "tube_physical": tube.tolist(),
                "tube_cap_passed": tube_cap_passed,
                "held_tube_contained_count": contained,
                "passed": bool(
                    tube_cap_passed
                    and contained == len(held_rows)
                    and all(row["passed"] for row in held_rows)
                ),
            }
        )
    return sorted(rows, key=lambda row: row["row_id"]), folds


def evaluate_outer(rows: Sequence[Mapping[str, Any]], folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = cfg["gates"]
    issues = [row for row in rows if bool(row["prescribed_issue"])]
    component_counts = np.sum(
        np.asarray([row["component_violation_counts"] for row in rows], dtype=int), axis=0
    ).astype(int).tolist()
    result = {
        "outer_fold_count": len(folds),
        "origin_row_count": len(rows),
        "origin_pass_count": sum(bool(row["passed"]) for row in rows),
        "prescribed_issue_row_count": len(issues),
        "prescribed_issue_pass_count": sum(bool(row["passed"]) for row in issues),
        "tube_cap_fold_count": sum(bool(fold["tube_cap_passed"]) for fold in folds),
        "tube_contained_origin_count": sum(bool(row["tube_contained"]) for row in rows),
        "component_violation_counts": component_counts,
        "maximum_absolute_scaled_point_error": max(
            float(row["maximum_absolute_scaled_point_error"]) for row in rows
        ),
        "maximum_absolute_physical_error": np.max(
            np.asarray([row["absolute_residual_physical"] for row in rows]), axis=(0, 1)
        ).tolist(),
        "pair_pass_counts": {
            pair: {
                "passed": sum(bool(row["passed"]) for row in rows if row["pair_id"] == pair),
                "total": sum(row["pair_id"] == pair for row in rows),
            }
            for pair in sorted({str(row["pair_id"]) for row in rows})
        },
        "history_pass_counts": {
            history: {
                "passed": sum(bool(row["passed"]) for row in rows if row["history_member"] == history),
                "total": sum(row["history_member"] == history for row in rows),
            }
            for history in sorted({str(row["history_member"]) for row in rows})
        },
    }
    result["passed"] = bool(
        result["outer_fold_count"] == int(gates["required_outer_fold_count"])
        and result["origin_row_count"] == int(gates["required_outer_origin_row_count"])
        and result["origin_pass_count"] == int(gates["required_origin_pass_count"])
        and result["prescribed_issue_row_count"]
        == int(gates["required_prescribed_issue_row_count"])
        and result["prescribed_issue_pass_count"]
        == int(gates["required_prescribed_issue_pass_count"])
        and result["tube_cap_fold_count"] == int(gates["required_tube_cap_fold_count"])
        and result["tube_contained_origin_count"]
        == int(gates["required_tube_contained_origin_count"])
        and all(fold["passed"] for fold in folds)
    )
    return result


def serializable_model(model: Mapping[str, Any], tube: Array) -> dict[str, Any]:
    candidate: Candidate = model["candidate"]
    output = {
        "candidate": candidate.as_dict(),
        "preprocessor": {
            key: np.asarray(value).tolist() for key, value in model["preprocessor"].items()
        },
        "training_x": np.asarray(model["training_x"]).tolist(),
        "target_mean": np.asarray(model["target_mean"]).tolist(),
        "bandwidth": float(model["bandwidth"]),
        "tube_physical": np.asarray(tube).tolist(),
    }
    if candidate.family == "linear":
        output["beta"] = np.asarray(model["beta"]).tolist()
    else:
        output["alpha"] = np.asarray(model["alpha"]).tolist()
    return output
