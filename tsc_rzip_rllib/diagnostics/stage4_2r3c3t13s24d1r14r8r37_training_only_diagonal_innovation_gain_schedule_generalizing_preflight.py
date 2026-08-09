"""R8R37 training-only diagonal innovation-gain schedule preflight."""

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
    stage4_2r3c3t13s24d1r14r8r35_causal_last_innovation_local_constant_schedule_generalizing_preflight
    as r8r35,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R37"
IDENTITY = "training_only_diagonal_innovation_gain_schedule_generalizing_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r37_training_only_diagonal_innovation_gain_schedule_generalizing_preflight"
FACTORS = r8r31.OUTPUT_FACTORS
MAX_COUNTS = r8r31.MAX_COUNTS

_read = r8r35._read
_write = r8r35._write
_sha = r8r35._sha
_digest = r8r35._digest
_jsonable = r8r35._jsonable


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
    r8r35_ctx: Any
    r8r35_stage: Path
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
    source_config = (root / str(cfg["source_r8r35_config"])).resolve()
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    gates = cfg["model_gates"]
    useful = cfg["adaptation_usefulness_gate"]
    scope = cfg["scientific_scope"]
    expected_routes = {
        "execution_fail": "TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_PREFLIGHT_EXECUTION_FAIL_STOP",
        "model_fail": "TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_MODEL_FAIL_NO_TSC",
        "not_useful": "TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_NOT_USEFUL_NO_TSC",
        "pass": "TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED",
    }
    invalid = (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source_config.is_file()
        or _sha(source_config) != cfg.get("source_r8r35_config_sha256")
        or int(bank.get("trajectory_count", -1)) != 560
        or int(bank.get("physical_pair_count", -1)) != 8
        or int(bank.get("history_context_count", -1)) != 16
        or int(bank.get("schedule_count", -1)) != 35
        or int(bank.get("interval_record_count", -1)) != 3360
        or int(bank.get("five_component_time_row_count", -1)) != 14560
        or int(bank.get("post_initial_time_row_count", -1)) != 13440
        or list(bank.get("decision_task_steps", [])) != [10, 12, 14, 16, 18, 22]
        or int(model.get("causal_base_dimension", -1)) != 44
        or int(model.get("action_dimension", -1)) != 18
        or int(model.get("coordinate_dimension", -1)) != 62
        or float(model.get("coordinate_scale_floor", -1.0)) != 1e-12
        or int(model.get("neighbor_count", -1)) != 64
        or float(model.get("uniform_neighbor_weight", -1.0)) != 1.0
        or int(model.get("slope_dimension", -1)) != 0
        or int(model.get("gain_transition_count", -1)) != 5
        or int(model.get("gain_component_count", -1)) != 5
        or int(model.get("gain_parameter_count", -1)) != 25
        or model.get("gain_fit_intercept") is not False
        or float(model.get("gain_ridge_penalty", -1.0)) != 0.0
        or float(model.get("gain_denominator_floor_normalized", -1.0)) != 1e-12
        or float(model.get("minimum_gain", -1.0)) != 0.0
        or float(model.get("maximum_gain", -1.0)) != 1.0
        or int(model.get("innovation_memory_intervals", -1)) != 1
        or float(model.get("reserve_multiplier", -1.0)) != 1.25
        or list(model.get("physical_point_error_floors", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or list(model.get("primary_independent_component_scales", []))
        != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or float(model.get("primary_independent_scaled_tolerance", -1.0)) != 1e-9
        or any(
            model.get(name) is not False
            for name in (
                "neighbor_search_allowed",
                "gain_search_allowed",
                "lag_search_allowed",
                "memory_search_allowed",
                "feature_search_allowed",
                "response_weighting_allowed",
                "outlier_deletion_allowed",
                "innovation_clipping_allowed",
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
        or float(useful.get("maximum_adapted_to_cold_total_l1_ratio", -1.0)) != 0.95
        or float(useful.get("maximum_fold_adapted_to_cold_l1_ratio", -1.0)) != 1.0
        or int(useful.get("required_post_initial_time_row_count", -1)) != 13440
        or int(useful.get("required_family_count", -1)) != 2
        or cfg.get("routes") != expected_routes
        or scope.get("zero_new_tsc") is not True
        or scope.get("controller_execution_authorized") is not False
        or scope.get("gate_a_qualified") is not False
        or scope.get("expert_data_allowed") is not False
        or scope.get("bc_dagger_or_rl_allowed") is not False
        or scope.get("all_stage_trajectories_allowed_in_expert_dataset") is not False
    )
    if invalid:
        raise ValueError("R8R37 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    root = _root()
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=root)
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (root / str(cfg["source_r8r35_config"])).resolve()
    source_args.run_dir = args.r8r35_run.expanduser().resolve()
    r8r35_ctx = r8r35.load_context(source_args)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r35_ctx=r8r35_ctx,
        r8r35_stage=r8r35_ctx.paths.stage,
        source_ctx=r8r35_ctx.source_ctx,
    )


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    contract = ctx.cfg["source_r8r35"]
    paths = {
        "primary_summary": ctx.r8r35_stage / "analysis/primary_summary.json",
        "primary_detailed": ctx.r8r35_stage / "analysis/primary_detailed.json",
        "model": ctx.r8r35_stage / "model/preflight_model.json",
        "independent": ctx.r8r35_stage / "analysis/independent.json",
        "compact_audit": ctx.r8r35_stage / "analysis/compact_audit.json",
        "final_report": ctx.r8r35_stage / "analysis/final_report.json",
        "stage_state": ctx.r8r35_stage / "stage_state.json",
        "stage_manifest": ctx.r8r35_stage / "stage_manifest.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise ValueError("R8R37 final R8R35 source hash changed")
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    if (
        summary.get("route") != contract["required_route"]
        or independent.get("passed") is not True
        or independent.get("primary_neighbor_agreement") is not True
        or independent.get("primary_route_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or final.get("route") != contract["required_route"]
        or final.get("integrity_gate_passed") is not True
        or final.get("scientific_gate_passed") is not False
        or state.get("route") != contract["required_route"]
        or state.get("independent_validation_passed") is not True
        or manifest.get("final_route") != contract["required_route"]
        or bool(final.get("real_tsc_executed"))
        or int(final.get("plant_step_count", -1)) != 0
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R37 final R8R35 source state changed")
    return {
        "r8r35_final": {"hashes": hashes, "passed": True},
        "transitive": r8r35.authenticate_sources(ctx.r8r35_ctx),
        "passed": True,
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
        or int(evidence["interval_record_count"])
        != int(contract["interval_record_count"])
        or time_rows != int(contract["five_component_time_row_count"])
        or any(
            evidence[key] != contract[key]
            for key in ("bank_digest", "feature_digest", "target_digest")
        )
    ):
        raise ValueError("R8R37 bank reproduction changed")


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
        raise ValueError("R8R37 gain fit selection empty")
    model = r8r35.fit_model(chosen, lambda _row: True, cfg)
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"], dtype=float
    )
    normalization = FACTORS / scales
    numerator = np.zeros((6, 5), dtype=float)
    denominator = np.zeros((6, 5), dtype=float)
    sample_counts = np.zeros((6, 5), dtype=int)
    for trajectory in chosen:
        cold = [
            predict_base(model, row, cfg)[0]
            for row in trajectory["intervals"]
        ]
        for interval in range(1, 6):
            previous_actual = np.asarray(
                trajectory["intervals"][interval - 1]["targets"], dtype=float
            ).reshape((-1, 5))
            current_actual = np.asarray(
                trajectory["intervals"][interval]["targets"], dtype=float
            ).reshape((-1, 5))
            innovation = (previous_actual[-1] - cold[interval - 1][-1]) * normalization
            response = (current_actual - cold[interval]) * normalization
            numerator[interval] += innovation * np.sum(response, axis=0)
            denominator[interval] += len(response) * np.square(innovation)
            sample_counts[interval] += len(response)
    floor = float(cfg["model_contract"]["gain_denominator_floor_normalized"])
    minimum = float(cfg["model_contract"]["minimum_gain"])
    maximum = float(cfg["model_contract"]["maximum_gain"])
    gains = np.zeros((6, 5), dtype=float)
    states = [["initial_cold" for _ in range(5)] for _ in range(6)]
    for interval in range(1, 6):
        for component in range(5):
            if denominator[interval, component] <= floor:
                states[interval][component] = "denominator_floor_zero"
                continue
            unconstrained = numerator[interval, component] / denominator[interval, component]
            gains[interval, component] = min(maximum, max(minimum, unconstrained))
            states[interval][component] = (
                "projected_lower"
                if unconstrained < minimum
                else "projected_upper"
                if unconstrained > maximum
                else "interior"
            )
    if (
        not np.all(np.isfinite(gains))
        or np.any(gains < minimum)
        or np.any(gains > maximum)
        or np.any(sample_counts[1:] <= 0)
    ):
        raise ValueError("R8R37 diagonal gain fit invalid")
    model.update(
        {
            "model_kind": "causal_local_constant_k64_training_only_diagonal_gain",
            "diagonal_gains": gains,
            "gain_numerators": numerator,
            "gain_denominators": denominator,
            "gain_sample_counts": sample_counts,
            "gain_projection_states": states,
        }
    )
    return model


def gain_evidence(model: Mapping[str, Any]) -> dict[str, Any]:
    rows = {
        "diagonal_gains": np.asarray(model["diagonal_gains"], dtype=float),
        "gain_numerators": np.asarray(model["gain_numerators"], dtype=float),
        "gain_denominators": np.asarray(model["gain_denominators"], dtype=float),
        "gain_sample_counts": np.asarray(model["gain_sample_counts"], dtype=int),
        "gain_projection_states": model["gain_projection_states"],
    }
    serial = _jsonable(rows)
    states = [state for row in serial["gain_projection_states"][1:] for state in row]
    serial["gain_parameter_count"] = len(states)
    serial["gain_projection_counts"] = {
        state: states.count(state) for state in sorted(set(states))
    }
    serial["gain_digest"] = _digest(serial["diagonal_gains"])
    return serial


def model_evidence(model: Mapping[str, Any]) -> dict[str, Any]:
    evidence = r8r34.model_evidence(model)
    evidence["gain_evidence"] = gain_evidence(model)
    return evidence


def predict_group(
    group: Mapping[str, Any], query_coordinate: np.ndarray, cfg: Mapping[str, Any]
) -> tuple[np.ndarray, list[str]]:
    mean = np.asarray(group["coordinate_mean"], dtype=float).reshape(62)
    scale = np.asarray(group["coordinate_scale"], dtype=float).reshape(62)
    training = np.asarray(group["standardized_coordinates"], dtype=float)
    targets = np.asarray(group["targets"], dtype=float)
    query = (np.asarray(query_coordinate, dtype=float).reshape(62) - mean) / scale
    distances = np.linalg.norm(training - query, axis=1)
    count = int(cfg["model_contract"]["neighbor_count"])
    chosen = np.argsort(distances, kind="mergesort")[:count]
    output = np.mean(targets[chosen], axis=0)
    keys = [str(group["training_keys"][int(index)]) for index in chosen]
    if output.shape != (targets.shape[1],) or not np.all(np.isfinite(output)):
        raise ValueError("R8R37 local-constant prediction invalid")
    return output, keys


def predict_base(
    model: Mapping[str, Any],
    row: Mapping[str, Any],
    cfg: Mapping[str, Any],
    *,
    predict_group_fn: Callable[..., tuple[np.ndarray, list[str]]] = predict_group,
) -> tuple[np.ndarray, list[str]]:
    interval = int(row["interval"])
    count = len(row["targets"])
    query = r8r34.coordinate62(row)
    output = np.empty((count, 5), dtype=float)
    filled = np.zeros(count, dtype=bool)
    neighbor_digests = []
    for group in model["intervals"][interval]["groups"]:
        values, keys = predict_group_fn(group, query, cfg)
        values = values.reshape((len(group["sample_offsets"]), 5))
        neighbor_digests.append(_digest(keys))
        for index, offset in enumerate(group["sample_offsets"]):
            if int(offset) < count:
                output[int(offset)] = values[index]
                filled[int(offset)] = True
    if not np.all(filled) or not np.all(np.isfinite(output)):
        raise ValueError("R8R37 prediction coverage invalid")
    return output, neighbor_digests


def _trajectory_residuals(
    model: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    *,
    predict_group_fn: Callable[..., tuple[np.ndarray, list[str]]],
) -> tuple[list[list[list[np.ndarray]]], dict[str, Any], list[dict[str, Any]]]:
    groups: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in MAX_COUNTS]
    scales = np.asarray(
        cfg["model_contract"]["primary_independent_component_scales"], dtype=float
    )
    cold_total = adapted_total = 0.0
    later_rows = 0
    serial = []
    predictions = []
    gains = np.asarray(model["diagonal_gains"], dtype=float).reshape((6, 5))
    for trajectory in trajectories:
        previous_innovation = np.zeros(5, dtype=float)
        residual_rows = []
        prediction_rows = []
        cold_rows = []
        neighbor_rows = []
        for interval, row in enumerate(trajectory["intervals"]):
            actual = np.asarray(row["targets"], dtype=float).reshape((-1, 5))
            base, neighbors = predict_base(
                model, row, cfg, predict_group_fn=predict_group_fn
            )
            adapted = base + gains[interval] * previous_innovation
            adapted_error = np.abs(actual - adapted)
            cold_error = np.abs(actual - base)
            residual_rows.append(adapted_error.tolist())
            prediction_rows.append(adapted.tolist())
            cold_rows.append(base.tolist())
            neighbor_rows.append(neighbors)
            for offset, value in enumerate(adapted_error):
                groups[interval][offset].append(value)
            if interval > 0:
                cold_total += float(np.sum(cold_error * FACTORS / scales))
                adapted_total += float(np.sum(adapted_error * FACTORS / scales))
                later_rows += len(actual)
            previous_innovation = actual[-1] - base[-1]
        serial.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "absolute_residuals": residual_rows,
            }
        )
        predictions.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "cold_predictions": cold_rows,
                "adapted_predictions": prediction_rows,
                "neighbor_key_digests": neighbor_rows,
            }
        )
    ratio = adapted_total / cold_total if cold_total > 0.0 else 1.0
    return groups, {
        "residual_digest": _digest(serial),
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
    row_count = sum(int(row["post_initial_time_row_count"]) for row in rows)
    limit = float(
        cfg["adaptation_usefulness_gate"]["maximum_adapted_to_cold_total_l1_ratio"]
    )
    fold_limit = float(
        cfg["adaptation_usefulness_gate"]["maximum_fold_adapted_to_cold_l1_ratio"]
    )
    fold_rows = [
        {
            "held_out": row["held_out"],
            "cold_normalized_l1": float(row["cold_post_initial_normalized_l1"]),
            "adapted_normalized_l1": float(row["adapted_post_initial_normalized_l1"]),
            "adapted_to_cold_l1_ratio": float(row["adapted_to_cold_l1_ratio"]),
            "passed_no_regression": float(row["adapted_to_cold_l1_ratio"])
            <= fold_limit + 1e-15,
        }
        for row in rows
    ]
    ratio = adapted / cold if cold > 0.0 else 1.0
    return {
        "family": family,
        "fold_count": len(rows),
        "post_initial_time_row_count": row_count,
        "cold_total_normalized_l1": cold,
        "adapted_total_normalized_l1": adapted,
        "adapted_to_cold_total_l1_ratio": ratio,
        "fold_rows": fold_rows,
        "passed": bool(
            ratio <= limit + 1e-15
            and all(row["passed_no_regression"] for row in fold_rows)
            and row_count
            == int(
                cfg["adaptation_usefulness_gate"][
                    "required_post_initial_time_row_count"
                ]
            )
        ),
    }


def outer_model_evaluation(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    source_cfg: Mapping[str, Any],
    *,
    fit_model_fn: Callable[..., dict[str, Any]] = fit_model,
    predict_group_fn: Callable[..., tuple[np.ndarray, list[str]]] = predict_group,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    pairs = sorted({str(row["pair_id"]) for row in trajectories})
    folds = []
    artifacts = []
    usefulness_rows = []
    for held_pair in pairs:
        training = [pair for pair in pairs if pair != held_pair]
        model = fit_model_fn(
            trajectories,
            lambda row, allowed=set(training): row["pair_id"] in allowed,
            cfg,
        )
        held = [row for row in trajectories if row["pair_id"] == held_pair]
        groups, evidence, predictions = _trajectory_residuals(
            model, held, cfg, predict_group_fn=predict_group_fn
        )
        model_record = model_evidence(model)
        fold = {
            "held_pair": held_pair,
            "training_pairs": training,
            "model_digest": _digest(model_record),
            "gain_evidence": model_record["gain_evidence"],
            "residual_groups": groups,
            "residual_digest": evidence["residual_digest"],
            "support": r8r31._support_fold(
                trajectories,
                training,
                held_pair,
                float(source_cfg["model_contract"]["support_threshold_multiplier"]),
            ),
        }
        folds.append(fold)
        usefulness_rows.append({"held_out": held_pair, **evidence})
        artifacts.append({"held_pair": held_pair, "trajectories": predictions})
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
                "gain_evidence": fold["gain_evidence"],
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
            maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15
        )
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
        "adaptation_usefulness": _usefulness(
            "whole_physical_pair", usefulness_rows, cfg
        ),
    }, artifacts


