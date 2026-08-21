"""Pure helpers for the prospectively frozen 1 ms NR1 qualification."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math
from typing import Any, Sequence

from tsc_rzip_rllib.core.inputa import format_number

from .rgeo_zgeo_1ms_contract import (
    CONTROL_PERIOD_MS,
    MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP,
    N_COILS,
)
from .rgeo_zgeo_contract import ContractError, RGeoZGeoSignal


NR1_1MS_CONTRACT_VERSION = "rgeo-zgeo-1ms-nr1r2-v1"
NR1_1MS_CAMPAIGN_ID = "rgeo_zgeo_1ms_nr1r2_command_readback_v1"
NR1_1MS_INTENDED_USE = "interface_validation"
NR1_1MS_HORIZON_STEPS = 4
NR1_1MS_ROLLOUTS = (
    ("hold_primary", "hold"),
    ("hold_replay", "hold"),
    ("pattern_a_primary", "pattern_a"),
    ("pattern_a_replay", "pattern_a"),
    ("pattern_b_primary", "pattern_b"),
    ("pattern_b_replay", "pattern_b"),
)
RETURN_EQUIVALENCE_A = Decimal("0.0001")


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ContractError(f"{name} must be finite")
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ContractError(f"{name} must be finite") from exc
    if not result.is_finite():
        raise ContractError(f"{name} must be finite")
    return result


def _vector(values: Sequence[float], name: str) -> tuple[float, ...]:
    try:
        result = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be a finite 14-vector") from exc
    if len(result) != N_COILS or not all(math.isfinite(value) for value in result):
        raise ContractError(f"{name} must be a finite 14-vector")
    return result


def decimal_single_turn_currents_a(
    currents_kat_tsc: Sequence[Any], turns_tsc: Sequence[Any], *, name: str
) -> tuple[Decimal, ...]:
    """Convert original decimal kA-turn fields to exact single-turn amperes."""
    try:
        currents = tuple(currents_kat_tsc)
        turns = tuple(turns_tsc)
    except TypeError as exc:
        raise ContractError(f"{name} must contain fourteen current and turn values") from exc
    if len(currents) != N_COILS or len(turns) != N_COILS:
        raise ContractError(f"{name} must contain fourteen current and turn values")
    result: list[Decimal] = []
    for index, (current, turn) in enumerate(zip(currents, turns)):
        denominator = _decimal(turn, f"{name}.turns[{index}]")
        if denominator <= 0:
            raise ContractError(f"{name}.turns[{index}] must be positive")
        result.append(
            _decimal(current, f"{name}.currents_kat_tsc[{index}]")
            * Decimal("1000")
            / denominator
        )
    return tuple(result)


def card15_target_decimal_a(
    target: "Card15Target", turns_tsc: Sequence[Any], *, name: str
) -> tuple[Decimal, ...]:
    return decimal_single_turn_currents_a(
        tuple(value.strip() for value in target.card15_fields), turns_tsc, name=name
    )


def assert_exact_slew(
    before_a_tsc: Sequence[Any], after_a_tsc: Sequence[Any], *, name: str
) -> float:
    try:
        before = tuple(before_a_tsc)
        after = tuple(after_a_tsc)
    except TypeError as exc:
        raise ContractError(f"{name} requires two finite 14-vectors") from exc
    if len(before) != N_COILS or len(after) != N_COILS:
        raise ContractError(f"{name} requires two finite 14-vectors")
    maximum = Decimal("0")
    for index, (left, right) in enumerate(zip(before, after)):
        delta = abs(_decimal(right, f"{name}[{index}]") - _decimal(left, f"{name}[{index}]"))
        maximum = max(maximum, delta)
        if delta > MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP:
            raise ContractError(f"{name}[{index}] exceeds the exact 0.3 A step limit")
    return float(maximum)


@dataclass(frozen=True)
class Card15Target:
    card15_fields: tuple[str, ...]
    current_a_tsc: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.card15_fields) != N_COILS or any(len(value) != 10 for value in self.card15_fields):
            raise ContractError("Card15 target requires fourteen exact 10-character fields")
        object.__setattr__(self, "current_a_tsc", _vector(self.current_a_tsc, "current_a_tsc"))

    def to_dict(self) -> dict[str, Any]:
        return {"card15_fields": list(self.card15_fields), "current_a_tsc": list(self.current_a_tsc)}


def quantize_target(current_a_tsc: Sequence[float], turns_tsc: Sequence[float]) -> Card15Target:
    current = _vector(current_a_tsc, "current_a_tsc")
    turns = _vector(turns_tsc, "turns_tsc")
    if any(value <= 0.0 for value in turns):
        raise ContractError("turn counts must be positive")
    fields = tuple(format_number(value * turn / 1000.0) for value, turn in zip(current, turns))
    quantized = tuple(float(field.strip()) * 1000.0 / turn for field, turn in zip(fields, turns))
    return Card15Target(card15_fields=fields, current_a_tsc=quantized)


def _signed_lattice_value(
    q0_a: float, source_a: float, turn: float, sign: int,
    maximum_delta_a: float = MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP,
) -> tuple[str, float]:
    if sign not in (-1, 1):
        raise ContractError("lattice sign must be -1 or +1")
    candidates: dict[str, float] = {}
    # 0.00005 A resolution covers the finest observed source lattice while
    # formatter output remains the sole authority for representability.
    for unit in range(1, 6001):
        request = q0_a + sign * unit * 0.00005
        field = format_number(request * turn / 1000.0)
        value = float(field.strip()) * 1000.0 / turn
        delta = _decimal(value, "quantized candidate") - _decimal(q0_a, "q0")
        source_delta = _decimal(value, "quantized candidate") - _decimal(
            source_a, "source readback"
        )
        if (
            delta * sign > 0
            and abs(delta) <= _decimal(maximum_delta_a, "maximum_delta_a")
            and abs(source_delta) <= _decimal(maximum_delta_a, "maximum_delta_a")
        ):
            candidates[field] = value
    if not candidates:
        raise ContractError("no nonzero Card15 lattice target exists within 0.3 A")
    field, value = max(
        candidates.items(), key=lambda item: abs(_decimal(item[1], "candidate") - _decimal(q0_a, "q0"))
    )
    return field, value


@dataclass(frozen=True)
class FrozenOneMsPrefixes:
    q0: Card15Target
    prefixes: dict[str, tuple[Card15Target, ...]]

    def __post_init__(self) -> None:
        if set(self.prefixes) != {"hold", "pattern_a", "pattern_b"}:
            raise ContractError("NR1 requires hold, pattern_a and pattern_b prefixes")
        if any(len(value) != NR1_1MS_HORIZON_STEPS for value in self.prefixes.values()):
            raise ContractError("each NR1 prefix requires exactly four targets")

    def to_dict(self) -> dict[str, Any]:
        return {
            "q0": self.q0.to_dict(),
            "prefixes": {key: [item.to_dict() for item in value] for key, value in self.prefixes.items()},
        }


def build_frozen_one_ms_prefixes(
    *,
    source_current_a_tsc: Sequence[float],
    source_command_a_tsc: Sequence[Any] | None = None,
    turns_tsc: Sequence[float],
    min_current_a_tsc: Sequence[float],
    max_current_a_tsc: Sequence[float],
    maximum_command_delta_a: float = MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP,
) -> FrozenOneMsPrefixes:
    source = _vector(source_current_a_tsc, "source_current_a_tsc")
    turns = _vector(turns_tsc, "turns_tsc")
    lower = _vector(min_current_a_tsc, "min_current_a_tsc")
    upper = _vector(max_current_a_tsc, "max_current_a_tsc")
    if not 0.0 < float(maximum_command_delta_a) <= MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP:
        raise ContractError("maximum_command_delta_a must be in (0, 0.3]")
    command_center = source if source_command_a_tsc is None else _vector(
        source_command_a_tsc, "source_command_a_tsc"
    )
    q0 = quantize_target(command_center, turns)
    assert_exact_slew(command_center, q0.current_a_tsc, name="command_center_to_q0")
    patterns: dict[str, Card15Target] = {}
    for name, signs in (
        ("pattern_a", tuple(1 if index % 2 == 0 else -1 for index in range(N_COILS))),
        ("pattern_b", tuple(-1 if index % 2 == 0 else 1 for index in range(N_COILS))),
    ):
        fields: list[str] = []
        values: list[float] = []
        for q0_value, center_value, turn, sign in zip(
            q0.current_a_tsc, command_center, turns, signs
        ):
            field, value = _signed_lattice_value(
                q0_value, center_value, turn, sign, maximum_command_delta_a,
            )
            fields.append(field)
            values.append(value)
        target = Card15Target(tuple(fields), tuple(values))
        assert_exact_slew(q0.current_a_tsc, target.current_a_tsc, name=name)
        assert_exact_slew(command_center, target.current_a_tsc, name=f"command_center_to_{name}")
        if max(abs(value - base) for value, base in zip(
                target.current_a_tsc, q0.current_a_tsc)) > maximum_command_delta_a + 1e-12:
            raise ContractError(f"{name} exceeds reserved command slew")
        if any(not low <= value <= high for value, low, high in zip(target.current_a_tsc, lower, upper)):
            raise ContractError(f"{name} exceeds an absolute current limit")
        patterns[name] = target
    hold = (q0,) * NR1_1MS_HORIZON_STEPS
    return FrozenOneMsPrefixes(
        q0=q0,
        prefixes={
            "hold": hold,
            "pattern_a": (patterns["pattern_a"], q0, q0, q0),
            "pattern_b": (patterns["pattern_b"], q0, q0, q0),
        },
    )


@dataclass(frozen=True)
class OneMsNR1SafetyEnvelope:
    source_r_geo_m: float
    source_z_geo_m: float
    source_ip_a: float
    r_radius_m: float = 0.05
    z_radius_m: float = 0.05
    ip_fraction: float = 0.10

    @classmethod
    def from_signal(cls, signal: RGeoZGeoSignal) -> "OneMsNR1SafetyEnvelope":
        return cls(signal.boundary.r_geo_m, signal.boundary.z_geo_m, signal.ip_a)

    def state_reasons(
        self,
        signal: RGeoZGeoSignal,
        current_a_tsc: Sequence[float],
        lower_a_tsc: Sequence[float],
        upper_a_tsc: Sequence[float],
    ) -> tuple[str, ...]:
        actual = _vector(current_a_tsc, "actual_current")
        lower = _vector(lower_a_tsc, "lower_current")
        upper = _vector(upper_a_tsc, "upper_current")
        reasons: list[str] = []
        if any(not low <= value <= high for value, low, high in zip(actual, lower, upper)):
            reasons.append("ACTUAL_CURRENT_LIMIT")
        r_geo, z_geo = signal.boundary.r_geo_m, signal.boundary.z_geo_m
        if not signal.limiter.r_inner_m <= r_geo <= signal.limiter.r_outer_m:
            reasons.append("R_GEO_OUTSIDE_LIMITER")
        if abs(r_geo - self.source_r_geo_m) > self.r_radius_m:
            reasons.append("R_GEO_CAMPAIGN_LIMIT")
        if abs(z_geo - self.source_z_geo_m) > self.z_radius_m:
            reasons.append("Z_GEO_CAMPAIGN_LIMIT")
        if math.copysign(1.0, signal.ip_a) != math.copysign(1.0, self.source_ip_a):
            reasons.append("IP_SIGN")
        if abs(signal.ip_a - self.source_ip_a) > self.ip_fraction * abs(self.source_ip_a):
            reasons.append("IP_CAMPAIGN_LIMIT")
        return tuple(reasons)


def validate_one_ms_config(
    *, start_folder: str, dt_ms: int, slew_a_per_ms: float,
    expected_start_folder: str = "1100ms",
) -> None:
    """Validate one-ms interface campaigns without changing legacy defaults.

    The explicit override exists for separately named takeover identities.  It
    must never be inferred from an old result or used to retime old evidence.
    """
    if start_folder != expected_start_folder:
        raise ContractError(f"NR1 requires the fixed {expected_start_folder} source")
    if dt_ms != CONTROL_PERIOD_MS:
        raise ContractError("NR1 requires dt_ms=1")
    if _decimal(slew_a_per_ms, "current_slew_a_per_ms") != Decimal("0.3"):
        raise ContractError("NR1 requires exact current_slew_a_per_ms=0.3")
