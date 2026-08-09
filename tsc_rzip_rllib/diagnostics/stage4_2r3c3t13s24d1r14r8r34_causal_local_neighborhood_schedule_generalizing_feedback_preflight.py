"""R8R34 causal local-neighborhood schedule-generalization preflight."""

from __future__ import annotations

import argparse
import copy
import json
import math
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight
    as r8r32,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r33_uniformly_supported_rank12_schedule_generalizing_feedback_preflight
    as r8r33,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R34"
IDENTITY = "causal_local_neighborhood_schedule_generalizing_feedback_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r34_causal_local_neighborhood_schedule_generalizing_feedback_preflight"
FACTORS = r8r31.OUTPUT_FACTORS
MAX_COUNTS = r8r31.MAX_COUNTS

_read = r8r32._read
_write = r8r32._write
_sha = r8r32._sha
_digest = r8r32._digest
_jsonable = r8r32._jsonable


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    stage: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path


@dataclass(frozen=True)
class Context:
    cfg: Mapping[str, Any]
    config_path: Path
    paths: Paths
    r8r33_ctx: Any
    r8r33_stage: Path
    source_ctx: Any


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(
        stage=stage,
        analysis=stage / "analysis",
        model=stage / "model",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    root = project_root.resolve()
    design = (root / str(cfg["design_document"])).resolve()
    source_config = (root / str(cfg["source_r8r33_config"])).resolve()
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    gates = cfg["model_gates"]
    offline = cfg["offline_gate"]
    scope = cfg["scientific_scope"]
    expected_routes = {
        "execution_fail": "CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP",
        "model_fail": "CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC",
        "authority_fail": "CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED",
        "pass": "CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED",
    }
    invalid = (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source_config.is_file()
        or _sha(source_config) != cfg.get("source_r8r33_config_sha256")
        or int(bank.get("trajectory_count", -1)) != 560
        or int(bank.get("physical_pair_count", -1)) != 8
        or int(bank.get("history_context_count", -1)) != 16
        or int(bank.get("schedule_count", -1)) != 35
        or int(bank.get("interval_record_count", -1)) != 3360
        or list(bank.get("decision_task_steps", [])) != [10, 12, 14, 16, 18, 22]
        or int(model.get("causal_base_dimension", -1)) != 44
        or int(model.get("action_dimension", -1)) != 18
        or int(model.get("coordinate_dimension", -1)) != 62
        or float(model.get("coordinate_scale_floor", -1.0)) != 1e-12
        or int(model.get("neighbor_count", -1)) != 64
        or int(model.get("neighbor_rows_per_history_context", -1)) != 4
        or int(model.get("history_context_count", -1)) != 16
        or float(model.get("slope_ridge_penalty", -1.0)) != 1.0
        or float(model.get("intercept_penalty", -1.0)) != 0.0
        or float(model.get("uniform_neighbor_weight", -1.0)) != 1.0
        or float(model.get("reserve_multiplier", -1.0)) != 1.25
        or list(model.get("physical_point_error_floors", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or list(model.get("primary_independent_component_scales", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or float(model.get("primary_independent_scaled_tolerance", -1.0)) != 1e-9
        or any(
            bool(model.get(name, True))
            for name in (
                "neighbor_search_allowed",
                "feature_search_allowed",
                "hyperparameter_search_allowed",
                "response_weighting_allowed",
                "outlier_deletion_allowed",
                "tube_clipping_allowed",
            )
        )
        or list(gates.get("maximum_point_error", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or list(gates.get("maximum_tube_half_width", []))
        != [0.025, 0.025, 5000.0, 0.08, 0.08]
        or float(gates.get("required_reserved_tube_containment_rate", -1.0)) != 1.0
        or int(offline.get("required_safe_search_context_count", -1)) != 16
        or int(offline.get("minimum_predicted_repaired_failed_baseline_count", -1)) != 1
        or int(offline.get("maximum_predicted_regressed_baseline_pass_count", -1)) != 0
        or int(offline.get("minimum_predicted_oracle_count", -1)) != 7
        or int(offline.get("minimum_nonzero_first_action_count", -1)) != 1
        or int(offline.get("required_fault_injection_count", -1)) != 6
        or cfg.get("routes") != expected_routes
        or scope.get("zero_new_tsc") is not True
        or scope.get("controller_execution_authorized") is not False
        or scope.get("gate_a_qualified") is not False
        or scope.get("expert_data_allowed") is not False
        or scope.get("bc_dagger_or_rl_allowed") is not False
        or scope.get("all_stage_trajectories_allowed_in_expert_dataset") is not False
    )
    if invalid:
        raise ValueError("R8R34 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    root = _root()
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=root)
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (root / str(cfg["source_r8r33_config"])).resolve()
    source_args.run_dir = args.r8r33_run.expanduser().resolve()
    r8r33_ctx = r8r33.load_context(source_args)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r33_ctx=r8r33_ctx,
        r8r33_stage=r8r33_ctx.paths.stage,
        source_ctx=r8r33_ctx.r8r32_ctx.source_ctx,
    )


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    contract = ctx.cfg["source_r8r33"]
    paths = {
        "primary_summary": ctx.r8r33_stage / "analysis/primary_summary.json",
        "primary_detailed": ctx.r8r33_stage / "analysis/primary_detailed.json",
        "model": ctx.r8r33_stage / "model/preflight_model.json",
        "independent_failure": ctx.r8r33_stage / "analysis/independent_failure.json",
        "compact_audit": ctx.r8r33_stage / "analysis/compact_audit.json",
        "final_report": ctx.r8r33_stage / "analysis/final_report.json",
        "stage_state": ctx.r8r33_stage / "stage_state.json",
        "stage_manifest": ctx.r8r33_stage / "stage_manifest.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise ValueError("R8R34 final R8R33 source hash changed")
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent_failure"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    if (
        summary.get("route") != contract["required_primary_route"]
        or independent.get("passed") is not False
        or independent.get("primary_route_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or final.get("route") != contract["required_final_route"]
        or final.get("primary_route") != contract["required_primary_route"]
        or final.get("failure_classification")
        != "independent_numerical_reproducibility_gate_failure"
        or final.get("integrity_gate_passed") is not False
        or state.get("route") != contract["required_final_route"]
        or manifest.get("final_route") != contract["required_final_route"]
        or any(bool(value) for value in (final.get("real_tsc_executed"),))
        or int(final.get("plant_step_count", -1)) != 0
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R34 final R8R33 source state changed")
    return {
        "r8r33_final": {"hashes": hashes, "passed": True},
        "transitive": r8r33.authenticate_sources(ctx.r8r33_ctx),
        "passed": True,
    }


def _verify_bank(evidence: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    contract = cfg["bank_contract"]
    if (
        int(evidence["trajectory_count"]) != int(contract["trajectory_count"])
        or int(evidence["context_count"]) != int(contract["history_context_count"])
        or int(evidence["schedule_count"]) != int(contract["schedule_count"])
        or int(evidence["interval_record_count"]) != int(contract["interval_record_count"])
        or any(
            evidence[key] != contract[key]
            for key in ("bank_digest", "feature_digest", "target_digest")
        )
    ):
        raise ValueError("R8R34 bank reproduction changed")


def coordinate62(row: Mapping[str, Any]) -> np.ndarray:
    feature = np.asarray(row["feature"], dtype=float).reshape(44)
    expanded = np.asarray(row["expanded"], dtype=float).reshape(238)
    value = np.concatenate((feature, expanded[44:62]))
    if value.shape != (62,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R34 causal coordinate invalid")
    return value


def fit_model(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    chosen = sorted(
        (row for row in trajectories if selected(row)),
        key=lambda row: str(row["trajectory_id"]),
    )
    if not chosen:
        raise ValueError("R8R34 fit selection empty")
    intervals = []
    for interval in range(6):
        maximum = max(len(row["intervals"][interval]["targets"]) for row in chosen)
        by_eligibility: dict[tuple[str, ...], list[int]] = {}
        for offset in range(maximum):
            ids = tuple(
                str(row["trajectory_id"])
                for row in chosen
                if len(row["intervals"][interval]["targets"]) > offset
            )
            by_eligibility.setdefault(ids, []).append(offset)
        groups = []
        for ids, offsets in by_eligibility.items():
            allowed = set(ids)
            rows = [row for row in chosen if str(row["trajectory_id"]) in allowed]
            coordinates = np.asarray(
                [coordinate62(row["intervals"][interval]) for row in rows], dtype=float
            ).reshape((-1, 62))
            mean = np.mean(coordinates, axis=0)
            scale = np.maximum(
                np.sqrt(np.mean(np.square(coordinates - mean), axis=0)),
                float(cfg["model_contract"]["coordinate_scale_floor"]),
            )
            standardized = (coordinates - mean) / scale
            targets = np.asarray(
                [
                    np.concatenate(
                        [
                            np.asarray(row["intervals"][interval]["targets"][offset], dtype=float)
                            for offset in offsets
                        ]
                    )
                    for row in rows
                ],
                dtype=float,
            )
            if (
                len(rows) < int(cfg["model_contract"]["neighbor_count"])
                or standardized.shape != (len(rows), 62)
                or targets.shape != (len(rows), 5 * len(offsets))
                or not np.all(np.isfinite(standardized))
                or not np.all(np.isfinite(targets))
            ):
                raise ValueError("R8R34 local training group invalid")
            groups.append(
                {
                    "sample_offsets": offsets,
                    "training_row_count": len(rows),
                    "training_keys": [str(row["trajectory_id"]) for row in rows],
                    "coordinate_mean": mean,
                    "coordinate_scale": scale,
                    "standardized_coordinates": standardized,
                    "targets": targets,
                }
            )
        intervals.append({"interval": interval, "groups": groups})
    return {"model_kind": "causal_local_affine_k64_ridge1", "intervals": intervals}


def model_evidence(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model_kind": model["model_kind"],
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
                        "target_digest": _digest(np.asarray(group["targets"]).tolist()),
                    }
                    for group in interval["groups"]
                ],
            }
            for interval in model["intervals"]
        ],
    }


def predict_group(
    group: Mapping[str, Any],
    query_coordinate: np.ndarray,
    cfg: Mapping[str, Any],
    *,
    solver: str,
) -> np.ndarray:
    mean = np.asarray(group["coordinate_mean"], dtype=float).reshape(62)
    scale = np.asarray(group["coordinate_scale"], dtype=float).reshape(62)
    training = np.asarray(group["standardized_coordinates"], dtype=float)
    target = np.asarray(group["targets"], dtype=float)
    query = (np.asarray(query_coordinate, dtype=float).reshape(62) - mean) / scale
    distance = np.linalg.norm(training - query, axis=1)
    order = np.argsort(distance, kind="mergesort")
    count = int(cfg["model_contract"]["neighbor_count"])
    chosen = order[:count]
    difference = training[chosen] - query
    response = target[chosen]
    difference_mean = np.mean(difference, axis=0)
    response_mean = np.mean(response, axis=0)
    centered_difference = difference - difference_mean
    centered_response = response - response_mean
    ridge = float(cfg["model_contract"]["slope_ridge_penalty"])
    active = np.any(centered_difference != 0.0, axis=0)
    slopes = np.zeros((62, response.shape[1]), dtype=float)
    if solver == "augmented_lstsq":
        if np.any(active):
            active_count = int(np.sum(active))
            slopes[active] = np.linalg.lstsq(
                np.vstack(
                    (
                        centered_difference[:, active],
                        math.sqrt(ridge) * np.eye(active_count),
                    )
                ),
                np.vstack(
                    (centered_response, np.zeros((active_count, response.shape[1])))
                ),
                rcond=None,
            )[0]
    elif solver == "normal":
        if np.any(active):
            active_difference = centered_difference[:, active]
            active_count = int(np.sum(active))
            normal = (
                active_difference.T @ active_difference
                + ridge * np.eye(active_count)
            )
            slopes[active] = np.linalg.solve(
                normal, active_difference.T @ centered_response
            )
    else:
        raise ValueError(f"unknown R8R34 solver {solver}")
    output = response_mean - difference_mean @ slopes
    if output.shape != (response.shape[1],) or not np.all(np.isfinite(output)):
        raise ValueError("R8R34 local prediction invalid")
    return output


def predict(
    model: Mapping[str, Any],
    row: Mapping[str, Any],
    cfg: Mapping[str, Any],
    *,
    solver: str,
    predict_group_fn: Callable[..., np.ndarray] = predict_group,
) -> np.ndarray:
    interval = int(row["interval"])
    count = len(row["targets"])
    query = coordinate62(row)
    output = np.empty((count, 5), dtype=float)
    filled = np.zeros(count, dtype=bool)
    for group in model["intervals"][interval]["groups"]:
        values = predict_group_fn(group, query, cfg, solver=solver).reshape(
            (len(group["sample_offsets"]), 5)
        )
        for index, offset in enumerate(group["sample_offsets"]):
            if int(offset) < count:
                output[int(offset)] = values[index]
                filled[int(offset)] = True
    if not np.all(filled) or not np.all(np.isfinite(output)):
        raise ValueError("R8R34 prediction coverage invalid")
    return output


def local_cardinality_audit(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    required = int(cfg["model_contract"]["neighbor_count"])
    definitions = (
        (
            "whole_physical_pair",
            sorted({str(row["pair_id"]) for row in trajectories}),
            lambda row, held: row["pair_id"] != held,
        ),
        (
            "whole_schedule",
            sorted({str(row["schedule_id"]) for row in trajectories}),
            lambda row, held: row["schedule_id"] != held,
        ),
    )
    families = []
    for family, held_values, selected in definitions:
        rows = []
        for held in held_values:
            chosen = [row for row in trajectories if selected(row, held)]
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
                "minimum_training_row_count": min(
                    int(row["training_row_count"]) for row in rows
                ),
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
        "minimum_training_row_count": min(
            int(family["minimum_training_row_count"]) for family in families
        ),
        "families": families,
        "passed": failed == 0,
    }


def _residuals(
    model: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    *,
    solver: str,
    predict_group_fn: Callable[..., np.ndarray],
) -> tuple[list[list[list[np.ndarray]]], dict[str, Any], list[dict[str, Any]]]:
    groups: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in MAX_COUNTS]
    serial = []
    predictions = []
    for trajectory in trajectories:
        residual_rows = []
        prediction_rows = []
        for interval, row in enumerate(trajectory["intervals"]):
            forecast = predict(
                model, row, cfg, solver=solver, predict_group_fn=predict_group_fn
            )
            residual = np.abs(np.asarray(row["targets"], dtype=float) - forecast)
            residual_rows.append(residual.tolist())
            prediction_rows.append(forecast.tolist())
            for offset, value in enumerate(residual):
                groups[interval][offset].append(value)
        serial.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "absolute_residuals": residual_rows,
            }
        )
        predictions.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "predictions": prediction_rows,
            }
        )
    return groups, {"residual_digest": _digest(serial)}, predictions


def outer_model_evaluation(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    source_cfg: Mapping[str, Any],
    *,
    solver: str,
    fit_model_fn: Callable[..., dict[str, Any]] = fit_model,
    predict_group_fn: Callable[..., np.ndarray] = predict_group,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    pairs = sorted({str(row["pair_id"]) for row in trajectories})
    folds = []
    prediction_artifact = []
    for held_pair in pairs:
        training = [pair for pair in pairs if pair != held_pair]
        model = fit_model_fn(
            trajectories,
            lambda row, allowed=set(training): row["pair_id"] in allowed,
            cfg,
        )
        held = [row for row in trajectories if row["pair_id"] == held_pair]
        groups, evidence, predictions = _residuals(
            model,
            held,
            cfg,
            solver=solver,
            predict_group_fn=predict_group_fn,
        )
        model_record = model_evidence(model)
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": training,
                "model": model,
                "model_digest": _digest(model_record),
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
                "support": r8r31._support_fold(
                    trajectories,
                    training,
                    held_pair,
                    float(source_cfg["model_contract"]["support_threshold_multiplier"]),
                ),
            }
        )
        prediction_artifact.append(
            {"held_pair": held_pair, "trajectories": predictions}
        )
    contained = total = 0
    maximum_error = np.zeros(5)
    maximum_tube = np.zeros(5)
    fold_rows = []
    for fold in folds:
        tube, tube_evidence = r8r31._tube_from_fold_groups(
            folds, lambda row, held=fold["held_pair"]: row["held_pair"] != held, cfg
        )
        fold_contained = fold_total = 0
        fold_error = np.zeros(5)
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values).reshape((-1, 5))
                fold_contained += int(
                    np.count_nonzero(residual <= tube[interval][offset] + 1e-15)
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
        and np.all(maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15)
        and rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
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
    }, prediction_artifact


