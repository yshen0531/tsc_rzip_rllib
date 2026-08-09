#!/usr/bin/env python3
"""R8R46 q0-calibration causal-innovation controller preflight."""

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
    stage4_2r3c3t13s24d1r14r8r43_fixed_affine_dominant_global_ridge_local_affine_cold_ensemble_preflight
    as r8r43,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r44_fixed_affine_dominant_global_local_affine_cold_ensemble_receding_controller_preflight
    as r8r44,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R46"
IDENTITY = "q0_calibration_causal_innovation_controller_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r46_q0_calibration_causal_innovation_controller_preflight"
POST_INTERVALS = tuple(range(1, 6))
FACTORS = np.asarray(r8r31.OUTPUT_FACTORS, dtype=float)

_read = r8r44._read
_write = r8r44._write
_sha = r8r44._sha
_digest = r8r44._digest
_jsonable = r8r44._jsonable


class SourceBlockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    stage: Path
    analysis: Path
    model: Path
    state: Path
    manifest: Path


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    r8r44_ctx: r8r44.Context
    r8r44_stage: Path

    @property
    def source_ctx(self):
        return self.r8r44_ctx.source_ctx

    @property
    def r8r43_ctx(self):
        return self.r8r44_ctx.r8r43_ctx


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    model = cfg.get("model_contract", {})
    gates = cfg.get("model_gates", {})
    useful = cfg.get("adaptation_usefulness_gate", {})
    calibration = cfg.get("calibration_contract", {})
    planner = cfg.get("planner_contract", {})
    action = cfg.get("action_contract", {})
    offline = cfg.get("offline_gate", {})
    formal = cfg.get("formal_contract", {})
    scope = cfg.get("scientific_scope", {})
    routes = {
        "source_blocked": "Q0_CALIBRATION_CAUSAL_INNOVATION_PREFLIGHT_BLOCKED_BY_SOURCE",
        "execution_fail": "Q0_CALIBRATION_CAUSAL_INNOVATION_PREFLIGHT_EXECUTION_FAIL_STOP",
        "model_fail": "Q0_CALIBRATION_CAUSAL_INNOVATION_MODEL_INSUFFICIENT_NO_TSC",
        "safety_fail": "Q0_CALIBRATION_CAUSAL_INNOVATION_SAFETY_FAIL_NO_TSC",
        "authority_fail": "Q0_CALIBRATION_CAUSAL_INNOVATION_AUTHORITY_INSUFFICIENT_NO_TSC",
        "pass": "Q0_CALIBRATION_CAUSAL_INNOVATION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED",
    }
    design = project_root / str(cfg.get("design_document", ""))
    source_config = project_root / str(cfg.get("source_r8r44_config", ""))
    invalid = (
        cfg.get("schema_version") != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source_config.is_file()
        or _sha(source_config) != cfg.get("source_r8r44_config_sha256")
        or tuple(float(model.get(key, -1.0)) for key in ("global_weight", "local_weight")) != (0.25, 0.75)
        or float(model.get("reserve_multiplier", -1.0)) != 1.25
        or tuple(
            float(model.get(key, -1.0))
            for key in (
                "innovation_update_previous_weight",
                "innovation_update_residual_weight",
                "innovation_forecast_decay",
            )
        )
        != (0.5, 0.5, 0.5)
        or list(model.get("adapted_validation_intervals", [])) != list(POST_INTERVALS)
        or any(model.get(key) is not False for key in (
            "gain_search_allowed",
            "weight_search_allowed",
            "feature_search_allowed",
            "tube_clipping_allowed",
            "outcome_selection_allowed",
        ))
        or list(gates.get("maximum_point_error", [])) != [0.015, 0.015, 3000.0, 0.05, 0.05]
        or list(gates.get("maximum_tube_half_width", [])) != [0.025, 0.025, 5000.0, 0.08, 0.08]
        or float(gates.get("required_reserved_tube_containment_rate", -1.0)) != 1.0
        or float(gates.get("required_whole_pair_support_rate", -1.0)) != 1.0
        or float(gates.get("required_whole_schedule_support_rate", -1.0)) != 1.0
        or float(gates.get("required_finite_prediction_rate", -1.0)) != 1.0
        or int(gates.get("required_forbidden_input_count", -1)) != 0
        or int(gates.get("required_innovation_clipping_component_count", -1)) != 0
        or tuple(
            useful.get(key)
            for key in (
                "maximum_adapted_to_cold_aggregate_normalized_squared_error_ratio",
                "minimum_strictly_improved_whole_pair_fold_count",
                "required_whole_pair_fold_count",
                "maximum_whole_pair_fold_ratio",
                "maximum_whole_schedule_aggregate_ratio",
                "required_whole_schedule_fold_count",
            )
        )
        != (0.95, 6, 8, 1.05, 0.95, 35)
        or tuple(calibration.get(key) for key in ("issue_task_step", "measurement_task_step", "candidate_index", "candidate_id"))
        != (10, 12, 0, "q0")
        or int(calibration.get("required_context_count", -1)) != 16
        or any(calibration.get(key) is not True for key in (
            "require_exact_target_hold",
            "require_cold_tube_containment",
            "require_zero_clipping_components",
        ))
        or list(planner.get("transport_decision_task_steps", [])) != [12, 14, 16, 18, 22]
        or tuple(int(planner.get(key, -1)) for key in ("candidate_count", "beam_width", "dynamic_exact_search_radius"))
        != (17, 512, 16)
        or planner.get("measurement_recentered") is not True
        or planner.get("execute_first_action_only") is not True
        or planner.get("failed_plan_deployment_allowed") is not False
        or planner.get("fallback") != "exact_current_target_hold"
        or planner.get("immediate_safety_tube") != "componentwise_max_cold_and_adapted"
        or tuple(float(action.get(key, -1.0)) for key in (
            "maximum_incremental_normalized_action_linf",
            "maximum_total_normalized_action_abs",
            "maximum_current_utilization",
            "minimum_desired_applied_current_cosine",
            "maximum_relative_off_basis_residual",
        ))
        != (0.25, 1.0, 0.55, 0.98, 0.1)
        or any(action.get(key) is not True for key in (
            "require_exact_card15_issue",
            "require_exact_card15_refresh",
            "safe_stop_before_failed_advance",
        ))
        or tuple(int(offline.get(key, -1)) for key in (
            "required_calibration_context_count",
            "required_safe_search_context_count",
            "minimum_predicted_repaired_failed_baseline_count",
            "maximum_predicted_regressed_baseline_pass_count",
            "minimum_predicted_oracle_count",
            "minimum_nonzero_first_transport_action_count",
            "required_fault_injection_count",
        ))
        != (16, 16, 1, 0, 7, 1, 6)
        or tuple(int(formal.get(key, -1)) for key in (
            "normal_arrival_deadline_step",
            "normal_hold_through_step",
            "weak_arrival_deadline_step",
            "weak_hold_through_step",
            "arrival_streak_steps",
        ))
        != (25, 35, 27, 37, 3)
        or tuple(float(formal.get(key, -1.0)) for key in (
            "position_tolerance_m", "speed_tolerance_m_per_s", "ip_tolerance_A"
        ))
        != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
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
        raise ValueError("R8R46 frozen config changed")


def load_context(args: argparse.Namespace) -> Context:
    root = _root()
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=root)
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (root / str(cfg["source_r8r44_config"])).resolve()
    source_args.run_dir = args.r8r44_run.expanduser().resolve()
    source_ctx = r8r44.load_context(source_args)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r44_ctx=source_ctx,
        r8r44_stage=source_ctx.paths.stage,
    )


