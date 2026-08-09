#!/usr/bin/env python3
"""Independent raw-bank and normal-equation audit for R8R34."""

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
    stage4_2r3c3t13s24d1r14r8r34_causal_local_neighborhood_schedule_generalizing_feedback_preflight
    as r8r34,
)


STAGE = r8r34.STAGE
IDENTITY = r8r34.IDENTITY
AUDIT_KIND = "causal_local_neighborhood_schedule_generalizing_preflight_independent"

_read = ind32._read
_write = ind32._write
_sha = ind32._sha
_digest = ind32._digest
_maximum_difference = ind32._maximum_difference
_without_digests = ind32._without_digests


def _coordinate(row: Mapping[str, Any]) -> np.ndarray:
    feature = np.asarray(row["feature"], dtype=np.float64).reshape(44)
    expanded = np.asarray(row["expanded"], dtype=np.float64).reshape(238)
    coordinate = np.hstack((feature, expanded[slice(44, 62)]))
    if coordinate.shape != (62,) or not np.isfinite(coordinate).all():
        raise ValueError("independent R8R34 coordinate invalid")
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
        raise ValueError("independent R8R34 fit selection empty")
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
                np.sqrt(np.sum((coordinates - center) ** 2, axis=0) / len(coordinates)),
                float(cfg["model_contract"]["coordinate_scale_floor"]),
            )
            standardized = (coordinates - center) / scale
            response = np.vstack(
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
                or response.shape != (len(rows), 5 * len(offsets))
                or not np.isfinite(standardized).all()
                or not np.isfinite(response).all()
            ):
                raise ValueError("independent R8R34 local group invalid")
            groups.append(
                {
                    "sample_offsets": list(offsets),
                    "training_row_count": len(rows),
                    "training_keys": [str(row["trajectory_id"]) for row in rows],
                    "coordinate_mean": center,
                    "coordinate_scale": scale,
                    "standardized_coordinates": standardized,
                    "targets": response,
                }
            )
        intervals.append({"interval": interval_index, "groups": groups})
    return {"model_kind": "causal_local_affine_k64_ridge1", "intervals": intervals}


def _predict_group(
    group: Mapping[str, Any],
    query_coordinate: np.ndarray,
    cfg: Mapping[str, Any],
    *,
    solver: str,
) -> np.ndarray:
    if solver != "normal":
        raise ValueError("independent R8R34 requires normal equations")
    center = np.asarray(group["coordinate_mean"], dtype=np.float64).reshape(62)
    scale = np.asarray(group["coordinate_scale"], dtype=np.float64).reshape(62)
    training = np.asarray(
        group["standardized_coordinates"], dtype=np.float64
    ).reshape((-1, 62))
    response = np.asarray(group["targets"], dtype=np.float64)
    query = (np.asarray(query_coordinate, dtype=np.float64).reshape(62) - center) / scale
    distances = np.sqrt(np.sum((training - query) ** 2, axis=1))
    indices = np.argsort(distances, kind="stable")[
        : int(cfg["model_contract"]["neighbor_count"])
    ]
    delta = training[indices] - query
    design = np.hstack((np.ones((len(indices), 1)), delta))
    ridge = float(cfg["model_contract"]["slope_ridge_penalty"])
    regularizer = np.zeros((63, 63), dtype=np.float64)
    regularizer[1:, 1:] = ridge * np.eye(62)
    coefficients = np.linalg.solve(
        design.T.dot(design) + regularizer,
        design.T.dot(response[indices]),
    )
    result = coefficients[0, :]
    if result.shape != (response.shape[1],) or not np.isfinite(result).all():
        raise ValueError("independent R8R34 prediction invalid")
    return result


def _prediction_map(
    rows: Sequence[Mapping[str, Any]], held_field: str
) -> dict[tuple[str, str], np.ndarray]:
    output = {}
    for fold in rows:
        held = str(fold[held_field])
        for trajectory in fold["trajectories"]:
            values = np.concatenate(
                [np.asarray(row, dtype=float).reshape((-1, 5)) for row in trajectory["predictions"]]
            )
            output[(held, str(trajectory["trajectory_id"]))] = values
    return output


def _scaled_prediction_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scale = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"], dtype=float
    )
    maximum = 0.0
    for key, held_field in (
        ("outer_predictions", "held_pair"),
        ("schedule_predictions", "held_schedule"),
    ):
        left = _prediction_map(primary[key], held_field)
        right = _prediction_map(independent[key], held_field)
        if set(left) != set(right):
            return math.inf
        for row_key in left:
            if left[row_key].shape != right[row_key].shape:
                return math.inf
            physical = np.abs(left[row_key] - right[row_key]) * r8r34.FACTORS
            maximum = max(maximum, float(np.max(physical / scale)))
    return maximum


