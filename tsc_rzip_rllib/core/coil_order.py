from __future__ import annotations

import numpy as np


# ============================================================
# Coil naming / ordering convention
# ============================================================
# DISPLAY order:
#   Used by config, UI table/legend, turns_display_order,
#   min_current_ka_display_order, max_current_ka_display_order.
#
# TSC order:
#   Used by TSC card 15, coil_currents.csv, runner internal state,
#   and RL action/observation unless explicitly converted for display.
# ============================================================

DISPLAY_COIL_NAMES = [
    "CS1U", "CS1L",
    "CS2U", "CS2L",
    "CS3U", "CS3L",
    "CS4U", "CS4L",
    "PF2U", "PF2L",
    "PF3U", "PF3L",
    "PF4U", "PF4L",
]

TSC_COIL_NAMES = [
    "CS1U", "CS2U", "CS3U",
    "CS1L", "CS2L", "CS3L",
    "CS4U", "CS4L",
    "PF2U", "PF2L",
    "PF3U", "PF3L",
    "PF4U", "PF4L",
]


# display_order -> tsc_order
# Example:
#   x_tsc = x_display[DISPLAY_TO_TSC_INDEX]
DISPLAY_TO_TSC_INDEX = [DISPLAY_COIL_NAMES.index(name) for name in TSC_COIL_NAMES]

# tsc_order -> display_order
# Example:
#   x_display = x_tsc[TSC_TO_DISPLAY_INDEX]
TSC_TO_DISPLAY_INDEX = [TSC_COIL_NAMES.index(name) for name in DISPLAY_COIL_NAMES]

TSC_NAME_TO_INDEX = {name: i for i, name in enumerate(TSC_COIL_NAMES)}
DISPLAY_NAME_TO_INDEX = {name: i for i, name in enumerate(DISPLAY_COIL_NAMES)}


def as_14_vector(x, name: str = "x") -> np.ndarray:
    """Return x as a float ndarray and require shape (14,)."""
    arr = np.asarray(x, dtype=float)
    if arr.shape != (14,):
        raise ValueError(f"{name} must have shape (14,), got {arr.shape}")
    return arr


def display_to_tsc(x_display) -> np.ndarray:
    """Convert a 14-channel vector from DISPLAY order to TSC order."""
    x_display = as_14_vector(x_display, "x_display")
    return x_display[DISPLAY_TO_TSC_INDEX]


def tsc_to_display(x_tsc) -> np.ndarray:
    """Convert a 14-channel vector from TSC order to DISPLAY order."""
    x_tsc = as_14_vector(x_tsc, "x_tsc")
    return x_tsc[TSC_TO_DISPLAY_INDEX]


def display_matrix_to_tsc(arr_display) -> np.ndarray:
    """Convert array data with shape (..., 14) from DISPLAY order to TSC order."""
    arr = np.asarray(arr_display, dtype=float)
    if arr.shape[-1] != 14:
        raise ValueError(f"expected last dimension 14, got {arr.shape}")
    return arr[..., DISPLAY_TO_TSC_INDEX]


def tsc_matrix_to_display(arr_tsc) -> np.ndarray:
    """Convert array data with shape (..., 14) from TSC order to DISPLAY order."""
    arr = np.asarray(arr_tsc, dtype=float)
    if arr.shape[-1] != 14:
        raise ValueError(f"expected last dimension 14, got {arr.shape}")
    return arr[..., TSC_TO_DISPLAY_INDEX]


def print_order_check() -> None:
    """Small helper for manual debugging."""
    print("DISPLAY order:")
    for i, name in enumerate(DISPLAY_COIL_NAMES):
        print(f"  display[{i:2d}] = {name}")

    print("\nTSC order:")
    for i, name in enumerate(TSC_COIL_NAMES):
        print(f"  tsc[{i:2d}] = {name}")

    print("\nDISPLAY_TO_TSC_INDEX =", DISPLAY_TO_TSC_INDEX)
    print("TSC_TO_DISPLAY_INDEX =", TSC_TO_DISPLAY_INDEX)