"""Frozen zero-TSC R8R24 causal local-residual-tube preflight.

The stage recomputes the accepted R8R23 cold point predictor and replaces
only its failed global maximum-residual tube with the prospectively frozen
local inner-OOF envelope.  It never launches Ray, gotsc, a controller, or a
plant step.
"""

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
    stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight
    as r8r23,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R24"
IDENTITY = "causal_local_residual_tube_receding_horizon_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r24_causal_local_residual_tube_receding_horizon_preflight"
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


def _maximum_difference(left: Any, right: Any) -> float:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return math.inf
        return max(
            (_maximum_difference(left[key], right[key]) for key in left),
            default=0.0,
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return math.inf
        return max(
            (_maximum_difference(a, b) for a, b in zip(left, right)),
            default=0.0,
        )
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    return 0.0 if left == right else math.inf


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
    source_config = (root / str(cfg["source_r8r23_config"])).resolve()
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    local = cfg["local_tube_contract"]
    action = cfg["action_contract"]
    formal = cfg["formal_contract"]
    gates = cfg["model_gates"]
    planning = cfg["planning_gate"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source_config.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source_config) != str(cfg["source_r8r23_config_sha256"])
        or tuple(map(int, bank["decision_task_steps"])) != DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"]))
        != (4, 4, 4, 15)
        or int(bank["physical_pair_count"]) != 8
        or int(bank["history_context_count"]) != 16
        or int(bank["trajectory_count_per_context"]) != 27
        or int(bank["total_trajectory_count"]) != 432
        or int(bank["causal_feature_dimension"]) != 42
        or int(bank["expanded_feature_dimension"]) != 133
        or tuple(map(float, bank["visible_scales"])) != (0.03, 0.03, 10000.0)
        or float(model["ridge_penalty"]) != 1e-4
        or int(model["outer_fold_count"]) != 8
        or int(model["nested_fold_count_per_outer"]) != 7
        or float(model["support_threshold_multiplier"]) != 1.5
        or model.get("innovation_enabled") is not False
        or model.get("whole_pair_exclusion") is not True
        or model.get("masked_final_horizon_outputs") is not True
        or model.get("feature_selection_allowed") is not False
        or model.get("hyperparameter_search_allowed") is not False
        or int(local["distance_feature_dimension"]) != 133
        or local.get("distance_metric") != "ordinary_euclidean"
        or local.get("same_interval_required") is not True
        or local.get("same_lead_sample_required") is not True
        or int(local["neighbor_count"]) != 32
        or float(local["reserve_multiplier"]) != 1.25
        or tuple(map(float, local["physical_point_error_floors"]))
        != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or local.get("include_all_kth_distance_ties") is not True
        or local.get("tube_clipping_allowed") is not False
        or int(action["alphabet_size"]) != 11
        or int(action["maximum_unfiltered_sequence_count"]) != 14641
        or float(action["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(action["maximum_total_normalized_action_abs"]) != 1.0
        or float(action["maximum_current_utilization"]) != 0.55
        or float(action["minimum_desired_applied_current_cosine"]) != 0.98
        or float(action["maximum_relative_off_basis_residual"]) != 0.10
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
        or float(gates["required_reserved_tube_containment_rate"]) != 1.0
        or float(gates["required_support_rate"]) != 1.0
        or int(gates["maximum_finite_exclusion_count"]) != 0
        or int(gates["maximum_forbidden_input_count"]) != 0
        or (
            float(formal["position_tolerance_m"]),
            float(formal["speed_tolerance_m_per_s"]),
            float(formal["ip_tolerance_A"]),
            int(formal["arrival_streak_steps"]),
        )
        != (0.03, 0.1, 10000.0, 3)
        or tuple(
            map(
                int,
                (
                    formal["normal_arrival_deadline_step"],
                    formal["normal_hold_through_step"],
                    formal["weak_arrival_deadline_step"],
                    formal["weak_hold_through_step"],
                ),
            )
        )
        != (25, 35, 27, 37)
        or formal.get("arrival_deadline_expansion_allowed") is not False
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
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
        or set(cfg["routes"]) != {"evidence_fail", "model_fail", "planning_fail", "pass"}
        or cfg["routes"]
        != {
            "evidence_fail": "R8R24_INTEGRITY_FAIL_STOP",
            "model_fail": "CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED",
            "planning_fail": "CAUSAL_LOCAL_RESIDUAL_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED",
            "pass": "CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED",
        }
    ):
        raise ValueError("R8R24 frozen contract changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = copy.copy(args)
    source_args.config = (_root() / str(cfg["source_r8r23_config"])).resolve()
    source_args.run_dir = args.r8r23_run
    source_ctx = r8r23.load_context(source_args)
    source_stage = args.r8r23_run.expanduser().resolve() / str(
        cfg["source_r8r23"]["stage_directory"]
    )
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        source_ctx=source_ctx,
        source_stage=source_stage,
    )


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r8r23"]
    paths = {
        "primary_detailed": ctx.source_stage / "analysis/primary_detailed.json",
        "primary_summary": ctx.source_stage / "analysis/primary_summary.json",
        "independent": ctx.source_stage / "analysis/independent.json",
        "final_report": ctx.source_stage / "analysis/final_report.json",
        "model_evidence": ctx.source_stage / "model/outer_fold_models.json",
        "stage_manifest": ctx.source_stage / "stage_manifest.json",
        "stage_state": ctx.source_stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("R8R24 R8R23 source hash changed")
    primary = _read(paths["primary_detailed"])
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    if (
        ctx.source_stage.parent.name != str(expected["run_name"])
        or final.get("route") != str(expected["required_route"])
        or independent.get("passed") is not True
        or final.get("primary_independent_agreement") is not True
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not False
        or int(state.get("plant_step_count", -1)) != 0
        or int(state.get("new_raw_count", -1)) != 0
        or manifest.get("zero_new_tsc") is not True
        or primary["bank_evidence"]["feature_digest"] != str(expected["feature_digest"])
        or primary["bank_evidence"]["target_digest"] != str(expected["target_digest"])
        or int(summary["trajectory_count"]) != int(expected["trajectory_count"])
        or int(summary["origin_row_count"]) != int(expected["origin_row_count"])
        or int(summary["forecast_point_count"]) != int(expected["forecast_point_count"])
    ):
        raise ValueError("R8R24 R8R23 source outcome changed")
    transitive = r8r23._authenticate_source(ctx.source_ctx)
    if transitive.get("passed") is not True:
        raise ValueError("R8R24 transitive source authentication failed")
    return {
        "hashes": hashes,
        "route": str(final["route"]),
        "transitive": transitive,
        "passed": True,
    }


def _bank_evidence(trajectories: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result = r8r23._bank_evidence(trajectories)
    if result["feature_digest"] == "" or result["target_digest"] == "":
        raise ValueError("R8R24 bank digest missing")
    return result


def _calibration_records(
    trajectories: Sequence[Mapping[str, Any]],
    training_pairs: Sequence[str],
    *,
    ridge: float,
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    pairs = tuple(sorted(map(str, training_pairs)))
    grouped: list[list[list[tuple[np.ndarray, np.ndarray]]]] = [
        [[] for _ in range(count)] for count in (4, 4, 4, 15)
    ]
    evidence = []
    for nested_held in pairs:
        nested_train = tuple(pair for pair in pairs if pair != nested_held)
        model = r8r23.fit_models(trajectories, nested_train, ridge=ridge)
        held = [row for row in trajectories if str(row["pair_id"]) == nested_held]
        predictions = r8r23._cold_predictions(model, held)
        for trajectory in held:
            identifier = str(trajectory["trajectory_id"])
            for interval, row in enumerate(trajectory["intervals"]):
                residual = np.abs(
                    np.asarray(row["targets"], dtype=float)
                    - np.asarray(predictions[identifier][interval], dtype=float)
                )
                for offset, value in enumerate(residual):
                    grouped[interval][offset].append(
                        (np.asarray(row["expanded"], dtype=float), value)
                    )
        evidence.append(
            {
                "held_pair": nested_held,
                "training_pairs": list(nested_train),
                "model_digest": _digest(r8r23._model_serializable(model)),
            }
        )
    records: list[list[dict[str, Any]]] = []
    for interval in grouped:
        offsets = []
        for values in interval:
            features = np.asarray([row[0] for row in values], dtype=float)
            residuals = np.asarray([row[1] for row in values], dtype=float)
            if (
                len(features) < 32
                or features.shape[1:] != (133,)
                or residuals.shape != (len(features), 5)
                or not np.all(np.isfinite(features))
                or not np.all(np.isfinite(residuals))
            ):
                raise ValueError("R8R24 local calibration records invalid")
            offsets.append(
                {
                    "features": features,
                    "residuals": residuals,
                    "tree": cKDTree(features),
                }
            )
        records.append(offsets)
    return records, evidence


def _neighbor_indices(record: Mapping[str, Any], query: np.ndarray, k: int) -> np.ndarray:
    features = np.asarray(record["features"], dtype=float)
    distances, _ = record["tree"].query(query, k=k, eps=0.0, workers=1)
    kth = float(np.asarray(distances, dtype=float).reshape(-1)[-1])
    candidates = np.asarray(
        record["tree"].query_ball_point(query, r=kth + max(1e-15, abs(kth) * 1e-14)),
        dtype=int,
    )
    exact = np.linalg.norm(features - query[None, :], axis=1)
    exact_kth = float(np.partition(exact, k - 1)[k - 1])
    selected = np.flatnonzero(exact <= exact_kth + max(1e-15, abs(exact_kth) * 1e-14))
    if len(selected) < k or not set(map(int, selected)).issubset(set(map(int, candidates))):
        raise ValueError("R8R24 local neighbor tie selection invalid")
    return selected


def _query_tube(
    calibration: Sequence[Sequence[Mapping[str, Any]]],
    row: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> tuple[np.ndarray, list[int]]:
    interval = int(row["interval"])
    count = len(row["targets"])
    query = np.asarray(row["expanded"], dtype=float).reshape(133)
    local = cfg["local_tube_contract"]
    k = int(local["neighbor_count"])
    reserve = float(local["reserve_multiplier"])
    floor = np.asarray(local["physical_point_error_floors"], dtype=float) / FACTORS
    output, counts = [], []
    for offset in range(count):
        record = calibration[interval][offset]
        selected = _neighbor_indices(record, query, k)
        residual = np.max(np.asarray(record["residuals"])[selected], axis=0)
        output.append(np.maximum(reserve * residual, floor))
        counts.append(len(selected))
    value = np.asarray(output, dtype=float)
    if value.shape != (count, 5) or not np.all(np.isfinite(value)):
        raise ValueError("R8R24 local tube query invalid")
    return value, counts


def _local_tubes(
    calibration: Sequence[Sequence[Mapping[str, Any]]],
    trajectories: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[dict[str, list[np.ndarray]], dict[str, Any]]:
    output: dict[str, list[np.ndarray]] = {}
    all_counts = []
    serial = []
    for trajectory in trajectories:
        identifier = str(trajectory["trajectory_id"])
        tubes = []
        for row in trajectory["intervals"]:
            tube, counts = _query_tube(calibration, row, cfg)
            tubes.append(tube)
            all_counts.extend(counts)
        output[identifier] = tubes
        serial.append(
            {"trajectory_id": identifier, "tubes": [value.tolist() for value in tubes]}
        )
    return output, {
        "tube_digest": _digest(serial),
        "minimum_neighbor_count_after_ties": min(all_counts),
        "maximum_neighbor_count_after_ties": max(all_counts),
        "query_count": len(all_counts),
    }


def _outer_fold(
    trajectories: Sequence[Mapping[str, Any]],
    all_pairs: Sequence[str],
    held_pair: str,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    training_pairs = tuple(pair for pair in all_pairs if pair != held_pair)
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    model = r8r23.fit_models(trajectories, training_pairs, ridge=ridge)
    calibration, nested = _calibration_records(
        trajectories, training_pairs, ridge=ridge
    )
    held = [row for row in trajectories if str(row["pair_id"]) == held_pair]
    cold = r8r23._cold_predictions(model, held)
    tubes, local_evidence = _local_tubes(calibration, held, cfg)
    support = r8r23._support_for_fold(
        trajectories,
        training_pairs,
        held_pair,
        multiplier=float(cfg["model_contract"]["support_threshold_multiplier"]),
    )
    training_features = [
        np.asarray(
            [
                trajectory["intervals"][interval]["feature"]
                for trajectory in trajectories
                if str(trajectory["pair_id"]) in set(training_pairs)
            ],
            dtype=float,
        )
        for interval in range(4)
    ]
    return {
        "held_pair": held_pair,
        "training_pairs": list(training_pairs),
        "model": model,
        "model_digest": _digest(r8r23._model_serializable(model)),
        "calibration": calibration,
        "nested_fit_evidence": nested,
        "local_tube_evidence": local_evidence,
        "held_trajectories": held,
        "cold_predictions": cold,
        "local_tubes": tubes,
        "support": support,
        "training_features": training_features,
    }


def _source_point_reproduction(
    ctx: Context,
    folds: Sequence[Mapping[str, Any]],
    model_evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    source_primary = _read(ctx.source_stage / "analysis/primary_detailed.json")
    source_models = _read(ctx.source_stage / "model/outer_fold_models.json")
    source_by_pair = {
        str(row["held_pair"]): row for row in source_models["folds"]
    }
    current_models = {
        str(fold["held_pair"]): r8r23._model_serializable(fold["model"])
        for fold in folds
    }
    model_difference = _maximum_difference(
        {pair: source_by_pair[pair]["model"] for pair in sorted(source_by_pair)},
        {pair: current_models[pair] for pair in sorted(current_models)},
    )
    source_evaluation = source_primary["model_evaluation"]
    point_difference = _maximum_difference(
        source_evaluation["maximum_absolute_physical_error"],
        model_evaluation["maximum_absolute_physical_error"],
    )
    source_support = {
        str(row["pair_id"]): row["support"]
        for row in source_evaluation["fold_rows"]
    }
    current_support = {
        str(row["pair_id"]): row["support"]
        for row in model_evaluation["fold_rows"]
    }
    support_difference = _maximum_difference(source_support, current_support)
    passed = bool(
        source_primary.get("adaptation_enabled") is False
        and source_evaluation.get("selected_predictor") == "cold"
        and model_evaluation.get("selected_predictor") == "cold"
        and model_difference <= 1e-12
        and point_difference <= 1e-12
        and support_difference <= 1e-12
    )
    if not passed:
        raise ValueError("R8R24 did not exactly reproduce the frozen R8R23 cold point model")
    return {
        "source_selected_predictor": source_evaluation["selected_predictor"],
        "source_innovation_enabled": bool(source_primary["adaptation_enabled"]),
        "maximum_outer_model_absolute_difference": model_difference,
        "maximum_point_metric_absolute_difference": point_difference,
        "maximum_support_absolute_difference": support_difference,
        "passed": True,
    }


def _evaluate_model(
    folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    maxima = np.zeros(5, dtype=float)
    tube_maxima = np.zeros(5, dtype=float)
    contained = total = finite = support_pass = support_total = 0
    fold_rows = []
    for fold in folds:
        fold_max = np.zeros(5, dtype=float)
        fold_tube_max = np.zeros(5, dtype=float)
        fold_contained = fold_total = 0
        for trajectory in fold["held_trajectories"]:
            identifier = str(trajectory["trajectory_id"])
            for interval, row in enumerate(trajectory["intervals"]):
                actual = np.asarray(row["targets"], dtype=float)
                predicted = np.asarray(fold["cold_predictions"][identifier][interval])
                tube = np.asarray(fold["local_tubes"][identifier][interval])
                residual = np.abs(actual - predicted)
                physical = residual * FACTORS[None, :]
                physical_tube = tube * FACTORS[None, :]
                fold_max = np.maximum(fold_max, np.max(physical, axis=0))
                fold_tube_max = np.maximum(
                    fold_tube_max, np.max(physical_tube, axis=0)
                )
                inside = residual <= tube + 1e-15
                fold_contained += int(np.count_nonzero(inside))
                fold_total += int(inside.size)
                finite += int(
                    not np.all(np.isfinite(actual))
                    or not np.all(np.isfinite(predicted))
                    or not np.all(np.isfinite(tube))
                )
        maxima = np.maximum(maxima, fold_max)
        tube_maxima = np.maximum(tube_maxima, fold_tube_max)
        contained += fold_contained
        total += fold_total
        support_pass += sum(map(int, fold["support"]["pass_counts"]))
        support_total += sum(map(int, fold["support"]["row_counts"]))
        fold_rows.append(
            {
                "pair_id": fold["held_pair"],
                "maximum_absolute_physical_error": fold_max.tolist(),
                "maximum_reserved_physical_tube_half_width": fold_tube_max.tolist(),
                "reserved_tube_contained_component_count": fold_contained,
                "reserved_tube_component_count": fold_total,
                "reserved_tube_containment_rate": fold_contained / fold_total,
                "support": fold["support"],
                "local_tube_evidence": fold["local_tube_evidence"],
            }
        )
    gate = cfg["model_gates"]
    point = bool(
        maxima[0] <= float(gate["maximum_R_point_error_m"]) + 1e-15
        and maxima[1] <= float(gate["maximum_Z_point_error_m"]) + 1e-15
        and maxima[2] <= float(gate["maximum_Ip_point_error_A"]) + 1e-12
        and maxima[3] <= float(gate["maximum_vR_point_error_m_per_s"]) + 1e-15
        and maxima[4] <= float(gate["maximum_vZ_point_error_m_per_s"]) + 1e-15
    )
    cap = bool(
        tube_maxima[0] <= float(gate["maximum_reserved_R_tube_half_width_m"]) + 1e-15
        and tube_maxima[1] <= float(gate["maximum_reserved_Z_tube_half_width_m"]) + 1e-15
        and tube_maxima[2] <= float(gate["maximum_reserved_Ip_tube_half_width_A"]) + 1e-12
        and tube_maxima[3]
        <= float(gate["maximum_reserved_vR_tube_half_width_m_per_s"]) + 1e-15
        and tube_maxima[4]
        <= float(gate["maximum_reserved_vZ_tube_half_width_m_per_s"]) + 1e-15
    )
    containment = contained / total
    support_rate = support_pass / support_total
    containment_passed = bool(
        containment
        >= float(gate["required_reserved_tube_containment_rate"]) - 1e-15
    )
    support_passed = bool(
        support_rate >= float(gate["required_support_rate"]) - 1e-15
    )
    passed = bool(
        point
        and cap
        and containment_passed
        and support_passed
        and finite <= int(gate["maximum_finite_exclusion_count"])
    )
    return {
        "selected_predictor": "cold",
        "maximum_absolute_physical_error": maxima.tolist(),
        "maximum_reserved_physical_tube_half_width": tube_maxima.tolist(),
        "reserved_tube_contained_component_count": contained,
        "reserved_tube_component_count": total,
        "reserved_tube_containment_rate": containment,
        "support_pass_count": support_pass,
        "support_row_count": support_total,
        "support_rate": support_rate,
        "finite_exclusion_count": finite,
        "forbidden_input_count": 0,
        "point_error_gate_passed": point,
        "tube_cap_gate_passed": cap,
        "reserved_tube_containment_gate_passed": containment_passed,
        "support_gate_passed": support_passed,
        "fold_rows": fold_rows,
        "passed": passed,
    }


def _query_supported(fold: Mapping[str, Any], feature: np.ndarray, interval: int) -> bool:
    distance = float(
        np.min(
            np.linalg.norm(
                np.asarray(fold["training_features"][interval]) - feature[None, :],
                axis=1,
            )
        )
    )
    return distance <= float(fold["support"]["thresholds"][interval]) + 1e-15


def _plan_context(
    ctx: Context, meta: Mapping[str, Any], fold: Mapping[str, Any]
) -> dict[str, Any]:
    levels = r8r23._action_levels(ctx.source_ctx)
    model = fold["model"]
    baseline = meta["baseline_result"]
    states = r8r23._state_matrix(baseline, meta["target"])
    prefix_states = states[: DECISIONS[0] + 1]
    prefix_tubes = np.zeros_like(prefix_states)
    trajectory = baseline["trajectory"]
    initial_current = np.asarray(
        trajectory[DECISIONS[0]]["currents_a_tsc"], dtype=float
    )
    horizon = int(meta["horizon"])
    deadline = (
        int(ctx.cfg["formal_contract"]["weak_arrival_deadline_step"])
        if math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
        else int(ctx.cfg["formal_contract"]["normal_arrival_deadline_step"])
    )
    endpoint = (
        int(ctx.cfg["formal_contract"]["weak_hold_through_step"])
        if math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
        else int(ctx.cfg["formal_contract"]["normal_hold_through_step"])
    )
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
                current_states,
                current_tubes,
                deadline=deadline,
                endpoint=endpoint,
                cfg=ctx.cfg,
            )
            key = (
                not passed,
                violation,
                integrated,
                movement,
                maximum_current,
                indices,
            )
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
        if not _query_supported(fold, feature, interval):
            unsupported_node_count += 1
            return
        count = 4 if interval < 3 else endpoint - DECISIONS[3]
        for level in levels:
            issue = r8r23._safe_issue(
                ctx.source_ctx, meta, current, level, DECISIONS[interval]
            )
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
            tube, _ = _query_tube(fold["calibration"], row, ctx.cfg)
            next_states = np.concatenate((current_states, prediction), axis=0)
            next_tubes = np.concatenate((current_tubes, tube), axis=0)
            next_current = np.asarray(
                issue["nominal_issue_readback_current_a_tsc"], dtype=float
            )
            visit(
                interval + 1,
                next_states,
                next_tubes,
                next_current,
                current,
                q,
                indices + (int(level["index"]),),
                movement + float(np.sum(np.abs(q - previous_q))),
                max(maximum_current, float(issue["predicted_current_utilization"])),
            )

    visit(
        0,
        prefix_states,
        prefix_tubes,
        initial_current,
        initial_current,
        np.zeros(2, dtype=float),
        (),
        0.0,
        0.0,
    )
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
    folds: Sequence[Mapping[str, Any]],
    context_meta: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    by_pair = {str(fold["held_pair"]): fold for fold in folds}
    plans = [
        _plan_context(ctx, context_meta[key], by_pair[key[0]])
        for key in sorted(context_meta)
    ]
    source = _read(ctx.source_ctx.r8r22_ctx.paths.analysis / "primary_detailed.json")
    baseline = {
        (str(row["pair_id"]), str(row["history_member"])): bool(
            row["baseline"]["formal_contract_pass"]
        )
        for row in source["formal_authority"]["context_rows"]
    }
    repairs = regressions = oracle = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        predicted = bool(plan["predicted_formal_pass"])
        repairs += int(not baseline[key] and predicted)
        regressions += int(baseline[key] and not predicted)
        oracle += int(baseline[key] or predicted)
    gate = ctx.cfg["planning_gate"]
    complete = sum(bool(row["safe_complete_plan"]) for row in plans)
    passed = bool(
        complete == int(gate["required_safe_complete_plan_count"])
        and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
        and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
        and oracle >= int(gate["minimum_predicted_oracle_count"])
    )
    return {
        "safe_complete_plan_count": complete,
        "predicted_repaired_failed_baseline_count": repairs,
        "predicted_regressed_baseline_pass_count": regressions,
        "predicted_baseline_plus_policy_oracle_count": oracle,
        "plans": plans,
        "passed": passed,
    }


def compute(ctx: Context) -> tuple[dict[str, Any], dict[str, Any]]:
    authentication = _authenticate_source(ctx)
    trajectories, context_meta = r8r23.build_bank(ctx.source_ctx)
    bank = _bank_evidence(trajectories)
    expected = ctx.cfg["source_r8r23"]
    if (
        bank["feature_digest"] != str(expected["feature_digest"])
        or bank["target_digest"] != str(expected["target_digest"])
    ):
        raise ValueError("R8R24 recomputed bank differs from R8R23")
    pairs = tuple(sorted({str(row["pair_id"]) for row in trajectories}))
    folds = [_outer_fold(trajectories, pairs, held, ctx.cfg) for held in pairs]
    model_evaluation = _evaluate_model(folds, ctx.cfg)
    source_point_reproduction = _source_point_reproduction(
        ctx, folds, model_evaluation
    )
    planning = (
        _planning_evaluation(ctx, folds, context_meta)
        if model_evaluation["passed"]
        else {
            "safe_complete_plan_count": 0,
            "predicted_repaired_failed_baseline_count": 0,
            "predicted_regressed_baseline_pass_count": 0,
            "predicted_baseline_plus_policy_oracle_count": 6,
            "plans": [],
            "skipped_reason": "frozen_point_support_or_local_tube_gate_failed",
            "passed": False,
        }
    )
    scientific = bool(model_evaluation["passed"] and planning["passed"])
    route = str(
        ctx.cfg["routes"][
            "pass"
            if scientific
            else ("planning_fail" if model_evaluation["passed"] else "model_fail")
        ]
    )
    fold_summaries = []
    model_folds = []
    for fold in folds:
        fold_summaries.append(
            {
                "held_pair": fold["held_pair"],
                "training_pairs": fold["training_pairs"],
                "model_digest": fold["model_digest"],
                "nested_fit_evidence": fold["nested_fit_evidence"],
                "local_tube_evidence": fold["local_tube_evidence"],
                "support": fold["support"],
            }
        )
        model_folds.append(
            {
                "held_pair": fold["held_pair"],
                "model": r8r23._model_serializable(fold["model"]),
                "nested_fit_evidence": fold["nested_fit_evidence"],
                "local_tube_evidence": fold["local_tube_evidence"],
            }
        )
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "bank_evidence": bank,
        "outer_fold_count": len(folds),
        "folds": fold_summaries,
        "innovation_enabled": False,
        "innovation_status": "disabled_by_frozen_r8r24_design",
        "source_point_reproduction": source_point_reproduction,
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
    }
    return detailed, model_evidence


def _summary(detailed: Mapping[str, Any], model_sha: str) -> dict[str, Any]:
    model = detailed["model_evaluation"]
    planning = detailed["planning_evaluation"]
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
        "maximum_reserved_physical_tube_half_width": model[
            "maximum_reserved_physical_tube_half_width"
        ],
        "reserved_tube_containment_rate": model[
            "reserved_tube_containment_rate"
        ],
        "support_rate": model["support_rate"],
        "model_gate_passed": detailed["model_gate_passed"],
        "safe_complete_plan_count": planning["safe_complete_plan_count"],
        "predicted_repaired_failed_baseline_count": planning[
            "predicted_repaired_failed_baseline_count"
        ],
        "predicted_regressed_baseline_pass_count": planning[
            "predicted_regressed_baseline_pass_count"
        ],
        "predicted_baseline_plus_policy_oracle_count": planning[
            "predicted_baseline_plus_policy_oracle_count"
        ],
        "predicted_feasibility_gate_passed": detailed[
            "predicted_feasibility_gate_passed"
        ],
        "scientific_gate_passed": detailed["scientific_gate_passed"],
        "route": detailed["route"],
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "gate_a_qualified": False,
    }


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists() and any(ctx.paths.stage.iterdir()):
        raise ValueError("R8R24 primary requires an empty stage directory")
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    ctx.paths.model.mkdir(parents=True, exist_ok=True)
    detailed, model_evidence = compute(ctx)
    model_path = ctx.paths.model / "outer_fold_models.json"
    _write(model_path, model_evidence)
    model_sha = _sha(model_path)
    detailed["model_evidence_sha256"] = model_sha
    detailed_path = ctx.paths.analysis / "primary_detailed.json"
    _write(detailed_path, detailed)
    summary = _summary(detailed, model_sha)
    summary_path = ctx.paths.analysis / "primary_summary.json"
    _write(summary_path, summary)
    _write(
        ctx.paths.manifest,
        {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "config_path": str(ctx.config_path),
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "source_r8r23_run": str(ctx.source_stage.parent),
            "source_r8r23_stage_state_sha256": ctx.cfg["source_r8r23"][
                "stage_state_sha256"
            ],
            "primary_detailed_sha256": _sha(detailed_path),
            "primary_summary_sha256": _sha(summary_path),
            "model_evidence_sha256": model_sha,
            "zero_new_tsc": True,
            "all_source_trajectories_allowed_in_expert_dataset": False,
        },
    )
    _write(
        ctx.paths.state,
        {
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
        },
    )
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    primary_path = ctx.paths.analysis / "primary_detailed.json"
    summary_path = ctx.paths.analysis / "primary_summary.json"
    independent_path = ctx.paths.analysis / "independent.json"
    independent = _read(independent_path)
    primary = _read(primary_path)
    summary = _read(summary_path)
    if (
        independent.get("passed") is not True
        or independent.get("primary_feature_agreement") is not True
        or independent.get("primary_fit_agreement") is not True
        or independent.get("primary_tube_agreement") is not True
        or independent.get("primary_plan_agreement") is not True
        or independent.get("primary_source_reproduction_agreement") is not True
        or independent.get("primary_route_agreement") is not True
    ):
        raise ValueError("R8R24 independent agreement is incomplete")
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
    _write(
        ctx.paths.state,
        {
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
                else (
                    "planning_gate_failed"
                    if primary["model_gate_passed"]
                    else "local_tube_preflight_gate_failed"
                )
            ),
        },
    )
    return final


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
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
    parser.add_argument("--command", choices=("primary", "postprocess"), required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = run_primary(ctx) if args.command == "primary" else postprocess(ctx)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