def _r8r44_paths(stage: Path) -> dict[str, Path]:
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


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    paths = _r8r44_paths(ctx.r8r44_stage)
    contract = ctx.cfg["source_r8r44"]
    if any(not path.is_file() for path in paths.values()):
        raise SourceBlockedError("R8R46 R8R44 source evidence incomplete")
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise SourceBlockedError("R8R46 R8R44 source hash changed")
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    route = contract["required_route"]
    if (
        summary.get("route") != route
        or summary.get("scientific_gate_passed") is not False
        or independent.get("passed") is not True
        or independent.get("primary_route_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or final.get("route") != route
        or final.get("integrity_gate_passed") is not True
        or final.get("scientific_gate_passed") is not False
        or state.get("route") != route
        or manifest.get("final_route") != route
        or bool(final.get("real_tsc_executed"))
        or int(final.get("plant_step_count", -1)) != 0
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise SourceBlockedError("R8R46 requires exact final R8R44 authority failure")
    return {
        "r8r44_final": {"hashes": hashes, "passed": True},
        "r8r44_transitive": r8r44.authenticate_sources(ctx.r8r44_ctx),
        "passed": True,
    }


def _verify_bank(bank: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    contract = cfg["bank_contract"]
    if (
        int(bank.get("trajectory_count", -1)) != int(contract["trajectory_count"])
        or int(bank.get("context_count", -1)) != int(contract["history_context_count"])
        or int(bank.get("schedule_count", -1)) != int(contract["schedule_count"])
        or int(bank.get("interval_record_count", -1)) != int(contract["interval_record_count"])
        or any(bank.get(key) != contract[key] for key in ("bank_digest", "feature_digest", "target_digest"))
    ):
        raise ValueError("R8R46 bank reproduction changed")


def _cold_source_binding(
    ctx: Context,
    trajectories: Sequence[Mapping[str, Any]],
    bank: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    transitive = r8r43.authenticate_sources(ctx.r8r43_ctx)
    detailed, artifact = r8r43.compute_from_bank(ctx.r8r43_ctx, transitive, trajectories, bank)
    source_detailed = _read(ctx.r8r43_ctx.paths.stage / "analysis/primary_detailed.json")
    source_model = _read(ctx.r8r43_ctx.paths.stage / "model/preflight_model.json")
    binding = {
        "recomputed_primary_detailed_digest": _digest(detailed),
        "source_primary_detailed_digest": _digest(source_detailed),
        "recomputed_model_digest": _digest(artifact),
        "source_model_digest": _digest(source_model),
        "primary_detailed_exact": detailed == source_detailed,
        "model_artifact_exact": artifact == source_model,
    }
    binding["passed"] = bool(binding["primary_detailed_exact"] and binding["model_artifact_exact"])
    return detailed, artifact, binding


def _schedule_support(
    trajectories: Sequence[Mapping[str, Any]], held_schedule: str, multiplier: float
) -> dict[str, Any]:
    schedules = sorted({str(row["schedule_id"]) for row in trajectories})
    training = [name for name in schedules if name != held_schedule]
    rows = []
    for interval in POST_INTERVALS:
        by_schedule = {
            name: np.asarray(
                [row["intervals"][interval]["feature"] for row in trajectories if str(row["schedule_id"]) == name],
                dtype=float,
            )
            for name in training
        }
        nested = []
        for name, values in by_schedule.items():
            others = np.concatenate([value for key, value in by_schedule.items() if key != name])
            nested.extend(r8r31.cKDTree(others).query(values, k=1, eps=0.0, workers=1)[0].tolist())
        threshold = multiplier * max(map(float, nested))
        train = np.concatenate(list(by_schedule.values()))
        held = np.asarray(
            [row["intervals"][interval]["feature"] for row in trajectories if str(row["schedule_id"]) == held_schedule],
            dtype=float,
        )
        distance = r8r31.cKDTree(train).query(held, k=1, eps=0.0, workers=1)[0]
        rows.append(
            {
                "interval": interval,
                "threshold": threshold,
                "maximum_held_distance": float(np.max(distance)),
                "pass_count": int(np.count_nonzero(distance <= threshold + 1e-15)),
                "row_count": len(distance),
            }
        )
    return {"rows": rows, "passed": all(row["pass_count"] == row["row_count"] for row in rows)}


def _adapt_held(
    held: Sequence[Mapping[str, Any]],
    prediction_rows: Sequence[Mapping[str, Any]],
    cold_training_tube: Sequence[np.ndarray],
    cfg: Mapping[str, Any],
) -> tuple[list[list[list[np.ndarray]]], dict[str, Any], list[dict[str, Any]]]:
    predictions = {str(row["trajectory_id"]): row for row in prediction_rows}
    groups: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in r8r31.MAX_COUNTS]
    reserve = float(cfg["model_contract"]["reserve_multiplier"])
    scales = np.asarray(cfg["model_contract"]["primary_independent_component_scales"], dtype=float)
    normalization = FACTORS / scales
    cold_squared = adapted_squared = 0.0
    post_rows = clipping_components = 0
    serial = []
    artifact = []
    for trajectory in sorted(held, key=lambda row: str(row["trajectory_id"])):
        source = predictions[str(trajectory["trajectory_id"])]
        cold_rows = [np.asarray(row, dtype=float) for row in source["ensemble_predictions"]]
        bias = np.zeros(5, dtype=float)
        adapted_rows = []
        residual_rows = []
        update_rows = []
        for interval, row in enumerate(trajectory["intervals"]):
            actual = np.asarray(row["targets"], dtype=float).reshape((-1, 5))
            cold = cold_rows[interval]
            adapted = cold + bias
            absolute = np.abs(actual - adapted)
            for offset, value in enumerate(absolute):
                groups[interval][offset].append(value)
            if interval in POST_INTERVALS:
                cold_squared += float(np.sum(np.square((actual - cold) * normalization)))
                adapted_squared += float(np.sum(np.square((actual - adapted) * normalization)))
                post_rows += len(actual)
            innovation = actual[-1] - adapted[-1]
            cap = np.asarray(cold_training_tube[interval][-1], dtype=float) / reserve
            proposed = 0.5 * bias + 0.5 * innovation
            clipped = np.abs(proposed) > cap + 1e-15
            clipping_components += int(np.count_nonzero(clipped))
            next_bias = np.clip(proposed, -cap, cap)
            update_rows.append(
                {
                    "interval": interval,
                    "innovation": innovation.tolist(),
                    "cap": cap.tolist(),
                    "proposed_bias": proposed.tolist(),
                    "next_bias": next_bias.tolist(),
                    "clipped_components": int(np.count_nonzero(clipped)),
                }
            )
            bias = next_bias
            adapted_rows.append(adapted.tolist())
            residual_rows.append(absolute.tolist())
        serial.append({"trajectory_id": trajectory["trajectory_id"], "absolute_residuals": residual_rows, "updates": update_rows})
        artifact.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "cold_predictions": [row.tolist() for row in cold_rows],
                "adapted_predictions": adapted_rows,
                "updates": update_rows,
            }
        )
    ratio = adapted_squared / cold_squared if cold_squared > 0.0 else math.inf
    return groups, {
        "residual_digest": _digest(serial),
        "cold_postcal_normalized_squared_error": cold_squared,
        "adapted_postcal_normalized_squared_error": adapted_squared,
        "adapted_to_cold_ratio": ratio,
        "postcal_time_row_count": post_rows,
        "innovation_clipping_component_count": clipping_components,
    }, artifact


def _post_metrics(
    folds: Sequence[dict[str, Any]],
    cfg: Mapping[str, Any],
    *,
    held_key: str,
    pair_family: bool,
) -> tuple[list[np.ndarray], dict[str, Any]]:
    contained = total = 0
    maximum_error = np.zeros(5, dtype=float)
    maximum_tube = np.zeros(5, dtype=float)
    fold_rows = []
    cold_total = adapted_total = 0.0
    clipping = 0
    strict_improved = 0
    maximum_ratio = 0.0
    for fold in folds:
        held = str(fold[held_key])
        tube, tube_evidence = r8r31._tube_from_fold_groups(
            folds, lambda row, current=held: str(row[held_key]) != current, cfg
        )
        fold_contained = fold_total = 0
        fold_error = np.zeros(5, dtype=float)
        for interval in POST_INTERVALS:
            for offset, values in enumerate(fold["residual_groups"][interval]):
                residual = np.asarray(values, dtype=float).reshape((-1, 5))
                fold_contained += int(np.count_nonzero(residual <= tube[interval][offset] + 1e-15))
                fold_total += residual.size
                if len(residual):
                    fold_error = np.maximum(fold_error, np.max(residual, axis=0))
        maximum_error = np.maximum(maximum_error, fold_error * FACTORS)
        maximum_tube = np.maximum(
            maximum_tube,
            np.max(np.concatenate([tube[index] for index in POST_INTERVALS]), axis=0) * FACTORS,
        )
        contained += fold_contained
        total += fold_total
        evidence = fold["adaptation_evidence"]
        cold_total += float(evidence["cold_postcal_normalized_squared_error"])
        adapted_total += float(evidence["adapted_postcal_normalized_squared_error"])
        ratio = float(evidence["adapted_to_cold_ratio"])
        strict_improved += int(ratio < 1.0)
        maximum_ratio = max(maximum_ratio, ratio)
        clipping += int(evidence["innovation_clipping_component_count"])
        fold_rows.append(
            {
                held_key: held,
                "cold_model_digest": fold["cold_model_digest"],
                "residual_digest": evidence["residual_digest"],
                "maximum_physical_error": (fold_error * FACTORS).tolist(),
                "contained_count": fold_contained,
                "component_count": fold_total,
                "support": fold["support"],
                "adapted_to_cold_ratio": ratio,
                "innovation_clipping_component_count": evidence["innovation_clipping_component_count"],
                "tube_evidence": tube_evidence,
            }
        )
    final_tube, final_tube_evidence = r8r31._tube_from_fold_groups(folds, lambda _row: True, cfg)
    gates = cfg["model_gates"]
    rate = contained / total
    aggregate_ratio = adapted_total / cold_total if cold_total > 0.0 else math.inf
    support_pass = all(bool(fold["support"]["passed"]) for fold in folds)
    model_pass = bool(
        np.all(maximum_error <= np.asarray(gates["maximum_point_error"]) + 1e-15)
        and np.all(maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15)
        and rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
        and support_pass
        and clipping == int(gates["required_innovation_clipping_component_count"])
        and float(gates["required_finite_prediction_rate"]) == 1.0
        and int(gates["required_forbidden_input_count"]) == 0
    )
    useful = cfg["adaptation_usefulness_gate"]
    usefulness_pass = bool(
        aggregate_ratio <= float(
            useful[
                "maximum_adapted_to_cold_aggregate_normalized_squared_error_ratio"
                if pair_family
                else "maximum_whole_schedule_aggregate_ratio"
            ]
        )
        + 1e-15
        and (
            strict_improved >= int(useful["minimum_strictly_improved_whole_pair_fold_count"])
            and maximum_ratio <= float(useful["maximum_whole_pair_fold_ratio"]) + 1e-15
            if pair_family
            else True
        )
    )
    return final_tube, {
        "fold_count": len(folds),
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "contained_count": contained,
        "component_count": total,
        "containment_rate": rate,
        "support_pass_count": sum(bool(fold["support"]["passed"]) for fold in folds),
        "innovation_clipping_component_count": clipping,
        "finite_prediction_rate": 1.0,
        "forbidden_predictor_input_count": 0,
        "fold_rows": fold_rows,
        "cold_total_normalized_squared_error": cold_total,
        "adapted_total_normalized_squared_error": adapted_total,
        "adapted_to_cold_aggregate_ratio": aggregate_ratio,
        "strictly_improved_fold_count": strict_improved,
        "maximum_fold_ratio": maximum_ratio,
        "model_passed": model_pass,
        "usefulness_passed": usefulness_pass,
        "passed": bool(model_pass and usefulness_pass),
        "final_tube_evidence": final_tube_evidence,
    }


def postcalibration_from_cold_folds(
    ctx: Context,
    trajectories: Sequence[Mapping[str, Any]],
    outer_folds: Sequence[dict[str, Any]],
    outer_predictions: Sequence[Mapping[str, Any]],
    schedule_folds: Sequence[dict[str, Any]],
    schedule_predictions: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg43 = ctx.r8r43_ctx.cfg
    outer_artifact = {str(row["held_pair"]): row["trajectories"] for row in outer_predictions}
    adapted_outer = []
    outer_prediction_artifact = []
    for fold in outer_folds:
        held_pair = str(fold["held_pair"])
        held = [row for row in trajectories if str(row["pair_id"]) == held_pair]
        groups, evidence, predictions = _adapt_held(
            held, outer_artifact[held_pair], fold["tube"], ctx.cfg
        )
        adapted_outer.append(
            {
                "held_pair": held_pair,
                "cold_model_digest": fold["model_digest"],
                "residual_groups": groups,
                "adaptation_evidence": evidence,
                "support": fold["support"],
            }
        )
        outer_prediction_artifact.append({"held_pair": held_pair, "trajectories": predictions})
    pair_tube, outer = _post_metrics(
        adapted_outer, ctx.cfg, held_key="held_pair", pair_family=True
    )

    schedule_artifact = {str(row["held_schedule"]): row["trajectories"] for row in schedule_predictions}
    adapted_schedule = []
    schedule_prediction_artifact = []
    multiplier = float(ctx.source_ctx.cfg["model_contract"]["support_threshold_multiplier"])
    for fold in schedule_folds:
        held_schedule = str(fold["held_schedule"])
        cold_training_tube, _unused = r8r31._tube_from_fold_groups(
            schedule_folds,
            lambda row, current=held_schedule: str(row["held_schedule"]) != current,
            cfg43,
        )
        held = [row for row in trajectories if str(row["schedule_id"]) == held_schedule]
        groups, evidence, predictions = _adapt_held(
            held, schedule_artifact[held_schedule], cold_training_tube, ctx.cfg
        )
        adapted_schedule.append(
            {
                "held_schedule": held_schedule,
                "cold_model_digest": fold["model_digest"],
                "residual_groups": groups,
                "adaptation_evidence": evidence,
                "support": _schedule_support(trajectories, held_schedule, multiplier),
            }
        )
        schedule_prediction_artifact.append(
            {"held_schedule": held_schedule, "trajectories": predictions}
        )
    schedule_tube, schedule = _post_metrics(
        adapted_schedule, ctx.cfg, held_key="held_schedule", pair_family=False
    )
    combined = [
        np.maximum(pair, schedule_value)
        for pair, schedule_value in zip(pair_tube, schedule_tube)
    ]
    combined_maximum = (
        np.max(np.concatenate([combined[index] for index in POST_INTERVALS]), axis=0)
        * FACTORS
    )
    combined_passed = bool(
        np.all(
            combined_maximum
            <= np.asarray(ctx.cfg["model_gates"]["maximum_tube_half_width"]) + 1e-15
        )
    )
    scientific = bool(outer["passed"] and schedule["passed"] and combined_passed)
    evidence = {
        "outer_model_evaluation": outer,
        "schedule_jackknife": schedule,
        "combined_postcalibration_tube_maximum_physical_half_width": combined_maximum.tolist(),
        "combined_postcalibration_tube_cap_passed": combined_passed,
        "model_gate_passed": scientific,
    }
    artifact = {
        "outer_predictions": outer_prediction_artifact,
        "schedule_predictions": schedule_prediction_artifact,
        "pair_tube": pair_tube,
        "schedule_tube": schedule_tube,
        "combined_tube": combined,
    }
    return _jsonable(evidence), _jsonable(artifact), {
        "outer_folds": adapted_outer,
        "schedule_folds": adapted_schedule,
    }


def postcalibration_model(
    ctx: Context,
    trajectories: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg43 = ctx.r8r43_ctx.cfg
    outer_folds, _cold_outer, outer_predictions = r8r43.outer_model_evaluation(
        trajectories, cfg43, ctx.source_ctx.cfg
    )
    _cold_schedule_tube, schedule_folds, _cold_schedule, schedule_predictions = r8r43.schedule_jackknife(
        trajectories, cfg43
    )
    return postcalibration_from_cold_folds(
        ctx,
        trajectories,
        outer_folds,
        outer_predictions,
        schedule_folds,
        schedule_predictions,
    )


def _calibration_row(
    ctx: Context,
    meta: Mapping[str, Any],
    q0_trajectory: Mapping[str, Any],
    model: Mapping[str, Any],
    cold_tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
    *,
    predict_fn: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], np.ndarray],
) -> dict[str, Any]:
    row = q0_trajectory["intervals"][0]
    feature = np.asarray(row["feature"], dtype=float)
    distance = float(r8r31.cKDTree(np.asarray(support["features"][0])).query(feature, k=1, eps=0.0, workers=1)[0])
    state_supported = distance <= float(support["thresholds"][0]) + 1e-15
    candidate = r8r31._candidate_rows(ctx.source_ctx.cfg)[0]
    transition_supported = r8r31.transition_supported(
        hulls[0], np.zeros(4), np.asarray(candidate["q"]), ctx.source_ctx.cfg
    )
    source_trajectory = q0_trajectory["trajectory"]
    current = np.asarray(source_trajectory[10]["currents_a_tsc"], dtype=float)
    issue = r8r31._safe_issue(ctx.source_ctx, meta, current, candidate, 10)
    cold = np.asarray(predict_fn(model, row, ctx.r8r43_ctx.cfg), dtype=float)
    actual = np.asarray(row["targets"], dtype=float)
    residual = actual - cold
    contained = bool(np.all(np.abs(residual) <= np.asarray(cold_tube[0][: len(actual)]) + 1e-15))
    cap = np.asarray(cold_tube[0][-1], dtype=float) / float(ctx.cfg["model_contract"]["reserve_multiplier"])
    proposed = 0.5 * residual[-1]
    clipped = np.abs(proposed) > cap + 1e-15
    bias = np.clip(proposed, -cap, cap)
    measured_states = np.asarray(q0_trajectory["states"], dtype=float)[:13]
    measured_current = np.asarray(source_trajectory[12]["currents_a_tsc"], dtype=float)
    expected_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
    target_hold_maximum_current_difference = float(np.max(np.abs(measured_current - expected_current)))
    exact_target_hold = bool(
        np.array_equal(np.asarray(row["q"], dtype=float), np.zeros(4, dtype=float))
        and np.array_equal(np.asarray(row["previous_q"], dtype=float), np.zeros(4, dtype=float))
        and target_hold_maximum_current_difference <= 1e-9
    )
    passed = bool(
        state_supported
        and transition_supported
        and issue["passed"]
        and contained
        and not np.any(clipped)
        and exact_target_hold
        and candidate["id"] == "q0"
        and int(candidate["index"]) == 0
    )
    return {
        "pair_id": str(meta["pair_id"]),
        "history_member": str(meta["history_member"]),
        "trajectory_id": str(q0_trajectory["trajectory_id"]),
        "candidate_index": int(candidate["index"]),
        "candidate_id": str(candidate["id"]),
        "state_support_distance": distance,
        "state_support_threshold": float(support["thresholds"][0]),
        "state_supported": state_supported,
        "transition_supported": transition_supported,
        "issue": issue,
        "exact_target_hold": exact_target_hold,
        "target_hold_maximum_current_difference_a": target_hold_maximum_current_difference,
        "measured_states_through_task_step_12": measured_states.tolist(),
        "measured_current_a_tsc": measured_current.tolist(),
        "previous_current_a_tsc": current.tolist(),
        "cold_tube_contained": contained,
        "innovation": residual[-1].tolist(),
        "innovation_cap": cap.tolist(),
        "proposed_bias": proposed.tolist(),
        "bias": bias.tolist(),
        "clipped_component_count": int(np.count_nonzero(clipped)),
        "passed": passed,
    }


def plan_after_calibration(
    ctx: Context,
    meta: Mapping[str, Any],
    calibration: Mapping[str, Any],
    model: Mapping[str, Any],
    adapted_tube: Sequence[np.ndarray],
    cold_tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
    hulls: Sequence[Mapping[str, Any]],
    *,
    predict_fn: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], np.ndarray],
) -> dict[str, Any]:
    candidates = r8r31._candidate_rows(ctx.source_ctx.cfg)
    states = np.asarray(calibration["measured_states_through_task_step_12"], dtype=float)
    current = np.asarray(calibration["measured_current_a_tsc"], dtype=float)
    previous = np.asarray(calibration["previous_current_a_tsc"], dtype=float)
    bias = np.asarray(calibration["bias"], dtype=float)
    beam = [
        {
            "states": states,
            "tubes": np.zeros_like(states),
            "current": current,
            "previous_current": previous,
            "previous_q": np.zeros(4, dtype=float),
            "tokens": tuple(),
            "movement": 0.0,
            "maximum_current": 0.0,
        }
    ]
    trees = [r8r31.cKDTree(np.asarray(values)) for values in support["features"]]
    counters = {"state_unsupported": 0, "transition_unsupported": 0, "hard_rejected": 0, "safe": 0}
    beam_counts = []
    for interval in POST_INTERVALS:
        decision = r8r31.DECISIONS[interval]
        expanded_nodes = []
        for node in beam:
            feature = r8r31._planning_feature44(
                np.asarray(node["states"]),
                np.asarray(node["current"]),
                np.asarray(node["previous_current"]),
                np.asarray(node["previous_q"]),
                np.asarray(meta["coil_limits"]),
            )
            distance = float(trees[interval].query(feature, k=1, eps=0.0, workers=1)[0])
            if distance > float(support["thresholds"][interval]) + 1e-15:
                counters["state_unsupported"] += 1
                continue
            for candidate in candidates:
                q = np.asarray(candidate["q"])
                if not r8r31.transition_supported(hulls[interval], node["previous_q"], q, ctx.source_ctx.cfg):
                    counters["transition_unsupported"] += 1
                    continue
                issue = r8r31._safe_issue(ctx.source_ctx, meta, np.asarray(node["current"]), candidate, decision)
                if not bool(issue["passed"]):
                    counters["hard_rejected"] += 1
                    continue
                count = r8r31.MAX_COUNTS[interval]
                if interval == 5 and int(meta["horizon"]) == 35:
                    count = 13
                row = {
                    "interval": interval,
                    "feature": feature,
                    "q": q,
                    "previous_q": np.asarray(node["previous_q"]),
                    "targets": np.zeros((count, 5)),
                }
                row["expanded"] = r8r31.expanded_feature238(feature, q, node["previous_q"])
                cold = np.asarray(predict_fn(model, row, ctx.r8r43_ctx.cfg), dtype=float)
                forecast = cold + (0.5 ** (interval - 1)) * bias
                next_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"])
                expanded_nodes.append(
                    {
                        "states": np.concatenate((np.asarray(node["states"]), forecast)),
                        "tubes": np.concatenate((np.asarray(node["tubes"]), np.asarray(adapted_tube[interval][:count]))),
                        "current": next_current,
                        "previous_current": np.asarray(node["current"]),
                        "previous_q": q,
                        "tokens": tuple(node["tokens"]) + (int(candidate["index"]),),
                        "movement": float(node["movement"]) + float(np.sum(np.abs(q - node["previous_q"]))),
                        "maximum_current": max(float(node["maximum_current"]), float(issue["predicted_current_utilization"])),
                    }
                )
                counters["safe"] += 1
        terminal = interval == 5
        expanded_nodes.sort(
            key=lambda node: r8r31._node_rank(node, terminal=terminal, meta=meta, cfg=ctx.source_ctx.cfg)
        )
        beam = expanded_nodes[: int(ctx.cfg["planner_contract"]["beam_width"])]
        beam_counts.append(len(beam))
        if not beam:
            break
    best = beam[0] if beam else None
    selected = None
    if best is not None:
        rank = r8r31._node_rank(best, terminal=True, meta=meta, cfg=ctx.source_ctx.cfg)
        selected = {
            "candidate_indices": list(best["tokens"]),
            "candidate_ids": [candidates[index]["id"] for index in best["tokens"]],
            "robust_formal_pass": not bool(rank[0]),
            "worst_formal_margin_violation": float(rank[1]),
            "integrated_normalized_error": float(rank[2]),
            "movement": float(rank[3]),
            "maximum_predicted_current_utilization": float(rank[4]),
        }
    robust = bool(selected and selected["robust_formal_pass"])
    immediate = np.asarray(adapted_tube[1])
    return {
        "pair_id": str(meta["pair_id"]),
        "history_member": str(meta["history_member"]),
        "calibration": calibration,
        "beam_counts": beam_counts,
        "counters": counters,
        "safe_search_complete": best is not None,
        "selected_plan": selected,
        "robust_formal_plan_found": robust,
        "causal_mode": "calibrated_first_action_plan" if robust else "exact_current_target_hold_fallback",
        "immediate_safety_tube_maximum_physical_half_width": (np.max(immediate, axis=0) * FACTORS).tolist(),
    }


