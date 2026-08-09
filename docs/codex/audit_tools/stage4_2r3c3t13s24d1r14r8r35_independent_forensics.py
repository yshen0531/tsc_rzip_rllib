#!/usr/bin/env python3
"""Independent raw-bank and causal last-innovation audit for R8R35."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r31_independent_forensics as ind31,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r32_independent_forensics as ind32,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r35_causal_last_innovation_local_constant_schedule_generalizing_preflight
    as r8r35,
)


STAGE = r8r35.STAGE
IDENTITY = r8r35.IDENTITY
AUDIT_KIND = "causal_last_innovation_local_constant_independent"
FACTORS = r8r31.OUTPUT_FACTORS
MAX_COUNTS = r8r31.MAX_COUNTS

_read = ind32._read
_write = ind32._write
_sha = ind32._sha
_digest = ind32._digest
_maximum_difference = ind32._maximum_difference


def _coordinate(row: Mapping[str, Any]) -> np.ndarray:
    feature = np.asarray(row["feature"], dtype=np.float64).reshape(44)
    expanded = np.asarray(row["expanded"], dtype=np.float64).reshape(238)
    coordinate = np.hstack((feature, expanded[slice(44, 62)]))
    if coordinate.shape != (62,) or not np.isfinite(coordinate).all():
        raise ValueError("independent R8R35 coordinate invalid")
    return coordinate


def _fit_model(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    chosen = sorted(
        [trajectory for trajectory in trajectories if selected(trajectory)],
        key=lambda trajectory: str(trajectory["trajectory_id"]),
    )
    if not chosen:
        raise ValueError("independent R8R35 fit selection empty")
    intervals = []
    for interval_index in range(6):
        maximum = max(
            len(trajectory["intervals"][interval_index]["targets"])
            for trajectory in chosen
        )
        memberships: dict[tuple[str, ...], list[int]] = {}
        for offset in range(maximum):
            membership = tuple(
                str(trajectory["trajectory_id"])
                for trajectory in chosen
                if len(trajectory["intervals"][interval_index]["targets"]) > offset
            )
            memberships.setdefault(membership, []).append(offset)
        groups = []
        for membership, offsets in memberships.items():
            membership_set = set(membership)
            rows = [
                trajectory
                for trajectory in chosen
                if str(trajectory["trajectory_id"]) in membership_set
            ]
            coordinates = np.vstack(
                [_coordinate(row["intervals"][interval_index]) for row in rows]
            )
            center = np.sum(coordinates, axis=0) / len(coordinates)
            scale = np.maximum(
                np.sqrt(np.sum((coordinates - center) ** 2, axis=0) / len(rows)),
                float(cfg["model_contract"]["coordinate_scale_floor"]),
            )
            standardized = (coordinates - center) / scale
            targets = np.vstack(
                [
                    np.hstack(
                        [
                            np.asarray(
                                row["intervals"][interval_index]["targets"][offset],
                                dtype=np.float64,
                            )
                            for offset in offsets
                        ]
                    )
                    for row in rows
                ]
            )
            if (
                len(rows) < int(cfg["model_contract"]["neighbor_count"])
                or standardized.shape != (len(rows), 62)
                or targets.shape != (len(rows), 5 * len(offsets))
                or not np.isfinite(standardized).all()
                or not np.isfinite(targets).all()
            ):
                raise ValueError("independent R8R35 training group invalid")
            groups.append(
                {
                    "sample_offsets": list(offsets),
                    "training_row_count": len(rows),
                    "training_keys": [str(row["trajectory_id"]) for row in rows],
                    "coordinate_mean": center,
                    "coordinate_scale": scale,
                    "standardized_coordinates": standardized,
                    "targets": targets,
                }
            )
        intervals.append({"interval": interval_index, "groups": groups})
    return {
        "model_kind": "causal_local_constant_k64_last_innovation",
        "intervals": intervals,
    }


def _model_evidence(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model_kind": str(model["model_kind"]),
        "intervals": [
            {
                "interval": int(interval["interval"]),
                "groups": [
                    {
                        "sample_offsets": list(group["sample_offsets"]),
                        "training_row_count": int(group["training_row_count"]),
                        "training_key_digest": _digest(group["training_keys"]),
                        "coordinate_digest": _digest(
                            np.asarray(group["standardized_coordinates"]).tolist()
                        ),
                        "target_digest": _digest(
                            np.asarray(group["targets"]).tolist()
                        ),
                    }
                    for group in interval["groups"]
                ],
            }
            for interval in model["intervals"]
        ],
    }


def _predict_group(
    group: Mapping[str, Any], query_coordinate: np.ndarray, cfg: Mapping[str, Any]
) -> tuple[np.ndarray, list[str]]:
    center = np.asarray(group["coordinate_mean"], dtype=np.float64).reshape(62)
    scale = np.asarray(group["coordinate_scale"], dtype=np.float64).reshape(62)
    training = np.asarray(
        group["standardized_coordinates"], dtype=np.float64
    ).reshape((-1, 62))
    targets = np.asarray(group["targets"], dtype=np.float64)
    query = (np.asarray(query_coordinate, dtype=np.float64).reshape(62) - center) / scale
    distances = np.sqrt(np.sum((training - query) ** 2, axis=1))
    order = sorted(range(len(distances)), key=lambda index: (distances[index], index))
    chosen = order[: int(cfg["model_contract"]["neighbor_count"])]
    values = np.vstack([targets[index] for index in chosen])
    output = np.asarray(
        [math.fsum(map(float, values[:, column])) / len(chosen) for column in range(values.shape[1])],
        dtype=np.float64,
    )
    keys = [str(group["training_keys"][index]) for index in chosen]
    if output.shape != (targets.shape[1],) or not np.isfinite(output).all():
        raise ValueError("independent R8R35 local-constant prediction invalid")
    return output, keys


def _predict_base(
    model: Mapping[str, Any], row: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[np.ndarray, list[str]]:
    interval_index = int(row["interval"])
    target_count = len(row["targets"])
    coordinate = _coordinate(row)
    output = np.empty((target_count, 5), dtype=np.float64)
    filled = np.zeros(target_count, dtype=bool)
    neighbor_digests = []
    for group in model["intervals"][interval_index]["groups"]:
        values, keys = _predict_group(group, coordinate, cfg)
        values = values.reshape((len(group["sample_offsets"]), 5))
        neighbor_digests.append(_digest(keys))
        for index, offset in enumerate(group["sample_offsets"]):
            if int(offset) < target_count:
                output[int(offset)] = values[index]
                filled[int(offset)] = True
    if not filled.all() or not np.isfinite(output).all():
        raise ValueError("independent R8R35 prediction coverage invalid")
    return output, neighbor_digests


def _trajectory_residuals(
    model: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[list[list[list[np.ndarray]]], dict[str, Any], list[dict[str, Any]]]:
    groups: list[list[list[np.ndarray]]] = [
        [[] for _ in range(count)] for count in MAX_COUNTS
    ]
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"],
        dtype=np.float64,
    )
    cold_total = 0.0
    adapted_total = 0.0
    later_rows = 0
    residual_serial = []
    predictions = []
    for trajectory in trajectories:
        previous_innovation = np.zeros(5, dtype=np.float64)
        residual_rows = []
        cold_rows = []
        adapted_rows = []
        neighbor_rows = []
        for interval_index, row in enumerate(trajectory["intervals"]):
            actual = np.asarray(row["targets"], dtype=np.float64).reshape((-1, 5))
            cold, neighbor_digests = _predict_base(model, row, cfg)
            adapted = cold + previous_innovation
            cold_error = np.abs(actual - cold)
            adapted_error = np.abs(actual - adapted)
            residual_rows.append(adapted_error.tolist())
            cold_rows.append(cold.tolist())
            adapted_rows.append(adapted.tolist())
            neighbor_rows.append(neighbor_digests)
            for offset, residual in enumerate(adapted_error):
                groups[interval_index][offset].append(residual)
            if interval_index > 0:
                cold_total += float(np.sum(cold_error * FACTORS / scales))
                adapted_total += float(np.sum(adapted_error * FACTORS / scales))
                later_rows += len(actual)
            previous_innovation = actual[-1] - cold[-1]
        residual_serial.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "absolute_residuals": residual_rows,
            }
        )
        predictions.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "cold_predictions": cold_rows,
                "adapted_predictions": adapted_rows,
                "neighbor_key_digests": neighbor_rows,
            }
        )
    ratio = adapted_total / cold_total if cold_total > 0.0 else 1.0
    return groups, {
        "residual_digest": _digest(residual_serial),
        "cold_post_initial_normalized_l1": cold_total,
        "adapted_post_initial_normalized_l1": adapted_total,
        "adapted_to_cold_l1_ratio": ratio,
        "post_initial_time_row_count": later_rows,
    }, predictions


def _usefulness(
    family: str, rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    cold = sum(float(row["cold_post_initial_normalized_l1"]) for row in rows)
    adapted = sum(float(row["adapted_post_initial_normalized_l1"]) for row in rows)
    count = sum(int(row["post_initial_time_row_count"]) for row in rows)
    ratio = adapted / cold if cold > 0.0 else 1.0
    total_limit = float(
        cfg["adaptation_usefulness_gate"][
            "maximum_adapted_to_cold_total_l1_ratio"
        ]
    )
    fold_limit = float(
        cfg["adaptation_usefulness_gate"][
            "maximum_fold_adapted_to_cold_l1_ratio"
        ]
    )
    fold_rows = [
        {
            "held_out": row["held_out"],
            "cold_normalized_l1": float(row["cold_post_initial_normalized_l1"]),
            "adapted_normalized_l1": float(
                row["adapted_post_initial_normalized_l1"]
            ),
            "adapted_to_cold_l1_ratio": float(row["adapted_to_cold_l1_ratio"]),
            "passed_no_regression": float(row["adapted_to_cold_l1_ratio"])
            <= fold_limit + 1e-15,
        }
        for row in rows
    ]
    return {
        "family": family,
        "fold_count": len(rows),
        "post_initial_time_row_count": count,
        "cold_total_normalized_l1": cold,
        "adapted_total_normalized_l1": adapted,
        "adapted_to_cold_total_l1_ratio": ratio,
        "fold_rows": fold_rows,
        "passed": bool(
            ratio <= total_limit + 1e-15
            and all(row["passed_no_regression"] for row in fold_rows)
            and count
            == int(
                cfg["adaptation_usefulness_gate"][
                    "required_post_initial_time_row_count"
                ]
            )
        ),
    }


def _outer(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    source_cfg: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    pair_ids = sorted({str(row["pair_id"]) for row in trajectories})
    folds = []
    artifacts = []
    usefulness_rows = []
    for held_pair in pair_ids:
        training_pairs = [pair for pair in pair_ids if pair != held_pair]
        model = _fit_model(
            trajectories,
            lambda row, allowed=set(training_pairs): row["pair_id"] in allowed,
            cfg,
        )
        held = [row for row in trajectories if row["pair_id"] == held_pair]
        groups, evidence, predictions = _trajectory_residuals(model, held, cfg)
        model_digest = _digest(_model_evidence(model))
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": training_pairs,
                "model_digest": model_digest,
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
                "support": r8r31._support_fold(
                    trajectories,
                    training_pairs,
                    held_pair,
                    float(
                        source_cfg["model_contract"][
                            "support_threshold_multiplier"
                        ]
                    ),
                ),
            }
        )
        usefulness_rows.append({"held_out": held_pair, **evidence})
        artifacts.append({"held_pair": held_pair, "trajectories": predictions})
    contained = 0
    total = 0
    maximum_error = np.zeros(5, dtype=np.float64)
    maximum_tube = np.zeros(5, dtype=np.float64)
    fold_rows = []
    for fold in folds:
        tube, tube_evidence = r8r31._tube_from_fold_groups(
            folds, lambda row, held=fold["held_pair"]: row["held_pair"] != held, cfg
        )
        fold_contained = 0
        fold_total = 0
        fold_error = np.zeros(5, dtype=np.float64)
        for interval_index, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values, dtype=np.float64).reshape((-1, 5))
                fold_contained += int(
                    np.count_nonzero(residual <= tube[interval_index][offset] + 1e-15)
                )
                fold_total += residual.size
                if len(residual):
                    fold_error = np.maximum(fold_error, np.max(residual, axis=0))
        maximum_error = np.maximum(maximum_error, fold_error * FACTORS)
        maximum_tube = np.maximum(
            maximum_tube, np.max(np.concatenate(tube), axis=0) * FACTORS
        )
        contained += fold_contained
        total += fold_total
        fold["tube"] = tube
        fold_rows.append(
            {
                "held_pair": fold["held_pair"],
                "model_digest": fold["model_digest"],
                "residual_digest": fold["residual_digest"],
                "maximum_physical_error": (fold_error * FACTORS).tolist(),
                "contained_count": fold_contained,
                "component_count": fold_total,
                "support": fold["support"],
                "tube_evidence": tube_evidence,
            }
        )
    gates = cfg["model_gates"]
    rate = contained / total
    passed = bool(
        np.all(maximum_error <= np.asarray(gates["maximum_point_error"]) + 1e-15)
        and np.all(
            maximum_tube
            <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15
        )
        and rate
        >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
        and all(fold["support"]["passed"] for fold in folds)
    )
    return folds, {
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "reserved_contained_count": contained,
        "reserved_component_count": total,
        "reserved_containment_rate": rate,
        "state_support_pass_count": sum(fold["support"]["passed"] for fold in folds),
        "fold_rows": fold_rows,
        "passed": passed,
        "adaptation_usefulness": _usefulness(
            "whole_physical_pair", usefulness_rows, cfg
        ),
    }, artifacts


def _schedule(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], dict[str, Any], list[dict[str, Any]]]:
    schedule_ids = sorted({str(row["schedule_id"]) for row in trajectories})
    folds = []
    artifacts = []
    usefulness_rows = []
    for held_schedule in schedule_ids:
        model = _fit_model(
            trajectories,
            lambda row, held=held_schedule: row["schedule_id"] != held,
            cfg,
        )
        held = [row for row in trajectories if row["schedule_id"] == held_schedule]
        if len(held) != 16:
            raise ValueError("independent R8R35 schedule fold cardinality changed")
        groups, evidence, predictions = _trajectory_residuals(model, held, cfg)
        folds.append(
            {
                "held_schedule": held_schedule,
                "model_digest": _digest(_model_evidence(model)),
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
            }
        )
        usefulness_rows.append({"held_out": held_schedule, **evidence})
        artifacts.append({"held_schedule": held_schedule, "trajectories": predictions})
    tube, tube_evidence = r8r31._tube_from_fold_groups(folds, lambda row: True, cfg)
    contained = 0
    total = 0
    maximum_error = np.zeros(5, dtype=np.float64)
    for fold in folds:
        for interval_index, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values, dtype=np.float64).reshape((-1, 5))
                contained += int(
                    np.count_nonzero(residual <= tube[interval_index][offset] + 1e-15)
                )
                total += residual.size
                if len(residual):
                    maximum_error = np.maximum(maximum_error, np.max(residual, axis=0))
    maximum_tube = np.max(np.concatenate(tube), axis=0) * FACTORS
    gates = cfg["model_gates"]
    passed = bool(
        contained == total
        and np.all(
            maximum_error * FACTORS
            <= np.asarray(gates["maximum_point_error"]) + 1e-15
        )
        and np.all(
            maximum_tube
            <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15
        )
    )
    return tube, {
        "schedule_count": len(schedule_ids),
        "training_schedule_count": len(schedule_ids) - 1,
        "folds": [
            {
                "held_schedule": fold["held_schedule"],
                "model_digest": fold["model_digest"],
                "residual_digest": fold["residual_digest"],
            }
            for fold in folds
        ],
        "maximum_absolute_physical_error": (maximum_error * FACTORS).tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "contained_count": contained,
        "component_count": total,
        "containment_rate": contained / total,
        "tube_evidence": tube_evidence,
        "passed": passed,
        "adaptation_usefulness": _usefulness("whole_schedule", usefulness_rows, cfg),
    }, artifacts


def _compute(
    ctx: Any,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    bank_evidence: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    r8r35._verify_bank(trajectories, bank_evidence, ctx.cfg)
    cardinality = r8r35.r8r34.local_cardinality_audit(trajectories, ctx.cfg)
    if not cardinality["passed"]:
        raise ValueError("independent R8R35 cardinality failed")
    folds, outer, outer_predictions = _outer(
        trajectories, ctx.cfg, ctx.source_ctx.cfg
    )
    schedule_tube, schedule, schedule_predictions = _schedule(trajectories, ctx.cfg)
    pair_tube, pair_evidence = r8r31._tube_from_fold_groups(
        folds, lambda row: True, ctx.cfg
    )
    combined_tube = [
        np.maximum(pair, schedule_value)
        for pair, schedule_value in zip(pair_tube, schedule_tube)
    ]
    combined_maximum = np.max(np.concatenate(combined_tube), axis=0) * FACTORS
    combined_passed = bool(
        np.all(
            combined_maximum
            <= np.asarray(ctx.cfg["model_gates"]["maximum_tube_half_width"])
            + 1e-15
        )
    )
    model_gate = bool(outer["passed"] and schedule["passed"] and combined_passed)
    usefulness_gate = bool(
        outer["adaptation_usefulness"]["passed"]
        and schedule["adaptation_usefulness"]["passed"]
    )
    scientific = bool(model_gate and usefulness_gate)
    route = (
        ctx.cfg["routes"]["model_fail"]
        if not model_gate
        else ctx.cfg["routes"]["pass"]
        if scientific
        else ctx.cfg["routes"]["not_useful"]
    )
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank_evidence,
        "local_cardinality_audit": cardinality,
        "outer_model_evaluation": outer,
        "schedule_jackknife": schedule,
        "pair_tube_evidence": pair_evidence,
        "combined_tube_maximum_physical_half_width": combined_maximum.tolist(),
        "combined_tube_cap_passed": combined_passed,
        "model_gate_passed": model_gate,
        "adaptation_usefulness_gate_passed": usefulness_gate,
        "integrity_gate_passed": True,
        "scientific_gate_passed": scientific,
        "passed": True,
        "route": route,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    artifact = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "model_kind": "causal_local_constant_k64_last_innovation",
        "bank_evidence": bank_evidence,
        "outer_model_evidence": [
            {"held_pair": fold["held_pair"], "model_digest": fold["model_digest"]}
            for fold in folds
        ],
        "outer_predictions": outer_predictions,
        "schedule_predictions": schedule_predictions,
        "pair_tube": pair_tube,
        "schedule_tube": schedule_tube,
        "combined_tube": combined_tube,
    }
    return r8r35._jsonable(detailed), r8r35._jsonable(artifact)


def _prediction_map(
    rows: Sequence[Mapping[str, Any]], held_field: str, prediction_field: str
) -> dict[tuple[str, str], np.ndarray]:
    output = {}
    for fold in rows:
        held = str(fold[held_field])
        for trajectory in fold["trajectories"]:
            output[(held, str(trajectory["trajectory_id"]))] = np.concatenate(
                [
                    np.asarray(row, dtype=np.float64).reshape((-1, 5))
                    for row in trajectory[prediction_field]
                ]
            )
    return output


def _neighbor_map(
    rows: Sequence[Mapping[str, Any]], held_field: str
) -> dict[tuple[str, str], Any]:
    return {
        (str(fold[held_field]), str(trajectory["trajectory_id"])): trajectory[
            "neighbor_key_digests"
        ]
        for fold in rows
        for trajectory in fold["trajectories"]
    }


def _scaled_prediction_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"],
        dtype=np.float64,
    )
    maximum = 0.0
    for family, held_field in (
        ("outer_predictions", "held_pair"),
        ("schedule_predictions", "held_schedule"),
    ):
        for prediction_field in ("cold_predictions", "adapted_predictions"):
            left = _prediction_map(primary[family], held_field, prediction_field)
            right = _prediction_map(independent[family], held_field, prediction_field)
            if set(left) != set(right):
                return math.inf
            for key in left:
                if left[key].shape != right[key].shape:
                    return math.inf
                physical = np.abs(left[key] - right[key]) * FACTORS
                maximum = max(maximum, float(np.max(physical / scales)))
    return maximum


def _neighbor_agreement(
    primary: Mapping[str, Any], independent: Mapping[str, Any]
) -> bool:
    return all(
        _neighbor_map(primary[family], held_field)
        == _neighbor_map(independent[family], held_field)
        for family, held_field in (
            ("outer_predictions", "held_pair"),
            ("schedule_predictions", "held_schedule"),
        )
    )


def _scaled_tube_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"],
        dtype=np.float64,
    )
    maximum = 0.0
    for field in ("pair_tube", "schedule_tube", "combined_tube"):
        if len(primary[field]) != len(independent[field]):
            return math.inf
        for left, right in zip(primary[field], independent[field]):
            left_array = np.asarray(left, dtype=np.float64)
            right_array = np.asarray(right, dtype=np.float64)
            if left_array.shape != right_array.shape:
                return math.inf
            maximum = max(
                maximum,
                float(np.max(np.abs(left_array - right_array) * FACTORS / scales)),
            )
    return maximum


def _scaled_metric_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"],
        dtype=np.float64,
    )
    maximum = 0.0
    for family in ("outer_model_evaluation", "schedule_jackknife"):
        for field in (
            "maximum_absolute_physical_error",
            "maximum_reserved_physical_tube_half_width",
        ):
            left = np.asarray(primary[family][field], dtype=np.float64)
            right = np.asarray(independent[family][field], dtype=np.float64)
            maximum = max(maximum, float(np.max(np.abs(left - right) / scales)))
        left_useful = primary[family]["adaptation_usefulness"]
        right_useful = independent[family]["adaptation_usefulness"]
        for field in (
            "cold_total_normalized_l1",
            "adapted_total_normalized_l1",
            "adapted_to_cold_total_l1_ratio",
        ):
            left_value = float(left_useful[field])
            right_value = float(right_useful[field])
            denominator = max(1.0, abs(left_value), abs(right_value))
            maximum = max(maximum, abs(left_value - right_value) / denominator)
    left = np.asarray(
        primary["combined_tube_maximum_physical_half_width"], dtype=np.float64
    )
    right = np.asarray(
        independent["combined_tube_maximum_physical_half_width"], dtype=np.float64
    )
    maximum = max(maximum, float(np.max(np.abs(left - right) / scales)))
    discrete = (
        (
            "outer_model_evaluation",
            (
                "reserved_contained_count",
                "reserved_component_count",
                "state_support_pass_count",
                "passed",
            ),
        ),
        (
            "schedule_jackknife",
            ("contained_count", "component_count", "schedule_count", "passed"),
        ),
    )
    for family, fields in discrete:
        if any(primary[family].get(field) != independent[family].get(field) for field in fields):
            return math.inf
        if (
            primary[family]["adaptation_usefulness"]["passed"]
            != independent[family]["adaptation_usefulness"]["passed"]
        ):
            return math.inf
    for field in (
        "combined_tube_cap_passed",
        "model_gate_passed",
        "adaptation_usefulness_gate_passed",
        "scientific_gate_passed",
    ):
        if primary[field] != independent[field]:
            return math.inf
    return maximum


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r35.load_context(args)
    if ctx.cfg.get("stage") != STAGE or ctx.cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R35 configuration identity changed")
    stage = ctx.paths.stage
    summary_path = stage / "analysis/primary_summary.json"
    detailed_path = stage / "analysis/primary_detailed.json"
    model_path = stage / "model/preflight_model.json"
    primary_summary = _read(summary_path)
    primary_detailed = _read(detailed_path)
    primary_model = _read(model_path)

    production_authentication = r8r35.authenticate_sources(ctx)
    independent_transitive = ind31._authenticate(args, ctx.source_ctx.cfg)
    trajectories = ind31._build_bank(args, ctx.source_ctx.cfg)
    bank_evidence = ind31._bank_evidence(trajectories)
    independent_detailed, independent_model = _compute(
        ctx,
        {
            "r8r34_final": production_authentication["r8r34_final"],
            "independent_transitive": independent_transitive,
            "passed": True,
        },
        trajectories,
        bank_evidence,
    )
    tolerance = float(
        ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"]
    )
    bank_difference = _maximum_difference(
        primary_detailed["bank_evidence"], independent_detailed["bank_evidence"]
    )
    neighbor_agreement = _neighbor_agreement(primary_model, independent_model)
    prediction_difference = _scaled_prediction_difference(
        primary_model, independent_model, ctx.cfg
    )
    tube_difference = _scaled_tube_difference(primary_model, independent_model, ctx.cfg)
    metric_difference = _scaled_metric_difference(
        primary_detailed, independent_detailed, ctx.cfg
    )
    route_agreement = bool(
        primary_detailed["route"] == independent_detailed["route"]
        and primary_summary["route"] == independent_detailed["route"]
    )
    outcome_agreement = bool(
        primary_detailed["integrity_gate_passed"] is True
        and independent_detailed["integrity_gate_passed"] is True
        and primary_detailed["scientific_gate_passed"]
        is independent_detailed["scientific_gate_passed"]
        and primary_summary["scientific_gate_passed"]
        is independent_detailed["scientific_gate_passed"]
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": AUDIT_KIND,
        "source_authentication": {
            "r8r34_final": production_authentication["r8r34_final"],
            "independent_transitive": independent_transitive,
            "passed": True,
        },
        "bank_evidence": bank_evidence,
        "independent_model_artifact_sha256": _digest(independent_model),
        "maximum_bank_absolute_difference": bank_difference,
        "maximum_scaled_prediction_difference": prediction_difference,
        "maximum_scaled_tube_difference": tube_difference,
        "maximum_scaled_metric_difference": metric_difference,
        "primary_bank_agreement": bank_difference == 0.0,
        "primary_neighbor_agreement": neighbor_agreement,
        "primary_prediction_agreement": prediction_difference <= tolerance,
        "primary_tube_agreement": tube_difference <= tolerance,
        "primary_metric_agreement": metric_difference <= tolerance,
        "primary_route_agreement": route_agreement,
        "primary_outcome_agreement": outcome_agreement,
        "route": independent_detailed["route"],
        "scientific_gate_passed": bool(independent_detailed["scientific_gate_passed"]),
        "primary_summary_sha256": _sha(summary_path),
        "primary_detailed_sha256": _sha(detailed_path),
        "primary_model_sha256": _sha(model_path),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    result["passed"] = bool(
        result["primary_bank_agreement"]
        and result["primary_neighbor_agreement"]
        and result["primary_prediction_agreement"]
        and result["primary_tube_agreement"]
        and result["primary_metric_agreement"]
        and result["primary_route_agreement"]
        and result["primary_outcome_agreement"]
    )
    if not result["passed"]:
        _write(stage / "analysis/independent_failure.json", result)
        raise ValueError("independent R8R35 preflight disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in r8r35.ARGUMENT_NAMES:
        parser.add_argument(
            f"--{name}", dest=name.replace("-", "_"), type=Path, required=True
        )
    return parser


def main() -> None:
    result = audit(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
