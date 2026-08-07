"""Pure prediction, scoring, and Card15 construction for the R8R8 MPC core."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import action_conditioned_history_response_model as response_model
from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s13_recurrent_sequence_tube_identification as s13,
    stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign as s21,
    stage4_2r3c3t13s9_unified_postqueue_q1_identification as s9,
)


N_COILS = 14


@dataclass(frozen=True)
class Candidate:
    name: str
    direction_index: int
    sign: int
    action_scale: float

    @property
    def is_zero(self) -> bool:
        return self.direction_index < 0


def candidates(cfg: Mapping[str, Any]) -> tuple[Candidate, ...]:
    rows = tuple(
        Candidate(
            str(row["name"]),
            int(row["direction_index"]),
            int(row["sign"]),
            float(row["action_scale"]),
        )
        for row in cfg["candidate_contract"]["ordered_candidates"]
    )
    if (
        len(rows) != 9
        or not rows[0].is_zero
        or any(row.is_zero for row in rows[1:])
        or {(row.direction_index, row.sign) for row in rows[1:]}
        != {(direction, sign) for direction in range(4) for sign in (-1, 1)}
    ):
        raise ValueError("R8R8 candidate set changed")
    return rows


def observer_model_from_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    model = value["model"]
    candidate = observer.Candidate(**model["candidate"])
    output: dict[str, Any] = {
        "candidate": candidate,
        "preprocessor": {
            key: np.asarray(item, dtype=float)
            for key, item in model["preprocessor"].items()
        },
        "training_x": np.asarray(model["training_x"], dtype=float),
        "target_mean": np.asarray(model["target_mean"], dtype=float),
        "bandwidth": float(model["bandwidth"]),
    }
    key = "beta" if candidate.family == "linear" else "alpha"
    output[key] = np.asarray(model[key], dtype=float)
    return output


def response_model_from_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    model = value["model"]
    return {
        "candidate": response_model.Candidate(**model["candidate"]),
        "preprocessor": {
            key: np.asarray(item, dtype=float)
            for key, item in model["preprocessor"].items()
        },
        "heads": {
            key: {
                "amplitude_mean": float(head["amplitude_mean"]),
                "amplitude_scale": float(head["amplitude_scale"]),
                "lags": [
                    {
                        "lag": int(row["lag"]),
                        "x": np.asarray(row["x"], dtype=float),
                        "bandwidth": float(row["bandwidth"]),
                        "y_mean": np.asarray(row["y_mean"], dtype=float),
                        "alpha": np.asarray(row["alpha"], dtype=float),
                    }
                    for row in head["lags"]
                ],
            }
            for key, head in model["heads"].items()
        },
    }


def visible_history(
    states: Sequence[Mapping[str, Any]], scales: Sequence[float]
) -> np.ndarray:
    if len(states) < 2:
        raise ValueError("R8R8 needs two states to reconstruct causal velocity")
    rows = []
    for index, state in enumerate(states):
        other = states[1] if index == 0 else states[index - 1]
        sign = 1.0 if index == 0 else -1.0
        v_r = sign * (float(other["R"]) - float(state["R"])) / 0.01
        v_z = sign * (float(other["Z"]) - float(state["Z"])) / 0.01
        rows.append([float(state["R"]), float(state["Z"]), v_r, v_z, float(state["Ip"])])
    output = np.asarray(rows, dtype=float) / np.asarray(scales, dtype=float)
    if output.shape != (len(states), 5) or not np.all(np.isfinite(output)):
        raise ValueError("R8R8 causal visible history invalid")
    return output


def response_descriptor(
    visible: np.ndarray,
    target_offsets: Sequence[float],
    origin: int,
    r8r7_cfg: Mapping[str, Any],
) -> np.ndarray:
    offsets = tuple(map(int, r8r7_cfg["bank_contract"]["history_offsets"]))
    history = visible[[max(0, origin - offset) for offset in offsets]].reshape(-1)
    availability = np.asarray([float(offset <= origin) for offset in offsets])
    target = np.asarray(target_offsets, dtype=float) / np.asarray(
        r8r7_cfg["bank_contract"]["target_scales"], dtype=float
    )
    descriptor = np.concatenate((history, availability, target, [(origin - 10.0) / 12.0]))
    if descriptor.shape != (
        int(r8r7_cfg["bank_contract"]["response_descriptor_dimension"]),
    ) or not np.all(np.isfinite(descriptor)):
        raise ValueError("R8R8 response descriptor changed")
    return descriptor


def robust_score(
    prediction_normalized: Sequence[Sequence[float]],
    tube_physical: Sequence[Sequence[float]],
    desired_physical: Sequence[float],
    objective_cfg: Mapping[str, Any],
) -> tuple[float, np.ndarray]:
    prediction = np.asarray(prediction_normalized, dtype=float)
    tube = np.asarray(tube_physical, dtype=float)
    scales = np.asarray(objective_cfg["physical_scales"], dtype=float)
    component = np.asarray(objective_cfg["component_weights"], dtype=float)
    lag = np.asarray(objective_cfg["lag_weights"], dtype=float)
    desired = np.asarray(desired_physical, dtype=float)
    if (
        prediction.shape != (4, 5)
        or tube.shape != (4, 5)
        or desired.shape != (5,)
        or scales.shape != component.shape != (5,)
        or lag.shape != (4,)
    ):
        raise ValueError("R8R8 robust objective shape changed")
    upper = np.abs(prediction * scales[None, :] - desired[None, :]) + tube
    normalized = upper / scales[None, :]
    score = float(np.sum(lag[:, None] * component[None, :] * np.square(normalized)))
    if not math.isfinite(score) or not np.all(np.isfinite(upper)):
        raise ValueError("R8R8 robust objective is non-finite")
    return score, upper


def predict_candidates(
    *,
    states: Sequence[Mapping[str, Any]],
    actions: Sequence[Sequence[float]],
    target_offsets: Sequence[float],
    static_model: Mapping[str, Any],
    action_model: Mapping[str, Any],
    static_tube_physical: Sequence[Sequence[float]],
    combined_tube_physical: Sequence[Sequence[float]],
    observer_cfg: Mapping[str, Any],
    response_cfg: Mapping[str, Any],
    r8r7_cfg: Mapping[str, Any],
    r8r8_cfg: Mapping[str, Any],
) -> list[dict[str, Any]]:
    origin = len(states) - 1
    if origin not in tuple(map(int, r8r8_cfg["rollout_contract"]["decision_task_steps"])):
        raise ValueError("R8R8 prediction called outside a decision origin")
    visible_scales = np.asarray(r8r7_cfg["bank_contract"]["visible_scales"], dtype=float)
    visible = visible_history(states, visible_scales)
    issued = np.asarray(actions, dtype=float)
    currents = np.asarray([row["currents_a_tsc"] for row in states], dtype=float)
    if issued.shape != (origin, N_COILS) or currents.shape != (origin + 1, N_COILS):
        raise ValueError("R8R8 causal action/current history changed")
    feature = observer.causal_feature(
        visible,
        issued,
        currents,
        target_offsets,
        origin,
        observer_cfg,
    )
    static_item = {
        "feature": feature,
        "origin_visible": visible[origin],
    }
    static_prediction = observer.predict_model(
        static_model, [static_item], observer_cfg
    )[0][:4]
    descriptor = response_descriptor(visible, target_offsets, origin, r8r7_cfg)
    base_target = np.asarray(r8r8_cfg["objective_contract"]["base_target_physical"], dtype=float)
    offset = np.asarray(target_offsets, dtype=float)
    desired = np.asarray(
        [base_target[0] + offset[0], base_target[1] + offset[1], 0.0, 0.0, base_target[2] + offset[2]],
        dtype=float,
    )
    static_tube = np.asarray(static_tube_physical, dtype=float)[:4]
    combined_tube = np.asarray(combined_tube_physical, dtype=float)
    if static_tube.shape != (4, 5) or combined_tube.shape != (4, 5):
        raise ValueError("R8R8 tube shape changed")
    rows = []
    for order, candidate in enumerate(candidates(r8r8_cfg)):
        response = np.zeros((4, 5), dtype=float)
        tube = static_tube
        if not candidate.is_zero:
            item = {
                "sign": candidate.sign,
                "direction_index": candidate.direction_index,
                "action_scale": candidate.action_scale,
                "descriptor": descriptor,
                "response": np.zeros((4, 5), dtype=float),
            }
            response = response_model.predict_item(action_model, item, response_cfg)
            tube = combined_tube
        prediction = static_prediction + response
        score, robust_upper = robust_score(
            prediction, tube, desired, r8r8_cfg["objective_contract"]
        )
        rows.append(
            {
                "order": order,
                "name": candidate.name,
                "direction_index": candidate.direction_index,
                "sign": candidate.sign,
                "action_scale": candidate.action_scale,
                "static_prediction": static_prediction.tolist(),
                "response_prediction": response.tolist(),
                "combined_prediction": prediction.tolist(),
                "tube_physical": tube.tolist(),
                "robust_upper_physical": robust_upper.tolist(),
                "score": score,
                "causal_feature_sha256": hashlib.sha256(
                    np.asarray(feature, dtype="<f8").tobytes(order="C")
                ).hexdigest(),
                "response_descriptor_sha256": hashlib.sha256(
                    np.asarray(descriptor, dtype="<f8").tobytes(order="C")
                ).hexdigest(),
            }
        )
    if len(rows) != 9:
        raise ValueError("R8R8 candidate forecast coverage changed")
    return rows


def select_candidate(
    forecast_rows: Sequence[Mapping[str, Any]],
    eligible_nonzero_names: Sequence[str],
    required_ratio: float,
) -> dict[str, Any]:
    rows = [copy.deepcopy(dict(row)) for row in forecast_rows]
    expected_names = (
        "zero",
        "direction0_minus",
        "direction0_plus",
        "direction1_minus",
        "direction1_plus",
        "direction2_minus",
        "direction2_plus",
        "direction3_minus",
        "direction3_plus",
    )
    if (
        len(rows) != 9
        or tuple(str(row.get("name")) for row in rows) != expected_names
        or tuple(int(row.get("order", -1)) for row in rows) != tuple(range(9))
    ):
        raise ValueError("R8R8 selection candidate order changed")
    scores = tuple(float(row["score"]) for row in rows)
    if (
        not math.isfinite(float(required_ratio))
        or not 0.0 < float(required_ratio) <= 1.0
        or not all(math.isfinite(score) for score in scores)
    ):
        raise ValueError("R8R8 selection score or ratio is non-finite")
    zero_score = float(rows[0]["score"])
    eligible = set(map(str, eligible_nonzero_names))
    if not eligible.issubset(set(expected_names[1:])):
        raise ValueError("R8R8 selection received an unknown eligible candidate")
    nonzero = [row for row in rows[1:] if str(row["name"]) in eligible]
    best = min(nonzero, key=lambda row: (float(row["score"]), int(row["order"]))) if nonzero else None
    selected = rows[0]
    if best is not None and float(best["score"]) <= float(required_ratio) * zero_score:
        selected = best
    score = float(selected["score"])
    improvement = 0.0 if zero_score <= 0.0 else (zero_score - score) / zero_score
    return {
        "selected_name": str(selected["name"]),
        "selected_order": int(selected["order"]),
        "selected_direction_index": int(selected["direction_index"]),
        "selected_sign": int(selected["sign"]),
        "selected_score": score,
        "zero_score": zero_score,
        "robust_improvement_fraction": improvement,
        "nonzero_selected": str(selected["name"]) != "zero",
        "eligible_nonzero_names": sorted(eligible),
    }


def actuator_from_payload(
    payload: Mapping[str, Any], lattice_cfg: Mapping[str, Any]
) -> QuantizedActuatorModel:
    minimum, maximum = s13._current_limits_tsc(payload)
    turns = s13._turns_tsc(payload)
    return QuantizedActuatorModel(
        minimum_current_a_tsc=tuple(map(float, minimum)),
        maximum_current_a_tsc=tuple(map(float, maximum)),
        max_slew_step_a=float(payload["max_delta_a"]),
        turns_tsc=tuple(map(float, turns)),
        bias_grid_units_tsc=tuple(map(float, lattice_cfg["readback_bias_grid_units_tsc"])),
        uncertainty_radius_grid_units_tsc=tuple(
            map(float, lattice_cfg["readback_radius_grid_units_tsc"])
        ),
    )


def construct_issue(
    *,
    task_step: int,
    currents_a_tsc: Sequence[float],
    fixed_basis_delta_field_kat_tsc: Sequence[Sequence[float]],
    candidate: Candidate,
    canonical_matrix_columns: Sequence[Sequence[float]],
    actuator: QuantizedActuatorModel,
    controller_cfg: Mapping[str, Any],
    lattice_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    if candidate.is_zero or candidate.sign not in (-1, 1) or candidate.direction_index not in range(4):
        raise ValueError("R8R8 pure issue requires a nonzero canonical candidate")
    currents = np.asarray(currents_a_tsc, dtype=float).reshape(N_COILS)
    field_basis = np.asarray(fixed_basis_delta_field_kat_tsc, dtype=float).reshape(4, N_COILS).T
    matrix = np.asarray(canonical_matrix_columns, dtype=float).reshape(4, 4)
    desired_coordinate = matrix[:, candidate.direction_index] * candidate.sign
    center = actuator.apply(currents, np.zeros(N_COILS, dtype=float))
    desired_field = field_basis @ desired_coordinate
    target_fields, actual_decimal, integer_counts = s21._dynamic_exact_target(
        center.card15_fields,
        tuple(Decimal(str(value)) for value in desired_field),
        search_radius=int(controller_cfg["dynamic_exact_search_radius"]),
    )
    chosen = s9.exact_stored_center_action(
        stored_fields=target_fields,
        measured_current_a_tsc=currents,
        baseline_action_norm_tsc=np.zeros(N_COILS, dtype=float),
        turns_tsc=actuator.turns_tsc,
        max_slew_step_a=actuator.max_slew_step_a,
        minimum_current_a_tsc=actuator.minimum_current_a_tsc,
        maximum_current_a_tsc=actuator.maximum_current_a_tsc,
        cfg=lattice_cfg,
    )
    issued = actuator.apply(currents, chosen["action_norm_tsc"])
    actual_field = np.asarray([float(value) for value in actual_decimal], dtype=float)
    turns = np.asarray(actuator.turns_tsc, dtype=float)
    actual_current = actual_field * 1000.0 / turns
    current_basis = field_basis * 1000.0 / turns[:, None]
    desired_current = current_basis @ desired_coordinate
    coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
    reconstructed = current_basis @ coordinate
    desired_norm = float(np.linalg.norm(desired_current))
    actual_norm = float(np.linalg.norm(actual_current))
    cosine = float(np.dot(desired_current, actual_current) / max(desired_norm * actual_norm, 1e-300))
    off_basis = float(np.linalg.norm(actual_current - reconstructed) / max(actual_norm, 1e-300))
    criteria = {
        "finite": bool(
            np.all(np.isfinite(coordinate))
            and np.all(np.isfinite(actual_field))
            and math.isfinite(cosine)
            and math.isfinite(off_basis)
        ),
        "requested_mixed_coordinate_exact": bool(
            np.array_equal(desired_coordinate, matrix[:, candidate.direction_index] * candidate.sign)
            and np.count_nonzero(desired_coordinate) == 4
        ),
        "center_exact": all(len(field) == 10 for field in center.card15_fields),
        "target_exact": all(len(field) == 10 for field in target_fields),
        "target_reproduction": list(issued.card15_fields) == list(target_fields),
        "no_saturation": not any(issued.action_saturated),
        "no_current_clip": not any(issued.current_limit_clipped),
        "incremental_action": float(chosen["incremental_normalized_action_linf"])
        <= float(controller_cfg["maximum_incremental_normalized_action_linf"]) + 1e-12,
        "total_action": float(chosen["total_normalized_action_abs"])
        <= float(controller_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
        "current_utilization": float(chosen["predicted_maximum_current_utilization"])
        <= float(controller_cfg["maximum_current_utilization"]) + 1e-12,
        "cosine": cosine >= float(controller_cfg["minimum_desired_applied_current_cosine"]) - 1e-12,
        "off_basis": off_basis <= float(controller_cfg["maximum_relative_off_basis_residual"]) + 1e-12,
        "actuator_gate": bool(chosen["passed"]),
    }
    event = {
        "event": "mpc_issue",
        "gate_revision": "r8r8_pure_exact_card15_candidate_v1",
        "task_step": int(task_step),
        "candidate_name": candidate.name,
        "slot": candidate.direction_index,
        "sign": candidate.sign,
        "requested_coordinate": desired_coordinate.tolist(),
        "actual_coordinate": coordinate.tolist(),
        "center_card15_fields": list(center.card15_fields),
        "target_card15_fields": list(target_fields),
        "integer_grid_steps_tsc": list(map(int, integer_counts)),
        "actual_signed_delta_field_kAt_tsc": actual_field.tolist(),
        "desired_applied_current_cosine": cosine,
        "relative_off_basis_residual": off_basis,
        "incremental_normalized_action_linf": float(chosen["incremental_normalized_action_linf"]),
        "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
        "predicted_current_utilization": float(chosen["predicted_maximum_current_utilization"]),
        "action_norm_tsc": list(map(float, chosen["action_norm_tsc"])),
        "nominal_issue_readback_current_a_tsc": list(issued.nominal_readback_current_a_tsc),
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "actuator_prediction": copy.deepcopy(chosen),
    }
    return event


def construct_cancel(
    *,
    task_step: int,
    currents_a_tsc: Sequence[float],
    issue_event: Mapping[str, Any],
    actuator: QuantizedActuatorModel,
    controller_cfg: Mapping[str, Any],
    lattice_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    currents = np.asarray(currents_a_tsc, dtype=float).reshape(N_COILS)
    stored_fields = tuple(map(str, issue_event["center_card15_fields"]))
    issue_target = tuple(map(str, issue_event["target_card15_fields"]))
    chosen = s9.exact_stored_center_action(
        stored_fields=stored_fields,
        measured_current_a_tsc=currents,
        baseline_action_norm_tsc=np.zeros(N_COILS, dtype=float),
        turns_tsc=actuator.turns_tsc,
        max_slew_step_a=actuator.max_slew_step_a,
        minimum_current_a_tsc=actuator.minimum_current_a_tsc,
        maximum_current_a_tsc=actuator.maximum_current_a_tsc,
        cfg=lattice_cfg,
    )
    cancelled = actuator.apply(currents, chosen["action_norm_tsc"])
    exact_zero = all(
        (s9._decimal_field(target) - s9._decimal_field(center))
        + (s9._decimal_field(center) - s9._decimal_field(target))
        == 0
        for center, target in zip(stored_fields, issue_target)
    )
    criteria = {
        "target_exact": list(cancelled.card15_fields) == list(stored_fields),
        "exact_fields": all(len(field) == 10 for field in stored_fields),
        "exact_zero_target_jump_net": exact_zero,
        "no_saturation": not any(cancelled.action_saturated),
        "no_current_clip": not any(cancelled.current_limit_clipped),
        "incremental_action": float(chosen["incremental_normalized_action_linf"])
        <= float(controller_cfg["maximum_incremental_normalized_action_linf"]) + 1e-12,
        "online_cancel_margin": float(chosen["incremental_normalized_action_linf"])
        <= float(controller_cfg["maximum_online_cancel_incremental_linf"]) + 1e-12,
        "total_action": float(chosen["total_normalized_action_abs"])
        <= float(controller_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
        "current_utilization": float(chosen["predicted_maximum_current_utilization"])
        <= float(controller_cfg["maximum_current_utilization"]) + 1e-12,
        "actuator_gate": bool(chosen["passed"]),
    }
    return {
        "event": "mpc_cancel",
        "gate_revision": "r8r8_pure_exact_card15_cancel_v1",
        "task_step": int(task_step),
        "candidate_name": str(issue_event["candidate_name"]),
        "slot": int(issue_event["slot"]),
        "sign": int(issue_event["sign"]),
        "stored_center_card15_fields": list(stored_fields),
        "issue_target_card15_fields": list(issue_target),
        "incremental_normalized_action_linf": float(chosen["incremental_normalized_action_linf"]),
        "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
        "predicted_current_utilization": float(chosen["predicted_maximum_current_utilization"]),
        "action_norm_tsc": list(map(float, chosen["action_norm_tsc"])),
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "actuator_prediction": copy.deepcopy(chosen),
    }


def value_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()