def evaluate_planning(
    ctx: Context,
    trajectories: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
    adapted_tube: Sequence[np.ndarray],
    cold_tube: Sequence[np.ndarray],
    *,
    fit_model_fn: Callable[..., Mapping[str, Any]],
    predict_fn: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], np.ndarray],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    model = fit_model_fn(trajectories, lambda _row: True, ctx.r8r43_ctx.cfg)
    support = r8r31.planning_support(trajectories, ctx.source_ctx.cfg)
    hulls = r8r31.transition_hulls(trajectories, ctx.source_ctx.cfg)
    q0 = {
        (str(row["pair_id"]), str(row["history_member"])): row
        for row in trajectories
        if str(row["schedule_id"]) == "q0"
    }
    if len(q0) != 16:
        raise ValueError("R8R46 q0 calibration trajectory coverage changed")
    calibrations = {
        key: _calibration_row(
            ctx,
            context_meta[key],
            q0[key],
            model,
            cold_tube,
            support,
            hulls,
            predict_fn=predict_fn,
        )
        for key in sorted(context_meta)
    }
    plans = [
        plan_after_calibration(
            ctx,
            context_meta[key],
            calibrations[key],
            model,
            adapted_tube,
            cold_tube,
            support,
            hulls,
            predict_fn=predict_fn,
        )
        for key in sorted(context_meta)
    ]
    baseline = r8r44._baseline_classification(ctx.r8r44_ctx)
    repairs = regressions = oracle = nonzero = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        robust = bool(plan["robust_formal_plan_found"])
        policy = bool(robust or baseline[key])
        repairs += int(not baseline[key] and robust)
        regressions += int(baseline[key] and not policy)
        oracle += int(policy)
        selected = plan.get("selected_plan") or {}
        tokens = selected.get("candidate_indices") or []
        nonzero += int(robust and bool(tokens) and int(tokens[0]) != 0)
        plan["baseline_formal_pass"] = baseline[key]
        plan["fallback_or_plan_predicted_pass"] = policy
        plan["selected_first_transport_action_index"] = int(tokens[0]) if robust and tokens else 0
        plan["selected_first_transport_action_mode"] = (
            "safe_nonzero_first_transport_action"
            if robust and tokens and int(tokens[0]) != 0
            else "safe_hold_first_transport_action"
            if robust
            else "exact_current_target_hold_fallback"
        )
    faults = r8r31.fault_injections()
    gate = ctx.cfg["offline_gate"]
    calibration_count = sum(bool(row["passed"]) for row in calibrations.values())
    safe_count = sum(bool(plan["safe_search_complete"]) for plan in plans)
    safety = bool(
        calibration_count == int(gate["required_calibration_context_count"])
        and safe_count == int(gate["required_safe_search_context_count"])
        and faults["pass_count"] == int(gate["required_fault_injection_count"])
        and faults["passed"]
    )
    authority = bool(
        safety
        and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
        and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
        and oracle >= int(gate["minimum_predicted_oracle_count"])
        and nonzero >= int(gate["minimum_nonzero_first_transport_action_count"])
    )
    planning = {
        "ran": True,
        "calibration_context_pass_count": calibration_count,
        "safe_search_context_count": safe_count,
        "predicted_repaired_failed_baseline_count": repairs,
        "predicted_regressed_baseline_pass_count": regressions,
        "predicted_fallback_plus_plan_oracle_count": oracle,
        "nonzero_first_transport_action_count": nonzero,
        "plans": plans,
        "safety_passed": safety,
        "authority_passed": authority,
        "passed": authority,
    }
    support_artifact = {
        "thresholds": support["thresholds"],
        "training_maxima": support["training_maxima"],
        "features": support["features"],
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
    return _jsonable(planning), _jsonable(faults), _jsonable(support_artifact), _jsonable(hull_summary)


def assemble_result(
    ctx: Context,
    authentication: Mapping[str, Any],
    bank: Mapping[str, Any],
    binding: Mapping[str, Any],
    model_evaluation: Mapping[str, Any],
    planning: Mapping[str, Any],
    faults: Mapping[str, Any],
) -> dict[str, Any]:
    model_gate = bool(binding["passed"] and model_evaluation["model_gate_passed"])
    safety = bool(model_gate and planning["safety_passed"] and faults["passed"])
    authority = bool(safety and planning["authority_passed"])
    route = (
        ctx.cfg["routes"]["model_fail"]
        if not model_gate
        else ctx.cfg["routes"]["safety_fail"]
        if not safety
        else ctx.cfg["routes"]["pass"]
        if authority
        else ctx.cfg["routes"]["authority_fail"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "cold_source_binding": binding,
        "postcalibration_model_evaluation": model_evaluation,
        "planning_evaluation": planning,
        "fault_injection": faults,
        "model_gate_passed": model_gate,
        "safety_gate_passed": safety,
        "authority_gate_passed": authority,
        "integrity_gate_passed": True,
        "scientific_gate_passed": authority,
        "passed": True,
        "route": route,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def skipped_planning() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[Any]]:
    faults = _jsonable(r8r31.fault_injections())
    planning = {
        "ran": False,
        "skip_reason": "postcalibration_model_gate_failed",
        "calibration_context_pass_count": 0,
        "safe_search_context_count": 0,
        "predicted_repaired_failed_baseline_count": 0,
        "predicted_regressed_baseline_pass_count": 0,
        "predicted_fallback_plus_plan_oracle_count": 0,
        "nonzero_first_transport_action_count": 0,
        "plans": [],
        "safety_passed": False,
        "authority_passed": False,
        "passed": False,
    }
    support = {"thresholds": [], "training_maxima": [], "features": []}
    return planning, faults, support, []


def execution_tube(
    cold_tube: Sequence[np.ndarray], adapted_tube: Sequence[np.ndarray]
) -> list[np.ndarray]:
    if len(cold_tube) != 6 or len(adapted_tube) != 6:
        raise ValueError("R8R46 execution tube interval coverage changed")
    return [np.asarray(cold_tube[0], dtype=float)] + [
        np.maximum(
            np.asarray(cold_tube[index], dtype=float),
            np.asarray(adapted_tube[index], dtype=float),
        )
        if index == 1
        else np.asarray(adapted_tube[index], dtype=float)
        for index in POST_INTERVALS
    ]


def compute_from_bank(
    ctx: Context,
    authentication: Mapping[str, Any],
    trajectories: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
    bank: Mapping[str, Any],
    *,
    fit_model_fn: Callable[..., Mapping[str, Any]] = r8r43.fit_model,
    predict_fn: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], np.ndarray] = lambda model, row, cfg: r8r43.predict(model, row, cfg)[2],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _verify_bank(bank, ctx.cfg)
    cold_detailed, cold_model, binding = _cold_source_binding(ctx, trajectories, bank)
    model_evaluation, adapted_model, _folds = postcalibration_model(ctx, trajectories)
    cold_tube = [np.asarray(row, dtype=float) for row in cold_model["combined_tube"]]
    adapted_tube = [np.asarray(row, dtype=float) for row in adapted_model["combined_tube"]]
    combined_execution_tube = execution_tube(cold_tube, adapted_tube)
    if bool(binding["passed"] and model_evaluation["model_gate_passed"]):
        planning, faults, support, hulls = evaluate_planning(
            ctx,
            trajectories,
            context_meta,
            combined_execution_tube,
            cold_tube,
            fit_model_fn=fit_model_fn,
            predict_fn=predict_fn,
        )
    else:
        planning, faults, support, hulls = skipped_planning()
    detailed = assemble_result(
        ctx, authentication, bank, binding, model_evaluation, planning, faults
    )
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "model_kind": "q0_calibration_fixed_ewma_causal_innovation_cold_ensemble_controller_preflight",
        "cold_base_model": cold_model,
        "postcalibration_model": adapted_model,
        "combined_execution_tube": combined_execution_tube,
        "planning_model_evidence": r8r43.model_evidence(
            fit_model_fn(trajectories, lambda _row: True, ctx.r8r43_ctx.cfg)
        ),
        "support": support,
        "transition_hulls": hulls,
        "planning_evaluation": planning,
        "cold_source_evaluation_digest": _digest(cold_detailed),
    }
    return _jsonable(detailed), _jsonable(artifact)


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    model = detailed["postcalibration_model_evaluation"]
    planning = detailed["planning_evaluation"]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "phase": "offline_primary",
        "passed": True,
        "integrity_gate_passed": True,
        "scientific_gate_passed": bool(detailed["scientific_gate_passed"]),
        "route": detailed["route"],
        "model_artifact_sha256": model_sha,
        "trajectory_count": int(detailed["bank_evidence"]["trajectory_count"]),
        "schedule_count": int(detailed["bank_evidence"]["schedule_count"]),
        "interval_record_count": int(detailed["bank_evidence"]["interval_record_count"]),
        "bank_digest": detailed["bank_evidence"]["bank_digest"],
        "cold_source_binding_passed": bool(detailed["cold_source_binding"]["passed"]),
        "outer_model_passed": bool(model["outer_model_evaluation"]["passed"]),
        "outer_adapted_to_cold_ratio": model["outer_model_evaluation"]["adapted_to_cold_aggregate_ratio"],
        "schedule_model_passed": bool(model["schedule_jackknife"]["passed"]),
        "schedule_adapted_to_cold_ratio": model["schedule_jackknife"]["adapted_to_cold_aggregate_ratio"],
        "combined_postcalibration_tube_maximum_physical_half_width": model["combined_postcalibration_tube_maximum_physical_half_width"],
        "model_gate_passed": bool(detailed["model_gate_passed"]),
        "calibration_context_pass_count": int(planning["calibration_context_pass_count"]),
        "safe_search_context_count": int(planning["safe_search_context_count"]),
        "predicted_repaired_failed_baseline_count": int(planning["predicted_repaired_failed_baseline_count"]),
        "predicted_regressed_baseline_pass_count": int(planning["predicted_regressed_baseline_pass_count"]),
        "predicted_fallback_plus_plan_oracle_count": int(planning["predicted_fallback_plus_plan_oracle_count"]),
        "nonzero_first_transport_action_count": int(planning["nonzero_first_transport_action_count"]),
        "fault_injection_hold_count": int(detailed["fault_injection"]["pass_count"]),
        "safety_gate_passed": bool(detailed["safety_gate_passed"]),
        "authority_gate_passed": bool(detailed["authority_gate_passed"]),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "controller_execution_authorized": False,
        "gate_a_qualified": False,
        "expert_data_allowed": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R46 primary requires a fresh stage directory")
    ctx.paths.stage.mkdir(parents=True)
    ctx.paths.analysis.mkdir()
    ctx.paths.model.mkdir()
    try:
        authentication = authenticate_sources(ctx)
        trajectories, context_meta, bank = r8r31.build_bank(ctx.source_ctx)
        detailed, artifact = compute_from_bank(
            ctx, authentication, trajectories, context_meta, bank
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
        route = ctx.cfg["routes"]["source_blocked" if isinstance(exc, SourceBlockedError) else "execution_fail"]
        failure = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "identity": IDENTITY,
            "phase": "offline_primary",
            "passed": False,
            "integrity_gate_passed": False,
            "scientific_gate_passed": False,
            "route": route,
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
    "primary_source_agreement",
    "primary_bank_agreement",
    "primary_model_agreement",
    "primary_innovation_agreement",
    "primary_tube_agreement",
    "primary_metric_agreement",
    "primary_planning_agreement",
    "primary_discrete_selection_agreement",
    "primary_route_agreement",
    "primary_outcome_agreement",
)
DIFFERENCE_FIELDS = (
    "maximum_bank_absolute_difference",
    "maximum_scaled_model_difference",
    "maximum_scaled_innovation_difference",
    "maximum_scaled_tube_difference",
    "maximum_scaled_metric_difference",
    "maximum_scaled_planning_difference",
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
        raise ValueError("R8R46 finalization evidence incomplete")
    if independent_path.is_file() == failure_path.is_file():
        raise ValueError("R8R46 finalization evidence ambiguous")
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
        raise ValueError("R8R46 finalization independent disagreement")
    route = summary["route"] if agreement else ctx.cfg["routes"]["execution_fail"]
    compact = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "r8r46_compact_primary_independent_finalization" if agreement else "r8r46_compact_independent_failure_finalization",
        "passed": agreement,
        "integrity_gate_passed": agreement,
        "scientific_gate_passed": bool(summary["scientific_gate_passed"]) if agreement else False,
        "route": route,
        "primary_route": summary["route"],
        "source_file_sha256": hashes,
        "summary": summary,
        "cold_source_binding": detailed["cold_source_binding"],
        "postcalibration_model_evaluation": detailed["postcalibration_model_evaluation"],
        "planning_evaluation": detailed["planning_evaluation"],
        "fault_injection": detailed["fault_injection"],
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
    final["audit_kind"] = "r8r46_final_report"
    final["compact_audit_sha256"] = _sha(compact_path)
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    manifest = _read(ctx.paths.manifest)
    manifest.update(
        {
            f"{selected_name}_sha256": hashes[selected_name],
            "compact_audit_sha256": _sha(compact_path),
            "final_report_sha256": _sha(final_path),
            "final_route": route,
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
            "route": route,
        }
    )
    _write(ctx.paths.state, state)
    return final


ARGUMENT_NAMES = ("config", "run-dir", "r8r44-run") + tuple(
    name for name in r8r44.ARGUMENT_NAMES if name not in {"config", "run-dir"}
)


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
