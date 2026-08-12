"""Pure NR0 contracts for boundary-center trajectory control.

This module validates signals and records only.  It does not start TSC, alter
an actuator command, advance a delay queue, or implement a controller.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Mapping, Sequence

from tsc_rzip_rllib.core.coil_order import TSC_COIL_NAMES


CONTRACT_VERSION = "rgeo-zgeo-nr0-v1"
FIXED_TAKEOVER_TIME_MS = 1100
N_COILS = len(TSC_COIL_NAMES)
_CARD15_FIELD = re.compile(r"^[ +-]?\d\.\d{3}E[+-]\d{2} ?$")


class ContractError(ValueError):
    """A fail-closed NR0 contract violation."""


def _strict_fields(payload: Mapping[str, Any], expected: set[str], name: str) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise ContractError(f"missing {name} fields: {sorted(missing)}")
    if unknown:
        raise ContractError(f"unknown {name} fields: {sorted(unknown)}")


def _finite(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ContractError(f"{name} must be finite")
    return result


def _finite_vector(values: Any, length: int | None, name: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)):
        raise ContractError(f"{name} must be a numeric sequence")
    try:
        result = tuple(_finite(value, name) for value in values)
    except TypeError as exc:
        raise ContractError(f"{name} must be a numeric sequence") from exc
    if length is not None and len(result) != length:
        raise ContractError(f"{name} must contain {length} values")
    return result


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(f"{name} must be a nonnegative integer")
    return value


def _positive_int(value: Any, name: str) -> int:
    result = _nonnegative_int(value, name)
    if result == 0:
        raise ContractError(f"{name} must be positive")
    return result


@dataclass(frozen=True)
class BoundaryBoxGeometry:
    """Bounding box from one paired plasma-boundary outline."""

    time_ms: int
    point_count: int
    r_boundary_min_m: float
    r_boundary_max_m: float
    z_boundary_min_m: float
    z_boundary_max_m: float
    source: str = "state.gfile.boundary_R/boundary_Z"

    def __post_init__(self) -> None:
        _nonnegative_int(self.time_ms, "boundary.time_ms")
        if self.point_count < 4:
            raise ContractError("a plasma boundary must contain at least four paired points")
        values = tuple(
            _finite(value, name)
            for value, name in (
                (self.r_boundary_min_m, "r_boundary_min_m"),
                (self.r_boundary_max_m, "r_boundary_max_m"),
                (self.z_boundary_min_m, "z_boundary_min_m"),
                (self.z_boundary_max_m, "z_boundary_max_m"),
            )
        )
        if values[0] >= values[1] or values[2] >= values[3]:
            raise ContractError("plasma-boundary bounding box must have positive width and height")
        if self.source != "state.gfile.boundary_R/boundary_Z":
            raise ContractError("unsupported plasma-boundary source")

    @property
    def r_geo_m(self) -> float:
        return 0.5 * (self.r_boundary_min_m + self.r_boundary_max_m)

    @property
    def z_geo_m(self) -> float:
        return 0.5 * (self.z_boundary_min_m + self.z_boundary_max_m)

    @classmethod
    def from_paired_points(
        cls, *, time_ms: int, r_boundary_m: Any, z_boundary_m: Any
    ) -> "BoundaryBoxGeometry":
        r_values = _finite_vector(r_boundary_m, None, "boundary_R")
        z_values = _finite_vector(z_boundary_m, None, "boundary_Z")
        if len(r_values) != len(z_values):
            raise ContractError("boundary_R and boundary_Z must be paired and equal-length")
        if len(r_values) < 4:
            raise ContractError("a plasma boundary must contain at least four paired points")
        return cls(
            time_ms=_nonnegative_int(time_ms, "boundary.time_ms"),
            point_count=len(r_values),
            r_boundary_min_m=min(r_values),
            r_boundary_max_m=max(r_values),
            z_boundary_min_m=min(z_values),
            z_boundary_max_m=max(z_values),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_ms": self.time_ms,
            "point_count": self.point_count,
            "r_boundary_min_m": self.r_boundary_min_m,
            "r_boundary_max_m": self.r_boundary_max_m,
            "z_boundary_min_m": self.z_boundary_min_m,
            "z_boundary_max_m": self.z_boundary_max_m,
            "r_geo_m": self.r_geo_m,
            "z_geo_m": self.z_geo_m,
            "source": self.source,
        }


@dataclass(frozen=True)
class LimiterMidplaneGeometry:
    midplane_z_m: float
    r_inner_m: float
    r_outer_m: float

    def __post_init__(self) -> None:
        midplane = _finite(self.midplane_z_m, "midplane_z_m")
        inner = _finite(self.r_inner_m, "r_inner_m")
        outer = _finite(self.r_outer_m, "r_outer_m")
        if inner >= outer:
            raise ContractError("inner limiter radius must be below outer limiter radius")
        object.__setattr__(self, "midplane_z_m", midplane)
        object.__setattr__(self, "r_inner_m", inner)
        object.__setattr__(self, "r_outer_m", outer)

    @property
    def r_mid_m(self) -> float:
        return 0.5 * (self.r_inner_m + self.r_outer_m)

    @classmethod
    def from_paired_trace(
        cls, *, limiter_r_m: Any, limiter_z_m: Any, midplane_z_m: float = 0.0
    ) -> "LimiterMidplaneGeometry":
        r_values = _finite_vector(limiter_r_m, None, "limiter_R")
        z_values = _finite_vector(limiter_z_m, None, "limiter_Z")
        if len(r_values) != len(z_values):
            raise ContractError("limiter_R and limiter_Z must be paired and equal-length")
        if len(r_values) < 3:
            raise ContractError("limiter trace must contain at least three paired points")
        z_mid = _finite(midplane_z_m, "midplane_z_m")
        points = list(zip(r_values, z_values))
        if points[0] != points[-1]:
            points.append(points[0])
        intersections: list[float] = []
        for (r0, z0), (r1, z1) in zip(points, points[1:]):
            d0, d1 = z0 - z_mid, z1 - z_mid
            if d0 == 0.0 and d1 == 0.0:
                intersections.extend((r0, r1))
            elif d0 == 0.0:
                intersections.append(r0)
            elif d1 == 0.0:
                intersections.append(r1)
            elif d0 * d1 < 0.0:
                fraction = (z_mid - z0) / (z1 - z0)
                intersections.append(r0 + fraction * (r1 - r0))
        unique = sorted({round(value, 14) for value in intersections})
        if len(unique) < 2 or unique[0] >= unique[-1]:
            raise ContractError("limiter trace has no valid inner/outer midplane intersections")
        return cls(midplane_z_m=z_mid, r_inner_m=unique[0], r_outer_m=unique[-1])

    def to_dict(self) -> dict[str, float]:
        return {
            "midplane_z_m": self.midplane_z_m,
            "r_inner_m": self.r_inner_m,
            "r_outer_m": self.r_outer_m,
            "r_mid_m": self.r_mid_m,
        }


@dataclass(frozen=True)
class RGeoZGeoSignal:
    """One fail-closed, same-step geometry/Ip observation."""

    boundary: BoundaryBoxGeometry
    limiter: LimiterMidplaneGeometry
    ip_a: float

    def __post_init__(self) -> None:
        if not isinstance(self.boundary, BoundaryBoxGeometry):
            raise ContractError("boundary must be BoundaryBoxGeometry")
        if not isinstance(self.limiter, LimiterMidplaneGeometry):
            raise ContractError("limiter must be LimiterMidplaneGeometry")
        object.__setattr__(self, "ip_a", _finite(self.ip_a, "ip_a"))

    @property
    def side(self) -> str:
        return "HFS" if self.boundary.r_geo_m < self.limiter.r_mid_m else "LFS"

    @property
    def r_geo_minus_r_mid_m(self) -> float:
        return self.boundary.r_geo_m - self.limiter.r_mid_m

    @classmethod
    def from_tsc_state(
        cls, state: Mapping[str, Any], *, midplane_z_m: float = 0.0
    ) -> "RGeoZGeoSignal":
        if not isinstance(state, Mapping):
            raise ContractError("TSC state must be a mapping")
        if bool(state.get("abnormal", False)):
            raise ContractError("abnormal TSC state cannot provide a valid geometry signal")
        if "time_ms" not in state or "Ip" not in state or "gfile" not in state:
            raise ContractError("TSC state is missing time_ms, Ip, or gfile")
        time_ms = _nonnegative_int(state["time_ms"], "state.time_ms")
        gfile = state["gfile"]
        if not isinstance(gfile, Mapping):
            raise ContractError("state.gfile must be a mapping")
        required = {"boundary_R", "boundary_Z", "limiter_R", "limiter_Z", "ip"}
        missing = required - set(gfile)
        if missing:
            raise ContractError(f"state.gfile is missing required fields: {sorted(missing)}")
        state_ip = _finite(state["Ip"], "state.Ip")
        gfile_ip = _finite(gfile["ip"], "state.gfile.ip")
        if state_ip != gfile_ip:
            raise ContractError("state.Ip and state.gfile.ip must identify the same step")
        boundary = BoundaryBoxGeometry.from_paired_points(
            time_ms=time_ms,
            r_boundary_m=gfile["boundary_R"],
            z_boundary_m=gfile["boundary_Z"],
        )
        limiter = LimiterMidplaneGeometry.from_paired_trace(
            limiter_r_m=gfile["limiter_R"],
            limiter_z_m=gfile["limiter_Z"],
            midplane_z_m=midplane_z_m,
        )
        return cls(boundary=boundary, limiter=limiter, ip_a=state_ip)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "boundary": self.boundary.to_dict(),
            "limiter": self.limiter.to_dict(),
            "ip_a": self.ip_a,
            "side": self.side,
            "r_geo_minus_r_mid_m": self.r_geo_minus_r_mid_m,
        }


@dataclass(frozen=True)
class IpConstraintContract:
    """Ip is observed/regulatable/safety-critical, never user-commanded here."""

    soft_reference_a: float
    soft_tolerance_a: float
    hard_min_a: float
    hard_max_a: float

    def __post_init__(self) -> None:
        reference = _finite(self.soft_reference_a, "soft_reference_a")
        tolerance = _finite(self.soft_tolerance_a, "soft_tolerance_a")
        hard_min = _finite(self.hard_min_a, "hard_min_a")
        hard_max = _finite(self.hard_max_a, "hard_max_a")
        if tolerance <= 0.0:
            raise ContractError("soft_tolerance_a must be positive")
        if hard_min >= hard_max:
            raise ContractError("hard Ip limits must be ordered")
        if not hard_min <= reference <= hard_max:
            raise ContractError("soft Ip reference must lie inside hard limits")
        object.__setattr__(self, "soft_reference_a", reference)
        object.__setattr__(self, "soft_tolerance_a", tolerance)
        object.__setattr__(self, "hard_min_a", hard_min)
        object.__setattr__(self, "hard_max_a", hard_max)

    def validate_observation(self, ip_a: float) -> bool:
        """Return hard-band membership; non-finite observations fail closed."""
        value = _finite(ip_a, "ip_a")
        return self.hard_min_a <= value <= self.hard_max_a

    def to_dict(self) -> dict[str, float]:
        return {
            "soft_reference_a": self.soft_reference_a,
            "soft_tolerance_a": self.soft_tolerance_a,
            "hard_min_a": self.hard_min_a,
            "hard_max_a": self.hard_max_a,
        }


@dataclass(frozen=True)
class RelativeEndpointCommand:
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
        object.__setattr__(self, "delta_r_m", _finite(self.delta_r_m, "delta_r_m"))
        object.__setattr__(self, "delta_z_m", _finite(self.delta_z_m, "delta_z_m"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "kind": self.kind,
            "takeover_time_ms": self.takeover_time_ms,
            "duration_ms": self.duration_ms,
            "delta_r_m": self.delta_r_m,
            "delta_z_m": self.delta_z_m,
        }


@dataclass(frozen=True)
class RGeoZGeoWaypoint:
    elapsed_ms: int
    r_geo_m: float
    z_geo_m: float

    def __post_init__(self) -> None:
        _nonnegative_int(self.elapsed_ms, "waypoint.elapsed_ms")
        object.__setattr__(self, "r_geo_m", _finite(self.r_geo_m, "waypoint.r_geo_m"))
        object.__setattr__(self, "z_geo_m", _finite(self.z_geo_m, "waypoint.z_geo_m"))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RGeoZGeoWaypoint":
        _strict_fields(payload, {"elapsed_ms", "r_geo_m", "z_geo_m"}, "waypoint")
        return cls(**dict(payload))

    def to_dict(self) -> dict[str, Any]:
        return {"elapsed_ms": self.elapsed_ms, "r_geo_m": self.r_geo_m, "z_geo_m": self.z_geo_m}


@dataclass(frozen=True)
class WaypointPathCommand:
    duration_ms: int
    waypoints: tuple[RGeoZGeoWaypoint, ...]
    takeover_time_ms: int = FIXED_TAKEOVER_TIME_MS
    kind: str = "waypoint_path"

    def __post_init__(self) -> None:
        if self.kind != "waypoint_path":
            raise ContractError("invalid waypoint command kind")
        if self.takeover_time_ms != FIXED_TAKEOVER_TIME_MS:
            raise ContractError("new-route commands must start at 1100 ms")
        duration = _positive_int(self.duration_ms, "duration_ms")
        if len(self.waypoints) < 2 or not all(
            isinstance(item, RGeoZGeoWaypoint) for item in self.waypoints
        ):
            raise ContractError("a waypoint path requires at least two valid waypoints")
        elapsed = tuple(item.elapsed_ms for item in self.waypoints)
        if elapsed[0] != 0 or elapsed[-1] != duration:
            raise ContractError("waypoints must begin at 0 and end at duration_ms")
        if any(right <= left for left, right in zip(elapsed, elapsed[1:])):
            raise ContractError("waypoint elapsed_ms values must be strictly increasing")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "kind": self.kind,
            "takeover_time_ms": self.takeover_time_ms,
            "duration_ms": self.duration_ms,
            "waypoints": [item.to_dict() for item in self.waypoints],
        }


def parse_rgeo_zgeo_command(
    payload: Mapping[str, Any],
) -> RelativeEndpointCommand | WaypointPathCommand:
    if not isinstance(payload, Mapping):
        raise ContractError("command must be a mapping")
    kind = payload.get("kind")
    common = {"contract_version", "kind", "takeover_time_ms", "duration_ms"}
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise ContractError("unsupported command contract_version")
    if kind == "relative_endpoint":
        _strict_fields(payload, common | {"delta_r_m", "delta_z_m"}, "relative command")
        return RelativeEndpointCommand(
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
            waypoints = tuple(RGeoZGeoWaypoint.from_mapping(item) for item in payload["waypoints"])
        except TypeError as exc:
            raise ContractError("waypoints must be a sequence of mappings") from exc
        return WaypointPathCommand(
            duration_ms=payload["duration_ms"],
            waypoints=waypoints,
            takeover_time_ms=payload["takeover_time_ms"],
            kind=kind,
        )
    raise ContractError("command kind must be relative_endpoint or waypoint_path")


@dataclass(frozen=True)
class DataIdentity:
    campaign_id: str
    intended_use: str
    declared_before_collection: bool
    source_revision: str

    def __post_init__(self) -> None:
        if not self.campaign_id or not self.source_revision:
            raise ContractError("campaign_id and source_revision must be nonempty")
        allowed = {"synthetic_fixture", "interface_validation", "identification", "oracle", "expert", "learning", "evaluation"}
        if self.intended_use not in allowed:
            raise ContractError("invalid intended_use")
        if self.declared_before_collection is not True:
            raise ContractError("data purpose must be declared before collection")

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "intended_use": self.intended_use,
            "declared_before_collection": self.declared_before_collection,
            "source_revision": self.source_revision,
        }


@dataclass(frozen=True)
class IssuedAction:
    action_id: str
    issue_step: int
    issue_time_ms: int
    issued_action_norm_tsc: tuple[float, ...]
    serialized_card15_fields: tuple[str, ...]
    quantized_target_current_a_tsc: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ContractError("action_id must be nonempty")
        _nonnegative_int(self.issue_step, "issue_step")
        _nonnegative_int(self.issue_time_ms, "issue_time_ms")
        object.__setattr__(self, "issued_action_norm_tsc", _finite_vector(self.issued_action_norm_tsc, N_COILS, "issued_action_norm_tsc"))
        fields = tuple(str(value) for value in self.serialized_card15_fields)
        if len(fields) != N_COILS or any(_CARD15_FIELD.fullmatch(value) is None for value in fields):
            raise ContractError("serialized_card15_fields must contain 14 exact .3E fields")
        object.__setattr__(self, "serialized_card15_fields", fields)
        object.__setattr__(self, "quantized_target_current_a_tsc", _finite_vector(self.quantized_target_current_a_tsc, N_COILS, "quantized_target_current_a_tsc"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "issue_step": self.issue_step,
            "issue_time_ms": self.issue_time_ms,
            "issued_action_norm_tsc": list(self.issued_action_norm_tsc),
            "serialized_card15_fields": list(self.serialized_card15_fields),
            "quantized_target_current_a_tsc": list(self.quantized_target_current_a_tsc),
        }


@dataclass(frozen=True)
class QueueEntry:
    action_id: str
    age_steps: int

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ContractError("queue action_id must be nonempty")
        _nonnegative_int(self.age_steps, "queue.age_steps")

    def to_dict(self) -> dict[str, Any]:
        return {"action_id": self.action_id, "age_steps": self.age_steps}


@dataclass(frozen=True)
class CausalHistoryFrame:
    step_index: int
    sample_interval_ms: int | None
    signal: RGeoZGeoSignal
    actual_coil_current_a_tsc: tuple[float, ...]
    passive_current_status: str
    passive_current_a: tuple[float, ...]
    missing_observation_fields: tuple[str, ...]
    belief_sequence_id: str
    issued_action: IssuedAction | None
    delay_queue_after_issue: tuple[QueueEntry, ...]
    applied_action_id: str | None
    applied_action_age_steps: int | None
    applied_current_delta_a_tsc: tuple[float, ...] | None

    def __post_init__(self) -> None:
        _nonnegative_int(self.step_index, "step_index")
        if self.sample_interval_ms is not None:
            _positive_int(self.sample_interval_ms, "sample_interval_ms")
        if not isinstance(self.signal, RGeoZGeoSignal):
            raise ContractError("signal must be RGeoZGeoSignal")
        object.__setattr__(self, "actual_coil_current_a_tsc", _finite_vector(self.actual_coil_current_a_tsc, N_COILS, "actual_coil_current_a_tsc"))
        if self.passive_current_status not in {"available", "unavailable"}:
            raise ContractError("passive_current_status must be available or unavailable")
        passive = _finite_vector(self.passive_current_a, None, "passive_current_a")
        if self.passive_current_status == "available" and not passive:
            raise ContractError("available passive current must contain data")
        if self.passive_current_status == "unavailable" and passive:
            raise ContractError("unavailable passive current must be empty")
        object.__setattr__(self, "passive_current_a", passive)
        missing = tuple(str(value) for value in self.missing_observation_fields)
        if any(not value for value in missing):
            raise ContractError("missing observation field names must be nonempty")
        object.__setattr__(self, "missing_observation_fields", missing)
        if not self.belief_sequence_id:
            raise ContractError("belief_sequence_id must be nonempty")
        if self.issued_action is not None and not isinstance(self.issued_action, IssuedAction):
            raise ContractError("issued_action must be IssuedAction or None")
        if not all(isinstance(value, QueueEntry) for value in self.delay_queue_after_issue):
            raise ContractError("delay queue must contain QueueEntry values")
        queue_ids = tuple(value.action_id for value in self.delay_queue_after_issue)
        if len(queue_ids) != len(set(queue_ids)):
            raise ContractError("delay queue action identifiers must be unique")
        if (self.applied_action_id is None) != (self.applied_action_age_steps is None):
            raise ContractError("applied action id and age must be present together")
        if self.applied_action_age_steps is not None:
            _nonnegative_int(self.applied_action_age_steps, "applied_action_age_steps")
        delta = None if self.applied_current_delta_a_tsc is None else _finite_vector(self.applied_current_delta_a_tsc, N_COILS, "applied_current_delta_a_tsc")
        object.__setattr__(self, "applied_current_delta_a_tsc", delta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "elapsed_since_takeover_ms": self.signal.boundary.time_ms - FIXED_TAKEOVER_TIME_MS,
            "sample_interval_ms": self.sample_interval_ms,
            "signal": self.signal.to_dict(),
            "actual_coil_current_a_tsc": list(self.actual_coil_current_a_tsc),
            "passive_current_status": self.passive_current_status,
            "passive_current_a": list(self.passive_current_a),
            "missing_observation_fields": list(self.missing_observation_fields),
            "belief_sequence_id": self.belief_sequence_id,
            "issued_action": None if self.issued_action is None else self.issued_action.to_dict(),
            "delay_queue_after_issue": [value.to_dict() for value in self.delay_queue_after_issue],
            "applied_action_id": self.applied_action_id,
            "applied_action_age_steps": self.applied_action_age_steps,
            "applied_current_delta_a_tsc": None if self.applied_current_delta_a_tsc is None else list(self.applied_current_delta_a_tsc),
        }


@dataclass(frozen=True)
class CausalHistory:
    identity: DataIdentity
    frames: tuple[CausalHistoryFrame, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DataIdentity):
            raise ContractError("identity must be DataIdentity")
        if not self.frames or not all(isinstance(frame, CausalHistoryFrame) for frame in self.frames):
            raise ContractError("history must contain at least one valid frame")
        if self.frames[0].step_index != 0 or self.frames[0].signal.boundary.time_ms != FIXED_TAKEOVER_TIME_MS:
            raise ContractError("history must start at step 0 and 1100 ms")
        belief_id = self.frames[0].belief_sequence_id
        issued: dict[str, IssuedAction] = {}
        previous: CausalHistoryFrame | None = None
        for frame in self.frames:
            if frame.belief_sequence_id != belief_id:
                raise ContractError("belief/history state must not reset, including at R_mid crossings")
            if previous is not None:
                if frame.step_index != previous.step_index + 1:
                    raise ContractError("history step indices must be consecutive")
                if frame.signal.boundary.time_ms <= previous.signal.boundary.time_ms:
                    raise ContractError("history timestamps must be strictly increasing")
                actual_dt = frame.signal.boundary.time_ms - previous.signal.boundary.time_ms
                if frame.sample_interval_ms != actual_dt:
                    raise ContractError("sample_interval_ms must match consecutive timestamps")
                if frame.applied_current_delta_a_tsc is None:
                    raise ContractError("post-start frames require applied current deltas")
                expected = tuple(now - old for now, old in zip(frame.actual_coil_current_a_tsc, previous.actual_coil_current_a_tsc))
                if any(abs(value - target) > 1e-9 for value, target in zip(frame.applied_current_delta_a_tsc, expected)):
                    raise ContractError("applied current delta must match consecutive readback currents")
            else:
                if frame.sample_interval_ms is not None:
                    raise ContractError("the initial frame cannot have a sample interval")
                if frame.applied_current_delta_a_tsc is not None:
                    raise ContractError("the initial frame cannot claim a prior current delta")
            if frame.issued_action is not None:
                action = frame.issued_action
                if action.action_id in issued:
                    raise ContractError("issued action identifiers must be unique")
                if action.issue_step != frame.step_index or action.issue_time_ms != frame.signal.boundary.time_ms:
                    raise ContractError("issued action step/time must match its causal frame")
                issued[action.action_id] = action
            for entry in frame.delay_queue_after_issue:
                if entry.action_id not in issued:
                    raise ContractError("delay queue references an unknown or future action")
                if entry.age_steps != frame.step_index - issued[entry.action_id].issue_step:
                    raise ContractError("delay queue action age is inconsistent")
            queue_issue_steps = tuple(issued[entry.action_id].issue_step for entry in frame.delay_queue_after_issue)
            if queue_issue_steps != tuple(sorted(queue_issue_steps)):
                raise ContractError("delay queue must preserve issue order")
            if frame.applied_action_id is not None:
                if frame.applied_action_id not in issued:
                    raise ContractError("applied action references an unknown or future action")
                expected_age = frame.step_index - issued[frame.applied_action_id].issue_step
                if frame.applied_action_age_steps != expected_age:
                    raise ContractError("applied action age is inconsistent")
            previous = frame

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "identity": self.identity.to_dict(),
            "frames": [frame.to_dict() for frame in self.frames],
        }
