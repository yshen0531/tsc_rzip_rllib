#!/usr/bin/env python3
"""Independent raw-bank and affine-dominant local-affine audit for R8R43."""

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
    stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight
    as r8r43,
)


STAGE = r8r43.STAGE
IDENTITY = r8r43.IDENTITY
AUDIT_KIND = "fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_independent"
FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=np.float64)
MAX_COUNTS = (2, 2, 2, 2, 4, 15)

_read = ind32._read
_write = ind32._write
_sha = ind32._sha
_digest = ind32._digest
_maximum_difference = ind32._maximum_difference


def _coordinate(row: Mapping[str, Any]) -> np.ndarray:
    feature = np.asarray(row["feature"], dtype=np.float64).reshape(44)
    expanded = np.asarray(row["expanded"], dtype=np.float64).reshape(238)
    coordinate = np.hstack((feature, expanded[44:62]))
    if coordinate.shape != (62,) or not np.isfinite(coordinate).all():
        raise ValueError("independent R8R43 coordinate invalid")
    return coordinate


def _fit_local(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    chosen = sorted(
        [trajectory for trajectory in trajectories if selected(trajectory)],
        key=lambda trajectory: str(trajectory["trajectory_id"]),
    )
    if not chosen:
        raise ValueError("independent R8R43 local fit selection empty")
    contract = cfg["model_contract"]
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
            allowed = set(membership)
            rows = [
                trajectory
                for trajectory in chosen
                if str(trajectory["trajectory_id"]) in allowed
            ]
            coordinates = np.vstack(
                [_coordinate(row["intervals"][interval_index]) for row in rows]
            )
            center = np.sum(coordinates, axis=0) / len(coordinates)
            scale = np.maximum(
                np.sqrt(np.sum((coordinates - center) ** 2, axis=0) / len(rows)),
                float(contract["local_coordinate_scale_floor"]),
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
                len(rows) < int(contract["local_neighbor_count"])
                or standardized.shape != (len(rows), 62)
                or targets.shape != (len(rows), 5 * len(offsets))
                or not np.isfinite(standardized).all()
                or not np.isfinite(targets).all()
            ):
                raise ValueError("independent R8R43 local training group invalid")
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
        "model_kind": "causal_local_affine_k64_ridge1_cold",
        "intervals": intervals,
    }