def schedule_jackknife(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    *,
    solver: str,
    fit_model_fn: Callable[..., dict[str, Any]] = fit_model,
    predict_group_fn: Callable[..., np.ndarray] = predict_group,
) -> tuple[list[np.ndarray], dict[str, Any], list[dict[str, Any]]]:
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    folds = []
    prediction_artifact = []
    for held_schedule in schedules:
        model = fit_model_fn(
            trajectories,
            lambda row, held=held_schedule: row["schedule_id"] != held,
            cfg,
        )
        held = [row for row in trajectories if row["schedule_id"] == held_schedule]
        if len(held) != 16:
            raise ValueError("R8R34 schedule fold cardinality changed")
        groups, evidence, predictions = _residuals(
            model,
            held,
            cfg,
            solver=solver,
            predict_group_fn=predict_group_fn,
        )
        model_record = model_evidence(model)
        folds.append(
            {
                "held_schedule": held_schedule,
                "model_digest": _digest(model_record),
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
            }
        )
        prediction_artifact.append(
            {"held_schedule": held_schedule, "trajectories": predictions}
        )
    tube, tube_evidence = r8r31._tube_from_fold_groups(folds, lambda row: True, cfg)
    contained = total = 0
    maximum_error = np.zeros(5)
    for fold in folds:
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values).reshape((-1, 5))
                contained += int(
                    np.count_nonzero(residual <= tube[interval][offset] + 1e-15)
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
        and np.all(maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15)
    )
    return tube, {
        "schedule_count": len(schedules),
        "training_schedule_count": len(schedules) - 1,
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
    }, prediction_artifact


