#!/usr/bin/env python3
"""Structurally independent zero-TSC audit for frozen R8R25."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r24_independent_forensics as ind24,
)


ind23 = ind24.ind23
STAGE = "Stage4.2R3c3T13S24D1R14R8R25"
IDENTITY = "training_cardinality_matched_outer_jackknife_tube_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r25_training_cardinality_matched_outer_jackknife_tube_preflight"
DECISIONS = (10, 14, 18, 22)
FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=float)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def _validate_config(cfg: Mapping[str, Any]) -> None:
    root = _root().resolve()
    design = (root / str(cfg["design_document"])).resolve()
    source = (root / str(cfg["source_r8r24_config"])).resolve()
    bank, model = cfg["bank_contract"], cfg["model_contract"]
    tube, action = cfg["outer_jackknife_tube_contract"], cfg["action_contract"]
    gates, formal = cfg["model_gates"], cfg["formal_contract"]
    support, planning = cfg["planning_support_contract"], cfg["planning_gate"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source) != str(cfg["source_r8r24_config_sha256"])
        or tuple(map(int, bank["decision_task_steps"])) != DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"])) != (4, 4, 4, 15)
        or tuple(map(int, (bank["physical_pair_count"], bank["history_context_count"], bank["trajectory_count_per_context"], bank["total_trajectory_count"], bank["causal_feature_dimension"], bank["expanded_feature_dimension"]))) != (8, 16, 27, 432, 42, 133)
        or tuple(map(float, bank["visible_scales"])) != (0.03, 0.03, 10000.0)
        or float(model["ridge_penalty"]) != 1e-4
        or tuple(map(int, (model["outer_fold_count"], model["outer_training_pair_count"]))) != (8, 7)
        or float(model["support_threshold_multiplier"]) != 1.5
        or model.get("whole_pair_exclusion") is not True
        or model.get("masked_final_horizon_outputs") is not True
        or model.get("feature_selection_allowed") is not False
        or model.get("hyperparameter_search_allowed") is not False
        or model.get("innovation_enabled") is not False
        or tube.get("evaluated_pair_residual_excluded") is not True
        or int(tube["outer_predictor_training_pair_count"]) != 7
        or tube.get("same_interval_required") is not True
        or tube.get("same_lead_sample_required") is not True
        or tube.get("feature_distance_used") is not False
        or tube.get("residual_aggregation") != "componentwise_maximum"
        or float(tube["reserve_multiplier"]) != 1.25
        or tuple(map(float, tube["physical_point_error_floors"])) != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or tube.get("planning_calibration_uses_all_eight_outer_groups") is not True
        or tube.get("tube_clipping_allowed") is not False
        or tuple(map(int, (action["alphabet_size"], action["maximum_unfiltered_sequence_count"]))) != (11, 14641)
        or tuple(map(float, (action["maximum_incremental_normalized_action_linf"], action["maximum_total_normalized_action_abs"], action["maximum_current_utilization"], action["minimum_desired_applied_current_cosine"], action["maximum_relative_off_basis_residual"]))) != (0.25, 1.0, 0.55, 0.98, 0.10)
        or action.get("require_exact_card15_issue") is not True
        or action.get("require_exact_card15_refresh") is not True
        or action.get("safe_stop_before_failed_advance") is not True
        or tuple(map(float, (gates["maximum_R_point_error_m"], gates["maximum_Z_point_error_m"], gates["maximum_Ip_point_error_A"], gates["maximum_vR_point_error_m_per_s"], gates["maximum_vZ_point_error_m_per_s"]))) != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or tuple(map(float, (gates["maximum_reserved_R_tube_half_width_m"], gates["maximum_reserved_Z_tube_half_width_m"], gates["maximum_reserved_Ip_tube_half_width_A"], gates["maximum_reserved_vR_tube_half_width_m_per_s"], gates["maximum_reserved_vZ_tube_half_width_m_per_s"]))) != (0.025, 0.025, 5000.0, 0.08, 0.08)
        or tuple(map(float, (gates["required_reserved_tube_containment_rate"], gates["required_support_rate"]))) != (1.0, 1.0)
        or tuple(map(int, (gates["maximum_finite_exclusion_count"], gates["maximum_forbidden_input_count"]))) != (0, 0)
        or tuple(map(int, (formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"], formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"], formal["arrival_streak_steps"]))) != (25, 35, 27, 37, 3)
        or tuple(map(float, (formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"], formal["ip_tolerance_A"]))) != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or int(support["training_pair_count"]) != 8
        or float(support["threshold_multiplier"]) != 1.5
        or support.get("outcome_or_residual_selection_allowed") is not False
        or tuple(map(int, (planning["required_safe_complete_plan_count"], planning["minimum_predicted_repaired_failed_baseline_count"], planning["maximum_predicted_regressed_baseline_pass_count"], planning["minimum_predicted_oracle_count"]))) != (16, 1, 0, 7)
        or float(planning["primary_independent_absolute_tolerance"]) != 1e-12
        or cfg.get("routes") != {
            "evidence_fail": "R8R25_INTEGRITY_FAIL_STOP",
            "model_fail": "TRAINING_CARDINALITY_MATCHED_OUTER_JACKKNIFE_TUBE_INSUFFICIENT_REDESIGN_REQUIRED",
            "planning_fail": "TRAINING_CARDINALITY_MATCHED_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED",
            "pass": "TRAINING_CARDINALITY_MATCHED_OUTER_JACKKNIFE_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED",
        }
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
    ):
        raise ValueError("independent R8R25 frozen contract changed")


def _source_config(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return _read((_root() / str(cfg["source_r8r24_config"])).resolve())


def _source_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r24_run.expanduser().resolve() / str(cfg["source_r8r24"]["stage_directory"])


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage, expected = _source_stage(args, cfg), cfg["source_r8r24"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "independent": stage / "analysis/independent.json",
        "final_report": stage / "analysis/final_report.json",
        "model_evidence": stage / "model/outer_fold_models.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
        "compact_audit": stage / "analysis/compact_audit.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("independent R8R25 R8R24 source hash changed")
    primary, summary = _read(paths["primary_detailed"]), _read(paths["primary_summary"])
    independent, final = _read(paths["independent"]), _read(paths["final_report"])
    state, manifest, compact = _read(paths["stage_state"]), _read(paths["stage_manifest"]), _read(paths["compact_audit"])
    if (
        stage.parent.name != str(expected["run_name"])
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
    ):
        raise ValueError("independent R8R25 R8R24 outcome changed")
    transitive = ind24._authenticate(args, _source_config(cfg))
    if transitive.get("passed") is not True:
        raise ValueError("independent R8R25 transitive authentication failed")
    return {"hashes": hashes, "route": str(final["route"]), "transitive": transitive, "passed": True}


def _outer(bank: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    pairs = tuple(sorted({str(row["pair_id"]) for row in bank}))
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    folds = []
    for held_pair in pairs:
        training = tuple(pair for pair in pairs if pair != held_pair)
        model = ind23._fit(bank, training, ridge)
        held = [row for row in bank if str(row["pair_id"]) == held_pair]
        predictions = ind23._predictions(model, held)
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
        groups = [[np.asarray(values, dtype=float) for values in offsets] for offsets in collected]
        if any(value.ndim != 2 or value.shape[1] != 5 for offsets in groups for value in offsets):
            raise ValueError("independent R8R25 outer residual group invalid")
        support = ind23._support(bank, training, held_pair, float(cfg["model_contract"]["support_threshold_multiplier"]))
        folds.append({
            "held_pair": held_pair,
            "training_pairs": list(training),
            "model": model,
            "model_digest": _digest(ind23._serial(model)),
            "held": held,
            "predictions": predictions,
            "residual_groups": groups,
            "outer_residual_group_digest": _digest(serial),
            "support": support,
        })
    return folds


def _tube_template(
    folds: Sequence[Mapping[str, Any]], calibration_pairs: Sequence[str], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], dict[str, Any]]:
    allowed = set(map(str, calibration_pairs))
    selected = [fold for fold in folds if str(fold["held_pair"]) in allowed]
    if len(selected) != len(allowed):
        raise ValueError("independent R8R25 calibration set incomplete")
    contract = cfg["outer_jackknife_tube_contract"]
    floor = np.asarray(contract["physical_point_error_floors"], dtype=float) / FACTORS
    reserve = float(contract["reserve_multiplier"])
    output, counts = [], []
    for interval, count in enumerate((4, 4, 4, 15)):
        rows = []
        for offset in range(count):
            residuals = np.concatenate([np.asarray(fold["residual_groups"][interval][offset]) for fold in selected])
            if residuals.ndim != 2 or residuals.shape[1] != 5 or not np.all(np.isfinite(residuals)):
                raise ValueError("independent R8R25 tube calibration invalid")
            rows.append(np.maximum(reserve * np.max(residuals, axis=0), floor))
            counts.append(len(residuals))
        output.append(np.asarray(rows))
    return output, {
        "calibration_pair_ids": sorted(allowed),
        "calibration_pair_count": len(allowed),
        "minimum_residual_record_count": min(counts),
        "maximum_residual_record_count": max(counts),
        "tube_digest": _digest([value.tolist() for value in output]),
    }


def _attach(folds: Sequence[dict[str, Any]], cfg: Mapping[str, Any]) -> None:
    pairs = tuple(sorted(str(fold["held_pair"]) for fold in folds))
    for fold in folds:
        held = str(fold["held_pair"])
        template, evidence = _tube_template(folds, [pair for pair in pairs if pair != held], cfg)
        fold["tubes"] = {
            str(trajectory["trajectory_id"]): [
                template[interval][: len(row["targets"])].copy()
                for interval, row in enumerate(trajectory["intervals"])
            ]
            for trajectory in fold["held"]
        }
        fold["local_tube_evidence"] = evidence


def _evaluate(folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    result = ind24._evaluate(folds, cfg)
    for row in result["fold_rows"]:
        row["outer_jackknife_tube_evidence"] = row.pop("local_tube_evidence")
    return result


def _planning_support(bank: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    pairs = tuple(sorted({str(row["pair_id"]) for row in bank}))
    features, trees, maxima, thresholds = [], [], [], []
    multiplier = float(cfg["planning_support_contract"]["threshold_multiplier"])
    for interval in range(4):
        by_pair = {
            pair: np.asarray([row["intervals"][interval]["feature"] for row in bank if str(row["pair_id"]) == pair])
            for pair in pairs
        }
        distance = []
        for pair, values in by_pair.items():
            other = np.concatenate([item for key, item in by_pair.items() if key != pair])
            distance.extend(np.min(np.linalg.norm(values[:, None] - other[None], axis=2), axis=1))
        all_features = np.concatenate(list(by_pair.values()))
        maximum = max(map(float, distance))
        features.append(all_features); trees.append(cKDTree(all_features))
        maxima.append(maximum); thresholds.append(multiplier * maximum)
    return {"features": features, "trees": trees,
            "training_nearest_neighbor_maxima": maxima, "thresholds": thresholds,
            "training_origin_count_by_interval": [len(value) for value in features]}


def _supported(support: Mapping[str, Any], feature: np.ndarray, interval: int) -> bool:
    distance = float(support["trees"][interval].query(feature, k=1, eps=0.0, workers=1)[0])
    return distance <= float(support["thresholds"][interval]) + 1e-15


def _plan_one(
    cfg: Mapping[str, Any], r22_cfg: Mapping[str, Any], meta: Mapping[str, Any],
    model: Sequence[Sequence[Mapping[str, Any]]], tube: Sequence[np.ndarray],
    support: Mapping[str, Any],
) -> dict[str, Any]:
    levels = ind24._levels(r22_cfg)
    states = ind23._states(meta["baseline_result"], meta["target"])
    prefix_states, prefix_tubes = states[:11], np.zeros_like(states[:11])
    current0 = np.asarray(meta["baseline_result"]["trajectory"][10]["currents_a_tsc"])
    weak = math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
    deadline = int(cfg["formal_contract"]["weak_arrival_deadline_step" if weak else "normal_arrival_deadline_step"])
    endpoint = int(cfg["formal_contract"]["weak_hold_through_step" if weak else "normal_hold_through_step"])
    best_key, best = None, None
    complete = safe_nodes = unsupported = 0

    def visit(interval: int, current_states: np.ndarray, current_tubes: np.ndarray,
              current: np.ndarray, previous: np.ndarray, previous_q: np.ndarray,
              indices: tuple[int, ...], movement: float, maximum_current: float) -> None:
        nonlocal best_key, best, complete, safe_nodes, unsupported
        if interval == 4:
            complete += 1
            passed, violation, integrated = ind24._formal(current_states, current_tubes, deadline, endpoint, cfg)
            key = (not passed, violation, integrated, movement, maximum_current, indices)
            if best_key is None or key < best_key:
                best_key = key
                best = {"alphabet_indices": list(indices),
                        "level_ids": [levels[index]["level_id"] for index in indices],
                        "robust_formal_pass": passed,
                        "worst_formal_margin_violation": violation,
                        "integrated_normalized_error": integrated,
                        "cumulative_normalized_action_movement": movement,
                        "maximum_predicted_current_utilization": maximum_current}
            return
        feature = ind24._feature(current_states, current, previous, previous_q, np.asarray(meta["limits"]))
        if not _supported(support, feature, interval):
            unsupported += 1
            return
        count = 4 if interval < 3 else endpoint - 22
        for level in levels:
            issue = ind24._safe_issue(cfg, r22_cfg, meta, current, level, DECISIONS[interval])
            if not bool(issue["passed"]):
                continue
            safe_nodes += 1
            q = np.asarray(level["q"])
            row = {"interval": interval, "feature": feature, "q": q,
                   "previous_q": previous_q, "targets": np.zeros((count, 5))}
            row["expanded"] = ind23._expand(feature, q, previous_q)
            prediction = ind23._predict(model, row)
            next_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"])
            visit(interval + 1, np.concatenate((current_states, prediction)),
                  np.concatenate((current_tubes, tube[interval][:count])),
                  next_current, current, q, indices + (int(level["index"]),),
                  movement + float(np.sum(np.abs(q - previous_q))),
                  max(maximum_current, float(issue["predicted_current_utilization"])))

    visit(0, prefix_states, prefix_tubes, current0, current0, np.zeros(2), (), 0.0, 0.0)
    return {"pair_id": meta["pair_id"], "history_member": meta["history_member"],
            "unfiltered_sequence_count": 14641, "safe_issue_node_count": safe_nodes,
            "unsupported_node_count": unsupported, "safe_complete_sequence_count": complete,
            "selected_plan": best, "safe_complete_plan": best is not None,
            "predicted_formal_pass": bool(best and best["robust_formal_pass"])}


def _planning(
    args: argparse.Namespace, cfg: Mapping[str, Any], r23_cfg: Mapping[str, Any],
    bank: Sequence[Mapping[str, Any]], folds: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata, r22_cfg, source_stage = ind24._planning_metadata(args, r23_cfg)
    pairs = tuple(sorted(str(fold["held_pair"]) for fold in folds))
    model = ind23._fit(bank, pairs, float(cfg["model_contract"]["ridge_penalty"]))
    tube, tube_evidence = _tube_template(folds, pairs, cfg)
    support = _planning_support(bank, cfg)
    plans = [_plan_one(cfg, r22_cfg, metadata[key], model, tube, support) for key in sorted(metadata)]
    source = _read(source_stage / "analysis/primary_detailed.json")
    baseline = {(str(row["pair_id"]), str(row["history_member"])): bool(row["baseline"]["formal_contract_pass"])
                for row in source["formal_authority"]["context_rows"]}
    repairs = regressions = oracle = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        predicted = bool(plan["predicted_formal_pass"])
        repairs += int(not baseline[key] and predicted)
        regressions += int(baseline[key] and not predicted)
        oracle += int(baseline[key] or predicted)
    complete = sum(bool(plan["safe_complete_plan"]) for plan in plans)
    gate = cfg["planning_gate"]
    passed = bool(complete == int(gate["required_safe_complete_plan_count"])
                  and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
                  and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
                  and oracle >= int(gate["minimum_predicted_oracle_count"]))
    summary_support = {key: support[key] for key in
                       ("training_nearest_neighbor_maxima", "thresholds", "training_origin_count_by_interval")}
    result = {"planning_model_digest": _digest(ind23._serial(model)),
              "planning_tube_evidence": tube_evidence, "planning_support": summary_support,
              "safe_complete_plan_count": complete,
              "predicted_repaired_failed_baseline_count": repairs,
              "predicted_regressed_baseline_pass_count": regressions,
              "predicted_baseline_plus_policy_oracle_count": oracle,
              "plans": plans, "passed": passed}
    evidence = {"model": ind23._serial(model), "tube_template": [value.tolist() for value in tube],
                "tube_evidence": tube_evidence, "support": summary_support}
    return result, evidence


def audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    _validate_config(cfg)
    authentication = _authenticate(args, cfg)
    r24_cfg = _source_config(cfg)
    r23_cfg = ind24._source_config(r24_cfg)
    stage = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path, summary_path = stage / "analysis/primary_detailed.json", stage / "analysis/primary_summary.json"
    model_path = stage / "model/outer_fold_models.json"
    primary, summary, primary_models = _read(primary_path), _read(summary_path), _read(model_path)
    bank = ind23._build_bank(args, r23_cfg)
    bank_evidence = ind23._bank_evidence(bank)
    folds = _outer(bank, cfg)
    _attach(folds, cfg)
    evaluation = _evaluate(folds, cfg)

    source_primary = _read(_source_stage(args, cfg) / "analysis/primary_detailed.json")
    source_models = _read(_source_stage(args, cfg) / "model/outer_fold_models.json")
    source_by_pair = {str(row["held_pair"]): row["model"] for row in source_models["folds"]}
    current_by_pair = {str(fold["held_pair"]): ind23._serial(fold["model"]) for fold in folds}
    source_eval = source_primary["model_evaluation"]
    source_support = {str(row["pair_id"]): row["support"] for row in source_eval["fold_rows"]}
    current_support = {str(row["pair_id"]): row["support"] for row in evaluation["fold_rows"]}
    reproduction = {
        "maximum_outer_model_absolute_difference": ind23._maximum_difference(source_by_pair, current_by_pair),
        "maximum_point_metric_absolute_difference": ind23._maximum_difference(
            source_eval["maximum_absolute_physical_error"], evaluation["maximum_absolute_physical_error"]),
        "maximum_support_absolute_difference": ind23._maximum_difference(source_support, current_support),
        "source_selected_predictor": source_eval["selected_predictor"],
        "source_innovation_enabled": bool(source_primary["innovation_enabled"]),
    }
    reproduction["passed"] = bool(reproduction["source_selected_predictor"] == "cold"
                                  and reproduction["source_innovation_enabled"] is False
                                  and max(reproduction["maximum_outer_model_absolute_difference"],
                                          reproduction["maximum_point_metric_absolute_difference"],
                                          reproduction["maximum_support_absolute_difference"]) <= 1e-12)
    if not reproduction["passed"]:
        raise ValueError("independent R8R25 source reproduction failed")

    if evaluation["passed"]:
        planning, planning_evidence = _planning(args, cfg, r23_cfg, bank, folds)
    else:
        planning = {"safe_complete_plan_count": 0, "predicted_repaired_failed_baseline_count": 0,
                    "predicted_regressed_baseline_pass_count": 0,
                    "predicted_baseline_plus_policy_oracle_count": 6, "plans": [],
                    "skipped_reason": "frozen_point_support_or_outer_jackknife_tube_gate_failed",
                    "passed": False}
        planning_evidence = None
    scientific = bool(evaluation["passed"] and planning["passed"])
    route = str(cfg["routes"]["pass" if scientific else ("planning_fail" if evaluation["passed"] else "model_fail")])
    independent_models = {
        "schema_version": 1, "stage": STAGE,
        "feature_digest": bank_evidence["feature_digest"], "target_digest": bank_evidence["target_digest"],
        "folds": [{"held_pair": fold["held_pair"], "model": ind23._serial(fold["model"]),
                   "outer_residual_group_digest": fold["outer_residual_group_digest"],
                   "outer_jackknife_tube_evidence": fold["local_tube_evidence"]} for fold in folds],
        "planning_evidence": planning_evidence,
    }
    tolerance = float(cfg["planning_gate"]["primary_independent_absolute_tolerance"])
    fit_difference = ind23._maximum_difference(primary_models, independent_models)
    tube_difference = ind23._maximum_difference(primary["model_evaluation"], evaluation)
    plan_difference = ind23._maximum_difference(primary["planning_evaluation"], planning)
    reproduction_difference = ind23._maximum_difference(primary["source_point_reproduction"], reproduction)
    feature_agreement = bool(primary["bank_evidence"]["feature_digest"] == bank_evidence["feature_digest"]
                             and primary["bank_evidence"]["target_digest"] == bank_evidence["target_digest"])
    result = {
        "schema_version": 1, "stage": STAGE,
        "audit_kind": "training_cardinality_matched_outer_jackknife_tube_preflight_independent",
        "source_authentication": authentication, "bank_evidence": bank_evidence,
        "innovation_enabled": False, "source_point_reproduction": reproduction,
        "model_evaluation": evaluation, "planning_evaluation": planning, "route": route,
        "maximum_fit_absolute_difference": fit_difference,
        "maximum_tube_absolute_difference": tube_difference,
        "maximum_plan_absolute_difference": plan_difference,
        "maximum_source_reproduction_absolute_difference": reproduction_difference,
        "primary_feature_agreement": feature_agreement,
        "primary_fit_agreement": fit_difference <= tolerance,
        "primary_tube_agreement": tube_difference <= tolerance,
        "primary_plan_agreement": plan_difference <= tolerance,
        "primary_source_reproduction_agreement": reproduction_difference <= tolerance,
        "primary_route_agreement": primary.get("route") == route and summary.get("route") == route,
        "primary_outcome_agreement": bool(primary.get("model_gate_passed") is evaluation["passed"]
                                          and primary.get("predicted_feasibility_gate_passed") is planning["passed"]),
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "primary_model_evidence_sha256": _sha(model_path),
        "real_tsc_executed": False, "plant_step_count": 0, "new_raw_count": 0,
    }
    result["passed"] = all(bool(result[key]) for key in (
        "primary_feature_agreement", "primary_fit_agreement", "primary_tube_agreement",
        "primary_plan_agreement", "primary_source_reproduction_agreement",
        "primary_route_agreement", "primary_outcome_agreement"))
    if not result["passed"]:
        raise ValueError("independent R8R25 audit disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
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
    cfg = _read(args.config.expanduser().resolve())
    _validate_config(cfg)
    result = audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
