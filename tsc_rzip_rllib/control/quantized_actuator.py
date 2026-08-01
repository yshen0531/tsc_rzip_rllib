"""Exact Card15 actuator quantization with an explicit readback tube.

All current vectors are in the repository's 14-channel TSC order and use
single-turn amperes unless a field explicitly says ``kAt`` or grid units.
The development bias is evidence provenance, not a universal plant constant.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from tsc_rzip_rllib.core.coil_order import TSC_COIL_NAMES
from tsc_rzip_rllib.core.inputa import format_number


N_COILS = len(TSC_COIL_NAMES)
OUTPUT_GRID_KAT = 1e-6
T13S2R1_REPORT_SHA256 = (
    "62b28bec07bde398cfec6b4aaf42899960e63a8761ce19316f83e8c929903c87"
)
DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC = (
    2.0,
    2.0,
    2.0,
    2.0,
    2.0,
    2.0,
    2.0,
    1.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
)


def _finite_tuple(values: Sequence[float], length: int, name: str) -> tuple[float, ...]:
    try:
        result = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite numeric sequence") from exc
    if len(result) != length or not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} must contain {length} finite values")
    return result


@dataclass(frozen=True)
class QuantizedActuatorResult:
    """One deterministic Card15 command and its prospective readback set."""

    measured_current_a_tsc: tuple[float, ...]
    requested_action_norm_tsc: tuple[float, ...]
    clipped_action_norm_tsc: tuple[float, ...]
    unconstrained_current_a_tsc: tuple[float, ...]
    desired_current_a_tsc: tuple[float, ...]
    card15_fields: tuple[str, ...]
    card15_target_current_a_tsc: tuple[float, ...]
    nominal_readback_current_a_tsc: tuple[float, ...]
    readback_lower_a_tsc: tuple[float, ...]
    readback_upper_a_tsc: tuple[float, ...]
    action_saturated: tuple[bool, ...]
    current_limit_clipped: tuple[bool, ...]
    active_command_collapsed_to_grid: tuple[bool, ...]
    bias_grid_units_tsc: tuple[float, ...]
    uncertainty_radius_grid_units_tsc: tuple[float, ...]
    output_grid_kAt: float
    provenance: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "measured_current_a_tsc": list(self.measured_current_a_tsc),
            "requested_action_norm_tsc": list(self.requested_action_norm_tsc),
            "clipped_action_norm_tsc": list(self.clipped_action_norm_tsc),
            "unconstrained_current_a_tsc": list(self.unconstrained_current_a_tsc),
            "desired_current_a_tsc": list(self.desired_current_a_tsc),
            "card15_fields": list(self.card15_fields),
            "card15_target_current_a_tsc": list(self.card15_target_current_a_tsc),
            "nominal_readback_current_a_tsc": list(
                self.nominal_readback_current_a_tsc
            ),
            "readback_lower_a_tsc": list(self.readback_lower_a_tsc),
            "readback_upper_a_tsc": list(self.readback_upper_a_tsc),
            "action_saturated": list(self.action_saturated),
            "current_limit_clipped": list(self.current_limit_clipped),
            "active_command_collapsed_to_grid": list(
                self.active_command_collapsed_to_grid
            ),
            "bias_grid_units_tsc": list(self.bias_grid_units_tsc),
            "uncertainty_radius_grid_units_tsc": list(
                self.uncertainty_radius_grid_units_tsc
            ),
            "output_grid_kAt": self.output_grid_kAt,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class QuantizedActuatorModel:
    """Pure exact-serialization model for the TSC Card15 actuator boundary."""

    minimum_current_a_tsc: tuple[float, ...]
    maximum_current_a_tsc: tuple[float, ...]
    max_slew_step_a: float
    turns_tsc: tuple[float, ...]
    bias_grid_units_tsc: tuple[float, ...] = DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC
    uncertainty_radius_grid_units_tsc: tuple[float, ...] = (1.0,) * N_COILS
    bias_report_sha256: str = T13S2R1_REPORT_SHA256

    def __post_init__(self) -> None:
        minimum = _finite_tuple(
            self.minimum_current_a_tsc, N_COILS, "minimum_current_a_tsc"
        )
        maximum = _finite_tuple(
            self.maximum_current_a_tsc, N_COILS, "maximum_current_a_tsc"
        )
        turns = _finite_tuple(self.turns_tsc, N_COILS, "turns_tsc")
        bias = _finite_tuple(
            self.bias_grid_units_tsc, N_COILS, "bias_grid_units_tsc"
        )
        uncertainty = _finite_tuple(
            self.uncertainty_radius_grid_units_tsc,
            N_COILS,
            "uncertainty_radius_grid_units_tsc",
        )
        if any(lo >= hi for lo, hi in zip(minimum, maximum)):
            raise ValueError("each minimum current must be below its maximum")
        if any(value <= 0.0 for value in turns):
            raise ValueError("turn counts must be positive")
        if any(value < 1.0 for value in uncertainty):
            raise ValueError("every readback uncertainty radius must be at least one grid unit")
        if not math.isfinite(float(self.max_slew_step_a)) or self.max_slew_step_a <= 0:
            raise ValueError("max_slew_step_a must be finite and positive")
        if self.bias_report_sha256 != T13S2R1_REPORT_SHA256:
            raise ValueError("development bias provenance hash changed")
        object.__setattr__(self, "minimum_current_a_tsc", minimum)
        object.__setattr__(self, "maximum_current_a_tsc", maximum)
        object.__setattr__(self, "turns_tsc", turns)
        object.__setattr__(self, "bias_grid_units_tsc", bias)
        object.__setattr__(self, "uncertainty_radius_grid_units_tsc", uncertainty)
        object.__setattr__(self, "max_slew_step_a", float(self.max_slew_step_a))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "QuantizedActuatorModel":
        allowed = {
            "minimum_current_a_tsc",
            "maximum_current_a_tsc",
            "max_slew_step_a",
            "turns_tsc",
            "bias_grid_units_tsc",
            "uncertainty_radius_grid_units_tsc",
            "bias_report_sha256",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"unknown actuator model fields: {sorted(unknown)}")
        return cls(**dict(payload))

    @property
    def provenance(self) -> tuple[tuple[str, str], ...]:
        return (
            ("bias_scope", "retrospective_T13S1_development_nominal_only"),
            ("bias_source_report_sha256", self.bias_report_sha256),
            ("card15_formatter", "tsc_rzip_rllib.core.inputa.format_number:.3E"),
            ("coil_order", "TSC"),
        )

    def apply(
        self,
        measured_current_a_tsc: Sequence[float],
        issued_action_norm_tsc: Sequence[float],
    ) -> QuantizedActuatorResult:
        current = _finite_tuple(
            measured_current_a_tsc, N_COILS, "measured_current_a_tsc"
        )
        requested = _finite_tuple(
            issued_action_norm_tsc, N_COILS, "issued_action_norm_tsc"
        )
        clipped_action = tuple(max(-1.0, min(1.0, value)) for value in requested)
        unconstrained = tuple(
            value + action * self.max_slew_step_a
            for value, action in zip(current, clipped_action)
        )
        desired = tuple(
            max(lo, min(hi, value))
            for value, lo, hi in zip(
                unconstrained,
                self.minimum_current_a_tsc,
                self.maximum_current_a_tsc,
            )
        )
        desired_kat = tuple(
            value * turns / 1000.0
            for value, turns in zip(desired, self.turns_tsc)
        )
        fields = tuple(format_number(value) for value in desired_kat)
        target = tuple(
            float(field.strip()) * 1000.0 / turns
            for field, turns in zip(fields, self.turns_tsc)
        )
        grid_a = tuple(
            OUTPUT_GRID_KAT * 1000.0 / turns for turns in self.turns_tsc
        )
        nominal = tuple(
            value - bias * spacing
            for value, bias, spacing in zip(
                target, self.bias_grid_units_tsc, grid_a
            )
        )
        radius_a = tuple(
            radius * spacing
            for radius, spacing in zip(
                self.uncertainty_radius_grid_units_tsc, grid_a
            )
        )
        lower = tuple(value - radius for value, radius in zip(nominal, radius_a))
        upper = tuple(value + radius for value, radius in zip(nominal, radius_a))
        return QuantizedActuatorResult(
            measured_current_a_tsc=current,
            requested_action_norm_tsc=requested,
            clipped_action_norm_tsc=clipped_action,
            unconstrained_current_a_tsc=unconstrained,
            desired_current_a_tsc=desired,
            card15_fields=fields,
            card15_target_current_a_tsc=target,
            nominal_readback_current_a_tsc=nominal,
            readback_lower_a_tsc=lower,
            readback_upper_a_tsc=upper,
            action_saturated=tuple(a != b for a, b in zip(requested, clipped_action)),
            current_limit_clipped=tuple(a != b for a, b in zip(unconstrained, desired)),
            active_command_collapsed_to_grid=tuple(
                abs(action) > 0.0 and quantized == measured
                for action, quantized, measured in zip(clipped_action, target, current)
            ),
            bias_grid_units_tsc=self.bias_grid_units_tsc,
            uncertainty_radius_grid_units_tsc=self.uncertainty_radius_grid_units_tsc,
            output_grid_kAt=OUTPUT_GRID_KAT,
            provenance=self.provenance,
        )
