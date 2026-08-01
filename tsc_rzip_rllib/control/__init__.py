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
]
