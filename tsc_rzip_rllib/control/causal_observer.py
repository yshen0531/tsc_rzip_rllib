"""Immutable causal restart-state schema for restart MPC development."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any, Mapping, Sequence

from .quantized_actuator import N_COILS, _finite_tuple


FORBIDDEN_FIELD_FRAGMENTS = (
    "pair",
    "history",
    "prefix",
    "source_action",
    "source_result",
    "source_current",
    "wire_current",
    "vessel_current",
    "future",
    "schedule",
    "nearest_r17_phase",
)


def _vector_or_none(values: Any, length: int, name: str) -> tuple[float, ...] | None:
    if values is None:
        return None
    return _finite_tuple(values, length, name)


def _rows(values: Sequence[Sequence[float]], width: int, name: str) -> tuple[tuple[float, ...], ...]:
    return tuple(_finite_tuple(row, width, f"{name}[{index}]") for index, row in enumerate(values))


def _reject_unknown(payload: Mapping[str, Any], allowed: set[str], context: str) -> None:
    keys = {str(key) for key in payload}
    forbidden = sorted(
        key
        for key in keys - allowed
        if any(fragment in key.lower() for fragment in FORBIDDEN_FIELD_FRAGMENTS)
    )
    if forbidden:
        raise ValueError(f"forbidden {context} fields: {forbidden}")
    unknown = sorted(keys - allowed)
    if unknown:
        raise ValueError(f"unknown {context} fields: {unknown}")


@dataclass(frozen=True)
class VelocityEstimate:
    value_mps: tuple[float, float]
    lower_mps: tuple[float, float]
    upper_mps: tuple[float, float]
    status: str

    def __post_init__(self) -> None:
        value = _finite_tuple(self.value_mps, 2, "velocity.value_mps")
        lower = _finite_tuple(self.lower_mps, 2, "velocity.lower_mps")
        upper = _finite_tuple(self.upper_mps, 2, "velocity.upper_mps")
        if self.status not in {"unknown_interval", "finite_difference"}:
            raise ValueError("invalid velocity status")
        if any(lo > val or val > hi for lo, val, hi in zip(lower, value, upper)):
            raise ValueError("velocity value must be contained in its interval")
        if any(lo == hi for lo, hi in zip(lower, upper)):
            raise ValueError("velocity uncertainty must be nonzero")
        object.__setattr__(self, "value_mps", value)
        object.__setattr__(self, "lower_mps", lower)
        object.__setattr__(self, "upper_mps", upper)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value_mps": list(self.value_mps),
            "lower_mps": list(self.lower_mps),
            "upper_mps": list(self.upper_mps),
            "status": self.status,
        }


@dataclass(frozen=True)
class CausalRestartObserverState:
    formal_task_step: int
    target_rzip: tuple[float, float, float]
    measurement_history_rzip: tuple[tuple[float, float, float], ...]
    velocity: VelocityEstimate
    measured_coil_current_a_tsc: tuple[float, ...]
    issued_commands_norm_tsc: tuple[tuple[float, ...], ...]
    authenticated_delay_queue_norm_tsc: tuple[tuple[float, ...], ...]
    previous_correction: tuple[float, ...] | None
    integral_state: tuple[float, ...] | None
    actuator_hypothesis_ids: tuple[str, ...]
    plant_response_tube_lower: tuple[float, ...]
    plant_response_tube_upper: tuple[float, ...]
    provenance_hashes: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.formal_task_step, int) or self.formal_task_step < 0:
            raise ValueError("formal_task_step must be a nonnegative integer")
        if not isinstance(self.velocity, VelocityEstimate):
            raise ValueError("velocity must be a VelocityEstimate")
        target = _finite_tuple(self.target_rzip, 3, "target_rzip")
        history = _rows(self.measurement_history_rzip, 3, "measurement_history_rzip")
        if not history:
            raise ValueError("measurement history must contain the restart measurement")
        measured = _finite_tuple(
            self.measured_coil_current_a_tsc,
            N_COILS,
            "measured_coil_current_a_tsc",
        )
        commands = _rows(
            self.issued_commands_norm_tsc, N_COILS, "issued_commands_norm_tsc"
        )
        queue = _rows(
            self.authenticated_delay_queue_norm_tsc,
            N_COILS,
            "authenticated_delay_queue_norm_tsc",
        )
        previous = None if self.previous_correction is None else _finite_tuple(
            self.previous_correction,
            len(self.previous_correction),
            "previous_correction",
        )
        integral = None if self.integral_state is None else _finite_tuple(
            self.integral_state, len(self.integral_state), "integral_state"
        )
        hypothesis_ids = tuple(str(value) for value in self.actuator_hypothesis_ids)
        if not hypothesis_ids or any(not value for value in hypothesis_ids):
            raise ValueError("at least one nonempty actuator hypothesis is required")
        if len(set(hypothesis_ids)) != len(hypothesis_ids):
            raise ValueError("actuator hypothesis identifiers must be unique")
        lower = _finite_tuple(
            self.plant_response_tube_lower,
            len(self.plant_response_tube_lower),
            "plant_response_tube_lower",
        )
        upper = _finite_tuple(
            self.plant_response_tube_upper,
            len(self.plant_response_tube_upper),
            "plant_response_tube_upper",
        )
        if not lower or len(lower) != len(upper) or any(lo > hi for lo, hi in zip(lower, upper)):
            raise ValueError("plant response tube must be nonempty and ordered")
        provenance = tuple(sorted((str(key), str(value)) for key, value in self.provenance_hashes))
        if not provenance or any(not key or not value for key, value in provenance):
            raise ValueError("nonempty provenance hashes are required")
        object.__setattr__(self, "target_rzip", target)
        object.__setattr__(self, "measurement_history_rzip", history)
        object.__setattr__(self, "measured_coil_current_a_tsc", measured)
        object.__setattr__(self, "issued_commands_norm_tsc", commands)
        object.__setattr__(self, "authenticated_delay_queue_norm_tsc", queue)
        object.__setattr__(self, "previous_correction", previous)
        object.__setattr__(self, "integral_state", integral)
        object.__setattr__(self, "actuator_hypothesis_ids", hypothesis_ids)
        object.__setattr__(self, "plant_response_tube_lower", lower)
        object.__setattr__(self, "plant_response_tube_upper", upper)
        object.__setattr__(self, "provenance_hashes", provenance)

    @classmethod
    def from_restart_mapping(cls, payload: Mapping[str, Any]) -> "CausalRestartObserverState":
        allowed = {
            "formal_task_step",
            "target_rzip",
            "restart_measurement_rzip",
            "measured_coil_current_a_tsc",
            "authenticated_delay_queue_norm_tsc",
            "previous_correction",
            "integral_state",
            "actuator_hypothesis_ids",
            "plant_response_tube_lower",
            "plant_response_tube_upper",
            "provenance_hashes",
            "unknown_velocity_bound_mps",
        }
        _reject_unknown(payload, allowed, "restart")
        missing = allowed - {"previous_correction", "integral_state"} - set(payload)
        if missing:
            raise ValueError(f"missing restart fields: {sorted(missing)}")
        bound = float(payload["unknown_velocity_bound_mps"])
        if not math.isfinite(bound) or bound <= 0.0:
            raise ValueError("unknown_velocity_bound_mps must be finite and positive")
        provenance = payload["provenance_hashes"]
        if isinstance(provenance, Mapping):
            provenance = tuple(provenance.items())
        return cls(
            formal_task_step=int(payload["formal_task_step"]),
            target_rzip=tuple(payload["target_rzip"]),
            measurement_history_rzip=(tuple(payload["restart_measurement_rzip"]),),
            velocity=VelocityEstimate(
                value_mps=(0.0, 0.0),
                lower_mps=(-bound, -bound),
                upper_mps=(bound, bound),
                status="unknown_interval",
            ),
            measured_coil_current_a_tsc=tuple(payload["measured_coil_current_a_tsc"]),
            issued_commands_norm_tsc=(),
            authenticated_delay_queue_norm_tsc=tuple(
                tuple(row) for row in payload["authenticated_delay_queue_norm_tsc"]
            ),
            previous_correction=_vector_or_none(
                payload.get("previous_correction"),
                len(payload.get("previous_correction") or ()),
                "previous_correction",
            ),
            integral_state=_vector_or_none(
                payload.get("integral_state"),
                len(payload.get("integral_state") or ()),
                "integral_state",
            ),
            actuator_hypothesis_ids=tuple(payload["actuator_hypothesis_ids"]),
            plant_response_tube_lower=tuple(payload["plant_response_tube_lower"]),
            plant_response_tube_upper=tuple(payload["plant_response_tube_upper"]),
            provenance_hashes=tuple(provenance),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CausalRestartObserverState":
        """Restore the exact causal state emitted by :meth:`to_dict`."""
        allowed = {
            "formal_task_step",
            "target_rzip",
            "measurement_history_rzip",
            "velocity",
            "measured_coil_current_a_tsc",
            "issued_commands_norm_tsc",
            "authenticated_delay_queue_norm_tsc",
            "previous_correction",
            "integral_state",
            "actuator_hypothesis_ids",
            "plant_response_tube_lower",
            "plant_response_tube_upper",
            "provenance_hashes",
        }
        _reject_unknown(payload, allowed, "serialized observer")
        missing = allowed - set(payload)
        if missing:
            raise ValueError(f"missing serialized observer fields: {sorted(missing)}")
        velocity_payload = payload["velocity"]
        if not isinstance(velocity_payload, Mapping):
            raise ValueError("serialized velocity must be a mapping")
        velocity_allowed = {"value_mps", "lower_mps", "upper_mps", "status"}
        _reject_unknown(velocity_payload, velocity_allowed, "velocity")
        if set(velocity_payload) != velocity_allowed:
            raise ValueError("serialized velocity fields are incomplete")
        provenance = payload["provenance_hashes"]
        if isinstance(provenance, Mapping):
            provenance = tuple(provenance.items())
        return cls(
            formal_task_step=payload["formal_task_step"],
            target_rzip=tuple(payload["target_rzip"]),
            measurement_history_rzip=tuple(
                tuple(row) for row in payload["measurement_history_rzip"]
            ),
            velocity=VelocityEstimate(
                value_mps=tuple(velocity_payload["value_mps"]),
                lower_mps=tuple(velocity_payload["lower_mps"]),
                upper_mps=tuple(velocity_payload["upper_mps"]),
                status=str(velocity_payload["status"]),
            ),
            measured_coil_current_a_tsc=tuple(payload["measured_coil_current_a_tsc"]),
            issued_commands_norm_tsc=tuple(
                tuple(row) for row in payload["issued_commands_norm_tsc"]
            ),
            authenticated_delay_queue_norm_tsc=tuple(
                tuple(row) for row in payload["authenticated_delay_queue_norm_tsc"]
            ),
            previous_correction=(
                None
                if payload["previous_correction"] is None
                else tuple(payload["previous_correction"])
            ),
            integral_state=(
                None
                if payload["integral_state"] is None
                else tuple(payload["integral_state"])
            ),
            actuator_hypothesis_ids=tuple(payload["actuator_hypothesis_ids"]),
            plant_response_tube_lower=tuple(payload["plant_response_tube_lower"]),
            plant_response_tube_upper=tuple(payload["plant_response_tube_upper"]),
            provenance_hashes=tuple(provenance),
        )

    def advance_from_mapping(self, payload: Mapping[str, Any]) -> "CausalRestartObserverState":
        allowed = {
            "next_measurement_rzip",
            "measured_coil_current_a_tsc",
            "issued_command_norm_tsc",
            "authenticated_delay_queue_norm_tsc",
            "dt_seconds",
            "finite_difference_uncertainty_mps",
            "previous_correction",
            "integral_state",
        }
        _reject_unknown(payload, allowed, "advance")
        missing = allowed - {"previous_correction", "integral_state"} - set(payload)
        if missing:
            raise ValueError(f"missing advance fields: {sorted(missing)}")
        next_measurement = _finite_tuple(
            payload["next_measurement_rzip"], 3, "next_measurement_rzip"
        )
        dt = float(payload["dt_seconds"])
        uncertainty = float(payload["finite_difference_uncertainty_mps"])
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        if not math.isfinite(uncertainty) or uncertainty <= 0.0:
            raise ValueError("finite_difference_uncertainty_mps must be positive")
        current = self.measurement_history_rzip[-1]
        velocity = tuple(
            (next_measurement[index] - current[index]) / dt for index in range(2)
        )
        return replace(
            self,
            formal_task_step=self.formal_task_step + 1,
            measurement_history_rzip=self.measurement_history_rzip + (next_measurement,),
            velocity=VelocityEstimate(
                value_mps=velocity,
                lower_mps=tuple(value - uncertainty for value in velocity),
                upper_mps=tuple(value + uncertainty for value in velocity),
                status="finite_difference",
            ),
            measured_coil_current_a_tsc=_finite_tuple(
                payload["measured_coil_current_a_tsc"],
                N_COILS,
                "measured_coil_current_a_tsc",
            ),
            issued_commands_norm_tsc=self.issued_commands_norm_tsc
            + (
                _finite_tuple(
                    payload["issued_command_norm_tsc"],
                    N_COILS,
                    "issued_command_norm_tsc",
                ),
            ),
            authenticated_delay_queue_norm_tsc=_rows(
                payload["authenticated_delay_queue_norm_tsc"],
                N_COILS,
                "authenticated_delay_queue_norm_tsc",
            ),
            previous_correction=(
                self.previous_correction
                if "previous_correction" not in payload
                else _vector_or_none(
                    payload["previous_correction"],
                    len(payload["previous_correction"] or ()),
                    "previous_correction",
                )
            ),
            integral_state=(
                self.integral_state
                if "integral_state" not in payload
                else _vector_or_none(
                    payload["integral_state"],
                    len(payload["integral_state"] or ()),
                    "integral_state",
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "formal_task_step": self.formal_task_step,
            "target_rzip": list(self.target_rzip),
            "measurement_history_rzip": [list(row) for row in self.measurement_history_rzip],
            "velocity": self.velocity.to_dict(),
            "measured_coil_current_a_tsc": list(self.measured_coil_current_a_tsc),
            "issued_commands_norm_tsc": [list(row) for row in self.issued_commands_norm_tsc],
            "authenticated_delay_queue_norm_tsc": [
                list(row) for row in self.authenticated_delay_queue_norm_tsc
            ],
            "previous_correction": (
                None if self.previous_correction is None else list(self.previous_correction)
            ),
            "integral_state": None if self.integral_state is None else list(self.integral_state),
            "actuator_hypothesis_ids": list(self.actuator_hypothesis_ids),
            "plant_response_tube_lower": list(self.plant_response_tube_lower),
            "plant_response_tube_upper": list(self.plant_response_tube_upper),
            "provenance_hashes": dict(self.provenance_hashes),
        }
