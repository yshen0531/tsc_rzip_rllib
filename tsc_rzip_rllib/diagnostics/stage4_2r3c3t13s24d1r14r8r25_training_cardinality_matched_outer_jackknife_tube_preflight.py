"""Frozen zero-TSC R8R25 training-cardinality-matched tube preflight."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r24_causal_local_residual_tube_receding_horizon_preflight
    as r8r24,
)


r8r23 = r8r24.r8r23
SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R25"
IDENTITY = "training_cardinality_matched_outer_jackknife_tube_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r25_training_cardinality_matched_outer_jackknife_tube_preflight"
DECISIONS = (10, 14, 18, 22)
FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=float)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


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
    source_ctx: Any
    source_stage: Path


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
    source = (root / str(cfg["source_r8r24_config"])).resolve()
    bank, model = cfg["bank_contract"], cfg["model_contract"]
    tube, action = cfg["outer_jackknife_tube_contract"], cfg["action_contract"]
    gates, formal = cfg["model_gates"], cfg["formal_contract"]
    support, planning = cfg["planning_support_contract"], cfg["planning_gate"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source) != str(cfg["source_r8r24_config_sha256"])
        or tuple(map(int, bank["decision_task_steps"])) != DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"])) != (4, 4, 4, 15)
        or tuple(
            map(
                int,
                (
                    bank["physical_pair_count"],
                    bank["history_context_count"],
                    bank["trajectory_count_per_context"],
                    bank["total_trajectory_count"],
                    bank["causal_feature_dimension"],
                    bank["expanded_feature_dimension"],
                ),
            )
        )
        != (8, 16, 27, 432, 42, 133)
        or tuple(map(float, bank["visible_scales"])) != (0.03, 0.03, 10000.0)
        or float(model["ridge_penalty"]) != 1e-4
        or tuple(map(int, (model["outer_fold_count"], model["outer_training_pair_count"]))) != (8, 7)
        or model.get("whole_pair_exclusion") is not True
        or model.get("masked_final_horizon_outputs") is not True
        or model.get("feature_selection_allowed") is not False
        or model.get("hyperparameter_search_allowed") is not False
        or model.get("innovation_enabled") is not False
        or float(model["support_threshold_multiplier"]) != 1.5
        or tube.get("evaluated_pair_residual_excluded") is not True
        or int(tube["outer_predictor_training_pair_count"]) != 7
        or tube.get("same_interval_required") is not True
        or tube.get("same_lead_sample_required") is not True
        or tube.get("feature_distance_used") is not False
        or tube.get("residual_aggregation") != "componentwise_maximum"
        or float(tube["reserve_multiplier"]) != 1.25
        or tuple(map(float, tube["physical_point_error_floors"]))
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or tube.get("planning_calibration_uses_all_eight_outer_groups") is not True
        or tube.get("tube_clipping_allowed") is not False
        or int(action["alphabet_size"]) != 11
        or int(action["maximum_unfiltered_sequence_count"]) != 14641
        or tuple(
            map(
                float,
                (
                    action["maximum_incremental_normalized_action_linf"],
                    action["maximum_total_normalized_action_abs"],
                    action["maximum_current_utilization"],
                    action["minimum_desired_applied_current_cosine"],
                    action["maximum_relative_off_basis_residual"],
                ),
            )
        )
        != (0.25, 1.0, 0.55, 0.98, 0.10)
        or action.get("require_exact_card15_issue") is not True
        or action.get("require_exact_card15_refresh") is not True
        or action.get("safe_stop_before_failed_advance") is not True
        or tuple(
            map(
                float,
                (
                    gates["maximum_R_point_error_m"],
                    gates["maximum_Z_point_error_m"],
                    gates["maximum_Ip_point_error_A"],
                    gates["maximum_vR_point_error_m_per_s"],
                    gates["maximum_vZ_point_error_m_per_s"],
                ),
            )
        )
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or tuple(
            map(
                float,
                (
                    gates["maximum_reserved_R_tube_half_width_m"],
                    gates["maximum_reserved_Z_tube_half_width_m"],
                    gates["maximum_reserved_Ip_tube_half_width_A"],
                    gates["maximum_reserved_vR_tube_half_width_m_per_s"],
                    gates["maximum_reserved_vZ_tube_half_width_m_per_s"],
                ),
            )
        )
        != (0.025, 0.025, 5000.0, 0.08, 0.08)
        or tuple(map(float, (gates["required_reserved_tube_containment_rate"], gates["required_support_rate"])))
        != (1.0, 1.0)
        or tuple(map(int, (gates["maximum_finite_exclusion_count"], gates["maximum_forbidden_input_count"])))
        != (0, 0)
        or tuple(
            map(
                int,
                (
                    formal["normal_arrival_deadline_step"],
                    formal["normal_hold_through_step"],
                    formal["weak_arrival_deadline_step"],
                    formal["weak_hold_through_step"],
                    formal["arrival_streak_steps"],
                ),
            )
        )
        != (25, 35, 27, 37, 3)
        or tuple(map(float, (formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"], formal["ip_tolerance_A"])))
        != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or int(support["training_pair_count"]) != 8
        or float(support["threshold_multiplier"]) != 1.5
        or support.get("outcome_or_residual_selection_allowed") is not False
        or tuple(
            map(
                int,
                (
                    planning["required_safe_complete_plan_count"],
                    planning["minimum_predicted_repaired_failed_baseline_count"],
                    planning["maximum_predicted_regressed_baseline_pass_count"],
                    planning["minimum_predicted_oracle_count"],
                ),
            )
        )
        != (16, 1, 0, 7)
        or float(planning["primary_independent_absolute_tolerance"]) != 1e-12
        or cfg.get("routes")
        != {
            "evidence_fail": "R8R25_INTEGRITY_FAIL_STOP",
            "model_fail": "TRAINING_CARDINALITY_MATCHED_OUTER_JACKKNIFE_TUBE_INSUFFICIENT_REDESIGN_REQUIRED",
            "planning_fail": "TRAINING_CARDINALITY_MATCHED_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED",
            "pass": "TRAINING_CARDINALITY_MATCHED_OUTER_JACKKNIFE_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED",
        }
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
    ):
        raise ValueError("R8R25 frozen contract changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = copy.copy(args)
    source_args.config = (_root() / str(cfg["source_r8r24_config"])).resolve()
    source_args.run_dir = args.r8r24_run
    source_ctx = r8r24.load_context(source_args)
    source_stage = args.r8r24_run.expanduser().resolve() / str(
        cfg["source_r8r24"]["stage_directory"]
    )
    return Context(cfg, config_path, _paths(args.run_dir), source_ctx, source_stage)


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r24"]
    paths = {
        "primary_detailed": ctx.source_stage / "analysis/primary_detailed.json",
        "primary_summary": ctx.source_stage / "analysis/primary_summary.json",
        "independent": ctx.source_stage / "analysis/independent.json",
        "final_report": ctx.source_stage / "analysis/final_report.json",
        "model_evidence": ctx.source_stage / "model/outer_fold_models.json",
        "stage_manifest": ctx.source_stage / "stage_manifest.json",
        "stage_state": ctx.source_stage / "stage_state.json",
        "compact_audit": ctx.source_stage / "analysis/compact_audit.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("R8R25 R8R24 source hash changed")
    primary, summary = _read(paths["primary_detailed"]), _read(paths["primary_summary"])
    independent, final = _read(paths["independent"]), _read(paths["final_report"])
    state, manifest, compact = (
        _read(paths["stage_state"]),
        _read(paths["stage_manifest"]),
        _read(paths["compact_audit"]),
    )
    if (
        ctx.source_stage.parent.name != str(expected["run_name"])
        or final.get("route") != str(expected["required_route"])
        or final.get("primary_independent_agreement") is not True
        or independent.get("passed") is not True
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not False
        or int(state.get("plant_step_count", -1)) != 0
        or int(state.get("new_raw_count", -1)) != 0
        or manifest.get("zero_new_tsc") is not True
        or compact.get("passed") is not True
        or primary["bank_evidence"]["feature_digest"] != str(expected["feature_digest"])
        or primary["bank_evidence"]["target_digest"] != str(expected["target_digest"])
        or int(summary["trajectory_count"]) != int(expected["trajectory_count"])
        or int(summary["origin_row_count"]) != int(expected["origin_row_count"])
        or int(summary["forecast_point_count"]) != int(expected["forecast_point_count"])
    ):
        raise ValueError("R8R25 R8R24 source outcome changed")
    transitive = r8r24._authenticate_source(ctx.source_ctx)
    if transitive.get("passed") is not True:
        raise ValueError("R8R25 transitive source authentication failed")
    return {"hashes": hashes, "route": str(final["route"]), "transitive": transitive, "passed": True}


def _outer_folds(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    pairs = tuple(sorted({str(row["pair_id"]) for row in trajectories}))
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    folds = []
    for held_pair in pairs:
        training = tuple(pair for pair in pairs if pair != held_pair)
        model = r8r23.fit_models(trajectories, training, ridge=ridge)
        held = [row for row in trajectories if str(row["pair_id"]) == held_pair]
        predictions = r8r23._cold_predictions(model, held)
        groups: list[list[np.ndarray]] = [[np.empty((0, 5)) for _ in range(count)] for count in (4, 4, 4, 15)]
        collected: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in (4, 4, 4, 15)]
        serial = []
        for trajectory in held:
            identifier = str(trajectory["trajectory_id"])
            interval_rows = []
            for interval, row in enumerate(trajectory["intervals"]):
                residual = np.abs(np.asarray(row["targets"]) - np.asarray(predictions[identifier][interval]))
                interval_rows.append(residual.tolist())
                for offset, value in enumerate(residual):
                    collected[interval][offset].append(value)
            serial.append({"trajectory_id": identifier, "absolute_residuals": interval_rows})
        for interval, offsets in enumerate(collected):
            for offset, values in enumerate(offsets):
                groups[interval][offset] = np.asarray(values, dtype=float).reshape((-1, 5))
                if not np.all(np.isfinite(groups[interval][offset])):
                    raise ValueError("R8R25 outer residual group invalid")
        support = r8r23._support_for_fold(
            trajectories,
            training,
            held_pair,
            multiplier=float(cfg["model_contract"]["support_threshold_multiplier"]),
        )
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": list(training),
                "model": model,
                "model_digest": _digest(r8r23._model_serializable(model)),
                "held_trajectories": held,
                "cold_predictions": predictions,
                "residual_groups": groups,
                "outer_residual_group_digest": _digest(serial),
                "support": support,
            }
        )
    return folds


def _tube_template(
    folds: Sequence[Mapping[str, Any]],
    calibration_pairs: Sequence[str],
    cfg: Mapping[str, Any],
) -> tuple[list[np.ndarray], dict[str, Any]]:
    selected = [fold for fold in folds if str(fold["held_pair"]) in set(calibration_pairs)]
    if len(selected) != len(set(calibration_pairs)):
        raise ValueError("R8R25 calibration pair set incomplete")
    contract = cfg["outer_jackknife_tube_contract"]
    reserve = float(contract["reserve_multiplier"])
    floor = np.asarray(contract["physical_point_error_floors"], dtype=float) / FACTORS
    templates, counts = [], []
    for interval, count in enumerate((4, 4, 4, 15)):
        values = []
        for offset in range(count):
            residuals = np.concatenate(
                [np.asarray(fold["residual_groups"][interval][offset]) for fold in selected], axis=0
            )
            if (
                residuals.ndim != 2
                or residuals.shape[1] != 5
                or len(residuals) == 0
                or not np.all(np.isfinite(residuals))
            ):
                raise ValueError("R8R25 cross-outer residual calibration invalid")
            values.append(np.maximum(reserve * np.max(residuals, axis=0), floor))
            counts.append(len(residuals))
        templates.append(np.asarray(values, dtype=float))
    serial = [value.tolist() for value in templates]
    return templates, {
        "calibration_pair_ids": sorted(map(str, calibration_pairs)),
        "calibration_pair_count": len(set(calibration_pairs)),
        "minimum_residual_record_count": min(counts),
        "maximum_residual_record_count": max(counts),
        "tube_digest": _digest(serial),
    }


def _attach_outer_tubes(
    folds: Sequence[dict[str, Any]], cfg: Mapping[str, Any]
) -> None:
    pairs = tuple(sorted(str(fold["held_pair"]) for fold in folds))
    for fold in folds:
        held = str(fold["held_pair"])
        calibration = tuple(pair for pair in pairs if pair != held)
        template, evidence = _tube_template(folds, calibration, cfg)
        tubes = {}
        for trajectory in fold["held_trajectories"]:
            tubes[str(trajectory["trajectory_id"])] = [
                template[interval][: len(row["targets"])].copy()
                for interval, row in enumerate(trajectory["intervals"])
            ]
        fold["local_tubes"] = tubes
        fold["local_tube_evidence"] = evidence


def _evaluate_model(folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    result = r8r24._evaluate_model(folds, cfg)
    for row in result["fold_rows"]:
        row["outer_jackknife_tube_evidence"] = row.pop("local_tube_evidence")
    return result


def _source_point_reproduction(
    ctx: Context, folds: Sequence[Mapping[str, Any]], evaluation: Mapping[str, Any]
) -> dict[str, Any]:
    source_primary = _read(ctx.source_stage / "analysis/primary_detailed.json")
    source_models = _read(ctx.source_stage / "model/outer_fold_models.json")
    source_by_pair = {str(row["held_pair"]): row["model"] for row in source_models["folds"]}
    current_by_pair = {str(fold["held_pair"]): r8r23._model_serializable(fold["model"]) for fold in folds}
    source_evaluation = source_primary["model_evaluation"]
    source_support = {str(row["pair_id"]): row["support"] for row in source_evaluation["fold_rows"]}
    current_support = {str(row["pair_id"]): row["support"] for row in evaluation["fold_rows"]}
    result = {
        "maximum_outer_model_absolute_difference": r8r24._maximum_difference(source_by_pair, current_by_pair),
        "maximum_point_metric_absolute_difference": r8r24._maximum_difference(
            source_evaluation["maximum_absolute_physical_error"],
            evaluation["maximum_absolute_physical_error"],
        ),
        "maximum_support_absolute_difference": r8r24._maximum_difference(source_support, current_support),
        "source_selected_predictor": source_evaluation["selected_predictor"],
        "source_innovation_enabled": bool(source_primary["innovation_enabled"]),
    }
    result["passed"] = bool(
        result["source_selected_predictor"] == "cold"
        and result["source_innovation_enabled"] is False
        and max(
            result["maximum_outer_model_absolute_difference"],
            result["maximum_point_metric_absolute_difference"],
            result["maximum_support_absolute_difference"],
        )
        <= 1e-12
    )
    if not result["passed"]:
        raise ValueError("R8R25 did not reproduce R8R24 point evidence")
    return result


def _planning_support(
    trajectories: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    pairs = tuple(sorted({str(row["pair_id"]) for row in trajectories}))
    multiplier = float(cfg["planning_support_contract"]["threshold_multiplier"])
    features, trees, thresholds, maxima = [], [], [], []
    for interval in range(4):
        by_pair = {
            pair: np.asarray(
                [row["intervals"][interval]["feature"] for row in trajectories if str(row["pair_id"]) == pair],
                dtype=float,
            )
            for pair in pairs
        }
        distances = []
        for pair, values in by_pair.items():
            other = np.concatenate([other_values for other_pair, other_values in by_pair.items() if other_pair != pair])
            distances.extend(np.min(np.linalg.norm(values[:, None] - other[None, :], axis=2), axis=1))
        all_features = np.concatenate(list(by_pair.values()))
        maximum = max(map(float, distances))
        features.append(all_features)
        trees.append(cKDTree(all_features))
        maxima.append(maximum)
        thresholds.append(multiplier * maximum)
    return {
        "features": features,
        "trees": trees,
        "training_nearest_neighbor_maxima": maxima,
        "thresholds": thresholds,
        "training_origin_count_by_interval": [len(value) for value in features],
    }


def _planning_supported(support: Mapping[str, Any], feature: np.ndarray, interval: int) -> bool:
    distance = float(support["trees"][interval].query(feature, k=1, eps=0.0, workers=1)[0])
    return distance <= float(support["thresholds"][interval]) + 1e-15


def _plan_context(
    ctx: Context,
    meta: Mapping[str, Any],
    model: Sequence[Sequence[Mapping[str, Any]]],
    tube_template: Sequence[np.ndarray],
    support: Mapping[str, Any],
) -> dict[str, Any]:
    source_ctx = ctx.source_ctx.source_ctx
    levels = r8r23._action_levels(source_ctx)
    baseline = meta["baseline_result"]
    states = r8r23._state_matrix(baseline, meta["target"])
    prefix_states = states[: DECISIONS[0] + 1]
    prefix_tubes = np.zeros_like(prefix_states)
    initial_current = np.asarray(baseline["trajectory"][DECISIONS[0]]["currents_a_tsc"], dtype=float)
    weak = math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
    deadline = int(ctx.cfg["formal_contract"]["weak_arrival_deadline_step" if weak else "normal_arrival_deadline_step"])
    endpoint = int(ctx.cfg["formal_contract"]["weak_hold_through_step" if weak else "normal_hold_through_step"])
    best_key: tuple[Any, ...] | None = None
    best: dict[str, Any] | None = None
    complete_sequences = safe_issue_count = unsupported_node_count = 0

    def visit(
        interval: int,
        current_states: np.ndarray,
        current_tubes: np.ndarray,
        current: np.ndarray,
        previous_current: np.ndarray,
        previous_q: np.ndarray,
        indices: tuple[int, ...],
        movement: float,
        maximum_current: float,
    ) -> None:
        nonlocal best_key, best, complete_sequences, safe_issue_count, unsupported_node_count
        if interval == 4:
            complete_sequences += 1
            passed, violation, integrated = r8r23._robust_formal(
                current_states, current_tubes, deadline=deadline, endpoint=endpoint, cfg=ctx.cfg
            )
            key = (not passed, violation, integrated, movement, maximum_current, indices)
            if best_key is None or key < best_key:
                best_key = key
                best = {
                    "alphabet_indices": list(indices),
                    "level_ids": [levels[index]["level_id"] for index in indices],
                    "robust_formal_pass": passed,
                    "worst_formal_margin_violation": violation,
                    "integrated_normalized_error": integrated,
                    "cumulative_normalized_action_movement": movement,
                    "maximum_predicted_current_utilization": maximum_current,
                }
            return
        feature = r8r23._planning_feature(
            current_states,
            current,
            previous_current,
            previous_q,
            np.asarray(meta["coil_limits"], dtype=float),
        )
        if not _planning_supported(support, feature, interval):
            unsupported_node_count += 1
            return
        count = 4 if interval < 3 else endpoint - DECISIONS[3]
        for level in levels:
            issue = r8r23._safe_issue(source_ctx, meta, current, level, DECISIONS[interval])
            if not bool(issue["passed"]):
                continue
            safe_issue_count += 1
            q = np.asarray(level["q"], dtype=float)
            row = {
                "interval": interval,
                "feature": feature,
                "q": q,
                "previous_q": previous_q,
                "targets": np.zeros((count, 5), dtype=float),
            }
            row["expanded"] = r8r23._expanded_row(row)
            prediction = r8r23.predict_row(model, row)
            tube = np.asarray(tube_template[interval][:count], dtype=float)
            next_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
            visit(
                interval + 1,
                np.concatenate((current_states, prediction), axis=0),
                np.concatenate((current_tubes, tube), axis=0),
                next_current,
                current,
                q,
                indices + (int(level["index"]),),
                movement + float(np.sum(np.abs(q - previous_q))),
                max(maximum_current, float(issue["predicted_current_utilization"])),
            )

    visit(0, prefix_states, prefix_tubes, initial_current, initial_current, np.zeros(2), (), 0.0, 0.0)
    return {
        "pair_id": meta["pair_id"],
        "history_member": meta["history_member"],
        "unfiltered_sequence_count": 14641,
        "safe_issue_node_count": safe_issue_count,
        "unsupported_node_count": unsupported_node_count,
        "safe_complete_sequence_count": complete_sequences,
        "selected_plan": best,
        "safe_complete_plan": best is not None,
        "predicted_formal_pass": bool(best and best["robust_formal_pass"]),
    }


def _planning_evaluation(
    ctx: Context,
    trajectories: Sequence[Mapping[str, Any]],
    folds: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    pairs = tuple(sorted(str(fold["held_pair"]) for fold in folds))
    model = r8r23.fit_models(trajectories, pairs, ridge=float(ctx.cfg["model_contract"]["ridge_penalty"]))
    tube, tube_evidence = _tube_template(folds, pairs, ctx.cfg)
    support = _planning_support(trajectories, ctx.cfg)
    plans = [_plan_context(ctx, context_meta[key], model, tube, support) for key in sorted(context_meta)]
    source = _read(ctx.source_ctx.source_ctx.r8r22_ctx.paths.analysis / "primary_detailed.json")
    baseline = {
        (str(row["pair_id"]), str(row["history_member"])): bool(row["baseline"]["formal_contract_pass"])
        for row in source["formal_authority"]["context_rows"]
    }
    repairs = regressions = oracle = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        predicted = bool(plan["predicted_formal_pass"])
        repairs += int(not baseline[key] and predicted)
        regressions += int(baseline[key] and not predicted)
        oracle += int(baseline[key] or predicted)
    complete = sum(bool(plan["safe_complete_plan"]) for plan in plans)
    gate = ctx.cfg["planning_gate"]
    passed = bool(
        complete == int(gate["required_safe_complete_plan_count"])
        and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
        and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
        and oracle >= int(gate["minimum_predicted_oracle_count"])
    )
    result = {
        "planning_model_digest": _digest(r8r23._model_serializable(model)),
        "planning_tube_evidence": tube_evidence,
        "planning_support": {
            key: support[key]
            for key in ("training_nearest_neighbor_maxima", "thresholds", "training_origin_count_by_interval")
        },
        "safe_complete_plan_count": complete,
        "predicted_repaired_failed_baseline_count": repairs,
        "predicted_regressed_baseline_pass_count": regressions,
        "predicted_baseline_plus_policy_oracle_count": oracle,
        "plans": plans,
        "passed": passed,
    }
    evidence = {
        "model": r8r23._model_serializable(model),
        "tube_template": [value.tolist() for value in tube],
        "tube_evidence": tube_evidence,
        "support": result["planning_support"],
    }
    return result, evidence


def compute(ctx: Context) -> tuple[dict[str, Any], dict[str, Any]]:
    authentication = _authenticate_source(ctx)
    trajectories, context_meta = r8r23.build_bank(ctx.source_ctx.source_ctx)
    bank = r8r23._bank_evidence(trajectories)
    expected = ctx.cfg["source_r8r24"]
    if bank["feature_digest"] != str(expected["feature_digest"]) or bank["target_digest"] != str(expected["target_digest"]):
        raise ValueError("R8R25 recomputed bank differs from R8R24")
    folds = _outer_folds(trajectories, ctx.cfg)
    _attach_outer_tubes(folds, ctx.cfg)
    model_evaluation = _evaluate_model(folds, ctx.cfg)
    source_reproduction = _source_point_reproduction(ctx, folds, model_evaluation)
    if model_evaluation["passed"]:
        planning, planning_evidence = _planning_evaluation(ctx, trajectories, folds, context_meta)
    else:
        planning = {
            "safe_complete_plan_count": 0,
            "predicted_repaired_failed_baseline_count": 0,
            "predicted_regressed_baseline_pass_count": 0,
            "predicted_baseline_plus_policy_oracle_count": 6,
            "plans": [],
            "skipped_reason": "frozen_point_support_or_outer_jackknife_tube_gate_failed",
            "passed": False,
        }
        planning_evidence = None
    scientific = bool(model_evaluation["passed"] and planning["passed"])
    route = str(ctx.cfg["routes"]["pass" if scientific else ("planning_fail" if model_evaluation["passed"] else "model_fail")])
    fold_summaries, model_folds = [], []
    for fold in folds:
        summary = {
            "held_pair": fold["held_pair"],
            "training_pairs": fold["training_pairs"],
            "model_digest": fold["model_digest"],
            "outer_residual_group_digest": fold["outer_residual_group_digest"],
            "outer_jackknife_tube_evidence": fold["local_tube_evidence"],
            "support": fold["support"],
        }
        fold_summaries.append(summary)
        model_folds.append({
            "held_pair": fold["held_pair"],
            "model": r8r23._model_serializable(fold["model"]),
            "outer_residual_group_digest": fold["outer_residual_group_digest"],
            "outer_jackknife_tube_evidence": fold["local_tube_evidence"],
        })
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "outer_fold_count": len(folds),
        "folds": fold_summaries,
        "innovation_enabled": False,
        "source_point_reproduction": source_reproduction,
        "model_evaluation": model_evaluation,
        "planning_evaluation": planning,
        "model_gate_passed": bool(model_evaluation["passed"]),
        "predicted_feasibility_gate_passed": bool(planning["passed"]),
        "scientific_gate_passed": scientific,
        "route": route,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "allowed_in_expert_dataset": False,
    }
    model_evidence = {
        "schema_version": 1,
        "stage": STAGE,
        "feature_digest": bank["feature_digest"],
        "target_digest": bank["target_digest"],
        "folds": model_folds,
        "planning_evidence": planning_evidence,
    }
    return detailed, model_evidence


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    model, planning = detailed["model_evaluation"], detailed["planning_evaluation"]
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_route": detailed["source_authentication"]["route"],
        "trajectory_count": detailed["bank_evidence"]["trajectory_count"],
        "origin_row_count": detailed["bank_evidence"]["origin_row_count"],
        "forecast_point_count": detailed["bank_evidence"]["forecast_point_count"],
        "feature_digest": detailed["bank_evidence"]["feature_digest"],
        "target_digest": detailed["bank_evidence"]["target_digest"],
        "model_evidence_sha256": model_sha,
        "innovation_enabled": False,
        "maximum_absolute_physical_error": model["maximum_absolute_physical_error"],
        "maximum_reserved_physical_tube_half_width": model["maximum_reserved_physical_tube_half_width"],
        "reserved_tube_containment_rate": model["reserved_tube_containment_rate"],
        "support_rate": model["support_rate"],
        "model_gate_passed": detailed["model_gate_passed"],
        "safe_complete_plan_count": planning["safe_complete_plan_count"],
        "predicted_repaired_failed_baseline_count": planning["predicted_repaired_failed_baseline_count"],
        "predicted_regressed_baseline_pass_count": planning["predicted_regressed_baseline_pass_count"],
        "predicted_baseline_plus_policy_oracle_count": planning["predicted_baseline_plus_policy_oracle_count"],
        "predicted_feasibility_gate_passed": detailed["predicted_feasibility_gate_passed"],
        "scientific_gate_passed": detailed["scientific_gate_passed"],
        "route": detailed["route"],
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "gate_a_qualified": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists() and any(ctx.paths.stage.iterdir()):
        raise ValueError("R8R25 primary requires an empty stage directory")
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    ctx.paths.model.mkdir(parents=True, exist_ok=True)
    detailed, model_evidence = compute(ctx)
    model_path = ctx.paths.model / "outer_fold_models.json"
    _write(model_path, model_evidence)
    model_sha = _sha(model_path)
    detailed["model_evidence_sha256"] = model_sha
    detailed_path = ctx.paths.analysis / "primary_detailed.json"
    summary_path = ctx.paths.analysis / "primary_summary.json"
    _write(detailed_path, detailed)
    _write(summary_path, _summary(detailed, model_sha))
    _write(ctx.paths.manifest, {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_r8r24_run": str(ctx.source_stage.parent),
        "source_r8r24_stage_state_sha256": ctx.cfg["source_r8r24"]["stage_state_sha256"],
        "primary_detailed_sha256": _sha(detailed_path),
        "primary_summary_sha256": _sha(summary_path),
        "model_evidence_sha256": model_sha,
        "zero_new_tsc": True,
        "all_source_trajectories_allowed_in_expert_dataset": False,
    })
    _write(ctx.paths.state, {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "primary_complete",
        "finished": False,
        "route": detailed["route"],
        "primary_detailed_sha256": _sha(detailed_path),
        "primary_summary_sha256": _sha(summary_path),
        "model_evidence_sha256": model_sha,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    })
    return _read(summary_path)


def postprocess(ctx: Context) -> dict[str, Any]:
    primary_path = ctx.paths.analysis / "primary_detailed.json"
    summary_path = ctx.paths.analysis / "primary_summary.json"
    independent_path = ctx.paths.analysis / "independent.json"
    primary, summary, independent = _read(primary_path), _read(summary_path), _read(independent_path)
    for key in (
        "passed",
        "primary_feature_agreement",
        "primary_fit_agreement",
        "primary_tube_agreement",
        "primary_plan_agreement",
        "primary_source_reproduction_agreement",
        "primary_route_agreement",
    ):
        if independent.get(key) is not True:
            raise ValueError(f"R8R25 independent agreement incomplete: {key}")
    final = {
        **summary,
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(independent_path),
        "primary_independent_agreement": True,
        "passed": bool(primary["scientific_gate_passed"]),
    }
    final_path = ctx.paths.analysis / "final_report.json"
    _write(final_path, final)
    _write(ctx.paths.state, {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "complete",
        "finished": True,
        "verdict": {"passed": final["passed"], "route": final["route"]},
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "independent_sha256": _sha(independent_path),
        "final_report_sha256": _sha(final_path),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "stop_reason": (
            "fresh_controller_sentinel_design_required"
            if final["passed"]
            else ("planning_gate_failed" if primary["model_gate_passed"] else "outer_jackknife_tube_preflight_gate_failed")
        ),
    })
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r25-command", choices=("primary", "postprocess"), required=True)
    parser.add_argument("--r8r24-run", type=Path, required=True)
    parser.add_argument("--r8r23-run", type=Path, required=True)
    for name in (
        "r8r22-run", "r8r7-run", "r8r12-run", "r8r14-run", "r8r15-run",
        "r8r19-run", "r8r20-run", "r8-run", "r8r1-output", "r8r6-run",
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run",
        "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run",
        "source-stage42r3c3-run", "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run", "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank", "q1-run", "q2-run",
        "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.r8r25_command == "primary" else postprocess(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