def compute_from_bank(
    ctx: Context,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
    bank: Mapping[str, Any],
    *,
    solver: str,
    fit_model_fn: Callable[..., dict[str, Any]] = fit_model,
    predict_group_fn: Callable[..., np.ndarray] = predict_group,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _verify_bank(bank, ctx.cfg)
    cardinality = local_cardinality_audit(trajectories, ctx.cfg)
    if not cardinality["passed"]:
        raise ValueError("R8R34 frozen local-neighbor cardinality failed")
    folds, outer, outer_predictions = outer_model_evaluation(
        trajectories,
        ctx.cfg,
        ctx.source_ctx.cfg,
        solver=solver,
        fit_model_fn=fit_model_fn,
        predict_group_fn=predict_group_fn,
    )
    schedule_tube, schedule, schedule_predictions = schedule_jackknife(
        trajectories,
        ctx.cfg,
        solver=solver,
        fit_model_fn=fit_model_fn,
        predict_group_fn=predict_group_fn,
    )
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
            <= np.asarray(ctx.cfg["model_gates"]["maximum_tube_half_width"]) + 1e-15
        )
    )
    model_gate = bool(outer["passed"] and schedule["passed"] and combined_passed)
    planning = {
        "ran": False,
        "safe_search_context_count": 0,
        "predicted_repaired_failed_baseline_count": 0,
        "predicted_regressed_baseline_pass_count": 0,
        "predicted_fallback_plus_plan_oracle_count": 0,
        "nonzero_first_action_count": 0,
        "plans": [],
        "passed": False,
    }
    faults: Mapping[str, Any] = {"ran": False, "passed": False}
    hull_summary: list[dict[str, Any]] = []
    support_artifact: Mapping[str, Any] = {}
    planning_model_evidence: Mapping[str, Any] = {"ran": False}
    if model_gate:
        model = fit_model_fn(trajectories, lambda _row: True, ctx.cfg)
        planning_model_evidence = model_evidence(model)
        hulls = r8r31.transition_hulls(trajectories, ctx.source_ctx.cfg)
        support = r8r31.planning_support(trajectories, ctx.source_ctx.cfg)
        predictor = lambda current_model, row: predict(
            current_model,
            row,
            ctx.cfg,
            solver=solver,
            predict_group_fn=predict_group_fn,
        )
        plans = [
            r8r31.plan_context(
                ctx.source_ctx,
                context_meta[key],
                model,
                combined_tube,
                support,
                hulls,
                predict_fn=predictor,
            )
            for key in sorted(context_meta)
        ]
        baseline_source = _read(
            ctx.source_ctx.r8r28_stage / "analysis/primary_detailed.json"
        )
        baseline = {
            (str(row["pair_id"]), str(row["history_member"])): bool(
                row["baseline"]["formal_contract_pass"]
            )
            for row in baseline_source["formal_authority"]["context_rows"]
        }
        repairs = regressions = oracle = nonzero = 0
        for plan in plans:
            key = (plan["pair_id"], plan["history_member"])
            robust = bool(plan["robust_formal_plan_found"])
            policy = robust or baseline[key]
            repairs += int(not baseline[key] and robust)
            regressions += int(baseline[key] and not policy)
            oracle += int(policy)
            selected = plan.get("selected_plan") or {}
            tokens = selected.get("candidate_indices") or []
            nonzero += int(robust and bool(tokens) and int(tokens[0]) != 0)
            plan["baseline_formal_pass"] = baseline[key]
            plan["fallback_or_plan_predicted_pass"] = policy
        faults = r8r31.fault_injections()
        gate = ctx.cfg["offline_gate"]
        planning_passed = bool(
            len(plans) == int(gate["required_safe_search_context_count"])
            and all(plan["safe_search_complete"] for plan in plans)
            and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
            and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
            and oracle >= int(gate["minimum_predicted_oracle_count"])
            and nonzero >= int(gate["minimum_nonzero_first_action_count"])
            and faults["pass_count"] == int(gate["required_fault_injection_count"])
            and faults["passed"]
        )
        planning = {
            "ran": True,
            "safe_search_context_count": sum(plan["safe_search_complete"] for plan in plans),
            "predicted_repaired_failed_baseline_count": repairs,
            "predicted_regressed_baseline_pass_count": regressions,
            "predicted_fallback_plus_plan_oracle_count": oracle,
            "nonzero_first_action_count": nonzero,
            "plans": plans,
            "passed": planning_passed,
        }
        hull_summary = [
            {
                "interval": row["interval"],
                "affine_rank": row["affine_rank"],
                "observed_transition_count": row["observed_transition_count"],
                "singular_values": row["singular_values"],
                "digest": row["digest"],
            }
            for row in hulls
        ]
        support_artifact = {
            "thresholds": support["thresholds"],
            "training_maxima": support["training_maxima"],
            "features": support["features"],
        }
    scientific = bool(model_gate and planning["passed"])
    route = (
        ctx.cfg["routes"]["model_fail"]
        if not model_gate
        else ctx.cfg["routes"]["pass"]
        if scientific
        else ctx.cfg["routes"]["authority_fail"]
    )
    detailed = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "solver": solver,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "local_cardinality_audit": cardinality,
        "outer_model_evaluation": outer,
        "schedule_jackknife": schedule,
        "pair_planning_tube_evidence": pair_evidence,
        "combined_tube_maximum_physical_half_width": combined_maximum.tolist(),
        "combined_tube_cap_passed": combined_passed,
        "model_gate_passed": model_gate,
        "transition_hulls": hull_summary,
        "planning_evaluation": planning,
        "fault_injection": faults,
        "integrity_gate_passed": True,
        "scientific_gate_passed": scientific,
        "passed": True,
        "route": route,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "solver": solver,
        "bank_evidence": bank,
        "local_cardinality_audit": cardinality,
        "outer_model_evidence": [
            {"held_pair": fold["held_pair"], "model_digest": fold["model_digest"]}
            for fold in folds
        ],
        "outer_predictions": outer_predictions,
        "schedule_predictions": schedule_predictions,
        "planning_model_evidence": planning_model_evidence,
        "pair_tube": pair_tube,
        "schedule_tube": schedule_tube,
        "combined_tube": combined_tube,
        "support": support_artifact,
        "transition_hulls": hull_summary,
        "planning_evaluation": planning,
    }
    return _jsonable(detailed), _jsonable(artifact)


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    outer = detailed["outer_model_evaluation"]
    schedule = detailed["schedule_jackknife"]
    planning = detailed["planning_evaluation"]
    cardinality = detailed["local_cardinality_audit"]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "phase": "offline_primary",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(detailed["scientific_gate_passed"]),
        "route": detailed["route"],
        "trajectory_count": int(detailed["bank_evidence"]["trajectory_count"]),
        "schedule_count": int(detailed["bank_evidence"]["schedule_count"]),
        "interval_record_count": int(detailed["bank_evidence"]["interval_record_count"]),
        "bank_digest": detailed["bank_evidence"]["bank_digest"],
        "feature_digest": detailed["bank_evidence"]["feature_digest"],
        "target_digest": detailed["bank_evidence"]["target_digest"],
        "local_cardinality_gate_passed": bool(cardinality["passed"]),
        "local_cardinality_head_count": int(cardinality["head_count"]),
        "local_cardinality_failed_head_count": int(cardinality["failed_head_count"]),
        "minimum_training_row_count": int(cardinality["minimum_training_row_count"]),
        "outer_model_gate_passed": bool(outer["passed"]),
        "outer_maximum_absolute_physical_error": outer["maximum_absolute_physical_error"],
        "outer_maximum_reserved_physical_tube_half_width": outer[
            "maximum_reserved_physical_tube_half_width"
        ],
        "schedule_jackknife_passed": bool(schedule["passed"]),
        "schedule_maximum_absolute_physical_error": schedule[
            "maximum_absolute_physical_error"
        ],
        "schedule_maximum_reserved_physical_tube_half_width": schedule[
            "maximum_reserved_physical_tube_half_width"
        ],
        "combined_tube_cap_passed": bool(detailed["combined_tube_cap_passed"]),
        "model_gate_passed": bool(detailed["model_gate_passed"]),
        "planning_ran": bool(planning["ran"]),
        "predicted_repaired_failed_baseline_count": int(
            planning["predicted_repaired_failed_baseline_count"]
        ),
        "predicted_fallback_plus_plan_oracle_count": int(
            planning["predicted_fallback_plus_plan_oracle_count"]
        ),
        "nonzero_first_action_count": int(planning["nonzero_first_action_count"]),
        "model_artifact_sha256": model_sha,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R34 primary requires a fresh stage directory")
    ctx.paths.stage.mkdir(parents=True)
    ctx.paths.analysis.mkdir()
    ctx.paths.model.mkdir()
    try:
        authentication = authenticate_sources(ctx)
        trajectories, context_meta, bank = r8r31.build_bank(ctx.source_ctx)
        detailed, artifact = compute_from_bank(
            ctx,
            authentication,
            trajectories,
            context_meta,
            bank,
            solver="augmented_lstsq",
        )
        model_path = ctx.paths.model / "preflight_model.json"
        _write(model_path, artifact)
        _write(ctx.paths.analysis / "primary_detailed.json", detailed)
        summary = _summary(detailed, _sha(model_path))
        _write(ctx.paths.analysis / "primary_summary.json", summary)
        _write(
            ctx.paths.manifest,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "identity": IDENTITY,
                "config_sha256": _sha(ctx.config_path),
                "design_sha256": str(ctx.cfg["design_document_sha256"]),
                "primary_summary_sha256": _sha(
                    ctx.paths.analysis / "primary_summary.json"
                ),
                "primary_detailed_sha256": _sha(
                    ctx.paths.analysis / "primary_detailed.json"
                ),
                "model_sha256": _sha(model_path),
                "zero_tsc_preflight": True,
            },
        )
        _write(
            ctx.paths.state,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "phase_status": "offline_primary_ready_for_independent",
                "finished": not bool(summary["scientific_gate_passed"]),
                "primary_completed": True,
                "independent_completed": False,
                "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
                "route": summary["route"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "controller_execution_authorized": False,
            },
        )
        return summary
    except Exception as exc:
        failure = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "phase": "offline_primary",
            "passed": False,
            "integrity_gate_passed": False,
            "scientific_gate_passed": False,
            "route": ctx.cfg["routes"]["execution_fail"],
            "failure_reason": repr(exc),
            "traceback": traceback.format_exc(),
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
        }
        _write(ctx.paths.analysis / "primary_failure.json", failure)
        _write(
            ctx.paths.state,
            {
                "schema_version": SCHEMA_VERSION,
                "stage": STAGE,
                "phase_status": "offline_primary_execution_failed",
                "finished": True,
                "primary_completed": False,
                "independent_completed": False,
                "scientific_gate_passed": False,
                "route": ctx.cfg["routes"]["execution_fail"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
            },
        )
        raise


def run_finalize(ctx: Context) -> dict[str, Any]:
    paths: dict[str, Path] = {
        "primary_summary": ctx.paths.analysis / "primary_summary.json",
        "primary_detailed": ctx.paths.analysis / "primary_detailed.json",
        "model": ctx.paths.model / "preflight_model.json",
    }
    independent_path = ctx.paths.analysis / "independent.json"
    independent_failure_path = ctx.paths.analysis / "independent_failure.json"
    independent_failed = not independent_path.is_file()
    paths["independent_failure" if independent_failed else "independent"] = (
        independent_failure_path if independent_failed else independent_path
    )
    if any(
        not path.is_file()
        for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)
    ):
        raise ValueError("R8R34 finalization evidence incomplete")
    summary = _read(paths["primary_summary"])
    detailed = _read(paths["primary_detailed"])
    independent = _read(
        paths["independent_failure" if independent_failed else "independent"]
    )
    manifest = _read(ctx.paths.manifest)
    hashes = {name: _sha(path) for name, path in paths.items()}
    agreement_fields = (
        "primary_bank_agreement",
        "primary_prediction_agreement",
        "primary_tube_agreement",
        "primary_metric_agreement",
        "primary_planning_agreement",
        "primary_route_agreement",
        "primary_outcome_agreement",
    )
    difference_fields = (
        "maximum_scaled_prediction_difference",
        "maximum_scaled_tube_difference",
        "maximum_scaled_metric_difference",
        "maximum_scaled_planning_difference",
    )
    tolerance = float(
        ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"]
    )
    if independent_failed:
        failed_numeric_agreements = tuple(
            field
            for field in (
                "primary_prediction_agreement",
                "primary_metric_agreement",
            )
            if independent.get(field) is False
        )
        source_authentication = independent.get("source_authentication", {})
        if (
            independent.get("passed") is not False
            or source_authentication.get("r8r33_final", {}).get("passed") is not True
            or source_authentication.get("independent_transitive", {}).get("passed")
            is not True
            or independent.get("primary_bank_agreement") is not True
            or independent.get("primary_tube_agreement") is not True
            or independent.get("primary_planning_agreement") is not True
            or independent.get("primary_route_agreement") is not True
            or independent.get("primary_outcome_agreement") is not True
            or not failed_numeric_agreements
            or not any(
                float(independent.get(field, 0.0)) > tolerance
                for field in (
                    "maximum_scaled_prediction_difference",
                    "maximum_scaled_metric_difference",
                )
            )
            or float(independent.get("maximum_bank_absolute_difference", math.inf))
            != 0.0
            or independent.get("primary_summary_sha256")
            != hashes["primary_summary"]
            or independent.get("primary_detailed_sha256")
            != hashes["primary_detailed"]
            or independent.get("primary_model_sha256") != hashes["model"]
            or independent.get("route") != summary.get("route")
            or summary.get("route") != ctx.cfg["routes"]["model_fail"]
            or detailed.get("model_gate_passed") is not False
            or detailed.get("planning_evaluation", {}).get("ran") is not False
            or bool(independent.get("real_tsc_executed"))
            or int(independent.get("plant_step_count", -1)) != 0
            or int(independent.get("new_raw_count", -1)) != 0
        ):
            raise ValueError("R8R34 independent-failure evidence invalid")
        compact = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "audit_kind": "r8r34_compact_independent_numeric_failure_finalization",
            "passed": False,
            "integrity_gate_passed": False,
            "primary_integrity_gate_passed": True,
            "scientific_gate_passed": False,
            "primary_scientific_gate_passed": bool(
                summary["scientific_gate_passed"]
            ),
            "route": ctx.cfg["routes"]["execution_fail"],
            "primary_route": summary["route"],
            "failure_classification": (
                "independent_numerical_reproducibility_gate_failure"
            ),
            "failed_numeric_agreements": list(failed_numeric_agreements),
            "primary_independent_scaled_tolerance": tolerance,
            "source_file_sha256": hashes,
            "summary": summary,
            "local_cardinality_audit": detailed["local_cardinality_audit"],
            "outer_model_evaluation": detailed["outer_model_evaluation"],
            "schedule_jackknife": detailed["schedule_jackknife"],
            "combined_tube_maximum_physical_half_width": detailed[
                "combined_tube_maximum_physical_half_width"
            ],
            "combined_tube_cap_passed": detailed["combined_tube_cap_passed"],
            "planning_evaluation": detailed["planning_evaluation"],
            "fault_injection": detailed["fault_injection"],
            "independent_agreement": {
                field: independent[field] for field in agreement_fields
            },
            "independent_maximum_scaled_difference": {
                field: independent[field] for field in difference_fields
            },
            "maximum_bank_absolute_difference": independent[
                "maximum_bank_absolute_difference"
            ],
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
            "controller_execution_authorized": False,
            "gate_a_qualified": False,
            "expert_data_allowed": False,
        }
        compact_path = ctx.paths.analysis / "compact_audit.json"
        _write(compact_path, compact)
        final = copy.deepcopy(compact)
        final["audit_kind"] = "r8r34_final_independent_numeric_failure_report"
        final["compact_audit_sha256"] = _sha(compact_path)
        final_path = ctx.paths.analysis / "final_report.json"
        _write(final_path, final)
        manifest.update(
            {
                "independent_failure_sha256": hashes["independent_failure"],
                "compact_audit_sha256": _sha(compact_path),
                "final_report_sha256": _sha(final_path),
                "primary_route": summary["route"],
                "final_route": ctx.cfg["routes"]["execution_fail"],
                "independent_completed": True,
                "independent_validation_passed": False,
            }
        )
        _write(ctx.paths.manifest, manifest)
        state = _read(ctx.paths.state)
        state.update(
            {
                "phase_status": "offline_preflight_independent_validation_failed",
                "finished": True,
                "primary_completed": True,
                "independent_completed": True,
                "independent_validation_passed": False,
                "scientific_gate_passed": False,
                "primary_scientific_gate_passed": bool(
                    summary["scientific_gate_passed"]
                ),
                "primary_route": summary["route"],
                "route": ctx.cfg["routes"]["execution_fail"],
                "real_tsc_executed": False,
                "plant_step_count": 0,
                "new_raw_count": 0,
                "controller_execution_authorized": False,
            }
        )
        _write(ctx.paths.state, state)
        return final
    if (
        independent.get("passed") is not True
        or any(independent.get(field) is not True for field in agreement_fields)
        or any(
            float(independent.get(field, math.inf)) > tolerance
            for field in difference_fields
        )
        or independent.get("primary_summary_sha256") != hashes["primary_summary"]
        or independent.get("primary_detailed_sha256") != hashes["primary_detailed"]
        or independent.get("primary_model_sha256") != hashes["model"]
        or independent.get("route") != summary.get("route")
        or bool(independent.get("real_tsc_executed"))
        or int(independent.get("plant_step_count", -1)) != 0
        or int(independent.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R34 finalization independent disagreement")
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r34_compact_primary_independent_finalization",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
        "route": summary["route"],
        "source_file_sha256": hashes,
        "summary": summary,
        "local_cardinality_audit": detailed["local_cardinality_audit"],
        "outer_model_evaluation": detailed["outer_model_evaluation"],
        "schedule_jackknife": detailed["schedule_jackknife"],
        "combined_tube_maximum_physical_half_width": detailed[
            "combined_tube_maximum_physical_half_width"
        ],
        "combined_tube_cap_passed": detailed["combined_tube_cap_passed"],
        "planning_evaluation": detailed["planning_evaluation"],
        "fault_injection": detailed["fault_injection"],
        "independent_agreement": {
            field: independent[field] for field in agreement_fields
        },
        "independent_maximum_scaled_difference": {
            field: independent[field] for field in difference_fields
        },
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }
    compact_path = ctx.paths.analysis / "compact_audit.json"
    _write(compact_path, compact)
    final = copy.deepcopy(compact)
    final["audit_kind"] = "r8r34_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest.update(
        {
            "independent_sha256": hashes["independent"],
            "compact_audit_sha256": _sha(compact_path),
            "final_report_sha256": _sha(final_path),
            "final_route": summary["route"],
            "independent_completed": True,
        }
    )
    _write(ctx.paths.manifest, manifest)
    state = _read(ctx.paths.state)
    state.update(
        {
            "phase_status": "offline_preflight_final",
            "finished": True,
            "primary_completed": True,
            "independent_completed": True,
            "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
            "route": summary["route"],
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
            "controller_execution_authorized": False,
        }
    )
    _write(ctx.paths.state, state)
    return final


