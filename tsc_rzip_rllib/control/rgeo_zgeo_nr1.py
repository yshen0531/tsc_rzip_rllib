"""NR1 fail-closed safety and fixed-prefix replay qualification helpers.

The helpers are pure: they do not instantiate a TSC runner or advance a
plant.  The server launcher is responsible for applying an accepted target.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.core.inputa import format_number

from .rgeo_zgeo_contract import ContractError, N_COILS, RGeoZGeoSignal


NR1_CONTRACT_VERSION = "rgeo-zgeo-nr1-v1"
NR1_INTENDED_USE = "interface_validation"
NR1_HORIZON_STEPS = 8
NR1_PULSE_NORMALIZED = 0.05
NR1_R_GEO_RADIUS_M = 0.05
NR1_Z_GEO_RADIUS_M = 0.05
NR1_IP_FRACTION = 0.10
NUMERIC_ATOL = 1e-9


@dataclass(frozen=True)
class QuantizedCurrentTarget:
    requested_current_a_tsc: tuple[float, ...]
    serialized_card15_fields: tuple[str, ...]
    quantized_current_a_tsc: tuple[float, ...]

    def __post_init__(self) -> None:
        for name, values in (
            ("requested_current_a_tsc", self.requested_current_a_tsc),
            ("serialized_card15_fields", self.serialized_card15_fields),
            ("quantized_current_a_tsc", self.quantized_current_a_tsc),
        ):
            if len(values) != N_COILS:
                raise ContractError(f"{name} must contain {N_COILS} values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_current_a_tsc": list(self.requested_current_a_tsc),
            "serialized_card15_fields": list(self.serialized_card15_fields),
            "quantized_current_a_tsc": list(self.quantized_current_a_tsc),
        }


def quantize_card15_target(
    requested_current_a_tsc: Sequence[float], turns_tsc: Sequence[float]
) -> QuantizedCurrentTarget:
    requested = np.asarray(requested_current_a_tsc, dtype=float)
    turns = np.asarray(turns_tsc, dtype=float)
    if requested.shape != (N_COILS,) or turns.shape != (N_COILS,):
        raise ContractError("requested currents and turns must both have shape (14,)")
    if not np.all(np.isfinite(requested)) or not np.all(np.isfinite(turns)):
        raise ContractError("requested currents and turns must be finite")
    if np.any(turns <= 0.0):
        raise ContractError("turns must be positive")
    requested_kat = requested * turns / 1000.0
    fields = tuple(format_number(value) for value in requested_kat)
    quantized_kat = np.asarray([float(value.strip()) for value in fields], dtype=float)
    quantized_a = quantized_kat * 1000.0 / turns
    return QuantizedCurrentTarget(
        requested_current_a_tsc=tuple(float(value) for value in requested),
        serialized_card15_fields=fields,
        quantized_current_a_tsc=tuple(float(value) for value in quantized_a),
    )


@dataclass(frozen=True)
class FrozenPrefix:
    name: str
    targets: tuple[QuantizedCurrentTarget, ...]

    def __post_init__(self) -> None:
        if self.name not in {"hold", "pulse"}:
            raise ContractError("NR1 prefix name must be hold or pulse")
        if len(self.targets) != NR1_HORIZON_STEPS:
            raise ContractError(f"NR1 prefixes require {NR1_HORIZON_STEPS} targets")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "targets": [target.to_dict() for target in self.targets]}


def build_frozen_prefixes(
    *,
    initial_current_a_tsc: Sequence[float],
    turns_tsc: Sequence[float],
    max_delta_current_a_per_step: float,
) -> dict[str, FrozenPrefix]:
    initial = np.asarray(initial_current_a_tsc, dtype=float)
    if initial.shape != (N_COILS,) or not np.all(np.isfinite(initial)):
        raise ContractError("initial_current_a_tsc must be a finite 14-vector")
    max_delta = float(max_delta_current_a_per_step)
    if not math.isfinite(max_delta) or max_delta <= 0.0:
        raise ContractError("max_delta_current_a_per_step must be positive and finite")
    center = quantize_card15_target(initial, turns_tsc)
    q0 = np.asarray(center.quantized_current_a_tsc, dtype=float)
    signs = np.asarray([1.0 if index % 2 == 0 else -1.0 for index in range(N_COILS)])
    pulse = quantize_card15_target(q0 + NR1_PULSE_NORMALIZED * max_delta * signs, turns_tsc)
    return {
        "hold": FrozenPrefix(name="hold", targets=(center,) * NR1_HORIZON_STEPS),
        "pulse": FrozenPrefix(
            name="pulse",
            targets=(pulse,) + (center,) * (NR1_HORIZON_STEPS - 1),
        ),
    }


@dataclass(frozen=True)
class NR1SafetyEnvelope:
    source_r_geo_m: float
    source_z_geo_m: float
    source_ip_a: float
    r_geo_radius_m: float = NR1_R_GEO_RADIUS_M
    z_geo_radius_m: float = NR1_Z_GEO_RADIUS_M
    ip_fraction: float = NR1_IP_FRACTION

    def __post_init__(self) -> None:
        values = (
            self.source_r_geo_m,
            self.source_z_geo_m,
            self.source_ip_a,
            self.r_geo_radius_m,
            self.z_geo_radius_m,
            self.ip_fraction,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ContractError("NR1 safety envelope values must be finite")
        if self.source_ip_a == 0.0:
            raise ContractError("source Ip must be nonzero")
        if self.r_geo_radius_m <= 0.0 or self.z_geo_radius_m <= 0.0:
            raise ContractError("NR1 geometry radii must be positive")
        if not 0.0 < self.ip_fraction < 1.0:
            raise ContractError("NR1 Ip fraction must lie between zero and one")

    @classmethod
    def from_source_signal(cls, signal: RGeoZGeoSignal) -> "NR1SafetyEnvelope":
        if not isinstance(signal, RGeoZGeoSignal):
            raise ContractError("source signal must be RGeoZGeoSignal")
        return cls(
            source_r_geo_m=signal.boundary.r_geo_m,
            source_z_geo_m=signal.boundary.z_geo_m,
            source_ip_a=signal.ip_a,
        )

    def state_reasons(
        self,
        *,
        signal: RGeoZGeoSignal,
        actual_current_a_tsc: Sequence[float],
        min_current_a_tsc: Sequence[float],
        max_current_a_tsc: Sequence[float],
    ) -> tuple[str, ...]:
        actual = _finite_14(actual_current_a_tsc, "actual_current_a_tsc")
        lower = _finite_14(min_current_a_tsc, "min_current_a_tsc")
        upper = _finite_14(max_current_a_tsc, "max_current_a_tsc")
        reasons: list[str] = []
        if np.any(lower >= upper):
            reasons.append("INVALID_CURRENT_LIMITS")
        if np.any(actual < lower - NUMERIC_ATOL) or np.any(actual > upper + NUMERIC_ATOL):
            reasons.append("ACTUAL_CURRENT_LIMIT")
        r_geo = signal.boundary.r_geo_m
        z_geo = signal.boundary.z_geo_m
        if not signal.limiter.r_inner_m <= r_geo <= signal.limiter.r_outer_m:
            reasons.append("R_GEO_OUTSIDE_LIMITER_MIDPLANE")
        if abs(r_geo - self.source_r_geo_m) > self.r_geo_radius_m:
            reasons.append("R_GEO_CAMPAIGN_LIMIT")
        if abs(z_geo - self.source_z_geo_m) > self.z_geo_radius_m:
            reasons.append("Z_GEO_CAMPAIGN_LIMIT")
        if math.copysign(1.0, signal.ip_a) != math.copysign(1.0, self.source_ip_a):
            reasons.append("IP_SIGN")
        if abs(signal.ip_a - self.source_ip_a) > self.ip_fraction * abs(self.source_ip_a):
            reasons.append("IP_CAMPAIGN_LIMIT")
        return tuple(reasons)

    def target_reasons(
        self,
        *,
        actual_current_a_tsc: Sequence[float],
        target_current_a_tsc: Sequence[float],
        min_current_a_tsc: Sequence[float],
        max_current_a_tsc: Sequence[float],
        max_delta_current_a_per_step: float,
    ) -> tuple[str, ...]:
        actual = _finite_14(actual_current_a_tsc, "actual_current_a_tsc")
        target = _finite_14(target_current_a_tsc, "target_current_a_tsc")
        lower = _finite_14(min_current_a_tsc, "min_current_a_tsc")
        upper = _finite_14(max_current_a_tsc, "max_current_a_tsc")
        max_delta = float(max_delta_current_a_per_step)
        if not math.isfinite(max_delta) or max_delta <= 0.0:
            raise ContractError("max current delta must be positive and finite")
        reasons: list[str] = []
        if np.any(target < lower - NUMERIC_ATOL) or np.any(target > upper + NUMERIC_ATOL):
            reasons.append("TARGET_CURRENT_LIMIT")
        if np.any(np.abs(target - actual) > max_delta + NUMERIC_ATOL):
            reasons.append("TARGET_SLEW_LIMIT")
        return tuple(reasons)

    def to_dict(self) -> dict[str, float]:
        return {
            "source_r_geo_m": self.source_r_geo_m,
            "source_z_geo_m": self.source_z_geo_m,
            "source_ip_a": self.source_ip_a,
            "r_geo_radius_m": self.r_geo_radius_m,
            "z_geo_radius_m": self.z_geo_radius_m,
            "ip_fraction": self.ip_fraction,
        }


def _finite_14(values: Sequence[float], name: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.shape != (N_COILS,) or not np.all(np.isfinite(result)):
        raise ContractError(f"{name} must be a finite 14-vector")
    return result


def artifact_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_replay_records(
    primary: Sequence[Mapping[str, Any]], replay: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    reasons: list[str] = []
    maximum = {"geometry_m": 0.0, "ip_a": 0.0, "coil_current_a": 0.0, "wire_current_a": 0.0}
    if len(primary) != len(replay):
        reasons.append("STATE_COUNT")
    for index, (left, right) in enumerate(zip(primary, replay)):
        if left.get("time_ms") != right.get("time_ms"):
            reasons.append(f"TIME_{index}")
        for key in ("r_geo_m", "z_geo_m", "r_mid_m"):
            difference = _scalar_difference(left, right, key, reasons, index)
            maximum["geometry_m"] = max(maximum["geometry_m"], difference)
        maximum["ip_a"] = max(
            maximum["ip_a"], _scalar_difference(left, right, "ip_a", reasons, index)
        )
        for key, maximum_key in (
            ("actual_current_a_tsc", "coil_current_a"),
            ("wire_current_a", "wire_current_a"),
        ):
            try:
                left_values = np.asarray(left[key], dtype=float)
                right_values = np.asarray(right[key], dtype=float)
                if left_values.shape != right_values.shape or not (
                    np.all(np.isfinite(left_values)) and np.all(np.isfinite(right_values))
                ):
                    raise ValueError
                difference = float(np.max(np.abs(left_values - right_values))) if left_values.size else 0.0
            except (KeyError, TypeError, ValueError):
                reasons.append(f"INVALID_{key.upper()}_{index}")
                difference = math.inf
            maximum[maximum_key] = max(maximum[maximum_key], difference)
        if left.get("target_card15_fields") != right.get("target_card15_fields"):
            reasons.append(f"TARGET_FIELDS_{index}")
    if maximum["geometry_m"] > 1e-12:
        reasons.append("GEOMETRY_TOLERANCE")
    if maximum["ip_a"] > 1e-9:
        reasons.append("IP_TOLERANCE")
    if maximum["coil_current_a"] > 1e-9:
        reasons.append("COIL_CURRENT_TOLERANCE")
    if maximum["wire_current_a"] > 1e-9:
        reasons.append("WIRE_CURRENT_TOLERANCE")
    unique_reasons = tuple(dict.fromkeys(reasons))
    return {"passed": not unique_reasons, "reasons": list(unique_reasons), "maximum_absolute_difference": maximum}


def _scalar_difference(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    key: str,
    reasons: list[str],
    index: int,
) -> float:
    try:
        left_value = float(left[key])
        right_value = float(right[key])
        if not math.isfinite(left_value) or not math.isfinite(right_value):
            raise ValueError
        return abs(left_value - right_value)
    except (KeyError, TypeError, ValueError):
        reasons.append(f"INVALID_{key.upper()}_{index}")
        return math.inf