def _predict_local(
    model: Mapping[str, Any], row: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[np.ndarray, list[str]]:
    interval = int(row["interval"])
    count = len(row["targets"])
    query_coordinate = _coordinate(row)
    output = np.empty((count, 5), dtype=np.float64)
    filled = np.zeros(count, dtype=bool)
    neighbor_digests = []
    for group in model["intervals"][interval]["groups"]:
        center = np.asarray(group["coordinate_mean"], dtype=np.float64).reshape(62)
        scale = np.asarray(group["coordinate_scale"], dtype=np.float64).reshape(62)
        training = np.asarray(group["standardized_coordinates"], dtype=np.float64)
        target = np.asarray(group["targets"], dtype=np.float64)
        query = (query_coordinate - center) / scale
        distance = np.sqrt(np.sum((training - query) ** 2, axis=1))
        chosen = np.argsort(distance, kind="mergesort")[: int(cfg["model_contract"]["local_neighbor_count"])]
        difference = training[chosen] - query
        response = target[chosen]
        difference_mean = np.sum(difference, axis=0) / len(chosen)
        response_mean = np.sum(response, axis=0) / len(chosen)
        centered_difference = difference - difference_mean
        centered_response = response - response_mean
        active = np.any(centered_difference != 0.0, axis=0)
        slopes = np.zeros((62, response.shape[1]), dtype=np.float64)
        if np.any(active):
            active_count = int(np.count_nonzero(active))
            ridge = float(cfg["model_contract"]["local_slope_ridge_penalty"])
            augmented_coordinate = np.concatenate(
                (
                    centered_difference[:, active],
                    math.sqrt(ridge) * np.identity(active_count),
                ),
                axis=0,
            )
            augmented_response = np.concatenate(
                (
                    centered_response,
                    np.zeros((active_count, response.shape[1]), dtype=np.float64),
                ),
                axis=0,
            )
            slopes[active] = np.linalg.lstsq(
                augmented_coordinate, augmented_response, rcond=None
            )[0]
        values = response_mean - difference_mean @ slopes
        keys = [str(group["training_keys"][int(index)]) for index in chosen]
        values = values.reshape((len(group["sample_offsets"]), 5))
        neighbor_digests.append(_digest(keys))
        for index, offset in enumerate(group["sample_offsets"]):
            if int(offset) < count:
                output[int(offset)] = values[index]
                filled[int(offset)] = True
    if not filled.all() or not np.isfinite(output).all():
        raise ValueError("independent R8R43 local prediction coverage invalid")
    return output, neighbor_digests


def _fit_model(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "model_kind": "fixed_affine_dominant_global_ridge_local_affine_cold_ensemble",
        "global_model": ind31._fit(
            trajectories,
            selected,
            float(cfg["model_contract"]["global_ridge_penalty"]),
        ),
        "local_model": _fit_local(trajectories, selected, cfg),
    }


def _model_evidence(model: Mapping[str, Any]) -> dict[str, Any]:
    global_json = ind31._model_json(model["global_model"])
    local_json = {
        "model_kind": model["local_model"]["model_kind"],
        "intervals": [
            {
                "interval": int(interval["interval"]),
                "groups": [
                    {
                        "sample_offsets": list(group["sample_offsets"]),
                        "training_row_count": int(group["training_row_count"]),
                        "training_key_digest": _digest(group["training_keys"]),
                        "coordinate_mean": np.asarray(group["coordinate_mean"]).tolist(),
                        "coordinate_scale": np.asarray(group["coordinate_scale"]).tolist(),
                        "coordinate_digest": _digest(
                            np.asarray(group["standardized_coordinates"]).tolist()
                        ),
                        "target_digest": _digest(np.asarray(group["targets"]).tolist()),
                    }
                    for group in interval["groups"]
                ],
            }
            for interval in model["local_model"]["intervals"]
        ],
    }
    value = {
        "model_kind": model["model_kind"],
        "global_model_digest": _digest(global_json),
        "local_model_digest": _digest(local_json),
        "global_model": global_json,
        "local_model_evidence": local_json,
    }
    value["ensemble_model_digest"] = _digest(value)
    return value


def _predict(
    model: Mapping[str, Any], row: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    global_prediction = ind31._predict(model["global_model"], row)
    local_prediction, neighbors = _predict_local(model["local_model"], row, cfg)
    ensemble = (
        float(cfg["model_contract"]["global_weight"]) * global_prediction
        + float(cfg["model_contract"]["local_weight"]) * local_prediction
    )
    if ensemble.shape != global_prediction.shape or not np.isfinite(ensemble).all():
        raise ValueError("independent R8R43 ensemble prediction invalid")
    return global_prediction, local_prediction, ensemble, neighbors


def _residuals(
    model: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[list[list[list[np.ndarray]]], str, list[dict[str, Any]]]:
    groups: list[list[list[np.ndarray]]] = [
        [[] for _ in range(count)] for count in MAX_COUNTS
    ]
    serial = []
    predictions = []
    for trajectory in trajectories:
        residual_rows = []
        global_rows = []
        local_rows = []
        ensemble_rows = []
        neighbor_rows = []
        for interval, row in enumerate(trajectory["intervals"]):
            global_prediction, local_prediction, ensemble, neighbors = _predict(
                model, row, cfg
            )
            residual = np.abs(np.asarray(row["targets"], dtype=np.float64) - ensemble)
            residual_rows.append(residual.tolist())
            global_rows.append(global_prediction.tolist())
            local_rows.append(local_prediction.tolist())
            ensemble_rows.append(ensemble.tolist())
            neighbor_rows.append(list(neighbors))
            for offset, value in enumerate(residual):
                groups[interval][offset].append(value)
        serial.append({"trajectory_id": trajectory["trajectory_id"], "absolute_residuals": residual_rows})
        predictions.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "global_predictions": global_rows,
                "local_predictions": local_rows,
                "ensemble_predictions": ensemble_rows,
                "absolute_residuals": residual_rows,
                "neighbor_key_digests": neighbor_rows,
            }
        )
    return groups, _digest(serial), predictions


def _cardinality(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    required = int(cfg["model_contract"]["local_neighbor_count"])
    definitions = (
        ("whole_physical_pair", sorted({str(row["pair_id"]) for row in trajectories}), "pair_id"),
        ("whole_schedule", sorted({str(row["schedule_id"]) for row in trajectories}), "schedule_id"),
    )
    families = []
    for family, held_values, field in definitions:
        rows = []
        for held in held_values:
            chosen = [row for row in trajectories if str(row[field]) != held]
            for interval in range(6):
                interval_rows = [row["intervals"][interval] for row in chosen]
                for offset in range(max(len(row["targets"]) for row in interval_rows)):
                    count = sum(len(row["targets"]) > offset for row in interval_rows)
                    rows.append(
                        {
                            "held_out": held,
                            "interval": interval,
                            "sample_offset": offset,
                            "training_row_count": count,
                            "passed": count >= required,
                        }
                    )
        families.append(
            {
                "family": family,
                "fold_count": len(held_values),
                "head_count": len(rows),
                "pass_count": sum(bool(row["passed"]) for row in rows),
                "failed_head_count": sum(not bool(row["passed"]) for row in rows),
                "minimum_training_row_count": min(int(row["training_row_count"]) for row in rows),
                "rows": rows,
                "passed": all(bool(row["passed"]) for row in rows),
            }
        )
    failed = sum(int(family["failed_head_count"]) for family in families)
    return {
        "required_neighbor_count": required,
        "family_count": len(families),
        "head_count": sum(int(family["head_count"]) for family in families),
        "pass_count": sum(int(family["pass_count"]) for family in families),
        "failed_head_count": failed,
        "minimum_training_row_count": min(int(family["minimum_training_row_count"]) for family in families),
        "families": families,
        "passed": failed == 0,
    }


def _fold_metrics(
    folds: Sequence[dict[str, Any]],
    cfg: Mapping[str, Any],
    *,
    held_key: str,
    leave_one_out: bool,
) -> tuple[list[np.ndarray], dict[str, Any]]:
    contained_total = component_total = 0
    maximum_error = np.zeros(5, dtype=np.float64)
    maximum_tube = np.zeros(5, dtype=np.float64)
    rows = []
    shared_tube = shared_evidence = None
    if not leave_one_out:
        shared_tube, shared_evidence = ind31._tube(folds, lambda _row: True, cfg)
    for fold in folds:
        if leave_one_out:
            held = fold[held_key]
            tube, tube_evidence = ind31._tube(
                folds, lambda row, held=held: row[held_key] != held, cfg
            )
        else:
            tube, tube_evidence = shared_tube, shared_evidence
        contained = component_count = 0
        fold_error = np.zeros(5, dtype=np.float64)
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values, dtype=np.float64).reshape((-1, 5))
                contained += int(np.count_nonzero(residual <= tube[interval][offset] + 1e-15))
                component_count += residual.size
                if len(residual):
                    fold_error = np.maximum(fold_error, np.max(residual, axis=0))
        maximum_error = np.maximum(maximum_error, fold_error * FACTORS)
        maximum_tube = np.maximum(maximum_tube, np.max(np.concatenate(tube), axis=0) * FACTORS)
        contained_total += contained
        component_total += component_count
        fold["tube"] = tube
        row = {
            held_key: fold[held_key],
            "model_digest": fold["model_digest"],
            "global_model_digest": fold["model_evidence"]["global_model_digest"],
            "local_model_digest": fold["model_evidence"]["local_model_digest"],
            "residual_digest": fold["residual_digest"],
            "maximum_physical_error": (fold_error * FACTORS).tolist(),
            "contained_count": contained,
            "component_count": component_count,
            "tube_evidence": tube_evidence,
        }
        if "support" in fold:
            row["support"] = fold["support"]
        rows.append(row)
    gates = cfg["model_gates"]
    rate = contained_total / component_total
    support = all(fold.get("support", {"passed": True})["passed"] for fold in folds)
    passed = bool(
        np.all(maximum_error <= np.asarray(gates["maximum_point_error"]) + 1e-15)
        and np.all(maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15)
        and rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
        and support
    )
    evidence = {
        "fold_count": len(folds),
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "contained_count": contained_total,
        "component_count": component_total,
        "containment_rate": rate,
        "fold_rows": rows,
        "passed": passed,
    }
    if held_key == "held_pair":
        evidence["state_support_pass_count"] = sum(bool(fold["support"]["passed"]) for fold in folds)
    return shared_tube if shared_tube is not None else [], evidence


def _outer(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    source_cfg: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    pairs = sorted({str(row["pair_id"]) for row in trajectories})
    folds = []
    artifact = []
    for held_pair in pairs:
        training = [pair for pair in pairs if pair != held_pair]
        model = _fit_model(
            trajectories,
            lambda row, allowed=set(training): row["pair_id"] in allowed,
            cfg,
        )
        held = [row for row in trajectories if row["pair_id"] == held_pair]
        residual_groups, residual_digest, predictions = _residuals(model, held, cfg)
        evidence = _model_evidence(model)
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": training,
                "model_digest": evidence["ensemble_model_digest"],
                "model_evidence": evidence,
                "residual_groups": residual_groups,
                "residual_digest": residual_digest,
                "support": ind31._support(
                    trajectories,
                    training,
                    held_pair,
                    float(source_cfg["model_contract"]["support_threshold_multiplier"]),
                ),
            }
        )
        artifact.append({"held_pair": held_pair, "trajectories": predictions})
    _unused, metrics = _fold_metrics(folds, cfg, held_key="held_pair", leave_one_out=True)
    return folds, metrics, artifact


