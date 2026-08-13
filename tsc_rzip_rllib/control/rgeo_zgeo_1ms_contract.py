"""Pure NR0 contracts for the 1 ms R_geo/Z_geo control route.

This module does not run TSC, quantize or apply an action, advance a queue,
or implement a controller.  It gives the new route a distinct identity so
the historical 10 ms / 3 A NR0--NR2 evidence cannot be silently reused.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
from typing import Any, Mapping, Sequence

from tsc_rzip_rllib.core.coil_order import TSC_COIL_NAMES

from .rgeo_zgeo_contract import (
    CausalHistory,
    ContractError,
    FIXED_TAKEOVER_TIME_MS,
    IssuedAction,
    RGeoZGeoSignal,
)


ONE_MS_CONTRACT_VERSION = "rgeo-zgeo-1ms-nr0-v1"
CONTROL_PERIOD_MS = 1
MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP = Decimal("0.3")
SINGLE_TURN_CURRENT_UNIT = "A"
COIL_ORDER = "TSC"
N_COILS = len(TSC_COIL_NAMES)


def _strict_fields(payload: Mapping[str, Any], expected: set[str], name: str) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise ContractError(f"missing {name} fields: {sorted(missing)}")
    if unknown:
        raise ContractError(f"unknown {name} fields: {sorted(unknown)}")


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(f"{name} must be a nonnegative integer")
    return value


def _positive_int(value: Any, name: str) -> int:
    result = _nonnegative_int(value, name)
    if result == 0:
        raise ContractError(f"{name} must be positive")
    return result


def _finite_float(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ContractError(f"{name} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ContractError(f"{name} must be finite")
    return result


def _finite_decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ContractError(f"{name} must be finite")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be finite") from exc
    if not result.is_finite():
        raise ContractError(f"{name} must be finite")
    return result


def _single_turn_vector(values: Any, name: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)):
        raise ContractError(f"{name} must be a numeric sequence")
    try:
        result = tuple(_finite_float(value, name) for value in values)
    except TypeError as exc:
        raise ContractError(f"{name} must be a numeric sequence") from exc
    if len(result) != N_COILS:
        raise ContractError(f"{name} must contain {N_COILS} TSC-order values")
    return result


def _assert_at_most_point_three(
    before: Sequence[float], after: Sequence[float], name: str
) -> None:
    for index, (left, right) in enumerate(zip(before, after)):
        delta = abs(
            _finite_decimal(right, f"{name}[{index}].after")
            - _finite_decimal(left, f"{name}[{index}].before")
        )
        if delta > MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP:
            raise ContractError(
                f"{name}[{index}] exceeds the absolute 0.3 A single-turn per-step limit"
            )


@dataclass(frozen=True)
class OneMsControlSpec:
    """Immutable timing/unit/action identity for the restarted route."""

    contract_version: str = ONE_MS_CONTRACT_VERSION
    control_period_ms: int = CONTROL_PERIOD_MS
    max_single_turn_coil_delta_a_per_step: float = 0.3
    full_limit_allowed: bool = True
    single_turn_current_unit: str = SINGLE_TURN_CURRENT_UNIT
    coil_order: str = COIL_ORDER

    def __post_init__(self) -> None:
        if self.contract_version != ONE_MS_CONTRACT_VERSION:
            raise ContractError("unsupported 1 ms contract_version")
        if self.control_period_ms != CONTROL_PERIOD_MS:
            raise ContractError("the restarted route requires a 1 ms control period")
        if _finite_decimal(
            self.max_single_turn_coil_delta_a_per_step,
            "max_single_turn_coil_delta_a_per_step",
        ) != MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP:
            raise ContractError("the restarted route requires an exact 0.3 A per-step cap")
        if self.full_limit_allowed is not True:
            raise ContractError("the exact 0.3 A limit is allowed, not reserved headroom")
        if self.single_turn_current_unit != SINGLE_TURN_CURRENT_UNIT:
            raise ContractError("current limit unit must be single-turn A")
        if self.coil_order != COIL_ORDER:
            raise ContractError("coil vectors must use TSC order")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OneMsControlSpec":
        if not isinstance(payload, Mapping):
            raise ContractError("1 ms control spec must be a mapping")
        expected = {
            "contract_version",
            "control_period_ms",
            "max_single_turn_coil_delta_a_per_step",
            "full_limit_allowed",
            "single_turn_current_unit",
            "coil_order",
        }
        _strict_fields(payload, expected, "1 ms control spec")
        return cls(**dict(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "control_period_ms": self.control_period_ms,
            "max_single_turn_coil_delta_a_per_step": self.max_single_turn_coil_delta_a_per_step,
            "full_limit_allowed": self.full_limit_allowed,
            "single_turn_current_unit": self.single_turn_current_unit,
            "coil_order": self.coil_order,
        }


@dataclass(frozen=True)
class OneMsRGeoZGeoObservation:
    """One same-step boundary-box geometry/Ip observation for this route."""

    signal: RGeoZGeoSignal

    def __post_init__(self) -> None:
        if not isinstance(self.signal, RGeoZGeoSignal):
            raise ContractError("signal must be a fail-closed RGeoZGeoSignal")

    @classmethod
    def from_tsc_state(
        cls, state: Mapping[str, Any], *, midplane_z_m: float = 0.0
    ) -> "OneMsRGeoZGeoObservation":
        return cls(signal=RGeoZGeoSignal.from_tsc_state(state, midplane_z_m=midplane_z_m))

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": ONE_MS_CONTRACT_VERSION,
            "control_period_ms": CONTROL_PERIOD_MS,
            "boundary": self.signal.boundary.to_dict(),
            "limiter": self.signal.limiter.to_dict(),
            "ip_a": self.signal.ip_a,
            "side": self.signal.side,
            "r_geo_minus_r_mid_m": self.signal.r_geo_minus_r_mid_m,
        }


@dataclass(frozen=True)
class OneMsRelativeEndpointCommand:
    delta_r_m: float
    delta_z_m: float
    duration_ms: int
    takeover_time_ms: int = FIXED_TAKEOVER_TIME_MS
    kind: str = "relative_endpoint"

    def __post_init__(self) -> None:
        if self.kind != "relative_endpoint":
            raise ContractError("invalid relative command kind")
        if self.takeover_time_ms != FIXED_TAKEOVER_TIME_MS:
            raise ContractError("new-route commands must start at 1100 ms")
        _positive_int(self.duration_ms, "duration_ms")
        object.__setattr__(self, "delta_r_m", _finite_float(self.delta_r_m, "delta_r_m"))
        object.__setattr__(self, "delta_z_m", _finite_float(self.delta_z_m, "delta_z_m"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": ONE_MS_CONTRACT_VERSION,
            "kind": self.kind,
            "takeover_time_ms": self.takeover_time_ms,
            "duration_ms": self.duration_ms,
            "delta_r_m": self.delta_r_m,
            "delta_z_m": self.delta_z_m,
        }


@dataclass(frozen=True)
class OneMsWaypoint:
    elapsed_ms: int
    r_geo_m: float
    z_geo_m: float

    def __post_init__(self) -> None:
        _nonnegative_int(self.elapsed_ms, "waypoint.elapsed_ms")
        object.__setattr__(self, "r_geo_m", _finite_float(self.r_geo_m, "waypoint.r_geo_m"))
        object.__setattr__(self, "z_geo_m", _finite_float(self.z_geo_m, "waypoint.z_geo_m"))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OneMsWaypoint":
        if not isinstance(payload, Mapping):
            raise ContractError("waypoint must be a mapping")
        _strict_fields(payload, {"elapsed_ms", "r_geo_m", "z_geo_m"}, "waypoint")
        return cls(**dict(payload))

    def to_dict(self) -> dict[str, Any]:
        return {"elapsed_ms": self.elapsed_ms, "r_geo_m": self.r_geo_m, "z_geo_m": self.z_geo_m}


@dataclass(frozen=True)
class OneMsWaypointPathCommand:
    duration_ms: int
    waypoints: tuple[OneMsWaypoint, ...]
    takeover_time_ms: int = FIXED_TAKEOVER_TIME_MS
    kind: str = "waypoint_path"

    def __post_init__(self) -> None:
        if self.kind != "waypoint_path":
            raise ContractError("invalid waypoint command kind")
        if self.takeover_time_ms != FIXED_TAKEOVER_TIME_MS:
            raise ContractError("new-route commands must start at 1100 ms")
        duration = _positive_int(self.duration_ms, "duration_ms")
        if len(self.waypoints) < 2 or not all(
            isinstance(item, OneMsWaypoint) for item in self.waypoints
        ):
            raise ContractError("a waypoint path requires at least two valid waypoints")
        elapsed = tuple(item.elapsed_ms for item in self.waypoints)
        if elapsed[0] != 0 or elapsed[-1] != duration:
            raise ContractError("waypoints must begin at 0 and end at duration_ms")
        if any(right <= left for left, right in zip(elapsed, elapsed[1:])):
            raise ContractError("waypoint elapsed_ms values must be strictly increasing")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": ONE_MS_CONTRACT_VERSION,
            "kind": self.kind,
            "takeover_time_ms": self.takeover_time_ms,
            "duration_ms": self.duration_ms,
            "waypoints": [item.to_dict() for item in self.waypoints],
        }


def parse_one_ms_command(
    payload: Mapping[str, Any],
) -> OneMsRelativeEndpointCommand | OneMsWaypointPathCommand:
    if not isinstance(payload, Mapping):
        raise ContractError("command must be a mapping")
    if payload.get("contract_version") != ONE_MS_CONTRACT_VERSION:
        raise ContractError("unsupported command contract_version")
    common = {"contract_version", "kind", "takeover_time_ms", "duration_ms"}
    kind = payload.get("kind")
    if kind == "relative_endpoint":
        _strict_fields(payload, common | {"delta_r_m", "delta_z_m"}, "relative command")
        return OneMsRelativeEndpointCommand(
            delta_r_m=payload["delta_r_m"],
            delta_z_m=payload["delta_z_m"],
            duration_ms=payload["duration_ms"],
            takeover_time_ms=payload["takeover_time_ms"],
            kind=kind,
        )
    if kind == "waypoint_path":
        _strict_fields(payload, common | {"waypoints"}, "waypoint command")
        if isinstance(payload["waypoints"], (str, bytes)):
            raise ContractError("waypoints must be a sequence")
        try:
            waypoints = tuple(OneMsWaypoint.from_mapping(item) for item in payload["waypoints"])
        except TypeError as exc:
            raise ContractError("waypoints must be a sequence of mappings") from exc
        return OneMsWaypointPathCommand(
            duration_ms=payload["duration_ms"],
            waypoints=waypoints,
            takeover_time_ms=payload["takeover_time_ms"],
            kind=kind,
        )
    raise ContractError("command kind must be relative_endpoint or waypoint_path")


@dataclass(frozen=True)
class OneMsIssuedTargetSlew:
    """Hard-slew evidence for one already serialized NR0 issued action."""

    action: IssuedAction
    causal_baseline_current_a_tsc: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.action, IssuedAction):
            raise ContractError("action must be IssuedAction")
        baseline = _single_turn_vector(
            self.causal_baseline_current_a_tsc, "causal_baseline_current_a_tsc"
        )
        object.__setattr__(self, "causal_baseline_current_a_tsc", baseline)
        _assert_at_most_point_three(
            baseline,
            self.action.quantized_target_current_a_tsc,
            "issued single-turn target delta",
        )

    @property
    def action_id(self) -> str:
        return self.action.action_id

    @property
    def maximum_absolute_delta_a(self) -> float:
        return max(
            abs(float(right) - float(left))
            for left, right in zip(
                self.causal_baseline_current_a_tsc,
                self.action.quantized_target_current_a_tsc,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.to_dict(),
            "causal_baseline_current_a_tsc": list(self.causal_baseline_current_a_tsc),
            "maximum_absolute_delta_a": self.maximum_absolute_delta_a,
            "limit_a_per_step": 0.3,
            "full_limit_allowed": True,
        }


@dataclass(frozen=True)
class OneMsCausalHistory:
    """A historical NR0 causal record qualified for the restarted 1 ms route."""

    history: CausalHistory
    issued_target_slew: tuple[OneMsIssuedTargetSlew, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.history, CausalHistory):
            raise ContractError("history must be CausalHistory")
        records = {record.action_id: record for record in self.issued_target_slew}
        if len(records) != len(self.issued_target_slew):
            raise ContractError("each issued action requires exactly one unique slew record")

        issued: dict[str, tuple[Any, IssuedAction]] = {}
        previous = None
        for frame in self.history.frames:
            expected_time_ms = FIXED_TAKEOVER_TIME_MS + frame.step_index * CONTROL_PERIOD_MS
            if frame.signal.boundary.time_ms != expected_time_ms:
                raise ContractError("1 ms history timestamps must equal 1100 ms + step_index")
            if frame.step_index == 0:
                if frame.sample_interval_ms is not None:
                    raise ContractError("initial 1 ms frame cannot have a sample interval")
            elif frame.sample_interval_ms != CONTROL_PERIOD_MS:
                raise ContractError("every post-start history frame must have sample_interval_ms=1")
            if previous is not None:
                _assert_at_most_point_three(
                    previous.actual_coil_current_a_tsc,
                    frame.actual_coil_current_a_tsc,
                    "observed single-turn current delta",
                )
            if frame.issued_action is not None:
                issued[frame.issued_action.action_id] = (frame, frame.issued_action)
            previous = frame

        if set(records) != set(issued):
            raise ContractError("slew records must match all and only issued action identifiers")
        for action_id, (frame, action) in issued.items():
            record = records[action_id]
            if record.action != action:
                raise ContractError("slew record action must equal the causal issued action")
            for index, (claimed, observed) in enumerate(
                zip(record.causal_baseline_current_a_tsc, frame.actual_coil_current_a_tsc)
            ):
                if _finite_decimal(claimed, f"baseline[{index}]") != _finite_decimal(
                    observed, f"observed[{index}]"
                ):
                    raise ContractError("slew baseline must equal same-frame causal current readback")

    def to_dict(self) -> dict[str, Any]:
        payload = self.history.to_dict()
        payload["contract_version"] = ONE_MS_CONTRACT_VERSION
        for frame in payload["frames"]:
            frame["signal"]["contract_version"] = ONE_MS_CONTRACT_VERSION
        payload["control_spec"] = OneMsControlSpec().to_dict()
        payload["issued_target_slew"] = [record.to_dict() for record in self.issued_target_slew]
        return payload
