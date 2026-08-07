"""Bounded causal one-step innovation update for the R8R6 observer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


Array = np.ndarray


def adapt_prediction(
    origin_visible: Sequence[float],
    previous_cold_prediction: Sequence[Sequence[float]],
    cold_prediction: Sequence[Sequence[float]],
    cfg: Mapping[str, Any],
) -> tuple[Array, dict[str, Any]]:
    """Apply the frozen causal innovation and preserve R/Z kinematics."""

    origin = np.asarray(origin_visible, dtype=float)
    previous = np.asarray(previous_cold_prediction, dtype=float)
    cold = np.asarray(cold_prediction, dtype=float)
    count = int(cfg["bank_contract"]["future_state_count"])
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    contract = cfg["innovation_contract"]
    clip_physical = np.asarray(contract["clip_physical"], dtype=float)
    rho = float(contract["persistence"])
    if (
        origin.shape != (5,)
        or previous.shape != (count, 5)
        or cold.shape != (count, 5)
        or scales.shape != (5,)
        or clip_physical.shape != (3,)
        or not np.all(np.isfinite(origin))
        or not np.all(np.isfinite(previous))
        or not np.all(np.isfinite(cold))
        or not np.all(np.isfinite(scales))
        or not np.all(scales > 0.0)
        or not np.all(clip_physical > 0.0)
        or not 0.0 <= rho <= 1.0
    ):
        raise ValueError("R8R6 innovation input contract changed")

    innovation_scaled = origin[2:5] - previous[0, 2:5]
    innovation_physical = innovation_scaled * scales[2:5]
    clipped_physical = np.clip(
        innovation_physical, -clip_physical, clip_physical
    )
    clipped_scaled = clipped_physical / scales[2:5]
    weights = rho ** np.arange(count, dtype=float)
    output = cold.copy()
    output[:, 2:5] += weights[:, None] * clipped_scaled[None, :]
    output[:, 0] = origin[0] + np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = origin[1] + np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    if not np.all(np.isfinite(output)):
        raise ValueError("R8R6 adapted prediction is non-finite")
    return output, {
        "innovation_physical": innovation_physical.tolist(),
        "clipped_innovation_physical": clipped_physical.tolist(),
        "clip_activated": bool(
            np.any(np.abs(innovation_physical) > clip_physical + 1e-15)
        ),
        "persistence": rho,
    }


def context_robust_tube(
    rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[Array, dict[str, Any]]:
    """Build the single frozen higher-quantile R8R6 tube."""

    residual = np.asarray(
        [row["absolute_residual_physical"] for row in rows], dtype=float
    )
    tube_cfg = cfg["tube_contract"]
    floor = np.asarray(tube_cfg["component_floor_physical"], dtype=float)
    if (
        residual.shape
        != (int(cfg["bank_contract"]["adapted_origin_row_count"]), 12, 5)
        or floor.shape != (5,)
        or not np.all(np.isfinite(residual))
    ):
        raise ValueError("R8R6 tube residual contract changed")
    base = np.quantile(
        residual,
        float(tube_cfg["base_absolute_residual_quantile"]),
        axis=0,
        method="higher",
    ) + floor[None, :]
    ratios = np.max(residual / base[None, :, :], axis=(1, 2))
    aggregate = float(
        np.quantile(
            ratios,
            float(tube_cfg["aggregate_row_ratio_quantile"]),
            method="higher",
        )
    )
    context_values: dict[str, float] = {}
    contexts = sorted(
        {f"{row['pair_id']}|{row['history_member']}" for row in rows}
    )
    for context in contexts:
        current = np.asarray(
            [
                ratio
                for row, ratio in zip(rows, ratios)
                if f"{row['pair_id']}|{row['history_member']}" == context
            ],
            dtype=float,
        )
        context_values[context] = float(
            np.quantile(
                current,
                float(tube_cfg["per_context_row_ratio_quantile"]),
                method="higher",
            )
        )
    calibration = max([aggregate, *context_values.values()])
    scalar = max(
        float(tube_cfg["scalar_floor"]),
        float(tube_cfg["prospective_reserve_multiplier"]) * calibration,
    )
    tube = scalar * base
    if not np.all(np.isfinite(tube)):
        raise ValueError("R8R6 tube is non-finite")
    return tube, {
        "aggregate_q95_row_ratio": aggregate,
        "per_context_q90_row_ratios": context_values,
        "calibration_ratio": calibration,
        "prospective_reserve_multiplier": float(
            tube_cfg["prospective_reserve_multiplier"]
        ),
        "scalar": scalar,
    }


def usefulness(
    cold_rows: Sequence[Mapping[str, Any]],
    adapted_rows: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate the frozen aggregate and per-context measurable-benefit gate."""

    cold_by_id = {str(row["row_id"]): row for row in cold_rows}
    adapted_by_id = {str(row["row_id"]): row for row in adapted_rows}
    if set(cold_by_id) != set(adapted_by_id) or len(cold_by_id) != int(
        cfg["bank_contract"]["adapted_origin_row_count"]
    ):
        raise ValueError("R8R6 cold/adapted row coverage changed")
    cold_mean = float(
        np.mean(
            [float(cold_by_id[key]["mean_squared_scaled_error"]) for key in cold_by_id]
        )
    )
    adapted_mean = float(
        np.mean(
            [
                float(adapted_by_id[key]["mean_squared_scaled_error"])
                for key in adapted_by_id
            ]
        )
    )
    gates = cfg["gates"]
    contexts = sorted(
        {
            f"{row['pair_id']}|{row['history_member']}"
            for row in adapted_by_id.values()
        }
    )
    context_rows: dict[str, dict[str, Any]] = {}
    improved = 0
    no_regression = True
    for context in contexts:
        keys = [
            key
            for key, row in adapted_by_id.items()
            if f"{row['pair_id']}|{row['history_member']}" == context
        ]
        cold_value = float(
            np.mean([float(cold_by_id[key]["mean_squared_scaled_error"]) for key in keys])
        )
        adapted_value = float(
            np.mean(
                [float(adapted_by_id[key]["mean_squared_scaled_error"]) for key in keys]
            )
        )
        ratio = adapted_value / cold_value if cold_value > 0.0 else float("inf")
        current_improved = adapted_value < cold_value
        current_no_regression = ratio <= float(
            gates["maximum_context_mse_ratio"]
        ) + 1e-15
        improved += int(current_improved)
        no_regression = no_regression and current_no_regression
        context_rows[context] = {
            "cold_mean_squared_scaled_error": cold_value,
            "adapted_mean_squared_scaled_error": adapted_value,
            "adapted_to_cold_ratio": ratio,
            "strictly_improved": current_improved,
            "no_more_than_five_percent_regression": current_no_regression,
        }
    aggregate_ratio = adapted_mean / cold_mean if cold_mean > 0.0 else float("inf")
    result = {
        "cold_mean_squared_scaled_error": cold_mean,
        "adapted_mean_squared_scaled_error": adapted_mean,
        "adapted_to_cold_ratio": aggregate_ratio,
        "required_maximum_aggregate_ratio": float(
            gates["maximum_aggregate_mse_ratio"]
        ),
        "strictly_improved_context_count": improved,
        "required_strictly_improved_context_count": int(
            gates["minimum_strictly_improved_context_count"]
        ),
        "all_contexts_within_regression_limit": no_regression,
        "context_counts": context_rows,
    }
    result["passed"] = bool(
        aggregate_ratio
        <= float(gates["maximum_aggregate_mse_ratio"]) + 1e-15
        and no_regression
        and improved >= int(gates["minimum_strictly_improved_context_count"])
    )
    return result