def _schedule(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    folds = []
    artifact = []
    for held_schedule in schedules:
        model = _fit_model(
            trajectories,
            lambda row, held=held_schedule: row["schedule_id"] != held,
            cfg,
        )
        held = [row for row in trajectories if row["schedule_id"] == held_schedule]
        if len(held) != 16:
            raise ValueError("independent R8R43 schedule fold cardinality changed")
        residual_groups, residual_digest, predictions = _residuals(model, held, cfg)
        evidence = _model_evidence(model)
        folds.append(
            {
                "held_schedule": held_schedule,
                "model_digest": evidence["ensemble_model_digest"],
                "model_evidence": evidence,
                "residual_groups": residual_groups,
                "residual_digest": residual_digest,
            }
        )
        artifact.append({"held_schedule": held_schedule, "trajectories": predictions})
    tube, metrics = _fold_metrics(folds, cfg, held_key="held_schedule", leave_one_out=False)
    return tube, folds, metrics, artifact


def _verify_bank(
    trajectories: Sequence[Mapping[str, Any]], evidence: Mapping[str, Any], cfg: Mapping[str, Any]
) -> None:
    contract = cfg["bank_contract"]
    rows = sum(len(interval["targets"]) for trajectory in trajectories for interval in trajectory["intervals"])
    if (
        int(evidence["trajectory_count"]) != int(contract["trajectory_count"])
        or int(evidence["context_count"]) != int(contract["history_context_count"])
        or int(evidence["schedule_count"]) != int(contract["schedule_count"])
        or int(evidence["interval_record_count"]) != int(contract["interval_record_count"])
        or rows != int(contract["five_component_time_row_count"])
        or any(evidence[key] != contract[key] for key in ("bank_digest", "feature_digest", "target_digest"))
    ):
        raise ValueError("independent R8R43 bank reproduction changed")


def _compute(
    ctx: Any,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    bank_evidence: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _verify_bank(trajectories, bank_evidence, ctx.cfg)
    cardinality = _cardinality(trajectories, ctx.cfg)
    if not cardinality["passed"]:
        raise ValueError("independent R8R43 cardinality failed")
    folds, outer, outer_predictions = _outer(trajectories, ctx.cfg, ctx.source_ctx.cfg)
    schedule_tube, schedule_folds, schedule, schedule_predictions = _schedule(trajectories, ctx.cfg)
    pair_tube, pair_evidence = ind31._tube(folds, lambda _row: True, ctx.cfg)
    combined_tube = [np.maximum(pair, schedule_value) for pair, schedule_value in zip(pair_tube, schedule_tube)]
    combined_maximum = np.max(np.concatenate(combined_tube), axis=0) * FACTORS
    combined_passed = bool(
        np.all(combined_maximum <= np.asarray(ctx.cfg["model_gates"]["maximum_tube_half_width"]) + 1e-15)
    )
    scientific = bool(outer["passed"] and schedule["passed"] and combined_passed)
    route = ctx.cfg["routes"]["pass" if scientific else "model_fail"]
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
        "finite_prediction_rate": 1.0,
        "forbidden_predictor_input_count": 0,
        "model_gate_passed": scientific,
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
        "model_kind": "fixed_affine_dominant_global_ridge_local_affine_cold_ensemble",
        "bank_evidence": bank_evidence,
        "outer_model_evidence": [{"held_pair": fold["held_pair"], **fold["model_evidence"]} for fold in folds],
        "schedule_model_evidence": [{"held_schedule": fold["held_schedule"], **fold["model_evidence"]} for fold in schedule_folds],
        "outer_predictions": outer_predictions,
        "schedule_predictions": schedule_predictions,
        "pair_tube": pair_tube,
        "schedule_tube": schedule_tube,
        "combined_tube": combined_tube,
    }
    return r8r43._jsonable(detailed), r8r43._jsonable(artifact)


def _prediction_map(
    rows: Sequence[Mapping[str, Any]], held_field: str, prediction_field: str
) -> dict[tuple[str, str], np.ndarray]:
    return {
        (str(fold[held_field]), str(trajectory["trajectory_id"])): np.concatenate(
            [np.asarray(row, dtype=np.float64).reshape((-1, 5)) for row in trajectory[prediction_field]]
        )
        for fold in rows
        for trajectory in fold["trajectories"]
    }


def _neighbor_map(rows: Sequence[Mapping[str, Any]], held_field: str) -> dict[tuple[str, str], Any]:
    return {
        (str(fold[held_field]), str(trajectory["trajectory_id"])): trajectory["neighbor_key_digests"]
        for fold in rows
        for trajectory in fold["trajectories"]
    }


def _scaled_prediction_difference(
    primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    scales = np.asarray(cfg["model_contract"]["primary_independent_component_scales"], dtype=np.float64)
    maximum = 0.0
    for family, held_field in (("outer_predictions", "held_pair"), ("schedule_predictions", "held_schedule")):
        for field in ("global_predictions", "local_predictions", "ensemble_predictions", "absolute_residuals"):
            left = _prediction_map(primary[family], held_field, field)
            right = _prediction_map(independent[family], held_field, field)
            if set(left) != set(right):
                return math.inf
            for key in left:
                if left[key].shape != right[key].shape:
                    return math.inf
                maximum = max(maximum, float(np.max(np.abs(left[key] - right[key]) * FACTORS / scales)))
    return maximum


def _neighbor_agreement(primary: Mapping[str, Any], independent: Mapping[str, Any]) -> bool:
    return all(
        _neighbor_map(primary[family], held_field) == _neighbor_map(independent[family], held_field)
        for family, held_field in (("outer_predictions", "held_pair"), ("schedule_predictions", "held_schedule"))
    )


def _evidence_map(model: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    output = {}
    for family, held_field in (("outer_model_evidence", "held_pair"), ("schedule_model_evidence", "held_schedule")):
        for fold in model[family]:
            output[(family, str(fold[held_field]))] = fold
    return output


def _scaled_model_difference(primary: Mapping[str, Any], independent: Mapping[str, Any]) -> float:
    left = _evidence_map(primary)
    right = _evidence_map(independent)
    if set(left) != set(right):
        return math.inf
    maximum = 0.0
    for key in left:
        a, b = left[key], right[key]
        if a["model_kind"] != b["model_kind"]:
            return math.inf
        ga, gb = a["global_model"], b["global_model"]
        if len(ga["intervals"]) != len(gb["intervals"]):
            return math.inf
        for ia, ib in zip(ga["intervals"], gb["intervals"]):
            if ia["interval"] != ib["interval"] or len(ia["offsets"]) != len(ib["offsets"]):
                return math.inf
            for oa, ob in zip(ia["offsets"], ib["offsets"]):
                if oa["sample_offset"] != ob["sample_offset"] or oa["training_row_count"] != ob["training_row_count"]:
                    return math.inf
                for field in ("intercept", "coefficients"):
                    xa = np.asarray(oa[field], dtype=np.float64)
                    xb = np.asarray(ob[field], dtype=np.float64)
                    if xa.shape != xb.shape:
                        return math.inf
                    denominator = np.maximum(1.0, np.maximum(np.abs(xa), np.abs(xb)))
                    maximum = max(maximum, float(np.max(np.abs(xa - xb) / denominator)))
        la, lb = a["local_model_evidence"], b["local_model_evidence"]
        if la["model_kind"] != lb["model_kind"] or len(la["intervals"]) != len(lb["intervals"]):
            return math.inf
        for ia, ib in zip(la["intervals"], lb["intervals"]):
            if ia["interval"] != ib["interval"] or len(ia["groups"]) != len(ib["groups"]):
                return math.inf
            for g1, g2 in zip(ia["groups"], ib["groups"]):
                for field in ("sample_offsets", "training_row_count", "training_key_digest", "target_digest"):
                    if g1[field] != g2[field]:
                        return math.inf
                for field in ("coordinate_mean", "coordinate_scale"):
                    xa = np.asarray(g1[field], dtype=np.float64)
                    xb = np.asarray(g2[field], dtype=np.float64)
                    denominator = np.maximum(1.0, np.maximum(np.abs(xa), np.abs(xb)))
                    maximum = max(maximum, float(np.max(np.abs(xa - xb) / denominator)))
    return maximum


def _scaled_tube_difference(primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]) -> float:
    scales = np.asarray(cfg["model_contract"]["primary_independent_component_scales"], dtype=np.float64)
    maximum = 0.0
    for field in ("pair_tube", "schedule_tube", "combined_tube"):
        if len(primary[field]) != len(independent[field]):
            return math.inf
        for left, right in zip(primary[field], independent[field]):
            a = np.asarray(left, dtype=np.float64)
            b = np.asarray(right, dtype=np.float64)
            if a.shape != b.shape:
                return math.inf
            maximum = max(maximum, float(np.max(np.abs(a - b) * FACTORS / scales)))
    return maximum


def _scaled_metric_difference(primary: Mapping[str, Any], independent: Mapping[str, Any], cfg: Mapping[str, Any]) -> float:
    scales = np.asarray(cfg["model_contract"]["primary_independent_component_scales"], dtype=np.float64)
    maximum = 0.0
    for family in ("outer_model_evaluation", "schedule_jackknife"):
        for field in ("maximum_absolute_physical_error", "maximum_reserved_physical_tube_half_width"):
            a = np.asarray(primary[family][field], dtype=np.float64)
            b = np.asarray(independent[family][field], dtype=np.float64)
            maximum = max(maximum, float(np.max(np.abs(a - b) / scales)))
        for field in ("contained_count", "component_count", "passed"):
            if primary[family].get(field) != independent[family].get(field):
                return math.inf
    a = np.asarray(primary["combined_tube_maximum_physical_half_width"], dtype=np.float64)
    b = np.asarray(independent["combined_tube_maximum_physical_half_width"], dtype=np.float64)
    maximum = max(maximum, float(np.max(np.abs(a - b) / scales)))
    for field in ("combined_tube_cap_passed", "model_gate_passed", "scientific_gate_passed"):
        if primary[field] != independent[field]:
            return math.inf
    return maximum


def _authenticate_final(stage: Path, contract: Mapping[str, Any], label: str) -> dict[str, Any]:
    paths = {
        "primary_summary": stage / "analysis/primary_summary.json",
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "model": stage / "model/preflight_model.json",
        "independent": stage / "analysis/independent.json",
        "compact_audit": stage / "analysis/compact_audit.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_state": stage / "stage_state.json",
        "stage_manifest": stage / "stage_manifest.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise ValueError(f"independent R8R43 {label} source hash changed")
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    route = contract["required_route"]
    if (
        summary.get("route") != route
        or independent.get("passed") is not True
        or independent.get("primary_route_agreement") is not True
        or final.get("route") != route
        or final.get("integrity_gate_passed") is not True
        or state.get("route") != route
        or manifest.get("final_route") != route
        or bool(final.get("real_tsc_executed"))
        or int(final.get("plant_step_count", -1)) != 0
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise ValueError(f"independent R8R43 {label} source state changed")
    return {"hashes": hashes, "passed": True}


def _authenticate_r8r34(
    stage: Path, contract: Mapping[str, Any]
) -> dict[str, Any]:
    paths = {
        "primary_summary": stage / "analysis/primary_summary.json",
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "model": stage / "model/preflight_model.json",
        "independent_failure": stage / "analysis/independent_failure.json",
        "compact_audit": stage / "analysis/compact_audit.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_state": stage / "stage_state.json",
        "stage_manifest": stage / "stage_manifest.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise ValueError("independent R8R43 R8R34 source hash changed")
    summary = _read(paths["primary_summary"])
    failure = _read(paths["independent_failure"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    if (
        summary.get("route") != contract["required_primary_route"]
        or failure.get("passed") is not False
        or failure.get("primary_route_agreement") is not True
        or failure.get("primary_outcome_agreement") is not True
        or final.get("route") != contract["required_final_route"]
        or final.get("primary_route") != contract["required_primary_route"]
        or final.get("failure_classification")
        != "independent_numerical_reproducibility_gate_failure"
        or state.get("route") != contract["required_final_route"]
        or state.get("independent_completed") is not True
        or manifest.get("final_route") != contract["required_final_route"]
        or bool(final.get("real_tsc_executed"))
        or int(final.get("plant_step_count", -1)) != 0
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("independent R8R43 R8R34 classification changed")
    return {"hashes": hashes, "historical_overall_passed": False, "passed": True}


def audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = r8r43.load_context(args)
    if ctx.cfg.get("stage") != STAGE or ctx.cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R43 configuration identity changed")
    stage = ctx.paths.stage
    summary_path = stage / "analysis/primary_summary.json"
    detailed_path = stage / "analysis/primary_detailed.json"
    model_path = stage / "model/preflight_model.json"
    primary_summary = _read(summary_path)
    primary_detailed = _read(detailed_path)
    primary_model = _read(model_path)
    r31_auth = _authenticate_final(ctx.source_ctx.paths.stage, ctx.cfg["source_r8r31"], "R8R31")
    r34_auth = _authenticate_r8r34(ctx.r8r34_stage, ctx.cfg["source_r8r34"])
    r39_auth = _authenticate_final(ctx.r8r39_stage, ctx.cfg["source_r8r39"], "R8R39")
    r41_auth = _authenticate_final(ctx.r8r41_stage, ctx.cfg["source_r8r41"], "R8R41")
    independent_transitive = ind31._authenticate(args, ctx.source_ctx.cfg)
    trajectories = ind31._build_bank(args, ctx.source_ctx.cfg)
    bank_evidence = ind31._bank_evidence(trajectories)
    independent_detailed, independent_model = _compute(
        ctx,
        {
            "r8r31_final": r31_auth,
            "r8r34_historical_failure": r34_auth,
            "r8r39_final": r39_auth,
            "r8r41_final": r41_auth,
            "independent_transitive": independent_transitive,
            "passed": True,
        },
        trajectories,
        bank_evidence,
    )
    tolerance = float(ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"])
    bank_difference = _maximum_difference(primary_detailed["bank_evidence"], independent_detailed["bank_evidence"])
    neighbor_agreement = _neighbor_agreement(primary_model, independent_model)
    model_difference = _scaled_model_difference(primary_model, independent_model)
    prediction_difference = _scaled_prediction_difference(primary_model, independent_model, ctx.cfg)
    tube_difference = _scaled_tube_difference(primary_model, independent_model, ctx.cfg)
    metric_difference = _scaled_metric_difference(primary_detailed, independent_detailed, ctx.cfg)
    route_agreement = bool(primary_detailed["route"] == independent_detailed["route"] and primary_summary["route"] == independent_detailed["route"])
    outcome_agreement = bool(
        primary_detailed["integrity_gate_passed"] is True
        and independent_detailed["integrity_gate_passed"] is True
        and primary_detailed["scientific_gate_passed"] is independent_detailed["scientific_gate_passed"]
        and primary_summary["scientific_gate_passed"] is independent_detailed["scientific_gate_passed"]
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": AUDIT_KIND,
        "source_authentication": independent_detailed["source_authentication"],
        "bank_evidence": bank_evidence,
        "independent_model_artifact_sha256": _digest(independent_model),
        "maximum_bank_absolute_difference": bank_difference,
        "maximum_scaled_model_difference": model_difference,
        "maximum_scaled_prediction_difference": prediction_difference,
        "maximum_scaled_tube_difference": tube_difference,
        "maximum_scaled_metric_difference": metric_difference,
        "primary_bank_agreement": bank_difference == 0.0,
        "primary_neighbor_agreement": neighbor_agreement,
        "primary_model_agreement": model_difference <= tolerance,
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
        and result["primary_model_agreement"]
        and result["primary_prediction_agreement"]
        and result["primary_tube_agreement"]
        and result["primary_metric_agreement"]
        and result["primary_route_agreement"]
        and result["primary_outcome_agreement"]
    )
    if not result["passed"]:
        _write(stage / "analysis/independent_failure.json", result)
        raise ValueError("independent R8R43 preflight disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in r8r43.ARGUMENT_NAMES:
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    return parser


def main() -> None:
    result = audit(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
