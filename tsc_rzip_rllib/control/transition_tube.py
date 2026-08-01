"""Fail-closed multi-hypothesis affine transition tube contract."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .causal_observer import _reject_unknown


SUPPORT_ORDER = {
    "measured": 0,
    "interpolation": 1,
    "extrapolation": 2,
    "unsupported": 3,
}


def _matrix(values: Sequence[Sequence[float]], name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 2 or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite matrix")
    return result


def _vector(values: Sequence[float], length: int, name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.shape != (length,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain {length} finite values")
    return result


@dataclass(frozen=True)
class AdditiveResponseTube:
    lower: tuple[float, ...]
    upper: tuple[float, ...]
    provenance: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        lower = tuple(float(value) for value in self.lower)
        upper = tuple(float(value) for value in self.upper)
        if (
            not lower
            or len(lower) != len(upper)
            or not all(math.isfinite(value) for value in lower + upper)
            or any(lo > hi for lo, hi in zip(lower, upper))
        ):
            raise ValueError("additive response tube must be finite, nonempty, and ordered")
        provenance = tuple(sorted((str(key), str(value)) for key, value in self.provenance))
        if not provenance:
            raise ValueError("tube provenance is required")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True)
class AffineTransitionHypothesis:
    hypothesis_id: str
    state_matrix: tuple[tuple[float, ...], ...]
    action_matrix: tuple[tuple[float, ...], ...]
    offset: tuple[float, ...]
    interpolation_state_lower: tuple[float, ...]
    interpolation_state_upper: tuple[float, ...]
    interpolation_action_lower: tuple[float, ...]
    interpolation_action_upper: tuple[float, ...]
    extrapolation_state_lower: tuple[float, ...]
    extrapolation_state_upper: tuple[float, ...]
    extrapolation_action_lower: tuple[float, ...]
    extrapolation_action_upper: tuple[float, ...]
    measured_state_action_points: tuple[tuple[float, ...], ...]
    provenance: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id must be nonempty")
        a = _matrix(self.state_matrix, "state_matrix")
        b = _matrix(self.action_matrix, "action_matrix")
        if a.shape[0] != a.shape[1] or b.shape[0] != a.shape[0]:
            raise ValueError("incompatible affine transition matrix shapes")
        n_state, n_action = a.shape[0], b.shape[1]
        offset = _vector(self.offset, n_state, "offset")
        bounds = {
            "interpolation_state": (
                _vector(self.interpolation_state_lower, n_state, "interpolation_state_lower"),
                _vector(self.interpolation_state_upper, n_state, "interpolation_state_upper"),
            ),
            "interpolation_action": (
                _vector(self.interpolation_action_lower, n_action, "interpolation_action_lower"),
                _vector(self.interpolation_action_upper, n_action, "interpolation_action_upper"),
            ),
            "extrapolation_state": (
                _vector(self.extrapolation_state_lower, n_state, "extrapolation_state_lower"),
                _vector(self.extrapolation_state_upper, n_state, "extrapolation_state_upper"),
            ),
            "extrapolation_action": (
                _vector(self.extrapolation_action_lower, n_action, "extrapolation_action_lower"),
                _vector(self.extrapolation_action_upper, n_action, "extrapolation_action_upper"),
            ),
        }
        if any(np.any(lo > hi) for lo, hi in bounds.values()):
            raise ValueError("support lower bounds must not exceed upper bounds")
        if np.any(bounds["extrapolation_state"][0] > bounds["interpolation_state"][0]) or np.any(
            bounds["extrapolation_state"][1] < bounds["interpolation_state"][1]
        ):
            raise ValueError("state extrapolation bounds must contain interpolation bounds")
        if np.any(bounds["extrapolation_action"][0] > bounds["interpolation_action"][0]) or np.any(
            bounds["extrapolation_action"][1] < bounds["interpolation_action"][1]
        ):
            raise ValueError("action extrapolation bounds must contain interpolation bounds")
        points = tuple(tuple(float(value) for value in row) for row in self.measured_state_action_points)
        if any(len(row) != n_state + n_action or not all(math.isfinite(value) for value in row) for row in points):
            raise ValueError("measured points must concatenate one finite state and action")
        provenance = tuple(sorted((str(key), str(value)) for key, value in self.provenance))
        if not provenance:
            raise ValueError("hypothesis provenance is required")
        object.__setattr__(self, "state_matrix", tuple(tuple(float(x) for x in row) for row in a))
        object.__setattr__(self, "action_matrix", tuple(tuple(float(x) for x in row) for row in b))
        object.__setattr__(self, "offset", tuple(float(x) for x in offset))
        object.__setattr__(self, "interpolation_state_lower", tuple(float(x) for x in bounds["interpolation_state"][0]))
        object.__setattr__(self, "interpolation_state_upper", tuple(float(x) for x in bounds["interpolation_state"][1]))
        object.__setattr__(self, "interpolation_action_lower", tuple(float(x) for x in bounds["interpolation_action"][0]))
        object.__setattr__(self, "interpolation_action_upper", tuple(float(x) for x in bounds["interpolation_action"][1]))
        object.__setattr__(self, "extrapolation_state_lower", tuple(float(x) for x in bounds["extrapolation_state"][0]))
        object.__setattr__(self, "extrapolation_state_upper", tuple(float(x) for x in bounds["extrapolation_state"][1]))
        object.__setattr__(self, "extrapolation_action_lower", tuple(float(x) for x in bounds["extrapolation_action"][0]))
        object.__setattr__(self, "extrapolation_action_upper", tuple(float(x) for x in bounds["extrapolation_action"][1]))
        object.__setattr__(self, "measured_state_action_points", points)
        object.__setattr__(self, "provenance", provenance)

    @property
    def state_dimension(self) -> int:
        return len(self.offset)

    @property
    def action_dimension(self) -> int:
        return len(self.action_matrix[0])

    def support_class(self, state: np.ndarray, action: np.ndarray) -> str:
        joined = np.concatenate((state, action))
        if any(np.array_equal(joined, np.asarray(point)) for point in self.measured_state_action_points):
            return "measured"
        checks = (
            (
                "interpolation",
                self.interpolation_state_lower,
                self.interpolation_state_upper,
                self.interpolation_action_lower,
                self.interpolation_action_upper,
            ),
            (
                "extrapolation",
                self.extrapolation_state_lower,
                self.extrapolation_state_upper,
                self.extrapolation_action_lower,
                self.extrapolation_action_upper,
            ),
        )
        for label, state_lo, state_hi, action_lo, action_hi in checks:
            if (
                np.all(state >= np.asarray(state_lo))
                and np.all(state <= np.asarray(state_hi))
                and np.all(action >= np.asarray(action_lo))
                and np.all(action <= np.asarray(action_hi))
            ):
                return label
        return "unsupported"


@dataclass(frozen=True)
class TransitionPrediction:
    formal_task_start_step: int
    formal_task_steps: tuple[int, ...]
    nominal_trajectories: tuple[tuple[str, tuple[tuple[float, ...], ...]], ...]
    hypothesis_support_classes: tuple[tuple[str, str], ...]
    support_class: str
    lower: tuple[tuple[float, ...], ...]
    upper: tuple[tuple[float, ...], ...]
    model_provenance: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    actuator_provenance: tuple[tuple[str, str], ...]
    tube_provenance: tuple[tuple[str, str], ...]
    point_model_certified: bool = False
    robust_controller_authorized: bool = False

    def __post_init__(self) -> None:
        if self.point_model_certified or self.robust_controller_authorized:
            raise ValueError("T13S3 cannot certify a point model or authorize robust control")

    def to_dict(self) -> dict[str, Any]:
        return {
            "formal_task_start_step": self.formal_task_start_step,
            "formal_task_steps": list(self.formal_task_steps),
            "nominal_trajectories": {
                key: [list(row) for row in rows]
                for key, rows in self.nominal_trajectories
            },
            "hypothesis_support_classes": dict(self.hypothesis_support_classes),
            "support_class": self.support_class,
            "lower": [list(row) for row in self.lower],
            "upper": [list(row) for row in self.upper],
            "model_provenance": {
                key: dict(value) for key, value in self.model_provenance
            },
            "actuator_provenance": dict(self.actuator_provenance),
            "tube_provenance": dict(self.tube_provenance),
            "point_model_certified": False,
            "robust_controller_authorized": False,
        }


@dataclass(frozen=True)
class SetValuedTransitionModel:
    hypotheses: tuple[AffineTransitionHypothesis, ...]
    additive_tube: AdditiveResponseTube
    actuator_provenance: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        hypotheses = tuple(self.hypotheses)
        if not hypotheses:
            raise ValueError("empty transition hypothesis set is forbidden")
        if not all(isinstance(value, AffineTransitionHypothesis) for value in hypotheses):
            raise ValueError("all hypotheses must be AffineTransitionHypothesis objects")
        ids = [hypothesis.hypothesis_id for hypothesis in hypotheses]
        if len(set(ids)) != len(ids):
            raise ValueError("transition hypothesis identifiers must be unique")
        dimensions = {
            (hypothesis.state_dimension, hypothesis.action_dimension)
            for hypothesis in hypotheses
        }
        if len(dimensions) != 1:
            raise ValueError("all hypotheses must have the same dimensions")
        state_dimension = hypotheses[0].state_dimension
        if len(self.additive_tube.lower) != state_dimension:
            raise ValueError("additive tube dimension does not match state")
        provenance = tuple(sorted((str(key), str(value)) for key, value in self.actuator_provenance))
        if not provenance:
            raise ValueError("actuator provenance is required")
        object.__setattr__(self, "hypotheses", hypotheses)
        object.__setattr__(self, "actuator_provenance", provenance)

    def predict_from_mapping(self, payload: Mapping[str, Any]) -> TransitionPrediction:
        allowed = {"formal_task_step", "initial_state", "action_sequence"}
        _reject_unknown(payload, allowed, "transition query")
        missing = allowed - set(payload)
        if missing:
            raise ValueError(f"missing transition query fields: {sorted(missing)}")
        formal_step = payload["formal_task_step"]
        if not isinstance(formal_step, int) or formal_step < 0:
            raise ValueError("formal_task_step must be a nonnegative integer")
        n_state = self.hypotheses[0].state_dimension
        n_action = self.hypotheses[0].action_dimension
        initial = _vector(payload["initial_state"], n_state, "initial_state")
        actions = np.asarray(payload["action_sequence"], dtype=float)
        if actions.ndim != 2 or actions.shape[1] != n_action or actions.shape[0] == 0 or not np.all(np.isfinite(actions)):
            raise ValueError("action_sequence must be a nonempty finite matrix")

        nominal_rows: list[tuple[str, tuple[tuple[float, ...], ...]]] = []
        support_rows: list[tuple[str, str]] = []
        model_provenance = []
        all_lower = []
        all_upper = []
        tube_lower = np.asarray(self.additive_tube.lower)
        tube_upper = np.asarray(self.additive_tube.upper)
        for hypothesis in self.hypotheses:
            a = np.asarray(hypothesis.state_matrix)
            b = np.asarray(hypothesis.action_matrix)
            c = np.asarray(hypothesis.offset)
            nominal = initial.copy()
            interval_lower = initial.copy()
            interval_upper = initial.copy()
            trajectory = []
            lower_trajectory = []
            upper_trajectory = []
            support = "measured"
            for action in actions:
                step_support = hypothesis.support_class(nominal, action)
                support = max((support, step_support), key=lambda value: SUPPORT_ORDER[value])
                if step_support == "unsupported":
                    raise ValueError(
                        f"unsupported transition query for hypothesis {hypothesis.hypothesis_id}"
                    )
                nominal = a @ nominal + b @ action + c
                positive = np.maximum(a, 0.0)
                negative = np.minimum(a, 0.0)
                next_lower = positive @ interval_lower + negative @ interval_upper + b @ action + c + tube_lower
                next_upper = positive @ interval_upper + negative @ interval_lower + b @ action + c + tube_upper
                interval_lower, interval_upper = next_lower, next_upper
                trajectory.append(tuple(float(value) for value in nominal))
                lower_trajectory.append(interval_lower.copy())
                upper_trajectory.append(interval_upper.copy())
            nominal_rows.append((hypothesis.hypothesis_id, tuple(trajectory)))
            support_rows.append((hypothesis.hypothesis_id, support))
            model_provenance.append((hypothesis.hypothesis_id, hypothesis.provenance))
            all_lower.append(np.asarray(lower_trajectory))
            all_upper.append(np.asarray(upper_trajectory))
        union_lower = np.min(np.asarray(all_lower), axis=0)
        union_upper = np.max(np.asarray(all_upper), axis=0)
        overall_support = max(
            (value for _, value in support_rows), key=lambda value: SUPPORT_ORDER[value]
        )
        return TransitionPrediction(
            formal_task_start_step=formal_step,
            formal_task_steps=tuple(formal_step + index + 1 for index in range(len(actions))),
            nominal_trajectories=tuple(nominal_rows),
            hypothesis_support_classes=tuple(support_rows),
            support_class=overall_support,
            lower=tuple(tuple(float(value) for value in row) for row in union_lower),
            upper=tuple(tuple(float(value) for value in row) for row in union_upper),
            model_provenance=tuple(model_provenance),
            actuator_provenance=self.actuator_provenance,
            tube_provenance=self.additive_tube.provenance,
        )
