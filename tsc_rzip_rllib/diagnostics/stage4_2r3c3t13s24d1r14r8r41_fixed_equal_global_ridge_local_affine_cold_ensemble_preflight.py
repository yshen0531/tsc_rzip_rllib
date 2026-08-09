"""R8R41 fixed equal global-ridge/local-affine cold-ensemble preflight."""

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
    stage4_2r3c3t13s24d1r14r8r34_causal_local_neighborhood_schedule_generalizing_feedback_preflight
    as r8r34,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r39_fixed_equal_global_ridge_local_constant_cold_ensemble_preflight
    as r8r39,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R41"
IDENTITY = "fixed_equal_global_ridge_local_affine_cold_ensemble_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r41_fixed_equal_global_ridge_local_affine_cold_ensemble_preflight"
FACTORS = r8r31.OUTPUT_FACTORS
MAX_COUNTS = r8r31.MAX_COUNTS

_read = r8r39._read
_write = r8r39._write
_sha = r8r39._sha
_digest = r8r39._digest
_jsonable = r8r39._jsonable


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
    r8r39_ctx: Any
    r8r39_stage: Path
    r8r34_ctx: Any
    r8r34_stage: Path
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
    r31_config = (root / str(cfg["source_r8r31_config"])).resolve()
    r34_config = (root / str(cfg["source_r8r34_config"])).resolve()
    r39_config = (root / str(cfg["source_r8r39_config"])).resolve()
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    gates = cfg["model_gates"]
    scope = cfg["scientific_scope"]
    routes = {
        "execution_fail": "FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_PREFLIGHT_EXECUTION_FAIL_STOP",
        "model_fail": "FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC",
        "pass": "FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED",
    }
    invalid = (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not r31_config.is_file()
        or _sha(r31_config) != cfg.get("source_r8r31_config_sha256")
        or not r34_config.is_file()
        or _sha(r34_config) != cfg.get("source_r8r34_config_sha256")
        or not r39_config.is_file()
        or _sha(r39_config) != cfg.get("source_r8r39_config_sha256")
        or int(bank.get("trajectory_count", -1)) != 560
        or int(bank.get("physical_pair_count", -1)) != 8
        or int(bank.get("history_context_count", -1)) != 16
        or int(bank.get("schedule_count", -1)) != 35
        or int(bank.get("interval_record_count", -1)) != 3360
        or int(bank.get("five_component_time_row_count", -1)) != 14560
        or list(bank.get("decision_task_steps", [])) != [10, 12, 14, 16, 18, 22]
        or int(model.get("global_expanded_dimension", -1)) != 238
        or float(model.get("global_ridge_penalty", -1.0)) != 1e-4
        or model.get("global_unpenalized_centered_intercept") is not True
        or int(model.get("local_coordinate_dimension", -1)) != 62
        or float(model.get("local_coordinate_scale_floor", -1.0)) != 1e-12
        or int(model.get("local_neighbor_count", -1)) != 64
        or float(model.get("local_uniform_neighbor_weight", -1.0)) != 1.0
        or int(model.get("local_slope_dimension", -1)) != 62
        or float(model.get("local_slope_ridge_penalty", -1.0)) != 1.0
        or float(model.get("local_intercept_penalty", -1.0)) != 0.0
        or model.get("local_inactive_centered_columns_zero_slope") is not True
        or model.get("local_solver") != "augmented_lstsq"
        or float(model.get("global_weight", -1.0)) != 0.5
        or float(model.get("local_weight", -1.0)) != 0.5
        or float(model.get("reserve_multiplier", -1.0)) != 1.25
        or list(model.get("physical_point_error_floors", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or list(model.get("primary_independent_component_scales", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or float(model.get("primary_independent_scaled_tolerance", -1.0)) != 1e-9
        or any(
            model.get(name) is not False
            for name in (
                "weight_search_allowed",
                "gating_allowed",
                "innovation_enabled",
                "feature_search_allowed",
                "ridge_search_allowed",
                "neighbor_search_allowed",
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
        or float(gates.get("required_whole_pair_state_support_rate", -1.0)) != 1.0
        or float(gates.get("required_finite_prediction_rate", -1.0)) != 1.0
        or int(gates.get("required_forbidden_input_count", -1)) != 0
        or cfg.get("routes") != routes
        or scope.get("zero_new_tsc") is not True
        or scope.get("controller_execution_authorized") is not False
        or scope.get("gate_a_qualified") is not False
        or scope.get("expert_data_allowed") is not False
        or scope.get("bc_dagger_or_rl_allowed") is not False
        or scope.get("all_stage_trajectories_allowed_in_expert_dataset") is not False
        or scope.get("global_plant_reachability_claimed") is not False
    )
    if invalid:
        raise ValueError("R8R41 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    root = _root()
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=root)
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (root / str(cfg["source_r8r39_config"])).resolve()
    source_args.run_dir = args.r8r39_run.expanduser().resolve()
    r8r39_ctx = r8r39.load_context(source_args)
    source_ctx = r8r39_ctx.source_ctx
    r8r34_ctx = r8r39_ctx.r8r37_ctx.r8r35_ctx.r8r34_ctx
    if (
        _sha(source_ctx.config_path) != cfg["source_r8r31_config_sha256"]
        or source_ctx.config_path.resolve()
        != (root / str(cfg["source_r8r31_config"])).resolve()
    ):
        raise ValueError("R8R41 R8R31 source context changed")
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r39_ctx=r8r39_ctx,
        r8r39_stage=r8r39_ctx.paths.stage,
        r8r34_ctx=r8r34_ctx,
        r8r34_stage=r8r34_ctx.paths.stage,
        source_ctx=source_ctx,
    )


def _source_paths(stage: Path) -> dict[str, Path]:
    return {
        "primary_summary": stage / "analysis/primary_summary.json",
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "model": stage / "model/preflight_model.json",
        "independent": stage / "analysis/independent.json",
        "compact_audit": stage / "analysis/compact_audit.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_state": stage / "stage_state.json",
        "stage_manifest": stage / "stage_manifest.json",
    }


def _authenticate_final_source(
    stage: Path, contract: Mapping[str, Any], *, label: str
) -> dict[str, Any]:
    paths = _source_paths(stage)
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise ValueError(f"R8R41 final {label} source hash changed")
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
        or independent.get("primary_outcome_agreement") is not True
        or final.get("route") != route
        or final.get("integrity_gate_passed") is not True
        or state.get("route") != route
        or state.get("independent_completed") is not True
        or manifest.get("final_route") != route
        or bool(final.get("real_tsc_executed"))
        or int(final.get("plant_step_count", -1)) != 0
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise ValueError(f"R8R41 final {label} source state changed")
    return {"hashes": hashes, "passed": True}


def _authenticate_r8r34_source(
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
        raise ValueError("R8R41 final R8R34 source hash changed")
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
        raise ValueError("R8R41 final R8R34 source classification changed")
    return {"hashes": hashes, "historical_overall_passed": False, "passed": True}


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    r31 = _authenticate_final_source(
        ctx.source_ctx.paths.stage, ctx.cfg["source_r8r31"], label="R8R31"
    )
    r34 = _authenticate_r8r34_source(
        ctx.r8r34_stage, ctx.cfg["source_r8r34"]
    )
    r39 = _authenticate_final_source(
        ctx.r8r39_stage, ctx.cfg["source_r8r39"], label="R8R39"
    )
    transitive = r8r39.authenticate_sources(ctx.r8r39_ctx)
    return {
        "r8r31_final": r31,
        "r8r34_historical_failure": r34,
        "r8r39_final": r39,
        "transitive": transitive,
        "passed": True,
    }


def _local_cfg(cfg: Mapping[str, Any]) -> dict[str, Any]:
    model = cfg["model_contract"]
    return {
        "model_contract": {
            "coordinate_scale_floor": float(model["local_coordinate_scale_floor"]),
            "neighbor_count": int(model["local_neighbor_count"]),
            "slope_ridge_penalty": float(model["local_slope_ridge_penalty"]),
        }
    }


def _verify_bank(
    trajectories: Sequence[Mapping[str, Any]],
    evidence: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> None:
    contract = cfg["bank_contract"]
    time_rows = sum(
        len(interval["targets"])
        for trajectory in trajectories
        for interval in trajectory["intervals"]
    )
    if (
        int(evidence["trajectory_count"]) != int(contract["trajectory_count"])
        or int(evidence["context_count"]) != int(contract["history_context_count"])
        or int(evidence["schedule_count"]) != int(contract["schedule_count"])
        or int(evidence["interval_record_count"]) != int(contract["interval_record_count"])
        or time_rows != int(contract["five_component_time_row_count"])
        or any(
            evidence[key] != contract[key]
            for key in ("bank_digest", "feature_digest", "target_digest")
        )
    ):
        raise ValueError("R8R41 bank reproduction changed")


def fit_model(
    trajectories: Sequence[Mapping[str, Any]],
    selected: Callable[[Mapping[str, Any]], bool],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    model = cfg["model_contract"]
    global_model = r8r31._fit(
        trajectories, selected, float(model["global_ridge_penalty"])
    )
    local_model = r8r34.fit_model(trajectories, selected, _local_cfg(cfg))
    local_model["model_kind"] = "causal_local_affine_k64_ridge1_cold"
    return {
        "model_kind": "fixed_equal_global_ridge_local_affine_cold_ensemble",
        "global_model": global_model,
        "local_model": local_model,
    }


def model_evidence(model: Mapping[str, Any]) -> dict[str, Any]:
    global_json = r8r31._model_json(model["global_model"])
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


def _predict_local_affine(
    model: Mapping[str, Any], row: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[np.ndarray, list[str]]:
    interval = int(row["interval"])
    count = len(row["targets"])
    query_coordinate = r8r34.coordinate62(row)
    output = np.empty((count, 5), dtype=float)
    filled = np.zeros(count, dtype=bool)
    neighbor_digests = []
    for group in model["intervals"][interval]["groups"]:
        mean = np.asarray(group["coordinate_mean"], dtype=float).reshape(62)
        scale = np.asarray(group["coordinate_scale"], dtype=float).reshape(62)
        training = np.asarray(group["standardized_coordinates"], dtype=float)
        target = np.asarray(group["targets"], dtype=float)
        query = (query_coordinate - mean) / scale
        distance = np.sqrt(np.sum(np.square(training - query), axis=1))
        chosen = np.argsort(distance, kind="mergesort")[:
            int(cfg["model_contract"]["local_neighbor_count"])
        ]
        difference = training[chosen] - query
        response = target[chosen]
        difference_mean = np.mean(difference, axis=0)
        response_mean = np.mean(response, axis=0)
        centered_difference = difference - difference_mean
        centered_response = response - response_mean
        active = np.any(centered_difference != 0.0, axis=0)
        slopes = np.zeros((62, response.shape[1]), dtype=float)
        if np.any(active):
            active_count = int(np.sum(active))
            ridge = float(cfg["model_contract"]["local_slope_ridge_penalty"])
            slopes[active] = np.linalg.lstsq(
                np.vstack(
                    (
                        centered_difference[:, active],
                        math.sqrt(ridge) * np.eye(active_count),
                    )
                ),
                np.vstack(
                    (
                        centered_response,
                        np.zeros((active_count, response.shape[1])),
                    )
                ),
                rcond=None,
            )[0]
        values = (response_mean - difference_mean @ slopes).reshape(
            (len(group["sample_offsets"]), 5)
        )
        keys = [str(group["training_keys"][int(index)]) for index in chosen]
        neighbor_digests.append(_digest(keys))
        for index, offset in enumerate(group["sample_offsets"]):
            if int(offset) < count:
                output[int(offset)] = values[index]
                filled[int(offset)] = True
    if not np.all(filled) or not np.all(np.isfinite(output)):
        raise ValueError("R8R41 local-affine prediction coverage invalid")
    return output, neighbor_digests


def predict(
    model: Mapping[str, Any], row: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    global_prediction = r8r31.predict(model["global_model"], row)
    local_prediction, neighbors = _predict_local_affine(model["local_model"], row, cfg)
    contract = cfg["model_contract"]
    ensemble = (
        float(contract["global_weight"]) * global_prediction
        + float(contract["local_weight"]) * local_prediction
    )
    if ensemble.shape != global_prediction.shape or not np.all(np.isfinite(ensemble)):
        raise ValueError("R8R41 ensemble prediction invalid")
    return global_prediction, local_prediction, ensemble, neighbors


def _residuals(
    model: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[list[list[list[np.ndarray]]], dict[str, Any], list[dict[str, Any]]]:
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
            global_prediction, local_prediction, ensemble, neighbors = predict(
                model, row, cfg
            )
            residual = np.abs(np.asarray(row["targets"], dtype=float) - ensemble)
            residual_rows.append(residual.tolist())
            global_rows.append(global_prediction.tolist())
            local_rows.append(local_prediction.tolist())
            ensemble_rows.append(ensemble.tolist())
            neighbor_rows.append(list(neighbors))
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
                "global_predictions": global_rows,
                "local_predictions": local_rows,
                "ensemble_predictions": ensemble_rows,
                "absolute_residuals": residual_rows,
                "neighbor_key_digests": neighbor_rows,
            }
        )
    return groups, {"residual_digest": _digest(serial)}, predictions


def _fold_metrics(
    folds: Sequence[dict[str, Any]],
    cfg: Mapping[str, Any],
    *,
    held_key: str,
    leave_one_out: bool,
) -> tuple[list[np.ndarray], dict[str, Any]]:
    total_contained = total = 0
    maximum_error = np.zeros(5, dtype=float)
    maximum_tube = np.zeros(5, dtype=float)
    rows = []
    shared_tube = None
    shared_evidence = None
    if not leave_one_out:
        shared_tube, shared_evidence = r8r31._tube_from_fold_groups(
            folds, lambda _row: True, cfg
        )
    for fold in folds:
        if leave_one_out:
            held = fold[held_key]
            tube, tube_evidence = r8r31._tube_from_fold_groups(
                folds, lambda row, held=held: row[held_key] != held, cfg
            )
        else:
            tube, tube_evidence = shared_tube, shared_evidence
        contained = component_count = 0
        fold_error = np.zeros(5, dtype=float)
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values, dtype=float).reshape((-1, 5))
                contained += int(
                    np.count_nonzero(residual <= tube[interval][offset] + 1e-15)
                )
                component_count += residual.size
                if len(residual):
                    fold_error = np.maximum(fold_error, np.max(residual, axis=0))
        maximum_error = np.maximum(maximum_error, fold_error * FACTORS)
        maximum_tube = np.maximum(
            maximum_tube, np.max(np.concatenate(tube), axis=0) * FACTORS
        )
        total_contained += contained
        total += component_count
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
    support = all(fold.get("support", {"passed": True})["passed"] for fold in folds)
    rate = total_contained / total
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
        "contained_count": total_contained,
        "component_count": total,
        "containment_rate": rate,
        "fold_rows": rows,
        "passed": passed,
    }
    if held_key == "held_pair":
        evidence["state_support_pass_count"] = sum(
            bool(fold["support"]["passed"]) for fold in folds
        )
    return shared_tube if shared_tube is not None else [], evidence


def outer_model_evaluation(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    source_cfg: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    pairs = sorted({str(row["pair_id"]) for row in trajectories})
    folds = []
    artifact = []
    for held_pair in pairs:
        training = [pair for pair in pairs if pair != held_pair]
        model = fit_model(
            trajectories,
            lambda row, allowed=set(training): row["pair_id"] in allowed,
            cfg,
        )
        held = [row for row in trajectories if row["pair_id"] == held_pair]
        groups, residual_evidence, predictions = _residuals(model, held, cfg)
        evidence = model_evidence(model)
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": training,
                "model_digest": evidence["ensemble_model_digest"],
                "model_evidence": evidence,
                "residual_groups": groups,
                "residual_digest": residual_evidence["residual_digest"],
                "support": r8r31._support_fold(
                    trajectories,
                    training,
                    held_pair,
                    float(source_cfg["model_contract"]["support_threshold_multiplier"]),
                ),
            }
        )
        artifact.append({"held_pair": held_pair, "trajectories": predictions})
    _unused, metrics = _fold_metrics(
        folds, cfg, held_key="held_pair", leave_one_out=True
    )
    return folds, metrics, artifact


def schedule_jackknife(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    folds = []
    artifact = []
    for held_schedule in schedules:
        model = fit_model(
            trajectories,
            lambda row, held=held_schedule: row["schedule_id"] != held,
            cfg,
        )
        held = [row for row in trajectories if row["schedule_id"] == held_schedule]
        if len(held) != 16:
            raise ValueError("R8R41 schedule fold cardinality changed")
        groups, residual_evidence, predictions = _residuals(model, held, cfg)
        evidence = model_evidence(model)
        folds.append(
            {
                "held_schedule": held_schedule,
                "model_digest": evidence["ensemble_model_digest"],
                "model_evidence": evidence,
                "residual_groups": groups,
                "residual_digest": residual_evidence["residual_digest"],
            }
        )
        artifact.append({"held_schedule": held_schedule, "trajectories": predictions})
    tube, metrics = _fold_metrics(
        folds, cfg, held_key="held_schedule", leave_one_out=False
    )
    return tube, folds, metrics, artifact


def compute_from_bank(
    ctx: Context,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    bank: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _verify_bank(trajectories, bank, ctx.cfg)
    cardinality = r8r34.local_cardinality_audit(trajectories, _local_cfg(ctx.cfg))
    if not cardinality["passed"]:
        raise ValueError("R8R41 frozen local-neighbor cardinality failed")
    folds, outer, outer_predictions = outer_model_evaluation(
        trajectories, ctx.cfg, ctx.source_ctx.cfg
    )
    schedule_tube, schedule_folds, schedule, schedule_predictions = schedule_jackknife(
        trajectories, ctx.cfg
    )
    pair_tube, pair_evidence = r8r31._tube_from_fold_groups(
        folds, lambda _row: True, ctx.cfg
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
    scientific = bool(outer["passed"] and schedule["passed"] and combined_passed)
    route = ctx.cfg["routes"]["pass" if scientific else "model_fail"]
    detailed = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
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
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "model_kind": "fixed_equal_global_ridge_local_affine_cold_ensemble",
        "bank_evidence": bank,
        "outer_model_evidence": [
            {"held_pair": fold["held_pair"], **fold["model_evidence"]}
            for fold in folds
        ],
        "schedule_model_evidence": [
            {"held_schedule": fold["held_schedule"], **fold["model_evidence"]}
            for fold in schedule_folds
        ],
        "outer_predictions": outer_predictions,
        "schedule_predictions": schedule_predictions,
        "pair_tube": pair_tube,
        "schedule_tube": schedule_tube,
        "combined_tube": combined_tube,
    }
    return _jsonable(detailed), _jsonable(artifact)


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    outer = detailed["outer_model_evaluation"]
    schedule = detailed["schedule_jackknife"]
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
        "local_cardinality_head_count": int(cardinality["head_count"]),
        "local_cardinality_failed_head_count": int(cardinality["failed_head_count"]),
        "minimum_training_row_count": int(cardinality["minimum_training_row_count"]),
        "outer_model_gate_passed": bool(outer["passed"]),
        "outer_maximum_absolute_physical_error": outer["maximum_absolute_physical_error"],
        "outer_maximum_reserved_physical_tube_half_width": outer["maximum_reserved_physical_tube_half_width"],
        "outer_reserved_contained_count": int(outer["contained_count"]),
        "outer_reserved_component_count": int(outer["component_count"]),
        "schedule_model_gate_passed": bool(schedule["passed"]),
        "schedule_maximum_absolute_physical_error": schedule["maximum_absolute_physical_error"],
        "schedule_maximum_reserved_physical_tube_half_width": schedule["maximum_reserved_physical_tube_half_width"],
        "schedule_contained_count": int(schedule["contained_count"]),
        "schedule_component_count": int(schedule["component_count"]),
        "combined_tube_cap_passed": bool(detailed["combined_tube_cap_passed"]),
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
        raise ValueError("R8R41 primary requires a fresh stage directory")
    ctx.paths.stage.mkdir(parents=True)
    ctx.paths.analysis.mkdir()
    ctx.paths.model.mkdir()
    try:
        authentication = authenticate_sources(ctx)
        trajectories, _context_meta, bank = r8r31.build_bank(ctx.source_ctx)
        detailed, artifact = compute_from_bank(ctx, authentication, trajectories, bank)
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
                "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
                "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
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
                "finished": False,
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
        _write(ctx.paths.state, {**failure, "phase_status": "offline_primary_execution_failed"})
        raise


AGREEMENT_FIELDS = (
    "primary_bank_agreement",
    "primary_neighbor_agreement",
    "primary_model_agreement",
    "primary_prediction_agreement",
    "primary_tube_agreement",
    "primary_metric_agreement",
    "primary_route_agreement",
    "primary_outcome_agreement",
)
DIFFERENCE_FIELDS = (
    "maximum_scaled_model_difference",
    "maximum_scaled_prediction_difference",
    "maximum_scaled_tube_difference",
    "maximum_scaled_metric_difference",
)


def run_finalize(ctx: Context) -> dict[str, Any]:
    paths: dict[str, Path] = {
        "primary_summary": ctx.paths.analysis / "primary_summary.json",
        "primary_detailed": ctx.paths.analysis / "primary_detailed.json",
        "model": ctx.paths.model / "preflight_model.json",
    }
    independent_path = ctx.paths.analysis / "independent.json"
    failure_path = ctx.paths.analysis / "independent_failure.json"
    if any(not path.is_file() for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)):
        raise ValueError("R8R41 finalization evidence incomplete")
    if independent_path.is_file() == failure_path.is_file():
        raise ValueError("R8R41 finalization evidence ambiguous")
    summary = _read(paths["primary_summary"])
    detailed = _read(paths["primary_detailed"])
    selected_path = independent_path if independent_path.is_file() else failure_path
    selected_name = "independent" if independent_path.is_file() else "independent_failure"
    paths[selected_name] = selected_path
    independent = _read(selected_path)
    hashes = {name: _sha(path) for name, path in paths.items()}
    tolerance = float(ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"])
    agreement = bool(
        independent.get("passed") is True
        and all(independent.get(field) is True for field in AGREEMENT_FIELDS)
        and all(float(independent.get(field, math.inf)) <= tolerance for field in DIFFERENCE_FIELDS)
        and independent.get("primary_summary_sha256") == hashes["primary_summary"]
        and independent.get("primary_detailed_sha256") == hashes["primary_detailed"]
        and independent.get("primary_model_sha256") == hashes["model"]
        and independent.get("route") == summary.get("route")
        and not bool(independent.get("real_tsc_executed"))
        and int(independent.get("plant_step_count", -1)) == 0
        and int(independent.get("new_raw_count", -1)) == 0
    )
    if independent_path.is_file() and not agreement:
        raise ValueError("R8R41 finalization independent disagreement")
    final_route = summary["route"] if agreement else ctx.cfg["routes"]["execution_fail"]
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r41_compact_primary_independent_finalization" if agreement else "r8r41_compact_independent_failure_finalization",
        "passed": agreement,
        "integrity_gate_passed": agreement,
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]) if agreement else False,
        "route": final_route,
        "primary_route": summary["route"],
        "source_file_sha256": hashes,
        "summary": summary,
        "local_cardinality_audit": detailed["local_cardinality_audit"],
        "outer_model_evaluation": detailed["outer_model_evaluation"],
        "schedule_jackknife": detailed["schedule_jackknife"],
        "combined_tube_maximum_physical_half_width": detailed["combined_tube_maximum_physical_half_width"],
        "combined_tube_cap_passed": detailed["combined_tube_cap_passed"],
        "independent_agreement": {field: independent.get(field) for field in AGREEMENT_FIELDS},
        "independent_maximum_scaled_difference": {field: independent.get(field) for field in DIFFERENCE_FIELDS},
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
    final["audit_kind"] = "r8r41_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest = _read(ctx.paths.manifest)
    manifest.update(
        {
            f"{selected_name}_sha256": hashes[selected_name],
            "compact_audit_sha256": _sha(compact_path),
            "final_report_sha256": _sha(final_path),
            "final_route": final_route,
            "independent_completed": True,
            "independent_validation_passed": agreement,
        }
    )
    _write(ctx.paths.manifest, manifest)
    state = _read(ctx.paths.state)
    state.update(
        {
            "phase_status": "offline_preflight_final" if agreement else "offline_preflight_independent_validation_failed",
            "finished": True,
            "independent_completed": True,
            "independent_validation_passed": agreement,
            "scientific_gate_passed": bool(summary["scientific_gate_passed"]) if agreement else False,
            "primary_route": summary["route"],
            "route": final_route,
        }
    )
    _write(ctx.paths.state, state)
    return final


ARGUMENT_NAMES = (
    "config",
    "run-dir",
    "r8r39-run",
) + tuple(name for name in r8r39.ARGUMENT_NAMES if name not in {"config", "run-dir"})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ARGUMENT_NAMES:
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--command", choices=("primary", "finalize"), default="primary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else run_finalize(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