def schedule_jackknife(
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    *,
    fit_model_fn: Callable[..., dict[str, Any]] = fit_model,
    predict_group_fn: Callable[..., tuple[np.ndarray, list[str]]] = predict_group,
) -> tuple[list[np.ndarray], dict[str, Any], list[dict[str, Any]]]:
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    folds = []
    artifacts = []
    usefulness_rows = []
    for held_schedule in schedules:
        model = fit_model_fn(
            trajectories,
            lambda row, held=held_schedule: row["schedule_id"] != held,
            cfg,
        )
        held = [row for row in trajectories if row["schedule_id"] == held_schedule]
        if len(held) != 16:
            raise ValueError("R8R37 schedule fold cardinality changed")
        groups, evidence, predictions = _trajectory_residuals(
            model, held, cfg, predict_group_fn=predict_group_fn
        )
        model_record = model_evidence(model)
        folds.append(
            {
                "held_schedule": held_schedule,
                "model_digest": _digest(model_record),
                "gain_evidence": model_record["gain_evidence"],
                "residual_groups": groups,
                "residual_digest": evidence["residual_digest"],
            }
        )
        usefulness_rows.append({"held_out": held_schedule, **evidence})
        artifacts.append({"held_schedule": held_schedule, "trajectories": predictions})
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
        and np.all(
            maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15
        )
    )
    return tube, {
        "schedule_count": len(schedules),
        "training_schedule_count": len(schedules) - 1,
        "folds": [
            {
                "held_schedule": fold["held_schedule"],
                "model_digest": fold["model_digest"],
                "gain_evidence": fold["gain_evidence"],
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
        "adaptation_usefulness": _usefulness(
            "whole_schedule", usefulness_rows, cfg
        ),
    }, artifacts


def compute_from_bank(
    ctx: Context,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    bank: Mapping[str, Any],
    *,
    fit_model_fn: Callable[..., dict[str, Any]] = fit_model,
    predict_group_fn: Callable[..., tuple[np.ndarray, list[str]]] = predict_group,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _verify_bank(trajectories, bank, ctx.cfg)
    cardinality = r8r34.local_cardinality_audit(trajectories, ctx.cfg)
    if not cardinality["passed"]:
        raise ValueError("R8R37 frozen local-neighbor cardinality failed")
    folds, outer, outer_predictions = outer_model_evaluation(
        trajectories,
        ctx.cfg,
        ctx.source_ctx.cfg,
        fit_model_fn=fit_model_fn,
        predict_group_fn=predict_group_fn,
    )
    schedule_tube, schedule, schedule_predictions = schedule_jackknife(
        trajectories,
        ctx.cfg,
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
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "model_kind": "causal_local_constant_k64_training_only_diagonal_gain",
        "bank_evidence": bank,
        "outer_model_evidence": [
            {
                "held_pair": fold["held_pair"],
                "model_digest": fold["model_digest"],
                "gain_evidence": fold["gain_evidence"],
            }
            for fold in folds
        ],
        "schedule_model_evidence": [
            {
                "held_schedule": fold["held_schedule"],
                "model_digest": fold["model_digest"],
                "gain_evidence": fold["gain_evidence"],
            }
            for fold in schedule["folds"]
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
        "outer_maximum_reserved_physical_tube_half_width": outer[
            "maximum_reserved_physical_tube_half_width"
        ],
        "outer_adapted_to_cold_l1_ratio": outer["adaptation_usefulness"][
            "adapted_to_cold_total_l1_ratio"
        ],
        "schedule_model_gate_passed": bool(schedule["passed"]),
        "schedule_maximum_absolute_physical_error": schedule[
            "maximum_absolute_physical_error"
        ],
        "schedule_maximum_reserved_physical_tube_half_width": schedule[
            "maximum_reserved_physical_tube_half_width"
        ],
        "schedule_adapted_to_cold_l1_ratio": schedule["adaptation_usefulness"][
            "adapted_to_cold_total_l1_ratio"
        ],
        "combined_tube_cap_passed": bool(detailed["combined_tube_cap_passed"]),
        "model_gate_passed": bool(detailed["model_gate_passed"]),
        "adaptation_usefulness_gate_passed": bool(
            detailed["adaptation_usefulness_gate_passed"]
        ),
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
        raise ValueError("R8R37 primary requires a fresh stage directory")
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


def _run_finalize_failure(
    ctx: Context,
    paths: Mapping[str, Path],
    summary: Mapping[str, Any],
    detailed: Mapping[str, Any],
    failure: Mapping[str, Any],
    hashes: Mapping[str, str],
) -> dict[str, Any]:
    tolerance = float(
        ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"]
    )
    agreement_fields = (
        "primary_bank_agreement",
        "primary_neighbor_agreement",
        "primary_gain_agreement",
        "primary_prediction_agreement",
        "primary_tube_agreement",
        "primary_metric_agreement",
        "primary_route_agreement",
        "primary_outcome_agreement",
    )
    difference_fields = (
        "maximum_scaled_gain_difference",
        "maximum_scaled_prediction_difference",
        "maximum_scaled_tube_difference",
        "maximum_scaled_metric_difference",
    )
    numerical_disagreement = any(
        failure.get(field) is not True for field in agreement_fields
    ) or any(
        float(failure.get(field, math.inf)) > tolerance
        for field in difference_fields
    )
    if (
        failure.get("passed") is not False
        or not numerical_disagreement
        or failure.get("primary_summary_sha256") != hashes["primary_summary"]
        or failure.get("primary_detailed_sha256") != hashes["primary_detailed"]
        or failure.get("primary_model_sha256") != hashes["model"]
        or bool(failure.get("real_tsc_executed"))
        or int(failure.get("plant_step_count", -1)) != 0
        or int(failure.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("R8R37 independent failure evidence invalid")
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r37_compact_independent_failure_finalization",
        "passed": False,
        "integrity_gate_passed": False,
        "scientific_gate_passed": False,
        "route": ctx.cfg["routes"]["execution_fail"],
        "primary_route": summary["route"],
        "failure_classification": "independent_numerical_reproducibility_gate_failure",
        "source_file_sha256": hashes,
        "summary": summary,
        "local_cardinality_audit": detailed["local_cardinality_audit"],
        "outer_model_evaluation": detailed["outer_model_evaluation"],
        "schedule_jackknife": detailed["schedule_jackknife"],
        "combined_tube_maximum_physical_half_width": detailed[
            "combined_tube_maximum_physical_half_width"
        ],
        "combined_tube_cap_passed": detailed["combined_tube_cap_passed"],
        "adaptation_usefulness_gate_passed": detailed[
            "adaptation_usefulness_gate_passed"
        ],
        "independent_failure": {
            field: failure.get(field)
            for field in (*agreement_fields, *difference_fields)
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
    final["audit_kind"] = "r8r37_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest = _read(ctx.paths.manifest)
    manifest.update(
        {
            "independent_failure_sha256": hashes["independent_failure"],
            "compact_audit_sha256": _sha(compact_path),
            "final_report_sha256": _sha(final_path),
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
            "independent_completed": True,
            "independent_validation_passed": False,
            "scientific_gate_passed": False,
            "primary_route": summary["route"],
            "route": ctx.cfg["routes"]["execution_fail"],
        }
    )
    _write(ctx.paths.state, state)
    return final


def run_finalize(ctx: Context) -> dict[str, Any]:
    paths: dict[str, Path] = {
        "primary_summary": ctx.paths.analysis / "primary_summary.json",
        "primary_detailed": ctx.paths.analysis / "primary_detailed.json",
        "model": ctx.paths.model / "preflight_model.json",
    }
    independent_path = ctx.paths.analysis / "independent.json"
    failure_path = ctx.paths.analysis / "independent_failure.json"
    if any(
        not path.is_file()
        for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)
    ) or independent_path.is_file() == failure_path.is_file():
        raise ValueError("R8R37 finalization evidence incomplete or ambiguous")
    summary = _read(paths["primary_summary"])
    detailed = _read(paths["primary_detailed"])
    if failure_path.is_file():
        paths["independent_failure"] = failure_path
        hashes = {name: _sha(path) for name, path in paths.items()}
        return _run_finalize_failure(
            ctx,
            paths,
            summary,
            detailed,
            _read(failure_path),
            hashes,
        )
    paths["independent"] = independent_path
    if any(
        not path.is_file()
        for path in (*paths.values(), ctx.paths.manifest, ctx.paths.state)
    ):
        raise ValueError("R8R37 finalization evidence incomplete")
    independent = _read(paths["independent"])
    hashes = {name: _sha(path) for name, path in paths.items()}
    tolerance = float(
        ctx.cfg["model_contract"]["primary_independent_scaled_tolerance"]
    )
    agreement_fields = (
        "primary_bank_agreement",
        "primary_neighbor_agreement",
        "primary_gain_agreement",
        "primary_prediction_agreement",
        "primary_tube_agreement",
        "primary_metric_agreement",
        "primary_route_agreement",
        "primary_outcome_agreement",
    )
    difference_fields = (
        "maximum_scaled_gain_difference",
        "maximum_scaled_prediction_difference",
        "maximum_scaled_tube_difference",
        "maximum_scaled_metric_difference",
    )
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
        raise ValueError("R8R37 finalization independent disagreement")
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r37_compact_primary_independent_finalization",
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
        "adaptation_usefulness_gate_passed": detailed[
            "adaptation_usefulness_gate_passed"
        ],
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
    final["audit_kind"] = "r8r37_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest = _read(ctx.paths.manifest)
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
            "independent_completed": True,
            "independent_validation_passed": True,
            "scientific_gate_passed": bool(summary["scientific_gate_passed"]),
            "route": summary["route"],
        }
    )
    _write(ctx.paths.state, state)
    return final


ARGUMENT_NAMES = (
    "config",
    "run-dir",
    "r8r35-run",
) + tuple(name for name in r8r35.ARGUMENT_NAMES if name not in {"config", "run-dir"})


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