def _scaled_tube_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scale = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"], dtype=float
    )
    maximum = 0.0
    for key in ("pair_tube", "schedule_tube", "combined_tube"):
        left = primary[key]
        right = independent[key]
        if len(left) != len(right):
            return math.inf
        for left_interval, right_interval in zip(left, right):
            left_array = np.asarray(left_interval, dtype=float)
            right_array = np.asarray(right_interval, dtype=float)
            if left_array.shape != right_array.shape:
                return math.inf
            physical = np.abs(left_array - right_array) * r8r34.FACTORS
            maximum = max(maximum, float(np.max(physical / scale)))
    return maximum


def _scaled_metric_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scale = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"], dtype=float
    )
    maximum = 0.0
    for family in ("outer_model_evaluation", "schedule_jackknife"):
        for field in (
            "maximum_absolute_physical_error",
            "maximum_reserved_physical_tube_half_width",
        ):
            left = np.asarray(primary[family][field], dtype=float)
            right = np.asarray(independent[family][field], dtype=float)
            maximum = max(maximum, float(np.max(np.abs(left - right) / scale)))
    left = np.asarray(primary["combined_tube_maximum_physical_half_width"], dtype=float)
    right = np.asarray(independent["combined_tube_maximum_physical_half_width"], dtype=float)
    maximum = max(maximum, float(np.max(np.abs(left - right) / scale)))
    discrete = (
        "reserved_contained_count",
        "reserved_component_count",
        "state_support_pass_count",
        "passed",
    )
    for field in discrete:
        if primary["outer_model_evaluation"].get(field) != independent[
            "outer_model_evaluation"
        ].get(field):
            return math.inf
    for field in ("contained_count", "component_count", "passed"):
        if primary["schedule_jackknife"].get(field) != independent[
            "schedule_jackknife"
        ].get(field):
            return math.inf
    return maximum


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r34.load_context(args)
    if ctx.cfg.get("stage") != STAGE or ctx.cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R34 configuration identity changed")
    stage = ctx.paths.stage
    summary_path = stage / "analysis/primary_summary.json"
    detailed_path = stage / "analysis/primary_detailed.json"
    model_path = stage / "model/preflight_model.json"
    primary_summary = _read(summary_path)
    primary_detailed = _read(detailed_path)
    primary_model = _read(model_path)

    production_authentication = r8r34.authenticate_sources(ctx)
    independent_transitive = ind31._authenticate(args, ctx.source_ctx.cfg)
    bank = ind31._build_bank(args, ctx.source_ctx.cfg)
    bank_evidence = ind31._bank_evidence(bank)
    _ignored, context_meta = r8r31.r8r23.build_bank(ctx.source_ctx.r8r23_ctx)
    if set(context_meta) != {
        (str(row["pair_id"]), str(row["history_member"])) for row in bank
    }:
        raise ValueError("independent R8R34 planning metadata coverage changed")

    independent_detailed, independent_model = r8r34.compute_from_bank(
        ctx,
        production_authentication,
        bank,
        context_meta,
        bank_evidence,
        solver="normal",
        fit_model_fn=_fit_model,
        predict_group_fn=_predict_group,
    )
    tolerance = float(
        ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"]
    )
    bank_difference = _maximum_difference(
        primary_detailed["bank_evidence"], independent_detailed["bank_evidence"]
    )
    prediction_difference = _scaled_prediction_difference(
        primary_model, independent_model, ctx.cfg
    )
    tube_difference = _scaled_tube_difference(primary_model, independent_model, ctx.cfg)
    metric_difference = _scaled_metric_difference(
        primary_detailed, independent_detailed, ctx.cfg
    )
    planning_difference = _maximum_difference(
        _without_digests(primary_detailed["planning_evaluation"]),
        _without_digests(independent_detailed["planning_evaluation"]),
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
            "r8r33_final": production_authentication,
            "independent_transitive": independent_transitive,
            "passed": True,
        },
        "bank_evidence": bank_evidence,
        "independent_model_artifact_sha256": _digest(independent_model),
        "maximum_bank_absolute_difference": bank_difference,
        "maximum_scaled_prediction_difference": prediction_difference,
        "maximum_scaled_tube_difference": tube_difference,
        "maximum_scaled_metric_difference": metric_difference,
        "maximum_scaled_planning_difference": planning_difference,
        "primary_bank_agreement": bank_difference == 0.0,
        "primary_prediction_agreement": prediction_difference <= tolerance,
        "primary_tube_agreement": tube_difference <= tolerance,
        "primary_metric_agreement": metric_difference <= tolerance,
        "primary_planning_agreement": planning_difference <= tolerance,
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
        and result["primary_prediction_agreement"]
        and result["primary_tube_agreement"]
        and result["primary_metric_agreement"]
        and result["primary_planning_agreement"]
        and result["primary_route_agreement"]
        and result["primary_outcome_agreement"]
    )
    if not result["passed"]:
        _write(stage / "analysis/independent_failure.json", result)
        raise ValueError("independent R8R34 preflight disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in r8r34.ARGUMENT_NAMES:
        parser.add_argument(
            f"--{name}", dest=name.replace("-", "_"), type=Path, required=True
        )
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = audit(args)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
