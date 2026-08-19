#!/usr/bin/env python3
"""Frozen five-context rerun of the two ID-2Z8 model classes."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import rgeo_zgeo_1ms_id2z8_small_sequence_model as base  # noqa: E402


CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2z10_five_context_model.json"
CONFIG_SHA256 = "abfe3316f877119720864ca2f867646b386240e148e62a2a1db0a6701dcd9315"
SCHEMA = "rgeo-zgeo-1ms-id2z10-five-context-model-result-v1"
CONTEXT_IDS = ("state49", "state53", "state57", "state61", "state65")


def require(stage: dict[str, Any]) -> None:
    expected_contexts = [
        {"context_id": "state49", "decision_state_index": 49,
         "source": "id2z8_inherited"},
        {"context_id": "state53", "decision_state_index": 53,
         "source": "id2z8_inherited"},
        {"context_id": "state57", "decision_state_index": 57,
         "source": "id2z8_inherited"},
        {"context_id": "state61", "decision_state_index": 61,
         "source": "id2z9_round_d"},
        {"context_id": "state65", "decision_state_index": 65,
         "source": "id2z9_round_e"},
    ]
    if (stage.get("schema_version")
            != "rgeo-zgeo-1ms-id2z10-five-context-model-v1"
            or stage.get("identity") != stage.get("schema_version")
            or stage.get("stage") != "ID-2Z10"
            or stage.get("decision_contexts") != expected_contexts
            or stage.get("arm_ids") != ["hold4", "b4", "f4", "b2f2", "f2b2"]
            or stage.get("nonhold_arm_ids") != ["b4", "f4", "b2f2", "f2b2"]
            or stage.get("history_steps") != 8
            or stage.get("whole_context_folds") is not True
            or stage.get("sibling_split_forbidden") is not True
            or stage.get("future_actual_current_forbidden") is not True
            or stage.get("future_truth_forbidden") is not True
            or stage.get("critical_replay_fit_and_evaluation_weight") != 0
            or stage.get("calibration_holdout_expert_bc_dagger_rl_weight") != 0):
        raise base.InputIntegrityError("frozen stage contract changed")
    if stage.get("candidate_specs") != [
            {"candidate_id": "stable_local_memory",
             "stable_action_memory_poles": [0.0, 0.5, 0.8, 0.95],
             "fold_local_context_pca_dimensions": 1, "ridge_lambda": 1.0,
             "intercept": False},
            {"candidate_id": "stable_local_memory_plus_gru4",
             "backbone": "stable_local_memory", "hidden_size": 4, "layers": 1,
             "seeds": [17, 29, 43], "epochs": 300, "learning_rate": 0.01,
             "weight_decay": 0.01, "residual_bound_scaled": [1.0, 1.0, 1.0]}]:
        raise base.InputIntegrityError("candidate capacity changed")
    if stage.get("selection_gates") != {
            "maximum_response_nrmse_each_fold": 0.75,
            "maximum_r_p95_m": 0.0003, "maximum_z_p95_m": 0.0003,
            "maximum_ip_p95_a": 50.0,
            "minimum_peak_vector_cosine_each_cell_exclusive": 0.0,
            "maximum_best_arm_normalized_score_regret_each_fold": 0.1,
            "nrmse_tie_margin": 0.01, "tie_preference": "stable_local_memory",
            "all_five_folds_required": True, "all_predictions_finite": True}:
        raise base.InputIntegrityError("selection gates changed")
    if stage.get("data_contract") != {
            "fit_weight_windows": 25, "independent_causal_contexts": 5,
            "siblings_per_context": 5, "nonhold_evaluation_cells": 20,
            "matched_hold_response_baseline": True,
            "models_fit_only_on_training_contexts": True,
            "normalization_and_pca_fold_local": True,
            "model_artifact_only_if_eligible": True, "development_only": True}:
        raise base.InputIntegrityError("data contract changed")


def load(path: Path = CONFIG) -> tuple[dict[str, Any], list[base.Context]]:
    path = base.inside(path, "stage config")
    if path != CONFIG.resolve() or base.sha256(path) != CONFIG_SHA256:
        raise base.InputIntegrityError("stage config identity mismatch")
    stage = base.load_json(path)
    require(stage)
    for value in stage["evidence"].values():
        evidence_path = base.inside(ROOT / value["path"], "evidence")
        if base.sha256(evidence_path) != value["sha256"]:
            raise base.InputIntegrityError(f"evidence hash mismatch: {evidence_path}")
    old_config = ROOT / stage["evidence"]["id2z8_config"]["path"]
    _, old_contexts = base.load(old_config)
    result = base.load_json(ROOT / stage["evidence"]["id2z9_result"]["path"])
    audit = base.load_json(ROOT / stage["evidence"]["id2z9_independent"]["path"])
    if (result.get("route")
            != stage["evidence"]["id2z9_result"]["required_route"]
            or result.get("passed") is not True or audit.get("audit_passed") is not True):
        raise base.InputIntegrityError("ID2Z9 evidence is ineligible")
    contexts = list(old_contexts)
    for spec in stage["decision_contexts"][3:]:
        context_id = spec["context_id"]
        decision = int(spec["decision_state_index"])
        rows: dict[str, dict[str, Any]] = {}
        for arm in stage["arm_ids"]:
            cell = stage["new_context_cells"][context_id][arm]
            cell_path = base.inside(ROOT / cell["path"], f"{context_id}:{arm}")
            if base.sha256(cell_path) != cell["sha256"]:
                raise base.InputIntegrityError(f"cell hash mismatch: {context_id}:{arm}")
            row = base.load_json(cell_path)
            if (row.get("arm_id") != arm or row.get("passed") is not True
                    or int(row.get("fit_weight", 0)) != 1
                    or len(row.get("states", [])) <= decision
                    or len(row.get("actions", [])) < decision):
                raise base.InputIntegrityError(f"cell contract: {context_id}:{arm}")
            rows[arm] = row
        if not all(base._same_prefix(rows["hold4"], rows[arm], decision)
                   for arm in stage["arm_ids"]):
            raise base.InputIntegrityError(f"sibling prefix mismatch: {context_id}")
        horizons = list(stage["response_horizons_by_context"][context_id])
        if decision + horizons[-1] >= len(rows["hold4"]["states"]):
            raise base.InputIntegrityError(f"terminal mismatch: {context_id}")
        contexts.append(base.Context(context_id, decision, rows, horizons))
    if tuple(value.context_id for value in contexts) != CONTEXT_IDS:
        raise base.InputIntegrityError("context order changed")
    return stage, contexts


def terminal_score(stage: dict[str, Any], context: base.Context, arm: str,
                   prediction: np.ndarray | None) -> float:
    hold = context.rows["hold4"]["states"]
    truth = context.rows[arm]["states"]
    source = base.state_y(truth[0])
    states: dict[int, np.ndarray] = {}
    for offset, horizon in enumerate(context.horizons):
        index = context.decision + horizon
        states[index] = (base.state_y(truth[index]) if prediction is None else
                         base.state_y(hold[index]) + prediction[offset] * base.SCALES)
    distances, speeds, ipf = [], [], []
    for index in stage["terminal_state_indices_by_context"][context.context_id]:
        current, previous = states[index], states[index - 1]
        distances.append(float(np.linalg.norm(current[:2] - source[:2])))
        speeds.append(float(np.linalg.norm(current[:2] - previous[:2]) / 0.001))
        ipf.append(abs(float(current[2] - source[2])) / abs(float(source[2])))
    return max(max(distances) / 0.025, max(speeds) / 0.1, max(ipf) / 0.05)


def fold_metrics(stage: dict[str, Any], context: base.Context,
                 predictions: dict[str, np.ndarray],
                 spread: dict[str, np.ndarray] | None) -> dict[str, Any]:
    truths = {arm: base.response(context, arm) for arm in predictions}
    error = np.concatenate([predictions[arm] - truths[arm] for arm in predictions])
    truth = np.concatenate(list(truths.values()))
    nrmse = math.sqrt(float(np.sum(error * error) / max(np.sum(truth * truth), 1e-18)))
    physical = np.abs(error * base.SCALES)
    cosines: dict[str, float] = {}
    for arm in predictions:
        actual = truths[arm][:, :2] * base.SCALES[:2]
        predicted = predictions[arm][:, :2] * base.SCALES[:2]
        peak = int(np.argmax(np.linalg.norm(actual, axis=1)))
        denominator = np.linalg.norm(actual[peak]) * np.linalg.norm(predicted[peak])
        cosines[arm] = (float(actual[peak] @ predicted[peak] / denominator)
                        if denominator > 1e-18 else -1.0)
    true_scores = {arm: terminal_score(stage, context, arm, None) for arm in predictions}
    predicted_scores = {
        arm: terminal_score(stage, context, arm, predictions[arm]) for arm in predictions}
    predicted_best = min(predicted_scores, key=lambda arm: (predicted_scores[arm], arm))
    true_best = min(true_scores, key=lambda arm: (true_scores[arm], arm))
    value = {
        "context_id": context.context_id, "response_nrmse": nrmse,
        "r_p95_m": float(np.quantile(physical[:, 0], 0.95)),
        "z_p95_m": float(np.quantile(physical[:, 1], 0.95)),
        "ip_p95_a": float(np.quantile(physical[:, 2], 0.95)),
        "r_max_m": float(physical[:, 0].max()),
        "z_max_m": float(physical[:, 1].max()),
        "ip_max_a": float(physical[:, 2].max()),
        "peak_vector_cosines": cosines,
        "minimum_peak_vector_cosine": min(cosines.values()),
        "true_terminal_scores": true_scores,
        "predicted_terminal_scores": predicted_scores,
        "true_best_arm": true_best, "predicted_best_arm": predicted_best,
        "best_arm_normalized_score_regret": float(
            true_scores[predicted_best] - true_scores[true_best]),
    }
    if spread:
        value["maximum_seed_std_scaled"] = float(max(
            np.max(spread[arm]) for arm in spread))
    return value


def eligible(folds: Sequence[dict[str, Any]], gates: dict[str, Any]) -> bool:
    return bool(len(folds) == 5 and all(
        value["response_nrmse"] <= gates["maximum_response_nrmse_each_fold"]
        and value["r_p95_m"] <= gates["maximum_r_p95_m"]
        and value["z_p95_m"] <= gates["maximum_z_p95_m"]
        and value["ip_p95_a"] <= gates["maximum_ip_p95_a"]
        and value["minimum_peak_vector_cosine"]
        > gates["minimum_peak_vector_cosine_each_cell_exclusive"]
        and value["best_arm_normalized_score_regret"]
        <= gates["maximum_best_arm_normalized_score_regret_each_fold"]
        for value in folds))


def execute(path: Path, source_revision: str,
            output: Path | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    stage, contexts = load(path)
    basis = base.action_basis(contexts)
    candidates, records = [], {}
    for candidate_id in ("stable_local_memory", "stable_local_memory_plus_gru4"):
        folds, prediction_records, diagnostics = [], [], []
        for held in contexts:
            train = [value for value in contexts if value.context_id != held.context_id]
            backbone = base.fit_backbone(train)
            predictions: dict[str, np.ndarray] = {}
            spread: dict[str, np.ndarray] | None = None
            if candidate_id == "stable_local_memory":
                predictions = {arm: base.predict_backbone(backbone, held, arm)
                               for arm in stage["nonhold_arm_ids"]}
            else:
                ensembles = {arm: [] for arm in stage["nonhold_arm_ids"]}
                seed_rows = []
                for seed in (17, 29, 43):
                    residual = base.fit_gru(train, backbone, basis, seed)
                    seed_rows.append({"seed": seed,
                                      "training_loss": residual["training_loss"],
                                      "parameter_count": residual["parameter_count"]})
                    for arm in stage["nonhold_arm_ids"]:
                        nominal = base.predict_backbone(backbone, held, arm)
                        ensembles[arm].append(
                            base.predict_gru(residual, held, arm, basis, nominal))
                spread = {}
                for arm, values in ensembles.items():
                    stacked = np.asarray(values)
                    predictions[arm] = stacked.mean(axis=0)
                    spread[arm] = stacked.std(axis=0)
                diagnostics.append({"context_id": held.context_id, "seeds": seed_rows})
            metrics = fold_metrics(stage, held, predictions, spread)
            transform = backbone["transform"]
            root = (base.root_vector(held) - transform["mean"]) / transform["scale"]
            train_roots = [((base.root_vector(value) - transform["mean"])
                            / transform["scale"]) for value in train]
            metrics.update({
                "root_support_distance": float(min(
                    np.linalg.norm(root - value) / math.sqrt(len(root))
                    for value in train_roots)),
                "backbone_feature_rank": backbone["feature_rank"],
                "backbone_feature_condition": backbone["feature_condition"],
                "backbone_parameter_count": backbone["parameter_count"],
            })
            folds.append(metrics)
            prediction_records.append({
                "context_id": held.context_id,
                "predictions_scaled": {arm: predictions[arm].tolist()
                                       for arm in predictions}})
        ok = eligible(folds, stage["selection_gates"])
        candidates.append({
            "candidate_id": candidate_id, "eligible": ok,
            "mean_response_nrmse": float(np.mean([x["response_nrmse"] for x in folds])),
            "maximum_response_nrmse": max(x["response_nrmse"] for x in folds),
            "maximum_r_p95_m": max(x["r_p95_m"] for x in folds),
            "maximum_z_p95_m": max(x["z_p95_m"] for x in folds),
            "maximum_ip_p95_a": max(x["ip_p95_a"] for x in folds),
            "minimum_peak_vector_cosine": min(x["minimum_peak_vector_cosine"] for x in folds),
            "maximum_best_arm_normalized_score_regret": max(
                x["best_arm_normalized_score_regret"] for x in folds),
            "folds": folds, "diagnostics": diagnostics})
        records[candidate_id] = prediction_records
    eligible_rows = sorted((x for x in candidates if x["eligible"]),
                           key=lambda x: (x["mean_response_nrmse"],
                                          0 if x["candidate_id"] == "stable_local_memory" else 1))
    winner = eligible_rows[0]["candidate_id"] if eligible_rows else None
    if len(eligible_rows) == 2 and abs(eligible_rows[0]["mean_response_nrmse"]
                                       - eligible_rows[1]["mean_response_nrmse"]) <= 0.01:
        winner = "stable_local_memory"
    artifact = None
    if winner is not None:
        full = base.fit_backbone(contexts)
        artifact = {"schema_version": "rgeo-zgeo-1ms-id2z10-model-artifact-v1",
                    "source_revision": source_revision,
                    "stage_config_sha256": CONFIG_SHA256,
                    "candidate_id": winner, "backbone": base.serialize_backbone(full)}
        if winner == "stable_local_memory_plus_gru4":
            artifact["gru_ensemble"] = [
                {"seed": seed, **base.serialize_gru(base.fit_gru(contexts, full, basis, seed))}
                for seed in (17, 29, 43)]
    route = stage["routes"]["pass" if winner is not None else "small_model_fail"]
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256, "passed": winner is not None,
        "route": route, "winner": winner, "independent_causal_contexts": 5,
        "fit_weight_windows": 25, "nonhold_evaluation_cells": 20,
        "folds": list(CONTEXT_IDS), "candidate_results": candidates,
        "prediction_records": records,
        "action_basis_rank": int(np.linalg.matrix_rank(basis)),
        "action_basis_condition": float(np.linalg.cond(basis)),
        "candidate_model_classes_evaluated": 2,
        "fold_backbone_fit_operations": 10, "fold_gru_fit_operations": 15,
        "full_data_artifact_fit_operations": (0 if winner is None else
                                              (1 if winner == "stable_local_memory" else 4)),
        "new_tsc_or_plant_advances": 0,
        "calibration_or_holdout_records_read": 0,
        "controller_or_optimizer_runs": 0,
        "claim_boundary": ("Five-context development model comparison only; not fresh "
                           "calibration, holdout, recovery, controller or reachability."),
    }
    if output is not None:
        output = base.inside(output, "output")
        if output.exists():
            raise FileExistsError(str(output))
        output.mkdir(parents=True)
        if artifact is not None:
            base.write_new(output / "model.json", artifact)
            result["model_sha256"] = base.sha256(output / "model.json")
        base.write_new(output / "result.json", result)
    return result, artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result, _ = execute(args.stage_config, args.source_revision, args.output)
    except Exception as exc:
        result = {"schema_version": SCHEMA, "source_revision": args.source_revision,
                  "stage_config_sha256": CONFIG_SHA256, "passed": False,
                  "route": "ONE_MS_ID2Z10_INPUT_OR_CAUSALITY_FAIL_NO_MODEL",
                  "failure": f"{type(exc).__name__}:{exc}",
                  "new_tsc_or_plant_advances": 0}
        if args.output is not None:
            output = base.inside(args.output, "output")
            output.mkdir(parents=True, exist_ok=True)
            if not (output / "result.json").exists():
                base.write_new(output / "result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