ARGUMENT_NAMES = (
    "config",
    "run-dir",
    "r8r33-run",
    "r8r32-run",
    "r8r31-run",
    "r8r23-run",
    "r8r28-run",
    "r8r22-run",
    "r8r7-run",
    "r8r12-run",
    "r8r14-run",
    "r8r15-run",
    "r8r19-run",
    "r8r20-run",
    "r8r27-run",
    "r8-run",
    "r8r1-output",
    "r8r6-run",
    "source-d1r11-run",
    "source-r2-run",
    "source-r4-run",
    "source-r6-run",
    "source-s21-run",
    "source-s23r1-output",
    "source-s24-run",
    "source-d1r9-v1",
    "source-d1r9-v2",
    "source-d1r10-run",
    "source-d1r10-audit",
    "source-stage42r3b-run",
    "source-stage42r3c3-run",
    "source-stage42r3c3-bank-dir",
    "source-stage42r3c3t1-run",
    "source-stage42r3c3t1-audit-dir",
    "source-stage42r3c3t3-controller-bank",
    "q1-run",
    "q2-run",
    "q1-audit",
    "q2-audit",
    "r3b-server-audit",
    "r3b-snapshot-checks",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ARGUMENT_NAMES:
        parser.add_argument(
            f"--{name}", dest=name.replace("-", "_"), type=Path, required=True
        )
    parser.add_argument("--command", choices=("primary", "finalize"), default="primary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else run_finalize(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
