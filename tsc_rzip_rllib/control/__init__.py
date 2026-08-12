"""Causal, fail-closed control interfaces.

This package contains software contracts only.  Importing it does not start
TSC, Ray, a controller, or any plant process.
"""

from .causal_observer import CausalRestartObserverState, VelocityEstimate
from .quantized_actuator import (
    DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC,
    T13S2R1_REPORT_SHA256,
    QuantizedActuatorModel,
    QuantizedActuatorResult,
)
from .transition_tube import (
    AdditiveResponseTube,
    AffineTransitionHypothesis,
    SetValuedTransitionModel,
    TransitionPrediction,
)
from .rgeo_zgeo_contract import (
    CONTRACT_VERSION,
    FIXED_TAKEOVER_TIME_MS,
    BoundaryBoxGeometry,
    CausalHistory,
    CausalHistoryFrame,
    ContractError,
    DataIdentity,
    IssuedAction,
    IpConstraintContract,
    LimiterMidplaneGeometry,
    QueueEntry,
    RelativeEndpointCommand,
    RGeoZGeoSignal,
    RGeoZGeoWaypoint,
    WaypointPathCommand,
    parse_rgeo_zgeo_command,
)

__all__ = [
    "AdditiveResponseTube",
    "AffineTransitionHypothesis",
    "CausalRestartObserverState",
    "DEVELOPMENT_READBACK_BIAS_GRID_UNITS_TSC",
    "QuantizedActuatorModel",
    "QuantizedActuatorResult",
    "SetValuedTransitionModel",
    "T13S2R1_REPORT_SHA256",
    "TransitionPrediction",
    "VelocityEstimate",
    "CONTRACT_VERSION",
    "FIXED_TAKEOVER_TIME_MS",
    "BoundaryBoxGeometry",
    "CausalHistory",
    "CausalHistoryFrame",
    "ContractError",
    "DataIdentity",
    "IssuedAction",
    "IpConstraintContract",
    "LimiterMidplaneGeometry",
    "QueueEntry",
    "RelativeEndpointCommand",
    "RGeoZGeoSignal",
    "RGeoZGeoWaypoint",
    "WaypointPathCommand",
    "parse_rgeo_zgeo_command",
]
