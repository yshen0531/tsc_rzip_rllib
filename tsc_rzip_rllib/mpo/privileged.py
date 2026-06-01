from __future__ import annotations

from typing import Any, Iterable

import numpy as np


DEFAULT_PRIVILEGED_KEYS = [
    "R_error_norm",
    "Z_error_norm",
    "Ip_error_norm",
    "velocity_norm",
    "vessel_current_total_a",
    "vessel_current_signed_sum_a",
    "vessel_current_abs_sum_a",
    "vessel_current_rms_a",
    "vessel_current_max_abs_a",
    "current_util_max",
    "episode_max_abs_R_error",
    "episode_max_abs_Z_error",
    "episode_max_abs_Ip_error",
    "episode_max_current_util",
    "episode_max_velocity_norm",
    "episode_max_vessel_total_abs_a",
    "episode_max_vessel_abs_sum_a",
    "raw_progress",
    "error_growth",
    "tracking_penalty",
    "hold_weight",
]

DEFAULT_PRIVILEGED_SCALES = {
    "vessel_current_total_a": 1.0e5,
    "vessel_current_signed_sum_a": 1.0e5,
    "vessel_current_abs_sum_a": 1.0e5,
    "vessel_current_rms_a": 1.0e5,
    "vessel_current_max_abs_a": 1.0e5,
    "episode_max_vessel_total_abs_a": 1.0e5,
    "episode_max_vessel_abs_sum_a": 1.0e5,
    "tracking_penalty": 100.0,
    "error_growth": 10.0,
    "raw_progress": 10.0,
}


def _as_scalar(value: Any) -> float:
    """Best-effort scalar extraction from env info values."""
    try:
        arr = np.asarray(value, dtype=np.float32)
        if arr.size == 0:
            return 0.0
        return float(arr.reshape(-1)[0])
    except Exception:
        return 0.0


def build_privileged_vector(
    info: dict[str, Any] | None,
    *,
    keys: Iterable[str] | None = None,
    scales: dict[str, float] | None = None,
    include_currents: bool = True,
    current_scale_a: float = 1000.0,
    clip: float = 50.0,
) -> np.ndarray:
    """Build critic-only privileged vector from TSC/RZIP env info.

    Actor must not receive this vector.  Critic can use it during training,
    matching the asymmetric actor-critic design recommended for tokamak POMDPs.
    """
    info = info or {}
    keys = list(keys or DEFAULT_PRIVILEGED_KEYS)
    scales = dict(DEFAULT_PRIVILEGED_SCALES | dict(scales or {}))

    vals: list[float] = []
    for key in keys:
        val = _as_scalar(info.get(key, 0.0))
        scale = float(scales.get(key, 1.0))
        if abs(scale) > 1.0e-12:
            val /= scale
        vals.append(val)

    if include_currents:
        for k in ["currents_a_tsc", "currents_a_display"]:
            raw = info.get(k, None)
            if raw is None:
                vals.extend([0.0] * 14)
            else:
                arr = np.asarray(raw, dtype=np.float32).reshape(-1)
                if arr.size < 14:
                    arr = np.pad(arr, (0, 14 - arr.size), mode="constant")
                vals.extend((arr[:14] / float(current_scale_a)).tolist())

    out = np.asarray(vals, dtype=np.float32)
    out = np.nan_to_num(out, nan=0.0, posinf=clip, neginf=-clip)
    if clip is not None and clip > 0:
        out = np.clip(out, -float(clip), float(clip))
    return out.astype(np.float32, copy=False)


def privileged_dim(
    keys: Iterable[str] | None = None,
    *,
    include_currents: bool = True,
) -> int:
    dim = len(list(keys or DEFAULT_PRIVILEGED_KEYS))
    if include_currents:
        dim += 28
    return dim
